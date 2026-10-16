"""Shared HTTP helpers and the adapter contract.

Adapter contract (every adapter module exposes):
    KIND = "obs" | "text"
    def fetch(cfg: dict, since: date | None) -> pandas.DataFrame
returning store.OBS_COLS or store.TEXT_COLS. Swap a free source for a vendor by
writing a module with the same contract and pointing config/sources.yaml at it.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

from ..runlog import redact

UA = "pm-agent-stack/0.1 (personal research; contact via GitHub repo owner)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "*/*"})


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def get(url: str, params: dict | None = None, headers: dict | None = None,
        tries: int = 3, timeout: int = 30) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
            last = RuntimeError(redact(f"HTTP {r.status_code} for {r.url}: {r.text[:200]}"))   # no key in errors
            if r.status_code in (400, 401, 403, 404):
                break
        except requests.RequestException as e:   # network blips (their text quotes the URL, key included)
            last = RuntimeError(redact(f"{type(e).__name__}: {e}"))
        time.sleep(2 * (i + 1))
    raise last  # type: ignore[misc]


def get_json(url: str, **kw):
    return get(url, **kw).json()


def get_text(url: str, **kw) -> str:
    return get(url, **kw).text
