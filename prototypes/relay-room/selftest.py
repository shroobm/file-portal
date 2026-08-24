#!/usr/bin/env python3
"""selftest.py - the LAW PROOF harness for prototypes/relay-room.

This is not the tripwire suite. `test_room.py` (CONTRACT.md §8) proves the 39 named tripwires
T1-T28 against the finished build. THIS file proves the EIGHT LAWS of CONTRACT.md §0, and it
proves them BOTH WAYS: every guarded assertion is also run against a deliberately unguarded
control, and a control that does NOT fail is reported as a TAUTOLOGY, which is a failure.

    "A guard born today gets its tripwire today, and the tripwire must be proven to FAIL
     against code that lacks the guard. A test that passes both ways is a tautology."  - L8

THREE THINGS THIS HARNESS DOES THAT AN ORDINARY TEST FILE DOES NOT
------------------------------------------------------------------
1. It runs against a COPY of the sources, staged in a fresh `tempfile.mkdtemp()`. Nothing is
   imported from, and nothing is written to, the live `prototypes/relay-room/state/` tree. The
   staged copy's own `ROOT` is the temp dir, so `assert_inside` fences the temp dir, and a
   quarantine escape lands in the temp dir rather than in the repo.
2. It SNAPSHOTS the real `coordination/` directory and the real `state/` tree (size + mtime_ns,
   recursively) before anything runs, and re-checks the snapshot at the very end. "I did not
   touch the real relay" is therefore a MEASUREMENT here, not a promise. Rab has a live open
   escalation in that directory; the promise was not good enough.
3. UNREAD IS NOT A SKIP. A check that could not RUN - because a module has not landed, because
   the server would not start - is recorded UNREAD, printed in its own column, and counted into
   the exit code as a failure. A missing module is not zero defects; it is zero readings. That
   is L1 turned on the harness itself, and it is the whole reason this file exists in a repo
   whose most expensive defect class (SYM-031) is a failed probe rendered as health.

RUN
---
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe selftest.py
    ... --verbose      print the detail line for passing checks too
    ... --keep         leave the temp tree on disk and print its path
    ... --list         print the check roster and exit 0 without running anything

Exit 0 only when every check PASSED and every control FIRED. Any FAIL, any UNREAD, any
TAUTOLOGY -> exit 1.

stdlib only (L6). Target Python 3.12 on Windows.

Authorship claim only, never Rab's authority: <claimed: Fable>, 2026-08-24.
"""

import argparse
import ast
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# LOCATIONS.  Derived, never guessed.
# ---------------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent                     # prototypes/relay-room
REPO = ROOT.parents[1]                                     # file-portal
GATE_PY = REPO / ".claude" / "skills" / "relay-gate" / "gate.py"
REAL_COORD = REPO / "coordination"                         # THE ONE WE MUST NOT TOUCH
REAL_STATE = ROOT / "state"                                # the live prototype state tree

# The modules this harness expects the four builders to land. Order matters only for reporting.
BUILD_FILES = ("roomlog.py", "status.py", "catcher.py", "room.py", "room.html", "test_room.py")
LOCAL_MODULES = {"roomlog", "status", "catcher", "room", "test_room", "selftest"}

# Copied into the staged tree. state/ and __pycache__/ are never copied - the point is a clean
# tree, and copying the live state would be the exact contamination this file exists to prevent.
STAGE_SKIP_DIRS = {"state", "__pycache__", ".git", ".pytest_cache"}


# ---------------------------------------------------------------------------------------------
# THE GRAMMAR - held INDEPENDENTLY, on purpose.
#
# This regex is a hand copy of CONTRACT.md §2.3, not an import of roomlog.HEADER_RE. A test that
# imports the grammar it is checking cannot detect a change to the grammar: it would agree with
# any edit, forever. Two copies that must agree is the point. If roomlog's regex drifts from this
# one, the L3 checks below start failing, which is the correct and desired outcome.
# ---------------------------------------------------------------------------------------------

SELFTEST_HEADER_RE = re.compile(
    r"^## (?P<id>RM-[0-9a-f]{12})"
    r" \u00b7 (?P<utc>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)"
    r" \u00b7 from: (?P<frm>Rab|Fable|Codex)"
    r" \u2192 to: (?P<to>Rab|Fable|Codex|all)"
    r" \u00b7 re: (?P<re>RM-[0-9a-f]{12}|\u2014)"
    r" \u00b7 kind: (?P<kind>say|note|error)"
    r" \u00b7 body-sha256:(?P<digest>[0-9a-f]{64})$"
)
SELFTEST_TERM_RE = re.compile(r"^<!-- /RM-[0-9a-f]{12} -->$")

SEP = " \u00b7 "        # SPACE MIDDLE-DOT SPACE
ARROW = " \u2192 "      # SPACE RIGHTWARDS-ARROW SPACE
EMDASH = "\u2014"       # answers nothing

PROTOCOL = "fp-relay-room/v1"


