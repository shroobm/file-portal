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
   rejected file.

## Why "fully written" matters

`inotify` fires on file creation, not on completion — a CREATE event arrives before the bytes
finish streaming. The allocator avoids racing the transfer by relying on an atomic rename rather
than the raw CREATE:

- The Windows widget streams each file into a temporary `inbox/<category>/.part-<name>` dotfile and
  then `mv`s it onto its final name once all the bytes are there. That rename is atomic on the same
  filesystem, so the watcher sees a single MOVED_TO event (the handler's `on_moved` path) for a
  complete file.
- The handler also skips dotfiles, so the in-progress `.part-` file is never allocated mid-write.
  Both halves live in [`transfer.rs`](../windows-widget/src-tauri/src/transfer.rs) (write side) and
  [`allocator/main.py`](../linux-receiver/allocator/main.py) (watch side).

## Key files

| File | Purpose |
|------|---------|
| `allocator/main.py` | Entry point — sets up the watchdog observer and event loop. |
| `allocator/rules.py` | Loads and evaluates `rules.toml`; resolves a file to a destination path. |
| `allocator/config.py` | Paths (inbox/sorted/logs roots), defaults, env overrides. |
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
