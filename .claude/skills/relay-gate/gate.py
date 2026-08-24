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


def next_id(model: str, data: dict) -> str:
    prefix = "FAB" if model == "Fable" else "CDX"
    n = 0
    for row in data.get("sent", []):
        m = MSG_RE.search(row.get("id", ""))
        if m and m.group(1) == prefix:
            n = max(n, int(m.group(2)))
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
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


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
    if a.ticket and not a.override:
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
            print(FULL_STOP_REMEDY, file=sys.stderr)
            return 1
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
    if claimed and claimed != mine_dg:
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
