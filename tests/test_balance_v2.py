"""Agent 9 v2 items (20 Oct 2026): per-series seasonality check and the FAS Data API address (offline)."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from pmstack import balance
from pmstack.adapters import usda_psd

CS = {"years": 10, "min_years": 6, "min_share": 0.10, "min_stability": 0.60}


def _weekly(pattern, noise: float, seed: int = 3, start="2016-01-08", end="2026-10-09") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = pd.date_range(start, end, freq="W-FRI")
    chg = np.array([pattern(x.month) for x in d]) + rng.normal(0, noise, len(d))
    return pd.DataFrame({"date": d.date, "value": 400 + np.cumsum(chg), "unit": "kbbl",
                         "source_url": "https://www.eia.gov/"})


def test_seasonal_series_is_not_flagged_and_noise_is():
    strong = balance.seasonality(_weekly(lambda m: 4.0 if m in (1, 2, 3) else -2.0 if m in (7, 8, 9) else 0.0, 1.0), CS)
    assert strong["share"] > 0.3 and strong["stability"] > 0.9 and strong["weak"] is False
    noise = balance.seasonality(_weekly(lambda m: 0.0, 3.0), CS)
    assert noise["weak"] is True


def test_seasonality_uses_only_data_up_to_the_series_end():
    s = _weekly(lambda m: 4.0 if m in (1, 2, 3) else -2.0, 1.0)
    cut = s[pd.to_datetime(s["date"]) <= pd.Timestamp("2024-06-30")]
    se = balance.seasonality(cut, CS)
    assert se["window"].endswith(str(cut["date"].iloc[-1])[:10])


def test_weak_seasonality_adds_52w_mean_and_suppresses_range_alert():
    s = _weekly(lambda m: 0.0, 3.0)
    s.loc[s.index[-1], "value"] = float(s["value"].min()) - 50          # far below any same-week range
    c = {"id": "X", "label": "Test", "markets": [], "alert": True}
    row = balance.stock_row(s, c, 5, 4, CS)
    assert row["beyond"] == "below" and row["seasonality"]["weak"] and row["vs_avg52w_pct"] < 0
    cfg = balance.cfg()
    sec = {"oil": {"stocks": [row]}, "grains": [], "condition": [], "stocks_quarterly": []}
    cfg = {**cfg, "oil": {**cfg["oil"], "stocks": [c]}}
    asof = date.fromisoformat(row["week_ending"]) + timedelta(days=2)
    assert not [a for a in balance.alerts(sec, asof, cfg) if a["kind"] == "balance_range"]
    text = "\n".join(balance.render({"oil": {"stocks": [row]}}))
    assert "weak or unstable seasonality" in text and "No range alert" in text


def test_fas_data_api_address_and_header():
    assert usda_psd.API.startswith("https://api.fas.usda.gov/api/psd")
    assert usda_psd.AUTH["how"] == "x-api-key"
