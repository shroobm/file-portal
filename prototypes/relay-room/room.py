#!/usr/bin/env python3
"""room.py - relay-room: THE SERVER + THE CLI.  [BUILDER B]

Contract: CONTRACT.md - §3 (the HTTP surface), §6 (the launch story + the model's CLI),
§4.5 (the board it serves), §5.4 (the trails it serves).

The eight laws, and where each one bites in THIS file:

  L1  UNREAD IS NEVER IDLE.  A failed probe is reported INSIDE the document it belongs to
      (`log_status`, `board_status`, `file_status`), never as a 500 and never as an empty
      list.  `GET /api/log` on a missing room.md answers 200 with "MISSING" + a remedy -
      an empty `entries[]` with `log_status: "ok"` would be the lie L1 exists to stop.
  L1b NO UNREAD WITHOUT A REMEDY.  Every error body is `{"error": "<sentence saying what to
      do>"}`.  The UI renders it verbatim.
  L2  STALENESS IS NOT HEALTH.  The SSE loop recomputes the RENDERED board every tick and
      diffs the render, not the file mtimes - so a lane that crosses its staleness threshold
      while nothing on disk changed still reaches the screen (§3.4, tripwire T9b).
  L3  APPENDS NEVER ERASE.  This file never opens room.md for writing.  Every append goes
      through `roomlog.append_entry` / `roomlog.append_stage`, which own the last-byte check
      and the single write().  The one exception is the preamble at `init`, written with the
      same discipline, in append mode, only when the file does not exist.
  L4  FAIL CLOSED.  `token_gate` runs on the whole POST verb BEFORE any route dispatch
      (T1, T2, T3, T4).  GETs are ungated by design; what fences them is the absence of any
      Access-Control-Allow-* header (T5), not obscurity.
  L5  QUARANTINE.  Every mutating filesystem call passes `roomlog.assert_inside` first.
      `gate.py` is invoked with an explicitly constructed environment whose FP_COORD is
      forced to the quarantined coord dir - never inherited (§6.4).
  L6  STDLIB ONLY.
  L7  the UI is one self-contained file; this server only reads it (fresh per request).
  L8  the tripwires for this file are T1-T5, T12, T20, T21 in test_room.py.

What this file is NOT: it is not a second implementation of anything.  `say` / `state` /
`claim` on the command line and `/api/say` / `/api/model/state` / `/api/claim` over HTTP call
the SAME three `op_*` functions below, which call the SAME roomlog appender under the SAME
lock.  The status ladder belongs to status.py and is CALLED, never reimplemented (§9's seam).
"""

import argparse
import hmac
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import roomlog
import status as roomstatus

# ----------------------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------------------

ROOT = roomlog.ROOT
VERSION = "fp-relay-room/v1"

# §3.2 - THE CENSUS.  Tripwire T1 asserts this tuple equals the set of `self.path == "/api/..."`
# literals inside do_POST.  A route added to dispatch and forgotten here fails the test.
MUTATING_POSTS = ("/api/say", "/api/claim", "/api/model/state")

_NO_GATE = object()          # a test harness constructing the server in-process is already inside

DECLARABLE = ("idle", "working", "composing")
REFUSED_DECLARATIONS = ("blocked-on-ack", "blocked-on-rab", "UNREAD", "STALE")

RE_ID = re.compile(r"^RM-[0-9a-f]{12}$")

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'")

# SSE frames whose payload differs only in these keys are NOT re-sent.  Without this the
# `status` frame would fire twice a second forever (every heartbeat moves `heartbeat_utc`),
# and the client would learn nothing from any of them.  Everything that CARRIES A VERDICT -
# rendered_agent, rendered_model, reasons, stages, ok flags, counts - stays in the signature,
# so a staleness crossing still fires within one tick.  §3.4 / T9b.
VOLATILE_KEYS = frozenset({
    "utc", "age_s", "read_utc", "heartbeat_utc", "doc_utc", "cycle", "since_utc",
    "stage_utc", "last_utc", "started_utc", "updated_utc", "heartbeat_interval_s",
})

# Ages live INSIDE remedy sentences ("last seen 3m12s ago"), so a reason string changes every
# second while saying the same thing.  Digit runs are masked for signature purposes only -
# the sentence itself is always sent verbatim.
_DIGITS = re.compile(r"\d+")

_CONFIG_STATUS = ("ok", None)     # (status, reason) of the last config.json probe - never faked


# ----------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------

class Refused(Exception):
    """A refusal with an HTTP code and a REMEDY.  Never a bare 'invalid input'."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _read_json(path: Path):
    """(obj, 'ok'|'MISSING'|'UNREAD', reason).  A failed probe never returns a healthy empty dict."""
    p = Path(path)
    if not p.exists():
        return None, "MISSING", f"{p} does not exist"
    try:
        raw = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception as exc:                                    # noqa: BLE001 - any failure is UNREAD
        return None, "UNREAD", f"{p} could not be read ({type(exc).__name__}: {exc})"
    try:
        obj = json.loads(raw)
    except Exception as exc:                                    # noqa: BLE001
        return None, "UNREAD", f"{p} is not valid JSON ({type(exc).__name__}: {exc})"
    return obj, "ok", None


def _write_json(path: Path, obj) -> Path:
    """Atomic .part-then-replace.  assert_inside FIRST (L5).  Never touches room.md."""
    p = roomlog.assert_inside(Path(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    roomlog.assert_inside(tmp)
    # write_bytes: no newline translation, and no "w" mode literal anywhere near a log file (T6a)
    tmp.write_bytes((json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, p)
    return p


def load_config(overrides=None) -> dict:
    global _CONFIG_STATUS
    cfg = dict(roomlog.DEFAULTS)
    obj, st, reason = _read_json(roomlog.STATE / "config.json")
    if st == "ok" and isinstance(obj, dict):
        _CONFIG_STATUS = ("ok", None)
        for k, v in obj.items():
            if k in cfg:
                cfg[k] = v
    elif st == "MISSING":
        _CONFIG_STATUS = ("MISSING", f"{reason} - run `room.py init` (defaults are in force meanwhile)")
    else:
        _CONFIG_STATUS = ("UNREAD", f"{reason} - delete it and re-run `room.py init`; "
                                    "the built-in defaults are in force meanwhile")
        print("UNREAD: " + _CONFIG_STATUS[1], file=sys.stderr)
    for k, v in (overrides or {}).items():
        if v is not None:
            cfg[k] = v
    return cfg


_CFG = None


def cfg(*, refresh=False, overrides=None) -> dict:
    global _CFG
    if _CFG is None or refresh:
        _CFG = load_config(overrides)
    return _CFG


def _sig(path):
    """(mtime_ns, size) or None when the probe failed.  None is a READING - 'we looked and it
    was not there' - and a transition into or out of it is a change."""
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _strip(o):
    """The change-signature of a payload: volatile clock fields removed, ages inside remedy
    sentences masked.  Used ONLY to decide whether to re-send a frame."""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in VOLATILE_KEYS:
                continue
            if isinstance(v, str) and (k == "detail" or k.endswith("reason")):
                out[k] = _DIGITS.sub("#", v)
            else:
                out[k] = _strip(v)
        return out
    if isinstance(o, list):
        return [_strip(v) for v in o]
    if isinstance(o, float):
        return round(o, 1)
    return o


