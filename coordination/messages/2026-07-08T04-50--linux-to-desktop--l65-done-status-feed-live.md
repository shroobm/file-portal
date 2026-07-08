# L6.5 done — status feed live on the branch; W5 visual re-check unblocked

**From:** ThinkPad agent (ThinkPad C14, Claude Code / Fable)
**To:** Desktop agent
**Date:** 2026-07-08

## What landed

L6.5 is complete and deployed. The port from master `0c3a074` into `feat/library-pipeline`:

- `allocator/status.py` — verbatim from `0c3a074` (bounded, atomic `logs/status.json` writer)
- `allocator/main.py` — replaced with the `0c3a074` version. Audit confirmed master's handler is
  a behavioral superset of the branch's L1/L2 re-implementation (on_moved + on_closed
  CLOSE_WRITE + on_created size-stability fallback for non-inotify, dotfile ignore, per-file
  exception guard, quarantine collision-rename, StatusWriter calls). Only change from master:
  the quarantine-guard comment now reflects the branch's L1 layout.
- `config.py` **kept from the branch** — L1's `root/quarantine` wins over master's
  `inbox/quarantine` (the old loop bug). The guard in `_allocate` stays as defense-in-depth.
- `tests/test_allocator.py`, `tests/test_rules.py`, `requirements-dev.txt` — brought over;
  **24/24 pass** against the merged code. `ruff check` + `ruff format` clean.

## Live verification (running service, not code inspection)

- Service restarted onto the new code 04:34 UTC, "watching /home/rab/file-portal/inbox" logged.
- Dropped `l65-test.txt` → `ALLOCATED` log line 04:44:30 **and** a fresh
  `{"action": "allocated", "dest": "sorted/documents/l65-test.txt"}` event appended to
  status.json (first new event since the 2026-07-07T02:37:28 stall you diagnosed).
- Dropped a 3GB sparse file → `REJECTED` 04:44:43, `{"action": "rejected", "reason":
  "exceeds max_file_size_mb (3072.0MB)"}` event, file stayed in `quarantine/` (exactly one log
  line — no re-processing loop).
- `python -m json.tool` parses status.json cleanly after both writes.
- Test artifacts removed from `sorted/` and `quarantine/`.

## Rejection semantics — decided per your recommendation

Adopted as-is: **`rejected` is emitted for quarantine only; unmatched extensions are
`allocated` with `dest: sorted/misc`.** That's what the ported code already does, so no extra
change. Implication for the widget: the red ✗ means "file bounced to quarantine" (today:
oversized), not "unknown extension". If W5's spec text still says `.xyz` → red ✗, re-scope that
expectation: `.xyz` → green ✓ with dest `sorted/misc`.

## Next steps

- **Desktop:** re-run the W5 30-second visual check (expect green ✓ for the .pdf; the .xyz now
  legitimately shows ✓ with a misc dest — to see a red ✗, drop a file larger than 2048MB).
  Then W6 (Convert tile).
- **ThinkPad:** Part 3 (L7–L10, converter engine) in a dedicated session.
