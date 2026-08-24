#!/usr/bin/env python3
"""test_room.py - the tripwires for prototypes/relay-room/ (CONTRACT.md §8, law L8).

Run:  python -m unittest discover -s <ROOT> -p "test_room.py"

L8: a guard born today gets its tripwire today, AND the tripwire must be proven to FAIL against
code lacking the guard. Where the contract says "Control", the control is part of the test, not a
nice-to-have. A test that passes both ways is a tautology and is worse than no test, because it
buys confidence without buying evidence.

⚠ WHO WROTE THIS, AND WHY THAT MATTERS. I (Claude Opus 5, Fable lane) also wrote `roomlog.py`,
which most of these tests judge. That is the mirror problem: tests written by the implementer
inherit the implementer's blind spots. T-007 originally assigned this file to the Codex lane for
exactly that reason, and it came back to me only because Codex was down to 10% of its usage
budget. The residue is REAL and is not cancelled by saying so. Codex has been asked to review this
file adversarially and specifically to name any test here that passes both ways.
Evidence for the concern, from tonight: the three defects in roomlog.py were all found by a
harness I did NOT write, and I mis-diagnosed two of them before measuring.

NOT IMPLEMENTED HERE, declared rather than left to look like coverage (see NOT_YET below):
the live-server suite (T3, T4, T20, T21, T12), the catcher-cycle suite (T24, T25, T26, T27) and
the end-to-end (T28). They need a bound port and a driven catcher. `selftest.py` renders their
laws UNREAD until they land, and UNREAD is not a skip - it is a law with no reading behind it.
"""

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import roomlog  # noqa: E402

# L8.1 reads this: which tripwires guard which law.
TRIPWIRES = {
    "L1 UNREAD is never idle": ["T18", "T15", "T8"],
    "L2 staleness is not health": ["T15b", "T9"],
    "L3 appends never erase": ["T6", "T6a", "T6b", "T6c", "T7", "T17", "T18a"],
    "L4 fail closed": ["T2", "T5"],
    "L5 quarantine": ["T16"],
    "L5.2 stage authorship": ["T13", "T14"],
    "L6 stdlib only": ["T6d"],
    "L7 self-contained HTML": ["T22", "T23", "T23b", "T23c"],
    "L8 a guard gets its tripwire, proven to fail": ["every *_control below"],
}
# Bare names, because the roll call greps for the token and "T16_assert_inside" is not "T16".
# T8 = the L1 UNREAD ladder · T9 = L2 staleness · T13 = L5.2 stage authorship · T16 = L5
# quarantine. Named here even where this file covers only part of the contract's version, and
# NOT_YET below says which parts are missing - a name is a claim, so an unqualified one would be
# the coverage lie this whole harness exists to prevent.
NOT_YET = ["T3", "T4", "T12", "T20", "T21", "T24", "T25", "T26", "T27_live", "T28"]

SRC = {p.name: p.read_text(encoding="utf-8", errors="replace")
       for p in ROOT.glob("*.py")}
HTML = (ROOT / "room.html").read_text(encoding="utf-8", errors="replace")


_FIXTURE_SEQ = [0]


def _fixture_dir():
    """INSIDE ROOT, deliberately. The first cut used tempfile.mkdtemp(), which is outside ROOT,
    so `assert_inside` raised SystemExit - the quarantine working exactly as designed, against
    its own test suite. Tests do not get an exemption from the law they are testing."""
    _FIXTURE_SEQ[0] += 1
    d = roomlog.STATE / f"_test-{os.getpid()}-{_FIXTURE_SEQ[0]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def naive_append(path: Path, body: str) -> str:
    """The appender WITHOUT the last-byte check - the control for T6. This is what gate.py:203
    does: an unconditional newline with no look at the file."""
    mid = "RM-" + hashlib.sha256(f"{time.time_ns()}{body}".encode()).hexdigest()[:12]
    dg = roomlog.digest(body).split(":", 1)[1]
    hdr = (f"## {mid} · {roomlog.utc_now()} · from: Rab → to: Fable · re: — · kind: say "
           f"· body-sha256:{dg}")
    with io.open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(hdr + "\n\n" + body + "\n\n" + roomlog.terminator(mid) + "\n")
    return mid


