---
title: Repair Bench
section: Product
last-verified: 2026-08-23
verified-against: c56d486
sources:
  - prototypes/repair-bench/bench.py
  - prototypes/repair-bench/bench.html
  - prototypes/repair-bench/signatures.json
  - prototypes/repair-bench/transcribe_worker.py
  - prototypes/repair-bench/acceptance.py
  - prototypes/README.md
  - windows-widget/src-tauri/src/bench.rs
  - windows-widget/src-tauri/src/main.rs
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
(the other 11 are pre-audit anchors the Room skips by design, windows-widget/src-tauri/src/room.rs:76-77).
`held/` is defined as "audit-failed bundles" (windows-converter/convert_and_ship.py:85) and holds
4 bundles, 4/4 `fail`. So every audited book ends up in front of a human at the Bench: a local
web app — `bench.py`, a 1,504-line stdlib+pymupdf server (`wc -l`), plus `bench.html`, a
1,379-line single-file UI with one inline `<style>` and one `<script>` — that shows the source-PDF
page beside the markdown, navigated by the audit's flagged zones, where the operator crops,
collapses, transcribes, and repairs. It lives in `prototypes/` under the quarantine convention,
yet the widget spawns it directly — a contradiction the record only half-acknowledges (below).


> **S108 update (2026-08-23):** three open defects closed this session — Ctrl+Z restored (native-undo path, `0f0e83f`; plaintext-only MODE was the killer), zone-click render is highlight-only when text is unchanged (`f9585b3`, perf log includes forced layout), and the bench gained a 19-test stdlib harness (`abe4830`) with both S106 regressions as named fixtures. Mutating routes now require the launch token (`fb2a919`).

## What it is

- `prototypes/repair-bench/` — `bench.py` (1,504 lines), `bench.html` (1,379), `acceptance.py`
  (408), `transcribe_worker.py` (127), `signatures.json` (108). Counts: `wc -l`, 2026-08-23.
- Design intent: docs/19 §7's Stage G — "the human IS the vision model" (prototypes/README.md:29).
  Server binds loopback only and prints its URL (`http://127.0.0.1:7077` default,
  bench.py:1492,1499); `--sandbox` repairs a copy under `.sandbox/` (bench.py:1490-1491).
- REPAIRS.md, the ledger's final report, is generated beside the bundle per docs/28 §3
  (bench.py:156).

### The quarantine contradiction

`prototypes/README.md:3-4` claims nothing in `prototypes/` "is imported, spawned, watched,
shipped, or run by the live" pipeline. But the widget's `bench_open` command
(windows-widget/src-tauri/src/main.rs:93) calls `bench::open` (bench.rs:105), which resolves
`prototypes/repair-bench/bench.py` (bench.rs:93-95) and spawns it as a child process
(`Command::new(gpu_python_exe)` … `.spawn()`, bench.rs:140-149). The same README's repair-bench
row narrows the claim to "the pipeline never depends on or triggers it" (prototypes/README.md:29),
and docs/38 names the seam honestly: "Live tool behind a quarantine boundary … The widget spawns
it as a child, but production code does not import it" (docs/38-file-portal-full-system-scope.md:148).
The blanket sentence at the top of prototypes/README.md is false at HEAD; the per-row carve-out
is the real rule.

## The API surface: 22 handlers, 18 reached

Route census (probe, 2026-08-23): `grep -c 'url.path == "/api'` → **11 GET** handlers
(bench.py:1374-1404); `grep -c 'self.path == "/api'` → **11 POST** (bench.py:1416-1469);
22 handlers over 21 distinct paths (`/api/md` is served under both verbs, bench.py:1376 and 1424).
The UI funnels every call through one `api(path, body)` wrapper around the file's single `fetch(`
(bench.html:514-515; `grep -c "fetch("` = 1), and all paths are literals:
`grep -o '/api/[a-z_-]*' bench.html | sort -u | wc -l` = **18**.

The three defined-but-unreached routes: **`/api/ledger`** (bench.py:1389), **`/api/triage`**
(bench.py:1465), **`/api/report`** (bench.py:1469) — server-complete, no button on the glass.
That is register item **B13** (OPEN-TASKS.md:164): "The bench UI has no buttons for
triage / report / ledger although `/api/triage`, `/api/report` and `/api/ledger` exist and are
proven."

Correction to a prior mapping pass: `/api/generate` is **not** a Bench route. It is Ollama's
endpoint, which bench.py calls *outbound* for the assist gesture
(`OLLAMA_URL = "http://127.0.0.1:11434/api/generate"`, bench.py:1012). Counting it as a fourth
unreachable server route was a probe error; the served-route census above is 22/18/3.

## The signature bank

