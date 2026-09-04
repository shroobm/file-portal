# docs/53 — The Lead Hunt (Rab's 20 GitHub links + 2 papers, read against the six-row spec)

*Filed 2026-09-04, post-close of S114, by Claude Fable 5.1. Nothing here was built, nothing was
signed, no GPU cycle was spent. The reading was done by the fleet shape Rab ordered — **one Fable
coordinator, five Sonnet lanes** (`wf_e0aafa5e-107`: 6/6 agents, 31 min, 1.0 M subagent tokens) —
plus a sixth lane read earlier for the MDPI paper he added mid-run. The coordinator's job was to
falsify the lanes, re-run their measurements, and rank; Fable then re-read the two claims that
changed the record (Marker's order code, the licences) in the installed packages by hand.*

## 0. What Rab asked

> "If I researched a bunch of githubs, and you had to read through the code base, while I look for
> leads?" — then the list (20 repositories + `2401.11874v2` Detect-Order-Construct + the MDPI paper
> `applsci-16-03089`), then the shape: *"use a fleet of 1 fable coordinator and 5 sonnet 5 sub agents."*

The question underneath, asked the same night: *"Have we solved how to make conversion perfectly by
finding out the anatomy of the PDF?"* — answered **No** in docs/52. This hunt is the follow-up: which
of the world's code, if any, moves one of the six failing rows.

The six rows (the GROUND brief is verbatim in `fleet-script.js`): **#1** tables in born-digital
untagged PDFs · **#2** the convert-stage `degeneration` verdict · **#3** the scan-vs-clean lane ·
**#4** reading order without a tree · **#5** blank crops (SYM-053 — needs building, not a lead) ·
**#6** a better reconstructor, same books, same audit, same denominators.

## 1. The verdict, ranked (coordinator; Fable concurs after re-reading #1 and the order code)

| # | Lead | Row | Verdict | The one measurement | Tag |
|---|---|---|---|---|---|
| 1 | **Table-aware degeneration gate** — strip pipe-table rows before `degeneration()` (our own SYM-067, not a repo) | #2 | **BUILD — Rab's signature (J29)** | Already run with the repo's own function: 2025 4e anchor 26 blocks → 0; held Univ 4e 25 → **1** (raw line 8776, `{1 - t}` × 441 — SYM-056's unterminated array, rightly stays); Beer anchors stay flagged (max_trigram 2,267 / 143) | `Verified` |
| 2 | **Qwen3-VL-4B-Instruct-GGUF** (official Qwen quant, Apache-2.0; Q4_K_M 2,497,281,664 B + mmproj 453,974,304 B ≈ 2.95 GB) | #6 | MEASURE_NEXT | Render held Damodaran anchor page 805 (130 `\| \|` empty-cell markers), run through llama.cpp, score with `fidelity_audit.py --pdf/--md` + `latex_balance` against Marker's page; negative control = filler md (0.0 measured) | `Verified` sizes; run UNREAD |
| 3 | **Chandra-OCR-2** (on disk; **5.3B**, not 5B/9B; `qwen3_5` hybrid; code Apache-2.0, weights OpenRAIL-M $2M + "not competitively with our API") | #6 | BAKE_OFF_CANDIDATE | Same page-805 protocol, loading the safetensors at INT4 from `docling-env` (`Verified` by Fable: transformers 5.14.1 with `models/qwen3_5` present, torch 2.11.0+cu128) or the third-party GGUF (≈3.43 GB with mmproj; llama.cpp support for the hybrid arch Unknown) | `Observed` on disk |
| 4 | **nougat-base** (348.7 M; MIT code, CC-BY-NC-4.0 weights; dormant 559 days) | #1 (arrays) | BAKE_OFF_CANDIDATE on the RIGHT book | Run on **Ashby** (61 unterminated arrays, six 30+-`c` colspecs) and count `latex_balance` unterminated in its `.mmd` vs Marker's 61; Damodaran's 3 is too small to see | `Verified` card |
| 5 | **docling TableFormer** (`docling-ibm-models`, NOT installed; fast 145,453,276 B) | #1 | MEASURE_NEXT (install first) | CPU on held pages 805/564/757 crops; diff the cell grid vs surya `table_rec` from a J24 `blocks.json`, TEDS-scored against a hand-labelled grid — **there is no table ground truth on the corpus yet** | `Inferred` |
| 6 | microsoft/table-transformer via `unstructured` | #1 | BAKE_OFF_CANDIDATE | Same cell-grid diff; same kind as what Marker already runs (box detector + text assignment) | `Verified` |
| 7 | PaddleOCR PP-StructureV3 / SLANeXt | #1 | LOW | 69.65 "accuracy" is on an *internal self-built Chinese dataset*; a second DL framework | `Verified` |
| 8 | JaidedAI/EasyOCR | #3 | DEFER | Row #3 is shipped (NUM-5) and re-measured 9/9 correct on drop/done; a third witness only sharpens the scan-lane audit | `Verified` |
| 9 | Recursive XY-cut over J24 block bboxes (ported, three versions) | #4 | **DISCARD as measured** | Net vs content-stream order on the only ground-truthed specimens: **0 pages fixed / 3 broken** (ISO 15, 38, 47); v2 2/57 and 18/60 vs declared. The algorithm's real target (multi-column body text) is on neither specimen | `Verified` |

