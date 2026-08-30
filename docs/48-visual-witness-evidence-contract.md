# 48 — Visual Witness evidence and corpus contract (VW-E1)

**Status:** Accepted for VW-E1 · VW-E2-R2 implementation verified; Rab calibration pending  
**Date:** 2026-08-28  
**Decider:** Rab  
**Authority observed:** *"I sign on E1"* in Codex task
`01a0496a-6b64-72b2-88b2-3c5b3d151855`  
**Scope:** VW-E1 accepted; direct corrective development authority recorded for VW-E2-R2;
VW-E3–VW-E8 remain unsigned  
**Planning anchor:** `feat/library-pipeline` at
`a29d703d981ebcef3994711be9d4ad3205446edf`  
**Canonical contract:** `docs/contracts/visual-witness-e1-contract-v1.json`,
SHA-256 `3c2144d33079f7868e0bd3a8c1e4328a4797a1ac9fdb7b2d34ab32412a5fcfd1`

## Decision

File Portal will treat the Visual Witness Map as an **out-of-band, immutable,
report-only evidence plane**. It may read a hash-verified source PDF, raw Marker
Markdown, analyst variants, manifests, and assets. It may render, tile, locate,
compare, classify, and display evidence. It may not mutate a source, bundle,
manifest, asset, fidelity verdict, repair ledger, pipeline gate, ship state, or
vault.

The evidence plane has four non-interchangeable layers:

1. **Observed source/output bytes** — hashes, pixels, exact Markdown spans, native
   PDF extraction results.
2. **Inferred machine evidence** — segmentation, visual localization, OCR,
   alignment, and omission candidates.
3. **Human disposition** — an append-only record bound to the immutable result.
4. **Production mutation** — outside this commission through VW-E8.

This separation follows the existing doctrine: the LLM may adjudicate a
deterministically marked page span, but never search the document or control a
verdict (`docs/41-conversion-completeness-plan.md:207-225`).

## Why this contract is necessary

The shipped figure instrument answers a page-presence question, not a regional
omission question. A page with three source figures and one output asset counts
as covered (`windows-converter/figure_coverage.py:5-20`). It also has measured
blind spots for scan pages, zero-area connectors, and table/prose vetoes
(`windows-converter/figure_coverage.py:36-77,435-470`). The new instrument must
not call those unread surfaces clean.

The current rescore seam supplies the correct fail-closed precedent: missing,
invalid, or mismatched source identity is `UNREAD`, and the bundle is not
modified (`windows-converter/coverage_rescore.py:73-95`).

Text metrics are phase-specific. Convert survival compares source-PDF witness
windows with raw Marker Markdown; analyst survival compares raw Marker Markdown
with analyst Markdown (`windows-converter/fidelity_audit.py:341-408`). They have
different references and denominators and may never be blended. A zero-window
denominator is `UNREAD`, never a perfect `1.0`.

The analyst currently protects only image-token membership, sorts those tokens,
and chunks on blank lines (`windows-converter/analyst.py:76-101,216-217`).
Its resume key includes the prompt program name but not prompt-file bytes
(`windows-converter/analyst.py:230-237`). VW-E5 must therefore bind prompt and
contract hashes and validate protected-span identity, structure, and ordered
assets before admitting any proposal.

The existing Bench demonstrates the right proposal boundary: the same rectangle
can produce a crop plus native-text witness, and model output is returned as a
proposal (`prototypes/repair-bench/bench.py:909-968`). Its apply path mutates
Markdown and manifest (`prototypes/repair-bench/bench.py:974-1005`), so VW-E6
will use a side-effect-free reader and intent ledger rather than those POST/apply
paths.

## Contract artifacts

| Artifact | Purpose | SHA-256 |
|---|---|---|
| `docs/contracts/visual-witness-e1-contract-v1.json` | Canonical machine-readable E1 contract | `3c2144d33079f7868e0bd3a8c1e4328a4797a1ac9fdb7b2d34ab32412a5fcfd1` |
| `docs/contracts/visual-witness-region-v1.schema.json` | Immutable regional evidence sidecar | `531b9ac22b302792ee66e1cecd1f94dd8385f5ca7904f26c0f31ee96c1d78d73` |
| `docs/contracts/visual-witness-corpus-v1.schema.json` | Private six-case corpus manifest | `0639e232311d7e0ee155c83806781010b6b437f6a80fec659c7493409df1b940` |
| `docs/contracts/visual-witness-event-receipt-v1.schema.json` | Mandatory event-exit receipt | `ae057c25216cbbe64c551752faa7ae603137343746dbacb46f990d69736e7b4f` |
| `codex/private/visual-witness/VW-E1-corpus-v1.local.json` | Gitignored titles, paths, and byte hashes | `e7299b50dd0d8ae5498ca13eb18c9a37c6bce5c38d24dd73351609e0c91a5c46` |

