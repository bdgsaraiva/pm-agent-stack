"""Shared test settings: no real pauses between (fake) API calls."""
import os

os.environ.setdefault("PMSTACK_NO_PAUSE", "1")
os.environ.setdefault("PMSTACK_NO_SOURCES_D", "1")   # agent sources in config/sources.d are tested with their own fakes

import pytest  # noqa: E402

# The narrative machinery tests were written with Hormuz / Iran as their worked example (fake GDELT data spreads it,
# ideas on Brent are placed against it). It left the live map on 20 Oct 2026 (Bernardo: redesigned into "Oil and
# product supply" and "Geopolitical risk"); offline tests keep it active so they test the machinery, not the map.
TEST_ACTIVE = {"hormuz_iran_v1", "ai_trade_v1", "ai_trade_v2g"}   # ai_trade: the burst tests' example (retired 20 Oct evening)


@pytest.fixture(autouse=True)
def _pin_worked_example_narratives(monkeypatch):
    from pmstack import srcconfig
    real = srcconfig.shared

    def shared():
        src = real()
        for blk in src.values():
            for q in (blk.get("queries") or []) if isinstance(blk, dict) else []:
                if q.get("id") in TEST_ACTIVE:
                    q.pop("retired", None)
        return src
    monkeypatch.setattr(srcconfig, "shared", shared)