def _lock_detail(lock_dir: Path) -> str:
    """Turn a LockTimeout into the sentence §2.6 demands, with the real pid and the real age."""
    try:
        owner = json.loads(io.open(lock_dir / "owner.json", encoding="utf-8").read())
        pid = owner.get("pid")
    except Exception:                                            # noqa: BLE001
        pid = "unknown"
    try:
        held = round(time.time() - os.stat(lock_dir).st_mtime, 1)
    except OSError:
        held = "unknown"
    return (f"room.md is locked by pid {pid} (held {held}s) - retry; if it persists, "
            f"delete {lock_dir}")


def gate_call(argv_tail, *, timeout=60.0) -> dict:
    """Invoke the ONE gate.py (roomlog.GATE_PY) against the QUARANTINED coord dir.

    §6.4: FP_COORD is CONSTRUCTED, never inherited.  gate.py:37 does a truthiness check, so an
    inherited empty value would fall through to the REAL coordination/ - where Rab has a live
    open escalation.  An inherited value that differs is overridden, and the override is
    RECORDED (see _record_fp_coord_override).
    """
    env = {**os.environ, "FP_COORD": str(roomlog.COORD)}
    cmd = [sys.executable, str(roomlog.GATE_PY)] + [str(a) for a in argv_tail]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        rc, out, err = p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as exc:                                     # noqa: BLE001
        rc, out, err = None, "", f"{type(exc).__name__}: {exc}"
    return {"cmd": cmd, "rc": rc, "stdout": out, "stderr": err,
            "utc": roomlog.utc_now(), "coord_dir": str(roomlog.COORD)}


def _fp_coord_override() -> dict | None:
    """§6.4.  Returns the override record when the inherited FP_COORD is not ours."""
    inherited = os.environ.get("FP_COORD")
    if inherited is None:
        return None
    try:
        same = Path(inherited).resolve() == Path(roomlog.COORD).resolve()
    except Exception:                                            # noqa: BLE001
        same = False
    if same:
        return None
    return {"inherited": inherited, "forced_to": str(roomlog.COORD), "utc": roomlog.utc_now(),
            "note": "FP_COORD was inherited and did not name this prototype's coord dir; every "
                    "gate.py subprocess is launched with it forced. The real coordination/ is "
                    "NOT touched by this process."}


# ----------------------------------------------------------------------------------------
# §3.2 - THE TOKEN GATE
# ----------------------------------------------------------------------------------------

def token_gate(presented, expected):
    """None = admitted.  A string = the honest 403 reason.  Constant-time compare.

    Two DISTINCT remedies, because they are two different operator mistakes: you started the
    server wrong, versus you loaded the page wrong.  T3 asserts on the first one's text.
    """
    if expected is _NO_GATE:
        return None
    if expected is None:
        return ("mutating routes are disabled: room.py was started with --no-token. "
                "Restart it as `room.py serve` (it mints a token and prints the URL) and open "
                "the page as /?token=<secret>.")
    if not presented or not hmac.compare_digest(
            str(presented).encode("utf-8"), str(expected).encode("utf-8")):
        return ("X-FP-Token missing or wrong - reload the page with ?token=<the value room.py "
                "printed at launch> so the UI attaches it to every mutating request.")
    return None


# ----------------------------------------------------------------------------------------
# the three operations.  ONE implementation, called by both the HTTP routes and the CLI.
# ----------------------------------------------------------------------------------------

def _remedy_declaration() -> str:
    return ("blocked-on-ack and blocked-on-rab are readings of the relay-gate sidecar, not "
            "declarations - set them with gate.py (escalate / post) against FP_COORD="
            f"{roomlog.COORD}. UNREAD and STALE are derived from a failed or old probe and can "
            "never be declared by the thing being probed.")


def op_say(*, frm, to, body, re_=None, kind="say") -> dict:
    """Append one entry to room.md.  §3.3 POST /api/say and §6.3 `room.py say`."""
    c = cfg()
    speakers = tuple(roomlog.SPEAKERS)
    if frm not in speakers:
        raise Refused(400, f"`from` must be one of {'/'.join(speakers)} - got {frm!r}. "
                           "The grammar is closed (CONTRACT §2.3); a new speaker needs a new "
                           "header grammar, not a new value.")
    if to not in speakers + ("all",):
        raise Refused(400, f"`to` must be one of {'/'.join(speakers)}/all - got {to!r}.")
    if kind not in tuple(roomlog.KINDS):
        raise Refused(400, f"`kind` must be one of {'/'.join(roomlog.KINDS)} - got {kind!r}.")
    if not isinstance(body, str) or not body.strip():
        raise Refused(400, "a message body may not be blank - type something, or the entry "
                           "would land in the log saying nothing.")
    limit = int(c.get("max_message_chars", 32768))
    if len(body) > limit:
        raise Refused(400, f"message is {len(body)} characters, limit {limit} - split it, or "
                           f"raise max_message_chars in state/config.json.")
    if "<!-- /RM-" in body:
        raise Refused(400, "a message body may not contain the entry terminator token "
                           "'<!-- /RM-'; remove it or fence it as code.")
    if re_ is not None:
        if not isinstance(re_, str) or not RE_ID.match(re_):
            raise Refused(400, f"`re` must be null or an id of the form RM-<12 hex> - got {re_!r}.")

    read = roomlog.read_log()
    re_resolved, re_note = True, None
    if re_:
        if read.status == "ok":
            re_resolved = any(e.id == re_ for e in read.entries)
        else:
            re_resolved, re_note = False, (f"the log itself is {read.status} ({read.reason}), so "
                                           f"whether {re_} exists is UNREAD - not 'absent'.")

    try:
        entry = roomlog.append_entry(frm=frm, to=to, body=body, re_=re_, kind=kind)
    except roomlog.LockTimeout:
        raise Refused(503, _lock_detail(roomlog.STATE / "room.lock"))

    if to in tuple(roomlog.LANES):
        lanes = [to]
    elif to == "all":
        lanes = [l for l in roomlog.LANES if l != frm]
    else:
        lanes = []                       # to: Rab - there is no probe for a human's attention

    out = {"id": entry.id, "utc": entry.utc, "digest": entry.digest, "stage": "landed",
           "re_resolved": re_resolved, "lanes": lanes}
    if re_note:
        out["re_note"] = re_note
    return out


