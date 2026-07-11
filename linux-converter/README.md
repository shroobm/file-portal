# linux-converter

The user-level converter service. It watches `~/file-portal/pipeline/convert-inbox` and
`~/file-portal/pipeline/convert-scan-inbox` -- the "process mouths" the allocator routes the
`convert`/`convert-scan` categories into -- and turns dropped documents into Obsidian-ready
markdown bundles (`<name>.md` + `assets/` + `manifest.json`), published atomically to
`library/anchor/` (immutable snapshot) and `library/staging/` (transient export queue).

**Status: Parts 3 + 4 complete.** Engines: PyMuPDF4LLM (`.pdf`/`.epub`; layout mode, text-layer
probe, Clean/Scan lanes per Open Decision #3) and Pandoc (`.docx`). Every output is
frontmatter-stamped with engine/lane/OCR provenance. The same process also runs the **exporter**
(`converter/exporter.py`, Part 4 -- L11/L12): staging bundles are committed into the vault
working clone at `Library/Inbox/<slug>--<sha256[:8]>/` and pushed to the local bare repo
`~/file-portal/vault.git`; the staging copy is deleted only after `git cat-file -e` confirms the
pushed blobs in the bare repo. Re-ingesting an identical `source_sha256` is a logged no-op. The
exporter never initializes the vault repos -- see CLAUDE_README Open Decisions #4/#5/#6 for the
binding transport/link/placement specs, and
[`../docs/10-library-pipeline-plan.md`](../docs/10-library-pipeline-plan.md) for the plan.

Event model: the allocator hop arrives as an unpaired `IN_MOVED_TO` (= watchdog `created`), so
the handlers react to `created` with a size-stability wait, plus `moved` and `closed`;
dot-prefixed `.part-*` temp files/dirs are always skipped.

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
