---
title: Linux Pipeline & Vault
section: Pipeline
last-verified: 2026-08-23
verified-against: "1790554"
sources:
  - windows-widget/src-tauri/src/transfer.rs
  - windows-converter/convert_and_ship.py
  - windows-converter/watch_and_convert.py
  - linux-receiver/allocator/main.py
  - linux-receiver/config/rules.toml
  - linux-converter/converter/main.py
  - linux-converter/converter/engines.py
  - linux-converter/converter/exporter.py
  - linux-converter/converter/fixity.py
  - linux-receiver/systemd/
  - linux-converter/systemd/
  - .github/workflows/ci.yml
  - docs/06-security-model.md
  - docs/12-phase4-rewiring.md
  - docs/15-survival-audit.md
  - docs/41-conversion-completeness-plan.md
---

# Linux Pipeline & Vault

**The ThinkPad is the receiving half of the factory: everything arrives over Tailscale SSH, is sorted by an allocator whose `rules.toml` is the write boundary, optionally converted by a CPU fallback lane, and committed into the vault by `exporter.py` — the vault's ONLY writer (582 LOC, `wc -l`), which is also the best-tested module in the repo (`tests/test_exporter.py`, 430 LOC). Two facts carry the page: in the library lane the source PDF never reaches the ThinkPad — only the finished bundle ships (docs/41:593) — and the three systemd `.service` units carry zero sandboxing/hardening directives (probe below, with controls). CI covers these Linux lanes (ruff + pytest); the live desktop GPU convert lane has no CI at all.**

## 1. Transport — how things move

Two distinct hops, both riding `tailscale ssh` because plain `scp`/`ssh` fail host-key
verification against Tailscale's managed keys (transfer.rs:3-6):

| Hop | Sender | Mechanism | Lands at |
|---|---|---|---|
| Portal file | widget, `transfer.rs:78` | stream file bytes into remote `cat > .part-<name>`, then `mv` (transfer.rs:117-128) | `~/file-portal/inbox/<category>/` (config.rs:58 default) |
| Library bundle | `convert_and_ship.py:1037 ship()` | `tar -cf - \| tailscale ssh` into `.part-<sha16>` dir, `tar -xf`, then `mv` (convert_and_ship.py:1040-1044) | `~/file-portal/library/staging/` (convert_and_ship.py:88) — bypasses inbox/ and the allocator entirely |

**Invariants** (every hop, both directions):

- **Dotfile-then-rename.** Writes go to a `.part-` dotfile/dir, published by atomic
  rename; receivers skip dotfiles and treat the rename (`on_moved`) as "a full file has
  arrived" (transfer.rs:117-121; allocator/main.py:37-43, :81-82).
- **The `convert-gpu` category never leaves the machine** — it copies into the Desktop
  watcher's own drop folder with the same dotfile invariant (transfer.rs:85-112).
- **Streaming, not buffering**: transfer.rs streams from disk into the remote stdin so a
  large drop never loads fully into RAM (transfer.rs:150-157).

**Offline recovery** (ThinkPad down mid-ship):

- `ship()` kills the wedged local `tar` when ssh dies, so tar's timeout never masks the
  real network error — "Learned live: an offline ThinkPad surfaced as 'tar timed out'"
  (convert_and_ship.py:1053-1057).
- The conversion is never lost: an unconditional anchor copy lands on the Desktop
  *before* the ship branch (convert_and_ship.py:1331-1332), and the failed PDF moves to
  `drop/failed/` (watch_and_convert.py:175-179). Nothing auto-re-ships; recovery is manual.
- Bundles that landed while the service was down are picked up by the exporter's startup
  sweep — inotify has no replay (exporter.py:145-149).

## 2. linux-receiver — the allocator

`allocator/main.py` (230 LOC) watches `inbox/<category>/` recursively and allocates
completed files per `config/rules.toml`, reloaded on every event (main.py:84). Completion
signals: `on_moved` (transport rename), `on_closed` (inotify `IN_CLOSE_WRITE` for
in-place writes), and an `on_created` + size-stability fallback only on non-inotify
platforms (main.py:37-60, :156-166).

