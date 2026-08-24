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


def ack_path(model: str) -> Path:
    return coord_dir() / f"ack-{model.lower()}.json"


def relay_path() -> Path:
    return coord_dir() / "relay.md"


def other(model: str) -> str:
    return MODELS[1] if model == MODELS[0] else MODELS[0]


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
    p = ack_path(a.as_model)
    if p.exists():
        print(f"already on: {p.name}")
        return 0
    save(a.as_model, blank(a.as_model), a.as_model)
    print(f"relay-gate ON for {a.as_model}: {p.name} created (state idle)")
    print(f"the protocol is LIVE only when BOTH ack files exist and Rab has signed it")
    return 0


def cmd_post(a):
    data, st = load(a.as_model)
    if st == "UNREAD":
        print(f"UNREAD: {ack_path(a.as_model).name} missing or malformed - run `init` first", file=sys.stderr)
        return 1
    # GUARD A (S108): never issue a NEW ticket into a recipient that is already working.
    # On 2026-08-24 a 90-second-stale board read manufactured a duplicate ticket; the tool now
    # refuses what care did not. Notices always pass (no --ticket, or the ticket they already
    # hold). --override "<reason>" bypasses and RECORDS the reason - never silently.
    if a.ticket and not a.override:
        theirs, st_theirs = load(a.to)
        if st_theirs == "ok" and theirs.get("state") == "working" and theirs.get("current_ticket") != a.ticket:
            print(f"REFUSED: {a.to} is working on {theirs.get('current_ticket')} — issuing {a.ticket} "
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
    data["sent"].append(row)
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
    pending = []
    for m in MODELS:
        d, st = load(m)
        if st == "ok":
            pending += [(m, e) for e in d.get("escalations", []) if e.get("state") == "open"]
    if pending:
        print("\n  AWAITING RAB — his decision queue:")
        for m, e in pending:
            print(f"    [{e.get('ticket')}] from {m}: {e['asking']}")
            if e.get("why"):
                print(f"       why not settled between us: {e['why']}")
    return 0


def cmd_ticket(a):
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
    d["current_ticket"] = None if a.id.lower() in ("none", "-", "clear") else a.id
    d["state"] = a.state
    save(a.as_model, d, a.as_model)
    print(f"{a.as_model}: ticket={d['current_ticket']} state={d['state']}")
    return 0


def cmd_escalate(a):
    """Announce to the peer that you are going to Rab, THEN block on him.

    Rab's rule, 2026-08-24: 'when you want to come to me, let each other know as protocol.'
    The peer always learns what the principal is being asked, and why, before he is asked."""
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
    trailer = "Claude Fable 5" if a.as_model == "Fable" else "OpenAI Codex"
    body = (
        f"**RECAP.** ⟨claimed: {a.as_model}⟩ **ESCALATION — going to Rab.**\n\n"
        f"- **Ticket:** {ticket}\n"
        f"- **What he must decide:** {a.asking.strip()}\n"
        f"- **Why it cannot be settled between us:** {a.why.strip() if a.why else '(not stated)'}\n\n"
        f"Announced to {peer} **before** he is asked — no back-channel to the principal. My state "
        f"is now `blocked-on-rab`, which no model may clear.\n\n"
        f"**FOR RAB.** {a.as_model} says: a decision is queued for you — `gate.py status` shows it.\n\n"
        f"Model trailer: `{trailer}` · authorship claim only, never Rab's authority.\n"
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
    while True:
        theirs, st = load(other(a.as_model))
        mine, st_mine = load(a.as_model)
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
    sp = add_as(sub.add_parser("post"))
    sp.add_argument("--to", required=True, choices=MODELS)
    sp.add_argument("--subject", required=True)
    sp.add_argument("--body", required=True, help="file with the entry body, or - for stdin")
    sp.add_argument("--ticket", default=None)
    sp.add_argument("--no-ack", action="store_true")
    sp.add_argument("--override", default=None,
                    help="bypass GUARD A (recipient is working) - the reason is RECORDED")
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
    sp.set_defaults(fn=cmd_ticket)
    sp = add_as(sub.add_parser("watch"))
    sp.add_argument("--interval", type=float, default=10.0)
    sp.set_defaults(fn=cmd_watch)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
