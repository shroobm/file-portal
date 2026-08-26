# `relay-room` — THE CONTRACT

**Status:** FROZEN interface. Four builders implement against this file in parallel and cannot
ask questions. Where this file and a builder's taste disagree, **this file wins**. Where this
file is silent, the builder picks the smallest thing that satisfies the eight laws in §0 and
records the choice in `DESIGN.md`.

**What is being built, in Rab's words (2026-08-24):**

> "both you and codex open a gate relay agent … develop a really simple ui that each of you can
> write into a markdown file, the markdown file is treated as a chat, I can type into a separate
> bar, that goes into transmission towards the markdown file, an agent that catches it, gives it
> to the relay agent, the relay agent gives it to you guys, and then you guys just type in the
> markdown file replying to me. Quarantine this artifact. Also make it work Live. With loading
> and conditions that help distill the agents actions and the models actions."

Three lanes on one append-only markdown chat log — **Rab** (human), **Fable** (Claude), **Codex**.
Rab types in a browser bar → POST → appended to the log → a **catcher** agent notices → hands it
to a **quarantined relay-gate instance** → the model picks it up and appends its reply to the same
log → Rab sees it live.

The interesting half is not the chat. It is that the UI must **visibly separate the mechanical
agent layer from the model layer**, and must never render a failed probe as health.

---

## §0 — THE EIGHT LAWS (binding; violating one is a defect, not a style choice)

| # | Law | Where it bites in this build |
|---|---|---|
| **L1** | **UNREAD IS NEVER IDLE.** `down`, `clean`, `idle`, `none`, `0` are READINGS and a reading requires a probe that WORKED. Missing / malformed / unreadable → **UNREAD**. (SYM-031.) | §4 status rendering, §2 log rendering, §5 flight trails |
| **L2** | **STALENESS IS NOT HEALTH.** A heartbeat older than its threshold renders `STALE (last seen Nm ago)`, never green. Absence of an update is not evidence of idleness. | §4.6, §5.6 |
| **L3** | **APPENDS NEVER ERASE.** Never rewrite, never truncate. **Check the last byte** and lead with `\n` if it is missing (SYM-037). One `write()` call per entry. | §2.5 |
| **L4** | **FAIL CLOSED.** Every mutating HTTP route requires the launch token and refuses without it, **with remedy text**. Non-mutating routes may be open. | §3.2 |
| **L5** | **QUARANTINE.** Nothing outside `prototypes/relay-room/` may be written, ever. Zero imports from the pipeline. The prototype uses its OWN relay-gate instance via `FP_COORD`. | §1.3, §6.4 |
| **L6** | **STDLIB-ONLY PYTHON.** No third-party imports, anywhere, including tests. Target Python 3.12 on Windows. | all |
| **L7** | **SELF-CONTAINED HTML.** One file, no CDN, no external fonts, no remote anything. Theme-aware, responsive, no horizontal page scroll. | §7 |
| **L8** | **A GUARD BORN TODAY GETS ITS TRIPWIRE TODAY**, and the tripwire must be **proven to FAIL** against code lacking the guard. A test that passes both ways is a tautology. | §8 |

Two derived laws that follow from L1/L2 and are load-bearing enough to name:

- **L1a — A DERIVED READING IS NEVER FRESHER THAN ITS PUBLISHER.** If the agent that publishes a
  reading renders UNREAD or STALE, everything that reading vouches for renders UNREAD too. An
  agent that died at 14:02 may not still be telling the UI the model is working at 14:19.
- **L1b — NO UNREAD WITHOUT A REMEDY.** Every `UNREAD` / `STALE` / failed stage carries a
  human-readable sentence saying **what to do about it**, and the UI renders that sentence inline.
  (`error-structure-protocol`: reason + highlight + solution.)

And one from SYM-052:

- **L3a — TRUNCATION IS ALWAYS MARKED.** Any string shortened for display carries a visible `…`
  and the full text remains reachable (the entry itself, or a `title=` attribute). A silently
  shortened line caused a wrong repair once; it will not do it here.

---

## §1 — DIRECTORY LAYOUT