`signatures.json` implements the error-structure design law (see memory `error-structure-protocol`;
Rab, S78 §8.5): every zone that pops up carries **reason + highlight + solution**, and the
diagnoses are **banked** so a new operator never starts cold. Six signatures (ids E, C, A, D, B, F —
`grep -c '"id":'` = 6), each pairing a mechanical detector against the zone's body window with the
three operator fields (signatures.json:42-107). Matches ship with `matched_on` evidence and the
bench prints the epistemic tag beside the diagnosis; an unmatched zone is `unclassified` — "an
honest answer. Do not add a catch-all" (signatures.json:15-22). The bank's own writing rule:
"Explain the DEFECT, never the HISTORY" (signatures.json:26). Loaded at bench.py:237-238; the
unclassified fallback tells the operator to extend the bank (bench.py:307).

## The vision-model seam: transcribe

`transcribe_worker.py` runs **granite-docling-258M** (`MODEL = "ibm-granite/granite-docling-258M"`,
transcribe_worker.py:26) at **zone scope**: `Bench.transcribe(zone_line, page, rect)` crops the
operator's rectangle at 220 dpi and returns a PROPOSAL — "Nothing is applied here; the human is
the final gate" (bench.py:909-912). The worker reads one crop PNG and emits markdown + gate
metrics as a single JSON line on stdout (transcribe_worker.py:3-4,119), spawned per-call via
subprocess under docling-env — never marker-env (transcribe_worker.py:4-5,9; invocation
bench.py:53-54,953). It refuses while `.gpu-lock` is held (bench.py:916-918).

Scope boundary, measured and left open (S71 calibration, this desktop's card): crop scope
~2-3 s at ~650-750 MiB peak — Bench-viable; **page scope 29-86 s at 144 dpi, "NOT competitive
with Marker on this card for whole documents"** (prototypes/docling-calibration/README.md:45,51-52).
Whole-page transcription is therefore not a Bench gesture today.

## Security posture

- Binds `127.0.0.1` only (bench.py:1500). Loopback blocks remote hosts — nothing more.
- **No Origin, Host, token, or CSRF check anywhere in bench.py**: `grep -c "Origin" bench.py` = 0
  (positive control: `grep -c "Content-Length"` = 2, same file, same probe). `do_POST` parses any
  body with `json.loads` regardless of Content-Type (bench.py:1414-1415).
- **No CSP of its own**: `grep -ci "Content-Security" bench.html` = 0. The widget's CSP covers its
  own webview, not this server's HTTP surface.
- POST routes mutate real files — `/api/repair`, `/api/collapse`, `/api/undo` edit the bundle
  body, and `/api/open` swaps the served bundle to an arbitrary caller-supplied path
  (bench.py:1438-1441).

The repo's own law already names this class: "Loopback is a network boundary, not authentication;
another local process may still be hostile. Any future route that mutates files requires the same
path/authority scrutiny as a native command" (docs/38-file-portal-full-system-scope.md:756-758).
Honest severity: exploitation requires the Bench server to be running (it lives only during a
repair session) *and* a hostile local process or a hostile web page in some browser firing
cross-origin POSTs at `127.0.0.1:7077` — the JSON parse accepts a preflight-free `text/plain`
body. Real, local-only, unmitigated in code. (unverified: no live cross-origin exploit was
demonstrated; the claim rests on the absent checks cited above.)

## Defect state at HEAD

Fixed but instructive (details live in the registers, not here): arrow keys no longer flip the
PDF page while typing — the S106 guard keys on `isContentEditable` (bench.html:733-742); the
silent 400-char line truncation that could cause a WRONG REPAIR is SYM-052, fixed in `4d06588`
with no tripwire guarding the regression. Still open and owned by the registers: dead Ctrl+Z, the
~1 s whole-file render, and the fact that nothing in the repo loads this UI's DOM at all —
`acceptance.py` drives the server (26/26 on a sandboxed real bundle, prototypes/README.md:29),
never the glass.

## Open items

- **OPEN-TASKS.md A30** — Ctrl+Z dead after any Enter; the `innerHTML` rebuild orphans Blink's
  undo stack. Fix is a product-shape choice (custom undo model vs textarea) — Rab's call.
- **OPEN-TASKS.md B22** — whole-file render ~1 s per zone click, ~1.2 s per newline at IV's
  size; the quoted "105 ms" excluded the forced layout.
- **OPEN-TASKS.md B5** — nothing in the repo tests `bench.html`; SYM-052's row confirms no
  tripwire guards its regression.
- **OPEN-TASKS.md B13** — `/api/triage`, `/api/report`, `/api/ledger` built, proven, unreachable
  from the UI.
- **OPEN-TASKS.md A35 / A36** — the Bench's operating doctrine is undiscovered; transcribe
  thresholds and repair audit-credit unsigned since S71/S72.
- **SYM-003** — OPEN: the table-loop disease the Bench exists to answer; the Bench is the
  response, not a fix.
- **SYM-023, SYM-025, SYM-026, SYM-030, SYM-052** — fixed Bench-adjacent rows; read before
  changing window lifecycle, zone anchoring, run rendering, report generation, or line display.
