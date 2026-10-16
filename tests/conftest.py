"""Shared test settings: no real pauses between (fake) API calls."""
import os

os.environ.setdefault("PMSTACK_NO_PAUSE", "1")
os.environ.setdefault("PMSTACK_NO_SOURCES_D", "1")   # agent sources in config/sources.d are tested with their own fakes