The private manifest is intentionally absent from Git. The repository is public,
and these are copyrighted/commercial source documents. New VW-E1 public
artifacts carry opaque case IDs, case classes, page counts, and the
private-manifest digest—never private titles, absolute paths, source bytes,
crops, or OCR text. Older project documentation is outside this disclosure
claim.

## Frozen corpus

The corpus is a **current-byte digest over a live operational tree**, not a copy
and not a claim that `ml\library` is immutable. Every later event must re-hash
before reading. A mismatch halts as ground drift.

| ID | Split | Lane/pages | Why it exists |
|---|---|---:|---|
| VW-T01 | calibration | clean / 104 | raw/analyst formatting baseline, two analyst variants, embedded figures |
| VW-T02 | calibration | scan / 184 | OCR, known blank asset, analyst structural damage, tables |
| VW-T03 | calibration | scan / 465 | OCR, large-table/Bench site, raw/analyst comparison |
| VW-H01 | held-out | clean / 1,356 | sole real doubled-page-map poison, large-book/table stress |
| VW-H02 | held-out | scan / 439 | embedded OCR, figures, formatting held-out; current fidelity verdict `UNREAD` |
| VW-H03 | held-out | clean / 91 | vector connectors and diagram fragmentation; raw-only |

Observed at freeze: all six source files were readable, and **6/6 actual source
SHA-256 values matched their manifest source hashes**. Numerator: matching source
files. Denominator: six declared corpus cases. Conditions: local
`drop\done` sources and `anchor` bundles at 2026-08-28; no converter or model run.

The split is sealed:

- VW-T01–T03 may tune configuration.
- VW-H01–H03 may not be opened for threshold, prompt, model, or rule tuning.
- Their first scored use is VW-E7 after code, contract, configuration,
  dependency, model, and prompt hashes are sealed.
- Any case-byte overlap across splits is `VW-HELDOUT-CONTAMINATION`.
- Held bundles carrying human repair state are not training inputs.

Known exclusions remain explicit:

- A challenge-only specimen lacks raw pre-analyst Markdown and cannot score
  formatting improvement.
- No second independent real page-map-poison family is available.
- VW-H03 has no analyst output.
- VW-H02 has no current fidelity verdict.

## Evidence identity

All identities use full lowercase SHA-256. Sixteen-character UI or resume
prefixes are not evidence identifiers.

- Source pages are 1-based.
- Asset filename page IDs remain recorded separately as 0-based.
- Coordinates are canonical PDF points plus normalized page fractions.
- A tile is a compute window, never region identity.
- `report_id` is SHA-256 over canonical UTF-8 JSON with `report_id` omitted.
- Region identity binds source hash, page, rectangle, class, and segmentation
  configuration hash.
- Exact Markdown spans carry byte offsets, line bounds, phase, and span hash.

Invalidation is transitive:

1. Source mismatch/unreadable → whole report `UNREAD`.
2. Manifest or manifest-source change → source/bundle/page-map join stale.
3. Markdown change → its spans, text result, pair result, and phase metrics stale.
4. Asset-inventory change → visual and pair results stale.
5. Contract/config/code/dependency/engine/prompt-byte change → all dependent
   inferred results stale.
6. A stale human disposition remains historical; it never transfers.

## Witness and result vocabulary

Native PDF text is a **fidelity witness** only when source, page, rectangle,
method, and hash are bound. Independent OCR is an **agreement witness**, never
source truth. Embedded or same-family OCR is correlated/untrusted. An empty
native extraction proves only an empty extraction.

Machine states:

- Visual: `matched`, `partial`, `wrong-or-blank-asset`,
  `omitted-candidate`, `ambiguous`, `unread`, `not-applicable`.
- Text: `matched`, `partial`, `substituted-candidate`,
  `omitted-candidate`, `ambiguous`, `unread`, `not-applicable`.
- Pair: `both-supported`, `visual-only`, `text-only`,
  `neither-supported-candidate`, `conflict`, `ambiguous`, `unread`.

No machine state is “confirmed omitted.” Human actions—`accept`, `edit`,
`reject`, `defer`—live in a separate append-only disposition chain bound to
`report_id`, `region_id`, and `base_result_sha256`. They record review intent;
they do not apply repairs.

## Metric law

Every rate names numerator, denominator, and conditions
(`docs/34-measurement-language.md:23-24,87-95`).

