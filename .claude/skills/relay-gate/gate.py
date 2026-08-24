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
    body = io.open(a.body, encoding="utf-8").read() if a.body != "-" else sys.stdin.read()
    mid = next_id(a.as_model, data)
    header = f"## {utc_now()} · ⟨from: {a.as_model}⟩ → ⟨to: {a.to}⟩ · ⟨msg: {mid}⟩"
    entry = header + "\n\n" + body.strip("\n") + "\n"
    with io.open(relay_path(), "a", encoding="utf-8", newline="") as fh:
        fh.write("\n" + entry)              # APPEND ONLY
    dg = digest(extract_entry(mid) or entry)
    data["sent"].append({
        "id": mid, "to": a.to, "utc": utc_now(), "digest": dg,
        "subject": a.subject, "ticket": a.ticket, "requires_ack": not a.no_ack,
    })
    if not a.no_ack:
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
    return 0


def cmd_ticket(a):
    d, st = load(a.as_model)
    if st == "UNREAD":
        print("UNREAD: run `init` first", file=sys.stderr)
        return 1
    d["current_ticket"] = None if a.id.lower() in ("none", "-", "clear") else a.id
    d["state"] = a.state
    save(a.as_model, d, a.as_model)
    print(f"{a.as_model}: ticket={d['current_ticket']} state={d['state']}")
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
    sp.set_defaults(fn=cmd_post)
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
