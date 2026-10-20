"""Research memory store: Parquet files on disk, queried through DuckDB.

Two tables, one file per source:
  data/obs/<source>/<year>.parquet   numeric observations (one row per series per date)
  data/text/<source>.parquet  text items (central-bank statements, news, filings)

Every row carries its source URL and fetch time, so any number in a note can be
traced back to where it came from.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

OBS_COLS = ["source", "series_id", "name", "date", "value", "unit", "freq", "source_url", "fetched_at"]
TEXT_COLS = ["source", "item_id", "title", "url", "published", "summary", "fetched_at"]


def _validate(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"adapter output missing columns: {missing}")
    out = df[cols]
    out.attrs = {}            # adapter side-channel (errors, headline frames) must not reach Parquet metadata
    return out


def upsert_obs(source: str, df: pd.DataFrame, root: Path | None = None) -> int:
    """Append observations into data/obs/<source>/<year>.parquet.

    On duplicate (series_id, date) the latest fetch wins (a provisional or live value is
    replaced by the final one). Year partitions keep daily git commits small: only the
    current year's file changes on a normal day. Returns total rows across touched years.
    """
    root = root or DATA
    if df is None or df.empty:
        return 0
    df = _validate(df.copy(), OBS_COLS)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    folder = root / "obs" / source
    folder.mkdir(parents=True, exist_ok=True)
    total = 0
    for year, part in df.groupby(pd.to_datetime(df["date"]).dt.year):
        path = folder / f"{year}.parquet"
        if path.exists():
            old = pd.read_parquet(path)
            old["date"] = pd.to_datetime(old["date"]).dt.date
            part = pd.concat([old, part], ignore_index=True)
        part = (part.sort_values("fetched_at")
                    .drop_duplicates(["series_id", "date"], keep="last")
                    .sort_values(["series_id", "date"])
                    .reset_index(drop=True))
        part.to_parquet(path, index=False)
        total += len(part)
    return total


def upsert_text(source: str, df: pd.DataFrame, root: Path | None = None, keep_days: int | None = None) -> int:
    """`keep_days` drops items published (or, undated, fetched) more than that many days ago: market news needs
    weeks, not years, and the file is committed daily."""
    root = root or DATA
    if df is None or df.empty:
        return 0
    df = _validate(df.copy(), TEXT_COLS)
    path = root / "text" / f"{source}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    df = (df.sort_values("fetched_at")
            .drop_duplicates(["item_id"], keep="first")      # keep first-seen fetch time
            .sort_values("published", ascending=False)
            .reset_index(drop=True))
    if keep_days:
        when = pd.to_datetime(df["published"], utc=True, errors="coerce").fillna(
            pd.to_datetime(df["fetched_at"], utc=True, errors="coerce"))
        df = df[when >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=keep_days)].reset_index(drop=True)
    df.to_parquet(path, index=False)
    return len(df)


def last_date(source: str, root: Path | None = None):
    root = root or DATA
    files = sorted((root / "obs" / source).glob("*.parquet"))
    if not files:
        return None
    s = pd.read_parquet(files[-1], columns=["date"])["date"]
    return pd.to_datetime(s).max().date() if len(s) else None


def connect(root: Path | None = None) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with views `obs` and `text` over the Parquet files."""
    root = root or DATA
    con = duckdb.connect()
    obs = list((root / "obs").glob("*/*.parquet"))
    txt = list((root / "text").glob("*.parquet"))
    if obs:
        con.execute(f"CREATE VIEW obs AS SELECT * FROM read_parquet('{(root / 'obs').as_posix()}/*/*.parquet', union_by_name=true)")
    else:
        con.execute("CREATE TABLE obs (source VARCHAR, series_id VARCHAR, name VARCHAR, date DATE, value DOUBLE, unit VARCHAR, freq VARCHAR, source_url VARCHAR, fetched_at TIMESTAMP)")
    if txt:
        con.execute(f"CREATE VIEW text AS SELECT * FROM read_parquet('{(root / 'text').as_posix()}/*.parquet', union_by_name=true)")
    else:
        con.execute("CREATE TABLE text (source VARCHAR, item_id VARCHAR, title VARCHAR, url VARCHAR, published TIMESTAMP, summary VARCHAR, fetched_at TIMESTAMP)")
    return con
