"""GetDeploying GPU rental price history: weekly on-demand medians per GPU model across ~90 cloud providers.

Free, no key, CC BY 4.0 ("GetDeploying GPU price dataset", https://getdeploying.com/dataset/gpu-prices). One CSV,
53 trailing weeks per model, updated daily; the latest week may be partial and can change (latest fetch wins).
A model's price is each provider's own median first, then the median across providers (`provider_median_price`, the
figure GetDeploying headlines); models priced by fewer than `min_providers` providers that week are dropped.

  gd:<gpu_slug>        USD per GPU-hour, on demand, dated at the week start (Monday)
  gd:<gpu_slug>:n      providers pricing it that week (coverage; a median can move when listings change)
"""
from __future__ import annotations

import io

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
CSV = "https://getdeploying.com/dataset/gpu-prices/weekly.csv"
PAGE = "https://getdeploying.com/gpu-price-trends"


def records(csv_text: str, cfg: dict, fetched) -> list[dict]:
    d = pd.read_csv(io.StringIO(csv_text))
    d = d[d["billing_type"] == cfg.get("billing_type", "ON_DEMAND")]
    names = {m["slug"]: m["name"] for m in cfg["models"]}
    d = d[d["gpu_slug"].isin(names) & (d["provider_count"] >= int(cfg.get("min_providers", 4)))]
    out = []
    for r in d.itertuples():
        out.append(ac.row("getdeploying", f"gd:{r.gpu_slug}", f"{names[r.gpu_slug]} rental, on demand (median of providers)",
                          r.date, r.provider_median_price, "USD/GPU-hr", "weekly", PAGE, fetched))
        out.append(ac.row("getdeploying", f"gd:{r.gpu_slug}:n", f"{names[r.gpu_slug]} providers priced",
                          r.date, r.provider_count, "providers", "weekly", PAGE, fetched))
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    text = ac.get(cfg.get("url", CSV), cfg).text
    rows = records(text, cfg, fetched)
    if since is not None:
        rows = [r for r in rows if r["date"] >= since]
    return ac.frame(rows, [])