| Phase | Numerator | Denominator | Required separation |
|---|---|---|---|
| Capture | valid rendered pixels covered by ≥1 declared base tile | valid rendered pixels on readable attempted pages | unread pages reported separately |
| Visual | evaluable source regions with source-conditioned asset support | evaluable declared source regions | stratify class and 1:many/many:1 |
| Native text | native-source windows found in exact raw-Marker span | eligible native-source windows | fidelity only |
| OCR text | independent-OCR windows agreeing with exact raw-Marker span | eligible OCR windows | agreement only |
| Convert | source-PDF windows surviving into raw Marker | eligible source-PDF windows | never analyst denominator |
| Analyst | raw-Marker windows surviving into analyst Markdown | eligible raw-Marker windows | never source-PDF denominator |
| Formatting | admitted candidates satisfying all contract predicates | admitted candidates | refusals/raw fallbacks separate |
| Bench | evidence-review tasks completed without hidden blocker | declared tasks attempted | keyboard/zoom/theme/label strata |

Denominator zero means `value=null`, status `UNREAD`. Images receive zero
text-survival credit. Visual and text evidence never collapse to one confidence
score.

Schema validation is necessary, not sufficient. The event's semantic probe must
recompute every ratio, reject numerator greater than denominator, re-hash every
computed identity, reject duplicate raw JSON members before parsing, and verify
cross-split source/bundle uniqueness. A self-reported equality boolean is not
proof.

## Privacy, retention, and resources

- New VW artifacts placed in public Git receive schemas, redacted census,
  contract prose, and private-manifest digests only.
- Full-page renders, tiles, region crops, native text, and OCR text are
  ephemeral through VW-E4 and deleted on both success and failure.
- Sidecars retain hashes, geometry, method/engine versions, counts, and states;
  no inline base64 or raw witness text.
- Metadata sidecars live locally outside source, bundle, repo, `anchor`, `held`,
  `pending`, staging, and vault.
- Network/cloud is denied by default. Any later upload requires a separate
  per-run human decision naming case IDs, exact outgoing fields/bytes, endpoint,
  resolved model/version, retention, cost, and expiry.
- Processing is one page and one worker at a time.
- Scratch is capped at 4 GiB; execution requires 8 GiB free-space preflight.
- VW-E2/E4/E5-validator/E6-read-only are CPU-only.
- GPU work is limited to separately signed VW-E3/VW-E7 packets, one process,
  named mutex `Local\file-portal-card`, and a 9 GiB VRAM ceiling.
- Every environment is isolated and pinned; nothing is installed into
  `marker-env`.
- `xrefs=True` is forbidden: it measured 34.6 seconds/page on a large scan
  (`windows-converter/figure_coverage.py:459-468`).
- A model length ceiling or missing completion reason is truncated/`UNREAD`.

## Test strategy

The strategy is a pipeline pyramid:

1. **Unit/property:** geometry, coordinate transforms, parsers, state truth
   tables, hash invalidation, and canonical serialization.
2. **Offline integration:** synthetic PDF → evidence; frozen copies only;
   before/after protected-tree digest identical.
3. **Visual/accessibility:** real browser, fixed viewport/font/theme/zoom,
   keyboard and axe-style checks. Source grep is not visual QA.
4. **Held-out:** VW-E7 only, after all tunable hashes are sealed.

Every event uses the same check for its planted failure. A green count without a
negative control is insufficient. The universal exit receipt records case
census, tests, metric formulas and counts, output hashes, privacy/network/GPU
receipts, before/after mutation digest, residue/process/port/GPU census,
independent verifier, conflicts, `UNREAD`s, blast radius, and
`next_event_authority=UNSIGNED`.

Required negative-control families include:

- one-pixel/four-tile-corner crossings, odd dimensions, rotation, CropBox
  offset, blank/corrupt page, and forced render failure;
- zero-area connectors, table-like drawings, full-page scans, gross and
  plausible page-map poison;
- correct, partial, blank, wrong, duplicate, shuffled, 1:many, and many:1
  assets;
- no text layer, repeated headers, no flanks, OCR skew/conflict/correlation;
- protected-span removal/reorder, code/math/table splits, CRLF/CJK, malformed
  and truncated candidate, stale resume journal;
- missing evidence, long/CJK labels, stale/overlap intent, malicious HTML,
  keyboard/focus, zoom, contrast, and color-only meaning.

The load-bearing visual negative control replaces a correctly named,
Markdown-referenced asset with a uniform-white image. Legacy page-level P-1
must still say “covered,” proving its ceiling; Visual Witness must report
`wrong-or-blank-asset`, while text remains independent.

## Options considered

### A — Out-of-band evidence plane (**selected**)

