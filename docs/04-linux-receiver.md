# 04 — Linux Receiver (Allocator Service)

Lives in [`linux-receiver/`](../linux-receiver). A small Python service, installed and run as a
**user-level** `systemd` unit (`systemd --user`, *not* a system service) — so it starts on login,
restarts on failure, and never needs root.

## What it does

1. Watches `~/file-portal/inbox/<category>/` directories using filesystem events
   ([`watchdog`](https://pypi.org/project/watchdog/), backed by Linux `inotify`).
2. When a new, fully-written file appears, matches it against rules in
   [`config/rules.toml`](../linux-receiver/config/rules.toml) — see
   [`05-allocation-rules.md`](05-allocation-rules.md) for the rule format.
3. Moves the file to the resolved destination under `~/file-portal/sorted/...`, handling name
   collisions (default: append ` (1)`, ` (2)`, ... before the extension).
4. Appends a structured line to `~/file-portal/logs/allocator.log` for every received/sorted/
   rejected file, and a machine-readable record to `~/file-portal/logs/status.json` (the feed the
   widget polls for the v2 feedback loop — see [`01-architecture.md`](01-architecture.md)).

## Why "fully written" matters

`inotify` fires on file creation, not on completion — the widget's streaming transport
(`tailscale ssh … "cat > file"`) creates the file first and then writes into it, so a CREATE
event arrives before the bytes do. The allocator waits for an explicit completion signal instead
of racing the transfer:

- **CLOSE_WRITE** (`on_closed`): inotify's "the writer closed the file" event. This is the
  completion signal for anything that writes in place — the widget's `cat` stream, plain `scp`,
  or a local `cp` into the inbox.
- **MOVED_TO** (`on_moved`): tools with atomic-rename semantics (e.g. `rsync`) write a hidden
  temp file and rename it into place once complete. Dot-prefixed files are ignored until that
  rename arrives, so an in-flight temp file is never sorted.
- **Fallback for non-inotify platforms** (the receiver is portable Python): if the watchdog
  backend can't deliver close events (macOS FSEvents, Windows, polling), the allocator reacts to
  CREATE but first waits for the file's size to stop changing before sorting it.

Files the allocator has quarantined (`inbox/quarantine/`) are inside the watched tree but are
explicitly ignored, so a rejected file is never re-processed.

## Key files

| File | Purpose |
|------|---------|
| `allocator/main.py` | Entry point — sets up the watchdog observer and event loop. |
| `allocator/rules.py` | Loads and evaluates `rules.toml`; resolves a file to a destination path. |
| `allocator/config.py` | Paths (inbox/sorted/logs roots), defaults, env overrides. |
| `allocator/status.py` | Bounded, atomically-written `logs/status.json` feed for the widget's v2 feedback loop. |
| `tests/` | Pytest suite: rules resolution, collision policies, quarantine, status feed. |
| `config/rules.toml` | The actual routing rules — edit this to change behavior, no code changes needed. |
| `systemd/file-portal-allocator.service` | The `systemd --user` unit definition. |
| `scripts/install.sh` | Creates the venv, installs deps, enables + starts the user service. |

## Running it

See [`linux-receiver/README.md`](../linux-receiver/README.md) for exact commands. In short:

```bash
cd linux-receiver
./scripts/install.sh
systemctl --user status file-portal-allocator
```

## Next

[`05-allocation-rules.md`](05-allocation-rules.md) — how to write/extend `rules.toml`.
