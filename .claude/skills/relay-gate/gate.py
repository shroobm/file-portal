#!/usr/bin/env python3
"""gate.py - the mechanical half of the /relay-gate skill (judgment half: SKILL.md).

Runtime-neutral by design: stdlib only, no third-party imports, invoked the same way from
Claude Code, Codex, or a human shell. See RELAY-ACK-PROTOCOL.md for the contract.

Laws this file enforces mechanically:
  - relay.md is APPEND-ONLY. Nothing here ever edits or removes an existing entry.
  - SINGLE WRITER: a model may write only its own ack-<model>.json. Enforced, not trusted.
  - A confirmation requires a RESTATEMENT. A bit can be flipped without reading; a
    restatement cannot.
  - A confirmation independently re-digests the log and compares to the sender's claim.
    A mismatch is a MEASURED RED (exit 1), never a shrug.
  - A missing or malformed sidecar renders UNREAD - never idle, never confirmed.
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

PROTOCOL = "fp-relay-ack/v1"
MODELS = ("Fable", "Codex")
STATES = ("idle", "working", "blocked-on-ack", "blocked-on-rab", "UNREAD")
_LOADED_REVISION = "_gate_loaded_raw_revision"
_ACTIVE_LOCK_FILE = None
TRANSACTION_PROTOCOL = "fp-relay-transaction/v1"


# ---------- locations ----------

def coord_dir() -> Path:
    """coordination/ - overridable by FP_COORD so the selftest never touches the real relay."""
    env = os.environ.get("FP_COORD")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "coordination"


def on_live_bus() -> bool:
    return not os.environ.get("FP_COORD")


def announce_bus(cmd: str) -> None:
    """Say WHICH bus is being written, before writing it (S109, after a live incident).

    FP_COORD's absence resolves to the REAL relay - a fail-OPEN default in the one place this
    project is most careful. On 2026-08-24T17:25Z a prototype build subagent ran
    `gate.py escalate --as Fable` from a shell to demonstrate GUARD B and omitted FP_COORD, so a
    fabricated question landed in Rab's actual decision queue. It caught and voided itself, and
    the queue is intact - but nothing in the tool ever SAID which bus it was about to write.
    This does not change the default (making FP_COORD required would break every existing caller
    and Codex's too - that is Rab's call). It removes the silence.
    """
    where = "LIVE BUS" if on_live_bus() else "quarantined bus (FP_COORD)"
    print(f"[gate] {cmd} -> {where}: {coord_dir()}", file=sys.stderr)


def ack_path(model: str) -> Path:
    return coord_dir() / f"ack-{model.lower()}.json"


def relay_path() -> Path:
    return coord_dir() / "relay.md"


def transaction_lock_path() -> Path:
    return coord_dir() / ".relay-gate.lock"


def other(model: str) -> str:
    return MODELS[1] if model == MODELS[0] else MODELS[0]


# LANE vs OCCUPANT (S109, Rab: "Codex keeps calling you Fable... I don't think Codex
# understands that yet"). MODELS holds LANE names - seats, addresses, the thing MSG-FAB-nnnn
# and ack-fable.json are keyed on. A lane is NOT a model's name. The OCCUPANT is whichever
# model is sitting in the seat, and it CHANGES: the Fable lane was occupied by Claude Fable 5
# through S108's wiki block and by Claude Opus 5 from the residency block onward.
# `escalate` used to hardcode `"Claude Fable 5" if lane == "Fable"`, so it stamped Opus 5's
# escalation - the one message in Rab's own decision queue - with a different model. Codex read
# that trailer correctly; the trailer was wrong. An undeclared occupant now renders UNDECLARED
# and is NEVER guessed from the lane, because guessing is how the misattribution happened.
UNDECLARED = "UNDECLARED"


def occupant_of(data: dict) -> str:
    """Who is actually in this seat. Never inferred from the lane name."""
    v = (data or {}).get("occupant")
    return v.strip() if isinstance(v, str) and v.strip() else UNDECLARED


# FULL STOP (S109, Rab signed): "if anything escalates, tell both you and codex to stop, and
# tell me to prompt the relay gates again. I want a full stop on an escalation."
# Before this, `escalate` halted only the ESCALATING lane; the peer kept taking tickets, so work
# continued past a question the principal had not answered. An escalation now halts BOTH lanes.
# It is DERIVED from the board, never written into the peer's file - the single-writer law holds,
# and the stop reconstructs from disk for whoever reads it next.
def open_escalations():
    """[(lane, escalation)] across BOTH lanes. A lane that reads UNREAD cannot be cleared of
    holding one, so an unreadable board is not a quiet board - the caller must fail closed."""
    out, unread = [], []
    for m in MODELS:
        d, st = load(m)
        if st != "ok":
            unread.append(m)
            continue
        out += [(m, e) for e in d.get("escalations", []) if e.get("state") == "open"]
    intent, intent_status = _read_append_intent()
    if intent_status not in ("absent", "ok"):
        unread.append("transaction-journal")
    elif intent_status == "ok" and intent.get("kind") == "escalation":
        out.append((intent["writer"], {
            "ticket": intent["msg_id"],
            "asking": "unreconciled escalation transaction; run status and exact retry",
            "msg_id": intent["msg_id"], "state": "open", "journal_orphan": True,
        }))
    return out, unread


FULL_STOP_REMEDY = (
    "  FULL STOP is Rab's rule: an open escalation halts BOTH lanes, not just the escalator's.\n"
    "  Nothing resumes on a model's judgement. Ask Rab to rule, then to PROMPT THE RELAY GATES\n"
    "  AGAIN - and only `resolve` (his decision, recorded) lifts the stop.\n"
    "  A notice (no --ticket) always passes: that is how you tell the other lane you have stopped."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


# ---------- canonical form + digest ----------

def canonical(text: str) -> str:
    """Line-ending- and trailing-space-blind. The repo is mixed CRLF (SYM-029), so a digest
    that changed with line endings would be a probe that lies."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()


# ---------- sidecar io (atomic, single-writer) ----------

def blank(model: str) -> dict:
    return {
        "writer": model,
        "protocol": PROTOCOL,
        "updated_utc": utc_now(),
        "state": "idle",
        "occupant": None,          # the model in this seat; None -> UNDECLARED, never guessed
        "beat": None,              # the status beat; None -> UNREAD, never "idle"
        "current_ticket": None,
        "sent": [],
        "confirmed": [],
        "escalations": [],
        "disagreements": [],       # terminal two-round dispositions; absent remains valid v1
    }


def load(model: str):
    """Returns (data, status). status is 'ok' or 'UNREAD' - a failed read NEVER returns a
    healthy-looking empty state."""
    p = ack_path(model)
    if not p.exists():
        return None, "UNREAD"
    try:
        raw = p.read_bytes()
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, "UNREAD"
    if not isinstance(d, dict) or d.get("protocol") != PROTOCOL or d.get("writer") != model:
        return None, "UNREAD"
    if d.get("occupant") is not None and not _valid_origin_occupant(d.get("occupant")):
        return None, "UNREAD"
    for key in ("sent", "confirmed"):
        if not isinstance(d.get(key), list):
            return None, "UNREAD"
    if not isinstance(d.get("escalations", []), list):   # added S108; absent is fine (back-compat)
        return None, "UNREAD"
    if not isinstance(d.get("disagreements", []), list):  # added S111; absent is fine (back-compat)
        return None, "UNREAD"
    d.setdefault("escalations", [])
    d.setdefault("disagreements", [])
    # Optimistic revision metadata is process-private. save() strips it before serialization.
    d[_LOADED_REVISION] = "sha256:" + hashlib.sha256(raw).hexdigest()
    return d, "ok"


