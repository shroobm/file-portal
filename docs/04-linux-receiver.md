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

`inotify` fires on file creation, not on completion — a large `rsync` transfer triggers a CREATE
event before the bytes finish arriving. The allocator waits for an explicit completion signal
instead of racing the transfer:

- `rsync` is invoked with `--temp-dir`-style atomic semantics out of the box: it writes to a
  hidden temp file and renames it into place only once the transfer is verified, so the watcher
  only ever sees a MOVED_TO event for a complete file (this is the main reason the project prefers
  `rsync` over plain `scp`).

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