def op_claim(*, lane, mid, note=None) -> dict:
    """The model says IT has the message.  §5.2: the only writer of stage `delivered`."""
    if lane not in tuple(roomlog.LANES):
        raise Refused(400, f"`lane` must be one of {'/'.join(roomlog.LANES)} - got {lane!r}.")
    if not isinstance(mid, str) or not RE_ID.match(mid):
        raise Refused(400, f"`id` must be an id of the form RM-<12 hex> - got {mid!r}.")
    read = roomlog.read_log()
    if read.status != "ok":
        raise Refused(503, f"room.md is {read.status}: {read.reason} - a claim cannot be checked "
                           f"against a log that could not be read, and an unchecked claim is "
                           f"exactly the substitution stage 6 exists to prevent.")
    hit = next((e for e in read.entries if e.id == mid), None)
    if hit is None:
        raise Refused(400, f"{mid} is not in room.md - a model may not claim delivery of a "
                           f"message the log does not carry.")
    if hit.to != lane and hit.to != "all":
        raise Refused(400, f"{mid} is addressed to {hit.to}, not to {lane} - only the addressed "
                           f"lane may claim it.")
    if hit.frm == lane:
        raise Refused(400, f"{mid} was written by {lane} - you cannot deliver to yourself.")
    try:
        roomlog.append_stage(mid, "delivered", f"model:{lane}", ok=True, note=note)
    except ValueError as exc:
        raise Refused(400, str(exc))
    except roomlog.LockTimeout:
        raise Refused(503, _lock_detail(roomlog.FLIGHT_DIR / f"{mid}.lock"))
    return roomlog.render_trail(mid, roomlog.read_log())


def op_model_state(*, lane, state, ticket=None, note=None) -> dict:
    """The model declares its OWN layer state.  §3.3, tripwire T12."""
    if lane not in tuple(roomlog.LANES):
        raise Refused(400, f"`lane` must be one of {'/'.join(roomlog.LANES)} - got {lane!r}.")
    if state in REFUSED_DECLARATIONS:
        raise Refused(400, _remedy_declaration())
    if state not in DECLARABLE:
        raise Refused(400, f"unknown model state {state!r} - the declarable states are "
                           f"{'/'.join(DECLARABLE)}. " + _remedy_declaration())
    if ticket is not None and (not isinstance(ticket, str) or not RE_ID.match(ticket)):
        raise Refused(400, f"`ticket` must be null or an id of the form RM-<12 hex> - got {ticket!r}.")

    roomstatus.write_model_declared(lane, state, ticket, note)

    stage_note = None
    if state in ("working", "composing") and ticket:
        read = roomlog.read_log()
        if read.status == "ok" and any(e.id == ticket for e in read.entries):
            try:
                roomlog.append_stage(ticket, "model-working", f"model:{lane}", ok=True, note=note)
            except (ValueError, roomlog.LockTimeout) as exc:
                stage_note = (f"the declaration was recorded but the flight stage was not: "
                              f"{type(exc).__name__}: {exc}")
        elif read.status != "ok":
            stage_note = (f"the declaration was recorded; whether {ticket} exists is UNREAD "
                          f"(room.md is {read.status}: {read.reason}), so no flight stage was "
                          f"written.")
        else:
            stage_note = (f"the declaration was recorded; {ticket} is not in room.md, so no "
                          f"flight stage was written.")

    out = {"lane": lane, "state": state, "utc": roomlog.utc_now(), "ticket": ticket}
    if stage_note:
        out["note"] = stage_note
    return out


# ----------------------------------------------------------------------------------------
# the documents the routes serve (module-level so the SSE loop reuses them verbatim)
# ----------------------------------------------------------------------------------------

def entry_json(e) -> dict:
    r = e.re
    if r in (None, "", "-", "\u2014"):
        r = None
    return {"id": e.id, "utc": e.utc, "from": e.frm, "to": e.to, "re": r, "kind": e.kind,
            "digest": e.digest, "digest_ok": e.digest_ok, "digest_note": e.digest_note,
            "torn": e.torn, "body": e.body}


def log_document(since=None) -> dict:
    """§3.3 GET /api/log.  ALWAYS 200: a failed read is reported INSIDE the document, because a
    500 renders as 'the room is broken' and loses the reason (L1)."""
    read = roomlog.read_log()
    all_entries = list(read.entries) if read.status == "ok" else []
    entries = all_entries
    since_resolved = True
    if since and since not in ("0", ""):
        ids = [e.id for e in all_entries]
        if since in ids:
            entries = all_entries[ids.index(since) + 1:]
        else:
            # T21: an unresolvable cursor must NOT look like "nothing new".
            since_resolved = False
            entries = all_entries
    return {"protocol": VERSION,
            "log_status": read.status,
            "reason": read.reason,
            "since_resolved": since_resolved,
            "preamble": read.preamble,
            "entries": [entry_json(e) for e in entries],
            "returned": len(entries),
            "debris": list(read.debris or []),
            "count": len(all_entries),
            "torn": read.torn,
            "bytes": read.bytes,
            "read_utc": read.read_utc}


def _unread_lane(lane: str, reason: str) -> dict:
    return {"rendered_agent": "UNREAD", "rendered_model": "UNREAD",
            "agent_reason": reason,
            "model_reason": ("the publisher of this reading is UNREAD, so the reading is UNREAD "
                             "(a derived reading is never fresher than its publisher)"),
            "doc_utc": None, "age_s": None,
            "agent": None, "model": None, "in_flight": None, "gate": None}


def board_document(srv=None) -> dict:
    """§4.5 GET /api/status.  status.py owns the ladder; this only ASSEMBLES and never judges."""
    try:
        board = roomstatus.render_board()
        if not isinstance(board, dict):
            raise TypeError(f"render_board returned {type(board).__name__}, not a dict")
    except Exception as exc:                                     # noqa: BLE001
        reason = (f"the status board could not be rendered ({type(exc).__name__}: {exc}) - "
                  "the board you are looking at is UNREAD, not empty. Check that status.py is "
                  "present beside room.py and that state/ exists (`room.py init`).")
        board = {"protocol": VERSION, "utc": roomlog.utc_now(), "board_status": "UNREAD",
                 "reason": reason, "thresholds": {},
                 "lanes": {lane: _unread_lane(lane, reason) for lane in roomlog.LANES},
                 "log": {"log_status": "UNREAD", "reason": reason}}
    board.setdefault("board_status", "ok")
    board.setdefault("protocol", VERSION)
    # the live socket count is the SERVER's own reading and outranks any file's copy of it
    rab = board.setdefault("rab", {})
    if srv is not None:
        rab["sse_clients"] = srv.sse_clients
        rab.setdefault("last_say_utc", srv.last_say_utc)
    else:
        rab.setdefault("sse_clients", None)
        rab.setdefault("sse_clients_reason",
                       "read outside the server process - the live socket count is UNREAD here")
    rab.setdefault("note", "no probe exists for a human's attention")
    return board


