# 08 — Roadmap

## v0 — Scaffold (this commit)

- [x] Repository structure and documentation set.
- [x] Tauri project skeleton with a working `send_to_portal` command shape.
- [x] Allocator service skeleton (watcher, rules engine, config loader).
- [x] `systemd --user` unit + install script.
- [ ] End-to-end manual test on real hardware (needs your two machines + Tailscale set up).

## v1 — Working fire-and-forget transfer

- [x] Finalize `portals.json` schema and wire it into the widget UI.
- [x] Harden `send_to_portal`: handle multi-file drops, surface transfer errors in the UI.
- [x] Allocator: finish collision handling and the quarantine path for oversized/rejected files.
- [ ] Package the widget (`cargo tauri build`) and document install steps for a second machine.

## v2 — Feedback loop

- [x] Linux half: the allocator writes every outcome (allocated/skipped/rejected) to a bounded,
      atomically-updated `~/file-portal/logs/status.json` the widget can poll over the same SSH
      channel (`tailscale ssh <user>@<host> "cat ~/file-portal/logs/status.json"`) — no new
      listening port.
- [ ] Windows half: widget polls `status.json` and shows delivered → sorted → failed per transfer.
- [ ] Toast/notification on the Windows side when a transfer completes or fails.

## v1.5 — Linux dashboard

- [x] Scaffold `linux-dashboard/`: GTK4 + libadwaita app, scanner, live-update watcher.
- [x] Photo thumbnail grid and flat-list view for non-photo categories.
- [x] Settings popover (window size, refresh interval, category filter, photo date range),
      persisted to `~/.config/file-portal/dashboard.toml`.
- [x] Single-instance toggle behavior and `.desktop` launcher for app-menu integration.
- [ ] End-to-end manual test on real hardware with the allocator actively sorting files.

## v3 — Polish / open-source readiness

- [x] Unit tests for `allocator/rules.py` (glob matching, date tokens, collision policy) plus the
      inbox handler (quarantine, guards, status feed) — `linux-receiver/tests/`.
- [x] CI (GitHub Actions): `cargo fmt --check`, `cargo clippy`, `ruff check` + `ruff format
      --check`, Python tests — `.github/workflows/ci.yml`.
- [ ] Screenshot/demo GIF for the README.
- [ ] Decide on public vs. private GitHub repo and finalize `CONTRIBUTING.md` if public.

## Explicitly out of scope (for now)

- Mobile clients.
- Any transfer path that doesn't go through Tailscale (no public internet fallback) — that would
  reopen exactly the exposure this design avoids.
- Content scanning of transferred files (see [`06-security-model.md`](06-security-model.md)).
