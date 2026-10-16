"""Network and reputation (agent 11): post-call debriefs, follow-ups, reconnects, a monthly network page and
the monthly public commodity note with its scored calls.

Why this shape (docs/research/network.md):
  - The adopted pattern is the post-call debrief (Morgan Stanley Debrief): structured note, dated follow-ups,
    contact update, drafted recap. The agent drafts; Bernardo sends (Millennium twins: never decide or send).
  - Every promise becomes a dated if-then task naming the item (Gollwitzer & Sheeran d = 0.65; Karlan et al.).
  - New ties decay fastest (~43% of active ties gone in four weeks: Raeder et al.), so a second touch is due
    14-28 days after a first call; dormant ties (Levin, Walter & Murnighan) are reconnected on purpose, ranked
    by novelty x engagement with one random pick (people choose by comfort; value doesn't fall down the list).
  - Bridging beats redundancy for ideas (Burt 2004); bandwidth matters when information refreshes fast
    (Aral & Van Alstyne), so the page shows bridging share and concentration, never a contact count.
  - Network "alpha" from issuer ties was mostly selective disclosure (Cohen, Frazzini & Malloy 2010) and the
    big wins in the record are insider cases (SEC 2012-237): every call note carries an MNPI attestation and a
    note that records MNPI is refused (CVM Res. 44 art. 13 reaches anyone with access).
  - Public writing pays in attention when it is regular and consistent with results (Kaniel & Parham;
    Hillert et al.): numbered, dated posts with a scored record of past calls and "what I got wrong".

Privacy: contacts and call notes live in a separate private repo (config `home`, env PM_NETWORK_HOME).
Only contacts.yaml holds names; call notes refer to opaque ids (c0001); call ids are dates (2026-10-15-01).
Nothing with a name is written to this repo or the run log.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from . import runlog

ROOT = Path(__file__).resolve().parents[1]
MEDIUMS = ("in-person", "video", "phone", "message", "email", "conference")
ATTEST_OK = "none received"


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "network.yaml").read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _today() -> str:
    return (_now() - timedelta(hours=3)).date().isoformat()


def _d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


def home() -> Path:
    env = os.environ.get("PM_NETWORK_HOME")
    h = (Path(env) if env else ROOT / cfg()["home"]).resolve()
    _outside_repo(h)
    return h


def _outside_repo(h: Path):
    """Contacts must never live inside pm-agent-stack, or they would be committed with it (review A11, finding 16).
    Tests may point PM_NETWORK_HOME at a temp folder; the repo's own .projtmp/ is allowed for demos (gitignored)."""
    try:
        rel = Path(h).resolve().relative_to(ROOT.resolve())
    except ValueError:
        return
    if rel.parts[:1] != (".projtmp",):
        raise SystemExit(f"network home {h} is inside pm-agent-stack: use a separate private repo (e.g. ../pm-network)")


def _require_home() -> Path:
    h = home()
    if not (h / "contacts.yaml").exists():
        raise SystemExit(f"no network repo at {h}: run `python -m pmstack network init` (or set PM_NETWORK_HOME)")
    return h


# ------------------------------------------------------------------ the private repo
README = """# pm-network (private)

Bernardo's contacts and call notes for agent 11 of pm-agent-stack. **Private repo on the personal GitHub
account only; never an employer org; 2FA on.** Code lives in pm-agent-stack (`python -m pmstack network ...`).

Rules (docs/research/network.md in pm-agent-stack):
- Minimal fields: name, role, firm, cluster, value-chain role, region, layer, tie, trust, how met, plan.
  Never health, politics, religion, family, addresses, phone numbers or other personal-life details (LGPD art. 5 II).
- Legal basis: legitimate interest (LGPD art. 7 IX; GDPR for EU contacts). A contact who asks to be removed:
  `python -m pmstack network forget <id>`, then rewrite history (`git filter-repo`) and force-push.
- Every call note ends with the MNPI attestation. If material non-public information was received: stop,
  do not record it, do not trade on it, tell compliance (CVM Res. 44 art. 13; SEC 2022 risk alert).
- Nothing public ever attributes a view to a named contact or firm.
- Check the fund's code of ethics covers keeping personal notes of industry contacts.
"""


def init(path: Path | None = None, git: bool = True) -> Path:
    h = Path(path).resolve() if path else home()
    _outside_repo(h)
    (h / "calls").mkdir(parents=True, exist_ok=True)
    (h / "monthly").mkdir(exist_ok=True)
    if not (h / "contacts.yaml").exists():
        (h / "contacts.yaml").write_text("# One entry per contact. Only this file holds names.\ncontacts: []\n", encoding="utf-8")
    if not (h / "README.md").exists():
        (h / "README.md").write_text(README, encoding="utf-8")
    if not (h / ".gitignore").exists():   # call drafts are written here, saved by `call new`, then deleted
        (h / ".gitignore").write_text(".draft-*.json\n", encoding="utf-8")
    if git and not (h / ".git").exists():
        try:
            subprocess.run(["git", "init", "-q", str(h)], check=True)
        except Exception as e:  # git missing is not fatal: the files still work
            print(f"git init skipped: {e}", file=sys.stderr)
    return h


# ------------------------------------------------------------------ contacts
CONTACT_FIELDS = ("id", "name", "role", "firm", "cluster", "chain_role", "region", "layer", "tie", "trust", "how_met",
                  "introduced_by", "alumni", "plan", "mnpi_risk", "markets", "topics", "first_contact", "status")


def _contacts_file(h: Path) -> dict:
    return yaml.safe_load((h / "contacts.yaml").read_text(encoding="utf-8")) or {}


def load_contacts(h: Path | None = None) -> list[dict]:
    h = h or _require_home()
    return _contacts_file(h).get("contacts") or []


