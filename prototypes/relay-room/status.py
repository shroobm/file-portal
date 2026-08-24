#!/usr/bin/env python3
"""status.py - relay-room, BUILDER C: the status documents and the UNREAD/STALE ladder.

The two layers this file exists to keep apart (CONTRACT §4.1):

  AGENT LAYER  - mechanical. A loop, a poll, a file write, a subprocess exit code. Cheap,
                 verifiable, and either running or not.
  MODEL LAYER  - judgment. Thinking, composing, waiting for a peer's ACK, waiting for Rab.
                 Expensive and unverifiable from outside.

They live in separate objects with DISJOINT enums so a reader can tell which layer a claim
came from without reading a label.

Laws enforced here, mechanically:

  L1  UNREAD IS NEVER IDLE. Every probe that fails returns UNREAD with a reason. There is no
      code path in this file that turns a failed read into a healthy-looking empty state.
      `count: 0`, `sse_clients: 0`, `state: "idle"` are READINGS; when the probe failed the
      field is null and the render is UNREAD.
  L1a A DERIVED READING IS NEVER FRESHER THAN ITS PUBLISHER. Agent UNREAD/STALE => model UNREAD.
  L1b NO UNREAD WITHOUT A REMEDY. Every UNREAD/STALE carries a sentence saying what to do.
  L2  STALENESS IS NOT HEALTH. Age is measured against a threshold and rendered WITH the age.
  L3a TRUNCATION IS ALWAYS MARKED - anything shortened here carries a visible ellipsis.
  L5  QUARANTINE. Every mutating call goes through roomlog.assert_inside first. gate.py is
      never imported; its `load()` contract is REIMPLEMENTED below (§4.4).
  L6  stdlib only.

Written by: status.py is a library. Its writers are catcher.py (status-<lane>.json) and
room.py (model-<lane>.json, server.json) - see the single-writer table, CONTRACT §1.3.
"""

import io
import json
import os
import re
from datetime import datetime, timezone

import roomlog

# ---------------------------------------------------------------- frozen enums (CONTRACT §9)

AGENT_STATES = ("watching", "catching", "handing", "awaiting-model", "mirroring", "error")
MODEL_STATES = ("idle", "working", "composing", "blocked-on-ack", "blocked-on-rab")

# UNREAD and STALE are the READER'S verdicts about a document. They are deliberately absent
# from both enums above: a process that can write its own status file is, by construction,
# neither unread nor stale. write_status() refuses them (T8c).
VERDICTS = ("UNREAD", "STALE")

PROTOCOL = getattr(roomlog, "PROTOCOL", "fp-relay-room/v1")
GATE_PROTOCOL = "fp-relay-ack/v1"          # gate.py's PROTOCOL - different, on purpose
LANES = getattr(roomlog, "LANES", ("Fable", "Codex"))

# Fallbacks used only if roomlog.DEFAULTS is missing a key. Named here so a KeyError in the
# threshold table can never take the board down (a board that cannot render is a board that
# renders nothing, which is the worst possible reading).
_FALLBACK = {
    "stale_after_s": 15.0,
    "model_stale_after_s": 300.0,
    "declared_fresh_s": 60.0,
    "flight_stall_after_s": 90.0,
    "catcher_interval_s": 2.0,
    "port": 7133,
}


def _read(path) -> str:
    """Read fully, then CLOSE. gate.py's `io.open(...).read()` idiom leaves the handle to the
    garbage collector; on Windows a lingering handle beside a lock directory is a defect
    waiting for a bad afternoon, and the tripwire run surfaced it as a ResourceWarning."""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()

# ---------------------------------------------------------------- paths

def _lane(lane) -> str:
    s = str(lane).strip()
    for known in LANES:
        if s.lower() == known.lower():
            return known
    raise ValueError(
        f"unknown lane {lane!r} - the lanes are {LANES}. A lane is a SEAT, not a model name."
    )


def status_path(lane) -> "os.PathLike":
    return roomlog.STATE / f"status-{_lane(lane).lower()}.json"


def declared_path(lane) -> "os.PathLike":
    return roomlog.STATE / f"model-{_lane(lane).lower()}.json"


def sidecar_path(lane) -> "os.PathLike":
    return roomlog.COORD / f"ack-{_lane(lane).lower()}.json"


def server_path() -> "os.PathLike":
    return roomlog.STATE / "server.json"


