---
title: Side Projects & Frontier
section: System
last-verified: 2026-08-23
verified-against: 1790554
sources:
  - windows-converter/convert_and_ship.py
  - windows-converter/analyst.py
  - prototypes/README.md
  - prototypes/repair-bench/transcribe_worker.py
  - prototypes/room-chat/README.md
  - windows-widget/src-tauri/src/bench.rs
  - windows-widget/src-tauri/src/chat.rs
  - .claude/launch.json
  - scripts/windows/claude-rc.ps1
  - docs/11-gpu-pipeline-revamp.md
  - docs/17-remote-access-runbook.md
  - docs/41-conversion-completeness-plan.md
  - OPEN-TASKS.md
  - SYMPTOM-INDEX.md
  - wiki/roadmap.md
  - windows-remote/
  - linux-dashboard/
---

# Side Projects & Frontier

**If you read nothing else:** the project has one frontier commission — a custom-OCR challenger (commissioned 2026-08-23, design stage, zero code), which plugs in at exactly one seam, `_run_marker()` in `windows-converter/convert_and_ship.py`, and is gated behind a SYM-050-clean eval corpus and a wired figure-coverage baseline (roadmap C1 gates C2 gates C3). Around the core sit five quarantined prototypes (one live and widget-spawned, one graduated into the converter, three dormant), a remote-access lane complete through Gate 5 in-home, a memory library that is load-bearing infrastructure with **no off-disk copy** (register A43), and a 705-line GTK dashboard with two commits ever and **no register row deciding its fate**. Two hygiene flags found while verifying this page: `.claude/launch.json` still launches the deleted `prototypes/room-chat/chat.py`, and the only Remote Control launcher on disk is untracked.

## 1. The custom-OCR challenger — frontier, design stage

Commissioned 2026-08-23. No code exists; its register of record is roadmap catalyst **C3** (wiki/roadmap.md:32): "an alternative engine runs at the `_run_marker()` seam and is scored against C2's baseline; win or lose, deltas published."

**The seam.** `_run_marker()` — defined at windows-converter/convert_and_ship.py:636, called exactly twice: :833 (one chunked slice) and :927 (one whole book). It is the repo's only engine launch site: `grep -rln "_run_marker\|marker_single\|run_marker" --include="*.py" --include="*.rs" .` (with `src-tauri/target/` and `node_modules/` excluded) hits only `windows-converter/convert_and_ship.py`. The function already owns the hard-won survival machinery — S52 stall monitor, S48 pipe-drain and tree-kill, page-scaled timeout (its docstring, :639-645) — so a challenger replaces or augments what runs *behind* that one function and inherits all of it.

**Prerequisites, in order** (ordering law "C1 gates C2 gates C3", wiki/roadmap.md:37; "no challenger work before C2's quarantine", wiki/roadmap.md:85):

1. **Clean eval corpus** — quarantine the pre-S60 doubled-offset bundles. On the poisoned Investment Valuation bundle, 19 of 20 adjudicated "uncovered" verdicts were FALSE → SYMPTOM-INDEX.md SYM-050 (row carries the full numerator/denominator/conditions).
2. **Scored baseline** — figure_coverage wired: host decision A4 + map repair A18 (the SYM-050 repair is **not in the shipped tool**) → OPEN-TASKS.md §A; roadmap C2 (wiki/roadmap.md:31).
3. **Challenger scored** against that baseline (C3). Nothing before this step touches the pipeline.

**Standing constraints** (each verified at 1790554):