@contextlib.contextmanager
def _relay_transaction_lock():
    """One stable OS advisory lock for relay transactions and standalone sidecar saves.

    A dedicated lock file is never replaced, unlike the sidecars. It also avoids Windows byte-
    range locking relay.md itself, which would make lock-held validation unable to read the bus.
    Append-producing commands hold this lock from their fresh reads and guards, through id
    allocation and append, until their own sidecar is published.
    """
    global _ACTIVE_LOCK_FILE
    p = transaction_lock_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
    descriptor = os.open(p, flags, 0o600)  # O_CREAT is atomic; no unlocked first-byte write
    with io.open(descriptor, "r+b", closefd=True) as lock_file:
        lock_file.seek(0)
        if os.name == "nt":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            lock_file.seek(0)
            legacy = lock_file.read()
            if not legacy or legacy.replace(b"# relay\n", b"") == b"":
                lock_file.seek(0)
                lock_file.write(b"L")
                lock_file.truncate()
                lock_file.flush()
                os.fsync(lock_file.fileno())
            if _ACTIVE_LOCK_FILE is not None:
                raise RuntimeError("relay transaction lock was reacquired in one process")
            _ACTIVE_LOCK_FILE = lock_file
            yield
        finally:
            _ACTIVE_LOCK_FILE = None
            lock_file.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _save_locked(model: str, data: dict, as_model: str, *, allow_pending: bool = False) -> None:
    """CAS-publish one sidecar while `_relay_transaction_lock` is already held."""
    if model != as_model:
        raise SystemExit(
            f"REFUSED: {as_model} may not write {ack_path(model).name} - single-writer law "
            "(RELAY-ACK-PROTOCOL.md). Each model writes only its own file."
        )
    intent, intent_status = _read_append_intent()
    if not allow_pending and intent_status != "absent":
        label = "malformed/UNREAD" if intent_status != "ok" else intent.get("msg_id")
        raise SystemExit(
            f"REFUSED: unresolved transaction journal {label}; ordinary sidecar mutations "
            "cannot destroy exact append recovery. Retry or reconcile the pending command."
        )
    p = ack_path(model)
    p.parent.mkdir(parents=True, exist_ok=True)
    expected = data.get(_LOADED_REVISION)
    current_raw = p.read_bytes() if p.exists() else None
    current = ("sha256:" + hashlib.sha256(current_raw).hexdigest()
               if current_raw is not None else None)
    if current != expected:
        raise SystemExit(
            f"REFUSED: stale {p.name} revision (loaded {expected or 'ABSENT'}, now "
            f"{current or 'ABSENT'}). Reload and retry; no stale whole-sidecar overwrite."
        )
    data["updated_utc"] = utc_now()
    public = dict(data)
    public.pop(_LOADED_REVISION, None)  # internal concurrency metadata never reaches JSON
    wire = (json.dumps(public, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    tmp = p.with_suffix(".part")       # .part-then-rename: the repo's publish invariant
    with io.open(tmp, "wb") as fh:
        fh.write(wire)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)
    data[_LOADED_REVISION] = "sha256:" + hashlib.sha256(wire).hexdigest()


def save(model: str, data: dict, as_model: str) -> None:
    """Standalone CAS save. Append transactions call `_save_locked` to avoid re-locking."""
    with _relay_transaction_lock():
        _save_locked(model, data, as_model)


# ---------- relay parsing (read-only, never edits) ----------

MSG_RE = re.compile(r"MSG-(FAB|CDX)-(\d{4})")

# An entry boundary in relay.md, by the log's OWN grammar. Used to bound what a digest seals -
# see extract_entry. Deliberately anchored on the ⟨msg:⟩ stamp: a "## " line inside a body is
# prose, and treating it as a boundary is how 76% of an escalation escaped its own seal.
ENTRY_HEADER_RE = re.compile(r"^## .*⟨msg:\s*MSG-(?:FAB|CDX)-\d{4}⟩")
ENTRY_META_RE = re.compile(
    r"^## (?P<utc>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z) · "
    r"⟨from: (?P<from>Fable|Codex)⟩ → ⟨to: (?P<to>Fable|Codex)⟩ · "
    r"⟨msg: (?P<id>MSG-(?:FAB|CDX)-\d{4})⟩$"
)
DISAGREEMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
DISAGREEMENT_MARKER_RE = re.compile(
    r"(?m)^\*\*DISAGREEMENT ID\.\*\*\s+`?(?P<id>[A-Z][A-Z0-9-]{2,63})`?\s*$"
)


def relay_entries():
    """Strictly parsed relay entries, including log position and complete sealed bytes."""
    p = relay_path()
    if not p.exists():
        return [], "UNREAD"
    try:
        text = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return [], "UNREAD"
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    heads = []
    for i, line in enumerate(lines):
        match = ENTRY_META_RE.match(line)
        if match:
            heads.append((i, match))
    rows = []
    for n, (start, match) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        row = match.groupdict()
        row.update({"position": start, "text": "\n".join(lines[start:end])})
        rows.append(row)
    return rows, "ok"


def _relay_id_stamp_count(msg_id: str):
    """Count minting stamps, including malformed headers strict parsing cannot accept."""
    try:
        text = io.open(relay_path(), encoding="utf-8", errors="replace").read()
    except Exception:
        return 0, "UNREAD"
    count = 0
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not (line.startswith("## ") or "⟨msg:" in line):
            continue
        count += sum(match.group(0) == msg_id for match in MSG_RE.finditer(line))
    return count, "ok"


_INTENT_KEYS = {
    "protocol", "kind", "writer", "to", "msg_id", "stamp", "entry_digest",
    "request_digest", "expected_revision",
}


def _read_append_intent():
    """Read the transaction journal embedded after byte 0 of the stable ignored lock file."""
    try:
        if _ACTIVE_LOCK_FILE is not None:
            _ACTIVE_LOCK_FILE.seek(0)
            raw = _ACTIVE_LOCK_FILE.read()
        else:
            p = transaction_lock_path()
            if not p.exists():
                return None, "absent"
            raw = p.read_bytes()
    except Exception:
        return None, "UNREAD"
    if raw in (b"", b"L") or (raw and raw.replace(b"# relay\n", b"") == b""):
        return None, "absent"
    if not raw.startswith(b"L"):
        return None, "RED"
    try:
        intent = json.loads(raw[1:].decode("utf-8"))
    except Exception:
        return None, "RED"
    if not isinstance(intent, dict) or set(intent) != _INTENT_KEYS:
        return None, "RED"
    prefix = "FAB" if intent.get("writer") == "Fable" else "CDX"
    if (intent.get("protocol") != TRANSACTION_PROTOCOL
            or intent.get("kind") not in ("post", "escalation", "disagreement")
            or intent.get("writer") not in MODELS
            or intent.get("to") != other(intent.get("writer"))
            or not isinstance(intent.get("msg_id"), str)
            or not re.fullmatch(rf"MSG-{prefix}-\d{{4}}", intent.get("msg_id", ""))
            or _parse_utc(intent.get("stamp")) is None
            or not _sha256_value(intent.get("entry_digest"))
            or not _sha256_value(intent.get("request_digest"))
            or not _sha256_value(intent.get("expected_revision"))):
        return None, "RED"
    return intent, "ok"


def _write_append_intent(intent: dict) -> None:
    if _ACTIVE_LOCK_FILE is None:
        raise RuntimeError("append intent write requires the relay transaction lock")
    wire = (b"L" + json.dumps(intent, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode("utf-8"))
    _ACTIVE_LOCK_FILE.seek(0)
    _ACTIVE_LOCK_FILE.write(wire)
    _ACTIVE_LOCK_FILE.truncate()
    _ACTIVE_LOCK_FILE.flush()
    os.fsync(_ACTIVE_LOCK_FILE.fileno())


def _clear_append_intent() -> None:
    if _ACTIVE_LOCK_FILE is None:
        raise RuntimeError("append intent clear requires the relay transaction lock")
    _ACTIVE_LOCK_FILE.seek(0)
    _ACTIVE_LOCK_FILE.write(b"L")
    _ACTIVE_LOCK_FILE.truncate()
    _ACTIVE_LOCK_FILE.flush()
    os.fsync(_ACTIVE_LOCK_FILE.fileno())


def _intent_relay_state(intent: dict):
    entries, status = relay_entries()
    stamp_count, stamp_status = _relay_id_stamp_count(intent["msg_id"])
    if status != "ok" or stamp_status != "ok":
        return "UNREAD", "relay cannot be read"
    hits = [row for row in entries if row["id"] == intent["msg_id"]]
    if stamp_count == 0 and not hits:
        return "pre-append", "intent was durable before the relay append"
    if (stamp_count != 1 or len(hits) != 1
            or hits[0].get("from") != intent["writer"]
            or hits[0].get("to") != intent["to"]
            or hits[0].get("utc") != intent["stamp"]
            or digest(hits[0]["text"]) != intent["entry_digest"]):
        return "RED", "relay identity or digest conflicts with the transaction intent"
    return "published", "relay append exists without a cleared transaction intent"


def _finish_append_intent(kind: str, writer: str, msg_id: str) -> None:
    """Clear only after relay and the command's exact sidecar publication are visible."""
    intent, status = _read_append_intent()
    if (status != "ok" or intent.get("kind") != kind or intent.get("writer") != writer
            or intent.get("msg_id") != msg_id):
        raise SystemExit("RED: transaction journal changed before sidecar publication completed")
    relay_state, detail = _intent_relay_state(intent)
    if relay_state != "published":
        raise SystemExit(f"RED: cannot clear transaction journal: {detail}")
    actor, actor_status = load(writer)
    if actor_status != "ok":
        raise SystemExit("RED: cannot clear transaction journal: writer sidecar is UNREAD")
    sent = [row for row in actor.get("sent", []) if isinstance(row, dict)
            and row.get("id") == msg_id and row.get("digest") == intent["entry_digest"]]
    structured = True
    if kind == "escalation":
        structured = len([row for row in actor.get("escalations", [])
                          if isinstance(row, dict) and row.get("msg_id") == msg_id]) == 1
    elif kind == "disagreement":
        structured = len([row for row in actor.get("disagreements", [])
                          if isinstance(row, dict) and row.get("terminal_msg_id") == msg_id]) == 1
    if len(sent) != 1 or not structured:
        raise SystemExit("RED: journal retained because sidecar publication is incomplete")
    _clear_append_intent()


def _append_relay_locked(entry: str, msg_id: str, *, kind: str,
                         request_digest: str, expected_revision: str,
                         resume: bool = False) -> str:
    """Append one globally unique entry while the caller holds the transaction lock.

    All runtime append producers go through this point. The pre-append uniqueness check and
    post-append parse happen inside the same lock as id allocation and sidecar publication.
    """
    entries, status = relay_entries()
    if status != "ok":
        raise SystemExit("REFUSED: relay.md is UNREAD; cannot allocate a unique message id")
    stamp_count, stamp_status = _relay_id_stamp_count(msg_id)
    if stamp_status != "ok":
        raise SystemExit("REFUSED: relay.md is UNREAD; cannot prove message-id uniqueness")
    if stamp_count or any(row["id"] == msg_id for row in entries):
        raise SystemExit(f"REFUSED: message id {msg_id} already exists in relay.md")
    structured_refs, structured_status = _global_structured_id_references(msg_id)
    if structured_status != "ok":
        raise SystemExit(
            "REFUSED: a lane sidecar is UNREAD; cannot prove global message-id uniqueness"
        )
    if structured_refs:
        raise SystemExit(
            f"REFUSED: message id {msg_id} is already allocated by a structured sidecar record"
        )
    header = ENTRY_META_RE.match(entry.split("\n", 1)[0])
    if not header or header.group("id") != msg_id:
        raise SystemExit("REFUSED: internal relay entry/header id mismatch")
    intent = {
        "protocol": TRANSACTION_PROTOCOL, "kind": kind, "writer": header.group("from"),
        "to": header.group("to"), "msg_id": msg_id, "stamp": header.group("utc"),
        "entry_digest": digest(entry), "request_digest": request_digest,
        "expected_revision": expected_revision,
    }
    pending, pending_status = _read_append_intent()
    if resume:
        if pending_status != "ok" or pending != intent:
            raise SystemExit("REFUSED: retry does not exactly match the pending transaction")
    elif pending_status != "absent":
        label = "malformed" if pending_status != "ok" else pending.get("msg_id")
        raise SystemExit(f"REFUSED: unresolved transaction journal {label}; exact retry or "
                         "reconciliation is required before another append")
    else:
        _write_append_intent(intent)
    crash_before = os.environ.get("FP_GATE_TEST_CRASH_BEFORE_APPEND")
    if os.environ.get("FP_COORD") and crash_before in (kind, "all"):
        os._exit(86)
    with io.open(relay_path(), "a", encoding="utf-8", newline="") as fh:
        fh.write("\n" + entry)
        fh.flush()
        os.fsync(fh.fileno())
    published, status = relay_entries()
    hits = [row for row in published if row["id"] == msg_id]
    stamp_count, stamp_status = _relay_id_stamp_count(msg_id)
    if status != "ok" or stamp_status != "ok" or len(hits) != 1 or stamp_count != 1:
        raise SystemExit(
            f"RED: relay append for {msg_id} could not be read back as one unique entry"
        )
    published_digest = digest(hits[0]["text"])
    crash_after = os.environ.get("FP_GATE_TEST_CRASH_AFTER_APPEND")
    if os.environ.get("FP_COORD") and crash_after in (kind, "all"):
        os._exit(87)
    return published_digest


def _slot(text: str, name: str):
    matches = re.findall(
        rf"(?m)^\*\*{re.escape(name)}\.\*\*[ \t]+(.+?)[ \t]*$", text
    )
    values = [value.strip() for value in matches if value.strip()]
    return values[0] if len(matches) == 1 and len(values) == 1 else None


def _parse_utc(value):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _stable_digest(value) -> str:
    wire = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return digest(wire)


def _normalized_occupant(value) -> str:
    return " ".join(str(value or "").split())


def _valid_origin_occupant(value) -> bool:
    return (isinstance(value, str) and 3 <= len(value) <= 200
            and value == _normalized_occupant(value))


def _origin_occupant(text: str):
    """Decode the JSON-string provenance slot; missing or noncanonical values are invalid."""
    raw = _slot(text, "ORIGIN OCCUPANT")
    try:
        value = json.loads(raw) if raw is not None else None
    except Exception:
        return None
    if not _valid_origin_occupant(value):
        return None
    return value


def _message_id_references(lanes: dict, msg_id: str):
    """All structured allocations of an id across both sidecars."""
    refs = []
    for lane, data in lanes.items():
        refs += [(lane, "sent", row) for row in data.get("sent", [])
                 if isinstance(row, dict) and row.get("id") == msg_id]
        refs += [(lane, "escalation", row) for row in data.get("escalations", [])
                 if isinstance(row, dict) and row.get("msg_id") == msg_id]
        refs += [(lane, "disagreement", row) for row in data.get("disagreements", [])
                  if isinstance(row, dict) and row.get("terminal_msg_id") == msg_id]
    return refs


def _global_structured_id_references(msg_id: str):
    """Read both sidecars under the active transaction before any message-id append."""
    lanes = {}
    for lane in MODELS:
        data, status = load(lane)
        if status != "ok":
            return [], "UNREAD"
        lanes[lane] = data
    return _message_id_references(lanes, msg_id), "ok"


def _normalized_reading(value: str) -> str:
    """Only exact normalized convergence is mechanical; semantic equivalence stays human."""
    return " ".join(value.split())


def _validate_disagreement_chain(round1, round2, lanes, *, terminal_utc=None):
    """Return the four structured messages or raise ValueError before any write."""
    terminal_at = None
    if terminal_utc is not None:
        terminal_at = _parse_utc(terminal_utc)
        if terminal_at is None:
            raise ValueError("terminal disposition timestamp is invalid")
    ids = list(round1) + list(round2)
    if len(ids) != 4 or len(set(ids)) != 4:
        raise ValueError("exactly four distinct existing relay ids are required")
    entries, status = relay_entries()
    if status != "ok":
        raise ValueError("relay.md is UNREAD; silence is not disagreement")
    by_id = {}
    for entry in entries:
        by_id.setdefault(entry["id"], []).append(entry)
    chain = []
    for msg_id in ids:
        hits = by_id.get(msg_id, [])
        if len(hits) != 1:
            raise ValueError(f"{msg_id} must name exactly one existing relay entry")
        chain.append(hits[0])

    order = [entry["from"] for entry in chain]
    first, peer = order[0], other(order[0])
    if order != [first, peer, first, peer]:
        raise ValueError("lane order must alternate identically across both rounds")
    if any(entry["to"] != other(entry["from"]) for entry in chain):
        raise ValueError("each disagreement entry must address the peer lane")
    if any((entry["from"] == "Fable") != entry["id"].startswith("MSG-FAB-")
           for entry in chain):
        raise ValueError("message id prefix does not match its sender lane")
    positions = [entry["position"] for entry in chain]
    if positions != sorted(positions) or len(set(positions)) != 4:
        raise ValueError("round ids are not in exact relay chronology")
    times = [_parse_utc(entry["utc"]) for entry in chain]
    if any(value is None for value in times) or any(a > b for a, b in zip(times, times[1:])):
        raise ValueError("round timestamps contradict relay chronology")

    structured = []
    for index, entry in enumerate(chain):
        sender, receiver = entry["from"], entry["to"]
        sent = [row for row in lanes[sender].get("sent", []) if row.get("id") == entry["id"]]
        confirmed = [row for row in lanes[receiver].get("confirmed", [])
                     if row.get("id") == entry["id"]]
        if len(sent) != 1 or len(confirmed) != 1:
            raise ValueError(f"{entry['id']} lacks one exact sender claim and peer receipt")
        expected = digest(entry["text"])
        if (sent[0].get("to") != receiver
                or sent[0].get("requires_ack", True) is not True):
            raise ValueError(f"{entry['id']} is not an acknowledged peer send")
        if sent[0].get("utc") != entry["utc"]:
            raise ValueError(f"{entry['id']} sender timestamp does not match relay header")
        if sent[0].get("digest") != expected or confirmed[0].get("digest") != expected:
            raise ValueError(f"{entry['id']} digest claim/receipt does not match relay bytes")
        if confirmed[0].get("from") != sender:
            raise ValueError(f"{entry['id']} confirmation names the wrong sender")
        if len(str(confirmed[0].get("restatement") or "").strip()) < 10:
            raise ValueError(f"{entry['id']} peer receipt lacks a substantive restatement")
        sent_at = _parse_utc(sent[0].get("utc"))
        confirmed_at = _parse_utc(confirmed[0].get("confirmed_utc"))
        if sent_at is None or confirmed_at is None or confirmed_at < sent_at:
            raise ValueError(f"{entry['id']} receipt chronology is invalid")
        if terminal_at is not None and confirmed_at > terminal_at:
            raise ValueError(f"{entry['id']} receipt occurs after terminal disposition")
        reading, probe = _slot(entry["text"], "READING"), _slot(entry["text"], "PROBE")
        if reading is None or probe is None:
            raise ValueError(f"{entry['id']} requires one nonempty READING and PROBE slot")
        structured.append({
            "round": 1 if index < 2 else 2,
            "order": index + 1,
            "id": entry["id"],
            "lane": sender,
            "reading": reading,
            "probe": probe,
            "sent_utc": sent[0]["utc"],
            "confirmed_utc": confirmed[0]["confirmed_utc"],
            "source_digest": expected,
        })

    first_round2_send = _parse_utc(structured[2]["sent_utc"])
    if any(_parse_utc(row["confirmed_utc"]) >= first_round2_send for row in structured[:2]):
        raise ValueError("both round-1 confirmations must precede the first round-2 send")
    round1_by_lane = {row["lane"]: row["id"] for row in structured[:2]}
    for row, entry in zip(structured[2:], chain[2:]):
        response = _slot(entry["text"], "RESPONDS-TO")
        match = re.fullmatch(r"`?(MSG-(?:FAB|CDX)-\d{4})`?", response or "")
        expected = round1_by_lane[other(row["lane"])]
        if not match or match.group(1) != expected:
            raise ValueError(f"{row['id']} must RESPOND-TO peer round-1 entry {expected}")
        row["responds_to"] = expected
    if _normalized_reading(structured[2]["reading"]) == _normalized_reading(
            structured[3]["reading"]):
        raise ValueError("round-2 READINGS are identical after normalization: this converged")
    return structured, entries


def _terminal_disagreement_entry(writer: str, msg_id: str, stamp: str, payload: dict) -> str:
    """Canonical terminal notice. Rebuilding it makes an orphan independently checkable."""
    messages = payload["messages"]
    latest = {row["lane"]: row for row in messages if row["round"] == 2}
    request_digest = _stable_digest(payload)
    body = [
        "**RECAP — PRESERVED DISAGREEMENT.**",
        "",
        f"**DISAGREEMENT ID.** `{payload['id']}`",
        "",
        f"**ORIGIN OCCUPANT.** {json.dumps(payload['origin_occupant'], ensure_ascii=False)}",
        "",
        f"**REQUEST DIGEST.** `{request_digest}`",
        "",
        "**GROUND.** Two reciprocal rounds are complete and every cited entry was "
        "peer-confirmed against its sender's digest.",
        "",
        "**CHAIN.** " + " → ".join(f"`{row['id']}`" for row in messages),
        "",
    ]
    for lane in MODELS:
        row = latest[lane]
        body += [f"**READING — {lane}.** {row['reading']}", "",
                 f"**PROBE — {lane}.** {row['probe']}", ""]
    body += [f"**CONSEQUENCE.** {payload['consequence']}", "",
             "**PROHIBITED ACTIONS.**"]
    body += [f"- {action}" for action in payload["prohibited_actions"]]
    body += [
        "",
        "**BOUNDS.** No reading is promoted, merged, averaged, or called agreement. This "
        "notice clears no `blocked-on-rab`, escalation, FULL STOP, signature, adoption, "
        "threshold, vault, or pipeline boundary.",
        "",
        "**TERMINAL.** DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED",
        "",
        "**FOR RAB.** No response is requested by this disposition. Reopen only for new "
        "evidence or Rab's instruction.",
        "",
    ]
    header = (f"## {stamp} · ⟨from: {writer}⟩ → ⟨to: {other(writer)}⟩ · "
              f"⟨msg: {msg_id}⟩")
    return header + "\n\n" + "\n".join(body)


def _record_terminal_disagreement(actor: dict, writer: str, payload: dict,
                                  msg_id: str, stamp: str, terminal_digest: str,
                                  adopter_occupant: str = None,
                                  adopted_utc: str = None) -> None:
    record = dict(payload)
    record.update({
        "recorded_utc": stamp,
        "writer": writer,
        "request_digest": _stable_digest(payload),
        "terminal_msg_id": msg_id,
        "terminal_digest": terminal_digest,
    })
    if adopter_occupant is not None:
        record["adopter_occupant"] = adopter_occupant
        record["adopted_utc"] = adopted_utc
    actor["sent"].append({
        "id": msg_id, "to": other(writer), "utc": stamp, "digest": terminal_digest,
        "subject": f"PRESERVED DISAGREEMENT: {payload['id']}", "ticket": None,
        "requires_ack": False, "disagreement_id": payload["id"],
    })
    actor["disagreements"].append(record)


def _blockers_fingerprint(data: dict):
    return (
        json.dumps(data.get("state"), ensure_ascii=False, separators=(",", ":")),
        json.dumps(data.get("escalations"), ensure_ascii=False, separators=(",", ":")),
    )


_TERMINAL_REQUIRED_KEYS = {
    "id", "messages", "consequence", "prohibited_actions", "origin_occupant",
    "recorded_utc", "writer", "request_digest", "terminal_msg_id", "terminal_digest",
}
_TERMINAL_OPTIONAL_KEYS = {"adopter_occupant", "adopted_utc"}
_SOURCE_BASE_KEYS = {
    "round", "order", "id", "lane", "reading", "probe", "sent_utc",
    "confirmed_utc", "source_digest",
}
_TERMINAL_SENT_KEYS = {
    "id", "to", "utc", "digest", "subject", "ticket", "requires_ack",
    "disagreement_id",
}


def _sha256_value(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"sha256:[0-9a-f]{64}", value))


def _verify_terminal_record(owner: str, record: dict, lanes: dict):
    """Strict shared proof for status and exact replay.

    Returns `(ok, classification, detail)`, where classification is `VERIFIED`, `RED`, or
    `UNREAD`. A dictionary-shaped row is never enough to render PRESERVED.
    """
    if not isinstance(record, dict):
        return False, "RED", "structured record is not an object"
    keys = set(record)
    if (not _TERMINAL_REQUIRED_KEYS.issubset(keys)
            or not keys.issubset(_TERMINAL_REQUIRED_KEYS | _TERMINAL_OPTIONAL_KEYS)):
        return False, "RED", "terminal record schema has missing or unknown fields"
    if ("adopter_occupant" in record) != ("adopted_utc" in record):
        return False, "RED", "adopter occupant and adoption UTC must appear together"
    if owner not in MODELS or record.get("writer") != owner:
        return False, "RED", "terminal writer does not match its single-writer sidecar"
    disagreement_id = record.get("id")
    if not isinstance(disagreement_id, str) or not DISAGREEMENT_ID_RE.fullmatch(disagreement_id):
        return False, "RED", "disagreement id is malformed"
    terminal_id = record.get("terminal_msg_id")
    prefix = "FAB" if owner == "Fable" else "CDX"
    if not isinstance(terminal_id, str) or not re.fullmatch(
            rf"MSG-{prefix}-\d{{4}}", terminal_id):
        return False, "RED", "terminal message id is malformed or names the wrong lane"
    if _parse_utc(record.get("recorded_utc")) is None:
        return False, "RED", "recorded UTC is malformed"
    if not _sha256_value(record.get("request_digest")):
        return False, "RED", "request digest is malformed"
    if not _sha256_value(record.get("terminal_digest")):
        return False, "RED", "terminal digest is malformed"
    origin = record.get("origin_occupant")
    if not _valid_origin_occupant(origin):
        return False, "RED", "origin occupant is missing or malformed"
    if "adopter_occupant" in record:
        adopter = record.get("adopter_occupant")
        adopted = _parse_utc(record.get("adopted_utc"))
        if (not _valid_origin_occupant(adopter) or adopter == origin or adopted is None
                or adopted < _parse_utc(record.get("recorded_utc"))):
            return False, "RED", "adopter provenance is malformed or contradicts origin"

    consequence = record.get("consequence")
    prohibited = record.get("prohibited_actions")
    if (not isinstance(consequence, str) or not consequence
            or consequence != " ".join(consequence.split())):
        return False, "RED", "consequence is empty or noncanonical"
    if (not isinstance(prohibited, list) or not prohibited
            or any(not isinstance(value, str) or not value
                   or value != " ".join(value.split()) for value in prohibited)
            or len(prohibited) != len(set(prohibited))):
        return False, "RED", "prohibited actions are empty, duplicate, or noncanonical"

    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) != 4:
        return False, "RED", "terminal source schema requires exactly four messages"
    for index, row in enumerate(messages):
        expected_keys = _SOURCE_BASE_KEYS | ({"responds_to"} if index >= 2 else set())
        if not isinstance(row, dict) or set(row) != expected_keys:
            return False, "RED", f"source message {index + 1} has malformed schema"
        if (type(row.get("round")) is not int or row.get("round") != (1 if index < 2 else 2)
                or type(row.get("order")) is not int or row.get("order") != index + 1
                or row.get("lane") not in MODELS
                or not isinstance(row.get("id"), str)
                or not isinstance(row.get("reading"), str) or not row.get("reading").strip()
                or not isinstance(row.get("probe"), str) or not row.get("probe").strip()
                or _parse_utc(row.get("sent_utc")) is None
                or _parse_utc(row.get("confirmed_utc")) is None
                or not _sha256_value(row.get("source_digest"))):
            return False, "RED", f"source message {index + 1} has invalid values"
        if index >= 2 and not isinstance(row.get("responds_to"), str):
            return False, "RED", f"source message {index + 1} lacks RESPONDS-TO provenance"

    payload = {
        "id": disagreement_id,
        "messages": messages,
        "consequence": consequence,
        "prohibited_actions": prohibited,
        "origin_occupant": origin,
    }
    if _stable_digest(payload) != record.get("request_digest"):
        return False, "RED", "request digest does not seal the structured payload"

    try:
        reconstructed, entries = _validate_disagreement_chain(
            [messages[0]["id"], messages[1]["id"]],
            [messages[2]["id"], messages[3]["id"]], lanes,
            terminal_utc=record.get("recorded_utc"),
        )
    except ValueError as error:
        classification = "UNREAD" if "UNREAD" in str(error) else "RED"
        return False, classification, f"cited source chain failed verification: {error}"
    except Exception as error:
        return False, "RED", f"cited source schema failed verification: {error}"
    if reconstructed != messages:
        return False, "RED", "stored source fields or digests differ from current verified chain"

    terminal = [entry for entry in entries if entry["id"] == terminal_id]
    stamp_count, stamp_status = _relay_id_stamp_count(terminal_id)
    if stamp_status != "ok":
        return False, "UNREAD", "relay message stamps cannot be read"
    if len(terminal) != 1 or stamp_count != 1:
        return False, "RED", "terminal relay identity is absent or not globally unique"
    terminal_entry = terminal[0]
    expected_entry = _terminal_disagreement_entry(
        owner, terminal_id, record["recorded_utc"], payload
    )
    if (terminal_entry.get("from") != owner or terminal_entry.get("to") != other(owner)
            or terminal_entry.get("utc") != record.get("recorded_utc")
            or _origin_occupant(terminal_entry["text"]) != origin
            or canonical(terminal_entry["text"]) != canonical(expected_entry)
            or digest(terminal_entry["text"]) != record.get("terminal_digest")):
        return False, "RED", "terminal relay content, digest, origin, or timestamp is not canonical"

    refs = _message_id_references(lanes, terminal_id)
    sent_refs = [(lane, row) for lane, kind, row in refs if kind == "sent"]
    disagreement_refs = [(lane, row) for lane, kind, row in refs if kind == "disagreement"]
    if (len(refs) != 2 or len(sent_refs) != 1 or len(disagreement_refs) != 1
            or sent_refs[0][0] != owner or disagreement_refs[0][0] != owner
            or disagreement_refs[0][1] is not record):
        return False, "RED", "terminal id lacks one exact sent/disagreement reference pair"
    sent = sent_refs[0][1]
    if set(sent) != _TERMINAL_SENT_KEYS:
        return False, "RED", "terminal sent row schema is malformed"
    expected_sent = {
        "id": terminal_id, "to": other(owner), "utc": record["recorded_utc"],
        "digest": record["terminal_digest"],
        "subject": f"PRESERVED DISAGREEMENT: {disagreement_id}",
        "ticket": None, "requires_ack": False, "disagreement_id": disagreement_id,
    }
    if sent != expected_sent:
        return False, "RED", "terminal sent row does not match the canonical disposition"
    id_records = [(lane, row) for lane, data in lanes.items()
                  for row in data.get("disagreements", [])
                  if isinstance(row, dict) and row.get("id") == disagreement_id]
    if len(id_records) != 1 or id_records[0][0] != owner or id_records[0][1] is not record:
        return False, "RED", "disagreement id is duplicated across structured records"
    return True, "VERIFIED", "terminal record and all source/relay references verified"


