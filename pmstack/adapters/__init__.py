"""Adapter registry. config/sources.yaml names an adapter per source block."""
from importlib import import_module

AVAILABLE = {"eia", "cftc", "fred", "bcb", "yahoo", "rss"}


def load(name: str):
    if name not in AVAILABLE:
        raise KeyError(f"unknown adapter '{name}'; add a module under pmstack/adapters and list it here")
    return import_module(f"pmstack.adapters.{name}")
