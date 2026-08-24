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

    total = PASS + FAIL
    print()
    if FAIL == 0:
        print(f"ALL TRIPWIRES FIRED — {PASS}/{total}, exit 0")
        return 0
    print(f"TRIPWIRES BROKEN — {FAIL} of {total} failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
