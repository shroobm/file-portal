# CLAUDE_README — File Portal / Library Pipeline Mission Brief

*Read this file first when activating on any machine in this project. The Change Ledger below
the Status Summary owns "last updated" — there is deliberately no hand-typed date here.*

---

## Session Protocol — How Every Claude Uses This File

This file is the shared brain across sessions and machines. Follow this every time.

### 1. On Activation
```bash
git pull  # always first
```
- Read this file top to bottom
- Read the most recent entry in **Session Log** to understand where the last session ended

### 2. Before Starting Work
- Write your plan in **Current Session Plan** (replace whatever was there)
- Include: what you're planning to do, in what order, and how you'll verify each step
- Commit and push:
  ```bash
  git add CLAUDE_README.md
  git commit -m "session: open plan — [machine] [date]"
  git push
  ```

### 3. During Work
- Verify each step before moving on (test, lint, check output, confirm expected behavior)
- If the solution to a step changes from the plan, note the change and why inline

### 4. Before Closing the Session
- Move the current session plan to **Session Log** with a timestamp and outcome
- Update the machine's task list above (check off done items, add new ones)
- Write the concrete next steps so the next Claude can start immediately
- Run `git diff --name-only <last ledger SHA>..HEAD`. Every changed file must be accounted
  for: either it appears in a `CHANGELOG.md` entry, or it is a doc/protocol file listed in
  your new Change Ledger row. If a source file changed and no CHANGELOG entry describes it,
  write one before closing.
- Append your Change Ledger row **after** the closing commit is made, in a **one-line
  follow-up commit** — do NOT `git commit --amend` it into the closing commit: amending
  changes that commit's SHA and orphans the row you just wrote (discovered by doing exactly
  that, 2026-07-10). Never write a SHA you have not seen.
  (A ledger SHA that is not an ancestor of `HEAD` is a mechanically detectable lie — one
  `git merge-base --is-ancestor` call. That check is what caught the L6.5 status-feed
  regression, where `0c3a074` was never merged into the branch.)
- Commit and push:
  ```bash
  git add CLAUDE_README.md
  git commit -m "session: close — [machine] [date]"
  git push
  ```

---

## Current Session Plan

*Replace this section at the start of each session. Commit it before starting work.*

