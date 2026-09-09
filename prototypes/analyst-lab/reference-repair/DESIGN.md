# `analyst-lab/reference-repair` — where the reference damage is born, and a repair (quarantined prototype)

*Built 2026-09-09 by Fable lane R1 of the S119 research fleet, beside `../edit-whitelist` (shares its
`common.py`). Read-only against the held DDIA bundle `fc1f068c3a8eeb63` and the source PDF; CPU only.
Every number is `Observed` from `repair.py` or the lane's probes unless tagged.*

## Ask A — decided by measurement

**The ligature damage is born in pdfium's char→Unicode fallback, which is pdftext's (Marker's) path;
MuPDF resolves the same glyphs correctly.**

- The PDF's subset fonts (Type1/CFF: MinionPro-It, MyriadPro-SemiboldCond, GuardianSans-*) place their
  ligature glyphs at codes 0x21–0x29 under OpenType glyph names — `/Encoding << /Differences [33 /f_l
  /f_k /f_f_i /f_t /T_h /f_f …] >>` (pymupdf `xref_get_key`, page 49 font `AAAAAT+MinionPro-It`) — and
  their ToUnicode CMaps carry NO entry for those codes (`bfchar` for 0x21–0x27 empty on every such font).
- pymupdf `page.get_text()` yields U+FB01 `ﬁ` / U+FB03 `ﬃ` for them (rawdict chars: `Diﬃcult`); pdfium's
  `FPDFText_GetUnicode` — the exact call in `pdftext/pdf/chars.py:18` — yields the raw code: `Di"cult`.
  Book-wide, matched glyph by glyph via bbox (224 ligature glyphs on 527 pages): MinionPro-It ﬁ→`'` ×57,
  ﬂ→`!` ×34, ﬀ→`&` ×29, ﬃ→`#` ×6, ﬄ→`)` ×5; MyriadPro-SemiboldCond ﬁ→`"` ×29, ﬂ→`#` ×27, ﬀ→`!` ×26,
  ﬄ→`$` ×4; GuardianSans ﬃ→`"`, ﬀ→`!`, ﬁ→`#`. `T_h` and `f_t` (no Unicode ligature code point) come
  out as `%` and `$` (`%ere` → There, `so\$ware` → software; markdownify escapes the `$`).
- pdftext's own `replace_ligatures` (`postprocessing.py`) maps only U+FB00–FB06 — it never sees these
  codes. Marker's `fix_text` (ftfy) does not touch them either. Marker's OCR-error model decides per PAGE
  and these pages read as good text. Marker 1.10.2 (`marker-pdf 1.10.2`, `pdftext 0.6.3`, `pypdfium2
  4.30.0`, marker-env) exposes no option that changes the char→Unicode mapping; `--force_ocr` is banned
  (docs/12) and would be the only Marker-native route.
- **The `!`-hyphen is a different animal:** `MinionPro-Regular` maps `/uni2010` at code 0x21 and its
  ToUnicode `bfrange <20> <26> <0020>` says code 0x21 IS U+0021 — the producer's error. BOTH extractors
  print `Chap!` + newline + `ter 4`. Marker's line joiner (`strip_trailing_hyphens`) looks for a hyphen,
  finds `!`, and keeps both halves; a link split over that line break becomes `[Chap](#page-138-0)! [ter
  4](#page-138-0)` — the "broken link syntax". Sidecar counts: 782 `x! y` joins, 138 broken links.
- **Escaped underscores/asterisks** are markdownify's defaults inside Marker's renderer
  (`escape_underscores=True`, `escape_asterisks=True`, `escape_dollars`; `renderers/markdown.py:287-289`):
  133 `\_`, 14 `\*`, 53 `\(` in the sidecar. Not damage — legal markdown the ladder mishandles (SYM-076).
- Sidecar reach: 73 in-word glyph garbles survive into Marker's body (`#` 28, `"` 15, `!` 13, `\$` 7,
  `'` 5, `&` 5; contractions excluded); the audit's ladder deletes the garble char and compares
  `dicult` against the model's `difficult`.

## The repair (`repair.py`)

Rules on Marker's body, gated by the PDF's own vocabulary (pymupdf text of all 673 pages, NFKC, casefold,
14,156 distinct words):

| rule | what | count on DDIA | audit alone (sidecar' vs shipped) |
|---|---|---|---|
| R-lig | garble glyph → the ONE ligature expansion that is a vocabulary word | 58 repaired · 1 ambiguous · 830 tries fell through the gate (real quotes before words) | 0.9727 / 48 |
| R-hyph | `x! y` → `xy` when in the vocabulary | 716 joined · 66 left (names, `corre! sponded`) | 0.9717 / 49 |
| R-link | `[A](u)! [b](u)` → `[Ab](u)` when the URLs are equal | 138 joined | 0.9713 / 55 |
| R-cite | `[[n\]](url)` → `[n](url)` | 1,396 — **NOT a default** | **0.9234 / 283 — worse** |
| all three defaults | | | **0.9726 / 50** (from 0.9718 / 49) |
| defaults + the acceptor's FULL body | | | 0.9814 / 28 |

Negative control: with an empty vocabulary the gated rules change nothing (`text unchanged = True`).

## What the numbers say

1. **Repairing the reference after the fact barely moves today's audit** (+0.0008): the model already
   repaired most garbles in its output, so the pairs matched by the repair were mostly failing for a
   second reason in the same window (a citation form, an escape); and a repair the model did NOT make —
   a rejected chunk ships verbatim with `#rst` — now mismatches the repaired `first` ("laid in the
   acclaimed first edition" is an open run). **The repair belongs BEFORE the analyst** (a pre-analyst
   pass on the Marker body, so the reference, the model's input and every rejected chunk carry it);
   this script can only approximate that with a body produced from the unrepaired input.
2. **A one-sided markup normalisation is a trap.** R-cite applied to the reference alone turns 1,396
   citations into the form the ladder strips, while the shipped body still carries Marker's form
   wherever the model left it (1,281 of 1,396) — 283 runs. The same rule applied to BOTH sides (ladder
   v3c in `../edit-whitelist/acceptor.py`) is what forgives the class.
3. **Upstream, the fix is one function**: pdftext could fall back from a missing ToUnicode entry to the
   glyph NAME (`f_i` → fi, the Adobe Glyph List rule MuPDF already applies) instead of the raw code — or
   File Portal can run this pass with the pymupdf witness it already builds (`fidelity_audit`'s witness
   is the same text). `Inferred` (falsifier: patch `pdftext/pdf/chars.py:18` to consult
   `FPDFText_GetFontInfo`'s glyph names and re-extract page 1 — `Diﬃcult` should appear).

Run: `python repair.py` (marker-env, from this directory). Writes `results_repair.json`.
