#!/usr/bin/env python3
"""test_room_c.py - BUILDER C's tripwires (CONTRACT §8), written the day the guards were.

WHAT THIS FILE DOES: unittest tests for status.py, the catcher and the parts of roomlog.py they
use. Each test builds a throwaway directory tree (class Fixture), points roomlog's path
constants at it, writes status/sidecar JSON files into it, and checks what status.render_lane,
write_status, read_sidecar and catcher.Catcher return. Some tests run the real gate.py as a
subprocess against the temporary coord directory. Run it with: python -m unittest test_room_c -v
It writes only to temporary directories and restores roomlog's constants after each test.

WHY THIS FILE IS NOT `test_room.py`: the contract puts every builder's tripwires in one
`test_room.py`, assembled by all four. Four builders are writing in parallel and cannot ask
each other questions; four writers on one path means three of them lose their work to the
last save. So Builder C's tripwires live here, as a normal unittest module, ready to be
merged into `test_room.py` verbatim at assembly. THIS IS A DEVIATION FROM §1 AND §8 AND IT IS
FLAGGED, NOT HIDDEN - the assembler should fold it in and delete this file.

Covered here: T8, T8b, T8c, T9, T9b, T10, T11, T12b, T15, T16, T19, T24, T25, T26, T27.
Not covered here (they test Builder A's `render_trail` / `append_stage` writer half, and are
listed against C only because C consumes them): T13, T14, T15b - written at assembly, when
`roomlog.py` exists.

Every test that guards a guard carries its CONTROL. A tripwire that passes both ways is a
tautology (L8), and the control is what makes it not one.

    python -m unittest test_room_c -v
"""

import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import roomlog
import status
import catcher

HERE = Path(__file__).resolve().parent
PY = sys.executable


# -- shared helpers and the base fixture --

