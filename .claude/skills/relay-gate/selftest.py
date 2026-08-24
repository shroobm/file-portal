#!/usr/bin/env python3
"""Tripwires for gate.py. Every law is proven BOTH ways: a fixture that must PASS and,
for each rule, a fixture that must FAIL. (The 2026-08-22 mapping pass shipped a false
byte-level claim from a probe nobody had controlled; this file is that lesson, vendored.)"""

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = str(Path(__file__).resolve().parent / "gate.py")
PY = sys.executable
PASS = FAIL = 0


def run(args, coord, expect=0):
    env = dict(os.environ, FP_COORD=str(coord))
    r = subprocess.run([PY, GATE] + args, env=env, capture_output=True, text=True)
    return r


def t(name, cond):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}")
        FAIL += 1


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

        run(["init", "--as", "Codex"], coord)

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

    total = PASS + FAIL
    print()
    if FAIL == 0:
        print(f"ALL TRIPWIRES FIRED — {PASS}/{total}, exit 0")
        return 0
    print(f"TRIPWIRES BROKEN — {FAIL} of {total} failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
