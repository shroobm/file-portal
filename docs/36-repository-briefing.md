# docs/36 — The Repository Briefing

*The two-machine familiarization's deliverable: ThinkPad S79 read the tree it could see and
handed off WIP; Desktop S86 completed the checklist and merged the fork the handoff exposed;
S87 finished this into the mappings Rab commissioned, and admitted it to the assistant's
corpus. Provenance: **[TP]** = verified by ThinkPad S79 on its box (2026-08-16, fork-point
tree); **[S86]/[S87]** = observed on the Desktop (merged tree); untagged = stable across
both. Counts cite their deriving command — re-derive, never quote (SYM-039).*

## 1. What this is

A two-machine **document factory**: books (PDF/EPUB/DOCX) drop onto a Windows desktop widget,
convert to Markdown bundles on the desktop GPU (Marker) or the Linux CPU lanes (pymupdf4llm /
pandoc), pass a survival audit and optionally a local-LLM readability analyst, ship over
Tailscale to the ThinkPad, and export into a git-backed Obsidian vault (the Library). Every
stage writes receipts; the laws in docs/00–35 govern what may be claimed, projected, and
shipped. An embedded assistant (this document is part of its corpus) answers questions about
the system with citations or refuses. ~20.6k lines of source **[TP]**.

What an engineer must internalize before touching anything: (1) **projection** — surfaces
render measured values verbatim or not at all; (2) **single-writer** — every shared file has
exactly one writer; (3) **epistemic tags** — a claim is Observed/Verified/Inferred/Intended/
Unknown/Historical and consequential acts need Observed premises; (4) **adoption is Rab's
hand** — built exes are staged, never launched by the builder; (5) the GPU carries **one lab
process, ever**.

## 2. Architecture map

```
Windows desktop                              ThinkPad (Linux, always-on-ish)
┌─────────────────────────────┐              ┌──────────────────────────────┐
│ windows-widget (Tauri v2)   │  tailscale   │ linux-receiver (allocator)   │
│  Dock ⇄ Room ⇄ Wall + Bench │  ssh cat>    │  inbox/ → sorted/ + pipeline │
│  + Assistant (S85)          │ ───────────► │ linux-converter (2 watches)  │
│  spawns: watcher chain,     │              │  convert lanes + EXPORTER    │
│  bench.py, room_chat.py     │  tar stream  │  → vault.git (bare) + clone  │
│ windows-converter (GPU)     │ ───────────► │  receipts.jsonl (the seam)   │
│  convert_and_ship → bundle  │              │  systemd + watchdogs +       │
└─────────────────────────────┘              │  weekly vault fixity [TP]    │
        │ git push/pull                      └───────────┬──────────────────┘
        └────────────► GitHub (origin) ◄─────────────────┘
   one repo = code + message bus (coordination/) + the session ledger (machine LANES, S86)
```

## 3. Subsystem map

