---
title: Architecture
section: System
last-verified: 2026-08-31
verified-against: "77d0361da33b496002f25967704c7cd8e0443d19"
sources: [docs/01-architecture.md, docs/13-control-room-design.md, docs/36-repository-briefing.md, windows-converter/convert_and_ship.py, windows-converter/events.py, windows-converter/watch_and_convert.py, linux-converter/converter/bundle.py, linux-converter/converter/exporter.py, linux-receiver/allocator/main.py, windows-widget/src-tauri/src/main.rs, windows-widget/src-tauri/src/vault.rs, windows-widget/src-tauri/src/events.rs, observability/schema_registry.py, observability/schemas.json, prototypes/repair-bench/bench.py, prototypes/repair-bench/bench.html, prototypes/repair-bench/ok15_evidence.py, sessions/S112-fable-sign-sheet.md, .github/workflows/ci.yml, OPEN-TASKS.md, SYMPTOM-INDEX.md]
---

# Architecture

**If you read nothing else: this codebase's skeleton is not its import graph — it is the
filesystem. The lanes (a Rust/JS desktop widget, a Python GPU converter, two Python systemd
services on the ThinkPad) couple almost exclusively through files under one hardcoded root,
`C:\Users\Bndit\ml\library`, which appears 28 times across 11 tracked source files — all
Python. Three filesystem contracts carry the load: the `events.jsonl` stream (widest reach,
generated key/variant parity enforced in CI but best-effort at runtime), the bundle/manifest
format (implemented twice, zero parity tests), and `.part-`-then-rename atomic publish (6
modules, with runtime tests). The one hard code chokepoint is `main.rs`. CI now statically
checks the signed filesystem schemas as well as building the Rust widget; it still does not run
the Windows converter or Marker.**

Era context: docs/01 covers only "the first era — file routing" (docs/01-architecture.md:3);
the library pipeline grew later. docs/36 §2–§5 is the maintained architecture/flow/contract
map (docs/36-repository-briefing.md:27,45,59,89). This page is the structural summary; descend
to those for detail.

## 1. The lane map

Measured 2026-08-23 at HEAD `1790554`. Files = `git ls-files <lane> | wc -l`. LOC counts
tracked `.py .rs .js .mjs .html .css .sh .ps1 .cmd` only (`git ls-files <lane> | grep -E
'\.(py|rs|js|mjs|html|css|sh|ps1|cmd)$' | xargs cat | wc -l`). Liveness = `git log -1
--format='%h %ad' --date=short -- <lane>`; commits = `git log --oneline -- <lane> | wc -l`.

| Lane | Stack | Files | Src LOC | Last commit | Commits |
|---|---|---|---|---|---|
| windows-widget | Rust (Tauri 2) + vanilla JS/HTML/CSS | 88 | 7,697 | 2026-08-20 `fc5d642` | 65 |
| windows-converter | Python, flat modules, no manifest | 18 | 5,641 | 2026-08-21 `3659ec7` | 55 |
| prototypes | Python + HTML/JS (quarantine) | 24 | 5,463 | 2026-08-21 `3659ec7` | 25 |
| linux-converter | Python 3.11 + systemd | 26 | 2,654 | 2026-08-16 `b7d948c` | 22 |
| .claude (skills) | Bash | 11 | 1,164 | 2026-08-21 `3659ec7` | 20 |
| observability | Python (stdlib + ast) | 4 | 869 | 2026-08-20 `deb1113` | 10 |
| linux-receiver | Python 3.11 + systemd | 16 | 782 | 2026-08-16 `9e6a380` | 14 |
| linux-dashboard | Python 3.11 + GTK4 | 15 | 737 | 2026-07-05 `efdcaea` | 2 |
| scripts | Bash/PowerShell/cmd | 5 | 173 | 2026-06-30 `a73e2ba` | 7 |
| coordination | Markdown + 1 Bash selftest | 20 | 141 | 2026-08-20 `40a643a` | 23 |
| windows-remote | PowerShell 5.1 | 3 | 118 | 2026-07-28 `f6b1d5c` | 1 |
| .github | Actions YAML (ci.yml only) | 1 | — | 2026-08-17 `7738d37` | 6 |

