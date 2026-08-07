# 20 — The File Portal Manual

*The complete textbook: Part I is the user's manual — every surface, every feature, every
lever, in plain language. Part II is the developer's reference — what code exists, what
packages it stands on, where everything comes from, what each piece does, and what each
machine should be doing at any moment. Written S65 (2026-08-07) at Rab's request. When this
manual and reality disagree, reality wins — measure, then fix the manual. Deeper design
records: docs/13 (control-room laws), docs/15 (Survival Audit), docs/16 (Room), docs/17
(remote access), docs/18 (levers & heartbeats), docs/19 (execution plan).*

---

# PART I — THE USER'S MANUAL

## 1. What File Portal is

File Portal is a **two-machine document factory** that turns PDFs into a clean, audited,
version-controlled Obsidian library:

```
 YOU drop a PDF on the widget (Desktop)
   ▸ Marker converts it on the RTX 3080 (GPU, slices for long books)
   ▸ the Survival Audit scores the conversion honestly
   ▸ (optionally) a local AI analyst pass improves readability
   ▸ the bundle ships over Tailscale to the ThinkPad
   ▸ the exporter commits it into the vault git repo (dedup'd, verified)
   ▸ the Library clone on the Desktop pulls it — it appears in Obsidian/ZenNotes
```

Its soul is a refusal to lie: every stage measures, every verdict is recorded, guards
fail closed, and **nothing lands in the vault unproven**. A parked bundle or an honest
"the audit said no" is a success, not a failure.

The widget is the factory's **control room**. It has four surfaces:
**Dock · Room · Wall · Bench** (titlebar buttons).

## 2. The Dock — the everyday face

The compact floating widget. Top to bottom:

- **Titlebar**: `Dock Room Wall Bench` surface switch · ◆ opens Obsidian · ◈ opens
  ZenNotes · **⏻ the watcher dot** (green = the conveyor is watching `drop/`; grey =
  paused; **terracotta = it DIED** — hover for the death certificate, click to restart) ·
  minimize.