def stamp(dt):
    """Format a datetime as the millisecond UTC stamp string the documents use. Pure."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


class Fixture(unittest.TestCase):
    """Every test runs against a throwaway tree. No test touches the real state/, and no test
    lets FP_COORD point outside it (CONTRACT §8 preamble)."""

    def setUp(self):
        """Create a temp tree, save roomlog's path constants, redirect them into the tree, make
        the state directories, and record `self.now`."""
        self.tmp = Path(tempfile.mkdtemp(prefix="relay-room-c-"))
        self._saved = {k: getattr(roomlog, k) for k in
                       ("ROOT", "STATE", "COORD", "ROOM_MD", "FLIGHT_DIR", "HANDOFF_DIR")}
        roomlog.ROOT = self.tmp
        roomlog.STATE = self.tmp / "state"
        roomlog.COORD = roomlog.STATE / "coord"
        roomlog.ROOM_MD = roomlog.STATE / "room.md"
        roomlog.FLIGHT_DIR = roomlog.STATE / "flight"
        roomlog.HANDOFF_DIR = roomlog.STATE / "handoff"
        for d in (roomlog.STATE, roomlog.COORD, roomlog.FLIGHT_DIR, roomlog.HANDOFF_DIR):
            d.mkdir(parents=True, exist_ok=True)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        """Restore roomlog's saved path constants and delete the temp tree."""
        for k, v in self._saved.items():
            setattr(roomlog, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- builders -------------------------------------------------------------

    def doc(self, lane="Fable", agent_state="watching", model_state="idle", **over):
        """Build a valid, fresh status document for `lane`; keyword overrides replace top-level keys."""
        d = {
            "protocol": status.PROTOCOL, "writer": f"catcher:{lane}", "lane": lane,
            "pid": 1, "started_utc": stamp(self.now), "heartbeat_utc": stamp(self.now),
            "cycle": 3, "heartbeat_interval_s": 2.0, "stale_after_s": 15.0,
            "model_stale_after_s": 300.0,
            "agent": {"state": agent_state, "since_utc": stamp(self.now), "detail": "x",
                      "last_error": None, "consecutive_errors": 0,
                      "log_read": {"status": "ok", "count": 1, "torn": 0, "debris": 0,
                                   "bytes": 10, "read_utc": stamp(self.now)}},
            "model": {"state": model_state, "source": "sidecar", "since_utc": stamp(self.now),
                      "note": None,
                      "sidecar": {"status": "ok", "state": model_state, "ticket": None,
                                  "sent": 0, "confirmed": 0, "updated_utc": stamp(self.now),
                                  "age_s": 1.0, "path": "state/coord/ack-fable.json",
                                  "reason": None},
                      "declared": {"status": "UNREAD", "state": None, "utc": None,
                                   "age_s": None, "reason": "not declared"}},
            "in_flight": None, "gate": None,
        }
        d.update(over)
        return d

    def put(self, lane, obj):
        """Write `obj` (raw string or JSON-able value) straight to the lane's status file,
        bypassing write_status so malformed files can be planted."""
        p = status.status_path(lane)
        p.parent.mkdir(parents=True, exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(obj if isinstance(obj, str) else json.dumps(obj))

    def put_sidecar(self, lane, obj):
        """Write `obj` (raw string or JSON-able value) to the lane's relay-gate sidecar file."""
        p = status.sidecar_path(lane)
        p.parent.mkdir(parents=True, exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(obj if isinstance(obj, str) else json.dumps(obj))

    def good_sidecar(self, lane="Fable", state="idle", **over):
        """Return a valid sidecar dict for `lane` in `state`; keyword overrides replace keys."""
        d = {"writer": lane, "protocol": status.GATE_PROTOCOL, "updated_utc": stamp(self.now),
             "state": state, "occupant": None, "current_ticket": None,
             "sent": [], "confirmed": [], "escalations": []}
        d.update(over)
        return d

    def gate_init_both(self):
        """Run the real gate.py `init` for both lanes as subprocesses, with FP_COORD set to the
        temporary coord directory, so real sidecars exist there."""
        for lane in ("Fable", "Codex"):
            subprocess.run([PY, str(roomlog.GATE_PY), "init", "--as", lane],
                           capture_output=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "FP_COORD": str(roomlog.COORD)}, timeout=60)


# =========================================================== T8 / T8b - the agent ladder

class TestAgentLadder(Fixture):
    """Tests of the agent-layer rules in status.render_lane (rules 1-9 of the ladder)."""

    def rules(self):
        """Nine (rule number, planted file content) cases; None means no file at all."""
        old = stamp(self.now - timedelta(seconds=40))
        return [
            (1, None),
            (2, "{not json at all"),
            (3, json.dumps([1, 2, 3])),
            (4, self.doc(**{"protocol": "fp-relay-room/v0"})),
            (5, self.doc(**{"writer": "catcher:Codex"})),
            (6, self.doc(agent_state="idle")),          # a MODEL word in the agent's mouth
            (7, self.doc(**{"heartbeat_utc": "yesterday"})),
            (8, self.doc(**{"stale_after_s": 99999})),
            (9, self.doc(**{"heartbeat_utc": old})),
        ]

    def test_T8_every_rule_renders_unread_or_stale_never_health(self):
        """Every broken-document case renders UNREAD (or STALE for rule 9), never a healthy state."""
        for n, obj in self.rules():
            with self.subTest(rule=n):
                if obj is None:
                    if status.status_path("Fable").exists():
                        status.status_path("Fable").unlink()
                else:
                    self.put("Fable", obj)
                r = status.render_lane("Fable", now=self.now)
                want = "STALE" if n == 9 else "UNREAD"
                self.assertEqual(r["rendered_agent"], want, f"rule {n}")
                self.assertNotIn(r["rendered_agent"], status.AGENT_STATES)
                self.assertNotEqual(r["rendered_model"], "idle")

    def test_T8_control_a_valid_document_renders_its_state(self):
        """Control: a valid document renders its own agent state with no reason."""
        self.put("Fable", self.doc(agent_state="handing"))
        r = status.render_lane("Fable", now=self.now)
        self.assertEqual(r["rendered_agent"], "handing")
        self.assertIsNone(r["agent_reason"])

    def test_T8b_every_unread_carries_a_remedy(self):
        """Every UNREAD/STALE case carries a non-trivial reason sentence for agent and model."""
        for n, obj in self.rules():
            with self.subTest(rule=n):
                if obj is None:
                    if status.status_path("Fable").exists():
                        status.status_path("Fable").unlink()
                else:
                    self.put("Fable", obj)
                r = status.render_lane("Fable", now=self.now)
                self.assertTrue((r["agent_reason"] or "").strip(), f"rule {n} reason empty")
                self.assertGreater(len(r["agent_reason"]), 30, f"rule {n} reason too thin")
                self.assertTrue((r["model_reason"] or "").strip(), f"rule {n} model reason")

    def test_T19_a_lane_may_not_exempt_itself_from_L2(self):
        """An out-of-range stale_after_s renders UNREAD; an in-range one (control) renders normally."""
        self.put("Fable", self.doc(**{"stale_after_s": 99999}))
        self.assertEqual(status.render_lane("Fable", now=self.now)["rendered_agent"], "UNREAD")
        self.put("Fable", self.doc(**{"stale_after_s": 30}))          # control
        self.assertEqual(status.render_lane("Fable", now=self.now)["rendered_agent"], "watching")


# =========================================================== T8c - the on-disk enum

class TestWriteRefusals(Fixture):
    """Tests of what write_status and write_model_declared refuse to put on disk."""

    def test_T8c_write_status_refuses_the_readers_verdicts(self):
        """write_status raises ValueError when an agent or model state is UNREAD or STALE."""
        for bad in ("UNREAD", "STALE"):
            with self.subTest(agent=bad):
                with self.assertRaises(ValueError) as cm:
                    status.write_status("Fable", self.doc(agent_state=bad))
                self.assertIn("reader", str(cm.exception).lower())
            with self.subTest(model=bad):
                d = self.doc()
                d["model"]["state"] = bad
                with self.assertRaises(ValueError):
                    status.write_status("Fable", d)

    def test_T8c_control_a_valid_document_is_written_and_reads_back(self):
        """Control: a valid document is written and read_status returns it."""
        status.write_status("Fable", self.doc(agent_state="mirroring"))
        d, st, reason = status.read_status("Fable")
        self.assertEqual((st, reason), ("ok", None))
        self.assertEqual(d["agent"]["state"], "mirroring")

    def test_T8c_a_null_model_state_is_legal_and_renders_unread(self):
        """A null model state may be written, and it renders the model layer as UNREAD."""
        d = self.doc()
        d["model"]["state"] = None                      # the honest publish when probes fail
        d["model"]["sidecar"] = {"status": "UNREAD", "reason": "ack-fable.json does not exist",
                                 "state": None}
        status.write_status("Fable", d)
        r = status.render_lane("Fable", now=self.now)
        self.assertEqual(r["rendered_model"], "UNREAD")
        self.assertNotEqual(r["rendered_model"], "idle")

    def test_T12_declaring_a_sidecar_state_is_refused(self):
        """write_model_declared refuses blocked-on-* / UNREAD / STALE; idle, working, composing pass."""
        for bad in ("blocked-on-ack", "blocked-on-rab", "UNREAD", "STALE"):
            with self.subTest(state=bad):
                with self.assertRaises(ValueError) as cm:
                    status.write_model_declared("Fable", bad)
                self.assertIn("gate.py", str(cm.exception))
        for good in ("idle", "working", "composing"):   # control
            self.assertEqual(status.write_model_declared("Fable", good)["state"], good)


# =========================================================== T9 / T9b - staleness

class TestStaleness(Fixture):
    """Tests of the age thresholds that turn a heartbeat into STALE."""

    def test_T9_both_directions(self):
        """A heartbeat 16 s old is STALE (with an age in the reason); 14 s old is healthy."""
        self.put("Fable", self.doc(**{"heartbeat_utc": stamp(self.now - timedelta(seconds=16))}))
        r = status.render_lane("Fable", now=self.now)
        self.assertEqual(r["rendered_agent"], "STALE")
        self.assertIn("ago", r["agent_reason"])
        self.assertRegex(r["agent_reason"], r"\d")             # L2: never a bare STALE

        self.put("Fable", self.doc(**{"heartbeat_utc": stamp(self.now - timedelta(seconds=14))}))
        self.assertEqual(status.render_lane("Fable", now=self.now)["rendered_agent"], "watching")

    def test_T9b_the_board_changes_with_the_clock_alone(self):
        """The clause an optimiser would break: no file changes between these two renders."""
        self.put("Fable", self.doc())
        before = os.stat(status.status_path("Fable")).st_mtime_ns
        a = status.render_lane("Fable", now=self.now)
        b = status.render_lane("Fable", now=self.now + timedelta(seconds=16))
        after = os.stat(status.status_path("Fable")).st_mtime_ns
        self.assertEqual(before, after, "the render must not write")
        self.assertEqual(a["rendered_agent"], "watching")
        self.assertEqual(b["rendered_agent"], "STALE")
        self.assertNotEqual(a["rendered_agent"], b["rendered_agent"])

    def test_T10_a_derived_reading_is_never_fresher_than_its_publisher(self):
        """A stale agent forces the model reading to UNREAD; a fresh one (control) shows idle."""
        old = stamp(self.now - timedelta(seconds=60))
        self.put("Fable", self.doc(model_state="idle", **{"heartbeat_utc": old}))
        r = status.render_lane("Fable", now=self.now)
        self.assertEqual(r["rendered_agent"], "STALE")
        self.assertEqual(r["rendered_model"], "UNREAD")     # though the disk says idle
        self.assertIn("publisher", r["model_reason"])

        self.put("Fable", self.doc(model_state="idle"))     # control: same model block, fresh
        r2 = status.render_lane("Fable", now=self.now)
        self.assertEqual(r2["rendered_model"], "idle")


# =========================================================== T11 / T12b - the model layer

class TestModelLayer(Fixture):
    """Tests of the model-layer rules: the sidecar probe versus the model's own declaration."""

    def sidecar_fixtures(self):
        """Six (name, planted sidecar content) cases that the sidecar reader must call UNREAD."""
        good = self.good_sidecar()
        return [
            ("missing", None),
            ("unparseable", "{ nope"),
            ("not a dict", json.dumps([1])),
            ("wrong protocol", dict(good, protocol="fp-relay-ack/v0")),
            ("wrong writer", dict(good, writer="Codex")),
            ("sent not a list", dict(good, sent={})),
        ]

    def test_T11_a_failed_sidecar_probe_beats_a_fresh_declaration(self):
        """For each bad sidecar, read_sidecar gives UNREAD with a remedy and the model renders
        UNREAD even beside a fresh 'idle' declaration."""
        for name, obj in self.sidecar_fixtures():
            with self.subTest(rule=name):
                p = status.sidecar_path("Fable")
                if obj is None:
                    if p.exists():
                        p.unlink()
                else:
                    self.put_sidecar("Fable", obj)
                _d, st, reason = status.read_sidecar("Fable")
                self.assertEqual(st, "UNREAD", name)
                self.assertTrue(reason and len(reason) > 30, f"{name}: no remedy")

                d = self.doc(model_state="idle")
                d["model"]["sidecar"] = status.sidecar_view("Fable")
                d["model"]["declared"] = {"status": "ok", "state": "idle",
                                          "utc": stamp(self.now), "age_s": 0.5, "reason": None}
                self.put("Fable", d)
                r = status.render_lane("Fable", now=self.now)
                self.assertEqual(r["rendered_model"], "UNREAD", name)
                self.assertNotEqual(r["rendered_model"], "idle")

    def test_T11_control_a_readable_sidecar_renders_its_state(self):
        """Control: a readable sidecar in state working renders the model as working."""
        self.put_sidecar("Fable", self.good_sidecar(state="working"))
        d = self.doc(model_state="working")
        d["model"]["sidecar"] = status.sidecar_view("Fable")
        self.put("Fable", d)
        self.assertEqual(status.render_lane("Fable", now=self.now)["rendered_model"], "working")

    def test_T12b_a_declaration_may_not_clear_a_block(self):
        """A sidecar blocked-on-rab / blocked-on-ack still renders even when the model declares idle."""
        for blocked in ("blocked-on-rab", "blocked-on-ack"):
            with self.subTest(state=blocked):
                self.put_sidecar("Fable", self.good_sidecar(state=blocked))
                d = self.doc(model_state=blocked)
                d["model"]["sidecar"] = status.sidecar_view("Fable")
                d["model"]["declared"] = {"status": "ok", "state": "idle",
                                          "utc": stamp(self.now), "age_s": 0.2, "reason": None}
                self.put("Fable", d)
                r = status.render_lane("Fable", now=self.now)
                self.assertEqual(r["rendered_model"], blocked)

    def test_a_sidecar_state_of_UNREAD_is_not_a_model_state(self):
        """gate.py's --state choices include the literal 'UNREAD'. A lane may not declare its
        own probe failed, so it renders UNREAD - the reader's verdict - not a state."""
        self.put_sidecar("Fable", self.good_sidecar(state="UNREAD"))
        view = status.sidecar_view("Fable")
        self.assertEqual(view["status"], "ok")
        self.assertIsNone(view["state"])
        self.assertIn("not one of the five", view["state_note"])


# =========================================================== T15 - the UNREAD trail

class TestTrails(Fixture):
    """Tests of roomlog's flight-trail rendering and its stage-writer rules."""

    def test_T15_an_entry_with_no_flight_file_is_UNREAD_not_typed(self):
        """A logged message with no flight file renders UNREAD, with all eight stages listed."""
        e = roomlog.append_entry(frm="Rab", to="Fable", body="a question")
        log = roomlog.read_log()
        t = roomlog.render_trails(e.id, log=log, now=self.now)   # S157 E52: the §5.4 object is render_trails
        lane = t["trails"]["Fable"]
        self.assertEqual(lane["rendered"], "UNREAD")
        self.assertNotEqual(lane["rendered"], "typed")
        self.assertIn("Fable", lane["reason"])
        self.assertEqual(len(lane["stages"]), 8)          # never an empty trail

    def test_T13_writer_half_an_agent_may_not_claim_delivery(self):
        """append_stage refuses 'delivered' and 'model-working' from a catcher; 'caught' is accepted."""
        e = roomlog.append_entry(frm="Rab", to="Fable", body="a question")
        for stage in ("delivered", "model-working"):
            with self.subTest(stage=stage):
                with self.assertRaises(ValueError):
                    roomlog.append_stage(e.id, stage, "catcher:Fable")
        roomlog.append_stage(e.id, "caught", "catcher:Fable")        # control
        self.assertTrue(roomlog.flight_path(e.id).exists())


# =========================================================== T16 - quarantine

class TestQuarantine(Fixture):
    """Tests that nothing is written outside the prototype's own tree."""

    def test_T16_assert_inside_both_directions(self):
        """assert_inside accepts a path under STATE and exits for a path in the system temp dir."""
        self.assertTrue(roomlog.assert_inside(roomlog.STATE / "x.json"))
        with self.assertRaises(SystemExit):
            roomlog.assert_inside(Path(tempfile.gettempdir()) / "definitely-outside.json")

    def test_T16_a_foreign_FP_COORD_is_overridden_and_left_empty(self):
        """With FP_COORD pointing elsewhere, the catcher's gate_init still writes inside the
        quarantined coord directory and leaves the foreign directory empty. Restores the env var."""
        foreign = Path(tempfile.mkdtemp(prefix="foreign-coord-"))
        saved = os.environ.get("FP_COORD")
        os.environ["FP_COORD"] = str(foreign)
        try:
            c = catcher.Catcher("Fable", interval=2.0, quiet=True)
            rec = c.gate_init()
            self.assertEqual(rec["coord_dir"], str(roomlog.COORD))
            self.assertTrue(status.sidecar_path("Fable").exists(),
                            "the quarantined coord/ did not receive the write")
            self.assertEqual(list(foreign.iterdir()), [],
                             "the foreign FP_COORD directory was written to")
        finally:
            if saved is None:
                os.environ.pop("FP_COORD", None)
            else:
                os.environ["FP_COORD"] = saved
            shutil.rmtree(foreign, ignore_errors=True)


# =========================================================== T24 / T26 - the gate allow-list

class TestGateAllowList(Fixture):
    """Tests that catcher.py only ever calls the allowed gate.py subcommands."""

    ALLOWED = {"init", "post", "ticket", "status", "inbox"}
    FORBIDDEN = {"check", "confirm", "escalate", "resolve"}

    def argv_literals(self):
        """Every list literal passed as the first positional argument of subprocess.run in
        catcher.py's source."""
        with io.open(HERE / "catcher.py", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute) else
                    getattr(f, "id", None))
            if name != "run":
                continue
            if not node.args or not isinstance(node.args[0], ast.List):
                continue
            items = []
            for el in node.args[0].elts:
                items.append(el.value if isinstance(el, ast.Constant) else "<expr>")
            found.append(items)
        return found

    def test_T24_the_subcommand_is_always_in_the_allow_list(self):
        """Every subprocess.run argv literal in catcher.py names an allowed gate subcommand."""
        argvs = self.argv_literals()
        self.assertGreaterEqual(len(argvs), 3,
                                "no subprocess.run list literals found - the parser is looking "
                                "at nothing, which would make this test a tautology")
        for argv in argvs:
            with self.subTest(argv=argv[:4]):
                self.assertGreater(len(argv), 2)
                self.assertIn(argv[2], self.ALLOWED)
                self.assertNotIn(argv[2], self.FORBIDDEN)

    def test_T24_control_the_parser_would_catch_a_forbidden_subcommand(self):
        """Proof of failure: the same parser, over source that DOES call `confirm`."""
        src = ('import subprocess\n'
               'subprocess.run([sys.executable, str(GATE_PY), "confirm", "--as", "Fable"])\n')
        tree = ast.parse(src)
        subs = [n.args[0].elts[2].value for n in ast.walk(tree)
                if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "run"]
        self.assertEqual(subs, ["confirm"])
        self.assertIn(subs[0], self.FORBIDDEN)          # the guard would have fired

    def test_T26_the_mirror_carries_no_ticket(self):
        """Every `post` call in catcher.py omits --ticket and --override."""
        posts = [a for a in self.argv_literals() if a[2] == "post"]
        self.assertTrue(posts, "no `post` invocation found")
        for argv in posts:
            self.assertNotIn("--ticket", argv)
            self.assertNotIn("--override", argv)

    def test_T26_control_a_ticketed_post_is_refused_by_the_real_gate(self):
        """The reason for the omission is MEASURED, not asserted: adding --ticket against a
        peer reproduces a real `REFUSED` and a non-zero rc from gate.py itself."""
        self.gate_init_both()
        self.put_sidecar("Codex", self.good_sidecar(
            lane="Codex", state="working", current_ticket="RM-000000000001"))
        body = roomlog.STATE / "tmp" / "b.md"
        body.parent.mkdir(parents=True, exist_ok=True)
        io.open(body, "w", encoding="utf-8").write("a notice\n")
        proc = subprocess.run(
            [PY, str(roomlog.GATE_PY), "post", "--as", "Fable", "--to", "Codex",
             "--subject", "x", "--body", str(body), "--ticket", "RM-000000000002"],
            capture_output=True, encoding="utf-8", errors="replace",
            env={**os.environ, "FP_COORD": str(roomlog.COORD)}, timeout=60)
        out = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, "a ticketed post into a working peer SUCCEEDED")
        if "Traceback (most recent call last)" in out:
            # Distinguish "the guard fired" from "the tool crashed". Both are non-zero, and
            # collapsing them into `assertNotEqual(rc, 0)` would let this control pass against
            # a gate.py that cannot refuse anything at all - a tautology wearing a green tick.
            self.fail(
                "gate.py CRASHED instead of refusing - the guard this control measures could "
                "not run, so nothing was proven. This is a finding about gate.py, not about "
                "the mirror. Output:\n" + out[-600:])
        self.assertIn("REFUSED", out)


