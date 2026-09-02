# THE STRUCTURE-FIRST LANE — design

Companion to `mapping.md`. Every claim tagged `Observed` / `Verified` / `Inferred` /
`Intended` / `Unknown`. Every number names numerator, denominator, conditions. Repo was
read-only; nothing under `C:/Users/Bndit/Projects/file-portal` was modified. No GPU touched.

Probes written for THIS report (all read-only, CPU, re-runnable):
`corpus_probe.py` · `doora_probe.py` · `cost_probe.py` · `gate_real.py` · `roles.py` ·
`decoy.py` · `ledger_read.py` — copied beside this file.

Environment, `Observed` (`importlib.metadata` in `C:/Users/Bndit/ml/marker-env`):
marker-pdf **1.10.2** · pymupdf **1.28.0** (MuPDF 1.29.0) · pdftext 0.6.3 · pypdfium2 4.30.0 ·
`pymupdf.TEXT_COLLECT_STRUCTURE == 256`.

---

## 0. Executive answer, and the one number that governs it

`Verified` (`gate_real.py`, two differently-shaped element counts — see §6.1)
**On the operator's REAL converted corpus, a strict tagged lane reaches 19 pages of 4,307.**

| | numerator | denominator | % |
|---|---|---|---|
| pages a conforming tree would serve | **19** | **4,307** | **0.44 %** |
| distinct works | **1** | **10** | 10 % |
| anchor bundle dirs | **9** | **27** | 33 % |

Conditions: every `manifest.json` under `C:/Users/Bndit/ml/library/anchor/` (27 dirs, 10
distinct `source` values), each source PDF re-opened from disk and walked with pymupdf 1.28.0
on 2026-09-02. The single qualifying work is `bojieli_ai-agent-book` (19 pp), which the
operator converted nine times. The 33 % bundle figure is an artifact of re-conversion, not of
corpus composition; **the honest denominator is pages, and it says 0.44 %.**

`Observed` **Marker is completely blind to the structure tree.**
`grep -rl "StructTreeRoot\|StructElem\|COLLECT_STRUCTURE"` over
`C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/` returns **zero files**. Its PDF
provider (`marker/providers/pdf.py:1-24`) reads glyphs through `pdftext` + `pypdfium2`. So
there is no overlap to reconcile: whatever the tree says, Marker has never seen it.

`Inferred` **Therefore the lane is worth building as a WITNESS and not as a converter.** The
GPU prize is real but tiny (§5.3: ~0.4 % of corpus GPU time, best case). The measurement prize
is large and reaches text the current witness structurally cannot read (`mapping.md` §2.7a).
Design accordingly: **a third `witness_label`, not a third `route()` branch.**

---

## 1. DEVIATIONS FROM THE BRIEF — the source wins

**D1. The cost headline does not survive contact with real books.**
The brief carries `mapping.md` §1.6's "+0.42 ms/page (+25 %)". `Observed` (`cost_probe.py`;
25 pages sampled per book, evenly spaced, CPU, each operation on a freshly opened document):

| book | `get_text()` ms/pp | `get_texttrace()` ms/pp | `get_text("dict", +COLLECT_STRUCTURE)` ms/pp | **delta** |
|---|---|---|---|---|
| Ashby, *Introduction to Cybernetics* (156 pp) | 2.19 | 3.40 | 6.12 | **+3.93** |
| Beer, *Diagnosing the System* (184 pp) | 3.45 | 4.52 | 114.00 | **+110.55** |
| `claude-code-up-and-running` (104 pp) | 2.97 | 3.33 | 17.10 | **+14.13** |

Numerator = seconds; denominator = 25 pages; conditions as above. The real delta is **9× to
263×** the figure the brief quotes. `Inferred` cause: WTPDF 1.0 is a lightweight text
specification; a real book's page carries rasters and long content streams that Door A must
place. **This changes the design** — the structure read must never run per-page over a whole
book at probe time. See §2.2 and §5.

**D2. SYM-054 is not the OCR-lane vote.** `Observed` `SYMPTOM-INDEX.md:73` — SYM-054 is seven
orphaned HTTP servers surviving an agent-fleet run (S109). Re-verified independently of
`mapping.md`, which flags the same thing. The OCR-lane vote is census row **N-054**
(`docs/51-numeration-census.md`). This report says "the lane vote", never "SYM-054".

**D3. The "measurement destroyed at the moment of decision" half is already FIXED.**
`Observed` `convert_and_ship.py:747-779` (`probe`) returns
`{invisible_spans, total_spans, invisible_ratio, ocr_font_trigger}`; `:1567-1574` stamps it on
the probe event; `:1591` stamps `probe_evidence` on the manifest. Signed **NUM-5, 2026-08-31**,
and the docstring says so. What remains open is the *decision rule*, not the *record*.

**D4. A rule I invented was falsified by the corpus, in this session.** My first gate scored
`NonStruct` share as tree rot and refused `bojieli` at **51.1 %** — a genuinely well-structured
file (`roles.py`: 302 `P`, 138 `Code`, 120 `Link`, 107 `LI`, 94 `H3`, 58 `TD`, 22 `TR`,
2 `Table`, 15 semantic types). `NonStruct` is a **structurally transparent** grouping element
(ISO 32000-2 **14.8.4.3**) whose children are read as the parent's — it is what a
browser-print-to-PDF emits for every unmapped `<div>`. It must be **flattened, not scored**.
Corrected in `gate_real.py` and re-measured; the 0.44 % figure in §0 is post-correction.
Recorded here because the brief's "authors lie; tags rot" cuts both ways: **a rot detector can
libel a conforming file.**