def rel(p) -> str:
    """A path as the operator sees it in the remedy sentence: relative to ROOT when possible.

    Computed against roomlog.ROOT at CALL time, not by splitting on the string "relay-room/" -
    the tripwires relocate ROOT to a temp tree, and a remedy that named a path the operator
    does not have is a remedy that wastes his next ten minutes.
    """
    try:
        r = os.path.relpath(os.fspath(p), os.fspath(roomlog.ROOT))
        return str(p) if r.startswith("..") else r.replace("\\", "/")
    except Exception:
        return str(p)


# ---------------------------------------------------------------- time

def utc_now() -> str:
    return roomlog.utc_now()


def parse_utc(s):
    """Tolerant UTC parse. Returns an aware datetime, or None - NEVER raises.

    Three lines duplicated rather than widening the seam with roomlog (CONTRACT §9): this
    reader must also swallow gate.py's MINUTE-precision stamps (its `utc_now()` writes
    "%Y-%m-%dT%H:%MZ"), and roomlog.parse_utc is specified only against room.md's
    millisecond stamps. A parser that returned None on the sidecar's clock would make every
    healthy lane render UNREAD on rule 7 - a probe that lies.
    """
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    for cand in (t, t.replace("+00:00", "") + "+00:00"):
        try:
            d = datetime.fromisoformat(cand)
        except Exception:
            continue
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    return None