# =========================================================== T25 - GUARD B carried across

class TestGuardB(Fixture):
    """Tests that the catcher never takes a ticket from a lane that is blocked on Rab."""

    def a_message_for_fable(self):
        """Append a Rab-to-Fable message to the temp log and return the Entry."""
        return roomlog.append_entry(frm="Rab", to="Fable", body="please look at the ladder")

    def test_T25_a_blocked_on_rab_sidecar_is_never_ticketed(self):
        """With the sidecar blocked-on-rab, one catcher cycle skips the gate, keeps the block,
        and still writes the handoff envelope."""
        self.gate_init_both()
        self.put_sidecar("Fable", self.good_sidecar(
            state="blocked-on-rab",
            escalations=[{"utc": stamp(self.now), "ticket": "T-1", "asking": "a real question",
                          "why": None, "msg_id": "MSG-FAB-0001", "state": "open"}]))
        e = self.a_message_for_fable()

        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        c.start()
        doc = c.one_cycle(now=self.now)

        self.assertEqual(doc["gate"]["status"], "skipped")
        self.assertIsNone(doc["gate"]["last_cmd"], "a gate command was built at all")
        self.assertEqual(doc["agent"]["state"], "awaiting-model")
        after, st, _r = status.read_sidecar("Fable")
        self.assertEqual(st, "ok")
        self.assertEqual(after["state"], "blocked-on-rab",
                         "the agent cleared the principal's gate as a side effect")
        self.assertTrue((roomlog.HANDOFF_DIR / "Fable" / f"{e.id}.json").exists(),
                        "the envelope must still be written - the message is not lost")

    def test_T25_control_an_idle_sidecar_IS_ticketed(self):
        """Control: with an idle sidecar, one catcher cycle takes the ticket and sets state working."""
        self.gate_init_both()
        e = self.a_message_for_fable()
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        c.start()
        doc = c.one_cycle(now=self.now)

        self.assertEqual(doc["gate"]["status"], "ok", doc["gate"].get("reason"))
        self.assertEqual(doc["gate"]["last_cmd"][2], "ticket")
        after, st, _r = status.read_sidecar("Fable")
        self.assertEqual(st, "ok")
        self.assertEqual(after["state"], "working")
        self.assertEqual(after["current_ticket"], e.id)


