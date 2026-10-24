"""Derived source: the spreads in config/spreads.yaml and the journal's rv:<idea> marks, computed from legs already
in the research memory (no network). Runs last in the data job (config/sources.d/spreads.yaml). See pmstack/spreads.py."""
from __future__ import annotations

import pandas as pd

KIND = "obs"


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    from .. import spreads
    df, notes = spreads.frames()
    df.attrs["errors"] = [n for n in notes if "not priced" in n or "no prices" in n]
    df.attrs["notes"] = notes
    return df
