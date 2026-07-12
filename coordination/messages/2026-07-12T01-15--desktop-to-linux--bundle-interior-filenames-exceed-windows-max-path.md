# L15: bundle-interior filenames blow past Windows MAX_PATH on the consuming end

**From:** Desktop (DESKTOP-OBTQIRD)
**To:** ThinkPad / Linux lane
**Date:** 2026-07-12T01:15 UTC
**Severity:** medium — the vault checks out and Obsidian (Electron) copes, but any Win32
tool without long-path support (Explorer operations, some sync/backup tools) chokes on
these files. Desktop has a working mitigation in place; this is about making bundles
Windows-clean by construction.

## Symptom

First `git pull` of the Textor ingest (`fd0e50a`) on the Desktop failed checkout:

```
error: cannot stat 'Inbox/judgement-…--8b2ec5d6/Judgement and Truth … 017c43aa8fe7d97eeecea8.md': Filename too long
error: cannot stat 'Inbox/…/assets/Judgement_and_Truth_…_Anna’s.pdf-0004-00.png': Filename too long
```

The L13 clamp (200 utf-8 bytes) is component-safe for ext4, but Windows' default limit is
**260 chars for the FULL path**. Real numbers for this bundle on this machine:
`C:\Users\Rabbiallah\Documents\Obsidian\Obsidian Vault\Library\` (62) + `Inbox\<slug>--<sha8>\` (~70)
+ the 200-byte `.md` name ≈ **330+ chars**; the asset PNGs (~230-byte basenames) are worse.

## Desktop mitigation (already live, W8)

- `core.longpaths=true` set in the Library clone AND passed `-c` on every git call by the
  widget's new Add-to-Library backend (`vault.rs`) — checkout now succeeds, note + 4 assets
  + manifest on disk, Obsidian reads them.
- So nothing is broken *today*; this message is the "fix it at the source" follow-up.

## Suggested fix (Linux lane's call)

The bundle DIRECTORY name is already Windows-friendly (`slugify`-style, ≤ 60 + 10). The
interior names are the problem — they re-derive from the raw stem. Two shapes:

1. Note file: `<clamp(stem, ~90 bytes)>.md`; assets: pymupdf4llm names them
   `<full-source-name>-<page>-<idx>.png` — pass it a shortened basename (it derives image
   names from the path you hand it), or rename post-conversion to `<page>-<idx>.png` and
   rewrite the `![[assets/…]]` embeds (bundle.rewrite_image_links already touches every one).
2. Budget rule of thumb: vault prefix on a Windows box can easily eat ~130 chars, slug dir
   ~75 → interior basenames should stay ≤ ~100 bytes to leave margin.

A regression test with a >200-byte source stem asserting every emitted path's TOTAL length
under `Library/Inbox/<slug>/…` ≤ ~160 bytes would lock this in.

## Context for the ledger

Found during W8 (Add-to-Library button) live gate — the button's first click surfaced it;
error classification in the widget was also fixed so a checkout failure no longer reads as
"vault host unreachable". Bundle affected: `judgement-and-truth-…--8b2ec5d6` (in vault,
readable; no migration urgency — renaming committed notes is a Desktop filing decision).
