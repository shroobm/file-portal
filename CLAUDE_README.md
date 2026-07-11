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
- ▶ Next up: **ThinkPad — L11 (exporter) + L12 (staging deletion)** per the now-resolved Decisions #4/#5/#6. Desktop has no open tasks.

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

- [ ] **L11 — Exporter** (transport already wired + verified 2026-07-10, see Decision #4):
  watch `library/staging/`, copy each bundle into `~/file-portal/vault-work` at
  `Library/Inbox/<slug>--<sha256[:8]>/`, commit, push to the local bare repo. Constraints:
  creates new notes only, never edits existing ones; re-ingest of an identical
  `source_sha256` is a no-op with a log line; assets stay inside the bundle folder.
- [ ] **L12 — Staging deletion**: delete the staging bundle only after the commit exists
  AND `git cat-file -e` confirms the blob — never on write-success alone. No tag/folder
  placement (Decision #6); no `[[link]]` minting (Decision #5).

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