326 tracked files total (`git ls-files | wc -l`). Liveness is bimodal: six lanes were touched
in the 48 hours before HEAD; scripts, linux-dashboard, and windows-remote have not moved since
June–July. `docs/` alone carries 104 commits (`git log --oneline -- docs | wc -l`) — more than
any code lane. A commit date proves the code stopped changing, not that a ThinkPad service
stopped running (unverified from this repo). Hazard: 6.4 GB of build output sits at
`windows-widget/src-tauri/target/` — scan via `git ls-files`, never a directory walk.

## 2. The central fact: coupling is the filesystem, not imports

The literal path `ml\library` appears **28 times across 11 tracked source files** — every one
a `.py` file (`git ls-files '*.py' '*.rs' '*.js' '*.sh' | xargs grep -c -F 'ml\library'`,
run 2026-08-23; top: convert_and_ship.py 9, bench.py 5, analyst.py 4). The Python lanes barely
import each other: windows-converter's only intra-lane imports are `from events import emit`
(×2), `import analyst`, `import corpus_schema`, plus selftests importing their subjects
(`grep -hE '^(import|from) (analyst|events|...)' windows-converter/*.py`), and **zero** Python
files import across lane directories (`grep -rn 'linux_converter' windows-converter/*.py |
grep import` → 0). Every hop is a file appearing in a watched directory.

The root is only partially overridable: `FP_PIPELINE` is honoured by events.py:14,
backend_parity.py:264, room_chat.py:45 and watch_and_convert.py:33, and set by four
selftest/acceptance files, but `grep -c FP_PIPELINE
windows-converter/convert_and_ship.py` = 0 — its ANCHOR/PENDING/HELD constants are hardcoded
(convert_and_ship.py:83-85). The Rust/Python boundary is processes and argv, not a library
interface — e.g. the widget spawns `watch_and_convert.py` from watcher.rs and reads its
output back through files.

## 3. The three load-bearing contracts

**events.jsonl — widest reach, static parity enforced.** Writer: windows-converter/events.py,
the "control room's event stream (docs/13 keystone)" (events.py:1-3); it swallows every runtime
failure by design. At `74f0d20`, `observability/schemas.json` contains **40** source-extracted
`stage/event` variants. `observability/schema_registry.py --check` resolves required/optional
keys per variant, checks Rust/JS consumer keys against the producing variant, and byte-compares
the deterministic registry; its hermetic selftest plants writer, consumer, alias, nested-path,
and unresolved-dynamic failures. CI runs that selftest as a hard gate. This is deliberately
static: event telemetry still cannot stop a conversion, and the reader still skips malformed
lines, so event absence and runtime write failure remain operational observability problems.

**The bundle/manifest format — implemented twice, zero parity tests.** Canonical definition:
"A bundle is a folder — `<name>/<name>.md` + `assets/` + `manifest.json` — never a bare file"
(linux-converter/converter/bundle.py:1-8). The Desktop GPU lane re-implements it under the
literal comment `# ---------- bundle contract, mirrored from linux-converter/converter/
bundle.py ----------` (convert_and_ship.py:462). No test compares the two: the only tracked
test importing convert_and_ship is card_mutex_selftest.py, which exercises solely
`acquire_card_mutex`/`release_card_mutex` (card_mutex_selftest.py:59-111), and
test_bundle.py covers only the Linux copy. Every downstream stage parses this shape; the two
sources of truth are kept aligned by that one comment.

