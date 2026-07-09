# Documentation Audit Changelog

> **Snapshot as of 2026-06-25.** Entries below describe the tree at that commit. Superseded by
> W1 (transport: streamed `tailscale ssh … cat` with `.part-` + `mv -f`, not rsync) and L1
> (quarantine location: `~/file-portal/quarantine/`, not `inbox/quarantine`). Treat as history
> only — do not act on its guidance.

Audited all 16 documentation files against the full source tree. Five files required corrections; eleven were accurate as-is.

---

## Files changed (5)

### `docs/00-overview.md` — Overclaimed validation capabilities

**Before:** "basic validation (reject empty files, oversized files, disallowed extensions)"
**After:** "basic validation (reject oversized files beyond `max_file_size_mb`)"

**Why:** `allocator/main.py` only checks `rules.defaults.max_file_size_mb`. There is no empty-file check and no extension-blocking logic anywhere in the codebase. The allocator routes by extension via glob matching, but that's categorization — it never *rejects* based on extension. Claiming it does would mislead a reviewer into thinking a security boundary exists that doesn't.

---

### `docs/01-architecture.md` — Wrong transfer invocation pattern (diagram + prose)

**Diagram before:** `spawns: tailscale ssh <linux-host> -- \ rsync --from-stdin / scp <file> :inbox/<cat>/`
**Diagram after:** `spawns: rsync -e "tailscale ssh" <file> <user>@<host>:inbox/<cat>/`

**Step 3 before:** Described shelling out via `tailscale ssh <host> -- <command>`
**Step 3 after:** Describes `rsync -av --progress -e "tailscale ssh"` with `scp -o "ProxyCommand=tailscale ssh -W %h:%p"` as fallback.

**Why:** `transfer.rs` lines 58–77 show the actual invocations. The difference matters: `tailscale ssh <host> -- rsync` would run rsync on the *remote* side, while `rsync -e "tailscale ssh"` runs rsync *locally* using tailscale as the SSH transport. These are structurally different — the former is remote command execution, the latter is rsync's own remote-shell mode. The code's own comment (lines 3–6 of `transfer.rs`) explicitly calls this out. The scp fallback uses `ProxyCommand`, not a `tailscale ssh <host> -- scp` pattern.

---

### `docs/03-windows-widget.md` — Three separate issues

**1. Wrong config source for portal categories**
**Before:** "defined in `windows-widget/src-tauri/tauri.conf.json` adjacent config (see `portals.json` once added)"
**After:** "defined in `config.rs`'s `AppConfig::default()` and loaded at runtime from `%APPDATA%\file-portal\config.toml`"

**Why:** `tauri.conf.json` contains window geometry and app metadata — zero portal definitions. `portals.json` is a reference copy that already exists (not "once added"). The runtime source of truth is `config.rs` → `config.toml`.

**2. Incomplete key files table**
Added `config.rs`, `transfer.rs`, and `portals.json`. Fixed `main.rs` description: it delegates transfer logic to `transfer.rs`, it doesn't build the child process itself.

**3. Wrong file attribution for `load_or_init`**
**Before:** "the `config::load_or_init` function in `main.rs`"
**After:** "the `load_or_init` function in `config.rs`"

**Why:** `main.rs:35` calls `config::load_or_init()`, but the function is defined at `config.rs:50`. The doc pointed readers to the wrong file.

---

### `docs/07-development-guide.md` — Stale "once added" qualifier

**Before:** "config in `linux-receiver/pyproject.toml` once added"
**After:** "config in `linux-receiver/pyproject.toml`"

**Why:** `linux-receiver/pyproject.toml` exists and already contains `[tool.ruff]` with `line-length = 100` and `target-version = "py311"`. The "once added" was accurate at initial scaffold time but is now stale.

---

### `docs/08-roadmap.md` — Three v1 items implemented but unchecked

Checked off:
- `portals.json` schema finalized and wired into UI (`config.rs` defaults, `main.js` calls `invoke("list_portals")`, renders tiles)
- Multi-file drops handled (`transfer.rs` iterates `Vec<String>`; `main.js` reports sent/failed counts)
- Collision handling + quarantine path complete (`main.py:_resolve_collision` implements rename/overwrite/skip; `_quarantine` moves oversized files to `inbox/quarantine/`)

Left unchecked: `cargo tauri build` packaging and second-machine install docs (no evidence these were completed).

---

## Files verified accurate (11)

| File | Notes |
|------|-------|
| `README.md` | Layout table, quickstart links, status section all match repo structure. |
| `docs/02-tailscale-setup.md` | Setup steps accurate. `apt` example has "or dnf/pacman/etc." qualifier. |
| `docs/04-linux-receiver.md` | Key files table correct. rsync atomic-rename explanation matches `on_moved` handler. |
| `docs/05-allocation-rules.md` | Format matches `rules.toml`. Collision/validation behavior matches code. |
| `docs/06-security-model.md` | Threat model accurate against current design surface. |
| `docs/09-linux-dashboard.md` | Thorough and matches all dashboard source files precisely. |
| `windows-widget/README.md` | Dev/build/config instructions accurate. |
| `linux-receiver/README.md` | Install, run, uninstall commands all match install.sh and systemd unit. |
| `linux-dashboard/README.md` | Install, run, toggle, settings, uninstall all accurate. |
| `scripts/setup-tailscale-ssh.md` | Checklist consistent with `02-tailscale-setup.md`. |
| `linux-dashboard/pyproject.toml` / `linux-receiver/pyproject.toml` | Deps match requirements.txt; metadata accurate. |

---

## Non-doc issue flagged (not fixed — code, not docs)

**`linux-receiver/systemd/file-portal-allocator.service`** hardcodes `WorkingDirectory=%h/file-portal-src/linux-receiver`. The `install.sh` copies this file without templating the path (unlike `linux-dashboard/scripts/install.sh`, which uses `sed` to inject `$(pwd)`). If someone clones the repo to a path other than `~/file-portal-src/`, the service will fail. The bootstrap script defaults to `~/file-portal-src` so the happy path works, but this is a latent bug. Recommend adding `sed` templating to `install.sh` to match the dashboard's approach.
