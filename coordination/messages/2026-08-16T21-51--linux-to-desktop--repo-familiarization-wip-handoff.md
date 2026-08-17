---
from: claude-code @ linux-receiver
to: cowork @ windows-desktop
created: 2026-08-16T21:51Z
expires: 2026-08-30
status: done
supersedes:
---

# WIP handoff — full-repo familiarization pass (Linux side done, Desktop side MUST finish)

Rab commissioned a full six-pass repo familiarization (repo map → architecture → subsystems →
cross-system flows → verification → briefing) and then explicitly ordered it handed off
**unfinished**: the Linux-verifiable portion is done and recorded below; the items in §2 are
YOURS and must be completed **no matter what** — they are the parts only the Desktop can check.
Treat this as a standing task, not context. Report completion as a reply message per
`coordination/README.md`.

Epistemic tags follow docs/21: `Verified` = machine-checked here (suite run, mechanical count);
`Observed` = read directly from full source files; `Inferred` = flagged as such.

## §1 What is already done (do NOT redo)

- Every Rust module in `windows-widget/src-tauri/src/` read in full; `main.js` in full;
  `room.js` outlined (invoke surface mapped, render bodies NOT line-read).
- `linux-receiver/` and `linux-converter/` read line-by-line including `exporter.py` whole.
- `windows-converter/` read in full (`convert_and_ship.py`, `analyst.py`, `fidelity_audit.py`,
  `watch_and_convert.py`, `events.py`).
- `Verified` on this box 2026-08-16: receiver suite **28 passed**, converter suite **73 passed**.
- `Verified`: widget registers **38** Tauri commands; widget crate holds **20** `#[test]`s
  (bench 4, receipts 4, assay 7, algedonic 5) — matches SYM-020's 20/20 record.
- Full knowledge document embedded in §3.

## §2 MUST-COMPLETE checklist (Desktop lane — check each, fix or file findings)

1. **Deep-read the deferred UI files** and finish the subsystem map: `room.js` render bodies,
   `bench.html`, `windows-widget/src/styles.css` (only if load-bearing), the two
   `windows-remote/*.ps1` bodies. Confirm the §3 model of them or amend it.
2. **`ocr_dpi: 192` question** (`convert_and_ship.py:818`): scan-lane frontmatter stamps 192
   while linux-converter stamps its real `ocr_dpi` (300). Determine whether 192 reflects
   Marker's actual render DPI or is a stale constant; fix the frontmatter or document intent.
3. **Config-vs-hardcode drift check**: verify Rab's live `%APPDATA%\file-portal\config.toml`
   `gpu_*` values agree with the `C:\Users\Bndit\ml\...` constants hardcoded across
   `windows-converter/` and `prototypes/repair-bench/bench.py`, and whether a `convert-gpu`
   portal exists in his live portal list (it is handled by `transfer.rs` but absent from the
   default set). Two sources of one fact — decide if that stays.
4. **`assay::bless` hardcode** (`assay.rs:375`): plain `scp` to literal `rab@archlinux:file-portal/
   library/staging/...`, ignoring `linux_host`/`remote_user` config. Confirm this is accepted
   debt or route it through config; a host rename breaks bless quietly today.
5. **Run `cargo test` + `cargo fmt --check` + clippy on the real Desktop toolchain (1.97.1)**
   to re-prove the widget crate green — cannot be done from the Linux box.
6. **Stale-docs fixes** (small, mechanical — do them):
   - `CLAUDE.md`: test counts "24"/"51" → 28/73 (or de-hardcode the counts); component table
     still says "rsync over tailscale ssh" — transport is the `cat >` stream (transfer.rs).
   - `SYMPTOM-INDEX.md` SYM-014 guard column says `clamp_name` "200 utf-8 bytes" — code is
     **80 bytes** (`bundle.py`, MAX_PATH recalibration). Fix the row (index is append-only in
     spirit; correct the guard text, keep the row).
   - SYM-018's "`cargo test` still absent from CI" is superseded by SYM-020 — annotate.
7. **windows-converter test debt**: it is the only substantial untested code (1,193-line core,
   not in CI). At minimum file the decision (test or accept) as its own ledger row; do not let
   the handoff close with this unaddressed.
