#!/usr/bin/env python3
"""roomlog.py - the append-only chat log, its lock, its digests, and the flight trail.

The keystone module of prototypes/relay-room/: room.py, catcher.py and status.py all import it
and nothing here imports them. Stdlib only (L6). Implements CONTRACT.md §2 and §5 exactly.

The three laws that live in this file, and the incident behind each:

  L3  APPENDS NEVER ERASE. Nothing here opens room.md in "w"/"r+"/"w+" or truncates it. Every
      append does the last-byte check first (SYM-037: a crash left a torn final line, the next
      append glued its record onto the garbage, and both were destroyed). The torn line STAYS
      torn - read_log surfaces it as debris - and the new record survives intact.

  L1  UNREAD IS NEVER IDLE. read_log distinguishes "ok with zero entries" from MISSING from
      UNREAD, and never lets a failed probe render as an empty-but-healthy log (SYM-031).

  §2.4  IDS ARE CONTENT-DERIVED, NEVER COUNTERS. Three writers share this file. A counter is a
      read-modify-write and collides (SYM-045) - and S109 proved it does not even need two racing
      writers: one writer plus one repair regressed gate.py's max()+1 and minted MSG-FAB-0018
      twice. A digest over (ns clock | speaker | canonical body | 64 bits of entropy) needs no
      coordination and therefore cannot be raced.
"""

import hashlib
import io
import json
import os
import re
import secrets
import time
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

# ---------- locations (L5: everything is under ROOT, and it is enforced, not promised) ----------

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
COORD = STATE / "coord"                 # this prototype's OWN relay-gate bus (FP_COORD points here)
ROOM_MD = STATE / "room.md"
FLIGHT_DIR = STATE / "flight"
HANDOFF_DIR = STATE / "handoff"
ROOM_LOCK = STATE / "room.lock"
CONFIG_JSON = STATE / "config.json"

# The real gate, driven as a subprocess with FP_COORD=COORD so it never touches the live bus.
GATE_PY = ROOT.parents[1] / ".claude" / "skills" / "relay-gate" / "gate.py"

LANES = ("Fable", "Codex")
SPEAKERS = ("Rab", "Fable", "Codex")
KINDS = ("say", "note", "error")

DEFAULTS = {
    "port": 7133,
    "poll_s": 0.5,
    "catcher_interval_s": 2.0,
    "stale_after_s": 15.0,
    "model_stale_after_s": 300.0,
    "declared_fresh_s": 60.0,
    "sse_ping_s": 10.0,
    "sse_dead_s": 25.0,
    "poll_fallback_ms": 2000,
    "flight_stall_after_s": 90.0,
    "lock_timeout_s": 5.0,
    "lock_stale_s": 30.0,
    "max_body_bytes": 65536,
    "max_message_chars": 32768,
    "max_sse_clients": 8,
}

LOCK_TIMEOUT_S = DEFAULTS["lock_timeout_s"]
LOCK_STALE_S = DEFAULTS["lock_stale_s"]
MAX_MESSAGE_CHARS = DEFAULTS["max_message_chars"]

TERMINATOR_TOKEN = "<!-- /RM-"

PREAMBLE = (
    "# relay-room · the chat log\n"
    "\n"
    "Three lanes, one append-only file: Rab (human), Fable and Codex (models).\n"
    "Written once at init and never rewritten. Nothing edits or deletes an entry here;\n"
    "corrections are appended, and a torn record stays torn beside its replacement.\n"
    "\n"
    "Quarantined prototype - this is NOT coordination/relay.md.\n"
)

_PREAMBLE_LINES = PREAMBLE.split("\n")


# ---------- L5: the quarantine, computed at call time ----------

def assert_inside(p) -> Path:
    """Resolve p and refuse anything outside ROOT.

    Computed against ROOT at CALL time, not by splitting on the string "relay-room/" - a path
    containing that substring somewhere else would sail straight through a string check.
    """
    rp = Path(p).resolve()
    try:
        rp.relative_to(ROOT)
    except ValueError:
        raise SystemExit(
            f"REFUSED (L5 quarantine): {rp} is outside {ROOT}. This prototype writes nothing "
            f"outside its own directory, ever. If you meant a state path, build it from "
            f"roomlog.STATE."
        )
    return rp


