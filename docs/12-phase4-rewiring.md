# Phase 4 — Pipeline Rewiring: the Intake Inversion

**Depends on:** docs/11 Phases 0–3 (all closed). **Machines:** Desktop builds; ThinkPad unchanged for slice 1.
**Prime directive:** the proven back half (bundle format, SHA dedup, exporter, vault push, Add-to-Library) must not change — the new front end conforms to it.

---

## What inverts

Today: PDF → widget → ThinkPad allocator → ThinkPad converter (pymupdf4llm) → bundle → staging → exporter → vault.
After: **PDF → Marker on the Desktop GPU (policy-routed) → format-identical bundle → transport to ThinkPad staging → the same exporter → the same vault.** The ThinkPad's converter service keeps running unchanged — it becomes the fallback lane (a file dropped on the old Convert tiles still works) and the enrichment host (Phase 3 sidecars).

## The contract the Desktop bundle must honor (verified against code, 2026-07-19)

From `linux-converter/converter/bundle.py` and `exporter.py` — cited by the behavior that enforces them:

1. **Shape:** a bundle is a directory `<name>/` containing `<name>.md`, `assets/`, and `manifest.json` — never a bare file (`bundle.py:1-7`).
2. **Name budget (L13/L15):** `<name>` = source stem clamped to **80 UTF-8 bytes** without splitting a codepoint (`bundle.clamp_name`). Marker's asset names (`_page_N_Picture_M.jpeg`, ≤ ~25 bytes) are inside every budget by construction. Vault-relative worst case stays ≤ 160 bytes: `Inbox/<slug60>--<sha8>/<name80>.md`.
3. **Markdown:** YAML frontmatter first (`conversion:` block — engine, lane, lane_reason, chars_per_page_detected, ocr, [ocr_dpi], converted_at, source_sha256), then body with every local image link rewritten to `![[assets/<basename>]]`; http/https/data links untouched (`bundle.rewrite_image_links`).
4. **Manifest:** `manifest.json` with `source`, `source_sha256` (full hex — **the dedup key**), `engine`, `lane`, `lane_reason`, `chars_per_page_detected`, `pages`, `converter_version`, engine version key, `converted_at`. The exporter reads only `source_sha256`, `source`, `lane` (`exporter.py:120-121,168`); the rest is honest provenance. Desktop bundles use `engine: marker` + `marker_version` in place of `pymupdf4llm_version`.
5. **Dedup is machine-agnostic by construction:** `git grep -F <full sha> main -- *manifest.json` in the **bare** repo (`exporter.py:129-141`). A source converted anywhere, ever, skips everywhere. This is the property slice 1's gate exercises.
6. **Delivery into staging must be invisible-then-atomic:** the exporter watches `~/file-portal/library/staging/` non-recursively; dot-prefixed dirs are ignored (`exporter.py:108,213`); a rename into a visible name is the publish event (`on_moved`), and even a non-atomic copy is tolerated via the stability wait + manifest-written-last rule (`exporter.py:217-239`). We use the strict form anyway: assemble in `.part-<sha16>`, finish with `mv`.
7. **Exporter placement:** `Inbox/<slugify(name)[:60]>--<sha256[:8]>/` in the vault, commit + push + `cat-file -e` blob verification against the bare repo before the staging copy is deleted (L12 gate) — all existing behavior, untouched.

## Transport (Desktop → ThinkPad staging)

`scp`/`rsync` are non-starters over Tailscale SSH (managed host keys — `transfer.rs:1-12`). The proven idiom is `tailscale ssh rab@archlinux "<cmd>"` with bytes streamed over stdin. A bundle is many files, so slice 1 ships **one tar stream per bundle** (Windows 10's built-in bsdtar):

```
tar -cf - -C <bundle-parent> <name>  |  tailscale ssh rab@archlinux
    "mkdir -p ~/file-portal/library/staging/.part-<sha16> &&
     tar -xf - -C ~/file-portal/library/staging/.part-<sha16> &&
     mv ~/file-portal/library/staging/.part-<sha16>/<name> ~/file-portal/library/staging/<name> &&
     rmdir ~/file-portal/library/staging/.part-<sha16>"
```

Failure at any point leaves only a dot-dir (invisible to the exporter, cleaned on retry). The final `mv` is the single atomic publish event. **No ThinkPad code changes needed** — this is the design's payoff.

## Engine routing (docs/11 policy table, made mechanical)

Implemented Desktop-side in the converter script, mirroring the ThinkPad's probe-and-route idiom:

1. `probe_chars_per_page` (pymupdf, identical math to `engines.py:46-55`).
2. Probe ≥ threshold **and** the text layer contains OCR-font spans (glyphless/invisible fonts — how tesseract/ABBYY layers identify themselves) → **`--strip_existing_ocr --recognition_batch_size 32`**, lane `scan`, lane_reason `untrusted_ocr_layer`.
3. Probe ≥ threshold, no OCR spans → **default Marker**, lane `clean`, lane_reason `text_layer_present`.
4. Probe < threshold → **default Marker** (its own OCR fires), lane `scan`, lane_reason `no_text_layer`, `--recognition_batch_size 32` as cheap insurance.

`min_chars_per_page = 100`, same provisional value and same revisit-note as the ThinkPad's.

## The analyst stage (slice 2 — design, gated on slice 1)

Per Phase 3: **Desktop GPU only** (52.6 tok/s vs ~5). Runs *between* Marker and bundle assembly, serialized by the same single-flight lock (Marker and Ollama never overlap; `keep_alive: 0` measured clean in Phase 2). **Link-fenced by construction:** every `![[assets/…]]`/`![](…)` embed is replaced by an opaque token `⟦IMG-n⟧` before the prompt, re-injected verbatim after; if token count in ≠ out, or any token altered, the pass is **rejected and the un-analyzed markdown ships** — the analyst can only ever improve prose, never lose an asset (the qwen3:8b URL-invention hazard, docs/11 Phase 2). Analyst output adds `analyst:` frontmatter (model, duration, pass/reject) so the vault can tell touched from untouched notes.

## Where things live

- **Repo (this lane):** `windows-converter/` — the Desktop converter script(s) + README. Slice 1 is script-driven (`convert_and_ship.py`); widget integration is a later, separate step (docs/11 design note).
- **Not repo:** ML envs (`C:\Users\Bndit\ml\marker-env`), Desktop anchor (`C:\Users\Bndit\ml\library\anchor` — same immutable-snapshot semantics as the ThinkPad's anchor), scratch outputs.
- **ThinkPad:** nothing changes. If slice testing reveals a needed change, it gets a coordination message, not a Desktop edit.

## Slice 1 gate (all three must hold)

1. A PDF never seen by the vault → Desktop convert → ship → **EXPORTED**: manifest `source_sha256` == locally computed hash of the source, bundle committed + blob-verified in the bare repo, visible after `git pull` on the Desktop's Library clone / Add-to-Library.
2. Same PDF shipped again → **EXPORT-SKIP**, no vault change.
3. The Beer book (converted only ever by the *ThinkPad*, sha `dbcce92c…` already in the vault) converted fresh on the *Desktop* and shipped → **EXPORT-SKIP**. This is the cross-machine dedup proof: the pipeline does not know or care which machine converted.

## Rollout after slice 2

Widget "Convert (GPU)" tile → local watched folder → this converter (instead of shipping the raw PDF) — the conveyor-belt rewire proper, with the old tiles kept as the ThinkPad fallback lane. Then the control-room build-out per the docs/11 design note (per-segment toggles, queue/ETA gauges fed by the measured s/page + tok/s numbers). Each step lands separately and switchable.
