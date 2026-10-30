"""Adapter registry. config/sources.yaml names an adapter per source block."""
from importlib import import_module

AVAILABLE = {"eia", "cftc", "fred", "bcb", "yahoo", "rss", "gdelt", "gdelt_bq", "gdelt_disc", "wasde", "usda_psd", "nass", "mof_jgb", "agenda",
             "getdeploying", "akash", "dramexchange", "openrouter", "ramp", "census_c30", "tsmc", "kcs",   # AI demand signals
             "westmetall", "spread",   # relative-value legs and spreads (24 Oct 2026)
             "yahoo_curve", "jodi", "anp", "steo",   # energy specialist S1 (24 Oct 2026): curves, JODI, ANP, STEO vintages
             "shfe", "pinksheet",   # metals specialist S3 (25 Oct 2026): SHFE weekly stocks, World Bank Pink Sheet
             "esmis", "conab", "fas_esr", "noaa_oni", "usdm"}   # ags specialist S4 (30 Oct 2026)


def load(name: str):
    if name not in AVAILABLE:
        raise KeyError(f"unknown adapter '{name}'; add a module under pmstack/adapters and list it here")
    return import_module(f"pmstack.adapters.{name}")
