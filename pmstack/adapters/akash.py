"""Akash Network GPU marketplace (public console API, no key): a small decentralised GPU market, a few hundred GPUs.

  akash:util           GPU utilisation of the network, % (daily history since Feb 2024, `graph-data/gpuUtilization`)
  akash:<model>        median listed price for the model, USD per GPU-hour (`gpu-prices`; a snapshot, dated the UTC day
                       of the fetch: history builds from our own daily fetches)
  akash:<model>:avail  GPUs of that model available / total, % (same snapshot)
  akash:gpus           GPUs on the network (same snapshot)

A thin market (a handful of providers per model): read it as colour beside GetDeploying, never alone.
"""
from __future__ import annotations

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
API = "https://console-api.akash.network/v1"
PAGE = "https://console.akash.network/gpu-prices"


def snapshot(js: dict, cfg: dict, day, fetched) -> list[dict]:
    out = []
    tot = (js.get("availability") or {}).get("total")
    if tot is not None:
        out.append(ac.row("akash", "akash:gpus", "Akash GPUs on the network", day, tot, "GPUs", "daily", PAGE, fetched))
    want = {m["model"]: m for m in cfg.get("models", [])}
    by: dict[str, dict] = {}
    for m in js.get("models") or []:
        key = str(m.get("model", "")).lower()
        if key not in want:
            continue
        a = m.get("availability") or {}
        prev = by.get(key)                       # several RAM/interface variants: keep the one with most GPUs
        if prev is None or (a.get("total") or 0) > ((prev.get("availability") or {}).get("total") or 0):
            by[key] = m
    for key, m in by.items():
        name, p, a = want[key]["name"], m.get("price") or {}, m.get("availability") or {}
        if p.get("med") is not None:
            out.append(ac.row("akash", f"akash:{key}", f"{name} median price on Akash", day, p["med"], "USD/GPU-hr",
                              "daily", PAGE, fetched))
        if a.get("total"):
            out.append(ac.row("akash", f"akash:{key}:avail", f"{name} available on Akash", day,
                              100.0 * a.get("available", 0) / a["total"], "%", "daily", PAGE, fetched))
    return out


def utilisation(js: dict, fetched, since=None) -> list[dict]:
    out = []
    for s in js.get("snapshots") or []:
        d = pd.Timestamp(s["date"]).date()
        if since is None or d >= since:
            out.append(ac.row("akash", "akash:util", "Akash GPU utilisation", d, s["value"], "%", "daily", PAGE, fetched))
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched, rows, errors = base.now_utc(), [], []
    try:
        rows += snapshot(ac.get(f"{API}/gpu-prices", cfg).json(), cfg, fetched.date(), fetched)
    except Exception as e:  # noqa: BLE001
        errors.append(f"gpu-prices: {type(e).__name__}: {e}")
    try:
        rows += utilisation(ac.get(f"{API}/graph-data/gpuUtilization", cfg).json(), fetched, since)
    except Exception as e:  # noqa: BLE001
        errors.append(f"gpuUtilization: {type(e).__name__}: {e}")
    if not rows and errors:
        raise RuntimeError("; ".join(errors))
    return ac.frame(rows, errors)
