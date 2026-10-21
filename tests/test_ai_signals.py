"""AI compute-demand signals (21 Oct 2026): adapters on fake responses shaped like the real ones, the fact-pack section
(changes, point in time, smoothing, no alerts) and one offline fetch -> store -> monitor run. No network."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from pmstack import ai_signals, fetch, monitor, runlog, store
from pmstack.adapters import (ai_common, akash, census_c30, dramexchange, getdeploying, kcs, openrouter, ramp,
                              tsmc)

ROOT = Path(__file__).resolve().parents[1]
SRC = yaml.safe_load((ROOT / "config" / "sources.d" / "ai_signals.yaml").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)
ASOF = date(2026, 10, 21)
FETCHED = NOW


# ---------------------------------------------------------------- fake payloads
def gd_csv() -> str:
    weeks = pd.date_range("2025-10-20", "2026-10-19", freq="W-MON")
    lines = ["gpu_slug,date,billing_type,reservation_months,min_price,max_price,median_price,provider_median_price,provider_count,offering_count"]
    for i, w in enumerate(weeks):
        for slug, p0, n in [("nvidia-h100", 3.0, 40), ("nvidia-b200", 6.0, 19), ("nvidia-a100", 1.8, 3)]:
            p = p0 * (1 + 0.004 * i)
            lines.append(f"{slug},{w:%Y-%m-%d},ON_DEMAND,,1,9,{p:.4f},{p:.4f},{n},50")
        lines.append(f"nvidia-h100,{w:%Y-%m-%d},SPOT,,1,9,1.0,1.0,10,10")       # spot rows are not on-demand
    return "\n".join(lines)


def akash_prices() -> dict:
    return {"availability": {"total": 368, "available": 122}, "models": [
        {"model": "h100", "ram": "80Gi", "interface": "SXM5", "availability": {"total": 69, "available": 5},
         "price": {"min": 2.0, "med": 2.56, "avg": 2.58, "weightedAverage": 2.7, "max": 3.1}},
        {"model": "h100", "ram": "80Gi", "interface": "PCIe", "availability": {"total": 4, "available": 4},
         "price": {"min": 1.0, "med": 1.5, "avg": 1.5, "weightedAverage": 1.5, "max": 2.0}},
        {"model": "b300", "ram": "288Gi", "interface": "SXM6", "availability": {"total": 24, "available": 0}, "price": None},
        {"model": "rtx4090", "availability": {"total": 4, "available": 2}, "price": {"med": 0.34}}]}


def akash_util() -> dict:
    days = pd.date_range("2025-06-01", "2026-10-21", freq="D")
    return {"currentValue": 71.7, "snapshots": [{"date": f"{d:%Y-%m-%d}T00:00:00.000Z", "value": 50 + 0.04 * i}
                                                for i, d in enumerate(days)]}


DX_HTML = """<html><body>
<div>DRAM Spot Price Last Update: Oct.21 2026 18:10 (GMT+8)</div><table>
<tr><td class="tab_title">Item</td><td>Daily High</td><td>Daily Low</td><td>Session High</td><td>Session Low</td><td>Session Average</td><td>Session Change</td><td>History</td></tr>
<tr><td class="tab_tr_gray2"><a href="/Price/Dram_Spot"><img src="/x.gif">
      DDR5 16Gb (2Gx8) 4800/5600
    </a></td><td>71.00</td><td>46.50</td><td>71.00</td><td>46.80</td><td>60.867</td><td><img src="/up.gif"><br>0.28 %</td><td></td></tr>