| Constraint | Proof |
|---|---|
| One process on the RTX 3080, ever — the card mutex `Local\file-portal-card`, claimed in `main()` before dispatch | windows-converter/convert_and_ship.py:203 |
| `force_ocr` at defaults is banned: 27+ min GPU-saturated with no output at 9,939 MiB peak, vs 97 s for the default run — conditions: models warm, whole-book re-OCR of 1,281 text regions, 10 GB card | docs/11-gpu-pipeline-revamp.md:86 |
| Generative super-resolution: standing ban *proposed* (docs/41-conversion-completeness-plan.md:247, P-6); decision **A7 unsigned**, register state "NOT RECORDED — zero code either way" | OPEN-TASKS.md §A A7, §E |
| `qwen3:8b` is the pinned local analyst model (`MODEL = "qwen3:8b"`); whether it remains the *only* local ollama model is (unverified) | windows-converter/analyst.py:24 |
| Zone-scope precedent: granite-docling-258M runs crop-scope only — ~2–3 s and ~650–750 MiB peak per crop PNG, in its own docling-env, never marker-env | prototypes/repair-bench/transcribe_worker.py:3-7, :26 |

**Seam:** `_run_marker()` (convert_and_ship.py:636). **Register:** wiki/roadmap.md C3; blockers A4/A18 (OPEN-TASKS.md §A) and the §E slate.

## 2. `prototypes/` — the quarantine, with liveness

The law: nothing in `prototypes/` is "imported, spawned, watched, shipped, or run by the live system" (prototypes/README.md:4, restated as rule "No pipeline coupling" at :33). The practice: the widget derives and spawns `prototypes/repair-bench/bench.py` on a real held bundle (windows-widget/src-tauri/src/bench.rs:4, path built at :86-95, spawn at :140-149). The README's own index row records the signed deviation for repair-bench ("it operates on real held bundles when a human runs it"), but the spawn *from the widget* is exactly what the top-of-file law says never happens. Both texts are load-bearing; read both before moving anything in or out.

| Prototype | Liveness | Seam into the core |
|---|---|---|
| `repair-bench` | **LIVE** — see wiki/repair-bench.md | spawned by the widget (bench.rs:149) on real held bundles; also `.claude/launch.json` `repair-bench` entry (runs `--sandbox` on held `b7b711d4d9e7234f`) |
| `control-panel` | dormant — 2 self-contained HTML mockups: `control-room/control-room.html` and `opsroom/opsroom.html` (`find prototypes/control-panel -type f`) | none — browser-open only |
| `docling-calibration` | dormant — the S71 calibration record for granite-docling-258M (prototypes/docling-calibration/README.md:1-6) | its numbers gate the Bench transcribe gesture (transcribe_worker.py:7 cites it) |
| `glm-ocr-probe` | evidence only — 5 page PNGs + 5 GLM transcripts + README, the S84 probe (`find prototypes/glm-ocr-probe -type f`) | none live; informs the GLM second-reader decision A12 |
| `room-chat` | **GRADUATED** — `chat.py` is deleted (`test -f prototypes/room-chat/chat.py` → missing; only README + `__pycache__` remain); the code lives at `windows-converter/room_chat.py`, spawned by the widget (chat.rs:69) | the quarantine's one success story: prototype → converter lane by explicit decision (commit `2bba88a` "room-chat GRADUATES"; origin record prototypes/room-chat/README.md:1-11) |

⚠ **Stale launch entry:** `.claude/launch.json:17` still points its `room-chat` configuration at `prototypes/room-chat/chat.py`, which no longer exists. The entry is dead — remove it or repoint it at `windows-converter/room_chat.py`.

**Register:** B25 (graduation debt — room-chat's llama-server grandchild spawn is un-adopted into the Job Object), B5 (nothing in the repo tests `bench.html`), B13 (bench UI buttons unwired), A35 (the Bench's operating doctrine is undiscovered) — all OPEN-TASKS.md.

## 3. Remote access — docs/17

State as the runbook itself records it: Gate 0 ✅ (docs/17-remote-access-runbook.md:169), Gate 1 ✅ (:174), Gate 2 ✅ (:206), Gate 3 ✅ (:267); Gate 4's heading carries no ✅ stamp (:315) although Gate 5's pairing + in-home stream — which requires Sunshine — is ✅ 2026-07-31 (:355). **Out-of-home is PENDING in the doc** (:355); memory records it working in practice per Rab 2026-08-17 (unverified in this repo). Gate 6 is "deferred, deliberately" (:379).