def now_dt(now=None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    d = parse_utc(now)
    return d or datetime.now(timezone.utc)


def age_s(stamp, now=None):
    """Seconds between `stamp` and now. None when the stamp is unreadable - never 0.0."""
    d = parse_utc(stamp)
    if d is None:
        return None
    return max(0.0, (now_dt(now) - d).total_seconds())


def age_phrase(seconds) -> str:
    """`3m12s`. L2 forbids a bare STALE; every STALE carries this."""
    if seconds is None:
        return "an unmeasurable time"
    s = max(0.0, float(seconds))
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(int(s), 60)
    if m < 60:
        return f"{m}m{sec:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def clip(text, n=160) -> str:
    """L3a / SYM-052: anything shortened carries a visible ellipsis. Never a silent cut."""
    if text is None:
        return None
    t = str(text)
    return t if len(t) <= n else t[: n - 1] + "…"


# ---------------------------------------------------------------- config (thresholds)

def config():
    """(values, source). A config.json that will not parse falls back to DEFAULTS and SAYS SO -
    a silent fallback is a failed probe rendering as a value."""
    base = {}
    try:
        base.update(dict(getattr(roomlog, "DEFAULTS", {}) or {}))
    except Exception:
        base = {}
    for k, v in _FALLBACK.items():
        base.setdefault(k, v)
    p = roomlog.STATE / "config.json"
    if not p.exists():
        return base, f"defaults ({rel(p)} does not exist - run `python room.py init`)"
    try:
        d = json.loads(_read(p))
        if not isinstance(d, dict):
            raise ValueError(f"not a JSON object (found {type(d).__name__})")
    except Exception as exc:
        return base, (f"defaults ({rel(p)} unreadable: {type(exc).__name__}: {clip(exc, 80)} - "
                      f"delete it and re-run `python room.py init`)")
    base.update({k: v for k, v in d.items() if v is not None})
    return base, rel(p)


def _num(value, lo, hi, fallback):
    """A threshold outside its range is not a threshold. Returns (value, ok)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback, False
    v = float(value)
    if v < lo or v > hi:
        return fallback, False
    return v, True


# ---------------------------------------------------------------- the relay-gate sidecar
# gate.py's load() contract REIMPLEMENTED, not imported (L5: gate.py is invoked, never
# imported). Six UNREAD rules, verbatim from gate.py's load(), each with its own remedy (L1b).

def read_sidecar(lane):
    """-> (data|None, "ok"|"UNREAD", reason|None). There is no path that returns a
    healthy-looking empty state."""
    lane = _lane(lane)
    p = sidecar_path(lane)
    r = rel(p)
    launch = (f"start it: python catcher.py --lane {lane}  (the catcher runs "
              f"`gate.py init --as {lane}` against FP_COORD={rel(roomlog.COORD)})")

    if not p.exists():                                                        # rule 1
        return None, "UNREAD", (
            f"{r} does not exist - the {lane} lane has not run `gate.py init`; {launch}.")
    try:                                                                      # rule 2
        raw = _read(p)
        d = json.loads(raw)
    except Exception as exc:
        return None, "UNREAD", (
            f"{r} could not be read or parsed ({type(exc).__name__}: {clip(exc, 90)}) - the "
            f"relay-gate sidecar is damaged. Stop the {lane} catcher, delete the file, then "
            f"{launch}. Do NOT hand-edit it while a process is running.")
    if not isinstance(d, dict):                                               # rule 3
        return None, "UNREAD", (
            f"{r} is not a JSON object (found {type(d).__name__}) - delete it and {launch}.")
    if d.get("protocol") != GATE_PROTOCOL:                                    # rule 4
        return None, "UNREAD", (
            f"{r} declares protocol {d.get('protocol')!r}, not {GATE_PROTOCOL!r} - it was "
            f"written by a different relay-gate version. Delete it and {launch}.")
    if d.get("writer") != lane:                                               # rule 5
        return None, "UNREAD", (
            f"{r} claims writer {d.get('writer')!r}, not {lane!r} - single-writer law "
            f"(gate.py's save()): only `gate.py --as {lane}` may write it. Someone ran the gate "
            f"with the wrong --as; delete the file and {launch}.")
    for key in ("sent", "confirmed"):                                         # rule 6a
        if not isinstance(d.get(key), list):
            return None, "UNREAD", (
                f"{r} has a malformed `{key}` field (expected a list, found "
                f"{type(d.get(key)).__name__}) - the sidecar is damaged; delete it and {launch}.")
    if not isinstance(d.get("escalations", []), list):                        # rule 6b
        return None, "UNREAD", (
            f"{r} has a malformed `escalations` field (expected a list, found "
            f"{type(d.get('escalations')).__name__}) - delete it and {launch}.")
    return d, "ok", None


def sidecar_view(lane):
    """The `model.sidecar` sub-object of the status document (CONTRACT §4.2)."""
    lane = _lane(lane)
    d, st, reason = read_sidecar(lane)
    view = {
        "status": st,
        "state": None,
        "state_note": None,
        "ticket": None,
        "sent": None,          # null, not 0: 0 is a reading and this probe failed
        "confirmed": None,
        "escalations_open": None,
        "occupant": None,
        "updated_utc": None,
        "age_s": None,
        "path": rel(sidecar_path(lane)),
        "reason": reason,
    }
    if st != "ok":
        return view
    state = d.get("state")
    if state not in MODEL_STATES:
        # gate.py's `--state` choices include the literal "UNREAD" (its STATES tuple). A process
        # may not declare its own probe failed, so it is not usable as a model state here.
        view["state_note"] = (
            f"the sidecar carries state {state!r}, which is not one of the five model states "
            f"{MODEL_STATES} - a lane may not declare itself UNREAD; UNREAD is the reader's "
            f"verdict. Set a real state: gate.py ticket --as {lane} --id <id> --state working")
        state = None
    occ = d.get("occupant")
    view.update({
        "state": state,
        "ticket": d.get("current_ticket"),
        "sent": len(d.get("sent") or []),
        "confirmed": len(d.get("confirmed") or []),
        "escalations_open": len([e for e in (d.get("escalations") or [])
                                 if isinstance(e, dict) and e.get("state") == "open"]),
        "occupant": occ.strip() if isinstance(occ, str) and occ.strip() else "UNDECLARED",
        "updated_utc": d.get("updated_utc"),
        "age_s": age_s(d.get("updated_utc")),
    })
    return view


# ---------------------------------------------------------------- the model's declaration

def read_declared(lane):
    """state/model-<lane>.json, written by room.py on the model's behalf.
    -> (data|None, "ok"|"UNREAD", reason|None)."""
    lane = _lane(lane)
    p = declared_path(lane)
    r = rel(p)
    if not p.exists():
        return None, "UNREAD", (
            f"{r} does not exist - the {lane} model has not declared its layer state. It is "
            f"optional: `python room.py state --lane {lane} --state working --note \"...\"` "
            f"writes it. Without it the sidecar is the only reading.")
    try:
        d = json.loads(_read(p))
    except Exception as exc:
        return None, "UNREAD", (
            f"{r} could not be read or parsed ({type(exc).__name__}: {clip(exc, 90)}) - delete "
            f"it; it is rewritten by `python room.py state --lane {lane} ...`.")
    if not isinstance(d, dict):
        return None, "UNREAD", f"{r} is not a JSON object (found {type(d).__name__}) - delete it."
    # `protocol` is checked only when present: CONTRACT §3.3 fixes the RESPONSE shape of
    # /api/model/state, not the file's, so a missing field is not evidence of damage. A WRONG
    # protocol is evidence, and is refused.
    if d.get("protocol") is not None and d.get("protocol") != PROTOCOL:
        return None, "UNREAD", (
            f"{r} declares protocol {d.get('protocol')!r}, not {PROTOCOL!r} - it was written by "
            f"a different version of this prototype. Delete it and re-declare.")
    if d.get("lane") is not None and str(d.get("lane")).lower() != lane.lower():
        return None, "UNREAD", (
            f"{r} claims lane {d.get('lane')!r}, not {lane!r} - single-writer law: this file is "
            f"the {lane} lane's declaration. Delete it and re-declare.")
    if d.get("state") not in MODEL_STATES:
        return None, "UNREAD", (
            f"{r} carries an unknown model state {d.get('state')!r} - the five are "
            f"{MODEL_STATES}. Re-declare: python room.py state --lane {lane} --state working")
    if parse_utc(d.get("utc")) is None:
        return None, "UNREAD", (
            f"{r} has no readable timestamp ({d.get('utc')!r}) - its age cannot be measured, so "
            f"it cannot outrank the sidecar. Re-declare it.")
    return d, "ok", None


def declared_view(lane):
    lane = _lane(lane)
    d, st, reason = read_declared(lane)
    if st != "ok":
        return {"status": st, "state": None, "utc": None, "age_s": None,
                "ticket": None, "note": None,
                "path": rel(declared_path(lane)), "reason": reason}
    return {"status": "ok", "state": d.get("state"), "utc": d.get("utc"),
            "age_s": age_s(d.get("utc")), "ticket": d.get("ticket"),
            "note": clip(d.get("note"), 200),
            "path": rel(declared_path(lane)), "reason": None}


def write_model_declared(lane, state, ticket=None, note=None):
    """Called by room.py for POST /api/model/state and `room.py state`. Owned by C because the
    refusal below is a law, not a validation: blocked-on-* are READINGS OF THE SIDECAR and
    UNREAD/STALE are readings of a failed probe. Neither can be declared by the thing being
    probed. Raises ValueError with the CONTRACT §3.3 remedy."""
    lane = _lane(lane)
    if state in ("blocked-on-ack", "blocked-on-rab", "UNREAD", "STALE"):
        raise ValueError(
            "blocked-on-ack and blocked-on-rab are readings of the relay-gate sidecar, not "
            f"declarations - set them with gate.py (escalate / post) against "
            f"FP_COORD={roomlog.COORD}. UNREAD and STALE are derived from a failed or old probe "
            "and can never be declared by the thing being probed.")
    if state not in ("idle", "working", "composing"):
        raise ValueError(
            f"unknown model state {state!r} - a model may declare only idle, working or "
            f"composing. blocked-on-ack / blocked-on-rab come from gate.py; UNREAD and STALE "
            f"are the reader's verdicts and are never written.")
    doc = {"protocol": PROTOCOL, "writer": "room.py", "lane": lane, "state": state,
           "ticket": ticket, "note": note, "utc": utc_now()}
    _atomic_json(declared_path(lane), doc)
    return doc


# ---------------------------------------------------------------- writing (atomic)

def _atomic_json(path, doc):
    """.part then os.replace - a reader never sees a half-file (gate.py's own invariant, in its save()).
    assert_inside FIRST: nothing outside ROOT is ever written (L5)."""
    p = roomlog.assert_inside(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, p)
    return p


def write_status(lane, doc):
    """The lane's catcher publishing its own document. Refuses (ValueError + remedy):

      - a writer that is not `catcher:<Lane>` (single-writer law, CONTRACT §1.3);
      - an agent.state of UNREAD or STALE, or anything outside the six (T8c);
      - a model.state of UNREAD or STALE (same law; null is legal and renders UNREAD);
      - a missing/unreadable heartbeat - a document whose age cannot be measured cannot be
        trusted, so it may not be published at all.
    """
    lane = _lane(lane)
    if not isinstance(doc, dict):
        raise ValueError(f"status document must be a dict, got {type(doc).__name__}")
    if doc.get("protocol") != PROTOCOL:
        raise ValueError(f"status document must declare protocol {PROTOCOL!r}")
    if doc.get("writer") != f"catcher:{lane}":
        raise ValueError(
            f"REFUSED: writer {doc.get('writer')!r} may not write {rel(status_path(lane))} - "
            f"single-writer law: only 'catcher:{lane}' may. Pass --lane {lane}.")
    agent = doc.get("agent")
    if not isinstance(agent, dict):
        raise ValueError("status document has no `agent` object")
    a_state = agent.get("state")
    if a_state in VERDICTS:
        raise ValueError(
            f"REFUSED: an agent may not publish {a_state!r} about itself. UNREAD and STALE are "
            f"the READER's verdicts about this file (CONTRACT §4.3); a process that can write "
            f"its status is by construction neither. Publish one of {AGENT_STATES} - `error` is "
            f"the one that means 'my last cycle raised'.")
    if a_state not in AGENT_STATES:
        raise ValueError(
            f"REFUSED: unknown agent state {a_state!r} - the six are {AGENT_STATES}.")
    model = doc.get("model")
    if not isinstance(model, dict):
        raise ValueError("status document has no `model` object")
    m_state = model.get("state")
    if m_state in VERDICTS:
        raise ValueError(
            f"REFUSED: {m_state!r} may not be written as a model state - it is the reader's "
            f"verdict about a failed or old probe (CONTRACT §4.4). Publish null; a null model "
            f"state renders UNREAD, never idle.")
    if m_state is not None and m_state not in MODEL_STATES:
        raise ValueError(
            f"REFUSED: unknown model state {m_state!r} - the five are {MODEL_STATES}, or null.")
    if parse_utc(doc.get("heartbeat_utc")) is None:
        raise ValueError(
            f"REFUSED: heartbeat_utc {doc.get('heartbeat_utc')!r} is unreadable - a document "
            f"whose age cannot be measured cannot be judged against L2, so it is not published.")
    return _atomic_json(status_path(lane), doc)


def write_server(doc):
    """state/server.json - room.py's own heartbeat. Stamped here so every reader of the board
    measures the server by the same clock the lanes are measured by."""
    if not isinstance(doc, dict):
        raise ValueError(f"server document must be a dict, got {type(doc).__name__}")
    d = dict(doc)
    d.setdefault("protocol", PROTOCOL)
    d.setdefault("writer", "room.py")
    d["heartbeat_utc"] = d.get("heartbeat_utc") or utc_now()
    return _atomic_json(server_path(), d)


# ---------------------------------------------------------------- reading a status document

def read_status(lane):
    """Ladder rules 1-5 of CONTRACT §4.6 (the readability half).
    -> (data|None, "ok"|"UNREAD", reason|None)."""
    lane = _lane(lane)
    p = status_path(lane)
    r = rel(p)
    start = f"Run: python catcher.py --lane {lane}   (README §Launch step 3)"

    if not p.exists():                                                        # rule 1
        return None, "UNREAD", (
            f"{r} does not exist - the {lane} catcher has not been started. {start}")
    try:                                                                      # rule 2
        d = json.loads(_read(p))
    except Exception as exc:
        return None, "UNREAD", (
            f"{r} could not be read as JSON ({type(exc).__name__}: {clip(exc, 90)}) - delete the "
            f"file and restart the catcher; it is rewritten every cycle. {start}")
    if not isinstance(d, dict):                                               # rule 3
        return None, "UNREAD", (
            f"{r} is not a JSON object (found {type(d).__name__}) - delete it and restart the "
            f"catcher. {start}")
    if d.get("protocol") != PROTOCOL:                                         # rule 4
        return None, "UNREAD", (
            f"{r} was written by a different protocol version (found {d.get('protocol')!r}, "
            f"expected {PROTOCOL!r}) - stop every relay-room process, delete state/*.json, and "
            f"restart. {start}")
    if d.get("writer") != f"catcher:{lane}":                                  # rule 5
        return None, "UNREAD", (
            f"{r} claims writer {d.get('writer')!r} - single-writer law: only `catcher:{lane}` "
            f"may write it (CONTRACT §1.3). Two catchers on one lane, or the wrong --lane. "
            f"Stop them all, delete the file, then {start}")
    return d, "ok", None


# ---------------------------------------------------------------- THE LADDER (CONTRACT §4.6)

def render_lane(lane, *, now=None):
    """The `lanes.<Lane>` value of GET /api/status. Evaluated in the contract's exact order;
    the first hit wins. Nothing below ever renders a failed probe as health."""
    lane = _lane(lane)
    cfg, _src = config()
    now = now_dt(now)
    out = {
        "lane": lane,
        "rendered_agent": None, "rendered_model": None,
        "agent_reason": None, "model_reason": None,
        "doc_utc": None, "age_s": None,
        "agent": None, "model": None, "in_flight": None, "gate": None,
        "doc_path": rel(status_path(lane)),
    }

    doc, st, reason = read_status(lane)                              # rules 1-5
    if st != "ok":
        out["rendered_agent"] = "UNREAD"
        out["agent_reason"] = reason
        out["rendered_model"] = "UNREAD"
        out["model_reason"] = (
            f"the publisher of this reading is UNREAD, so the reading is UNREAD (L1a: a derived "
            f"reading is never fresher than its publisher). Fix the agent first: {reason}")
        return out

    agent = doc.get("agent") if isinstance(doc.get("agent"), dict) else {}
    model = doc.get("model") if isinstance(doc.get("model"), dict) else {}
    r = rel(status_path(lane))
    out["doc_utc"] = doc.get("heartbeat_utc")

    a_state = agent.get("state")
    if a_state not in AGENT_STATES:                                  # rule 6
        out["rendered_agent"] = "UNREAD"
        out["agent_reason"] = (
            f"{r} carries an unknown agent state {a_state!r} - the six are {AGENT_STATES}. The "
            f"file was hand-edited or written by something that is not this catcher. Delete it "
            f"and restart: python catcher.py --lane {lane}")
    elif parse_utc(doc.get("heartbeat_utc")) is None:                # rule 7
        out["rendered_agent"] = "UNREAD"
        out["agent_reason"] = (
            f"{r} has no readable heartbeat ({doc.get('heartbeat_utc')!r}) - its age cannot be "
            f"measured, so its contents cannot be trusted (L2 cannot be applied to a clock that "
            f"does not read). Delete it and restart: python catcher.py --lane {lane}")
    else:
        declared_stale, ok_thr = _num(doc.get("stale_after_s"), 1.0, 3600.0,
                                      cfg.get("stale_after_s", 15.0))
        if not ok_thr:                                               # rule 8
            out["rendered_agent"] = "UNREAD"
            out["agent_reason"] = (
                f"{r} declares an out-of-range staleness threshold "
                f"({doc.get('stale_after_s')!r}); a lane may not exempt itself from L2. Legal "
                f"range is 1-3600 s. Restart the catcher without a hand-edited threshold: "
                f"python catcher.py --lane {lane}")
        else:
            a = age_s(doc.get("heartbeat_utc"), now)
            out["age_s"] = None if a is None else round(a, 3)
            if a is not None and a > declared_stale:                 # rule 9
                out["rendered_agent"] = "STALE"
                out["agent_reason"] = (
                    f"STALE (last seen {age_phrase(a)} ago) - {r} has not been rewritten in "
                    f"{age_phrase(a)}, past its own {declared_stale:g}s threshold. The catcher "
                    f"is stopped, hung, or the clock moved. Check its terminal; restart with "
                    f"python catcher.py --lane {lane}")
            else:
                out["rendered_agent"] = a_state                      # a reading, at last
                out["agent_reason"] = None
                out["agent"] = agent
                out["in_flight"] = doc.get("in_flight")
                out["gate"] = doc.get("gate")

    if out["rendered_agent"] == "STALE":
        # The document read fine; it is only old. Its last agent/flight/gate readings stay
        # visible (with the age beside them) - but nothing DERIVED from it may render fresh.
        out["agent"] = agent
        out["in_flight"] = doc.get("in_flight")
        out["gate"] = doc.get("gate")

    # ---- model ladder
    if out["rendered_agent"] in VERDICTS:                            # rule 1 (L1a)
        out["rendered_model"] = "UNREAD"
        out["model_reason"] = (
            f"the publisher of this reading is {out['rendered_agent']}, so the reading is UNREAD "
            f"(L1a: a derived reading is never fresher than its publisher - an agent that died "
            f"at 14:02 may not still be telling the UI the model is working at 14:19). "
            f"{out['agent_reason']}")
        return out

    sidecar = model.get("sidecar") if isinstance(model.get("sidecar"), dict) else {}
    declared = model.get("declared") if isinstance(model.get("declared"), dict) else {}
    m_state = model.get("state")

    if sidecar.get("status") != "ok":                                # rule 2
        out["rendered_model"] = "UNREAD"
        out["model_reason"] = sidecar.get("reason") or (
            f"the relay-gate sidecar for {lane} did not read (status "
            f"{sidecar.get('status')!r}) and carried no reason - treat the model layer as "
            f"unknown and check {rel(sidecar_path(lane))} by hand.")
        out["model"] = None
        return out

    if m_state not in MODEL_STATES:                                  # rule 3
        out["rendered_model"] = "UNREAD"
        extra = sidecar.get("state_note") or ""
        out["model_reason"] = (
            f"{r} carries an unknown model state {m_state!r} - the five are {MODEL_STATES}. The "
            f"catcher publishes null when its probes cannot produce one, and null renders "
            f"UNREAD, never idle. {extra}").strip()
        out["model"] = None
        return out

    out["model"] = model
    s_state = sidecar.get("state")
    if s_state in ("blocked-on-ack", "blocked-on-rab"):              # rule 4
        out["rendered_model"] = s_state
        out["model_reason"] = None
        return out

    fresh_s, _ = _num(cfg.get("declared_fresh_s"), 1.0, 3600.0, 60.0)
    d_age = declared.get("age_s")
    if d_age is None:
        d_age = age_s(declared.get("utc"), now)
    if (declared.get("status") == "ok" and declared.get("state") in MODEL_STATES
            and d_age is not None and d_age <= fresh_s):             # rule 5
        out["rendered_model"] = declared.get("state")
        out["model_reason"] = None
        return out

    model_stale, _ok = _num(doc.get("model_stale_after_s"), 1.0, 86400.0,
                            cfg.get("model_stale_after_s", 300.0))
    s_age = sidecar.get("age_s")
    if s_age is None:
        s_age = age_s(sidecar.get("updated_utc"), now)
    s_old = s_age is None or s_age > model_stale
    d_old = d_age is None or d_age > model_stale or declared.get("status") != "ok"
    if s_old and d_old:                                              # rule 6
        newest, src, stamp = None, None, None
        if s_age is not None:
            newest, src, stamp = s_age, "the relay-gate sidecar", sidecar.get("updated_utc")
        if d_age is not None and (newest is None or d_age < newest):
            newest, src, stamp = d_age, "its own declaration", declared.get("utc")
        out["rendered_model"] = "STALE"
        out["model_reason"] = (
            f"STALE (last seen {age_phrase(newest)} ago) - the model has not moved in "
            f"{age_phrase(newest)}; its last reading is {s_state or m_state!r} from {src} at "
            f"{stamp}. The agent is alive, so this is the MODEL that stopped: check its session, "
            f"or `python room.py state --lane {lane} --state working --note \"...\"` to declare "
            f"it moving. (Threshold {model_stale:g}s; gate.py stamps updated_utc at MINUTE "
            f"precision, so anything under ~120s would false-alarm.)")
        return out

    out["rendered_model"] = s_state if s_state in MODEL_STATES else m_state
    out["model_reason"] = None
    return out


def render_server(*, now=None):
    """The board's `server` block. Same ladder, one publisher."""
    cfg, _ = config()
    now = now_dt(now)
    p = server_path()
    r = rel(p)
    start = "Run: python room.py serve --port %s" % cfg.get("port", 7133)
    blank = {"rendered": "UNREAD", "reason": None, "pid": None, "port": None,
             "token_mode": None, "heartbeat_utc": None, "age_s": None, "path": r}

    if not p.exists():
        blank["reason"] = (f"{r} does not exist - the server is not running (or has never run). "
                           f"{start}")
        return blank
    try:
        d = json.loads(_read(p))
        if not isinstance(d, dict):
            raise ValueError(f"not a JSON object (found {type(d).__name__})")
    except Exception as exc:
        blank["reason"] = (f"{r} could not be read ({type(exc).__name__}: {clip(exc, 90)}) - "
                           f"delete it and restart the server. {start}")
        return blank
    if d.get("protocol") != PROTOCOL:
        blank["reason"] = (f"{r} declares protocol {d.get('protocol')!r}, not {PROTOCOL!r} - "
                           f"stop every relay-room process, delete state/server.json, restart. "
                           f"{start}")
        return blank
    if parse_utc(d.get("heartbeat_utc")) is None:
        blank["reason"] = (f"{r} has no readable heartbeat ({d.get('heartbeat_utc')!r}) - its "
                           f"age cannot be measured, so it cannot be trusted. {start}")
        return blank

    a = age_s(d.get("heartbeat_utc"), now)
    thr, ok = _num(d.get("stale_after_s"), 1.0, 3600.0, cfg.get("stale_after_s", 15.0))
    out = {"rendered": "ok", "reason": None, "pid": d.get("pid"), "port": d.get("port"),
           "token_mode": d.get("token_mode"), "heartbeat_utc": d.get("heartbeat_utc"),
           "age_s": None if a is None else round(a, 3), "path": r}
    if not ok:
        out["rendered"] = "UNREAD"
        out["reason"] = (f"{r} declares an out-of-range staleness threshold "
                         f"({d.get('stale_after_s')!r}); nothing may exempt itself from L2.")
        return out
    if a is not None and a > thr:
        out["rendered"] = "STALE"
        out["reason"] = (f"STALE (last seen {age_phrase(a)} ago) - the server process is stopped "
                         f"or hung; the page you are reading is showing you a corpse's last "
                         f"words. {start}")
    return out


def render_board(*, now=None):
    """The whole GET /api/status document (CONTRACT §4.5).

    NOTE for Builder B's SSE diff: `utc`, every `age_s`, and `log.read_utc` are VOLATILE by
    construction - they change on every tick because time passed, which is exactly what makes
    a clock-driven STALE reach the UI (T9b). Diff the board with those fields excluded, or the
    `status` frame fires every 0.5s; do NOT solve it by freezing the clock.
    """
    cfg, cfg_src = config()
    now = now_dt(now)
    board = {
        "protocol": PROTOCOL,
        "utc": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "thresholds": {
            "stale_after_s": cfg.get("stale_after_s", 15.0),
            "model_stale_after_s": cfg.get("model_stale_after_s", 300.0),
            "flight_stall_after_s": cfg.get("flight_stall_after_s", 90.0),
            "declared_fresh_s": cfg.get("declared_fresh_s", 60.0),
        },
        "thresholds_source": cfg_src,
        "server": render_server(now=now),
        "lanes": {lane: render_lane(lane, now=now) for lane in LANES},
        "rab": {"sse_clients": None, "last_say_utc": None},
        "log": {"log_status": "UNREAD", "reason": None, "count": None, "torn": None,
                "debris": None, "bytes": None, "read_utc": None},
    }

    srv = board["server"]
    if srv.get("rendered") == "ok":
        try:
            d = json.loads(_read(server_path()))
            board["rab"]["sse_clients"] = d.get("sse_clients")
        except Exception:
            board["rab"]["sse_clients"] = None      # null, never 0 - 0 is a reading
    try:
        log = roomlog.read_log()
        board["log"] = {
            "log_status": log.status,
            "reason": log.reason,
            "count": len(log.entries) if log.status == "ok" else None,
            "torn": log.torn if log.status == "ok" else None,
            "debris": len(log.debris) if log.status == "ok" else None,
            "bytes": log.bytes if log.status == "ok" else None,
            "read_utc": log.read_utc,
        }
        if log.status == "ok":
            says = [e.utc for e in log.entries if e.frm == "Rab" and e.kind == "say"]
            board["rab"]["last_say_utc"] = max(says) if says else None
    except Exception as exc:
        board["log"] = {
            "log_status": "UNREAD",
            "reason": (f"state/room.md could not be read ({type(exc).__name__}: "
                       f"{clip(exc, 90)}) - run `python room.py init`, and check nothing else "
                       f"holds the file open."),
            "count": None, "torn": None, "debris": None, "bytes": None,
            "read_utc": utc_now(),
        }
    return board


# ---------------------------------------------------------------- a board on the terminal

def board_lines(board=None):
    """`room.py status` and the catcher's --once summary print this. One line per claim, the
    layer named on every line - the terminal gets the same distillation the UI gets."""
    b = board or render_board()
    out = [f"relay-room board · {b['utc']}   thresholds from {b.get('thresholds_source')}"]
    s = b["server"]
    out.append(f"  server   {s['rendered']:<8} pid={s.get('pid')} port={s.get('port')} "
               f"token={s.get('token_mode')} age={age_phrase(s.get('age_s'))}")
    if s.get("reason"):
        out.append(f"           -> {s['reason']}")
    for lane, L in b["lanes"].items():
        out.append(f"  {lane:<8} AGENT {L['rendered_agent']:<15} MODEL {L['rendered_model']}")
        if L.get("agent_reason"):
            out.append(f"           agent -> {L['agent_reason']}")
        if L.get("model_reason"):
            out.append(f"           model -> {L['model_reason']}")
        fl = L.get("in_flight")
        if fl:
            out.append(f"           flight {fl.get('id')} {fl.get('stage')} "
                       f"({fl.get('stage_index')}/8) age={age_phrase(fl.get('age_s'))}"
                       + ("  STALLED" if fl.get("stalled") else ""))
    lg = b["log"]
    out.append(f"  log      {lg['log_status']:<8} entries={lg['count']} torn={lg['torn']} "
               f"debris={lg['debris']} bytes={lg['bytes']} read={lg['read_utc']}")
    if lg.get("reason"):
        out.append(f"           -> {lg['reason']}")
    return out


if __name__ == "__main__":                     # a library, but readable from a terminal
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("\n".join(board_lines()))