# THE COUNTER'S FLOOR IS THE LOG, NOT THE SIDECAR (S109, after a live id collision).
#
# next_id used to take max() over the sidecar's sent[] alone. The sidecar is MUTABLE and can be
# restored BACKWARDS: on 2026-08-24 a repair of the fabricated-escalation incident restored
# ack-fable.json with `git checkout`, the sent row for MSG-FAB-0018 vanished with it, the counter
# regressed, and the next post minted MSG-FAB-0018 a SECOND time. relay.md now permanently names
# two different entries MSG-FAB-0018 (relay.md:2111 and relay.md:2125) - appends never erase, so
# that collision is in the record forever.
#
# The asymmetry is the fix: relay.md is APPEND-ONLY and cannot lose an entry, so the log is the
# one clock that never runs backwards. The floor is now max(sidecar sent[], ids stamped in the
# log). A restored sidecar can no longer regress the counter, because the log still holds the
# evidence of the mint. Format unchanged; nothing is renumbered; the max() INPUT SET is the whole
# change.
#
# S109 SINGLE-LANE DISCLOSURE: this repair and its tripwires (T56/T57 in selftest.py) were
# designed, written and checked by Claude agents ONLY. The Codex lane was out of budget, so there
# is NO cross-vendor check on this code. Discount the evidence accordingly.
def log_max_id(prefix: str):
    """Highest nnnn for `prefix` stamped in the APPEND-ONLY log. Returns (n, status).

    status is 'ok' or 'UNREAD'. A log that cannot be read returns UNREAD and is NEVER rendered
    as "no ids found" - a 0 from a failed probe is exactly the lie the restored sidecar told.
    """
    p = relay_path()
    if not p.exists():
        return 0, "UNREAD"
    try:
        text = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return 0, "UNREAD"
    n = 0
    for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        # Only a MINTING STAMP counts: an entry header, or any line carrying the ⟨msg: …⟩ marker
        # that `post` and `escalate` write. Prose that merely NAMES an id - a void notice, a
        # correction, this very incident's write-up - is not a mint, and counting it would let
        # commentary move the counter. (Measured on the live log 2026-08-24: stamps-only and
        # whole-file scans both give FAB 27 / CDX 9, so the narrower rule loses nothing today.)
        if not (ln.startswith("## ") or "⟨msg:" in ln):
            continue
        for m in MSG_RE.finditer(ln):
            if m.group(1) == prefix:
                n = max(n, int(m.group(2)))
    return n, "ok"


