# CLAUDE_README — File Portal / Library Pipeline Mission Brief

*Last updated: 2026-07-05 by Desktop agent (Cowork/Dispatch)*
*Read this file first when activating on any machine in this project.*

---

## Status Summary (as of 2026-07-05)

- ✅ File Portal v2 status feedback loop — Tauri v2 built (45s, 2 bundles), all 4 files committed
- ✅ `coordination/messages/` folder created in repo
- ✅ Desktop build report written and committed to `feat/library-pipeline`
- ✅ Branch `feat/library-pipeline` pushed to origin
- ⏸ E2E test — widget running, needs user at desktop to approve File Portal access dialog
- ⏸ All Library Pipeline Parts — not yet started; Part 1 Linux gates everything

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

**Task W1 — Make transfer atomic** (fixes file-corruption race)
File: `src-tauri/src/transfer.rs`
- Build `remote_tmp = "{remote_dir}/.part-{filename}"`
- Set `remote_cmd = "mkdir -p {dir} && cat > {tmp} && mv -f {tmp} {final}"` (quote tmp and final via `remote_path_expr`)
- Why: receiver currently sees `on_created` on a half-written file; atomic rename hits the safe `on_moved` path

**Task W2 — Stream, don't buffer** (prevents OOM on large files)
Same file: `src-tauri/src/transfer.rs`
- Replace `read_to_end` into a `Vec` with `std::io::copy(&mut local_file, &mut stdin)`

**Task W3 — Widget window controls** (independent quick win — no separate rebuild)
- `src/index.html`: add `<div id="titlebar" data-tauri-drag-region>` containing a title span and `#min-btn` button (button has NO drag attribute)
- `src/styles.css`: style `#titlebar` (height ~26px, `cursor: grab`) and `#min-btn` hover state
- `src/main.js`: add `const { getCurrentWindow } = window.__TAURI__.window;` and wire `document.getElementById("min-btn").addEventListener("click", () => getCurrentWindow().minimize())`
- NEW FILE `src-tauri/capabilities/default.json`:
  ```json
  {
    "identifier": "default",
    "description": "Default capability",
    "windows": ["main"],
    "permissions": [
      "core:default",
      "core:window:allow-start-dragging",
      "core:window:allow-minimize"
    ]
  }
  ```
- `tauri.conf.json`: bump window `height` from 160 → 186

**Task W4 — Rebuild** after W1–W3:
```
npm run tauri build
```

**Task W5 — E2E test** (needs user present at desktop)
- Approve File Portal computer-use access dialog
- Drop a .pdf onto a portal tile → expect green "✓ allocated"
- Drop a .xyz onto a portal tile → expect red "✗ rejected"
- Verify UI tile color feedback updates within ~30s

### Part 2 — Windows Tasks (after Part 1 Linux is done)

**Task W6 — Add Convert tile**
File: `%APPDATA%\file-portal\config.toml`
```toml
[[portals]]
category = "convert"
label = "To Vault"
icon = "🔁"
```
Also mirror into `src-tauri/src/config.rs` `AppConfig::default()` and `windows-widget/portals.json`

### Part 3 — Windows Tasks (after Part 3 Linux is done)

**Task W7 — Add Convert-Scan tile**
Same as W6 but: `category = "convert-scan"`, `label = "Scan → Vault"`, `icon = "🔍"`

---

## MACHINE: ThinkPad C14 (Arch Linux)

*Claude Code in `~/Projects/file-portal` (or wherever the repo is cloned)*

### Part 1 — Linux Tasks ⚠️ GATE — must complete before anything else ⚠️

**Task L1 — Kill quarantine loop** (critical bug — stuck files keep re-processing)
File: `linux-receiver/allocator/config.py`
Change:
```python
# OLD
quarantine = root / "inbox" / "quarantine"
# NEW
quarantine = root / "quarantine"
```
Update `Paths.from_root` and `ensure_exist` accordingly.
Why: quarantining a file fires `on_moved` inside the watched tree, which re-handles it and un-quarantines it into `sorted/misc`.

**Task L2 — Ignore temp/dotfiles in watcher**
File: `linux-receiver/allocator/main.py`, inside `_handle` method
Add at the very top of the method:
```python
if file_path.name.startswith("."):
    return
```
Why: protects against .part-* temp files from the atomic transfer (Task W1)

**Task L3 — Enable persistence**
Run on the ThinkPad:
```bash
sudo systemctl enable --now tailscaled
sudo loginctl enable-linger "$USER"
```
Verify all three pass:
```bash
systemctl is-enabled tailscaled                         # → enabled
loginctl show-user "$USER" --property=Linger            # → Linger=yes
systemctl --user is-enabled file-portal-allocator       # → enabled
```

**Task L4 — Put linger in installer**
File: `scripts/linux/bootstrap-arch.sh`
Add: `sudo loginctl enable-linger "$USER"`
(Do NOT add to `install.sh` — that script refuses sudo by design)

