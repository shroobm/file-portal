# `analyst-lab/edit-whitelist` — the diff-whitelist acceptor (quarantined prototype)

*Built 2026-09-09 by Fable lane R1 of the S119 research fleet (Rab's commission: "look for optimal
solutions that are interpretable into the file-portal ecosystem … if improbable or impossible, find a way
to isolate a quarantined example case"). Worktree `wf_cd7e80f0-d5a-1`, base `e19e0e0`. CPU only; the
pipeline, `held/`, ollama and the GPU were never touched. Every number below is `Observed` from the
scripts in this directory run against the held DDIA bundle `fc1f068c3a8eeb63` unless tagged otherwise.*

## What it is

Three scripts that answer one question on the real 492 analyst pairs of DDIA 2e: **if the analyst's
output were gated edit-by-edit against a whitelist of formatting-only changes, and every other edit
reverted to the input span, what would the REAL document audit (`fidelity_audit.audit_analyst`) read?**

| file | role |
|---|---|
| `common.py` | loads the held bundle read-only; rebuilds the analyst's 492 chunks exactly as `analyst.process` does (`fence` → `_chunks`) |
| `align.py` | segments the shipped body into the 492 per-chunk counterparts (method recorded per boundary; 20/20 rejected chunks come back verbatim; the pieces concatenate to the shipped body byte-for-byte) |
| `classify.py` | **Ask B** — word-level opcodes per pair in the audit's own ladder view, one class per edit, and every FAILED 12-word window attributed to the class of the edit overlapping it |
| `acceptor.py` | **Ask C** — the whitelist acceptor: `reconcile(input, candidate, rungs)` → reconciled chunk; reassembles a body; audits it; two negative controls; two policies; three ladders |
| `results_*.json` | the measurements, as written by the scripts |

Run (marker-env interpreter, from this directory): `python align.py`, `python classify.py`, `python acceptor.py`.
`reconciled_*.md` (the two reassembled bodies, 2 MB each) are written here and git-ignored.

## How the pairs were located (honestly)

`analyst.process` builds `unfence("\n\n".join(out), embeds)` where `out[i]` is the candidate (passed) or the
original chunk (rejected). Re-fencing the shipped body therefore yields the same 154 `⟦IMG-n⟧` tokens in
the same order. Boundaries: for chunk k+1 its first 12 non-empty normalised keys are searched in the
shipped token stream inside a window sized by chunk k (×1.6 + 200 — the inflation guard admits ≤1.5×);
all occurrences are collected and the one closest to the expected position wins (title pages repeat their
blurbs — the first occurrence was the wrong one); a REJECTED chunk's verbatim match is taken as the
boundary unconditionally (it ships verbatim by construction). Census: `verbatim` 51 · `exact12` 409 ·
`exact8` 27 · `exact6` 1 · `exact4` 1 · `fuzzy` 2 · last 1. Checks: 20/20 rejected chunks equal their
input; the pieces concatenate to the shipped body byte-for-byte; per-pair `word_ratio` matches the
manifest's `r` within 0.005 on 466/472 passed rows and `chunk_survival` matches `s` on 471/472 (the one
off is chunk 4, a TOC table the model reflowed: 0.9286 vs 1.0).

## Ask B — the 3 % by class (Observed, `classify.py`)

Population: 20,589 twelve-word windows of the sidecar under the j32a-v2 ladder; 581 fail against the
whole shipped body (doc_survival 0.9718, reproducing the manifest). Each failed window takes the
highest-priority class among the edits overlapping it (deletion > substitution > numeral > ligature >
escape > link-syntax > insertion > reflow):

| class | failed windows | % of all | % of failed | what it is |
|---|---:|---:|---:|---|
| link-syntax | 175 | 0.850 | 30.1 | Marker's citation `[[2\]](#page-490-0)` rewritten by the model as `[2](#page-490-0)`; the ladder's link regex strips only the second form, so the reference reads `2page490` and the output `2` |
| ligature | 138 | 0.670 | 23.8 | `dicult`→`difficult`, `soware`→`software`, `ere`→`there`: Marker's mis-mapped ligature glyphs repaired by the model (fi fl ff ffi ffl ft fk Th) |
| deletion | 127 | 0.617 | 21.9 | words or paragraphs gone |
| escape | 78 | 0.379 | 13.4 | SYM-076: `within\_recursive` → `within_recursive` |
| substitution | 46 | 0.223 | 7.9 | `become`→`becomes`, `headvertex`→`head`, `uur`→`üur` (a lost diacritic the model restored) |
| insertion | 10 | 0.049 | 1.7 | headings/URLs added, one `/no_think` leak |
| numeral | 7 | 0.034 | 1.2 | `person(100,`→`person(10,` (chunk 81) |
| unexplained | 0 | | | every failed window overlaps an aligned edit |