def _utc(dt=None) -> str:
    """Millisecond-precision UTC, CONTRACT.md §2.3."""
    d = dt or datetime.now(timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def _canonical(text: str) -> str:
    """gate.py:61-69 semantics, reimplemented (L5 forbids importing skill code)."""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def _bare_digest(text: str) -> str:
    return hashlib.sha256(_canonical(text).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# VERDICTS
# ---------------------------------------------------------------------------------------------

PASS, FAIL, UNREAD = "PASS", "FAIL", "UNREAD"


class Unread(Exception):
    """The check could not be RUN. Not a pass. Not a skip. Carries a remedy (L1b)."""

    def __init__(self, reason: str, remedy: str):
        super().__init__(reason)
        self.reason = reason
        self.remedy = remedy


class Tautology(AssertionError):
    """A control did not fail the probe. The probe therefore proves nothing."""


CHECKS = []          # [(law, cid, title, fn, is_control)] - registration order IS execution order
RESULTS = []         # [dict(law, cid, title, verdict, detail, remedy, control)]


def register(law: str, cid: str, title: str, *, control: bool = False):
    """`control=True` marks a check whose job is to FAIL a probe against unguarded code.

    The flag is explicit and not inferred from the title. It was inferred once, with
    `"control" in title.lower()`, and the very first run mis-classified the check named
    "no route carries an Access-Control-Allow-* header" as a control - a substring match on a
    header name. A classifier that reads prose is a classifier that reads wrong.
    """
    def deco(fn):
        CHECKS.append((law, cid, title, fn, control))
        return fn
    return deco


def expect_fail(probe, *args, **kwargs) -> str:
    """Run a probe against UNGUARDED code and REQUIRE it to fail.

    This is the L8 half. If the probe passes here it passes against anything, which means it
    was never measuring the guard - it was measuring nothing. That is reported as a TAUTOLOGY
    and is a hard failure, never a pass.
    """
    try:
        probe(*args, **kwargs)
    except AssertionError as exc:
        first = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        return f"control fired: {first[:150]}"
    except Exception as exc:                        # noqa: BLE001 - deliberate
        raise AssertionError(
            f"the control raised {exc.__class__.__name__}({str(exc)[:120]!r}) instead of failing "
            f"the assertion - the probe never got to make its judgment, so this proves nothing"
        ) from exc
    raise Tautology(
        "TAUTOLOGY: the probe PASSED against code that lacks the guard, so it does not measure "
        "the guard. Rewrite the probe until the unguarded control fails it (L8)."
    )


# ---------------------------------------------------------------------------------------------
# FIXTURE BUILDERS - used ONLY to construct inputs and to drive the unguarded controls.
# They are never used to judge the real appender: judgment goes through SELFTEST_HEADER_RE and
# through the build's own read_log.
# ---------------------------------------------------------------------------------------------

def _fixture_entry(mid: str, body: str, *, frm="Rab", to="Fable", re_=None, kind="say",
                   utc=None) -> str:
    hdr = (f"## {mid}{SEP}{utc or _utc()}{SEP}from: {frm}{ARROW}to: {to}"
           f"{SEP}re: {re_ or EMDASH}{SEP}kind: {kind}{SEP}body-sha256:{_bare_digest(body)}")
    if not SELFTEST_HEADER_RE.match(hdr):            # the fixture builder checks itself
        raise RuntimeError(f"selftest fixture built a header its own grammar rejects: {hdr!r}")
    return hdr + "\n\n" + body.strip("\n") + "\n\n" + f"<!-- /{mid} -->" + "\n"


_fixture_counter = [0]


def _fixture_id(seed: str) -> str:
    _fixture_counter[0] += 1
    raw = f"{seed}\x1f{_fixture_counter[0]}\x1f{time.time_ns()}"
    return "RM-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def naive_append(path: Path, body: str) -> str:
    """CONTROL - the appender WITHOUT the last-byte check (L3).

    One line is missing relative to the real appender: the seek(-1, 2) probe of CONTRACT.md
    §2.5 step 6. Everything else is identical. That single omission is what glues a new header
    onto a torn line and destroys both records - SYM-037, reproduced here on purpose.
    """
    mid = _fixture_id("naive")
    with io.open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(_fixture_entry(mid, body))          # <-- no lead, no last-byte check
    return mid


def rewriting_append(path: Path, body: str) -> str:
    """CONTROL - the 'tidy' appender that rewrites the whole file (violates L3).

    It reads, normalises trailing whitespace, and writes the file back in "w" mode. Every byte
    it writes is defensible on its own; together they mean the prefix of the log is no longer
    the bytes that were witnessed. This is what "append-only" forbids.
    """
    mid = _fixture_id("rewrite")
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    tidied = "\n".join(ln.rstrip() for ln in old.replace("\r\n", "\n").split("\n"))
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(tidied.rstrip("\n") + "\n\n" + _fixture_entry(mid, body))
    return mid


def lost_update_append(path: Path, body: str) -> str:
    """CONTROL - an appender with NO LOCK, doing read-modify-write (violates §2.6).

    The sleep between the read and the write makes the race deterministic rather than
    probabilistic, which is what CONTRACT.md §8's T6b control asks for: "prefer the injected
    sleep". Two threads through this function lose records every time.
    """
    mid = _fixture_id("lost")
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    time.sleep(0.004)                                 # the window a lock would have closed
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(old + _fixture_entry(mid, body))
    return mid


def naive_render_lane(state_dir: Path, lane: str) -> dict:
    """CONTROL - the status renderer WITHOUT the UNREAD/STALE ladder (violates L1 and L2).

    Its only sin is the `except` branch, and the sin is a single word: `idle`. It reads a
    missing file, a corrupt file, and a month-old file all the same way, and it renders every
    one of them as a healthy negative reading. This is SYM-031 written in four lines.
    """
    p = state_dir / f"status-{lane.lower()}.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"rendered_agent": d["agent"]["state"], "agent_reason": None,
                "rendered_model": d["model"]["state"], "model_reason": None}
    except Exception:                                 # noqa: BLE001 - the defect, verbatim
        return {"rendered_agent": "idle", "agent_reason": None,
                "rendered_model": "idle", "model_reason": None}


def naive_read_log(path: Path) -> dict:
    """CONTROL - a log reader that reports a missing file as an empty healthy log (violates L1)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:                                 # noqa: BLE001
        return {"status": "ok", "entries": [], "reason": None}
    return {"status": "ok", "entries": SELFTEST_HEADER_RE.findall(text), "reason": None}


def valid_status_doc(lane: str, *, heartbeat: str = None, stale_after_s: float = 15.0,
                     agent_state: str = "watching", protocol: str = PROTOCOL,
                     writer: str = None) -> dict:
    """A status document that satisfies CONTRACT.md §4.2 in full. Mutated per fixture."""
    now = datetime.now(timezone.utc)
    return {
        "protocol": protocol,
        "writer": writer if writer is not None else f"catcher:{lane}",
        "lane": lane,
        "pid": os.getpid(),
        "started_utc": _utc(now - timedelta(seconds=60)),
        "heartbeat_utc": heartbeat if heartbeat is not None else _utc(now),
        "cycle": 30,
        "heartbeat_interval_s": 2.0,
        "stale_after_s": stale_after_s,
        "model_stale_after_s": 300.0,
        "agent": {
            "state": agent_state,
            "since_utc": _utc(now - timedelta(seconds=5)),
            "detail": "selftest fixture",
            "last_error": None,
            "consecutive_errors": 0,
            "log_read": {"status": "ok", "count": 0, "torn": 0, "debris": 0,
                         "bytes": 0, "read_utc": _utc(now)},
        },
        "model": {
            "state": "idle",
            "source": "declared",
            "since_utc": _utc(now - timedelta(seconds=5)),
            "note": None,
            "sidecar": {"status": "ok", "state": "idle", "ticket": None, "sent": 0,
                        "confirmed": 0, "updated_utc": now.strftime("%Y-%m-%dT%H:%MZ"),
                        "path": f"state/coord/ack-{lane.lower()}.json", "reason": None},
            "declared": {"status": "ok", "state": "idle", "utc": _utc(now),
                         "ticket": None, "note": None, "reason": None},
        },
        "in_flight": None,
        "gate": {"status": "ok", "coord_dir": "selftest", "last_cmd": None, "last_rc": 0,
                 "last_utc": _utc(now), "last_stdout": None, "last_stderr": None},
    }


# ---------------------------------------------------------------------------------------------
# INDEPENDENT LOG SCANNER - byte-level, owned by this file, shared by guarded and control runs.
# ---------------------------------------------------------------------------------------------

def scan_log_bytes(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    heads, ids = [], []
    for ln in lines:
        m = SELFTEST_HEADER_RE.match(ln)
        if m:
            heads.append(ln)
            ids.append(m.group("id"))
    terms = [ln for ln in lines if SELFTEST_TERM_RE.match(ln)]
    # A header that is not at column 0 of its own line has been GLUED to something.
    glued = [ln for ln in lines if "## RM-" in ln and not ln.startswith("## RM-")]
    return {"bytes": raw, "text": text, "ids": ids, "headers": heads,
            "terminators": terms, "glued": glued}


# ---------------------------------------------------------------------------------------------
# THE PROBES.  Each takes an implementation and judges it. Each is run TWICE: once against the
# build, once against an unguarded control that must fail it.
# ---------------------------------------------------------------------------------------------

TORN_REMNANT = "2026-08-24T00:00:00.000Z partial body line torn in half by a crash mid-write"


def probe_last_byte(append, path: Path) -> None:
    """L3: appending onto a file whose last byte is NOT a newline."""
    path.write_bytes(("# relay-room \u00b7 the chat log\n\nprologue\n\n" + TORN_REMNANT)
                     .encode("utf-8"))
    before = path.read_bytes()
    assert not before.endswith(b"\n"), "fixture is wrong: the file must NOT end in a newline"
    mid = append(path, "the record that must survive a torn predecessor")
    scan = scan_log_bytes(path)
    assert scan["bytes"].startswith(before), (
        "the bytes that were already on disk changed - appends never erase (L3)")
    assert not scan["glued"], (
        f"the new header was glued onto the torn line: {scan['glued'][0][:110]!r} - the "
        f"last-byte check of CONTRACT.md §2.5 step 6 is missing")
    assert mid in scan["ids"], (
        f"the new entry {mid} is not a column-0 header, so it is not a record at all - it was "
        f"absorbed into the torn line and both records are lost (SYM-037)")
    assert TORN_REMNANT in scan["text"], (
        "the torn remnant was erased - a torn line stays torn and surfaces as debris; it is "
        "never tidied away")


def probe_prefix_immutable(append, path: Path) -> None:
    """L3: everything already written stays byte-for-byte identical."""
    seed = ("# relay-room \u00b7 the chat log   \n\na preamble line with a trailing space   \n\n"
            + _fixture_entry(_fixture_id("seed1"), "first")
            + "\n" + _fixture_entry(_fixture_id("seed2"), "second"))
    path.write_text(seed, encoding="utf-8", newline="")
    before = path.read_bytes()
    before_dg = hashlib.sha256(before).hexdigest()
    append(path, "the append that must not disturb one byte behind it")
    after = path.read_bytes()
    assert len(after) > len(before), "the append wrote nothing"
    prefix = after[:len(before)]
    assert hashlib.sha256(prefix).hexdigest() == before_dg, (
        "the prefix of the log CHANGED across an append: "
        f"sha256 {before_dg[:16]}... -> {hashlib.sha256(prefix).hexdigest()[:16]}... - the log "
        "was rewritten, not appended to (L3)")


def probe_concurrent(append, path: Path, *, per_lane: int = 25) -> None:
    """L3/§2.6: two lanes appending at once. Real threads, real writes, no mock."""
    path.write_text("# relay-room \u00b7 the chat log\n\n", encoding="utf-8", newline="")
    errors, lanes = [], ("Fable", "Codex")
    barrier = threading.Barrier(len(lanes))

    def worker(tag):
        barrier.wait()                                # make them collide on purpose
        for i in range(per_lane):
            try:
                append(path, f"lane {tag} message {i}")
            except Exception as exc:                  # noqa: BLE001
                errors.append(f"{tag}#{i}: {exc.__class__.__name__}: {str(exc)[:100]}")

    threads = [threading.Thread(target=worker, args=(t,), daemon=True) for t in lanes]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    assert not errors, f"{len(errors)} append(s) raised; first: {errors[0]}"
    want = len(lanes) * per_lane
    scan = scan_log_bytes(path)
    assert not scan["glued"], f"a header was glued to another line: {scan['glued'][0][:110]!r}"
    assert len(scan["ids"]) == want, (
        f"{len(scan['ids'])} records survived out of {want} - {want - len(scan['ids'])} were "
        f"lost to the race")
    assert len(set(scan["ids"])) == len(scan["ids"]), (
        f"{len(scan['ids']) - len(set(scan['ids']))} duplicate id(s) - two writers minted the "
        f"same id (SYM-045)")
    assert len(scan["terminators"]) == want, (
        f"{len(scan['terminators'])} terminators for {want} headers - at least one entry has no "
        f"boundary and is torn")


def probe_missing_status_unread(render, lane: str) -> None:
    """L1: a status file that is not there is UNREAD, never idle."""
    r = render(lane)
    got = r.get("rendered_agent")
    assert got == "UNREAD", (
        f"a MISSING status file rendered {got!r} - a reading requires a probe that worked; the "
        f"probe did not work, so the only honest answer is UNREAD (L1, SYM-031)")
    assert (r.get("agent_reason") or "").strip(), (
        "UNREAD with no remedy sentence - L1b: every UNREAD says what to do about it")


def probe_malformed_status_unread(render, lane: str, label: str) -> None:
    """L1: a status file that cannot be trusted is UNREAD, never idle."""
    r = render(lane)
    got = r.get("rendered_agent")
    assert got == "UNREAD", (
        f"a MALFORMED status file ({label}) rendered {got!r}, not UNREAD - the file exists but "
        f"the probe still failed, and a failed probe is not a healthy reading (L1)")
    assert (r.get("agent_reason") or "").strip(), f"UNREAD ({label}) with no remedy (L1b)"


def probe_old_heartbeat_stale(render, lane: str) -> None:
    """L2: an old heartbeat is STALE with an age, never green."""
    r = render(lane)
    got = r.get("rendered_agent")
    assert got == "STALE", (
        f"a heartbeat older than stale_after_s rendered {got!r} - absence of an update is not "
        f"evidence of idleness (L2)")
    reason = (r.get("agent_reason") or "")
    assert reason.strip(), "STALE with no remedy (L1b)"
    assert re.search(r"\d", reason), (
        f"STALE with no age in the reason: {reason[:110]!r} - CONTRACT.md §4.6 requires "
        f"'STALE (last seen Nm Ns ago)', never a bare STALE and never a colour alone")


def probe_fresh_heartbeat_healthy(render, lane: str, expect_state: str) -> None:
    """The other direction of L2: a live lane must render its real state, not STALE."""
    r = render(lane)
    got = r.get("rendered_agent")
    assert got == expect_state, (
        f"a FRESH heartbeat rendered {got!r}, expected {expect_state!r} - if a healthy lane "
        f"cannot render healthy, the STALE verdict above proves nothing")


def probe_missing_log_not_ok(read, path: Path) -> None:
    """L1 on the log itself: a missing room.md is MISSING, not 'ok with zero entries'."""
    assert not path.exists(), "fixture is wrong: the file must not exist"
    r = read(path)
    status = r.get("status")
    assert status != "ok", (
        f"a MISSING room.md read back as {status!r} with {len(r.get('entries') or [])} entries - "
        f"'zero entries' is a READING and there was no reading (L1)")
    assert status in ("MISSING", "UNREAD"), f"unexpected log status {status!r}"
    assert (r.get("reason") or "").strip(), "a MISSING log with no remedy (L1b)"


def probe_token_refused(base: str, room_md: Path) -> None:
    """L4: a mutating route with no token refuses, with a remedy, AND writes nothing."""
    before = room_md.read_bytes() if room_md.exists() else b""
    payload = json.dumps({"from": "Rab", "to": "Fable", "re": None, "kind": "say",
                          "body": "this POST carries no token and must not land"}).encode("utf-8")
    code, headers, body = http("POST", base + "/api/say",
                               headers={"Content-Type": "application/json"}, body=payload)
    assert code == 403, (
        f"a mutating POST with NO token returned {code}, not 403 - the gate did not fail closed (L4)")
    text = body.decode("utf-8", "replace")
    try:
        err = (json.loads(text) or {}).get("error") or ""
    except Exception:                                 # noqa: BLE001
        err = ""
    assert err.strip(), (
        f"the 403 carried no remedy text - body was {text[:110]!r}. L1b: a refusal that does not "
        f"say how to proceed is a dead end, not a guard")
    after = room_md.read_bytes() if room_md.exists() else b""
    assert after == before, (
        "the route answered 403 but the log CHANGED - a leaking gate: the refusal is cosmetic "
        "and the write happened anyway")


def probe_assert_inside(guard, inside: Path, outside: Path) -> None:
    """L5: the quarantine refuses a path outside ROOT and admits one inside."""
    try:
        guard(outside)
    except SystemExit:
        pass
    except Exception as exc:                          # noqa: BLE001
        raise AssertionError(
            f"the quarantine raised {exc.__class__.__name__} for an outside path; CONTRACT.md "
            f"§6.4 specifies SystemExit with a remedy") from exc
    else:
        raise AssertionError(
            f"the quarantine ADMITTED a path outside ROOT: {outside} - L5 is absolute; nothing "
            f"outside prototypes/relay-room/ may be written, ever")
    guard(inside)                                     # must not raise


def probe_stdlib_only(sources: dict) -> None:
    """L6: every import in every module resolves to the stdlib or to a sibling here."""
    stdlib = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    assert stdlib, "this interpreter does not expose sys.stdlib_module_names; cannot judge L6"
    offenders = []
    for name, src in sources.items():
        for mod in imports_of(src, name):
            if mod not in stdlib and mod not in LOCAL_MODULES:
                offenders.append(f"{name}: import {mod}")
    assert not offenders, (
        f"third-party import(s): {', '.join(offenders[:6])} - L6 is stdlib-only so Codex can run "
        f"this with whatever interpreter it has")


def probe_self_contained_html(html: str) -> None:
    """L7: one file, no CDN, no external font, no remote anything."""
    bad = []
    for pat, why in (
        (r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", "an absolute or protocol-relative URL"),
        (r"@import", "a CSS @import"),
        (r"fonts\.googleapis|fonts\.gstatic", "a Google Fonts host"),
        (r"""<link[^>]+rel\s*=\s*["']stylesheet""", "an external stylesheet link"),
    ):
        m = re.search(pat, html, re.I)
        if m:
            bad.append(f"{why} ({m.group(0)[:40]!r})")
    assert not bad, f"room.html reaches off the machine: {'; '.join(bad)} - L7 forbids it"