**`rules.toml` is the security boundary.** docs/06:24-27: the allocator "does not accept
arbitrary destination paths from the Windows side — the widget only ever sends a
*category* name, and the category → directory mapping lives solely in `rules.toml` on the
Linux box. A compromised or buggy widget cannot direct a write outside that tree."
Oversized files (> `max_file_size_mb`, default 2048 — rules.toml:4) are quarantined
outside the watched tree (main.py:88-89, :111-117). The `convert` / `convert-scan`
categories route into the pipeline's "process mouths", not under `sorted/`
(rules.toml:11-19).

## 3. linux-converter — the CPU fallback lane

Since the Phase-4 rewire, the primary convert lane is the Desktop GPU (Marker); the
ThinkPad service "becomes the fallback lane (a file dropped on the old Convert tiles
still works) and the enrichment host" (docs/12:11). It watches
`pipeline/convert-inbox` (clean) and `pipeline/convert-scan-inbox` (scan)
(converter/main.py:1, :40); a sub-threshold text layer reroutes clean → scan; scan is
terminal — "no cycle is possible by construction" (main.py:4-8).

**Engines** (`converter/engines.py`, first-match on extension, engines.py:33-36):
PyMuPDF4LLM for `.pdf`/`.epub`, Pandoc for `.docx`. Two load-bearing subtleties:

- `import pymupdf.layout` MUST precede `import pymupdf4llm`, or auto-OCR silently never
  fires on image-only pages (engines.py:7-12).
- **OCRMode semantics — the name `force_ocr` lies.** OCR is need-based in every mode; the
  modes control *prior* OCR spans. Clean = `SELECT_KEEP_OLD` (trust existing text);
  Scan = `FORCE_DROP_OLD` + `ocr_dpi` (discard prior OCR, redo it, raise if no OCR engine
  is available). The plan doc's `force_ocr=True` "maps to FORCE_KEEP_OLD and would KEEP a
  bad prior OCR layer" (engines.py:73-81, kwargs at :92-99). Scan-lane OCR needs
  tesseract language data (tests/test_main.py:3).

**The ThinkPad never receives the library lane's source PDF.** docs/41 §C9 (heading
:591): "⛔ THE LOAD-BEARING FINDING: **the source PDF never reaches the ThinkPad**"
(docs/41:593); "Nothing in `linux-converter/converter/*.py` ever opens or expects a
source PDF in a bundle" (docs/41:600). After conversion the PDF lives at
`drop/done/` on the Desktop only (docs/41:602). A CPU-side source↔output audit on the
ThinkPad is therefore architecturally impossible (docs/41:69). The one exception is this
fallback lane itself: a raw file dropped on an old Convert tile does arrive via
inbox → `pipeline/convert-inbox` and is converted here.

## 4. exporter.py — the vault's only writer

`converter/exporter.py` (582 LOC by `wc -l`; its suite `tests/test_exporter.py` is 430
LOC, the largest test file in the repo) ships staging bundles into the vault repo pair —
working clone → local bare repo, HEAD pinned to `main` (exporter.py:3-7, :43). Invariants
in the order the code enforces them (exporter.py:14-24):

- **Create-only**: never edits existing notes; commits are pathspec-scoped to the new
  bundle dir at `Inbox/<slug>--<sha8>/` (exporter.py:15-17, :47, :335).
- **Dedup on the full `source_sha256`**, grepped over committed `manifest.json` in the
  BARE repo — an identical re-ingest is a logged no-op and the staging copy is removed
  (exporter.py:318-332).
- **L12 deletion gate**: staging is removed only after the push succeeded AND
  `git cat-file -e` confirms the commit and every blob in the bare repo — never on
  write-success alone (exporter.py:21-24).
- **The supersede branch** (deliberate audit remedies only, opt-in via a `supersede`
  manifest block): fail-closed verdict guard — replace only on `pass`, or `flag` with a
  valid human bless (exporter.py:247-264); locate-don't-assume (exact-one-match grep,
  exporter.py:290-307); 0 matches falls through to a normal create with
  `EXPORT-SUPERSEDE-MISS` (exporter.py:309-316). A refused supersede is **held**: vault
  untouched, staging copy kept, `supersede-held` receipt (exporter.py:257-264) — the
  re-fire-per-boot shape of SYM-015.