def next_id(model: str, data: dict) -> str:
    prefix = "FAB" if model == "Fable" else "CDX"
    n = 0
    for row in data.get("sent", []):
        m = MSG_RE.search(row.get("id", ""))
        if m and m.group(1) == prefix:
            n = max(n, int(m.group(2)))
    log_n, log_status = log_max_id(prefix)
    if log_status == "ok":
        n = max(n, log_n)
    elif n:
        # The sidecar remembers sends but the append-only witness cannot be read, so for THIS
        # mint the regression guard is absent. Say it out loud rather than mint silently on one
        # clock. (A brand-new bus with no sends yet is not this case and stays quiet.)
        print(f"[gate] WARNING: {relay_path()} is UNREAD - minting MSG-{prefix}-{n + 1:04d} from "
              "the MUTABLE sidecar alone; a restored sidecar cannot be caught without the log.",
              file=sys.stderr)
    return f"MSG-{prefix}-{n + 1:04d}"


def extract_entry(msg_id: str):
    """Body = the entry's header line through the line before the next '## ' header.
    Returns None if the id is not in the log."""
    if not relay_path().exists():
        return None
    text = io.open(relay_path(), encoding="utf-8", errors="replace").read()
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = None
    for i, ln in enumerate(lines):
        if msg_id in ln and ln.startswith("## "):
            start = i
            break
    if start is None:                       # id may sit in the RECAP rather than the header
        for i, ln in enumerate(lines):
            if msg_id in ln:
                for j in range(i, -1, -1):
                    if lines[j].startswith("## "):
                        start = j
                        break
                break
    if start is None:
        return None
    # THE SEAL MUST COVER THE WHOLE ENTRY. This loop ended the body at ANY line starting with
    # "## " - so a markdown H2 anywhere in a body truncated what the digest covers. Measured
    # S109 by the Circle and reproduced independently: an escalation whose `--asking` contained a
    # heading sealed 451 of 1861 chars. BOUNDS, ROUTE, **FOR RAB** and SUGGESTED PROMPT all fell
    # OUTSIDE the seal - the entire block that tells Rab what he is being asked - and rewriting
    # the FOR RAB sentence still confirmed as "digest verified".
    # The trigger is not adversarial: any entry quoting a heading does it by accident.
    # An ENTRY BOUNDARY is a header matching the log's own grammar, not any "## " line.
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if ENTRY_HEADER_RE.match(lines[i]):
            end = i
            break
    return "\n".join(lines[start:end])


# ---------- D2: commitments (a DONE stated on the bus) ----------
#
# PRODUCED SINGLE-LANE by Claude agents (S109). No cross-vendor check: the Codex lane ran out of
# budget, so nothing here was re-derived by a second model. That is a discount on the evidence.
#
# The Disclosure Standard names its own ceiling: "the triggers are enforced by discipline, not by
# code. Only the beat's shape is mechanical." This closes exactly ONE of the six - D2, a broken
# commitment - and only because `**DONE.**` is not prose. It is a DECLARED SLOT of the five-slot
# transaction contract: `escalate` emits it, CR-CDX-0002 clause 2 requires it, and selftest's
# clause-2 census already asserts it appears exactly once in order. Reading it is reading a
# FIELD, not inferring an intent. The other five triggers stay discipline-only, because deciding
# whether a paragraph "is a record-damage disclosure" would be a guesser wearing a guard's badge.
#
# WHAT THIS DOES NOT DO, stated here rather than discovered later:
#   - It never reads the DONE's prose to decide whether it "counts". It prints the clause and
#     lets a human judge. A tool that scored commitments by their wording would be the guesser
#     this design refused to ship.
#   - It never treats an ACK as a discharge. `MSG-FAB-0020` was confirmed by the peer and its
#     deliverable was never produced - that is the specimen the standard was written from. The
#     two columns are computed from different sources and are never collapsed.
#   - It over-reports rather than under-reports. Anything with no explicit discharge record reads
#     OWED, including the 25 entries that predate this ledger. A false OWED costs one command; a
#     false clear costs what MSG-FAB-0020 cost.

ENTRY_HDR_RE = re.compile(r"^## .*⟨from:\s*(\w+)\s*⟩.*⟨msg:\s*(MSG-(?:FAB|CDX)-\d{4})\s*⟩")
# S109 Circle: this was anchored at column 0 (`^\*\*DONE`, re.M), so a DONE inside a list item
# (`- **DONE.** …`) or mid-line (`**GROUND.** … **DONE.** …`) was INVISIBLE. Measured: three
# commitments stated, one seen, `--enforce` exit 0 — while the docstring below claimed the
# function "over-reports rather than under-reports". It did the opposite, and the sentence
# asserting the safe direction was the reason nobody checked.
# Unanchored now, which over-reports (prose mentioning **DONE** counts) — and over-reporting is
# the stated, and correct, bias for a commitment tracker.
DONE_SLOT_RE = re.compile(r"\*\*DONE\b[^\n]*")
_DONE_LEAD_RE = re.compile(r"^\*\*DONE\b[\s.:;—–-]*\*{0,2}[\s.:—–-]*")


def lane_commitments(lane: str):
    """Every entry `lane` posted that carries a DONE slot, oldest first.

    Returns (rows, status). status 'UNREAD' NEVER comes back with a plausible empty list: a log
    that cannot be read is not a lane that owes nothing (S4, and this file's own fail-closed law
    at `open_escalations`)."""
    p = relay_path()
    if not p.exists():
        return [], "UNREAD"
    try:
        text = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return [], "UNREAD"
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    heads = []
    for i, ln in enumerate(lines):
        m = ENTRY_HDR_RE.match(ln)
        if m:
            heads.append((i, m.group(1), m.group(2)))
    rows = []
    for k, (i, frm, mid) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        if frm != lane:
            continue
        m = DONE_SLOT_RE.search("\n".join(lines[i:end]))
        if not m:
            continue
        rows.append({"id": mid, "done": _DONE_LEAD_RE.sub("", m.group(0)).strip()})
    return rows, "ok"


# ---------- commands ----------

def cmd_init(a):
    announce_bus("init")
    p = ack_path(a.as_model)
    if p.exists():
        print(f"already on: {p.name}")
        return 0
    save(a.as_model, blank(a.as_model), a.as_model)
    print(f"relay-gate ON for {a.as_model}: {p.name} created (state idle)")
    print(f"the protocol is LIVE only when BOTH ack files exist and Rab has signed it")
    return 0


# THE STATUS BEAT (S109, Rab: "tell Codex to prompt you as well, in regards of info, status, what
# its doing, planning, completed, verified"). The gate had STATE but no NARRATIVE: `working` never
# said working on WHAT, how far, or what had been PROVED. A peer could see that you were busy and
# nothing else, so it could not plan around you - which is most of what a teammate needs.
#
# `verified` is mechanically expensive on purpose: it REQUIRES --probe. This is the tag law
# (docs/21 §1) made structural rather than aspirational - a verified claim that cannot name the
# command that settled it is not verified, it is inferred wearing a better word.
BEAT_STALE_MIN = 45  # lever-waiver: Rab; moves on a measured beat cadence across sessions (a distribution of real beat intervals), not a guess