**Done when Part 1:** a 200MB+ file transfers without truncation; an oversized file lands in `quarantine/` and STAYS there; allocator + tailscaled survive a reboot with no login.

### Part 2 — Linux Tasks

**Task L5 — Route the convert category**
File: `linux-receiver/config/rules.toml`
Add:
```toml
[[rule]]
category = "convert"
match = ["*.pdf", "*.epub", "*.docx"]
destination = "pipeline/convert-inbox"
```
(Allocator auto-creates `inbox/convert/` at startup)

**Task L6 — Scaffold converter service**
New directory: `linux-converter/` mirroring `linux-receiver/` structure
Files needed: pyproject, requirements, `systemd/file-portal-converter.service` (as `--user` service), `scripts/install.sh`
Watches: `~/file-portal/pipeline/convert-inbox`
At this stage: only LOG "would convert <path>" — no conversion engine yet
Enable: `systemctl --user enable --now file-portal-converter`

**Done when Part 2:** dropping a PDF on the Convert tile lands it in `pipeline/convert-inbox` and the converter service logs the arrival.

### Part 3 — Linux Tasks (HEAVY — dedicate a full session after reset)

**Task L7 — Install engines**
```bash
pip install pymupdf4llm --break-system-packages
sudo pacman -S tesseract tesseract-data-eng pandoc
```
CRITICAL: `import pymupdf.layout` BEFORE `import pymupdf4llm` or auto-OCR silently fails on image-only pages.

**Task L8 — Dispatch by extension**
- `.pdf`/`.epub` → PyMuPDF4LLM handler
- `.docx` → Pandoc handler (`pandoc -f docx -t markdown --extract-media=<assets>`)

**Task L9 — Two conversion lanes**
- Clean lane (category `convert`): `force_ocr=False`, run membership test for real text layer, reroute to scan if fails
- Scan lane (category `convert-scan`): `use_ocr=True`/`force_ocr=True`, `ocr_language=<code>`, `ocr_dpi=300`

**Task L10 — Bundle output**
```python
to_markdown(..., write_images=True, image_path="<bundle>/assets", dpi=150)
```
- Rewrite `![](assets/..)` → Obsidian `![[..]]`
- Output a bundle folder (markdown + assets), never a bare file
- Write to: (a) anchor/master + `manifest.json` (source SHA-256, converter version, timestamp); (b) staging/exports queue

### Part 4 — Linux Tasks

**Task L11 — Return transport** (recommended: git/Forgejo)
Converter commits the bundle into the vault repo; desktop pulls via Obsidian Git or scheduled pull.
Alternatives: Taildrop (`tailscale file cp`) or Windows OpenSSH + rsync `--remove-source-files`.

**Task L12 — Place by tags**
Map frontmatter tags → vault subfolder. Staging copy deleted on successful transport. Anchor retains permanent snapshot.

---

## Cross-Machine Communication Protocol

### Method 1 — Git-based messages (current, async) ✅
Write a markdown file to `coordination/messages/` with this filename format:
```
YYYY-MM-DDTHH-MM--{from}-to-{to}--{subject}.md
```
Commit and push. The other agent pulls and reads.
**Already in place.** Use this for status updates between sessions.

### Method 2 — Tailscale SSH shared file (lightweight sync)
Both agents can read/write a JSON state file on the ThinkPad via:
```bash
# Desktop → write to ThinkPad
tailscale ssh user@thinkpad "cat > ~/file-portal/coordination/state.json" < state.json
# Desktop → read from ThinkPad
tailscale ssh user@thinkpad "cat ~/file-portal/coordination/state.json"
```
Desktop `status.rs` already uses this pattern. Extend it for bidirectional state.

### Method 3 — MCP server over Tailscale (real-time, optional)
If file-based is too slow, run a lightweight MCP HTTP server on the ThinkPad:

**Setup (ThinkPad):**
```bash
pip install mcp --break-system-packages
# Or use a simple Flask/FastAPI MCP endpoint
# Bind to 0.0.0.0 so Tailscale can reach it
# Suggested port: 8765
```

**Desktop agent config** (`~/.claude/settings.json` or similar):
```json
{
  "mcpServers": {
    "thinkpad-coordination": {
      "url": "http://100.XX.XX.XX:8765/mcp",
      "transport": "http"
    }
  }
}
```
Replace `100.XX.XX.XX` with ThinkPad's Tailscale IP (check with `tailscale ip -4`).

The MCP server can expose tools like `post_status`, `get_status`, `list_messages` for real-time coordination.

---

## Open Decisions

| # | Decision | Recommended |
|---|---|---|
| 1 | Disable Tailscale key expiry on always-on nodes | Yes — unattended reliability |
| 2 | Convert tile only vs push-from-library-on-demand | Tile only |
| 3 | Clean-lane failure mode: bounce whole file vs convert-and-flag | Your call |
| 4 | Return transport method | git/Forgejo |
| 5 | Graph links: dense/dirty (instant graph, junk nodes) vs sparse/earned | Your call |

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
