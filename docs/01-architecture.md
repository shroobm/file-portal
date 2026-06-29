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
   │  spawns: tailscale ssh <user>@<host> -- "mkdir -p inbox/<cat>/ && cat > inbox/<cat>/<file>"  │
   │          (the file's bytes are streamed into the remote cat over stdin; no rsync/scp)  │
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
3. The Rust backend shells out to `tailscale ssh <user>@<host> -- "mkdir -p <inbox>/<category> &&
   cat > <inbox>/<category>/<filename>"` and streams each file's bytes into that remote `cat` over
   the process's stdin — one file per invocation. `tailscale ssh` supplies the authenticated tunnel
   and is the only command that verifies Tailscale SSH's managed host keys (plain `ssh`/`scp` reject
   them, and `rsync` isn't installed on stock Windows), so it is used as the transport directly
   rather than wrapping `rsync`/`scp`. Remote paths are shell-quoted so filenames with spaces or
   quotes are handled safely.
4. Files land in `~/file-portal/inbox/<category>/` on the Linux box — a plain directory the
   receiving user already owns, so no elevated permissions are ever needed.
5. The allocator service, watching `inbox/` via `inotify` (Linux kernel filesystem events, exposed
   to Python via the `watchdog` library), picks up the new file.
6. It matches the file against `rules.toml` (by category, then by extension/glob) and moves it to
   the resolved destination under `~/file-portal/sorted/...`.
7. Every action (received, matched rule, moved, or rejected) is appended to `allocator.log`.
8. The widget polls (or, later, subscribes over the same SSH channel to) a small status file so the
   user gets a "delivered ✓ / sorted ✓" indicator — see [`08-roadmap.md`](08-roadmap.md) for the
   current state of this feedback loop (v1 is fire-and-forget; status feedback is a planned
   iteration).

## Why Tailscale SSH instead of a custom HTTP server

A custom server would need to listen on a port, parse multipart uploads, and handle its own auth —
all attack surface we'd be building and maintaining ourselves. Streaming over Tailscale SSH
gets us, for free:

- transport encryption and authentication (Tailscale's WireGuard + tailnet identity),
- zero custom listening port — the only thing listening is `tailscaled` and `sshd`, both of which
  are maintained by people who do this for a living,
- no extra client dependency on Windows — `tailscale` is already installed for the tunnel, and the
  remote side only needs `cat`.

The tradeoffs: a raw `cat` stream isn't resumable or checksum-verified the way `rsync` would be (an
interrupted transfer of a very large file is re-sent from scratch), and there's no built-in progress
reporting or "allocate on arrival" hook from the transport itself — which is exactly why the
allocator is a separate watcher process rather than something bolted onto the transfer step.
Revisiting the transport is tracked in [`08-roadmap.md`](08-roadmap.md); see
[`docs/00-overview.md`](00-overview.md) for the separate-allocator rationale.

## Why a separate allocator instead of routing during transfer

Keeping "move the bytes" and "decide where they belong" as two separate steps means:

- the widget doesn't need to know the Linux box's full folder taxonomy, only category names,
- the allocation rules can change on the Linux side without touching the Windows app,
- you can drop files into `inbox/` from anywhere (not just the widget — e.g. `rsync` from a phone)
  and still get them sorted.
