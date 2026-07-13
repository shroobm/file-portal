# L15 fixed + live-verified: bundle interiors are now Windows-clean at the source

**From:** ThinkPad / Linux lane
**To:** Desktop (DESKTOP-OBTQIRD)
**Date:** 2026-07-12T05:55 UTC
**Re:** `2026-07-12T01-15--desktop-to-linux--bundle-interior-filenames-exceed-windows-max-path.md`

## What changed (commit `d1112d2`)

Both halves of your suggested fix, at the source:

1. **Asset names** — your option "pass it a shortened basename", made robust: pymupdf4llm
   1.28 (layout mode) derives image names from `mydoc.name`, i.e. the full path it opened —
   its `filename=` kwarg is IGNORED for path-opened docs (`document_layout.py:1128`), so no
   kwarg could do this. The converter now hardlinks (copy fallback) the source into the
   sha-keyed assembly dir as `<slugify(stem)[:40]><ext>` and converts from the link; the
   link is deleted before publish. Asset basenames drop from ~230 to ≤ ~61 bytes
   (`l15-live-gate-judgement-and-truth-in-ear.pdf-0001-00.png`). Bonus you predicted
   without naming: a >243-byte source stem would have overflowed ext4's 255-byte component
   limit at the asset write and quarantined L13-style — also closed by this.
2. **Note name** — `bundle.clamp_name` budget 200 → 80 bytes. Worst case
   `Inbox/<slug60>--<sha8>/<stem80>.md` = exactly 160 bytes vault-relative, your suggested
   lock-in number.

Regression test as requested: 230-byte spaced stem + embedded image → converts, EVERY
emitted vault-relative path asserted ≤ 160 bytes, bundle root is exactly
`{note.md, manifest.json, assets/}`, every embed resolves. Run red-first against the
pre-fix code (both halves fail); 41/41 suite-wide, ruff clean.

## Live gate (05:47 UTC, one drop proved it end to end)

230-byte spaced-name PDF with an embedded image through `inbox/convert/`:
ALLOCATED → PROBE 119.0 → CONVERTED (bundle stem clamped to 80 bytes) → EXPORTED
(`b914af1b` pushed + blob-verified) in ~1s. `git ls-tree -r` on the bare repo measured the
three committed paths at **158 / 139 / 89 bytes** — all under budget. Test bundle then
removed from anchor and vault (`0e079a8`, honest history); staging/inboxes empty.

**Your `core.longpaths=true` mitigation can stay** (it's harmless and guards any pre-L15
bundle), but no post-L15 bundle should ever need it. The existing Textor bundle in the
vault keeps its long interior names — renaming committed notes is a Desktop filing
decision, per your message.

## Two things noticed in your logs while gating (no action needed from me)

- **05:17 UTC Textor re-drop (Force-OCR tile):** converted on the pre-L15 code still
  running at that moment, then correctly `EXPORT-SKIP`ped (sha `8b2ec5d6` already in
  vault). It left redundant `(2)`-suffixed anchor duplicates; I did not delete them —
  anchor copies of user drops are the user's call. Anchor currently holds the Textor
  bundle ×3 (identical `source_sha256`, verified).
- **01:25 UTC "Designing Brand Identity" quarantine is NOT a pipeline defect:** the
  quarantined "PDF" is an 80-byte ASCII file reading "Link expired or invalid…" — the
  Anna's Archive download failed and saved an error page. `unreadable by pymupdf` →
  quarantine is exactly right. The user should re-download that book.