| Dimension | Assessment |
|---|---|
| Pipeline risk | Low: operational roots remain read-only |
| Back-fill | Supports existing bundles |
| Region fidelity | Requires new render/localization work |
| GPU coupling | None for capture/pair; separately signed later |
| Auditability | Strong: immutable sidecar and exit receipt |

### B — In-converter capture

Richer Marker layout may be available, but every audit second extends the
one-card lock and changes the production conversion blast radius
(`docs/41-conversion-completeness-plan.md:142-171`). This is rejected for the
first implementation.

### C — Image-only reconstruction

It guarantees a visible page facsimile but destroys searchable structure,
accessibility, and phase-correct text measurement. It remains a comparison
fallback, never the default converted document.

## Consequences

What becomes easier:

- omissions carry exact source/image/text/Markdown provenance;
- blank or wrong assets can be distinguished from missing references;
- agents can propose against fixed spans without searching the whole book;
- later UX can show crop, captured text, Markdown, and asset together.

What becomes harder:

- every configuration change invalidates dependent inferences;
- held-out discipline slows tuning;
- OCR disagreement must remain visible instead of becoming one answer;
- local evidence has storage/privacy costs even when no document changes.

## VW-E1 verification

Observed during this event:

- hard and soft session clocks both name S111 close `4e613696`; the close and
  ledger-row SHAs are ancestors of the planning anchor;
- six source files were re-hashed and matched their manifests;
- the private corpus JSON conforms to the checked-in corpus schema using
  PowerShell `Test-Json`;
- the same schema rejected an in-memory negative control with
  `source_hash_match=false`;
- ordinal asset-inventory hashes were independently recomputed for all six
  cases; a locale-sensitive first pass was rejected and replaced;
- schema negatives reject a 2/4 corpus split, measured `0/0`, swapped modality
  states, false `COMPLETE`, and unauthorized network/cleanup claims;
- no converter, model, browser, network, GPU, mutex test, or live process was
  started;
- the initial Python `jsonschema` import was unavailable, so that probe is
  `UNREAD`; the built-in PowerShell schema validator supplied the actual check.

Final wiki, diff, schema-syntax, digest, and residue checks are recorded in the
VW-E1 exit receipt.

## Next event — unsigned

`docs/contracts/visual-witness-e2-packet-r1.json` is the exact proposed
Detect/Capture packet. SHA-256:
`0bcabaf843ea54416f4111af8e1e3dbb88ef33d053e0829fcecc9162593832f0`.

It proposes two new out-of-band files, 192-DPI page rendering, 1,024-pixel
tiles with 20% overlap, six declared region classes, calibration cases only,
CPU/network/GPU isolation, explicit geometry and identity controls, a 45,000
aggregate-token ceiling, and a required stop with VW-E3 unsigned.

No part of VW-E2 is authorized by this document or by the VW-E1 signature.

### VW-E2-R2 implementation handoff — calibration still unread

R1 remains the immutable stopped revision. Rab's later direct instruction authorized the
corrective R2 development and tests but reserved the real run for File Portal/operator handoff
(`coordination/SIGNATURES.md`, current final entry). The current R2 packet is 110,341 bytes,
SHA-256 `ebc047b8d963a8e3b92ebd7479055dbf78121fad93094f38c902ce9f92cc6769`.

The frozen producer, self-test, and independent verifier are respectively:

- 279,578 bytes / `a4c789d8571b7c69052bca746285740c194a9df6f4461995ad0ae4b8d9ca6992`;
- 99,730 bytes / `dc62fcc79608f077b23394654caf63118ef0dea7df19cc2ab5a38f2dbb43373a`;
- 25,251 bytes / `b5c5e7b373650e1a85121a06f803cebcd32a7bcfea88210718e801b584e149f0`.

Two independent runs passed 54 of 54 hermetic tests. A separate static Circle passed the final
packet/code order and anti-fabrication boundaries: a report is created and reopened before
receipt assembly; a post-report failure preserves the report and emits a minimal attempt exit;
repository-configured Git helpers are denied before execution; HEAD, protected inputs, privacy,
cleanup, process/port activity, and verifier evidence are measured and fail closed.

E2 captures page renders, tiles, crops, and native text ephemerally, but retains no raw page,
image, crop, tile, or extracted-text payload. Only hashes, geometry, counts, states, and bounded
provenance can persist. This does not alter converted documents or product behavior.

Observed at this handoff: real calibration runs 0; operational reports 0; COMPLETE receipts 0.
Therefore VW-E2 is not complete and VW-E3 remains `UNSIGNED`. The thread-scoped observability
artifact contains the private local run command and evidence-return checklist.

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5) · S112 · 2026-08-28⟩
