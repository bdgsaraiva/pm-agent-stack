"""ANP (Brazil) open data: national crude production and fuel sales, monthly (free CSV, no key; CC Attribution).

Files on gov.br/anp (dados abertos): `producao-petroleo-m3.csv` (by state and onshore/offshore, from 1997) and
`vendas-combustiveis-m3-1990-2025.csv` (by state and product, from 1990; rows run into the current year). Months
not yet published appear as 0 in the production file: a month whose national total is 0 is dropped. Production is
also converted to kb/d (1 m3 = 6.2898 bbl; calendar days of the month). Sales are updated "by the last day of the
following month" (ANP), so a reader uses each month from about 60 days after it ends (point in time).
"""
from __future__ import annotations

import io

import pandas as pd

from . import base

KIND = "obs"
BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/"
MONTHS = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}
BBL_PER_M3 = 6.2898


def _csv(path: str, timeout: int) -> pd.DataFrame:
    import requests
    r = requests.get(BASE + path, timeout=timeout, headers={"User-Agent": "pm-agent-stack (personal research)"})
    r.raise_for_status()
    txt = r.content.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(txt), sep=";", dtype=str)
    df.columns = [c.strip().upper() for c in df.columns]
    return df


def _month(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["ANO"].astype(int).astype(str) + "-" + df["MÊS"].str.strip().str.upper().map(MONTHS).astype(str) + "-01")


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    timeout = int(cfg.get("timeout_s", 60))
    fetched = base.now_utc()
    frames, errors = [], []
    try:
        p = _csv(cfg["production_file"], timeout)
        p = p[p["PRODUTO"].str.upper().str.contains("PETR")]
        p["date"], p["v"] = _month(p), _num(p["PRODUÇÃO"])
        tot = p.groupby("date")["v"].sum()
        tot = tot[tot > 0]
        days = tot.index.days_in_month
        url = BASE + cfg["production_file"]
        frames.append(pd.DataFrame({"source": "anp", "series_id": "anp:crude_production_m3", "name": "Brazil crude production (ANP)",
                                    "date": tot.index.date, "value": tot.values, "unit": "m3", "freq": "monthly",
                                    "source_url": url, "fetched_at": fetched}))
        frames.append(pd.DataFrame({"source": "anp", "series_id": "anp:crude_production_kbd", "name": "Brazil crude production (ANP, kb/d)",
                                    "date": tot.index.date, "value": tot.values * BBL_PER_M3 / days / 1000.0, "unit": "kbd",
                                    "freq": "monthly", "source_url": url, "fetched_at": fetched}))
    except Exception as e:  # noqa: BLE001
        errors.append(f"production: {e}")
    try:
        s = _csv(cfg["sales_file"], timeout)
        s["date"], s["v"] = _month(s), _num(s["VENDAS"])
        want = {k.upper(): v for k, v in cfg["products"].items()}
        s = s[s["PRODUTO"].str.strip().str.upper().isin(want)]
        g = s.groupby([s["PRODUTO"].str.strip().str.upper(), "date"])["v"].sum().reset_index()
        g = g[g["v"] > 0]
        frames.append(pd.DataFrame({"source": "anp", "series_id": "anp:sales_m3:" + g["PRODUTO"].map(want),
                                    "name": "Brazil fuel sales (ANP): " + g["PRODUTO"].str.title(), "date": g["date"].dt.date,
                                    "value": g["v"], "unit": "m3", "freq": "monthly", "source_url": BASE + cfg["sales_file"],
                                    "fetched_at": fetched}))
    except Exception as e:  # noqa: BLE001
        errors.append(f"sales: {e}")
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["errors"] = errors
    if errors and not frames:
        raise RuntimeError("; ".join(errors)[:500])
    return out
