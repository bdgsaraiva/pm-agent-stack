"""Banco Central do Brasil: SGS time series and Focus market expectations (Olinda OData). No key."""
from __future__ import annotations

from datetime import date
from urllib.parse import quote

import pandas as pd

from . import base

KIND = "obs"
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/dados"
SGS_HUMAN = "https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarValores&optSelecionaSerie={id}"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
FOCUS_HUMAN = "https://www.bcb.gov.br/publicacoes/focus"


def _sgs(sid: int, start: date) -> pd.DataFrame:
    # SGS limits daily series to 10-year windows; our backfill is shorter.
    js = base.get_json(SGS.format(id=sid), params={
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": date.today().strftime("%d/%m/%Y"),
    })
    df = pd.DataFrame(js)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.date
    df["value"] = pd.to_numeric(df["valor"], errors="coerce")
    return df[["date", "value"]]


def _focus(indicator: str, start: date) -> pd.DataFrame:
    flt = f"Indicador eq '{indicator}' and baseCalculo eq 0 and Data ge '{start.isoformat()}'"
    q = quote(flt, safe="'")
    url = (f"{OLINDA}?$top=10000&$format=json&$orderby=Data%20desc"
           f"&$select=Indicador,Data,DataReferencia,Mediana"
           f"&$filter={q}")
    js = base.get_json(url)
    return pd.DataFrame(js.get("value", []))


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = since or date.fromisoformat(cfg.get("backfill_start", "2022-01-01"))
    if isinstance(start, str):
        start = date.fromisoformat(start)
    fetched = base.now_utc()
    frames = []
    for s in cfg.get("sgs", []):
        df = _sgs(s["id"], start)
        if df.empty:
            continue
        frames.append(pd.DataFrame({
            "source": "bcb", "series_id": f"sgs.{s['id']}", "name": s["name"],
            "date": df["date"], "value": df["value"], "unit": s["unit"],
            "freq": "daily" if s["id"] in (1, 11) else "monthly" if s["id"] == 433 else "event",
            "source_url": SGS_HUMAN.format(id=s["id"]), "fetched_at": fetched,
        }))
    for f in cfg.get("focus", []):
        df = _focus(f["indicator"], start)
        if df.empty:
            continue
        slug = f["indicator"].lower().replace("â", "a")
        frames.append(pd.DataFrame({
            "source": "bcb",
            "series_id": "focus." + slug + "." + df["DataReferencia"].astype(str),
            "name": f["name"] + " for " + df["DataReferencia"].astype(str),
            "date": pd.to_datetime(df["Data"]).dt.date,
            "value": pd.to_numeric(df["Mediana"], errors="coerce"),
            "unit": "brl" if slug == "cambio" else "pct",
            "freq": "weekly", "source_url": FOCUS_HUMAN, "fetched_at": fetched,
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