- **The bless rail** (docs/18 §5.4, signed S56): `bless.json` beside the bundle lets a
  `flag` verdict through — sha-matched, flag-only, provenance folded into the manifest
  BEFORE any vault write so "the vault must never pretend a blessed note passed on its
  own merits" (exporter.py:172-207, :266-271).
- **Seam receipts + spot-check**: every EXPORT-* outcome appends one JSON line to
  `receipts.jsonl` (best-effort, torn-line-healing — exporter.py:49-99); every 10th
  accepted export is flagged for human eyes regardless of confidence
  (`SPOT_CHECK_EVERY = 10`, counter derived from receipts.jsonl itself, exporter.py:61-69).

**THE SUPERSEDE GAP** is the name docs/15 gave the dead-end where a re-convert
remedy could not swap the vaulted note (named in §13's remedy loop, docs/15:344; design
record in §14, docs/15:361-363). The exporter half was
built at S43 and live-fired (OPEN-TASKS §G); the Desktop half of the seam is still open
(OPEN-TASKS D7), and both widget renderers still show pre-implementation "manual/pending"
copy (SYM-043, OPEN-TASKS B11).

**Weekly fixity**: `converter/fixity.py` runs `git fsck --strict --no-dangling` over the
bare vault on the NDSA level-3 cadence — oneshot service fired by a weekly timer with
`Persistent=true`; a fail exits nonzero and writes a `fixity-check` receipt; "Repair of a
corrupt vault is archaeology with Rab, never automation" (fixity.py:1-13, :38-39).

## 5. systemd units — three services, zero hardening

Three `.service` units plus one `.timer` (`git ls-files linux-receiver linux-converter |
grep systemd`): `file-portal-allocator.service`, `file-portal-converter.service`
(both `Type=notify`, `WatchdogSec=90`, `Restart=on-failure` — a dead watcher thread
inside a living process becomes a restart, SYM-023's class; heartbeat gated on
`observer.is_alive()`, allocator/main.py:202-211), and the oneshot
`file-portal-vault-fixity.service` + weekly timer.

**Zero hardening directives in any unit.** Probe: `grep -cE` for a 30-directive
`[Service]` sandboxing list (`ProtectSystem|ProtectHome|PrivateTmp|NoNewPrivileges|
CapabilityBoundingSet|SystemCallFilter|ReadWritePaths|DynamicUser|...`) returned 0/0/0/0
across all four unit files, re-run 2026-08-23 against 1790554. Probe demonstrated
against controls first: a positive-control file containing `ProtectSystem=strict` +
`NoNewPrivileges=yes` scored 2; a negative-control plain oneshot scored 0. The units run
as the everyday user by design — docs/06:37-40 explicitly claims no extra privilege
boundary beyond the user account.

## 6. CI

CI runs ruff (all three Linux subprojects) + pytest (linux-receiver, linux-converter)
precisely because "the converter writes the vault — it is the last code that should be
unverified" (ci.yml:3-5, steps :35-55); the desktop GPU lane (windows-converter, 5,449
LOC of tracked Python, `wc -l`) has no CI job at all — see this wiki's testing page.

## Open items

- **OPEN-TASKS D7** — the Desktop half of the supersede seam (ThinkPad lane phase-gated).
- **OPEN-TASKS B11 / SYM-043** — supersede/pending projection drift in both widget renderers.
- **SYM-015** — a retained fail-verdict bundle in `staging/` re-fires `supersede-held` every boot (fixed by deletion once; the shape remains).
- **docs/41 §C9 / §D** — where a source↔output audit can actually hook (Desktop, not ThinkPad).
- Systemd hardening: no register item exists for it — this page's §5 measurement is the only record (unverified whether any hardening is *wanted*; the docs/06:37-40 posture suggests it is out of scope by design).