# ---------- time ----------

def utc_now() -> str:
    """Millisecond-precision UTC. The ms are an input to the id (§2.4), not decoration."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def parse_utc(s):
    """-> aware datetime, or None. None is a READING that the caller must render as UNREAD;
    it is never silently treated as 'now' or as age zero."""
    if not isinstance(s, str) or not s:
        return None
    try:
        txt = s[:-1] + "+00:00" if s.endswith("Z") else s
        dt = datetime.fromisoformat(txt)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ---------- digests (semantically identical to gate.py:106-114) ----------

def canonical(text: str) -> str:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()


def new_id(speaker: str, body: str, *, nonce=lambda: secrets.token_hex(8)) -> str:
    raw = f"{time.time_ns()}\x1f{speaker}\x1f{canonical(body)}\x1f{nonce()}"
    return "RM-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def subject(body: str, n: int = 80) -> str:
    """First non-blank line, whitespace collapsed, truncated with a VISIBLE ellipsis whenever
    anything was removed (L3a / SYM-052: a silently shortened line caused a wrong repair once)."""
    first = ""
    for ln in (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if ln.strip():
            first = ln.strip()
            break
    collapsed = re.sub(r"\s+", " ", first)
    removed = collapsed != (body or "").strip()
    if len(collapsed) > n:
        return collapsed[: max(0, n - 1)].rstrip() + "…"
    return collapsed + ("…" if removed and collapsed else "")


# ---------- the lock (§2.6) ----------

class LockTimeout(Exception):
    """Never swallowed, and never rendered as a successful send."""


class Lock:
    """os.mkdir is atomic on Windows and POSIX, stdlib, no msvcrt."""

    def __init__(self, dir_path, *, timeout_s=LOCK_TIMEOUT_S, stale_s=LOCK_STALE_S, owner="?"):
        self.dir = assert_inside(dir_path)
        self.timeout_s = float(timeout_s)
        self.stale_s = float(stale_s)
        self.owner = owner
        self.broke = None          # set when this acquirer broke a stale lock

    def __enter__(self):
        deadline = time.time() + self.timeout_s
        while True:
            try:
                self.dir.parent.mkdir(parents=True, exist_ok=True)
                os.mkdir(self.dir)
                break
            except FileExistsError:
                held = self._held()
                age = self._age()
                if age is not None and age > self.stale_s:
                    # A lock is NEVER broken silently: a silent break is how two writers become
                    # one lost record. The caller appends a kind:error entry naming this.
                    self.broke = {"pid": held.get("pid"), "owner": held.get("owner"),
                                  "age_s": round(age, 1), "new_owner": self.owner}
                    try:
                        (self.dir / "owner.json").unlink(missing_ok=True)
                        os.rmdir(self.dir)
                    except OSError:
                        pass
                    continue
                if time.time() >= deadline:
                    raise LockTimeout(
                        f"{self.dir.name} is locked by pid {held.get('pid')} "
                        f"(held {age if age is None else round(age, 1)}s) — retry; if it "
                        f"persists, delete {self.dir}")
                time.sleep(0.02)
        try:
            (self.dir / "owner.json").write_text(
                json.dumps({"pid": os.getpid(), "owner": self.owner, "utc": utc_now()}),
                encoding="utf-8")
        except OSError:
            pass                                    # best effort; the mkdir IS the lock
        return self

    def __exit__(self, *exc):
        # MEASURED (S109): the first cut swallowed both failures, and on Windows that leaked the
        # lock. A waiter's `_held()` read of owner.json holds a momentary handle; the owner's
        # unlink then fails with a sharing violation, rmdir fails "directory not empty", both
        # excepts passed silently, and the dir survived - so every later acquire waited out the
        # 5 s timeout until the 30 s stale-break. 50 concurrent appends took over two minutes and
        # 39 of them raised LockTimeout. A swallowed release is not a release.
        deadline = time.time() + 2.0
        while True:
            try:
                (self.dir / "owner.json").unlink(missing_ok=True)
                os.rmdir(self.dir)
                return False
            except OSError:
                if time.time() >= deadline:
                    break
                time.sleep(0.01)
        # Still stuck: do NOT pretend it was released. Leave it for the stale-break and say so,
        # because a lock that silently fails to release is how two writers become one lost record.
        try:
            print(f"[roomlog] WARNING: could not release {self.dir} (owner {self.owner}); "
                  f"it will be stale-broken in {self.stale_s:.0f}s", file=__import__("sys").stderr)
        except Exception:
            pass
        return False

    def _held(self) -> dict:
        try:
            return json.loads((self.dir / "owner.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _age(self):
        try:
            return time.time() - self.dir.stat().st_mtime
        except OSError:
            return None


# ---------- the log ----------

HEADER_RE = re.compile(
    r"^## (?P<id>RM-[0-9a-f]{12})"
    r" · (?P<utc>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)"
    r" · from: (?P<frm>Rab|Fable|Codex)"
    r" → to: (?P<to>Rab|Fable|Codex|all)"
    r" · re: (?P<re>RM-[0-9a-f]{12}|—)"
    r" · kind: (?P<kind>say|note|error)"
    r" · body-sha256:(?P<digest>[0-9a-f]{64})$"
)

NEARLY_HEADER_RE = re.compile(r"^## RM-")

Entry = namedtuple(
    "Entry", "id utc frm to re kind digest body digest_ok digest_note torn start_line")
LogRead = namedtuple(
    "LogRead", "status reason preamble entries debris torn bytes read_utc")


def terminator(mid: str) -> str:
    return f"<!-- /{mid} -->"


def _header_line(mid, utc, frm, to, re_, kind, dg_hex) -> str:
    return (f"## {mid} · {utc} · from: {frm} → to: {to} · re: {re_ or '—'} "
            f"· kind: {kind} · body-sha256:{dg_hex}")


def _last_byte_lead(path: Path) -> str:
    """SYM-037, the measured idiom. NOT gate.py's unconditional "\\n" + entry, which never
    inspects the file and simply accumulates blank lines."""
    try:
        with open(path, "rb") as check:
            check.seek(-1, 2)
            if check.read(1) != b"\n":
                return "\n"
    except OSError:
        pass                                        # missing or empty file needs no lead
    return ""


def append_entry(*, frm, to, body, re_=None, kind="say", path=ROOM_MD,
                 nonce=lambda: secrets.token_hex(8)) -> Entry:
    path = assert_inside(path)
    if frm not in SPEAKERS:
        raise ValueError(f"from must be one of {SPEAKERS}, got {frm!r}")
    if to not in SPEAKERS + ("all",):
        raise ValueError(f"to must be a speaker or 'all', got {to!r}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    body = "" if body is None else str(body)
    if TERMINATOR_TOKEN in body:
        raise ValueError(
            "a message body may not contain the entry terminator token '<!-- /RM-'; "
            "remove it or fence it as code")
    if not body.strip():
        raise ValueError("an empty message is not a message; type something")
    if len(body) > MAX_MESSAGE_CHARS:
        raise ValueError(
            f"message is {len(body)} chars, limit is {MAX_MESSAGE_CHARS}; split it")

    # Per-FILE lock. The first cut always grabbed ROOM_LOCK, so an append to any other path -
    # every test fixture, every probe file - contended on the real log's lock and serialised
    # against writers it had nothing to do with. state/room.lock stays the named lock for the
    # real log, exactly as §2.6 says; anything else locks beside itself.
    lock_dir = ROOM_LOCK if path == assert_inside(ROOM_MD) else path.with_name(path.name + ".lock")
    lock_owner = f"append:{frm}"
    with Lock(lock_dir, owner=lock_owner):
        # The critical section is deliberately CHEAP. The first cut decoded the whole log to str
        # on every append, which is O(n) per write and therefore quadratic across a run: under
        # 50 concurrent appenders, 39 of them hit the 5 s lock timeout (measured, L3.7). A bytes
        # containment check does the same collision scan at C speed with no decode, and the
        # contract's requirement - scan the log for the candidate id UNDER THE LOCK - is met
        # exactly as written.
        try:
            raw_bytes = path.read_bytes()
        except OSError:
            raw_bytes = b""
        mid = None
        for _ in range(4):
            cand = new_id(frm, body, nonce=nonce)
            if b"## " + cand.encode("ascii") + b" " not in raw_bytes:
                mid = cand
                break
        if mid is None:
            raise SystemExit(
                "REFUSED: four id candidates collided in the log. That is astronomically "
                "unlikely with real entropy — check that `nonce` has not been pinned to a "
                "constant by a test fixture.")
        utc = utc_now()
        dg = digest(body)
        header = _header_line(mid, utc, frm, to, re_, kind, dg.split(":", 1)[1])
        entry = header + "\n\n" + body.strip("\n") + "\n\n" + terminator(mid) + "\n"
        prefix = "" if raw_bytes.strip() else PREAMBLE + "\n"
        lead = _last_byte_lead(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with io.open(path, "a", encoding="utf-8", newline="") as fh:
            fh.write(lead + prefix + entry)         # ONE call (§2.5 step 8)
    return Entry(id=mid, utc=utc, frm=frm, to=to, re=re_, kind=kind, digest=dg,
                 body=body.strip("\n"), digest_ok=True, digest_note=None, torn=False,
                 start_line=-1)


def read_log(path=ROOM_MD) -> LogRead:
    path = Path(path)
    read_at = utc_now()
    if not path.exists():
        return LogRead("MISSING",
                       f"{path.name} does not exist — run `room.py init`.",
                       "", [], [], 0, 0, read_at)
    try:
        raw = io.open(path, encoding="utf-8", errors="replace").read()
        size = path.stat().st_size
    except Exception as exc:                        # a failed probe is UNREAD, never empty-ok
        return LogRead("UNREAD",
                       f"{path.name} could not be read: {type(exc).__name__}: {exc}",
                       "", [], [], 0, 0, read_at)

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    entries, debris, torn_count = [], [], 0
    preamble_lines, seen_header = [], False
    i, n = 0, len(lines)
    pending_debris, last_id = [], None

    def flush_debris():
        nonlocal pending_debris
        text = "\n".join(pending_debris).strip()
        if text:
            debris.append({"after_id": last_id, "lines": len(pending_debris),
                           "sample": text[:120] + ("…" if len(text) > 120 else ""),
                           "reason": "text between a terminator and the next header"})
        pending_debris = []

    while i < n:
        line = lines[i]
        m = HEADER_RE.match(line)
        if not m:
            if NEARLY_HEADER_RE.match(line):
                debris.append({"after_id": last_id, "lines": 1,
                               "sample": line[:120] + ("…" if len(line) > 120 else ""),
                               "reason": "malformed header"})
            elif seen_header:
                pending_debris.append(line)
            else:
                # Before the first header. Only the lines that ARE the canonical preamble count
                # as preamble; anything else here is debris. A torn remnant left by a crashed
                # write lands in exactly this position, and the first cut of this parser swallowed
                # it into the preamble - i.e. silently discarded it, which §2.8 rule 5 forbids and
                # which is the whole point of SYM-037. Preamble is what init wrote; the rest got
                # here some other way, and "some other way" is what debris means.
                k = len(preamble_lines)
                if k < len(_PREAMBLE_LINES) and line.rstrip() == _PREAMBLE_LINES[k].rstrip():
                    preamble_lines.append(line)
                elif line.strip():
                    debris.append({"after_id": None, "lines": 1,
                                   "sample": line[:120] + ("…" if len(line) > 120 else ""),
                                   "reason": "text before the first entry that is not part of "
                                             "the preamble — a torn remnant or a stray write"})
                else:
                    preamble_lines.append(line)
            i += 1
            continue

        seen_header = True
        flush_debris()
        start_line = i + 1
        mid = m.group("id")
        term = terminator(mid)
        body_lines, torn = [], False
        j = i + 1
        if j < n and lines[j].strip() == "":
            j += 1
        while j < n:
            if lines[j] == term:
                j += 1
                break
            if HEADER_RE.match(lines[j]):
                torn = True                          # never merged, never dropped (§2.8 rule 4)
                break
            body_lines.append(lines[j])
            j += 1
        else:
            torn = True

        body = "\n".join(body_lines).strip("\n")
        claimed = "sha256:" + m.group("digest")
        actual = digest(body)
        ok = (claimed == actual)
        note = None
        if not ok:
            note = (f"header claims {claimed[7:15]}…, body reads {actual[7:15]}… — "
                    f"the entry was edited after it was written")
        if torn:
            torn_count += 1
        entries.append(Entry(id=mid, utc=m.group("utc"), frm=m.group("frm"), to=m.group("to"),
                             re=None if m.group("re") == "—" else m.group("re"),
                             kind=m.group("kind"), digest=claimed, body=body,
                             digest_ok=ok, digest_note=note, torn=torn, start_line=start_line))
        last_id = mid
        i = j
    flush_debris()
    return LogRead("ok", None, "\n".join(preamble_lines).strip("\n"),
                   entries, debris, torn_count, size, read_at)


# ---------- the flight trail (§5) ----------

STAGES = ("typed", "transmitted", "landed", "caught", "handed",
          "delivered", "model-working", "replied")
CLIENT_ONLY = ("typed", "transmitted")
DERIVED = ("landed", "replied")
BY_RE = re.compile(r"^(catcher|model):(Fable|Codex)$")


def flight_path(mid: str) -> Path:
    return assert_inside(FLIGHT_DIR / f"{mid}.jsonl")


def append_stage(mid, stage, by, ok=True, note=None, detail=None):
    """§5.2 - who may write which stage, ENFORCED. The reader independently re-applies these
    rules, so a bad line written by some future path never becomes a green chip."""
    if stage in CLIENT_ONLY or stage in DERIVED:
        raise ValueError(
            f"stage {stage!r} has no line form: 'typed'/'transmitted' are client-only and "
            f"'landed'/'replied' are derived from room.md itself. Writing them would add a "
            f"writer and a way to lie.")
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {STAGES}")
    if not BY_RE.match(by or ""):
        raise ValueError(f"by must match 'catcher:<Lane>' or 'model:<Lane>', got {by!r}")
    if stage in ("delivered", "model-working") and by.startswith("catcher:"):
        raise ValueError(
            f"only a MODEL may write {stage!r}; {by!r} is an agent. An agent asserting delivery "
            f"on the model's behalf is proxy substitution (docs/32): a mechanical signal standing "
            f"in for a judgment reading. Use the model's own /api/claim or `room.py state`.")
    p = flight_path(mid)
    row = {"id": mid, "stage": stage, "utc": utc_now(), "by": by,
           "ok": bool(ok), "note": note, "detail": detail}
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with Lock(FLIGHT_DIR / f"{mid}.lock", owner=by):
        p.parent.mkdir(parents=True, exist_ok=True)
        with io.open(p, "a", encoding="utf-8", newline="") as fh:
            fh.write(_last_byte_lead(p) + line)
    return row


def _read_flight(mid):
    p = flight_path(mid)
    if not p.exists():
        return "MISSING", [], 0, 0
    try:
        raw = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception as exc:
        return f"UNREAD: {type(exc).__name__}: {exc}", [], 0, 0
    rows, torn, invalid = [], 0, 0
    for ln in raw.split("\n"):
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            torn += 1                                # counted, never dropped from the reading
            continue
        st, by = row.get("stage"), row.get("by") or ""
        if st not in STAGES or st in CLIENT_ONLY or st in DERIVED or not BY_RE.match(by):
            invalid += 1
            continue
        if st in ("delivered", "model-working") and by.startswith("catcher:"):
            invalid += 1
            continue
        rows.append(row)
    return "ok", rows, torn, invalid


def render_trail(mid, lane, *, log=None, now=None, stall_after_s=None, lane_reading=None):
    """The trail object for one lane (§5.4). Monotonic, failure-stopping, and STALLED-aware."""
    stall_after_s = DEFAULTS["flight_stall_after_s"] if stall_after_s is None else stall_after_s
    now = datetime.now(timezone.utc) if now is None else now
    log = read_log() if log is None else log

    landed_utc = replied_utc = None
    if log.status == "ok":
        for e in log.entries:
            if e.id == mid:
                landed_utc = e.utc
            if e.re == mid:
                replied_utc = replied_utc or e.utc

    fstatus, rows, torn, invalid = _read_flight(mid)
    file_status = "ok" if fstatus == "ok" else ("MISSING" if fstatus == "MISSING" else "UNREAD")
    first = {}
    for row in rows:
        if row.get("by", "").endswith(":" + lane):
            first.setdefault(row["stage"], row)

    stages, reached_idx, failed_at = [], -1, None
    for idx, name in enumerate(STAGES):
        st = {"name": name, "reached": False, "utc": None, "by": None, "ok": None, "note": None}
        if name in CLIENT_ONLY:
            st["client_only"] = True
        if name in DERIVED:
            st["derived"] = True
        if name == "landed" and landed_utc:
            st.update(reached=True, utc=landed_utc, by="log", ok=True)
        elif name == "replied" and replied_utc:
            st.update(reached=True, utc=replied_utc, by="log", ok=True)
        elif name in first:
            row = first[name]
            st.update(reached=True, utc=row.get("utc"), by=row.get("by"),
                      ok=bool(row.get("ok")), note=row.get("note"))
            if not row.get("ok") and failed_at is None:
                failed_at = idx
        if st["reached"] and failed_at is None:
            reached_idx = max(reached_idx, idx)      # monotonic: never moves backwards
        stages.append(st)

    if failed_at is not None:
        # A failed stage stops the trail: no later stage may render green (T14).
        for k in range(failed_at + 1, len(stages)):
            stages[k].update(reached=False, ok=None, by=None, utc=None)
        rendered, reason = "FAILED", (stages[failed_at].get("note")
                                      or f"stage {STAGES[failed_at]} failed")
        stage_idx = failed_at
    elif file_status == "MISSING":
        rendered = "UNREAD"
        reason = (f"no flight record for {mid} — the {lane} catcher has not caught it "
                  f"(is it running?)")
        stage_idx = reached_idx
    elif file_status == "UNREAD":
        rendered, reason, stage_idx = "UNREAD", fstatus, reached_idx
    else:
        stage_idx = reached_idx
        rendered = STAGES[stage_idx] if stage_idx >= 0 else "UNREAD"
        reason = None
        if stage_idx < 0:
            reason = (f"no stage has been reached for {mid} on the {lane} lane — "
                      f"is the catcher running?")

    stage_utc = stages[stage_idx]["utc"] if 0 <= stage_idx < len(stages) else None
    age = None
    dt = parse_utc(stage_utc)
    if dt is not None:
        age = round((now - dt).total_seconds(), 1)
    if (rendered not in ("FAILED", "UNREAD") and stage_idx < len(STAGES) - 1
            and age is not None and age > stall_after_s):
        rendered = "STALLED"
        mins, secs = divmod(int(age), 60)
        reason = (f"stalled at {STAGES[stage_idx]} for {mins}m {secs}s — "
                  f"{lane_reading or 'the lane reading is UNREAD'}")
    if lane_reading and rendered not in ("FAILED",) and reason is None:
        reason = None
    return {"stage": STAGES[stage_idx] if 0 <= stage_idx < len(STAGES) else None,
            "stage_index": stage_idx + 1 if stage_idx >= 0 else 0,
            "stage_utc": stage_utc, "stage_by": (stages[stage_idx]["by"]
                                                 if 0 <= stage_idx < len(stages) else None),
            "rendered": rendered, "reason": reason, "age_s": age,
            "stages": stages, "torn": torn, "invalid": invalid,
            "file_status": file_status}