**Discarded with reasons** (all in `VERIFIED.md` and the lane reports): Detect-Order-Construct
(MSRA: *"Due to company policy, we cannot release the code"* — no model, no weights, only the
benchmark; trained on 8 × V100 32 GB); deepdoctection and `unstructured` as frameworks (licence +
weight + tooling before fit); zerox, llama-parse, colpali (cloud or retrieval, not conversion);
`rawdict` span flags and Producer metadata as scan signals (render mode 3/7 already does it, 9/9);
go-exiftool. **Idea only:** PdfPig (its Docstrum and interval-algebra reading-order detectors are
the one unmeasured thing on row #4 — Lane A flags them MEASURE_NEXT for the cover-page failure
shape), Florence-2, the YousifHisham notebook, and the MDPI synthetic-DLA paper (Lane F: training
data for a detector we do not train).

## 2. What the coordinator falsified (30 claims: 18 CONFIRMED · 6 WRONG · 5 OVERSTATED · 1 UNREAD)

The WRONG ones, because they are the ones that would have reached the record:

- **GROUND (my brief):** "marker 1.10.2 and surya 0.17.1 are Apache-2.0." **Wrong.** Both installed
  `METADATA` files say `License: GPL-3.0-or-later`; weights under a modified OpenRAIL-M ($2M). Upstream
  master reads Apache-2.0 / $5M per the coordinator's fetch. Fable re-read the two METADATA files: `Verified`.
- **Lane A (headline):** "Marker's final order is pdftext's span order; pymupdf raw block order is a
  faithful proxy." **Wrong, and inverted.** `marker/builders/layout.py:140` sorts every page's blocks
  by surya's layout `position` (`surya/layout/__init__.py:97`); `marker/processors/order.py:17-22`
  re-sorts **only** `layout_sliced` pdftext pages. Fable re-read both files: `Verified`. Consequence:
  **docs/52 §2.7c's "2/57, 15/60" measured the content stream against the declared tree, not Marker**
  — corrected in place in docs/52; the real measurement is J30.
- **Lane D:** "Chandra is 9B per the HF card" — that was Chandra **v1**; v2 is 5.3B
  (`du -b model.safetensors` 10,591,220,088 B ÷ 2). "10,611,947,865 bytes on disk" was the folder total.
- **Lane B:** "PaddleOCR … accuracy denominator likely PubTabNet-style" — it is an *internal self-built
  Chinese dataset* (their own doc). "1,277 anchors, monotonic, 0 violations" — 1,393 anchors, 2 violations.
- **SYMPTOM-INDEX SYM-067 (ours):** "counterfactual → 0 paragraphs trip in both 4e audits" —
  **OVERSTATED**: the held University 4e keeps **one** block, and it is a real runaway. The gate would
  still hold that book on line 8776 — which is correct behaviour, and is now the acceptance test.

Seventeen measurements were re-run, all listed in `VERIFIED.md` §measurements: XY-cut v1/v2/v3 byte-match
Lane A; `latex_balance` 87/84/3 on the held md; the probe()+route() loop on all 9 drop/done PDFs
(pymupdf 1.28.0); `fidelity_audit.py` positive 0.9271/1372 and negative 0.0/1372; the SYM-067 pair.

## 3. Findings that changed the registers

