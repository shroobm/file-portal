---
title: Testing & CI
section: Governance
last-verified: 2026-08-23
verified-against: c56d486
sources:
  - .github/workflows/ci.yml
  - .claude/skills/muster/close.sh
  - .claude/skills/muster/selftest.sh
  - coordination/selftest.sh
  - observability/glass_detector.py
  - observability/acceptance.py
  - windows-converter/card_mutex_selftest.py
  - windows-converter/deferral_gate_selftest.py
  - windows-widget/p0-asset-ledger.test.mjs
  - windows-widget/package.json
  - linux-converter/tests/
  - linux-receiver/tests/
  - windows-widget/src-tauri/src/
  - docs/45-s105-circle-findings.md
---

**This project has two verification worlds that never touch. World A is one 99-line GitHub
Actions workflow (`wc -l .github/workflows/ci.yml` = 99) that lints and tests the three Linux
lanes and the Rust widget — Linux code last changed 2026-08-16, the widget 2026-08-20. World B is a hand-built
substrate of 15 selftest/acceptance harnesses and gate scripts totalling 3,460 lines (wc
command below) that guards the live lanes — sessions, the card mutex, the watcher gate, the
glass layer — and CI runs none of it: grepping ci.yml for `selftest`, `observability`,
`prototypes`, or `windows-converter` returns zero hits. The bridge cannot be built casually
from this machine: `command -v pytest` and `command -v ruff` both fail here, so Python-lane
verification exists only inside GitHub's runner, and close.sh's CI check structurally cannot
see the runs its own push triggers (docs/45-s105-circle-findings.md:141, F16).**


> **S108 update (2026-08-23):** windows-converter entered CI (ruff + figure_coverage_selftest, warn-only until first green is observed) with its first dependency manifest; observability/acceptance.py (41/41) runs in CI; the bench gained test_bench_page.py (19 tests); status writers gained tests (UNREAD locally, CI observes). close.sh gained DOCTOR + tripwire-census sections, warn-only this session.

## World A — `.github/workflows/ci.yml`

Triggers: push to `master` and `feat/library-pipeline`, plus pull requests (ci.yml:20-21).
The header records why the branch is listed explicitly: CI had not run on 203 consecutive
commits before S67 — every green ledger check until then was hand-run (ci.yml:12-14; SYM-018's
row says 205, counted at observation time).

| Job | Runner | Steps | Lanes covered |
|---|---|---|---|
| `python` (ci.yml:24) | ubuntu, Python 3.11 | `ruff check` + `ruff format --check` (:38-49); `pytest tests/ -v` (:52,:55) | lint: linux-receiver, linux-dashboard, linux-converter; tests: **receiver and converter only** |
| `rust` (ci.yml:57) | windows-latest, rustc pinned 1.97.1 | `cargo fmt --check` (:95), `cargo clippy --all-targets -- -D warnings` (:97), `cargo test` (:99) | windows-widget/src-tauri |

**linux-dashboard is lint-only** — no pytest step names it, and it has no test files at all
(`git ls-files | grep test` returns none under linux-dashboard/). Absent from the workflow
entirely: windows-converter, all JS, observability/, prototypes/, and every governance script.

## World B — the hand-built substrate CI never runs

All line counts from one command:
`wc -l` over the 16 files below (run 2026-08-23 at HEAD 1790554) = **3,460 total**.

