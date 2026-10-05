---
title: Repair Bench
section: Product
last-verified: 2026-10-05
verified-against: "10c32cf41bf4a72c5c4745cca42015b3ce64861c"
sources:
  - prototypes/repair-bench/bench.py
  - prototypes/repair-bench/bench.html
  - prototypes/repair-bench/test_textlayer_restore.py
  - prototypes/repair-bench/test_collapse_embedded.py
  - prototypes/repair-bench/signatures.json
  - prototypes/repair-bench/transcribe_worker.py
  - prototypes/repair-bench/acceptance.py
  - prototypes/repair-bench/test_bench_page.py
  - prototypes/README.md
  - windows-widget/src-tauri/src/bench.rs
  - windows-widget/src-tauri/src/main.rs
  - windows-widget/src/event-vocab.js
  - windows-widget/src/main.js
  - windows-widget/src/room.js
  - windows-converter/convert_and_ship.py
  - docs/38-file-portal-full-system-scope.md
  - prototypes/docling-calibration/README.md
  - OPEN-TASKS.md
  - SYMPTOM-INDEX.md
---

**The Repair Bench is where the pipeline actually terminates.** No bundle on this machine has
ever carried a `pass` verdict — a census of every manifest in the desktop library (probe, run
2026-08-23: `grep -o '"verdict"...' C:/Users/Bndit/ml/library/{anchor,held}/*/manifest.json`)
finds 27 manifests, of which 16 carry a fidelity verdict: **13 `fail`, 3 `flag`, 0 `pass`**
(the other 11 are pre-audit anchors the Room skips by design, windows-widget/src-tauri/src/room.rs:84-85).
`held/` is defined as "audit-failed bundles" (windows-converter/convert_and_ship.py:155) and holds
4 bundles, 4/4 `fail`. So every audited book ends up in front of a human at the Bench: a local
web app — `bench.py`, a 2,881-line stdlib+pymupdf server, plus `bench.html`, a 3,419-line
single-file UI (`wc -l`, 2026-09-30) —
that shows the source-PDF
page beside the markdown, navigated by the audit's flagged zones, where the operator crops,
collapses, transcribes, and repairs. It lives in `prototypes/` under the quarantine convention,
yet the widget spawns it directly — a contradiction the record only half-acknowledges (below).


> **S108 update (2026-08-23):** three open defects closed this session — Ctrl+Z restored (native-undo path, `0f0e83f`; plaintext-only MODE was the killer), zone-click render is highlight-only when text is unchanged (`f9585b3`, perf log includes forced layout), and the bench gained its first 19-test stdlib harness (`abe4830`) with both S106 regressions as named fixtures. That harness now runs 81 tests; mutating routes require the launch token (`fb2a919`).

