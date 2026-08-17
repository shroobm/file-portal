# 08 — Roadmap

> **Scope: the first era — file routing.** This document describes the original system (drag a file
> onto a tile, the allocator sorts it on the Linux box), which is built and in daily use. It does
> **not** cover the document library pipeline the project grew later — conversion, the survival
> audit, the vault, the control room, the repair bench. For the system as a whole see
> [`20-file-portal-manual.md`](20-file-portal-manual.md); the pipeline's own design docs are `10`–`19`.
> Statements here are accurate within this scope unless noted inline.

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

## Transport — revisiting the raw `cat` stream

*`transfer.rs:11-12` and `docs/01-architecture.md`'s tradeoff paragraph have pointed at this
entry since the transport was built; it was a dangling pointer until 2026-08-17 (S93). The
accepted tradeoff, recorded in docs/01: the `tailscale ssh … cat > dest` stream is not
resumable, not checksummed, and reports no progress — an interrupted large transfer re-sends
from scratch.*

- [ ] **Library-pipeline lane — scheduled**: `docs/37` Stage 3 (the verified seam) closes the
      integrity half — a per-file SHA-256 `inventory.json` at bundle build on both lanes, the
      exporter verifying it BEFORE commit, and the receipt binding the package digest. An
      arrival is then proven intact instead of assumed.
- [ ] **File-routing lane (this document's scope) — unscheduled**: resumable/chunked transfer
      for very large single files stays a non-goal until a real interrupted-transfer incident
      is observed; that incident is the re-entry trigger.

## Explicitly out of scope (for now)

- Mobile clients.
- Any transfer path that doesn't go through Tailscale (no public internet fallback) — that would
  reopen exactly the exposure this design avoids.
- Content scanning of transferred files (see [`06-security-model.md`](06-security-model.md)).