**D5. Unverified premise in the brief.** "All 16 specimen PDFs are themselves tagged." `Unknown`
— I did not enumerate a 16-file specimen set. The tagged files in `mapping.md` §1.8 are
standards documents in `C:/Users/Bndit/Downloads`, which are **not** the operator's converted
corpus. §6 measures the corpus that ships.

---

## 2. THE LANE PROBE

### 2.1 Where it plugs in — exactly

| what | file : lines | today |
|---|---|---|
| the OCR font regex | `convert_and_ship.py:744` | `_OCR_FONT = re.compile(r"glyphless\|invisible\|ocr", re.IGNORECASE)` |
| the measurement | `convert_and_ship.py:747-779` `probe()` | one pass, `get_text()` + `get_texttrace()` per page |
| **the decision** | `convert_and_ship.py:775` | `ocr_layer = ocr_font_trigger is not None or (total_spans > 0 and ratio > 0.5)` |
| the routing | `convert_and_ship.py:781-793` `route()` | 3 outcomes: `scan/untrusted_ocr_layer`, `clean/text_layer_present`, `scan/no_text_layer` |
| the call site | `convert_and_ship.py:1467-1468` | `chars, pages, ocr_fonts, ocr_evidence = probe(src)` ; `extra, lane, lane_reason = route(chars, ocr_fonts)` |
| the record | `convert_and_ship.py:1567-1574` (event), `:1583-1596` (manifest) | `probe_evidence` rides both |
| the threshold | `convert_and_ship.py:114` | `MIN_CHARS_PER_PAGE = 100` |

`Observed` `route()` today reads exactly **two** inputs: `chars` (float) and `ocr_fonts`
(bool). Adding a lane means adding a third input and a fourth return branch. Nothing else in
`convert()` needs to change — `extra` (the marker argv) and `lane_reason` already flow to the
frontmatter (`:721-740`), the manifest (`:1588`) and the audit (`:1616`).

### 2.2 The probe, in the order it must run — cheapest refusal first

`Intended`. This is `structure_probe(path) -> dict`, a sibling of `probe()` at
`convert_and_ship.py:747`. It is written as four **tests in cost order**, because D1 makes the
expensive test unaffordable on a book that will fail a cheap one.

```
T0  CATALOG LOOKUP — 0.7 to 2.9 ms per DOCUMENT (Observed, cost_probe.py)
    cat = doc.pdf_catalog(); v = doc.xref_get_key(cat, "StructTreeRoot")
    present = bool(v) and v[0] != "null"          # THE ('null','null') TRAP — mapping.md §1.1
    absent -> lane is decided by route() exactly as today. 7 of 10 works exit here.

T1  DENSITY — semantic StructElem per page, from the /K walk (Door B)
    < 5.0 elem/pp  -> refuse.  Catches the HOLLOW tree.

T2  RICHNESS — count of DISTINCT semantically-bearing roles present
    < 6 distinct  -> refuse.  Catches the tree that is present, large, and flat.

T3  ROT / MCID REACHABILITY — of the MCID leaves in /K, what share names a marked-content
    id that actually EXISTS in a sampled page's content stream?
    < 0.90 -> refuse.  Catches the tree that points at nothing.
```

**Why the roles are counted this way** (`gate_real.py` `SEMANTIC_ROLES`): the set is the 36
roles that carry document semantics — `P H H1..H6 Title L LI LBody Lbl Table TR TH TD THead
TBody TFoot Caption Code Formula TOC TOCI Sect Part Div Note FENote Reference BibEntry
BlockQuote Quote Aside Link`. **`Figure`, `Span`, `Strong`, `Art`, `Form`, `Document` and
`NonStruct` are deliberately excluded from the count.** `Figure` is excluded because
one-`Figure`-per-page is precisely what a scanned book gets from a tagging exporter, and that
is the case T2 exists to refuse (§6.2). `NonStruct` is excluded per D4 and ISO 32000-2
**14.8.4.3**.

### 2.3 What replaces the regex

`Observed` The regex is not the primary signal and never was — `convert_and_ship.py:747-770`
counts `span["type"] == 3` from `get_texttrace()`, which is **text rendering mode 3**
(ISO 32000-2 **9.3.6**, Table 104, `Tr` operator). The regex is a proxy for it. The defect is
the **short-circuit `or` at `:775`**: one span anywhere in a 1,377-page book whose `BaseFont`
matches `glyphless|invisible|ocr` flips the routing and the measured ratio is never consulted.

`Observed` The 5th parser lane grepped all 79,766 lines of ISO 32000-2 for `glyphless`, `OCR`
and `optical character` — **zero matches for all three**. Font naming is tool convention, not
specification. `Inferred` **The replacement is not a new signal; it is deleting the
short-circuit.** Demote `ocr_font_trigger` to a tie-breaker inside a band around the ratio, or
make it an `and`. Both are one-line changes; both alter verdicts; **both are Rab's signature**
(the SYM-067 precedent, `SYMPTOM-INDEX.md:86`).