def flight_document(mid=None) -> dict:
    """§3.3 GET /api/flight."""
    read = roomlog.read_log()
    if read.status != "ok":
        doc = {"flights": {}, "log_status": read.status, "reason": read.reason,
               "read_utc": read.read_utc}
        if mid:
            doc["flight"] = None
        return doc
    if mid:
        if not any(e.id == mid for e in read.entries):
            raise Refused(404, f"no such message: {mid} - it is not in room.md.")
        return {"flight": roomlog.render_trail(mid, read), "log_status": "ok",
                "read_utc": read.read_utc}
    says = [e for e in read.entries if e.kind == "say"][-50:]
    return {"flights": {e.id: roomlog.render_trail(e.id, read) for e in says},
            "log_status": "ok", "reason": None, "read_utc": read.read_utc}


# ----------------------------------------------------------------------------------------
# the HTTP handler
# ----------------------------------------------------------------------------------------

class RoomHandler(BaseHTTPRequestHandler):
    server_version = "fp-relay-room/v1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):       # the console belongs to the operator, not to access logs
        pass

    # -------- response plumbing --------

    def _send(self, body: bytes, code=200, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        # §3.1: NO Access-Control-Allow-* header, ever, on any route (T5).  The token fences
        # writes; what keeps the ungated GETs unreadable to a drive-by local page is the
        # same-origin policy, and one CORS header would hand the whole room away.
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload, code=200):
        self._send(json.dumps(payload, ensure_ascii=False).encode("utf-8"), code)

    def _fail(self, exc):
        tb = traceback.format_exc(limit=4).strip().splitlines()[-3:]
        self._json({"error": f"unexpected server error ({type(exc).__name__}: {exc}) - this is a "
                             f"defect, not a usage mistake; the traceback tail is included so it "
                             f"can be reported rather than guessed.",
                    "traceback": tb}, 500)

    def _health(self) -> dict:
        srv = self.server
        if srv.token is _NO_GATE:
            mode = "in-process"
        elif srv.token is None:
            mode = "no-token"
        else:
            mode = "token"
        doc = {"ok": True, "utc": roomlog.utc_now(), "pid": os.getpid(),
               "port": srv.server_address[1], "token_mode": mode,
               "root": str(ROOT), "coord_dir": str(roomlog.COORD),
               "sse_clients": srv.sse_clients, "version": VERSION,
               "config_status": _CONFIG_STATUS[0], "config_reason": _CONFIG_STATUS[1]}
        if srv.heartbeat_error:
            doc["ok"] = False
            doc["heartbeat_error"] = srv.heartbeat_error
        if srv.fp_coord_override:
            doc["fp_coord_override"] = srv.fp_coord_override
        return doc

    # -------- GET --------

    def do_GET(self):
        parsed = urlparse(self.path)
        path, q = parsed.path, parse_qs(parsed.query)
        try:
            if path in ("/", "/index.html"):
                return self._page()
            if path == "/api/health":
                return self._json(self._health())
            if path == "/api/log":
                return self._json(log_document(q.get("since", [None])[0]))
            if path == "/api/status":
                return self._json(board_document(self.server))
            if path == "/api/flight":
                return self._json(flight_document(q.get("id", [None])[0]))
            if path == "/api/events":
                return self._events()
            self._json({"error": f"no such route: {path}"}, 404)
        except Refused as r:
            self._json({"error": r.message}, r.code)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as exc:                                 # noqa: BLE001
            self._fail(exc)

    def _page(self):
        # §3.1 / S65: read FRESH per request, so a UI edit reaches the operator on F5 rather
        # than on the next server respawn.
        try:
            data = (ROOT / "room.html").read_bytes()
        except OSError as exc:
            msg = (f"UNREAD: room.html could not be read ({type(exc).__name__}: {exc}).\n\n"
                   f"It is the UI, and it ships beside room.py at\n  {ROOT / 'room.html'}\n\n"
                   f"The server itself is up - the JSON routes still answer:\n"
                   f"  /api/health  /api/log  /api/status  /api/flight  /api/events\n\n"
                   f"This page is deliberately NOT a friendly empty room: a blank page that "
                   f"looked healthy would be the exact defect this prototype exists to refuse.\n")
            self._send(msg.encode("utf-8"), 503, "text/plain; charset=utf-8")
            return
        self._send(data, 200, "text/html; charset=utf-8",
                   extra={"Content-Security-Policy": CSP})

    # -------- POST --------

    def do_POST(self):
        deny = token_gate(self.headers.get("X-FP-Token"), self.server.token)
        if deny:
            # Drain the request body first: answering while the client is still sending makes
            # Windows abort the socket (WinError 10053, measured) and the remedy never arrives.
            try:
                self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
            except (OSError, ValueError):
                pass
            self._json({"error": deny}, 403)
            return
        payload = self._read_body()
        if payload is None:
            return
        try:
            if self.path == "/api/say":
                out = op_say(frm=payload.get("from"), to=payload.get("to"),
                             body=payload.get("body"), re_=payload.get("re"),
                             kind=payload.get("kind", "say"))
                if payload.get("from") == "Rab":
                    self.server.last_say_utc = out["utc"]
                return self._json(out)
            if self.path == "/api/claim":
                return self._json(op_claim(lane=payload.get("lane"), mid=payload.get("id"),
                                           note=payload.get("note")))
            if self.path == "/api/model/state":
                return self._json(op_model_state(lane=payload.get("lane"),
                                                 state=payload.get("state"),
                                                 ticket=payload.get("ticket"),
                                                 note=payload.get("note")))
            self._json({"error": f"no such route: {urlparse(self.path).path}"}, 404)
        except Refused as r:
            self._json({"error": r.message}, r.code)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as exc:                                 # noqa: BLE001
            self._fail(exc)

    def _read_body(self):
        """dict, or None after an error response has already been sent."""
        limit = int(self.server.cfg.get("max_body_bytes", 65536))
        raw_cl = self.headers.get("Content-Length", "0") or "0"
        try:
            cl = int(raw_cl)
        except ValueError:
            self._json({"error": f"Content-Length is not an integer ({raw_cl!r}) - send a "
                                 f"well-formed request."}, 400)
            return None
        if cl > limit:
            remaining = min(cl, 10 * 1024 * 1024)
            while remaining > 0:                     # drain, then refuse (see WinError 10053)
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            self.close_connection = True
            self._json({"error": f"request body too large ({cl} bytes, limit {limit})"}, 413)
            return None
        raw = self.rfile.read(cl) if cl > 0 else b""
        if not raw:
            return {}                                # let field validation produce the real remedy
        try:
            obj = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:                                 # noqa: BLE001
            self._json({"error": f"malformed JSON ({type(exc).__name__}: {exc}) - expected an "
                                 f"object, e.g. {{\"from\":\"Rab\",\"to\":\"Fable\","
                                 f"\"kind\":\"say\",\"re\":null,\"body\":\"...\"}}"}, 400)
            return None
        if not isinstance(obj, dict):
            self._json({"error": f"the request body must be a JSON object, not a "
                                 f"{type(obj).__name__}."}, 400)
            return None
        return obj

    # -------- SSE (§3.4) --------

    def _emit(self, name: str, payload) -> None:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if "\n" in data or "\r" in data:             # a raw newline would split the frame
            data = data.replace("\r", "\\r").replace("\n", "\\n")
        self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _events(self):
        srv = self.server
        c = srv.cfg
        cap = int(c.get("max_sse_clients", 8))
        with srv.sse_lock:
            if srv.sse_clients >= cap:
                self._json({"error": f"too many live clients ({cap}) - close a tab, or fall "
                                     f"back to polling"}, 503)
                return
            srv.sse_clients += 1
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            self._stream(c)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with srv.sse_lock:
                srv.sse_clients -= 1
            self.close_connection = True

    def _stream(self, c: dict) -> None:
        srv = self.server
        poll_s = float(c.get("poll_s", 0.5))
        ping_s = float(c.get("sse_ping_s", 10.0))

        read = roomlog.read_log()
        cursor = read.entries[-1].id if (read.status == "ok" and read.entries) else None

        # §3.4: the stream NEVER replays history - but unlike gate.py's watch (which suppresses
        # its first iteration SILENTLY, gate.py:428), the client is TOLD so, and told what to do.
        self._emit("hello", {"utc": roomlog.utc_now(), "health": self._health(), "cursor": cursor,
                             "note": "this stream is a change notifier, not a backlog - "
                                     "GET /api/log now"})

        log_sig = _sig(roomlog.ROOM_MD)
        last_log_block = None
        last_board_sig = None                        # None -> one snapshot frame on the first tick
        # flight signatures are PRIMED from current state, so connecting does not replay 50 trails
        flight_sigs = {}
        cached = read
        if read.status == "ok":
            for e in [x for x in read.entries if x.kind == "say"][-50:]:
                try:
                    flight_sigs[e.id] = _strip(roomlog.render_trail(e.id, read))
                except Exception:                    # noqa: BLE001
                    flight_sigs[e.id] = None
        last_ping = time.monotonic()
        last_sweep = time.monotonic()

        while not srv.stopping.is_set():
            time.sleep(poll_s)
            now_m = time.monotonic()

            # 1 - the log
            sig = _sig(roomlog.ROOM_MD)
            log_changed = sig != log_sig
            if log_changed:
                log_sig = sig
                cached = roomlog.read_log()
                if cached.status == "ok":
                    ids = [e.id for e in cached.entries]
                    if cursor is None:
                        fresh = cached.entries
                    elif cursor in ids:
                        fresh = cached.entries[ids.index(cursor) + 1:]
                    else:
                        fresh = cached.entries[-200:]   # cursor lost: loud, never silent
                    for e in fresh:
                        self._emit("entry", entry_json(e))
                        cursor = e.id
                block = {"log_status": cached.status, "reason": cached.reason,
                         "count": len(cached.entries) if cached.status == "ok" else 0,
                         "torn": cached.torn, "debris": len(cached.debris or []),
                         "bytes": cached.bytes, "read_utc": cached.read_utc}
                if _strip(block) != _strip(last_log_block or {}):
                    self._emit("log", block)
                    last_log_block = block

            # 2 - the board, recomputed EVERY tick.  §3.4 / T9b: staleness is clock-driven, so
            #     diffing file mtimes here would leave a dead lane green on screen forever.
            board = board_document(srv)
            bsig = _strip(board)
            if bsig != last_board_sig:
                self._emit("status", board)
                last_board_sig = bsig

            # 3 - the trails.  On a log change, and on a slow clock sweep so STALLED surfaces.
            if log_changed or (now_m - last_sweep) >= 5.0:
                last_sweep = now_m
                if cached.status == "ok":
                    for e in [x for x in cached.entries if x.kind == "say"][-50:]:
                        try:
                            trail = roomlog.render_trail(e.id, cached)
                        except Exception as exc:                  # noqa: BLE001
                            trail = {"id": e.id, "file_status": "UNREAD",
                                     "reason": f"the trail could not be rendered "
                                               f"({type(exc).__name__}: {exc})"}
                        tsig = _strip(trail)
                        if flight_sigs.get(e.id) != tsig:
                            flight_sigs[e.id] = tsig
                            self._emit("flight", trail)

            # 4 - the heartbeat.  The comment line is written FIRST: a dead socket raises here,
            #     which is how this thread learns the tab is gone.
            if (now_m - last_ping) >= ping_s:
                last_ping = now_m
                self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
                self._emit("ping", {"utc": roomlog.utc_now()})

        try:
            self._emit("bye", {"utc": roomlog.utc_now(), "reason": "server stopping"})
        except Exception:                                        # noqa: BLE001
            pass


class RoomServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, handler, *, token, config):
        self.token = token
        self.cfg = config
        self.sse_clients = 0
        self.sse_lock = threading.Lock()
        self.stopping = threading.Event()
        self.last_say_utc = None
        self.heartbeat_error = None
        self.fp_coord_override = _fp_coord_override()
        self.started_utc = roomlog.utc_now()
        super().__init__(addr, handler)


def _heartbeat(srv: RoomServer) -> None:
    """state/server.json - room.py is its SOLE writer (§1.3).  Written unconditionally every
    tick: the heartbeat IS the product, and a heartbeat that only appears when something
    changed cannot distinguish 'quiet' from 'dead'."""
    cycle = 0
    announced = False
    while True:
        if srv.token is _NO_GATE:
            mode = "in-process"
        elif srv.token is None:
            mode = "no-token"
        else:
            mode = "token"
        doc = {"protocol": VERSION, "writer": "room.py", "pid": os.getpid(),
               "port": srv.server_address[1], "token_mode": mode,
               "started_utc": srv.started_utc, "heartbeat_utc": roomlog.utc_now(),
               "cycle": cycle, "heartbeat_interval_s": 2.0,
               "stale_after_s": float(srv.cfg.get("stale_after_s", 15.0)),
               "sse_clients": srv.sse_clients, "last_say_utc": srv.last_say_utc,
               "root": str(ROOT), "coord_dir": str(roomlog.COORD),
               "fp_coord_override": srv.fp_coord_override}
        try:
            roomstatus.write_server(doc)
            srv.heartbeat_error = None
        except Exception as exc:                                 # noqa: BLE001
            srv.heartbeat_error = (f"state/server.json is NOT being published "
                                   f"({type(exc).__name__}: {exc}) - the server's own row on the "
                                   f"board will render UNREAD, which is correct: it is unread.")
            if not announced:
                announced = True
                print("UNREAD: " + srv.heartbeat_error, file=sys.stderr, flush=True)
        cycle += 1
        if srv.stopping.wait(2.0):
            return