- **`windows-remote/`** — 3 files (`README.md`, `gate1-bootstrap.ps1`, `gate2-lockdown.ps1`) and **1 commit ever**: `git log --oneline -- windows-remote/` → `f6b1d5c`. A finished bootstrap artifact, not a live lane; the 2026-08-22 repo scan measured it coupled to nothing.
- **`scripts/windows/claude-rc.ps1`** — the Remote Control launcher (`claude --remote-control`, header states verified against Claude Code 2.1.239, :9). **UNTRACKED**: `git status --porcelain scripts/` → `?? scripts/windows/claude-rc.ps1`. The only phone-dispatch launcher on disk survives no clean checkout — commit it or lose it.

**Seam:** SSH over Tailscale → repo root → MUSTER (the launcher lands in the repo root by design, claude-rc.ps1:6). **Register:** no OPEN-TASKS.md row names `windows-remote` (see the gap note in §5); the remaining done-whens live in docs/17 §4 itself.

## 4. The memory library — infrastructure, out of repo

Lives at `~/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory/`, outside this repo. It IS a git work tree (`git rev-parse --is-inside-work-tree` → `true`) and `git remote -v` prints **nothing** — local-only, so a single disk loss takes the project's entire cross-session memory. That is register **A43** verbatim: "Give the memory library's git a remote, or fold it into the Drive mirror. It is local-only; a disk loss takes it" (OPEN-TASKS.md:127, source S96 §18.7).

**Seam:** every session's MUSTER open reads it before trusting anything in this repo; its inventory is docs/39-memory-library-inventory.md. **Register:** A43.

## 5. `linux-dashboard` — revive or retire

- **Size:** 705 lines over its 10 `.py` files (`find linux-dashboard -name "*.py" -not -path "*__pycache__*" | xargs wc -l`, at 1790554). The audited 2026-08-22 repo scan counted 757 LOC across all 15 tracked files, install scripts included [v].
- **History:** **2 commits ever** — `git log --oneline -- linux-dashboard/` → `efdcaea` (2026-07-05, formatting sweep) and `364daf1` (2026-06-25, birth). Nothing since.
- **CI:** lint-only — `ci.yml` lints it but runs pytest only for linux-receiver and linux-converter (`.github/workflows/ci.yml:35-55`; B4's evidence column, OPEN-TASKS.md:142, covers the lint half).
- **No register id exists for the revive-or-retire decision.** `grep -in linux OPEN-TASKS.md` hits only rows A29, B4 and D6, all mentioning the linux dirs in passing; §A–§G contain no linux-dashboard row. The nearest is **B31** (the docs/08 end-to-end test that names the dashboard). The 2026-08-22 audit flagged the same absence for `windows-remote` [v]: the register that calls itself "the roll call of what File Portal has NOT done" is silent on two whole directories.

**Seam:** GTK4 read-only viewer of the ThinkPad's `sorted/` tree (docs/09-linux-dashboard.md:10-12). **Register:** B31 (nearest); the decision row itself does not exist yet — that absence is this page's third flag.

## Open items

- OPEN-TASKS.md §A: A4, A7, A12, A18, A35, A43 · §B: B4, B5, B13, B25, B31 · §E: the P-1…P-6 slate (challenger blockers).
- SYMPTOM-INDEX.md: SYM-050 (poisoned bundles — the corpus quarantine), SYM-049 (fragmenting diagrams — baseline blind spot), SYM-047 (orphan GPU watchers — any challenger process must respect the card mutex AND the Job Object gap).
- wiki/roadmap.md: C1 → C2 → C3 ordering; risk 2 ("no challenger work before C2's quarantine").
- Flags raised by this page: dead `room-chat` entry in `.claude/launch.json:17` · untracked `scripts/windows/claude-rc.ps1` · no register row for linux-dashboard or windows-remote.
- docs/17-remote-access-runbook.md §4: Gate 5 out-of-home done-when + HDMI dummy plug; Gate 6 deferred.