# =========================================================== T27 - rc 0 is not health

class TestExitCodeIsNotHealth(Fixture):
    """Tests that Catcher.gate_record judges gate output, not just the process exit code."""

    def test_T27_rc_zero_while_printing_UNREAD_is_UNREAD(self):
        """A gate call that exits 0 but prints UNREAD is recorded as UNREAD."""
        self.gate_init_both()                      # a perfectly healthy sidecar on disk
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        proc = subprocess.CompletedProcess(
            args=[PY, str(roomlog.GATE_PY), "inbox", "--as", "Fable"],
            returncode=0,
            stdout="UNREAD: ack-codex.json - Codex has not turned the skill on\n", stderr="")
        rec = c.gate_record(proc)
        self.assertEqual(rec["last_rc"], 0)
        self.assertEqual(rec["status"], "UNREAD")
        self.assertIn("exit code is not a health reading", rec["reason"])

    def test_T27_control_a_real_successful_call_reads_ok(self):
        """Control: a clean exit with a normal ticket line is recorded as ok."""
        self.gate_init_both()
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        proc = subprocess.CompletedProcess(
            args=[PY, str(roomlog.GATE_PY), "ticket", "--as", "Fable"],
            returncode=0, stdout="Fable: ticket=RM-000000000001 state=working", stderr="")
        self.assertEqual(c.gate_record(proc)["status"], "ok")

    def test_T27_an_unreadable_sidecar_outranks_a_clean_exit(self):
        """A damaged sidecar makes gate_record UNREAD even when the exit code is 0."""
        self.put_sidecar("Fable", "{ torn")
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        proc = subprocess.CompletedProcess(args=["x", "y", "ticket"], returncode=0,
                                           stdout="looks fine", stderr="")
        rec = c.gate_record(proc)
        self.assertEqual(rec["status"], "UNREAD")
        self.assertIn("damaged", rec["reason"])