| Subsystem | Role | Key files (largest first) | Proof | State |
|---|---|---|---|---|
| windows-widget | The operator's surface: Dock/Room/Wall, Bench + Assistant windows, watcher lifecycle, transports, levers | main.rs, assay.rs, room.rs, chat.rs [S85], line.rs, algedonic.rs, bench.rs, watcher.rs, transfer.rs, receipts.rs, vault.rs, config.rs, preflight.rs · JS: main.js, room.js, styles.css | `cargo test` 23/23 [S87] · fmt+clippy clean · CI rust job | live; 42 commands (`grep -c "#\[tauri::command\]" src/*.rs`) |
| windows-converter | GPU convert lane: probe→route→Marker→audit→analyst→bundle→ship; the assistant's server | convert_and_ship.py (~1.2k lines), fidelity_audit.py, analyst.py, room_chat.py [S85], watch_and_convert.py, events.py | NO test suite, not in CI — decision before Rab [S86] | live; hardcoded `ml\` paths (see §7) |
| linux-receiver | inbox watcher → rules → sorted/ + pipeline feeds | allocator/: main.py, rules.py, status.py, sdnotify.py [TP] | pytest (receiver suite green [TP]) · CI · systemd watchdog live-proven [TP] | live |
| linux-converter | CPU convert lanes + THE EXPORTER (vault's only writer) + fixity | converter/: exporter.py, main.py, bundle.py, engines.py, degeneration.py [TP], fixity.py [TP] | pytest (converter suite green [TP]) · CI · watchdog | live |
| prototypes/repair-bench | Human repair of held bundles: crop/transcribe/collapse/AI-assist over a ledger with undo | bench.py, bench.html, acceptance.py, transcribe_worker.py | acceptance vs sandboxed real bundle; quarantined (child process only) | live tool |
| windows-remote | SSH access gates (docs/17): scoped-at-birth firewall, two-run lockout | gate1-bootstrap.ps1, gate2-lockdown.ps1 [S86 read] | transcripts + MSIX-probe refusal | done through Gate 5 in-home |
| observability/ | The glass detector: computed-but-rendered-nowhere finder, closeout-ritual mode | glass_detector.py, acceptance.py, dispositions.json | acceptance suite; runs at every close | live guard |
| .claude/skills/muster | The session-open protocol: lane-aware clocks, origin fetch, collision checks | open.sh, muster.sh, selftest.sh, SKILL.md | selftest 22/22 [S86] | live guard |
| linux-dashboard | GTK4 read-only viewer of sorted/ | main.py, window.py, scanner.py, widgets/ | skimmed [TP] | passive |

## 4. Flow maps

**A. Drop → vault (GPU lane):** ⚡ tile → `drop/` → watcher (single-flight; defers while the
assistant holds a model via `chat-hold.json` [S85]) → probe (chars/page + OCR-layer detect)
routes clean/scan → Marker (chunked >600pp clean / >400pp scan; resumable slices; stall
monitor kills >900s frozen) → survival audit → [analyst per `analyst-mode.txt`] → bundle
(manifest + fidelity block) → `anchor/` + tar-stream to ThinkPad `staging/` → exporter verdict
gate (fail-closed; sha-dedup vs bare) → vault commit + receipt → widget receipt cache → Room.

**B. Drop → vault (Linux lanes):** inbox categories → allocator rules → pipeline watches →
pymupdf4llm (Clean=KEEP_OLD auto-OCR / Scan=DROP_OLD@300dpi — never `force_ocr`, SYM-012) or
pandoc → degeneration tripwire [TP] → same staging → the same exporter serves both fronts.

**C. The gate (deferred analyst):** mode `ask` → pending card → widget routes → detached
`--resume` (stderr to a last-words file, SYM-024).

**D. Remedy loop:** assay ◎ / Room held rows → ⟳ re-convert (authors THE supersede marker) ·
⟲ re-analyze (refused under `.gpu-lock`) · ✓ bless (sha-bound, flag-only, no degeneration) ·
🔧 Bench (repairs.jsonl chokepoint, sha chain, undo; REPAIRS.md excluded from body scan,
SYM-030-desktop).

**E. The assistant:** titlebar → `chat_open` spawns room_chat.py (Job Object) → picker
(ollama manifests + HF cache, ids only) → load (`-c 16384`; fixed prompt MEASURED 13,076 tok
[S93], headroom 3,308) → answers cite docs/20/35/36 or are withheld (docs/33 §2.2) → unload
clears the hold.

**F. The session record:** muster open (per-lane clocks + origin fetch) → opening commit →
work → closeout §§ + glass detector → close commit → ledger row (separate commit, never
amend, SYM-016) → push (ahead-0 is part of the close, S86).

## 5. Interface & contract map

| Artifact | Single writer | Readers | Contract / trap | Rows |
|---|---|---|---|---|
| `events.jsonl` | windows-converter (events.py) | widget line.rs/events.rs, Room | append-only telemetry; best-effort | — |
| `receipts.jsonl` (ThinkPad) | exporter | widget receipts.rs (ssh tail → cache) | the vault's own answers; torn-line healed | SYM-037 |
| `.receipts-cache.jsonl` | widget receipts.rs | Room render | empty fetch never overwrites cache | — |
| `.gpu-lock` | watch_and_convert.py | displays only | a busy SIGNAL, not a mutex | SYM-032 |
| `chat-hold.json` | widget/room_chat | watcher (defers) | the real GPU exclusion, signed S85; stale holds reaped by pid-liveness | — |
| levers: `analyst-mode.txt` `audit-mode.txt` `chunk-batch.txt` `rules.json` | widget (validated setters) | Python, re-read per event/slice | user intent files | — |
| `pending/<id>.json` | convert_and_ship `--defer-analyst` | preflight.rs → cards | decide spawns detached resume | SYM-024 |
| `drop/.supersede/<src>.json` | assay.rs reconvert (ONLY author) | convert_and_ship (consume-once) | sha-guarded; the exporter's verdict gate closes THE SUPERSEDE GAP | — |
| bundle `manifest.json` | converter (each lane) | assay.rs, Bench, exporter | fidelity block; `clamp_name` 80 utf-8 bytes | SYM-014 |
| `config.toml` (%APPDATA%) | **Rab's hand only** — a packaged session's write lands in the MSIX mirage | widget at boot | verify from the widget's boot log, never from the writing surface | SYM-007 (4th firing S87-filed) |
| vault (bare + clone) | exporter commits; Desktop pulls | Obsidian, room metrics | ff-only, pathspec-scoped, L12 blob gate, weekly fixity [TP] | — |
| Change Ledger (CLAUDE_README) | each session's close, own MACHINE LANE | muster (per-lane parse) | append-below; row = separate commit; SHAs must be ancestors | SYM-016/028/040 |

## 6. The doctrine map (docs/ → what governs what)

| Range | Governs |
|---|---|
| 00–09 | Foundations: overview, architecture, tailnet, widget, receiver, rules, security, dev guide, roadmap, dashboard |
| 10–12 | The library pipeline: plan, GPU revamp, phase-4 rewiring |
| 13–14, 16 | Surfaces: projection law (13), remote projection (14), the Room's face (16) |
| 15 | The Survival Audit: witness, scoring, verdict policy (SIGNED) |
| 17 | Remote access runbook (gates; MSIX refusal idiom) |
| 18–19 | Levers & heartbeats; execution laws (kill trees, ssh flags, adoption, GPU serialization) |
| 20 | THE OPERATOR MANUAL (assistant corpus) |
| 21 | Session closeout contract: epistemic tags, §-structure, admission prices |
| 22–25 | HTML artifacts: engineering manual, showcases, design plan |
| 26–28 | Audits & repair: mass-audit findings, collapse (27), the repair ledger (28) |
| 29–32 | The observability complex (29), algedonic channels (30), circle findings (31), proxy substitution (32) |
| 33 | The chat surface doctrine: projection §2.1, citation-or-refusal §2.2, deferral gate §2.3 |
| 34 | The measurement language: numerator+denominator+conditions, always |
| 35 | The portal schema (assistant corpus) |
| 36 | This briefing (assistant corpus, S87) |

## 7. Risk register

| Risk | Evidence | Direction | Gate |
|---|---|---|---|
| windows-converter untested, not in CI | only substantial untested code; drives GPU + vault feed [TP] | pure-seam suite recommended [S86] | Rab's word |
| config-vs-hardcode duality (`gpu_*` vs `ml\` constants) | agree today by convention only [S86] | extend S85's FP_PIPELINE env override | next converter slice |
| `assay::bless` literal user@host (assay.rs) | ignores `linux_host`/`remote_user`; host rename breaks bless alone [TP][S86] | thread config through | next widget slice (staged-exe protection ended at adoption) |
| 3 receipt fields unrendered (`spot_check`, `degeneration_flagged`, `fixity-check`) | SYM-027's shape [TP] | glass or signed disposition | next widget slice |
| SYM-033 second-widget launch unprevented | card shows it; nothing stops it | single-instance guard | Rab's signature |
| conversation headroom 3,308 tok | fixed prompt 13,076/16,384 [S93] | trim history or raise `-c` (re-measure VRAM) | when long chats hit it |
| open symptom rows | SYM-003 (table loops), 024, 027, 032, 034, 035 | per-row | standing |

## 8. Unresolved questions (owner: Rab)

Converter test decision · `SPOT_CHECK_EVERY` 10→3–5 · this file's location if not docs/36 ·
stale-hold reap countersign · GLM bench second-reader · wrapper decision · docs/34 rule 8 ·
the ThinkPad's untracked CLAUDE.md counts (assigned back, coordination 2026-08-17T03-05).
