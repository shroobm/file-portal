# 05 — Allocation Rules

> **Scope: the first era — file routing.** This document describes the original system (drag a file
> onto a tile, the allocator sorts it on the Linux box), which is built and in daily use. It does
> **not** cover the document library pipeline the project grew later — conversion, the survival
> audit, the vault, the control room, the repair bench. For the system as a whole see
> [`20-file-portal-manual.md`](20-file-portal-manual.md); the pipeline's own design docs are `10`–`19`.
> Statements here are accurate within this scope unless noted inline.

Rules live in [`linux-receiver/config/rules.toml`](../linux-receiver/config/rules.toml) and are
re-read on every file event (no service restart needed to pick up changes).

## Format

```toml
[defaults]
unmatched_destination = "sorted/misc"
on_collision = "rename"          # "rename" | "overwrite" | "skip"
max_file_size_mb = 2048

[[rule]]
category = "documents"           # matches the portal/category subfolder under inbox/
match = ["*.pdf", "*.docx", "*.txt", "*.md"]
destination = "sorted/documents"

[[rule]]
category = "photos"
match = ["*.jpg", "*.jpeg", "*.png", "*.heic"]
destination = "sorted/photos/{yyyy}/{mm}"   # destination paths support date tokens

[[rule]]
category = "code"
match = ["*.zip", "*.tar.gz"]
destination = "sorted/code/archives"

[[rule]]
category = "code"
match = ["*"]                     # catch-all for the "code" category
destination = "sorted/code/inbox"
```

## Matching order

Rules are evaluated top-to-bottom **within the matching category**; the first `match` glob that
hits wins. A category with no matching rule falls back to `defaults.unmatched_destination`.

## Date tokens

`{yyyy}`, `{mm}`, `{dd}` in a `destination` path are substituted with the file's arrival date.
Useful for photo/log dumping grounds that would otherwise become unsorted piles.

## Collision policy

- `rename` (default): `report.pdf` → `report (1).pdf` if the destination already exists.
- `overwrite`: replace the existing file. Use sparingly.
- `skip`: leave the incoming file in `inbox/` untouched and log a `SKIPPED` event — useful while
  you're still tuning rules and don't want accidental data loss.

## Validation

`max_file_size_mb` rejects (logs `REJECTED`, moves the file to `~/file-portal/quarantine/`) anything
over the limit — a cheap guard against a bad drag-and-drop of an entire folder. Quarantine lives
*outside* the watched `inbox/` tree on purpose: quarantining into a watched path would fire another
filesystem event and re-process the file forever.

## Adding a new portal/category

1. Add a `[[rule]]` block (or several) for the new `category` name.
2. Add a matching tile in the Windows widget's `portals.json` (see
   [`03-windows-widget.md`](03-windows-widget.md)) with the same category string.
3. No service restart needed on the Linux side; restart the widget (or just relaunch it) to pick
   up the new tile.