# ----------------------------------------------------------------------------------------
# the CLI
# ----------------------------------------------------------------------------------------

PREAMBLE_FALLBACK = (
    "# relay-room · the chat log\n"
    "\n"
    "Three lanes, one append-only file: **Rab** (human), **Fable** (Claude), **Codex**.\n"
    "Rab types in the browser; a catcher agent notices, hands the message to a quarantined\n"
    "relay-gate instance, and the model replies by appending here.\n"
    "\n"
    "APPEND-ONLY. Nothing edits or removes an entry. An entry is\n"
    "`## RM-<id> · <utc> · from: X → to: Y · re: ... · kind: ... · body-sha256:<64 hex>`,\n"
    "a blank line, the body, a blank line, and `<!-- /RM-<id> -->`.\n"
    "The digest covers the BODY ONLY - it lives in the header and cannot cover itself.\n"
)


def ensure_preamble() -> str:
    """Create room.md WITH ITS PREAMBLE if it does not exist.  Append mode, one write, under the
    room lock - the same discipline as every other write to this file (L3).  If it exists,
    nothing happens: this function has no path that can shorten the log."""
    path = roomlog.assert_inside(roomlog.ROOM_MD)
    if path.exists():
        return "already on"
    text = getattr(roomlog, "PREAMBLE", None) or PREAMBLE_FALLBACK
    path.parent.mkdir(parents=True, exist_ok=True)
    with roomlog.Lock(roomlog.STATE / "room.lock", owner="room.py init"):
        if path.exists():                            # someone won the race; theirs stands
            return "already on"
        with io.open(path, "a", encoding="utf-8", newline="") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    return "created"


def cmd_init(a) -> int:
    dirs = [roomlog.STATE, roomlog.FLIGHT_DIR, roomlog.HANDOFF_DIR, roomlog.COORD,
            roomlog.STATE / "tmp"]
    dirs += [roomlog.HANDOFF_DIR / lane for lane in roomlog.LANES]
    for d in dirs:
        roomlog.assert_inside(d).mkdir(parents=True, exist_ok=True)

    conf_path = roomlog.STATE / "config.json"
    if conf_path.exists():
        conf_note = "already on"
    else:
        _write_json(conf_path, dict(roomlog.DEFAULTS))
        conf_note = "written"

    log_note = ensure_preamble()

    override = _fp_coord_override()
    rows = []
    for lane in roomlog.LANES:
        rows.append((lane, gate_call(["init", "--as", lane])))

    print(f"relay-room init · {roomlog.utc_now()}")
    print(f"  root     {ROOT}")
    print(f"  state    {roomlog.STATE}")
    print(f"  coord    {roomlog.COORD}   (FP_COORD)")
    print(f"  config   {conf_path.name}: {conf_note}")
    print(f"  log      {roomlog.ROOM_MD.name}: {log_note}")
    for lane, g in rows:
        line = g["stdout"] or g["stderr"] or "(no output)"
        print(f"  gate     {lane}: rc={g['rc']}  {line.splitlines()[0] if line else ''}")
    if override:
        print(f"  FP_COORD OVERRIDE: inherited {override['inherited']!r} -> forced "
              f"{override['forced_to']!r}")
        print("    (recorded in state/server.json while serving; the real coordination/ is "
              "NOT touched)")
    print("  QUARANTINE: nothing outside this directory is written, ever.")
    bad = [lane for lane, g in rows if g["rc"] != 0]
    if bad:
        print(f"  UNREAD: gate init did not return 0 for {', '.join(bad)} - read the output "
              f"above; `post` opens relay.md in append mode with no mkdir (gate.py:202), so a "
              f"failed init becomes a FileNotFoundError later, far from its cause.",
              file=sys.stderr)
        return 1
    return 0


def _banner(port: int, token) -> None:
    if token is None:
        url = f"http://127.0.0.1:{port}/"
    else:
        url = f"http://127.0.0.1:{port}/?token={token}"
    print(f"relay-room · {url}")
    print(f"  state    {roomlog.STATE}")
    print(f"  coord    {roomlog.COORD}   (FP_COORD)")
    print("  QUARANTINE: the real coordination/ is NOT touched by this process")
    if token is None:
        print("  --no-token: mutating routes are DISABLED - this is a read-only room. "
              "Restart without --no-token to write.")
    else:
        print("  open the URL ABOVE, including ?token= — mutating routes fail closed without it")
    py = sys.executable
    print(f"  agents:  {py} catcher.py --lane Fable   |   {py} catcher.py --lane Codex")
    sys.stdout.flush()


def cmd_serve(a) -> int:
    c = cfg(refresh=True, overrides={"port": a.port})
    if not roomlog.STATE.exists():
        print(f"UNREAD: {roomlog.STATE} does not exist - run `room.py init` first. Serving "
              f"anyway would answer every probe with 'missing', which is honest but useless.",
              file=sys.stderr)
        return 1
    token = None if a.no_token else (a.token or secrets.token_hex(16))
    srv = RoomServer(("127.0.0.1", int(a.port)), RoomHandler, token=token, config=c)
    port = srv.server_address[1]
    hb = threading.Thread(target=_heartbeat, args=(srv,), daemon=True, name="server-heartbeat")
    hb.start()
    _banner(port, token)
    try:
        srv.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nstopping…", flush=True)
    finally:
        srv.stopping.set()
        time.sleep(min(float(c.get("poll_s", 0.5)) * 2 + 0.2, 1.5))   # let the SSE threads say bye
        try:
            srv.shutdown()
        except Exception:                                        # noqa: BLE001
            pass
        srv.server_close()
    return 0


def _read_body_arg(spec: str) -> str:
    """--body -  reads stdin; --body <path> reads a file.  gate.py's own semantics (gate.py:242),
    so the two tools feel like one tool."""
    if spec == "-":
        return sys.stdin.read()
    p = Path(spec)
    if not p.exists():
        raise Refused(400, f"--body {spec!r}: no such file. Pass a path, or `-` to read stdin.")
    return io.open(p, encoding="utf-8", errors="replace").read()


def cmd_say(a) -> int:
    body = _read_body_arg(a.body)
    out = op_say(frm=a.frm, to=a.to, body=body, re_=a.re, kind=a.kind)
    print(f"{out['id']} · {out['utc']} · from: {a.frm} → to: {a.to} · {out['digest'][:19]}…")
    if out["lanes"]:
        print(f"  lanes: {', '.join(out['lanes'])}")
    else:
        print("  lanes: none — a message to Rab has no lane trail; whether he has read it is "
              "UNREAD, permanently, by construction.")
    if not out["re_resolved"] and a.re:
        print(f"  re: {a.re} (UNRESOLVED — not in the log; accepted anyway, the log is "
              f"append-only and the target may arrive later)")
    return 0