# =========================================================== crash safety

class TestCrashSafety(Fixture):
    """Crash safety: an absent room.md, a torn journal, and the rule that the published document never carries a
    verdict (UNREAD/STALE) as its own state."""

    def test_an_unreadable_log_is_never_no_new_messages(self):
        """With no room.md, one cycle reports agent state error and a null (not zero) entry count."""
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        doc = c.one_cycle(now=self.now)                       # room.md does not exist
        self.assertEqual(doc["agent"]["state"], "error")
        self.assertEqual(doc["agent"]["log_read"]["status"], "MISSING")
        self.assertIsNone(doc["agent"]["log_read"]["count"], "0 is a reading; this probe failed")
        self.assertTrue(doc["agent"]["last_error"])

    def test_a_torn_journal_is_rebuilt_from_the_log_not_read_as_empty(self):
        """A corrupt journal file is rebuilt from the log and marked REBUILT with a reason."""
        roomlog.append_entry(frm="Rab", to="Fable", body="hello")
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        with io.open(c.journal_path(), "w", encoding="utf-8") as fh:
            fh.write("{ torn")
        c.load_journal(roomlog.read_log())
        self.assertEqual(c.journal_status, "REBUILT")
        self.assertIn("rebuilt_reason", c.journal)

    def test_the_publish_never_writes_a_verdict_about_itself(self):
        """The document a cycle publishes never carries UNREAD or STALE as its own state."""
        self.gate_init_both()
        roomlog.append_entry(frm="Rab", to="Fable", body="hello")
        c = catcher.Catcher("Fable", interval=2.0, quiet=True)
        doc = c.one_cycle(now=self.now)
        self.assertIn(doc["agent"]["state"], status.AGENT_STATES)
        self.assertNotIn(doc["agent"]["state"], status.VERDICTS)
        self.assertNotIn(doc["model"]["state"], status.VERDICTS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