**Audit-blindness classes (link + ligature + escape) = 391 windows = 67 % of the loss; content classes
(deletion + substitution + insertion + numeral) = 190 = 33 %.** Forgiving the blindness alone would read
0.9908; reverting the content alone 0.9810; neither reaches 0.995 by itself.

Edit counts (opcodes, all 492 pairs, ladder view): deletion 984 · substitution 956 · link-syntax 189 ·
ligature 163 · escape 99 · numeral 38 · insertion 33. Pairs: 69 passed chunks came back word-identical,
403 differ, 20 rejected are verbatim. Numeral census (clean, J45's first act): 141 chunks / 268
digit-bearing ladder words present in the input and absent from the output (denominator 492 pairs; this
counts citation numbers moved out of `[[n\]]` links as well as real rewrites — J45's rule must exclude
link text before it counts).

## Ask C — the acceptor (Observed, `acceptor.py`)

The whitelist N, applied to both spans, compared space-free: curly quotes/dashes unified (NFKC + the
audit's `_QUOTES`); markdown backslash-escapes removed; `[text](url)` and `[[n\]](url)` collapsed to their
text **with the URL multiset of the two spans required equal**; heading marks, `*`, boundary `_`,
backticks, `>`, table pipes/separators, square brackets removed; a line-end `!`-hyphen or `-` followed by
whitespace and a lowercase letter joined; the input's mis-mapped ligature glyph may be REPLACED by one of
`ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|Th|th` (required, so a dropped quote alone is not a repair). Everything
else is reverted: substitutions, deletions, insertions, numeral changes, punctuation-only and case-only
edits (strict on purpose — the audit is blind to those, so reverting them costs nothing and keeps the
author's text).

| run | doc_survival / runs (j32a-v2, as shipped) | under v3b (escape-first + ligature-blind) | under v3c (v3b + `[[n]](url)` collapsed) |
|---|---|---|---|
| shipped body (the manifest) | **0.9718 / 49** | 0.9808 / 33 | — |
| CONTROL accept-ALL | 0.9718 / 49, body == shipped byte-for-byte | | |
| CONTROL accept-NONE | 1.0 / 0, ladder words == sidecar | | |
| policy FULL (whole whitelist) | **0.9817 / 24** | 0.9898 / 9 | **0.9968 / 1 — clears 0.995** |
| policy STRICT (FULL minus ligature, escape, link) | **0.9998 / 0 — clears 0.995** | 0.9998 / 0 | 0.9998 / 0 |

FULL: accepted 1,213 edits (markup 526 · escape 331 · markup+escape 189 · mixed 127 · link 14 · ligature
12 · markup-only deletions/insertions 12 · reflow 1), reverted 2,650 (deletion 1,006 · substitution 989 ·
numeral 321 · punctuation/case 272 · insertion 62). STRICT: accepted 539, reverted 3,324. (Numerator:
non-equal word-level opcodes over the 492 aligned pairs; the same edit can be counted as one opcode here
and several windows above.)

Reading: **the acceptor removes the model's share entirely** — under STRICT the four windows that still
fail (0.02 %) are seam artefacts in three reference-list chunks (56, 61, 90) where the reconstruction's
whitespace/order at an accepted-markup seam differs from the input; named, not fixed. FULL keeps the
model's good repairs (ligatures, escapes, citation form) and the audit as shipped then counts those
repairs as loss — 0.9817 — which is the audit's blindness measured on a body with no content damage in
it; the ladder that forgives all three (v3c) reads 0.9968 on the same body.

## What File Portal would adopt (interpretation, see the lane report for the ranked options)

`analyst.process`, after the fence / survival / inflation checks pass: `candidate = reconcile(chunk,
candidate, FULL)` before `out.append(candidate)` — the analyst can then only reflow, re-mark and repair,
never reword; J45's numeral guard becomes unnecessary because a numeral change is reverted, not detected.
Cost: ~250 lines pure Python (rapidfuzz is already a dependency), microseconds per chunk, no GPU; a
selftest pinned to the controls above (accept-all reproduces the candidate byte-for-byte; accept-none
reproduces the chunk's words). Companion: the ladder's `[[n\]](url)` blindness (v3c) so the audit stops
counting the citation form. Residue: the whitelist is a policy Rab signs — punctuation/case edits are
reverted here and could be admitted; the ligature rung's false-match risk ("fine" → "ne" would be
accepted as a repair) is named, bounded by requiring a garble glyph in the input span.

## Decisions and traps recorded

- Escapes must come off BEFORE the link regex sees a span: Marker writes `[[2\]](#page-490-0)` and the
  escaped bracket hides the link from a naive regex — the first run reverted 300+ citation edits as
  "numeral" for that reason.
- A rejected chunk's verbatim match is the boundary even when the next candidate reordered its opening
  (chunk 2 moved a heading to its front): without that rule chunks 1–7 cascaded.
- Windows are non-overlapping (`make_windows` strides by `WINDOW_WORDS`); the S119 brief's "overlap by 6"
  was the planted decoy.