def cmd_state(a) -> int:
    out = op_model_state(lane=a.lane, state=a.state, ticket=a.ticket, note=a.note)
    print(f"{a.lane}: model state={out['state']} ticket={out['ticket']} @ {out['utc']}")
    if out.get("note"):
        print(f"  note: {out['note']}")
    return 0


def cmd_claim(a) -> int:
    trail = op_claim(lane=a.lane, mid=a.id, note=a.note)
    stage = trail.get("trails", {}).get(a.lane, {})
    print(f"{a.lane}: claimed {a.id} — trail now {stage.get('rendered')} at "
          f"{stage.get('stage')} ({stage.get('stage_index')}/8)")
    return 0


def _fmt_lane(lane: str, d: dict) -> str:
    ra, rm = d.get("rendered_agent"), d.get("rendered_model")
    out = [f"  {lane:<6} AGENT {ra}"]
    if d.get("agent_reason"):
        out.append(f"           ↳ {d['agent_reason']}")
    out.append(f"  {'':<6} MODEL {rm}")
    if d.get("model_reason"):
        out.append(f"           ↳ {d['model_reason']}")
    fl = d.get("in_flight")
    if fl:
        out.append(f"  {'':<6} in flight {fl.get('id')} · {fl.get('stage')} · "
                   f"{fl.get('age_s')}s · {fl.get('subject')}")
    return "\n".join(out)


def cmd_status(a) -> int:
    board = board_document(None)
    print(f"relay-room board · {board.get('utc')}")
    if board.get("board_status") != "ok":
        print(f"  BOARD {board.get('board_status')}: {board.get('reason')}")
    for lane in roomlog.LANES:
        d = board.get("lanes", {}).get(lane)
        if not isinstance(d, dict):
            print(f"  {lane:<6} UNREAD — the board carries no row for this lane")
            continue
        print(_fmt_lane(lane, d))
    log = board.get("log") or {}
    print(f"  log    {log.get('log_status')} · {log.get('count')} entries · "
          f"{log.get('torn')} torn · {log.get('debris')} debris · read {log.get('read_utc')}")
    if log.get("reason"):
        print(f"           ↳ {log['reason']}")
    if a.json:
        print(json.dumps(board, indent=2, ensure_ascii=False))
    return 0


# ----------------------------------------------------------------------------------------
# selftest (§8 T28's server half; the full end-to-end also needs catcher.py)
# ----------------------------------------------------------------------------------------

def _redirect_state(base: Path):
    """Point the frozen module constants at a throwaway tree INSIDE ROOT.

    §8 blesses tempfile.mkdtemp for the unittest suite; L5 forbids writing outside ROOT.  Here
    the throwaway tree lives at state/selftest-<pid>-<ts>/, which satisfies both: assert_inside
    still holds, and state/ is gitignored, so nothing survives into the repo.
    """
    missing = []
    values = {"STATE": base, "ROOM_MD": base / "room.md", "FLIGHT_DIR": base / "flight",
              "HANDOFF_DIR": base / "handoff", "COORD": base / "coord"}
    for name, value in values.items():
        if not hasattr(roomlog, name):
            missing.append(f"roomlog.{name}")
        setattr(roomlog, name, value)
        if hasattr(roomstatus, name):
            setattr(roomstatus, name, value)
    return missing


def _snapshot(d: Path):
    """A listing + mtimes of a directory we must PROVE we did not touch."""
    try:
        return sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size)
                      for p in d.iterdir() if p.is_file())
    except OSError as exc:
        return f"UNREAD:{type(exc).__name__}"


