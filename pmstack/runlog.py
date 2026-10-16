"""Audit trail: one JSON line per run step in logs/runs.jsonl (Step 2 pattern)."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "runs.jsonl"


# API keys travel as query parameters (EIA api_key, NASS key): an error message that quotes the request URL must
# never carry one into the committed log (16 Oct 2026: a failed EIA call printed the key into a probe log).
SECRET_RE = re.compile(r"(?i)([?&](?:api_key|apikey|key|token|access_token|api-key)=)[^&\s\"']+")


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1REDACTED", text)


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def log(run_id: str, step: str, status: str, **fields) -> dict:
    rec = {
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "step": step,
        "status": status,
        **fields,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(redact(json.dumps(rec, default=str, ensure_ascii=False)) + "\n")
    return rec


def read(last_n: int = 200) -> list[dict]:
    if not LOG.exists():
        return []
    lines = LOG.read_text(encoding="utf-8").splitlines()[-last_n:]
    return [json.loads(x) for x in lines if x.strip()]
