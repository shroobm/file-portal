# linux-receiver

The user-level allocator service that sorts files dropped into `inbox/`. See
[`../docs/04-linux-receiver.md`](../docs/04-linux-receiver.md) for the design rationale and
[`../docs/05-allocation-rules.md`](../docs/05-allocation-rules.md) for the `rules.toml` format.

## Run in the foreground (for development/debugging)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m allocator.main
```

Default root is `~/file-portal` (override with `--root`). This creates `inbox/`, `sorted/`,
`logs/`, and `inbox/quarantine/` on first run.

## Install as a systemd --user service

```bash
./scripts/install.sh
systemctl --user status file-portal-allocator
journalctl --user -u file-portal-allocator -f
```

Never run `install.sh` with `sudo` — the script refuses to run as root on purpose. See
[`../docs/06-security-model.md`](../docs/06-security-model.md) for why.

## Editing rules

Edit `config/rules.toml` and save — no restart needed, it's re-read on every incoming file.

## Uninstalling

```bash
systemctl --user disable --now file-portal-allocator
rm ~/.config/systemd/user/file-portal-allocator.service
systemctl --user daemon-reload
```