def save_contacts(contacts: list[dict], h: Path | None = None, last_id: int | None = None):
    h = h or _require_home()
    prev = _contacts_file(h).get("last_id") or 0
    used = max([int(x["id"][1:]) for x in contacts if re.fullmatch(r"c\d+", str(x.get("id")))] or [0])
    head = "# One entry per contact. Only this file holds names. last_id: ids are never reused.\n"
    body = yaml.safe_dump({"last_id": max(prev, used, last_id or 0), "contacts": contacts}, sort_keys=False,
                          allow_unicode=True, width=110)
    (h / "contacts.yaml").write_text(head + body, encoding="utf-8")


def _key_words(k) -> set[str]:
    k = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(k))
    words = [w for w in re.split(r"[\s_\-.]+", k.lower()) if w]
    return set(words) | {"_".join(words)}


def _forbidden(d, path: str = "") -> list[str]:
    """Forbidden keys anywhere in a record, nested too: 'phoneNumber', 'personal.spouse' (review A11, finding 16)."""
    bad = set(cfg()["forbidden_fields"])
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            if str(k).startswith("_"):
                continue
            here = f"{path}.{k}" if path else str(k)
            if _key_words(k) & bad:
                out.append(here)
            out += _forbidden(v, here)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out += _forbidden(v, f"{path}[{i}]")
    return out