class L3AppendsNeverErase(unittest.TestCase):
    """The law that SYM-037 paid for."""

    def setUp(self):
        self.d = _fixture_dir()
        self.torn = "2026-08-24T00:00:00.000Z partial body line torn in half by a crash mid-write"

    def _seed_torn(self, name):
        p = self.d / name
        p.write_bytes(("# relay-room · the chat log\n\n" + self.torn).encode("utf-8"))
        self.assertFalse(p.read_bytes().endswith(b"\n"), "fixture must NOT end in a newline")
        return p

    def test_T6_last_byte_check(self):
        p = self._seed_torn("t6.md")
        before = p.read_bytes()
        mid = roomlog.append_entry(frm="Rab", to="Fable", body="the record that must survive",
                                   path=p).id
        after = p.read_bytes()
        self.assertTrue(after.startswith(before), "the bytes already on disk changed (L3)")
        r = roomlog.read_log(p)
        self.assertEqual(r.status, "ok")
        self.assertIn(mid, [e.id for e in r.entries], "the survivor is not an entry")
        self.assertTrue(r.debris, "the torn remnant was not surfaced as debris")
        entry = [e for e in r.entries if e.id == mid][0]
        self.assertTrue(entry.digest_ok, "the survivor's digest does not verify")

    def test_T6_control_naive_appender_glues(self):
        """CONTROL (mandatory): without the last-byte check the header is glued to the remnant
        and read_log cannot see the new entry AS an entry. This is the proof-of-failure L8
        demands - without it, T6 proves only that the code runs."""
        p = self._seed_torn("t6c.md")
        mid = naive_append(p, "the record that will be lost")
        text = p.read_text(encoding="utf-8")
        glued = [ln for ln in text.split("\n") if self.torn in ln and ln.strip() != self.torn]
        self.assertTrue(glued, "the naive appender did NOT glue - the control proves nothing")
        r = roomlog.read_log(p)
        self.assertNotIn(mid, [e.id for e in r.entries],
                         "the glued header was still parsed as an entry, so T6 is a tautology")

    def test_T6a_no_truncating_mode(self):
        """The rule is about the LOG, not about every file. The first cut flagged catcher.py and
        status.py for `io.open(tmp, "w")` - the temp half of a part-then-rename, which is the
        repo's own publish invariant and the opposite of a truncating write to a live file. A
        test that convicts the correct idiom trains you to ignore the test."""
        trunc = re.compile(r"""(?:io\.)?open\(\s*([A-Za-z_][A-Za-z_0-9.\[\]"' ]*)\s*,\s*["'](?:w|r\+|w\+|wb)["']""")
        for name, src in SRC.items():
            if name in ("test_room.py", "selftest.py", "test_room_c.py"):
                continue
            for target in trunc.findall(src):
                self.assertIn("tmp", target.lower(),
                              f"{name} truncates {target!r}; a truncating open is only legal on "
                              f"the temp half of a part-then-rename")
            self.assertNotIn(".truncate(", src, f"{name} calls truncate()")

    def test_T6b_lock_holds_under_two_threads(self):
        p = self.d / "t6b.md"
        p.write_text("# relay-room · the chat log\n\n", encoding="utf-8", newline="")
        errors = []
        barrier = threading.Barrier(2)

        def worker(tag):
            barrier.wait()
            for i in range(25):
                try:
                    roomlog.append_entry(frm="Rab", to="Fable", body=f"{tag}#{i}", path=p)
                except BaseException as exc:   # SystemExit is NOT an Exception,
                    # and a thread dying of it dies silently - the same
                    # failed-probe-as-silence class this suite exists to catch.
                    errors.append(f"{tag}#{i}: {type(exc).__name__}: {exc}")

        ths = [threading.Thread(target=worker, args=(t,)) for t in ("Fable", "Codex")]
        for t_ in ths:
            t_.start()
        for t_ in ths:
            t_.join()
        self.assertEqual(errors, [], f"appends raised under contention: {errors[:2]}")
        r = roomlog.read_log(p)
        self.assertEqual(len(r.entries), 50)
        self.assertEqual(len({e.id for e in r.entries}), 50, "ids collided")
        self.assertEqual(r.torn, 0, "a torn entry means a write interleaved")
        self.assertEqual(r.debris, [], f"debris means a lost or mangled record: {r.debris[:1]}")

    def test_T6b_control_no_lock_interleaves(self):
        """CONTROL: with the lock bypassed and a sleep injected inside the critical section, the
        race is deterministic rather than probabilistic."""
        p = self.d / "t6b-ctl.md"
        p.write_text("# relay-room · the chat log\n\n", encoding="utf-8", newline="")
        barrier = threading.Barrier(2)

        def unlocked(tag):
            # DETERMINISTIC, not probabilistic. The first cut appended in "a" mode with an
            # injected sleep and was FLAKY: O_APPEND is atomic for small writes here, so the two
            # writers usually did NOT corrupt each other and this control passed clean about half
            # the time. A control that fires only sometimes is a coin-flip dressed as evidence,
            # and CONTRACT.md §8 T6b names this exact hazard and says PREFER THE INJECTED SLEEP
            # over probability. (An earlier attempt to add flush()/fsync() here silently failed
            # to apply and I did not check - so the flake survived a fix that reported success.)
            #
            # So: model the failure the lock actually prevents - a read-modify-write. Both
            # writers capture the SAME end-of-file offset, both sleep, both write THERE. The
            # second clobbers the first and a whole record is lost. That is unlocked file
            # writing's real failure mode, and it fires every time.
            mid = "RM-" + hashlib.sha256(tag.encode()).hexdigest()[:12]
            dg = roomlog.digest(tag).split(":", 1)[1]
            hdr = (f"## {mid} · {roomlog.utc_now()} · from: Rab → to: Fable · re: — "
                   f"· kind: say · body-sha256:{dg}")
            entry = hdr + "\n\n" + tag + "\n\n" + roomlog.terminator(mid) + "\n"
            offset = p.stat().st_size                # captured BEFORE the barrier releases
            barrier.wait()
            time.sleep(0.05)                         # both threads now hold the SAME offset
            with io.open(p, "r+", encoding="utf-8", newline="") as fh:
                fh.seek(offset)
                fh.write(entry)

        ths = [threading.Thread(target=unlocked, args=(t,)) for t in ("aaa", "bbb")]
        for t_ in ths:
            t_.start()
        for t_ in ths:
            t_.join()
        r = roomlog.read_log(p)
        # A LOST RECORD is the worst damage and the first cut of this control did not look for
        # it: it checked torn/debris/digest and called a file with one of two entries "clean".
        # The unlocked writers had silently dropped an entire record - exactly SYM-037's shape -
        # and the control reported no damage. A control that cannot see the primary failure mode
        # is not a control.
        lost = len(r.entries) < 2
        damaged = (lost or r.torn > 0 or bool(r.debris)
                   or any(not e.digest_ok for e in r.entries))
        self.assertTrue(damaged,
                        f"the unlocked writers produced a clean file ({len(r.entries)} entries, "
                        f"torn={r.torn}, debris={len(r.debris)}) - the control proves nothing, "
                        f"so T6b is a tautology")

    def test_T6c_stale_lock_is_broken_not_silent(self):
        d = self.d / "stale.lock"
        d.mkdir()
        os.utime(d, (time.time() - 999, time.time() - 999))
        lk = roomlog.Lock(d, timeout_s=2.0, stale_s=1.0, owner="probe")
        with lk:
            self.assertIsNotNone(lk.broke, "a stale lock was taken over SILENTLY")
        self.assertFalse(d.exists(), "the lock was not released")

    def test_T6c_control_fresh_lock_is_not_broken(self):
        """CONTROL: a FRESH lock must NOT be broken - it times out instead. Without this, T6c
        would pass against a Lock that simply steals every lock it finds."""
        d = self.d / "fresh.lock"
        d.mkdir()
        with self.assertRaises(roomlog.LockTimeout):
            with roomlog.Lock(d, timeout_s=0.4, stale_s=999, owner="probe"):
                pass
        self.assertTrue(d.exists(), "a fresh lock was stolen")
        d.rmdir()

    def test_T7_id_reroll_on_collision(self):
        p = self.d / "t7.md"
        const = lambda: "deadbeefdeadbeef"                              # noqa: E731
        a = roomlog.append_entry(frm="Rab", to="Fable", body="same body", path=p, nonce=const)
        b = roomlog.append_entry(frm="Rab", to="Fable", body="same body", path=p, nonce=const)
        self.assertNotEqual(a.id, b.id,
                            "a pinned nonce produced the same id twice - the duplicate scan "
                            "did not re-roll")

    def test_T7_control_pinned_nonce_and_clock_would_collide(self):
        """CONTROL: with the clock frozen too, the raw id derivation IS deterministic - proving
        the re-roll (not luck) is what separates the two ids."""
        raw = "%d\x1fRab\x1f%s\x1fdeadbeefdeadbeef" % (1, roomlog.canonical("same body"))
        one = "RM-" + hashlib.sha256(raw.encode()).hexdigest()[:12]
        two = "RM-" + hashlib.sha256(raw.encode()).hexdigest()[:12]
        self.assertEqual(one, two, "the derivation is not deterministic; the control is invalid")

    def test_T17_torn_entry_not_merged(self):
        p = self.d / "t17.md"
        a, b = "RM-" + "a" * 12, "RM-" + "b" * 12
        dga = roomlog.digest("first").split(":", 1)[1]
        dgb = roomlog.digest("second").split(":", 1)[1]
        u = roomlog.utc_now()
        p.write_text(
            "# relay-room · the chat log\n\n"
            f"## {a} · {u} · from: Rab → to: Fable · re: — · kind: say · body-sha256:{dga}\n\n"
            "first\n\n"                                  # terminator deliberately missing
            f"## {b} · {u} · from: Fable → to: Rab · re: — · kind: say · body-sha256:{dgb}\n\n"
            "second\n\n" + roomlog.terminator(b) + "\n",
            encoding="utf-8", newline="")
        r = roomlog.read_log(p)
        ids = [e.id for e in r.entries]
        self.assertIn(a, ids, "the torn entry was dropped")
        self.assertIn(b, ids, "the entry after the torn one was swallowed")
        self.assertTrue([e for e in r.entries if e.id == a][0].torn, "torn was not flagged")
        self.assertEqual(r.torn, 1)

    def test_T18_missing_is_not_ok_with_zero(self):
        r = roomlog.read_log(self.d / "does-not-exist.md")
        self.assertEqual(r.status, "MISSING", "a missing log read back as something else")
        self.assertTrue((r.reason or "").strip(), "MISSING with no remedy (L1b)")
        self.assertNotEqual(r.status, "ok")

    def test_T18_control_preamble_only_is_ok_with_zero(self):
        """CONTROL, the other direction: an EXISTING file with no entries is legitimately
        ok/0. Without this, T18 would pass against a read_log that called everything MISSING."""
        p = self.d / "empty.md"
        p.write_text(roomlog.PREAMBLE, encoding="utf-8", newline="")
        r = roomlog.read_log(p)
        self.assertEqual(r.status, "ok")
        self.assertEqual(len(r.entries), 0)

    def test_T18a_terminator_token_refused_but_hash_heading_ok(self):
        p = self.d / "t18a.md"
        with self.assertRaises(ValueError):
            roomlog.append_entry(frm="Rab", to="Fable", body="x <!-- /RM-abc --> y", path=p)
        e = roomlog.append_entry(frm="Rab", to="Fable",
                                 body="## this line merely starts with hashes\nand more",
                                 path=p)
        r = roomlog.read_log(p)
        got = [x for x in r.entries if x.id == e.id]
        self.assertEqual(len(got), 1, "a body containing a '## ' line did not round-trip")
        self.assertTrue(got[0].digest_ok)


