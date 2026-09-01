---
title: Repair Bench
section: Product
last-verified: 2026-09-01
verified-against: "12f0ca9333d151f07107928aacab75af96791539"
sources:
  - prototypes/repair-bench/bench.py
  - prototypes/repair-bench/bench.html
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
(the other 11 are pre-audit anchors the Room skips by design, windows-widget/src-tauri/src/room.rs:76-77).
`held/` is defined as "audit-failed bundles" (windows-converter/convert_and_ship.py:85) and holds
4 bundles, 4/4 `fail`. So every audited book ends up in front of a human at the Bench: a local
web app — `bench.py`, a 2,249-line stdlib+pymupdf server, plus `bench.html`, a 2,224-line
single-file UI with one inline `<style>` and one `<script>` (`Get-Content .Count`, 2026-08-31) —
that shows the source-PDF
page beside the markdown, navigated by the audit's flagged zones, where the operator crops,
collapses, transcribes, and repairs. It lives in `prototypes/` under the quarantine convention,
yet the widget spawns it directly — a contradiction the record only half-acknowledges (below).


> **S108 update (2026-08-23):** three open defects closed this session — Ctrl+Z restored (native-undo path, `0f0e83f`; plaintext-only MODE was the killer), zone-click render is highlight-only when text is unchanged (`f9585b3`, perf log includes forced layout), and the bench gained its first 19-test stdlib harness (`abe4830`) with both S106 regressions as named fixtures. That harness now runs 81 tests; mutating routes require the launch token (`fb2a919`).

## What it is

- `prototypes/repair-bench/` — `bench.py` (2,249 lines), `bench.html` (2,224), plus the
  acceptance, glass-test, transcription, evidence, and signature artifacts. Counts:
  `Get-Content .Count`, 2026-08-31.
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

## The API surface: 26 handlers, 22 reached

Route census (probe, 2026-08-31): `rg -c 'url.path == "/api'` → **15 GET** handlers
(bench.py:2068-2126); `rg -c 'self.path == "/api'` → **11 POST** (bench.py:2150-2203);
26 handlers over 25 distinct paths (`/api/md` is served under both verbs).
The UI funnels every call through one `api(path, body)` wrapper around the file's single `fetch(`
(bench.html:636-640; `rg -c "fetch\("` = 1), and its literal-path census reaches **22**.

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

- Binds `127.0.0.1` only. Every POST is enumerated in `MUTATING_POSTS` and passes one
  constant-time `X-FP-Token` gate before dispatch; a server launched without `--token` disables
  mutations, and the widget launches with a nonempty random token (bench.py:2005-2037,
  2135-2148,2230-2237; windows-widget/src-tauri/src/bench.rs). The UI reads the launch query
  token and attaches the header (bench.html:633-640). The expensive evidence GET is gated too
  (bench.py:2088-2098).
- The stdlib wire suite refuses missing/wrong tokens, admits the right token, and proves refused
  writes leave the fixture unchanged (test_bench_page.py:184-241). This is a loopback capability,
  not user identity or remote authentication.
- No Origin/Host policy or CSP exists (`rg`, 2026-08-31). The token prevents the old blind
  cross-origin write shape because hostile pages cannot supply the custom header without a
  successful preflight; a hostile local process that learns the capability remains in scope.

## Capped evidence cannot recommend a false bless

M6-R1 makes evidence-list completeness a typed server record instead of a number inferred from
the displayed array. Runs and degeneration zones now carry `shown`, `total`, `unseen`, producer cap,
`completeness`, a label, and a remedy. A totals-bearing manifest renders `N of M`; a legacy list
below its historical cap is exact; a legacy list at cap renders `N of at least N — total UNREAD`
and names `re-convert to measure totals`; malformed or contradictory totals are also UNREAD
(`prototypes/repair-bench/bench.py:95-155,315-334`).

The completeness decision reads the manifest's **retained producer list only**. It never reads a
surface display limit. The Bench now exposes every retained omission run instead of silently
slicing the state at 40; the re-score preview likewise returns the producer-bounded zone list
instead of a second six-zone slice. Dock and Room still keep compact maps (first 40) and detail
lists (first 3), but name each truncation separately and direct the operator to the Repair Bench;
the widget backend projects the actual `runs_capped_at` / `worst_capped_at` values so its shared
count grammar can distinguish a valid `60 of 531` record from a real producer-cap contradiction
(`prototypes/repair-bench/bench.py:469-478,1852-1862`; `windows-widget/src-tauri/src/assay.rs:153-172`;
`windows-widget/src/event-vocab.js:6-32`; `windows-widget/src/main.js:862-905`).

Coverage calls its tallies `shown`, `addressed_shown`, and `open_shown`. The re-score preview now
requires clean current degeneration, zero shown-open sites, and complete evidence with zero
unseen sites before it can recommend the bless rail. Known hidden sites instead name
`full-evidence review required`; unknown legacy totals name reconversion
(`prototypes/repair-bench/bench.py:1395-1433,1809-1887`). The Bench chip, status line, and info
popover render those fields, while the shared widget helper applies the same cap-aware grammar
(`prototypes/repair-bench/bench.html:685-688,814-824,1817-1845`;
`windows-widget/src/event-vocab.js:6-20`).

The regression matrix covers future capped, future complete, legacy-at-cap, legacy-under-cap,
malformed, display-truncated, producer-cap overflow, re-score projection, and live HTTP
projection. It reproduces 25 shown of 634 runs plus 10 shown of 37 zones, with all 35 visible
sites addressed, and still requires `eligible=false`; the complete Bench suite is 81/81 and real
sandbox acceptance is 85/85 (`prototypes/repair-bench/test_bench_page.py:266-466`;
`prototypes/repair-bench/acceptance.py`).
A 2026-08-31 read-only census found 11 of 33 manifests affected (7 anchor, 4 held); none were
modified.

## Defect state at HEAD

Fixed but instructive (details live in the registers, not here): arrow keys no longer flip the
PDF page while typing, native undo survives Enter, and zone clicks move only the highlight when
text is unchanged. The source/wire suite now guards the historical line-truncation, navigation,
token, viewport, search, text-layer, table, trim, OK-15, and M6 failures (81/81); real sandbox
acceptance is 85/85. The remaining test limit is honest: no tracked harness loads the whole DOM
in a browser, so pixel/layout behavior still needs a browser smoke.

## Open items

- **docs/50 AUD-1 / M6-R2** — the fail-closed decision is built; reviewing the hidden sites
  still needs separately signed pageable evidence or identity-bound uncapped recomputation.
- **OPEN-TASKS.md B13** — `/api/triage`, `/api/report`, `/api/ledger` built, proven, unreachable
  from the UI.
- **OPEN-TASKS.md A35 / A36** — the Bench's operating doctrine is undiscovered; transcribe
  thresholds and repair audit-credit unsigned since S71/S72.
- **SYM-003** — OPEN: the table-loop disease the Bench exists to answer; the Bench is the
  response, not a fix.
- **SYM-023, SYM-025, SYM-026, SYM-030, SYM-052** — fixed Bench-adjacent rows; read before
  changing window lifecycle, zone anchoring, run rendering, report generation, or line display.