Root for everything: `C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\` — referred to
below as `ROOT`. In code, `ROOT = Path(__file__).resolve().parent`.

```
prototypes/relay-room/
  CONTRACT.md        this file — the frozen interface
  DESIGN.md          REQUIRED by the quarantine convention: what it is, references, decisions,
                     and an honest "What it cannot do" register (house style: room-chat README §4)
  README.md          operator quickstart — the launch story of §6, verbatim and copy-pasteable
  .gitignore         ignores state/ and __pycache__/  (see §1.2)

  roomlog.py         [BUILDER A] the log core: ids, digests, header grammar, parser, appender,
                     the lock, assert_inside, flight-file read/append. stdlib only.
  status.py          [BUILDER C] status documents: sidecar reader, status writer/reader,
                     render_lane / render_board (the UNREAD + STALE ladder). imports roomlog.
  catcher.py         [BUILDER C] THE AGENT. One process per lane. Filesystem-only — it never
                     speaks HTTP. imports roomlog + status.
  room.py            [BUILDER B] THE SERVER + the CLI. HTTP surface, token gate, SSE,
                     subcommands init/serve/say/state/claim/status/selftest.
                     imports roomlog + status.
  room.html          [BUILDER D] THE UI. One self-contained file. Imports nothing.
  test_room.py       [ALL FOUR] the tripwire suite (unittest, stdlib). Each builder writes the
                     tripwires listed against their name in §8.

  state/             RUNTIME. GITIGNORED. Every mutable byte this prototype produces lives here.
    config.json      thresholds in force (§4.7)
    room.md          THE CHAT LOG (§2)
    server.json      the server's own heartbeat doc — written ONLY by room.py
    status-fable.json   written ONLY by catcher.py --lane Fable
    status-codex.json   written ONLY by catcher.py --lane Codex
    model-fable.json    written ONLY by room.py (on the model's behalf, §3.3.3)
    model-codex.json    written ONLY by room.py
    flight/
      RM-<id>.jsonl  append-only stage log for one message (§5)
      RM-<id>.lock/  per-flight lock dir (§2.6)
    handoff/
      Fable/RM-<id>.json   the envelope the catcher hands the model (§4.8) — immutable once written
      Codex/RM-<id>.json
    tmp/             scratch for gate.py --body files; safe to delete at any time
    room.lock/       the room.md lock dir (§2.6)
    coord/           THE QUARANTINED RELAY-GATE INSTANCE — the FP_COORD target
      relay.md
      ack-fable.json
      ack-codex.json
```

### §1.1 Import graph (frozen — no module may import outside this set)

```
roomlog.py    -> stdlib only
status.py     -> roomlog
catcher.py    -> roomlog, status
room.py       -> roomlog, status
room.html     -> nothing at all
test_room.py  -> roomlog, status, catcher, room  (+ stdlib)
```

**Zero imports from the pipeline.** `windows-converter/`, `linux-converter/`, `observability/`,
`windows-widget/` are off limits — including by reading their modules at runtime. The only
external program this prototype executes is `gate.py` (§4.8), by absolute path, as a subprocess.

### §1.2 `.gitignore` (exact content)

```
state/
__pycache__/
*.pyc
```

### §1.3 The single-writer table (frozen — no file has two writers)

| File | Sole writer | Everyone else |
|---|---|---|
| `state/room.md` | anyone, **under the lock**, append-only via `roomlog.append_entry` | — |
| `state/status-<lane>.json` | `catcher.py --lane <Lane>` | read-only |
| `state/model-<lane>.json` | `room.py` (server + CLI) | read-only |
| `state/server.json` | `room.py serve` | read-only |
| `state/flight/RM-*.jsonl` | catchers and models, append-only under the per-flight lock | — |
| `state/handoff/<Lane>/*.json` | `catcher.py --lane <Lane>`, **write-once, never modified** | read-only |
| `state/coord/ack-<lane>.json` | `gate.py --as <Lane>` invoked by `catcher.py --lane <Lane>` **only** | read-only |
| `state/coord/relay.md` | `gate.py post` (§4.8), append-only | read-only |

The catcher for lane L passes `--as L` to `gate.py` and **never any other value**. This is
gate.py's single-writer law (`gate.py:108-113`) carried into this prototype. Tripwire **T24**.

### §1.4 Two open items that are RAB'S CALL, not a builder's

Record these in `DESIGN.md` under "Open for Rab"; do not resolve them by silent choice.

1. **The path violates the naming convention.** `prototypes/README.md` fixes the layout as
   `prototypes/<category>/<name>/` (two levels). `prototypes/relay-room/` is one level. The
   recommendation is `prototypes/coordination/relay-room/`. It is built at the instructed
   one-level path because that is what the commission named; the deviation is flagged, not hidden.
   (`repair-bench` and `glm-ocr-probe` are existing one-level violators, so there is precedent —
   which is a reason to ask, not a reason to assume.)
2. **The index row in `prototypes/README.md`.** The convention requires a row (Category · Name ·
   What it is · Status), and it must carry an explicit **"Deviation from the mocked-data rule, by
   signed design"** notice like `repair-bench`'s, because this prototype runs a REAL relay-gate
   instance (quarantined by `FP_COORD`). **No builder edits that file** — L5 is absolute and that
   path is outside `ROOT`. Draft the row in `DESIGN.md`; Rab lands it.

Also, for the record and **not to be touched** (outside the quarantine boundary): `.claude/launch.json`
still carries a `room-chat` entry pointing at `prototypes/room-chat/chat.py`, a path that died when
room-chat graduated. Do not add a launch entry for this prototype, and do not name anything here
`room-chat`.

---

## §2 — `room.md`, THE CHAT LOG

One file. Append-only. Human-readable as a document; machine-parseable without ambiguity.

### §2.1 Encoding and line endings

- Always `encoding="utf-8"`, explicitly, on every read and write. Never rely on the platform default.
- Written with `newline=""` so the `\n` characters written are the bytes that land (no CRLF
  translation). The file is LF.
- Read tolerantly: `errors="replace"` on read, and the parser normalises `\r\n` and `\r` to `\n`
  before matching (the repo is mixed-CRLF, SYM-029).
- Every CLI `main()` starts with
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` and the same for `stderr` —
  gate.py's `·`/`—`/`…` come back as `?` on the Windows console codepage otherwise (measured).
- Every `subprocess.run` capture passes `encoding="utf-8"`, for the same reason.

### §2.2 File shape

```
# relay-room · the chat log
<preamble: 1–20 lines of prose, written once at init, never re-written>

## RM-a1b2c3d4e5f6 · 2026-08-24T14:07:31.482Z · from: Rab → to: Fable · re: — · kind: say · body-sha256:6f4a…(64 hex)

Rab's message body, verbatim markdown, any content.
Multiple lines are fine. Blank lines are fine.

<!-- /RM-a1b2c3d4e5f6 -->

## RM-9c8b7a6d5e4f · 2026-08-24T14:07:44.108Z · from: Fable → to: Rab · re: RM-a1b2c3d4e5f6 · kind: say · body-sha256:11ee…(64 hex)

Fable's reply.

<!-- /RM-9c8b7a6d5e4f -->
```

**Entry = header line · blank line · body · blank line · terminator line.** Nothing else.

### §2.3 The header line (exact grammar — copy this regex verbatim)

```python
HEADER_RE = re.compile(
    r"^## (?P<id>RM-[0-9a-f]{12})"
    r" · (?P<utc>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)"
    r" · from: (?P<frm>Rab|Fable|Codex)"
    r" → to: (?P<to>Rab|Fable|Codex|all)"
    r" · re: (?P<re>RM-[0-9a-f]{12}|—)"
    r" · kind: (?P<kind>say|note|error)"
    r" · body-sha256:(?P<digest>[0-9a-f]{64})$"
)
```

- Separator is `" · "` (SPACE, U+00B7, SPACE) except before `to:` where it is `" → "` (SPACE,
  U+2192, SPACE). The arrow makes the direction readable at a glance in a plain text file and
  makes `from:`/`to:` impossible to transpose by eye.
- `re: —` (U+2014 EM DASH) means "answers nothing". A reply names **exactly one** id.
- `kind`:
  - `say` — a human or model utterance. **This is the conversation.**
  - `note` — an agent-authored mechanical note (catcher started, lock broken, gate call made).
    Rendered in the agent strip, **never** in the conversation column.
  - `error` — an agent-authored failure note. Same strip, red, always carries a remedy sentence.
- `utc` is millisecond-precision UTC:
  `now = datetime.now(timezone.utc); now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"`.
  Milliseconds are not decoration: they are an input to the id (§2.4) and they let the UI order
  three concurrent writers without a shared counter.

### §2.4 Message ids — content-derived, **never** counters

```python
def new_id(speaker: str, body: str, *, nonce=lambda: secrets.token_hex(8)) -> str:
    raw = f"{time.time_ns()}\x1f{speaker}\x1f{canonical(body)}\x1f{nonce()}"
    return "RM-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
```

**Why not a counter.** `gate.py`'s `next_id()` (`gate.py:127`) takes `max()` over its own `sent[]`
and increments. That is a read-modify-write over a shared surface, and it is safe there only
because each model writes its own sidecar. Here there are **three concurrent writers** into one
file — the server (on Rab's behalf), Fable's lane, Codex's lane — and a counter read before
another writer's uncommitted increment collides. That is **SYM-045** exactly, and it bit twice on
one machine on one day (SYM-043 and docs/40 both taken twice). A digest over
`(nanosecond clock ‖ speaker ‖ canonical body ‖ 64 bits of `secrets` entropy)` requires **no
coordination at all** and therefore cannot be raced.

**The collision check is measured, not asserted.** 12 hex = 48 bits, which is ample at this
volume, but `append_entry` still scans the log for the candidate id **under the lock** before
writing; on a hit it re-rolls the nonce, up to 3 times, then raises `SystemExit` with a remedy.
The `nonce` parameter exists so tripwire **T7** can inject a constant and prove the re-roll fires.

### §2.5 Appending (L3 — the exact procedure)

`roomlog.append_entry(*, frm, to, body, re_=None, kind="say", path=ROOM_MD, nonce=...) -> Entry`

1. `assert_inside(path)` (§6.4). Reject a `body` containing the substring `"<!-- /RM-"` — 400 with
   remedy `"a message body may not contain the entry terminator token '<!-- /RM-'; remove it or
   fence it as code"`. Reject `body.strip() == ""`. Reject `len(body) > MAX_MESSAGE_CHARS`.
2. Acquire the room lock (§2.6).
3. Derive `mid` (§2.4); scan the current log for a header with that id; re-roll up to 3×.
4. Compute `dg = digest(body)` — **over the body only**, see §2.7.
5. Build the entry as **one string**:
   `entry = header + "\n\n" + body.strip("\n") + "\n\n" + terminator(mid) + "\n"`
6. **Last-byte check** (SYM-037), the measured idiom from `linux-converter/converter/exporter.py:83-97`
   — not gate.py's unconditional `"\n" + entry` (`gate.py:203`), which never inspects the file and
   just accumulates blank lines:

   ```python
   lead = ""
   try:
       with open(path, "rb") as check:
           check.seek(-1, 2)
           if check.read(1) != b"\n":
               lead = "\n"
   except OSError:
       pass  # missing or empty file needs no lead
   ```
   A crash mid-append leaves a torn final line; appending straight onto it glues this record into
   the garbage and destroys both. The torn line stays torn — the parser surfaces it as debris —
   but this record survives.
7. If the file does not exist, `lead` is `""` and the **preamble is written as part of the same
   single string**, before the header.
8. **ONE call:**
   `with io.open(path, "a", encoding="utf-8", newline="") as fh: fh.write(lead + prefix + entry)`
9. Release the lock in a `finally`.
10. Return the `Entry`.

Nothing in this codebase ever opens `room.md` in `"w"`, `"r+"`, `"w+"`, or calls `truncate()`.
There is no delete, no edit, no compaction. Tripwire **T6a** greps the sources for those modes.

### §2.6 The lock (three writers, stdlib, Windows)

`class Lock(dir_path: Path, *, timeout_s=LOCK_TIMEOUT_S, stale_s=LOCK_STALE_S, owner: str)` —
a context manager.

- Acquire: `os.mkdir(dir_path)` — atomic on Windows and POSIX, stdlib, no `msvcrt`. On
  `FileExistsError`, sleep 20 ms and retry until `timeout_s`.
- After acquiring, best-effort write `dir_path/"owner.json"` = `{"pid":…, "owner":…, "utc":…}`.
- Release: remove `owner.json`, then `os.rmdir(dir_path)`, in a `finally`.
- **Stale break:** if the lock dir's mtime is older than `stale_s`, the waiter removes it and
  **appends a `kind: error` entry to the log** naming the broken lock (its pid, its age, the new
  owner). A lock is never broken silently — a silent break is how two writers become one lost
  record.
- Timeout: raise `LockTimeout`. Callers turn it into HTTP **503** with remedy
  `"room.md is locked by pid N (held Ns) — retry; if it persists, delete state/room.lock/"`.
  **A lock timeout is never swallowed and never renders as a successful send.**

Two lock dirs exist: `state/room.lock/` for `room.md`, and `state/flight/RM-<id>.lock/` per flight
file. Same class, same rules.

### §2.7 Digests

`canonical()` and `digest()` are **semantically identical to gate.py:61-69** so the two systems
never disagree about the same text:

```python
def canonical(text: str) -> str:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip("\n")

def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()
```

**One deliberate difference from gate.py, and it must be written in `DESIGN.md` so nobody
cross-compares the two and reports a false RED:** gate.py digests the entry *including its header
line* (`extract_entry`, `gate.py:137`). Here the digest covers the **body only**, because the
digest lives *in* the header and cannot cover itself. A `room.md` digest and a `relay.md` digest
of "the same message" are **expected to differ**; they are not comparable quantities.

### §2.8 Parsing — `roomlog.read_log(path=ROOM_MD) -> LogRead`

```python
LogRead = namedtuple("LogRead",
    "status reason preamble entries debris torn bytes read_utc")
Entry   = namedtuple("Entry",
    "id utc frm to re kind digest body digest_ok digest_note torn start_line")
```

`status` ∈ `("ok", "MISSING", "UNREAD")`:

- `"MISSING"` — the file does not exist. `reason` = a remedy: `"state/room.md does not exist — run
  `room.py init`."` **Not** `"ok"` with zero entries.
- `"UNREAD"` — the file exists but could not be read or decoded (OSError, permission, decode
  failure after `errors="replace"` is impossible, so: any exception). `reason` names the exception.
- `"ok"` — a probe that worked. `entries` may legitimately be `[]` **only** in this state (a file
  containing just the preamble).

Parsing rules:

1. Scan lines. A line matching `HEADER_RE` at column 0 opens an entry.
2. Text before the **first** header is the **preamble** — rendered as the document header, not debris.
3. The body runs from the line after the header's blank line to the line before the terminator
   `<!-- /{id} -->` (exact string match on a whole line).
4. **If the next `## RM-` header appears before this entry's terminator, the entry is TORN**:
   `torn=True`, `body` = whatever was read, and the next entry still opens normally. A torn entry
   is **never merged into its neighbour** and **never dropped**. The LogRead's `torn` counter
   increments.
5. Non-blank text between a terminator and the next header is **debris**: recorded as
   `{"after_id":…, "lines":n, "sample": first 120 chars + "…"}`. Debris is never silently discarded
   and never parsed as a message.
6. For every entry, recompute `digest(body)` and compare to the header's claim.
   Mismatch → `digest_ok=False` and `digest_note` = `"header claims <a…>, body reads <b…> — the
   entry was edited after it was written"`. **A mismatched entry is still rendered**, flagged red.
   A digest mismatch is a MEASURED RED, never a shrug (gate.py's posture, `gate.py:258`).
7. A header line that *nearly* matches (starts `## RM-` but fails `HEADER_RE`) is debris with
   `sample` = the line, and the reason `"malformed header"`. It never becomes an entry.

`bytes` is the file size actually read; `read_utc` is when the probe ran. Both are rendered in the
UI's log-integrity chip so "41 entries" always names *when* it was 41.

---

## §3 — THE HTTP SURFACE

`room.py serve` — `http.server.ThreadingHTTPServer` bound to `("127.0.0.1", port)`, `log_message`
suppressed. Default port **7133** (`--port` overrides). 7133 clears the whole documented block:
7077 repair-bench, 7080 room-harness, 7100 room-chat (dead), 7110–7119 room-chat's llama range,
8321 docs, 8765 atlas-sim.

### §3.1 Headers on every response

- `Content-Type` and `Content-Length` always.
- On `text/html` responses, the CSP — this page renders **model output**:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline';
    style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'
  ```
- **NO `Access-Control-Allow-*` header, ever, on any route.** This is load-bearing, not hygiene:
  the token fences *writes*; what keeps the ungated GETs unreadable to a drive-by local page is
  the same-origin policy, and a single CORS header would hand the whole room to any web page in
  any local browser. Tripwire **T5**.
- `GET /` reads `room.html` **fresh per request** (S65's law): a UI edit reaches the operator on
  F5, not on the next server respawn.

### §3.2 The token gate (L4)

**Generation.** `secrets.token_hex(16)` (32 hex chars) at launch, unless `--token <secret>` is
given. `secrets` is stdlib, so the widget's SystemTime⊕pid⊕counter mix (`bench.rs:91`) is not
needed here — same shape, strictly stronger, zero dependency cost.

**Threat model, stated so nobody over- or under-builds it** (docs/38 §9.4, S108): the server binds
127.0.0.1, so the adversary is **not the network** — it is any web page in any local browser firing
cross-origin requests at the port. A secret carried only in argv and in the URL the operator opens
defeats that page. It is **not** an authentication boundary against local processes: argv is
readable by same-user processes, and `room.py say` (the CLI, §6.3) writes the log with no token at
all, deliberately, because a local process is already on the trusted side. **`from:` in an entry is
therefore a CLAIM, not proof of identity.** Say so in `DESIGN.md`'s "What it cannot do".

**Modes.**

| launch | `expected` | effect |
|---|---|---|
| `serve` (default) | a fresh 32-hex token | mutating routes require `X-FP-Token` |
| `serve --token <s>` | `<s>` | same, with the operator's secret (used by the tripwires) |
| `serve --no-token` | `None` | **mutating routes are disabled entirely**; a read-only room |
| constructed in-process by a test harness | `_NO_GATE` sentinel | admitted (already inside the process boundary) |

**The census — one gate on the whole POST verb, before dispatch:**

```python
MUTATING_POSTS = ("/api/say", "/api/claim", "/api/model/state")
```

```python
_NO_GATE = object()

def token_gate(presented: str | None, expected) -> str | None:
    """None = admitted. A string = the honest 403 reason. Constant-time compare."""
    if expected is _NO_GATE:
        return None
    if expected is None:
        return ("mutating routes are disabled: room.py was started with --no-token. "
                "Restart it as `room.py serve` (it mints a token and prints the URL) and open "
                "the page as /?token=<secret>.")
    if not presented or not hmac.compare_digest(
            presented.encode("utf-8"), str(expected).encode("utf-8")):
        return ("X-FP-Token missing or wrong — reload the page with ?token=<the value room.py "
                "printed at launch> so the UI attaches it to every mutating request.")
    return None
```

Two **distinct** remedy strings — "you started the server wrong" vs "you loaded the page wrong" —
and they are load-bearing: tripwire **T3** asserts on the first one's text.

**Call site** — in `do_POST`, **before any route dispatch**, so a route added later cannot forget it:

```python
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
    ...  # first `self.path == "/api/..."` appears only after this block
```

Tripwires **T1** (census == dispatch), **T2** (gate index < first dispatch index in source).

**Client half.** `room.html` reads the token itself (strategy (a) from bench.html:514) — a
one-file artifact keeps its token logic visible:

```javascript
const TOKEN = new URLSearchParams(location.search).get("token");
```
and attaches `X-FP-Token: TOKEN` to every POST. Every error response is `{"error": "<remedy>"}` and
the UI renders `j.error` **verbatim** in the status line. No server-injected shim.

### §3.3 Routes

Body limit: `Content-Length > MAX_BODY_BYTES` (65536) → **413** `{"error": "request body too large
(N bytes, limit 65536)"}`, after draining. Unknown path → **404** `{"error": "no such route: <path>"}`.
Malformed JSON → **400** with the parse error and the expected shape.

#### Non-mutating (GET, ungated)

**`GET /`** → `room.html`, 200, `text/html; charset=utf-8` + CSP.

**`GET /api/health`** → 200
```json
{"ok": true, "utc": "…", "pid": 1234, "port": 7133, "token_mode": "token"|"no-token",
 "root": "C:\\…\\relay-room", "coord_dir": "C:\\…\\relay-room\\state\\coord",
 "sse_clients": 2, "version": "fp-relay-room/v1"}
```

**`GET /api/log?since=<RM-id>`** → 200, always (a failed read is reported *inside* the document,
never as a 500 — a 500 renders as "the room is broken" and loses the reason):
```json
{"protocol": "fp-relay-room/v1",
 "log_status": "ok" | "MISSING" | "UNREAD",
 "reason": null | "…remedy sentence…",
 "since_resolved": true,
 "preamble": "# relay-room · the chat log\n…",
 "entries": [
   {"id":"RM-a1b2c3d4e5f6","utc":"2026-08-24T14:07:31.482Z","from":"Rab","to":"Fable",
    "re": null,"kind":"say","digest":"sha256:6f4a…","digest_ok":true,"digest_note":null,
    "torn":false,"body":"…verbatim…"}
 ],
 "debris": [{"after_id":"RM-…","lines":2,"sample":"…"}],
 "count": 41, "torn": 0, "bytes": 18211, "read_utc": "…"}
```
- `since` omitted or `0` → the whole log.
- `since` names an id present in the log → only entries strictly after it.
- **`since` names an id NOT in the log → the FULL log with `"since_resolved": false`.** Never an
  empty list: an unresolvable cursor must not look like "nothing new". Tripwire **T21**.

**`GET /api/status`** → 200, the assembled board. Schema in §4.5.

**`GET /api/flight`** → 200 `{"flights": {"RM-…": <trail object §5.4>, …}, "read_utc": "…"}`
(newest 50 by message utc). **`GET /api/flight?id=RM-…`** → 200 `{"flight": <trail object>}`; if
there is no flight file for an id that IS in the log, the trail object is the UNREAD trail of §5.5,
**not** a 404 and **not** an empty stage list.

**`GET /api/events`** → SSE. §3.4.

#### Mutating (POST, token required, fail closed)

**`POST /api/say`**

Request:
```json
{"from": "Rab", "to": "Fable"|"Codex"|"Rab"|"all", "re": null|"RM-…",
 "kind": "say", "body": "…"}
```
Validation: `from` ∈ SPEAKERS · `to` ∈ SPEAKERS+`"all"` · `kind` ∈ KINDS · `body` non-blank,
≤ `MAX_MESSAGE_CHARS`, no `"<!-- /RM-"` · `re` null or `RM-[0-9a-f]{12}`. A `re` that names an
absent id is **accepted** (the log is append-only; the target may arrive later or may have been
lost) and the response carries `"re_resolved": false` so the UI can render `re: RM-… (UNRESOLVED)`.

Response 200:
```json
{"id":"RM-…","utc":"…","digest":"sha256:…","stage":"landed","re_resolved":true,
 "lanes":["Fable"]}
```
`lanes` = the lanes that will run a flight trail for this message (`[]` when `to` is `Rab`).

Errors: 403 (token) · 400 (validation, with remedy) · 413 · 503 (`LockTimeout`) ·
500 only for a genuine unexpected exception, and its body still carries `{"error": …}`.

**`POST /api/claim`** — the model says *it* has the message. **The only writer of stage `delivered`.**
```json
{"lane": "Fable"|"Codex", "id": "RM-…", "note": null|"…"}
```
Refuses (400, remedy) if: the id is not in the log · `lane` is not the entry's `to` and the entry's
`to` is not `all` · the entry's `from` is that same lane (you cannot deliver to yourself).
On success appends the flight line `{"stage":"delivered","by":"model:<Lane>"}` and returns the trail.

**`POST /api/model/state`** — the model declares its own layer state.
```json
{"lane": "Fable"|"Codex", "state": "idle"|"working"|"composing",
 "ticket": null|"RM-…", "note": null|"…"}
```
- Writes `state/model-<lane>.json` atomically (`.part` + `os.replace`).
- If `state` ∈ `{"working","composing"}` and `ticket` names a message in the log, also appends the
  flight line `{"stage":"model-working","by":"model:<Lane>"}`.
- **REFUSES (400) `blocked-on-ack`, `blocked-on-rab`, `UNREAD`, `STALE`** with the remedy:
  `"blocked-on-ack and blocked-on-rab are readings of the relay-gate sidecar, not declarations —
  set them with gate.py (escalate / post) against FP_COORD=<coord>. UNREAD and STALE are derived
  from a failed or old probe and can never be declared by the thing being probed."`
  Tripwire **T12**.

Response 200: `{"lane":…,"state":…,"utc":…,"ticket":…}`.

### §3.4 The live mechanism — SSE, with a mandatory polling fallback

There is **no SSE precedent anywhere in this repo** (`grep -rn "EventSource\|text/event-stream"` →
zero hits), so the shape is fixed here in full.

**`GET /api/events`** → 200 with:
```
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```
(and, per §3.1, **no CORS header**.)

Frame format, exactly:
```
event: <name>\ndata: <ONE line of JSON>\n\n
```
`json.dumps(payload, separators=(",",":"), ensure_ascii=False)` — the payload must contain no raw
newline (body text is JSON-escaped, so `\n` inside a string is fine). Flush after every frame.

**The server loop:** each client gets its own thread (ThreadingHTTPServer). The loop sleeps
`POLL_S` (0.5 s), re-reads `room.md` when `(mtime, size)` changed, re-reads the flight dir and the
status files, recomputes the rendered board, and emits only what changed. It catches
`BrokenPipeError` / `ConnectionResetError` / `OSError` and exits the thread. Concurrent clients are
capped at `MAX_SSE_CLIENTS` (8); beyond that: 503 `{"error":"too many live clients (8) — close a
tab, or fall back to polling"}`.

**Events:**

| event | when | payload |
|---|---|---|
| `hello` | immediately on connect | `{"utc":…,"health":{…GET /api/health…},"cursor":"RM-…"\|null,"note":"this stream is a change notifier, not a backlog — GET /api/log now"}` |
| `entry` | a new entry appears in `room.md` | the entry object of §3.3 `/api/log` |
| `log` | the log's integrity reading changed (torn/debris/status/count) | `{"log_status":…,"reason":…,"count":n,"torn":n,"debris":n,"bytes":n,"read_utc":…}` |
| `flight` | a flight trail changed | the trail object of §5.4 |
| `status` | **the RENDERED board differs from the last one sent** | the board object of §4.5 |
| `ping` | every `SSE_PING_S` (10 s) unconditionally | `{"utc":…}` |
| `bye` | on server shutdown, best effort | `{"utc":…,"reason":"server stopping"}` |

**The stream never replays history.** `gate.py`'s `watch` suppresses everything on its first
iteration (`first = True`, `gate.py:428`) so pre-existing state is *silently* never announced.
Here the same choice is made **explicitly and told to the client**: `hello` carries the instruction
to fetch the backlog, and the client's first action after `hello` is a full `GET /api/log` +
`GET /api/status` + `GET /api/flight`.

**Staleness is a clock-driven change.** The `status` event must fire when a lane crosses its
staleness threshold **even though no file changed**. The server therefore recomputes the rendered
board on every tick and diffs the *rendered* result, not the file mtimes. Without this clause a
dead lane stays green on screen forever, which is L2 defeated by an optimisation. Tripwire **T9b**.

**Polling fallback (mandatory, not optional).** The client uses SSE when `EventSource` exists AND a
frame of any kind has arrived within `SSE_DEAD_S` (25 s). Otherwise it polls every
`POLL_FALLBACK_MS` (2000 ms):
`GET /api/log?since=<cursor>` · `GET /api/status` · `GET /api/flight`.

**The transport's own state is rendered, always**, in the header bar:
`LIVE` (SSE frame within 25 s) · `POLLING (2s)` · **`NO CONTACT — readings <Nm> old`** when both
transports have failed. In the third state the whole board is overlaid with the age of the newest
reading. There must be no combination of failures that leaves a healthy-looking room on screen
while nothing is being read. This is L1 applied to the transport itself.

---

## §4 — THE STATUS SCHEMA (the heart: agents vs models)

### §4.1 The two layers, and why they are two

The **agent layer** is mechanical: a loop, a poll, a file write, a subprocess exit code. It is
either running or it is not, and its statements are cheap and verifiable.

The **model layer** is judgment: a model is thinking, composing, waiting for a peer's ACK, or
waiting for Rab. Its statements are expensive and unverifiable from outside.

Rab's requirement — "conditions that help distill the agents actions and the models actions" — is
satisfied only if a reader can tell, at a glance and without reading labels, **which layer a claim
came from**. The schema keeps them in separate objects with disjoint enums; the UI keeps them in
visually distinct rows (§7.3).

### §4.2 `state/status-<lane>.json` — written ONLY by that lane's catcher

```json
{
  "protocol": "fp-relay-room/v1",
  "writer": "catcher:Fable",
  "lane": "Fable",
  "pid": 12345,
  "started_utc": "2026-08-24T14:00:02.001Z",
  "heartbeat_utc": "2026-08-24T14:07:31.482Z",
  "cycle": 918,
  "heartbeat_interval_s": 2.0,
  "stale_after_s": 15.0,
  "model_stale_after_s": 300.0,

  "agent": {
    "state": "watching",
    "since_utc": "2026-08-24T14:07:29.400Z",
    "detail": "polling state/room.md (41 entries, 18211 B) + state/coord/ack-fable.json",
    "last_error": null,
    "consecutive_errors": 0,
    "log_read": {"status": "ok", "count": 41, "torn": 0, "debris": 0,
                 "bytes": 18211, "read_utc": "2026-08-24T14:07:31.470Z"}
  },

  "model": {
    "state": "working",
    "source": "declared",
    "since_utc": "2026-08-24T14:06:02.900Z",
    "note": "reading the contract",
    "sidecar": {"status": "ok", "state": "working", "ticket": "RM-a1b2c3d4e5f6",
                "sent": 3, "confirmed": 2, "updated_utc": "2026-08-24T14:06Z",
                "path": "state/coord/ack-fable.json", "reason": null},
    "declared": {"status": "ok", "state": "working", "utc": "2026-08-24T14:07:12.010Z",
                 "ticket": "RM-a1b2c3d4e5f6", "note": "reading the contract", "reason": null}
  },

  "in_flight": {
    "id": "RM-a1b2c3d4e5f6",
    "from": "Rab",
    "subject": "the first 80 chars of the body, whitespace-collapsed, single line…",
    "stage": "handed",
    "stage_index": 5,
    "stage_utc": "2026-08-24T14:07:19.220Z",
    "stage_by": "catcher:Fable",
    "age_s": 12.3,
    "stalled": false
  },

  "gate": {
    "status": "ok",
    "coord_dir": "C:\\…\\prototypes\\relay-room\\state\\coord",
    "last_cmd": ["…gate.py", "ticket", "--as", "Fable", "--id", "RM-a1b…", "--state", "working"],
    "last_rc": 0,
    "last_utc": "2026-08-24T14:07:19.190Z",
    "last_stdout": "Fable: ticket=RM-a1b2c3d4e5f6 state=working",
    "last_stderr": null
  }
}
```

Written atomically: `.part` then `os.replace` — a reader never sees a half-file (gate.py's own
publish invariant, `gate.py:117`).

`in_flight` is `null` when the lane has nothing in flight. `null` here is a **reading** and is
legal only because the catcher just probed the flight dir successfully; if the flight dir could not
be read, `agent.state` is `error` and `agent.last_error` says so.

### §4.3 The agent enum — written to disk

Exactly one of, and nothing else:

| value | means |
|---|---|
| `watching` | loop healthy; nothing in flight for this lane |
| `catching` | a new entry addressed to this lane was seen; being read and digest-verified |
| `handing` | writing the handoff envelope and invoking relay-gate |
| `awaiting-model` | handed off; waiting for the model to claim it |
| `mirroring` | pushing a model-authored room entry into the quarantined relay-gate |
| `error` | the last cycle raised; `last_error` non-null, `consecutive_errors ≥ 1` |

**`UNREAD` and `STALE` are NOT in this enum and the catcher may never write them.** A process that
can write its own status file is, by construction, neither unread nor stale. UNREAD and STALE are
**the reader's verdicts about the file**, never the file's claim about itself. Tripwire **T8c**
asserts the on-disk enum excludes them.

### §4.4 The model enum — written to disk

| value | means | who can produce it |
|---|---|---|
| `idle` | nothing in hand | declared, or sidecar |
| `working` | acting on a ticket (running tools, reading, deciding) | declared, or sidecar |
| `composing` | actively writing a reply into `room.md` | **declared only** — the sidecar has no such state |
| `blocked-on-ack` | waiting for the peer model to confirm | **sidecar only** |
| `blocked-on-rab` | waiting for Rab; **no model may clear it** | **sidecar only** |

Two sources, and the **precedence is fixed**:

1. If the **sidecar probe failed** → `model.state` renders **`UNREAD`**, regardless of what
   `declared` says. A model-declared "idle" may never paper over an unreadable sidecar. (L1;
   tripwire **T11**.)
2. Else if `sidecar.state ∈ {blocked-on-ack, blocked-on-rab}` → that wins, `source: "sidecar"`.
   A declaration may not clear a block. (Tripwire **T12b**.)
3. Else if `declared` exists and `declared.utc` is within 60 s → declared wins,
   `source: "declared"`.
4. Else → `sidecar.state` wins, `source: "sidecar"`.

The sidecar probe is **gate.py's `load()` contract reimplemented, not imported** (L5 forbids
importing pipeline/skill code; gate.py is invoked, never imported). Six UNREAD rules, verbatim from
`gate.py:87-105`:

> file does not exist · any exception reading/parsing JSON · not a `dict` ·
> `protocol != "fp-relay-ack/v1"` · `writer != <lane>` · `sent` or `confirmed` not a list, or
> `escalations` present-but-not-a-list.

`read_sidecar()` returns `(None, "UNREAD", reason)` on every one of them — **there is no path that
returns a healthy-looking empty state.** Each of the six reasons is a distinct remedy sentence
(e.g. `"state/coord/ack-codex.json does not exist — Codex's lane has not run `gate.py init`; start
its catcher (README §Launch step 3)."`).

### §4.5 `GET /api/status` — the assembled board

```json
{
  "protocol": "fp-relay-room/v1",
  "utc": "2026-08-24T14:07:33.001Z",
  "thresholds": {"stale_after_s": 15.0, "model_stale_after_s": 300.0,
                 "flight_stall_after_s": 90.0, "declared_fresh_s": 60.0},
  "server": {"rendered": "ok"|"UNREAD"|"STALE", "reason": null|"…",
             "pid":…, "port":…, "token_mode":"token", "heartbeat_utc":"…", "age_s":0.4},
  "lanes": {
    "Fable": {
      "rendered_agent": "watching",
      "rendered_model": "working",
      "agent_reason": null,
      "model_reason": null,
      "doc_utc": "2026-08-24T14:07:31.482Z",
      "age_s": 1.5,
      "agent": { …the doc's agent object, or null when UNREAD… },
      "model": { …the doc's model object, or null when UNREAD… },
      "in_flight": { … or null … },
      "gate": { … or null … }
    },
    "Codex": {
      "rendered_agent": "UNREAD",
      "rendered_model": "UNREAD",
      "agent_reason": "state/status-codex.json does not exist — the Codex catcher has not been started. Run: python catcher.py --lane Codex   (README §Launch step 3)",
      "model_reason": "the publisher of this reading is UNREAD, so the reading is UNREAD (a derived reading is never fresher than its publisher)",
      "doc_utc": null, "age_s": null,
      "agent": null, "model": null, "in_flight": null, "gate": null
    }
  },
  "rab": {"sse_clients": 2, "last_say_utc": "2026-08-24T14:07:31.482Z"},
  "log": {"log_status":"ok","reason":null,"count":41,"torn":0,"debris":0,
          "bytes":18211,"read_utc":"…"}
}
```

`rendered_agent` ∈ the six agent values ∪ `{"UNREAD","STALE"}`.
`rendered_model` ∈ the five model values ∪ `{"UNREAD","STALE"}`.
When rendered is `UNREAD` or `STALE`, the corresponding `*_reason` is **non-null and is a remedy**
(L1b). Tripwire **T8b** asserts every UNREAD path produces a non-empty reason.

### §4.6 The UNREAD and STALE ladder — `status.render_lane(lane, now) -> dict`

Evaluated in this exact order; the first hit wins.

**Agent:**

| # | condition | rendered | reason (remedy) |
|---|---|---|---|
| 1 | `status-<lane>.json` does not exist | `UNREAD` | "…has not been started. Run: `python catcher.py --lane <Lane>`" |
| 2 | read raises / not valid JSON | `UNREAD` | names the exception + "delete the file and restart the catcher; it is rewritten every cycle" |
| 3 | not a dict | `UNREAD` | "…is not a JSON object" |
| 4 | `protocol != "fp-relay-room/v1"` | `UNREAD` | "…was written by a different protocol version (found `X`)" |
| 5 | `writer != "catcher:<Lane>"` | `UNREAD` | "…claims writer `X` — single-writer law: only `catcher:<Lane>` may write it" |
| 6 | `agent.state` missing or not in the six | `UNREAD` | "…carries an unknown agent state `X`" |
| 7 | `heartbeat_utc` missing or unparseable | `UNREAD` | "…has no readable heartbeat — its age cannot be measured, so its contents cannot be trusted" |
| 8 | `stale_after_s` absent, non-numeric, `< 1`, or `> 3600` | `UNREAD` | "…declares an out-of-range staleness threshold (`X`); a lane may not exempt itself from L2" |
| 9 | `now - heartbeat_utc > stale_after_s` | `STALE` | "last seen `<Nm Ns>` ago — the catcher is stopped, hung, or the clock moved. Check its terminal; restart with `python catcher.py --lane <Lane>`" |
| — | otherwise | `agent.state` | `null` |

**Model:**

| # | condition | rendered | reason |
|---|---|---|---|
| 1 | the **agent** rendered `UNREAD` or `STALE` | `UNREAD` | L1a: "the publisher of this reading is `<X>`, so the reading is UNREAD" |
| 2 | `model.sidecar.status != "ok"` | `UNREAD` | the sidecar's own remedy from §4.4 |
| 3 | `model.state` missing or not in the five | `UNREAD` | "…carries an unknown model state `X`" |
| 4 | `sidecar.state ∈ {blocked-on-ack, blocked-on-rab}` | that state | `null` |
| 5 | `declared` fresh (≤ `declared_fresh_s`) | `declared.state` | `null` |
| 6 | `sidecar.updated_utc` older than `model_stale_after_s` **and** `declared` absent or older than `model_stale_after_s` | `STALE` | "the model has not moved in `<Nm>`; its last reading is `<state>` from `<source>` at `<utc>`" |
| — | otherwise | `sidecar.state` | `null` |

**`model_stale_after_s = 300.0`, and the reason is measured, not chosen by feel:** `gate.py:56`
stamps `updated_utc` with `"%Y-%m-%dT%H:%MZ"` — **minute precision, truncated**. A threshold under
about 120 s would render a perfectly healthy lane STALE on clock granularity alone. 300 s is five
times the granularity and still catches a genuinely dead model inside one coffee. Write this
sentence into `DESIGN.md`; a future tuner will otherwise "fix" it downward and manufacture false
alarms.

`STALE` rendering, everywhere, is the literal string `STALE` **plus** an age:
`STALE (last seen 3m12s ago)`. Never a bare `STALE`, never a colour alone.

### §4.7 Thresholds and where they are configured

Defaults live in `roomlog.DEFAULTS` and are written to `state/config.json` by `room.py init` /
`room.py serve` (CLI flags override). Every status doc **echoes the thresholds it expects to be
judged by**, and the reader uses the doc's value — so a lane running a deliberately slow loop is
not judged by the server's fast threshold. Out-of-range values are UNREAD (ladder rule 8), so the
echo cannot become an escape hatch.

| key | default | governs |
|---|---|---|
| `port` | `7133` | the server |
| `poll_s` | `0.5` | the server's disk poll driving SSE |
| `catcher_interval_s` | `2.0` | the catcher loop |
| `stale_after_s` | `15.0` | agent layer (= 7.5 × heartbeat) |
| `model_stale_after_s` | `300.0` | model layer (§4.6) |
| `declared_fresh_s` | `60.0` | how long a model's declaration outranks its sidecar |
| `sse_ping_s` | `10.0` | server ping frame |
| `sse_dead_s` | `25.0` | client falls back to polling |
| `poll_fallback_ms` | `2000` | the fallback poll |
| `flight_stall_after_s` | `90.0` | a trail renders STALLED |
| `lock_timeout_s` | `5.0` | `Lock` acquire |
| `lock_stale_s` | `30.0` | `Lock` stale-break |
| `max_body_bytes` | `65536` | HTTP request body |
| `max_message_chars` | `32768` | one message |
| `max_sse_clients` | `8` | concurrent streams |

### §4.8 The catcher's cycle — and its relationship to relay-gate

`catcher.py --lane <Lane> [--interval 2.0] [--once]`. Filesystem-only; it never speaks HTTP, so the
agent layer stays observable even when the server is dead.

Each cycle:

1. `read_log()`. Record the reading into `agent.log_read`. If `status != "ok"` → `agent.state =
   "error"`, `last_error` = the reason, publish, sleep. **Never treat an unreadable log as "no new
   messages".**
2. Find entries addressed to this lane (`to == lane` or `to == "all"`) whose flight trail lacks
   `caught`, oldest first, one per cycle.
3. **`catching`** — verify `digest_ok`. A mismatch does **not** stop the catch; it appends the
   flight line `{"stage":"caught","ok":false,"note":"digest mismatch: <detail>"}` and a
   `kind: error` room entry, and the trail renders RED at `caught` (§5.3). A red trail must never
   advance to `handed`.
4. **`handing`** —
   a. write `state/handoff/<Lane>/<mid>.json` (§4.9), write-once;
   b. invoke relay-gate (below);
   c. append `{"stage":"handed","by":"catcher:<Lane>","ok": rc == 0}`.
5. **`awaiting-model`** until a `delivered` line appears (only the model can write it, §5.2).
6. **`mirroring`** — for entries whose `from == lane` and `to ∈ {Fable, Codex}` and which have not
   yet been mirrored: post them into the quarantined relay (below), then append a `kind: note`
   room entry recording the resulting `MSG-…` id.
7. Publish `status-<lane>.json`. **The status file is written every cycle, unconditionally**, even
   when nothing changed — the heartbeat *is* the product.

**The gate commands the catcher may run — an allow-list:**

`init` · `post` · `ticket` · `status` · `inbox`.

**Forbidden, permanently: `check`, `confirm`, `escalate`, `resolve`.** Reasons, each independent:

- **`check` mutates.** A read-shaped command writes `state` (`gate.py:275-312`). Calling it on a
  render tick would let the monitor change what it monitors.
- **`confirm` requires a restatement**, and a restatement auto-generated by a loop is a forged act
  of reading. Confirmation is model work.
- **`escalate` and `resolve` reach Rab.** No agent goes to the principal; no agent records his
  decision. Only a model may escalate, and only Rab may resolve.

Tripwire **T24** greps `catcher.py` for those four subcommand strings appearing in a gate argv.

**Rab→model messages become TICKETS, not posts.** gate.py's `MODELS` is `("Fable","Codex")` — there
is no Rab, and a catcher may not post as a party that does not exist. So the receiving lane's
catcher runs:

```
gate.py ticket --as <Lane> --id <RM-id> --state working
```

**GUARD B, carried across (S108/S109).** Before that call the catcher reads its own sidecar. If
`state == "blocked-on-rab"` it **skips the ticket call entirely**, sets `agent.state =
"awaiting-model"` and `agent.detail = "sidecar is blocked-on-rab — only Rab may clear it; ticket
not set"`, and appends a `kind: note`. A monitoring loop must never clear the principal's gate as a
side effect; that is precisely the defect S109 patched out of `check`. Tripwire **T25**.

**Model→model messages are MIRRORED,** by the **sender's** lane, without a ticket:

```
gate.py post --as <SenderLane> --to <OtherLane> --subject "<RM-id> <subject…>" --body <state/tmp/…>
```

No `--ticket`: GUARD A (`gate.py:189`) refuses a new ticket into a peer that is working, and a
mirror is a notice, not an assignment — a notice always passes. Acks are left ON (no `--no-ack`) so
the discipline is real; **the catcher does not confirm them** — the model does, in its own session.

**Exit codes are not health.** `gate.py check` and `inbox` print `UNREAD: …` to **stdout and exit
0** (verified). `gate.status` in the status doc is therefore derived from **parsing the sidecar
JSON**, never from `returncode`. `last_rc` is recorded for display only. Tripwire **T27**.

### §4.9 The handoff envelope — `state/handoff/<Lane>/<mid>.json`

Written once by the lane's catcher; **never modified afterwards** (a second writer would need a
lock and would give `claimed` two truths). Whether the model has claimed it is **derived from the
flight trail**, not stored here.

```json
{"protocol":"fp-relay-room/v1","writer":"catcher:Fable","lane":"Fable",
 "id":"RM-a1b2c3d4e5f6","utc":"…","from":"Rab","to":"Fable","re":null,"kind":"say",
 "digest":"sha256:…","digest_ok":true,"subject":"…80 chars…",
 "body":"…verbatim…",
 "gate":{"cmd":[…],"rc":0,"stdout":"…","stderr":"","utc":"…",
         "coord_dir":"C:\\…\\state\\coord"}}
```

This directory **is the model's inbox**. A model session picks up work by listing
`state/handoff/<Lane>/` and comparing against the flight trails.

---

## §5 — THE IN-FLIGHT PIPELINE

### §5.1 The eight stages, ordered

The UI renders these as a progress trail, left to right, always all eight, with the not-yet-reached
ones neutral.

| # | stage | advanced by | witnessed | meaning |
|---|---|---|---|---|
| 1 | `typed` | **the browser** | **client-only** | Rab pressed Send; nothing has left the tab |
| 2 | `transmitted` | **the browser** | **client-only** | the POST is in flight; the server has not answered |
| 3 | `landed` | **derived from `room.md`** | the log itself | the entry exists in the log; `utc` = its header timestamp |
| 4 | `caught` | **the receiving lane's catcher** | flight line | the catcher read it out of the log and checked its digest |
| 5 | `handed` | **the same catcher** | flight line | the handoff envelope is written **and** the relay-gate call returned |
| 6 | `delivered` | **the model** (`/api/claim` or `room.py claim`) | flight line | the model itself says it has the message |
| 7 | `model-working` | **the model** (`/api/model/state` or `room.py state`) | flight line | the model is acting on it |
| 8 | `replied` | **derived from `room.md`** | the log itself | an entry whose `re:` names this id exists |

**Stages 3 and 8 are derived, not written.** The log is its own witness: if the entry is in the
file it landed, at the timestamp in its own header; if a reply naming it is in the file it was
replied to. Deriving them removes two writers and two ways to lie. It also means the trail survives
the server being restarted mid-message.

**Stages 1 and 2 are client-only and must be rendered as such** — dashed outline, the label
`client-asserted`. They exist nowhere on disk, and a page reload legitimately loses them. That
visual distinction *is* the "distill the agents' actions from the models'" requirement applied to
the trail: the reader can see exactly which claims have a witness on disk and which are the
browser's own optimism.

### §5.2 Who may write which stage — enforced, not trusted

`roomlog.append_stage(mid, stage, by, ok=True, note=None, detail=None)` **rejects**:

- any `by` not matching `^(catcher|model):(Fable|Codex)$`;
- `stage` ∈ `{"typed","transmitted","landed","replied"}` — those are client-only or derived and
  have no line form at all;
- **`stage == "delivered"` with a `catcher:*` `by`** — only a model may claim delivery. An agent
  asserting delivery on the model's behalf is precisely the class of proxy-substitution defect this
  project keeps paying for (docs/32): a mechanical signal standing in for a judgment reading.
- **`stage == "model-working"` with a `catcher:*` `by`** — same reason.

Rejection raises `ValueError` with a remedy. The **reader** independently ignores any line that
violates these rules and counts it into the trail's `invalid` field — a bad line must not become a
green chip just because it got written by some future path. Tripwire **T13** (both halves).

### §5.3 The flight file — `state/flight/RM-<id>.jsonl`

Append-only JSONL. One object per line, written with the **same last-byte check and single
`write()`** as `room.md` (§2.5), under the per-flight lock (§2.6).

```json
{"id":"RM-a1b…","stage":"caught","utc":"2026-08-24T14:07:18.900Z","by":"catcher:Fable","ok":true,"note":null,"detail":null}
```

- Duplicate stage lines are legal; the reader takes the **first** occurrence per `(stage, lane)`.
- `ok: false` marks that stage FAILED; `note` carries the reason **and a remedy**.
- An unparseable line is counted into `torn` and **never dropped from the reading** — the trail
  carries a warning badge.

### §5.4 The trail object (returned by `/api/flight`, embedded in SSE `flight` events)

```json
{"id":"RM-a1b2c3d4e5f6","from":"Rab","to":"Fable","utc":"…","subject":"…80 chars…",
 "lanes":["Fable"],
 "trails":{
   "Fable":{
     "stage":"handed","stage_index":5,"stage_utc":"…","stage_by":"catcher:Fable",
     "rendered":"handed"|"STALLED"|"FAILED"|"UNREAD",
     "reason": null|"…remedy…",
     "age_s":12.3,
     "stages":[
       {"name":"typed","reached":false,"client_only":true,"utc":null,"by":null,"ok":null,"note":null},
       {"name":"transmitted","reached":false,"client_only":true,"utc":null,"by":null,"ok":null,"note":null},
       {"name":"landed","reached":true,"derived":true,"utc":"…","by":"log","ok":true,"note":null},
       {"name":"caught","reached":true,"utc":"…","by":"catcher:Fable","ok":true,"note":null},
       {"name":"handed","reached":true,"utc":"…","by":"catcher:Fable","ok":true,"note":null},
       {"name":"delivered","reached":false,"utc":null,"by":null,"ok":null,"note":null},
       {"name":"model-working","reached":false,"utc":null,"by":null,"ok":null,"note":null},
       {"name":"replied","reached":false,"derived":true,"utc":null,"by":null,"ok":null,"note":null}
     ],
     "torn":0,"invalid":0
   }},
 "file_status":"ok"|"MISSING"|"UNREAD","read_utc":"…"}
```

Rules the renderer must obey:

- **A failed stage stops the trail.** Once a stage has `ok: false`, `rendered` is `FAILED` and
  **no later stage may render green**, even if a later line exists. Tripwire **T14**.
- **Monotonic.** A line for a stage at or below the current maximum is recorded but never moves the
  trail backwards.
- **STALLED.** If `rendered` is not `FAILED`, `stage_index < 8`, and `now - stage_utc >
  flight_stall_after_s` (90 s) → `rendered = "STALLED"`, reason
  `"stalled at <stage> for <Nm Ns> — <the lane's current agent/model reading>"`. A stalled trail
  never renders as complete and never renders as idle. (L2 on the trail.)
- **A lane that is UNREAD or STALE blocks its trail visibly.** If the addressed lane renders UNREAD
  or STALE, the trail's `reason` must carry that lane's remedy inline, so a message stuck at
  `landed` reads as *"the Codex catcher is not running"* and not merely as *"slow"*.

### §5.5 UNREAD trails (L1 on the trail)

- Entry in `room.md`, **no flight file** → `file_status: "MISSING"`, `rendered: "UNREAD"`, reason
  `"no flight record for RM-… — the <Lane> catcher has not caught it (is it running?)"`. It must
  **not** render as `typed`, and must **not** render as an empty/quiet trail. Tripwire **T15**.
- Flight file unreadable → `file_status: "UNREAD"` with the exception in the reason.
- **A message addressed `to: Rab` has no lane trail at all.** `lanes: []`, and the UI renders:
  `landed · DELIVERED TO THE ROOM — whether Rab has read it is UNREAD (there is no probe for a
  human's attention)`. This is not a joke clause. Rendering "delivered" for a human because a file
  was written is exactly the reading-vs-probe substitution L1 exists to prevent.

### §5.6 Subject lines

`roomlog.subject(body, n=80)` — first non-blank line, whitespace collapsed to single spaces,
truncated to `n` with a trailing `…` **whenever anything was removed** (L3a / SYM-052). The full
body is always reachable in the entry itself and in the UI's `title=` attribute.

---

## §6 — THE LAUNCH STORY (Windows)

The interpreter is **`C:\Users\Bndit\ml\marker-env\Scripts\python.exe`**. A bare `python` on this
machine is the Windows Store stub and exits 49. `README.md` must open with that sentence.

### §6.1 PowerShell (primary)

```powershell
$PY   = "C:\Users\Bndit\ml\marker-env\Scripts\python.exe"
$ROOM = "C:\Users\Bndit\Projects\file-portal\prototypes\relay-room"

# 1 — create state/, state/coord/, config.json, and room.md's preamble. Idempotent.
& $PY "$ROOM\room.py" init

# 2 — the server (terminal 1). Prints the TOKEN-BEARING URL.
& $PY "$ROOM\room.py" serve --port 7133

# 3 — the agents, one terminal each. Filesystem-only; they need no token and no server.
& $PY "$ROOM\catcher.py" --lane Fable
& $PY "$ROOM\catcher.py" --lane Codex

# 4 — the tripwires
& $PY -m unittest discover -s "$ROOM" -p "test_room.py" -v
& $PY "$ROOM\room.py" selftest        # end-to-end on a throwaway state dir
```

`room.py init` also runs, with `FP_COORD` forced to `state\coord`:
`gate.py init --as Fable` and `gate.py init --as Codex` — because `relay.md` is opened in `"a"`
mode with **no mkdir** (`gate.py:202`), so `post` raises `FileNotFoundError` if the directory does
not exist yet. **Always init first.**

### §6.2 What `serve` prints (exactly this shape — the token MUST be in the URL)

```
relay-room · http://127.0.0.1:7133/?token=4b7e0c9a1d2f3e5a6b8c0d1e2f3a4b5c
  state    C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state
  coord    C:\Users\Bndit\Projects\file-portal\prototypes\relay-room\state\coord   (FP_COORD)
  QUARANTINE: the real coordination/ is NOT touched by this process
  open the URL ABOVE, including ?token= — mutating routes fail closed without it
  agents:  python catcher.py --lane Fable   |   python catcher.py --lane Codex
```

The repo's existing standalone launchers print a token-less URL (`bench.py:1567`,
`room_chat.py:592`), so an operator who starts them by hand gets a page that 403s every POST until
they hand-append `?token=`. **Do not reproduce that gap.** There is no `webbrowser.open` anywhere in
the repo and there is none here either; printing the correct URL is the whole fix.

### §6.3 The CLI a model uses from its own session (no token — it is a local process)

```powershell
# reply into the room
& $PY "$ROOM\room.py" say --from Fable --to Rab --re RM-a1b2c3d4e5f6 --body -   # body on stdin
& $PY "$ROOM\room.py" say --from Fable --to Codex --body msg.md

# declare the model layer
& $PY "$ROOM\room.py" state --lane Fable --state composing --ticket RM-a1b2c3d4e5f6 --note "drafting"

# claim a message (the ONLY way stage 6 is reached)
& $PY "$ROOM\room.py" claim --lane Fable --id RM-a1b2c3d4e5f6

# read the board without a browser
& $PY "$ROOM\room.py" status
```

`say` / `state` / `claim` share **exactly** the library code the HTTP routes use — one appender, one
lock, one set of laws. The CLI is not a second implementation. `--body -` reads stdin;
`--body <path>` reads a file (mirroring gate.py's `--body` semantics so the two tools feel the same).

### §6.4 Quarantine enforcement in code (L5)

```python
ROOT  = Path(__file__).resolve().parent
STATE = ROOT / "state"
COORD = STATE / "coord"

def assert_inside(p: Path) -> Path:
    r = Path(p).resolve()
    if ROOT not in r.parents and r != ROOT:
        raise SystemExit(
            f"QUARANTINE: refusing to touch {r} — this prototype writes only under {ROOT}. "
            f"If you meant to point it elsewhere, you meant to build a different tool."
        )
    return r
```

- **Every** mutating filesystem call in every module goes through `assert_inside` first.
- **`FP_COORD` is never inherited.** Every `gate.py` subprocess is launched with an explicitly
  constructed environment: `env = {**os.environ, "FP_COORD": str(COORD)}`. `gate.py:37` does a
  truthiness check, so an empty inherited value would silently fall through to the **real**
  `coordination/` — where Rab has a live open escalation. If an inherited `FP_COORD` differs from
  `COORD`, the process overwrites it **and appends a `kind: note`** recording the override.
- `gate.py` is invoked by **one absolute path only**:
  `C:\Users\Bndit\Projects\file-portal\.claude\skills\relay-gate\gate.py`.
  (`.agents/skills/relay-gate/gate.py` is byte-identical and `coord_dir()` resolves the same from
  either, but two paths means two things to keep in step — pick one so Fable and Codex invoke the
  same file. Put the path in one module constant, `roomlog.GATE_PY`.)
- Tripwire **T16** runs the gate-invoking function with a foreign `FP_COORD` in the environment and
  asserts (a) the quarantined `coord/` received the write and (b) the foreign directory is still
  empty.

---

## §7 — THE UI (`room.html`)

One file. No CDN, no external font, no remote anything (L7). Served by `room.py`, read fresh per
request, under the CSP of §3.1.

### §7.1 Layout

- **Header bar** — the room's title; the **transport chip** (`LIVE` / `POLLING (2s)` /
  `NO CONTACT — readings 3m12s old`); the **log-integrity chip**
  (`41 entries · 0 torn · 0 debris · read 1.2s ago`, red when `torn` or `debris` is non-zero, and
  `UNREAD` + remedy when the log probe failed); the **quarantine chip** (`coord: state/coord`).
- **Left column — the conversation.** `kind: say` entries only, oldest→newest, lane-coloured by
  `from`. Each entry: speaker, UTC, id (monospace, click-to-copy), `re:` link, and a Reply button
  that fills the composer's `re:`. A `digest_ok: false` entry gets a red border and its
  `digest_note` rendered inline. A `torn` entry gets a hatched border and the words
  `TORN — the terminator is missing; the text below may be incomplete`.
- **Right column — the board.** Three cards: Rab, Fable, Codex. §7.3.
- **Under the board — the agent strip.** `kind: note` and `kind: error` entries, newest first,
  monospace, muted. **These never appear in the conversation column.** This is where the machinery
  narrates itself.
- **Bottom — the composer.** A textarea, a `to:` selector (`Fable` / `Codex` / `all`), an optional
  `re:` chip with an ✕, and Send. Ctrl+Enter sends. Under it, the **flight trail** (§7.4).

No horizontal page scroll at any width. Code blocks, long ids and wide tables live inside their own
`overflow-x: auto` container.

### §7.2 Rendering model output safely

**`innerHTML` appears nowhere in `room.html`.** Bodies are inserted with `textContent` into a
`<pre class="body">` with `white-space: pre-wrap; overflow-wrap: anywhere`. If a builder adds
inline formatting (fenced code, inline backticks), it is built by DOM construction —
`document.createElement` + `textContent` — never by assembling an HTML string. Tripwire **T22**
greps the file. The page renders text written by two language models and typed by a human; that is
the whole reason.

### §7.3 Distilling the two layers — a hard visual requirement, not a suggestion

Every lane card carries exactly two status rows, and they must be distinguishable **without reading
the labels**:

| | AGENT row | MODEL row |
|---|---|---|
| typeface | monospace | the UI's proportional face |
| badge | **square**, 2px border, muted/steel hue | **round/pill**, filled, the lane's colour |
| content | `AGENT · watching · hb 0.8s · cycle 918` | `MODEL · composing · 14s · "drafting the reply"` |
| tone | mechanical, always shows the heartbeat age | judgmental, always shows how long in that state |

- **`UNREAD` is a distinct treatment of its own** — diagonal hatching plus the remedy sentence
  rendered inline beneath the row. It is **never** grey-neutral (grey reads as "off, and that's
  fine") and **never** green.
- **`STALE`** is amber, hatched at the edge, and always carries the age:
  `STALE (last seen 3m12s ago)`.
- The **model row of a lane whose agent row is UNREAD or STALE is itself rendered UNREAD** (L1a),
  with the reason `"the publisher of this reading is <X>"`. The UI must not be able to show a
  fresh-looking model state under a dead agent.
- The Rab card is deliberately thin: `sse_clients`, `last_say_utc`, and the honest line
  `no probe exists for a human's attention`.

### §7.4 The flight trail

Eight chips in the order of §5.1, always all eight.

- Not reached: neutral outline.
- Reached, `client_only`: **dashed** outline + the label `client-asserted`.
- Reached, disk-witnessed: solid, with `by` and the elapsed seconds.
- `ok: false`: red, with `note` inline; **every chip after it stays neutral** — nothing green above
  a failure.
- `STALLED`: the current chip turns amber and reads `STALLED at handed · 2m14s`, with the addressed
  lane's remedy underneath.
- `UNREAD` (no flight file): the whole trail is hatched with the remedy inline — never an empty
  trail, never `typed`.
- `to: Rab`: the trail shows stages 1–3 only, then the sentence from §5.5.

An in-flight message also shows a **live elapsed counter** in the composer area — the idiom from
`bench.html:1100`: not a spinner, but a line naming **who is working, on what, for how long**, e.g.
`⌛ Fable · handed 00:12 · the catcher wrote the envelope; the model has not claimed it yet`.

### §7.5 Theme

Full light palette as CSS custom properties on bare `:root`; only the tokens redefined under
`@media (prefers-color-scheme: dark)` and again under `:root[data-theme="dark"]` so an explicit
toggle wins in both directions. `body` gets an explicit token background. No colour may have its
only definition inside a media query. Every state that carries meaning (UNREAD, STALE, FAILED)
carries it in **shape and text** as well as colour — a colour-blind reader and a greyscale
screenshot must both still read the board correctly.

---

## §8 — THE TRIPWIRES (L8)

`test_room.py`, `unittest`, stdlib only, runnable as
`python -m unittest discover -s <ROOT> -p "test_room.py"`. Every test that guards a guard must be
**proven to fail** against code lacking the guard — where a control is named below, it is
mandatory, and the control is what makes the test not a tautology.

Live-server tests bind an ephemeral port on 127.0.0.1 in a `setUpClass`, run against a temporary
`state/` tree (`tempfile.mkdtemp()`), and tear down in `tearDownClass`. **No test may run against
the real `state/` and no test may leave `FP_COORD` pointing outside its temp tree.**

### Builder B — the server and the token

- **T1** `MUTATING_POSTS` equals the set of `self.path == "/api/..."` literals in `do_POST`'s
  source. *(Control: a route added to dispatch and not to the census fails the test.)*
- **T2** In `room.py`'s `do_POST` source, `token_gate(` occurs **before** the first
  `self.path == "` — a route added later cannot escape the gate.
- **T3** Live `--no-token` server: every route in `MUTATING_POSTS` → **403**, and the error text
  contains `"started with --no-token"`; `room.md` is **byte-identical before and after**; and
  `GET /api/log` still returns 200. *(The write-check is the point: a 403 that still wrote is a
  leaking gate.)*
- **T4** Live token server: missing header → 403 · `X-FP-Token: nope` → 403 · correct token →
  **assertNotEqual 403** (an admitted request may legitimately 400; the assertion is only that the
  gate let it through). Uses a per-route BENIGN payload table chosen so an admitted call fails
  validation before it writes outside the fixture.
- **T5** No response from any route (`/`, `/api/health`, `/api/log`, `/api/status`, `/api/flight`,
  `/api/events`, and a 403 and a 404) carries any header starting `Access-Control-Allow-`.
- **T20** SSE: connect; the first frame is `event: hello`; every `data:` line parses as JSON and
  contains no raw newline; a `ping` arrives within 12 s; appending an entry produces an `entry`
  frame within 3 s. *(Control: a payload with an embedded newline must fail the parse assertion.)*
- **T21** `GET /api/log?since=RM-000000000000` returns the **full** log with
  `since_resolved: false`. *(Control: returning `[]` fails.)*
- **T12** `POST /api/model/state` with each of `blocked-on-ack`, `blocked-on-rab`, `UNREAD`,
  `STALE` → 400, remedy text names gate.py. `idle`/`working`/`composing` → 200.

### Builder A — the log core

- **T6** Write a `room.md` whose last byte is **not** `\n`; append; assert (a) the new header is at
  column 0 on its own line, (b) `read_log` returns **both** the torn remnant as debris **and** the
  new entry, (c) the new entry's digest verifies. **Control (mandatory):** a naive appender
  without the last-byte check, run on the same fixture, produces a line where the header is glued
  to the remnant and `read_log` finds the new entry as **debris, not an entry** — assert that
  difference explicitly. This is the proof-of-failure L8 demands.
- **T6a** Source grep: no module opens `room.md` with `"w"`, `"r+"`, `"w+"`, `"wb"`, or calls
  `.truncate(`.
- **T7** `new_id` with an injected constant nonce and a frozen clock: two appends of an identical
  body by the same speaker produce **distinct ids**, and the second append's stage log records the
  re-roll. **Control:** with the duplicate-scan removed, the two ids are identical — assert the
  collision would have occurred.
- **T17** An entry whose terminator is missing before the next header: `torn is True`, the entry is
  **not** merged with its neighbour, and **both** entries appear in `entries`.
- **T18** Missing file → `log_status == "MISSING"` (**not** `"ok"` with 0 entries); preamble-only
  file → `"ok"` with `count == 0`. *(Both directions.)*
- **T18a** A body containing `"<!-- /RM-"` is refused with a remedy; a body containing a line that
  merely starts with `## ` is accepted and round-trips (the terminator, not the header, is what
  bounds an entry).
- **T6b** Lock: two threads appending 50 entries each produce 100 well-formed entries, 100 distinct
  ids, zero debris, zero torn. **Control:** with the lock bypassed, assert the test can produce a
  malformed file (allowed to be probabilistic — run it 20× and require at least one failure, or
  drive it with an injected sleep inside the critical section to make the race deterministic;
  prefer the injected sleep).
- **T6c** A stale lock (mtime forced older than `lock_stale_s`) is broken **and** a `kind: error`
  entry naming the broken lock appears in the log. *(Control: a fresh lock is not broken; the
  acquire times out and raises `LockTimeout`.)*

### Builder C — the agent, the status ladder, the trails

- **T8** For each of the **nine** agent ladder rules of §4.6, construct the exact malformed
  document and assert `render_lane` returns `UNREAD` (or `STALE` for rule 9) and **never**
  `watching`/`idle`. **Control:** a valid document renders the on-disk `agent.state`.
- **T8b** Every `UNREAD`/`STALE` result carries a non-empty `*_reason` (L1b). Assert across all
  nine.
- **T8c** The on-disk agent enum excludes `UNREAD` and `STALE`: `write_status` refuses a document
  whose `agent.state` is either, with a remedy.
- **T9** `heartbeat_utc = now - (stale_after_s + 1)` → `STALE` and the reason contains an age;
  `now - (stale_after_s - 1)` → healthy. *(Both directions.)*
- **T9b** The board recomputed at `T` and at `T + stale_after_s + 1` **differs**, with no file
  having changed — proving staleness is clock-driven and will reach the UI. *(This is the clause
  an optimiser would break.)*
- **T10** Agent `STALE` ⇒ model renders `UNREAD` even though `model.state == "idle"` on disk
  (L1a). *(Control: a fresh agent with the same model block renders `idle`.)*
- **T11** Sidecar `UNREAD` (each of gate.py's six rules, built as six fixtures) + a fresh declared
  `idle` ⇒ model renders `UNREAD`.
- **T12b** Sidecar `blocked-on-rab` + declared `idle` (fresh) ⇒ renders `blocked-on-rab`. A
  declaration may not clear a block.
- **T13** `append_stage` raises for: a bad `by`; a derived/client stage; `delivered` with
  `by="catcher:Fable"`; `model-working` with `by="catcher:Codex"`. And the **reader** ignores such
  a line if it is present in the file (hand-written fixture), counting it in `invalid` and leaving
  the stage unreached. *(Both halves — writer refusal and reader refusal.)*
- **T14** A trail with `caught ok:false` followed by `handed ok:true` renders `FAILED` at `caught`
  and does **not** render `handed` as reached-green. *(Control: `caught ok:true` + `handed ok:true`
  renders `handed`.)*
- **T15** An entry in `room.md` with no flight file renders `UNREAD` with a remedy naming the lane
  — **not** `typed`, **not** an empty trail.
- **T15b** A trail whose newest stage is older than `flight_stall_after_s` renders `STALLED` with
  an age; one inside the threshold does not.
- **T16** With `FP_COORD` pre-set in the environment to a foreign temp directory, the catcher's
  gate-invoking function still writes into the quarantined `coord/` and the foreign directory is
  **empty afterwards**. Plus: `assert_inside` raises for a path outside `ROOT`, and returns for one
  inside.
- **T19** A status document declaring `stale_after_s: 99999` renders `UNREAD` (a lane may not
  exempt itself from L2). *(Control: `stale_after_s: 30` renders normally.)*
- **T24** Source grep of `catcher.py`: the strings `"check"`, `"confirm"`, `"escalate"`,
  `"resolve"` never appear as a gate.py subcommand argument. *(Implement as: parse every list
  literal passed to `subprocess.run` in the source and assert its `argv[2]` — the subcommand — is
  in the allow-list `{init, post, ticket, status, inbox}`.)*
- **T25** GUARD B carried across: with the lane's sidecar at `blocked-on-rab`, one catcher cycle
  over a new Rab message **does not invoke `gate.py ticket`**, sets `agent.state ==
  "awaiting-model"`, and the sidecar still reads `blocked-on-rab` afterwards. **Control:** with the
  sidecar at `idle`, the same cycle **does** invoke `ticket` and the sidecar moves to `working`.
- **T27** A gate invocation that exits **0** while printing `UNREAD: …` yields `gate.status ==
  "UNREAD"` in the published document. *(Control: a real successful call yields `"ok"`. This is the
  `returncode == 0 is not a health reading` law, and it is the SYM-031 trap in its exact local
  form.)*
- **T26** GUARD A avoidance: the mirror invocation's argv contains no `--ticket`. *(Control: adding
  `--ticket` against a peer in `working` state reproduces gate.py's `REFUSED:` and a non-zero rc —
  assert it, so the reason for the omission is measured rather than asserted.)*

### Builder D — the UI

- **T22** `room.html` contains no occurrence of `innerHTML`, `outerHTML`, `document.write`,
  `insertAdjacentHTML`, or `new Function`.
- **T23** `room.html` references no external resource: no `src=`/`href=` beginning `http`, `//`, or
  `data:` for scripts; no `@import`; no `fonts.googleapis`; no `<link rel="stylesheet">` to
  anything but nothing at all (styles are inline).
- **T23b** Every string in `STAGES` appears in `room.html`, and every member of the agent enum and
  the model enum appears, **and so do the literals `UNREAD` and `STALE`** — a UI that cannot name a
  state cannot render it.
- **T23c** `room.html` contains a `prefers-color-scheme: dark` block **and** a
  `[data-theme="dark"]` block, and every custom property redefined in either is also defined on
  bare `:root`.

### Everyone — the end-to-end

- **T28** `room.py selftest`: on a throwaway state tree, start the server on an ephemeral port,
  start both catchers with `--once` driven in-process, POST a message from Rab to Fable, and assert
  the trail reaches `handed` with real flight lines and a real `MSG-…` id (or a real `ticket` call)
  in the quarantined `coord/`; then `claim` + `state` + a reply, and assert the trail reaches
  `replied`. Assert at the end that the **real** `coordination/` directory was never opened — by
  asserting `os.environ["FP_COORD"]` resolved inside the temp tree for every subprocess launched
  and that the temp `coord/relay.md` is the only relay touched.

**A tripwire that passes both ways is a tautology and must be rewritten.** Where the table above
says "Control", the control is part of the test, not a nice-to-have.

---

## §9 — BUILDER SPLIT

| Builder | Owns | Writes | Tripwires |
|---|---|---|---|
| **A** | the log core | `roomlog.py` | T6, T6a, T6b, T6c, T7, T17, T18, T18a |
| **B** | the server + CLI | `room.py` | T1–T5, T12, T20, T21 |
| **C** | the agent + status | `status.py`, `catcher.py` | T8, T8b, T8c, T9, T9b, T10, T11, T12b, T13, T14, T15, T15b, T16, T19, T24, T25, T26, T27 |
| **D** | the UI + the record | `room.html`, `DESIGN.md`, `README.md` | T22, T23, T23b, T23c |
| **all** | end-to-end | `test_room.py` assembly, `room.py selftest` | T28 |

**The seam between B and C** is `status.render_lane` / `status.render_board`: C owns them, B calls
them for `GET /api/status` and for the SSE `status` diff. B must not reimplement the ladder.

**The seam between A and everyone** is `roomlog`'s frozen signatures:

```python
# roomlog.py — FROZEN
ROOT: Path; STATE: Path; COORD: Path; ROOM_MD: Path; FLIGHT_DIR: Path; HANDOFF_DIR: Path
GATE_PY: Path
PROTOCOL   = "fp-relay-room/v1"
LANES      = ("Fable", "Codex")
SPEAKERS   = ("Rab", "Fable", "Codex")
KINDS      = ("say", "note", "error")
STAGES     = ("typed","transmitted","landed","caught","handed","delivered","model-working","replied")
CLIENT_STAGES  = ("typed", "transmitted")
DERIVED_STAGES = ("landed", "replied")
DEFAULTS: dict            # §4.7

def assert_inside(p) -> Path
def utc_now() -> str
def parse_utc(s: str) -> datetime | None          # None on anything unparseable — never raises
def canonical(text: str) -> str
def digest(text: str) -> str
def subject(body: str, n: int = 80) -> str
def new_id(speaker: str, body: str, *, nonce=...) -> str
def header_line(mid, utc, frm, to, re_, kind, dg) -> str
def terminator(mid: str) -> str
HEADER_RE: re.Pattern
class Lock: ...                                    # §2.6
class LockTimeout(Exception): ...
def read_log(path: Path = ROOM_MD) -> LogRead
def append_entry(*, frm, to, body, re_=None, kind="say", path=ROOM_MD, nonce=...) -> Entry
def read_flight(mid: str) -> FlightRead
def append_stage(mid, stage, by, ok=True, note=None, detail=None) -> None
def render_trail(mid, log: LogRead, *, now=None, stall_after_s=None) -> dict   # §5.4

# status.py — FROZEN
AGENT_STATES = ("watching","catching","handing","awaiting-model","mirroring","error")
MODEL_STATES = ("idle","working","composing","blocked-on-ack","blocked-on-rab")
def read_sidecar(lane) -> tuple[dict | None, str, str | None]     # (data, "ok"|"UNREAD", reason)
def read_declared(lane) -> tuple[dict | None, str, str | None]
def write_status(lane, doc) -> None
def read_status(lane) -> tuple[dict | None, str, str | None]
def write_model_declared(lane, state, ticket, note) -> None
def write_server(doc) -> None
def render_lane(lane, *, now=None) -> dict         # §4.5 "lanes" value
def render_board(*, now=None) -> dict              # §4.5 whole document
```

Nothing outside these names is shared. If a builder needs a helper another builder owns, they
duplicate the three lines rather than widen the seam.

---

## §10 — WHAT THIS PROTOTYPE CANNOT DO (write this into `DESIGN.md` and keep it honest)

1. **`from:` is a claim, not an identity.** Any local process with the token — or with filesystem
   access and no token at all — can append as `Rab`. The loopback token fences the *network*
   (a drive-by page), not the machine.
2. **There is no probe for a human's attention.** A message to Rab renders `landed`, and whether he
   has read it is UNREAD, permanently, by construction.
3. **The digest proves the body was not edited after writing; it does not prove who wrote it.**
   There are no signatures here.
4. **A room digest and a `relay.md` digest of "the same message" differ by design** (§2.7) — they
   cover different bytes and are not comparable.
5. **The catcher never confirms, escalates, or resolves.** ACK discipline and escalation remain
   model and human work; the agent layer only carries and announces.
6. **This is a prototype under `prototypes/`.** Nothing in the live system imports, spawns,
   watches, ships, or runs it, and CI does not touch it. It graduates only by an explicit,
   separate decision — never by living here.

---

*Contract authored 2026-08-24. ⟨claimed: Fable lane · occupant: Claude Opus 5⟩ — authorship claim only, never Rab's authority.*