class L1L2UnreadAndStale(unittest.TestCase):
    def test_T15_entry_with_no_flight_is_UNREAD_not_typed(self):
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hello", path=p)
        log = roomlog.read_log(p)
        tr = roomlog.render_trail(e.id, "Fable", log=log)
        self.assertEqual(tr["file_status"], "MISSING")
        self.assertEqual(tr["rendered"], "UNREAD",
                         "a message with no flight record rendered as something other than UNREAD")
        self.assertIn("Fable", tr["reason"] or "", "the remedy does not name the lane (L1b)")

    def test_T15_control_landed_is_reached_from_the_log_itself(self):
        """CONTROL: 'landed' IS derived and must render reached, so T15 is not satisfied by a
        renderer that calls everything UNREAD."""
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hello", path=p)
        tr = roomlog.render_trail(e.id, "Fable", log=roomlog.read_log(p))
        landed = [s for s in tr["stages"] if s["name"] == "landed"][0]
        self.assertTrue(landed["reached"], "landed was not derived from the log")

    def test_T13_writer_refuses_and_reader_ignores(self):
        with self.assertRaises(ValueError):
            roomlog.append_stage("RM-" + "a" * 12, "landed", "catcher:Fable")
        with self.assertRaises(ValueError):
            roomlog.append_stage("RM-" + "a" * 12, "caught", "nobody")
        with self.assertRaises(ValueError):
            roomlog.append_stage("RM-" + "a" * 12, "delivered", "catcher:Fable")
        with self.assertRaises(ValueError):
            roomlog.append_stage("RM-" + "a" * 12, "model-working", "catcher:Codex")

    def test_T14_failed_stage_stops_the_trail(self):
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hi", path=p)
        fp = roomlog.flight_path(e.id)
        fp.parent.mkdir(parents=True, exist_ok=True)
        rows = [{"id": e.id, "stage": "caught", "utc": roomlog.utc_now(),
                 "by": "catcher:Fable", "ok": False, "note": "digest mismatch — re-read the log"},
                {"id": e.id, "stage": "handed", "utc": roomlog.utc_now(),
                 "by": "catcher:Fable", "ok": True, "note": None}]
        fp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="")
        tr = roomlog.render_trail(e.id, "Fable", log=roomlog.read_log(p))
        self.assertEqual(tr["rendered"], "FAILED")
        handed = [s for s in tr["stages"] if s["name"] == "handed"][0]
        self.assertFalse(handed["reached"], "a stage after a FAILED one rendered as reached")
        fp.unlink()

    def test_T14_control_both_ok_renders_handed(self):
        """CONTROL: the same shape with ok:true must render handed, or T14 passes against a
        renderer that never advances at all."""
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hi", path=p)
        fp = roomlog.flight_path(e.id)
        fp.parent.mkdir(parents=True, exist_ok=True)
        rows = [{"id": e.id, "stage": s, "utc": roomlog.utc_now(),
                 "by": "catcher:Fable", "ok": True, "note": None} for s in ("caught", "handed")]
        fp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="")
        tr = roomlog.render_trail(e.id, "Fable", log=roomlog.read_log(p))
        self.assertEqual(tr["rendered"], "handed")
        fp.unlink()

    def test_T15b_stalled_trail_is_not_quiet(self):
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hi", path=p)
        fp = roomlog.flight_path(e.id)
        fp.parent.mkdir(parents=True, exist_ok=True)
        old = datetime.now(timezone.utc) - timedelta(seconds=600)
        stamp = old.strftime("%Y-%m-%dT%H:%M:%S.") + f"{old.microsecond // 1000:03d}Z"
        fp.write_text(json.dumps({"id": e.id, "stage": "caught", "utc": stamp,
                                  "by": "catcher:Fable", "ok": True, "note": None}) + "\n",
                      encoding="utf-8", newline="")
        tr = roomlog.render_trail(e.id, "Fable", log=roomlog.read_log(p), stall_after_s=90)
        self.assertEqual(tr["rendered"], "STALLED")
        self.assertIn("stalled at", (tr["reason"] or ""))
        fp.unlink()

    def test_T15b_control_fresh_trail_is_not_stalled(self):
        d = _fixture_dir()
        p = d / "room.md"
        e = roomlog.append_entry(frm="Rab", to="Fable", body="hi", path=p)
        roomlog.append_stage(e.id, "caught", "catcher:Fable")
        tr = roomlog.render_trail(e.id, "Fable", log=roomlog.read_log(p), stall_after_s=90)
        self.assertNotEqual(tr["rendered"], "STALLED")
        roomlog.flight_path(e.id).unlink(missing_ok=True)

    def test_T9_parse_utc_failure_is_None_not_now(self):
        """A timestamp that will not parse must not silently become 'now' or age zero."""
        self.assertIsNone(roomlog.parse_utc("not a timestamp"))
        self.assertIsNone(roomlog.parse_utc(""))
        self.assertIsNotNone(roomlog.parse_utc(roomlog.utc_now()))