def validate_contact(c: dict, contacts: list[dict] | None = None) -> list[str]:
    k = cfg()
    out = []
    for f in ("name", "role", "firm", "cluster"):
        if not c.get(f):
            out.append(f"{f} is required")
    for f, allowed in (("cluster", k["clusters"]), ("chain_role", k["chain_roles"]), ("region", k["regions"]),
                       ("mnpi_risk", k["mnpi_risk"]), ("plan", k["plans"])):
        if c.get(f) is not None and c.get(f) not in allowed:
            out.append(f"{f} '{c.get(f)}' not in {allowed}")
    def _int(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return None
    if c.get("layer") is not None and _int(c["layer"]) not in k["layers"]:
        out.append(f"layer must be one of {list(k['layers'])}")
    for f in ("tie", "trust"):
        if c.get(f) is not None and not 1 <= (_int(c[f]) or 0) <= 5:
            out.append(f"{f} must be a whole number 1-5")
    fb = _forbidden(c)
    if fb:
        out.append(f"fields never stored (LGPD sensitive or personal life): {fb}")
    extra = [f for f in c if f not in CONTACT_FIELDS]
    if extra and not fb:
        out.append(f"unknown fields {extra}: keep the record minimal")
    if contacts and c.get("introduced_by") and c["introduced_by"] not in {x["id"] for x in contacts}:
        out.append(f"introduced_by {c['introduced_by']} is not a contact id")
    return out


def add_contact(fields: dict, h: Path | None = None) -> tuple[dict | None, list[str]]:
    h = h or _require_home()
    contacts = load_contacts(h)
    c = {f: fields[f] for f in CONTACT_FIELDS if fields.get(f) not in (None, "", [])}
    c.update({k: v for k, v in fields.items() if k not in CONTACT_FIELDS})   # unknown keys are caught by validation
    c.setdefault("layer", 150)
    c.setdefault("mnpi_risk", "none")
    c.setdefault("first_contact", _today())
    c.setdefault("status", "active")
    n = max([int(x["id"][1:]) for x in contacts if re.fullmatch(r"c\d+", str(x.get("id")))]
            + [_contacts_file(h).get("last_id") or 0] or [0]) + 1
    c["id"] = f"c{n:04d}"
    errs = validate_contact(c, contacts)
    if errs:
        return None, errs
    c = {f: c[f] for f in CONTACT_FIELDS if f in c}
    contacts.append(c)
    save_contacts(contacts, h)
    runlog.log(runlog.new_run_id(), "network:contact", "ok", action="add", contact=c["id"], cluster=c["cluster"])
    return c, []


def update_contact(cid: str, fields: dict, h: Path | None = None) -> tuple[dict | None, list[str]]:
    h = h or _require_home()
    contacts = load_contacts(h)
    c = next((x for x in contacts if x["id"] == cid), None)
    if not c:
        return None, [f"no contact {cid}"]
    new = {**c, **{k: v for k, v in fields.items() if v is not None}}
    errs = validate_contact(new, contacts)
    if errs:
        return None, errs
    c.clear()
    c.update({f: new[f] for f in CONTACT_FIELDS if f in new})
    save_contacts(contacts, h)
    runlog.log(runlog.new_run_id(), "network:contact", "ok", action="update", contact=cid)
    return c, []


# ------------------------------------------------------------------ call notes
def _read_md(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        raise ValueError(f"{path}: no YAML header")
    meta = yaml.safe_load(m.group(1)) or {}
    meta["_body"], meta["_path"] = m.group(2), path
    return meta


def _write_md(path: Path, meta: dict):
    body = meta.get("_body", "")
    clean = {k: v for k, v in meta.items() if not k.startswith("_")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(clean, sort_keys=False, allow_unicode=True, width=110) + "---\n" + body,
                    encoding="utf-8")


def load_calls(h: Path | None = None, until: str | None = None) -> list[dict]:
    h = h or _require_home()
    out = []
    for p in sorted((h / "calls").glob("*/*.md")):
        try:
            m = _read_md(p)
        except Exception as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        if until and str(m.get("date")) > until:
            continue
        out.append(m)
    return sorted(out, key=lambda m: (str(m.get("date")), str(m.get("id"))))


def validate_call(meta: dict, contacts: list[dict]) -> tuple[list[str], list[str]]:
    """(blocking problems, warnings). A call note that records MNPI, or has no attestation, is not saved."""
    block, warn = [], []
    att = re.sub(r"[^a-z ]", " ", str(meta.get("mnpi_attestation") or "").lower())
    att = re.sub(r"\s+", " ", att).strip()
    if att in ("none received", "not received", "none", "no mnpi received", "no mnpi"):
        meta["mnpi_attestation"] = ATTEST_OK
    elif "receiv" in att and not re.search(r"\b(none|not|no)\b", att):
        block.append("MNPI received: do not record it, do not trade on it, tell compliance (CVM Res. 44 art. 13). "
                     "Save the note again with only the public part and mnpi_attestation: 'none received'.")
    else:
        block.append(f"mnpi_attestation is required and must read '{ATTEST_OK}' (got '{meta.get('mnpi_attestation')}')")
    try:
        _d(meta.get("date"))
    except Exception:
        block.append("date must be YYYY-MM-DD")
    ids = {c["id"] for c in contacts}
    w = meta.get("with") or []
    if not w:
        block.append("with: at least one contact id")
    for cid in w:
        if cid not in ids:
            block.append(f"{cid} is not a contact id (add the contact first)")
    if meta.get("initiator") not in ("me", "them"):
        block.append("initiator must be me or them")
    if meta.get("medium") not in MEDIUMS:
        block.append(f"medium must be one of {MEDIUMS}")
    for i, f in enumerate(meta.get("follow_ups") or [], 1):
        if not f.get("what"):
            block.append(f"follow-up {i}: name the item (what)")
        if f.get("owner") not in ("me", "them"):
            block.append(f"follow-up {i}: owner must be me or them")
        try:
            if _d(f.get("due")) < _d(meta.get("date")):
                block.append(f"follow-up {i}: due before the call")
        except Exception:
            block.append(f"follow-up {i}: due must be YYYY-MM-DD")
    fb = _forbidden(meta)
    if fb:
        block.append(f"fields never stored: {fb}")
    names = [c["name"] for c in contacts if c.get("name")]
    body = str(meta.get("_body") or "")
    named = [n for n in names if n.lower() in body.lower()]
    if named:
        warn.append("contact names in the body: refer to people by id (c0001) so only contacts.yaml holds names")
    return block, warn


def new_call(meta: dict, body: str = "", h: Path | None = None) -> tuple[dict | None, list[str], list[str]]:
    """Save a call note: id = date-NN; follow-ups get ids and default due dates; nothing saved on a blocking problem."""
    h = h or _require_home()
    k = cfg()
    contacts = load_contacts(h)
    m = dict(meta)
    m["_body"] = body
    m.setdefault("date", _today())
    m["date"] = str(m["date"])[:10]
    fus = []
    for i, f in enumerate(m.get("follow_ups") or [], 1):
        f = dict(f)
        f.setdefault("owner", "me")
        f.setdefault("due", (_d(m["date"]) + timedelta(days=k["followup_default_days"])).isoformat())
        f["due"] = str(f["due"])[:10]
        f.setdefault("status", "open")
        f["id"] = f"f{i}"
        fus.append(f)
    m["follow_ups"] = fus
    block, warn = validate_call(m, contacts)
    if block:
        return None, block, warn
    day = m["date"]
    folder = h / "calls" / day[:4]
    n = 1 + max([int(p.stem.rsplit("-", 1)[1]) for p in folder.glob(f"{day}-*.md")] or [0])
    m["id"] = f"{day}-{n:02d}"
    order = ["id", "date", "with", "initiator", "medium", "topics", "public_sources", "drew_attention",
             "my_view_vs_room", "questions_asked", "gives", "asks", "follow_ups", "mnpi_attestation"]
    out = {key: m[key] for key in order if key in m}
    out.update({key: v for key, v in m.items() if key not in out})
    _write_md(folder / f"{m['id']}.md", out)
    runlog.log(runlog.new_run_id(), "network:call", "ok", call=m["id"], contacts=len(m["with"]),
               follow_ups=len(fus), warnings=len(warn))
    return out, [], warn


def close_followup(call_id: str, fu_id: str, done: str | None = None, h: Path | None = None) -> dict:
    h = h or _require_home()
    p = h / "calls" / call_id[:4] / f"{call_id}.md"
    if not p.exists():
        raise SystemExit(f"no call {call_id}")
    m = _read_md(p)
    f = next((x for x in m.get("follow_ups") or [] if x.get("id") == fu_id), None)
    if not f:
        raise SystemExit(f"no follow-up {fu_id} on {call_id}")
    f["status"], f["done"] = "done", (done or _today())
    _write_md(p, m)
    runlog.log(runlog.new_run_id(), "network:followup", "ok", call=call_id, follow_up=fu_id,
               on_time=_d(f["done"]) <= _d(f["due"]))
    return f


# ------------------------------------------------------------------ derived views
def history(contacts: list[dict], calls: list[dict], asof: str) -> dict[str, dict]:
    """Per contact, from call notes up to `asof`: dates, last contact, who initiated, gives and asks."""
    out = {c["id"]: {"dates": [], "them": 0, "gives": 0, "asks": 0} for c in contacts}
    for m in calls:
        if str(m["date"]) > asof:
            continue
        for cid in m.get("with") or []:
            if cid in out:
                h = out[cid]
                h["dates"].append(str(m["date"]))
                h["them"] += m.get("initiator") == "them"
                h["gives"] += len(m.get("gives") or [])
                h["asks"] += len(m.get("asks") or [])
    for c in contacts:
        h = out[c["id"]]
        h["n"] = len(h["dates"])
        h["last"] = max(h["dates"]) if h["dates"] else None
        h["first_logged"] = min(h["dates"]) if h["dates"] else None
        base = h["last"] or str(c.get("first_contact") or asof)
        h["days_since"] = (_d(asof) - _d(base)).days
    return out


def _open_on(f: dict, day: date) -> bool:
    """Was this follow-up still open on `day`? (closed later = open then: review A11, finding 8)"""
    return f.get("status") != "done" or not f.get("done") or _d(f["done"]) > day


def due(asof: str | None = None, h: Path | None = None) -> dict:
    """Open follow-ups (overdue and due within 7 days), cadence gaps by layer, second touches for new ties."""
    asof = asof or _today()
    h = h or _require_home()
    k = cfg()
    contacts, calls = load_contacts(h), load_calls(h, asof)
    hist = history(contacts, calls, asof)
    d0 = _d(asof)
    fus = []
    for m in calls:
        for f in m.get("follow_ups") or []:
            if _open_on(f, d0) and _d(f["due"]) <= d0 + timedelta(days=7):
                fus.append({"call": m["id"], "follow_up": f["id"], "owner": f.get("owner"), "what": f.get("what"),
                            "with": m.get("with"), "due": f["due"], "overdue_days": max(0, (d0 - _d(f["due"])).days)})
    gaps, second = [], []
    for c in contacts:
        if c.get("status") == "inactive":
            continue
        hc = hist[c["id"]]
        cad = k["layers"].get(int(c.get("layer") or 150))
        if hc["n"] and cad and hc["days_since"] > cad:
            gaps.append({"id": c["id"], "layer": c.get("layer"), "days_since": hc["days_since"], "cadence_days": cad})
        lo, hi = k["second_touch_days"]
        # a second touch is for a new tie, not for a reconnected old one (review A11, finding 9)
        new_tie = not c.get("first_contact") or (_d(hc["first_logged"]) - _d(c["first_contact"])).days <= hi
        if hc["n"] == 1 and hc["days_since"] >= lo and new_tie:
            second.append({"id": c["id"], "first_call": hc["first_logged"], "days_since": hc["days_since"],
                           "late": hc["days_since"] > hi})
    return {"asof": asof, "follow_ups": sorted(fus, key=lambda x: x["due"]),
            "cadence_gaps": sorted(gaps, key=lambda x: -x["days_since"] / x["cadence_days"]),
            "second_touch": second}


def reconnect(asof: str | None = None, seed: str | None = None, h: Path | None = None) -> dict:
    """Dormant contacts to reconnect this week: ranked by novelty (outside the home clusters, outer layers,
    brief acquaintance) x engagement (trust, past reciprocity), plus one random pick from the shortlist.
    Random seed = ISO week, so the same week gives the same list."""
    asof = asof or _today()
    h = h or _require_home()
    k = cfg()
    contacts, calls = load_contacts(h), load_calls(h, asof)
    hist = history(contacts, calls, asof)
    cands = []
    for c in contacts:
        hc = hist[c["id"]]
        if c.get("status") == "inactive" or hc["days_since"] < k["dormant_days"]:
            continue
        novelty = 1.0 + (c.get("cluster") not in k["home_clusters"]) + (int(c.get("layer") or 150) >= 50) \
            + (int(c.get("tie") or 3) <= 2) * 0.5
        engagement = (int(c.get("trust") or 3) / 5) * (0.5 + (hc["them"] / hc["n"] if hc["n"] else 0.5))
        cands.append({"id": c["id"], "cluster": c.get("cluster"), "days_since": hc["days_since"],
                      "score": round(novelty * engagement, 3), "mnpi_risk": c.get("mnpi_risk")})
    cands.sort(key=lambda x: -x["score"])
    short = cands[: k["reconnect"]["shortlist"]]
    n = k["reconnect"]["per_week"]
    picks = [dict(x, why="ranked") for x in short[: max(0, n - 1)]]
    rest = [x for x in short if x["id"] not in {p["id"] for p in picks}]
    if rest:
        iso = _d(asof).isocalendar()
        rng = random.Random(seed or f"{iso[0]}-W{iso[1]}")
        picks.append(dict(rng.choice(rest), why="random pick from the shortlist (comfort bias)"))
    return {"asof": asof, "dormant": len(cands), "picks": picks}


def prep(cid: str, asof: str | None = None, h: Path | None = None) -> dict:
    """Meeting prep: the contact, the last calls, open follow-ups both ways, give/ask balance, and questions
    from digested notes on the contact's markets (agent 10)."""
    asof = asof or _today()
    h = h or _require_home()
    contacts = load_contacts(h)
    c = next((x for x in contacts if x["id"] == cid), None)
    if not c:
        raise SystemExit(f"no contact {cid}")
    calls = [m for m in load_calls(h, asof) if cid in (m.get("with") or [])]
    hc = history(contacts, load_calls(h, asof), asof)[cid]
    open_fu = [{"call": m["id"], **f} for m in calls for f in m.get("follow_ups") or [] if f.get("status") != "done"]
    out = {"contact": c, "calls": hc["n"], "last": hc["last"], "days_since": hc["days_since"],
           "initiated_by_them": hc["them"], "gives": hc["gives"], "asks": hc["asks"],
           "recent": [{"id": m["id"], "date": m["date"], "topics": m.get("topics"), "gives": m.get("gives"),
                       "asks": m.get("asks"), "questions_asked": m.get("questions_asked")} for m in calls[-3:]],
           "open_follow_ups": open_fu, "questions": [], "cards": []}
    if c.get("mnpi_risk") not in (None, "none"):
        out["warning"] = (f"mnpi_risk {c['mnpi_risk']}: discuss public information only; if anything material and "
                          "non-public comes up, stop, don't record it, tell compliance")
    mk = set(c.get("markets") or [])
    try:
        from . import digest
        for p in digest.NOTES.rglob("*.md"):
            try:
                m = digest.read_note(p)
            except SystemExit:
                continue
            if m.get("questions") and str(m.get("date")) <= asof and (not mk or mk & set(m.get("assets") or [])):
                out["questions"] += [{"q": q, "note": digest.note_key(p)} for q in m["questions"]]
        if mk:
            ks = [x for x in digest.load_cards(asof) if mk & set(x.get("markets") or [])]
            out["cards"] = [{"id": x["id"], "as_of": x["as_of"], "speaker": x.get("speaker"), "claim": x.get("claim"),
                             "direction": x.get("direction")} for x in sorted(ks, key=lambda x: x["as_of"])[-5:]]
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ monthly page
def _month_bounds(month: str) -> tuple[date, date]:
    y, m = map(int, month.split("-"))
    start = date(y, m, 1)
    end = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    return start, end


def metrics(month: str | None = None, h: Path | None = None) -> dict:
    """The month's network metrics (counts and shares only), with the targets beside them."""
    h = h or _require_home()
    k = cfg()
    month = month or _today()[:7]
    start, end = _month_bounds(month)
    if start > _d(_today()):
        raise SystemExit(f"{month} hasn't started yet")
    asof = min(end, _d(_today())).isoformat()
    contacts, calls = load_contacts(h), load_calls(h, asof)
    byid = {c["id"]: c for c in contacts}
    inm = [m for m in calls if start <= _d(m["date"]) <= end]
    days = (_d(asof) - start).days + 1
    out = {"month": month, "asof": asof, "calls": len(inm), "calls_per_week": round(len(inm) / (days / 7), 1)}
    # follow-ups due in the month: closed on time
    due_m = [f for m in calls for f in m.get("follow_ups") or [] if f.get("owner") == "me" and start <= _d(f["due"]) <= _d(asof)]
    on_time = [f for f in due_m if not _open_on(f, _d(asof)) and _d(f["done"]) <= _d(f["due"])]
    out["followups_due"] = len(due_m)
    out["followups_on_time_pct"] = round(100 * len(on_time) / len(due_m), 0) if due_m else None
    out["followups_overdue"] = sum(1 for m in calls for f in m.get("follow_ups") or []
                                   if f.get("owner") == "me" and _open_on(f, _d(asof)) and _d(f["due"]) < _d(asof))
    # bridging: calls with at least one contact outside the home clusters
    bridge = [m for m in inm if any(byid.get(c, {}).get("cluster") not in k["home_clusters"] for c in m.get("with") or [])]
    out["bridging_share_pct"] = round(100 * len(bridge) / len(inm), 0) if inm else None
    out["initiated_by_them_pct"] = round(100 * sum(m.get("initiator") == "them" for m in inm) / len(inm), 0) if inm else None
    gives = sum(len(m.get("gives") or []) for m in inm)
    asks = sum(len(m.get("asks") or []) for m in inm)
    out.update(gives=gives, asks=asks, give_ask=round(gives / asks, 2) if asks else None)
    # concentration over 90 days: share of conversations going to the top 5 and top 15 contacts
    lo = _d(asof) - timedelta(days=90)
    cnt: dict[str, int] = {}
    for m in calls:
        if _d(m["date"]) > lo:
            for c in m.get("with") or []:
                cnt[c] = cnt.get(c, 0) + 1
    tot = sum(cnt.values())
    srt = sorted(cnt.values(), reverse=True)
    out["top5_share_pct"] = round(100 * sum(srt[:5]) / tot, 0) if tot else None
    out["top15_share_pct"] = round(100 * sum(srt[:15]) / tot, 0) if tot else None
    out["concentration_warning"] = bool(tot and out["top15_share_pct"] >= k["inner_concentration_warn_pct"] and len(cnt) > 15)
    # ties: new (first logged this month), reconnected (gap >= dormant_days before this month's call), decayed (inner past 2x cadence)
    prev = history(contacts, [m for m in calls if _d(m["date"]) < start], (start - timedelta(days=1)).isoformat())
    new, recon = set(), set()
    for m in inm:
        for c in m.get("with") or []:
            ph = prev.get(c)
            if ph is None:
                continue
            fc = byid.get(c, {}).get("first_contact")
            last = ph["last"] or (str(fc) if fc else None)
            if ph["n"] == 0 and (not fc or _d(fc) >= start):
                new.add(c)
            elif last and (_d(m["date"]) - _d(last)).days >= k["dormant_days"]:
                recon.add(c)
    hist = history(contacts, calls, asof)
    decayed = [c["id"] for c in contacts if int(c.get("layer") or 150) in k["inner_layers"] and hist[c["id"]]["n"]
               and hist[c["id"]]["days_since"] > 2 * k["layers"][int(c["layer"])]]
    out.update(new_ties=len(new), reconnects=len(recon), decayed_inner=len(decayed))
    cad = {}
    for L, days_ in k["layers"].items():
        members = [c for c in contacts if int(c.get("layer") or 150) == L and c.get("status") != "inactive"]
        if members:
            ok = sum(1 for c in members if hist[c["id"]]["n"] and hist[c["id"]]["days_since"] <= days_)
            cad[str(L)] = {"contacts": len(members), "within_cadence": ok}
    out["cadence"] = cad
    out["contacts_by_cluster"] = {cl: sum(1 for c in contacts if c.get("cluster") == cl) for cl in k["clusters"]
                                  if any(c.get("cluster") == cl for c in contacts)}
    out["targets"] = k["targets"]
    out["purge_candidates"] = sum(1 for c in contacts if hist[c["id"]]["days_since"] > 365 * k["purge_idle_years"])
    return out


def monthly(month: str | None = None, write: bool = False, h: Path | None = None) -> dict:
    h = h or _require_home()
    mt = metrics(month, h)
    d = due(mt["asof"], h)
    rc = reconnect(mt["asof"], h=h)
    page = {"metrics": mt, "due": d, "reconnect": rc}
    if write:
        p = h / "monthly" / f"{mt['month']}.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(page, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        page["written"] = str(p)
    runlog.log(runlog.new_run_id(), "network:monthly", "ok", month=mt["month"], calls=mt["calls"],
               followups_on_time_pct=mt["followups_on_time_pct"], bridging_share_pct=mt["bridging_share_pct"],
               reconnects=mt["reconnects"], overdue=mt["followups_overdue"])
    return page


def compliance_log(start: str, end: str, h: Path | None = None) -> list[dict]:
    """What a compliance reviewer could ask for (SEC 2022 alert): date, counterparty role and firm, medium,
    topics, attestation. No content."""
    h = h or _require_home()
    byid = {c["id"]: c for c in load_contacts(h)}
    out = []
    for m in load_calls(h, end):
        if str(m["date"]) < start:
            continue
        out.append({"call": m["id"], "date": m["date"], "medium": m.get("medium"),
                    "counterparties": [f"{byid.get(c, {}).get('role', '?')} at {byid.get(c, {}).get('firm', '?')}"
                                       for c in m.get("with") or []],
                    "topics": m.get("topics"), "mnpi_attestation": m.get("mnpi_attestation")})
    return out


def forget(cid: str, h: Path | None = None) -> dict:
    """Remove a contact: their record, call notes with only them, their id from shared notes and intros."""
    h = h or _require_home()
    contacts = load_contacts(h)
    if not any(c["id"] == cid for c in contacts):
        raise SystemExit(f"no contact {cid}")
    last = max([int(x["id"][1:]) for x in contacts if re.fullmatch(r"c\d+", str(x.get("id")))] or [0])
    contacts = [c for c in contacts if c["id"] != cid]
    for c in contacts:
        if c.get("introduced_by") == cid:
            c.pop("introduced_by")
    save_contacts(contacts, h, last_id=last)
    deleted, edited, review = 0, 0, []
    for p in sorted((h / "calls").glob("*/*.md")):
        m = _read_md(p)
        w = m.get("with") or []
        if cid in w:
            if w == [cid]:
                p.unlink()
                deleted += 1
            else:
                m["with"] = [x for x in w if x != cid]
                _write_md(p, m)
                edited += 1
                review.append(m.get("id") or p.stem)
    runlog.log(runlog.new_run_id(), "network:forget", "ok", contact=cid, calls_deleted=deleted, calls_edited=edited)
    return {"forgotten": cid, "calls_deleted": deleted, "calls_edited": edited,
            "redact_by_hand": review,   # shared calls: body, follow-ups, gives and asks may still describe them
            "next": "the record is still in git history: in the network repo run `git filter-repo` (or recreate "
                    "the repo) and force-push, so the removal is complete"}


# ------------------------------------------------------------------ public note (this repo: public data only)
def public_dir() -> Path:
    return ROOT / cfg()["public"]["dir"]


def public_series(market: str) -> tuple[str, str]:
    """(series id, name) of the public-domain series a post may use for a market or series id. The Yahoo
    adapter is personal-use only, so a market without a public series cannot go in a post."""
    from . import store
    k = cfg()["public"]
    sid = k["series"].get(market, market)
    row = store.connect().execute("SELECT any_value(source) s, any_value(name) n FROM obs WHERE series_id = ?", [sid]).fetchone()
    if not row or row[0] is None:
        raise SystemExit(f"{market}: no stored series {sid}")
    if row[0] not in k["allowed_sources"]:
        raise SystemExit(f"{market}: series {sid} comes from '{row[0]}', not a public source {k['allowed_sources']}; "
                         f"public posts use public-domain data only (config/network.yaml public.series)")
    return sid, row[1] or sid


def public_pack(market: str, asof: str | None = None, out_dir: Path | None = None, slug: str | None = None,
                chart: bool = True) -> dict:
    """Code facts for the monthly post on one market (as of a date) and its chart, from a public-domain series:
    last value, 1/3/12-month changes, 12-month high and low, CFTC managed-money percentile when mapped (counted
    from its Friday release). Every value with its source."""
    from . import digest, journal
    asof = asof or _today()
    out_dir = out_dir or public_dir()
    sid, name = public_series(market)
    df = digest._series(sid, asof)
    if df is None or len(df) < 30:
        raise SystemExit(f"not enough stored data for {sid} up to {asof}")
    df["value"] = df["value"].astype(float)
    last = df.iloc[-1]
    pack = {"market": name, "series": sid, "price_ref": market, "asof": asof, "last": round(float(last["value"]), 4),
            "last_date": last["date"], "source_url": last["source_url"]}

    def chg(days):
        d0 = (_d(last["date"]) - timedelta(days=days)).isoformat()
        prior = df[df["date"] <= d0]
        return round(100 * (float(last["value"]) / float(prior["value"].iloc[-1]) - 1), 1) if len(prior) else None

    pack.update(chg_1m_pct=chg(30), chg_3m_pct=chg(91), chg_12m_pct=chg(365))
    yr = df[df["date"] > (_d(last["date"]) - timedelta(days=365)).isoformat()]
    pack.update(high_12m=round(float(yr["value"].max()), 4), high_12m_date=yr.loc[yr["value"].idxmax(), "date"],
                low_12m=round(float(yr["value"].min()), 4), low_12m_date=yr.loc[yr["value"].idxmin(), "date"])
    code = journal._cfg()["cftc_map"].get(market)
    # the report is dated Tuesday and released Friday: use the last report already public on the as-of date
    cf = _cftc_asof(code, (_d(asof) - timedelta(days=3)).isoformat()) if code else None
    if cf:
        pack["cftc"] = {"managed_money_pct_3y": cf["pct"], "net_pct_oi": cf["net_pct_oi"], "date": cf["date"],
                        "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}
    slug = slug or f"{asof[:7]}-{re.sub(r'[^a-z0-9]+', '-', sid.lower()).strip('-')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    if chart:
        pack["chart"] = str(_chart(df, name, asof, out_dir / f"{slug}.png", cfg()["public"]["chart_months"]))
    (out_dir / f"{slug}.pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    pack["pack"] = str(out_dir / f"{slug}.pack.json")
    return pack


def _cftc_asof(code: str, until: str) -> dict | None:
    """Managed-money net (% of open interest) percentile over 3 years, from reports dated on or before `until`."""
    from . import store
    try:
        df = store.connect().execute("SELECT date, value FROM obs WHERE series_id = ? AND date <= ? ORDER BY date",
                                     [f"{code}.mm_net_pct_oi", until]).df()
    except Exception:
        return None
    if len(df) < 52:                       # same window as the journal's crowded-side check (156 weekly reports)
        return None
    v = df["value"].astype(float).tail(156).to_numpy()
    return {"pct": round(100 * float((v <= v[-1]).mean()), 0), "net_pct_oi": round(float(v[-1]), 1),
            "date": str(df["date"].iloc[-1])[:10]}


def _chart(df: pd.DataFrame, name: str, asof: str, path: Path, months: int) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = df[df["date"] > (_d(asof) - timedelta(days=int(months * 30.5))).isoformat()]
    x = pd.to_datetime(d["date"])
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    ax.plot(x, d["value"], color="#1f4e79", lw=1.6)
    ax.scatter([x.iloc[-1]], [d["value"].iloc[-1]], color="#1f4e79", s=14, zorder=3)
    ax.annotate(f"{d['value'].iloc[-1]:,.2f}", (x.iloc[-1], d["value"].iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9, color="#1f4e79")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    ax.set_title(f"{name}, daily close, last {months} months", loc="left", fontsize=11)
    fig.text(0.01, 0.01, f"Source: {d['source_url'].iloc[-1]}, as of {d['date'].iloc[-1]}. Personal view on public data.",
             fontsize=7, color="#666666")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)
    return path


def public_calls() -> list[dict]:
    p = public_dir() / "calls.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("calls", []) if p.exists() else []


def add_public_call(call: dict) -> tuple[dict | None, list[str]]:
    """Record a call made in a post (market, direction or level, deadline, probability, invalidation)."""
    from . import digest
    errs = []
    c = dict(call)
    for f in ("issue", "date", "market", "deadline", "claim", "invalidation"):
        if not c.get(f):
            errs.append(f"{f} is required (every public call has an invalidation and a review date)")
    if c.get("market"):
        try:
            c["series"] = public_series(c["market"])[0]
        except SystemExit as e:
            errs.append(str(e))
    if not (c.get("direction") in ("up", "down", "flat") or c.get("level") is not None):
        errs.append("direction (up/down/flat) or level is required")
    if c.get("probability") is not None and not 0 < float(c["probability"]) < 1:
        errs.append("probability must be between 0 and 1")
    try:
        if _d(c["deadline"]) <= _d(c["date"]):
            errs.append("deadline must be after the post date")
    except Exception:
        errs.append("date and deadline must be YYYY-MM-DD")
    if errs:
        return None, errs
    calls = public_calls()
    c["id"] = f"pub-{c['issue']}-{1 + sum(1 for x in calls if x.get('issue') == c['issue'])}"
    c["date"], c["deadline"] = str(c["date"])[:10], str(c["deadline"])[:10]
    calls.append(c)
    public_dir().mkdir(parents=True, exist_ok=True)
    (public_dir() / "calls.yaml").write_text(
        "# Calls made in the monthly public note, scored by code (python -m pmstack network public score)\n"
        + yaml.safe_dump({"calls": calls}, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
    return c, []


def score_public(asof: str | None = None) -> dict:
    """The public track record as of a date, scored like digested calls (pmstack.digest.resolve) on the same
    public series the post used, so anyone can re-check it."""
    from . import digest
    asof = asof or _today()
    rows = []
    for c in public_calls():
        if c["date"] > asof:
            continue
        try:
            sid = public_series(c["market"])[0]
        except SystemExit as e:
            rows.append({"card": c.get("id"), "issue": c.get("issue"), "status": "refused", "reason": str(e)})
            continue
        if c.get("series") and c["series"] != sid:
            rows.append({"card": c.get("id"), "issue": c.get("issue"), "status": "refused",
                         "reason": f"recorded series {c['series']} is not the public series {sid}"})
            continue
        card = {"id": c["id"], "type": "forecast", "scoreable": True, "speaker": "Bernardo (public note)",
                "price_ref": sid, "markets": [c["market"]], "as_of": c["date"], "deadline": c["deadline"],
                "direction": c.get("direction"), "level": c.get("level"), "level_kind": c.get("level_kind"),
                "probability": c.get("probability"), "claim": c["claim"]}
        rows.append({**digest.resolve(card, asof), "issue": c["issue"], "invalidation": c.get("invalidation")})
    res = [r for r in rows if r["status"] in ("hit", "miss")]
    hits = sum(r["status"] == "hit" for r in res)
    briers = [r["brier"] for r in res if r.get("brier") is not None]
    return {"asof": asof, "calls": rows, "resolved": len(res), "hits": hits,
            "wilson_pct": digest._wilson(hits, len(res)), "mean_brier": round(sum(briers) / len(briers), 3) if briers else None,
            "open": sum(r["status"] == "open" for r in rows)}


def check_post(path: str | Path, h: Path | None = None) -> dict:
    """Public post rules: length, disclaimer, no contact names, calls recorded, scorecard once calls exist."""
    path = Path(path)
    k = cfg()["public"]
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    words = len(re.findall(r"\b\w[\w'.,%-]*\b", body))
    probs = []
    if words > k["words_max"]:
        probs.append(f"{words} words > {k['words_max']}")
    if k["disclaimer"].lower() not in body.lower():
        probs.append("the disclaimer line is missing")
    try:
        contacts = load_contacts(h)
    except SystemExit:
        contacts = None
        probs.append("network repo not found, so contact names were not checked (set PM_NETWORK_HOME or clone ../pm-network)")
    contacts = contacts or []
    named = []
    for c in contacts:
        parts = [c.get("name") or ""] + [w for w in re.split(r"\s+", c.get("name") or "") if len(w) >= 4]
        if any(w and re.search(rf"\b{re.escape(w)}\b", body) for w in parts):   # surnames too, case-sensitive
            named.append(c["id"])
    if named:
        probs.append(f"names {len(named)} contact(s) ({', '.join(named)}): never attribute a view to a contact")
    firms = sorted({c["firm"] for c in contacts if c.get("firm") and re.search(rf"\b{re.escape(c['firm'])}\b", body, re.I)})
    warn = [f"mentions a contact's firm ({', '.join(firms)}): fine only as public data, never as 'they told me'"] if firms else []
    m = re.search(r"(?i)\bnote\s*#\s*(\d+)", body)
    issue = int(m.group(1)) if m else None
    if issue is None:
        probs.append("no issue number (e.g. 'Commodity note #3')")
    earlier = [c for c in public_calls() if issue is not None and int(c["issue"]) < issue]
    if earlier and not re.search(r"(?i)scorecard|what i got wrong|last calls", body):
        probs.append("past calls exist: add the scorecard line (what I got wrong)")
    if issue is not None and not any(int(c["issue"]) == issue for c in public_calls()):
        warn.append("no call recorded for this issue: `network public add-call` for each call in the post")
    return {"file": str(path), "words": words, "issue": issue, "problems": probs, "warnings": warn}


# ------------------------------------------------------------------ CLI
def _print(obj):
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def _kv(pairs: list[str]) -> dict:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        v = v.strip()
        out[k.strip()] = int(v) if re.fullmatch(r"-?\d+", v) else [x.strip() for x in v.split(",")] \
            if k.strip() in ("markets", "topics", "alumni") else v
    return out


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack network", description="Network and reputation (agent 11)")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="create the private network repo folder")
    i.add_argument("--path")
    c = sub.add_parser("contact", help="add | update <id> | list | show <id>")
    c.add_argument("action", choices=["add", "update", "list", "show"])
    c.add_argument("id", nargs="?")
    c.add_argument("--set", nargs="*", default=[], help="field=value pairs (markets=BZ=F,CL=F)")
    cl = sub.add_parser("call", help="new --json file | close <call> <follow-up>")
    cl.add_argument("action", choices=["new", "close"])
    cl.add_argument("args", nargs="*")
    cl.add_argument("--json", help="call note header as JSON (body in the 'body' key)")
    cl.add_argument("--date")
    for name in ("due", "reconnect"):
        s = sub.add_parser(name)
        s.add_argument("--date")
    pr = sub.add_parser("prep")
    pr.add_argument("id")
    pr.add_argument("--date")
    mo = sub.add_parser("monthly")
    mo.add_argument("--month")
    mo.add_argument("--write", action="store_true")
    fo = sub.add_parser("forget")
    fo.add_argument("id")
    fo.add_argument("--yes", action="store_true")
    lg = sub.add_parser("compliance-log")
    lg.add_argument("--from", dest="start", required=True)
    lg.add_argument("--to", dest="end", required=True)
    pu = sub.add_parser("public", help="pack --market | add-call --json | score | check <post>")
    pu.add_argument("action", choices=["pack", "add-call", "score", "check"])
    pu.add_argument("file", nargs="?")
    pu.add_argument("--market")
    pu.add_argument("--date")
    pu.add_argument("--slug")
    pu.add_argument("--json")
    a = p.parse_args(argv)

    if a.cmd == "init":
        print(f"network repo ready at {init(Path(a.path) if a.path else None)}")
        return 0
    if a.cmd == "contact":
        if a.action == "add":
            rec, errs = add_contact(_kv(a.set))
        elif a.action == "update":
            if not a.id:
                print("usage: network contact update <id> --set field=value ...", file=sys.stderr)
                return 2
            rec, errs = update_contact(a.id, _kv(a.set))
        elif a.action == "list":
            _print([{k: x.get(k) for k in ("id", "name", "role", "firm", "cluster", "layer", "mnpi_risk")} for x in load_contacts()])
            return 0
        else:
            if not a.id:
                print("usage: network contact show <id>", file=sys.stderr)
                return 2
            _print(prep(a.id)["contact"])
            return 0
        _print(rec if rec else {"errors": errs})
        return 0 if rec else 1
    if a.cmd == "call":
        if a.action == "new":
            meta = json.loads(Path(a.json).read_text(encoding="utf-8"))
            body = meta.pop("body", "")
            rec, block, warn = new_call(meta, body)
            _print({"saved": rec["id"] if rec else None, "problems": block, "warnings": warn,
                    "follow_ups": rec.get("follow_ups") if rec else None})
            return 0 if rec else 1
        if len(a.args) != 2:
            print("usage: network call close <call-id> <follow-up-id> [--date YYYY-MM-DD]", file=sys.stderr)
            return 2
        _print(close_followup(a.args[0], a.args[1], a.date))
        return 0
    if a.cmd == "due":
        _print(due(a.date))
        return 0
    if a.cmd == "reconnect":
        _print(reconnect(a.date))
        return 0
    if a.cmd == "prep":
        _print(prep(a.id, a.date))
        return 0
    if a.cmd == "monthly":
        _print(monthly(a.month, a.write))
        return 0
    if a.cmd == "forget":
        if not a.yes:
            print(f"this deletes {a.id} and their call notes from the network repo; re-run with --yes")
            return 1
        _print(forget(a.id))
        return 0
    if a.cmd == "compliance-log":
        _print(compliance_log(a.start, a.end))
        return 0
    if a.cmd == "public":
        if a.action == "pack":
            out = public_pack(a.market, a.date, slug=a.slug)
            runlog.log(runlog.new_run_id(), "network:public-pack", "ok", market=a.market, asof=out["asof"])
            _print(out)
        elif a.action == "add-call":
            rec, errs = add_public_call(json.loads(Path(a.json).read_text(encoding="utf-8")))
            _print(rec or {"errors": errs})
            return 0 if rec else 1
        elif a.action == "score":
            out = score_public(a.date)
            runlog.log(runlog.new_run_id(), "network:public-score", "ok", asof=out["asof"], resolved=out["resolved"],
                       hits=out["hits"], open=out["open"])
            _print(out)
        else:
            out = check_post(a.file)
            _print(out)
            return 0 if not out["problems"] else 1
        return 0
    return 2