8. When 1–7 are done, produce the **final Repository Briefing** (architecture map, subsystem
   map, flows, interfaces, invariants, risks, unresolved questions), merging §3 with your
   Desktop findings, and file it where Rab directs (it does not yet exist in the repo —
   deliberately: this handoff is the WIP).

## §3 The WIP knowledge document (verbatim from the Linux session)

# File Portal — Repository Knowledge Document
Working notes for full familiarization pass. Repo: ~/file-portal-src, branch feat/library-pipeline (synced with origin). ~20.6k lines source. 2026-08-16.

## Pass 1 — Repo map (DONE)

Top-level:
- windows-widget/ — Tauri v2 app (Rust + vanilla JS). Rust modules: main.rs(621), assay.rs(629), room.rs(443), line.rs(393), algedonic.rs(385), bench.rs(317), watcher.rs(182), transfer.rs(168), receipts.rs(163), vault.rs(151), config.rs(129), preflight.rs(100), events.rs(78). JS: main.js(1036), room.js(928), styles.css(833). portals.json. harness-s62.html, harness-s74-audit.html (test harnesses?). NOTE: docs/CLAUDE.md only mention transfer.rs — widget has grown massively (cybernetic naming: algedonic = Stafford Beer VSM, cf. coordination msg 2026-07-20 "brain of the firm").
- linux-receiver/ — allocator pkg: main.py(227), rules.py(74), status.py(66), config.py, sdnotify.py. config/rules.toml. tests: test_allocator(185), test_rules(78), test_sdnotify. systemd unit. install.sh.
- linux-converter/ — converter pkg: exporter.py(582), main.py(349), bundle.py(145), engines.py(134), degeneration.py(88), config.py(77), status.py(67), fixity.py, sdnotify.py. config/converter.toml. 7 test files. systemd: converter.service, vault-fixity.service+timer.
- linux-dashboard/ — GTK4 viewer: main.py, window.py(151), scanner.py(83), watcher.py, config.py, widgets/{photo_grid,settings_popover,file_tree}.
- windows-converter/ — convert_and_ship.py(1193), fidelity_audit.py(491), analyst.py(438), watch_and_convert.py(127), events.py, prompts/readability.txt. No tests, not in CI.
- windows-remote/ — gate1-bootstrap.ps1, gate2-lockdown.ps1.
- prototypes/ — repair-bench (bench.py 1369, bench.html 1095, acceptance.py 408, transcribe_worker.py 127), control-panel (control-room.html, opsroom.html — HTML mockups), docling-calibration.
- coordination/ — inter-machine messages (dated md files), README.
- sessions/ — S67–S78 closeouts. docs/ — 00–29. SYMPTOM-INDEX.md, CHANGELOG.md, DOCS-AUDIT-CHANGELOG.md, CLAUDE_README.md.
- .github/workflows/ci.yml. scripts/ (bootstrap-arch.sh, windows dev-setup, install-shortcuts).
- Generated/skip: src-tauri/gen/schemas, icons/, package-lock.json, node_modules, target, .venv.

Runtime tree (live box): ~/file-portal/{inbox,sorted,pipeline/convert-inbox,logs/{allocator.log,status.json},vault.git, staging?, receipts?}

## Pass 2 — Architecture / entry points (DONE — all read)

## Subsystem notes