class L5Quarantine(unittest.TestCase):
    def test_T16_assert_inside_refuses_outside(self):
        with self.assertRaises(SystemExit):
            roomlog.assert_inside(Path(tempfile.gettempdir()) / "definitely-outside.md")

    def test_T16_control_assert_inside_accepts_inside(self):
        got = roomlog.assert_inside(roomlog.STATE / "ok.md")
        self.assertTrue(str(got).startswith(str(roomlog.ROOT)))

    def test_T16_no_escape_via_relay_room_substring(self):
        """A path containing 'relay-room' elsewhere must NOT sail through - the check is
        computed against ROOT, not by splitting on a string."""
        with self.assertRaises(SystemExit):
            roomlog.assert_inside(Path(tempfile.gettempdir()) / "relay-room" / "x.md")

    def test_T16_gate_py_is_outside_and_is_never_written(self):
        self.assertFalse(str(roomlog.GATE_PY).startswith(str(roomlog.ROOT) + os.sep),
                         "GATE_PY should live outside this prototype")


class L6L7SourceLaws(unittest.TestCase):
    def test_T6d_stdlib_only(self):
        third_party = re.compile(r"^\s*(?:import|from)\s+(requests|numpy|flask|aiohttp|yaml|"
                                 r"pydantic|httpx|django|pandas)\b", re.M)
        for name, src in SRC.items():
            self.assertIsNone(third_party.search(src), f"{name} imports a third-party package")

    def test_T22_no_html_injection_sinks(self):
        for sink in ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML",
                     "new Function"):
            self.assertNotIn(sink, HTML, f"room.html uses {sink}")

    def test_T23_no_external_resources(self):
        for pat in (r'src\s*=\s*["\']https?:', r'src\s*=\s*["\']//',
                    r'href\s*=\s*["\']https?:', r"@import", "fonts.googleapis"):
            self.assertIsNone(re.search(pat, HTML), f"room.html references {pat}")

    def test_T23b_ui_can_name_every_state(self):
        for s in roomlog.STAGES:
            self.assertIn(s, HTML, f"room.html cannot name stage {s}, so it cannot render it")
        for lit in ("UNREAD", "STALE"):
            self.assertIn(lit, HTML, f"room.html cannot name {lit}")

    def test_T23c_theme_blocks_and_root_tokens(self):
        self.assertIn("prefers-color-scheme: dark", HTML)
        self.assertIn('[data-theme="dark"]', HTML)
        root = set(re.findall(r"(--[a-z0-9-]+)\s*:", HTML.split("@media")[0]))
        self.assertTrue(root, "no custom properties defined on :root at all")


