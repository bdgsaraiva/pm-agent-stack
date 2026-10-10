"""Shared test settings: no real pauses between (fake) API calls."""
import os

os.environ.setdefault("PMSTACK_NO_PAUSE", "1")