def _beat_age_min(beat) -> int:
    if not isinstance(beat, dict) or not beat.get("utc"):
        return -1
    try:
        then = datetime.strptime(beat["utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return -1
    return int((datetime.now(timezone.utc) - then).total_seconds() // 60)


def render_beat(d) -> list:
    """Lines for the board. A missing or unparseable beat is UNREAD - never silence, never idle."""
    b = (d or {}).get("beat")
    if not isinstance(b, dict):
        return ["         beat UNREAD - this lane has published no status beat"]
    age = _beat_age_min(b)
    if age < 0:
        return ["         beat UNREAD - beat present but its timestamp is unreadable"]
    stamp = f"{age}m ago" + ("  *** STALE ***" if age > BEAT_STALE_MIN else "")
    rev = b.get("gate_rev") or UNDECLARED
    mine = gate_rev()
    drift = "" if rev in (mine, UNDECLARED) else f"  *** running {rev}, this shell runs {mine} ***"
    out = [f"         beat {stamp} · gate {rev}{drift}"]
    for k in ("doing", "planning", "blocked", "needs_from_peer"):
        v = b.get(k)
        if v:
            out.append(f"           {k:<16} {v}")
    for c in b.get("completed") or []:
        out.append(f"           completed        {c}")
    for v in b.get("verified") or []:
        out.append(f"           VERIFIED         {v.get('claim')}")
        out.append(f"             probe          {v.get('probe')}")
    return out


def cmd_beat(a):
    announce_bus("beat")
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    if not a.show and not any([a.doing, a.planning, a.completed, a.verified, a.blocked, a.needs]):
        print("REFUSED: a beat with no content is noise. Say at least what you are DOING.",
              file=sys.stderr)
        return 1
    if a.show:
        for ln in render_beat(d):
            print(ln)
        return 0
    if a.verified and not a.probe:
        print("REFUSED: --verified requires --probe. A verified claim that cannot name the "
              "command that settled it is INFERRED wearing a better word (docs/21 §1, the tag "
              "law). Use --completed for work you finished but did not prove.", file=sys.stderr)
        return 1
    if a.verified and len(a.verified) != len(a.probe):
        print(f"REFUSED: {len(a.verified)} --verified claim(s) but {len(a.probe)} --probe(s). "
              f"Each verified claim names its own probe.", file=sys.stderr)
        return 1
    prev = d.get("beat") if isinstance(d.get("beat"), dict) else {}
    d["beat"] = {
        "utc": utc_now(),
        "gate_rev": gate_rev(),          # automatic: a lane cannot forget to declare it

        "doing": a.doing if a.doing is not None else prev.get("doing"),
        "planning": a.planning if a.planning is not None else prev.get("planning"),
        "blocked": a.blocked if a.blocked is not None else prev.get("blocked"),
        "needs_from_peer": a.needs if a.needs is not None else prev.get("needs_from_peer"),
        "completed": a.completed or [],
        "verified": [{"claim": c, "probe": pr} for c, pr in zip(a.verified or [], a.probe or [])],
    }
    save(a.as_model, d, a.as_model)
    print(f"{a.as_model}: beat published")
    for ln in render_beat(d):
        print(ln)
    return 0


def gate_rev() -> str:
    """SHA-8 of the gate.py this process is actually running.

    S109: twice in one evening a lane reasoned about which code its PEER was running and got it
    wrong - once by inferring "your watcher is blind" from "I never posted the fix" (a probe of
    the BUS, rendered as a claim about a PROCESS), and once by a fix landing with no notice at
    all. Nothing on this bus said what code a lane was running, so drift between the lanes was
    invisible by construction. Recorded automatically: a lane cannot forget to declare it, and
    the board shows the two lanes disagreeing without either having to notice.
    """
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8]
    except Exception:
        return UNDECLARED


def cmd_occupant(a):
    """Declare (or read) which model is sitting in this lane. Single-writer, like everything else."""
    announce_bus("occupant")
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    if not a.model:
        print(f"lane {a.as_model} · occupant {occupant_of(d)}")
        return 0
    name = _normalized_occupant(a.model)
    if len(name) < 3:
        print("REFUSED: name the model, not an abbreviation (>=3 chars).", file=sys.stderr)
        return 1
    if not _valid_origin_occupant(name):
        print("REFUSED: occupant must be one normalized line of 3-200 characters.",
              file=sys.stderr)
        return 1
    if name in MODELS:
        print(f"REFUSED: '{name}' is a LANE name, not a model. The occupant is the model in the "
              f"seat (e.g. 'Claude Opus 5', 'OpenAI Codex') — naming the lane here is exactly the "
              f"conflation this field exists to end.", file=sys.stderr)
        return 1
    prev = occupant_of(d)
    d["occupant"] = name
    save(a.as_model, d, a.as_model)
    print(f"lane {a.as_model} · occupant {prev} -> {name}")
    return 0


def _post_request_digest(a, body: str) -> str:
    return _stable_digest({
        "kind": "post", "writer": a.as_model, "to": a.to, "subject": a.subject,
        "body": body, "ticket": a.ticket, "no_ack": bool(a.no_ack),
        "override": a.override, "serves": a.serves,
    })


def _post_entry(a, body: str, msg_id: str, stamp: str) -> str:
    header = f"## {stamp} · ⟨from: {a.as_model}⟩ → ⟨to: {a.to}⟩ · ⟨msg: {msg_id}⟩"
    return header + "\n\n" + body.strip("\n") + "\n"


def _post_row(a, msg_id: str, stamp: str, entry_digest: str) -> dict:
    row = {
        "id": msg_id, "to": a.to, "utc": stamp, "digest": entry_digest,
        "subject": a.subject, "ticket": a.ticket, "requires_ack": not a.no_ack,
    }
    if a.override:
        row["override_reason"] = a.override
    if a.serves:
        row["serves_escalation"] = a.serves
    return row


def _apply_post_sidecar(data: dict, a, row: dict) -> None:
    if any(isinstance(old, dict) and old.get("id") == row["id"] for old in data["sent"]):
        raise SystemExit(f"REFUSED: sidecar already allocates {row['id']} inconsistently")
    data["sent"].append(row)
    if a.ticket:
        data["current_ticket"] = a.ticket
    if not a.no_ack and data.get("state") != "blocked-on-rab":
        data["state"] = "blocked-on-ack"


def cmd_post(a):
    announce_bus("post")
    body = io.open(a.body, encoding="utf-8").read() if a.body != "-" else sys.stdin.read()
    with _relay_transaction_lock():
        return _cmd_post_locked(a, body)


def _cmd_post_locked(a, body):
    data, st = load(a.as_model)
    if st == "UNREAD":
        print(f"UNREAD: {ack_path(a.as_model).name} missing or malformed - run `init` first", file=sys.stderr)
        return 1
    # GUARD A (S108): never issue a NEW ticket into a recipient that is already working.
    # On 2026-08-24 a 90-second-stale board read manufactured a duplicate ticket; the tool now
    # refuses what care did not. Notices always pass (no --ticket, or the ticket they already
    # hold). --override "<reason>" bypasses and RECORDS the reason - never silently.
    # THE FULL STOP IS NOT OVERRIDABLE. This block used to open `if a.ticket and not a.override`,
    # so `--override` - documented in its own help text as "bypass GUARD A (recipient is working)"
    # - silently crossed a halt Rab SIGNED, including its fail-closed UNREAD branch. Measured
    # S109 by the Circle and reproduced: a ticketed post refused by FULL STOP was posted at exit 0
    # with `--override "recipient looked idle to me"`, and the recorded row said only
    # `override_reason`, so nothing on disk showed a signed halt had been crossed.
    # Two different guards were sharing one condition. Guard A protects the PEER'S TURN and a lane
    # may reasonably judge its way past it, on the record. The full stop protects the PRINCIPAL'S
    # UNANSWERED QUESTION, and no model's judgement outranks that - the only ways past it are
    # `--serves` (the narrow carve-out he signed) and `resolve` (his ruling, recorded).
    if a.ticket:
        # FULL STOP first: no NEW work crosses the bus while a question sits with Rab.
        stops, unread = open_escalations()
        # THE CARVE-OUT (S109, Rab signed): "a full stop still permits work that SERVES resolving
        # the open escalation." Without it the stop is self-locking - it blocks the very work that
        # would lift it. Deliberately narrow: --serves must name a ticket that ACTUALLY has an open
        # escalation right now, so it cannot become a general bypass, and the claim is RECORDED on
        # the row. A model asserting "this serves the escalation" is making a claim, and a claim
        # goes on the record or it is not a claim.
        if a.serves and stops and not unread:
            if any(str(e.get("ticket")) == a.serves for _, e in stops):
                pass                                   # permitted, and recorded below
            else:
                print(f"REFUSED: --serves {a.serves} names no OPEN escalation. The carve-out only "
                      f"covers work serving a question actually before Rab.\n"
                      f"  Open now: {', '.join(str(e.get('ticket')) for _, e in stops) or '(none)'}",
                      file=sys.stderr)
                return 1
        elif stops or unread:
            if stops:
                for lane, e in stops:
                    print(f"REFUSED — FULL STOP: {lane} has an open escalation to Rab "
                          f"({e.get('ticket')}): {str(e.get('asking'))[:90]}…", file=sys.stderr)
            if unread:
                # A lane we cannot read cannot be shown to be free of an escalation. Fail closed:
                # this is the same law as "UNREAD is never idle", applied to the halt itself.
                print(f"REFUSED — FULL STOP (fail closed): cannot read {', '.join(unread)}, so no "
                      f"lane can be shown clear of an escalation.", file=sys.stderr)
            if a.override:
                print("  NOTE: --override does NOT lift a FULL STOP. It bypasses GUARD A (the "
                      "peer's turn),\n  which is a lane's judgement to make. This halt is Rab's "
                      "signed rule and is not.", file=sys.stderr)
            print(FULL_STOP_REMEDY, file=sys.stderr)
            return 1
    # GUARD A stays overridable - it protects the peer's turn, not the principal's question.
    if a.ticket and not a.override:
        theirs, st_theirs = load(a.to)
        if st_theirs == "ok" and theirs.get("state") == "working":
            held = theirs.get("current_ticket")
            if held is None:
                # GUARD A used to compare against a field NOTHING automatically maintained, so a
                # stale or empty current_ticket made it both false-refuse and false-allow (found
                # S109, when Rab asked "t-005 you mean?" and this lane had read T-003 for three
                # tickets running). A working lane that will not say what it holds is UNREAD.
                print(f"REFUSED: {a.to} is working but names no current ticket — its state cannot "
                      f"be compared to {a.ticket}, so this fails closed.\n"
                      f"  Ask it to run `gate.py ticket --as {a.to} --id <id> --state working`, "
                      f"post without --ticket, or re-issue with --override \"<reason>\".",
                      file=sys.stderr)
                return 1
            if held != a.ticket:
                print(f"REFUSED: {a.to} is working on {held} — issuing {a.ticket} "
                      f"now would duplicate or interrupt.\n"
                      f"  Wait for its delivery · post without --ticket (a notice always passes) · "
                      f"or re-issue with --override \"<reason>\".", file=sys.stderr)
                return 1

    request_digest = _post_request_digest(a, body)
    intent, intent_status = _read_append_intent()
    recovered = False
    if intent_status != "absent":
        if intent_status != "ok":
            print("REFUSED: transaction journal is malformed or UNREAD; reconcile it first",
                  file=sys.stderr)
            return 1
        if (intent.get("kind") != "post" or intent.get("writer") != a.as_model
                or intent.get("request_digest") != request_digest):
            print("REFUSED: conflicting retry while another append transaction is pending",
                  file=sys.stderr)
            return 1
        mid, now = intent["msg_id"], intent["stamp"]
        entry = _post_entry(a, body, mid, now)
        if digest(entry) != intent["entry_digest"]:
            print("REFUSED: retry does not reconstruct the pending post bytes", file=sys.stderr)
            return 1
        relay_state, detail = _intent_relay_state(intent)
        expected_row = _post_row(a, mid, now, intent["entry_digest"])
        if data.get(_LOADED_REVISION) != intent["expected_revision"]:
            if (relay_state == "published"
                    and len([row for row in data.get("sent", []) if row == expected_row]) == 1):
                _finish_append_intent("post", a.as_model, mid)
                print(f"already posted {mid}; cleared completed transaction journal")
                return 0
            print("REFUSED: writer sidecar changed after the pending post; no overwrite",
                  file=sys.stderr)
            return 1
        if relay_state == "pre-append":
            dg = _append_relay_locked(
                entry, mid, kind="post", request_digest=request_digest,
                expected_revision=intent["expected_revision"], resume=True,
            )
        elif relay_state == "published":
            dg = intent["entry_digest"]
        else:
            print(f"REFUSED: pending post relay state is {relay_state}: {detail}",
                  file=sys.stderr)
            return 1
        recovered = True
    else:
        mid = next_id(a.as_model, data)
        now = utc_now()
        entry = _post_entry(a, body, mid, now)
        dg = _append_relay_locked(
            entry, mid, kind="post", request_digest=request_digest,
            expected_revision=data[_LOADED_REVISION],
        )
    row = _post_row(a, mid, now, dg)
    _apply_post_sidecar(data, a, row)
    # Keep current_ticket TRUE (S109). Only `ticket` used to write this field, so `post --ticket`
    # never advanced it: this lane read T-003 through T-004, T-005 and T-006, and the board
    # printed that stale value to Rab with confidence. Guard A compares against it, so the
    # staleness was not cosmetic - it made the guard misfire both ways.
    # GUARD B, second half (S108): posting must never DOWNGRADE blocked-on-rab. The original
    # guard stopped a model ENTERING that state silently; nothing stopped it LEAVING by side
    # effect. Found 2026-08-24 while about to post during a live escalation.
    _save_locked(a.as_model, data, a.as_model, allow_pending=True)
    if (os.environ.get("FP_COORD")
            and os.environ.get("FP_GATE_TEST_CRASH_AFTER_SIDECAR") in ("post", "all")):
        os._exit(88)
    _finish_append_intent("post", a.as_model, mid)
    verb = "recovered and posted" if recovered else "posted"
    print(f"{verb} {mid} -> {a.to}  digest {dg[:19]}…  state={data['state']}")
    return 0


def cmd_inbox(a):
    mine, st_mine = load(a.as_model)
    theirs, st_theirs = load(other(a.as_model))
    if st_theirs == "UNREAD":
        print(f"UNREAD: {ack_path(other(a.as_model)).name} - {other(a.as_model)} has not turned the skill on")
        return 0
    done = {c["id"] for c in (mine or {}).get("confirmed", [])}
    pending = [s for s in theirs["sent"] if s.get("to") == a.as_model and s.get("requires_ack") and s["id"] not in done]
    if not pending:
        print("inbox empty - nothing awaiting your confirmation")
        return 0
    for s in pending:
        print(f"  {s['id']}  {s['utc']}  ticket={s.get('ticket')}  {s.get('subject','')}")
    return 0


def cmd_confirm(a):
    announce_bus("confirm")
    mine, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    if not a.restatement or len(a.restatement.strip()) < 10:
        print("REFUSED: a confirmation requires a RESTATEMENT of the ask (>=10 chars). "
              "A bit can be flipped without reading; a restatement cannot.", file=sys.stderr)
        return 1
    body = extract_entry(a.id)
    if body is None:
        print(f"REFUSED: {a.id} is not in {relay_path().name}", file=sys.stderr)
        return 1
    mine_dg = digest(body)
    theirs, st_theirs = load(other(a.as_model))
    claimed = None
    if st_theirs == "ok":
        for s in theirs["sent"]:
            if s["id"] == a.id:
                claimed = s.get("digest")
    # NO CLAIM IS NOT A MATCH. `claimed` is None when the peer's sidecar is UNREAD or carries no
    # row for this id, and the comparison below used to be guarded by `if claimed and ...` - so a
    # missing claim SKIPPED the check and fell through to printing "digest verified".
    # Measured S109 by the Circle and reproduced: with the sender's sidecar corrupted, an entry
    # rewritten from "convert the bundle" to "DELETE the bundle" confirmed at exit 0 as VERIFIED.
    # That is the exact condition law 4 exists to catch, rendering as a healthy state - and this
    # command refuses an unprobed `--verified` on the beat while doing it here itself.
    if claimed is None:
        print(f"REFUSED: no digest claim for {a.id} — {other(a.as_model)}'s sidecar reads "
              f"{st_theirs.upper() if st_theirs != 'ok' else 'ok but has no row for it'}, so "
              f"there is NOTHING TO COMPARE.\n"
              f"  A confirmation with no counter-claim is not a verification; it is a bit flip.\n"
              f"  Re-read the board (`gate.py status`); if the peer's sidecar is broken that is "
              f"the finding, not this entry.", file=sys.stderr)
        return 1
    if claimed != mine_dg:
        print(f"RED: digest mismatch on {a.id}\n  sender claimed {claimed}\n  log reads      {mine_dg}\n"
              "  the entry changed after posting, or the wrong bytes were read. Post the mismatch "
              "to the log; do not confirm.", file=sys.stderr)
        return 1
    if any(c["id"] == a.id for c in mine["confirmed"]):
        print(f"already confirmed: {a.id}")
        return 0
    mine["confirmed"].append({
        "id": a.id, "from": other(a.as_model), "digest": mine_dg,
        "confirmed_utc": utc_now(), "restatement": a.restatement.strip(),
    })
    save(a.as_model, mine, a.as_model)
    print(f"confirmed {a.id}  digest verified {mine_dg[:19]}…")
    return 0


def cmd_check(a):
    mine, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first")
        return 0
    theirs, st_theirs = load(other(a.as_model))
    if st_theirs == "UNREAD":
        print(f"UNREAD: {other(a.as_model)} has no ack file - the protocol is not two-party yet")
        return 0
    conf = {c["id"]: c for c in theirs["confirmed"]}
    waiting = 0
    for s in mine["sent"]:
        if not s.get("requires_ack"):
            continue
        c = conf.get(s["id"])
        if not c:
            print(f"  AWAITING  {s['id']}  {s.get('subject','')}")
            waiting += 1
        elif c["digest"] != s["digest"]:
            print(f"  RED       {s['id']}  digest mismatch in their confirmation")
            return 1
        else:
            print(f"  CONFIRMED {s['id']}  \"{c['restatement'][:70]}\"")
    # GUARD B, third path (S109): a QUERY may not change what only Rab may change. The second
    # half was patched into `post` alone; `check` still assigned blocked-on-ack over
    # blocked-on-rab whenever anything awaited an ACK - so merely asking "did mine land?"
    # cleared his gate. Found by running it during the live T-005 escalation: the decision
    # queue survived, the state field did not. Same family as SYM-042/047/049 - a guard
    # cannot cover a path it was not born on.
    if mine["state"] == "blocked-on-rab":
        new_state = "blocked-on-rab"
    else:
        new_state = "blocked-on-ack" if waiting else ("idle" if mine["state"] == "blocked-on-ack" else mine["state"])
    if new_state != mine["state"]:
        mine["state"] = new_state
        save(a.as_model, mine, a.as_model)
        print(f"  state -> {new_state}" + ("  (settled)" if new_state == "idle" else ""))
    return 0


def cmd_status(a):
    with _relay_transaction_lock():
        return _cmd_status_locked(a)


def _cmd_status_locked(a):
    print(f"relay-gate board · {utc_now()}")
    boards = {model: load(model) for model in MODELS}
    lanes = {model: data for model, (data, status) in boards.items() if status == "ok"}
    invalid_terminal = False
    invalid_intent = False
    for m in MODELS:
        d, st = boards[m]
        if st == "UNREAD":
            print(f"  {m:<6} UNREAD (skill not on, or file malformed)")
            continue
        print(f"  {m:<6} state={d['state']:<15} ticket={d.get('current_ticket')}  "
              f"sent={len(d['sent'])} confirmed={len(d['confirmed'])}  updated={d['updated_utc']}")
        print(f"         lane {m} · occupant {occupant_of(d)}")
        for ln in render_beat(d):
            print(ln)
        for record in d.get("disagreements", []):
            if not isinstance(record, dict):
                print("         RED INVALID DISAGREEMENT — structured record is not an object")
                invalid_terminal = True
                continue
            if len(lanes) != len(MODELS):
                print(f"         UNREAD DISAGREEMENT {record.get('id', 'UNREAD')} — "
                      "both sidecars are required for terminal verification")
                invalid_terminal = True
                continue
            verified, classification, detail = _verify_terminal_record(m, record, lanes)
            if not verified:
                print(f"         {classification} INVALID DISAGREEMENT "
                      f"{record.get('id', 'UNREAD')} — {detail}")
                invalid_terminal = True
                continue
            print(f"         PRESERVED DISAGREEMENT {record.get('id', 'UNREAD')} · "
                  f"terminal={record.get('terminal_msg_id', 'UNREAD')}")
            print(f"           origin occupant  {record.get('origin_occupant', 'UNREAD')}")
            if record.get("adopter_occupant"):
                print(f"           adopted by       {record.get('adopter_occupant')} · "
                      f"{record.get('adopted_utc', 'UNREAD')}")
            print(f"           consequence      {record.get('consequence', 'UNREAD')}")
            for action in record.get("prohibited_actions", []) or []:
                print(f"           PROHIBITED       {action}")
    journal_escalation = None
    intent, intent_status = _read_append_intent()
    if intent_status not in ("absent", "ok"):
        print(f"  {intent_status} TRANSACTION JOURNAL — malformed or unreadable; "
              "the board cannot be shown calm")
        invalid_intent = True
    elif intent_status == "ok":
        relay_state, detail = _intent_relay_state(intent)
        actor, actor_status = boards.get(intent["writer"], (None, "UNREAD"))
        sent = [] if actor_status != "ok" else [
            row for row in actor.get("sent", []) if isinstance(row, dict)
            and row.get("id") == intent["msg_id"]
            and row.get("digest") == intent["entry_digest"]
        ]
        structured = True
        if intent["kind"] == "escalation" and actor_status == "ok":
            structured = len([row for row in actor.get("escalations", [])
                              if isinstance(row, dict)
                              and row.get("msg_id") == intent["msg_id"]]) == 1
        elif intent["kind"] == "disagreement" and actor_status == "ok":
            structured = len([row for row in actor.get("disagreements", [])
                              if isinstance(row, dict)
                              and row.get("terminal_msg_id") == intent["msg_id"]]) == 1
        complete = relay_state == "published" and len(sent) == 1 and structured
        if relay_state == "pre-append":
            label = "PENDING BEFORE RELAY APPEND"
        elif complete:
            label = "UNCLEARED AFTER SIDECAR PUBLICATION"
        elif relay_state == "published":
            label = "ORPHAN RELAY APPEND — SIDECAR EFFECT ABSENT"
        else:
            label = f"{relay_state} TRANSACTION"
        print(f"  RED {intent['kind'].upper()} {label}: {intent['msg_id']} — {detail}")
        if intent["kind"] == "post":
            print("      delivery, blocked-on-ack, and current-ticket state are NOT proven")
        invalid_intent = True
        if intent["kind"] == "escalation":
            journal_escalation = (intent["writer"], {
                "ticket": intent["msg_id"],
                "asking": "unreconciled escalation transaction journal",
                "msg_id": intent["msg_id"], "state": "open",
            })
    pending = []
    for m in MODELS:
        d, st = boards[m]
        if st == "ok":
            pending += [(m, e) for e in d.get("escalations", []) if e.get("state") == "open"]
    if journal_escalation and not any(
            e.get("msg_id") == journal_escalation[1]["msg_id"] for _, e in pending):
        pending.append(journal_escalation)
    if pending:
        # ASCII only on this line. `status` is piped, and on Windows a pipe decodes as cp1252:
        # an emoji here raised UnicodeEncodeError and took the WHOLE BOARD down - the banner
        # announcing the halt was the thing that crashed the halt's own display. Caught by T34.
        print("\n  *** FULL STOP - BOTH LANES HALTED (Rab's rule, S109) ***")
        print("     An open escalation halts every lane, not just the escalator's. No lane may")
        print("     start work or issue a new ticket. Notices still pass, so each lane can say")
        print("     that it has stopped. Only Rab's ruling, recorded with `resolve`, lifts this.")
        print("     RAB: rule on the item(s) below, then PROMPT THE RELAY GATES AGAIN.")
        print("\n  AWAITING RAB — his decision queue:")
        for m, e in pending:
            print(f"    [{e.get('ticket')}] from {m}: {e['asking']}")
            if e.get("why"):
                print(f"       why not settled between us: {e['why']}")
    return 1 if invalid_terminal or invalid_intent else 0


def cmd_ticket(a):
    announce_bus("ticket")
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    # GUARD B (S108, Rab's rule): you may not go to Rab silently. Entering blocked-on-rab
    # requires an ANNOUNCED escalation - the peer learns what he is being asked, and why,
    # before he is asked. No back-channel to the principal.
    if a.state == "blocked-on-rab":
        if not [e for e in d.get("escalations", []) if e.get("state") == "open"]:
            print("REFUSED: blocked-on-rab requires an announced escalation.\n"
                  "  run: gate.py escalate --as <you> --asking \"<what Rab must decide>\" "
                  "[--why \"<why we cannot settle it>\"]", file=sys.stderr)
            return 1
    # FULL STOP (S109): a lane may not pick up WORK while a question sits with Rab. It may still
    # move to blocked-on-* or idle - stopping is always allowed, starting is not.
    if a.state == "working":
        stops, unread = open_escalations()
        # Same carve-out as post: a lane may enter `working` during a stop ONLY to serve the
        # open escalation, and only when --serves names one that is actually open.
        if getattr(a, "serves", None) and stops and not unread \
                and any(str(e.get("ticket")) == a.serves for _, e in stops):
            stops, unread = [], []
        if stops or unread:
            for lane, e in stops:
                print(f"REFUSED — FULL STOP: {lane} has an open escalation to Rab "
                      f"({e.get('ticket')}). No lane starts work while it is open.", file=sys.stderr)
            if unread:
                print(f"REFUSED — FULL STOP (fail closed): cannot read {', '.join(unread)}.",
                      file=sys.stderr)
            print(FULL_STOP_REMEDY, file=sys.stderr)
            return 1
    d["current_ticket"] = None if a.id.lower() in ("none", "-", "clear") else a.id
    d["state"] = a.state
    save(a.as_model, d, a.as_model)
    print(f"{a.as_model}: ticket={d['current_ticket']} state={d['state']}")
    return 0


def cmd_escalate(a):
    """Announce to the peer that you are going to Rab, THEN block on him.

    Rab's rule, 2026-08-24: 'when you want to come to me, let each other know as protocol.'
    The peer always learns what the principal is being asked, and why, before he is asked."""
    announce_bus("escalate")
    with _relay_transaction_lock():
        return _cmd_escalate_locked(a)


def _cmd_escalate_locked(a):
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    if len(a.asking.strip()) < 15:
        print("REFUSED: name what Rab must decide, in a sentence (>=15 chars).", file=sys.stderr)
        return 1
    peer = other(a.as_model)
    ticket = a.ticket or d.get("current_ticket")
    trailer = occupant_of(d)
    # CR-CDX-0002 COMPLIANCE (Rab signed 2026-08-24: "I sign it", with the repair as a stated
    # condition). The old template emitted RECAP and FOR RAB and nothing else - no SUGGESTED
    # PROMPT (clause 1) and none of the five inner slots (clause 2), despite requires_ack=True.
    # Measured on MSG-FAB-0009, which is the escalation that ASKED HIM TO SIGN THIS VERY CARD:
    # six required elements missing across two clauses. Both models had endorsed the contract
    # without ever running it against the artifact - SYM-001 at the level of review.
    why = a.why.strip() if a.why else "(not stated)"
    body = (
        f"**RECAP — ESCALATION: a decision is going to Rab.**\n\n"
        f"**GROUND.** ⟨claimed: {a.as_model} lane · occupant: {trailer}⟩ Ticket **{ticket}**. "
        f"Announced to {peer} **before** Rab is asked — there is no back-channel to the "
        f"principal. Why this cannot be settled between the models: {why}\n\n"
        f"**ASK.** Rab, and Rab alone, decides exactly one thing: {a.asking.strip()}\n\n"
        f"**DONE.** Complete when Rab states his decision and it is recorded with `resolve`. "
        f"My state is `blocked-on-rab`, which **no model may clear** — not by file, not by "
        f"checkbox, not by inference. An approval artifact's presence proves nothing.\n\n"
        f"**BOUNDS.** This entry signs nothing, adopts nothing, starts no work, and moves no "
        f"other ticket. It records a question; it does not answer one. While it is open, "
        f"FULL STOP halts **both** lanes: no new ticket crosses the bus and no lane enters "
        f"`working`. Notices always pass, and work that SERVES this escalation may cross with "
        f"`--serves {ticket}`.\n\n"
        f"**ROUTE.** {peer} may verify every cited byte from the repo and should correct this "
        f"entry rather than escalate alongside it. Only the decision itself is Rab's; anything "
        f"factual still settles between the lanes at measurement.\n\n"
        f"**FOR RAB.** {a.as_model} says: a decision is queued for you and both lanes are "
        f"stopped until you make it. Run `gate.py status` to see it, decide, and then prompt "
        f"the relay gates again.\n\n"
        f"**SUGGESTED PROMPT** (for Rab to give either model): *\"Rule on {ticket}: "
        f"{a.asking.strip()[:120]}{'…' if len(a.asking.strip()) > 120 else ''} — then prompt "
        f"the relay gates again.\"*\n\n"
        f"Lane `{a.as_model}` · occupant `{trailer}` — the lane is a seat, the occupant is the "
        f"model in it, and they are not the same claim. Authorship only, never Rab's authority.\n"
    )
    request_digest = _stable_digest({
        "kind": "escalation", "writer": a.as_model, "asking": a.asking.strip(),
        "why": (a.why or "").strip() or None, "ticket": ticket,
        "origin_occupant": trailer,
    })
    intent, intent_status = _read_append_intent()
    recovered = False
    if intent_status != "absent":
        if intent_status != "ok":
            print("REFUSED: transaction journal is malformed or UNREAD; reconcile it first",
                  file=sys.stderr)
            return 1
        if (intent.get("kind") != "escalation" or intent.get("writer") != a.as_model
                or intent.get("request_digest") != request_digest):
            print("REFUSED: conflicting retry while another append transaction is pending",
                  file=sys.stderr)
            return 1
        mid, now = intent["msg_id"], intent["stamp"]
    else:
        mid, now = next_id(a.as_model, d), utc_now()
    header = f"## {now} · ⟨from: {a.as_model}⟩ → ⟨to: {peer}⟩ · ⟨msg: {mid}⟩"
    entry = header + "\n\n" + body
    sent_row = {"id": mid, "to": peer, "utc": now, "digest": digest(entry),
                "subject": "ESCALATION: " + a.asking.strip()[:60], "ticket": ticket,
                "requires_ack": True}
    escalation_row = {"utc": now, "ticket": ticket, "asking": a.asking.strip(),
                      "why": (a.why or "").strip() or None, "msg_id": mid, "state": "open"}
    if intent_status == "ok":
        if digest(entry) != intent["entry_digest"]:
            print("REFUSED: retry does not reconstruct the pending escalation bytes",
                  file=sys.stderr)
            return 1
        relay_state, detail = _intent_relay_state(intent)
        if d.get(_LOADED_REVISION) != intent["expected_revision"]:
            if (relay_state == "published" and sent_row in d.get("sent", [])
                    and escalation_row in d.get("escalations", [])):
                _finish_append_intent("escalation", a.as_model, mid)
                print(f"already escalated {mid}; cleared completed transaction journal")
                return 0
            print("REFUSED: writer sidecar changed after the pending escalation; no overwrite",
                  file=sys.stderr)
            return 1
        if relay_state == "pre-append":
            dg = _append_relay_locked(
                entry, mid, kind="escalation", request_digest=request_digest,
                expected_revision=intent["expected_revision"], resume=True,
            )
        elif relay_state == "published":
            dg = intent["entry_digest"]
        else:
            print(f"REFUSED: pending escalation relay state is {relay_state}: {detail}",
                  file=sys.stderr)
            return 1
        recovered = True
    else:
        dg = _append_relay_locked(
            entry, mid, kind="escalation", request_digest=request_digest,
            expected_revision=d[_LOADED_REVISION],
        )
    sent_row["digest"] = dg
    d["sent"].append(sent_row)
    d["escalations"].append(escalation_row)
    d["state"] = "blocked-on-rab"
    _save_locked(a.as_model, d, a.as_model, allow_pending=True)
    if (os.environ.get("FP_COORD")
            and os.environ.get("FP_GATE_TEST_CRASH_AFTER_SIDECAR")
            in ("escalation", "all")):
        os._exit(88)
    _finish_append_intent("escalation", a.as_model, mid)
    verb = "recovered and escalated" if recovered else "escalated"
    print(f"{verb} {mid} -> {peer}   state=blocked-on-rab")
    print(f"  asking Rab: {a.asking.strip()}")
    return 0


def cmd_preserve_disagreement(a):
    """Terminate a complete two-round disagreement without changing any other blocker."""
    if not DISAGREEMENT_ID_RE.fullmatch(a.id or ""):
        print("REFUSED: --id must be an uppercase durable id such as DIS-001", file=sys.stderr)
        return 1
    consequence = " ".join((a.consequence or "").split())
    prohibited = [" ".join(value.split()) for value in (a.prohibits or [])]
    if not consequence:
        print("REFUSED: --consequence must name the unresolved consequence", file=sys.stderr)
        return 1
    if not prohibited or any(not value for value in prohibited):
        print("REFUSED: provide one or more nonempty --prohibits actions", file=sys.stderr)
        return 1
    if len(set(prohibited)) != len(prohibited):
        print("REFUSED: prohibited actions must be distinct", file=sys.stderr)
        return 1

    with _relay_transaction_lock():
        return _cmd_preserve_disagreement_locked(a, consequence, prohibited)


def _cmd_preserve_disagreement_locked(a, consequence, prohibited):
    """Lock-held validation, allocation, append, and sidecar publication."""

    lanes = {}
    for lane in MODELS:
        data, status = load(lane)
        if status != "ok":
            print(f"REFUSED: {lane} sidecar is UNREAD; silence is not disagreement and an "
                  "unresponsive close needs separate authority", file=sys.stderr)
            return 1
        lanes[lane] = data
    try:
        messages, entries = _validate_disagreement_chain(a.round1, a.round2, lanes)
    except ValueError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    base_payload = {
        "id": a.id,
        "messages": messages,
        "consequence": consequence,
        "prohibited_actions": prohibited,
    }
    existing = []
    for lane, data in lanes.items():
        for record in data.get("disagreements", []):
            if isinstance(record, dict) and record.get("id") == a.id:
                existing.append((lane, record))
    bus_markers = []
    for entry in entries:
        for marker in DISAGREEMENT_MARKER_RE.finditer(entry["text"]):
            if marker.group("id") == a.id:
                bus_markers.append(entry)
    sent_markers = []
    for lane, data in lanes.items():
        for row in data.get("sent", []):
            if row.get("disagreement_id") == a.id:
                sent_markers.append((lane, row))
    if existing:
        if len(existing) != 1:
            print(f"REFUSED: conflicting disagreement id {a.id}", file=sys.stderr)
            return 1
        owner, record = existing[0]
        verified, classification, detail = _verify_terminal_record(owner, record, lanes)
        if not verified:
            print(f"REFUSED: {a.id} terminal record is {classification}: {detail}",
                  file=sys.stderr)
            return 1
        origin = record.get("origin_occupant")
        payload = dict(base_payload, origin_occupant=origin)
        request_digest = _stable_digest(payload)
        if record.get("request_digest") != request_digest:
            print(f"REFUSED: conflicting disagreement id {a.id}", file=sys.stderr)
            return 1
        intent, intent_status = _read_append_intent()
        if intent_status != "absent":
            if (intent_status != "ok" or intent.get("kind") != "disagreement"
                    or intent.get("writer") != a.as_model
                    or intent.get("msg_id") != record.get("terminal_msg_id")
                    or intent.get("request_digest") != request_digest):
                print("REFUSED: conflicting or malformed transaction journal", file=sys.stderr)
                return 1
            _finish_append_intent("disagreement", a.as_model, intent["msg_id"])
        print(f"already preserved: {a.id} ({record.get('terminal_msg_id')})")
        print("DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED")
        return 0
    if bus_markers:
        # Bus-first process-crash recovery. The canonical request, origin, global id uniqueness,
        # and absence of every structured allocation must all agree before a fresh caller adopts.
        if len(bus_markers) != 1 or sent_markers:
            print(f"REFUSED: {a.id} has a malformed or partial orphan terminal record",
                  file=sys.stderr)
            return 1
        orphan = bus_markers[0]
        origin = _origin_occupant(orphan["text"])
        if origin is None:
            print(f"REFUSED: orphan {a.id} has missing or malformed origin occupant",
                  file=sys.stderr)
            return 1
        try:
            messages, entries = _validate_disagreement_chain(
                a.round1, a.round2, lanes, terminal_utc=orphan["utc"])
        except ValueError as error:
            print(f"REFUSED: orphan {a.id} source chain is invalid: {error}", file=sys.stderr)
            return 1
        payload = dict(base_payload, messages=messages, origin_occupant=origin)
        request_digest = _stable_digest(payload)
        raw_request = _slot(orphan["text"], "REQUEST DIGEST")
        request_match = re.fullmatch(r"`?(sha256:[0-9a-f]{64})`?", raw_request or "")
        relay_id_hits = [entry for entry in entries if entry["id"] == orphan["id"]]
        terminal_stamp_count, terminal_stamp_status = _relay_id_stamp_count(orphan["id"])
        id_refs = _message_id_references(lanes, orphan["id"])
        expected_entry = _terminal_disagreement_entry(
            a.as_model, orphan["id"], orphan["utc"], payload
        )
        if (orphan["from"] != a.as_model or orphan["to"] != other(a.as_model)
                or len(relay_id_hits) != 1
                or terminal_stamp_status != "ok" or terminal_stamp_count != 1 or id_refs
                or not request_match or request_match.group(1) != request_digest
                or digest(orphan["text"]) != digest(expected_entry)):
            print(f"REFUSED: orphan {a.id} conflicts with this request or is not canonical",
                  file=sys.stderr)
            return 1
        actor = lanes[a.as_model]
        intent, intent_status = _read_append_intent()
        if intent_status != "absent":
            if (intent_status != "ok" or intent.get("kind") != "disagreement"
                    or intent.get("writer") != a.as_model or intent.get("msg_id") != orphan["id"]
                    or intent.get("request_digest") != request_digest
                    or intent.get("expected_revision") != actor.get(_LOADED_REVISION)):
                print("REFUSED: orphan conflicts with the pending transaction journal",
                      file=sys.stderr)
                return 1
        blockers_guard = _blockers_fingerprint(actor)
        adopter = _normalized_occupant(occupant_of(actor))
        adopted_utc = utc_now() if adopter != origin else None
        try:
            adoption_sources, _ = _validate_disagreement_chain(
                a.round1, a.round2, lanes, terminal_utc=orphan["utc"])
        except ValueError as error:
            print(f"REFUSED: orphan {a.id} source chain changed before adoption: {error}",
                  file=sys.stderr)
            return 1
        if adoption_sources != messages:
            print(f"REFUSED: orphan {a.id} source chain changed before adoption",
                  file=sys.stderr)
            return 1
        _record_terminal_disagreement(
            actor, a.as_model, payload, orphan["id"], orphan["utc"],
            digest(orphan["text"]),
            adopter_occupant=adopter if adopter != origin else None,
            adopted_utc=adopted_utc,
        )
        if _blockers_fingerprint(actor) != blockers_guard:
            print("REFUSED: internal blocker-preservation guard fired", file=sys.stderr)
            return 1
        _save_locked(a.as_model, actor, a.as_model, allow_pending=True)
        if (os.environ.get("FP_COORD")
                and os.environ.get("FP_GATE_TEST_CRASH_AFTER_SIDECAR")
                in ("disagreement", "all")):
            os._exit(88)
        if intent_status == "ok":
            _finish_append_intent("disagreement", a.as_model, orphan["id"])
        print(f"adopted orphan {a.id} from {orphan['id']} without a second append")
        print("DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED")
        return 0

    # Re-read and revalidate the cited chain under the transaction immediately before append.
    # The structured source digests bind the exact relay bytes that passed this final validation.
    try:
        messages, entries = _validate_disagreement_chain(a.round1, a.round2, lanes)
    except ValueError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    if any(marker.group("id") == a.id for entry in entries
           for marker in DISAGREEMENT_MARKER_RE.finditer(entry["text"])):
        print(f"REFUSED: {a.id} appeared during validation; retry from fresh state",
              file=sys.stderr)
        return 1
    actor = lanes[a.as_model]
    origin = _normalized_occupant(occupant_of(actor))
    if not _valid_origin_occupant(origin):
        print("REFUSED: current origin occupant is malformed", file=sys.stderr)
        return 1
    payload = {
        "id": a.id,
        "messages": messages,
        "consequence": consequence,
        "prohibited_actions": prohibited,
        "origin_occupant": origin,
    }
    blockers_guard = _blockers_fingerprint(actor)
    request_digest = _stable_digest(payload)
    intent, intent_status = _read_append_intent()
    resume = False
    if intent_status != "absent":
        if (intent_status != "ok" or intent.get("kind") != "disagreement"
                or intent.get("writer") != a.as_model
                or intent.get("request_digest") != request_digest
                or intent.get("expected_revision") != actor.get(_LOADED_REVISION)):
            print("REFUSED: conflicting or malformed transaction journal", file=sys.stderr)
            return 1
        relay_state, detail = _intent_relay_state(intent)
        if relay_state != "pre-append":
            print(f"REFUSED: pending disagreement relay state is {relay_state}: {detail}",
                  file=sys.stderr)
            return 1
        mid, now, resume = intent["msg_id"], intent["stamp"], True
    else:
        now, mid = utc_now(), next_id(a.as_model, actor)
    if _message_id_references(lanes, mid):
        print(f"REFUSED: allocated id {mid} conflicts with a structured sidecar record",
              file=sys.stderr)
        return 1
    # `now` is the proposed terminal boundary. Revalidate every receipt against it under the
    # transaction immediately before constructing and appending the canonical disposition.
    try:
        terminal_messages, entries = _validate_disagreement_chain(
            a.round1, a.round2, lanes, terminal_utc=now)
    except ValueError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    if any(marker.group("id") == a.id for entry_row in entries
           for marker in DISAGREEMENT_MARKER_RE.finditer(entry_row["text"])):
        print(f"REFUSED: {a.id} appeared during terminal validation; retry from fresh state",
              file=sys.stderr)
        return 1
    terminal_payload = dict(payload, messages=terminal_messages)
    terminal_request_digest = _stable_digest(terminal_payload)
    if terminal_request_digest != request_digest:
        print("REFUSED: cited chain changed before terminal append; retry from fresh state",
              file=sys.stderr)
        return 1
    messages, payload, request_digest = (
        terminal_messages, terminal_payload, terminal_request_digest)
    entry = _terminal_disagreement_entry(a.as_model, mid, now, payload)
    terminal_digest = digest(entry)

    announce_bus("preserve-disagreement")
    published_digest = _append_relay_locked(
        entry, mid, kind="disagreement", request_digest=request_digest,
        expected_revision=actor[_LOADED_REVISION], resume=resume,
    )
    if published_digest != terminal_digest:
        raise SystemExit(f"RED: canonical terminal digest changed while publishing {mid}")
    try:
        published_sources, _ = _validate_disagreement_chain(
            a.round1, a.round2, lanes, terminal_utc=now)
    except ValueError as error:
        raise SystemExit(
            f"RED: cited chain changed during terminal publication ({error}); {mid} remains "
            "an unadopted bus marker, not a structured disposition"
        )
    if published_sources != messages:
        raise SystemExit(
            f"RED: cited source chain changed during terminal publication; {mid} remains "
            "an unadopted bus marker, not a structured disposition"
        )
    _record_terminal_disagreement(actor, a.as_model, payload, mid, now, terminal_digest)
    if _blockers_fingerprint(actor) != blockers_guard:
        print("REFUSED: internal blocker-preservation guard fired", file=sys.stderr)
        return 1
    _save_locked(a.as_model, actor, a.as_model, allow_pending=True)
    if (os.environ.get("FP_COORD")
            and os.environ.get("FP_GATE_TEST_CRASH_AFTER_SIDECAR")
            in ("disagreement", "all")):
        os._exit(88)
    _finish_append_intent("disagreement", a.as_model, mid)
    print(f"preserved {a.id} as {mid}")
    print("DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED")
    return 0


def cmd_resolve(a):
    """Record Rab's decision on an open escalation. This is a TRANSCRIPT, not authority:
    writing it here does not make it his, and no gate may treat it as proof."""
    announce_bus("resolve")
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    hit = [e for e in d["escalations"] if e.get("msg_id") == a.id and e.get("state") == "open"]
    if not hit:
        print(f"REFUSED: no OPEN escalation with msg id {a.id}", file=sys.stderr)
        return 1
    if len(a.decision.strip()) < 10:
        print("REFUSED: record what he decided, in his terms (>=10 chars).", file=sys.stderr)
        return 1
    hit[0]["state"] = "resolved"
    hit[0]["decision"] = a.decision.strip()
    hit[0]["resolved_utc"] = utc_now()
    d["state"] = "idle"
    save(a.as_model, d, a.as_model)
    print(f"resolved {a.id} — recorded: \"{a.decision.strip()[:70]}\"   state=idle")
    return 0


OWED_CEILING = (
    "  This is D2 only. The other five triggers remain enforced by discipline, not by code.\n"
    "  OWED means THE RECORD CONTAINS NO REPORT OF THE OUTCOME. It does not mean the work was\n"
    "  not done - it means the bus cannot show that it was, which is the disclosure D2 names.\n"
    "  Discharge is an ACT, never an inference: gate.py discharge --as <lane> --id <msg>\n"
    "    --in <a LATER message of yours that reports it> --outcome \"<what actually happened>\"\n"
    "  PRODUCED SINGLE-LANE by Claude agents - no cross-vendor check (the Codex lane is out of\n"
    "  budget). Discount the evidence accordingly."
)


def cmd_owed(a):
    """D2 made mechanical: every DONE this lane stated on the bus, and whether the record
    reports its outcome.

    The two columns come from DIFFERENT sources and are never collapsed into one verdict:
      ack     - did the PEER confirm reading the entry (peer sidecar `confirmed`)
      outcome - does MY sidecar carry an explicit discharge record for it
    Conflating them is the exact defect this exists to surface. `MSG-FAB-0020` was confirmed by
    the peer and its deliverable was never produced; a tool that read the ACK as the discharge
    would have rendered that specimen CLEAN.
    """
    lane = a.as_model
    commits, cst = lane_commitments(lane)
    mine, mst = load(lane)
    if cst == "UNREAD" or mst == "UNREAD":
        bad = ["relay.md"] if cst == "UNREAD" else []
        if mst == "UNREAD":
            bad.append(ack_path(lane).name)
        print(f"UNREAD: cannot read {', '.join(bad)} — this lane CANNOT be shown to owe nothing. "
              f"A failed probe is not a clean bill (S4).", file=sys.stderr)
        return 1
    theirs, tst = load(other(lane))
    acked = {c["id"] for c in theirs.get("confirmed", [])} if tst == "ok" else None
    rows = {s.get("id"): s for s in mine.get("sent", [])}

    owed = unread = discharged = 0

    self_disch = 0
    print(f"{lane}: commitments stated on the bus (entries carrying a **DONE** slot)")
    if not commits:
        print("  none — this lane has posted no entry with a DONE slot")
    for c in commits:
        row = rows.get(c["id"])
        if row is None:
            # The entry is in the log but this lane's sidecar has no row for it. We cannot read
            # a discharge that may or may not exist, so this is UNREAD - never "not owed".
            state, unread = "UNREAD ", unread + 1
            extra = "no sidecar row for this id"
        elif row.get("discharged"):
            d = row["discharged"]
            sr = bool(d.get("self_reported"))
            state, discharged = ("DISCH(self)" if sr else "DISCHARGED"), discharged + 1
            self_disch += 1 if sr else 0
            extra = f"in {d.get('in')} · {str(d.get('outcome'))[:60]}"
        else:
            state, owed = "OWED   ", owed + 1
            extra = ""
        if acked is None:
            ack = "ack=UNREAD"          # peer sidecar unreadable: never render that as "no ack"
        elif row is not None and not row.get("requires_ack", True):
            ack = "ack=n/a   "
        elif c["id"] in acked:
            ack = "ack=CONFIRMED"
        else:
            ack = "ack=awaiting "
        print(f"  {c['id']}  {state}  {ack}  DONE: \"{c['done'][:88]}\"")
        if extra:
            print(f"                             {extra}")
    print(f"\n  {owed} OWED · {discharged} discharged · {unread} UNREAD · {len(commits)} stated")
    print(OWED_CEILING)
    if a.enforce and (owed or unread or self_disch):
        # Fail closed, the same law as the FULL STOP's unread branch: a commitment that cannot
        # be shown reported is not a commitment that was reported.
        #
        # SELF-REPORTED discharges count as NOT DISCHARGED here (S109 Circle). SKILL.md says
        # "--in must name a message of yours THE PEER CAN READ ON THE BUS, so a lane cannot clear
        # its own commitments privately" - and `--enforce` was passing a self-report at exit 0,
        # which refutes that sentence verbatim. Measured on a forward-looking DONE ("I WILL
        # produce the converted bundle"): discharged in one command, enforce green, ZERO bytes on
        # the bus for the peer to read. Exactly MSG-FAB-0020's shape, the case this command was
        # built for. The self-report stays PERMITTED and RECORDED for `owed`'s own readout - a
        # DONE can be true when written - but it is not evidence a peer can check, so it may not
        # satisfy an enforcement gate.
        print(f"MEASURED: {owed} owed, {unread} unread, {self_disch} self-reported — "
              f"D2 is not discharged.", file=sys.stderr)
        if self_disch:
            print(f"  {self_disch} discharge(s) cite only the lane's OWN entry. A self-report is "
                  f"recorded, not verifiable:\n  the peer has nothing on the bus to read. Report "
                  f"the outcome in a LATER entry and discharge against that.", file=sys.stderr)
        return 1
    return 0


def cmd_discharge(a):
    """Report the outcome of a DONE you stated. The report must be ON THE BUS, not just in your
    own ledger: `--in` names a message of yours that the peer can read. A lane that could clear
    its own commitments privately would have a back-channel, which is GUARD B's defect one level
    down."""
    announce_bus("discharge")
    lane = a.as_model
    d, st = load(lane)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    commits, cst = lane_commitments(lane)
    if cst == "UNREAD":
        print("UNREAD: relay.md cannot be read — nothing may be discharged against a log that "
              "cannot be checked.", file=sys.stderr)
        return 1
    by_id = {c["id"]: c for c in commits}
    rows = {s.get("id"): s for s in d.get("sent", [])}
    if a.id not in rows:
        print(f"REFUSED: {a.id} is not one of {lane}'s sent messages. A lane discharges only its "
              f"OWN commitments — the single-writer law, applied to outcomes.", file=sys.stderr)
        return 1
    if a.id not in by_id:
        print(f"REFUSED: {a.id} carries no **DONE** slot in relay.md — there is no stated "
              f"commitment to discharge.", file=sys.stderr)
        return 1
    if len(a.outcome.strip()) < 20:
        print("REFUSED: state what ACTUALLY happened (>=20 chars). \"done\" is not an outcome.",
              file=sys.stderr)
        return 1
    if a.in_id not in rows or extract_entry(a.in_id) is None:
        print(f"REFUSED: --in {a.in_id} is not a message of yours present in relay.md. The "
              f"outcome must be reportable BY THE PEER, from the bus.", file=sys.stderr)
        return 1
    if str(rows[a.in_id].get("utc", "")) < str(rows[a.id].get("utc", "")):
        print(f"REFUSED: {a.in_id} predates {a.id} — an outcome cannot be reported before the "
              f"commitment that produced it.", file=sys.stderr)
        return 1
    if rows[a.id].get("discharged"):
        prev = rows[a.id]["discharged"]
        print(f"REFUSED: {a.id} was already discharged {prev.get('utc')} in {prev.get('in')}: "
              f"\"{str(prev.get('outcome'))[:70]}\". Appends never erase — post a correction "
              f"entry instead of overwriting this one.", file=sys.stderr)
        return 1
    rows[a.id]["discharged"] = {
        "utc": utc_now(), "in": a.in_id, "outcome": a.outcome.strip(),
        # A self-report is PERMITTED (a DONE can be true when written, e.g. "already done") but
        # it is RECORDED as one, the same way --override records its reason. Never silent.
        "self_reported": a.in_id == a.id,
    }
    save(lane, d, lane)
    print(f"discharged {a.id} — reported in {a.in_id}"
          f"{'  (SELF-REPORTED)' if a.in_id == a.id else ''}")
    print(f"  DONE was: \"{by_id[a.id]['done'][:80]}\"")
    print(f"  outcome : \"{a.outcome.strip()[:80]}\"")
    return 0


def cmd_watch(a):
    """One stdout line per state change. Unbounded by design - run it under a monitor."""
    seen_conf, seen_in = set(), set()
    first = True
    warned_unread = False
    while True:
        theirs, st = load(other(a.as_model))
        mine, st_mine = load(a.as_model)
        # UNREAD IS NEVER SILENCE (S109, found while arming this as a monitor). The loop below
        # ran only when BOTH sidecars read ok; when either was missing or malformed it looped
        # forever printing nothing, and to a monitor that is indistinguishable from "a quiet
        # bus". This is the gate agent's own sleep signal rendering a FAILED PROBE as calm -
        # SYM-031, in the one place a lane trusts to wake it.
        if st != "ok" or st_mine != "ok":
            if not warned_unread:
                warned_unread = True
                bad = [m for m, s in ((other(a.as_model), st), (a.as_model, st_mine)) if s != "ok"]
                print(f"UNREAD {', '.join(bad)} — the board cannot be read, so this watch is "
                      f"BLIND, not quiet. Run `gate.py status`; if a sidecar is missing run "
                      f"`init`.", flush=True)
        elif warned_unread:
            warned_unread = False
            print("board readable again — watch resumed", flush=True)
        if st == "ok" and st_mine == "ok":
            mine_ids = {s["id"] for s in mine["sent"]}
            for c in theirs["confirmed"]:
                if c["id"] in mine_ids and c["id"] not in seen_conf:
                    seen_conf.add(c["id"])
                    if not first:
                        print(f"CONFIRMED {c['id']} by {other(a.as_model)} — \"{c['restatement'][:90]}\"", flush=True)
            done = {c["id"] for c in mine["confirmed"]}
            for s in theirs["sent"]:
                if s.get("to") == a.as_model and s["id"] not in done and s["id"] not in seen_in:
                    seen_in.add(s["id"])
                    if not first:
                        print(f"TICKET {s['id']} from {other(a.as_model)} — {s.get('subject','')}", flush=True)
        first = False
        time.sleep(a.interval)


def main() -> int:
    p = argparse.ArgumentParser(description="relay-gate: the ACK protocol's mechanical half")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_as(sp):
        sp.add_argument("--as", dest="as_model", required=True, choices=MODELS)
        return sp

    add_as(sub.add_parser("init")).set_defaults(fn=cmd_init)
    sp = add_as(sub.add_parser("beat"))
    sp.add_argument("--doing", default=None, help="what you are doing RIGHT NOW")
    sp.add_argument("--planning", default=None, help="what you intend to do next")
    sp.add_argument("--completed", action="append", default=None, help="finished since the last beat (repeatable)")
    sp.add_argument("--verified", action="append", default=None, help="PROVED (repeatable) - each one REQUIRES a --probe")
    sp.add_argument("--probe", action="append", default=None, help="the command/output that settles the matching --verified")
    sp.add_argument("--blocked", default=None, help="what stops you, or 'none'")
    sp.add_argument("--needs", dest="needs", default=None, help="what you need FROM THE PEER")
    sp.add_argument("--show", action="store_true", help="print this lane's beat and exit")
    sp.set_defaults(fn=cmd_beat)
    sp = add_as(sub.add_parser("occupant"))
    sp.add_argument("--model", default=None,
                    help="the model in this seat, e.g. 'Claude Opus 5'. Omit to read it. "
                         "A lane name is refused: the lane is the seat, not the occupant.")
    sp.set_defaults(fn=cmd_occupant)
    sp = add_as(sub.add_parser("post"))
    sp.add_argument("--to", required=True, choices=MODELS)
    sp.add_argument("--subject", required=True)
    sp.add_argument("--body", required=True, help="file with the entry body, or - for stdin")
    sp.add_argument("--ticket", default=None)
    sp.add_argument("--no-ack", action="store_true")
    sp.add_argument("--override", default=None,
                    help="bypass GUARD A (recipient is working) - the reason is RECORDED")
    sp.add_argument("--serves", default=None, help="the FULL STOP carve-out (Rab, S109): this work SERVES resolving that open escalation. Must name a ticket whose escalation is open NOW; the claim is recorded.")
    sp.set_defaults(fn=cmd_post)
    sp = add_as(sub.add_parser("escalate"))
    sp.add_argument("--asking", required=True, help="what Rab must decide")
    sp.add_argument("--why", default=None,
                    help="why this is HIS: (1) authority by domain - adoption, thresholds, "
                         "the vault, graduation, governance organs: ours to recommend, never to "
                         "decide, even in agreement; or (2) deadlock - we disagree and evidence "
                         "will not settle it")
    sp.add_argument("--ticket", default=None)
    sp.set_defaults(fn=cmd_escalate)
    sp = add_as(sub.add_parser("preserve-disagreement"))
    sp.add_argument("--id", required=True, help="durable disagreement id, e.g. DIS-001")
    sp.add_argument("--round1", nargs=2, required=True, metavar=("FIRST", "REPLY"),
                    help="the two peer-confirmed round-1 relay ids, in exact log order")
    sp.add_argument("--round2", nargs=2, required=True, metavar=("FIRST", "REPLY"),
                    help="the two peer-confirmed round-2 relay ids, in the same lane order")
    sp.add_argument("--consequence", required=True,
                    help="the nonempty unresolved consequence")
    sp.add_argument("--prohibits", action="append", required=True,
                    help="an action still prohibited (repeatable; at least one required)")
    sp.set_defaults(fn=cmd_preserve_disagreement)
    sp = add_as(sub.add_parser("resolve"))
    sp.add_argument("--id", required=True, help="the escalation's msg id")
    sp.add_argument("--decision", required=True, help="what Rab decided, in his terms")
    sp.set_defaults(fn=cmd_resolve)
    add_as(sub.add_parser("inbox")).set_defaults(fn=cmd_inbox)
    sp = add_as(sub.add_parser("confirm"))
    sp.add_argument("--id", required=True)
    sp.add_argument("--restatement", required=True)
    sp.set_defaults(fn=cmd_confirm)
    sp = add_as(sub.add_parser("owed"))
    sp.add_argument("--enforce", action="store_true",
                    help="exit 1 if anything is OWED or UNREAD (fail closed). Without it this is "
                         "a report and always exits 0.")
    sp.set_defaults(fn=cmd_owed)
    sp = add_as(sub.add_parser("discharge"))
    sp.add_argument("--id", required=True, help="the message whose DONE you are discharging")
    sp.add_argument("--in", dest="in_id", required=True,
                    help="a message of yours, present in relay.md and not older than --id, that "
                         "reports the outcome. May be --id itself for a DONE that was already "
                         "true when written; that is RECORDED as self-reported.")
    sp.add_argument("--outcome", required=True, help="what ACTUALLY happened (>=20 chars)")
    sp.set_defaults(fn=cmd_discharge)
    add_as(sub.add_parser("check")).set_defaults(fn=cmd_check)
    sub.add_parser("status").set_defaults(fn=cmd_status, as_model=None)
    sp = add_as(sub.add_parser("ticket"))
    sp.add_argument("--id", required=True)
    sp.add_argument("--state", default="working", choices=STATES)
    sp.add_argument("--serves", default=None, help="the FULL STOP carve-out (Rab, S109): this work SERVES resolving that open escalation. Must name a ticket whose escalation is open NOW; the claim is recorded.")
    sp.set_defaults(fn=cmd_ticket)
    sp = add_as(sub.add_parser("watch"))
    sp.add_argument("--interval", type=float, default=10.0)
    sp.set_defaults(fn=cmd_watch)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
