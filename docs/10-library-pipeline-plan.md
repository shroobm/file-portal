# File Portal → Library Pipeline — Execution Plan

**Branch:** `feat/library-pipeline` (single new branch; each Part is an ordered milestone of commits)
**Strategy:** 4 parts, dependency-chain order, ~24h, usage-conserving. Each Part lands on the verified output of the one before it. Do **not** parallelize across the chain — Part *N+1* assumes Part *N* is correct.
**Drop this file in:** `docs/10-library-pipeline-plan.md` on the branch, and check items off as you go.

---

## Tooling

| Machine | Tool | Why |
|---|---|---|
| ThinkPad (Arch Linux) | **Claude Code** | Only option there, and correct — all Linux work is repo code (Python allocator/converter, systemd units, shell). |
| Desktop (Windows) | **Claude Code** | Today's Windows deliverables are repo code (Rust/JS/CSS/JSON) that must build with `cargo tauri` and lint. That's Claude Code's lane — not Dispatch (phone→desktop kickoff) or Cowork (multi-step knowledge work). Use **Cowork** *only* if you later want the architecture decision-records written up as prose docs; the code itself stays in Claude Code. |

**Both machines work the same branch.** They touch non-overlapping directories — Linux owns `linux-receiver/`, the new `linux-converter/`, and `config/`; Windows owns `windows-widget/`. **Pull before every push.** No file conflicts if you stay in your lane.

### Git, once
```bash
# on either machine, from main
git checkout -b feat/library-pipeline
git push -u origin feat/library-pipeline
# on the other machine
git fetch origin && git checkout feat/library-pipeline
```
Commit per logical change. Optionally tag each milestone: `git tag part-1-done && git push --tags`.

---

## PART 1 — Foundation: correct transport, correct allocator, always-on
*Nothing downstream works until the base is atomic and persistent. This is the load-bearing link.*

**Depends on:** nothing. **Machines:** Linux + Windows (independent files).

### Linux (Claude Code)
- [x] **Kill the quarantine loop.** `linux-receiver/allocator/config.py`: move quarantine **out of** the watched inbox tree. Change `quarantine = root / "inbox" / "quarantine"` → `quarantine = root / "quarantine"`. Update `Paths.from_root` and `ensure_exist`. *(Currently quarantining a file fires `on_moved` inside the watched tree, which re-handles it and un-quarantines it into `sorted/misc`.)*
- [x] **Ignore temp/dotfiles in the watcher.** `allocator/main.py` `_handle`: add at the top `if file_path.name.startswith("."): return`. Protects against seeing the `.part-*` temp files from the new transfer pattern below.
- [x] **Persistence.** Run `sudo systemctl enable --now tailscaled`; `sudo loginctl enable-linger "$USER"`. Verify: `systemctl is-enabled tailscaled` → `enabled`, `loginctl show-user "$USER" --property=Linger` → `Linger=yes`, `systemctl --user is-enabled file-portal-allocator` → `enabled`.
- [x] **Put linger in the installer.** Add `sudo loginctl enable-linger "$USER"` to `scripts/linux/bootstrap-arch.sh` (which already uses sudo) — **not** `install.sh`, which refuses sudo by design.