> **2026-09-30 update (Rab: "absolute locked inside my tailscale vpn"):** the bench now refuses everyone outside this machine and the tailnet on its own — a listener lock, a peer lock, a proxy-header refusal and, since the plain-http round, an `Origin` rule plus proof for its one side-effecting GET, beside the S215 Host pin and the token. Browsers send `Sec-Fetch-Site` only to https and loopback, so over plain http to the tailnet that rule is inert and the `Origin` rule carries the lock. The "Security posture" section below says what is refused, by which check, and which 403 or 421 shows it. The suite is now 206 tests (the round-4 verifier's run of test_bench_page.py, 2026-09-30: 206 OK). Read in the working tree: the code is uncommitted on top of 61e3552.

## What it is

- `prototypes/repair-bench/` — `bench.py` (2,881 lines), `bench.html` (3,419), plus the acceptance,
  glass-test, transcription, evidence, and signature artifacts (`wc -l`, 2026-09-30).
- Design intent: docs/19 §7's Stage G — "the human IS the vision model" (prototypes/README.md:29).
  Server always binds `127.0.0.1` (default `http://127.0.0.1:7077`, bench.py:2833,2872) and
  `--also-bind` adds one tailnet listener for the phone (:2836; Security posture); `--sandbox`
  repairs a copy under `.sandbox/` (:2831).
- REPAIRS.md, the ledger's final report, is generated beside the bundle per docs/28 §3
  (`repairs_report`, bench.py:2117-2175).

### The quarantine contradiction

`prototypes/README.md:3-4` claims nothing in `prototypes/` "is imported, spawned, watched,
shipped, or run by the live" pipeline. But the widget's `bench_open` command
(windows-widget/src-tauri/src/main.rs:93) calls `bench::open` (bench.rs:144), which resolves
`prototypes/repair-bench/bench.py` (`bench_script`, bench.rs:127-134) and spawns it as a child process
(`Command::new(gpu_python_exe)` … `.spawn()`, bench.rs:184-197). The same README's repair-bench
row narrows the claim to "the pipeline never depends on or triggers it" (prototypes/README.md:29),
and docs/38 names the seam honestly: "Live tool behind a quarantine boundary … The widget spawns
it as a child, but production code does not import it" (docs/38-file-portal-full-system-scope.md:148).
The blanket sentence at the top of prototypes/README.md is false at HEAD; the per-row carve-out
is the real rule.

## The API surface: 26 handlers, all 25 paths reached

Route census (probe, 2026-09-30; S220 E7 on 2026-10-04 added one mutating POST, `/api/restore_textlayer` — the text-layer restoration, provenance `pdf-textlayer`, `preview: true` computes only — under the same fail-closed gate, not re-counted here): `rg -c 'url.path == "/api'` → **15 GET** handlers
(bench.py:2605-2694); `rg -c 'self.path == "/api'` → **11 POST** (bench.py:2727-2781);
26 handlers over 25 distinct paths (`/api/md` is served under both verbs), beside the non-API
GETs `/`, `/fp-tokens.css` and `/vendor/*.js`. The UI sends its `/api` calls through one `api(path, body)`
wrapper (bench.html:1076-1082) and loads the page and assets as images; `rg -c "fetch\("` = 2
(the wrapper, and one bare read of `/api/textlayer`, :1847). Every one of the 25 paths appears
literally in bench.html (`grep -c` per path, 2026-09-30).

The three routes that were defined and unreached on 2026-08-31 (`/api/ledger`, `/api/triage`,
`/api/report`) now have their buttons: register item **B13** is struck (OPEN-TASKS.md:232;
`TestB13BenchButtons`, test_bench_page.py:364).

Correction to a prior mapping pass: `/api/generate` is **not** a Bench route. It is Ollama's
endpoint, which bench.py calls *outbound* for the assist gesture
(`OLLAMA_URL = "http://127.0.0.1:11434/api/generate"`, bench.py:1855).

## The signature bank

`signatures.json` implements the error-structure design law (see memory `error-structure-protocol`;
Rab, S78 §8.5): every zone that pops up carries **reason + highlight + solution**, and the
diagnoses are **banked** so a new operator never starts cold. Six signatures (ids E, C, A, D, B, F —
`grep -c '"id":'` = 6), each pairing a mechanical detector against the zone's body window with the
three operator fields (signatures.json:42-107). Matches ship with `matched_on` evidence and the
bench prints the epistemic tag beside the diagnosis; an unmatched zone is `unclassified` — "an
honest answer. Do not add a catch-all" (signatures.json:15-22). The bank's own writing rule:
"Explain the DEFECT, never the HISTORY" (signatures.json:26). Loaded at bench.py:407-409; the
unclassified fallback tells the operator to extend the bank (bench.py:482-485).

## The vision-model seam: transcribe

`transcribe_worker.py` runs **granite-docling-258M** (`MODEL = "ibm-granite/granite-docling-258M"`,
transcribe_worker.py:26) at **zone scope**: `Bench.transcribe(zone_line, page, rect)` crops the
operator's rectangle at 220 dpi and returns a PROPOSAL — "Nothing is applied here; the human is
the final gate" (bench.py:1752). The worker reads one crop PNG and emits markdown + gate
metrics as a single JSON line on stdout (transcribe_worker.py:3-4,119), spawned per-call via
subprocess under docling-env — never marker-env (transcribe_worker.py:4-5,9; invocation
bench.py:62-63,1786). It refuses while `.gpu-lock` is held (bench.py:1753-1757).

Scope boundary, measured and left open (S71 calibration, this desktop's card): crop scope
~2-3 s at ~650-750 MiB peak — Bench-viable; **page scope 29-86 s at 144 dpi, "NOT competitive
with Marker on this card for whole documents"** (prototypes/docling-calibration/README.md:45,51-52).
Whole-page transcription is therefore not a Bench gesture today.

## Security posture

- **Who can reach it (2026-09-30).** `127.0.0.1` plus at most one `--also-bind` address, which must be a
  literal loopback or Tailscale IP (127.0.0.0/8, ::1, 100.64.0.0/10, fd7a:115c:a1e0::/48); `0.0.0.0`, `''`,
  `::`, a LAN or public address or a name is refused at the start, before a socket exists: argparse exit 2
  (`bind_ok` bench.py:2288, `_bind_arg` :2838, `serve_on` :2819). The widget passes no `--also-bind`.
- **What it refuses, in order** (`make_handler`'s `Handler`, bench.py:2523-2815):
  1. a peer outside loopback and the tailnet: bare `403` before any request byte, every method (`peer_ok` :2277, `handle` :2534).
  2. a `Host` that is not 127.0.0.1, localhost, ::1, the arrival address or a `--host` name: **421** (`host_ok` :2333); so is a second `Host` header (`host_header_ok` :2341).
  3. a `Forwarded`, `Via`, `X-Real-IP`, `X-Forwarded-*`, CDN or `Tailscale-*` header: **403** (`PROXY_MARKERS` :2372); a proxy
     or Funnel arrives from 127.0.0.1. The Funnel refusal covers HTTP-mode only; `security/lockdown_check.py` (D4/T1) catches any.
  4. `page_refusal` (:2499; on the tailnet listener 127.0.0.1, localhost and ::1 are not its own): an `Origin` that is not the bench's own (http, its names, its port; `null`, a
     second Origin, a sibling port refused) **403** `origin`; `Sec-Fetch-Site: cross-site` except a GET navigation of `/`
     into a window or frame **403** `fetch-site`; the evidence GET with no proof it came from our page **403**
     `unproven-origin`. The Fetch Metadata rule fires only where browsers send it (https, loopback), not over
     plain http to the tailnet, where the `Origin` rule and the GET rule (proof for `/api/evidence`) carry the lock: a browser puts `Origin` on
     every POST, so a foreign page's simple POST arrives with its own or `null` and is refused; an `Origin`-less
     POST is a non-browser client and goes on to the token.
  5. a POST, or the evidence GET, without the launch token: **403** with the remedy.
- Every POST is in `MUTATING_POSTS` (:2234) behind one constant-time `X-FP-Token` gate (`token_gate` :2254),
  read from the header only; without `--token` mutations are disabled. The UI attaches it (bench.html:1076-1081).
  GETs are classified `READ_ONLY_GETS` / `SIDE_EFFECT_GETS` (:2388-2391; the one side effect is `/api/evidence`).
  The suite proves refusals change nothing (test_bench_page.py:197-247) and covers the locks (:2158-3462).
- No CSP and no `frame-ancestors` is sent (every other File Portal server sends one); every answer says
  `Referrer-Policy: no-referrer`, because the page URL carries `?token=` (bench.py:2532). The token is a capability, not
  identity; a local process that learns it is in scope. The refusals rest on the lane's tests, not on a browser run (UNREAD).

## Capped evidence cannot recommend a false bless

M6-R1 makes evidence-list completeness a typed server record instead of a number inferred from
the displayed array. Runs and degeneration zones now carry `shown`, `total`, `unseen`, producer cap,
`completeness`, a label, and a remedy. A totals-bearing manifest renders `N of M`; a legacy list
below its historical cap is exact; a legacy list at cap renders `N of at least N — total UNREAD`
and names `re-convert to measure totals`; malformed or contradictory totals are also UNREAD
(`prototypes/repair-bench/bench.py:96-155,361-377`).

The completeness decision reads the manifest's **retained producer list only**. It never reads a
surface display limit. The Bench now exposes every retained omission run instead of silently
slicing the state at 40; the re-score preview likewise returns the producer-bounded zone list
instead of a second six-zone slice. Dock and Room still keep compact maps (first 40) and detail
lists (first 3), but name each truncation separately and direct the operator to the Repair Bench;
the widget backend projects the actual `runs_capped_at` / `worst_capped_at` values so its shared
count grammar can distinguish a valid `60 of 531` record from a real producer-cap contradiction
(`prototypes/repair-bench/bench.py:361-377,2078-2090`; `windows-widget/src-tauri/src/assay.rs:168-173`;
`windows-widget/src/event-vocab.js:6-32`; `windows-widget/src/main.js:930-938`).

Coverage calls its tallies `shown`, `addressed_shown`, and `open_shown`. The re-score preview now
requires clean current degeneration, zero shown-open sites, and complete evidence with zero
unseen sites before it can recommend the bless rail. Known hidden sites instead name
`full-evidence review required`; unknown legacy totals name reconversion
(`prototypes/repair-bench/bench.py:1454-1492,2035-2090`). The Bench chip, status line, and info
popover render those fields, while the shared widget helper applies the same cap-aware grammar
(`prototypes/repair-bench/bench.html:1166-1169,1337-1338,2339-2365`;
`windows-widget/src/event-vocab.js:6-20`).

The regression matrix covers future capped, future complete, legacy-at-cap, legacy-under-cap,
malformed, display-truncated, producer-cap overflow, re-score projection, and live HTTP
projection. It reproduces 25 shown of 634 runs plus 10 shown of 37 zones, with all 35 visible
sites addressed, and still requires `eligible=false`; the complete Bench suite was 81/81 (2026-08-31; 206 tests now, see the 2026-09-30 note) and real
sandbox acceptance was 85/85 on 2026-08-31 (`prototypes/repair-bench/test_bench_page.py:438-640`;
`prototypes/repair-bench/acceptance.py`).
A 2026-08-31 read-only census found 11 of 33 manifests affected (7 anchor, 4 held); none were
modified.

## Defect state at HEAD

Fixed but instructive (details live in the registers, not here): arrow keys no longer flip the
PDF page while typing, native undo survives Enter, and zone clicks move only the highlight when
text is unchanged. The source/wire suite now guards the historical line-truncation, navigation,
token, viewport, search, text-layer, table, trim, OK-15, and M6 failures, and since 2026-09-30 the tailnet locks (206 tests; 81/81 on 2026-08-31); real sandbox
acceptance was 85/85 on 2026-08-31 and was not re-run on 2026-09-30 (UNREAD). The remaining test limit is honest: no tracked harness loads the whole DOM
in a browser, so pixel/layout behavior still needs a browser smoke.

## Open items

- **docs/50 AUD-1 / M6-R2** — the fail-closed decision is built; reviewing the hidden sites
  still needs separately signed pageable evidence or identity-bound uncapped recomputation.
- **Bench locks, open** — no `frame-ancestors`; the plain-http locks are proven by request shapes
  and not yet by a browser on the phone (wiki/security.md, Open items).
- **OPEN-TASKS.md A35 / A36** — the Bench's operating doctrine is undiscovered (the operator's sequence, S220 E6–E8, starts it:
  [How an operator authenticates a hold](operator-authentication.md)); transcribe thresholds and repair audit-credit unsigned since S71/S72.
- **SYM-003** — OPEN: the table-loop disease the Bench exists to answer; the Bench is the
  response, not a fix.
- **SYM-023, SYM-025, SYM-026, SYM-030, SYM-052** — fixed Bench-adjacent rows; read before
  changing window lifecycle, zone anchoring, run rendering, report generation, or line display.
