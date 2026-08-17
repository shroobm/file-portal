# docs/36 — The Repository Briefing

*The deliverable of the two-machine familiarization pass: ThinkPad S79 read the tree it could
see and handed off WIP (coordination `2026-08-16T21-51`); Desktop S86 completed the must-do
list and merged the fork the handoff itself exposed. Provenance is tagged per docs/21: facts
marked **[TP]** were `Verified`/`Observed` by ThinkPad S79 on its box (2026-08-16, fork-point
tree); **[S86]** were `Observed`/`Verified` on the Desktop tonight (2026-08-16, merged tree);
untagged structure is stable across both. Counts are commands-cited so they can be re-derived,
never trusted from this page (SYM-039).*

*Filed at docs/36 by the docs/NN precedent — Rab may direct it elsewhere; move the file, keep
the history.*

## 1. What this repository is

A two-machine **document factory**: books (PDF/EPUB/DOCX) drop onto a Windows desktop widget,
convert to Markdown bundles on the desktop GPU (Marker) or the Linux CPU lanes (pymupdf4llm /
pandoc), survive a survival audit, optionally pass a local-LLM readability analyst, ship over
Tailscale to the ThinkPad, and export into a git-backed Obsidian vault ("the Library"). Every
stage writes receipts; two humans' worth of laws (docs/00–35) govern what may be claimed,
projected, and shipped. ~20.6k lines of source **[TP]**.

## 2. Architecture map

```
Windows desktop                              ThinkPad (Linux, always-on-ish)
┌─────────────────────────────┐              ┌──────────────────────────────┐
│ windows-widget (Tauri v2)   │  tailscale   │ linux-receiver (allocator)   │
│  Dock ⇄ Room ⇄ Wall + Bench │  ssh cat>    │  inbox/ → sorted/ + pipeline │
│  42 commands [S86]          │ ───────────► │ linux-converter (2 watches)  │
│  spawns: watcher chain,     │              │  convert lanes + EXPORTER    │
│  bench.py, room_chat.py     │              │  → vault.git (bare) + clone  │
│ windows-converter (GPU)     │  tar stream  │  receipts.jsonl (seam)       │
│  convert_and_ship 1,205 ln  │ ───────────► │  systemd units + watchdogs   │
│  Marker → bundle → ship     │              │  weekly vault fixity [TP]    │
└─────────────────────────────┘              └──────────────────────────────┘
Both clones push/pull origin (GitHub) — the repo IS the message bus (coordination/)
and, since S86, the session ledger's two machine LANES live in one CLAUDE_README.
```

Entry points: widget `main.rs` (boot → config → watcher autostart); `watch_and_convert.py`
(drop poll → single-flight convert); allocator `main.py` (inotify on inbox/); converter
`main.py` (pipeline + staging watches); exporter sweep at staging arrival.

## 3. Subsystem map

### windows-widget (Rust, Tauri v2 + vanilla JS)
Modules and roles as mapped by **[TP]** §3 (all read in full there), still accurate post-merge
with these S85 additions **[S86]**: **`chat.rs`** — the embedded assistant on bench.rs's
chassis: spawns `windows-converter/room_chat.py` inside the watcher's Job Object,
`llama_server_exe` config key (empty hides the feature), `chat_stop`, death-certificate mutex
with the exit code RENDERED on reopen. Command count 38 → **42** (`grep -c
"#\[tauri::command\]" src/*.rs`), crate tests 20 → **23** (`cargo test`, tonight: 23 passed,
fmt + clippy -D warnings clean, toolchain 1.97.1).

Frontend: `main.js` (Dock; drag→portal, preflight cards, watcher lifecycle + death
certificate, vault bar, assay card, algedonic chip, Assistant panel [S85]); `room.js` (Room +
Wall surfaces). Render-body reading **[S86]** confirms the outlined model and adds the
load-bearing constraints: projection-only holds everywhere; `gatherVM` enforces the S59
no-network law (its comment carries the history); the S74 glow grammar modulates ONLY from the
signed M lever and item volume; press-on-complete diffs poll N against N−1; the S75 rule that
convert/vault rail rows must never carry a verdict (or `rl-fail` overrides `rl-pressed` by
stylesheet order); the belt invents no traffic; the drill-down pauses the Room poll; GPU
rings sample only while viewed. `styles.css` carries the `--fp-*` mass/glow token layer with
reduced-motion collapse (26 refs, `grep -c -- "--fp-"`) **[S86]**.