### windows-widget Rust backend (READ — complete)
Entry: main.rs — hydrate_env_from_registry() (PATH + GEMINI_API_KEY from registry; Explorer-launch env divergence fix), config::load_or_init, 38 commands. Window-Destroyed hook: only main window's death stops watcher (SYM-023 fix).
- config.rs: AppConfig from %APPDATA%\file-portal\config.toml. Fields: linux_host, remote_user, remote_inbox_root(~/file-portal/inbox), vault_library_dir (Library git clone), gpu_pipeline_dir (pending/drop/anchor/held), gpu_python_exe, gpu_converter_dir, reader_obsidian/zennotes, portals[]. Malformed config = surfaced error (not silent defaults). portals.json in repo = reference copy only, NOT loaded.
- transfer.rs: send_to_portal. Special case category "convert-gpu" → local copy into <pipeline>/drop (dotfile .part- + rename). Else: `tailscale ssh user@host "mkdir -p … && cat > .part-X && mv -f .part-X X"` streaming stdin. shell_quote + remote_path_expr (~/ handling). No resume/checksum for big files (known tradeoff).
- status.rs: fetch status.json via tailscale ssh `cat ~/file-portal/logs/status.json`; find_event(file,category) → widget tile feedback.
- watcher.rs: widget owns Desktop conveyor watcher lifecycle (spawns watch_and_convert.py in marker-env). Windows Job Object KILL_ON_JOB_CLOSE = no orphans on any widget exit (S37). Death certificate = second mutex remembers exit code (Stage A). stderr → watcher-stderr.log ("last words" idiom).
- line.rs: line_state projection of pipeline dir: drop count, .gpu-lock (converting + elapsed), .convert-progress.json (stage/frac, age = liveness), .analyst-progress.json (<300s fresh), queue (sorted names = watcher order), .convert-estimate.json (promise, only if lock matches source), events.jsonl tail → last shipped, ETA = pages × median s/page. Levers (widget WRITES user intent, Python reads): chunk-batch.txt (8|16|32, default 16), analyst-mode.txt (ask|local|gemini|off), rules.json (auto_local_over_chunks), audit-mode.txt (report|enforce via assay.rs). open_engineering: NAMED allowlist of paths → notepad/explorer. last_receipt from events.jsonl.
- preflight.rs: pending/<id>.json cards (written by convert_and_ship --defer-analyst); decide(id, backend local|gemini|none) spawns `convert_and_ship.py --resume <id> --backend <b>` detached, stderr→resume-stderr.log (SYM-024 fix).
- assay.rs: survival audit read side. manifest.json "fidelity" block: verdict pass|flag|fail, convert.doc_survival, tripwires.degeneration(+detail: md_lines, worst zones w/ zlib ratio, max_trigram, excerpt), runs. held/<sha16>/ = enforce-parked. reconvert(source): copy drop/done/<src> → drop/ + author supersede marker drop/.supersede/<src>.json {reason:audit-remedy, source_sha256 guard, from_verdict} — ONLY author of supersede intent (THE SUPERSEDE GAP). Marker before trigger; rollback marker if copy fails. reanalyze: --reanalyze detached, refused while .gpu-lock held (VRAM thrash S45). bless(source): verdict must be flag AND no degeneration; writes sha-bound bless.json via PLAIN scp (System32 OpenSSH, BatchMode, accept-new, hardcoded rab@archlinux:file-portal/library/staging/<bundle>/bless.json) — NOTE hardcoded host+path here vs config-driven elsewhere. Eligibility from events.jsonl ship/shipped sha16 match. Has real unit tests incl. cross-language seam artifact.
- algedonic.rs: Beer-style escalation. Sources: events.jsonl (convert/stalled, audit/held, */failed) + .receipts-cache.jsonl (supersede-held, bless-invalid, failed). Resolution suppression (later success retires alarm; nothing auto-resolves a park except human). 7-day window, dedupe kind|bundle newest, cap 12. acks → algedonic-acks.jsonl (append-only, widget-owned); M lever algedonic-minutes.txt default 30 (PROVISIONAL, unsigned by Rab). Hand-rolled ISO↔epoch (Hinnant civil algorithms, no chrono).
- receipts.rs: seam receipts. Remote ~/file-portal/receipts.jsonl (ThinkPad exporter appends outcomes: exported, exported-supersede, blessed, skip, supersede-held, bless-invalid, failed). fetch via tailscale ssh tail -60 → cache .receipts-cache.jsonl (empty output never overwrites cache); read_cached for Room render. Two-files/single-writer law: desktop events.jsonl (Python) vs receipts cache (widget).
- room.rs: KPI metrics (median s/page, throughput, survival avg from manifests, vault note count from Library/Inbox/<slug>--<sha8>/), gpu_vram via nvidia-smi, station_tree(seg: intake|convert|gate|assay|ship|vault) real on-disk drill trees.
- bench.rs: spawns prototypes/repair-bench/bench.py on newest/named held bundle, port 7077-7096, readiness probe, kill-on-close job, dedicated Tauri window "repair-bench". Quarantine: no import, only child process.
- events.rs: shift_summary (today's converted/analyzed/protected/shipped/failed + tail 10) from events.jsonl.

Desktop pipeline dir files (contract between widget and windows-converter): events.jsonl (Python-owned event stream; stages intake/convert/gate/analyst/audit/ship), .gpu-lock, .convert-progress.json, .convert-estimate.json, .analyst-progress.json, conversion-ledger.jsonl, chunk-batch.txt, analyst-mode.txt, audit-mode.txt, rules.json, drop/, drop/done/, drop/failed/, drop/.supersede/, pending/, anchor/, held/, watcher.log, watcher-stderr.log, resume-stderr.log, bench-stderr.log, widget-boot.log, .receipts-cache.jsonl, algedonic-acks.jsonl, algedonic-minutes.txt.

### windows-widget frontend (READ)
main.js: Dock surface. Drag-drop → send_to_portal; poll fetch_file_status (10×3s); convert-gpu category = local (no remote poll). Preflight cards poll 15s (fast 4s), decide → preflight_decide. Line strip poll 5-10s (line_state), stage ticker phrases. Watcher autostart at boot + 5s liveness poll ("never trust remembered state"), death certificate surfaced. Vault bar 45s poll (fast 10s) → vault_check/vault_pull; receipts_fetch piggybacks on vault poll. Assay ◎ card 20s poll, remedy/reanalyze/bless/bench buttons per held row. Algedonic chip 30s. Surfaces: dock ⇄ room ⇄ wall (room.js, same commands, denser projection + drill-down station_tree + acks + theme); bench = separate window. Sizing: per-surface user size memory; center on primary monitor.

### linux-receiver (READ — complete)
allocator/main.py: watchdog Observer on inbox/ recursive. inotify → on_closed(CLOSE_WRITE) + on_moved; non-inotify platforms → on_created + size-stability wait (react_to_created flag). Skips dotfiles, quarantine. Rules re-read per event. Flow: size check (max_file_size_mb 2048 → quarantine 'rejected') → rules.resolve(category, filename) fnmatch first-match → dest = root/template({yyyy}{mm}{dd} LOCAL time deliberately, DTZ005 noqa) → collision policy rename(default)/overwrite/skip → shutil.move → log + status.record. Unmatched → sorted/misc. Pre-creates inbox/<category> for all rule categories at startup. sd_notify READY after watch armed; WATCHDOG=1/s only while observer.is_alive().
- status.py: logs/status.json atomic rewrite (tmp+os.replace), bounded 200 events {ts,action,file,category,dest,reason}; never breaks allocation.
- rules.toml live: documents, convert→pipeline/convert-inbox, convert-scan→pipeline/convert-scan-inbox, photos/{yyyy}/{mm}, code (2 rules), archive.
- systemd: Type=notify, WatchdogSec=90, Restart=on-failure, __WORKDIR__/__EXEC_PATH__ templated by install.sh.
- sdnotify.py: stdlib NOTIFY_SOCKET datagram; DUPLICATED converter/sdnotify.py — must stay identical (stated invariant).

### linux-converter (READ — complete)
main.py: one Observer, two watches: pipeline/ recursive (ConvertHandler) + library/staging/ non-recursive (ExportHandler). Lanes: convert-inbox=clean, convert-scan-inbox=scan. Event model: allocator's rename INTO pipeline arrives as unpaired IN_MOVED_TO = `created` event (empirically verified), so on_created + stability wait is the main path. Engines: pymupdf4llm (*.pdf/*.epub; layout import order load-bearing; Clean=SELECT_KEEP_OLD auto-OCR, Scan=FORCE_DROP_OLD @ ocr_dpi 300 — NOT force_ocr=True which is FORCE_KEEP_OLD trap SYM-012), pandoc (*.docx → gfm, media flattened). Probe: chars/page < min_chars_per_page(100, provisional; calibration bar of 30 docs NOT met, held at G2) → clean reroutes to scan-inbox (as 'allocated' status), scan lane terminal (below-yield → quarantine 'rejected'). Degeneration tripwire (report-mode) → manifest. Bundle: temp dir keyed .part-<sha16> (L13 spaces bug), engine fed via slugified 40-char hardlink (L15 MAX_PATH), clamp_name 80 bytes. assemble: <name>.md (frontmatter+rewrite_image_links → ![[assets/x]]) + manifest.json. publish: atomic renames → anchor/ (immutable) + staging/ (export queue). Source file unlinked after publish.
- exporter.py: Exporter, threading.Lock serialized; sweep() at startup after watch armed. _export: requires vault-work clone + vault.git bare (never initializes — Decision #4). fetch+merge --ff-only first (Desktop filing moves). supersede block in manifest (authored only by widget reconvert click): verdict guard fail-closed (pass, or flag+valid bless.json sha-bound; else supersede-held receipt, staging kept); locate live note via git grep full sha in BARE repo (Desktop may have re-filed); ambiguous >1 → refuse; 1 → _supersede_replace (preserve old .md filename to keep wikilinks; swap assets+manifest; noop if byte-identical; resume if committed-not-pushed); 0 → supersede-miss → normal create. Normal path: dedup grep full sha in bare *manifest.json → EXPORT-SKIP + rm staging. Create: Inbox/<slug60>--<sha8>/, .part- assemble, pathspec-scoped commit (identity file-portal-converter@file-portal.invalid), push, L12 gate: cat-file -e commit + EVERY blob in bare, only then rm staging. Receipts: append_receipt → ~/file-portal/receipts.jsonl (torn-line healing; best-effort never raises). Outcomes: exported, exported-supersede, blessed, bless-invalid, skip, supersede-held, supersede-miss, supersede-noop, failed, fixity-check. Spot-check: every 10th accepted export flagged spot_check:true (FADGI); counter derived from receipts file itself (stateless). degeneration_flagged surfaced in receipt.
- degeneration.py: zlib ratio <0.20 AND max trigram ≥40 per ¶ (≥200 chars); contiguous repeated-line run >20; thresholds ported from Desktop calibration (docs/15 §9.1/9.2) — do not fork.
- fixity.py: oneshot git fsck --strict --no-dangling on bare vault, weekly timer (Persistent=true), receipt fixity-check pass/fail, no auto-repair.
- config.py Paths: pipeline/, quarantine (shared w/ allocator), library/anchor, library/staging, vault-work, vault.git. Settings re-read per event.
- Desktop bundles ALSO land in library/staging (shipped by windows-converter over ssh) — same exporter serves both conversion fronts.

### windows-converter (READ — complete; hardcoded paths C:\Users\Bndit\ml\{library,marker-env}, REMOTE=rab@archlinux)
- watch_and_convert.py: poll drop/ every 5s (no watchdog dep), stable-size wait, one at a time (GPU single-flight). analyst-mode.txt: off|local|gemini|ask→--defer-analyst. Holds .gpu-lock during child run; outer timeout 21600s (backstop above inner page-scaled cap). done→drop/done/, fail→drop/failed/ + intake/failed event.
- events.py: emit() appends events.jsonl {ts,pid,stage,event,...} best-effort.
- convert_and_ship.py: probe (chars/page, pages, OCR-layer detection via get_texttrace type-3 invisible spans majority + glyphless font regex) → route: ≥100 chars + ocr_fonts → scan --strip_existing_ocr (untrusted_ocr_layer); ≥100 clean; else scan (no_text_layer). recognition_batch 32 capped both lanes (VRAM). Marker run (_run_marker): stall monitor — progress file (.convert-progress.json from tqdm parse of marker stdout; drain-thread w/ utf-8 errors=replace, S48 pipe deadlock), frozen >900s → taskkill /T tree-kill + convert/stalled event + GPU signature; hard timeout max(3600, pages×20). Chunking (Stage D): >600pp clean / >400pp scan → 200-page slices via --page_range, chunk-batch.txt lever (8/16/32 def 16) re-read per slice; slice resume in .chunk-work/<sha16>/slice-XXXXX-YYYYY/ with .done marker (atomic rename); asset names use ABSOLUTE page numbers (measured S60); out_of_range_assets tripwire; seams recorded in manifest.chunking, never smoothed. Ledger: conversion-ledger.jsonl per success (true cost incl resumed slices); estimate_from_ledger = same-lane 3 nearest chars/pp neighbours median s/page → .convert-estimate.json promise + promised vs actual on converted event. Supersede: _take_supersede_marker consume-once from drop/.supersede/<name>.json BEFORE work; _stamp_supersede_safe sha-guarded → manifest.supersede. Audit hooks _audit_convert_safe/_audit_analyst_safe (report-only, never raise) → manifest.fidelity. Enforce lever audit-mode.txt: _enforce_hold parks fail bundles to held/<sha16>/ (S65: repairs-bearing occupant never rmtree'd — incoming parks BESIDE as --superseded-<stamp>; fails OPEN = ships). Bundle mirror of linux bundle.py (clamp 80, slugify 60, frontmatter same shape, engine marker, ocr_dpi 192 in frontmatter). ship(): tar -cf - | tailscale ssh rab@archlinux 'tar -xf - -C .part-<sha16> && mv → staging/<bundle>' (ASCII-only local paths — bsdtar CJK argv bug; visible name applied by remote mv); tar killed if ssh dies. Modes: default=convert+anchor+ship; --dry-run; --analyst --backend; --defer-analyst → pending/<id>/+<id>.json card (auto-route rule auto_local_over_chunks); --resume <id> (widget card decision); --reanalyze <source> (analyst-only rerun from pre-analyst anchor copy; refuses if only analyst output survives; ships as supersede reason=analyst-rerun).
- analyst.py: link-fence: ![[embeds]]→⟦IMG-n⟧ tokens; chunk ~4000 chars on ¶; local=qwen3:8b ollama (keep_alive 0, num_ctx 8192, think false) or gemini-flash (13s pacing =4.6RPM free tier, 3 retries backoff; GEMINI_API_KEY env); token-multiset equality check per chunk — violation = rejected, original kept; backend error = failed, original kept, NOT journalled (transient). Chunk resume journal .analyst-work/<key>/chunks.jsonl (key=sha(fenced|backend|program|chunk_target); per-chunk hash validation; fsync). .analyst-progress.json heartbeat per chunk (rate over generated-only). preflight(): card JSON — est_chunks, gpu_busy, measured eta_range from events history (fallback static), free-tier window warn >18 chunks, recommendation. prompts/readability.txt = the "program".
- fidelity_audit.py: Survival Audit. Witness = pymupdf text per page (ephemeral). Normalization (NFKC, quotes, dehyphen, markdown strip, witness repeated-line strip ≥40% pages, casefold, ws collapse). 12-word windows (CJK: 24-char), containment + rapidfuzz partial_ratio ≥90 fallback via rarest-anchor probe. Page score = passed/windows; doc_survival = window-weighted; runs = ≥2 adjacent missed windows. Tripwires: degeneration (same as linux port), garbage_rate (scan; no-vowel token frac), reverse_sample (anti-hallucination, 200 sampled output windows sought in witness, fixed seed), asset_delta. audit_analyst: near-exact (no fuzzy), Marker doc is reference. compute_verdict (SIGNED policy): fail ONLY on degeneration OR analyst loss (doc<0.995 or run≥25 words); everything else max flag (clean: doc<0.97, page<0.85, run≥50; scan: page flags or garbage>0.20). \\?\ longpath handling.

### Other subsystems (skimmed, sufficient)
- linux-dashboard: GTK4/Adw single-instance app; scanner.py walks sorted/ per category (photos special-cased), watcher.py debounced watchdog → refresh; widgets: photo_grid (thumbnail LRU cache), file_tree (ColumnView), settings_popover. Read-only viewer.
- prototypes/repair-bench: bench.py stdlib+pymupdf HTTP server 127.0.0.1 (spawned by widget bench.rs or manually). Human repair of held bundles: PDF page raster left / markdown at flagged zone right; gestures: crop→assets/_repair_pN_k.png + ![[..]] embed + manifest["repairs"]; transcribe (granite-docling-258M via docling-env subprocess worker, process-per-request); collapse (token-loop TTR-based, measured thresholds); AI assist (fenced); undo ledger with _write_body single chokepoint (docs/28); triage/coverage; sandbox mode. Zone line staleness fixed via excerpt search (_resolve_zone_line, SYM-025); omission runs rendered (SYM-026). acceptance.py = 26 checks against sandbox copy of real held bundle, hash-proves original untouched, OS-assigned port (SYM-010). Quarantined: pipeline never imports it.
- windows-remote: gate1 (sshd enable, tailnet-scoped firewall), gate2 (key install → proven login → password lockout, two runs). Zero pipeline coupling.
- coordination/: repo-as-message-bus between machine agents; frontmatter status/expires; newest unexpired open message authoritative.
- CLAUDE_README.md: mission brief + Change Ledger + session protocol (open plan commit, close commit, ledger row as separate commit — never amend, SYM-016).
- CI (.github/workflows/ci.yml): python job = ruff check+format for 3 subprojects + pytest receiver/converter; rust job on windows-latest, toolchain pinned 1.97.1, fmt --check + clippy -D warnings + cargo test. Triggers: master + feat/library-pipeline + PRs (SYM-018). windows-converter and repair-bench NOT in CI (no suites; acceptance.py needs real machine).

## Pass 5 verification results
- Suites run live 2026-08-16: receiver 28 passed, converter 73 passed (0.06s / 3.35s).
- Test counts in CLAUDE.md ("24 allocator, 51 converter") are STALE — pre-S78 numbers.
- CLAUDE.md component table "drag → rsync over tailscale ssh" stale — transport is cat>-stream via tailscale ssh (architecture section states correctly). allocator/main.py on_moved comment still says "rsync renames its temp file" — mechanism-correct (mv fires on_moved) but naming stale.
- SYMPTOM-INDEX SYM-014 guard cites clamp_name "200 utf-8 bytes"; code is 80 bytes (bundle.py, recalibrated for Windows MAX_PATH; docstring documents 160-byte worst case). Index row stale.
- SYM-018 note "cargo test still absent from CI" superseded by SYM-020 fix (cargo test present in ci.yml).
- Desktop scan-lane frontmatter ocr_dpi = 192 (convert_and_ship.py:818) vs linux 300 — different engines (Marker vs pymupdf4llm), deliberate? unverified.
- assay.rs bless uses PLAIN scp + hardcoded rab@archlinux + path 'file-portal/library/staging/...' (matches converter REMOTE_STAGING); transfer.rs comment says scp can't verify tailscale host keys — bless works because System32 OpenSSH TOFU accept-new + tailnet MagicDNS name 'archlinux' resolvable. Host/user here NOT config-driven (linux_host/remote_user unused in bless) — fragile if host renamed.
- windows-converter paths hardcoded to C:\Users\Bndit\ml\... — config.toml gpu_* keys must point there; widget passes dirs but converter scripts also hardcode (two sources of the same fact; watch_and_convert BASE vs widget's gpu_pipeline_dir must agree).

## Open items / debt (from code, not docs)
- PROVISIONAL unsigned: algedonic M + ack mechanism (Rab hasn't signed); min_chars_per_page=100 (calibration bar not met, ~10 distinct docs); repair-earns-audit-credit policy unsigned (bench re-score is preview only); SPOT_CHECK_EVERY=10 hardcoded (promote to converter.toml when tuned).
- OPEN symptoms: SYM-003 table-loop degeneration (bench is response, not fix); SYM-024 vanishing resume (hardened via resume-stderr.log, not root-caused); SYM-027 observability complex (~83 silent fields censused, detector not automated).
- windows-converter has no test suite, not in CI (the only substantial untested code; the widget crate has 20 tests, linux sides 101).
- Transfer: no resume/checksum for large files (docs/08 roadmap item).

## Unresolved questions (remaining)
- ocr_dpi 192 vs settings mismatch (§2 item 2); whether desktop 'convert-gpu' portal category is present in Rab's live config.toml (§2 item 3).

## Outcome

Completed by Desktop S86, 2026-08-16 evening (Rab signed). All eight items dispositioned —
see the reply `2026-08-17T03-05--desktop-to-linux--familiarization-complete-and-the-fork-reconciled.md`
and `docs/36-repository-briefing.md`. One item returned: the CLAUDE.md with stale counts is
untracked on the ThinkPad and must be fixed there.
