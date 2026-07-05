# 01 — Architecture

## Component diagram

```
                          Windows 10 Desktop
   ┌──────────────────────────────────────────────────────────┐
   │  windows-widget (Tauri)                                  │
   │  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
   │  │  Portal:   │ │  Portal:   │ │  Portal:   │   ...       │
   │  │  Documents │ │  Photos    │ │  Code      │             │
   │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘             │
   │        │ drag&drop    │              │                    │
   │        ▼              ▼              ▼                    │
   │  Rust command: transfer::send(category, file_paths)       │
   │        │                                                  │
   │        ▼                                                  │
   │  spawns: tailscale ssh <user>@<host> "mkdir -p inbox/<cat> && cat > inbox/<cat>/<file>"  │
   │          (file bytes streamed through the process's stdin)           │
   └────────┼───────────────────────────────────────────────────┘
            │  Tailscale tunnel (WireGuard, tailnet-only)
            ▼
                              Linux Box
   ┌──────────────────────────────────────────────────────────┐
   │  ~/file-portal/inbox/<category>/<file>                   │
   │        │                                                  │
   │        ▼ (inotify watch)                                  │
   │  linux-receiver allocator (systemd --user)                │
   │        │ reads config/rules.toml                          │
   │        ▼                                                  │
   │  ~/file-portal/sorted/<destination>/<file>                │
   │        │                                                  │
   │        ▼                                                  │
   │  ~/file-portal/logs/allocator.log (event log)             │
   └──────────────────────────────────────────────────────────┘
```

## Data flow, step by step

1. User drags one or more files onto a portal widget in the Windows app.
2. The frontend (HTML/JS) calls a Tauri command (`send_to_portal`) with the category name and the
   absolute file paths (Tauri's drag-and-drop API gives native paths, not blobs).
3. The Rust backend streams each file's bytes through
   `tailscale ssh <user>@<host> "mkdir -p <inbox>/<category> && cat > <inbox>/<category>/<file>"`,
   piping the local file into the remote `cat` via stdin. `tailscale ssh` supplies the
   authenticated tunnel; no `rsync`/`scp` is involved (`rsync` isn't on stock Windows, and
   `scp`/plain `ssh` can't verify Tailscale SSH's managed host keys — see the comment block in
   `windows-widget/src-tauri/src/transfer.rs`).
4. Files land in `~/file-portal/inbox/<category>/` on the Linux box — a plain directory the
   receiving user already owns, so no elevated permissions are ever needed.
5. The allocator service, watching `inbox/` via `inotify` (Linux kernel filesystem events, exposed
   to Python via the `watchdog` library), picks up the new file.
6. It matches the file against `rules.toml` (by category, then by extension/glob) and moves it to
   the resolved destination under `~/file-portal/sorted/...`.
7. Every action (received, matched rule, moved, or rejected) is appended to `allocator.log`.
8. Every outcome is also appended to a machine-readable status feed,
   `~/file-portal/logs/status.json` (newest-last, bounded to the most recent 200 events, written
   atomically so a reader never sees partial JSON). The widget can poll it over the same SSH
   channel — `tailscale ssh <user>@<host> "cat ~/file-portal/logs/status.json"` — to show a
   "delivered ✓ / sorted ✓" indicator. The Linux side of this feedback loop is implemented; the
   widget-side polling/notification is tracked in [`08-roadmap.md`](08-roadmap.md) (v2).

## Why SSH streaming instead of a custom HTTP server

A custom server would need to listen on a port, parse multipart uploads, and handle its own auth —
all attack surface we'd be building and maintaining ourselves. Streaming over Tailscale SSH
gets us, for free:

- transport encryption and authentication (Tailscale's WireGuard + tailnet identity),
- zero extra dependencies — the remote side only needs coreutils (`mkdir`, `cat`),
- zero custom listening port — the only thing listening is `tailscaled`, which is maintained by
  people who do this for a living.

The tradeoff versus an rsync-style transport: no resumable, checksum-verified transfers for very
large files. Revisiting that is tracked in [`08-roadmap.md`](08-roadmap.md).

The tradeoff: less control over progress reporting and no built-in "allocate on arrival" hook from
the transport itself — which is exactly why the allocator is a separate watcher process rather than
something bolted onto the transfer step. See [`docs/00-overview.md`](00-overview.md) for that
rationale.

## Why a separate allocator instead of routing during transfer

Keeping "move the bytes" and "decide where they belong" as two separate steps means:

- the widget doesn't need to know the Linux box's full folder taxonomy, only category names,
- the allocation rules can change on the Linux side without touching the Windows app,
- you can drop files into `inbox/` from anywhere (not just the widget — e.g. `rsync` from a phone)
  and still get them sorted.