*(S41 closed 2026-07-23 (Desktop). **GPU telemetry stream COMPLETE** (docs/16 §8 #4). S38 shipped the
VRAM sparkline; the probe already reported util+temp as numbers — S41 gives **utilization +
temperature their own rolling sparklines**. A unified **GPU telemetry strip** in the Room shows all
three fixed-scale (VRAM 0–100 / util 0–100 / temp 30–95 °C), each with its value + clay stroke under
pressure (>92 / >95 / >83). `sampleGpu` feeds three rings from the same one read per poll (still no
backend thread); the VRAM sparkline graduated from the KPI tile into the strip (tile → gauge, no
duplication). Frontend-only; `room.js` + `styles.css` (`.room-gpu`/`.rg-*`). Harness-verified (0
console errors; all three accumulate on their fixed scales — temp Y-coords confirm the 30–95 domain;
util clay at 98 %; dark+light), `tauri build` green. Installed swapped (SHA256 `55128BE2…`) +
relaunched (PID 22152). Close `a0554dd`. **Deferred by choice:** always-on backend sampler (S37 idle
discipline); throughput/median rolling-window rework (their events-tail series already IS a
last-12-converts rolling window). **Next: S42 = true per-page convert %** (§8 #3, fail-safe Popen
streaming of the converter). §8 #5 supersede = ThinkPad-only (widget side done via ⟳ re-convert).)*

*(S40 closed 2026-07-23 (Desktop). **Start-centered-on-monitor-1 SHIPPED** (Rab-requested follow-up
to S39; sizes don't persist, so every launch should start somewhere predictable). New
`main.js::centerOnPrimary()` runs once at boot (just after the initial reflow settles the height):
reads `primaryMonitor()` (position + size) + `getCurrentWindow().outerSize()`, then `setPosition`s to
the monitor-center — all in **physical px** (DPI-correct; lands on the primary regardless of a 2nd
monitor's offset). Only at launch; the user can still drag it anywhere (moves aren't tracked). Added
the `core:window:allow-set-position` capability (regenerated `gen/schemas/capabilities.json`).
**Verified LIVE:** the relaunched window's center measured **(1280,720)** — exactly the 2560×1440
primary's center — on DISPLAY1. `node --check` clean, `tauri build` green. Installed widget swapped
(SHA256 `11038318…`) + relaunched (PID 10116, centered). Close `ba922f8`.)*

*(S39 closed 2026-07-23 (Desktop). **Widget resize fix SHIPPED** (Rab-reported). The widget
"defaulted to a size" — dragging an edge to enlarge it reverted, because `reflow()` (main.js)
re-asserted `setSize(480, content-height)` on nearly every poll (via `pfCheck → pfRender → pfResize
→ reflow`, even with an empty queue), pinning width to 480 + height to content, and fired regardless
of surface (also yanked Room/Wall back toward Dock dims). The window was already `resizable:true` —
the frontend was fighting the user. Fix (frontend-only, no Rust): a manual resize is detected via
`getCurrentWindow().onResized` (event dims vs. the last size WE applied, with a short suppress-window
after our own `applySize` to ignore the settle echo) and **remembered per surface**
(`userSize.{dock,room,wall}`); `reflow()` is now Dock-only and, once the user has sized the Dock,
only **grows** height to prevent a content clip (never shrinks, never touches width); surface
switches restore the remembered size (else default: Dock content-fit / Room 760×600 / Wall 900×500).
**Verified LIVE** on the real widget: a programmatic resize to 796×639 **held across 13 s of polling**
(was reverting to ~496), and the boot log recorded the `onResized` beacon (`user-sized dock →
780×631`). `node --check` clean, `tauri build` green. Installed widget swapped in place (SHA256
`BDA346A6…`) + relaunched fresh (PID 25504, clean default). Close `9cc0f31`.)*

*(S38 closed 2026-07-23 (Desktop). **GPU telemetry sparkline SHIPPED** (docs/16 §8 #4) — the next
genuine installment after the Control Room finished at S37. The Room's GPU VRAM tile now draws a
**rolling sparkline** instead of a bare gauge: a bounded module-scoped ring (`vramHist`, 48) fed one
sample per poll (the poll loop IS the sampler — no always-on backend thread), drawn on a **fixed
0–100 % scale** so height = true card-fullness (idle low, a convert spikes; honest, unlike the
autoscaled throughput/median tiles). `gpu_vram()` extended to also report **utilization +
temperature** (`{used,total,util,temp}`), surfaced on the header GPU stat. `sparkSvg` gained an
optional fixed-domain param; gauge stays the first-poll fallback. Read-only projection; pipeline
untouched. Verified in a browser harness (0 console errors; the ring accumulated across polls; the
fixed-scale Y-coords matched exactly; gauge→sparkline transition; util/temp in dark+light; the other
two sparklines unregressed), `clippy -D warnings` clean, `tauri build` green. **Installed widget
swapped in place (SHA256-verified, DC26F26D…) + relaunched (PID 28148) — running the S38 build now**
(Rab present, approved the swap; the S37 Job Object re-confirmed live: the force-stop took the
watcher + its child too). Close `6dc8813`. **Still deferred** (their own installments): an always-on
backend sampler; re-backing throughput/median sparklines with a rolling window; true per-page
convert % (#3, core converter); the Beer remedy / SUPERSEDE GAP (#5, ThinkPad).)*

---

## Status Summary

- ✅ File Portal v2 status feedback loop — Tauri v2 built (45s, 2 bundles), all 4 files committed
- ✅ `coordination/messages/` folder created in repo
- ✅ Desktop build report written and committed to `feat/library-pipeline`
- ✅ Branch `feat/library-pipeline` pushed to origin
- ✅ `CLAUDE_README.md` created with session protocol and pushed (this file)
- ✅ W1 atomic transfer — verified in committed code (transfer.rs: `.part-` tmp + `mv -f`)
- ✅ W2 streaming copy — verified in committed code (`std::io::copy`, not `read_to_end`)
- ✅ W3 widget controls — verified in committed code (titlebar in index.html, capabilities/default.json, height=186)
- ✅ W4 rebuild — complete; `npm run tauri build` succeeded (1m 04s, 2 bundles: MSI + NSIS)
- ✅ W5 E2E test RUN 2026-07-08 — transport verified byte-exact both directions of the matrix (.pdf→documents, .xyz→misc); W1/W2 confirmed in production
- ✅ L6.5 COMPLETE 2026-07-08 — status feed ported from `0c3a074` into the branch, reconciled with L1 (branch `config.py` kept), 24/24 tests pass, service restarted, `allocated` + `rejected` events live-verified in status.json → **W5 visual re-check is unblocked**
- ✅ Rejection semantics DECIDED — `rejected` = quarantine only; unmatched extensions = `allocated` with `dest: sorted/misc`. Red ✗ now means "quarantined" (today: oversized). W5's `.xyz → red ✗` expectation is re-scoped: `.xyz` → green ✓ with misc dest (see 04-50 coordination msg)
- ✅ Part 1 Linux (L1-L4) COMPLETE — gate is open; code was in e314607, ThinkPad verified live 2026-07-07
- ✅ L1/L2 live-tested on ThinkPad: 3GB sparse file → quarantined and STAYED (no loop); dotfile ignored; normal file allocated
- ✅ L3 verified: tailscaled enabled, Linger=yes, file-portal-allocator enabled+active; service restarted onto feat/library-pipeline code
- ✅ Part 2 Linux (L5-L6) COMPLETE — convert rule live-tested; `file-portal-converter` installed, enabled, e2e verified (allocator hop → "would convert" logged, dotfiles ignored)
- ✅ Docs consistency pass 2026-07-07: stale `inbox/quarantine` refs fixed (docs/05, receiver README), `linux-converter` added to root README/docs/00/docs/01, docs/10 checkboxes synced to reality, CHANGELOG updated
- ✅ W6 Convert tile DONE + E2E verified 2026-07-08 (`af904a2`) — green ✓ in ~4s, full Windows→allocator→converter chain confirmed. **W5 visual re-check PASSED** with it. Part 2 "Done when" = CLOSED both lanes.
- ✅ Part 3 Linux (L7-L10) COMPLETE 2026-07-10 — conversion engine live: probe → Clean/Scan lanes → atomic bundles to anchor+staging, all gates verified on the live service (see Session Log 2026-07-09/10). Open Decision #3 RESOLVED (probe/reroute/terminal-scan). Defect A (hardcoded WorkingDirectory) fixed both services; Defect B banner added.
- ✅ W7 "Force OCR → Vault" tile DONE + E2E verified 2026-07-10 (`1d15b16`) — 6th tile renders; drop → green ✓ with `dest: pipeline/convert-scan-inbox/…` in ~1s; ThinkPad converter forced the Scan lane on a digital PDF (probe 277 chars/page, `lane_reason: user_forced_scan`, re-OCR at 300 dpi, yield 279) and published the bundle to anchor+staging; source SHA-256 matched the local file byte-exact. Part 3 "Done when" = CLOSED both lanes.
- ✅ Part 4 groundwork 2026-07-10 — vault repo wired both ends, transport verified. L11 (exporter) and L12 (staging deletion) remain.
- ✅ Part 4 Linux (L11+L12) COMPLETE 2026-07-11 — exporter live in the converter service: staging bundle → vault commit → push → `cat-file -e` blob verification in the bare repo → staging deleted. Dedup no-op verified live; a 2×60s event-stall defect found at the live gate and fixed same session (export latency now ~25ms). **All Linux milestones (L1–L12) closed; the pipeline loop is code-complete.**
- ✅ Desktop vault consumption VERIFIED 2026-07-11 — `git pull` inside `<Vault>\Library` fast-forwarded `0272f89..ec1eaf6` over Tailscale SSH; history shows both L11 test ingests (`a49d49c`, `cfca152`) + the honest removal (`ec1eaf6`), tree back to seed files; no stray `.obsidian/` in Library and no Library entry in Obsidian's vault registry (Decision #4 gotcha clear). **The full pipeline loop is closed end to end: widget → allocator → converter → vault → Desktop.**
- ✅ First REAL document ingested 2026-07-12 ("Designing Freedom", Stafford Beer, 116 pp, 4.4 MB): converted (70s, Clean lane, 25 images), exported (`c624e00`), pulled + byte-verified on Desktop, filed to `Inbox/` (`0fa976c`). It took 4 attempts and surfaced **two defects** (see 2026-07-12 coordination messages):
  - **L13 (high): spaced filenames + images fail** — pymupdf4llm space-sanitizes the whole image path incl. directory components, but `main.py` builds the staging temp dir from the stem verbatim → first image write ENOENTs → quarantine. All milestone test files were space-free, so L1–L12 never caught it. Workaround until fixed: no spaces in dropped filenames.
  - **L14 (low): `INBOX_REL` off by one** — exporter commits to `Library/Inbox/` inside a repo whose root IS the vault's Library folder → vault shows `Library/Library/Inbox/`. Fix: `INBOX_REL = Path("Inbox")` + test expectations; no migration (Desktop filed the one bundle).
- ✅ L13 + L14 FIXED + live-verified 2026-07-12 (ThinkPad) — assembly dir now sha-keyed (`.part-<sha256[:16]>`, sanitizer- and length-proof; published bundles keep the original stem) + `bundle.clamp_name` 200-byte cap; `INBOX_REL = Path("Inbox")`. Regression test reproduces the exact field failure; 40/40 tests; one live drop (`L13 Live Gate - Spaced Name.pdf`) proved both fixes: CONVERTED (no quarantine) + EXPORTED to repo-root `Inbox/…` (commit `139f74d0`). **The spaces workaround is retired.** See `coordination/messages/2026-07-12T00-38--…l13-l14-fixed-live-verified.md`.
- ✅ L13 Desktop re-verification 2026-07-12 00:55 UTC with the **worst-case real name**: the original ~225-byte Anna's Archive filename (spaces + U+2019) CONVERTED in 70s, published name visibly clamped at 200 bytes (`…be8508ec`), and 12ms later `EXPORT-SKIP … dbcce92c already in vault` — the dedup no-op kept the vault clean. Retest anchor duplicate removed; all queues empty.
- ✅ **W8 "Add to Library" button DONE + E2E verified 2026-07-12 (`854d89f`)** — new `#vault-bar` in the widget (Claude Code-styled, ✳/terracotta) backed by `vault.rs`: glows "Add N new note(s) to Library" when the bare repo is ahead of the Desktop clone, one click pulls and names what arrived; 45s poll, 10s fast-poll for 3 min after any `pipeline/convert*` drop; new `vault_library_dir` config key (live config + `serde(default)`); window height 224; console window killed (`windows_subsystem`). Live gate: the Textor ingest (`fd0e50a`, 2nd real book, dropped by the user with its natural spaced name — L13 fix holding in the wild) lit the button in one poll; click pulled note+4 assets+manifest into `<Vault>\Library\Inbox\`. **Defect L15 found by that first click:** bundle-interior filenames (200-byte stems, ~230-byte asset names) exceed Windows' 260-char MAX_PATH — checkout failed until `core.longpaths=true` (now set in the clone AND passed `-c` by the widget). Filed to Linux lane: shorten interior names at the source (see 01-15 coordination msg).
- ✅ L15 FIXED + live-verified 2026-07-12 (ThinkPad, `d1112d2`) — bundle interiors are
  Windows-clean at the source: the engine converts from a short sanitizer-proof hardlink
  (`<slugify(stem)[:40]><ext>`, removed before publish) so asset names drop ~230 → ≤ ~61
  bytes, and `clamp_name` 200 → 80 bytes puts the worst-case note at exactly 160 bytes
  vault-relative. Also closes a latent ext4 overflow (>243-byte stems would quarantine at
  the asset write). Red-first regression test; 41/41; live gate: 230-byte spaced name →
  CONVERTED → EXPORTED `b914af1b`, committed paths measured 158/139/89 bytes by `ls-tree`.
  Desktop's `core.longpaths` mitigation may stay but is no longer needed for new bundles.
- ✅ **PR #1 (feat/library-pipeline → master) MERGED 2026-07-13 (`7c006f2`, merge commit, branch kept)** after repairing both first-contact CI failures same session: `CI / python` (pytest couldn't import the packages in the bare runner venv — `pythonpath = ["."]` added to both Python pyproject.tomls) and `CI / rust` (`cargo fmt` on post-July-5 widget code; clippy pre-cleared). All 6 checks green (python 14s, rust 3m14s, CodeQL ×3 + summary). Stale `fix/widget-blank-window` deleted on origin (all 5 commits patch-equivalent in feat, verified with `git cherry`). Known-red follow-ups: CI runs no `linux-converter`/`linux-dashboard` tests; checkout/setup-python actions emit Node 20 deprecation warnings.
- ✅ **GPU pipeline revamp scoped + Phase 0+1 executed 2026-07-18 (Desktop)** — scope committed as `docs/11-gpu-pipeline-revamp.md`; Phase 0 gate PASSED (uv + Python 3.12.13 + torch 2.11.0+cu128, 3080 visible); Phase 1 Marker-vs-pymupdf4llm A/B on the Beer book = **mixed pass** (Marker structurally better — paragraphs, sketches, 36 images, `_meta.json` TOC — but inherits `<sup>`/word-merge noise from the PDF's embedded 2013 OCR layer; `--force_ocr` at defaults thrashes the 10 GB card, killed at 27 min). Full numbers + fix candidates in docs/11.
- ✅ **Phases 1.5 + 2 CLOSED 2026-07-18 evening (Desktop, Session 14)** — Phase 1.5a: `--strip_existing_ocr --recognition_batch_size 32` **fixes the whole Phase-1 noise class** (0 `<sup>`, perfect TOC table, ~4 s/page, peak 7.9 GB); 1.5b: born-digital A/B (webpage-PDF, CJK) = Marker wins outright (27 s/19 pp, working hyperlinks, no icon spam); Phase 2 VRAM handoff **PASSED** (Ollama 0.32.1 + qwen3:8b, `keep_alive:0`: baseline 623 → 623 → 621 → 620 MiB across Marker→generate→Marker, 52.6 tok/s, no OOM). **Engine policy table + ⚠️ LLM link-rewriting hazard + factory/control-center design note recorded in docs/11.**
- ✅ **Phase 3 CLOSED 2026-07-19 (ThinkPad)** — sidecars measured and PASSED: specs recorded (i7-1265U 2P+8E/12t, 15.3 GiB RAM, 199 GB free, 4 GiB zram); Ollama 0.32.1 (user-level tarball, `~/ml/ollama` — no sudo in session; pacman package if role goes permanent) + phi4-mini q4: **~30 tok/s prompt eval, 4.1–5.8 tok/s generation, 3.06 GiB peak RSS** → async tagging gate PASS (10–60 s/doc), full-document analyst ruled out (~3 h/book); ChromaDB + MiniLM over the real vault (1218 chunks, 2 books): embed 34.2 s, queries 3–6 ms, all 4 relevance probes hit the right book → PASS. **Recommendation recorded in docs/11: product analyst stays on Desktop GPU (52.6 vs ~5 tok/s); ThinkPad carries tag/embed/structure.** Red flag #2 resolved.
- ✅ **Phase 4 slices 1+2 LANDED 2026-07-19 (Desktop, Session 15)** — `windows-converter/convert_and_ship.py` + `analyst.py`, design in `docs/12`. Slice 1 E2E with the **unchanged** ThinkPad exporter: agent-book bundle EXPORTED (`6008eb66`, blob-verified, byte-identical sha), re-ship → EXPORT-SKIP, and the **cross-machine dedup proof** — Beer converted fresh on the Desktop GPU (489 s full strip-OCR) skipped against the ThinkPad's 2026-07-12 ingest (`dbcce92c`). Slice 2: link-fenced qwen3:8b readability pass, 7/7 chunks fence-clean, 0 stray tokens, VRAM back to baseline. OCR-layer detection = text render mode 3 (font-name heuristic failed on the Beer layer — hit live). Windows gotcha: bsdtar mangles non-ASCII argv → tar sees only ASCII paths, remote `mv` applies the CJK name.
- ✅ **S27: the assumption is now a measurement — degeneration findings filed + Survival Audit spec committed 2026-07-20** — the user visually caught OCR degeneration loops in the vaulted Brain of the Firm; a prototype of the docs/15 §5 tripwire quantified them: **12.3% of chars (140,513/1,139,354) in two zones**, worst block a 32,294-char `## The Control of the Control of…` heading loop (trigram ×2,152, zlib 0.003). Findings F1–F5 filed in coordination/messages (F3: analyst chunker passes oversized paragraphs unexamined — fail-safe correct, no analyst fault; F5: pre-L15 vault paths up to 349 chars need `\\?\`). Other 3 vaulted books scanned CLEAN; thresholds separate cleanly (**flag at zlib<0.20 OR trigram≥40 → 0 false positives on corpus**). `docs/15-survival-audit.md` = the full audit spec; build is S28 (report-only until thresholds signed off). Beer's bad copy deliberately retained as the labeled true-positive calibration specimen; remedy = re-convert + supersede-swap once the audit proves detection on it.
- ✅ **S28: the Survival Audit is BUILT (report-only) 2026-07-20** — `windows-converter/fidelity_audit.py` implements docs/15 (window-survival containment vs an ephemeral pymupdf witness; per-stage strictness; §5 tripwires), wired crash-safe into `convert_and_ship.py` (fidelity block in manifest + `stage:"audit"` events; verdict gates nothing). Calibrated over the vaulted corpus: **degeneration tripwire is production-ready** (flags Beer's two zones only, clean on the other three, at zlib<0.20 OR trigram≥40); **survival score is a report-only localizer** (0.76–0.96 on acceptable books — legitimate reflow, so no doc-level gate yet); analyst near-exact validated (reformatting doesn't false-fail, omission caught). Awaiting Rab's threshold sign-off → then widget terracotta-on-fail slice + Beer remedy loop (re-convert + supersede-swap). Full findings in the S28 Session Log.
- ✅ **S29: the widget "old version" ghost SOLVED — it was MSIX AppData redirection, not the build 2026-07-20.** Multi-session symptom (widget missing the ⚡ GPU→Vault tile) traced to the true cause: **Claude's tools run sandboxed in the Claude desktop app's MSIX package, so all `AppData` reads/writes are redirected into the package container** (proven: a marker written to `AppData\Roaming\file-portal\` appeared in `…\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\…`; the "two" configs share one File ID). The widget's `config.toml` lives in `AppData` → Claude's config edits + Claude-launched widgets used the sandbox copy (7 tiles), while Rab's normal unpackaged launches read the REAL AppData (stale → 6-tile `default()`). **Fix:** Rab copied the good 7-portal config into real AppData from an UNPACKAGED terminal (staged at `ml\library\config-RESTORE-to-real-appdata.toml`) → ⚡ tile back and stays across taskbar/shortcut launches. **Scope = AppData only**; vault (Documents), repo (Projects), pipeline (ml\library) are the real shared filesystem (all prior work is real). Mid-session wrong turn: a "stale frontend embedding" theory (from grepping brotli-compressed Tauri assets) led to an unnecessary but harmless rebuild — corrected once assets were decompressed. Saved to memory (desktop-machine "THE BIG ONE").
- ✅ **S30: the Survival Audit's enforcement policy is SIGNED + the widget projection is designed 2026-07-20.** Rab signed "degeneration + analyst near-exact only": `fidelity_audit.compute_verdict` rewritten so **degeneration** (either lane) and **analyst loss** (`doc<0.995 OR run≥25`) are the sole `fail` signals; survival/agreement, page flags, runs, garbage-rate are report-only **localizers** (`flag`). A clean-lane survival gate was considered + rejected (acceptable books span 0.76–0.96). Verified over all four vaulted books (Beer→`fail` at zlib 0.003/tri×2,267; the other three→`pass`; **zero false positives**; the prototype's Textor false alarm cleared). Verdict is recorded honestly; **enforcement is a separate default-off lever** (`audit-mode.txt` `report`|`enforce` → parks a `fail` in `held/`; contract docs/15 §12). Widget projection specced as **docs/15 §13 "The Assay"** — a `◎ assay` line station + evidence card (damage map + verbatim runs) + `report ⇄ enforce` control, terracotta reserved for `fail`. No pipeline behavior change yet (verdict-only). **Next = the dedicated Assay build session** (Tauri + rebuild ritual).
- ✅ **S31: the Assay is BUILT — the Survival Audit's widget projection 2026-07-20.** New Rust `assay.rs` (`status`/`get_mode`/`set_mode`/`reconvert`) + 4 commands; a `◎ assay` line station (verdict dot: green pass / amber flag / **terracotta fail, the only pulse**) + an evidence card on flag/fail (book-length **damage map** with loop zones as bands, worst runs **verbatim**, a `report ⇄ enforce` lever, a `⟳ re-convert` remedy) + the verdict on the ship receipt (`index.html`/`main.js`/`styles.css`). **Enforcement wired default-off:** `convert_and_ship.audit_mode()` + `_enforce_hold()` park a `fail` in `held/<sha16>/` at all 3 ship sites (report = verified no-op); `fidelity_audit.degeneration()` gained `md_lines` for the map. Verified: clippy `-D warnings` clean, `py_compile` + `audit_mode()`→`report`, `main.js` parses. **NOT yet built/relaunched** — `npm run tauri build` + the kill-widget rebuild ritual + the live Beer remedy test are Rab's next step. Remedy's vault swap still bounded by THE SUPERSEDE GAP.
- ✅ **S32: live-test hardening + widget rebuild 2026-07-21.** Four defects found by running the installed widget end to end, all fixed + verified + committed (`eb4dd87`): (1) **autostart crash** on a Start-menu launch — windowless spawn inherited dead stdio → `Stdio::null()` in watcher.rs/preflight.rs; (2) **UI freeze** on an offline vault host — `vault_check`/`vault_pull` now async + spawn_blocking (off the main thread); (3) **clean-lane VRAM thrash/timeout** on figure-dense PDFs — `route()` now caps the clean-lane Marker batch (live-verified ~8 GB peak, was 9.9); (4) **audit false positives** on a table/heading-dense book — `degeneration()` recalibrated (docs/15 §9.2: zlib **AND** trigram + contiguous-run line check; re-verified Beer flags, other 4 clear). Widget **rebuilt** (fresh exe + installer, Rust fixes baked in). **AWAITING Rab: run the new installer** — `…\target\release\bundle\nsis\File Portal_0.1.0_x64-setup.exe` → Start-menu launch = a self-sufficient widget (autostart survives, no freeze, capped converts, recalibrated audit).
- ✅ **S33: the Opsroom — a quarantined control-panel dashboard prototype 2026-07-21 (overnight, autonomous).** A professional, self-contained, zero-dependency dashboard (`prototypes/control-panel/opsroom/opsroom.html`): the 6-station line, a live **canvas transit viewer**, golden-signal KPI tiles, convert-station progress, the Survival Audit (verdicts + damage map), a live event stream. Theme-aware, reduced-motion-safe, palette-cached. Design lineage (researched; sources in `DESIGN.md`): Project Cybersyn's Opsroom × ISOTYPE × modern observability × Linear × the Claude Design System — "a control room for a viable system, in the lineage of the one Beer built." New **`prototypes/` quarantine section** (category/name; zero pipeline coupling; CI-untouched). Published as an Artifact. **Quarantined + disposable** — reads/triggers nothing. **AWAITING Rab's verdict**; if it lands, wire to the existing `invoke()` projections (`line_state`/`assay_status`/`shift_summary`/`last_receipt`).
- ✅ **S34: the Control Room becomes the widget's face 2026-07-22 (autonomous).** Graduated the merged Claude-Design *Control Room* artifact into the live widget as a `Dock ⇄ Room` surface switch — Rab's own recommendation (the vanilla *lift*: lift the source object's logic + tokens + markup, drop its React runtime, swap its simulation for the existing `invoke()` projections). New **`room.js`** rebuilds the source object's `renderVals()` shape from real commands: six-station rail, golden-signal KPI band, convert station, the full Survival-Audit evidence card, live event stream. New **`room.rs`** adds two read-only projections — `room_metrics` (throughput / median s-per-page / survival average / recent audits / vault count, from `events.jsonl` + manifests + the Library clone) and `gpu_vram` (live `nvidia-smi`). Token layer (dark/light + clay/indigo/teal) lifted into `styles.css`; Dock left pixel-stable. **The pipeline was never touched** (projection law; `windows-converter/` untouched in git). Verified: mock harness on the real snapshot (0 console errors; fixed a light-mode `.ac-*` contrast bug), `clippy -D warnings` clean, `tauri build` green, and **LIVE in the real Tauri app** (VRAM 1.9/10 GB from nvidia-smi, VAULT 4 from the Library, survival avg 0.69, real event stream, Cybernetics `fail` in terracotta). Every pipeline segment tested green (converter/formatter compile + watcher watching; vault clone healthy; ThinkPad **active over Tailscale**). **The installed widget was updated in place (SHA256-verified copy) + relaunched — it is running now.** Fresh installer staged: `…\target\release\bundle\nsis\File Portal_0.1.0_x64-setup.exe`. Design record + build audit: **docs/16-control-room-face.md**. Deferred to next MAJOR installments (docs/16 §8): the Wall surface, the canvas transit belt, the drill-down file explorer, live convert page %.
- ✅ **S35: the surface trio completed — the Wall + the canvas transit belt 2026-07-22 (autonomous).** Continuing docs/16 §8 #1. Added the third density to the `Dock ⇄ Room ⇄ Wall` switch: **Wall** = a glanceable across-room projection (giant system verdict — terracotta only on attention/fail — the six stations as big dots + three hero numbers: survival avg / throughput / vault; window resizes to 900×500). The **canvas transit belt** sits under the Room's station rail as an *ambient activity projection* — chip count/tint reflect real in-flight work (drop_waiting / converting / gate / held), empty when the watcher is down; reduced-motion-safe, palette-cached, persistent chips across the poll's `innerHTML` redraw. The Room header verdict now reflects real state (viable/attention/paused). **Frontend-only — no Rust, pipeline untouched.** Verified: harness on the real snapshot (0 console errors, dark+light), `node --check`, `tauri build` green, and **LIVE in the real widget** (Dock⇄Room⇄Wall all switch; belt animating; Wall "ATTENTION" on the real Cybernetics hold; live VRAM 1.4/10, survival 0.69, vault 4). **Installed widget updated in place (SHA256-verified) + running (Dock, tucked top-left).** Design record: docs/16 (§8 #1 shipped).
- ✅ **S36: the drill-down observation system 2026-07-22 (autonomous).** docs/16 §8 #2. Clicking a Room station flip-expands (transform-origin at the click) into a **live, accurate on-disk file tree** — a real granularity/observation surface, not a simulation. New read-only `room::station_tree(seg)` (`room.rs`) walks the real directories per station: vault→`Library/Inbox/*`, assay→`held/*` (+ the manifest's real degeneration zones) + recent verdicts, convert→`drop/`/`.gpu-lock`/`drop/done/`/`anchor/`, gate→`pending/*`, ship→last-shipped, intake→`drop/`+`drop/failed/`. Nodes carry true byte sizes, manifest fields (lane/pages/sha/engine), the analyst pass/reject/fail summary, and verbatim degeneration zones (zlib/tri×/chars/excerpt) with survival/verdict colour. Frontend (`room.js`): flip-open overlay + recursive collapsible tree (stable name-hash ids) + Esc/backdrop/× close + 4 s live re-read. **Read-only; pipeline untouched.** clippy `-D warnings` clean, `tauri build` green; verified in the harness (0 console errors) + **LIVE in the real widget** (Assay drill: held Cybernetics real .md 155 KB / assets 92 / zones @1014,2400 == manifest; Convert drill: anchor analyst 270✓22🛡10✗). Installed widget updated in place (SHA256) + running.
- ✅ **S37: orphan-watcher shutdown FIXED + Control Room finished 2026-07-22 (autonomous).** (a) **The live PDF test** (S36 payoff): re-dropped bojieli (dedup-safe) — the **observation system tracked it accurately live** (Convert drill showed drop→converting; Assay updated to bojieli 0.764 flag), but the convert **thrashed**: force-killing the widget ~5× this session (to adopt each rebuild) orphaned watchers (graceful `watcher::stop` skipped on force-kill), and 4 orphans raced the same file on the 10 GB GPU. Recovered (sweep + relaunch one); the **clean re-run succeeded end-to-end** (convert 73 s → audit → ship, sha `21bfdffc` dedup-skip, vault stayed 4). (b) **The fix** (`watcher.rs`): the watcher + its Marker subprocesses run in a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; the widget holds the sole handle for its life, so it dies with the widget by ANY means. **Proven live**: `Stop-Process -Force` — incl. **mid-convert** — takes watcher + Marker to zero. ⏻ pause unchanged (widget alive → in-flight convert finishes). Adds `windows-sys` (already in lock). (c) A **live convert progress bar** in the Room (elapsed ÷ measured ETA; `convert_elapsed_s` in `line_state`; capped 95 % until `converted`). clippy `-D warnings` clean, `tauri build` green; installed widget updated (SHA256) + running. **The Control Room is complete: Dock/Room/Wall + belt + drill-down + robust lifecycle.**
- ✅ **S38: GPU telemetry sparkline 2026-07-23 (Desktop, Rab present).** docs/16 §8 #4. The Room's GPU VRAM tile now draws a **rolling sparkline** (was a bare gauge): a bounded module ring (`vramHist`, 48) fed one sample per poll — the poll loop IS the sampler, no always-on backend thread — on a **fixed 0–100 % scale** so height = true card-fullness (idle low, a convert spikes; honest vs. the autoscaled throughput/median tiles). `room.rs::gpu_vram()` extended to also report **utilization + temperature** (`{used,total,util,temp}`), shown on the header GPU stat; `sparkSvg` gained an optional fixed-domain param; gauge is the first-poll fallback. Read-only projection; pipeline untouched. Harness-verified (0 console errors; ring accumulates across polls; fixed-scale Y-coords exact; gauge→sparkline; util/temp in dark+light; the other two sparklines unregressed), `clippy -D warnings` clean, `tauri build` green. **Installed widget swapped in place (SHA256 `DC26F26D…`) + relaunched (PID 28148) — running the S38 build now**; the S37 Job Object re-confirmed live (the force-stop took the watcher + its child too). Close `6dc8813`.
- ✅ **S39: widget resize fix 2026-07-23 (Desktop, Rab present).** Rab-reported: the widget "defaulted to a size" — dragging an edge to enlarge it reverted. Cause: `reflow()` (main.js) re-asserted `setSize(480, content)` on nearly every poll (via `pfCheck → pfRender → pfResize → reflow`, even empty-queue) and fired regardless of surface, pinning width to 480 + fighting the drag. Fix (frontend-only, no Rust): detect a manual resize via `getCurrentWindow().onResized` (event dims vs. the last size WE applied + a suppress-window for the settle echo), **remember it per surface** (`userSize.{dock,room,wall}`); `reflow()` now Dock-only and, once user-sized, only **grows** height to prevent a clip (never shrinks/never touches width); surface switches restore the remembered size (else default Dock content-fit / Room 760×600 / Wall 900×500). **Verified LIVE:** a programmatic resize to 796×639 **held across 13 s of polling** (was reverting to ~496); boot log recorded `user-sized dock → 780×631`. `node --check` clean, `tauri build` green. Installed widget swapped (SHA256 `BDA346A6…`) + relaunched fresh (PID 25504). Close `9cc0f31`.
- ✅ **S40: start centered on monitor 1 2026-07-23 (Desktop, Rab-requested).** Follow-up to S39 (sizes don't persist → every launch should start predictably). New `main.js::centerOnPrimary()` runs once at boot (after the initial reflow settles height): `primaryMonitor()` (pos+size) + `outerSize()` → `setPosition` to the monitor-center, all physical px (DPI-correct; lands on the primary regardless of a 2nd monitor's offset). Launch-only; the user can still drag it anywhere (moves untracked). Added `core:window:allow-set-position` (regenerated `gen/schemas/capabilities.json`). **Verified LIVE:** relaunched window center = **(1280,720)** = the 2560×1440 primary's exact center, on DISPLAY1. `node --check` clean, `tauri build` green. Installed widget swapped (SHA256 `11038318…`) + relaunched (PID 10116, centered). Close `ba922f8`.
- ✅ **S41: GPU telemetry stream complete 2026-07-23 (Desktop).** docs/16 §8 #4 fully done. Gave **utilization + temperature their own rolling sparklines**: a unified **GPU telemetry strip** in the Room (VRAM % / GPU util % / Temp °C, fixed scales 0–100 / 0–100 / 30–95 °C, clay under pressure >92/>95/>83, else flow). `sampleGpu` feeds three rings (`vramHist`/`utilHist`/`tempHist`) from the same one read per poll — no backend thread. The VRAM sparkline graduated from the KPI tile into the strip (tile → gauge). Frontend-only (`room.js` + `styles.css`); read-only projection. Harness-verified (0 console errors; all three accumulate on fixed scales — temp Y-coords confirm the 30–95 domain; util clay at 98%; dark+light), `tauri build` green. Installed swapped (SHA256 `55128BE2…`) + relaunched (PID 22152). Close `a0554dd`. Deferred by choice: always-on backend sampler; throughput/median rolling-window rework (already an events-tail rolling window).
- ▶ Next up: **S42 = true per-page convert %** (§8 #3, fragile Marker `--disable_tqdm`→streamed-tqdm parsing of surya's multi-stage bars; touches the core convert — fail-safe Popen streaming) · ThinkPad **exporter supersede flow** (THE SUPERSEDE GAP, §8 #5 — widget side done via ⟳ re-convert; the exporter auto-swap is ThinkPad-only) · the **Beer** remedy loop (depends on the supersede). Phase 5 Forgejo: deferred. Carry-forward: `min_chars_per_page=100` provisional.

---

## Change Ledger

*Append one row at session close, after the closing commit exists. The SHA is the closing
commit; "Docs touched" covers the whole session (open plan → close). Verify a row with
`git merge-base --is-ancestor <SHA> HEAD`.*

| Date (UTC) | Machine | Milestones closed | Docs touched | Closing SHA |
|---|---|---|---|---|
| 2026-07-07 | ThinkPad | L1–L4 | CLAUDE_README | d4841e0 |
| 2026-07-07 | ThinkPad | L5, L6 | CLAUDE_README, CHANGELOG, README, docs/00, docs/01, docs/05, docs/10, linux-receiver/README | 6ffd910 |
| 2026-07-08 | Desktop | W5 (transport) | CLAUDE_README, coordination | f9ad76a |
| 2026-07-08 | ThinkPad | L6.5 | CLAUDE_README, CHANGELOG, coordination | 28057f8 |
| 2026-07-08 | Desktop | W6 | CLAUDE_README | e302785 |
| 2026-07-10 | ThinkPad | L7–L10, Defect A, Defect B, Decision #3, Change Ledger + §4 | CLAUDE_README, CHANGELOG, DOCS-AUDIT-CHANGELOG, docs/10, coordination, .gitignore | c718ed2 |
| 2026-07-10 | Desktop | W7 | CLAUDE_README, CHANGELOG | 2a921ae |
| 2026-07-10 | ThinkPad | Decisions #4/#5/#6, Part 4 groundwork recorded (docs only; close commit recovered 2026-07-11) | CLAUDE_README | 7b4c286 |
| 2026-07-11 | ThinkPad | L11, L12 (Part 4 Linux CLOSED — L1–L12 all done), exporter event-stall fix | CLAUDE_README, CHANGELOG, docs/10, linux-converter/README | 10f6bc6 |
| 2026-07-11 | Desktop | Vault consumption verified (pipeline loop CLOSED end to end) | CLAUDE_README | fb2570d |
| 2026-07-12 | Desktop | First real ingest; defects L13 (spaces) + L14 (INBOX_REL) found, proven, filed | CLAUDE_README, coordination ×2 | ef5a8e8 |
| 2026-07-12 | ThinkPad | L13, L14 (fixed + live-verified; spaces workaround retired) | CLAUDE_README, CHANGELOG, coordination | 94db496 |
| 2026-07-12 | Desktop | L13/L14 re-verified with worst-case name; EXPORT-SKIP dedup confirmed | CLAUDE_README | 25e8688 |
| 2026-07-12 | Desktop | W8 (Add-to-Library button); L15 found + Desktop-mitigated + filed | CLAUDE_README, CHANGELOG, coordination | 1e33b11 |
| 2026-07-12 | Desktop | W8 console-flash regression fixed (CREATE_NO_WINDOW, all spawn sites) | CLAUDE_README, CHANGELOG | 99a5271 |
| 2026-07-12 | ThinkPad | L15 (fixed + live-verified; interiors Windows-clean at source) | CLAUDE_README, CHANGELOG, coordination | d53c152 |
| 2026-07-13 | Desktop | CI python+rust repaired (first contact); **PR #1 MERGED to master (`7c006f2`)**; fix/widget-blank-window deleted on origin; 2a1778f merge accounted | CLAUDE_README, CHANGELOG | b340684 |
| 2026-07-18 | Desktop | GPU revamp scoped (docs/11); Phase 0 PASSED (torch cu128 on 3080); Phase 1 Marker A/B = mixed pass, force_ocr ruled out at defaults | CLAUDE_README, docs/11 | 071a918 |
| 2026-07-18 | Desktop | Phases 1.5a/1.5b/2 CLOSED (strip-OCR fix proven; born-digital outright win; Ollama handoff PASSED 52.6 tok/s; LLM link hazard + factory design note) | CLAUDE_README, docs/11 | e26255c |
| 2026-07-19 | ThinkPad | Phase 3 CLOSED (specs; phi4-mini CPU bench — tagging gate PASS, analyst ruled out; ChromaDB+MiniLM PASS; red flag #2 resolved; analyst→Desktop GPU recommendation) | CLAUDE_README, docs/11 | e20115e |
| 2026-07-19 | Desktop | Phase 4 slices 1+2 (windows-converter: E2E EXPORTED 6008eb66 + EXPORT-SKIP + cross-machine dedup vs dbcce92c; link-fenced analyst 7/7) | CLAUDE_README, docs/11, docs/12, .gitignore | 74ec982 |
| 2026-07-19 | Desktop | S16: Gemini analyst backend (fence 7/7, 186.7 chars/s) + pre-flight estimator; entitlement verified (AI Plus ≠ API); rclone remote + first anchor-mirror | CLAUDE_README | 4221f82 |
| 2026-07-19 | Desktop | S17: drop-folder watcher LIVE (E2E: drop→convert→ship→EXPORT-SKIP); Beer local analyst 44/47 (3 fence-saves); estimator free-tier-window aware | CLAUDE_README | b47bc87 |
| 2026-07-19 | Desktop | S18: pre-flight analyst card LIVE (pending queue + routing UI + detached resume; E2E via CLI-simulated buttons); CHANGELOG landed | CLAUDE_README, CHANGELOG | 147a250 |
| 2026-07-19 | Desktop | S19: docs/13 control-room design (projection principle, line grammar, analyst programs, metrics doctrine, launchers, events keystone) | CLAUDE_README, docs/13 | 8e8d2de |
| 2026-07-19 | Desktop | S20: foundation — events.jsonl stream + emitters, analyst programs (prompt files), widget-owned watcher (autostart verified live), shift line | CLAUDE_README | 671ee9a |
| 2026-07-19 | Desktop | S21: line strip (5 stations, filesystem projection), gate mode selector, failed-tray click, Obsidian/ZenNotes launchers | CLAUDE_README | 7635e1a |
| 2026-07-19 | Desktop | S22: ETA ranges from measured rates, auto-route rule (rules.json), ship receipts, failed tray; orphan-watcher sharp edge filed | CLAUDE_README | a589528 |
| 2026-07-19 | Desktop | S23: docs/14 remote projection design (phone window over tailnet; ThinkPad-hosted; corrections to relayed plan; think-only) | CLAUDE_README, docs/14 | 65fe7ff |
| 2026-07-19 | Desktop | S24: launch-context bug fixed — stale Explorer env (login-time PATH) broke shortcut launches; registry hydration at boot + no-prompt git + boot-log instrumentation; preview-pane mirage identified | CLAUDE_README | 8b65af1 |
| 2026-07-19 | Desktop | S25: ⚡ GPU → Vault tile (convert-gpu → local drop, line as status) — Marker is on the widget | CLAUDE_README | 2c7de12 |
| 2026-07-19 | Desktop | S26: stage ticker + ⚙ convert countdown (the line narrates READY→CONVERTING→…→COMPLETE); first real ⚡ drop (439pp) at the gate | CLAUDE_README | 2b965ca |
| 2026-07-20 | Desktop | S27: degeneration findings F1–F5 filed (vaulted Beer 12.3% two-zone OCR loops, user-found; other 3 books clean; thresholds separate at zlib<0.20 OR tri≥40) + docs/15 Survival Audit spec committed; retroactive CHANGELOG entry for post-S26 `e7ea85a` ship fix caught by §4 | CLAUDE_README, docs/15, coordination, CHANGELOG | 0c1138c |
| 2026-07-20 | Desktop | S28: Survival Audit BUILT (fidelity_audit.py per docs/15) + report-only crash-safe hooks in convert_and_ship.py (fidelity manifest block + audit events, verdict gates nothing); calibrated — degeneration tripwire production-ready (flags Beer only), survival is report-only localizer; awaiting Rab threshold sign-off | CLAUDE_README, CHANGELOG, fidelity_audit.py, convert_and_ship.py | 35a6d7c |
| 2026-07-20 | Desktop | S29: widget "old version" ghost SOLVED = MSIX AppData redirection (Claude's tools sandboxed → AppData writes hit the package container, not Rab's real config; scope=AppData only). Fixed by Rab copying good config to real AppData unpackaged; ⚡ tile back+persistent. Honest correction of a wrong stale-frontend-embed theory (brotli-compressed-asset grep). No source changed; permanent code fix declined (procedural rule in memory). | CLAUDE_README | c2c11d3 |
| 2026-07-20 | Desktop | S30: Survival Audit enforcement SIGNED (degeneration + analyst near-exact only) → compute_verdict rewritten + verified over all 4 vaulted books (Beer→fail zlib.003/tri×2267, other 3→pass, zero FP); enforcement = separate default-off lever (audit-mode.txt); the Assay widget projection designed (docs/15 §13). No pipeline behavior change (verdict-only). | CLAUDE_README, CHANGELOG, docs/15, fidelity_audit.py | c5cebe0 |
| 2026-07-20 | Desktop | S31: the Assay BUILT (docs/15 §13) — assay.rs + 4 commands, ◎ station + evidence card (damage map + verbatim runs + report⇄enforce lever + ⟳ re-convert) in the frontend, default-off enforcement (audit_mode/_enforce_hold park a fail in held/) at all 3 ship sites; degeneration() gained md_lines. clippy -D warnings clean, py_compile, main.js parses; tauri build + live Beer test pending (Rab, rebuild ritual). | CLAUDE_README, CHANGELOG, assay.rs, main.rs, index.html, main.js, styles.css, convert_and_ship.py, fidelity_audit.py | c81c102 |
| 2026-07-21 | Desktop | S32: live-test hardening — 4 defects fixed (autostart `Stdio::null`, vault `async`+`spawn_blocking`, clean-lane batch cap [~8 GB verified], degeneration recalibration docs/15 §9.2 [zlib AND trigram + contiguous-run; Beer flags, 4 books clear]) + widget rebuilt; fresh installer staged for Rab | CLAUDE_README, CHANGELOG, docs/15, watcher.rs, preflight.rs, main.rs, convert_and_ship.py, fidelity_audit.py | 650d067 |
| 2026-07-21 | Desktop | S33: the Opsroom — a quarantined control-panel dashboard prototype (`prototypes/control-panel/opsroom/`); pipeline segmentation + live canvas transit viewer + golden-signal KPIs + Survival Audit + event stream; researched lineage (Cybersyn Opsroom × ISOTYPE × observability × Linear × Claude Design System); new `prototypes/` quarantine section; published as an Artifact; disposable, zero pipeline coupling | CLAUDE_README, CHANGELOG, prototypes/** | 898d5af |
| 2026-07-22 | Desktop | S34: the Control Room becomes the widget's face — `Dock ⇄ Room` surface switch; new `room.js` (Room render: station rail + golden-signal KPIs + convert station + Survival-Audit evidence card + event stream) rebuilding the source object's `renderVals()` shape from live `invoke()`; new `room.rs` (`room_metrics` + `gpu_vram`, read-only projections); token layer (dark/light + accents) into `styles.css`, Dock pixel-stable; pipeline untouched (projection law); verified LIVE in the real Tauri app; installed widget updated in place (SHA256-verified) + running; every pipeline segment tested green; installer staged | CLAUDE_README, CHANGELOG, docs/16, prototypes/control-panel/control-room, room.js, room.rs, main.rs, main.js, index.html, styles.css | 5cfaec4 |
| 2026-07-22 | Desktop | S35: the surface trio completed — the `Dock ⇄ Room ⇄ Wall` switch. **Wall** = glanceable across-room projection (giant system verdict + six station dots + three hero numbers, window 900×500). **Canvas transit belt** under the Room's rail = ambient activity projection (chips reflect real in-flight work; empty when watcher down; reduced-motion-safe, palette-cached, persistent across the poll). Room header verdict now real (viable/attention/paused). Frontend-only, no Rust, pipeline untouched. Verified in harness (0 errors) + LIVE in the real widget; installed widget updated in place (SHA256) + running | CLAUDE_README, CHANGELOG, docs/16, room.js, main.js, index.html, styles.css | 0508221 |
| 2026-07-22 | Desktop | S36: the drill-down observation system (docs/16 §8 #2) — click a Room station → flip-expand into a **live, accurate on-disk file tree**. New read-only `room::station_tree(seg)` walks the real dirs per station (vault/held/anchor bundles with manifest fields + analyst summary + verbatim degeneration zones + true byte sizes; drop/pending/failed; 4 s live re-read; collapse persists via name-hash ids). Frontend flip-open overlay + recursive tree in `room.js`. Read-only projection, pipeline untouched. clippy `-D warnings` clean; verified in harness (0 errors) + LIVE (Assay/Convert drills match on-disk manifests). Installed widget updated (SHA256) + running | CLAUDE_README, CHANGELOG, docs/16, room.rs, main.rs, room.js, styles.css | cf218de |
| 2026-07-22 | Desktop | S37: orphan-watcher shutdown FIXED + Control Room finished. Live PDF test found force-killed widgets orphan the Python watcher (graceful `stop` skipped) → 4 orphans thrashed the GPU. Fix (`watcher.rs`): watcher + Marker subprocesses run in a Windows Job Object with `KILL_ON_JOB_CLOSE` → die with the widget by ANY means (proven live, incl. mid-convert → tree to 0); ⏻ pause unchanged; adds `windows-sys` (already in lock). Also a live convert progress bar in the Room (`convert_elapsed_s` in `line_state`). Clean re-run of the PDF test succeeded end-to-end (convert→audit→ship, dedup, vault 4). clippy `-D warnings` clean; installed widget updated (SHA256) + running | CLAUDE_README, CHANGELOG, docs/16, watcher.rs, line.rs, Cargo.toml, room.js, styles.css | dd01bf8 |
| 2026-07-23 | Desktop | S38: GPU telemetry sparkline (docs/16 §8 #4). The Room's GPU VRAM tile draws a **rolling sparkline** (was a bare gauge): a bounded module ring (`vramHist`, 48) fed one sample per poll (the poll loop IS the sampler — no always-on backend thread), on a **fixed 0–100 % scale** so height = true card-fullness (idle low, convert spikes; honest vs. the autoscaled throughput/median tiles). `gpu_vram()` extended to also report **utilization + temperature** (`{used,total,util,temp}`) → header GPU stat; `sparkSvg` gained an optional fixed-domain param; gauge = first-poll fallback. Read-only projection; pipeline untouched. Harness-verified (0 console errors; ring accumulates; fixed-scale Y-coords exact; util/temp dark+light; other sparklines unregressed), clippy `-D warnings` clean, `tauri build` green. **Installed widget swapped in place (SHA256 DC26F26D…) + relaunched (PID 28148) — S38 build running** (Rab approved; S37 Job Object re-confirmed live — force-stop took the watcher + child too) | CLAUDE_README, CHANGELOG, docs/16, room.rs, room.js | ae2b224 |
| 2026-07-23 | Desktop | S39: widget resize fix (Rab-reported). The widget "defaulted to a size" — a manual drag reverted because `reflow()` re-asserted `setSize(480, content)` on nearly every poll (via `pfCheck → pfRender → pfResize → reflow`, even empty-queue) and fired regardless of surface. Fix (main.js, frontend-only, no Rust): detect a manual resize via `getCurrentWindow().onResized` (event dims vs. last-applied + a suppress-window for the settle echo), remember per surface (`userSize.{dock,room,wall}`); `reflow()` now Dock-only + grow-only (never shrinks/touches width once user-sized); surface switches restore the remembered size (else default Dock content-fit / Room 760×600 / Wall 900×500). Verified LIVE: programmatic resize to 796×639 held across 13 s of polling (was reverting to ~496); boot log recorded `user-sized dock → 780×631`. `node --check` clean, `tauri build` green; installed widget swapped (SHA256 BDA346A6…) + relaunched fresh (PID 25504) | CLAUDE_README, CHANGELOG, main.js | 9cc0f31 |
| 2026-07-23 | Desktop | S40: widget opens centered on the primary monitor (monitor 1), Rab-requested follow-up to S39. New `main.js::centerOnPrimary()` at boot (after the initial reflow settles height): `primaryMonitor()` pos+size + `outerSize()` → `setPosition` to the monitor-center, all physical px (DPI-correct; lands on the primary regardless of a 2nd monitor's offset). Launch-only; moves untracked. Added `core:window:allow-set-position` (regenerated `gen/schemas/capabilities.json`). Verified LIVE: relaunched window center = (1280,720) = the 2560×1440 primary's exact center, on DISPLAY1. `node --check` clean, `tauri build` green; installed swapped (SHA256 11038318…) + relaunched (PID 10116) | CLAUDE_README, CHANGELOG, main.js, capabilities/default.json, gen/schemas/capabilities.json | ba922f8 |
| 2026-07-23 | Desktop | S41: GPU telemetry stream complete (docs/16 §8 #4). Gave utilization + temperature their own rolling sparklines — a unified GPU telemetry strip in the Room (VRAM % / GPU util % / Temp °C; fixed scales 0–100 / 0–100 / 30–95 °C; clay under pressure >92/>95/>83). `sampleGpu` feeds three rings (`vramHist`/`utilHist`/`tempHist`) from the same one nvidia-smi read per poll (no backend thread). The VRAM sparkline graduated from the KPI tile into the strip (tile → gauge, no duplication). New `.room-gpu`/`.rg-*` CSS. Frontend-only, read-only projection. Harness-verified (0 console errors; all three accumulate on fixed scales — temp Y-coords confirm the 30–95 domain; util clay at 98%; dark+light), `tauri build` green; installed swapped (SHA256 55128BE2…) + relaunched (PID 22152) | CLAUDE_README, CHANGELOG, docs/16, room.js, styles.css | a0554dd |

---

## Active Branch: `feat/library-pipeline`

Both machines work this branch. **Pull before every push.**
- Linux owns: `linux-receiver/`, `linux-converter/`, `config/`
- Windows owns: `windows-widget/`

No file conflicts if each machine stays in its lane.

---

## MACHINE: DESKTOP-OBTQIRD (Windows)

*Claude Code in `C:\Users\Rabbiallah\Projects\file-portal\windows-widget`*

### Part 1 — Windows Tasks (do these first)

- [x] **W1 — Make transfer atomic** (fixes file-corruption race)
  File: `src-tauri/src/transfer.rs`
  - Build `remote_tmp = "{remote_dir}/.part-{filename}"`
  - Set `remote_cmd = "mkdir -p {dir} && cat > {tmp} && mv -f {tmp} {final}"` (quote tmp and final via `remote_path_expr`)
  - Why: receiver currently sees `on_created` on a half-written file; atomic rename hits the safe `on_moved` path

- [x] **W2 — Stream, don't buffer** (prevents OOM on large files)
  Same file: `src-tauri/src/transfer.rs`
  - Replace `read_to_end` into a `Vec` with `std::io::copy(&mut local_file, &mut stdin)`

- [x] **W3 — Widget window controls** (independent quick win — no separate rebuild)
  - `src/index.html`: add `<div id="titlebar" data-tauri-drag-region>` containing a title span and `#min-btn` button (button has NO drag attribute)
  - `src/styles.css`: style `#titlebar` and `#min-btn` hover state
  - `src/main.js`: wire `#min-btn` to `getCurrentWindow().minimize()`
  - `src-tauri/capabilities/default.json`: `core:window:allow-start-dragging` + `core:window:allow-minimize`
  - `tauri.conf.json`: window `height` bumped to 186

- [x] **W4 — Rebuild** after W1-W3:
  ```
  npm run tauri build
  ```

- [x] **W5 — E2E test** — RUN 2026-07-08 (user present, access approved). Result: **transport PASS, UI feedback BLOCKED**
  - .pdf → transferred byte-exact, ALLOCATED to `sorted/documents/` on ThinkPad (log 04:22:16 UTC) ✅
  - .xyz → transferred byte-exact, allocated to `sorted/misc/` (NOT rejected — branch code never emits "rejected" for unmatched extensions) ⚠️
  - Green ✓ / red ✗ never appeared: the status.json writer lives only on `master` (commit `0c3a074`), never merged into this branch → status.json stale since the 7/7 service restart. See `coordination/messages/2026-07-08T00-30--desktop-to-linux--w5-results-status-feed-regression.md`
  - **Re-run the visual check after Linux L6.5 lands**

### Part 2 — Windows Tasks (after Part 1 Linux is done)

- [x] **W6 — Add Convert tile** — DONE 2026-07-08 (commit `af904a2`), E2E verified
  - Added to live `%APPDATA%\file-portal\config.toml`, `config.rs` `AppConfig::default()`, and `portals.json`
  - Rebuilt (clippy clean, 2 bundles); 5th tile "To Vault" 🔁 renders (tiles are `flex: 1` — no window resize needed)
  - Drop test: .pdf → tile went GREEN "✓ w6-convert-test.pdf → pipeline/convert-inbox/..." in ~4s; allocator hop + converter "would convert" both logged on ThinkPad at 04:56:45 UTC
  - **This also closes the W5 visual re-check** — L6.5's status feed drove the green ✓ live. Part 2 "Done when" = fully closed.

### Part 3 — Windows Tasks (after Part 3 Linux is done)

- [x] **W7 — Add Convert-Scan tile** — DONE 2026-07-10 (commit `1d15b16`), E2E verified with
  force-OCR semantics per the 2026-07-09T23-05 coordination message: `category = "convert-scan"`,
  `label = "Force OCR → Vault"`, `icon = "🔍"` added to live `%APPDATA%\file-portal\config.toml`,
  `config.rs` `AppConfig::default()`, and `portals.json`; no `main.js` change. Drop test: digital
  .pdf → green ✓ "→ pipeline/convert-scan-inbox/…"; converter probe 277 chars/page but lane
  forced scan (`lane_reason: user_forced_scan`, `ocr_dpi: 300`, yield 279), bundle in
  anchor+staging, manifest SHA-256 = local file's hash.

---

## MACHINE: ThinkPad C14 (Arch Linux)

*Claude Code in `~/Projects/file-portal` (or wherever the repo is cloned)*

### Part 1 — Linux Tasks ⚠️ GATE — must complete before anything else ⚠️

- [x] **L1 — Kill quarantine loop** (critical bug — stuck files keep re-processing)
  File: `linux-receiver/allocator/config.py`
  Change:
  ```python
  # OLD
  quarantine = root / "inbox" / "quarantine"
  # NEW
  quarantine = root / "quarantine"
  ```
  Update `Paths.from_root` and `ensure_exist` accordingly.
  Why: quarantining a file fires `on_moved` inside the watched tree, which re-handles it and un-quarantines it.

- [x] **L2 — Ignore temp/dotfiles in watcher**
  File: `linux-receiver/allocator/main.py`, inside `_handle` method
  Add at the very top:
  ```python
  if file_path.name.startswith("."):
      return
  ```

- [x] **L3 — Enable persistence**
  ```bash
  sudo systemctl enable --now tailscaled
  sudo loginctl enable-linger "$USER"
  ```
  Verify:
  ```bash
  systemctl is-enabled tailscaled                         # → enabled
  loginctl show-user "$USER" --property=Linger            # → Linger=yes
  systemctl --user is-enabled file-portal-allocator       # → enabled
  ```

- [x] **L4 — Put linger in installer**
  File: `scripts/linux/bootstrap-arch.sh`
  Add: `sudo loginctl enable-linger "$USER"`
  (NOT `install.sh` — that script refuses sudo)

**Done when Part 1:** 200MB+ file transfers without truncation; oversized file lands in `quarantine/` and stays; allocator + tailscaled survive a reboot with no login.

### Part 2 — Linux Tasks

- [x] **L5 — Route the convert category**
  File: `linux-receiver/config/rules.toml`
  ```toml
  [[rule]]
  category = "convert"
  match = ["*.pdf", "*.epub", "*.docx"]
  destination = "pipeline/convert-inbox"
  ```

- [x] **L6.5 — Port status feed from master `0c3a074` into the branch** — DONE 2026-07-08, live-verified
  (`allocated` + `rejected` events in status.json, 24/24 tests, service restarted).
  Results: `coordination/messages/2026-07-08T04-50--linux-to-desktop--l65-done-status-feed-live.md`

- [x] **L6 — Scaffold converter service**
  New: `linux-converter/` mirroring `linux-receiver/` structure
  Watches: `~/file-portal/pipeline/convert-inbox`
  At this stage: only LOG "would convert <path>" — no engine
  Enable: `systemctl --user enable --now file-portal-converter`

### Part 3 — Linux Tasks (HEAVY — dedicate a full session after reset)

- [x] **L7 — Install engines** — DONE 2026-07-09/10. `pymupdf4llm 1.28.0` into
  `linux-converter/.venv` (+`requirements.txt`) — NOT `--break-system-packages`; the service
  runs from its venv. `tesseract 5.5.2` + `tesseract-data-eng`; `pandoc 3.6` (Arch package is
  `pandoc-cli`). Import order `pymupdf.layout` → `pymupdf4llm` encoded in
  `converter/engines.py` (1.28 auto-satisfies it, kept as insurance).
- [x] **L8 — Dispatch by extension** — DONE 2026-07-10, live-verified: three `converter.log`
  lines at 00:41/01:02 UTC naming `engine=pymupdf4llm` (.pdf, .epub) and `engine=pandoc`
  (.docx). First-match dispatch mirrors `allocator/rules.py`.
- [x] **L9 — Two lanes + probe** — DONE 2026-07-10, live-verified: probe logged 1388.0
  chars/page (digital) vs 0.0 (scan); scan on Clean REROUTED to `convert-scan-inbox` with an
  `allocated` status event carrying `dest`; Scan lane OCR'd it (yield 929.0); terminal test:
  blank scan → exactly one REJECTED → `quarantine/`, scan-inbox empty after 75s, no loop.
  NOTE: in pymupdf4llm 1.28 the lanes are `SELECT_KEEP_OLD` vs `FORCE_DROP_OLD` — not
  `force_ocr=True`, which would KEEP a bad prior OCR layer (see CHANGELOG + coordination msg).
- [x] **L10 — Bundle output** — DONE 2026-07-10, live-verified: `tree` shows
  `<name>.md + assets/ + manifest.json` in both `library/anchor/` and `library/staging/`;
  the image link target resolved by `ls` (62,445-byte PNG); frontmatter stamped on both
  lanes' outputs; manifest carries source SHA-256 + engine/converter versions.

### Part 4 — Linux Tasks

- [x] **L11 — Exporter** — DONE 2026-07-11, live-verified. `converter/exporter.py`, a second
  watch inside the existing converter service (no third unit) + startup sweep. All Decision
  #4/#5/#6 constraints implemented: `Library/Inbox/<slug>--<sha256[:8]>/`, new-notes-only
  (pathspec-scoped, self-identifying `file-portal-converter` commits), identical-sha
  re-ingest = `EXPORT-SKIP` no-op (deduped via `git grep` over committed manifests in the
  **bare** repo, so Desktop-filed notes still count), assets nested. 8 unit tests on real
  temp git repos. Live: `EXPORTED … commit a49d49c4 pushed + blob-verified` at 21:22 UTC.
- [x] **L12 — Staging deletion** — DONE 2026-07-11, live-verified with L11: deletion fires
  only after the push succeeded AND `git cat-file -e` confirms the commit + every bundle
  file's blob in the bare repo. Git failure → `EXPORT-FAIL`, staging kept, sweep retries;
  committed-but-unpushed resumes at push (unit-tested). No tag/folder placement; no
  `[[link]]` minting.

---

## Cross-Machine Communication Protocol

### Method 1 — Git-based messages (current) ✅
Write a markdown file to `coordination/messages/`:
```
YYYY-MM-DDTHH-MM--{from}-to-{to}--{subject}.md
```
Commit and push. The other agent pulls and reads. Already in use.

### Method 2 — Tailscale SSH shared file
```bash
# write to ThinkPad from Desktop
tailscale ssh user@thinkpad "cat > ~/file-portal/coordination/state.json" < state.json
# read from ThinkPad
tailscale ssh user@thinkpad "cat ~/file-portal/coordination/state.json"
```

### Method 3 — MCP server over Tailscale (real-time, optional)
**Setup (ThinkPad):**
```bash
pip install mcp --break-system-packages
# Run a lightweight HTTP MCP endpoint on port 8765, bind 0.0.0.0
```
**Desktop agent config:**
```json
{
  "mcpServers": {
    "thinkpad-coordination": {
      "url": "http://<thinkpad-tailscale-ip>:8765/mcp",
      "transport": "http"
    }
  }
}
```
Check ThinkPad Tailscale IP: `tailscale ip -4`

---

## Open Decisions

| # | Decision | Recommended |
|---|---|---|
| 1 | Disable Tailscale key expiry on always-on nodes | Yes |
| 2 | Convert tile only vs push-from-library-on-demand | Tile only |
| 3 | Clean-lane failure: bounce whole file vs convert-and-flag | **RESOLVED 2026-07-09: neither.** Pre-flight text-layer probe; auto-route to Scan on empty (normal `allocated` hop). Scan lane is terminal — OCR failure quarantines (`rejected`). All output frontmatter-stamped. Threshold (`min_chars_per_page`, seed 100) configurable. |
| 4 | Return transport method | **RESOLVED + VERIFIED 2026-07-10: bare repo + Tailscale SSH.** Bare repo `~/file-portal/vault.git` on the ThinkPad, HEAD pinned to `refs/heads/main` (deliberate; git default was master). Seed `71cc4c5` (`.gitattributes`: `* text=auto eol=lf`, png/pdf binary) landed **before any content**; `0272f89` adds `.gitignore` for `.obsidian/`. Converter commits in the non-bare working clone `~/file-portal/vault-work`, pushes over the local filesystem. Desktop clone at `<Vault>\Library` with `core.sshCommand="tailscale ssh"` persisted in its config; host `rab@archlinux`, the same pair the widget has used since W5. **Fetch and push both confirmed.** Vault root stays a plain folder — only `Library/` is a repo, so wiki-links resolve vault-wide while git scope stays confined to machine-produced bundles. Exactly one side initializes. Invariant: the converter creates new notes only, never edits existing ones. Assets-in-repo is deliberate and irreversible. Forgejo may later serve the same bare repo as a read-only browse surface, never the write path. **GOTCHA:** opening `Library/` in Obsidian creates a stray `.obsidian/` and registers it as a separate vault, breaking wiki-link resolution from the parent. `.gitignore` guards the artifact; the vault switcher must not list Library. |
| 5 | Graph links: dense/dirty vs sparse/earned | **RESOLVED 2026-07-10: sparse.** The converter transcodes, it does not read. Mint a link only where it encodes a fact the converter knows (`![[asset]]` embeds do; `[[concept]]` links do not). Two structural reasons: (a) minted and hand-earned links are indistinguishable in the graph after the fact, so minting destroys the graph's value as a record of what was noticed — not recoverable later; (b) wiki-links mutate the note body while frontmatter does not — frontmatter is losslessly strippable, prose is not. No extraction heuristic will be added. |
| 6 | Vault placement of converted bundles | **RESOLVED 2026-07-10: single inbox, no automatic tag/folder placement.** Bundles land at `Library/Inbox/<slug>--<sha256[:8]>/`. Lane facts stay in frontmatter, not in the path — the path is the irreversible axis and lane is an ingestion detail. Assets live inside the bundle folder (`assets/`), never a shared attachments dir, so relative links survive later filing. Re-ingesting an identical `source_sha256` is a no-op with a log line, not a duplicate bundle. "Delete staging after send" fires only after the commit exists AND `git cat-file -e` confirms the blob — never on write-success alone. Content tagging is a future, separate stage that reads the markdown (Ollama batch) — never the converter's job. |

---

## Key Paths Reference

| Item | Path |
|---|---|
| Repo (Windows) | `C:\Users\Rabbiallah\Projects\file-portal` |
| Widget source | `windows-widget/src/` |
| Widget Tauri config | `windows-widget/tauri.conf.json` |
| User portal config | `%APPDATA%\file-portal\config.toml` |
| Built widget exe | `windows-widget/src-tauri/target/release/file-portal-widget.exe` |
| Coordination messages | `coordination/messages/` |
| Desktop Tailscale IP | `100.79.42.106` |
| Linux status.json | `~/file-portal/logs/status.json` |
| Library pipeline plan | `docs/10-library-pipeline-plan.md` (drop the plan doc here) |

---

## Session Log

### 2026-07-05 — Desktop agent Session 1 (Cowork/Dispatch)
**Machine:** DESKTOP-OBTQIRD (Windows)
**What was done:**
- Verified Tauri v2 build: 45s compile, 2 bundles (MSI + NSIS), no errors
- Widget launched (file-portal-widget.exe, 8.77 MB)
- Created `coordination/messages/` folder in repo
- Wrote and committed desktop build report to coordination/messages/
- Created this CLAUDE_README.md with full mission brief and session protocol
- Pushed all to `feat/library-pipeline`
**E2E test:** pending — needs user at desktop to approve File Portal access dialog

### 2026-07-05 — Desktop agent Session 2 (Cowork/Dispatch)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Audit W1-W3 code in repo; update task list; close session cleanly.
**What was done:**
- Opened transfer.rs — W1 (atomic `.part-` + `mv -f`) and W2 (`std::io::copy`) ALREADY implemented and committed
- Opened capabilities/default.json — W3 permissions (`allow-start-dragging`, `allow-minimize`) ALREADY present
- Opened index.html — W3 titlebar + min-btn ALREADY in place
- Opened tauri.conf.json — height ALREADY 186
- Updated CLAUDE_README.md: marked W1/W2/W3 [x], updated Status Summary with verified findings
- Committed and pushed session protocol update + audit results
**Verification:** Opened each file directly in Notepad and confirmed code presence — not inferred from comments.
**Next for Desktop (W4):** Run `npm run tauri build` from a terminal — ensure compiled exe includes W1-W3 (last known build was 11:10 AM, uncertain if W1-W3 were present then)
**Next for ThinkPad (L1):** open `linux-receiver/allocator/config.py`, move quarantine out of inbox tree — GATE for all other work

### 2026-07-05 — Desktop agent Session 3 (Cowork/Dispatch)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Execute W4 — run `npm run tauri build` from windows-widget/ directory.
**What was done:**
- User ran `npm run tauri build` from `C:\Users\Rabbiallah\Projects\file-portal\windows-widget`
- Rust compiled successfully in 1m 04s (release profile, optimized)
- Built: `src-tauri\target\release\file-portal-widget.exe`
- Bundled: `File Portal_0.1.0_x64_en-US.msi` and `File Portal_0.1.0_x64-setup.exe`
- Zero errors
- Marked W4 [x] in this file
**Next for Desktop (W5):** E2E test — run the widget, drop .pdf (expect green/allocated) and .xyz (expect red/rejected) on portal tiles
**Next for ThinkPad (L1):** open `linux-receiver/allocator/config.py`, move quarantine out of inbox tree — GATE for all other work

### 2026-07-07 — ThinkPad agent Session 1 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** Start L1 per task list; discovered L1/L2/L4 code already committed (e314607, drafted from desktop, never verified on Linux). Pivoted to: deploy the branch to the live service, verify L1-L3 on real hardware, close the Part 1 gate.
**What was done:**
- Checked out `feat/library-pipeline` locally (clone was on master — the running service had the OLD buggy code in memory)
- Audited e314607: L1 (quarantine = root/"quarantine"), L2 (dotfile early-return in `_handle`), L4 (linger in bootstrap-arch.sh) all present in code
- Verified L3 system state: `tailscaled` enabled, `Linger=yes`, `file-portal-allocator` enabled + active — persistence was already configured
- Restarted `file-portal-allocator` so the running process picked up the branch code; it created `~/file-portal/quarantine/` at root
- **Live gate test (all passed):** 3GB sparse file → REJECTED to `~/file-portal/quarantine/` with a single log line and STAYED (no re-processing loop); `.part-dotfile-test` → silently ignored, no log entry; `normal-test.txt` → ALLOCATED to `sorted/documents/`
- Cleaned up test artifacts and removed stale empty `~/file-portal/inbox/quarantine/` dir
- Marked L1-L4 [x]; updated Status Summary
**Verification:** Functional, on live service — not code inspection. Log lines in `~/file-portal/logs/allocator.log` at 2026-07-07 02:39 UTC.
**Not yet done from "Done when":** 200MB+ real transfer from Windows (needs W5/user at desktop) and reboot-survival check (needs a reboot — config is correct: enabled + linger).
**Next for ThinkPad (L5/L6):** add `convert` rule to `rules.toml`; scaffold `linux-converter/` log-only watcher service
**Next for Desktop (W5):** unchanged — E2E test needs user present

### 2026-07-07 — ThinkPad agent Session 2 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** L5 → L6, segment-wise verification, docs consistency pass.
**What was done (each segment verified before moving on):**
- *Segment L5 (convert rule):* already in `rules.toml` from desktop draft. Live-verified: `.pdf` on convert → `pipeline/convert-inbox/`; unmatched `.xyz` → `sorted/misc/`; no allocator restart needed (rules re-read per event). Log lines 02:48 UTC.
- *Segment L6 code:* `linux-converter/` scaffold already on branch. Read every file. `ruff check` passed; `ruff format` fixed one over-long line in `main.py`; **found + fixed: `scripts/install.sh` was mode 100644** (README says `./scripts/install.sh` — would have failed). chmod +x, committed as mode change.
- *Segment L6 deploy:* ran `./scripts/install.sh` (no sudo) — venv created, watchdog 4.0.2, unit installed. `is-active` + `is-enabled` both positive; "watching /home/rab/file-portal/pipeline/convert-inbox" logged 03:00 UTC.
- *Segment L6 e2e:* `.pdf` dropped on convert → allocator ALLOCATED and converter "would convert" logged in the same millisecond (03:00:47.782). `.part-*` dotfile in convert-inbox → correctly silent.
- *Docs consistency pass:* fixed stale `inbox/quarantine/` claims in `docs/05-allocation-rules.md` + `linux-receiver/README.md` (contradicted the L1 fix); added `linux-converter/` to root README table, `docs/00-overview.md` components, `docs/01-architecture.md` data flow (step 6: process-mouth destinations); synced `docs/10` Part 1+2 Linux checkboxes to reality; CHANGELOG: 2 Added + 2 Fixed entries. Left historical `inbox/quarantine` mentions in CHANGELOG/DOCS-AUDIT (they describe the past, correctly).
- Cleaned all test artifacts (convert-inbox, sorted/misc).
**Verification:** every claim above has a log line, systemctl output, or grep behind it — nothing inferred from code comments.
**Part 2 "Done when" status:** Linux half fully green. Remaining: W6 Convert tile on Desktop, then a real tile-drop confirms the full path.
**Next for Desktop (W5 + W6):** E2E test (user present) + add Convert tile (`config.toml`, `config.rs` default, `portals.json`)
**Next for ThinkPad (Part 3, L7-L10):** converter engine — heavy; dedicate a full session; remember `import pymupdf.layout` BEFORE `import pymupdf4llm`

### 2026-07-08 — Desktop agent Session 4 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Execute W5 E2E test (user present to approve access dialog).
**What was done:**
- Pulled `6ffd910` (cleared a stale 3-day-old `.git/HEAD.lock` first — zero bytes, no git process running)
- Launched post-W4 widget build (exe dated 2026-07-05 23:19); computer-use access approved by user — W5's standing blocker cleared
- **W5a (.pdf → Documents tile):** drag-drop registered ("Sent 1 file(s) to documents."), file arrived byte-exact (246 B, `%PDF-1.4` header intact), ThinkPad allocator ALLOCATED to `sorted/documents/` at 04:22:16 UTC
- **W5b (.xyz → Documents tile):** transferred byte-exact (16 B), allocator allocated to `sorted/misc/` — NOT rejected
- **Green ✓ / red ✗ never appeared (waited >30s).** Widget status advanced to "Sent — allocator pending for 1 file(s)." and stalled there.
- **Root cause found (regression):** widget's `status.rs` polls `~/file-portal/logs/status.json`; the writer was implemented only on `master` (`0c3a074`, "add status feed and tests") and is NOT an ancestor of `feat/library-pipeline`. status.json's last event is 2026-07-07T02:37:28 — the moment the ThinkPad restarted the service onto branch code, events stopped.
- **Second gap:** branch allocator routes unmatched extensions to `sorted/misc/` and never emits "rejected" — the red-✗ path in `main.js` is unreachable regardless of the status feed.
- Filed both in `coordination/messages/2026-07-08T00-30--desktop-to-linux--w5-results-status-feed-regression.md`; added task **L6.5** (port status feed) to the ThinkPad list
- Cleaned all test artifacts (ThinkPad `sorted/`, local Desktop test folder)
**Verification:** allocator log lines, remote `stat` byte counts, `git merge-base --is-ancestor` check, widget screenshots at each stage.
**W5 verdict:** transport + allocation E2E = PASS (W1/W2 proven in production); visual feedback = BLOCKED on L6.5. Re-run the 30s visual check after L6.5 lands.
**Next for ThinkPad (L6.5):** port status feed from `0c3a074` into `linux-receiver/allocator/`, reconcile with branch L1/L2, restart service
**Next for Desktop:** W6 Convert tile; re-check W5 visuals once L6.5 is live

### 2026-07-08 — ThinkPad agent Session 3 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** L6.5 — port status feed from master `0c3a074`; adopt recommended rejection semantics; deploy + live-verify.
**What was done (segment-wise, each verified before moving on):**
- *Audit:* diffed `0c3a074` against the branch. Master's `main.py` is a behavioral superset of the branch's L1/L2 re-implementation; the only genuine conflict is `config.py` quarantine location, where the branch's L1 fix (`root/quarantine`) wins.
- *Port:* copied `status.py`, both test files, and `requirements-dev.txt` verbatim from `0c3a074`; replaced `main.py` with the master version (single change: quarantine-guard comment reworded for the L1 layout — the guard itself stays as defense-in-depth); `rules.py` picked up master's formatting via `ruff format`. Branch `config.py` untouched.
- *Tests/lint:* installed requirements-dev.txt into the repo venv; **24/24 pytest pass**, `ruff check` + `ruff format` clean.
- *Deploy:* restarted `file-portal-allocator` (04:34 UTC, "watching" logged, active).
- *Live verify:* `l65-test.txt` → ALLOCATED 04:44:30 + fresh `allocated` event in status.json (first since the 07-07 02:37:28 stall). 3GB sparse file → REJECTED 04:44:43 + `rejected` event with reason; stayed in `quarantine/`, exactly one log line (no loop). `python -m json.tool` parses status.json cleanly. Artifacts removed.
- *Rejection semantics DECIDED* per Desktop's recommendation: `rejected` = quarantine only; unmatched → `allocated` with `dest: sorted/misc`. W5's `.xyz → red ✗` expectation is re-scoped (now green ✓ with misc dest).
- Wrote coordination reply `2026-07-08T04-50--linux-to-desktop--l65-done-status-feed-live.md`; CHANGELOG entry added; marked L6.5 [x].
**Verification:** every claim has a log line, systemctl output, pytest run, or json.tool parse behind it.
**Next for Desktop:** W5 visual re-check (expect green ✓ on .pdf within 30s; .xyz now legitimately ✓ with misc dest; red ✗ requires >2048MB) then W6 Convert tile.
**Next for ThinkPad:** Part 3 (L7-L10 converter engine) — dedicate a full session; `import pymupdf.layout` BEFORE `import pymupdf4llm`.

### 2026-07-08 — Desktop agent Session 5 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** W6 Convert tile → rebuild → E2E verify (doubling as the W5 visual re-check).
**What was done (each step verified):**
- Added `convert` / "To Vault" / 🔁 portal to live `%APPDATA%\file-portal\config.toml`, `config.rs` `AppConfig::default()`, and `portals.json` (commit `af904a2`)
- Checked layout first: tiles are `flex: 1` in a 480px window — 5 tiles fit, no resize needed
- `cargo clippy --release` clean; `npm run tauri build` → 2 bundles (stopped the running widget first so the linker could replace the exe)
- Relaunched widget: 5th tile renders (screenshot-verified)
- **E2E drop:** .pdf on To Vault → tile went GREEN with "✓ w6-convert-test.pdf → pipeline/convert-inbox/w6-convert-test.pdf" in ~4 seconds. ThinkPad logs confirm the full chain at 04:56:45 UTC: allocator ALLOCATED → converter "would convert" → `allocated` event in status.json (which is what drove the green tile)
- **W5 visual re-check: PASSED** — L6.5's status feed works end-to-end through the widget UI. Part 2 "Done when" closed on both lanes.
- Test artifacts cleaned (ThinkPad convert-inbox + local test folder); widget left running with the new build
**Verification:** widget screenshots (green tile + status line), allocator/converter log lines, status.json event, clippy/build output.
**Next for ThinkPad:** Part 3 (L7-L10 converter engine) — dedicate a full session; `import pymupdf.layout` BEFORE `import pymupdf4llm`.
**Next for Desktop:** W7 (Convert-Scan tile) — blocked until Part 3 Linux lands.

### 2026-07-09/10 — ThinkPad agent Session 4 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** Part 3 (L7-L10 converter engine) + Defects A/B + Change Ledger protocol change, per the session brief. Open Decision #3 resolved by user amendment before work began: **neither** bounce nor flag — pre-flight text-layer probe, sub-threshold reroute to Scan as a normal `allocated` hop, terminal Scan lane → quarantine, frontmatter on every output.
**What was done (each gate verified on the live service before the next):**
- *L7:* `pymupdf4llm 1.28.0` into `linux-converter/.venv` (divergence: docs/10 said `--break-system-packages`, but the service runs from its venv); `tesseract 5.5.2` + `eng` listed by `tesseract --list-langs`; `pandoc 3.6` (divergence: Arch has no `pandoc` package — it's `pandoc-cli`). Venv one-liner printed `pymupdf4llm 1.28.0` with `pymupdf.layout` imported first. Divergence: 1.28 hard-depends on `pymupdf_layout` and sets `_use_layout=True` regardless of import order — ordering kept in `engines.py` as insurance.
- *Engine (L8-L10 code, `29ff68f` + fix `4f15c33`):* first-match dispatch mirroring `allocator/rules.py`; probe; reroute; terminal Scan; atomic bundle publish to `library/anchor` + `library/staging`; Obsidian embed rewrite; frontmatter + manifest with source SHA-256; `converter.toml` (`min_chars_per_page=100`, provisional) re-read per event; `convert-scan` rule in `rules.toml`. 26 unit tests; ruff clean. Unit tests caught one bug pre-deploy (staging temp path collided with the assembly temp dir).
- **Live-gate bug #1 (the reason the gates exist):** first L8 run produced allocator ALLOCATED lines but zero converter reaction. Event probe proved: a rename whose source is outside the watch (the allocator hop, inbox/→pipeline/) is an unpaired `IN_MOVED_TO` = watchdog `created` event — never `moved`, never `close_write`. The allocator's event model does not transfer to this topology (the old L6 scaffold only worked because it reacted to `created` unconditionally). Fixed: handler reacts to `created` + size-stability wait, `moved` (reroute), `closed` (in-place writes), deduped by source consumption + watchdog's single dispatch thread.
- *L8 gate:* `00:41:20 CONVERTING l10-digital-with-image.pdf engine=pymupdf4llm lane=clean`, `00:41:32 … l8-book.epub engine=pymupdf4llm`, `00:41:40 … l8-paper.docx engine=pandoc` — three extensions, correct engines, live service.
- **Live-gate finding #2:** the brief's L9 wc-c gate premise ("Scan yields text where Clean yields little or none") is obsolete in 1.28 — layout mode auto-OCRs need-based in EVERY lane (both lanes produced byte-identical 929-byte output on the scan fixture). Engine source (`make_ocr_decision`) shows the OCR modes only govern *prior OCR spans*, and `force_ocr=True` maps to `FORCE_KEEP_OLD` — it would KEEP a bad prior OCR layer. Scan lane now passes `use_ocr=OCRMode.FORCE_DROP_OLD` + `ocr_dpi=300` (discard prior OCR, redo, hard-fail without an engine); Clean is `SELECT_KEEP_OLD`. Coordination message updated: W7's honest meaning is "redo any embedded OCR properly".
- *L9 gates (final code, 01:02-01:03 UTC):* PROBE 1388.0 (digital, Clean) vs 0.0 (scan) both logged; scan on Clean → `REROUTED … -> pipeline/convert-scan-inbox/l9-scan.pdf (chars_per_page 0.0 < 100)` + `allocated` event with that `dest` in status.json; Scan lane OCR-YIELD 929.0 → CONVERTED. **Terminal test:** blank scan through `inbox/convert-scan` (also proves the new rule live through the allocator) → exactly one `REJECTED (ocr yield 0.0 …) -> quarantine/`, one `rejected` status event (`category: convert-scan`), scan-inbox empty after 75s — no re-entry, no loop.
- *L10 gate:* `tree` showed `<name>.md + assets/ + manifest.json` in anchor AND staging; the markdown's one image embed `![[assets/l10-digital-with-image.pdf-0001-02.png]]` resolved by `ls` (62,445 bytes); `head -12` on Clean output (`lane: clean`, `ocr: false`, `chars_per_page_detected: 1388.0`) and Scan output (`lane: scan`, `lane_reason: no_text_layer`, `ocr: true`, `ocr_dpi: 300`); manifest carries sha256 + `pymupdf4llm_version: 1.28.0`.
- *Defect A:* both units templated (`__WORKDIR__`/`__EXEC_PATH__`), both installers `sed` like the dashboard's; verified by fresh install run + `systemctl --user show -p WorkingDirectory` showing the substituted path, both services active (`da9063e`). *Defect B:* snapshot banner added.
- *Protocol:* header `Last updated` deleted; Change Ledger added below Status Summary, backfilled from five SHAs each verified `--is-ancestor` (corrected the brief's 6ffd910 row: session also touched CLAUDE_README, docs/00, docs/01); §4 gained the diff-accounting + append-after-close steps (`935304c`).
- *Cleanup:* all test bundles, quarantined blank, and inbox files removed; inboxes/library verified empty. §4 accounting run over `e302785..HEAD`: every source file has a CHANGELOG entry; docs/protocol files are in this session's ledger row.
**Verification:** every claim above has a log line with timestamp, systemctl/pytest/ruff stdout, a status.json event, or an event-probe transcript behind it — quoted in this entry or in the commit messages.
**Next for Desktop (W7 — UNBLOCKED):** `git pull`, read `coordination/messages/2026-07-09T23-05--linux-to-desktop--w7-semantics-force-scan.md`, then W6-style tile: `category = "convert-scan"`, `label = "Force OCR → Vault"`, `icon = "🔍"` in `config.toml` + `config.rs` default + `portals.json`; rebuild; drop a PDF on it → expect green ✓ with `dest: pipeline/convert-scan-inbox/…` then a converted bundle on the ThinkPad. No `main.js` change needed.
**Next for ThinkPad (Part 4, L11-L12):** return transport (recommended git/Forgejo — Open Decision #4) + place-by-tags + delete staging after send. Also carry forward: `min_chars_per_page=100` is provisional — revisit after ~30 real conversions (chars_per_page is logged on every one).

### 2026-07-10 — Desktop agent Session 6 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** W7 Force OCR tile per the 2026-07-09T23-05 coordination message → rebuild → E2E through the ThinkPad's Scan lane.
**What was done (each step verified):**
- Pulled `ce56ca7` (fast-forward); read the W7 semantics message before touching anything — tile is a force-OCR *override* (`FORCE_DROP_OLD` re-OCR at 300 dpi), not a "scans go here" category
- Added `convert-scan` / "Force OCR → Vault" / 🔍 portal to live `%APPDATA%\file-portal\config.toml`, `config.rs` `AppConfig::default()`, and `portals.json`; no `main.js` change (reroute/reject reuse existing `allocated`/`rejected` events). Commit `1d15b16` (+ CHANGELOG entry — also noted W6 never got one; W7's covers the tile pattern)
- `cargo clippy --release` clean; `npm run tauri build` → 2 bundles in 42s (widget was not running — no linker conflict); relaunched: 6 tiles render, zoom-verified label (tiles are `flex: 1`, no resize)
- **E2E drop (computer-use, user-granted):** digital-text .pdf (901 B, generated) onto Force OCR tile → "Sent 1 file(s) to convert-scan." → green ✓ "w7-force-ocr-test.pdf → pipeline/convert-scan-inbox/w7-force-ocr-test.pdf" within ~8s
- **ThinkPad chain (01:25:42-43 UTC):** allocator ALLOCATED `inbox/convert-scan/` → `pipeline/convert-scan-inbox/`; converter PROBE 277.0 chars/page (above threshold — a real text layer) yet lane stayed `scan` (the override working as designed), CONVERTING engine=pymupdf4llm, OCR-YIELD 279.0, CONVERTED → bundle in `library/anchor/` + `library/staging/` with `manifest.json`; frontmatter reads `lane: scan`, `lane_reason: user_forced_scan`, `ocr: true`, `ocr_dpi: 300`; OCR'd body text matches the source page
- **Byte-exactness:** manifest `source_sha256` `7b060b…` == local `Get-FileHash` output — W1/W2 transport re-proven on this path
- Cleaned: ThinkPad anchor+staging test bundles removed (inboxes already empty — consumed, no loop), local test folder deleted
- §4 accounting over `c718ed2..HEAD`: `config.rs`/`portals.json`/`CHANGELOG.md` covered by the CHANGELOG entry; `CLAUDE_README.md` is protocol, in this session's ledger row
**Verification:** widget screenshots (6 tiles, green ✓ status line), allocator/converter log lines with timestamps, status.json `allocated` event, frontmatter head, SHA-256 comparison.
**Part 3 "Done when": CLOSED both lanes.** Desktop has no open tasks.
**Next for ThinkPad (Part 4, L11-L12):** return transport (git/Forgejo per Open Decision #4) + place-by-tags + delete staging after send. Carry forward: `min_chars_per_page=100` provisional — revisit after ~30 real conversions.

### 2026-07-10 — ThinkPad agent Session 5 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** Documentation-only, per user instruction: record the Part 4 vault wiring (done manually outside any session) and the resolutions of Open Decisions #4/#5/#6. No code; nothing under `linux-converter/` or `windows-widget/` touched.
**What was done:**
- *Read-only verification of the ThinkPad-side claims before recording them:* `~/file-portal/vault.git` is bare (`rev-parse --is-bare-repository` → true), HEAD pinned to `refs/heads/main` (`symbolic-ref`); `~/file-portal/vault-work` at `0272f89` on `main...origin/main` with origin = the local bare repo; seed `71cc4c5` ships `.gitattributes` (`* text=auto eol=lf`, `*.png`/`*.pdf` binary) before any content; `find ~ -maxdepth 3 -name .obsidian` → nothing, so the vault lives only on the Desktop and L11 remains a real task. Desktop-side facts (clone at `<Vault>\Library`, `core.sshCommand="tailscale ssh"` persisted, fetch+push proven) recorded as reported by the user, who wired and verified them manually.
- *Open Decisions:* row 4 → RESOLVED + VERIFIED (bare repo + Tailscale SSH, full wiring facts + the Obsidian stray-`.obsidian` gotcha); row 5 → RESOLVED sparse (converter transcodes, does not read; mint only links that encode facts the converter knows); new row 6 → vault placement (`Library/Inbox/<slug>--<sha256[:8]>/`, no tag/folder mapping, assets nested, identical-sha re-ingest is a no-op, staging deletion gated on `git cat-file -e`).
- *Status Summary:* "(as of …)" date removed from the heading (the Change Ledger owns that fact); Part 4 groundwork line added.
**Verification:** the git-command outputs quoted above; the diff of this file is the deliverable. §4 accounting: only `CLAUDE_README.md` changed — listed in this session's ledger row.
**Next for ThinkPad (L11 + L12, the last Linux milestones):** build the exporter per the now-binding specs in Open Decisions #4/#5/#6 — converter (or a separate export step) commits each staging bundle into `~/file-portal/vault-work` at `Library/Inbox/<slug>--<sha256[:8]>/`, pushes to the local bare repo, verifies the blob with `git cat-file -e`, THEN deletes the staging copy; creates new notes only, never edits existing ones; no tags, no minted links. Invariants to test live: identical-sha re-ingest no-op, no partial bundle ever visible in the vault repo.
**Next for Desktop:** none. When L11 lands, `git pull` inside `<Vault>\Library` (or wire Obsidian Git) is the only consumer step — do NOT open Library/ as its own vault (see row 4 gotcha).

### 2026-07-11 — ThinkPad agent Session 6 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** L11 (exporter) + L12 (staging deletion) per the binding specs in Open Decisions #4/#5/#6.
**Housekeeping first:** Session 5's completed doc changes were found sitting UNCOMMITTED in the working tree (its close was never made — HEAD was still the open-plan commit). Committed them verbatim as that session's close (`7b4c286`, message notes the recovery) + its ledger row (`dde44f8`) before opening this session's plan (`80cc6ed`).
**What was done (each gate verified before the next):**
- *L11/L12 code:* `converter/exporter.py` — a second, non-recursive watch on `library/staging/` inside the existing converter service (no third systemd unit) plus a startup sweep for bundles that landed while the service was down; all git work serialized behind one lock. Flow per bundle: read `manifest.json` → `fetch` + `merge --ff-only origin/main` (commit on top of Desktop filing moves, never behind them) → dedup by `git grep -F <full source_sha256> main -- '*manifest.json'` **in the bare repo** (so a note the Desktop filed out of Inbox/ still counts, and a committed-but-unpushed clone can't fake a dedup hit) → copy via dot-prefixed temp + rename into `Library/Inbox/<slug>--<sha8>/` → pathspec-scoped `git add`/`commit` (self-identifying author `file-portal-converter`) → `push` → **L12 gate:** `git cat-file -e` on the commit AND every bundle file's blob, in the bare repo → only then `rmtree` the staging copy. Failure at any git step logs `EXPORT-FAIL` and keeps staging; committed-but-unpushed resumes at push (never re-commits); an uncommitted stray target from a crashed run is cleaned, a committed path is never overwritten. The exporter never initializes either repo (Decision #4: exactly one side does).
- *Tests:* `tests/test_exporter.py` — 8 tests against REAL temp git repos asserting on the bare repo's committed tree, covering: happy path, identical-sha no-op, dedup-after-Desktop-filed-it (`git mv` out of Inbox + push, then re-ingest → no new commit), git failure keeps staging, push-failure-then-resume (exactly one ingest commit total), incomplete bundle kept, sweep ignores dot-dirs. 34/34 suite-wide, ruff check+format clean.
- **Live-gate defect (the reason the gates exist, again):** first live drop converted instantly but exported 120s late (`CONVERTED` 21:20:45 → `EXPORTED` 21:22:45). Cause: the converter assembles TWO dot-prefixed temp dirs inside staging per bundle (`.part-<name>`, `.part-<name>.staging-copy`); each fired a `created` event whose stability wait held the single watchdog dispatch thread for the full 60s timeout — the dir gets renamed away, `rglob` on a missing dir yields `[]` forever, and the dot-check sat AFTER the wait. Fixed: dot-check before any waiting + the wait bails when the dir vanishes. Re-verified: `CONVERTED` 21:24:16.160 → `EXPORTED` 21:24:16.184 (~25ms).
- *Live gates (all on the running service):* fresh PDF → `EXPORTED l11-live-test-2 -> Library/Inbox/l11-live-test-2--141c0d4c (commit cfca1521 pushed + blob-verified, staging copy removed)`; byte-identical re-drop of the first PDF → converter re-converted (anchor got `l11-live-test (1)`) but exporter logged `EXPORT-SKIP … source_sha256 1dbf1aa1 already in vault — no-op, staging copy removed`, bare repo commit count unchanged; committed note's frontmatter `source_sha256` == `sha256sum` of the local source file; `vault-work` clean and in sync with origin; staging empty after every gate.
- *Cleanup:* anchor test bundles removed; vault test ingests removed via `git rm` + commit `chore: remove exporter live-test bundles` + push (history retains them honestly — the tree is back to seed files). Inboxes empty.
- *Docs:* CHANGELOG (Added: exporter; Fixed: event stall), linux-converter README rewritten (was still claiming "Part 2 skeleton (log-only)" — stale since Part 3), docs/10 Part 4 checkboxes + decisions table synced to reality (incl. the stale W7 checkbox), this file.
**Verification:** every claim above has a converter.log line with timestamp, a `git log`/`ls-tree`/`cat-file` output, or pytest/ruff stdout behind it. §4 accounting over `7b4c286..HEAD`: source files (`exporter.py`, `config.py`, `main.py`, `test_exporter.py`) covered by the CHANGELOG entry; CLAUDE_README/CHANGELOG/docs/10/linux-converter README are in this session's ledger row.
**Part 4 "Done when": Linux side CLOSED.** All Linux milestones L1–L12 complete; the pipeline loop is code-complete end to end.
**Next for user/Desktop:** `git pull` inside `<Vault>\Library` (or wire Obsidian Git) to consume ingested bundles — do NOT open Library/ as its own vault (Decision #4 gotcha). No open agent tasks on either machine. Carry-forward: `min_chars_per_page=100` provisional — revisit after ~30 real conversions.

### 2026-07-11 — Desktop agent Session 7 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Consume the vault — the single Desktop step left after ThinkPad Session 6 closed L11/L12. (Small consumer step; work was done before this plan section was committed — recorded at close instead of as a separate open-plan commit.)
**What was done (each step verified):**
- Pulled `feat/library-pipeline` (`b615b0c..2ac2441`, fast-forward) and read Session 6's close before touching anything
- Located the vault clone: `C:\Users\Rabbiallah\Documents\Obsidian\Obsidian Vault\Library` — `core.sshCommand = tailscale ssh` persisted in its config, origin `rab@archlinux:file-portal/vault.git`, exactly as Decision #4 records
- **Decision #4 gotcha check (both halves):** no `.obsidian/` inside `Library/` (`Test-Path` → False) and no Library path among the five vaults in `%APPDATA%\obsidian\obsidian.json` — the vault switcher does not list Library
- Pre-pull state: clone at seed `0272f89`, working tree clean except a stat-only `.gitignore` phantom (`git diff` empty — the `eol=lf` normalization artifact this machine's clones are known for; no real delta)
- **Pull:** fast-forward `0272f89..ec1eaf6` over Tailscale SSH. History received: `a49d49c` + `cfca152` (the two L11 live-test ingests, SHAs matching Session 6's log exactly) + `ec1eaf6` (their honest removal). `git ls-tree -r HEAD` → `.gitattributes` + `.gitignore` only; on-disk dir matches (plus `.git`)
- No cleanup needed — the ThinkPad already removed all test artifacts; this session created none
**Verification:** git command outputs quoted above (pull transcript, ls-tree, config reads, registry read). §4 accounting over `2ac2441..HEAD`: only `CLAUDE_README.md` changed — protocol file, listed in this session's ledger row.
**The pipeline loop is now closed end to end and verified from both machines:** widget → allocator → converter → vault commit/push → Desktop pull.
**Next for both machines:** none open. Real usage begins; revisit `min_chars_per_page=100` after ~30 real conversions.

### 2026-07-12 — Desktop agent Session 8 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** First real document through the pipeline, user-requested: the Stafford Beer "Designing Freedom" PDF from Downloads (Anna's Archive copy, ~225-byte filename, 116 pages, 4.4 MB, sha256 `dbcce92c…fad`). Sent via the widget's own atomic transport (`.part-` + `mv` over `tailscale ssh` into `inbox/convert/`), which is also why the user's own earlier tile drop appears in the same logs. (Work ran ahead of the plan commit — recorded at close.)
**What was done (each step verified):**
- **Attempts 1–3 all quarantined on the identical failure:** first image write (page 43 = the book's first image) → `code=2: cannot open file '…/.part-Designing_Freedom_…/assets/….png'`. Attempt 1 was the user's own Force-OCR tile drop (23:52 UTC), attempt 2 my Clean-lane send of the verbatim name, attempt 3 a short-but-spaced name — which eliminated filename length and isolated spaces as the variable.
- **Root cause proven by two manual repros on the ThinkPad** (venv python, scratch dir, service untouched): (a) the identical file converts cleanly with a space-free assets path (116 pp, 24 images, 176 KB md); (b) `image_path="…/dir with space/assets"` fails with the error naming `dir_with_space` — **pymupdf4llm sanitizes spaces→underscores across the entire image path, directory components included**, while `main.py` builds `tmp_dir` from `file_path.stem` verbatim. Red herring documented: attempt 1's "filename too long" look was MuPDF's ~256-byte error-message truncation.
- Filed as coordination msg `2026-07-12T00-01--desktop-to-linux--converter-spaces-in-filename-defect.md` (commit `b65871d`) with repro + two fix shapes + "clamp length too" note. **No Linux code touched** (lane discipline; live service left as-is).
- **Attempt 4 (space-free `Designing-Freedom--Stafford-Beer.pdf`): full success.** CONVERTED in 70s (Clean lane, probe 1484.7), EXPORTED in 121ms (`c624e00` pushed + blob-verified, staging removed) — the Session 6 event-stall fix visibly holding.
- **Desktop consumption:** `git pull` in `<Vault>\Library` → 27 files. Byte-exactness: manifest `source_sha256` == frontmatter == local `Get-FileHash`, all `dbcce92c…fad`; 25 assets; md opens `# DESIGNING FREEDOM / Stafford Beer`.
- **Second defect found at pull:** bundle checked out at `<Vault>\Library\Library\Inbox\…` — `INBOX_REL = Path("Library")/"Inbox"` is vault-relative wording applied repo-relatively (repo root IS the Library folder; L11 tests encode the same misreading). Filed as `2026-07-12T00-20--desktop-to-linux--exporter-inbox-rel-double-library.md`. Desktop-side remedy applied as a normal Decision #6 filing move: `git mv` to repo-root `Inbox/` + push (`0fa976c`) — dedup unaffected (manifest travels; grep is repo-wide).
- *Cleanup:* 3 quarantined copies on the ThinkPad sha-verified identical to the local original, then removed; `~/tmp/df-debug/` repro dir removed; inboxes/staging empty. User's original stays in Downloads untouched.
**Verification:** converter.log lines with timestamps, two repro transcripts, git pull/push/log output, Get-FileHash vs manifest vs frontmatter, remote `sha256sum` before every delete. §4 accounting over `0f02b6c..HEAD`: only coordination messages + this file — no source changed; all listed in this session's ledger row.
**Defect tally for the first real document: 2 (one high, one cosmetic) — both found by real input within minutes of "code-complete", both with proven root causes.**
**Next for ThinkPad (L13 + L14):** fix per the two coordination messages; add a spaced-filename+image test; consider clamping `bundle_name` length.
**Next for Desktop/user:** drop real documents (space-free names until L13 lands); pull `<Vault>\Library` to consume.

### 2026-07-12 — ThinkPad agent Session 7 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** L13 (spaced filenames + images) + L14 (`INBOX_REL` doubled level), per the Desktop's two 2026-07-12 coordination messages.
**What was done (each gate verified before the next):**
- *L14 (`be3a7fd`):* `INBOX_REL = Path("Inbox")` — Decision #6's `Library/Inbox/…` is vault-relative; the repo root IS the vault's Library folder (Decision #4), so repo-relative it is plain `Inbox/`. Module docstring corrected; `test_exporter.py` expectations fixed (they encoded the same misreading), incl. the Desktop-filing test which now moves to `Filed/` so it stays a genuine out-of-Inbox move. 8/8 exporter tests green. No migration, per the Desktop's analysis.
- *L13 (`1e1ea6d`):* the assembly temp dir the engine writes into is now keyed on the source sha — `.part-<sha256[:16]>` — instead of the verbatim stem (`sha256_of` moved above dir creation). Sanitizer-proof by construction (pymupdf4llm rewrites spaces→underscores across the whole image path, directory components included) and immune to filename-length pressure. The published bundle keeps the original stem: anchor/staging dirs and the `.md` note name are unchanged — only the engine-visible path changed. Added `bundle.clamp_name` (200 utf-8 bytes, codepoint-safe, trailing dot/space strip) applied to `bundle_name`, covering the Desktop's ~225-byte Anna's Archive near-miss: 200 + `.part-…staging-copy` (+19) + ` (n)` stays under ext4's 255-byte component limit.
- *Tests:* `test_spaced_filename_with_image_converts` — **run red first against pre-fix `main.py` (git stash), failing with the byte-for-byte field error** (`cannot open file '….part-Designing_Freedom_-_Stafford_Beer/assets/….png'`), green after; every `![[assets/…]]` embed in the output asserted to resolve on disk. Plus a 250-byte spaced-stem clamp test and 4 `clamp_name` unit tests. **40/40 suite-wide, ruff check+format clean.**
- *Deploy + live gate (one drop proved both fixes):* service restarted (both watches logged); `L13 Live Gate - Spaced Name.pdf` (spaced name, embedded image, sha `498ceb81…`) through `inbox/convert/` → 00:18:00 ALLOCATED → PROBE 118.0 → CONVERTED (anchor bundle under the original spaced name; embed `![[assets/L13_Live_Gate_-_Spaced_Name.pdf-0001-00.png]]` resolved by `ls`) → 00:18:01 `EXPORTED … -> Inbox/l13-live-gate-spaced-name--498ceb81 (commit 139f74d0 pushed + blob-verified, staging copy removed)` — repo-root `Inbox/`, no `Library/` prefix, confirmed by `ls-tree` on the bare repo (which also shows the Desktop's `0fa976c` filing at the same root).
- *Cleanup:* test bundle removed from anchor and `git rm`'d from the vault (`chore: remove L13/L14 live-gate test bundle`, pushed — history honest, tree back to seed + designing-freedom); staging/inboxes/quarantine verified empty.
- *Docs:* CHANGELOG (2 Fixed entries), coordination reply `2026-07-12T00-38--linux-to-desktop--l13-l14-fixed-live-verified.md`, this file.
**Verification:** every claim above has a pytest/ruff run, a converter/allocator log line with timestamp, or a `git ls-tree`/`log` output behind it. §4 accounting over `ef5a8e8..HEAD`: source files (`main.py`, `bundle.py`, `exporter.py`, 3 test files) covered by the two CHANGELOG entries; CLAUDE_README + coordination message are in this session's ledger row.
**The spaces workaround is retired — drop files with their natural names.**
**Next for Desktop/user:** `git pull` in `<Vault>\Library` when convenient (brings the test bundle's add+remove pair); then just real usage. No open agent tasks on either machine. Carry-forward: `min_chars_per_page=100` provisional — revisit after ~30 real conversions (the L13 live gate's dense single page probed 118.0 — real one-pagers can sit near the threshold).

### 2026-07-12 — Desktop agent Session 9 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** User-requested re-verification of L13/L14 with the worst-case real input: resend the original Anna's Archive filename (~225 bytes, spaces, U+2019 apostrophe) that produced Session 8's three quarantines. Expected outcome: CONVERTED (L13) then EXPORT-SKIP (content `dbcce92c…` already in vault — dedup, not a duplicate). (Short verification session; recorded at close.)
**What was done:**
- Pulled `4bcbef1..f490592` (ThinkPad Session 7 close) and read the 00:38 coordination reply before sending.
- Sent the verbatim original name via the atomic transport → 00:55:08 PROBE 1484.7 lane=clean → **00:56:18 CONVERTED (70s)** with the published name visibly clamped at 200 bytes (`…60cd4be69533ace7be8508ec`) → **00:56:18.375 `EXPORT-SKIP … source_sha256 dbcce92c already in vault — no-op, staging copy removed`** (12ms). Both fixes + dedup confirmed on the exact input that broke Session 8.
- *Cleanup:* retest's long-name anchor duplicate removed (anchor keeps the real `Designing-Freedom--Stafford-Beer` copy); staging/inboxes/quarantine verified empty; vault clone pulled `0fa976c..c8fbe28` (the live-gate add+remove pair) — tree = seed + designing-freedom at `Inbox/`, exactly as the ThinkPad predicted.
**Verification:** converter.log lines quoted above; remote `ls` of anchor/staging/inboxes/quarantine; `git log` + `Get-ChildItem` on the vault clone. §4 accounting over `f490592..HEAD`: only CLAUDE_README — this session's ledger row.
**Next for both machines:** none open. Real usage with natural filenames; carry-forward unchanged.

### 2026-07-12 — Desktop agent Session 10 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** W8 — user-requested "Add to Library" button in the widget: visual, Claude Code-styled, one click pulls new vault bundles into Obsidian. Plan committed `6e9f9c6` before work.
**What was done (each step verified):**
- *Backend:* new `src-tauri/src/vault.rs` — `vault_check` (fetch → `rev-list --count HEAD..origin/main` + new-bundle slugs from `--diff-filter=A` on `Inbox/*/manifest.json`) and `vault_pull` (fetch + `merge --ff-only`, then old..new diff for what arrived). Transport rides the clone's persisted `core.sshCommand="tailscale ssh"`; never initializes a repo (Decision #4). New `vault_library_dir` config key (`serde(default)` — pre-W8 configs parse; empty hides the feature); real path added to live `%APPDATA%` config.
- *Frontend:* `#vault-bar` between tiles and status — near-black panel, terracotta `#D97757`, monospace, ✳ glyph; states idle/ready(glow-pulse + slug preview)/working(spinning ✳)/success/offline. 45s poll; `applyStatusEvent` triggers a 10s fast-poll window for 3 min after any drop allocated to `pipeline/convert*`. Height 186 → 224. `cargo clippy --release` clean.
- *Live gate 1 (the reason the gates exist, third time running):* the user's own drop — the Textor book, natural ~230-byte spaced Anna's Archive name (L13 fix holding in the wild, `lane=scan`, exported `fd0e50a9` at 01:06) — lit the button "✳ Add 1 new note to Library" with slug preview on the first poll (screenshot-verified, computer-use granted). **Click FAILED usefully: defect L15.** `git merge` couldn't check out the bundle — interior filenames (200-byte clamped `.md`, ~230-byte asset PNGs) push full vault paths past Windows' 260-char MAX_PATH ("Filename too long"); my error mapping showed it as "vault host unreachable" (pull was one opaque step).
- *Fixes, same session:* every `vault.rs` git call now passes `-c core.longpaths=true` (+ set persistently in the clone); `vault_pull` split into fetch (fail ⇒ "offline") vs `merge --ff-only` (fail ⇒ "error" with git's real message); partial-checkout debris cleaned before retry. Also: `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` added — the exe was console-subsystem and spawned a console window behind the widget.
- *Live gate 2 (post-fix):* button ready → click → pulled `c8fbe28..fd0e50a`, note (764 KB) + 4 assets + manifest on disk, `git status` clean, bar returned to "✳ Library · up to date" (screenshot + filesystem + `git log` verified). Final `npm run tauri build` (2 bundles) + relaunch: no console window, idle bar correct.
- *Filed L15* (`2026-07-12T01-15` coordination msg): bundle-interior names should be Windows-clean at the source (budget ≤ ~100 bytes; asset names re-derivable from the path handed to pymupdf4llm or renamed post-conversion with embeds rewritten). Desktop mitigation is live, so severity medium, no migration urgency.
**Verification:** clippy/build output, three widget screenshots (ready-glow with slug, post-fix pull, final idle), git log/status/ls in the clone, the failing merge transcript. §4 accounting over `6e9f9c6..HEAD`: widget source + tauri.conf covered by the CHANGELOG W8 entry; CHANGELOG/coordination/CLAUDE_README in this session's ledger row.
**The user's consume loop is now: drop → tile turns green → button glows within ~10s of export → one click → note in Obsidian.**
**Next for ThinkPad (L15, medium):** shorten bundle-interior filenames per the coordination message; regression test with a >200-byte stem asserting total path budget.
**Next for Desktop/user:** real usage. Widget left running with the final build.

### 2026-07-12 — Desktop agent Session 11 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** User-reported W8 regression: a black console window flashes and vanishes at random. (Small fix session; recorded at close.)
**What was done:**
- *Diagnosis:* W8's `windows_subsystem = "windows"` removed the exe's console — which every child process had been invisibly attaching to. Orphaned, each spawn (`git` in the 45s vault poll, `tailscale ssh` in status polls and transfers) opened its own console for the command's duration. The "random" timing = the 45s poll cadence plus event-driven status calls.
- *Fix (`vault.rs`, `status.rs`, `transfer.rs`):* `CREATE_NO_WINDOW` (0x08000000) via `CommandExt::creation_flags` on all three spawn sites (const lives in `vault.rs`, shared). clippy clean.
- *Verify:* rebuilt, relaunched, screenshots at +8s and +53s bracketing a full poll cycle — no console anywhere, bar still reads "✳ Library · up to date" (proof the hidden fetch ran). Bundles regenerated so the MSI/NSIS installers carry the fix; widget left running on the final build.
**Verification:** clippy/build output, two timed screenshots, bar state. §4 accounting over `e360106..HEAD`: 3 source files covered by the CHANGELOG entry; CHANGELOG + this file in this session's ledger row.
**Next for both machines:** ThinkPad L15 (unchanged); Desktop real usage.

### 2026-07-12 — ThinkPad agent Session 8 (Claude Code / Fable)
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** L15 (bundle-interior filenames vs Windows MAX_PATH), per the Desktop's 2026-07-12T01-15 coordination message. Plan committed `c73c130` before work.
**What was done (each gate verified before the next):**
- *L15, asset half (`d1112d2`):* the engine now converts from a short, sanitizer-proof hardlink (copy fallback) inside the sha-keyed assembly dir, named `<slugify(stem)[:40]><ext>`, deleted before publish. Chosen over the coordination message's rename-post-conversion shape because pymupdf4llm 1.28 (layout mode) derives asset names from `mydoc.name` — the full path it opened; the `filename=` kwarg is IGNORED for path-opened docs (`document_layout.py:1128`), so only the path handed to the engine controls the names. Asset basenames drop ~230 → ≤ ~61 bytes, and the link's extension means it can never collide with `assets/`. Bonus finding encoded in the code comment: a >243-byte source stem would have overflowed ext4's 255-byte limit at the asset write and quarantined L13-style on Linux — same fix closes it.
- *L15, note half (same commit):* `bundle.clamp_name` 200 → 80 bytes; worst case `Inbox/<slug60>--<sha8>/<stem80>.md` = exactly 160 bytes vault-relative, the lock-in number the coordination message proposed.
- *Tests:* new `test_interior_paths_fit_windows_budget` — 230-byte spaced stem + embedded image → converts, EVERY emitted file's vault-relative path ≤ 160 bytes, bundle root exactly `{note, manifest, assets/}`, every embed resolves — **run red-first against pre-fix code (git stash), both halves failing**; 200-byte expectations in test_bundle/test_main tightened to 80. 41/41, ruff check+format clean. (First test draft used a 260-byte stem — which cannot exist on ext4 at all; capped to 230, the real Anna's Archive shape.)
- *Deploy + live gate:* service restarted (both watches logged 05:47:11); 230-byte spaced-name PDF with embedded image through `inbox/convert/` → 05:47:30 ALLOCATED → PROBE 119.0 → CONVERTED (stem clamped to 80; asset `l15-live-gate-judgement-and-truth-in-ear.pdf-0001-00.png` = 56 bytes, embed resolved) → 05:47:31 EXPORTED (`b914af1b` pushed + blob-verified). `git ls-tree -r` on the bare repo measured the three committed paths at **158/139/89 bytes**. Test bundle removed from anchor and `git rm`'d from the vault (`0e079a8`, honest history); staging/inboxes verified empty.
- *Noticed while gating (user-facing, no code action):* (a) the 05:17 Textor re-drop hit the pre-L15 code, converted, correctly EXPORT-SKIPped, and left identical-sha `(1)`/`(2)` anchor duplicates — left in place, anchor copies of user drops are the user's call; (b) the 01:25 "Designing Brand Identity" quarantine is a genuinely bad file — an 80-byte "Link expired or invalid" error page saved as .pdf (failed download), so `unreadable by pymupdf → quarantine` is correct behavior; user should re-download.
- *Docs:* CHANGELOG (1 Fixed entry), coordination reply `2026-07-12T05-55--linux-to-desktop--l15-fixed-live-verified.md`, this file.
**Verification:** every claim has a pytest/ruff run, a timestamped allocator/converter log line, an `ls`/`xxd` inspection, or `git ls-tree` byte counts behind it. §4 accounting over `94db496..HEAD`: source files (`bundle.py`, `main.py`, 2 test files) covered by the CHANGELOG L15 entry; CLAUDE_README, CHANGELOG, coordination message in this session's ledger row.
**Interior names are Windows-clean at the source; the Desktop's `core.longpaths` mitigation is now belt-and-braces only.**
**Next for Desktop/user:** real usage; re-download the Brand Identity book (the quarantined copy is an expired-link error page); optionally tidy the two duplicate Textor anchor copies. Carry-forward: `min_chars_per_page=100` provisional — revisit after ~30 real conversions.

### 2026-07-13 — Desktop agent Session 12 (Claude Code / Fable)
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Repair both CI failures blocking PR #1 (feat → master), merge it with a merge commit, delete the stale fix branch. Plan committed `b3c3baa` before work. Context: master had been merged into feat earlier tonight (`2a1778f`, ThinkPad-side, 9 conflicts ours-side, 65/65 tests — no ledger row of its own; its master-carried files are accounted here), which put the July-5 workflow in contact with the branch's code for the first time.
**What was done (each step verified):**
- *CI / python (`665097b`):* reproduced CI's exact failure locally — fresh venv with ONLY `requirements-dev.txt` (CI's install), `pytest tests/` from `linux-receiver/` → the identical `ModuleNotFoundError: No module named 'allocator'` collection death. Root cause: the runner never installs the package and bare `pytest` doesn't put the package root on `sys.path` (local venvs/`python -m pytest` mask it). Fix: `[tool.pytest.ini_options] pythonpath = ["."]` in `linux-receiver/pyproject.toml` AND `linux-converter/pyproject.toml` (same latent bug; converter tests aren't in CI yet). Re-run in the same bare venv: 24 collected, 23 pass — the 1 failure is Windows-only (`sorted\documents` vs `sorted/documents` path-separator assertion), and CI's Ubuntu run confirmed: **python job green in 14s**.
- *CI / rust (`6aaa042`):* `gh run view --log-failed` showed pure `cargo fmt --check` diffs (no clippy/logic reached). `cargo fmt` reformatted `config.rs`/`main.rs`/`status.rs`/`vault.rs` — all code written after the July-5 formatting pass; zero behavior change. `cargo fmt --check` exit 0; `cargo clippy --all-targets -- -D warnings` run locally to pre-clear the never-reached next CI step: clean.
- *CI green:* `gh pr checks 1 --watch` → all 6 checks pass (python 14s, rust 3m14s, CodeQL javascript/python/rust + summary).
- *Merge:* `gh pr merge 1 --merge` (no squash/rebase, no branch delete) → **MERGED 23:20:02 UTC, merge commit `7c006f2`** — verified two parents (`6630792` old master + `6aaa042` feat tip) and `feat/library-pipeline` still on origin.
- *Branch cleanup:* before deleting, checked `fix/widget-blank-window` (`b949b2a`) was NOT an ancestor of feat/master — but `git cherry` showed all 5 of its commits patch-equivalent to commits already in feat, so nothing orphaned. `git push origin --delete fix/widget-blank-window`; `ls-remote` confirms gone. Local copy left untouched.
- *Docs:* CHANGELOG (1 Fixed entry covering both CI fixes + known-red follow-ups), this file.
**Verification:** the before/after pytest transcripts in the CI-sim venv, fmt/clippy exit codes, `gh pr checks` final table, `git log origin/master -1 --format="%h %p %s"`, `git cherry` output, `ls-remote` empty result. §4 accounting over `d53c152..HEAD`: `2a1778f` merge-carried files (ci.yml, coordination README + 07-05 brief, docs/08, linux-dashboard/*, linux-converter test/bundle changes) belong to master's history and the merge commit's message; this session's source changes (2 pyproject.tomls, 4 widget .rs files) are covered by the CHANGELOG entry; CLAUDE_README + CHANGELOG in this session's ledger row.
**master now contains the full library pipeline; CI is green on contact.**
**Next for ThinkPad:** none open. **Next for Desktop/user:** real usage (unchanged carry-forwards: re-download Brand Identity, tidy Textor anchor dupes, `min_chars_per_page` review). CI follow-ups when convenient: add converter/dashboard tests to the python job; bump `actions/checkout` and `setup-python` majors to silence Node 20 deprecation warnings.

### 2026-07-18 — Desktop agent Session 13 (Claude Code / Fable) — GPU revamp scope + Phase 0+1
**Machine:** DESKTOP-OBTQIRD (Windows, post-reset)
**Plan:** Commit the GPU pipeline revamp scope (from the same-day planning session) as docs/11, then run Phase 0 (Desktop ML baseline) + Phase 1 (Marker vertical slice vs pymupdf4llm ground truth) in one sitting. Plan committed `f531451` before work.
**What was done (each step verified):**
- *Scope doc (`5e8b945`):* `docs/11-gpu-pipeline-revamp.md` — verified hardware table, VRAM math, both red flags (Forgejo not-on-Windows; ThinkPad unbenchmarked), the intake-flow inversion and its bundle-format-compatibility constraint, pre-answered decisions, Phases 0–5 with gates.
- *Phase 0 (no repo changes):* `uv` 0.11.29 via winget; CPython 3.12.13; torch **2.11.0+cu128** in `C:\Users\Bndit\ml\marker-env`. Gate verified: `torch.cuda.is_available() → True`, device `NVIDIA GeForce RTX 3080`. (One benign uv quirk: "Missing expected target directory for Python minor version link" — the interpreter installs and works anyway.)
- *Baseline:* `C:\Users\Bndit\ml\pymu-env` with pymupdf4llm **1.28.0 — the exact ThinkPad pin** — driven by a script replicating `engines.run_pymupdf` Clean-lane flags verbatim (incl. the load-bearing `pymupdf.layout` import order). Probe reproduced the recorded first-ingest value **to the decimal** (1484.7 chars/page) → faithful ground truth. 74.8 s, 24 images.
- *Phase 1 Marker run:* marker-pdf **1.10.2** (surya 0.17.1), default mode, warm conversion **97.3 s**, peak VRAM **8 675 MiB** (desktop baseline 1 156). Structurally better across the board (real paragraphs; 1 vs 30 bogus blockquotes; 36 vs 24 images; relative image paths; clean sketch captions where pymu emitted OCR-gibberish "picture text"; `_meta.json` structural TOC). Defect class inherited from the PDF's embedded 2013 Archive.org OCR layer: **319** `<sup>` artifacts, scrambled TOC table, word merges.
- *`--force_ocr` probe:* saturated the GPU 27+ min with no output at **9 939 MiB** peak (batch auto-scaling thrashes the 10 GB ceiling on a full-book 1 281-region re-OCR) — killed deliberately. Ruled out at defaults; not a hardware fault.
- *Verdict recorded in docs/11:* **Phase 1 = mixed pass.** Fix candidates ranked (all flags verified against `marker_single --help`): `--strip_existing_ocr` + capped `--recognition_batch_size` on a `--page_range` subset first; general batch caps to hit the ≤6 GB coexistence budget; deterministic `<sup>`/hyphenation post-pass in the bundle normalizer; born-digital PDF A/B as the missing evidence half.
**Verification:** torch gate output; probe-value match vs the 2026-07-12 ingest record; artifact counts measured on both outputs (`<sup>`, blockquote lines, image counts); nvidia-smi 2 s-interval VRAM logs (peaks extracted, logs deleted after); side-by-side reads of front matter + the Ashby's Law sketch pages. §4 accounting over `ab69064..HEAD`: CLAUDE_README + docs/11 only — doc/protocol files, in this row; no source changes, no CHANGELOG entry needed. Test artifacts kept at `C:\Users\Bndit\ml\phase1\` for the user's own inspection.
**Boundaries honored (user-set):** no Phase 2 (Ollama), nothing ThinkPad-side.
**Next for Desktop:** Phase 1.5 retests (strip-existing-ocr timed subset; born-digital book), then Phase 2 with the user present. **Next for ThinkPad:** nothing new — waits on the user's go.

### 2026-07-18 — Desktop agent Session 14 (Claude Code / Fable) — Phases 1.5 + 2 CLOSED
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** User green-lit the Phase 1.5 retests then Phase 2, and delivered the factory/control-center vision (widget = command center, allocator = conveyor, Marker = processing plant, Ollama = product analyst, vault = shipping) with instruction to capture it as design only. Plan committed `c2ac5a9` before work.
**What was done (each step verified):**
- *Phase 1.5a (`--strip_existing_ocr --recognition_batch_size 32`, Beer pp 0–15):* 63.3 s conversion (~4 s/page → ~8 min/116 pp), peak 7 887 MiB. Quality: **0** `<sup>` (was 319), **0** fake blockquotes, TOC table renders perfectly, word merges gone, italics recovered, complete ISBNs both prior engines mangled. **The Phase-1 noise class is fully fixed** — this is the Scan-lane config for PDFs with untrusted OCR layers. Output: `ml\phase1\marker-strip16`.
- *Phase 1.5b (born-digital A/B):* found a real candidate in Downloads — Chromium/Skia webpage-print PDF (AI Agent book GitHub page, 19 pp, mixed CJK/English, probe 1407.7). Marker default: 27.3 s, zero artifacts, working hyperlinks (pymu emits none), clean tables, CJK+emoji intact, 4 meaningful images vs pymu's 27 icon-spam assets, correct reading order (pymu interleaves the page sidebar). **Marker wins outright on born-digital.** Outputs: `ml\phase1\marker-agentbook` vs `pymu-agentbook`.
- *Engine policy recorded in docs/11:* born-digital → default (~1.5 s/pp); scan-with-OCR-layer → strip+batch-cap (~4 s/pp); raw scan → default. Router idea: existing `probe_chars_per_page` + pymupdf OCR-font-span check.
- *Phase 2 (Ollama VRAM handoff):* Ollama 0.32.1 (winget) + qwen3:8b (5.2 GB). Scripted Marker → `keep_alive:0` generate → Marker (`ml\phase1\phase2_handoff.ps1`): VRAM 623 → 623 → 621 → 620 MiB across all checkpoints, `ollama ps` empty immediately post-generate, sequence peak 6 187 MiB serialized, **52.6 tok/s**, no OOM. **Gate PASSED.**
- *⚠️ Product-analyst hazard found:* raw reformat prompt → qwen3:8b **invented image URLs** (`_page_0_Picture_2.jpeg` → `https://example.com/…`). Recorded in docs/11: the LLM pass must be link-fenced (strip/re-inject or in==out link validation). Never let the analyst touch packaging.
- *Design note (no implementation):* factory/control-center vision captured in docs/11 — station↔component map, two load-bearing principles (per-segment on/off + eval; logistics/ETA reporting from measured s/page + a converter status feed in the spirit of the allocator's `status.json`).
- *Two PS 5.1 gotchas recorded* (matter for any future Windows service wrapper): native stderr under redirection becomes fake failures (use `cmd /c`); `Invoke-RestMethod` mangles non-ASCII JSON (use UTF-8 file + `curl.exe --data-binary`). Both hit live, both fixed in the handoff script.
**Verification:** wall/VRAM from 2 s-interval pollers (logs deleted after extraction); artifact counts measured on every output; `ollama ps` checked at the unload boundary; all marker exits 0. §4 accounting over `c2ac5a9..HEAD`: CLAUDE_README + docs/11 only — doc/protocol files in this row; no source changes, no CHANGELOG entry needed.
**Boundaries honored (user-set):** no widget implementation, no Phase 4 rewiring, nothing ThinkPad-side.
**Next for Desktop:** control-room build-out is now unblocked design-wise — Phase 4 wiring (engine policy + link-fenced analyst stage, bundle-format compatible) and the widget factory-view, both user-gated. **Next for ThinkPad:** Phase 3 sidecars when online + user go.

### 2026-07-19 — ThinkPad agent Session 9 (Claude Code / Fable) — Phase 3 sidecars CLOSED
**Machine:** ThinkPad C14 (Arch Linux), repo at `~/file-portal-src`
**Plan:** Phase 3 per the user brief: spec check → Ollama + phi4-mini CPU tagging benchmark → ChromaDB + MiniLM over the real vault → Phase 3 results section in docs/11. Plan committed `8e755b3` before work. Boundaries: no live-service/exporter changes, no Phase 4, no Forgejo; benchmark envs outside the repo.
**What was done (each step verified from raw output):**
- *Spec check (the plan was blind on this):* i7-1265U (12th gen, 2 P + 8 E cores, 12 threads, 4.8 GHz max), 15.3 GiB RAM (~13.5 available at idle), 233 GB NVMe with 199 GB free, 4 GiB zstd zram swap active (0B used throughout all benchmarks). All from `lscpu`/`free`/`df`/`zramctl` directly.
- *Divergence noted per protocol:* the brief said native Arch `ollama` package, but no sudo credential was available in the session (`sudo -n` refused; autonomous run, nobody to type a password). Installed the official **v0.32.1 release tarball user-level** instead — same version as the Desktop's Phase 2 — extracted to `~/ml/ollama`, run as `OLLAMA_MODELS=~/ml/ollama/models ./bin/ollama serve` (no systemd unit, nothing system-level, fully removable; process stopped at session close). `sudo pacman -S ollama` supersedes it if the role goes permanent. (First download 404'd — release assets are now `.tar.zst`, not `.tgz`; second pull attempt needed after a registry HEAD timeout.)
- *phi4-mini benchmark (q4, 2.5 GB — the registry tag exists, no substitution needed):* real Beer-book body text → YAML frontmatter (tags/summary/reading_level) prompt; timings from the API's own `*_duration` fields, RAM from the runner's `VmHWM`. **Load 3.5 s cold / 0.3 s warm; prompt eval ~29–31 tok/s (consistent across 422- and 1330-token inputs); generation 4.1–5.8 tok/s; peak runner RSS 3.06 GiB.** Wall per tagging call: 9–56 s depending on excerpt size. **Async-tagging gate: PASS** (10–60 s/doc; generous multi-chunk stays under ~5 min). Same numbers rule the full-document product-analyst role OUT here: ~45 K-token book ≈ 3 h vs minutes on the 3080. Quality note recorded: on a bare 1500-char excerpt phi4-mini tagged Beer's wave *metaphor* as `physics`/`oceanography`; the 6000-char run recovered the real topics — tagging prompts need document context (title/TOC/multiple chunks).
- *ChromaDB + all-MiniLM-L6-v2 (384d):* `uv` 0.11.29 (user-level install — machine had none) venv at `~/ml/chroma-env` (CPU torch); vault cloned read-only to `~/ml/vault` (2 real books; exporter's `vault-work` untouched). 1218 × ~800-char chunks: **model load 4.6 s, embed 34.2 s (35.6 chunks/s), Chroma add 0.8 s, queries 3–6 ms, peak RSS 1.16 GiB.** All 4 relevance probes hit the correct book with on-point passages (best: "Frege's account of judgement and assertion" → the Textor Frege chapter at distance 0.209). **Embedding gate: PASS with margin.**
- *docs/11:* Phase 3 results section written (Phase 1.5/2 style — spec table, both benchmarks, gate verdicts), Phase 3 checkbox ticked, red flag #2 marked RESOLVED, **recommendation recorded: product analyst on Desktop GPU (52.6 vs ~5 tok/s, mutex per Phase 2); ThinkPad carries tag/embed/structure sidecars.**
- *Hygiene:* `ollama serve` stopped; live allocator/converter services never touched (verified nothing under `systemctl --user` changed — no installs, no restarts); everything installed lives under `~/ml/` + `~/.local/bin/uv`, outside the repo.
**Verification:** every number above is from captured command output (lscpu/free/df/zramctl transcripts, Ollama API response JSON, `/proc/<pid>/status` VmHWM, timed index run with printed query results). §4 accounting over `a561cb7..HEAD`: only CLAUDE_README.md + docs/11 changed — doc/protocol files, listed in this session's ledger row; no source changes, no CHANGELOG entry needed.
**Boundaries honored (user-set):** no live-service/exporter changes, no Phase 4 rewiring, no Forgejo; benchmark envs outside the repo.
**Next for Desktop:** Phase 4 rewiring is now fully unblocked evidence-wise — engine policy (docs/11 table) + link-fenced analyst on the Desktop GPU, enrichment handoff to the ThinkPad sidecars proven here; all user-gated. **Next for ThinkPad:** none open — sidecar implementation arrives with Phase 4 wiring. If the enrichment role goes permanent: replace the tarball Ollama with the pacman package + a user-level service unit.

### 2026-07-19 — Desktop agent Session 15 (Claude Code / Fable) — Phase 4 slices 1+2 LANDED
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** User green-lit Phase 4 (the intake inversion). Design before code, then the vertical slice, analyst only if slice 1 closes cleanly. Plan committed `0a6e99b`. (User-supplied kickstart referenced the dead pre-reset `C:\Users\Rabbiallah\…` path — corrected to `C:\Users\Bndit\…` and verified the ThinkPad S9 Phase 3 claims against the pushed branch before building on them.)
**What was done (each step verified):**
- *Design (`27813dd`):* `docs/12-phase4-rewiring.md` — the bundle/exporter contract extracted from the real code (bundle.py/exporter.py/transfer.rs, cited by behavior), tar-over-`tailscale ssh` transport with dot-dir + atomic `mv` (scp/rsync unusable — managed host keys), mechanical engine routing, link-fenced analyst design, slice gates.
- *Slice 1 (`72b2532`, hygiene `88b10da`):* `windows-converter/convert_and_ship.py` — probe (pymupdf) → route → `marker_single` → format-identical bundle (80-byte clamp, `conversion:` frontmatter, `![[assets/…]]` embeds, manifest with full source sha) → local anchor (`C:\Users\Bndit\ml\library\anchor`) → ship. **Two live defects found and fixed during bring-up:** (1) OCR-layer detection by font name fails on the Beer layer — plain "Courier" — the robust signal is **text render mode 3** (`get_texttrace`), majority-of-spans rule, verified against both test PDFs; (2) **Windows bsdtar mangles non-ASCII argv** (CJK dir name arrived empty) — tar now only ever sees ASCII paths (bundle stays in `.part-<sha16>` locally; the remote `mv` applies the visible name — tailscale ssh carries Unicode argv correctly).
- *Slice 1 gates, all three PASSED with the **unchanged** ThinkPad exporter:* (1) agent-book PDF (born-digital, CJK name, 19 pp, 2.0 s/page) → **EXPORTED** `Inbox/bojieli-ai-agent-book-ai-agent--21bfdffc` (commit `6008eb66` pushed + blob-verified); independent `Get-FileHash` of the source == the vault-committed manifest sha, byte-identical. (2) Re-ship → **EXPORT-SKIP**, staging empty, no duplicate. (3) **Cross-machine dedup:** Beer converted fresh on the Desktop (full 116-pp strip-OCR run, 489 s = 4.2 s/page, exactly the docs/11 prediction) → **EXPORT-SKIP against `dbcce92c`**, the ThinkPad's 2026-07-12 ingest — the pipeline provably does not know or care which machine converted.
- *Slice 2 (`45e5995`):* `windows-converter/analyst.py` — the link-fenced qwen3:8b readability pass (docs/12 design): every embed → opaque `⟦IMG-n⟧` token pre-prompt, re-injected post; per-chunk token-multiset validation, violation ⇒ that chunk ships un-analyzed. Live test on the agent book: **7/7 chunks passed, 0 rejected, 206.5 s**, 4 embeds in == 4 out, 0 stray tokens, `analyst:` frontmatter stamped, VRAM back to baseline (659 MiB) after 7 `keep_alive:0` round-trips. Analyst-to-vault E2E leg deliberately deferred to the next genuinely-new document (dedup skips re-ships of already-vaulted sources — correct behavior, not a gap).
- *Interruption note:* a **power outage** killed the first Beer conversion mid-run (~22:40 local). Recovery was clean: all durable state (vault commits, pushed repo work) survived; one temp dir swept; the uncommitted slice code was intact on disk and committed before the rerun. Lesson applied: commit code before long verification runs.
**Verification:** all gate evidence is captured command output (converter.log lines, bare-repo `git log`/`git show`, `Get-FileHash`, staging `ls | wc -l`, nvidia-smi checkpoints). §4 accounting over `6547f52..HEAD`: `windows-converter/*` covered by the two feat commits + this row; CLAUDE_README/docs/11/docs/12/.gitignore are doc/protocol files in this row. CHANGELOG entry: pending next session alongside widget work (new component is additive, not yet wired to the widget).
**Boundaries honored:** zero `linux-receiver`/`linux-converter` edits (the whole point — the exporter consumed foreign bundles as-is); no widget changes; no Forgejo; ML envs + anchor outside the repo.
**Next for Desktop:** widget "Convert (GPU)" tile → watched folder → `convert_and_ship.py` (the conveyor rewire proper), control-room gauges per docs/11 design note. **Next for ThinkPad:** enrichment consumer (tagging/embeddings) fed from staging arrivals — needs a coordination message when Desktop wiring lands.

### 2026-07-19 — Desktop agent Session 16 (Claude Code / Fable) — Gemini analyst backend + pre-flight estimator
**Machine:** DESKTOP-OBTQIRD (Windows)
**Plan:** Gemini entitlement check → `--backend` flag → estimator → live fence test. Plan committed `ee1baeb`. Pre-session: rclone Drive remote established (user OAuth) and the **first headless anchor-mirror ran** — both Desktop-converted bundles to `gdrive:Claude Code Memory Backup/anchor-mirror/` (44 files); vault zip verified on Drive (4th copy).
**What was done (each step verified):**
- *Entitlement check — answer is NO, the hard way:* Gemini CLI 0.51.0 installed but its individual Google-login is **sunset** ("migrate to Antigravity"); the user's AI Plus subscription does NOT cover programmatic access. Programmatic door = Gemini API key (AI Studio, free tier). Key lives in the user's env (`GEMINI_API_KEY`, user scope) — set by the user's own hands, never in chat/code/logs (one accidental chat exposure happened mid-setup; that key was **revoked and rotated** immediately). API verified live: HTTP 200, 50 models listed.
- *Backend (`040e713`):* `analyst.py` `_generate_gemini` → `gemini-flash-latest:generateContent` via curl header auth; `process(markdown, backend=)`; identical chunking/fence/reject; code-fence unwrap for Flash's markdown habit; `--backend {local,gemini}` wired through `convert_and_ship.py`.
- *Live fence test (agent book, 26 498 chars):* **7/7 chunks passed, 4/4 embeds, 0 stray tokens, 141.9 s = 186.7 chars/s — ~35% faster than local (138)**. Meta records backend + model in frontmatter.
- *Pre-flight estimator:* `analyst.preflight(chars)` returns the Tauri card JSON — est_tokens (chars/4), per-backend ETAs from measured all-in throughput, `gpu_busy` (nvidia-smi, >2 GiB threshold), privacy labels ("100% air-gapped" vs "cloud routing"), honest cost line ("API free tier — NOT covered by AI Plus, verified 2026-07-19"). Estimator's Gemini ETA for the test doc: 142 s vs 141.9 s actual.
**Verification:** fence counts/stray-token scans on live output; measured wall times; preflight JSON inspected against measurements. §4 accounting over `ee1baeb..HEAD`: `windows-converter/*` in the feat commit; CLAUDE_README in this row. CHANGELOG still deferred to the widget-integration session (component remains pre-widget).
**Boundaries honored:** no Tauri card yet (next session); no ThinkPad work; key never touched repo, logs, or memory.
**Next for Desktop:** the Tauri pre-flight card (poll a pending-analyst queue dir, render preflight JSON, route on click) — first control-room panel; then the Convert (GPU) tile. **Next for ThinkPad:** unchanged (enrichment consumer, user-gated).

### 2026-07-19 — Desktop agent Session 17 (Claude Code / Fable) — drop-folder watcher live; both analyst backends book-proven
**Machine:** DESKTOP-OBTQIRD (Windows). **Plan committed `aaef944`.** User asleep for the close; results also left in the Desktop messages folder.
**What was done (each step verified):**
- *Estimator hardening (`b72cbe8`):* `preflight` now returns `est_chunks`, a **free-tier window warning** (>18 chunks → "throttling likely, local recommended"; threshold from the live 429 body: metric `generate_content_free_tier_requests`, limit 20 on gemini-3.5-flash), a `recommendation` field (over-window→local; gpu_busy→gemini; else user's choice), and a gemini ETA that includes the RPM pacing floor. Verified: 7-chunk doc → rec=gemini (GPU was busy), no warning; 43-chunk doc → rec=local + warning, gemini ETA (1470 s) honestly loses to local (1232 s).
- *Gemini rate-limit hardening (`2976469`, earlier tonight):* unpaced 47-chunk run melted into 41 fast API failures (57 s) — diagnosis via live 429 probe; fix = 13 s pacing + backoff retry on 429/5xx + meta split `chunks_failed` (API) vs `chunks_rejected` (fence). Graceful degradation held: every failed chunk shipped as its original.
- *User decision recorded:* declined the $20 API credit minimum — **routing policy: small docs (≤18 chunks) may go Gemini free tier; books route local.** The card should present, not pressure.
- *Beer book, local analyst (full run):* 47 chunks → **44 passed, 3 fence-rejected (qwen3 touched embeds; originals shipped), 0 failed**, 621 s analyst leg. Output: 36/36 embeds, 0 stray tokens, "unexpect edly"→"unexpectedly" healed; the one surviving "atmos phere" sits inside a rejected chunk — the audit trail works. Bundle: anchor `…West Sussex IS (1)`, frontmatter `backend: local`. Gemini twin of the agent book also exists (anchor `…工程实践 (1)`, 7/7). Both backends now have real-book artifacts.
- *`watch_and_convert.py` (`b72cbe8`) + E2E:* poll watcher on `C:\Users\Bndit\ml\library\drop` (dotfile skip, size-stability wait, sequential single-flight = Marker/Ollama never overlap, `.gpu-lock` busy signal, done/failed archiving, `analyst-mode.txt` toggle file re-read per conversion — off|local|gemini). Live E2E: dropped the agent-book PDF → detected ~20 s → converted+shipped 52 s → ThinkPad `EXPORT-SKIP 21bfdffc` → staging 0 → source archived to done/. **The Desktop conveyor front door is real: drop a PDF, it ends up in the vault (or dedup-skips), no human in the loop.**
**Verification:** watcher.log + converter.log line pairs; fence counts on both book artifacts; estimator JSON on small/big inputs. §4 accounting over `aaef944..HEAD`: windows-converter/* in the two feat commits; CLAUDE_README this row. CHANGELOG: still rides with the widget session (S18) as agreed.
**Boundaries honored:** no widget UI (user must be present for look-and-feel decisions — their factory, their aesthetics); no ThinkPad-side changes (its exporter consumed foreign bundles untouched, again).
**Next for Desktop (S18, kickstart prompt in the Desktop messages folder):** the Tauri pre-flight card + Convert (GPU) tile — render `analyst.preflight()` JSON, per-segment toggles, route on click; wire the tile to the drop folder; CHANGELOG entry for windows-converter. **Next for ThinkPad:** enrichment consumer (needs coordination message; user-gated).

### 2026-07-19 — Desktop agent Session 18 (Claude Code / Fable) — the pre-flight analyst card is REAL
**Machine:** DESKTOP-OBTQIRD (Windows). *Protocol note:* no separate open-plan commit — the user green-lit S18 verbally immediately after S17 closed ("do the widget pre-flight card to your best ability"), and the plan lived in the S17 close + Desktop-message kickstart. Everything else per protocol.
**What was done (each step verified):**
- *Queue mechanics (`convert_and_ship.py`):* `--defer-analyst` converts + anchors + parks the bundle in `<gpu_pipeline_dir>\pending\<sha16>\` with a `<sha16>.json` card (bundle name, source, state, `analyst.preflight()` data); `--resume <id> --backend local|gemini|none` applies the link-fenced analyst in place (frontmatter + manifest updated, analyst-stamped anchor copy), ships, and clears the queue — failures flip the card to `failed` with the error for a retry click. Watcher analyst-mode gains **`ask`** (now the live default).
- *Rust (`preflight.rs` + config + main):* `preflight_list` (reads card JSONs raw — Python stays the single schema owner), `preflight_decide` (validates id/backend, spawns the resume **detached** with `CREATE_NO_WINDOW` — a 10-minute analyst must never block the UI). Three new `serde(default)` config keys: `gpu_pipeline_dir`, `gpu_python_exe`, `gpu_converter_dir` — feature hidden when unset, the per-segment-toggle pattern. `cargo fmt` + `clippy -D warnings` clean.
- *UI (`index.html`/`styles.css`/`main.js`):* `#preflight-cards` between tiles and vault bar, styled in the W8 Claude Code language (near-black, terracotta, monospace, ✳). Per card: name row, meta line (chunks · ~tokens · GPU free/busy), amber free-tier warning when over the window, red error row on failure, three route buttons — 🔒 Local ~ETA / ☁ Flash ~ETA / Ship as-is — with the estimator's recommendation getting the terracotta border. Working state spins the spark + locks buttons. Poll 15 s, tightens to 4 s after a click; queue-clear triggers the vault fast-poll (card → ship → glow → Add to Library, the full conveyor visible). Window height = 224 + 76/card via `core:window:allow-set-size` (added to capabilities).
- *Verified without burning tokens on screenshots:* backend chain proven by CLI with the exact argv the buttons spawn — defer (card written: 7 chunks, `state: pending`, honest empty recommendation with GPU free) → resume `--backend none` → SHIPPED → ThinkPad `EXPORT-SKIP 21bfdffc` → queue 0. Release build clean; widget restarted on it and running; **a live card was left parked** (agent book, re-deferred) so the user's first morning look shows the real thing.
- *CHANGELOG:* the deferred `windows-converter/` + S18 widget entry landed (Unreleased → Added).
**Usage-awareness (user asked):** one batched read of all six widget sources, zero browser screenshots (native window; CLI-simulated the button path instead), design decided once, edits batched — the session's context cost stayed in code-and-logs, not pixels.
**Boundaries honored:** no ThinkPad changes; bundle format untouched; every new piece toggleable (config keys empty → invisible).
**Next for Desktop:** user's morning: click the waiting card (any route — "Ship as-is" is free) and watch the conveyor run tile-to-Library; then S19 candidates: Convert (GPU) tile in `transfer.rs` (local drop-dir move), widget-managed watcher lifecycle, ETA ranges. **Next for ThinkPad:** enrichment consumer (user-gated; schema-constrained outputs per the injection note).

### 2026-07-19 — Desktop agent Session 19 (Claude Code / Fable) — control-room design committed
**Machine:** DESKTOP-OBTQIRD. **Plan `f75f867`.** Live co-design with the user (their first card click ran the full loop: local analyst → ship → EXPORT-SKIP → queue clear).
**Done:** `docs/13-control-room-design.md` — the projection principle (user doctrine: the widget is a second source of truth, a projection of the pipeline/git, "conventional and pragmatic, but with taste"; all state on disk, Python owns schemas, widget renders); the line grammar (chips through Drop▸Convert▸Analyst▸Ship▸Library; card = chip at a decision gate; terracotta = exclusively "your hand required"); stations/levers incl. the 4-position analyst gate + remember-my-choice rules; two-engines rationale (Marker = switches-only stamping press; analyst = program slot, prompt-file personas in `windows-converter/prompts/`, fence as station infrastructure); Marker-visibility fix (Convert station, density toggle); metrics doctrine (numbers on levers — free-tier bar on the ☁ button; rolling rates; shift report; fence saves shown as protections); receipts/lineage from existing frontmatter; Obsidian+ZenNotes launcher icons; the events.jsonl keystone + widget-owned watcher lifecycle; build order S20/S21/S22.
**Verification:** doc matches the chat design conversation point-for-point. §4: docs/13 + CLAUDE_README only — this row.
**Next for Desktop:** S20 foundation (events stream, watcher lifecycle, shift line, prompt-file programs). **Next for ThinkPad:** unchanged (enrichment consumer, user-gated).

### 2026-07-19 — Desktop agent Session 20 (Claude Code / Fable) — foundation shift: programs, events, lifecycle, shift line
**Machine:** DESKTOP-OBTQIRD. **Plan `66d5f19`.**
**Done (each verified):**
- *Programs:* prompt extracted to `windows-converter/prompts/readability.txt`; `analyst.process(..., program=)` loads prompt files; meta/frontmatter record the program. The analyst is now formally a program slot (docs/13) — new jobs are new text files.
- *Event stream:* `events.py` (best-effort JSON-line append to `<gpu_pipeline_dir>\events.jsonl`); emitters across the pipeline: intake detected/failed, convert probe/converted (with s/page), gate pending/resolved/failed, analyst start/done (with fence counts), ship shipped/failed. Live trail verified over a full defer→resume cycle: probe→converted→pending→shipped→resolved, timestamped with metrics — the shift report, receipts, and rolling rates all derive from this one file now.
- *Widget lifecycle:* `watcher.rs` — the widget autostarts watch_and_convert.py when configured (CREATE_NO_WINDOW), a titlebar power dot shows/toggles it (green hum = running, grey = stopped — deliberately not terracotta per the docs/13 color law), and `on_window_event(Destroyed)` kills it with the window (in-flight conversions run to completion — documented). **Verified live: fresh widget launch spawned the watcher itself (pid observed).** The manual console ritual is gone.
- *Shift line:* `events.rs` `shift_summary` (today counts + tail; UTC date via civil-from-days, no date crate) rendered in a new quiet `#shift` line — "shift: N converted · N analyzed (M protected) · N shipped" — fence saves surfaced as protections per doctrine.
- `cargo fmt` + `clippy -D warnings` clean; release build; widget restarted on it.
**§4 accounting `66d5f19..HEAD`:** windows-converter/* + windows-widget/* in the feat commit (CHANGELOG: S20 rides under the S18 Unreleased entry's feature family; formal entry folds in at the next release cut); CLAUDE_README this row.
**Next for Desktop:** S21 — the line view (chips through stations, Convert-station visibility, station toggles, reader launcher icons). **Next for ThinkPad:** unchanged.

### 2026-07-19 — Desktop agent Session 21 (Claude Code / Fable) — the line is visible
**Machine:** DESKTOP-OBTQIRD. **Plan `39d6a75`.**
**Done (each verified):** `line.rs` — one `line_state` read (drop-waiting count, converting name from `.gpu-lock`, failed count, last-shipped from the events tail) + `analyst_mode_get/set` (projects `analyst-mode.txt`; ask/local/gemini/off) + `open_reader` (config-allowlisted exe/URI) + `open_failed_tray`. UI: the docs/13 station strip `▚ drop ▸ ⚙ convert ▸ ✳ gate ▸ ⇈ ship ▸ ▤ library` above the cards — Convert shows the piece in the press (green when active), the gate shows its mode and flips terracotta only when cards wait (the color law holds), Drop shows a clickable amber `+N✗` when the failed tray has pieces; gate click cycles the 4 modes; Obsidian ◆ / ZenNotes ◈ titlebar launchers (config keys `reader_obsidian`/`reader_zennotes`, live config set: obsidian:// URI + ZenNotes.exe). Window reflow accounts for the strip. `clippy -D warnings` clean; release build; widget restarted (watcher auto-spawned again).
**§4 `39d6a75..HEAD`:** windows-widget/* in the feat commit; CLAUDE_README this row.
**Next:** S22 (same sitting): receipts, auto-route rule, ETA ranges from rolling event rates.

### 2026-07-19 — Desktop agent Session 22 (Claude Code / Fable) — the judgment layer
**Machine:** DESKTOP-OBTQIRD. *(Plan folded into the S21 open — same sitting, user directive "continue until done done".)*
**Done (each verified):**
- *ETA ranges:* `analyst.eta_range()` computes typical/slow (median + ~p10) from the event stream's measured analyst rates per backend (fallback to constants under 3 samples); the pacing floor still clamps Gemini. preflight now emits `eta_range_s`; the card renders "~2m–4m". Live check on a 170k-char doc: gemini [911, 1518]s from real history — the estimates now *learn*.
- *Remember-my-choice:* `rules.json` (`auto_local_over_chunks`) — written by a checkbox that appears only on big-doc cards (docs/13: variety on first encounter, automation after); `defer()` applies the rule and auto-routes local with a `gate/auto_routed` event instead of parking. Widget writes intent; the pipeline decides — projection preserved.
- *Receipts:* ⇈ ship-station click → `last_receipt` gathers the last shipped bundle's chain (pages @ s/page · backend passed✓/protected🛡 · duration) from events into the status line.
- *Failed tray:* S21's `+N✗` amber count + click-through (Explorer) — closed as part of this pair of sessions.
- `clippy -D warnings` clean (one `map_or`→`is_some_and` fix); release build.
- **Sharp edge found:** `Stop-Process` on the widget skips the Destroyed handler → orphaned watcher (observed two pythons; swept). Normal window close is safe. Future: watcher PID file + startup sweep.
**§4 `7635e1a..HEAD`:** windows-widget/* + windows-converter/* in the feat commit; CLAUDE_README this row.
**Next:** docs/14 (mobile projection design, think-only) then wrap. **ThinkPad:** unchanged.

### 2026-07-19 — Desktop agent Session 23 (Claude Code / Fable) — docs/14 remote projection (think-only)
**Machine:** DESKTOP-OBTQIRD. Design analysis only, per the user's "think about it once done remodeling": `docs/14-remote-projection.md` — verdict FEASIBLE (the tailnet is the transport, the docs/13 projection principle means the phone is just a second projector over the same on-disk truth). **Corrections to the relayed Gemini plan recorded:** host = ThinkPad (always-on; user's own version was right), not a "two-node HA cluster" (Desktop is duty-cycled — the UI must honestly show "plant offline"), laptop is NOT the heavy worker (~5 tok/s measured, Phase 3), and no new task framework — the directory queues + watcher + sha-dedup already are one; the phone needs an HTTP door, not a backend. Phases: A read-only projection (tailscale serve + state sync), B submit/route only (pull-model mobile-inbox + decision files), C maybe. Security: tailnet-bound only, no arbitrary commands, size-capped allowlisted uploads. Build is ThinkPad-side and user-gated.
**§4:** docs/14 + CLAUDE_README this row. **Next:** user reviews the S21/S22 widget live + docs/14; ThinkPad enrichment consumer + Phase A when green-lit.

### 2026-07-19 — Desktop agent Session 24 (Claude Code / Fable) — the launch-context bug, hunted and fixed
**Machine:** DESKTOP-OBTQIRD. Debugging session, user reporting "icons disappeared / Library stuck Checking…".
**The hunt (recorded because the misdirections teach):** (1) Red herring #1 — the Claude app's preview pane had auto-opened the widget's index.html as a static snapshot; the user's screenshots of the "broken widget" were partly THIS mirage (no JS → no icons, default station values). (2) Red herring #2 — a filesystem overlay/sandbox theory (seeded by an earlier gemini.cmd anomaly) was disproven by the user's own Test-Path run. (3) Real signal: identical exe, identical config — instances launched from harness shells boot perfectly (boot-log beacons, watcher spawns); instances launched from the user's shortcut write nothing, spawn nothing, and vault_check hangs at "Checking…". (4) Root cause: **Explorer hands shortcut-launched apps the LOGIN-time environment** — every PATH entry added since login (a lot, today) is missing, so the widget's git→tailscale-ssh and other spawns lived in a different world than shell launches. A windowless app's ssh also had a live prompt-deadlock risk.
**The fix (`in this commit`):** `hydrate_env_from_registry()` at widget boot — reads Machine+User PATH (REG_EXPAND_SZ expansion included) and GEMINI_API_KEY from the registry and sets them process-wide, making every launch context identical by construction; `vault.rs` git calls get `GIT_TERMINAL_PROMPT=0` + null stdin (fail fast, never hang a windowless app); `debug_log` boot-beacon channel (JS → `widget-boot.log`) + window.onerror surfacing + DOM-measured window autosizing (kills the scrollbar that clipped titlebar icons) — all kept as permanent instrumentation. Also: WebView2 profile swept once (dev.fileportal.widget), shortcuts rebuilt with proper working dir + icon, stale Obsidian vault-name URI fixed after the user's vault rename.
**Verified:** clippy -D warnings clean; fixed build boots healthy from a fresh launch (beacons complete, watcher spawned, readers configured). **Morning test for the user: launch from the Desktop shortcut — if beacons appear in widget-boot.log, case closed; if not, next suspect is Malwarebytes exclusions (add the widget exe + C:\Users\Bndit\ml).**
**§4:** windows-widget/* in the fix commit; CLAUDE_README this row.

### 2026-07-19 — Desktop agent Session 25 (Claude Code / Fable) — Marker joins the tiles
**Machine:** DESKTOP-OBTQIRD. **Plan `aead3a4`.** User asked the right question ("why isn't Marker part of the widget?") — answer was sequencing debt from docs/13; paid now.
**Done:** `transfer.rs` — the `convert-gpu` category never leaves the machine: collision-safe copy into `<gpu_pipeline_dir>\drop` via the pipeline-standard dotfile-then-rename; JS skips the allocator status poll for it (the line strip IS its status: drop count → ⚙ converting → gate card → ship). New ⚡ "GPU → Vault" tile in the live config (7 tiles at 480px is snug but workable — revisit width if an 8th ever lands). clippy clean, rebuilt, relaunched healthy (watcher up).
**Verify remaining:** one real drag onto the ⚡ tile (user, morning) — the underlying drop→convert→card→ship chain is already E2E-proven.
**§4 `aead3a4..HEAD`:** windows-widget/* in the feat commit; CLAUDE_README this row.
**Next:** user's morning shortcut-launch check (S24) + first ⚡ drag. ThinkPad items unchanged (enrichment, supersede flow, docs/14 Phase A).

### 2026-07-19 — Desktop agent Session 26 (Claude Code / Fable) — the line speaks
**Machine:** DESKTOP-OBTQIRD. *(Compact; user asked "how do I know it is converting?" mid-drop of a 439-page book — the answer was "you barely can," so this session fixed that.)*
**Done:** `line_state` now returns `converting_eta_s` (pages from the piece's probe event × measured median s/page from history, minus lock-file-mtime elapsed) and `latest` (the newest event verbatim); JS renders a countdown on the ⚙ station and a **stage ticker** in the shift line — the user's requested narration (📥 on the belt → ⚙ probing/converting ~Nm left → ✳ awaiting YOUR routing decision → 🧠 analyzing → ⇈ shipped ✓ → ✓ task complete), failures included; 5s line poll while converting. Swap deliberately delayed until the in-flight conversion finished (restart mid-convert would orphan the job AND re-queue the source — recorded hazard). clippy clean.
**Live validation in progress:** first real ⚡-tile drop (BRAIN OF THE FIRM, 439 pp, scan lane, 59 min convert — dense 2 375 chars/page book; the s/page history now spans 3.4–8 s/page so ETAs will show honest ranges) is parked at the gate (est_chunks 263) awaiting the user's routing click.
**§4 `3978d7a..HEAD`:** windows-widget/* in the feat commit; CLAUDE_README this row.

### 2026-07-20 — Desktop agent Session 27 (Claude Code / Fable 5) — the assumption becomes a measurement
**Machine:** DESKTOP-OBTQIRD. *(Report-only session, opened at the user's "write these as findings and audit them" after they visually caught garbage in the vaulted Beer book that the pipeline had shipped all-green.)*
**Done:** `docs/15-survival-audit.md` committed (`bd13c52`) — the Survival Audit spec: window-survival containment over an ephemeral pymupdf witness, per-stage strictness (tolerant convert / ruthless analyst / agreement-labeled scan lane), §1 closed-decisions register, §5 deterministic tripwires, §9.1 measured calibration priors. Findings register filed same commit at `coordination/messages/2026-07-20T03-30--desktop-degeneration-findings-brain-of-the-firm.md`: **F1 (HIGH)** degeneration loops in vaulted Beer — 140,513/1,139,354 chars (12.3%) in two zones (~lines 1594–1668, 2758–2814; worst: 32,294-char heading loop, trigram ×2,152, zlib 0.003); **F2** duplication accompanies degeneration (3 degraded copies of one source paragraph); **F3** analyst `_chunks()` passes >CHUNK_TARGET single paragraphs through unexamined (fail-safe behaved correctly — attribution is Marker OCR decode loops, evidenced by OCR-shaped misreads in the zones); **F4** clean threshold separation (flag at zlib<0.20 OR trigram≥40 → zero false positives on this corpus; Designing Freedom/bojieli/Textor CLEAN; CJK needs char-n-grams); **F5** MAX_PATH — pre-L15 vault paths to 349 chars, `\\?\` prefix required (reproduced).
**Verification:** every claim from live prototype runs over all 4 vaulted books (marker-env python, read-only), direct code read of `analyst.py:62–73`, or reproduced error. Beer's bad copy deliberately RETAINED as the §9 labeled true-positive specimen.
**Next:** S28 — build `fidelity_audit.py` per docs/15 (Opus 4.8, kickstart prompt prepared; report-only), calibrate on all 4 books, then the F1 remedy loop: audit flags vaulted Beer → re-convert → audit passes → supersede-swap. Note for the record: open-plan commit `ff56f1e` carries ~80 EOL-only line rewrites in the ledger region (known CRLF churn; verified content-identical in the diff).
**§4 `2b965ca..HEAD`:** CLAUDE_README (protocol edits), docs/15 + coordination findings register — all doc/protocol files, listed in this session's ledger row. No source files changed.

### 2026-07-20 — Desktop agent Session 28 (Claude Code / Opus 4.8) — the Survival Audit is built
**Machine:** DESKTOP-OBTQIRD. *(Build session — Fable 5 authored docs/15 + the S27 findings; Opus 4.8 implemented to spec, no redesign. Report-only: nothing gates on the verdict until Rab signs thresholds.)*
**Done:** `windows-converter/fidelity_audit.py` (new) — the Survival Audit per docs/15: ephemeral pymupdf witness (extract→score→discard), 7-step normalization, non-overlapping 12-word window-survival (rapidfuzz anchor-fuzzy fallback), §5 tripwires (degeneration zlib+trigram, page-coverage, xref-deduped asset-delta [informational], reverse-containment sample, scan-lane garbage-rate), `audit_convert`/`audit_analyst`/`compute_verdict`/`build_fidelity_block` + CLI. CPU-only, long-path-safe (`\\?\` via byte-stream to MuPDF), CJK space-free char-window matching. Wired **report-only** into `convert_and_ship.py` (convert stage after Marker; analyst stage inline + in `apply_analyst`) — every hook crash-wrapped (an audit failure can never fail a conversion), writes a `fidelity` manifest block (schema §7) and emits `stage:"audit"` events; **verdict gates nothing**. Activates on next watcher restart (widget-owned; not restarted this session). rapidfuzz already in marker-env; wordfreq absent → scan-lane reference-free signal is a zero-dep garbage-token rate, `dict_hit=null` (within §5's "wordfreq OR bundled" latitude).
**Calibration (report-only, over the vaulted corpus; sources: Beer+bojieli in drop/done, Designing Freedom in ~/Downloads [sha-verified dbcce92c], Textor absent=degeneration-only):**
  - **Degeneration tripwire = production-ready.** Flags Beer only (both zones, lines 1600/1624/2758…), CLEAN on bojieli/Designing Freedom/Textor, at the §9.1 priors. This is the one threshold-ready gate today.
  - **Survival/containment = a good LOCALIZER, not yet a doc-level gate.** doc_survival for *acceptable* books spans 0.76–0.96 (bojieli clean-CJK 0.76 — a GitHub-readme PDF reflow + mixed-script; Beer scan 0.91; Designing Freedom scan 0.96), and the runs correctly point at real trouble spots (Beer's index + OCR-garbage pages; Designing Freedom's noisy-OCR pages). A doc-level survival threshold would false-alarm on legitimate reflow → keep survival+runs REPORT-ONLY. The design's own priority order maps to readiness: **degeneration gates, runs localize, survival trends** — only the first is enforceable now.
  - **Analyst near-exact validated** (real-scale synthetic): identical→1.000 pass, reformat-only→1.000 pass (reformatting does NOT false-fail), 2%-paragraph-drop→0.87 fail (runs point at the omissions), single-para rewrite→0.999 with a 24-word run at the fail boundary (ANALYST_RUN_WORDS=25 → consider 20).
  - Runtimes: witness+audit ≤5 s/book (Beer 405pp scored in 5.0 s), well under the §9 <1-min target. Hook verified end-to-end (manifest block 4.6 KB, JSON-clean, events correct) without running Marker.
  - **Known limits (noted, not bugs):** no clean-English book is vaulted yet, so the clean `fidelity` doc-threshold is uncalibrated; a raw scan with no extractable witness text can't be survival-audited (degeneration still applies); asset-delta is informational (Marker drops full-page scan rasters + decorations by design).
**Next / awaiting Rab:** sign off thresholds (recommendation: enforce degeneration only; keep survival+runs report-only; analyst fail at doc<0.995 OR run≥20-25). Then: widget projection slice (terracotta-on-fail, docs/13) + the Beer remedy loop (audit flags → re-convert → audit passes → supersede-swap). Health-check note: two `file-portal-widget.exe` (7552, 11980) at open — possible duplicate; left untouched.
**§4 `5d4a0f0..HEAD`:** fidelity_audit.py + convert_and_ship.py → CHANGELOG "Added" entry; CLAUDE_README (open plan + this close) → ledger row. No Rust touched.

### 2026-07-20 — Desktop agent Session 29 (Claude Code / Opus 4.8) — the widget ghost: MSIX AppData redirection (and an honest wrong turn)
**Machine:** DESKTOP-OBTQIRD. *(Opened to fix "the widget shows an old version / missing ⚡ tile," a symptom that had survived multiple sessions. The open-plan asserted a "stale frontend embedding" root cause — THAT WAS WRONG; this entry corrects it. No source files changed all session.)*
**TRUE root cause (proven):** Claude's Bash/PowerShell tools run **sandboxed inside the Claude desktop app's MSIX package** (`Claude_pzs8sxrjxfjjc`). Every file op under **`AppData\Roaming`/`AppData\Local`** is silently redirected into `…\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\{Roaming,Local}\`, even though `$env:APPDATA` prints the normal path. Proof: (1) a marker written to `AppData\Roaming\file-portal\` appeared in the package container; (2) the "two" file-portal `config.toml` I kept finding share ONE File ID (same physical file via the redirect). The widget reads its tiles from `config.toml` in `AppData\Roaming\file-portal`; `list_portals` returns `config::default()` (6 tiles, no `convert-gpu`) when no config is found. So: Claude-launched widgets (packaged) read the sandbox config (7 tiles) and every Claude "config fix" wrote to the sandbox; Rab's normal UNPACKAGED launches read the REAL AppData, which never got those fixes → 6-tile defaults. **Scope = AppData ONLY** (LocalCache mirrors only Roaming+Local): `ml\library`, `Documents`(vault), `Projects`(repo) are NOT redirected — real shared filesystem, so all repo/vault/pipeline work is genuinely real.
**Wrong turn (documented for honesty):** I first concluded "stale frontend embedding" from grepping `target\release\file-portal-widget.exe` (S17 strings found, S18+ missing). That grep is invalid — Tauri **brotli-compresses** embedded assets, so app strings are unfindable regardless of age (`data-tauri-drag-region` matched Tauri's own framework copy). I forced clean rebuilds chasing it; harmless but unnecessary. Decompressing the codegen asset settled it: the embedded `main.js` is the current 23,854 bytes with `convert-gpu`/`st-gate`/ticker — the exe was current all along.
**Fix applied:** staged the good 7-portal config to the shared `ml\library\config-RESTORE-to-real-appdata.toml`; Rab ran an UNPACKAGED PowerShell (`$env:APPDATA` → real Roaming) to copy it into the real `AppData\file-portal\config.toml` (verified 7 portals). Rab confirmed: ⚡ GPU→Vault tile is back and **stays** across taskbar/shortcut launches. Orphan watcher (8796/3160) swept during the session; no widget or watcher left running by Claude.
**Decision — permanent fix DECLINED (with reason):** do NOT move the widget config out of AppData in code. AppData is the correct per-user location for the "works for anyone who clones" design (config.rs); bending it to dodge Claude's sandbox would pollute a clean design for a dev-tooling quirk. The durable fix is procedural + already in memory (desktop-machine "THE BIG ONE"): **Claude must never treat its AppData view as Rab's truth; config/state changes get staged to a shared path for Rab to apply unpackaged.** Optional future nicety (only if it keeps biting): a `FILE_PORTAL_CONFIG` env override so a Claude launch can point at a shared config. `tauri-plugin-single-instance` remains a reasonable independent polish (prevents duplicate windows) but was NOT the bug.
**§4 `aefec8c..HEAD`:** CLAUDE_README only (open plan + this close). No source/CHANGELOG change (nothing in the codebase changed; the fix was environmental + a user-applied config copy). Ledger row follows.

### 2026-07-20 — Desktop agent Session 30 (Claude Code / Opus 4.8) — the Assay: enforcement signed, projection designed
**Machine:** DESKTOP-OBTQIRD. *(Opened at Rab's "full throttle on docs/15 + design a widget visualization for variety control & observation." Survey → refreshed memory (segment control-room/analyst/convert-marker/vault-export) → design → the verifiable Python+docs core here; the Tauri build is a dedicated follow-on session.)*
**Enforcement SIGNED (docs/15 §12):** Rab chose "degeneration + analyst near-exact only." `windows-converter/fidelity_audit.py` `compute_verdict` rewritten — **degeneration** (OCR/LLM repetition loops; witness-free, so it gates on EITHER lane) and **analyst loss** (`doc<0.995 OR run≥25`) are now the sole `fail` signals; survival/agreement, page flags, omission runs, garbage-rate are report-only **localizers** (`flag` at most). A clean-lane survival gate was explicitly considered and REJECTED (acceptable books measured 0.76–0.96 survival = legitimate reflow). Module header comment updated to match.
**Verified (not asserted):** ran the edited `compute_verdict` + real `degeneration()` over all four vaulted books' markdown (marker-env python, read-only). **Brain of the Firm → `fail`** (degeneration True; worst block zlib 0.003, trigram ×2,267 — the §9.1 "Stage of the Stage of…" loop); **Designing Freedom, bojieli, Textor → `pass`** (degeneration False). **Zero false positives**; the prototype's loose-threshold Textor false alarm is cleared at the production 0.20/40 priors.
**Enforcement is separated from the verdict:** the verdict is always computed + recorded; whether a `fail` PARKS a bundle is a default-off lever — `audit-mode.txt` (`report`|`enforce`; a `fail` under `enforce` → `held/<sha16>/` + `audit/held` event). Contract written (docs/15 §12); the ship-path wiring (`_enforce_hold` in ship/defer/resume) is deliberately left to the build session so it lands + live-tests with the widget toggle. **No pipeline behavior changed this session** (verdict semantics only; nothing gates, enforce defaults off).
**Design (docs/15 §13 "The Assay"):** the audit as a see-and-steer channel (VSM System 3\* / algedonic framing). A `◎ assay` line station (verdict dot: green pass / amber flag / **terracotta fail — the only pulse**) + an evidence card on flag/fail (a book-length **damage map** with loop zones as bands, the worst **runs verbatim**, the `report ⇄ enforce` control, a `⟳ re-convert` remedy trigger) + the fidelity verdict on the ship receipt. Rendered as a private "Assay" design artifact in the widget's own language. **The remedy's vault swap is honestly bounded by THE SUPERSEDE GAP** — manual content-replace until the ThinkPad exporter supersede flow lands (phase-gated); drawn as such, not papered over.
**Next (the dedicated Assay build session):** Tauri build — Rust `assay_status`/`audit_mode_get|set`/receipt verdict, the frontend station+card+damage-map+toggle, CSS, `_enforce_hold` wiring, the `⟳ re-convert`+manual-swap remedy; then live-test the Beer flag→re-convert→re-audit→supersede loop on the retained specimen. Needs the rebuild ritual (kill widget first; `cargo clippy -D warnings`; build; launch). Memory refreshed (segment-control-room next-builds, file-portal-project state/queue, cookie).
**§4 `e77dd40..HEAD`:** `windows-converter/fidelity_audit.py` (compute_verdict + header) → CHANGELOG "Changed" entry; `docs/15` (§8 pointer + §12 sign-off + §13 The Assay); CLAUDE_README (Current Session Plan + Status S30 + Next-up + this close) → ledger row in the follow-up commit. No Rust/convert_and_ship changed.

### 2026-07-20 — Desktop agent Session 31 (Claude Code / Opus 4.8) — the Assay is built
**Machine:** DESKTOP-OBTQIRD. *(Build session — Rab: "start the Assay build session, full throttle." Dedicated Tauri build of the docs/15 §13 projection. Widget was live (PID 8428); source edited, the build+relaunch ritual handed to Rab.)*
**Built:**
- **Rust** `windows-widget/src-tauri/src/assay.rs` (new) — pure projection: `status()` reads the newest anchor/pending/held `manifest.json` fidelity block (verdict, doc_survival, kind, pages_scored, degeneration_detail, runs, analyst) + the `held/` queue + the lever; `get_mode`/`set_mode` on `audit-mode.txt`; `reconvert()` re-queues `drop/done/<src>`→`drop/` (bare-filename guard). `main.rs`: `mod assay` + 4 commands (`assay_status`/`audit_mode_get`/`audit_mode_set`/`assay_reconvert`) registered.
- **Frontend** — `index.html`: `◎ assay` station (gate↔ship) + `#assay-card`. `main.js`: `assayLoop` (20 s poll); station dot (green pass / amber flag / terracotta-pulse fail); the evidence card — damage map from `zones[].line ÷ md_lines` (degeneration, terracotta bands) + omission `runs[].page ÷ pages_scored` (amber), verbatim runs, `report ⇄ enforce` toggle → `audit_mode_set`, `⟳ re-convert` → `assay_reconvert`, held list; verdict appended to the ship receipt. `styles.css`: card/map/dots, terracotta reserved for `fail`.
- **Python** — `convert_and_ship.py`: `audit_mode()` (`audit-mode.txt`, default `report`) + `_enforce_hold()` (park a `fail` in `held/<sha16>/`; fails OPEN so a lever/IO error never loses a bundle) guarding all 3 ship sites (direct `main`, `defer` auto-local, `resume`). `fidelity_audit.degeneration()` returns `md_lines` (the damage-map denominator).
**Verification (as far as possible without relaunching):** `cargo clippy --all-targets -- -D warnings` CLEAN (one lint caught+fixed: `manual_pattern_char_comparison` → array form); `py_compile` both converter files; `audit_mode()` → `report` (enforcement is a verified no-op until flipped); `node --check main.js` parses. **Did NOT run `npm run tauri build` or relaunch** — the widget was live (PID 8428) and the rebuild ritual (kill widget first — it locks its own exe; sweep orphan marker-env pythons) is Rab's to drive; a Claude-launched widget would also read the sandbox AppData config (S29). Guardrails held: projection only (Python owns the verdict), terracotta = `fail` only, enforce default-off, remedy swap bounded by THE SUPERSEDE GAP (manual content-replace).
**Next (Rab-driven):** rebuild ritual → launch → confirm the `◎` station + card render (watch the now-6-station line doesn't clip at 480 px) → flip `report ⇄ enforce` → drop Brain-of-the-Firm and drive the flag→re-convert→re-audit loop; then the ThinkPad exporter supersede flow for the auto-swap.
**§4 `6630687..HEAD`:** `assay.rs` (new) + `main.rs` + `index.html` + `main.js` + `styles.css` + `convert_and_ship.py` + `fidelity_audit.py` → CHANGELOG "Added" entry; CLAUDE_README (open plan `d7a737b` + Status S31 + Next-up + this close) → ledger row in the follow-up commit.

### 2026-07-21 — Desktop agent Session 32 (Claude Code / Opus 4.8) — live-test hardening + rebuild
**Machine:** DESKTOP-OBTQIRD. *(Rab installed the S31 widget from the Start menu and drove real drops; four defects surfaced that only a live end-to-end run could expose. Fixed, verified, committed, rebuilt. Rab went to bed mid-session; the dashboard-prototype build he commissioned is the SEPARATE next session, S33.)*
**Four defects found + fixed (all by actually running it):**
1. **Auto-start crash (HIGH) — `watcher.rs` + `preflight.rs`.** The boot log showed `watcher_start: running` every launch, but no watcher ever logged "watching" and drops piled up unconverted. Root cause: a Start-menu (GUI, windows-subsystem) launch has NO console, so the spawned Python child inherited invalid std handles and died on startup. Fix: spawn children with explicit `Stdio::null()`. Masked before because terminal/dev launches had a console to inherit — this only bit once the widget became a real installed app. **Proven** by starting the watcher directly (with a console): it ran fine and converted.
2. **UI freeze (MED) — `main.rs`.** `vault_check`/`vault_pull` do a no-timeout `git fetch` over tailscale ssh, and Tauri runs sync commands on the main UI thread → the widget went "not responding" every 45 s poll while the ThinkPad was unreachable ("vault host unreachable" in the status line was the tell). Fix: `async` + `tauri::async_runtime::spawn_blocking`. Diagnosis confirmed by reading `vault.rs` (no timeout) + the offline-host symptom.
3. **Clean-lane VRAM thrash (MED) — `convert_and_ship.route()`.** A figure-dense born-digital book (Dubberly/Pangaro cybernetics models, 91 pp) ran Marker UNCAPPED on the clean lane, auto-scaled its batch to fill the 10 GB card (VRAM pinned 9.9/10, 100% util), thrashed, and hit Marker's 3600 s timeout → DNF. Beer's 439 pp finished only because the scan lane is capped. Fix: cap the clean lane too (`--recognition_batch_size 32`). **Live-verified:** re-convert peaked ~8.0 GB with ~2 GB headroom, no thrash. (Rab's own Beer counterexample pointed straight at the missing cap.)
4. **Audit false positives (MED) — `fidelity_audit.degeneration()` (docs/15 §9.2).** That same book converted fine but the degeneration tripwire fired `fail` (held, enforce mode) on legitimate structure: dense tables tripped the zlib half (zlib 0.11/0.15, but trigram only ×28/×10 — real Beer loops are ×2,267), and repeated section headings (`#### a. goal of model` ×48) tripped the repeated-line check. Recalibrated: block rule `OR`→`AND` (a loop is BOTH crushed-zlib AND word-repetitive); repeated-line check now the longest CONTIGUOUS run (loops repeat contiguously; headings/tables are distributed). **Re-verified over all 5 books** (marker-env, read-only): Beer flags (zlib 0.003, tri ×2,267), Cybernetics + Designing Freedom + bojieli + Textor clear. This is docs/15 §9 step 3 ("show its false alarms before it pulses terracotta") working as designed on the first live drop.
**Rebuild:** stopped the temp watcher I'd started (a console-launched watcher was carrying conversions while the widget's own kept dying); swept it + any running widget; `npm.cmd run tauri build` succeeded (51 s, MSI + NSIS, fresh `file-portal-widget.exe` 02:03 with the Rust fixes). **Did NOT reinstall** — a headless per-user NSIS install would land in the MSIX sandbox (S29); the fresh installer is staged for Rab to double-click in the morning.
**Verification:** clippy `-D warnings` clean; `py_compile` both converter files; degeneration recalibration re-verified over the full corpus. Nothing pushed to the pipeline's behavior beyond the four fixes.
**Next:** Rab runs the installer (Start-menu launch → self-sufficient widget: autostart survives, no freeze, capped converts, recalibrated audit). Then S33 = the professional control-panel dashboard prototype (quarantined) he commissioned overnight.
**§4 `9f6d5e1..HEAD`:** `watcher.rs` + `preflight.rs` + `main.rs` + `convert_and_ship.py` + `fidelity_audit.py` → CHANGELOG "Fixed"; `docs/15` (§9.2 recalibration record); CLAUDE_README (open plan `c34f938` + Status S32 + this close) → ledger row. Widget rebuilt (binary, not tracked).

### 2026-07-21 — Desktop agent Session 33 (Claude Code / Opus 4.8) — the Opsroom (dashboard prototype)
**Machine:** DESKTOP-OBTQIRD. *(Autonomous overnight session — Rab commissioned a professional control-panel prototype and went to sleep, with explicit latitude to take my time, research the web, and quarantine the result. Followed the build-workflow cadence: survey → refresh memory → research → design → build → document.)*
**Commissioned:** a professional, lightweight, "full-fledged app" dashboard representation of the pipeline — live numbers, loading bars, a live transit viewer, pipeline segmentation, the audit — "akin to what's marketed by Claude Design," from high-order researched references, quarantined from the pipeline, documented, elite code organization.
**Research (WebSearch; sources in DESIGN.md):** Project Cybersyn's Operations Room (Beer + Bonsiepe, 1972 — the hexagonal cybernetic control room; orange cushions → the project's clay accent; Ulm/Bonsiepe restraint) · ISOTYPE (Neurath/Arntz — iconic glanceable grammar) · modern observability practice (Grafana/SRE golden signals, "healthy in seconds", drill-down) · Linear (restraint, sans-UI + mono-data) · the Claude Design System (the named target). **Thesis:** a control room for a viable system, in the lineage of the one the author of these very books built.
**Built (quarantined):** `prototypes/` — a new quarantine section + convention (category/name, zero pipeline coupling, CI-untouched) → `prototypes/control-panel/opsroom/opsroom.html`: one self-contained, zero-dependency page — the 6-station line, a live **canvas transit viewer**, golden-signal KPI tiles, a convert-station progress panel (live ETA), the Survival Audit panel (verdicts + damage map), a live event stream. Theme-aware (committed-dark + a deliberate light), `prefers-reduced-motion`-safe, palette-cached (60 fps canvas never touches layout). All figures from the real pipeline. `DESIGN.md` records research/references/decisions; `prototypes/README.md` the convention. Published as a private **Artifact:** https://claude.ai/code/artifact/58b778cf-3c5d-464d-aef7-cc6bb4d0cadc
**Verification:** JS `node --check` clean; **two real bugs caught + fixed on review** — SVG `stroke="var(--x)"` doesn't resolve (custom props don't apply to presentation attributes) → resolved via the cached palette; `getComputedStyle` called per canvas frame → cached once + on theme change (keeps it "super light"). The in-app browser blocks claude.ai + localhost so no live screenshot was possible; did NOT open Rab's real Chrome (he's asleep — too intrusive for a disposable prototype). Quality relied on syntax verification + careful authoring; the prototype is explicitly disposable/iterable.
**Boundaries held:** reads/writes/triggers NOTHING in the pipeline; simulated data only; quarantined; graduating it is a separate explicit decision.
**Next / awaiting Rab:** his verdict on the direction ("if it sucks," it's captured as a record or deletable — built to be disposable). If it lands: wire it to the existing `invoke()` projections (`line_state`/`assay_status`/`shift_summary`/`last_receipt`) and decide the surface (larger window / separate ops window / tray panel).
**§4 `650d067..HEAD`:** `prototypes/**` (README, opsroom.html, DESIGN.md) + CHANGELOG "Added" → feat commit `4c7de7f`; CLAUDE_README (open plan `60fb4ff` + Status S33 + this close) → ledger row.
