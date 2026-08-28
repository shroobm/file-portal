#!/usr/bin/env python3
"""Tripwires for gate.py. Every law is proven BOTH ways: a fixture that must PASS and,
for each rule, a fixture that must FAIL. (The 2026-08-22 mapping pass shipped a false
byte-level claim from a probe nobody had controlled; this file is that lesson, vendored.)"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

GATE = str(Path(__file__).resolve().parent / "gate.py")
SKILL = Path(__file__).resolve().parent / "SKILL.md"
BUS = Path(__file__).resolve().parents[3] / "coordination" / "BUS-STANDARD.md"
PY = sys.executable
PASS = FAIL = 0


def run(args, coord, expect=0, extra_env=None):
    env = dict(os.environ, FP_COORD=str(coord))
    env.update(extra_env or {})
    r = subprocess.run([PY, GATE] + args, env=env, capture_output=True, text=True)
    return r


def spawn(args, coord, extra_env=None):
    """Start a real gate CLI process for lock/transaction races."""
    env = dict(os.environ, FP_COORD=str(coord), PYTHONDONTWRITEBYTECODE="1")
    env.update(extra_env or {})
    return subprocess.Popen([PY, GATE] + args, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)


def finish(process):
    stdout, stderr = process.communicate(timeout=30)
    return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)


def t(name, cond):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}")
        FAIL += 1


def disagreement_doctrine(skill_text, bus_text):
    """Documentation tripwire for signed S110 B2 and its runtime disposition."""
    skill = " ".join(skill_text.replace("*", "").replace("`", "").split()).lower()
    bus = " ".join(bus_text.replace("*", "").replace("`", "").split()).lower()
    return all(phrase in skill for phrase in (
        "two complete rounds",
        "both readings, both probes",
        "session close proceeds",
        "no forced alignment",
        "never clears blocked-on-rab",
        "full stop",
        "both round-one confirmations must precede",
        "no later than the terminal disposition",
        "request digest",
        "semantic equivalence",
        "origin occupant",
        "source entry digests",
        "stable dedicated lock",
        "bounded exact-retry recovery",
        "journal is cleared only after",
        "ordinary mutations refuse",
    )) and all(phrase in bus for phrase in (
        "disagreement terminates without forced alignment",
        "both readings and both probes",
        "blocked-on-rab",
        "full stop",
        "both round-one receipts",
        "all four receipts are no later than the terminal disposition",
        "semantic equivalence",
        "os advisory transaction lock",
        "origin occupant",
        "source entry digests",
        "bounded exact-retry recovery",
        "pending or malformed intents block ordinary sidecar mutation",
    ))


def commit_last_doctrine(skill_text):
    skill = " ".join(skill_text.replace("*", "").replace("`", "").split()).lower()
    return all(phrase in skill for phrase in (
        "commit-last ordering for sidecars",
        "commit last, then make no further",
        "write → commit → nothing",
        "the last write must be the commit",
    ))


def body_file(coord, text):
    p = Path(coord) / "_body.md"
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    return str(p)


def main():
    with tempfile.TemporaryDirectory(prefix="relay-gate-selftest-") as tmp:
        coord = Path(tmp)
        io.open(coord / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")

        # T1 positive: init turns the skill on and writes a well-formed file
        r = run(["init", "--as", "Fable"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("init creates a valid sidecar (state idle)", r.returncode == 0 and d["state"] == "idle" and d["writer"] == "Fable")
        t("new sidecars carry the backward-compatible disagreement ledger",
          d.get("disagreements") == [])

        # T2 negative: single-writer law - Fable may not write Codex's file
        import gate as _  # noqa - import path check only if colocated
        try:
            sys.path.insert(0, str(Path(GATE).parent))
            import importlib
            g = importlib.import_module("gate")
            os.environ["FP_COORD"] = str(coord)
            refused = False
            try:
                g.save("Codex", g.blank("Codex"), "Fable")
            except SystemExit:
                refused = True
            t("single-writer law refuses a cross-write", refused)
        except Exception:
            t("single-writer law refuses a cross-write", False)

        # Concurrency guard: two same-lane commands loaded the same raw revision. Only the first
        # may publish; the second must reload instead of replacing the whole newer sidecar.
        first, fst = g.load("Fable")
        stale, sst = g.load("Fable")
        first["occupant"] = "first concurrent writer"
        g.save("Fable", first, "Fable")
        stale["occupant"] = "stale concurrent writer"
        stale_refused = False
        try:
            g.save("Fable", stale, "Fable")
        except SystemExit as error:
            stale_refused = "stale" in str(error).lower()
        disk = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("optimistic save refuses a stale whole-sidecar overwrite",
          fst == sst == "ok" and stale_refused
          and disk.get("occupant") == "first concurrent writer")
        t("private raw revision metadata is never serialized",
          "_gate_loaded_raw_revision" not in disk)

        fresh, fresh_status = g.load("Fable")
        fresh["occupant"] = "fresh reloaded writer"
        fresh_saved = True
        try:
            g.save("Fable", fresh, "Fable")
        except SystemExit:
            fresh_saved = False
        disk = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("a fresh reload saves successfully after the concurrent winner",
          fresh_status == "ok" and fresh_saved
          and disk.get("occupant") == "fresh reloaded writer")
        reset, _ = g.load("Fable")
        reset["occupant"] = None
        g.save("Fable", reset, "Fable")

        run(["init", "--as", "Codex"], coord)

        first_use = Path(tmp) / "concurrent-absent-lock"
        first_use.mkdir()
        io.open(first_use / "relay.md", "w", encoding="utf-8", newline="\n").write(
            "# relay (first-use fixture)\n")
        first_fable = spawn(["init", "--as", "Fable"], first_use)
        first_codex = spawn(["init", "--as", "Codex"], first_use)
        first_results = finish(first_fable), finish(first_codex)
        t("concurrent first use initializes one stable lock byte without LL corruption",
          all(result.returncode == 0 for result in first_results)
          and (first_use / ".relay-gate.lock").read_bytes() == b"L")

        # T3 positive: post appends, records, and blocks on ack
        bf = body_file(coord, "**RECAP.** first ticket\n\n**FOR RAB.** none\n")
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "first", "--body", bf], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        relay = io.open(coord / "relay.md", encoding="utf-8").read()
        t("post appends to the log and records the send", r.returncode == 0 and len(d["sent"]) == 1 and "MSG-FAB-0001" in relay)
        t("post sets state blocked-on-ack", d["state"] == "blocked-on-ack")

        # T4 negative: check before any confirmation must NOT report confirmed
        r = run(["check", "--as", "Fable"], coord)
        t("check before confirmation reports AWAITING", "AWAITING" in r.stdout and "CONFIRMED" not in r.stdout)

        # T5 positive: inbox shows the pending message on the other side
        r = run(["inbox", "--as", "Codex"], coord)
        t("inbox surfaces the pending ticket", "MSG-FAB-0001" in r.stdout)

        # T6 negative: a confirmation without a restatement is refused (the anti-bit-flip rule)
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-0001", "--restatement", "ok"], coord)
        t("confirmation without a real restatement is refused", r.returncode == 1 and "REFUSED" in r.stderr)

        # T7 negative: confirming an id that is not in the log is refused
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-9999", "--restatement", "a full restatement here"], coord)
        t("confirming a non-existent id is refused", r.returncode == 1)

        # T8 positive: a real confirmation verifies the digest and records
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-0001",
                 "--restatement", "understood: post the first ticket and wait"], coord)
        d = json.loads(io.open(coord / "ack-codex.json", encoding="utf-8").read())
        t("confirm records with a verified digest", r.returncode == 0 and len(d["confirmed"]) == 1)

        # T9 positive: the sender's check now settles to idle
        r = run(["check", "--as", "Fable"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("check sees the flip and the agent settles", "CONFIRMED" in r.stdout and d["state"] == "idle")

        # T10 negative: a tampered log makes the digest mismatch a MEASURED RED
        bf2 = body_file(coord, "**RECAP.** second ticket\n")
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "second", "--body", bf2], coord)
        txt = io.open(coord / "relay.md", encoding="utf-8").read()
        io.open(coord / "relay.md", "w", encoding="utf-8", newline="\n").write(txt.replace("second ticket", "SECOND ticket TAMPERED"))
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-0002",
                 "--restatement", "understood: the second ticket as written"], coord)
        t("a tampered entry is a measured RED, not a shrug", r.returncode == 1 and "digest mismatch" in r.stderr)

        # T11 negative: a malformed sidecar renders UNREAD, never idle
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write("{ this is not json")
        r = run(["status"], coord)
        t("a malformed sidecar reads UNREAD, never idle", "UNREAD" in r.stdout and "Codex idle" not in r.stdout)

        # T12 negative: a missing sidecar also reads UNREAD (absence != healthy)
        os.remove(coord / "ack-codex.json")
        r = run(["check", "--as", "Fable"], coord)
        t("a missing counterpart reads UNREAD, not two-party", "UNREAD" in r.stdout)

        # ---- GUARD A: never issue a NEW ticket into a working recipient (S108) ----
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "working", "current_ticket": "T-002",
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        bf3 = body_file(coord, "**RECAP.** third\n")

        # T13 negative: a NEW ticket into a working recipient is refused
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "dup",
                 "--body", bf3, "--ticket", "T-009"], coord)
        t("GUARD A refuses a new ticket into a working recipient", r.returncode == 1 and "REFUSED" in r.stderr)

        # T14 positive: a NOTICE (no ticket) always passes, even mid-work
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "notice", "--body", bf3], coord)
        t("GUARD A lets a no-ticket notice through", r.returncode == 0)

        # T15 positive: the ticket they ALREADY hold passes (a correction, not a duplicate)
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "same-ticket",
                 "--body", bf3, "--ticket", "T-002"], coord)
        t("GUARD A allows a post on the ticket they already hold", r.returncode == 0)

        # T16 positive: --override bypasses AND records the reason
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "urgent", "--body", bf3,
                 "--ticket", "T-010", "--override", "hardware on fire"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("GUARD A override works and is recorded, never silent",
          r.returncode == 0 and any(s.get("override_reason") == "hardware on fire" for s in d["sent"]))

        # T17 positive: an idle recipient takes a new ticket normally
        c = json.loads(io.open(coord / "ack-codex.json", encoding="utf-8").read())
        c["state"] = "idle"; c["current_ticket"] = None
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(json.dumps(c, indent=2))
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "ok", "--body", bf3, "--ticket", "T-011"], coord)
        t("GUARD A passes a new ticket to an idle recipient", r.returncode == 0)

        # ---- GUARD B: no silent trip to Rab (S108, Rab's rule) ----
        # T18 negative: blocked-on-rab without an announced escalation is refused
        r = run(["ticket", "--as", "Fable", "--id", "T-011", "--state", "blocked-on-rab"], coord)
        t("GUARD B refuses blocked-on-rab with no announced escalation",
          r.returncode == 1 and "announced escalation" in r.stderr)

        # T19 negative: an escalation with no real ask is refused
        r = run(["escalate", "--as", "Fable", "--asking", "help"], coord)
        t("GUARD B refuses an escalation that names no decision", r.returncode == 1)

        # T20 positive: escalate announces to the peer, records, and blocks on Rab
        r = run(["escalate", "--as", "Fable", "--asking", "which book breathes first for C0",
                 "--why", "the choice is his corpus, not ours", "--ticket", "T-011"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        relay = io.open(coord / "relay.md", encoding="utf-8").read()
        t("GUARD B escalation posts to the peer and sets blocked-on-rab",
          r.returncode == 0 and d["state"] == "blocked-on-rab"
          and len([e for e in d["escalations"] if e["state"] == "open"]) == 1
          and "ESCALATION" in relay)

        # T21 positive: the board surfaces Rab's decision queue
        r = run(["status"], coord)
        t("the board shows AWAITING RAB with the ask",
          "AWAITING RAB" in r.stdout and "which book breathes first" in r.stdout)

        # T22 positive: recording his decision resolves it and settles the agent
        esc = [e for e in d["escalations"] if e["state"] == "open"][0]
        r = run(["resolve", "--as", "Fable", "--id", esc["msg_id"],
                 "--decision", "he named the book and signed the GO"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("recording his decision resolves the escalation and settles to idle",
          r.returncode == 0 and d["state"] == "idle"
          and d["escalations"][-1]["state"] == "resolved")

        # T24 negative: posting while blocked-on-rab must NOT clear it (Guard B, second half)
        run(["escalate", "--as", "Fable", "--asking", "a second decision only Rab may make"], coord)
        bf4 = body_file(coord, "**RECAP.** notice during escalation\n")
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "notice", "--body", bf4], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("posting during an escalation does not clear blocked-on-rab", d["state"] == "blocked-on-rab")

        # T25 negative: CHECK while blocked-on-rab must NOT clear it either (Guard B, third
        # path, S109). The second half covered `post` alone, so merely asking "did mine land?"
        # cleared his gate - every sent message was awaiting an ACK, so check assigned
        # blocked-on-ack straight over blocked-on-rab. Found live during the T-005 escalation.
        r = run(["check", "--as", "Fable"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("check during an escalation does not clear blocked-on-rab",
          r.returncode == 0 and d["state"] == "blocked-on-rab")

        # T26 positive control: the guard freezes ONLY blocked-on-rab. With his gate released,
        # check must still move the state - without this, T25 cannot tell a working guard from
        # a check that quietly stopped writing state at all.
        esc2 = [e for e in d["escalations"] if e["state"] == "open"][0]
        run(["resolve", "--as", "Fable", "--id", esc2["msg_id"],
             "--decision", "he ruled and released the gate"], coord)
        r = run(["check", "--as", "Fable"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("check still sets blocked-on-ack when Rab's gate is not held",
          d["state"] == "blocked-on-ack")

        # T23 negative: resolving an id with no open escalation is refused
        r = run(["resolve", "--as", "Fable", "--id", "MSG-FAB-9999", "--decision", "made this up"], coord)
        t("resolving a non-existent escalation is refused", r.returncode == 1)

        # ---- LANE vs OCCUPANT (S109): a seat is not a model's name ----
        # gate.py used to hardcode `"Claude Fable 5" if lane == "Fable"`, so Opus 5's escalation -
        # the one message in Rab's decision queue - was stamped with a different model. Codex read
        # it correctly; the trailer lied. These three prove the lane can never name the occupant.

        # T27 negative: an UNDECLARED occupant must render UNDECLARED, never a guessed generation
        run(["escalate", "--as", "Fable", "--asking", "a decision with no occupant declared"], coord)
        relay = io.open(coord / "relay.md", encoding="utf-8").read()
        tail = relay[relay.rindex("ESCALATION"):]
        t("an undeclared occupant renders UNDECLARED, never a guessed model",
          "UNDECLARED" in tail and "Fable 5" not in tail and "Opus" not in tail)

        # T28 positive control: a DECLARED occupant reaches the trailer - so T27 cannot be
        # satisfied by a trailer that simply stopped naming anyone at all.
        r = run(["occupant", "--as", "Fable", "--model", "Claude Opus 5"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        run(["escalate", "--as", "Fable", "--asking", "a decision with the occupant declared"], coord)
        relay = io.open(coord / "relay.md", encoding="utf-8").read()
        tail = relay[relay.rindex("ESCALATION"):]
        t("a declared occupant reaches the escalation trailer",
          r.returncode == 0 and d["occupant"] == "Claude Opus 5" and "Claude Opus 5" in tail)

        # T29 negative: naming the LANE as the occupant is the exact conflation - refuse it
        r = run(["occupant", "--as", "Fable", "--model", "Fable"], coord)
        t("a lane name is refused as an occupant", r.returncode == 1 and "LANE name" in r.stderr)

        occupant_before = (coord / "ack-fable.json").read_bytes()
        r = run(["occupant", "--as", "Fable", "--model", "X" * 201], coord)
        t("an occupant over the 200-character provenance bound refuses with zero mutation",
          r.returncode == 1 and "3-200" in r.stderr
          and (coord / "ack-fable.json").read_bytes() == occupant_before)
        r = run(["occupant", "--as", "Fable", "--model", "Y" * 200], coord)
        bounded = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("the exact 200-character occupant bound remains a valid control",
          r.returncode == 0 and bounded.get("occupant") == "Y" * 200)
        run(["occupant", "--as", "Fable", "--model", "Claude Opus 5"], coord)

        # ---- FULL STOP + Guard A's stale field (S109, Rab signed) ----
        # "if anything escalates, tell both you and codex to stop... I want a full stop on an
        # escalation." Before this, escalate halted only the escalating lane and the peer kept
        # taking tickets - work continued past a question Rab had not answered.
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "idle", "occupant": "OpenAI Codex", "current_ticket": None,
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        # Fixture reset: the occupant cases above left escalations open, which the brand-new FULL
        # STOP correctly refuses to work through. Clear them Rab's way - by recording a decision -
        # rather than by editing state, so the reset itself obeys the law it is setting up.
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        for e in [x for x in d["escalations"] if x["state"] == "open"]:
            run(["resolve", "--as", "Fable", "--id", e["msg_id"], "--decision", "fixture reset"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        open_before = [e for e in d["escalations"] if e["state"] == "open"]
        bf5 = body_file(coord, "**RECAP.** work during a full stop\n")

        # T30 positive control: with NO escalation open, a ticketed post passes. Without this,
        # T31 cannot tell a working FULL STOP from a post that refuses everything.
        t("fixture has no open escalation before the full-stop cases", len(open_before) == 0)
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "work",
                 "--body", bf5, "--ticket", "T-030"], coord)
        t("a ticketed post passes while NO escalation is open", r.returncode == 0)

        # T31 negative: an open escalation halts the OTHER lane too - the whole point
        run(["escalate", "--as", "Fable", "--asking", "a decision that must halt both lanes"], coord)
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "work",
                 "--body", bf5, "--ticket", "T-031"], coord)
        t("FULL STOP halts the PEER lane, not just the escalator",
          r.returncode == 1 and "FULL STOP" in r.stderr)

        # T32 negative: a lane may not START work during a full stop
        r = run(["ticket", "--as", "Codex", "--id", "T-031", "--state", "working"], coord)
        t("FULL STOP refuses a lane starting work", r.returncode == 1 and "FULL STOP" in r.stderr)

        # T33 positive: a NOTICE still passes - it is how a lane says it has stopped
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "I have stopped",
                 "--body", bf5], coord)
        t("a notice still passes during a full stop", r.returncode == 0)

        # T34 positive: the board tells RAB what to do, in his own instruction's terms
        r = run(["status"], coord)
        t("the board renders FULL STOP and tells Rab to prompt the gates again",
          "FULL STOP" in r.stdout and "PROMPT THE RELAY GATES AGAIN" in r.stdout)

        # T35 positive: only Rab's recorded ruling lifts it
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        esc3 = [e for e in d["escalations"] if e["state"] == "open"][0]
        run(["resolve", "--as", "Fable", "--id", esc3["msg_id"], "--decision", "he ruled on it and released the gate"], coord)
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "resumed",
                 "--body", bf5, "--ticket", "T-035"], coord)
        t("resolving Rab's escalation lifts the full stop", r.returncode == 0)

        # T36 negative: GUARD A must FAIL CLOSED on a working lane that names no ticket.
        # It used to compare against current_ticket, a field nothing maintained, so a stale or
        # empty value made it both false-refuse and false-allow.
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "working", "occupant": "OpenAI Codex", "current_ticket": None,
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "dup",
                 "--body", bf5, "--ticket", "T-036"], coord)
        t("GUARD A fails closed when a working lane names no ticket",
          r.returncode == 1 and "names no current ticket" in r.stderr)

        # T37 positive: `post --ticket` now ADVANCES current_ticket, so the board stops lying
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "idle", "occupant": "OpenAI Codex", "current_ticket": None,
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "advance",
             "--body", bf5, "--ticket", "T-037"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        t("post --ticket advances the sender's current_ticket", d["current_ticket"] == "T-037")

        # ---- THE CARVE-OUT (S109, Rab signed): a full stop still permits work that SERVES
        # resolving the open escalation. Without it the stop is self-locking - it blocks the very
        # work that would lift it. It must stay NARROW or it is just a bypass with a nicer name.
        run(["escalate", "--as", "Fable", "--ticket", "T-050",
             "--asking", "a decision the carve-out must be able to serve"], coord)

        # T38 negative: the stop still bites without --serves (else T39 proves nothing)
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "unrelated",
                 "--body", bf5, "--ticket", "T-051"], coord)
        t("the stop still refuses ordinary ticketed work", r.returncode == 1 and "FULL STOP" in r.stderr)

        # T39 negative: --serves naming a ticket with NO open escalation is refused - the
        # carve-out may not become a general bypass
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "sneaky",
                 "--body", bf5, "--ticket", "T-051", "--serves", "T-999"], coord)
        t("--serves naming no open escalation is refused",
          r.returncode == 1 and "names no OPEN escalation" in r.stderr)

        # T40 positive: --serves naming the genuinely open escalation passes
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "the freshness card",
                 "--body", bf5, "--ticket", "T-050", "--serves", "T-050"], coord)
        t("--serves the OPEN escalation passes during a full stop", r.returncode == 0)

        # T41 positive: the carve-out is a CLAIM, so it is recorded - never silent
        d = json.loads(io.open(coord / "ack-codex.json", encoding="utf-8").read())
        # Indexed defensively: against a gate with no --serves at all the post never lands, and a
        # test that RAISES aborts the suite and hides every case after it. A missing guard must
        # read as FAIL, not as a stack trace.
        last = d["sent"][-1] if d.get("sent") else {}
        t("the carve-out claim is recorded on the row",
          last.get("serves_escalation") == "T-050")

        # T42 negative: an UNREAD board fails closed even WITH --serves. A lane that cannot be
        # read cannot be shown clear, and the carve-out must not become the hole in that.
        codex_backup = io.open(coord / "ack-codex.json", encoding="utf-8").read()
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write("{ not json")
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "during unread",
                 "--body", bf5, "--ticket", "T-050", "--serves", "T-050"], coord)
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(codex_backup)
        t("the carve-out still fails closed on an UNREAD board",
          r.returncode == 1 and "FULL STOP" in r.stderr)

        # ---- THE STATUS BEAT (S109, Rab: "info, status, what its doing, planning, completed,
        # verified"). The gate had STATE but no NARRATIVE. `verified` is mechanically expensive
        # on purpose - the tag law made structural instead of aspirational.

        # T43 negative: an empty beat is noise, and noise is refused
        r = run(["beat", "--as", "Fable"], coord)
        t("an empty beat is refused", r.returncode == 1 and "no content" in r.stderr)

        # T44 negative: --verified without --probe is refused. THIS is the tag law with teeth.
        r = run(["beat", "--as", "Fable", "--doing", "x", "--verified", "it all works"], coord)
        t("--verified without --probe is refused",
          r.returncode == 1 and "requires --probe" in r.stderr)

        # T45 negative: two claims and one probe is not two probes
        r = run(["beat", "--as", "Fable", "--doing", "x", "--verified", "a", "--verified", "b",
                 "--probe", "ran one thing"], coord)
        t("each verified claim must name its OWN probe", r.returncode == 1)

        # T46 positive control: a real beat publishes and carries its probe through to the board.
        # Without this, T44/T45 could be satisfied by a beat that refuses everything.
        r = run(["beat", "--as", "Fable", "--doing", "writing the card",
                 "--planning", "post it then stop", "--completed", "the disclosure standard",
                 "--verified", "suite is green", "--probe", "selftest.py -> 44/44 exit 0",
                 "--needs", "Codex to confirm MSG-FAB-0016"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        b = d.get("beat") or {}
        t("a real beat publishes with its probe attached",
          r.returncode == 0 and b.get("doing") == "writing the card"
          and b["verified"][0]["probe"].startswith("selftest.py"))
        r = run(["status"], coord)
        t("the board renders the beat, probe and all",
          "writing the card" in r.stdout and "selftest.py -> 44/44" in r.stdout)

        # T47 negative: a lane that has published NO beat reads UNREAD, never idle, never blank
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "idle", "occupant": "OpenAI Codex", "current_ticket": None,
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        r = run(["status"], coord)
        t("a lane with no beat renders UNREAD, not idle and not blank",
          "beat UNREAD" in r.stdout)

        # T48 negative: an OLD beat renders STALE. Absence of an update is not evidence of calm.
        c = json.loads(io.open(coord / "ack-codex.json", encoding="utf-8").read())
        c["beat"] = {"utc": "2020-01-01T00:00Z", "doing": "something long ago",
                     "completed": [], "verified": []}
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(json.dumps(c, indent=2))
        r = run(["status"], coord)
        t("an old beat renders STALE, never healthy", "STALE" in r.stdout)

        # T49 negative: an unparseable beat timestamp is UNREAD, not age-zero
        c["beat"]["utc"] = "not a timestamp"
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(json.dumps(c, indent=2))
        r = run(["status"], coord)
        t("an unreadable beat timestamp is UNREAD, not fresh", "timestamp is unreadable" in r.stdout)

        # ---- CR-CDX-0002 COMPLIANCE (Rab signed 2026-08-24, with this repair as the condition) ----
        # The card was endorsed by BOTH models and neither had run it against the artifact. When
        # one of us finally did, `escalate` failed it in six places - in the very message that
        # asked Rab to sign it. This census is that check, mechanised, so no generated entry can
        # drift out of the contract again without the suite saying so.
        run(["escalate", "--as", "Fable", "--ticket", "T-060",
             "--asking", "a decision that must be carried in the signed envelope",
             "--why", "authority by domain, not deadlock"], coord)
        relay = io.open(coord / "relay.md", encoding="utf-8").read()
        entry = relay[relay.rindex("## ") :]
        OUTER = ["**RECAP", "**FOR RAB.**", "**SUGGESTED PROMPT**"]
        INNER = ["**GROUND.**", "**ASK.**", "**DONE.**", "**BOUNDS.**", "**ROUTE.**"]

        # T50 negative: clause 1 - the three-part outer envelope on EVERY entry
        missing_outer = [s for s in OUTER if entry.count(s) != 1]
        t("clause 1: a generated escalation carries the three-part envelope exactly once",
          not missing_outer)

        # T51 negative: clause 2 - the five inner slots, exactly once each, IN ORDER
        missing_inner = [s for s in INNER if entry.count(s) != 1]
        positions = [entry.find(s) for s in INNER]
        t("clause 2: the five inner slots appear exactly once, in order",
          not missing_inner and positions == sorted(positions))

        # T52 positive control: the census can actually FAIL. Without this, T50/T51 could be
        # satisfied by a census that finds every marker in any text handed to it.
        fake = "**RECAP** only, with nothing else in it at all"
        t("control: the same census fails on an entry that lacks the sections",
          [s for s in OUTER if fake.count(s) != 1] != [])

        # ---- T53: the gate agent's own sleep signal must not render UNREAD as silence ----
        # `watch` looped only when BOTH sidecars read ok. With one missing or malformed it looped
        # forever printing nothing, and to the monitor a lane sleeps on, "blind" and "quiet" are
        # the same picture. SYM-031 inside the wake-up mechanism itself.
        codex_backup2 = io.open(coord / "ack-codex.json", encoding="utf-8").read()
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write("{ nope")
        env = dict(os.environ, FP_COORD=str(coord))
        pr = subprocess.Popen([PY, GATE, "watch", "--as", "Fable", "--interval", "0.2"],
                              env=env, stdout=subprocess.PIPE, text=True)
        line = ""
        try:
            line = (pr.stdout.readline() or "")
        finally:
            pr.kill()
            try:
                pr.wait(timeout=5)
            except Exception:
                pass
        io.open(coord / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(codex_backup2)
        t("watch announces UNREAD instead of going quiet",
          line.startswith("UNREAD") and "BLIND, not quiet" in line)

        # ---- T54: the beat carries WHICH CODE the lane is running ----
        # Twice in one evening a lane reasoned about its peer's running code and got it wrong.
        # The sharper of the two: I probed the BUS ("I never posted the fix") and rendered the
        # result as a claim about a PROCESS ("your watcher is blind"). Codex had already
        # restarted. That is docs/45 Family 1 - the sentence describing the NEIGHBOUR of the
        # probe - committed inside a message about disclosure discipline. Nothing on the bus
        # said what code a lane ran, so drift was invisible by construction.
        run(["beat", "--as", "Fable", "--doing", "checking the revision stamp"], coord)
        d = json.loads(io.open(coord / "ack-fable.json", encoding="utf-8").read())
        rev = (d.get("beat") or {}).get("gate_rev")
        t("a beat records the gate revision it was written by, automatically",
          isinstance(rev, str) and len(rev) == 8 and rev != "UNDECLARED")
        r = run(["status"], coord)
        t("the board renders each lane's running revision", f"gate {rev}" in r.stdout)

        # T55 negative: a lane running DIFFERENT code is flagged, not quietly averaged over
        d["beat"]["gate_rev"] = "deadbeef"
        io.open(coord / "ack-fable.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, indent=2))
        r = run(["status"], coord)
        t("a lane running a different revision is flagged on the board",
          "deadbeef" in r.stdout and "this shell runs" in r.stdout)

        # ---- ID REUSE: the counter's floor is the APPEND-ONLY LOG, not the mutable sidecar
        # (S109). next_id took max() over the sidecar's sent[] alone. Restoring ack-fable.json
        # with `git checkout` during the 2026-08-24 repair dropped the sent row for MSG-FAB-0018,
        # the counter went BACKWARDS, and the next post minted MSG-FAB-0018 a second time -
        # relay.md permanently names two different entries by that id (relay.md:2111, :2125).
        #
        # S109 SINGLE-LANE DISCLOSURE: T56/T57 and the gate.py repair they cover were written and
        # checked by Claude agents ONLY - the Codex lane was out of budget, so there is NO
        # cross-vendor check on either. Discount the evidence accordingly.
        idr = Path(tmp) / "idreuse"
        idr.mkdir()

        def _lane(path, writer, sent):
            io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(
                {"writer": writer, "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                 "state": "idle", "occupant": "fixture", "current_ticket": None,
                 "sent": sent, "confirmed": [], "escalations": []}, indent=2))

        def _row(mid):
            return {"id": mid, "to": "Codex", "utc": "x", "digest": "sha256:x",
                    "subject": "fixture", "ticket": None, "requires_ack": True}

        def _log(path, ids):
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                "# relay (fixture)\n" + "".join(
                    f"\n## 2026-08-24T17:2{i}Z · ⟨from: Fable⟩ → ⟨to: Codex⟩ · ⟨msg: {m}⟩\n\n"
                    f"**RECAP.** fixture entry {m}\n"
                    for i, m in enumerate(ids)))

        bf6 = body_file(idr, "**RECAP.** a post after the sidecar was restored backwards\n")

        # T56 negative: THE INCIDENT, exactly. The log holds MSG-FAB-0018; the sidecar's sent[]
        # tops out at 0017 - the post-`git checkout` state. The next id must be 0019, and the
        # log must still name 0018 exactly once.
        _log(idr / "relay.md", ["MSG-FAB-0017", "MSG-FAB-0018"])
        _lane(idr / "ack-fable.json", "Fable", [_row("MSG-FAB-0017")])
        _lane(idr / "ack-codex.json", "Codex", [])
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "after the restore",
                 "--body", bf6], idr)
        relay = io.open(idr / "relay.md", encoding="utf-8").read()
        t("a restored sidecar cannot regress the counter into a live id",
          r.returncode == 0 and "MSG-FAB-0019" in r.stdout
          and relay.count("⟨msg: MSG-FAB-0018⟩") == 1
          and relay.count("⟨msg: MSG-FAB-0019⟩") == 1)

        # T57 positive control: the log is a FLOOR, not a replacement. Here the sidecar is AHEAD
        # of the log (0018 sent, its entry never appended) and the next id must still be 0019 -
        # so T56 cannot be satisfied by a fix that reads the log INSTEAD of sent[].
        _log(idr / "relay.md", ["MSG-FAB-0017"])
        _lane(idr / "ack-fable.json", "Fable", [_row("MSG-FAB-0017"), _row("MSG-FAB-0018")])
        _lane(idr / "ack-codex.json", "Codex", [])
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "sidecar ahead of log",
                 "--body", bf6], idr)
        t("the log is a floor, not a replacement: a sidecar ahead of it still wins",
          r.returncode == 0 and "MSG-FAB-0019" in r.stdout)

        # ---- D2 MADE MECHANICAL: `owed` / `discharge` (S109) ----
        # The Disclosure Standard states its own ceiling: "the triggers are enforced by
        # discipline, not by code." D2 - a DONE stated on the bus whose outcome was never
        # reported - is the one trigger that could be lifted out of discipline, because
        # `**DONE.**` is a DECLARED SLOT of the transaction contract rather than prose.
        # The specimen these fixtures reproduce is real: MSG-FAB-0020 announced a deliverable,
        # the peer CONFIRMED the message, and the deliverable was never produced.
        #
        # S109 SINGLE-LANE DISCLOSURE: T58-T68 and the gate.py commands they cover were written
        # and checked by Claude agents ONLY - the Codex lane was out of budget, so there is NO
        # cross-vendor check on any of it. Discount the evidence accordingly.
        owd = Path(tmp) / "owed"
        owd.mkdir()

        def _side(path, writer, sent, confirmed=()):
            io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(
                {"writer": writer, "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                 "state": "idle", "occupant": "fixture", "current_ticket": None,
                 "sent": sent, "confirmed": list(confirmed), "escalations": []}, indent=2))

        def _srow(mid, utc, ack=True):
            return {"id": mid, "to": "Codex", "utc": utc, "digest": "sha256:x",
                    "subject": "fixture", "ticket": None, "requires_ack": ack}

        def _dlog(path, entries):
            """entries: (from_lane, msg_id, done_clause_or_None)"""
            out = ["# relay (fixture)\n"]
            for n, (frm, mid, done) in enumerate(entries):
                to = "Codex" if frm == "Fable" else "Fable"
                out.append(f"\n## 2026-08-24T17:0{n}Z · ⟨from: {frm}⟩ → ⟨to: {to}⟩ · "
                           f"⟨msg: {mid}⟩\n\n**RECAP.** fixture {mid}\n")
                if done:
                    out.append(f"\n**DONE.** {done}\n")
            io.open(path, "w", encoding="utf-8", newline="\n").write("".join(out))

        def _fixture():
            _dlog(owd / "relay.md", [
                ("Fable", "MSG-FAB-0001", "I am now producing the freshness card you asked for."),
                ("Fable", "MSG-FAB-0002", None),          # a message that promises nothing
                ("Fable", "MSG-FAB-0003", "Complete when the harness is green."),
                ("Codex", "MSG-CDX-0001", "Complete when Fable confirms this entry."),
            ])
            _side(owd / "ack-fable.json", "Fable",
                  [_srow("MSG-FAB-0001", "2026-08-24T17:00Z"),
                   _srow("MSG-FAB-0002", "2026-08-24T17:01Z"),
                   _srow("MSG-FAB-0003", "2026-08-24T17:02Z")])
            # The peer CONFIRMED the promise. That is the whole trap.
            _side(owd / "ack-codex.json", "Codex", [],
                  [{"id": "MSG-FAB-0001", "from": "Fable", "confirmed_utc": "2026-08-24T17:05Z",
                    "digest": "sha256:x", "restatement": "read it"}])

        _fixture()
        r = run(["owed", "--as", "Fable"], owd)

        # T58 positive: a stated DONE with no discharge record reads OWED
        t("a DONE stated on the bus with no reported outcome reads OWED",
          r.returncode == 0 and "MSG-FAB-0001" in r.stdout and "OWED" in r.stdout)

        # T59 THE BITE: an ACK IS NOT A DISCHARGE. The tool SEES the confirmation - it prints
        # ack=CONFIRMED on the same row - and still refuses to call the outcome reported. A
        # version that collapsed the two columns would render MSG-FAB-0020 clean, which is the
        # exact failure the Disclosure Standard was written from.
        line1 = [ln for ln in r.stdout.splitlines() if "MSG-FAB-0001" in ln]
        t("a CONFIRMED message with an undischarged DONE is still OWED (an ack is not a discharge)",
          len(line1) == 1 and "OWED" in line1[0] and "ack=CONFIRMED" in line1[0])

        # T60 control: it parses the DECLARED SLOT, not "every message". Without this, T58 would
        # pass for a tool that simply listed the sent set and proved nothing about D2.
        # Both controls assert a POSITIVE alongside the absence. Written as a bare "X not in
        # stdout" they passed against the pre-change gate.py too - where `owed` is not a
        # subcommand at all, stdout is empty and every absence is trivially true. That is the
        # tautology S3 names, caught by running these against `git show HEAD:` before shipping.
        t("a message carrying no DONE slot is not reported as a commitment",
          r.returncode == 0 and "MSG-FAB-0001" in r.stdout and "MSG-FAB-0002" not in r.stdout)

        # T61 control: lane scoping - the PEER's DONE is not this lane's debt
        t("owed reports only this lane's own commitments",
          r.returncode == 0 and "MSG-FAB-0001" in r.stdout and "MSG-CDX-0001" not in r.stdout)

        # T62: --enforce is a MEASURED red, exit 1
        r = run(["owed", "--as", "Fable", "--enforce"], owd)
        t("owed --enforce exits 1 on a measured OWED", r.returncode == 1 and "MEASURED" in r.stderr)

        # T63 negative: an outcome cannot be reported before the promise that produced it
        r = run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0003", "--in", "MSG-FAB-0001",
                 "--outcome", "reported in an earlier message somehow"], owd)
        t("discharge refuses an --in that predates the commitment",
          r.returncode == 1 and "predates" in r.stderr)

        # T64 negative: nothing to discharge on a message that promised nothing
        r = run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0002", "--in", "MSG-FAB-0003",
                 "--outcome", "pretending this one carried a commitment"], owd)
        t("discharge refuses a message carrying no DONE slot",
          r.returncode == 1 and "no **DONE** slot" in r.stderr)

        # T65 negative: a lane discharges only its OWN commitments
        r = run(["discharge", "--as", "Fable", "--id", "MSG-CDX-0001", "--in", "MSG-FAB-0003",
                 "--outcome", "clearing the peer's commitment for it"], owd)
        t("discharge refuses another lane's commitment",
          r.returncode == 1 and "own commitments" in r.stderr.lower())

        # T66 positive: a real discharge lands and the board flips
        r = run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0001", "--in", "MSG-FAB-0003",
                 "--outcome", "the card was never produced; T-005 was withdrawn instead"], owd)
        rs = run(["owed", "--as", "Fable"], owd)
        line1 = [ln for ln in rs.stdout.splitlines() if "MSG-FAB-0001" in ln]
        t("a discharge reported in a later bus entry clears the commitment",
          r.returncode == 0 and len(line1) == 1 and "DISCHARGED" in line1[0]
          and "OWED" not in line1[0])

        # T67 negative: appends never erase - a second discharge is refused, not overwritten
        r = run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0001", "--in", "MSG-FAB-0003",
                 "--outcome", "a different story about the same commitment"], owd)
        t("a second discharge is refused rather than overwriting the first",
          r.returncode == 1 and "already discharged" in r.stderr)

        # T68 negative: UNREAD IS NOT A SKIP. With relay.md gone the command must fail loudly;
        # rendering "none owed" from a probe that could not run is the S4 defect.
        os.replace(str(owd / "relay.md"), str(owd / "relay.hidden"))
        r = run(["owed", "--as", "Fable"], owd)
        t("owed renders UNREAD, never a clean bill, when the log cannot be read",
          r.returncode == 1 and "UNREAD" in r.stderr and "none" not in r.stdout.lower())
        os.replace(str(owd / "relay.hidden"), str(owd / "relay.md"))

        # T69 negative: an unreadable PEER sidecar renders ack=UNREAD, never ack=awaiting -
        # a failed probe is not a negative observation.
        io.open(owd / "ack-codex.json", "w", encoding="utf-8", newline="\n").write("{ broken")
        r = run(["owed", "--as", "Fable"], owd)
        t("an unreadable peer sidecar renders ack=UNREAD, not ack=awaiting",
          r.returncode == 0 and "ack=UNREAD" in r.stdout and "ack=awaiting" not in r.stdout)

        # ---- T56-T60: THE THREE VIOLATIONS THE S109 CIRCLE FOUND, each reproduced ----
        # All three were live while this suite read 73/73 green. That is the point of writing
        # them down here: the suite could not see any of them, because none of their properties
        # had ever been stated as a test.
        cd = coord / "_circle"
        cd.mkdir(exist_ok=True)
        io.open(cd / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], cd)
        run(["init", "--as", "Codex"], cd)

        # T56 — THE SEAL MUST COVER THE WHOLE ENTRY. extract_entry ended the body at ANY "## "
        # line, so a markdown heading in a body truncated what the digest covers: 451 of 1861
        # chars sealed, with BOUNDS / ROUTE / FOR RAB / SUGGESTED PROMPT all OUTSIDE it. The FOR
        # RAB block is the part that tells the principal what he is being asked.
        run(["escalate", "--as", "Fable", "--asking",
             "Decide this\n## a heading inside the ask\nthat is the point"], cd)
        sys.path.insert(0, str(Path(GATE).parent))
        import importlib
        g2 = importlib.import_module("gate")
        os.environ["FP_COORD"] = str(cd)
        sealed = g2.extract_entry("MSG-FAB-0001") or ""
        full = io.open(cd / "relay.md", encoding="utf-8").read()
        whole = full[full.index("## 2026"):]
        t("the digest seals the WHOLE entry, not up to the first '## ' in a body",
          len(sealed) >= len(whole) - 3)
        t("…so FOR RAB and SUGGESTED PROMPT are inside the seal",
          "**FOR RAB.**" in sealed and "**SUGGESTED PROMPT**" in sealed)

        # T57 — NO CLAIM IS NOT A MATCH. With the sender's sidecar UNREAD there is no digest to
        # compare, and `confirm` fell through to printing "digest verified" - on a body that had
        # been rewritten from "convert the bundle" to "DELETE the bundle".
        cd2 = coord / "_circle2"
        cd2.mkdir(exist_ok=True)
        io.open(cd2 / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], cd2)
        run(["init", "--as", "Codex"], cd2)
        bfc = body_file(cd2, "**RECAP.** convert the bundle\n")
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "t", "--body", bfc], cd2)
        io.open(cd2 / "ack-fable.json", "w", encoding="utf-8", newline="\n").write("{ corrupted")
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-0001",
                 "--restatement", "you asked me to convert the bundle"], cd2)
        t("a confirmation with NO counter-claim is refused, never 'verified'",
          r.returncode == 1 and "NOTHING TO COMPARE" in r.stderr)

        # T58 control — and a REAL claim must still confirm, or T57 is satisfied by a confirm
        # that refuses everything.
        cd3 = coord / "_circle3"
        cd3.mkdir(exist_ok=True)
        io.open(cd3 / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], cd3)
        run(["init", "--as", "Codex"], cd3)
        bfd = body_file(cd3, "**RECAP.** an honest ticket\n")
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "t", "--body", bfd], cd3)
        r = run(["confirm", "--as", "Codex", "--id", "MSG-FAB-0001",
                 "--restatement", "understood: an honest ticket, nothing tampered"], cd3)
        t("control: a genuine claim still confirms", r.returncode == 0)

        # T59 — THE FULL STOP IS NOT OVERRIDABLE. --override is documented as a GUARD A bypass and
        # was silently crossing a halt Rab SIGNED, including its fail-closed branch.
        cd4 = coord / "_circle4"
        cd4.mkdir(exist_ok=True)
        io.open(cd4 / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], cd4)
        run(["init", "--as", "Codex"], cd4)
        run(["escalate", "--as", "Fable", "--ticket", "T-100",
             "--asking", "a decision only Rab may make here"], cd4)
        bfe = body_file(cd4, "**RECAP.** work\n")
        r = run(["post", "--as", "Codex", "--to", "Fable", "--subject", "w", "--body", bfe,
                 "--ticket", "T-101", "--override", "recipient looked idle to me"], cd4)
        t("--override does NOT lift a FULL STOP",
          r.returncode == 1 and "FULL STOP" in r.stderr)
        t("…and it says so, rather than refusing without a reason",
          "does NOT lift a FULL STOP" in r.stderr)

        # T60 control — GUARD A must STILL be overridable, or T59 is satisfied by an --override
        # that does nothing at all. Peer working, no escalation anywhere.
        io.open(cd3 / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps({"writer": "Codex", "protocol": "fp-relay-ack/v1", "updated_utc": "x",
                        "state": "working", "occupant": "OpenAI Codex", "current_ticket": "T-9",
                        "sent": [], "confirmed": [], "escalations": []}, indent=2))
        r = run(["post", "--as", "Fable", "--to", "Codex", "--subject", "urgent", "--body", bfd,
                 "--ticket", "T-777", "--override", "hardware on fire"], cd3)
        t("control: --override still bypasses GUARD A when no escalation is open",
          r.returncode == 0)

        # ---- T61-T63: the two `owed` false clears the S109 Circle found ----
        cd5 = coord / "_circle5"
        cd5.mkdir(exist_ok=True)
        io.open(cd5 / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], cd5)
        run(["init", "--as", "Codex"], cd5)
        for name, txt in (("a", "**RECAP.** a\n\n- **DONE.** inside a list item\n"),
                          ("b", "**GROUND.** t. **DONE.** mid-line\n"),
                          ("c", "**RECAP.** c\n\n**DONE.** at column zero\n")):
            bf = body_file(cd5, txt)
            run(["post", "--as", "Fable", "--to", "Codex", "--subject", name, "--body", bf], cd5)

        # T61 — a DONE not at column 0 was INVISIBLE. Measured 3 stated, 1 seen, --enforce exit 0,
        # while the docstring claimed the function "over-reports rather than under-reports".
        r = run(["owed", "--as", "Fable"], cd5)
        t("owed sees a DONE in a list item and mid-line, not only at column 0",
          "3 stated" in r.stdout)

        # T62 — A SELF-REPORT IS NOT A DISCHARGE UNDER --enforce. SKILL.md: "--in must name a
        # message of yours THE PEER CAN READ ON THE BUS, so a lane cannot clear its own
        # commitments privately." --enforce was passing a self-report at exit 0, refuting that
        # sentence verbatim on exactly MSG-FAB-0020's shape.
        run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0001", "--in", "MSG-FAB-0001",
             "--outcome", "cleared privately with nothing on the bus"], cd5)
        r = run(["owed", "--as", "Fable", "--enforce"], cd5)
        t("a SELF-REPORTED discharge does not satisfy --enforce",
          r.returncode == 1 and "self-reported" in r.stderr)

        # T63 control — a discharge reported in a LATER entry the peer can read must still clear,
        # or T62 is satisfied by an --enforce that refuses every discharge.
        bfd2 = body_file(cd5, "**RECAP.** the outcome, reported for the peer to read\n")
        run(["post", "--as", "Fable", "--to", "Codex", "--subject", "outcome", "--body", bfd2], cd5)
        run(["discharge", "--as", "Fable", "--id", "MSG-FAB-0002", "--in", "MSG-FAB-0004",
             "--outcome", "reported in a later entry on the bus"], cd5)
        r = run(["owed", "--as", "Fable"], cd5)
        t("control: a peer-readable discharge is recorded as DISCHARGED, not self-reported",
          "DISCHARGED" in r.stdout)

        # ---- S111 signed doctrine: terminal disagreement + commit-last ordering ----
        # Doctrine and runtime must agree; disagreement is a record, never a new blocker state.
        skill_text = SKILL.read_text(encoding="utf-8")
        bus_text = BUS.read_text(encoding="utf-8")
        t("B2 records two-round disagreement without forced alignment and preserves FULL STOP",
          disagreement_doctrine(skill_text, bus_text))

        # Negative control: an agreement-gated close is the exact incentive failure B2 forbids.
        waits_for_agreement = skill_text.replace(
            "session close proceeds", "session close waits for agreement", 1)
        t("B2 refuses an agreement-gated close",
          not disagreement_doctrine(waits_for_agreement, bus_text))

        # Boundary negative: preserved disagreement may never clear Rab's held authority.
        clears_rab = skill_text.replace("never clears `blocked-on-rab`;", "", 1)
        t("B2 cannot erase blocked-on-rab or FULL STOP",
          not disagreement_doctrine(clears_rab, bus_text))

        t("ERR-017 commit-last ordering is present in the canonical relay skill",
          commit_last_doctrine(skill_text))
        ordering_removed = skill_text.replace("write → commit → NOTHING", "write then commit", 1)
        t("ERR-017 ordering tripwire fails when NOTHING is removed",
          not commit_last_doctrine(ordering_removed))

        # ---- S111 B2 runtime: four received entries become one terminal disposition ----
        dg = Path(tmp) / "disagreement"
        dg.mkdir()
        io.open(dg / "relay.md", "w", encoding="utf-8", newline="\n").write("# relay (fixture)\n")
        run(["init", "--as", "Fable"], dg)
        run(["init", "--as", "Codex"], dg)

        exchanges = [
            ("Fable", "Codex", "r1-f", "**READING.** terminal means done\n\n**PROBE.** source A line 10\n"),
            ("Codex", "Fable", "r1-c", "**READING.** terminal leaves residue\n\n**PROBE.** source B line 20\n"),
            ("Fable", "Codex", "r2-f", "**READING.** terminal means done after reply\n\n**PROBE.** reran source A\n\n**RESPONDS-TO.** `MSG-CDX-0001`\n"),
            ("Codex", "Fable", "r2-c", "**READING.** terminal still leaves residue\n\n**PROBE.** reran source B\n\n**RESPONDS-TO.** `MSG-FAB-0001`\n"),
        ]
        ids = []
        for sender, receiver, subject, body in exchanges:
            result = run(["post", "--as", sender, "--to", receiver, "--subject", subject,
                          "--body", body_file(dg, body)], dg)
            mid = [part for part in result.stdout.split() if part.startswith("MSG-")][0]
            ids.append(mid)
            run(["confirm", "--as", receiver, "--id", mid, "--restatement",
                 f"understood {subject}: preserve this stated reading"], dg)

        # The wire format is minute-granular, so this fixture gives the round boundary distinct
        # recorded minutes: both R1 receipts at 00:01, first R2 send at 00:02. Sender sidecar
        # timestamps remain bound to the corresponding relay headers, and digests are resealed.
        timeline = {
            ids[0]: ("2026-01-01T00:00Z", "2026-01-01T00:01Z"),
            ids[1]: ("2026-01-01T00:00Z", "2026-01-01T00:01Z"),
            ids[2]: ("2026-01-01T00:02Z", "2026-01-01T00:03Z"),
            ids[3]: ("2026-01-01T00:04Z", "2026-01-01T00:05Z"),
        }
        relay_lines = io.open(dg / "relay.md", encoding="utf-8").readlines()
        for index, line in enumerate(relay_lines):
            for msg_id, (sent_utc, _) in timeline.items():
                if f"⟨msg: {msg_id}⟩" in line:
                    relay_lines[index] = f"## {sent_utc} · " + line.split(" · ", 1)[1]
        io.open(dg / "relay.md", "w", encoding="utf-8", newline="\n").writelines(relay_lines)
        os.environ["FP_COORD"] = str(dg)
        for filename in ("ack-fable.json", "ack-codex.json"):
            side = json.loads(io.open(dg / filename, encoding="utf-8").read())
            for row in side["sent"]:
                if row.get("id") in timeline:
                    row["utc"] = timeline[row["id"]][0]
                    row["digest"] = g2.digest(g2.extract_entry(row["id"]))
            for row in side["confirmed"]:
                if row.get("id") in timeline:
                    row["confirmed_utc"] = timeline[row["id"]][1]
                    row["digest"] = g2.digest(g2.extract_entry(row["id"]))
            io.open(dg / filename, "w", encoding="utf-8", newline="\n").write(
                json.dumps(side, indent=2) + "\n")

        run(["occupant", "--as", "Codex", "--model", "Occupant A"], dg)
        race_seed = Path(tmp) / "disagreement-race-seed"
        shutil.copytree(dg, race_seed)

        # Strong boundary fixture: preservation is a notice during FULL STOP, not a resolver.
        codex = json.loads(io.open(dg / "ack-codex.json", encoding="utf-8").read())
        codex["state"] = "blocked-on-rab"
        codex["escalations"] = [{"ticket": "T-RAB", "asking": "Rab must decide this",
                                  "msg_id": "MSG-CDX-9999", "state": "open"}]
        io.open(dg / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(codex, indent=2) + "\n")
        preserve = ["preserve-disagreement", "--as", "Codex", "--id", "DIS-001",
                    "--round1", ids[0], ids[1], "--round2", ids[2], ids[3],
                    "--consequence", "the close records two incompatible classifications",
                    "--prohibits", "do not promote either reading",
                    "--prohibits", "do not clear Rab's decision"]
        before_state = codex["state"]
        before_escalations = json.dumps(codex["escalations"], separators=(",", ":"))
        r = run(preserve, dg)
        after = json.loads(io.open(dg / "ack-codex.json", encoding="utf-8").read())
        relay = io.open(dg / "relay.md", encoding="utf-8").read()
        t("preserve-disagreement appends a canonical notice and structured record",
          r.returncode == 0 and "PRESERVED DISAGREEMENT" in relay
          and len(after.get("disagreements", [])) == 1
          and "DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED" in r.stdout)
        terminal_record = after["disagreements"][0]
        os.environ["FP_COORD"] = str(dg)
        terminal_at = g2._parse_utc(terminal_record["recorded_utc"])
        t("genuine terminal disposition follows every required confirmation receipt",
          terminal_at is not None
          and all(g2._parse_utc(row["confirmed_utc"]) <= terminal_at
                  for row in terminal_record["messages"]))
        t("terminal provenance binds the originating occupant into notice and record",
          terminal_record.get("origin_occupant") == "Occupant A"
          and '**ORIGIN OCCUPANT.** "Occupant A"' in relay)
        t("the structured record seals every cited source entry digest",
          all(row.get("source_digest") == g2.digest(g2.extract_entry(row["id"]))
              for row in terminal_record.get("messages", [])))
        t("preservation leaves blocked-on-rab and escalations byte-equivalent",
          after["state"] == before_state
          and json.dumps(after["escalations"], separators=(",", ":")) == before_escalations)
        status = run(["status"], dg)
        t("FULL STOP remains visible after terminal disagreement", "FULL STOP" in status.stdout)
        t("status renders the preserved disagreement, consequence, and prohibitions",
          status.returncode == 0 and "PRESERVED DISAGREEMENT DIS-001" in status.stdout
          and "two incompatible classifications" in status.stdout
          and "PROHIBITED" in status.stdout)

        def _snap(path):
            return tuple((path / name).read_bytes()
                         for name in ("relay.md", "ack-fable.json", "ack-codex.json"))

        timestamp_mismatch = Path(tmp) / "disagreement-sender-timestamp-mismatch"
        shutil.copytree(race_seed, timestamp_mismatch)
        side = json.loads(io.open(
            timestamp_mismatch / "ack-fable.json", encoding="utf-8").read())
        next(row for row in side["sent"] if row.get("id") == ids[0])["utc"] = (
            "2025-12-31T23:59Z")
        io.open(timestamp_mismatch / "ack-fable.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(side, indent=2) + "\n")
        mismatch_before = _snap(timestamp_mismatch)
        mismatch_args = preserve.copy()
        mismatch_args[mismatch_args.index("--id") + 1] = "DIS-UTC-MISMATCH"
        mismatch_result = run(mismatch_args, timestamp_mismatch)
        t("source validation binds each sender timestamp to its relay header",
          mismatch_result.returncode == 1
          and "sender timestamp does not match relay header" in mismatch_result.stderr
          and _snap(timestamp_mismatch) == mismatch_before)

        def _terminal_status_fixture(name, mutate_sidecar=None, mutate_relay=None):
            path = Path(tmp) / name
            shutil.copytree(dg, path)
            if mutate_sidecar:
                side = json.loads(io.open(path / "ack-codex.json", encoding="utf-8").read())
                mutate_sidecar(side["disagreements"][0])
                io.open(path / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
                    json.dumps(side, indent=2) + "\n")
            if mutate_relay:
                mutate_relay(path)
            return path, run(["status"], path)

        absent_terminal, absent_status = _terminal_status_fixture(
            "disagreement-status-absent-terminal",
            lambda record: record.update(terminal_msg_id="MSG-CDX-9999"),
        )
        t("status rejects a forged record whose terminal relay identity is absent",
          absent_status.returncode == 1 and "RED INVALID DISAGREEMENT" in absent_status.stdout
          and "PRESERVED DISAGREEMENT DIS-001" not in absent_status.stdout)

        digest_tamper, digest_status = _terminal_status_fixture(
            "disagreement-status-digest-tamper",
            lambda record: record.update(terminal_digest="sha256:" + ("0" * 64)),
        )
        t("status rejects a tampered terminal digest instead of rendering PRESERVED",
          digest_status.returncode == 1 and "RED INVALID DISAGREEMENT" in digest_status.stdout
          and "PRESERVED DISAGREEMENT DIS-001" not in digest_status.stdout)

        origin_forge, origin_status = _terminal_status_fixture(
            "disagreement-status-origin-forge",
            lambda record: record.update(origin_occupant="Forged Occupant"),
        )
        t("status rejects forged origin provenance",
          origin_status.returncode == 1 and "RED INVALID DISAGREEMENT" in origin_status.stdout)

        request_forge, request_status = _terminal_status_fixture(
            "disagreement-status-request-forge",
            lambda record: record.update(request_digest="sha256:" + ("2" * 64)),
        )
        t("status rejects a forged request digest",
          request_status.returncode == 1 and "RED INVALID DISAGREEMENT" in request_status.stdout)

        def _forge_source(record):
            record["messages"][0]["source_digest"] = "sha256:" + ("3" * 64)

        source_forge, source_status = _terminal_status_fixture(
            "disagreement-status-source-forge", _forge_source)
        t("status rejects a forged cited-source digest",
          source_status.returncode == 1 and "RED INVALID DISAGREEMENT" in source_status.stdout)

        def _duplicate_terminal(path):
            with io.open(path / "relay.md", "a", encoding="utf-8", newline="\n") as fh:
                fh.write(f"\n## malformed duplicate terminal · ⟨msg: "
                         f"{after['disagreements'][0]['terminal_msg_id']}⟩\n")

        duplicate_terminal, duplicate_status = _terminal_status_fixture(
            "disagreement-status-duplicate-terminal", mutate_relay=_duplicate_terminal)
        t("status rejects a terminal id with a duplicate relay minting stamp",
          duplicate_status.returncode == 1
          and "RED INVALID DISAGREEMENT" in duplicate_status.stdout)

        def _break_schema(record):
            record.pop("prohibited_actions")

        malformed_record, malformed_status = _terminal_status_fixture(
            "disagreement-status-malformed-schema", _break_schema)
        t("status rejects a malformed terminal-record schema",
          malformed_status.returncode == 1
          and "RED INVALID DISAGREEMENT" in malformed_status.stdout)

        invalid_occupant = Path(tmp) / "disagreement-invalid-loaded-occupant"
        shutil.copytree(dg, invalid_occupant)
        invalid_side = json.loads(io.open(
            invalid_occupant / "ack-codex.json", encoding="utf-8").read())
        invalid_side["occupant"] = "Z" * 201
        io.open(invalid_occupant / "ack-codex.json", "w", encoding="utf-8",
                newline="\n").write(json.dumps(invalid_side, indent=2) + "\n")
        invalid_occupant_status = run(["status"], invalid_occupant)
        t("load rejects an already-poisoned occupant beyond the provenance bound",
          "Codex  UNREAD" in invalid_occupant_status.stdout
          and "PRESERVED DISAGREEMENT DIS-001" not in invalid_occupant_status.stdout)

        snap = _snap(dg)
        replay = run(preserve, dg)
        t("exact replay is idempotent with zero byte mutation",
          replay.returncode == 0 and "already preserved" in replay.stdout and _snap(dg) == snap)
        conflict = preserve.copy()
        conflict[conflict.index("--consequence") + 1] = "a conflicting consequence"
        refused = run(conflict, dg)
        t("conflicting disagreement id refuses with zero mutation",
          refused.returncode == 1 and "conflicting" in refused.stderr and _snap(dg) == snap)

        def _make_orphan(destination):
            shutil.copytree(dg, destination)
            side = json.loads(io.open(destination / "ack-codex.json", encoding="utf-8").read())
            side["disagreements"] = [row for row in side.get("disagreements", [])
                                     if row.get("id") != "DIS-001"]
            side["sent"] = [row for row in side.get("sent", [])
                            if row.get("disagreement_id") != "DIS-001"]
            io.open(destination / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
                json.dumps(side, indent=2) + "\n")

        orphan = Path(tmp) / "disagreement-orphan"
        _make_orphan(orphan)
        orphan_side = json.loads(io.open(orphan / "ack-codex.json", encoding="utf-8").read())
        orphan_side["occupant"] = "Occupant B"
        io.open(orphan / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(orphan_side, indent=2) + "\n")
        orphan_bus = (orphan / "relay.md").read_bytes()
        adopted = run(preserve, orphan)
        adopted_side = json.loads(io.open(orphan / "ack-codex.json", encoding="utf-8").read())
        adopted_record = adopted_side.get("disagreements", [None])[0]
        t("a digest-valid crash-after-append orphan is adopted without a second append",
          adopted.returncode == 0 and "adopted orphan" in adopted.stdout
          and (orphan / "relay.md").read_bytes() == orphan_bus
          and len(adopted_side.get("disagreements", [])) == 1
          and any(row.get("disagreement_id") == "DIS-001"
                  for row in adopted_side.get("sent", [])))
        t("A-to-B orphan adoption retains origin and records adopter provenance",
          adopted_record.get("origin_occupant") == "Occupant A"
          and adopted_record.get("adopter_occupant") == "Occupant B"
          and bool(adopted_record.get("adopted_utc")))
        adopted_snap = _snap(orphan)
        adopted_retry = run(preserve, orphan)
        t("retry after orphan adoption is an exact byte-idempotent replay",
          adopted_retry.returncode == 0 and "already preserved" in adopted_retry.stdout
          and _snap(orphan) == adopted_snap)

        orphan_origin_bad = Path(tmp) / "disagreement-orphan-origin-tamper"
        _make_orphan(orphan_origin_bad)
        origin_text = io.open(orphan_origin_bad / "relay.md", encoding="utf-8").read()
        io.open(orphan_origin_bad / "relay.md", "w", encoding="utf-8", newline="\n").write(
            origin_text.replace('**ORIGIN OCCUPANT.** "Occupant A"\n\n', "", 1))
        origin_bad_snap = _snap(orphan_origin_bad)
        refused = run(preserve, orphan_origin_bad)
        t("a missing or tampered orphan origin refuses with zero mutation",
          refused.returncode == 1 and "origin occupant" in refused.stderr
          and _snap(orphan_origin_bad) == origin_bad_snap)

        orphan_bad = Path(tmp) / "disagreement-orphan-mismatch"
        _make_orphan(orphan_bad)
        request_digest = after["disagreements"][0]["request_digest"]
        bad_request = "sha256:" + ("0" * 64)
        orphan_text = io.open(orphan_bad / "relay.md", encoding="utf-8").read()
        io.open(orphan_bad / "relay.md", "w", encoding="utf-8", newline="\n").write(
            orphan_text.replace(request_digest, bad_request, 1))
        orphan_bad_snap = _snap(orphan_bad)
        refused = run(preserve, orphan_bad)
        t("a mismatched orphan request digest refuses with zero mutation",
          refused.returncode == 1 and "conflicts" in refused.stderr
          and _snap(orphan_bad) == orphan_bad_snap)

        orphan_duplicate_id = Path(tmp) / "disagreement-orphan-duplicate-relay-id"
        _make_orphan(orphan_duplicate_id)
        terminal_id = terminal_record["terminal_msg_id"]
        with io.open(orphan_duplicate_id / "relay.md", "a", encoding="utf-8",
                     newline="\n") as fh:
            fh.write(f"\n## malformed duplicate mint · ⟨from: Codex⟩ → ⟨to: Fable⟩ · "
                     f"⟨msg: {terminal_id}⟩\n\n**RECAP.** duplicate id control\n")
        duplicate_snap = _snap(orphan_duplicate_id)
        refused = run(preserve, orphan_duplicate_id)
        t("orphan adoption refuses a terminal id duplicated anywhere in relay",
          refused.returncode == 1 and "conflicts" in refused.stderr
          and _snap(orphan_duplicate_id) == duplicate_snap)

        orphan_structured_id = Path(tmp) / "disagreement-orphan-structured-id-conflict"
        _make_orphan(orphan_structured_id)
        conflicting_side = json.loads(io.open(
            orphan_structured_id / "ack-fable.json", encoding="utf-8").read())
        conflicting_side["sent"].append({
            "id": terminal_id, "to": "Codex", "utc": "2026-01-01T00:08Z",
            "digest": "sha256:" + ("1" * 64), "subject": "conflicting allocation",
            "ticket": None, "requires_ack": False,
        })
        io.open(orphan_structured_id / "ack-fable.json", "w", encoding="utf-8",
                newline="\n").write(json.dumps(conflicting_side, indent=2) + "\n")
        structured_snap = _snap(orphan_structured_id)
        refused = run(preserve, orphan_structured_id)
        t("orphan adoption refuses an id allocated by any structured record",
          refused.returncode == 1 and "conflicts" in refused.stderr
          and _snap(orphan_structured_id) == structured_snap)

        bad = Path(tmp) / "disagreement-tampered"
        shutil.copytree(dg, bad)
        text_bad = io.open(bad / "relay.md", encoding="utf-8").read()
        io.open(bad / "relay.md", "w", encoding="utf-8", newline="\n").write(
            text_bad.replace("terminal means done", "terminal was tampered", 1))
        bad_args = preserve.copy()
        bad_args[bad_args.index("DIS-001")] = "DIS-002"
        bad_snap = _snap(bad)
        refused = run(bad_args, bad)
        t("tampered round refuses with zero mutation",
          refused.returncode == 1 and "digest" in refused.stderr and _snap(bad) == bad_snap)

        wrong = Path(tmp) / "disagreement-order"
        shutil.copytree(dg, wrong)
        wrong_args = preserve.copy()
        wrong_args[wrong_args.index("DIS-001")] = "DIS-003"
        r1_at = wrong_args.index("--round1")
        wrong_args[r1_at + 1], wrong_args[r1_at + 2] = wrong_args[r1_at + 2], wrong_args[r1_at + 1]
        wrong_snap = _snap(wrong)
        refused = run(wrong_args, wrong)
        t("invalid lane/order chain refuses with zero mutation",
          refused.returncode == 1 and _snap(wrong) == wrong_snap)

        missing = Path(tmp) / "disagreement-missing-receipt"
        shutil.copytree(dg, missing)
        missing_codex = json.loads(io.open(missing / "ack-codex.json", encoding="utf-8").read())
        missing_codex["confirmed"] = [row for row in missing_codex["confirmed"]
                                      if row.get("id") != ids[0]]
        io.open(missing / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(missing_codex, indent=2) + "\n")
        missing_args = preserve.copy()
        missing_args[missing_args.index("DIS-001")] = "DIS-004"
        missing_snap = _snap(missing)
        refused = run(missing_args, missing)
        t("an incomplete receipt chain refuses with zero mutation (silence is not disagreement)",
          refused.returncode == 1 and "receipt" in refused.stderr
          and _snap(missing) == missing_snap)

        slotless = Path(tmp) / "disagreement-missing-slot"
        shutil.copytree(dg, slotless)
        slot_text = io.open(slotless / "relay.md", encoding="utf-8").read()
        io.open(slotless / "relay.md", "w", encoding="utf-8", newline="\n").write(
            slot_text.replace("**PROBE.** source A line 10", "**EVIDENCE.** source A line 10", 1))
        os.environ["FP_COORD"] = str(slotless)
        repaired_digest = g2.digest(g2.extract_entry(ids[0]))
        for filename, field in (("ack-fable.json", "sent"),
                                ("ack-codex.json", "confirmed")):
            side = json.loads(io.open(slotless / filename, encoding="utf-8").read())
            for row in side[field]:
                if row.get("id") == ids[0]:
                    row["digest"] = repaired_digest
            io.open(slotless / filename, "w", encoding="utf-8", newline="\n").write(
                json.dumps(side, indent=2) + "\n")
        slot_args = preserve.copy()
        slot_args[slot_args.index("DIS-001")] = "DIS-005"
        slot_snap = _snap(slotless)
        refused = run(slot_args, slotless)
        t("a digest-confirmed chain missing a required PROBE slot refuses with zero mutation",
          refused.returncode == 1 and "READING and PROBE" in refused.stderr
          and _snap(slotless) == slot_snap)

        converged = Path(tmp) / "disagreement-converged"
        shutil.copytree(dg, converged)
        converged_text = io.open(converged / "relay.md", encoding="utf-8").read()
        io.open(converged / "relay.md", "w", encoding="utf-8", newline="\n").write(
            converged_text.replace("terminal still leaves residue",
                                   "terminal   means done after reply", 1))
        os.environ["FP_COORD"] = str(converged)
        converged_digest = g2.digest(g2.extract_entry(ids[3]))
        for filename, field in (("ack-codex.json", "sent"),
                                ("ack-fable.json", "confirmed")):
            side = json.loads(io.open(converged / filename, encoding="utf-8").read())
            for row in side[field]:
                if row.get("id") == ids[3]:
                    row["digest"] = converged_digest
            io.open(converged / filename, "w", encoding="utf-8", newline="\n").write(
                json.dumps(side, indent=2) + "\n")
        converged_args = preserve.copy()
        converged_args[converged_args.index("DIS-001")] = "DIS-006"
        converged_snap = _snap(converged)
        refused = run(converged_args, converged)
        t("exact-normalized identical final READINGS refuse as convergence with zero mutation",
          refused.returncode == 1 and "converged" in refused.stderr
          and _snap(converged) == converged_snap)

        late = Path(tmp) / "disagreement-late-round1-ack"
        shutil.copytree(dg, late)
        late_codex = json.loads(io.open(late / "ack-codex.json", encoding="utf-8").read())
        for row in late_codex["confirmed"]:
            if row.get("id") == ids[0]:
                row["confirmed_utc"] = "2099-01-01T00:00Z"
        io.open(late / "ack-codex.json", "w", encoding="utf-8", newline="\n").write(
            json.dumps(late_codex, indent=2) + "\n")
        late_args = preserve.copy()
        late_args[late_args.index("DIS-001")] = "DIS-007"
        late_snap = _snap(late)
        refused = run(late_args, late)
        t("round two refuses when both round-one receipts did not precede its first send",
          refused.returncode == 1 and "precede" in refused.stderr
          and _snap(late) == late_snap)

        future_r2 = Path(tmp) / "disagreement-future-round2-receipts"
        shutil.copytree(race_seed, future_r2)
        for filename, msg_id in (("ack-codex.json", ids[2]),
                                 ("ack-fable.json", ids[3])):
            side = json.loads(io.open(future_r2 / filename, encoding="utf-8").read())
            next(row for row in side["confirmed"] if row.get("id") == msg_id)[
                "confirmed_utc"] = "2099-01-01T00:00Z"
            io.open(future_r2 / filename, "w", encoding="utf-8", newline="\n").write(
                json.dumps(side, indent=2) + "\n")
        future_args = preserve.copy()
        future_args[future_args.index("DIS-001")] = "DIS-008"
        future_snap = _snap(future_r2)
        refused = run(future_args, future_r2)
        t("terminal disposition refuses future round-two receipts with zero mutation",
          refused.returncode == 1 and "after terminal disposition" in refused.stderr
          and _snap(future_r2) == future_snap)

        empty = preserve.copy()
        empty[empty.index("--consequence") + 1] = "   "
        empty_snap = _snap(dg)
        refused = run(empty, dg)
        t("an empty consequence refuses with zero mutation",
          refused.returncode == 1 and _snap(dg) == empty_snap)
        empty_action = preserve.copy()
        empty_action[empty_action.index("--prohibits") + 1] = "   "
        refused = run(empty_action, dg)
        t("an empty prohibited action refuses with zero mutation",
          refused.returncode == 1 and _snap(dg) == empty_snap)

        # ---- Cross-process transaction controls ----
        def _preserve_args(disagreement_id):
            args = preserve.copy()
            args[args.index("DIS-001")] = disagreement_id
            return args

        def _locked_race(path, first_args, second_args):
            """Queue two real CLIs behind the stable lock, then release them together."""
            os.environ["FP_COORD"] = str(path)
            with g2._relay_transaction_lock():
                first = spawn(first_args, path)
                time.sleep(0.20)
                second = spawn(second_args, path)
                time.sleep(0.35)
            return finish(first), finish(second)

        def _relay_rows(path):
            os.environ["FP_COORD"] = str(path)
            return g2.relay_entries()[0]

        race_same = Path(tmp) / "disagreement-race-same-request"
        shutil.copytree(race_seed, race_same)
        same_args = _preserve_args("DIS-RACE-SAME")
        same_results = _locked_race(race_same, same_args, same_args)
        same_side = json.loads(io.open(race_same / "ack-codex.json", encoding="utf-8").read())
        same_rows = _relay_rows(race_same)
        same_markers = [row for row in same_rows
                        if "**DISAGREEMENT ID.** `DIS-RACE-SAME`" in row["text"]]
        t("concurrent same-request preserves serialize to one terminal and one replay",
          all(result.returncode == 0 for result in same_results)
          and len(same_markers) == 1
          and len([row for row in same_side.get("disagreements", [])
                   if row.get("id") == "DIS-RACE-SAME"]) == 1
          and len([result for result in same_results
                   if "already preserved" in result.stdout]) == 1)
        t("same-request race leaves no duplicate relay message ids",
          len([row["id"] for row in same_rows])
          == len(set(row["id"] for row in same_rows)))

        race_distinct = Path(tmp) / "disagreement-race-distinct-requests"
        shutil.copytree(race_seed, race_distinct)
        distinct_results = _locked_race(
            race_distinct, _preserve_args("DIS-RACE-A"), _preserve_args("DIS-RACE-B"))
        distinct_side = json.loads(io.open(
            race_distinct / "ack-codex.json", encoding="utf-8").read())
        distinct_rows = _relay_rows(race_distinct)
        distinct_records = [row for row in distinct_side.get("disagreements", [])
                            if row.get("id") in ("DIS-RACE-A", "DIS-RACE-B")]
        t("two concurrent distinct preserves retain both records with distinct terminal ids",
          all(result.returncode == 0 for result in distinct_results)
          and len(distinct_records) == 2
          and len({row.get("terminal_msg_id") for row in distinct_records}) == 2)
        t("distinct-request race leaves every relay message id globally unique",
          len([row["id"] for row in distinct_rows])
          == len(set(row["id"] for row in distinct_rows)))

        escalation_args = [
            "escalate", "--as", "Codex",
            "--asking", "whether the concurrent transaction boundary is accepted",
            "--why", "the principal owns this decision", "--ticket", "T-RACE",
        ]

        def _mixed_race_ok(path, results, first_kind):
            side = json.loads(io.open(path / "ack-codex.json", encoding="utf-8").read())
            records = [row for row in side.get("disagreements", [])
                       if row.get("id") == "DIS-RACE-MIXED"]
            escalations = [row for row in side.get("escalations", [])
                           if row.get("asking") == escalation_args[4]]
            rows = _relay_rows(path)
            if (not all(result.returncode == 0 for result in results)
                    or len(records) != 1 or len(escalations) != 1):
                return False
            terminal_id, escalation_id = records[0].get("terminal_msg_id"), escalations[0].get("msg_id")
            by_id = {row["id"]: row for row in rows}
            escalation_sent = [row for row in side.get("sent", [])
                               if row.get("id") == escalation_id]
            if (terminal_id == escalation_id or terminal_id not in by_id
                    or escalation_id not in by_id or len(escalation_sent) != 1
                    or escalation_sent[0].get("digest") != g2.digest(by_id[escalation_id]["text"])):
                return False
            expected_order = (by_id[terminal_id]["position"] < by_id[escalation_id]["position"])
            if first_kind == "escalate":
                expected_order = not expected_order
            status = run(["status"], path)
            return (expected_order and side.get("state") == "blocked-on-rab"
                    and escalations[0].get("state") == "open"
                    and "FULL STOP" in status.stdout
                    and len([row["id"] for row in rows])
                    == len(set(row["id"] for row in rows)))

        mixed_preserve_first = Path(tmp) / "disagreement-race-preserve-first"
        shutil.copytree(race_seed, mixed_preserve_first)
        mixed_args = _preserve_args("DIS-RACE-MIXED")
        mixed_results = _locked_race(
            mixed_preserve_first, mixed_args, escalation_args)
        t("preserve-first race publishes both unique records and a matching FULL STOP escalation",
          _mixed_race_ok(mixed_preserve_first, mixed_results, "preserve"))

        mixed_escalate_first = Path(tmp) / "disagreement-race-escalate-first"
        shutil.copytree(race_seed, mixed_escalate_first)
        mixed_results = _locked_race(
            mixed_escalate_first, escalation_args, mixed_args)
        t("escalate-first race publishes both unique records and a matching FULL STOP escalation",
          _mixed_race_ok(mixed_escalate_first, mixed_results, "escalate"))

        # ---- Append-intent journal: process-death windows cannot render calm ----
        def _journal_fixture(name):
            path = Path(tmp) / name
            path.mkdir()
            io.open(path / "relay.md", "w", encoding="utf-8", newline="\n").write(
                "# relay (journal fixture)\n")
            run(["init", "--as", "Fable"], path)
            run(["init", "--as", "Codex"], path)
            return path

        def _journal_snap(path):
            return tuple((path / name).read_bytes() for name in (
                "relay.md", "ack-fable.json", "ack-codex.json", ".relay-gate.lock"))

        structured_post_collision = _journal_fixture("structured-id-collision-post")
        peer = json.loads(io.open(
            structured_post_collision / "ack-codex.json", encoding="utf-8").read())
        peer["disagreements"] = [{"terminal_msg_id": "MSG-FAB-0001"}]
        io.open(structured_post_collision / "ack-codex.json", "w",
                encoding="utf-8", newline="\n").write(json.dumps(peer, indent=2) + "\n")
        post_collision_before = _journal_snap(structured_post_collision)
        collision_body = body_file(
            structured_post_collision, "**RECAP.** must not reuse a structured id\n")
        post_collision = run([
            "post", "--as", "Fable", "--to", "Codex", "--subject", "id-collision",
            "--body", collision_body,
        ], structured_post_collision)

        structured_escalation_collision = _journal_fixture(
            "structured-id-collision-escalation")
        peer = json.loads(io.open(
            structured_escalation_collision / "ack-fable.json", encoding="utf-8").read())
        peer["escalations"] = [{"msg_id": "MSG-CDX-0001", "state": "resolved"}]
        io.open(structured_escalation_collision / "ack-fable.json", "w",
                encoding="utf-8", newline="\n").write(json.dumps(peer, indent=2) + "\n")
        escalation_collision_before = _journal_snap(structured_escalation_collision)
        escalation_collision = run([
            "escalate", "--as", "Codex", "--asking", "whether this id may be reused",
            "--why", "the sidecar already allocated it", "--ticket", "T-ID-COLLISION",
        ], structured_escalation_collision)
        t("post and escalate refuse ids allocated only by any structured sidecar record",
          post_collision.returncode == 1
          and escalation_collision.returncode == 1
          and "structured sidecar record" in post_collision.stderr
          and "structured sidecar record" in escalation_collision.stderr
          and _journal_snap(structured_post_collision) == post_collision_before
          and _journal_snap(structured_escalation_collision) == escalation_collision_before)

        crash_before_post = _journal_fixture("journal-crash-before-post")
        crash_body = body_file(crash_before_post, "**RECAP.** journal post control\n")
        post_args = ["post", "--as", "Fable", "--to", "Codex", "--subject",
                     "journal-control", "--body", crash_body, "--ticket", "T-JOURNAL"]
        crashed = run(post_args, crash_before_post, extra_env={
            "FP_GATE_TEST_CRASH_BEFORE_APPEND": "post"})
        pending_status = run(["status"], crash_before_post)
        t("process death after intent but before post append is visible and nonzero",
          crashed.returncode == 86 and pending_status.returncode == 1
          and "PENDING BEFORE RELAY APPEND" in pending_status.stdout
          and "MSG-FAB-0001" not in io.open(
              crash_before_post / "relay.md", encoding="utf-8").read())
        pending_snap = _journal_snap(crash_before_post)
        beat_refused = run(["beat", "--as", "Fable", "--doing", "must not overwrite"],
                           crash_before_post)
        occupant_refused = run(["occupant", "--as", "Fable", "--model", "Occupant C"],
                               crash_before_post)
        ticket_refused = run(["ticket", "--as", "Fable", "--id", "T-OTHER",
                              "--state", "working"], crash_before_post)
        t("pending intent interlocks beat, occupant, and ticket with byte-zero mutation",
          all(result.returncode == 1 for result in
              (beat_refused, occupant_refused, ticket_refused))
          and _journal_snap(crash_before_post) == pending_snap)
        conflicting_post = post_args.copy()
        conflicting_post[conflicting_post.index("journal-control")] = "different-request"
        conflict_snap = _journal_snap(crash_before_post)
        conflict_result = run(conflicting_post, crash_before_post)
        t("a conflicting post retry refuses without changing journal, bus, or sidecars",
          conflict_result.returncode == 1 and "conflicting retry" in conflict_result.stderr
          and _journal_snap(crash_before_post) == conflict_snap)
        recovered = run(post_args, crash_before_post)
        recovered_side = json.loads(io.open(
            crash_before_post / "ack-fable.json", encoding="utf-8").read())
        t("an exact retry resumes the pre-append post with its original unique id",
          recovered.returncode == 0 and "recovered and posted MSG-FAB-0001" in recovered.stdout
          and len([row for row in recovered_side["sent"]
                   if row.get("id") == "MSG-FAB-0001"]) == 1
          and (crash_before_post / ".relay-gate.lock").read_bytes() == b"L")

        crash_after_post = _journal_fixture("journal-crash-after-post")
        after_body = body_file(crash_after_post, "**RECAP.** orphan post control\n")
        after_post_args = ["post", "--as", "Fable", "--to", "Codex", "--subject",
                           "orphan-post", "--body", after_body, "--ticket", "T-ORPHAN"]
        crashed = run(after_post_args, crash_after_post, extra_env={
            "FP_GATE_TEST_CRASH_AFTER_APPEND": "post"})
        orphan_status = run(["status"], crash_after_post)
        orphan_side = json.loads(io.open(
            crash_after_post / "ack-fable.json", encoding="utf-8").read())
        t("post append orphan is RED/nonzero and never looks delivered or blocked-on-ack",
          crashed.returncode == 87 and orphan_status.returncode == 1
          and "ORPHAN RELAY APPEND" in orphan_status.stdout
          and "NOT proven" in orphan_status.stdout
          and orphan_side["sent"] == [] and orphan_side["state"] == "idle")
        recovered = run(after_post_args, crash_after_post)
        rows_after_recovery = _relay_rows(crash_after_post)
        t("exact post-orphan retry adopts without duplicate relay ids and clears journal",
          recovered.returncode == 0 and "recovered and posted" in recovered.stdout
          and len([row["id"] for row in rows_after_recovery])
          == len(set(row["id"] for row in rows_after_recovery))
          and (crash_after_post / ".relay-gate.lock").read_bytes() == b"L")

        crash_after_sidecar = _journal_fixture("journal-crash-after-sidecar")
        sidecar_body = body_file(crash_after_sidecar, "**RECAP.** completed journal control\n")
        sidecar_args = ["post", "--as", "Fable", "--to", "Codex", "--subject",
                        "completed-post", "--body", sidecar_body]
        crashed = run(sidecar_args, crash_after_sidecar, extra_env={
            "FP_GATE_TEST_CRASH_AFTER_SIDECAR": "post"})
        uncleared_status = run(["status"], crash_after_sidecar)
        recovered = run(sidecar_args, crash_after_sidecar)
        t("journal survives sidecar-publication crash and exact retry clears it idempotently",
          crashed.returncode == 88 and uncleared_status.returncode == 1
          and "UNCLEARED AFTER SIDECAR PUBLICATION" in uncleared_status.stdout
          and recovered.returncode == 0 and "already posted" in recovered.stdout
          and (crash_after_sidecar / ".relay-gate.lock").read_bytes() == b"L")

        crash_after_escalation = _journal_fixture("journal-crash-after-escalation")
        escalation_crash_args = [
            "escalate", "--as", "Codex",
            "--asking", "whether this orphan escalation is accepted",
            "--why", "only Rab can decide", "--ticket", "T-ESC-ORPHAN",
        ]
        crashed = run(escalation_crash_args, crash_after_escalation, extra_env={
            "FP_GATE_TEST_CRASH_AFTER_APPEND": "escalation"})
        escalation_status = run(["status"], crash_after_escalation)
        t("an orphan escalation is RED, nonzero, and imposes FULL STOP",
          crashed.returncode == 87 and escalation_status.returncode == 1
          and "ORPHAN RELAY APPEND" in escalation_status.stdout
          and "FULL STOP" in escalation_status.stdout)
        conflicting_escalation = escalation_crash_args.copy()
        conflicting_escalation[conflicting_escalation.index(
            "whether this orphan escalation is accepted")] = "whether a different ask is accepted"
        conflict_snap = _journal_snap(crash_after_escalation)
        conflict_result = run(conflicting_escalation, crash_after_escalation)
        escalation_conflict_unchanged = _journal_snap(crash_after_escalation) == conflict_snap
        recovered = run(escalation_crash_args, crash_after_escalation)
        escalation_side = json.loads(io.open(
            crash_after_escalation / "ack-codex.json", encoding="utf-8").read())
        t("conflicting escalation retry refuses, exact retry recovers FULL STOP state",
          conflict_result.returncode == 1 and escalation_conflict_unchanged
          and recovered.returncode == 0 and escalation_side["state"] == "blocked-on-rab"
          and len(escalation_side["escalations"]) == 1
          and (crash_after_escalation / ".relay-gate.lock").read_bytes() == b"L")

        malformed_journal = _journal_fixture("journal-malformed")
        io.open(malformed_journal / ".relay-gate.lock", "wb").write(b"L{not-json")
        malformed_snap = _journal_snap(malformed_journal)
        malformed_status = run(["status"], malformed_journal)
        malformed_save = run(["occupant", "--as", "Fable", "--model", "Occupant D"],
                             malformed_journal)
        t("malformed/tampered journal fails closed and blocks ordinary mutation",
          malformed_status.returncode == 1 and "TRANSACTION JOURNAL" in malformed_status.stdout
          and malformed_save.returncode == 1
          and _journal_snap(malformed_journal) == malformed_snap)

        # A caller starts while the transaction is held; a noncompliant edit changes one cited
        # entry before release. The command must validate the changed bytes, not reuse any view
        # obtained before it owned the transaction, and must append nothing.
        toctou = Path(tmp) / "disagreement-transaction-revalidation"
        shutil.copytree(race_seed, toctou)
        os.environ["FP_COORD"] = str(toctou)
        with g2._relay_transaction_lock():
            pending = spawn(_preserve_args("DIS-RACE-TOCTOU"), toctou)
            time.sleep(0.50)
            changed = io.open(toctou / "relay.md", encoding="utf-8").read()
            io.open(toctou / "relay.md", "w", encoding="utf-8", newline="\n").write(
                changed.replace("terminal means done", "terminal changed after start", 1))
            changed_snap = _snap(toctou)
        revalidated = finish(pending)
        t("a cited-chain change before lock-held validation refuses with no terminal append",
          revalidated.returncode == 1 and "digest" in revalidated.stderr
          and _snap(toctou) == changed_snap
          and "DIS-RACE-TOCTOU" not in io.open(
              toctou / "relay.md", encoding="utf-8").read())

        # Non-gate writers do not honor the advisory lock. Mutate a cited source immediately
        # after the central append helper returns: the post-append source revalidation must make
        # the bus marker visibly orphaned and publish no sidecar disposition.
        post_validation = Path(tmp) / "disagreement-post-validation-change"
        shutil.copytree(race_seed, post_validation)
        os.environ["FP_COORD"] = str(post_validation)
        original_append = g2._append_relay_locked

        def _append_then_change_source(entry, msg_id, **kwargs):
            result = original_append(entry, msg_id, **kwargs)
            text = io.open(post_validation / "relay.md", encoding="utf-8").read()
            io.open(post_validation / "relay.md", "w", encoding="utf-8", newline="\n").write(
                text.replace("terminal means done", "terminal changed after validation", 1))
            return result

        g2._append_relay_locked = _append_then_change_source
        post_validation_error = ""
        try:
            command = SimpleNamespace(
                as_model="Codex", id="DIS-RACE-POST-VALIDATION",
                round1=ids[:2], round2=ids[2:],
            )
            with g2._relay_transaction_lock():
                g2._cmd_preserve_disagreement_locked(
                    command, "the source changed during publication",
                    ["do not treat the orphan as terminal"],
                )
        except SystemExit as error:
            post_validation_error = str(error)
        finally:
            g2._append_relay_locked = original_append
        post_validation_side = json.loads(io.open(
            post_validation / "ack-codex.json", encoding="utf-8").read())
        t("a post-validation source change cannot silently become a structured disposition",
          "changed during terminal publication" in post_validation_error
          and not any(row.get("id") == "DIS-RACE-POST-VALIDATION"
                      for row in post_validation_side.get("disagreements", []))
          and "DIS-RACE-POST-VALIDATION" in io.open(
              post_validation / "relay.md", encoding="utf-8").read())

    total = PASS + FAIL
    print()
    if FAIL == 0:
        print(f"ALL TRIPWIRES FIRED — {PASS}/{total}, exit 0")
        return 0
    print(f"TRIPWIRES BROKEN — {FAIL} of {total} failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
