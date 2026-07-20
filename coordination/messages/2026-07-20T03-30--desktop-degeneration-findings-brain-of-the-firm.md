# Findings Register — Degeneration in vaulted "Brain of the Firm" + audit-tooling hazards

**From:** Desktop (DESKTOP-OBTQIRD), Session 27, Claude Fable 5
**Date:** 2026-07-20 ~03:30 UTC (2026-07-19 late evening local)
**Discovery credit:** Rab, visually, while reading the vaulted book in the reader — the pipeline reported nothing.
**Verification instrument:** prototype of the docs/15 §5 degeneration tripwire (`degen_scan.py`, scratchpad):
per paragraph ≥ 200 chars, zlib(level 6) compression ratio + max repeated word-trigram count;
flag at ratio < 0.18 OR trigram ≥ 8 (deliberately loose). Run via marker-env python, read-only,
over all four vaulted books in the Desktop Library clone at vault commit `f310f75`.

**Audit status of this register:** every finding below is CONFIRMED — each is backed by a live
run quoted verbatim, a direct code read, or a reproduced error. No inferred claims. (F4 is a
measurement, not a defect.)

---

## F1 — HIGH — Degeneration loops in the vaulted Brain of the Firm (scan lane)

**Statement:** The production vault copy of Brain of the Firm (`7de1c31a`, lane=scan, exported
`f310f75`) contains large OCR degeneration loops: **140,513 of 1,139,354 chars (12.3%) flagged,
in two contiguous zones** — vaulted-md lines ~1594–1668 and ~2758–2814.

**Evidence (scan output, worst blocks):**

| line | chars | zlib | max trigram | first words |
|---|---|---|---|---|
| 1600 | 32,294 | 0.003 | ×2,152 | `## The Control of the Control of` |
| 1624 | 29,477 | 0.003 | ×2,267 | `## The Stage of the Stage of` |
| 2758 | 22,019 | 0.009 | ×1,674 | `in Agril 1972. The selection of one` |
| 2774 | 6,253 | 0.026 | ×466 | `We saw in the last chapter how` |
| 1658 | 6,164 | 0.028 | ×371 | `The regulatory system as so far described` |
| 1634 | 3,685 | 0.062 | ×247 | `All this aver year to arrange on` |

(29 paragraphs flagged total at loose thresholds; see F4 for how many are true positives.)

**Root cause:** autoregressive decode loop in Marker's OCR stage on hard scan pages — the
classic LLM-OCR repetition pathology. Attribution to the convert stage (not the analyst) is
supported by (a) OCR-shaped misreads woven through the same zones ("drivation" for derivation,
"clausitying", "We taw", "Agril"), which a formatting LLM would not invent, and (b) F3: these
blocks are single paragraphs the analyst never successfully processed.

**Disposition:** re-convert the book (decode loops are typically nondeterministic; the PDF's
embedded OCR layer is a per-zone fallback), verify with the audit, supersede-swap into the
vault (Designing Freedom `9e40b2b` pattern). **Keep the current bad copy until then: it is the
labeled true-positive calibration specimen required by docs/15 §9.** Suggested S28 validation
loop: audit flags vaulted copy → re-convert → audit passes → swap. Supersede mechanics touch
the exporter lane (open queue item #1, ThinkPad, user-gated).

## F2 — MEDIUM — Duplication accompanies degeneration

**Statement:** The same source region was emitted multiple times in independently degraded
variants — e.g. three copies descending from "We saw in the last chapter how" (lines 2764,
2774, 2784) and repeated "in April 1972" variants (2758, 2766, 2776).

**Implication for docs/15:** survival/containment scoring alone could be fooled on such pages
(the true text may exist *somewhere* among the duplicates); the §5 degeneration + duplication
tripwires are therefore load-bearing, not optional. CONFIRMED by scan output above.

## F3 — MEDIUM — Analyst chunker passes oversized paragraphs through unexamined

**Statement:** `analyst.py::_chunks()` splits only on blank lines and never inside a paragraph;
a paragraph larger than CHUNK_TARGET (4,000 chars) becomes a single oversized chunk. The 32K
and 29K degenerate blocks exceeded NUM_CTX=8192 entirely; per the fail-safe policy
(exception/fence-violation → ship original) they flowed to the vault untouched and unexamined.

**Assessment:** the fail-safe behaved CORRECTLY (no content was lost by the analyst) — but it
means the analyst provides no backstop against degeneration, and legitimately huge paragraphs
silently skip analysis. Verified by code read (`windows-converter/analyst.py:62–73`) plus the
vaulted evidence. **Disposition:** detection belongs to the audit (§5), not the analyst;
optionally hard-split oversized paragraphs at a later date (not urgent, not this build).

## F4 — MEASUREMENT — Clean threshold separation; other three books clean

**Statement:** On this corpus the true loops and legitimate repetitive content separate with
clear water: every true loop has **zlib ≤ 0.17 OR trigram ≥ 42**; every false positive at loose
thresholds (chapter TOC line 94, binary-pattern table line 586, table headers 2149/2335, one
Textor philosophy paragraph at zlib 0.433/×8) sits at **zlib ≥ 0.31 AND trigram ≤ 31**.

**Production prior (recorded in docs/15 §9.1): flag at zlib < 0.20 OR trigram ≥ 40** → zero
false positives and 100% catch on known specimens. Corpus scan results: Brain of the Firm
INFECTED (above); **Designing Freedom 0 flags; bojieli 0 flags** (CJK caveat: word-trigram
detector requires spaces — the audit must use character n-grams for CJK; zlib column remains
valid); **Textor 1 false positive** (healthy prose).

## F5 — LOW — MAX_PATH hazard for audit tooling on pre-L15 bundles

**Statement:** The vaulted Textor md path is **349 chars**; a naive Python `open()` fails
FileNotFoundError until the path is passed with the `\\?\` long-path prefix (reproduced, then
fixed, this session). L15 fixed interior name lengths at the source for NEW bundles; the four
existing vault books predate it and keep long names.

**Disposition:** `fidelity_audit.py` and any Desktop-side tooling that reads the vault clone
MUST be long-path-safe (`\\?\` prefix or os.add_dll/long-path-aware open helper). Noted in
docs/15 §8.

---

## Meta

- This register accompanies the first commit of `docs/15-survival-audit.md` (the Survival
  Audit spec + §9.1 calibration priors). The audit build is scheduled as S28 (Opus 4.8,
  kickstart prompt prepared; report-only mode until Rab signs off thresholds per §9).
- Larger point for the record: this is the empirical proof of the fidelity think-tank's
  premise — 1 of 4 vaulted books carried 12% garbage through a pipeline that reported all
  green. The eyeball caught it this time; the audit exists so it doesn't have to again.
