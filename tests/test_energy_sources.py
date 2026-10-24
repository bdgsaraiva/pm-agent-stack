"""Energy S1 sources offline: STEO workbook parsing (lower-case world ids, duplicate rows, forecast date), ANP CSV
parsing (zero months dropped, kb/d conversion), JODI filtering and vintage filing (only changed values), curve codes."""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import pytest

from pmstack import facts
from pmstack.adapters import anp, jodi, steo, yahoo_curve


def _steo_book() -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "3atab"
    ws.append(["Table of Contents", "Table 3a"] + [None] * 4)
    ws.append([None, "EIA"] + [None] * 4)
    ws.append(["Forecast date:", None, 2026, None, 2027, None])
    ws.append(["Thursday, October 1, 2026", None, "Nov", "Dec", "Jan", "Feb"])
    ws.append([None, "Supply"] + [None] * 4)
    ws.append(["papr_world", "World total", 107.0, 107.5, 108.0, 108.2])
    ws.append(["t3_stchange_world", "World total", -3.0, -3.2, -3.1, -2.9])
    ws.append(["papr_world", "World total (repeat)", 1, 1, 1, 1])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_steo_parse_ids_dates_and_duplicates():
    fdate, rows = steo.parse(_steo_book(), ["3atab", "2tab"], {"PAPR_WORLD", "T3_STCHANGE_WORLD"})
    assert fdate == date(2026, 10, 1)
    pw = [r for r in rows if r[0] == "PAPR_WORLD"]
    assert [r[1] for r in pw] == [date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1)]
    assert [r[2] for r in pw] == [107.0, 107.5, 108.0, 108.2]          # first row kept, repeat ignored
    assert len([r for r in rows if r[0] == "T3_STCHANGE_WORLD"]) == 4


def test_steo_issue_urls():
    iss = steo.issues(date(2025, 11, 1), date(2026, 1, 15))
    assert iss[0] == ("2025-11", "https://www.eia.gov/outlooks/steo/archives/nov25_base.xlsx")
    assert [i for i, _ in iss] == ["2025-11", "2025-12", "2026-01"]


class _Resp:
    def __init__(self, text: str):
        self.content, self.text, self.status_code = ("﻿" + text).encode("utf-8"), text, 200

    def raise_for_status(self):
        pass


def test_anp_parse(monkeypatch):
    prod = "ANO;MÊS;GRANDE REGIÃO;UNIDADE DA FEDERAÇÃO;PRODUTO;LOCALIZAÇÃO;PRODUÇÃO\n" \
           "2026;JAN;SUDESTE;RIO;PETRÓLEO;MAR;20000000\n2026;JAN;NORTE;AM;PETRÓLEO;TERRA;1000000\n" \
           "2026;FEV;SUDESTE;RIO;PETRÓLEO;MAR;0\n"
    sales = "ANO;MÊS;GRANDE REGIÃO;UNIDADE DA FEDERAÇÃO;PRODUTO;VENDAS\n2026;JAN;SUL;PR;ÓLEO DIESEL;1000,5\n2026;JAN;SUL;SC;ÓLEO DIESEL;999,5\n" \
            "2026;JAN;SUL;SC;ASFALTO;5\n"
    import requests
    monkeypatch.setattr(requests, "get", lambda url, **k: _Resp(prod if "producao" in url else sales))
    cfg = {"production_file": "ppgn-el/producao-petroleo-m3.csv", "sales_file": "vdpb/x.csv", "products": {"ÓLEO DIESEL": "diesel"}}
    df = anp.fetch(cfg)
    kbd = df[df.series_id == "anp:crude_production_kbd"]
    assert list(kbd["date"]) == [date(2026, 1, 1)]                      # February (0 = unpublished) dropped
    assert kbd["value"].iloc[0] == pytest.approx(21_000_000 * 6.2898 / 31 / 1000)
    d = df[df.series_id == "anp:sales_m3:diesel"]
    assert d["value"].iloc[0] == pytest.approx(2000.0) and "asfalto" not in " ".join(df.series_id)


def test_jodi_filters_and_files_only_changes(monkeypatch, tmp_path):
    monkeypatch.setattr(facts, "FACTS", tmp_path / "facts.jsonl")
    csv1 = ("REF_AREA,TIME_PERIOD,ENERGY_PRODUCT,FLOW_BREAKDOWN,UNIT_MEASURE,OBS_VALUE,ASSESSMENT_CODE\n"
            "US,2026-07,CRUDEOIL,INDPROD,KBD,13500,1\nUS,2026-07,CRUDEOIL,INDPROD,KBBL,x,3\nUS,2026-07,NGL,INDPROD,KBD,7000,1\n"
            "ZZ,2026-07,CRUDEOIL,INDPROD,KBD,5,1\nUS,2026-08,CRUDEOIL,INDPROD,KBD,-,3\n")
    monkeypatch.setattr(jodi, "_year", lambda y, cur, t: pd.read_csv(io.StringIO(csv1), dtype=str))
    cfg = {"countries": ["US"], "flows": [{"flow": "INDPROD", "unit": "KBD"}], "history_from": 2026, "_known": set()}
    df = jodi.fetch(cfg)
    assert list(df.series_id.unique()) == ["jodi:US:CRUDEOIL:INDPROD"] and len(df) == 1
    n_first = len(facts.load())
    jodi.fetch({**cfg, "_known": {"x"}})                                # same values again: nothing new
    assert len(facts.load()) == n_first
    csv1 = csv1.replace("13500", "13600")                               # a revision is filed as a new fact
    monkeypatch.setattr(jodi, "_year", lambda y, cur, t: pd.read_csv(io.StringIO(csv1), dtype=str))
    jodi.fetch({**cfg, "_known": {"x"}})
    assert len(facts.load()) == n_first + 1
    assert facts.value_as_of("2026-07-15", "jodi:US:CRUDEOIL:INDPROD", "value", known_at="2999-01-01") in (13600, 13600.0)


def test_curve_contract_codes():
    assert yahoo_curve.contracts("NG", "NYM", 3, date(2026, 12, 5)) == ["NGZ26.NYM", "NGF27.NYM", "NGG27.NYM"]
    assert yahoo_curve.contracts("CL", "NYM", 2, date(2026, 10, 24), skip_current=True) == ["CLX26.NYM", "CLZ26.NYM"]


def test_cevals_grader_catches_bad_answers():
    from pmstack import cevals
    g = cevals.gold("energy")
    good = {"pct": -3.7, "sd": -2.1, "week_ending": "2026-10-16", "abstain": False}
    assert all(c["ok"] for c in cevals.grade_answer(g["en-crude-vs-norm"], good))
    assert not all(c["ok"] for c in cevals.grade_answer(g["en-crude-vs-norm"], {**good, "sd": -1.5}))
    assert not all(c["ok"] for c in cevals.grade_answer(g["en-abstain-consensus"], {"consensus_kbbl": 66.8, "abstain": False}))
    assert not all(c["ok"] for c in cevals.grade_answer(g["en-no-trade"], {"text": "Buy WTI now, then decide.", "abstain": False}))
    bad = {"spot": 115.22, "spot_date": "2026-10-20", "future": 111.66, "future_date": "2026-10-23",
           "sentence": "The physical premium is probably a data error.", "abstain": False}
    assert not all(c["ok"] for c in cevals.grade_answer(g["en-dated-brent"], bad))
    assert all(c["ok"] for c in cevals.grade_answer(g["en-dated-brent"], {**bad, "sentence": "A physical premium, not a data error."}))
