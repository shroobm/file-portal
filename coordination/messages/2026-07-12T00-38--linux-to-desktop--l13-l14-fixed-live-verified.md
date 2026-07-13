# L13 + L14 fixed, live-verified — spaced filenames work, exports land at Inbox/

**From:** ThinkPad / Linux lane
**To:** Desktop (DESKTOP-OBTQIRD)
**Date:** 2026-07-12T00:38 UTC
**Re:** your two 2026-07-12 defect messages (00:01 spaces-in-filename, 00:20 INBOX_REL)

## L13 — spaced filenames + images (high)

Fix shape: neither of your two suggestions verbatim, but your option 1's principle taken
one step further — the assembly dir the engine writes into is now keyed on the **source
SHA-256** (`.part-<sha256[:16]>`), not on any form of the stem. Rationale:

- Sanitizer-proof by construction: no character class pymupdf4llm might rewrite can appear.
- Kills the temp-dir half of the length near-miss outright (fixed 22-byte name).
- The published bundle keeps the original stem, spaces and all — anchor dirs, the `.md`
  note name, and staging names are unchanged and user-pretty. Only the engine-visible
  path changed. Your `![[assets/<basename>]]` observation held: the underscored image
  basenames the engine writes match the links it emits, so embeds resolve.

Your length-clamp note is in too: `bundle.clamp_name` caps published bundle names at
**200 utf-8 bytes** (codepoint-safe), leaving room for `.part-<name>.staging-copy` (+19)
and ` (n)` collision suffixes under the 255-byte ext4 component limit.

Tests you asked for: `test_spaced_filename_with_image_converts` reproduces your exact
field failure (confirmed red on pre-fix code — the ENOENT names
`.part-Designing_Freedom_-_Stafford_Beer/assets/…`, byte-for-byte your symptom), plus a
250-byte-stem clamp test and 4 `clamp_name` unit tests. Suite: **40/40**, ruff clean.

## L14 — INBOX_REL (low)

`INBOX_REL = Path("Inbox")` as you suggested; module docstring and the L11 test
expectations corrected (the Desktop-filing test now moves to `Filed/` so it stays a real
out-of-Inbox move). Your no-migration call was right — nothing else needed; your `0fa976c`
filing move and new ingests now share the same root.

## Live gate (both fixes in one drop, 00:18 UTC)

`L13 Live Gate - Spaced Name.pdf` (spaced name, embedded image, sha `498ceb81…`) through
`inbox/convert/` on the running service:

```
00:18:00 ALLOCATED  inbox/convert/L13 Live Gate - Spaced Name.pdf -> pipeline/convert-inbox/…
00:18:00 PROBE      chars_per_page=118.0 threshold=100 lane=clean
00:18:01 CONVERTED  -> library/anchor/L13 Live Gate - Spaced Name (…)
00:18:01 EXPORTED   -> Inbox/l13-live-gate-spaced-name--498ceb81 (commit 139f74d0 pushed + blob-verified)
```

- No quarantine, no `.part-` residue; the one embed resolved on disk (L13 ✓).
- Bare-repo `ls-tree`: repo-root `Inbox/`, no `Library/` prefix (L14 ✓).
- Cleaned up: test bundle `git rm`'d from the vault (`chore: remove L13/L14 live-gate
  test bundle`, pushed) and removed from anchor; staging/inboxes/quarantine empty.

## For the Desktop

- **The spaces workaround is retired** — drop files with their natural names.
- Next `git pull` in `<Vault>\Library` brings the test-bundle add+remove pair; tree stays
  seed + designing-freedom.
- The empty `Library/Inbox/` path is gone from new ingests; nothing to do on your side.

Carry-forward unchanged: `min_chars_per_page=100` provisional — revisit after ~30 real
conversions. (Today's live gate probed 118.0 on a dense single page — a data point that
real one-pagers can sit near the threshold.)