| Harness | LOC | Invocation | What it proves |
|---|---|---|---|
| muster `open.sh` | 298 | `bash .claude/skills/muster/open.sh` | mechanical session open; prints values, never checkmarks (open.sh:8-12) |
| muster `close.sh` | 183 | `bash .claude/skills/muster/close.sh` | the mechanical close: diff accounting (:49), glass `--enforce` (:58), rust fmt-first (:73), CI conclusion for HEAD (:94), levers gate (:131), push state (:179-180) |
| muster `muster.sh` | 221 | `bash .claude/skills/muster/muster.sh` | memory loaded + the two clocks reconcile; exit 1 = incident (muster.sh:2-4) |
| muster `selftest.sh` | 315 | `bash .claude/skills/muster/selftest.sh` | each case VIOLATES a guarded property and asserts the guard fires; case 0 is the positive control (selftest.sh:4-14) |
| echo `sweep.sh` + `selftest.sh` | 98 + 49 | `bash .claude/skills/echo/sweep.sh` | commission-grounding sweep — values, never checkmarks (sweep.sh:4-7) — plus its tripwire |
| `coordination/selftest.sh` | 141 | `bash coordination/selftest.sh` | relay entry shape, UTC stamps, concordance amendment, ledger-row format are mechanically checkable (coordination/selftest.sh:5-8) |
| `glass_detector.py` | 519 | `python observability/glass_detector.py --since <pin> --enforce` | exit 1 on any unsigned glitch — ONLY this form's exit code carries a verdict (SYM-046; usage at glass_detector.py:24-29) |
| `observability/acceptance.py` | 350 | `python observability/acceptance.py` | pins the detector to docs/29 §7's answer key, end-to-end on the real trees (acceptance.py:2-8) |
| `backend_parity_selftest.py` | 103 | `python backend_parity_selftest.py` | parity-harness judgment functions vs banked S80-S82 pathologies; offline, no GPU (its :2-6) |
| `card_mutex_selftest.py` | 115 | see Danger below | at most ONE converter owns the card; a dead holder never deadlocks the next (its :4-6) |
| `deferral_gate_selftest.py` | 111 | see Danger below | a PDF dropped under hold defers, converts the moment the hold clears — against the REAL watcher (its :3-7) |
| `events_selftest.py` | 85 | `python events_selftest.py` | `emit()`'s torn-line healing (SYM-037); no GPU, no network (its :2-7) |
| `figure_coverage_selftest.py` | 279 | `python windows-converter/figure_coverage_selftest.py` | P-1 tripwires on hermetic synthesized PDFs; ASCII output by scar (its :3-9) |
| `room_chat_acceptance.py` | 185 | `python room_chat_acceptance.py` | the Room assistant's mutex and citation guard fire when violated (its :4-7) |
| `repair-bench/acceptance.py` | 408 | marker-env python | the REAL Bench over a sandboxed copy of the real held bundle; byte-identical, hash-proven (its :3-6) |

## Coverage by lane

| Lane | Automated tests (measured at HEAD 1790554) | In CI? |
|---|---|---|
| linux-converter | **73** = matches of `def test_` at any indent across the 7 files of `tests/` (`grep -c 'def test_' linux-converter/tests/*.py`, summed) | yes (tests + lint) |
| linux-receiver | **25** by the same command over its 3 test files (anchored `^def test_` agrees: 25) | yes (tests + lint) |
| linux-dashboard | **0** test files tracked | lint only |
| widget (Rust) | **25** `#[test]` across the 15 `src/*.rs` modules, concentrated in 4: algedonic 8, assay 9, bench 4, receipts 4 (`grep -c '#\[test\]'` per file) | yes |
| widget (JS) | **1** file: `p0-asset-ledger.test.mjs`, 46 lines (`wc -l`) | no |
| windows-converter | **0** matches of `def test_` in any tracked `.py` (control: the same command on linux-receiver returns 25); 5 selftests + 1 acceptance, hand-run only | no |
| prototypes/repair-bench | `acceptance.py`, 408 lines, hand-run with marker-env python | no |
| governance shell (muster/echo/coordination) | 3 `selftest.sh` + sweep, hand-run | no |

**The pattern trap:** anchored `^def test_` counts only 40 of linux-converter's 73, because
`test_bundle.py` (15), `test_engines.py` (9), and `test_main.py` (9) wrap their tests in
pytest classes (`grep -l '^class Test' linux-converter/tests/*.py` names exactly those three).
Any census of this lane must use the unanchored pattern or pytest's own collector.

**The Rust zero-test list:** 11 of 15 modules carry no `#[test]` — chat, config, events, line,
**main**, preflight, room, status, transfer, vault, watcher. main.rs holds all 42
`#[tauri::command]` handlers (`grep -c '#\[tauri::command\]' ...main.rs` = 42) and zero tests.

**The JS test is unwired and fragile:** it string-extracts two functions from source and
`eval()`s them (p0-asset-ledger.test.mjs:17-18); no node job exists in ci.yml (read in full —
jobs are `python` and `rust` only) and package.json's scripts are `tauri`/`dev`/`build`
(windows-widget/package.json) — nothing runs it.

## The delegation constraint nothing records