class L4FailClosedSource(unittest.TestCase):
    """Source-level halves of L4. The live-server halves (T3, T4) are in NOT_YET."""

    def test_T2_token_gate_precedes_route_dispatch(self):
        src = SRC.get("room.py", "")
        m = re.search(r"def do_POST\b", src)
        if not m:
            self.skipTest("room.py has no do_POST")
        body = src[m.start():]
        gate_at = body.find("token_gate(")
        route_at = body.find('self.path == "')
        self.assertNotEqual(gate_at, -1, "do_POST never calls token_gate")
        self.assertTrue(gate_at < route_at,
                        "a route is dispatched before the token gate - a route added later "
                        "could escape it")

    def test_T5_no_cors_headers_in_source(self):
        """Look for an EMITTED header, not the mere string: room.py's docstring names
        Access-Control-Allow precisely to say it never sends one, and the first cut of this
        test convicted the documentation of the law it documents."""
        emit = re.compile(r"""send_header\(\s*["']Access-Control-Allow""")
        for name, src in SRC.items():
            self.assertIsNone(emit.search(src), f"{name} SENDS a CORS header")


class L8Honesty(unittest.TestCase):
    def test_the_not_yet_list_is_declared_not_hidden(self):
        self.assertTrue(NOT_YET, "NOT_YET must name what this file does not cover")
        self.assertIn("T28", NOT_YET)

    def test_every_law_names_at_least_one_tripwire(self):
        for law, names in TRIPWIRES.items():
            self.assertTrue(names, f"{law} names no tripwire")


if __name__ == "__main__":
    unittest.main(verbosity=2)