| Register | Change |
|---|---|
| `docs/52` design.md §2.7c + VERIFIED.md | **Correction block:** the resequencing counts are content-stream-vs-tree, not Marker-vs-tree; Marker's true divergence UNREAD → J30 |
| `SYMPTOM-INDEX` SYM-067 | The measured pair (26→0 / 25→1 with line 8776 staying / Beer stays) recorded as the acceptance |
| `SYMPTOM-INDEX` SYM-073 | **New:** the held bundle's manifest says `convert.doc_survival` 0.9334; a fresh audit on the byte-identical pair says 0.9271. Cause Unknown — the manifest carries `marker_version: "unknown"` and the audit stamps only `SCHEMA_VERSION = 1`, so the two numbers are not the same measurement |
| `OPEN-TASKS` J25 | Refined: Chandra 5.3B / `qwen3_5` hybrid; INT4 path via `docling-env`; the roster ranking; **Marker 2.0.0 (2026-07-20) as its own candidate in a separate `marker2-env`** (surya 0.22.1, transformers ≥ 5.12.1 — the same transformers line Chandra needs); the page-805 protocol; the licence correction |
| `OPEN-TASKS` J29 | **New — the build-first.** The SYM-067 table-aware gate with the measured pair as acceptance. Gate change ⇒ Rab's signature |
| `OPEN-TASKS` J30 | **New.** Marker's actual order vs the declared tree on WTPDF + ISO via a GPU `marker_blocks.py` run |

## 4. What Rab decides (sign-by-slot)

1. **J29 — build the gate / leave SYM-067 open.** CPU-only, one function, the audit scores itself, and it is the verdict holding the maiden voyage. Recommendation: build.
2. **Rank 2 — download Qwen3-VL-4B-Instruct-GGUF (~2.95 GB, official Qwen org) / not yet.** One GPU session, ~5 GB headroom, first reconstructor number that is his own.
3. **Rank 3 — Chandra: read the OpenRAIL-M clause yourself before any run / skip.** Then INT4 from `docling-env` or the third-party GGUF.
4. **J30 — schedule the GPU run on WTPDF + ISO / leave docs/52's prize unmeasured.**
5. **`marker2-env` — stage marker 2.0.0 beside 1.10.2 / stay on 1.10.2** (J25). The `FlatBlockOutput.page` bug (J24) is still at upstream master; filing it upstream is his call.

## 5. Residue (declared, not resolved)

From the coordinator, verbatim in `VERIFIED.md`: (1) Marker's actual block order vs the declared
tree UNREAD; (2) PaddleOCR, EasyOCR, TableFormer never installed — no CPU-s/page on this hardware;
(3) PaddleOCR's first-use model host / offline caching UNREAD; (4) whether llama.cpp runs the Qwen3.5-
hybrid Chandra GGUF: Unknown, nothing downloaded; (5) the Qwen3-VL document-parsing cookbook prompt
was summarised, not quoted — fetch it before a real run; (6) the SYM-073 drift's cause; (7) Lane B's
page numbers are ± the local anchor gap (largest 839 lines) — exact pages need a `blocks.json` this
held bundle predates; (8) Designing with Freedom's source PDF is absent from disk; (9) Lane F's paper:
four numbers and two defects re-checked, the other 29 pages not re-read; (10) every web fetch passed
through the summariser — licence and size fields were requested verbatim, not hand-parsed from raw
bytes, except the two Fable re-read (§2); (11) GPU untouched; nothing under the repo was written by
any agent — the register edits above are Fable's, in one post-close commit.

## 6. Files

- `A-reading-order.md` · `B-tables.md` · `C-scan-lane.md` · `D-reconstructors.md` · `E-frameworks.md` ·
  `F-synthetic-dla-paper.md` — the lane reports, each with its own residue section.
- `VERIFIED.md` — the coordinator's falsification pass, measurements, ranking, build-first, residue.
- `fleet-result.json` — the structured output of all six agents. `fleet-script.js` — the workflow
  as run (GROUND brief, schemas, decoys, lane prompts).
- `scripts/` — the probes as run: `xycut_probe.py` / `xycut_v2.py` / `xycut_v3_net.py` (Lane A),
  `measure_lanes.py` + `lane_measurements.json` (Lane C), `verify_lane_b.py`, `verify_lanes_c_e.py`,
  `verify_sym067_pair.py`, `verify_sym067_residual.py` (coordinator). Paper text extractions were
  **not** copied — the repository is public.