**`.part-`-then-rename atomic publish — the only tested contract.** The invariant ("assembled
in a dot-prefixed temp directory and published by atomic rename", bundle.py:1-8) is carried by
6 non-test modules across 4 lanes: convert_and_ship.py (4 sites), transfer.rs (3), bundle.py
(3), linux-converter/converter/{exporter,main}.py (2 each), linux-receiver/allocator/main.py
(2) (`git ls-files '*.py' '*.rs' '*.js' | xargs grep -c -F '.part-'`). Test coverage: 10
`.part` assertions, all in linux-converter/tests (test_main.py 5, test_bundle.py 4,
test_exporter.py 1). It is the one contract stated once, replicated deliberately, and
verified — the model the other two lack.

## 4. The chokepoint, and the false skeleton

**main.rs is the entire IPC surface.** All **42 of 42** `#[tauri::command]` definitions in
the crate live in windows-widget/src-tauri/src/main.rs (`grep -c '#\[tauri::command\]'
src-tauri/src/*.rs`: main.rs 42, every other module 0), against 35 distinct `invoke("...")`
names in the frontend (`grep -ohE 'invoke\("[a-z_]+"' src/*.js | sort -u | wc -l`). The file
is 696 lines (`wc -l`) with **0** `#[test]` (`grep -c '#\[test\]' main.rs`). Every UI→system
path flows through it.

**vault.rs looks central and is not.** It has 10 inbound `crate::vault::` references from 10
of the 15 modules — and every single one is `use crate::vault::CREATE_NO_WINDOW;` (`grep -rn
'crate::vault::' src-tauri/src/`), a Windows process-spawn constant parked there
(vault.rs:15). Its real surface is two functions: `check` (vault.rs:81) and `pull`
(vault.rs:111). Any centrality ranking by raw reference count inverts these two files.

## 5. Dependency direction: stages, files, and what CI sees

Flow is strictly downstream, Desktop → ThinkPad, each hop a file landing in a watched
directory. Every stage is real code in this repo — none is docs-only:

| Stage | Implementation | LOC (`wc -l`) |
|---|---|---|
| intake | windows-converter/watch_and_convert.py (polls drop/; spawned by watcher.rs) | 209 |
| convert | windows-converter/convert_and_ship.py (probe → route → Marker) | 1,346 |
| analyst | windows-converter/analyst.py | 502 |
| ship | ~29 lines inside convert_and_ship.py:1037-1065 — `tar \| tailscale ssh` into `.part-<sha16>` then `mv`; not a module | — |
| allocate | linux-receiver/allocator/main.py | 230 |
| export | linux-converter/converter/exporter.py — "ships converted bundles from library/staging/ into the vault repo" (exporter.py:1) | 582 |
| vault | a git repo **outside this repo**; in-repo code is the widget's read side only, vault.rs `check`/`pull` | 151 |

linux-converter/converter/main.py (349 LOC) is the ThinkPad's own CPU convert lane plus the
exporter's host process — the bundle contract is live on both sides of the mirror in §3. The
only upstream edge is the widget's read-only vault check/pull.

CI still does not execute the Windows converter or Marker, and no JS runtime suite runs there.
It does, however, parse the current Windows converter and widget consumers through the A4
schema-registry selftest. That hard gate covers `events.jsonl`, `coverage_rescore --json`, slice
`.done`, both progress files, and `conversion-ledger.jsonl`; it proves key/path parity without
importing converter dependencies or opening live pipeline files. Runtime behavior remains a
separate local/operator gate.

### The OK-15 evidence inspector is quarantine, not a fourth pipeline stage

The Repair Bench can now inspect five PDF-source signals on demand: per-page MuPDF warnings,
logical page labels, a PyMuPDF/Xpdf reading-order comparison, an all-OCG-off raster
counterfactual made from a disposable copy, and bounded `/Thumb` metadata. The collector runs
in an isolated child because MuPDF's warning buffer is process-global; one loopback-token-gated
GET and an in-process lock prevent hostile or duplicate full-book launches. The modal exposes
physical/logical page pairs, affected-page navigation, and explicit `UNREAD` reasons.

This is deliberately **not** part of the filesystem contract above. The report exists only in
Bench process memory; pixels and extracted text are not retained. It does not change the source,
Marker input, bundle/manifest, audit verdict, Visual Witness, pipeline, or vault. S112 signed
only `prototypes/repair-bench/` with zero pipeline coupling, so persisting this evidence into
conversion bundles remains a separate operator signature rather than an implied graduation.

## Open items

- OPEN-TASKS.md §B: **B4** (windows-converter outside CI's lint set), **B9** (watcher
  pid/parent file — the Job Object cannot reach a process it never spawned), **B25**
  (adopt the llama-server spawn into the Job Object).
- SYMPTOM-INDEX.md: **SYM-032** (`.gpu-lock` is write-only advice, not a lock), **SYM-046**
  (bare `glass_detector.py` exits 0 while listing glitches — the ritual form is
  `--since <pin> --enforce`), **SYM-047** (orphan watcher survives force-kill).
- docs/36 §5 (interface & contract map) and §7 (risk register) for the maintained versions
  of §3's contracts; docs/18 §2 for the modularity gate any main.rs split must pass.
