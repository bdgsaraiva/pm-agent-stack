"""The shared source config (config/sources.yaml), read in one place. Every module that needs the frozen narrative
definitions or the source blocks calls `srcconfig.shared()` (as a module attribute), so offline tests can pin the
worked-example narratives they were written against even after the live map retires them (tests/conftest.py)."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def shared() -> dict:
    return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8")) or {}