def cmd_selftest(a) -> int:
    import http.client

    results = []          # (name, "PASS"|"FAIL"|"UNREAD", detail)

    def record(name, ok, detail=""):
        results.append((name, "PASS" if ok else "FAIL", detail))
        return ok

    real_coord = Path(roomlog.GATE_PY).resolve().parents[3] / "coordination"
    before = _snapshot(real_coord)

    base = roomlog.assert_inside(roomlog.STATE / f"selftest-{os.getpid()}-{int(time.time())}")
    missing = _redirect_state(base)
    if missing:
        results.append(("frozen constants present", "UNREAD",
                        "roomlog is missing " + ", ".join(missing)))
    for d in (base, base / "flight", base / "coord", base / "tmp", base / "handoff"):
        roomlog.assert_inside(d).mkdir(parents=True, exist_ok=True)
    for lane in roomlog.LANES:
        (base / "handoff" / lane).mkdir(parents=True, exist_ok=True)
    _write_json(base / "config.json", dict(roomlog.DEFAULTS))
    cfg(refresh=True)
    ensure_preamble()

    srv = None
    try:
        for lane in roomlog.LANES:
            g = gate_call(["init", "--as", lane])
            record(f"gate init {lane}", g["rc"] == 0, f"rc={g['rc']} {g['stdout']}{g['stderr']}")

        token = secrets.token_hex(16)
        srv = RoomServer(("127.0.0.1", 0), RoomHandler, token=token, config=cfg())
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1},
                         daemon=True).start()

        def call(method, path, payload=None, headers=None):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
            body = json.dumps(payload).encode("utf-8") if payload is not None else None
            h = dict(headers or {})
            if body is not None:
                h["Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=h)
            r = conn.getresponse()
            raw = r.read().decode("utf-8", "replace")
            conn.close()
            try:
                return r.status, json.loads(raw), dict(r.getheaders())
            except Exception:                                    # noqa: BLE001
                return r.status, raw, dict(r.getheaders())

        # L4 - the closed door, measured, including that nothing was written through it
        size_before = roomlog.ROOM_MD.stat().st_size
        st, body, _ = call("POST", "/api/say",
                           {"from": "Rab", "to": "Fable", "body": "should never land"})
        size_after = roomlog.ROOM_MD.stat().st_size
        record("POST without token is 403", st == 403, f"got {st}: {body}")
        record("a 403 wrote nothing", size_before == size_after,
               f"{size_before} -> {size_after} bytes")

        # L5 applied to the wire - no CORS header anywhere
        cors = []
        for m, p in (("GET", "/api/health"), ("GET", "/api/log"), ("GET", "/api/status"),
                     ("GET", "/api/flight"), ("GET", "/nope")):
            _, _, hd = call(m, p)
            cors += [k for k in hd if k.lower().startswith("access-control-allow-")]
        record("no Access-Control-Allow-* on any route", not cors, str(cors))

        hdr = {"X-FP-Token": token}
        st, said, _ = call("POST", "/api/say",
                           {"from": "Rab", "to": "Fable", "kind": "say",
                            "body": "selftest: first message from Rab to Fable."}, hdr)
        ok = record("POST /api/say with token is 200", st == 200, f"got {st}: {said}")
        mid = said.get("id") if ok and isinstance(said, dict) else None

        st, doc, _ = call("GET", "/api/log")
        record("GET /api/log reads it back", st == 200 and doc.get("log_status") == "ok"
               and doc.get("count") == 1, f"got {st}: {str(doc)[:200]}")

        st, doc, _ = call("GET", "/api/log?since=RM-000000000000")
        record("T21 unknown cursor returns the FULL log, since_resolved false",
               st == 200 and doc.get("since_resolved") is False and doc.get("returned") == 1,
               f"since_resolved={doc.get('since_resolved')} returned={doc.get('returned')}")

        for bad in REFUSED_DECLARATIONS:
            st, body, _ = call("POST", "/api/model/state",
                               {"lane": "Fable", "state": bad}, hdr)
            record(f"T12 model/state refuses {bad}",
                   st == 400 and "gate.py" in str(body), f"got {st}: {body}")

        if mid:
            st, body, _ = call("POST", "/api/claim", {"lane": "Fable", "id": mid}, hdr)
            record("claim reaches stage delivered", st == 200, f"got {st}: {str(body)[:200]}")
            st, body, _ = call("POST", "/api/model/state",
                               {"lane": "Fable", "state": "working", "ticket": mid}, hdr)
            record("model/state working is accepted", st == 200, f"got {st}: {body}")
            st, body, _ = call("POST", "/api/say",
                               {"from": "Fable", "to": "Rab", "re": mid,
                                "body": "selftest: Fable's reply."}, hdr)
            record("the reply lands", st == 200, f"got {st}: {body}")
            st, body, _ = call("GET", f"/api/flight?id={mid}")
            trail = (body or {}).get("flight", {}) if isinstance(body, dict) else {}
            names = [s.get("name") for s in
                     trail.get("trails", {}).get("Fable", {}).get("stages", [])
                     if s.get("reached")]
            record("the trail reaches replied", "replied" in names, f"reached: {names}")

        # the catcher half of T28 - reported, never assumed
        if (ROOT / "catcher.py").exists():
            r = subprocess.run([sys.executable, str(ROOT / "catcher.py"), "--lane", "Fable",
                                "--once"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env={**os.environ, "FP_COORD": str(roomlog.COORD)},
                               timeout=60)
            record("catcher --lane Fable --once ran", r.returncode == 0,
                   f"rc={r.returncode} {(r.stdout or '')[:200]}{(r.stderr or '')[:200]}")
        else:
            results.append(("stages caught/handed exercised", "UNREAD",
                            "catcher.py is not present beside room.py - the agent half of T28 "
                            "was NOT exercised. This is not a pass."))

        after = _snapshot(real_coord)
        record("the REAL coordination/ was not touched", before == after,
               f"{real_coord}")
        record("the quarantined relay is the only one written",
               (roomlog.COORD / "relay.md").exists() or
               any((roomlog.COORD).glob("ack-*.json")),
               str(roomlog.COORD))
    finally:
        if srv is not None:
            srv.stopping.set()
            time.sleep(0.3)
            try:
                srv.shutdown()
            except Exception:                                    # noqa: BLE001
                pass
            srv.server_close()

    width = max(len(n) for n, _, _ in results)
    print(f"relay-room selftest · {roomlog.utc_now()}")
    print(f"  tree   {base}")
    print(f"  coord  {roomlog.COORD}")
    for name, verdict, detail in results:
        print(f"  {verdict:<6} {name:<{width}}  {detail if verdict != 'PASS' else ''}".rstrip())
    fails = [r for r in results if r[1] == "FAIL"]
    unread = [r for r in results if r[1] == "UNREAD"]
    print(f"  {len(results) - len(fails) - len(unread)} passed · {len(fails)} FAILED · "
          f"{len(unread)} UNREAD")
    if a.keep:
        print(f"  kept: {base}")
    else:
        shutil.rmtree(roomlog.assert_inside(base), ignore_errors=True)
    if fails:
        return 1
    if unread:
        print("  exit 2 = INCOMPLETE. Something was not measured; an unmeasured step is not a "
              "pass (L1).", file=sys.stderr)
        return 2
    return 0


# ----------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="room.py", description="relay-room: the server and the model's CLI (CONTRACT §3, §6)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create state/, coord/, config.json, room.md's preamble, and "
                                "run gate.py init for both lanes").set_defaults(fn=cmd_init)

    sp = sub.add_parser("serve", help="the HTTP server; prints the TOKEN-BEARING url")
    sp.add_argument("--port", type=int, default=int(roomlog.DEFAULTS.get("port", 7133)))
    sp.add_argument("--token", default=None, help="use this secret instead of a fresh one")
    sp.add_argument("--no-token", action="store_true",
                    help="DISABLE the mutating routes entirely - a read-only room")
    sp.set_defaults(fn=cmd_serve)

    sp = sub.add_parser("say", help="append one entry to room.md")
    sp.add_argument("--from", dest="frm", required=True, choices=list(roomlog.SPEAKERS))
    sp.add_argument("--to", required=True, choices=list(roomlog.SPEAKERS) + ["all"])
    sp.add_argument("--re", default=None, help="the RM- id this answers")
    sp.add_argument("--kind", default="say", choices=list(roomlog.KINDS))
    sp.add_argument("--body", required=True, help="a file with the body, or - for stdin")
    sp.set_defaults(fn=cmd_say)

    sp = sub.add_parser("state", help="declare the MODEL layer state for a lane")
    sp.add_argument("--lane", required=True, choices=list(roomlog.LANES))
    sp.add_argument("--state", required=True,
                    help="idle | working | composing  (blocked-* are sidecar READINGS, not "
                         "declarations - set them with gate.py)")
    sp.add_argument("--ticket", default=None)
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_state)

    sp = sub.add_parser("claim", help="the model says it HAS a message (the only way to stage 6)")
    sp.add_argument("--lane", required=True, choices=list(roomlog.LANES))
    sp.add_argument("--id", required=True)
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_claim)

    sp = sub.add_parser("status", help="the board, without a browser")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("selftest", help="end-to-end on a throwaway state tree")
    sp.add_argument("--keep", action="store_true", help="do not delete the throwaway tree")
    sp.set_defaults(fn=cmd_selftest)
    return p


def main(argv=None) -> int:
    # §2.1: gate.py's · — … come back as ? on the Windows console codepage otherwise (measured).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                        # noqa: BLE001
            pass
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except Refused as r:
        print(f"REFUSED ({r.code}): {r.message}", file=sys.stderr)
        return 1
    except roomlog.LockTimeout:
        print("REFUSED (503): " + _lock_detail(roomlog.STATE / "room.lock"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