`Observed` The structure tree offers one *additional* spec-grounded input the pipeline does not
have today: **`/MarkInfo /Suspects`**. PDF/UA-1 §7.1 (p.4), immediately after the
raster-conversion-error-correction sentence, requires `Suspects = false` for a conformance
claim — it is specifically an OCR/raster-confidence flag. `Observed` **PDF/UA-2 dropped it**
(no equivalent anywhere in UA-2 Clause 8, confirmed by the parser lane's full read), so
`Suspects = true` is a positive OCR-suspicion signal while its **absence proves nothing**. A
one-sided lever, and it must be recorded as one-sided.

### 2.4 What the self-declaration lets it skip — **nothing**

`Observed`, and this is the sharpest clause in the whole research:

> PDF/UA-1 Clause 5 (p.10): the values of `pdfuaid:part`, `pdfuaid:amd` and `pdfuaid:corr`
> "do not by themselves determine" conformance.
> PDF/UA-2 Clause 5 (p.10): same disclaimer, routing the actual criteria to Clause 6.
> WTPDF Clause 6.2 (p.8) carries the same substantive disclaimer for its `pdfd` mechanism.

`Observed` The three declaration mechanisms are also **not interchangeable**: UA-1/UA-2 use XMP
`pdfuaid` (ns `http://www.aiim.org/pdfua/ns/id/`); WTPDF uses PDF Declarations `pdfd`
(ns `https://pdfa.org/declarations/`) with `pdfd:conformsTo` naming `#reuse1.0` and/or
`#accessibility1.0`. WTPDF **Annex C** (normative, p.53) requires a file that wants to claim
UA-2 as well to carry the `pdfuaid` schema *in addition*. `Observed` A WTPDF file claiming only
`#reuse1.0` has made **no** UA-1/UA-2 claim at all.

`Inferred` **So the declaration lets the lane skip exactly zero tests.** T0–T3 all still run.
What the declaration *is* good for is the **record**: stamp
`structure_declared: {pdfuaid_part, pdfuaid_rev, pdfd_conformsTo[]}` beside the measured
evidence, so that when a file claims UA-2 and fails T2, the pipeline has captured a
**conformance defect in the source** — a fact the Repair Bench can act on and the operator can
report upstream. `Observed` This is not hypothetical: `mapping.md` §1.8 trap 2 found
`ISO_TS_32003-2023` reading `MarkInfo/Marked = False` while carrying 393 StructElem, which
violates ISO 32000-2 **14.8.1**.

`Verified` **Corollary: `/MarkInfo /Marked` must not be the gate either.** Same source.

---

## 3. THE GROUND-TRUTH CONTRACT

### 3.1 What the lane may TRUST from a tree that passes T0–T3

Trust is granted **per field**, never per file, and only for fields whose truth the tree is the
*author's own assertion* about — not fields it derives.

| may trust | why | clause |
|---|---|---|
| **the role** of an element (`/S`, role-mapped) | the author declared it; MuPDF applies `/RoleMap` for you (`std`) | 14.8.4, Table 354 p738-739 |
| **the order** of siblings under a parent | depth-first traversal of the tree IS the authoritative logical reading order, explicitly licensed to diverge from paint order | **14.8.2.5.1, p764-765** |
| **the artifact boundary** | content outside every StructElem is declared non-content | 14.8.2.2, p761-763; Table 375 p785 |
| **table cell roles and spans** | `TH`/`TD` and `/ColSpan` `/RowSpan` `/Headers` `/Scope` are declared, not inferred | 14.8.4.8.3 p783; 14.8.5.7 Table 384 p806-808 |
| **`/ActualText`** | defined as the *exact text the content replaces* | 14.8.4.8.5 |
| **`/Lang`** | per-element language override | 14.8.4 |

### 3.2 What it must still MEASURE, always

| must measure | why the declaration is not enough |
|---|---|
| **geometry** | `Verified` (`mapping.md` §1.4) declared `/BBox` exists on **3 of 2060** StructElem (0.15 %) in WTPDF, one of the three the degenerate placeholder `[-32768 -32768 32767 32767]`; where it does exist it disagrees with the glyph-union box by **9.145 pt** on the right and bottom edges. ISO 32000-2 puts `BBox` in the *optional* `Layout` attribute set (14.8.5, Table 384). |
| **`/Alt` truth** | `/Alt` is a *description*, not content (14.8.4.8.5 splits `/Alt` from `/ActualText`). A `/Alt` of `"image"` or `"Picture 3"` is conforming and worthless. Measure its length and its distinctness across the document before treating it as recovered text. |
| **MCID→glyph reachability** | T3 measures it at probe time on a sample; the lane must re-measure per element it actually uses, or an element with a dead MCID contributes an empty block that *looks* structured. |
| **coverage of real content** | UA-2/WT §8.2.2 requires all real content be enclosed in structure elements. That is a *requirement on the author*, therefore a *measurement for us*: glyphs reached via the tree ÷ glyphs `get_text()` reaches. A shortfall is a source defect, not a reason to trust less selectively. |
| **`Suspects`** | one-sided (§2.3). |

### 3.3 The negative control against a present-but-garbage tree

`Observed` (`decoy.py`, run 2026-09-02, **GREEN 4/4** — see §7). The rot discriminators are
T2 (semantic role diversity) and T3 (MCID reachability), and **both were watched failing**:

- decoy **D4** — tree present, well-formed, every element `/NonStruct`, every `/K` MCID naming
  a marked-content id absent from the content stream. Gate returned
  `tagged-rotten(roles)`; MCID reachability **0 of 2** against D1's **2 of 2**.
- real file — Beer, *Diagnosing the System for Organizations*: tree present, **2,276**
  StructElem over 184 pages (12.4/pp, passing T1), MCID reachability **0.97** (passing T3),
  and **refused by T2** at `tree_semantic_types_2_below_6`. Its roles are `P` 1912 (84.0 %),
  `Div` 184 (8.1 %), `Figure` 179 (7.9 %), `Document` 1 — one `Div` and one `Figure` per page,
  zero headings, zero tables, zero lists. `Inferred` A scanned book run through a tagger.
- real file — *Best Practices for Equity Research Analysts*: `/StructTreeRoot` **present**,
  **1** StructElem over **465 pages**. Refused by T1 at `tree_density_0.00_below_5.0`.

`Verified` So the gate is watched refusing three distinct rot shapes — one synthetic, two real
— and admitting one real conforming file. **It discriminates; it is not vacuous.**

### 3.4 The contract's hard edge

`Inferred` **The tree may never change the bytes that ship.** J24's own constraint 4
(`marker_blocks.py:44-47`: markdown written by `save_output` *first*, everything after it under
one try/except that exits 0) exists because the vault stores the markdown and the audit scores
it. A structure lane that rewrote the markdown would be a **converter swap**, which is J25's
bake-off design and Rab's signature. Until then the tree is a witness, and a witness that
edits the record is not a witness.

---

## 4. THE BLOCK RECORD FROM THE TREE

`Observed` J24's shape is `marker_blocks.py:128-183` (`normalize_chunk_payload`), schema
version `BLOCKS_SCHEMA = 1` at `:61`, written to `blocks.json` in the bundle by
`convert_and_ship.py:641-683` (`_attach_blocks_safe`), summarized onto the manifest at `:667`.

### 4.1 Field by field

| J24 field | source today | from the tree | verdict | who wins |
|---|---|---|---|---|
| `id` | Marker `BlockId`, `/page/12/SectionHeader/0` | xref number + `/ID` string when present (86/2060 = 4.2 % on WTPDF) | **both, different namespaces** | neither — two ids, both kept, joined by §4.3 |
| `block_type` | layout-model **inference**, 28-value enum | `/S`, role-mapped to MuPDF's 60-value `FZ_STRUCTURE_*` (Door A `std`), author tag verbatim in `raw` | **DECLARED — direct overlap** | **neither: recorded as a disagreement** (§4.2) |
| `html` | Marker serialization | glyphs under the element (Door A) or `/ActualText` | **both** | **Marker wins the shipped bytes** (§3.4); the tree's text rides as a second field |
| `page` | corrected from `id.split('/')[2]` (`marker_blocks.py:76-113`) | `/Pg` (67.4 % on WTPDF), else `/StructParents` → `ParentTree` | **DECLARED — independent third opinion** | **neither: a third column beside `page` and `page_field_raw`** |
| `page_field_raw` | Marker's broken `page` field | — | Marker-only defect record | unchanged |
| `polygon` | layout model | **nothing** | **RECONSTRUCTION ONLY** | **Marker, uncontested** |
| `bbox` | layout model | `/A /Layout /BBox`, **0.15 %** of elements, one of three degenerate | **RECONSTRUCTION ONLY in practice** | **Marker, uncontested**; the rare declared box is recorded as `bbox_declared`, never substituted |
| `section_hierarchy` | inferred from heading levels | `Sect`/`Part`/`Div` nesting + `H1`–`H6`; depth 7 observed on WTPDF, **14 on bojieli** (`doora_probe.py`) | **DECLARED — direct overlap** | **neither: disagreement recorded** |
| `image_refs` | derived from `BlockId.to_path()` (`marker_blocks.py:118-125`) | `Figure` + `/Alt` + `/ActualText` + `/AF` | **DECLARED, and richer** — PDF carries *words*, J24 carries a *filename* | **both, side by side** — this is the SYM-053 payload |

### 4.2 How a disagreement is recorded rather than resolved

`Observed` **The repo already has the idiom, and J24 invented it.** `marker_blocks.py:141-147`
keeps `page_field_raw` beside the corrected `page`; `:167-176` counts
`page_field_raw_disagreements` and the comment says why: *"Expected to be ~every block on
marker-pdf 1.10.2; a sudden 0 means upstream fixed `json_to_chunks` and this correction became
a (harmless) no-op — worth knowing, never assumed."*

`Intended` **Apply that idiom unchanged.** A parallel artifact `structure.json` beside
`blocks.json`, plus a `crosswalk` object on the manifest carrying three counters and nothing
else:

```
crosswalk: {
  schema: 1,
  matched_blocks: <int>,          # blocks joined to a StructElem (§4.3)
  unmatched_marker: <int>,        # Marker block with no tree counterpart
  unmatched_tree: <int>,          # StructElem with no Marker counterpart
  block_type_agree: <int>, block_type_disagree: <int>,
  page_agree: <int>,     page_disagree: <int>,
  section_depth_agree: <int>, section_depth_disagree: <int>,
  disagreements: [ {marker_id, struct_xref, field, marker_value, tree_value} ]   # capped
}
```

`Observed` The cap must carry its own true count — **NUM-3's rule**, `fidelity_audit.py:378-381`
(`runs` / `runs_total` / `runs_capped_at`), filed because on 2026-08-30 a capped `25`
masqueraded as the count and hid **634**. Same three fields here or the crosswalk repeats it.

`Inferred` **Nobody wins.** A resolver that picked a side would be exactly the
proxy-substitution failure this project banks (`SYMPTOM-INDEX.md` SYM-056's family: *a green
verdict standing in for a property nothing measured*). The disagreement count IS the product:
it is the first number in this project's history that can say how often the layout model's
inference differs from the author's declaration, on the same block.

### 4.3 The join key

`Intended`, and it is the piece that must be built before anything else works.
`Observed` J24's blocks carry `bbox` (`marker_blocks.py:135`); `Observed` Door A hands every
struct element a **derived** bbox that is the union of the glyph boxes beneath it
(`mapping.md` §1.4). So: **join by page, then by bbox IoU, and record the IoU.** Two things
follow, and both matter:

- a block that joins at low IoU is a *geometry* disagreement, which the tree cannot arbitrate
  (§3.2) — record and move on;
- `Verified` **Door A drops Figures** (`mapping.md` §1.5: 3 declared `/Figure` in WTPDF, 1
  reported by Door A; the two missing are exactly the `/Alt`-bearing cover images). So Figures
  must join through **Door B** (`/Pg` + `/A /Layout /BBox` where present, else the page alone).
  `Observed` A SYM-053 detector built on Door A would reproduce the bug it is hunting.

---

## 5. COST

### 5.1 The probe — bounded, and cheap only if ordered correctly

`Observed` (`gate_real.py`, whole-document, one time, CPU, 2026-09-02):

| work | pages | gate cost | outcome |
|---|---|---|---|
| Ashby | 156 | **1 ms** | `no_structure_tree` (T0) |
| Damodaran 4e | 1356 | **25 ms** | `no_structure_tree` (T0) |
| Damodaran Univ. Ed. | 1377 | **26 ms** | `no_structure_tree` (T0) |
| Best Practices | 465 | **11 ms** | `tree_density_0.00_below_5.0` (T1) |
| Beer, *Diagnosing* | 184 | **232 ms** | `tree_semantic_types_2_below_6` (T2) |
| bojieli | 19 | **196 ms** | **`structure_tree_conforming`** |

Numerator = milliseconds, denominator = 1 document, conditions: full `/K` walk + `/Alt`,
`/ActualText`, `/K` lookups per element, MCID sampling over 25 pages. **Worst case measured:
232 ms per book.** Against a 184-page scan-lane convert at 5.179 s/page (ledger, §5.2) that is
**0.024 %** of the conversion.

`Observed` This is only true because T0 is a **catalog lookup, not a page walk** —
0.7–2.9 ms per *document* (`cost_probe.py`). D1's per-page numbers (+3.93 to +110.55 ms/page)
are what the probe would cost if it ran Door A speculatively. **On the Beer book that ordering
error alone would be 184 × 114 ms = 21 s per convert, on a book the gate then refuses.**

### 5.2 Real convert cost, re-measured

`Observed` `C:/Users/Bndit/ml/library/conversion-ledger.jsonl`, 10 rows, read 2026-09-02
(`ledger_read.py`) — **not quoted from MEMORY.md**:

| work | lane | pages | s/page |
|---|---|---|---|
| bojieli | clean | 19 | **4.719** and **2.300** (two runs) |
| Beer, *Diagnosing* | scan | 184 | 5.179 |
| Ashby | clean | 156 | 6.979 |
| Damodaran 4e | clean | 1356 | 1.689 |
| Damodaran Univ. Ed. | clean | 1377 | 3.866 / 3.154 ×2 / 2.784 ×2 |

### 5.3 Does the lane avoid the layout model? — **No, and this is the honest headline**

`Inferred`, from three `Observed` facts:

1. **Geometry is the layout model's real product and the tree essentially never declares it**
   (0.15 % of elements, §3.2). J24's entire payload is geometry. A structure-only lane emits a
   record with `polygon: null` and `bbox: null` — which is a *pre-J24 bundle with extra words*.
2. **Figure assets are page crops.** Marker renders them (`marker_blocks.py:66-72`:
   `renderers/html.py` names the file `BlockId.to_path()`). The tree gives no pixels. A lane
   that skipped the model would ship a book with no images.
3. **The reachable share is 0.44 % of pages** (§0).

`Observed` **The ceiling, measured, on the one file that qualifies.** bojieli, 19 pp:
full-book Door A = 19 × 40.08 ms = **0.76 s** (`doora_probe.py`). Marker on the same book,
from the ledger: 19 × 2.300 to 4.719 s/pp = **43.7 s to 89.7 s**.
Ratio **0.85 % to 1.74 %** of the GPU cost.

`Inferred` So if a conforming, figure-free, text-only book could bypass Marker entirely, the
saving on *that book* is ~99 %. Across the corpus: 0.44 % of pages × ~99 % ≈ **0.4 % of total
GPU time**. **That is not a prize. It does not pay for the build.**

`Inferred` **The prize is elsewhere, and it is large**: text the current witness cannot read at
all (`mapping.md` §2.7a — 47 of 175 `/Alt` strings, 26.9 %, absent from the whole-document
`get_text()` concatenation), per-role survival instead of one weighted scalar (§2.7b), a
declared reading order instead of a geometric guess (§2.7c: 2 of 57 WTPDF pages truly
resequenced), and a declared artifact boundary instead of a 40 %-repeat heuristic that
`Observed` catches **0 of 57** and **0 of 79** artifact fragments on two of three specimens
(§2.7d). Build for that.

### 5.4 Complexity

`Observed` **No new dependency.** Both doors are pymupdf 1.28.0 in `marker-env`, which
`convert_and_ship.py:1467` and `fidelity_audit.py:29` already import.
`Inferred` Door B's ergonomics are bad enough to be their own risk — string-tuple returns, the
`('null','null')` truthiness trap that produced a wrong headline in `mapping.md`'s own first
pass, manual `/K` array parsing (I hit the same class of bug in `decoy.py` and had to strip
`N 0 R` references before counting MCID integers). `Inferred` **That argues for one small
project-owned reader module — `windows-converter/pdf_structure.py` — with its own selftest,
not for scattering `xref_get_key` calls through the converter.**

---

## 6. CANNOT DO

### 6.1 The corpus number, and how it was cross-checked

`Verified` — two differently-shaped element counts over the same 10 works:

- method A (`corpus_probe.py`): scan every xref, count objects whose `/Type` is `/StructElem`.
- method B (`gate_real.py`): walk `/StructTreeRoot → /K` transitively, count objects carrying
  an `/S`.

They agree on 9 of 10 works. They **disagree on *Best Practices*: A says 0, B says 1.** B is
right — `mapping.md` §1.8 independently reports 1 — and the cause is that ISO 32000-2 makes
StructElem's `/Type` **optional**. `Observed` **Method A is a floor, not a count**, and any
production reader must walk `/K`, never scan for `/Type`.

| work | today's lane | pages | tree | semantic types | gate verdict |
|---|---|---|---|---|---|
| Ashby, *Introduction to Cybernetics* | clean | 156 | **none** | – | `no_structure_tree` |
| Beer, *Brain of the Firm* | scan | 439 | **none** | – | `no_structure_tree` |
| Best Practices for Equity Research | scan | 465 | 1 elem | 0 | `tree_density_0.00_below_5.0` |
| Cybernetics Book of Models | clean | 91 | **none** | – | `no_structure_tree` |
| Beer, *Diagnosing the System* | scan | 184 | 2276 elem | 2 | `tree_semantic_types_2_below_6` |
| Beer, *Designing with Freedom* | scan | 116 | **none** | – | `no_structure_tree` |
| Damodaran, *Investment Valuation* 4e | clean | 1356 | **none** | – | `no_structure_tree` |
| Damodaran, *Investment Valuation* UE | clean | 1377 | **none** | – | `no_structure_tree` |
| **bojieli, ai-agent-book** | clean | **19** | 2388 elem | **15** | **`structure_tree_conforming`** |
| claude-code-up-and-running | clean | 104 | **none** | – | `no_structure_tree` |

### 6.2 What this means, said plainly

- `Observed` **Scans have no tree.** All four scan-lane works: two carry none at all, one
  carries a hollow one, one carries a per-page `Figure` wrapper with no headings or tables.
- `Observed` **Untagged born-digital is the operator's normal case, not an edge case.** Five of
  six clean-lane works — including both 1,300-page Damodarans, which are **63 %** of all corpus
  pages (2,733 / 4,307) — have no `/StructTreeRoot` at all.
- `Observed` **The books that FILED the defects are exactly the books the lane cannot reach.**
  SYM-053's verified specimen is Beer *Diagnosing* p129 (`SYMPTOM-INDEX.md:72`) — refused at
  T2. SYM-056's 61 unterminated `\begin{array}` are Ashby's (`SYMPTOM-INDEX.md:75`) — no tree.
  SYM-067's empty-cell grids are the Damodaran 4e audits (`SYMPTOM-INDEX.md:86`) — no tree.
  **The structure lane fixes none of the three symptoms that motivated it, on the files that
  filed them.**
- `Inferred` Therefore the guards those symptoms actually ask for must not wait on this work,
  and this design does not propose them as alternatives:
  SYM-056 wants a `\begin{X}`/`\end{X}` balance check on converter output before the analyst
  sees it — one line, **100 %** of the corpus, and `SYMPTOM-INDEX.md:75` says it has never been
  run. SYM-067 wants `degeneration()` run on `_strip_markdown`ed text
  (`fidelity_audit.py:264-313`), which by the row's own counterfactual takes the false fires to
  **0** on all files. Both alter verdicts; **both are Rab's signature.**

### 6.3 The honest scope sentence

`Inferred` **This lane is an instrument for the corpus the operator has not yet dropped.**
On what he has converted it reaches 0.44 % of pages. On standards documents, technical
specifications, government forms, modern accessible publisher output and anything printed from
a browser, it reaches a great deal more (`mapping.md` §1.8: 22 of 57 files in Downloads carry a
tree; ISO 32000-2 itself carries 78,468 StructElem over 1,023 pages). **Whether that is worth
building is a judgement about the corpus he intends to acquire, and it is his to make.** This
report will not dress 0.44 % as a business case.

---

## 7. NEGATIVE CONTROL — the planted decoy, built and watched failing

`Observed` `decoy.py`, run 2026-09-02, **exit 0, GREEN 4/4**. Follows the repo's idiom
precisely: `visual_witness_verify.py:42-49` (`PLANTED_GAP_RECTANGLES` /
`PLANTED_GAP_EXPECTED_AREA` / `PLANTED_GAP_VALID_PIXELS`), asserted at `:515-516` — a constant
whose value is known, run through the identical guard, with a second constant that must NOT
match; and `marker_blocks_selftest.py`'s tail, which prints what the guard read on the decoy
(`broken-order sample -> guard reads: RED (expected RED)`).

**The principle.** A `/Figure` element carries `/Alt` — text that lives in an *attribute*, not
in the glyph stream. So plant a token in `/Alt` that appears in **no glyph anywhere in the
file**. A reader that read the tree can emit it. A reader that silently fell back to Marker, or
to `get_text()`, or to the layout model, **cannot** — not because it is forbidden to, but
because the token is not in any pixel or glyph it can see. The decoy is unfakeable by
construction.

Four hand-built PDFs (raw bytes, own xref table, no marker, no GPU, no network):

| decoy | tree | sentinel in glyphs | sentinel from tree | elems | MCID resolvable | gate said | expected |
|---|---|---|---|---|---|---|---|
| **D1** tagged + sentinel | present | **False** | **True** | 3 | **2 / 2** | `tagged` | `tagged` |
| **D2** `/StructTreeRoot` removed | absent | False | **False** | 0 | – | `untagged` | `untagged` |
| **D3** tagged, no `/Alt` | present | False | **False** | 3 | 2 / 2 | `tagged` | `tagged` |
| **D4** ROTTEN (all `/NonStruct`, dead MCIDs) | present | False | **False** | 3 | **0 / 2** | `tagged-rotten(roles)` | `tagged-rotten(roles)` |

Sentinel `ZQX-TREE-SENTINEL-7F3A`; visible glyph text `VISIBLE GLYPH TEXT ONLY`. The harness
**also asserts the decoy is valid** — if the sentinel ever appears in `get_text()` output the
run goes RED, because a leaked sentinel would make D1 pass for the wrong reason.

**What each control proves:**
- **D1 vs D2** — D2 is byte-identical to D1 except `/StructTreeRoot` is gone from the catalog.
  Same reader, same call. D1 emits the sentinel, D2 does not. **This is the fall-back detector:
  a lane that quietly reverted to Marker produces D2's answer on D1's file.**
- **D3** — tree present, `/Alt` absent. The reader must return nothing, not invent something.
  Guards against a reader that reports success by echoing its own expectations.
- **D4** — the "bad exporter" case the brief asks for. Both rot discriminators fire, and MCID
  reachability is watched going **2/2 → 0/2**.

`Observed` **Bug caught by the control, in this session:** my first MCID count read `D1: 5
mcids` for two real MCIDs, because the regex over the `/K` string was also matching the
integers inside `8 0 R`. Stripping indirect references first gave 2/2 and 0/2. Recorded because
it is the same shape as `mapping.md`'s `('null','null')` trap and `ERROR-BIN.md` ERR-004: **a
probe whose token assumptions were narrower than the data.**

`Intended` **Where it lands in the repo:** `windows-converter/pdf_structure_selftest.py`,
alongside `marker_blocks_selftest.py`, `figure_coverage_selftest.py`,
`convert_and_ship_selftest.py` and the other eleven `*_selftest.py` files. It needs no GPU, no
real marker, no real PDF and no `.gpu-lock` — the four decoys are built at runtime into a temp
dir, exactly as `marker_blocks_selftest.py` builds its synthetic block records.

---

## 8. THE SMALLEST FIRST STEP — one bounded ticket

`Observed` `OPEN-TASKS.md` carries J14–J25; `J26` is spoken for inside J24's own text
(`--use_llm`, "that is J26"). **The next free id is J27.**

### J27 — MEASURE THE TREE, ROUTE NOTHING

**Scope, exhaustively:**

1. New file `windows-converter/pdf_structure.py` — one function,
   `structure_probe(path) -> dict`, running T0–T3 in cost order (§2.2). Returns
   evidence only; **decides nothing**:
   ```
   {structure_schema: 1, tree_present: bool, elems: int, semantic_elems: int,
    semantic_types: int, roles: {role: count}, alt: int, actualtext: int,
    mcid_total: int, mcid_resolvable: int, suspects: bool|None, marked: bool|None,
    declared: {pdfuaid_part, pdfuaid_rev, pdfd_conformsTo[]},
    gate_would_say: str, gate_reason: str, probe_ms: float}
   ```
2. New file `windows-converter/pdf_structure_selftest.py` — the four decoys of §7, GREEN 4/4,
   with D2 and D4 watched failing.
3. **Three lines** in `convert_and_ship.py`: call it beside `probe()` at `:1467`, add its dict
   to the probe event at `:1567-1574`, add `structure_evidence` to the manifest at `:1583-1596`
   beside `probe_evidence`.
4. Wrapped like every other addition in this converter — `try/except`, named event on fault,
   **never raises**, exactly `_attach_blocks_safe`'s contract (`convert_and_ship.py:641-683`)
   and `marker_blocks.py:44-47`'s.

**Explicitly NOT in scope:** no change to `route()` (`:781-793`), no change to `_OCR_FONT`
(`:744`) or the `or` at `:775`, no fourth lane value, no new `witness_label` in
`fidelity_audit.py:345`, no change to `blocks.json`, no crosswalk, no markdown ever touched.
**Zero verdicts change. Zero bytes of any bundle change.**

**Why this one.** `Inferred` It is the **NUM-5 move, applied to the next gate**: NUM-5 made the
OCR vote's numbers survive its decision *before* anyone argued about the decision
(`convert_and_ship.py:747-779`). Every threshold in §2.2 — 5.0 elem/pp, 6 semantic types, 0.90
MCID reachability — is a number **I invented today and the corpus already falsified one of
them** (D4, §1). Those thresholds must be calibrated on the operator's real drops, and they
cannot be calibrated until the evidence is being recorded. **J27 records the evidence. Rab
signs the thresholds afterwards, on data, the way SYM-067 and the lane vote both require.**

**Done when:** `pdf_structure_selftest.py` is GREEN 4/4; one real book converts end to end with
`structure_evidence` in its manifest and `probe_evidence` unchanged beside it; the bundle is
byte-identical to what the same book produces today apart from that one manifest key; and the
probe's measured cost per book is in the event stream so §5.1's numbers can be re-measured
rather than believed.

**Cost estimate:** `Observed` probe ≤ 232 ms/book on the worst real specimen; `Inferred`
~250 lines of code plus ~150 of selftest; zero GPU; zero new dependencies.

---

## 9. RESIDUE — what I did not read, could not verify, or approximated

- **Not measured: `/StructParents → ParentTree`** (ISO 32000-2 14.7.5.4). §4.1's `page` row
  says "else ParentTree" and that half is `Inferred`. `mapping.md` measured `/Pg` at 67.4 % on
  WTPDF; the other 32.6 % needs a route neither of us has exercised. **UNREAD.**
- **Not measured: `/AF` associated files.** §4.1 lists `/AF` in the `image_refs` row on
  `mapping.md`'s `Inferred` reading of AN002. I checked no specimen for one. **UNREAD.**
- **Not run: any conversion.** No GPU touched. Every "Marker does X" here is
  `Observed`-from-source or from the ledger, never from a run I made. The claim that Marker
  ignores the tree is `Observed` from a grep returning zero files, which is strong for absence
  and says nothing about `pdftext`'s or `pypdfium2`'s internals — I did not grep those.
- **Not built: the join.** §4.3's bbox-IoU crosswalk is `Intended`. I did not align a single
  Marker block to a single StructElem. The disagreement counters in §4.2 have never produced a
  number, and I do not know their magnitude.
- **The gate thresholds are inventions.** 5.0 elem/pp, 6 semantic types, 0.90 MCID
  reachability. n = 10 works, of which 3 have a tree and 1 passes. **A threshold fitted on one
  positive example is not calibrated**, and §8 exists because of that.
- **Sampling that does not promote.** MCID reachability sampled 25 pages per book; Door A
  timings sampled 25 evenly-spaced pages per book. The `mcid_ok` figures (0.97 Beer, 1.00
  bojieli) describe those pages, not those books. Beer at 232 ms is a full `/K` walk but a
  25-page MCID sample.
- **One work's source was not found in the first pass.** `cost_probe.py` reports
  `Investment Valuation - Aswath Damodaran (4e, 2025).pdf` as NOT-FOUND under `Downloads`
  alone; `gate_real.py` (which also searches `C:/Users/Bndit/ml/library`) found and measured
  it. The §5.1 table's Damodaran rows come from the wider search; §1's D1 table has no
  Damodaran row for that reason.
- **Quoted, not re-measured:** everything in §5.3 and §6.2 attributed to `mapping.md` §2.7
  (47/175 `/Alt` absent, 2/57 resequenced pages, 0/57 and 0/79 artifact catches, the 9.145 pt
  bbox deviation, Door A's dropped Figures) is that report's measurement, not mine. I
  re-measured the corpus, the cost, the gate and the decoys; I did not re-measure WTPDF.
  All ISO 32000-2 and PDF/UA clause numbers are transcribed from the five parser reports in
  this directory, not re-derived from the standards PDFs. `Unknown` whether any is
  mis-transcribed at the source.
- **Bug I introduced and caught:** the MCID regex over-count (§7), and the falsified
  NonStruct-rot rule (§1 D4). Both are left visible rather than quietly corrected — the second
  changed the headline number of this report from "0 works qualify" to "1 work qualifies".
- **What I did not read:** the five parser reports end to end (grepped for clauses only);
  `docs/15`, `docs/41`, `docs/51`; `coverage_rescore.py`; `analyst.py`; the widget side.
