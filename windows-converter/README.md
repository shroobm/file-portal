# windows-converter — Desktop GPU conversion lane (Phase 4)

Converts documents to markdown bundles on the Desktop's RTX 3080 with
[Marker](https://github.com/datalab-to/marker) and ships them to the ThinkPad's
`library/staging/`, where the **unchanged** `linux-converter` exporter commits them to the
vault. Design + the bundle contract this code honors: `docs/12-phase4-rewiring.md`;
engine benchmarks and policy: `docs/11-gpu-pipeline-revamp.md`.

## Slice 1 (current): `convert_and_ship.py`

```
C:\Users\Bndit\ml\marker-env\Scripts\python.exe convert_and_ship.py <pdf> [--dry-run]
```

Pipeline per run: probe (pymupdf; chars/page + OCR-layer detection via text render mode 3)
→ route per the docs/11 policy table → `marker_single` → assemble a format-identical
bundle (80-byte name clamp, `conversion:` frontmatter, `![[assets/…]]` embeds,
`manifest.json` with full `source_sha256`) → local anchor copy
(`C:\Users\Bndit\ml\library\anchor`) → tar-over-`tailscale ssh` into a dot-prefixed
staging dir, atomic `mv` to publish.

Requirements: `marker-env` (torch cu128 + marker-pdf + pymupdf — see docs/11 Phase 0),
`tailscale` on PATH, ThinkPad online with the converter service active.

E2E verified 2026-07-19 (Session 15): EXPORTED with blob verification, same-file
re-ship → `EXPORT-SKIP`, and cross-machine dedup (a source the *ThinkPad* converted
skips when *Desktop*-converted) — see the Session Log.

## Windows gotchas baked into the code

- **bsdtar mangles non-ASCII argv** (CJK bundle names arrive empty): tar only ever sees
  ASCII paths — the bundle stays in its `.part-<sha16>` dir locally and the remote `mv`
  applies the visible name (`tailscale ssh` carries Unicode argv correctly).
- Marker derives output/asset names from the input stem: conversion runs from a
  short slugified copy (the ThinkPad's L15 idiom) so long/spaced/CJK stems can't
  blow path budgets.

## Not yet here (by design)

Watched-folder/widget trigger, the link-fenced analyst stage (slice 2), per-segment
toggles + status feed for the widget control room. One step at a time, each switchable.
