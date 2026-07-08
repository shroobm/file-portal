# CLAUDE_README — File Portal / Library Pipeline Mission Brief

*Last updated: 2026-07-05 by Desktop agent (Cowork/Dispatch) — Session 2*
*Read this file first when activating on any machine in this project.*

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
- Commit and push:
  ```bash
  git add CLAUDE_README.md
  git commit -m "session: close — [machine] [date]"
  git push
  ```

---

## Current Session Plan

*Replace this section at the start of each session. Commit it before starting work.*

**Machine:** [DESKTOP-OBTQIRD / ThinkPad C14]
**Date:** YYYY-MM-DD
**Claude:** [Cowork / Claude Code / Fable]

### What I'm planning to do (in order):
1.

### How I'll verify each step:
1.

### Dependencies / blockers:
-

---

## Status Summary (as of 2026-07-08)

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
- ▶ Next up: **Desktop — W5 visual re-check (30s ✓ test) + W6 (Convert tile)** closes Part 2 "Done when"; **ThinkPad — Part 3 (L7-L10, converter engine — dedicate a full session)**

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

- [ ] **W6 — Add Convert tile**
  File: `%APPDATA%\file-portal\config.toml`
  ```toml
  [[portals]]
  category = "convert"
  label = "To Vault"
  icon = "🔁"
  ```
  Also mirror into `src-tauri/src/config.rs` `AppConfig::default()` and `windows-widget/portals.json`

### Part 3 — Windows Tasks (after Part 3 Linux is done)

- [ ] **W7 — Add Convert-Scan tile**
  Same as W6 but: `category = "convert-scan"`, `label = "Scan → Vault"`, `icon = "🔍"`

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

- [ ] **L7 — Install engines**
  ```bash
  pip install pymupdf4llm --break-system-packages
  sudo pacman -S tesseract tesseract-data-eng pandoc
  ```
  CRITICAL: `import pymupdf.layout` BEFORE `import pymupdf4llm`

- [ ] **L8** — Dispatch by extension (`.pdf`/`.epub` → PyMuPDF4LLM; `.docx` → Pandoc)
- [ ] **L9** — Two lanes: Clean (`force_ocr=False`) and Scan (`force_ocr=True`, `ocr_dpi=300`)
- [ ] **L10** — Bundle output: markdown + assets folder, write to anchor/master + staging

### Part 4 — Linux Tasks

- [ ] **L11** — Return transport (recommended: git/Forgejo)
- [ ] **L12** — Place by frontmatter tags; delete staging after send

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
| 3 | Clean-lane failure: bounce whole file vs convert-and-flag | Your call |
| 4 | Return transport method | git/Forgejo |
| 5 | Graph links: dense/dirty vs sparse/earned | Your call |

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