On this desktop, `command -v pytest` and `command -v ruff` both exit 1 (run 2026-08-23;
positive control: `command -v cargo` → `/c/Users/Bndit/.cargo/bin/cargo`, `command -v node` →
present). So the Python checks CI will apply exist **only inside GitHub's ubuntu runner** — an
agent on this machine cannot pre-verify Python-lane work with the same instruments, while Rust
and JS can be verified locally. The substrate already knows this: observability/acceptance.py
is stdlib-only because "no pytest on this machine, and a check you cannot run is not a check"
(acceptance.py:16-17). Four of the five windows-converter selftests are stdlib for the same
reason; `figure_coverage_selftest.py` needs pymupdf to synthesise its fixture PDFs.

## Which selftests are dangerous to run

- **`card_mutex_selftest.py`** — spawns real child processes contending on a real named OS
  mutex. It self-isolates (unique per-run name via `FP_CARD_MUTEX`, scratch pipeline via
  `FP_PIPELINE`, card_mutex_selftest.py:16-18), but an interrupted run leaves live processes.
- **`deferral_gate_selftest.py`** — runs the REAL `watch_and_convert.py` watcher for ~40 s
  (deferral_gate_selftest.py:3-9, stub converter via `FP_CONVERT`). A killed run can orphan a
  watcher over a drop folder — exactly SYM-047's specimen class (no Job Object covers a
  watcher the widget did not spawn).
- **`repair-bench/acceptance.py`** — needs the out-of-repo marker-env python and performs a
  live HTTP round through the real handler (its :3-8).

Safe by design: `events_selftest.py`, `figure_coverage_selftest.py` (hermetic),
`backend_parity_selftest.py` (offline), and the read-only shell selftests.

## What "green" cannot mean

- close.sh reads CI's conclusion for HEAD via the stored credential and prints
  "NOT a statement that CI is green" on every unreadable path (close.sh:94-126). But **docs/45
  F16**: the close lands 1-3 minutes after the last work commit, so CI is always `NO-RUN` at
  close time — the check can only catch a red that predates the session
  (docs/45-s105-circle-findings.md:141). Observe CI AFTER the push, by hand.
- `gh` is unauthenticated on this machine; this page makes no claim about CI's current colour.
- A bare `glass_detector.py` run exits 0 while listing glitches — its exit code is a printout,
  not a verdict; only `--since <pin> --enforce` gates (SYM-046).
- A green World A says nothing about the live lanes: windows-converter (55 commits, most
  recent activity) and all JS sit entirely outside it (grep evidence above).

## Lint & format configs — present vs absent

- **ruff**: configured per Linux lane — `[tool.ruff]` line-length 100, target py311 in all
  three pyprojects (linux-converter/pyproject.toml:11-13, linux-receiver:10-12,
  linux-dashboard:11-18 incl. an E402 per-file ignore for GTK) — and pinned `ruff==0.15.20`
  in both requirements-dev.txt files (line 7 of each; the float-vs-pin scar is SYM-019).
- **rustfmt + clippy**: exist only as CI steps and the rebuild ritual (ci.yml:95-97; fmt
  LEADS per the SYM-020 block, ci.yml:58-63). No `rustfmt.toml` or `clippy.toml` anywhere.
- **Absent entirely**: no eslint, prettier, or editorconfig config is tracked
  (`git ls-files | grep -iE 'eslint|prettier|rustfmt|clippy\.toml|\.editorconfig'` = 0 hits;
  positive control: the same pipe finds 3 pyproject.toml). main.js + room.js have zero
  automated checks of any kind.

## Open items

- OPEN-TASKS.md §A: **A2** (Stage 2 GO — converter tests + CI), **A26** (invert glass's
  default to `--enforce`), **A29** (put the governance suites in CI — "nothing checks the
  layer that checks everything"), **A42** (the windows-converter test decision, open since S86).
- OPEN-TASKS.md §B: **B2** (`.agents/` stale muster copy — a blind close under a green
  banner), **B4** (windows-converter ships unlinted), **B5** (nothing in the repo tests
  `bench.html`), **B10** (SYM-049's clustering fix).
- SYMPTOM-INDEX.md: **SYM-018/019/020** (CI's birth scars), **SYM-046** (the glass ritual
  form), **SYM-047** (orphan watcher — why the danger list above exists).
- docs/45 **F16** (the close-time CI blind spot); docs/32 §5 (the tripwire doctrine World B
  implements).