### windows-converter (Python, GPU lane; NOT in CI)
`convert_and_ship.py` (~1,205 lines after tonight), `fidelity_audit.py`, `analyst.py`,
`watch_and_convert.py`, `events.py`, `room_chat.py` [S85: the assistant server — model picker
over ollama manifests + HF hub cache, citation-or-refusal over docs/20+35 corpus, signed
chat-hold deferral gate consumed by the watcher]. Full mechanics in **[TP]** §3 (read in
full there) — still accurate, plus: the scan-lane `ocr_dpi` frontmatter stamp is now DERIVED
from the installed Marker (`DocumentBuilder.highres_image_dpi`, observed `int 192`) **[S86]**.
Hardcoded `C:\…\ml\` paths remain (see §6 Risks).

### linux-receiver / linux-converter (Python, systemd; in CI)
As **[TP]** §3 (read line-by-line there), plus their own S78: degeneration tripwire ported to
the linux lanes (report-mode), spot-check every 10th accepted export (`spot_check: true`
receipts), systemd watchdogs live-proven on both services, weekly vault fixity timer
(`git fsck --strict`, `fixity-check` receipts), torn-line healing in `append_receipt`
(SYM-037). Suites: receiver 28 passed / converter 73 passed **[TP]** (`pytest`, their box; CI
re-runs both on every push to the branch).

### prototypes/ (quarantined)
`repair-bench/` — human repair of held bundles. `bench.html` read in full **[S86]**: the
SYM-026 omission-run chips (◍, anchor-aware), the S79 error-structure diagnosis card rendering
signature/name/**epistemic tag**/reason/highlight/solution on the glass, three-way crop
targeting (run anchor / zone line / context), transcribe gates (numeric Jaccard · window
survival · tables), collapse preview with TTR gate, ledger undo depth surfaced, rescore
keeping MEASURED / COVERED / VAULT unblended, ◆ picker grouping held/pending/anchor/PDFs.
`bench.py` mechanics as **[TP]** §3. Pipeline never imports the bench (child process only).

### windows-remote (zero pipeline coupling)
Both ps1 bodies read **[S86]**: `gate1-bootstrap.ps1` — OpenSSH Server enabled with the
firewall scoped AT BIRTH to the tailnet CGNAT range, the auto-created allow-any rule
disabled, PS 5.1 as SSH shell, host-key fingerprints printed for pinning, and an MSIX-sandbox
probe that REFUSES to run from a packaged shell (SYM-007's law mechanized). `gate2-lockdown.ps1`
— two runs BY DESIGN (key install + proven login before password lockout), admin keys in
`administrators_authorized_keys` with ACL lock, UTF-8-no-BOM load-bearing, and
prepend-never-append into `sshd_config` (an appended directive would silently scope itself to
the trailing Match block).

## 4. Cross-system flows

1. **Drop → vault (GPU lane):** ⚡ tile → `drop/` → watcher (single-flight, `.gpu-lock`
   holder) → probe routes clean/scan → Marker (chunked >600/400 pp, resumable slices) →
   audit → [analyst] → bundle → anchor/ + tar-stream to ThinkPad staging → exporter verdict
   gate → vault commit + receipt → widget receipt cache → Room event stream.
2. **Drop → vault (Linux lanes):** inbox categories → allocator → pipeline watches →
   pymupdf4llm/pandoc → since S78 also the degeneration tripwire → same staging → same
   exporter. One exporter serves both fronts.
3. **The gate:** analyst-mode `ask` defers to a pending card; the widget routes
   (`--resume <id>`, detached, stderr to a last-words file — SYM-024).
4. **Remedy loop:** assay card / Room held rows → reconvert (supersede marker, THE one
   author) / reanalyze / bless (sha-bound, verdict-guarded) / Bench repair (chokepoint +
   repairs.jsonl + sha chain, docs/28).
5. **The assistant [S85]:** picker → `room_chat.py` loads llama-server (Job Object) → answers
   cite docs/20/docs/35 or refuse; live tree renders as surface DATA; `chat-hold.json` defers
   the watcher's converts while a model is resident (signed gate, tripwired 12/12).
6. **Session record:** MUSTER open (lane-aware clocks + origin row [S86]) → work → closeout →
   ledger row → push (enforced by the origin row after the 2026-08-16 fork).

## 5. Interfaces & invariants (the ones that bite)

- **Pipeline dir contract** (widget ⇄ Python): events.jsonl single-writer per file; levers are
  intent files (analyst-mode/audit-mode/chunk-batch/rules.json); `.gpu-lock` is a busy SIGNAL,
  not a mutex (SYM-032) — the real exclusion is the chat-hold gate + one-lab-process law.
- **Bundle anatomy:** manifest.json (fidelity block, supersede block, chunking seams),
  `clamp_name` 80 utf-8 bytes (Windows MAX_PATH; SYM-014 row corrected S86), assets by
  ABSOLUTE page (SYM-002), frontmatter mirrored across engines.
- **Transport:** tailscale ssh `mkdir -p && cat > .part-X && mv` (transfer.rs) / tar-stream
  per bundle (converter); ASCII-only local tar paths; atomic dotfile-then-rename at EVERY hop.
- **Vault:** bare + work clone, ff-only merges, pathspec-scoped commits, L12 gate (blob
  verified in bare before staging cleanup), dedup by full source sha in bare grep.
- **Projection law** (docs/13/33): surfaces render measured values verbatim or not at all;
  docs/29's glass detector runs in the closeout ritual (`--since` mode).
- **Two clocks + two lanes [S86]:** ledger machine column = lane; muster parses per-lane
  (`MUSTER_LANE`), origin fetch at open; symptom IDs one shared namespace.
- **Repo markdown is CRLF** — slice with head/tail, `sed -b`, or the Edit tool (SYM-029).

## 6. Risks / debt (current, honest)

- **windows-converter untested & not in CI** — the only substantial untested code; drives the
  GPU and the vault feed. Decision drafted for Rab (§7 of the S86 closeout): a pure-seam
  suite (probe routing, frontmatter, estimate math, supersede take/stamp, name clamps) would
  cover the logic without GPU; the Marker/ship paths stay acceptance-tested by use.
- **Config-vs-hardcode duality:** `gpu_*` config keys and `C:\…\ml\` constants agree today
  **[S86]** by convention only; extend S85's `FP_PIPELINE` env override so the widget's spawn
  passes the configured root (next converter slice).
- **`assay::bless` literal user@host** (assay.rs:375) while every other transport reads
  config — a host rename breaks bless alone, at click time. Fix = thread
  `linux_host`/`remote_user` through; deferred so the staged exe `6CA0DEF0` stays exactly
  what Rab will adopt.
- **Three new receipt fields unrendered** (`spot_check`, `degeneration_flagged`,
  `fixity-check`) — SYM-027's shape; needs glass or a signed disposition next widget slice.
- **SYM-033** two-widget prevention unbuilt (card shows it; nothing prevents it).
- **Open symptom rows:** SYM-003 (table-loop degeneration), SYM-024 (unproven resume death),
  SYM-027 (observability debt), SYM-032, SYM-033, SYM-034 (stalled generate), SYM-035
  (order-drift confound), SYM-039 (docs drift class; this file cites commands for that
  reason).
- **ThinkPad-local CLAUDE.md is untracked** — its stale counts can't be fixed from here;
  assigned back in the S86 coordination reply.

## 7. Unresolved questions (Rab's)

- Where this briefing should live if not docs/36.
- windows-converter test debt: accept / pure-seam suite / full harness.
- `SPOT_CHECK_EVERY` 10 → 3–5 at current volume (ThinkPad's number, awaiting his word).
- The standing S85 queue: stale-hold reap countersign · SYM-033 prevention · GLM bench
  second-reader · wrapper decision · docs/34 rule 8 countersign.
