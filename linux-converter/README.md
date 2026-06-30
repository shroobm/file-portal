# linux-converter

The user-level converter service. It watches `~/file-portal/pipeline/convert-inbox` -- the "process
mouth" the allocator routes the `convert` category into -- and turns dropped documents into
Obsidian-ready markdown bundles.

**Status: Part 2 skeleton (log-only).** Right now it just logs `would convert <path>` for every
arrival and runs no conversion engine. The engine (PyMuPDF4LLM / Pandoc, Clean/Scan lanes, bundle
output) lands in Part 3 -- see [`../docs/10-library-pipeline-plan.md`](../docs/10-library-pipeline-plan.md).

It reuses the allocator's event model: prefer the atomic-rename (`on_moved`) signal, fall back to
`on_created`, and skip `.part-*` temp files.

## Run in the foreground (for development/debugging)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m converter.main
```

Default root is `~/file-portal` (override with `--root`). Creates `pipeline/convert-inbox/` and
`logs/` on first run; logs to `logs/converter.log`.

## Install as a systemd --user service

```bash
./scripts/install.sh
systemctl --user status file-portal-converter
journalctl --user -u file-portal-converter -f
```

Never run `install.sh` with `sudo` -- it refuses to run as root on purpose, same as the allocator.
Linger (so the service runs without an active login) is enabled by the Part 1 bootstrap.

## Uninstalling

```bash
systemctl --user disable --now file-portal-converter
rm ~/.config/systemd/user/file-portal-converter.service
systemctl --user daemon-reload
```