### Windows (Claude Code)
- [x] **Make transfer atomic.** `windows-widget/src-tauri/src/transfer.rs`: change the remote command from writing straight to the final name to a temp-then-rename. Build `remote_tmp = "{remote_dir}/.part-{filename}"`; set `remote_cmd = "mkdir -p {dir} && cat > {tmp} && mv -f {tmp} {final}"` (quote `tmp` and `final` via `remote_path_expr`). *(This makes the receiver see an atomic rename → allocator's safe `on_moved` path, instead of `on_created` on a half-written file. This is the race we diagnosed — and the same pattern the converter watcher reuses in Part 2.)*
- [x] **Stream, don't buffer.** Same file: replace `read_to_end` into a `Vec` with `std::io::copy(&mut local_file, &mut stdin)` so large Archive drops don't load fully into RAM on the 16GB box.
- [x] **Widget window controls** *(independent quick win)*. Apply the four edits:
  - `src/index.html`: add `<div id="titlebar" data-tauri-drag-region>` with a `data-tauri-drag-region` title span and a `#min-btn` button (button has **no** drag attribute).
  - `src/styles.css`: style `#titlebar` (height ~26px, `cursor: grab`) and `#min-btn` hover.
  - `src/main.js`: add `const { getCurrentWindow } = window.__TAURI__.window;` and wire `#min-btn` → `getCurrentWindow().minimize()`.
  - **NEW** `src-tauri/capabilities/default.json`: `windows: ["main"]`, permissions `["core:default", "core:window:allow-start-dragging", "core:window:allow-minimize"]`. *(Without this the buttons silently do nothing.)*
  - `tauri.conf.json`: bump window `height` 160 → ~186 so the bar doesn't crowd the tiles.
- [x] *(If time)* `config.rs`: surface a TOML parse error instead of silently reverting to `CHANGE_ME` defaults. `main.rs`: fix the stale "rsync/scp" header comment to describe the `cat`-stream reality.

**Done when:** a 200MB+ file transfers without truncation; an oversized file lands in `quarantine/` and **stays** there; allocator + tailscaled survive a reboot with no login; the widget drags by its bar and minimizes to the taskbar.
**Decision:** disable Tailscale **key expiry** on the two always-on nodes (admin console → Machines)? Recommended yes for unattended reliability; the tradeoff is the stolen-device auto-revoke you noted in `06-security-model.md`.

---

## PART 2 — Converter entry: the tile, the category, the safe watcher
*Establish the front door and the event-driven intake — no conversion engine yet.*

**Depends on:** Part 1 (reuses the atomic watcher pattern; assumes a correct allocator). **Machines:** Windows + Linux.

### Windows (Claude Code)
- [ ] **Add the Convert tile.** Edit `%APPDATA%\file-portal\config.toml` `[[portals]]`: `category = "convert"`, `label = "To Vault"`, `icon = "🔁"`. Relaunch — tile appears (no rebuild). Mirror into `src-tauri/src/config.rs` `AppConfig::default()` and `windows-widget/portals.json` so fresh installs ship it.

### Linux (Claude Code)
- [x] **Route the category.** *(Verified live on ThinkPad 2026-07-07: `.pdf` → `pipeline/convert-inbox/`, unmatched ext → `sorted/misc/`.)* `linux-receiver/config/rules.toml`: add
  ```toml
  [[rule]]
  category = "convert"
  match = ["*.pdf", "*.epub", "*.docx"]
  destination = "pipeline/convert-inbox"   # a process mouth, NOT under sorted/
  ```
  *(Allocator auto-creates `inbox/convert/` at startup from this rule.)*
- [x] **Scaffold the converter service.** *(Installed + enabled on ThinkPad 2026-07-07; e2e verified: allocator hop → `would convert` logged, dotfiles ignored.)* New `linux-converter/` mirroring `linux-receiver/` structure (pyproject, requirements, `systemd/file-portal-converter.service` as `systemd --user`, `scripts/install.sh`). It watches `~/file-portal/pipeline/convert-inbox` using the **same** event model as Part 1 (prefer `on_moved`, skip dotfiles). At this stage it only **logs** `would convert <path>` — no engine. Enable it (linger already on).

**Done when:** dropping a PDF on the Convert tile lands it in `pipeline/convert-inbox` and the converter service logs the arrival.
**Decision:** Convert tile as the **only** entry, or also add a rule to push existing `sorted/documents` PDFs into conversion on demand? Recommended tile-only for now — simplest, and intent stays human-declared at the drop.

---

## PART 3 — Converter engine: dispatch, OCR lanes, bundle output
*The heaviest part. The unanimous converter with case-dispatch + the Clean/Scan split.*

**Depends on:** Part 2 (entry + watcher skeleton). **Machines:** Linux (heavy) + Windows (light).

### Linux (Claude Code)
- [ ] **Install engines.** `pip install pymupdf4llm`; `sudo pacman -S tesseract tesseract-data-eng pandoc`. **Critical:** `import pymupdf.layout` **before** `import pymupdf4llm` or auto-OCR silently never fires on image-only pages.
- [ ] **Dispatch by extension (format-as-set).** `.pdf`/`.epub` → PyMuPDF4LLM; `.docx` → Pandoc (`pandoc -f docx -t markdown --extract-media=<assets>`). Each handler owns its membership by extension. **Do not** give docx its own tile — the extension is a free, certain test.
- [ ] **Two lanes.**
  - **Clean** (`convert` category): `force_ocr=False`, trust the text layer. Run a **membership test** — pre-analyze whether a real text layer exists. On a page that fails, reroute (see decision).
  - **Scan** (`convert-scan` category, added below): `use_ocr=True` / `force_ocr=True`, `ocr_language=<code>`, higher `ocr_dpi` (e.g. 300).
- [ ] **Images → bundle.** `to_markdown(..., write_images=True, image_path="<bundle>/assets", dpi=150)` (layout mode off for image extraction). Rewrite `![](assets/..)` → Obsidian `![[..]]`. Output a **bundle folder** (markdown + assets), never a bare file.
- [ ] **Write to two places.** (a) **anchor/master** folder: the immutable as-converted snapshot + a `manifest.json` (source PDF SHA-256, converter version, timestamp). (b) **staging/exports** queue (transient).

### Windows (Claude Code)
- [ ] **Add the Convert-Scan tile.** `config.toml` + `config.rs` default + `portals.json`: `category = "convert-scan"`, `label = "Scan → Vault"`, `icon = "🔍"`. Linux `rules.toml`: add a `convert-scan` rule → `pipeline/scan-inbox`. Converter watches both inboxes and applies the matching lane.

**Done when:** a born-digital PDF on Convert → clean bundle (images resolve); a scanned PDF on Convert-Scan → OCR'd markdown in the right language; a docx → Pandoc markdown with media; a mixed PDF on Convert triggers the reroute/flag behavior.
**Decisions:** (a) Clean-lane failure = **bounce whole file** to scan-inbox (cleaner) vs **convert-what-you-can-and-flag** (more forgiving)? (b) which `tesseract-data-*` language packs to install.

---

## PART 4 — Return loop: ship to the vault, close the cycle
*Mirror transport back to the desktop. This is where the loop actually closes — and where the graph either lights up or doesn't.*

**Depends on:** Part 3 (needs finished bundles). **Machines:** Linux + Windows (vault-side).

- [ ] **Build the return transport.** *Windows can't host a Tailscale SSH server*, so this is a new wire, not a reuse. **Recommended:** git/Forgejo sync — the converter commits the bundle into the vault repo; the desktop pulls (Obsidian Git or scheduled). This makes the anchor's "content certainty" = commit history, for free. *Alternatives:* Taildrop (`tailscale file cp` → Windows watcher files it in) or Windows OpenSSH (rsync `--remove-source-files`).
- [ ] **Place by tags.** Map frontmatter tags → vault subfolder (your vault architecture) so the bundle lands in the right place.
- [ ] **Delete-after-send.** rsync `--remove-source-files`, or `rm` on transport exit 0. Safe because the **anchor** keeps the permanent copy; the staging queue is disposable.
- [ ] **Link behavior (the graph gate).** Decide before writing link logic: does the converter **mint/stub `[[concept]]` notes** (dense & dirty — instant graph, junk nodes) or **emit links and let you create targets** (sparse & earned)? The graph only lights if links resolve.

**Done when:** a finished bundle lands at the tag-resolved vault path on the desktop, images resolve in Obsidian, the staging copy is deleted on success, the anchor retains the immutable snapshot, and (if dense) the new note shows connected in the graph.

---

## Open decisions (resolve at or before each Part)

| # | Decision | Gates | Leaning |
|---|---|---|---|
| 1 | Disable Tailscale key expiry on always-on nodes | Part 1 | Yes (unattended reliability) |
| 2 | Convert tile only vs also push-from-library | Part 2 | Tile only |
| 3 | Clean-lane failure: bounce whole file vs convert-and-flag | Part 3 | *your call — usage-driven* |
| 4 | Return transport: git/Forgejo vs Taildrop vs Windows OpenSSH | Part 4 | git/Forgejo |
| 5 | Graph links: dense/dirty vs sparse/earned | Part 4 | *your call — affects every future note* |

## Pacing (24h, conserve)
Parts 1–2 are light (likely one usage window). Part 3 is the heavy one (give it its own window after a reset). Part 4 is medium. Sequence over clock — never start a Part until the previous one's "Done when" passes.
