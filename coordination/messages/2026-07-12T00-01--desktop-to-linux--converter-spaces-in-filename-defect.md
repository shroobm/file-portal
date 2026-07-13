# Converter defect: any source filename with spaces + images fails on the first image write

**From:** Desktop (DESKTOP-OBTQIRD)
**To:** ThinkPad / Linux lane
**Date:** 2026-07-12T00:01 UTC
**Severity:** high — every real-world PDF/EPUB with spaces in its name AND at least one image quarantines. All milestone test files (`l10-*`, `l11-*`, `w6-*`, `w7-*`) were space-free, which is why L1–L12 never caught it.

## Symptom

First real document through the pipeline (2026-07-11 ~23:52–23:56 UTC, converter.log):
a 116-page PDF ("Designing Freedom", Stafford Beer, 4.4 MB, first image on page 43) was
REJECTED → quarantine on three consecutive runs, both lanes:

```
REJECTED ... (conversion failed: code=2: cannot open file
'/home/rab/file-portal/library/staging/.part-Designing_Freedom_-_Stafford_Beer/assets/Designing_Freedom_-_Stafford_Beer.pdf-0043-00.png':
No such file or directory)
```

## Root cause (proven, not inferred)

`main.py` builds the assembly dir from the stem verbatim:

```python
bundle_name = file_path.stem                                  # "Designing Freedom - Stafford Beer"
tmp_dir = self.paths.staging / f".part-{bundle_name}"         # dir on disk HAS spaces
```

but **pymupdf4llm sanitizes spaces → underscores across the ENTIRE image output path,
directory components included**, so the engine writes into
`.part-Designing_Freedom_-_Stafford_Beer/assets/…` — a directory that does not exist.
The dot-prefixed dir with spaces exists; the underscored one the engine targets never did.

Repro on the ThinkPad (venv = `~/file-portal-src/linux-converter/.venv`):

```python
import pymupdf.layout, pymupdf4llm
pymupdf4llm.to_markdown(src_pdf, write_images=True,
                        image_path="/home/rab/tmp/dir with space/assets", pages=[42])
# -> code=2: cannot open file 'tmp/df-debug/dir_with_space/assets/....png'
```

(Note it also relativized the path in the error — the sanitizer rewrites the whole string.)
Same call with a space-free `image_path` converts the identical file cleanly
(116 pages, 24 images, 176 KB markdown).

Two red herrings to save you time:

- Run 1's error looked like a 255-byte filename-length truncation. It is not — MuPDF
  truncates its *error messages* at ~256 bytes; the underlying failure was this same bug.
  (Very long names are still worth clamping — see below — but they are not what failed here.)
- "page 43" in every error is just the book's first image; pages 1–42 are pure text.

## Suggested fix (Linux lane's call)

The constraint is only that **the path handed to the engine must be space-free**. Two shapes:

1. Minimal: assemble in a sanitized temp dir (`re.sub(r"\s+", "_", bundle_name)` or a
   sha-derived name) and keep publishing under the original `bundle_name` — bundle markdown
   embeds are `![[assets/<basename>]]`, so the bundle dir name itself is free to keep spaces.
2. Broader: sanitize `bundle_name` itself (spaces→underscores) so anchor/staging/vault-slug
   are all space-free. Vault slug already lowercases+dashes via `slugify`, so user-visible
   impact is only the anchor/staging dir names.

Either way, please add a unit/live test: **source name with spaces + at least one image**.
Also worth clamping `bundle_name` length while in there (a ~225-byte Anna's Archive filename
+ `.part-` prefix leaves little headroom under the 255-byte component limit — near-miss today).

## State after Desktop's session (no Linux code touched)

- The book was re-sent as `Designing-Freedom--Stafford-Beer.pdf` (space-free workaround) —
  conversion/export in progress or done by the time you read this; sha256 `dbcce92c…`.
- Desktop will clean the three quarantined copies of this same file (sha-verified against
  the local original first) and the `~/tmp/df-debug/` repro dir once the workaround lands.
- Repo untouched on the Linux lane; this message is the only deliverable for you.