<tr><td><a>DDR4 16Gb (2Gx8) 3200</a></td><td>116.00</td><td>45.50</td><td>116.00</td><td>45.50</td><td>83.117</td><td>-0.30 %</td><td></td></tr>
</table>
<div>Module Spot Price Last Update:Oct.12 2026 14:40 (GMT+8)</div><table>
<tr><td><a>DDR5 RDIMM 32GB 4800/5600</a></td><td>2420.00</td><td>2130.00</td><td>2420.00</td><td>2130.00</td><td>2,185.000</td><td>0.41 %</td><td></td></tr>
</table></body></html>"""


def or_payload(params) -> dict:
    a, b = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
    rows, d = [], a
    while d <= b:
        k = (d - date(2025, 1, 1)).days
        rows += [{"date": str(d), "model_permaslug": "x/model-a", "total_tokens": str(int(6e11 + 1e9 * k))},
                 {"date": str(d), "model_permaslug": "y/model-b", "total_tokens": str(int(3e11))},
                 {"date": str(d), "model_permaslug": "other", "total_tokens": str(int(1e11))}]
        d += timedelta(days=1)
    return {"data": rows, "meta": {"as_of": "2026-10-21T02:00:00.000Z", "start_date": str(a), "end_date": str(b)}}


def ramp_page() -> str:
    months = pd.date_range("2024-09-01", "2026-09-01", freq="MS")
    overall = [{"date_month": f"{m:%Y-%m-%d}", "adoption_rate_pct": round(40 + 0.6 * i, 2), "mom_change_pp": 0.6,
                "yoy_change_pp": None} for i, m in enumerate(months)]
    share = [{"my_date": f"{m:%Y-%m-%d}", "ai_share_of_tpv": 0.03 + 0.001 * i} for i, m in enumerate(months)]
    vend = [{"date_month": f"{m:%Y-%m-%d}", "vendor": v, "adoption_rate_pct": 20 + i, "mom_change_pp": 1}
            for i, m in enumerate(months) for v in ("OpenAI", "Anthropic", "xAI")]
    blob = json.dumps({"adoptionOverall": overall, "x": 1, "adoptionVendor": vend,
                       "spendShareData": {"overall": share, "bySize": []}}, separators=(",", ":"))
    return '<html><script>self.__next_f.push([1,"' + blob.replace('"', '\\"') + '"])</script></html>'


def census_xlsx() -> bytes:
    strings = ["Value of Private Construction Put in Place", "Date", "Total\n_x000D_Private Construction1",
               "Nonresidential", "Data center", "Electric"]
    months = pd.date_range("2024-01-01", "2026-08-01", freq="MS")[::-1]
    sheet = ['<row r="1"><c r="A1" t="s"><v>0</v></c></row>',
             '<row r="4"><c r="A4" t="s"><v>1</v></c><c r="B4" t="s"><v>2</v></c><c r="C4" t="s"><v>3</v></c>'
             '<c r="D4" t="s"><v>4</v></c><c r="E4" t="s"><v>5</v></c></row>']
    for i, m in enumerate(months):
        r = 5 + i
        lab = f"{m:%b-%y}" + ("p" if i == 0 else "r" if i < 3 else "")
        sheet.append(f'<row r="{r}"><c r="A{r}" t="inlineStr"><is><t>{lab}</t></is></c><c r="B{r}"><v>1600000</v></c>'
                     f'<c r="C{r}"><v>750000</v></c><c r="D{r}"><v>{85000 - 1500 * i}</v></c><c r="E{r}"><v>140000</v></c></row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    sst = f'<sst {ns}>' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData>{"".join(sheet)}</sheetData></worksheet>')
    return buf.getvalue()


def tsmc_page(year: int) -> str:
    vals = {2026: [(m, 400_000 + 10_000 * m, 30 + m) for m in range(1, 10)],
            2025: [(m, 300_000 + 8_000 * m, 20.5) for m in range(1, 13)]}.get(year, [(m, 200_000, -1.5) for m in range(1, 13)])
    names = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
    rows = "".join(f"<tr><td>{names[m - 1]}</td><td>{v:,}</td><td>{y}%</td></tr>" for m, v, y in vals)
    return (f"<html><body><nav>Monthly Revenue Jan. 999,999 9.9%</nav><h2>{year} Monthly Revenue (In Millions of New "
            f"Taiwan Dollars)</h2><table><tr><th>Month</th><th>Consolidated Net Revenue</th><th>YoY Change</th></tr>{rows}"
            f"<tr><td>Total</td><td>1</td><td>1%</td></tr></table></body></html>")


KCS_LIST = """<table>
<tr><td><a href="javascript:" data-id="10180466" data-url="aa11" class="nttInfoBtn" title="관세청, 코리아 커스텀즈 위크 개최">x</a></td>
<td data-table="date">2026.10.21</td></tr>
<tr><td><a href="javascript:" data-id="10180465" data-url="bb22" class="nttInfoBtn" title="2026년 10월 1일 ~ 10월 20일 수출입 현황 [잠정치]">
<em class="new">새글</em> 2026년 10월 1일 ~ 10월 20일 수출입 현황 [잠정치]</a></td><td data-table="write">이준</td>
<td data-table="date">2026.10.21</td></tr>
<tr><td><a href="javascript:" data-id="10178304" data-url="cc33" class="nttInfoBtn" title="2026년 9월 수출입 현황 [잠정치]">x</a></td>
<td data-table="date">2026.10.01</td></tr>
<tr><td><a href="javascript:" data-id="10177443" data-url="dd44" class="nttInfoBtn" title="2026년 9월 1일 ~ 9월 20일 수출입 현황 [잠정치]">x</a></td>
<td data-table="date">2026.09.21</td></tr>
</table>"""

KCS_INFO = {
    "10180465": """<div>요 약 > ◇ 관세청은 21 일 , 10 월 1 일 ~20 일 기간의 수출입 현황 잠정치를 발표 했다 . ◇ 동기간 수출은 616 억 달러 로
        전년동기대비 105.4% 증가 , 수입은 471 억 달러 로 42.8% 증가 했으며 → 반도체 (275 억 달러 ) 수출 10 월 기준 역대최대</div>
        <a href="/common/nttFileDownload.do?fileKey=8e52" title="261021 수출입 현황.pdf 다운로드">pdf</a>""",
    "10177443": """<div>요 약 > ◇ 동 기 간 수 출 은 714 억 달 러로 전 년 동 기 대 비 78.3% 증 가 , 수입은 484억 달러로 26.7% 증가
        (주요품목) 전년동기대비 반도체(259.4%), 석유제품(10.0%) 등 증가 - 반도체 수출 비중은 47.8%로 20.1%p 증가
        (수입) 반도체(50.0%)</div>""",
}
KCS_PDF_TEXT = "ㅇ (주요품목) 전년동기대비 반도체(222.5%), 석유제품(68.3%) 등 증가\n - 반도체 수출 비중은 44.7%로 16.2%p 증가"


class FakeResp:
    def __init__(self, text: str = "", content: bytes | None = None, js=None, status: int = 200):
        self.text, self._js, self.status_code = text, js, status
        self.content = content if content is not None else text.encode("utf-8")
        self.ok = status == 200

    def json(self):
        return self._js

    def raise_for_status(self):
        if self.status_code != 200:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


def fake_get(url, cfg, params=None, headers=None, **kw):
    if "getdeploying" in url:
        return FakeResp(gd_csv())
    if url.endswith("/gpu-prices"):
        return FakeResp(js=akash_prices())
    if "gpuUtilization" in url:
        return FakeResp(js=akash_util())
    if "dramexchange" in url:
        return FakeResp(DX_HTML)
    if "openrouter" in url:
        assert headers["Authorization"] == "Bearer test-key"
        return FakeResp(js=or_payload(params))
    if "ramp.com" in url:
        return FakeResp(ramp_page())
    if "census.gov" in url:
        return FakeResp(content=census_xlsx())
    if "tsmc" in url:
        return FakeResp(tsmc_page(int(url.rsplit("/", 1)[1])))
    raise AssertionError(f"unexpected URL {url}")


class FakeSession:
    """requests.Session stand-in for the KCS board: list page, release page (POST), PDF attachment."""
    pdf_calls = 0

    def __init__(self):
        self.headers = {}

    def request(self, method, url, params=None, data=None, headers=None, timeout=None):
        if url.endswith("selectNttList.do"):
            return FakeResp(KCS_LIST if (params or {}).get("currPage") == 1 else "<table></table>")
        if url.endswith("selectNttInfo.do"):
            return FakeResp(KCS_INFO[data["nttSn"]])
        if "nttFileDownload" in url:
            FakeSession.pdf_calls += 1
            return FakeResp(content=b"%PDF-fake")
        raise AssertionError(url)


@pytest.fixture()
def fakes(monkeypatch):
    monkeypatch.setattr(ai_common, "get", fake_get)
    monkeypatch.setattr(kcs.requests, "Session", FakeSession)
    monkeypatch.setattr(kcs, "_pdf_text", lambda blob: KCS_PDF_TEXT)
    monkeypatch.setattr(ai_common.base, "now_utc", lambda: NOW)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


# ---------------------------------------------------------------- adapters
def test_getdeploying_keeps_on_demand_models_with_enough_providers():
    rows = getdeploying.records(gd_csv(), SRC["ai_gpu_gd"], FETCHED)
    ids = {r["series_id"] for r in rows}
    assert "gd:nvidia-h100" in ids and "gd:nvidia-b200:n" in ids
    assert "gd:nvidia-a100" not in ids                                     # 3 providers < min_providers 4
    h = sorted((r for r in rows if r["series_id"] == "gd:nvidia-h100"), key=lambda r: r["date"])
    assert h[0]["value"] == pytest.approx(3.0) and h[-1]["date"] == date(2026, 10, 19) and h[-1]["freq"] == "weekly"


def test_akash_snapshot_takes_the_largest_variant_and_utilisation_history():
    rows = akash.snapshot(akash_prices(), SRC["ai_gpu_akash"], ASOF, FETCHED)
    by = {r["series_id"]: r["value"] for r in rows}
    assert by["akash:h100"] == 2.56 and by["akash:gpus"] == 368            # SXM5 (69 GPUs) beats PCIe (4)
    assert by["akash:h100:avail"] == pytest.approx(100 * 5 / 69)
    assert "akash:b300" not in by and "akash:rtx4090" not in by           # no price / not configured
    util = akash.utilisation(akash_util(), FETCHED, since=date(2026, 10, 1))
    assert {r["date"] for r in util} == {date(2026, 10, d) for d in range(1, 22)}


def test_dramexchange_reads_session_average_dated_at_its_table_update():
    rows, errors = dramexchange.parse(DX_HTML, SRC["ai_dram"]["items"], FETCHED)
    by = {r["series_id"]: r for r in rows}
    assert by["dx:ddr5_16gb"]["value"] == 60.867 and by["dx:ddr5_16gb"]["date"] == date(2026, 10, 21)
    assert by["dx:ddr5_rdimm_32gb"]["value"] == 2185.0 and by["dx:ddr5_rdimm_32gb"]["date"] == date(2026, 10, 12)
    assert errors == []
    rows, errors = dramexchange.parse(DX_HTML.replace("DDR4 16Gb (2Gx8) 3200", "DDR4 renamed"), SRC["ai_dram"]["items"], FETCHED)
    assert any("DDR4 16Gb" in e for e in errors) and len(rows) == 2       # a layout change is an error, not a crash


def test_openrouter_sums_the_day_and_is_skipped_without_key(monkeypatch):
    rows = openrouter.records(or_payload({"start_date": "2026-10-19", "end_date": "2026-10-20"}), FETCHED)
    tok = [r for r in rows if r["series_id"] == "or:tokens"]
    assert len(tok) == 2 and tok[0]["value"] == pytest.approx(6e11 + 1e9 * 656 + 3e11 + 1e11)
    share = [r for r in rows if r["series_id"] == "or:top_share"][0]["value"]
    assert 60 < share < 80
    w = openrouter.windows(None, date(2026, 10, 21))
    assert w[0][0] == date(2025, 1, 1) and w[-1][1] == date(2026, 10, 20) and all((b - a).days <= 365 for a, b in w)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    df = openrouter.fetch(SRC["ai_tokens_or"], None)
    assert df.empty and "OPENROUTER_API_KEY" in df.attrs["skipped"]


def test_ramp_parses_the_embedded_page_data():
    rows, errors = ramp.records(ramp_page(), SRC["ai_ramp"], FETCHED)
    by = {}
    for r in rows:
        by.setdefault(r["series_id"], []).append(r)
    assert errors == [] and set(by) == {"ramp:adoption", "ramp:spend_share", "ramp:adoption:openai", "ramp:adoption:anthropic"}
    last = max(by["ramp:adoption"], key=lambda r: r["date"])
    assert last["date"] == date(2026, 9, 1) and last["value"] == pytest.approx(40 + 0.6 * 24)
    assert max(by["ramp:spend_share"], key=lambda r: r["date"])["value"] == pytest.approx(100 * (0.03 + 0.024))
    rows, errors = ramp.records("<html>nothing</html>", SRC["ai_ramp"], FETCHED)
    assert rows == [] and errors


def test_census_workbook_columns_by_label_and_revision_marks():
    rows, errors = census_c30.records(census_xlsx(), SRC["ai_census_dc"], FETCHED)
    assert errors == []
    dc = sorted((r for r in rows if r["series_id"] == "census:data_center"), key=lambda r: r["date"])
    assert dc[-1]["date"] == date(2026, 8, 1) and dc[-1]["value"] == 85000          # "Aug-26p"
    assert {r["series_id"] for r in rows} == {"census:data_center", "census:private_nonres", "census:electric"}
    bad = {**SRC["ai_census_dc"], "series": [{"slug": "x", "column": "Nope", "name": "x"}]}
    assert census_c30.records(census_xlsx(), bad, FETCHED)[1] == ["column 'Nope' not found"]


def test_tsmc_reads_the_year_table_only():
    rows = tsmc.records(tsmc_page(2026), 2026, FETCHED)
    rev = [r for r in rows if r["series_id"] == "tsmc:revenue"]
    assert len(rev) == 9 and rev[-1]["date"] == date(2026, 9, 1) and rev[-1]["value"] == 490_000   # nav text ignored
    assert [r for r in rows if r["series_id"] == "tsmc:revenue_yoy"][-1]["value"] == 39


def test_kcs_titles_list_and_release_text():
    assert kcs.classify("2026년 10월 1일 ~ 10월 20일 수출입 현황 [잠정치]") == ("d20", 2026, 10, "1-20 Oct 2026")
    assert kcs.classify("2026년 10월 1일 ~ 10월 10일 수출입 현황 [잠정치]")[0] == "d10"
    assert kcs.classify("2026년 9월 월간 수출입 현황 [확정치]") == ("m", 2026, 9, "Sep 2026 final")
    assert kcs.classify("2026년 9월 수출입 현황 [잠정치]") is None          # states no chip figure
    assert kcs.classify("2026년 9월 수출입 운송비용 현황") is None
    it = kcs.items(KCS_LIST)
    assert [x["date"] for x in it] == [date(2026, 10, 21)] * 2 + [date(2026, 10, 1), date(2026, 9, 21)]
    f = kcs.parse(KCS_INFO["10177443"])                                   # spaced-out PDF text; share x total
    assert f["exports"] == pytest.approx(71.4) and f["exports_yoy"] == 78.3 and f["chips_yoy"] == 259.4
    assert f["chips"] == pytest.approx(71.4 * 0.478) and f["chips_derived"]
    m = kcs.parse("전년 동월 대비 수출은 83.7% 증가한 1,211억 달러, 반도체 수출(605억 달러) 최초 "
                  "(품목별) 반도체(전년동월대비 증감률 260.3%)ㆍ승용차(△5.6%)")
    assert m["exports"] == pytest.approx(121.1) and m["chips"] == pytest.approx(60.5) and m["chips_yoy"] == 260.3
    neg = kcs.parse("수출은 300억 달러로 전년동기대비 △8.3% 감소 반도체(△12.0%)")
    assert neg["exports_yoy"] == -8.3 and neg["chips_yoy"] == -12.0


def test_kcs_fetch_skips_stored_prints(fakes):
    df = kcs.fetch(SRC["ai_kcs"], None)
    by = {(r.series_id, str(r.date)): r.value for r in df.itertuples()}
    assert by[("kcs:chips:d20", "2026-10-21")] == pytest.approx(27.5)          # stated in the summary
    assert by[("kcs:chips_yoy:d20", "2026-10-21")] == 222.5                   # from the PDF text
    assert by[("kcs:chips:d20", "2026-09-21")] == pytest.approx(71.4 * 0.478, abs=1e-3)
    assert not any(s.endswith(":mp") for s, _ in by)
    again = kcs.fetch({**SRC["ai_kcs"], "_last": {"kcs:exports:d20": date(2026, 10, 21)}}, date(2026, 10, 7))
    assert again.empty


# ---------------------------------------------------------------- section
def _obs(sid, dates, values, freq="weekly", source="getdeploying", name=None):
    return pd.DataFrame({"source": source, "series_id": sid, "name": name or sid, "date": [pd.Timestamp(d).date() for d in dates],
                         "value": values, "unit": "", "freq": freq, "source_url": "https://example.org/", "fetched_at": NOW})


def test_section_changes_point_in_time_and_no_alerts():
    weeks = pd.date_range("2025-10-20", "2026-10-19", freq="W-MON")
    months = pd.date_range("2025-01-01", "2026-09-01", freq="MS")
    obs = pd.concat([
        _obs("gd:nvidia-h100", weeks, np.linspace(3.0, 3.7, len(weeks))),
        _obs("ramp:adoption", months, [40 + i for i in range(len(months))], "monthly", "ramp"),
        _obs("tsmc:revenue", months, [400_000.0] * (len(months) - 1) + [500_000.0], "monthly", "tsmc")], ignore_index=True)
    sec, alerts = ai_signals.build(obs, date(2026, 10, 21))
    assert alerts == []
    r = {x["id"]: x for x in sec["rows"]}
    h = r["gd:nvidia-h100"]
    assert h["value"] == pytest.approx(3.7) and h["prev"]["change"] == pytest.approx((3.7 / h["prev"]["from"] - 1) * 100, abs=0.01)
    assert h["1y"]["from_date"] == "2025-10-20"                            # nearest print either side, within tolerance
    a = r["ramp:adoption"]
    assert a["date"] == "2026-09-01" and a["prev"]["change"] == pytest.approx(1.0) and a["1y"]["change"] == pytest.approx(12.0)
    t = r["tsmc:revenue"]
    assert t["value"] == pytest.approx(500.0) and t["prev"]["change"] == pytest.approx(25.0)   # scaled to NT$ bn
    # point in time: on 5 Oct the September TSMC figure (public ~10 Oct) and Ramp's (mid-October) are not yet out
    early = {x["id"]: x for x in ai_signals.build(obs, date(2026, 10, 5))[0]["rows"]}
    assert early["tsmc:revenue"]["date"] == "2026-08-01" and early["ramp:adoption"]["date"] == "2026-08-01"
    assert "OpenRouter tokens per day (7-day mean)" in sec["no_data"]
    text = "\n".join(ai_signals.render(sec))
    assert "## AI demand signals" in text and "| cloud compute | H100 rental" in text and "+12.0 pp" in text


def test_section_smooths_daily_tokens_and_flags_stale():
    days = pd.date_range("2026-08-01", "2026-10-10", freq="D")
    vals = [1e12 if d.dayofweek < 5 else 0.5e12 for d in days]
    obs = _obs("or:tokens", days, vals, "daily", "openrouter")
    sec, _ = ai_signals.build(obs, date(2026, 10, 21))
    r = sec["rows"][0]
    assert r["value"] == pytest.approx((5 * 1 + 2 * 0.5) / 7, rel=1e-6)    # 7-day mean, in trillions
    assert r["stale"] and "(stale)" in "\n".join(ai_signals.render(sec))   # 11 days old > 7 + 1


def test_render_survives_an_error_and_an_empty_store():
    assert "Not available: boom" in "\n".join(ai_signals.render({"error": "boom"}))
    sec, _ = ai_signals.build(pd.DataFrame(), ASOF)
    assert sec["rows"] == [] and "No AI demand data stored yet" in "\n".join(ai_signals.render(sec))


# ---------------------------------------------------------------- fetch -> store -> monitor
def test_fetch_store_and_fact_pack(tmp_path, monkeypatch, fakes):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(monitor, "BRIEFS", tmp_path / "briefs")
    from pmstack import journal
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    monkeypatch.setattr(fetch, "load_sources", lambda: SRC)
    res = fetch.run()
    status = {r["step"]: r["status"] for r in res}
    assert status == {f"fetch:{k}": "ok" for k in SRC}, res
    con = store.connect()
    assert con.execute("SELECT count(*) FROM obs WHERE source_url IS NULL OR fetched_at IS NULL").fetchone()[0] == 0
    facts = monitor.build(asof=ASOF, now=NOW)
    sec = facts["sections"]["ai_signals"]
    assert "error" not in sec, sec
    parts = {r["part"] for r in sec["rows"]}
    assert parts == {"applications", "cloud compute", "data centres"}
    assert not [a for a in facts["alerts"] if str(a.get("kind", "")).startswith("ai")]
    md = (tmp_path / "briefs" / str(ASOF) / "facts.md").read_text(encoding="utf-8")
    assert "## AI demand signals" in md and "Korea chip exports, 1-20 day print" in md

    # one source down (a site blocking the runner) costs only that source
    def broken(url, cfg, **kw):
        if "dramexchange" in url:
            raise RuntimeError("HTTP 403 for https://www.dramexchange.com/")
        return fake_get(url, cfg, **kw)
    monkeypatch.setattr(ai_common, "get", broken)
    res = fetch.run()
    status = {r["step"]: r["status"] for r in res}
    assert status["fetch:ai_dram"] == "error" and status["fetch:ai_gpu_gd"] == "ok"