- **The tiles** — drag-and-drop targets. Four send files to the ThinkPad's sorter
  (*Documents, Photos, Code, Archive*); three feed the conversion pipeline:
  **🔁 To Vault** (ThinkPad's pymupdf4llm lane, legacy), **🔍 Force OCR → Vault**
  (ThinkPad, forced OCR), and **⚡ GPU → Vault** — *the main lane*: the Desktop GPU
  converts it with Marker. The ⚡ tile is a **drag target, not a switch**.
- **The line** — one glance at the whole factory:
  `▚ drop · ⚙ convert · ✳ gate · ◎ assay · ⇈ ship · ▤ library`.
  ▚ counts waiting PDFs (`+N✗` = failed tray, click to open). ⚙ shows the converting
  book + honest ETA. ✳ is the **analyst gate** (click to cycle its mode — see §6). ◎ is
  the audit verdict dot (click opens the evidence card). ⇈ click = the last ship receipt.
- **The assay card** (appears on flag/fail/held): the verdict, a damage map of the book,
  the worst evidence verbatim, the `report ⇄ enforce` lever, and per-bundle remedies —
  **⟳ re-convert · ⟲ re-analyze · ✓ bless · 🔧 open on the Repair Bench** — on the card
  AND on every held row.
- **Pre-flight cards** (when the gate is `ask`): a converted book waits for your routing
  call — 🔒 Local analyst / ☁ Flash / Ship as-is — with measured ETAs and a
  remember-my-choice rule for big documents.
- **The vault bar**: glows terracotta when the ThinkPad has pushed notes you don't have —
  one click pulls them into the Library.
- **The algedonic chip** (terracotta, appears only when pain is unacknowledged past M
  minutes): click it to jump to the Room and ⚑ ack.
- Status line + shift line (today's totals; a live ticker while the machine works).

## 3. The Room — the operations dashboard

Click **Room**. Everything here is a *projection* — it reads the pipeline's own files and
never invents state.

- **Header**: system verdict (viable / attention / paused), watcher, GPU, clock, **◐ theme**
  (persists).
- **⚑ ALGEDONIC banner** (only when unacknowledged pain is older than M minutes): each
  alert with its age and an **⚑ ack** button. Acking silences *that occurrence* — a new
  one re-alarms. The M selector (15m/30m/1h/4h) is provisional until Rab signs it.
- **The station rail** — the six stations; **click any station to drill into its real
  on-disk tree** (bundles, manifests, zones, sizes — live, 4 s re-read).
- **The belt** — ambient canvas: chips = real in-flight work.
- **KPI band + GPU strip** — throughput, median s/page, VRAM/util/temp sparklines
  (fixed scales; clay under pressure).
- **⚙ Convert station** — live Marker stage (`Recognizing Text · 2/7`), the bar running
  against **the ledger's promise** when one exists (`promise: 33m left · 1.69 s-pp
  (similar ×1)`), liveness age (clay past 120 s — you see a freeze ~13 min before the
  killer acts), and the policy row with the **slice batch lever: 8 | 16 | 32** (live
  buttons; re-read per slice; 8 = VRAM headroom on long clean books).
- **≡ Queue** — the waiting PDFs in the watcher's true order (read-only; reordering
  awaits a signed watcher contract), plus the converting item's promise.
- **◎ Survival Audit panel** — verdict, damage map, held queue with the full remedy row
  (⟳ ⟲ ✓ 🔧) per bundle.
- **Event stream** — the desktop's `events.jsonl` merged at render time with the
  **vault's own receipts** from the ThinkPad (`exported / skip / supersede-held /
  blessed…`) — the story no longer ends at "shipped".

## 4. The Wall — across the room

Click **Wall**: giant verdict, six station dots, three hero numbers, and the ⚑ flag when
anything is unacknowledged. Readable from a couch.

## 5. The Repair Bench — the human is the vision model

Click **Bench** (opens on the newest held bundle) or **🔧 on any held row** (opens on that
bundle). A dedicated window appears: the bench server is spawned and supervised by the
widget and dies with it. You can also run it by hand on **any folder containing one .md**
(anchor copies, pending bundles, mid-conversions — the folder is all that matters):

```
C:\Users\Bndit\ml\marker-env\Scripts\python.exe  ^
  C:\Users\Bndit\Projects\file-portal\prototypes\repair-bench\bench.py  "<FOLDER>"  --port 7077
```

`--sandbox` repairs a copy under `.sandbox/` — trial mode. Without a `manifest.json` the
bench runs in *folder mode*: no audit zones, everything else works, and a minimal manifest
is created on your first repair so provenance is never unrecorded.

**Anatomy**: left sidebar (**Contents** = the PDF's own outline · **Search** = full-text
with highlighted hits, on books with a text layer · **Pages** = thumbnail rail); middle =
the **source page** (page box, ◂ ▸, zoom, **⌖ locate**); right = the **markdown at the
zone** (the ▶ line is the wreck; your repairs show green) with the **AI bar** above it.

**The repair loop** (the ☰ guide coaches you through it live; ? opens the full help):

1. **Pick a zone** — the chips are the audit's flagged wreck sites; ✓ = repaired.
2. **Find the true page** — ⌖ locates it from the prose around the wreck on text-layer
   books (evidence, with a confidence); raw scans get an honest `~ratio` guess you refine
   with ◂ ▸. *(Live case: Valentine's first zone guessed ~p120; the real exhibit was
   p234. The human out-ranged the machine by 114 pages — that's why you're here.)*
3. **Capture the truth** — drag a rectangle → **✂ insert crop at zone**, or Ctrl+V any
   screenshot. It lands in `assets/_repair_pN_k.png`, embedded `![[…]]` at the zone,
   provenance appended to `manifest["repairs"]`.
4. **Fix the text** — type into the AI bar (*"replace this broken table with a clean
   markdown table"*) → **✦ fix**. Local qwen3 rewrites ONLY the visible passage; every
   image embed is fenced into an opaque token first and a damaged fence means the change
   is **refused**; "nothing to fix" is honest and free. **↩ undo AI** restores the file
   byte-for-byte, twenty deep. Or **✎ edit** by hand. *Fixing the text is what clears the
   degeneration flag; the image documents the truth either way.*
5. **◎ re-score preview** — re-runs the degeneration tripwire on the current text and
   answers honestly. It writes nothing; whether repairs earn audit credit is Rab's
   unsigned policy.

**Safety net**: `.md.bench-bak` before the first write of a session; append-only
provenance; the AI undo stack; and since S65 the enforce-park can never overwrite a
repairs-bearing held bundle (an incoming park lands *beside* it, timestamped).

## 6. The levers — every one, and the file behind it

| Lever | Where | Values | File (pipeline root) | Meaning |
|---|---|---|---|---|
| Analyst gate | Dock ✳ click | ask / auto-🔒 / auto-☁ / off | `analyst-mode.txt` | Route converted books to the analyst, ask per book, or skip. **Gemini (☁) is OFF by standing rule** until Rab re-opens it. |
| Audit lever | Assay card / Room | report ⇄ enforce | `audit-mode.txt` | `report`: fails ship with the verdict filed. `enforce`: a fail parks in `held/` — nothing ships unproven. **Standing at `enforce` since S61.** |
| Slice batch | Room policy row | 8 / 16 / 32 | `chunk-batch.txt` | Marker's recognition batch per 200-page slice; re-read every slice; 8 buys VRAM headroom (a long clean book peaked 9.8/10.2 GB at 16). |
| Algedonic M | Room banner | 15m/30m/1h/4h | `algedonic-minutes.txt` | Unacked pain older than M escalates. Provisional. |
| Big-doc rule | Pre-flight card checkbox | on/off | `rules.json` | Auto-route documents over ~18 chunks to the local analyst. |
| Watcher | Titlebar ⏻ | run/pause | (process) | Pause = graceful; an in-flight convert finishes. |

## 7. The life of a book (what happens to your PDF)

1. **Drop** on ⚡ → lands in `drop/`; the watcher (5 s poll) picks it up.
2. **Probe** — pymupdf measures chars/page + page count (*never* file metadata) and
   routes: clean lane / scan lane (OCR-layer detection included).
3. **Convert** — Marker on the GPU. Books over the lane threshold (clean > 600 pp, scan >
   400 pp) go in **200-page resumable slices**; a killed slice costs one slice. Progress,
   liveness, and the ledger's **promise** are all on the glass; a stall is killed early at
   15 min frozen with a death certificate. The estimate is recorded next to the actual,
   forever.
4. **Audit (convert phase)** — the Survival Audit scores survival against a witness and
   trips on **degeneration** (OCR loops — the Beer disease). Verdict: pass / flag / fail.
5. **Gate** — per the ✳ mode: the analyst runs (local qwen3, link-fenced, chunk-resume
   journal — a power cut costs ~16 s, not an afternoon), or the book ships as-is, or a
   card asks you.
6. **Audit (analyst phase)** — near-exact discipline; omission fails honestly.
7. **Enforce gate** — a `fail` under `enforce` parks in `held/` (repairs-safe since S65).
8. **Ship** — tar over Tailscale into ThinkPad staging (atomic rename).
9. **Export** — the ThinkPad commits into the bare vault repo: dedup by source SHA,
   `Inbox/<slug>--<sha8>/`, push + blob-verify, then staging is deleted. A re-convert
   replaces a vaulted note ONLY with a `supersede` intent AND a `pass` (or Rab's ✓ bless
   on a flag). Every outcome is filed as a **receipt** the Room shows.
10. **Library** — the vault bar glows; one click pulls; the book is in Obsidian.

## 8. Remedies, refusals, and what to do when

- **Held bundle (◎ terracotta)** → open the evidence. Options per row: **⟳ re-convert**
  (full GPU redo; carries a supersede intent), **⟲ re-analyze** (analyst-only, Marker
  never runs; only for pre-analyst bundles — feeding an analyst its own output is
  refused), **✓ bless** (your human override for `flag` verdicts — sha-bound, exporter
  honors it on its next sweep), **🔧 Repair Bench** (fix it with your hands).
- **Watcher died (⏻ terracotta)** → hover for the exit code; last words are in
  `watcher-stderr.log`; click to restart.
- **Vault host unreachable** → nothing is lost, ever: ships fail honestly, bundles stay
  in `pending/` with a `failed` card; retry ships as-is (`--backend none` — never re-run
  an analyst on its own output).
- **⚑ algedonic banner lit** → read it, fix or accept, then ⚑ ack. Acks are per
  occurrence and logged.
- **A page/figure is wrong in a vaulted note** → that's a Repair Bench + supersede
  conversation; the vaulted original is never edited by machines in place.

---

# PART II — DEVELOPER NOTES

## 9. The repo, and where everything comes from

**Repo**: `github.com/shroobm/file-portal`, branch `feat/library-pipeline` (PRs to
`master`). Desktop checkout `C:\Users\Bndit\Projects\file-portal`; ThinkPad
`~/file-portal-src`. The brain is `CLAUDE_README.md` (session protocol + Change Ledger —
every session opens with a plan commit and closes with a ledger row). `CHANGELOG.md`
narrates every source change. Design docs live in `docs/`.

```
windows-widget/          the Tauri control room (Rust + framework-free JS)
  src-tauri/src/         main.rs config.rs transfer.rs status.rs vault.rs watcher.rs
                         preflight.rs events.rs line.rs assay.rs room.rs receipts.rs
                         algedonic.rs bench.rs
  src/                   index.html main.js room.js styles.css   (NO framework, NO bundler)
windows-converter/       the GPU lane (Python, runs FROM THE REPO — no install step)
  convert_and_ship.py    probe → route → Marker → audit → gate → ship (the heart)
  analyst.py             link-fenced qwen3 readability pass + chunk-resume journal
  fidelity_audit.py      the Survival Audit (docs/15)
  watch_and_convert.py   the conveyor watcher (5 s poll on drop/)
linux-receiver/          ThinkPad sorter (allocator; the four plain tiles land here)
linux-converter/         ThinkPad service: legacy pymupdf4llm lane + THE EXPORTER
  converter/exporter.py  staging → vault git commits (dedup, supersede, bless, receipts)
prototypes/              QUARANTINED experiments (nothing imports them)
  repair-bench/          bench.py + bench.html + acceptance.py  (spawned by bench.rs)
coordination/messages/   cross-machine work orders (committed markdown)
```

## 10. Languages, packages, provenance

| Layer | Tech | Version | Source | Why |
|---|---|---|---|---|
| Widget shell | Rust + Tauri | 1.97.1 / tauri 2 | rustup, crates.io | native windows, tiny footprint, Job Objects |
| Rust deps | serde, serde_json, toml, dirs, windows-sys 0.61 | lock-pinned | crates.io | config, projections, kill-on-close job |
| Widget UI | vanilla ES modules | — | this repo only | no bundler, no framework — the webview runs the files as written |
| JS tooling | @tauri-apps/cli, node | Node 24 LTS | npm | build only |
| Converter env | CPython | 3.12.13 | uv-managed (`%APPDATA%\uv\python`) | marker-env's base |
| Conversion | marker-pdf (+surya) | 1.10.2 / 0.17.1 | PyPI | the stamping press; switches only, not promptable |
| GPU stack | torch | 2.11.0+cu128 | PyPI (CUDA wheel) | RTX 3080 10 GB |
| PDF probe/raster | pymupdf | current | PyPI | probe(), witnesses, bench rasters/TOC/search |
| Audit fuzz | rapidfuzz | current | PyPI | near-exact analyst matching |
| Local LLM | Ollama + qwen3:8b | 0.32.1 | ollama.com / ollama library | analyst + bench AI; `keep_alive:0`, `think:false` |
| Marker models | datalab weights (~2.4 GB) | pinned by marker | `%LOCALAPPDATA%\datalab\datalab\Cache` | layout/recognition |
| Bench server | Python **stdlib** + pymupdf | — | this repo | zero new deps, quarantined |
| ThinkPad lane | pymupdf4llm | 1.28.0 | PyPI | legacy converter (ThinkPad pin) |
| Transport | Tailscale (+ its ssh) | node `desktop-bndit` / `archlinux` | tailscale.com | all cross-machine traffic |
| Services | systemd --user | — | Arch | `file-portal-converter` on the ThinkPad |

**Version truth lives in**: `Cargo.lock`, `package-lock.json`, marker-env's pip freeze,
and the manifests each conversion stamps (`converter_version`, `marker_version`).

## 11. What each module does (one line each, then the load-bearing details)

**Rust (`src-tauri/src/`)** — every module is either a *projection* (reads pipeline
truth) or a *lever/spawner* (writes only backend-owned files or supervises children):

- `main.rs` — command registry + env hydration from the registry (stale-Explorer-env fix).
- `config.rs` — `%APPDATA%\file-portal\config.toml`; serde defaults; empty key = feature hidden.
- `transfer.rs` / `status.rs` — the four plain tiles → ThinkPad (atomic `.part-` + `mv`), allocator status feed.
- `watcher.rs` — spawns/supervises the conveyor; **kill-on-close Job Object** (any widget
  exit kills the whole tree — S37); death certificates with remembered exit codes;
  stderr → `watcher-stderr.log` (nothing dies unheard).
- `preflight.rs` — pending cards list + detached `--resume` spawns.
- `line.rs` — the line projection (drop/convert/queue/estimate/liveness/chunk-batch) +
  the analyst-mode, rules, and chunk-batch levers.
- `events.rs` — today's shift totals + event tail.
- `assay.rs` — audit projection, audit lever, ⟳ supersede-intent author, ⟲ spawn,
  ✓ bless (validated against the EVENT stream; scp with BatchMode).
- `receipts.rs` — fetches the ThinkPad's `receipts.jsonl` tail on the Dock's 45 s poll
  into a local cache; the Room reads only the cache (**the Room's loop may not touch the
  network** — S59 law).
- `room.rs` — Room metrics, GPU probe, drill-down trees.
- `algedonic.rs` — pain derivation (events + receipts), resolution suppression, ⚑ ack
  ledger, M lever. Pure local reads.
- `bench.rs` — resolves a held bundle, spawns the quarantined bench server (free-port
  scan 7077–7096, last-words `bench-stderr.log`, job-adopted), opens/renavigates the
  dedicated window. The prototype is never imported.

**Python (Desktop, `windows-converter/`)**:

- `watch_and_convert.py` — the conveyor: 5 s poll on `drop/`, `.gpu-lock` while
  converting, `done/`/`failed/` trays, outer timeout backstop.
- `convert_and_ship.py` — probe (pymupdf; render-mode-3 OCR detection) → route →
  `_run_marker()` (ONE monitored implementation: draining reader, utf-8 pipes, kill-early
  stall detector at 900 s frozen, tree-kill, page-scaled timeout) → 200-pp slice
  chunking with resume + absolute-page assets → bundle + manifest → Survival Audit →
  defer/analyst → `_enforce_hold` (repairs-safe) → `ship` (tar over tailscale ssh,
  atomic) → conversion ledger + `estimate_from_ledger` promises.
- `analyst.py` — link-fence (⟦IMG-n⟧ multiset law), chunking, qwen3 via Ollama
  (`think:false`, `keep_alive:0`), **chunk-resume journal** (fsync'd per chunk;
  failed chunks deliberately not journalled), heartbeat file.
- `fidelity_audit.py` — window-survival vs an ephemeral witness; degeneration tripwires
  (zlib + trigram + contiguous-run); per-stage strictness; verdict = degeneration OR
  analyst loss only (Rab-signed, docs/15 §12).

**Python (ThinkPad, `linux-converter/`)**: the exporter — staging sweep, dedup
(`git grep` the source SHA in the bare repo), create `Inbox/<slug>--<sha8>/`, supersede
replace-in-place (old note name kept so `[[wikilinks]]` survive; **pass, or flag with
bless**, else `EXPORT-SUPERSEDE-HELD` with staging kept), L12 gate (push + `cat-file -e`
every blob), one receipt line per outcome.

**Prototypes (`prototypes/repair-bench/`)**: `bench.py` (stdlib HTTP server: state, page
rasters, TOC, search over a normalized de-hyphenated text index, ⌖ locate by prose-needle
voting, crop/paste repairs with server-tracked line offsets, fenced AI assist + snapshot
undo, re-score preview) + `bench.html` (the Apple-skinned UI + coach + help) +
`acceptance.py` (26 checks on a sandbox of the real Valentine, baseline-aware).

## 12. The single-writer files (the law: one writer each, projections read)

| File (in `C:\Users\Bndit\ml\library\`) | Writer | Read by |
|---|---|---|
| `events.jsonl` | Python (emit) | widget projections, algedonic |
| `conversion-ledger.jsonl` | convert_and_ship | estimator |
| `.gpu-lock`, `.convert-progress.json`, `.convert-estimate.json` | converter | line.rs |
| `.analyst-progress.json`, `.analyst-work/<key>/chunks.jsonl` | analyst | line.rs / analyst resume |
| `analyst-mode.txt`, `audit-mode.txt`, `chunk-batch.txt`, `rules.json`, `algedonic-minutes.txt` | **widget (user intent)** | Python re-reads per use |
| `algedonic-acks.jsonl` | widget ⚑ | algedonic.rs |
| `.receipts-cache.jsonl` | widget (fetch) | Room render |
| `drop/.supersede/<src>.json` | assay.rs ⟳ (consume-once) | convert_and_ship |
| `watcher.log`, `watcher-stderr.log`, `bench-stderr.log`, `widget-boot.log` | their processes | humans + diagnostics |
| `anchor/ pending/ held/ drop/(done,failed)` | converter (held/ also: Repair Bench) | projections, bench |
| ThinkPad `~/file-portal/receipts.jsonl` | exporter | widget fetch |

Marker files are **consume-once**; a lost intent is the safe direction. Manifests carry
`fidelity`, `chunking` (seams), `supersede`, `repairs`, `blessed` — the book's whole
biography travels with it.

## 13. What each device should be doing

**Desktop (`bndit@DESKTOP-BNDIT`, Win10, RTX 3080 10 GB, 16 GB RAM)**
- At rest: widget ~3 MB / no GPU; watcher polling; Ollama idle (~600 MiB VRAM baseline
  only while loaded — `keep_alive:0` returns it); nothing listening but sshd
  (tailnet-scoped, key-only) and Sunshine (docs/17).
- Converting: ONE Marker tree under `.gpu-lock` — 4–8 GB VRAM typical, long clean books
  to **9.8/10.2 GB at batch 16** (use 8 for headroom). **Never convert while the little
  brother games** — the seat is his (law 8).
- Analyst running: qwen3 cycles VRAM per chunk; heartbeat file beats every chunk.
- Bench open: one `bench.py` per patient on 7077–7096, job-owned by the widget.
- Installed exe: `%LOCALAPPDATA%\File Portal\file-portal-widget.exe` — **adopted only by
  Rab's hands** (build → SHA-8 → his Copy-Item; the MSIX ghost laws, docs/19 §0.3).

**ThinkPad (`rab@archlinux`, Arch, tailnet 100.107.238.61)**
- Always: `file-portal-converter` (systemd --user) watching `~/file-portal/library/
  staging/`; the allocator for the plain tiles; the bare vault `~/file-portal/vault.git`.
- On service restart: a startup sweep re-processes staging (this is how blesses and
  stuck bundles get their next chance).
- Writes one receipt line per export outcome; never edits an existing note except
  through the signed supersede path.
- Deploy = `cd ~/file-portal-src && git pull && systemctl --user restart
  file-portal-converter` (Rab runs it).

**Between them**: everything rides Tailscale (`tailscale ssh` — the known_hosts-proof
transport; plain programmatic ssh/scp always gets `-o BatchMode=yes -o
StrictHostKeyChecking=accept-new -o ConnectTimeout=10`).

## 14. Gates, rituals, invariants (the short list that keeps it honest)

1. **MUSTER** at session start/close: memory loaded + the two clocks agree (git ledger ↔
   TIME-STATE ↔ cookie tally).
2. **The projection law**: the widget reads; Python owns pipeline truth; levers write
   only backend-owned files.
3. **Widget gates**: `cargo clippy --all-targets -- -D warnings` · `node --check` ·
   `cargo test` · `npm run build` → hash → **Rab adopts**.
4. **Fail-safe rule (S42)**: progress/estimate/provenance bookkeeping may never change a
   conversion's outcome.
5. **Kill process TREES** (`taskkill /t` / `_kill_tree`) — single-pid kills orphan the
   real python.
6. **The link-fence is non-negotiable** wherever an LLM touches markdown.
7. **A stub that shares the code's assumptions proves nothing** — acceptance runs use the
   real artifact (the real book, the real exporter, the real bundle).
8. **Human work is sacred**: held bundles with repairs are never overwritten; `.bench-bak`
   precedes first writes; undo is byte-identical; adoption and vault writes belong to
   human hands.