def probe_no_html_injection(html: str) -> None:
    """T22: the page renders two language models' output; string-assembled HTML is not allowed."""
    hits = [t for t in ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML",
                        "new Function") if t in html]
    assert not hits, (
        f"room.html uses {', '.join(hits)} - bodies are model output and go in by textContent "
        f"only (CONTRACT.md §7.2)")


# ---------------------------------------------------------------------------------------------
# SMALL UTILITIES
# ---------------------------------------------------------------------------------------------

def imports_of(src: str, filename: str) -> set:
    mods = set()
    tree = ast.parse(src, filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def http(method: str, url: str, *, headers=None, body=None, timeout=15):
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def free_port() -> int:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def snapshot(path: Path) -> dict:
    """(size, mtime_ns) for every file under path. 'MISSING' is itself a reading here."""
    if not path.exists():
        return {"__status__": "MISSING"}
    out = {"__status__": "ok"}
    try:
        for p in sorted(path.rglob("*")):
            try:
                st = p.stat()
                out[str(p.relative_to(path))] = (p.is_dir(), st.st_size, st.st_mtime_ns)
            except OSError as exc:
                out[str(p)] = f"UNREADABLE: {exc}"
    except OSError as exc:
        return {"__status__": f"UNREAD: {exc}"}
    return out


def diff_snapshot(before: dict, after: dict) -> list:
    keys = set(before) | set(after)
    out = []
    for k in sorted(keys):
        if before.get(k) != after.get(k):
            out.append(f"{k}: {before.get(k)!r} -> {after.get(k)!r}")
    return out


def run_py(args, *, env=None, cwd=None, timeout=60):
    """Run a python subprocess with THIS interpreter. utf-8 capture (CONTRACT.md §2.1)."""
    e = dict(os.environ)
    if env:
        e.update({k: v for k, v in env.items() if v is not None})
        for k, v in env.items():
            if v is None:
                e.pop(k, None)
    proc = subprocess.run([sys.executable, *[str(a) for a in args]], env=e,
                          cwd=str(cwd) if cwd else None, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return proc


def human_age(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s" if m else f"{s}s"


# ---------------------------------------------------------------------------------------------
# THE UNGUARDED CONTROL SERVER - a route that writes, with no token gate at all.
# ---------------------------------------------------------------------------------------------

class _UngatedHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):                        # silence
        pass

    def _json(self, obj, code=200):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/api/health"):
            self._json({"ok": True, "note": "unguarded control server"})
        else:
            self._json({"error": "no such route"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        self.rfile.read(n)
        # THE DEFECT, in three lines: it writes without ever looking for a token.
        with io.open(self.server.room_md, "a", encoding="utf-8", newline="") as fh:
            fh.write("\nthis line was written by a request that carried NO TOKEN\n")
        self._json({"id": "RM-000000000000", "stage": "landed"}, 200)


def start_ungated_server(room_md: Path):
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), _UngatedHandler)
    srv.room_md = room_md
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------------------------------------
# CONTEXT
# ---------------------------------------------------------------------------------------------

class Ctx:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.staged = tmp / "relay-room"
        self.state = self.staged / "state"
        self.probe = self.state / "probe"
        self.foreign_coord = tmp / "FOREIGN-coord-must-stay-empty"
        self.gatebox = tmp / "gatebox"
        self.mods = {}                 # name -> module or None
        self.mod_reason = {}           # name -> why it is None
        self.sources = {}              # filename -> source text (from the REAL ROOT)
        self.html = None
        self.server = None             # (proc, base_url, token)
        self.cleanup = []
        self.coord_before = None
        self.state_before = None
        self.init_rc = None
        self.init_out = ""

    # -- staged tree ---------------------------------------------------------------------
    def stage(self):
        self.staged.mkdir(parents=True, exist_ok=True)
        for item in sorted(ROOT.iterdir()):
            if item.name in STAGE_SKIP_DIRS:
                continue
            if item.is_dir():
                shutil.copytree(item, self.staged / item.name,
                                ignore=shutil.ignore_patterns(*STAGE_SKIP_DIRS))
            else:
                shutil.copy2(item, self.staged / item.name)
        self.probe.mkdir(parents=True, exist_ok=True)
        self.foreign_coord.mkdir(parents=True, exist_ok=True)
        self.gatebox.mkdir(parents=True, exist_ok=True)

    def load_modules(self):
        sys.path.insert(0, str(self.staged))
        import importlib
        for name in ("roomlog", "status", "catcher", "room"):
            src = self.staged / f"{name}.py"
            if not src.exists():
                self.mods[name] = None
                self.mod_reason[name] = (
                    f"{name}.py has not landed in {ROOT} - the builder who owns it "
                    f"(CONTRACT.md §9) has not written it yet")
                continue
            try:
                mod = importlib.import_module(name)
            except Exception as exc:                  # noqa: BLE001
                self.mods[name] = None
                self.mod_reason[name] = (
                    f"{name}.py exists but will not import: {exc.__class__.__name__}: "
                    f"{str(exc)[:160]}")
                continue
            # Refuse a module that resolved to the REAL tree - it would write the live state.
            mod_root = getattr(mod, "ROOT", None)
            if mod_root is not None and Path(str(mod_root)).resolve() != self.staged.resolve():
                self.mods[name] = None
                self.mod_reason[name] = (
                    f"{name} imported with ROOT={mod_root!r}, which is NOT the staged copy "
                    f"{self.staged} - refusing to run against the live tree")
                continue
            self.mods[name] = mod
            self.mod_reason[name] = None

    def load_sources(self):
        """EVERY .py in ROOT, not just the six on the manifest.

        Scanning only the manifest would leave a module nobody declared unscanned - and an
        undeclared module is precisely the one that smuggles in a third-party import or a
        pipeline import. `room_agent.py` was sitting here, off the manifest, on the first run.
        """
        for p in sorted(ROOT.glob("*.py")):
            self.sources[p.name] = p.read_text(encoding="utf-8", errors="replace")
            LOCAL_MODULES.add(p.stem)
        html = ROOT / "room.html"
        if html.exists():
            self.html = html.read_text(encoding="utf-8", errors="replace")

    def need(self, name: str):
        mod = self.mods.get(name)
        if mod is None:
            raise Unread(
                self.mod_reason.get(name) or f"{name} is not available",
                f"land {name}.py under {ROOT} (CONTRACT.md §9), then re-run this selftest")
        return mod

    def need_source(self, fname: str) -> str:
        if fname not in self.sources and fname != "room.html":
            raise Unread(f"{fname} has not landed under {ROOT}",
                         f"write {fname} per CONTRACT.md §9, then re-run this selftest")
        if fname == "room.html":
            if self.html is None:
                raise Unread(f"room.html has not landed under {ROOT}",
                             "write room.html per CONTRACT.md §7, then re-run this selftest")
            return self.html
        return self.sources[fname]

    # -- the live server -----------------------------------------------------------------
    def live_server(self):
        """Start room.py serve once, on an ephemeral port, against the STAGED state tree."""
        if self.server is not None:
            return self.server
        room_py = self.staged / "room.py"
        if not room_py.exists():
            raise Unread(f"room.py has not landed under {ROOT}",
                         "write room.py per CONTRACT.md §3, then re-run this selftest")
        if self.init_rc is None:
            self.run_init()
        if self.init_rc != 0:
            raise Unread(
                f"`room.py init` exited {self.init_rc}: {self.init_out[-400:]!r}",
                "fix `room.py init` (CONTRACT.md §6.1 step 1) - the server cannot be judged "
                "until the state tree it serves can be created")
        token = "5e1f7e57" * 4                        # 32 hex, deterministic, test-only
        port = free_port()
        env = dict(os.environ)
        env.pop("FP_COORD", None)                     # never inherit it (CONTRACT.md §6.4)
        log = open(self.tmp / "server.out", "ab")
        proc = subprocess.Popen(
            [sys.executable, str(room_py), "serve", "--port", str(port), "--token", token],
            cwd=str(self.staged), env=env, stdout=log, stderr=subprocess.STDOUT)
        base = f"http://127.0.0.1:{port}"
        self.cleanup.append(lambda: _stop(proc, log))
        deadline = time.time() + 25
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                code, _, _ = http("GET", base + "/api/health", timeout=3)
                if code == 200:
                    self.server = (proc, base, token)
                    return self.server
            except Exception:                          # noqa: BLE001 - not up yet
                pass
            time.sleep(0.25)
        tail = ""
        try:
            log.flush()
            tail = (self.tmp / "server.out").read_text(encoding="utf-8",
                                                       errors="replace")[-600:]
        except OSError:
            pass
        raise Unread(
            f"room.py serve did not answer GET /api/health on {base} within 25s "
            f"(exit={proc.poll()}); server output tail: {tail!r}",
            "run `room.py serve --port 7133` by hand and read the traceback; the token gate "
            "cannot be measured on a server that is not up, and an unmeasured gate is UNREAD, "
            "not open and not closed")

    def run_init(self):
        room_py = self.staged / "room.py"
        if not room_py.exists():
            self.init_rc, self.init_out = 127, "room.py missing"
            return
        # A FOREIGN FP_COORD is planted here on purpose: CONTRACT.md §6.4 says it is never
        # inherited. If room.py honours that, the foreign dir stays empty (checked in L5.4).
        # FP_GATE_PY: the staged tree is a COPY, so roomlog's ROOT-relative derivation resolves
        # to <tempdir>/.claude/skills/relay-gate/gate.py, which does not exist. Without this the
        # staged `init` fails and L5.4 can never RUN - it renders UNREAD, which this harness
        # rightly refuses to call a pass.
        #
        # ⚠ EDITED BY THE AUTHOR OF THE CODE THIS HARNESS JUDGES (Claude Opus 5, S109), after
        # the Codex lane ran out of budget and could not take it. That is a real loss of
        # independence and it is recorded here rather than in a commit nobody re-reads. What
        # makes it defensible: this adds an environment pass-through and touches NO assertion,
        # threshold or expectation. It converts an UNREAD into a check that can FAIL, so it
        # INCREASES this harness's power over roomlog.py rather than reducing it. Proven by
        # deliberately breaking room.py's FP_COORD override and confirming L5.4 then FAILS
        # (see the commit). If it had not failed, the edit was to be reverted and the check
        # left UNREAD.
        proc = run_py([room_py, "init"],
                      env={"FP_COORD": str(self.foreign_coord), "FP_GATE_PY": str(GATE_PY)},
                      cwd=self.staged, timeout=90)
        self.init_rc = proc.returncode
        self.init_out = (proc.stdout or "") + (proc.stderr or "")

    def close(self):
        for fn in reversed(self.cleanup):
            try:
                fn()
            except Exception:                          # noqa: BLE001
                pass


def _stop(proc, log):
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:                                  # noqa: BLE001
        try:
            proc.kill()
        except Exception:                              # noqa: BLE001
            pass
    try:
        log.close()
    except Exception:                                  # noqa: BLE001
        pass


# =============================================================================================
# THE CHECKS
# =============================================================================================

# ---- L0 - the harness proves it can pass, and proves it can fail ----------------------------

@register("L0", "L0.1", "positive control: a check that passes trivially")
def _l0_1(ctx):
    """If this line ever fails, nothing below it means anything."""
    assert 2 + 2 == 4
    assert hashlib.sha256(b"relay-room").hexdigest().startswith("")
    assert _bare_digest("a\r\nb  ") == _bare_digest("a\nb"), "canonical() is not line-ending blind"
    return "2+2=4, and canonical() is CRLF-blind - a PASS is reachable in this harness"


@register("L0", "L0.2", "negative control: the harness catches a probe that should fail",
          control=True)
def _l0_2(ctx):
    """Proves 'the guard fired' is distinguishable from 'everything always fires'."""
    def always_true_probe():
        assert True                                    # a probe that measures nothing
    try:
        expect_fail(always_true_probe)
    except Tautology:
        pass
    else:
        raise AssertionError("expect_fail() accepted a probe that cannot fail - the L8 "
                             "machinery of this harness is broken and every 'control fired' "
                             "line below is worthless")

    def honest_probe():
        assert False, "the thing under test is wrong"
    note = expect_fail(honest_probe)
    return f"tautology detector works; {note}"


@register("L0", "L0.3", "roll call: which of the six build files have landed")
def _l0_3(ctx):
    present = [f for f in BUILD_FILES if (ROOT / f).exists()]
    missing = [f for f in BUILD_FILES if not (ROOT / f).exists()]
    broken = [f"{n} ({r})" for n, r in ctx.mod_reason.items() if r and (ROOT / f"{n}.py").exists()]
    if missing or broken:
        raise Unread(
            f"{len(present)}/{len(BUILD_FILES)} build files present; missing: "
            f"{', '.join(missing) or 'none'}"
            + (f"; present but unusable: {'; '.join(broken)}" if broken else ""),
            "the checks below that need those modules render UNREAD, and UNREAD counts as a "
            "FAILURE in the exit code. That is deliberate: an unbuilt law is an unproven law, "
            "not a satisfied one.")
    return f"all {len(BUILD_FILES)} build files present and importable"


# ---- L1 - UNREAD IS NEVER IDLE ---------------------------------------------------------------

@register("L1", "L1.1", "a MISSING status file renders UNREAD, not idle")
def _l1_1(ctx):
    st = ctx.need("status")
    p = ctx.state / "status-fable.json"
    if p.exists():
        p.unlink()
    probe_missing_status_unread(lambda lane: st.render_lane(lane), "Fable")
    return "render_lane('Fable') on an absent file -> UNREAD + remedy"


@register("L1", "L1.2", "control: a renderer without the ladder calls the same file idle",
          control=True)
def _l1_2(ctx):
    ctx.state.mkdir(parents=True, exist_ok=True)
    p = ctx.state / "status-fable.json"
    if p.exists():
        p.unlink()
    return expect_fail(probe_missing_status_unread,
                       lambda lane: naive_render_lane(ctx.state, lane), "Fable")


MALFORMED_FIXTURES = [
    ("not JSON at all", "{ this is not json"),
    ("a JSON list, not an object", "[1, 2, 3]"),
    ("wrong protocol", None),
    ("wrong writer (single-writer law)", None),
    ("an agent state outside the enum", None),
    ("no readable heartbeat", None),
]


def _write_malformed(ctx, label):
    p = ctx.state / "status-fable.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    if label == "not JSON at all":
        p.write_text("{ this is not json", encoding="utf-8")
    elif label == "a JSON list, not an object":
        p.write_text("[1, 2, 3]", encoding="utf-8")
    elif label == "wrong protocol":
        d = valid_status_doc("Fable", protocol="fp-relay-room/v0")
        p.write_text(json.dumps(d), encoding="utf-8")
    elif label == "wrong writer (single-writer law)":
        d = valid_status_doc("Fable", writer="catcher:Codex")
        p.write_text(json.dumps(d), encoding="utf-8")
    elif label == "an agent state outside the enum":
        d = valid_status_doc("Fable", agent_state="fine")
        p.write_text(json.dumps(d), encoding="utf-8")
    elif label == "no readable heartbeat":
        d = valid_status_doc("Fable")
        d["heartbeat_utc"] = "whenever"
        p.write_text(json.dumps(d), encoding="utf-8")
    else:
        raise RuntimeError(label)
    return p


@register("L1", "L1.3", "a MALFORMED status file renders UNREAD, not idle (6 fixtures)")
def _l1_3(ctx):
    st = ctx.need("status")
    for label, _ in MALFORMED_FIXTURES:
        _write_malformed(ctx, label)
        probe_malformed_status_unread(lambda lane: st.render_lane(lane), "Fable", label)
    return f"{len(MALFORMED_FIXTURES)} malformed documents, {len(MALFORMED_FIXTURES)} UNREAD"


@register("L1", "L1.4", "control: the same six documents render idle without the ladder",
          control=True)
def _l1_4(ctx):
    notes = []
    for label, _ in MALFORMED_FIXTURES:
        _write_malformed(ctx, label)
        notes.append(expect_fail(probe_malformed_status_unread,
                                 lambda lane: naive_render_lane(ctx.state, lane), "Fable", label))
    return f"{len(notes)} controls fired; first: {notes[0][:80]}"


@register("L1", "L1.5", "every UNREAD verdict carries a remedy sentence (L1b)")
def _l1_5(ctx):
    st = ctx.need("status")
    checked, bare = 0, []
    p = ctx.state / "status-fable.json"
    if p.exists():
        p.unlink()
    cases = [("missing", None)] + [(lbl, lbl) for lbl, _ in MALFORMED_FIXTURES]
    for label, fixture in cases:
        if fixture:
            _write_malformed(ctx, fixture)
        elif p.exists():
            p.unlink()
        r = st.render_lane("Fable")
        for key in ("rendered_agent", "rendered_model"):
            if r.get(key) in ("UNREAD", "STALE"):
                checked += 1
                reason_key = "agent_reason" if key == "rendered_agent" else "model_reason"
                if not (r.get(reason_key) or "").strip():
                    bare.append(f"{label}/{key}")
    assert not bare, (
        f"{len(bare)} UNREAD/STALE verdict(s) with no remedy: {bare[:4]} - L1b: a reader who "
        f"cannot act on a verdict has been told nothing")
    assert checked, "no UNREAD verdict was produced at all - the fixtures did not bite"
    return f"{checked} UNREAD/STALE verdicts, {checked} remedies"


@register("L1", "L1.6", "a MISSING room.md reads back MISSING, not 'ok with zero entries'")
def _l1_6(ctx):
    rl = ctx.need("roomlog")
    p = ctx.probe / "room-absent.md"
    if p.exists():
        p.unlink()

    def read(path):
        r = rl.read_log(path)
        return {"status": getattr(r, "status", None), "entries": getattr(r, "entries", None),
                "reason": getattr(r, "reason", None)}

    probe_missing_log_not_ok(read, p)
    return "read_log(absent) -> MISSING + remedy"


@register("L1", "L1.7", "control: a reader that calls an absent log an empty healthy log",
          control=True)
def _l1_7(ctx):
    p = ctx.probe / "room-absent.md"
    if p.exists():
        p.unlink()
    return expect_fail(probe_missing_log_not_ok, naive_read_log, p)


# ---- L2 - STALENESS IS NOT HEALTH ------------------------------------------------------------

@register("L2", "L2.1", "an OLD heartbeat renders STALE with an age, not healthy")
def _l2_1(ctx):
    st = ctx.need("status")
    stale_after = 15.0
    old = _utc(datetime.now(timezone.utc) - timedelta(seconds=stale_after + 90))
    doc = valid_status_doc("Fable", heartbeat=old, stale_after_s=stale_after)
    (ctx.state / "status-fable.json").write_text(json.dumps(doc), encoding="utf-8")
    probe_old_heartbeat_stale(lambda lane: st.render_lane(lane), "Fable")
    return f"heartbeat {human_age(stale_after + 90)} old, stale_after_s={stale_after} -> STALE"


@register("L2", "L2.2", "the other direction: a FRESH heartbeat renders its real state")
def _l2_2(ctx):
    st = ctx.need("status")
    doc = valid_status_doc("Fable", heartbeat=_utc(), stale_after_s=15.0,
                           agent_state="watching")
    (ctx.state / "status-fable.json").write_text(json.dumps(doc), encoding="utf-8")
    probe_fresh_heartbeat_healthy(lambda lane: st.render_lane(lane), "Fable", "watching")
    return "a live lane renders 'watching' - so the STALE verdict above discriminates"


@register("L2", "L2.3", "control: a renderer with no clock calls the stale lane healthy",
          control=True)
def _l2_3(ctx):
    old = _utc(datetime.now(timezone.utc) - timedelta(seconds=105))
    doc = valid_status_doc("Fable", heartbeat=old, stale_after_s=15.0)
    (ctx.state / "status-fable.json").write_text(json.dumps(doc), encoding="utf-8")
    return expect_fail(probe_old_heartbeat_stale,
                       lambda lane: naive_render_lane(ctx.state, lane), "Fable")


@register("L2", "L2.4", "a lane may not exempt itself: stale_after_s=99999 renders UNREAD")
def _l2_4(ctx):
    st = ctx.need("status")
    doc = valid_status_doc("Fable", heartbeat=_utc(datetime.now(timezone.utc)
                                                   - timedelta(seconds=600)),
                           stale_after_s=99999)
    (ctx.state / "status-fable.json").write_text(json.dumps(doc), encoding="utf-8")
    r = st.render_lane("Fable")
    got = r.get("rendered_agent")
    assert got == "UNREAD", (
        f"a document declaring stale_after_s=99999 rendered {got!r} - CONTRACT.md §4.6 rule 8: "
        f"an out-of-range threshold is UNREAD, or the echo becomes an escape hatch from L2")
    assert (r.get("agent_reason") or "").strip(), "UNREAD with no remedy (L1b)"
    return "stale_after_s=99999 -> UNREAD + remedy"


# ---- L3 - APPENDS NEVER ERASE ----------------------------------------------------------------

def _roomlog_appender(rl):
    def app(path: Path, body: str) -> str:
        entry = rl.append_entry(frm="Rab", to="Fable", body=body, path=path)
        mid = getattr(entry, "id", None)
        if mid is None and isinstance(entry, (tuple, list)):
            mid = entry[0]
        assert isinstance(mid, str) and mid.startswith("RM-"), (
            f"append_entry returned {entry!r}, which carries no RM- id")
        return mid
    return app


@register("L3", "L3.1", "last byte is not a newline: the next append leads with one")
def _l3_1(ctx):
    rl = ctx.need("roomlog")
    probe_last_byte(_roomlog_appender(rl), ctx.probe / "room-lastbyte.md")
    return ("the torn line stayed torn, the new header landed at column 0, and the prefix is "
            "byte-identical")


@register("L3", "L3.2", "control: an appender without the last-byte check glues the record on",
          control=True)
def _l3_2(ctx):
    return expect_fail(probe_last_byte, naive_append, ctx.probe / "room-lastbyte-control.md")


@register("L3", "L3.3", "read_log sees the torn remnant as debris AND the new entry as an entry")
def _l3_3(ctx):
    rl = ctx.need("roomlog")
    p = ctx.probe / "room-torn-read.md"
    p.write_bytes(("# relay-room \u00b7 the chat log\n\n" + TORN_REMNANT).encode("utf-8"))
    mid = _roomlog_appender(rl)(p, "the survivor")
    r = rl.read_log(p)
    assert getattr(r, "status", None) == "ok", f"read_log status {getattr(r, 'status', None)!r}"
    ids = [getattr(e, "id", None) for e in (r.entries or [])]
    assert mid in ids, (
        f"the new record {mid} is not in entries {ids!r} - it was absorbed by the torn line")
    debris = list(getattr(r, "debris", None) or [])
    assert debris, (
        "the torn remnant was not reported as debris - CONTRACT.md §2.8 rule 5: debris is never "
        "silently discarded and never parsed as a message")
    entry = [e for e in r.entries if getattr(e, "id", None) == mid][0]
    assert getattr(entry, "digest_ok", None) is not False, "the survivor's digest does not verify"
    return f"1 entry ({mid}), {len(debris)} debris record(s), digest verifies"


@register("L3", "L3.4", "the log is never rewritten: the prefix is byte-identical after an append")
def _l3_4(ctx):
    rl = ctx.need("roomlog")
    probe_prefix_immutable(_roomlog_appender(rl), ctx.probe / "room-prefix.md")
    return "sha256 of the pre-append prefix is unchanged after the append"


@register("L3", "L3.5", "control: a 'tidy' appender that rewrites the file changes the prefix",
          control=True)
def _l3_5(ctx):
    return expect_fail(probe_prefix_immutable, rewriting_append,
                       ctx.probe / "room-prefix-control.md")


@register("L3", "L3.6", "no module opens the log in a truncating mode (source grep)")
def _l3_6(ctx):
    sources = {n: s for n, s in ctx.sources.items() if n != "selftest.py"}
    if not sources:
        raise Unread(
            f"no build module has landed under {ROOT}, so nothing was grepped - zero files "
            f"scanned is zero readings, not a clean bill of health",
            "land roomlog.py / room.py / catcher.py / status.py, then re-run this selftest")
    bad = []
    pat = re.compile(r"""open\s*\([^)\n]*?["'](?:w|w\+|r\+|wb|wb\+)["']|\.truncate\s*\(""")
    for name, src in sources.items():
        for i, line in enumerate(src.split("\n"), 1):
            if "room.md" in line or "ROOM_MD" in line or "roomlog" in line.lower():
                if pat.search(line):
                    bad.append(f"{name}:{i}: {line.strip()[:90]}")
            elif pat.search(line) and "ROOM" in line.upper():
                bad.append(f"{name}:{i}: {line.strip()[:90]}")
    assert not bad, (
        f"the log is opened in a truncating mode: {bad[:3]} - CONTRACT.md §2.5: nothing in this "
        f"codebase ever opens room.md in 'w', 'r+', 'w+', or calls truncate()")
    return f"{len(sources)} module(s) grepped, 0 truncating opens of the log"


@register("L3", "L3.7", "two lanes appending at once: 50 records, 50 ids, 0 lost")
def _l3_7(ctx):
    rl = ctx.need("roomlog")
    t0 = time.time()
    probe_concurrent(_roomlog_appender(rl), ctx.probe / "room-concurrent.md", per_lane=25)
    scan = scan_log_bytes(ctx.probe / "room-concurrent.md")
    extra = ""
    try:
        r = rl.read_log(ctx.probe / "room-concurrent.md")
        extra = (f"; read_log: {len(r.entries)} entries, torn={getattr(r, 'torn', '?')}, "
                 f"debris={len(list(getattr(r, 'debris', None) or []))}")
        assert getattr(r, "torn", 0) == 0, f"read_log reports {r.torn} torn entries"
        assert not list(getattr(r, "debris", None) or []), "read_log reports debris"
        assert len(r.entries) == 50, f"read_log sees {len(r.entries)} of 50 entries"
    except Unread:
        raise
    return (f"2 real threads x 25 real appends in {time.time() - t0:.1f}s: "
            f"{len(scan['ids'])} records, {len(set(scan['ids']))} distinct ids{extra}")


@register("L3", "L3.8", "control: the same two lanes without a lock lose records",
          control=True)
def _l3_8(ctx):
    return expect_fail(probe_concurrent, lost_update_append,
                       ctx.probe / "room-concurrent-control.md", per_lane=25)


# ---- L4 - FAIL CLOSED -------------------------------------------------------------------------

@register("L4", "L4.1", "a mutating POST with NO token is refused 403 and writes nothing")
def _l4_1(ctx):
    proc, base, token = ctx.live_server()
    probe_token_refused(base, ctx.state / "room.md")
    return f"POST /api/say with no X-FP-Token -> 403 + remedy, room.md byte-identical ({base})"


@register("L4", "L4.2", "a mutating POST with the WRONG token is refused 403")
def _l4_2(ctx):
    proc, base, token = ctx.live_server()
    payload = json.dumps({"from": "Rab", "to": "Fable", "re": None, "kind": "say",
                          "body": "wrong token"}).encode("utf-8")
    code, _, body = http("POST", base + "/api/say",
                         headers={"Content-Type": "application/json",
                                  "X-FP-Token": "not-the-token"}, body=payload)
    assert code == 403, f"a wrong token returned {code}, not 403"
    err = ""
    try:
        err = (json.loads(body.decode("utf-8", "replace")) or {}).get("error") or ""
    except Exception:                                  # noqa: BLE001
        pass
    assert err.strip(), "the 403 for a wrong token carried no remedy (L1b)"
    return "X-FP-Token: not-the-token -> 403 + remedy"


@register("L4", "L4.3", "the other direction: WITH the token the gate lets the request through")
def _l4_3(ctx):
    proc, base, token = ctx.live_server()
    before = (ctx.state / "room.md").read_bytes() if (ctx.state / "room.md").exists() else b""
    payload = json.dumps({"from": "Rab", "to": "Fable", "re": None, "kind": "say",
                          "body": "selftest: this message carries the launch token"}
                         ).encode("utf-8")
    code, _, body = http("POST", base + "/api/say",
                         headers={"Content-Type": "application/json", "X-FP-Token": token},
                         body=payload)
    assert code != 403, (
        f"the CORRECT token was still refused 403 - the gate is closed to everyone, which is "
        f"not 'fail closed', it is broken. body={body[:160]!r}")
    after = (ctx.state / "room.md").read_bytes() if (ctx.state / "room.md").exists() else b""
    landed = len(after) > len(before)
    assert code != 403
    return (f"HTTP {code} (not 403), room.md grew by {len(after) - len(before)} bytes"
            f"{'' if landed else ' - the route admitted the request but wrote nothing'}")


@register("L4", "L4.4", "control: an ungated server accepts the tokenless POST and writes",
          control=True)
def _l4_4(ctx):
    room = ctx.tmp / "control-room.md"
    room.write_text("# relay-room \u00b7 the chat log\n\n", encoding="utf-8", newline="")
    srv, base = start_ungated_server(room)
    ctx.cleanup.append(srv.shutdown)
    try:
        return expect_fail(probe_token_refused, base, room)
    finally:
        srv.shutdown()


@register("L4", "L4.5", "no route carries an Access-Control-Allow-* header")
def _l4_5(ctx):
    proc, base, token = ctx.live_server()
    offenders = []
    for path in ("/", "/api/health", "/api/log", "/api/status", "/api/flight",
                 "/api/nope-404"):
        try:
            code, headers, _ = http("GET", base + path, timeout=8)
        except Exception as exc:                       # noqa: BLE001
            offenders.append(f"{path}: {exc.__class__.__name__}")
            continue
        for h in headers:
            if h.lower().startswith("access-control-allow"):
                offenders.append(f"{path} [{code}]: {h}")
    code, headers, _ = http("POST", base + "/api/say",
                            headers={"Content-Type": "application/json"}, body=b"{}")
    for h in headers:
        if h.lower().startswith("access-control-allow"):
            offenders.append(f"POST /api/say [{code}]: {h}")
    assert not offenders, (
        f"CORS header(s) present: {offenders[:3]} - the token fences WRITES; what keeps the "
        f"ungated GETs unreadable to a drive-by local page is the same-origin policy, and one "
        f"CORS header hands the whole room to any page in any local browser (CONTRACT.md §3.1)")
    return "7 responses (incl. a 404 and a 403), 0 Access-Control-Allow-* headers"


# ---- L5 - QUARANTINE ---------------------------------------------------------------------------

@register("L5", "L5.1", "the code refuses to write outside its own directory")
def _l5_1(ctx):
    rl = ctx.need("roomlog")
    inside = ctx.state / "inside.md"
    outside = ROOT.parent / "ESCAPE-must-never-be-written.md"
    probe_assert_inside(rl.assert_inside, inside, outside)
    also = ctx.tmp / "far-away.md"
    probe_assert_inside(rl.assert_inside, inside, also)
    assert not outside.exists(), f"the escape path was actually created: {outside}"
    return (f"assert_inside refuses {outside.name} and the temp tree root, admits "
            f"state/inside.md")


@register("L5", "L5.2", "control: an identity guard admits the escape path",
          control=True)
def _l5_2(ctx):
    return expect_fail(probe_assert_inside, lambda p: p, ctx.state / "inside.md",
                       ROOT.parent / "ESCAPE-must-never-be-written.md")


@register("L5", "L5.3", "gate.py honours FP_COORD: the real coordination/ is not touched")
def _l5_3(ctx):
    if not GATE_PY.exists():
        raise Unread(f"gate.py is not at {GATE_PY}",
                     "the relay-gate skill must be installed; CONTRACT.md §6.4 pins this one "
                     "absolute path so both models invoke the same file")
    before = snapshot(REAL_COORD)
    proc = run_py([GATE_PY, "init", "--as", "Fable"], env={"FP_COORD": str(ctx.gatebox)},
                  timeout=60)
    assert proc.returncode == 0, (
        f"gate.py init exited {proc.returncode}: {(proc.stderr or proc.stdout)[:200]!r}")
    landed = ctx.gatebox / "ack-fable.json"
    assert landed.exists(), (
        f"FP_COORD={ctx.gatebox} but ack-fable.json did not land there - the quarantine hinge "
        f"(gate.py:36) did not hold, and this prototype's whole isolation rests on it")
    after = snapshot(REAL_COORD)
    drift = diff_snapshot(before, after)
    assert not drift, (
        f"the REAL coordination/ changed during a quarantined gate call: {drift[:3]} - Rab has "
        f"a live open escalation in that directory")
    return f"ack-fable.json landed in the box; real coordination/ unchanged ({len(before)} paths)"


@register("L5", "L5.4", "a FOREIGN FP_COORD in the environment is overridden, not inherited")
def _l5_4(ctx):
    if not (ctx.staged / "room.py").exists():
        raise Unread(f"room.py has not landed under {ROOT}",
                     "write room.py per CONTRACT.md §3/§6.4, then re-run this selftest")
    if ctx.init_rc is None:
        ctx.run_init()
    if ctx.init_rc != 0:
        # NOT a FAIL. `init` never ran to completion, so the foreign directory was never given
        # the chance to be written - "it is empty" would be a reading with no probe behind it.
        raise Unread(
            f"`room.py init` exited {ctx.init_rc}, so the override was never exercised: "
            f"{ctx.init_out[-300:]!r}",
            "fix `room.py init` (CONTRACT.md §6.1 step 1), then re-run - an empty foreign "
            "directory proves nothing when nothing tried to write to it")
    foreign = sorted(p.name for p in ctx.foreign_coord.iterdir())
    assert not foreign, (
        f"the FOREIGN FP_COORD directory received {foreign} - CONTRACT.md §6.4: FP_COORD is "
        f"never inherited, because gate.py:37 is a truthiness check and an inherited value "
        f"would silently steer writes at the real coordination/")
    coord = ctx.state / "coord"
    assert coord.exists(), (
        f"`room.py init` did not create {coord} - relay.md is opened in 'a' mode with no mkdir "
        f"(gate.py:202), so post() would raise FileNotFoundError")
    return (f"foreign FP_COORD dir is empty; staged coord/ holds "
            f"{sorted(p.name for p in coord.iterdir())}")


@register("L5", "L5.5", "no module imports pipeline code")
def _l5_5(ctx):
    sources = {n: s for n, s in ctx.sources.items() if n != "selftest.py"}
    if not sources:
        raise Unread(
            f"no build module has landed under {ROOT}, so nothing was scanned",
            "land the modules of CONTRACT.md §9, then re-run this selftest")
    banned = {"converter", "observability", "widget", "marker", "fitz", "pymupdf"}
    offenders = []
    for name, src in sources.items():
        for mod in imports_of(src, name):
            if mod.lower() in banned:
                offenders.append(f"{name}: import {mod}")
    assert not offenders, f"pipeline import(s): {offenders} - L5 forbids them"
    return f"{len(sources)} module(s), 0 pipeline imports"


# ---- L6 - STDLIB ONLY ---------------------------------------------------------------------------

@register("L6", "L6.1", "every import in every module is stdlib or a sibling")
def _l6_1(ctx):
    sources = {n: s for n, s in ctx.sources.items() if n != "selftest.py"}
    if not sources:
        raise Unread(
            f"no build module has landed under {ROOT}, so zero imports were judged - an empty "
            f"scan is not a clean scan",
            "land the modules of CONTRACT.md §9, then re-run this selftest")
    probe_stdlib_only(sources)
    count = sum(len(imports_of(s, n)) for n, s in sources.items())
    return f"{len(sources)} module(s), {count} import(s), all stdlib or local"


@register("L6", "L6.2", "control: a module importing a third-party package is caught",
          control=True)
def _l6_2(ctx):
    return expect_fail(probe_stdlib_only,
                       {"control.py": "import json\nimport requests\nfrom roomlog import ROOT\n"})


@register("L6", "L6.3", "this selftest is itself stdlib-only")
def _l6_3(ctx):
    src = ctx.sources.get("selftest.py")
    if src is None:
        raise Unread("selftest.py could not read itself", "check file permissions on " + str(ROOT))
    probe_stdlib_only({"selftest.py": src})
    return f"{len(imports_of(src, 'selftest.py'))} imports, all stdlib"


# ---- L7 - SELF-CONTAINED HTML ---------------------------------------------------------------

@register("L7", "L7.1", "room.html reaches nothing off the machine")
def _l7_1(ctx):
    probe_self_contained_html(ctx.need_source("room.html"))
    return "no absolute URL, no @import, no font host, no external stylesheet"


@register("L7", "L7.2", "room.html never assembles HTML from strings")
def _l7_2(ctx):
    probe_no_html_injection(ctx.need_source("room.html"))
    return "no innerHTML / outerHTML / document.write / insertAdjacentHTML / new Function"


@register("L7", "L7.3", "control: a page with a CDN script and innerHTML is caught by both",
          control=True)
def _l7_3(ctx):
    bad = ('<script src="https://cdn.example.com/x.js"></script>'
           '<div id="a"></div><script>a.innerHTML = "<b>hi</b>";</script>')
    a = expect_fail(probe_self_contained_html, bad)
    b = expect_fail(probe_no_html_injection, bad)
    return f"{a} | {b}"


@register("L7", "L7.4", "room.html names every state it must be able to render")
def _l7_4(ctx):
    html = ctx.need_source("room.html")
    agent = ("watching", "catching", "handing", "awaiting-model", "mirroring", "error")
    model = ("idle", "working", "composing", "blocked-on-ack", "blocked-on-rab")
    stages = ("typed", "transmitted", "landed", "caught", "handed", "delivered",
              "model-working", "replied")
    missing = [w for w in agent + model + stages + ("UNREAD", "STALE") if w not in html]
    assert not missing, (
        f"room.html never mentions {missing} - a UI that cannot name a state cannot render it, "
        f"and the ones it cannot name will silently render as nothing (CONTRACT.md §8 T23b)")
    return f"{len(agent) + len(model) + len(stages) + 2} state names all present"


# ---- L8 - THE TRIPWIRE SUITE ------------------------------------------------------------------

@register("L8", "L8.1", "test_room.py exists and names the tripwires that guard the eight laws")
def _l8_1(ctx):
    p = ROOT / "test_room.py"
    if not p.exists():
        raise Unread(
            f"test_room.py has not landed under {ROOT}, so the 39 named tripwires of "
            f"CONTRACT.md §8 are unproven",
            "assemble test_room.py per CONTRACT.md §8/§9, then run "
            "`python -m unittest discover -s <ROOT> -p \"test_room.py\"`")
    src = p.read_text(encoding="utf-8", errors="replace")
    found = set(re.findall(r"\bT\d{1,2}[a-c]?\b", src))
    core = {"T3": "L4 token gate", "T6": "L3 last byte", "T8": "L1 UNREAD ladder",
            "T9": "L2 staleness", "T13": "L5.2 stage authorship", "T16": "L5 quarantine",
            "T22": "L7 no innerHTML", "T24": "the forbidden gate subcommands"}
    missing = {k: v for k, v in core.items() if k not in found}
    assert not missing, (
        f"test_room.py never names {sorted(missing)} - each guards a law: "
        f"{'; '.join(f'{k}={v}' for k, v in list(missing.items())[:4])}")
    return f"{len(found)} tripwire ids named; all {len(core)} law-guarding ids present"


# ---- FINAL - the measurements that must be taken LAST -----------------------------------------

@register("L5", "L5.6", "FINAL: the real coordination/ is byte-for-byte unchanged")
def _l5_6(ctx):
    after = snapshot(REAL_COORD)
    drift = diff_snapshot(ctx.coord_before, after)
    assert not drift, (
        f"{len(drift)} path(s) in the REAL coordination/ changed during this run: {drift[:4]} - "
        f"this harness is supposed to be incapable of that")
    n = len([k for k in ctx.coord_before if k != "__status__"])
    return f"{n} paths under {REAL_COORD}, all identical (size + mtime_ns)"


@register("L5", "L5.7", "FINAL: the live prototype state/ tree is byte-for-byte unchanged")
def _l5_7(ctx):
    after = snapshot(REAL_STATE)
    drift = diff_snapshot(ctx.state_before, after)
    assert not drift, (
        f"{len(drift)} path(s) in the LIVE {REAL_STATE} changed: {drift[:4]} - every write in "
        f"this run was supposed to land in the staged copy")
    if ctx.state_before.get("__status__") == "MISSING":
        return f"{REAL_STATE} did not exist before and does not exist now"
    n = len([k for k in ctx.state_before if k != "__status__"])
    return f"{n} paths under {REAL_STATE}, all identical"


@register("L8", "L8.2", "FINAL: every control in this run actually fired")
def _l8_2(ctx):
    controls = [r for r in RESULTS if r["control"]]
    assert controls, "no controls ran at all - nothing here is proven both ways"
    dead = [f"{r['cid']} ({r['verdict']})" for r in controls if r["verdict"] != PASS]
    assert not dead, (
        f"{len(dead)} control(s) did not fire: {dead} - a guard whose control does not fail is "
        f"a guard nobody has measured (L8)")
    return (f"{len(controls)} unguarded controls, {len(controls)} fired - every guarded "
            f"assertion above was proven to discriminate")


# =============================================================================================
# RUNNER
# =============================================================================================

BAR = "\u2500" * 92


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                  # noqa: BLE001
        pass

    ap = argparse.ArgumentParser(description="prove the eight laws of CONTRACT.md, both ways")
    ap.add_argument("--verbose", action="store_true", help="print the detail line for passes too")
    ap.add_argument("--keep", action="store_true", help="keep the temp tree and print its path")
    ap.add_argument("--list", action="store_true", help="print the roster and exit")
    args = ap.parse_args(argv)

    if args.list:
        print(f"relay-room selftest \u00b7 {len(CHECKS)} checks")
        for law, cid, title, _, is_control in CHECKS:
            print(f"  {law:<3} {cid:<6} {'[control] ' if is_control else ''}{title}")
        return 0

    started = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="relay-room-selftest-"))
    ctx = Ctx(tmp)
    ctx.coord_before = snapshot(REAL_COORD)
    ctx.state_before = snapshot(REAL_STATE)

    print(f"relay-room \u00b7 SELFTEST \u00b7 {_utc()}")
    print(f"  python    {sys.executable}")
    print(f"  version   {sys.version.split()[0]}")
    print(f"  ROOT      {ROOT}")
    print(f"  staged    {ctx.staged}")
    print(f"  gate.py   {GATE_PY}{'' if GATE_PY.exists() else '   [NOT FOUND]'}")
    print(f"  snapshot  {REAL_COORD} ({ctx.coord_before.get('__status__')}, "
          f"{max(0, len(ctx.coord_before) - 1)} paths)")
    print(f"  snapshot  {REAL_STATE} ({ctx.state_before.get('__status__')}, "
          f"{max(0, len(ctx.state_before) - 1)} paths)")
    print("  QUARANTINE: sources are COPIED into the staged tree and run from there; the two")
    print("              snapshots above are re-measured at the end (L5.6, L5.7).")
    print(BAR)

    try:
        ctx.stage()
        ctx.load_sources()
        ctx.load_modules()
    except Exception as exc:                           # noqa: BLE001
        print(f"  FATAL: could not stage the tree: {exc.__class__.__name__}: {exc}")
        traceback.print_exc()
        return 1

    counts = {PASS: 0, FAIL: 0, UNREAD: 0}
    for law, cid, title, fn, is_control in CHECKS:
        t0 = time.time()
        remedy = ""
        try:
            detail = fn(ctx) or ""
            verdict = PASS
        except Unread as u:
            verdict, detail, remedy = UNREAD, u.reason, u.remedy
        except Tautology as t:
            verdict, detail = FAIL, str(t)
            remedy = ("rewrite the probe until the unguarded control fails it; until then the "
                      "guarded half proves nothing")
        except AssertionError as a:
            verdict, detail = FAIL, (str(a) or "assertion failed")
        except Exception as exc:                       # noqa: BLE001
            verdict = FAIL
            detail = (f"{exc.__class__.__name__}: {exc} | "
                      f"{traceback.format_exc().strip().splitlines()[-3:]}")
        counts[verdict] += 1
        RESULTS.append({"law": law, "cid": cid, "title": title, "verdict": verdict,
                        "detail": detail, "remedy": remedy, "control": is_control,
                        "secs": time.time() - t0})

        mark = {PASS: "PASS  ", FAIL: "FAIL  ", UNREAD: "UNREAD"}[verdict]
        secs = f"{time.time() - t0:5.1f}s"
        print(f"  {mark} {cid:<6} {secs}  {title}")
        if verdict != PASS or args.verbose:
            for chunk in _wrap(detail, 84):
                print(f"                        \u2514 {chunk}")
            if remedy:
                for chunk in _wrap("REMEDY: " + remedy, 84):
                    print(f"                          {chunk}")

    print(BAR)
    total = sum(counts.values())
    controls = [r for r in RESULTS if r["control"]]
    fired = len([r for r in controls if r["verdict"] == PASS])
    print(f"  {total} checks \u00b7 {counts[PASS]} PASS \u00b7 {counts[FAIL]} FAIL \u00b7 "
          f"{counts[UNREAD]} UNREAD \u00b7 {time.time() - started:.1f}s")
    print(f"  controls: {fired}/{len(controls)} fired  "
          f"(a control that does not fire means the tripwire is a tautology \u2014 L8)")
    if counts[UNREAD]:
        print("  UNREAD IS NOT A SKIP. A check that could not run is not a check that passed;")
        print("  it is a law with no reading behind it. It counts as a failure here, by design (L1).")
        for r in RESULTS:
            if r["verdict"] == UNREAD:
                print(f"      {r['cid']:<6} {r['title']}")
    if counts[FAIL]:
        print("  FAILURES:")
        for r in RESULTS:
            if r["verdict"] == FAIL:
                print(f"      {r['cid']:<6} {r['title']}")

    ctx.close()
    if args.keep:
        print(f"  temp tree kept: {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        if tmp.exists():
            print(f"  note: the temp tree could not be fully removed: {tmp}")

    rc = 0 if (counts[FAIL] == 0 and counts[UNREAD] == 0) else 1
    print(f"  EXIT {rc}")
    return rc


def _wrap(text: str, width: int):
    text = " ".join(str(text).split())
    if not text:
        return [""]
    out, line = [], ""
    for word in text.split(" "):
        if len(line) + len(word) + 1 > width and line:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out[:8]


if __name__ == "__main__":
    sys.exit(main())
