"""Central-bank and policy text from RSS feeds (and the BCB Copom JSON feed)."""
from __future__ import annotations

import hashlib
import re

import feedparser
import pandas as pd

from . import base

KIND = "text"


def _clean(s: str | None, n: int = 600) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()[:n]


def _rss(feed: dict) -> list[dict]:
    parsed = feedparser.parse(base.get_text(feed["url"]))
    out = []
    for e in parsed.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        out.append({
            "title": _clean(e.get("title"), 300),
            "url": e.get("link"),
            "published": pd.Timestamp(*t[:6], tz="UTC") if t else pd.NaT,
            "summary": _clean(e.get("summary")),
        })
    return out


def _bcb_json(feed: dict) -> list[dict]:
    js = base.get_json(feed["url"])
    items = js.get("conteudo", js if isinstance(js, list) else [])
    out = []
    for it in items:
        url = it.get("link") or it.get("url") or "https://www.bcb.gov.br/publicacoes/comunicadoscopom"
        if url.startswith("/"):
            url = "https://www.bcb.gov.br" + url
        out.append({
            "title": _clean(it.get("titulo") or it.get("title"), 300),
            "url": url,
            "published": pd.to_datetime(it.get("dataReferencia") or it.get("data") or it.get("dataPublicacao"), utc=True, errors="coerce"),
            "summary": _clean(it.get("textoComunicado") or it.get("resumo") or ""),
        })
    return out


def _strip_suffix(title: str, outlet: str | None) -> str:
    """Google News titles end in " - <Outlet>"; the outlet has its own field."""
    if outlet and title.endswith(f" - {outlet}"):
        return title[: -len(outlet) - 3].rstrip()
    return re.sub(r"\s+-\s+[A-Z][\w.&' ]{1,30}$", "", title) if " - " in title else title


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    """Each feed's items. Market news (`news` source) keeps headlines only: `keep_summary: false` drops the summary,
    `strip_suffix` removes Google News's " - Outlet" tail; the outlet name comes from the feed id (pmstack/news.py)."""
    fetched = base.now_utc()
    rows, errors = [], []
    for feed in cfg["feeds"]:
        try:
            items = _bcb_json(feed) if feed.get("format") == "bcb_json" else _rss(feed)
        except Exception as e:
            errors.append(f"{feed['id']}: {e}")
            continue
        for it in items:
            if cfg.get("keep_summary") is False:
                it["summary"] = ""
            if cfg.get("strip_suffix"):
                it["title"] = _strip_suffix(it["title"], feed.get("outlet"))
            key = f"{feed['id']}|{it['url']}|{it['title']}"
            rows.append({"source": feed["id"], "item_id": hashlib.sha1(key.encode()).hexdigest()[:16],
                         **it, "fetched_at": fetched})
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors
    return out
