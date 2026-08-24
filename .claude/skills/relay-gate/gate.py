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
import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROTOCOL = "fp-relay-ack/v1"
MODELS = ("Fable", "Codex")
STATES = ("idle", "working", "blocked-on-ack", "blocked-on-rab", "UNREAD")


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
    }


def load(model: str):
    """Returns (data, status). status is 'ok' or 'UNREAD' - a failed read NEVER returns a
    healthy-looking empty state."""
    p = ack_path(model)
    if not p.exists():
        return None, "UNREAD"
    try:
        d = json.loads(io.open(p, encoding="utf-8").read())
    except Exception:
        return None, "UNREAD"
    if not isinstance(d, dict) or d.get("protocol") != PROTOCOL or d.get("writer") != model:
        return None, "UNREAD"
    for key in ("sent", "confirmed"):
        if not isinstance(d.get(key), list):
            return None, "UNREAD"
    if not isinstance(d.get("escalations", []), list):   # added S108; absent is fine (back-compat)
        return None, "UNREAD"
    d.setdefault("escalations", [])
    return d, "ok"


def save(model: str, data: dict, as_model: str) -> None:
    if model != as_model:
        raise SystemExit(
            f"REFUSED: {as_model} may not write {ack_path(model).name} - single-writer law "
            "(RELAY-ACK-PROTOCOL.md). Each model writes only its own file."
        )
    data["updated_utc"] = utc_now()
    p = ack_path(model)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")           # .part-then-rename: the repo's own publish invariant
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


# ---------- relay parsing (read-only, never edits) ----------

MSG_RE = re.compile(r"MSG-(FAB|CDX)-(\d{4})")

# An entry boundary in relay.md, by the log's OWN grammar. Used to bound what a digest seals -
# see extract_entry. Deliberately anchored on the ⟨msg:⟩ stamp: a "## " line inside a body is
# prose, and treating it as a boundary is how 76% of an escalation escaped its own seal.
ENTRY_HEADER_RE = re.compile(r"^## .*⟨msg:\s*MSG-(?:FAB|CDX)-\d{4}⟩")


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
DONE_SLOT_RE = re.compile(r"^\*\*DONE\b[^\n]*", re.M)
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
BEAT_STALE_MIN = 45


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
    name = a.model.strip()
    if len(name) < 3:
        print("REFUSED: name the model, not an abbreviation (>=3 chars).", file=sys.stderr)
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


def cmd_post(a):
    announce_bus("post")
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

    body = io.open(a.body, encoding="utf-8").read() if a.body != "-" else sys.stdin.read()
    mid = next_id(a.as_model, data)
    header = f"## {utc_now()} · ⟨from: {a.as_model}⟩ → ⟨to: {a.to}⟩ · ⟨msg: {mid}⟩"
    entry = header + "\n\n" + body.strip("\n") + "\n"
    with io.open(relay_path(), "a", encoding="utf-8", newline="") as fh:
        fh.write("\n" + entry)              # APPEND ONLY
    dg = digest(extract_entry(mid) or entry)
    row = {
        "id": mid, "to": a.to, "utc": utc_now(), "digest": dg,
        "subject": a.subject, "ticket": a.ticket, "requires_ack": not a.no_ack,
    }
    if a.override:
        row["override_reason"] = a.override      # a bypass is always on the record
    if a.serves:
        row["serves_escalation"] = a.serves      # the carve-out is a claim, so it is recorded
    data["sent"].append(row)
    # Keep current_ticket TRUE (S109). Only `ticket` used to write this field, so `post --ticket`
    # never advanced it: this lane read T-003 through T-004, T-005 and T-006, and the board
    # printed that stale value to Rab with confidence. Guard A compares against it, so the
    # staleness was not cosmetic - it made the guard misfire both ways.
    if a.ticket:
        data["current_ticket"] = a.ticket
    # GUARD B, second half (S108): posting must never DOWNGRADE blocked-on-rab. The original
    # guard stopped a model ENTERING that state silently; nothing stopped it LEAVING by side
    # effect. Found 2026-08-24 while about to post during a live escalation.
    if not a.no_ack and data.get("state") != "blocked-on-rab":
        data["state"] = "blocked-on-ack"
    save(a.as_model, data, a.as_model)
    print(f"posted {mid} -> {a.to}  digest {dg[:19]}…  state={data['state']}")
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
    print(f"relay-gate board · {utc_now()}")
    for m in MODELS:
        d, st = load(m)
        if st == "UNREAD":
            print(f"  {m:<6} UNREAD (skill not on, or file malformed)")
            continue
        print(f"  {m:<6} state={d['state']:<15} ticket={d.get('current_ticket')}  "
              f"sent={len(d['sent'])} confirmed={len(d['confirmed'])}  updated={d['updated_utc']}")
        print(f"         lane {m} · occupant {occupant_of(d)}")
        for ln in render_beat(d):
            print(ln)
    pending = []
    for m in MODELS:
        d, st = load(m)
        if st == "ok":
            pending += [(m, e) for e in d.get("escalations", []) if e.get("state") == "open"]
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
    return 0


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
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    if len(a.asking.strip()) < 15:
        print("REFUSED: name what Rab must decide, in a sentence (>=15 chars).", file=sys.stderr)
        return 1
    peer = other(a.as_model)
    ticket = a.ticket or d.get("current_ticket")
    mid = next_id(a.as_model, d)
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
    header = f"## {utc_now()} · ⟨from: {a.as_model}⟩ → ⟨to: {peer}⟩ · ⟨msg: {mid}⟩"
    entry = header + "\n\n" + body
    with io.open(relay_path(), "a", encoding="utf-8", newline="") as fh:
        fh.write("\n" + entry)
    dg = digest(extract_entry(mid) or entry)
    d["sent"].append({"id": mid, "to": peer, "utc": utc_now(), "digest": dg,
                      "subject": "ESCALATION: " + a.asking.strip()[:60], "ticket": ticket,
                      "requires_ack": True})
    d["escalations"].append({"utc": utc_now(), "ticket": ticket, "asking": a.asking.strip(),
                             "why": (a.why or "").strip() or None, "msg_id": mid, "state": "open"})
    d["state"] = "blocked-on-rab"
    save(a.as_model, d, a.as_model)
    print(f"escalated {mid} -> {peer}   state=blocked-on-rab")
    print(f"  asking Rab: {a.asking.strip()}")
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
            state, discharged = ("DISCH(self)" if d.get("self_reported") else "DISCHARGED"), discharged + 1
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
    if a.enforce and (owed or unread):
        # Fail closed, the same law as the FULL STOP's unread branch: a commitment that cannot
        # be shown reported is not a commitment that was reported.
        print(f"MEASURED: {owed} owed, {unread} unread — D2 is not discharged.", file=sys.stderr)
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
