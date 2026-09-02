# Declared structure, mapped onto File Portal

Every claim is tagged `Observed` / `Verified` / `Inferred` / `Intended` / `Unknown`.
Every number names numerator, denominator, conditions.
Probe scripts are beside this file: `probe_a_api.py` … `probe_l_artifact.py`; the corpus
survey is `survey.tsv`. All probes are read-only; nothing under
`C:/Users/Bndit/Projects/file-portal` was modified.

---

## 0. Executive answer

`Observed` **pymupdf 1.28.0, already installed at `C:/Users/Bndit/ml/marker-env`, reads the
PDF structure tree — two independent ways, no new dependency.** One is a first-class
text-extraction mode that hands back the tree *with the glyphs and a bbox already attached*.
The other is raw object access for the attributes that mode drops (`/Alt`, `/ActualText`,
`/Headers`, `/Scope`, `/BBox`, `/Lang`).

`Observed` It costs **+0.42 ms/page** over the witness extraction the audit already runs.

`Observed` **But it is not free of catches, and two of them are load-bearing:**
1. The convenient mode is **lossy on image content** — it showed 1 of the 3 `/Figure`
   elements the file declares (WTPDF 1.0). The two it dropped are exactly the
   "asset exists, words are in the tag" case that SYM-053 is about.
2. **35 of 57 PDFs in `C:/Users/Bndit/Downloads` have no structure tree at all**, and every
   scanned book in the working corpus is among them. Two more have a *hollow* tree
   (1 and 17 elements across 465 and 613 pages) that a boolean "is it tagged?" gate would
   route into a lane with nothing in it.

`Inferred` So this is not a replacement for Marker. It is a **second witness on the ~39 % of
this corpus that is born-digital**, and it is strongest exactly where the current witness is
structurally blind: figure text, artifact/real-content separation, table cell roles, and
author-declared reading order.

---

## 1. THE EMPIRICAL QUESTION — measured

### 1.1 What pymupdf 1.28.0 exposes

`Observed` (`probe_a_api.py`, `probe_b_mupdf.py`)

`pymupdf.Document` has **no** `struct*` / `tag*` method. Searching the whole module namespace
for `struct|tag|mark|mcid|logic|role` returns only `markinfo` / `set_markinfo`,
`find_bookmark` / `make_bookmark`, and constants. **There is no `doc.get_structure_tree()`.**

The capability is delivered through two other doors:

**Door A — the text extractor.** `pymupdf.TEXT_COLLECT_STRUCTURE == 256`, which is MuPDF's
`FZ_STEXT_COLLECT_STRUCTURE`. Passed in `flags` to `page.get_text("dict"|"rawdict"|"xml")`, the
returned `blocks` list becomes a **nested tree**, and a new block type appears:

```python
FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE
page.get_text("dict", flags=FL)
# block type 0 = text, 1 = image, 2 = FZ_STEXT_BLOCK_STRUCT (new)
```

`Observed` A type-2 block carries exactly these keys, and no others:
`{"type": 2, "number", "bbox", "index", "raw", "std", "blocks"}` — where `raw` is the
author's tag name **verbatim** (`"P group big_"`, `"Author_"`, `"p"`) and `std` is MuPDF's
role-mapped normalization into its 60-value `FZ_STRUCTURE_*` enum
(`ANNOT ART ARTIFACT ASIDE BIBENTRY BLOCKQUOTE CAPTION CODE DIV DOCUMENT DOCUMENTFRAGMENT EM
FENOTE FIGURE FORM FORMULA H H1..H6 INDEX LABEL LINK LIST LISTBODY LISTITEM NONSTRUCT NOTE P
PART PRIVATE QUOTE RB REFERENCE RP RT RUBY SECT SPAN STRONG SUB TABLE TBODY TD TFOOT TH THEAD
TITLE TOC TOCI TR WARICHU WP WT`). `raw` → `std` **is the `/RoleMap` already applied**
(ISO 32000-2 Table 354, p738–739): this file's custom `Title`, `Author_`, `p` and
`P group big_` all normalize to `std = "P"`.

**Door B — raw object access.** `Document.pdf_catalog()`, `.xref_get_keys(x)`,
`.xref_get_key(x, k)`, `.xref_object(x)` walk `/StructTreeRoot → /K → StructElem` directly.
This is where `/Alt`, `/ActualText`, `/Lang`, `/A` (attribute objects), `/Pg`, `/ID` live —
**none of which Door A surfaces.**

> ⚠ `Observed` **`xref_get_key` returns `('null','null')` for an ABSENT key, and that tuple is
> truthy.** My first pass reported "2281 of 2281 elements carry `/Alt`". The true figure is
> 175 of 2060. Any code the project writes against this API must test `v[0] != 'null'`, not
> `if v:`. Filed here because it is exactly the shape of defect this project banks.

### 1.2 The specimen probe — WTPDF 1.0, 57 pages

`Observed` (`probe_c_dict.py`, `probe_d_walk.py`, `probe_f_fixed.py`)

| | value |
|---|---|
| `/MarkInfo` | `<</Marked true /Suspects false>>` |
| catalog `/StructTreeRoot` | `389 0 R` |
| root keys | `ClassMap, IDTree, K, ParentTree, ParentTreeNextKey, RoleMap, Type` |
| page 10 `/StructParents` | `10` (the `ParentTree` reverse-map key, ISO 32000-2 Table 359, p750) |
| StructElem via xref walk | **2060** (2281 objects reached; 221 carry no `/S`) |
| StructElem instances via Door A | **2112** over 57/57 pages, max nesting depth **7** |
| distinct `/S` types (xref) | **28** |
| distinct `raw` / `std` tags (Door A) | 27 / 23 |

`Inferred` The two counts differ (2060 vs 2112) because Door A materializes an element **once
per page it appears on** — `Document` is 1 object in the xref tree and 57 struct blocks in
Door A. Door A is page-scoped; the xref tree is document-scoped. Consequential for anyone
counting.

Element-type tally (numerator = instances; denominator = 2060 StructElem; conditions =
WTPDF 1.0, xref walk):

```
P 783 · Link 173 · Reference 162 · Span 123 · LI/Lbl/LBody 105 each · TH 86 · H5 64
TR 62 · TD 53 · TOCI 45 · H4 40 · H3 33 · H6 33 · L 26 · H2 13 · Code 11
Table 10 · Caption 10 · TOC 7 · Figure 3 · p 2 · "P group big_" 2
Document 1 · Author_ 1 · Subtitle 1 · Title 1
```

Attribute availability (numerator / **2060**, same conditions):

| entry | count | % | what it is |
|---|---|---|---|
| `/Pg` | 1388 | 67.4 % | direct page association (ISO 32000-2 Table 355, p739–742) |
| `/C` | 819 | 39.8 % | attribute **class** name → `/ClassMap` (14.7.6.2) |
| `/Alt` | 175 | 8.5 % | accessible description |
| `/A` | 175 | 8.5 % | attribute object(s) |
| `/ActualText` | 93 | 4.5 % | exact replacement text |
| `/ID` | 86 | 4.2 % | element id, targeted by `/Headers` |
| `/Lang` | 28 | 1.4 % | language override |
| `/T` | 3 | 0.1 % | human title |

Attribute-object contents, by `/O` owner (numerator / 175 attribute objects):

```
/Table 114 · /Layout 20 · /List 3
keys: ColSpan 114 · Headers 114 · RowSpan 114 · Scope 61 · Placement 13
      LineHeight 6 · ListNumbering 3 · BBox 3 · TextDecorationType 1 · TextAlign 1
```

A real one, verbatim:

```
<< /ColSpan 1
   /Headers [ (BYYII6Erw0aCoF4vDzeCOA) (WbmYaEAzrUWOH8uDWLhsxw) ]
   /O /Table
   /RowSpan 1 >>
```

### 1.3 THE PRIZE — one StructElem to its glyphs and its box

`Observed` (`probe_d_walk.py`, WTPDF page index 10). Door A hands this back directly — the
indentation is the declared nesting, the bboxes are on the elements:

```
[TEXT] (56.7 804.8 538.6 819.9) 'PDF Association — Well-Tagged PDF (WTPDF) 8'   ← OUTSIDE the tree
<Document> std=Document idx=0 bbox=(56.7 54.4 540.5 449.0)
  <P> std=P idx=94 bbox=(70.9 54.4 480.0 80.6)
    [TEXT] (70.9 54.4 480.0 80.6) 'NOTE 1 Embedded files referenced from the containing file…'
    <Reference> std=Reference idx=1 bbox=(306.1 67.4 324.4 80.6)
      <Link> std=Link idx=0 bbox=(306.1 67.4 324.4 80.6)
        [TEXT] (306.1 67.4 324.4 80.6) '8.14'
  <L> std=L idx=100 bbox=(71.1 333.3 531.4 401.9)
    <LI> std=LI idx=0 bbox=(71.1 333.3 436.7 348.4)
      <Lbl> std=Lbl idx=0 bbox=(71.1 338.1 77.7 345.7)
      <LBody> std=LBody idx=1 bbox=(85.5 333.3 436.7 348.4)
        [TEXT] (85.5 333.3 436.7 348.4) 'where authors have used colour or contrast in an…'
```

Note the first line: **the running head sits outside `<Document>`.** That is the declared
artifact boundary, free (§4.7).

### 1.4 The bbox is DERIVED, not declared — cross-checked

`Verified` (`probe_i_verify.py` — two differently-shaped methods on the same element)

Method A (Door A, derived) and Method B (raw xref, author-declared `/A /Layout /BBox`),
on the `/Figure` at WTPDF page index 26, `/Alt = ' cube root of x '`:

| | x0 | y0 | x1 | y1 |
|---|---|---|---|---|
| declared `/BBox` (PDF y-up) | 369.289 | 757.564 | 381.762 | 770.163 |
| …converted to pymupdf top-down | 369.29 | **71.73** | 381.76 | 84.33 |
| Door A derived bbox | 369.29 | **71.73** | 372.62 | 79.69 |

- **Element identity agrees**: both methods find exactly one `Figure` on page 26; `x0` and
  `y0` match to **0.00 pt**.
- **Extent disagrees**: max per-edge deviation **9.145 pt** (right and bottom edges).
  Door A's box is the **union of the glyph/image boxes MuPDF placed under the element**; the
  declared box is the author's layout extent. Door A **under-covers**.
- `Observed` Numerator 9.145 pt; denominator 1 element (the only non-degenerate declared
  `/BBox` in the file); conditions WTPDF 1.0, page index 26, pymupdf 1.28.0.

**Negative control 1** — the same declared box vs the first `<P>` on that page: **298.4 pt**
deviation. The comparison discriminates; it is not vacuous.

**Negative control 2** — `Ashby - An Introduction to Cybernetics (1956).pdf`:
`/StructTreeRoot` = `('null','null')`, **0** struct blocks over pages 0–19, while page 0
yields **933 characters** of text. The detector is watched failing on a file that is
otherwise perfectly readable.

`Observed` **Declared `/BBox` is rare**: 3 of 2060 StructElem (0.15 %), all on `Figure`, and
one of those three is the degenerate placeholder `[-32768 -32768 32767 32767]`.
`Inferred` **Declared structure does not replace J24's geometry.** ISO 32000-2 puts `BBox`
in the optional `Layout` attribute set (14.8.5, Table 384) — a writer may omit it, and this
writer did for 2057 of 2060 elements.

### 1.5 The lossy half — Door A drops Figures

`Observed` (`probe_f_fixed.py`, `probe_g_page0.py`)

| | count |
|---|---|
| `/Figure` StructElem in the xref tree | **3** |
| `Figure` struct blocks Door A reports, all 57 pages, `TEXTFLAGS_DICT` | **1** |
| …with `TEXT_PRESERVE_IMAGES` forced on | **1** (unchanged) |

The two missing ones are on the cover, `/Pg = 2987 0 R` = page index 0, with
`/Alt = 'Creative Commons'` and `/Alt = 'PDF Association logo'`. Door A's tree for page 0
puts the one image block under `<Author_>` — **the wrong parent** — and shows no `<Figure>`
at all.

`Inferred` **This is SYM-053's exact shape, in the tooling rather than the corpus**: the asset
is referenced, the structure declares words for it, and the extraction view shows neither.
Any structure lane must read Figures through **Door B**, not Door A.

### 1.6 Cost

`Observed` (`probe_j_tables.py`; WTPDF 1.0, 57 pp, CPU, pymupdf 1.28.0)

| operation | total | per unit |
|---|---|---|
| `page.get_text()` — **today's witness** | 0.095 s / 57 pp | **1.67 ms/page** |
| `get_text("dict", +TEXT_COLLECT_STRUCTURE)` | 0.119 s / 57 pp | **2.09 ms/page** |
| raw xref tree walk + 5 attribute lookups/elem | 0.184 s / 2060 elem | **0.089 ms/elem** |

`Observed` Structure reading costs **+0.42 ms/page (+25 %)** on top of the witness pass the
audit already pays. `Unknown` Against the convert cost — MEMORY.md records 2.78 s/page for the
post-reboot Damodaran run, which I did **not** re-measure — that would be ~0.08 % of one
page. Quote the ratio only after re-measuring the denominator.

### 1.7 Is a new dependency needed?

`Observed` **No.** Both doors are pymupdf 1.28.0 in `marker-env`, which
`convert_and_ship.py` and `fidelity_audit.py` already import. `pikepdf` / `pypdf` would add
nothing Door B lacks for reading. `Inferred` Door B's ergonomics are poor (string-tuple
returns, the `('null','null')` trap, manual `/K` array regex) — that argues for one small
project-owned reader module, not a new package.

### 1.8 Corpus survey — who actually has a tree

`Observed` (`probe_h_survey.py` → `survey.tsv`; 57 PDFs in `C:/Users/Bndit/Downloads`;
full xref walk + Door A on the first 25 pages of each)

**22 of 57 files carry a `/StructTreeRoot`; 35 do not.**

Every scanned book in the working corpus has **none**: Ashby 1956, Brain of the Firm (both
copies), Damodaran Investment Valuation (all three), GMAT 2024-25, Neural Networks from
Scratch, Levinas, The Unicode Standard v13, Bulgakov, Cybernetics_Book_of_Models (both),
Designing with Freedom (all three), 2406.18256v3.

Richest trees (StructElem / pages):

| file | pages | elems | types | H* | Table | Figure | Alt | ActualText |
|---|---|---|---|---|---|---|---|---|
| ISO_32000-2_sponsored_EC3 | 1023 | 78468 | 40 | 981 | 745 | 195 | 186 | 2 |
| ISO-TS-32005-2023 | 49 | 6265 | 55 | 0 | 5 | 6 | 6 | 4497 |
| File_Portal_System_of_Operations | 42 | 3429 | 17 | 108 | 60 | 3 | 0 | 0 |
| bojieli ai-agent-book | 19 | 2388 | 21 | 119 | 2 | 9 | 9 | 0 |
| Well-Tagged-PDF-WTPDF-1.0 | 57 | 2060 | 28 | 183 | 10 | 3 | 175 | 93 |
| Tagged-PDF-Best-Practice-Guide | 72 | 2025 | 29 | 186 | 8 | 8 | 8 | 0 |
| ISO-14289-2-2024 | 51 | 2017 | 29 | 179 | 11 | 9 | 215 | 6 |

**Three traps, all measured:**

1. `Observed` **The hollow tree.** *Best Practices for Equity Research Analysts* — 465 pages,
   `/StructTreeRoot` **present**, **1** StructElem, 1 type. *Designing Data Intensive
   Applications* — 613 pages, tree present, **17** StructElem. A boolean gate on
   "has a structure tree" routes both into a lane with nothing in it.
   **The gate must be a density, not a boolean** — e.g. StructElem/page and distinct-type
   count, both of which this survey already computes.
2. `Observed` **`/MarkInfo /Marked` is not the gate either.** `ISO_TS_32003-2023` reads
   `Marked = False` and carries **393** StructElem across 13 pages. Three
   `SDT_Comprehensive_Record` files read `Marked = False` with **213** each.
   *(This is a conformance defect in those files — ISO 32000-2 14.8.1 requires `Marked true`
   for Tagged PDF — but the tree is there and readable regardless.)*
3. `Observed` **Structure present, semantics absent.** *DIAGNOSING THE SYSTEM FOR
   ORGANIZATIONS* (Beer, 184 pp): **2276** StructElem but only **4** distinct types —
   **179 `Figure`, each with an `/Alt`**, 0 headings, 0 tables. A scanned book wrapped one
   `Figure` per page. `Inferred` Element *count* is not richness; distinct-type count and the
   heading/table population are the discriminators.

---

## 2. THE MAPPING — defect by defect

### 2.1 SYM-053 — "looks covered" but the asset is blank paper

`SYMPTOM-INDEX.md:72`. Verified 2026-08-23: Beer p129, `_page_128_Picture_15.jpeg`,
511 × 70, extrema 240/240, stddev 0, entropy 0 — a blank strip standing in for two hand-drawn
callout bubbles whose words never survived.

**What the declared structure GIVES.**
`Observed` A `Figure` element carries `/Alt` — an author-written description — and
`/ActualText` — the *exact text the content replaces* (ISO 32000-2 Table 355, p739–742;
14.8.4.8.5 splits the two). On WTPDF 1.0, 175 elements carry `/Alt`; the three `Figure`
elements read `' cube root of x '`, `'Creative Commons'`, `'PDF Association logo'`.
`Observed` The `Figure`'s `/A /Layout /BBox` gives an author-declared region when present
(3/2060 here). `Observed` `/Pg` gives the page directly (1388/2060). `Inferred` Per AN002
(PDF Association, Associated Files) §4.2.2–4.2.4, a `Figure` may also carry an
`/AF` associated file with `AFRelationship = /Data` or `/Alternative` — the source MathML,
chart data or SVG — which would be lossless recovery rather than description.

**What Marker CURRENTLY DOES.**
`Observed` It crops a region of the *rendered page* and writes a JPEG named from the block id
(`assets/_page_128_Picture_15.jpeg`). `Observed` `figure_coverage.py` then asks a **per-page
presence** question — "does a page bearing ≥1 figure-like region have ≥1 output asset
attributed to that page" — and its own docstring says the bbox-overlap version specified in
docs/41 "is not computable on this stack". `Observed` Nothing anywhere compares the crop's
*pixels* to the source region. `Observed` `coverage_rescore.py` carries only the fail-closed
UNREAD rule.

**THE GAP.**
`Inferred` For a **tagged** source, the words in a diagram need not be recovered by vision at
all — they may already be sitting in `/Alt` / `/ActualText`, addressable in 0.089 ms.
`Verified` And the *blankness* is independently checkable today: `probe_g_page0.py` shows
`'Creative Commons'` and `'PDF Association logo'` are declared by the tree and **absent from
the whole-document pymupdf witness text**, which is the SYM-053 signature stated as a
difference of two readable sets rather than as a pixel judgement.
`Observed` **Caveat that must not be lost**: Door A missed both of those Figures. A
SYM-053 detector built on Door A would reproduce the bug it is hunting. Use Door B.
`Observed` **And the corpus limit is severe**: the Beer book that produced the verified
specimen has **no structure tree**. This helps born-digital diagrams; it does nothing for the
scanned Beer page that filed the symptom.

---

### 2.2 The OCR-lane vote (brief's "SYM-054")

> **DEVIATION FROM THE BRIEF — the source wins.**
> `Observed` The brief describes SYM-054 as "the OCR-layer majority vote … the deciding
> measurement is destroyed at the moment of decision". **`SYMPTOM-INDEX.md:73` SYM-054 is
> something else entirely** — seven orphaned HTTP servers surviving an agent-fleet run (S109).
> The OCR-lane vote is **census row N-054**, `docs/51-numeration-census.md:57` and `:279`.
>
> `Observed` **And the "destroyed at the moment of decision" half is FIXED.**
> `convert_and_ship.py:747–778` (`probe`) now returns
> `{invisible_spans, total_spans, invisible_ratio, ocr_font_trigger}`, stamped into the probe
> event (`:1475–1479`) and into the manifest as `probe_evidence` (`:1591`). Signed **NUM-5,
> 2026-08-31**, and the docstring says so.

**What remains open**, `Observed` from the source:

```python
_OCR_FONT = re.compile(r"glyphless|invisible|ocr", re.IGNORECASE)
...
ocr_layer = ocr_font_trigger is not None or (total_spans > 0 and ratio > 0.5)
```

The primary signal is already the right one — `span["type"] == 3` from `get_texttrace()`,
i.e. **text rendering mode 3**, ISO 32000-2 9.3.6 Table 104, `Tr` operator. But the font-name
regex is a **short-circuit `or`**: one span anywhere in a million-span book whose `BaseFont`
matches flips the whole routing, and the ratio is never consulted.

**What the declared structure GIVES.**
`Inferred` Per the Tagged PDF Best Practice Guide §5.5.3.1 (p.65), the spec-sanctioned OCR
pattern is *invisible render-mode-3 text positionally matching a scan, structured normally* —
which confirms mode 3 is the right signal and the font name is a proxy for it.
`Observed` The 5th parser lane grepped all 79,766 lines of the ISO 32000-2 text for
`glyphless`, `OCR` and `optical character`: **zero matches for all three**. Font naming is
tool convention, not specification.
`Inferred` Independently: a *born-digital* tagged tree is itself weak evidence against the
scan lane — 179-Figures-and-nothing-else (the Beer *Diagnosing* profile, §1.8 trap 3) versus
183 headings + 10 tables (WTPDF) are distinguishable from the tree alone.

**THE GAP.** `Inferred` The cheap fix owes nothing to this research: drop the `or` to an
`and`, or demote the font name to a tie-breaker inside a band, since the ratio is now
recorded and auditable. `Observed` Any gate change alters verdicts and is **Rab's signature**
(the SYM-067 precedent).

---

### 2.3 SYM-056 — 61 unterminated `\begin{array}`

`SYMPTOM-INDEX.md:75`. Semantic count **61** unmatched opens (127 opens / 66 closes,
whitespace-aware byte-order stack; the strict-literal 126/66 = 60 is under-reported by one
and must be labelled as literal). Three chunks × 900 s timeouts = **49.9 % of the analyst
lane for 1.6 % of the chunks**. Degenerate column specs of 35–36 identical `c`s.

**What the declared structure GIVES.**
`Verified` (`probe_j_tables.py`) A `Table` → `TR` → `TH`/`TD` walk emits Markdown with **zero
geometric inference and zero `\begin{array}`**. WTPDF page index 19: 1 `Table`, 2 declared
`TR`, cells self-identifying as TH/TD:

```
TR0  [('TH','Owner value for the attribute object'), ('TH','Description')]
TR1  [('TH','FENote'),  ('TD','Attribute governing type of footnote…')]
```

emitted directly as

```
| Owner value for the attrib | Description |
| --- | --- |
| FENote | Attribute governing type o |
```

`Observed` Column count comes from the declared cells, never from a column-position guess —
so a 36-`c` spec is not reachable by construction. `Observed` Span geometry is declared too:
`ColSpan` on 114 objects, `RowSpan` on 114, `Headers` on 114, `Scope` on 61
(ISO 32000-2 14.8.5.7, Table 384, p806–808; the header-association algorithm is 14.8.4.8.3,
p783).

**What Marker CURRENTLY DOES.**
`Inferred` Reconstructs the grid from layout-model cell detection and glyph positions, then
serializes; a mis-inferred column count is what produces both the 36-`c` spec and the missing
`\end`. `Observed` The J24 record does carry `block_type = TableCell` and per-cell `bbox`,
so the grid is now at least *inspectable* after the fact.

**THE GAP.**
`Inferred` For a tagged source, table emission could be **declared-first, Marker-fallback**,
and SYM-056 would be structurally unreachable on that lane.
`Observed` **But**: of the 22 files with a tree, only ISO 32000-2 (745), File_Portal_System
(60), ISO-14289-2 (11), WTPDF (10) and the BPG (8) carry meaningful `Table` populations.
Ashby — the book that filed SYM-056 with 40 unterminated arrays — **has no tree**.
`Observed` The guard SYM-056 actually asks for (balance every `\begin{X}` against its
`\end{X}` on converter output, before the analyst sees it) is a one-line check that costs
nothing and covers **100 %** of the corpus. `Inferred` **Structure-first tables are the
better fix on 39 % of files; the balance check is the necessary fix on all of them.** They
are not alternatives, and the balance check should not wait on this.

---

### 2.4 SYM-067 — degeneration false-positives on empty-cell grids

`SYMPTOM-INDEX.md:86`. `degeneration()` runs on **raw** markdown; empty-cell table grids
drive `max_trigram` to **205** via pipe tokens; `repeated_lines = 0` in both 4e audits;
counterfactual with `_strip_markdown` first → 0 paragraphs trip. Degeneration is the **only**
convert-stage path to `fail` (`fidelity_audit.py:436`).

**What the declared structure GIVES.**
`Observed` An empty `TD` is still a **present, addressable cell** — WTPDF's sample table
reports `TH 3 · TD 1 · EMPTY cells 0`, and the walker counts empties as declared structure
rather than as repetition. `Inferred` Best Practice Guide §4.2.6.2 explicitly sanctions empty
`TD` cells ("empty cells are always TD cells, never TH cells") as legitimate structure.
`Inferred` So a tripwire could exempt a run of pipes whose cells the *source declares*, while
still firing on an invented grid.

**What Marker CURRENTLY DOES.**
`Observed` Emits pipe tables; `degeneration()` reads the pipes as word trigrams. The AND-gate
(`ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX`) was already tightened for the
Cybernetics case; the residual false-fire is on *sparse* tables where the words genuinely
don't vary because the cells are empty.

**THE GAP.**
`Observed` The declared tree tells you a 30-row empty grid was **promoted from a
single-sentence callout** — i.e. the source declares no `Table` there at all — which is a
*sharper* discriminator than any property of the markdown string.
`Inferred` But the cheapest correct fix is still the one the symptom names: run
`degeneration()` on `_strip_markdown`ed text, which by the row's own counterfactual takes the
false fires to **0**, on **all** files, tagged or not.
`Observed` **Any gate change alters verdicts and is Rab's signature.** This section proposes
nothing; it records that the tree offers a second, independent discriminator if he wants one.

---

### 2.5 J24's block record — field for field

`Observed` `marker_blocks.py` `normalize_chunk_payload` persists, per block:

| J24 field | source | what a tagged PDF DECLARES instead | verdict |
|---|---|---|---|
| `id` (`/page/12/SectionHeader/0`) | Marker `BlockId` | `/ID` string (86/2060), `/IDTree`; `/K` MCID int | **both**, different namespaces; PDF ids are author-stable |
| `block_type` (28-value enum) | layout model **inference** | `/S` structure type, role-mapped (60-value vocabulary) | **DECLARED — direct overlap**, see §3 |
| `html` | Marker serialization | glyphs under the element (Door A), or `/ActualText` | **both**; PDF side is the source's own text |
| `page` (corrected, absolute) | parsed from `id.split('/')[2]` | `/Pg` (1388/2060 = 67.4 %), else `/StructParents` → `ParentTree` (ISO 32000-2 14.7.5.4, Table 359, p749–752) | **DECLARED — independent second source** |
| `page_field_raw` | Marker's broken `page` | — | Marker-only defect record; no PDF analogue |
| `polygon` | layout model | **nothing** | **RECONSTRUCTION ONLY** |
| `bbox` | layout model | `/A /Layout /BBox` — **3 of 2060 (0.15 %)** here, one degenerate | **RECONSTRUCTION ONLY in practice** |
| `section_hierarchy` | inferred from heading levels | `Sect`/`Part`/`Div` nesting + `H1`–`H6`; **depth 7 observed** | **DECLARED — direct overlap** |
| `image_refs` | derived from `BlockId.to_path()` | `Figure` + `/Alt` + `/ActualText` + `/AF` | **DECLARED, and richer** — PDF carries *words*, J24 carries a *filename* |

**THE GAP, stated precisely.**
`Verified` **J24's geometry is not replaceable by declared structure** — `/BBox` exists on
0.15 % of elements, and where it does exist it disagrees with the glyph-union box by 9.1 pt
(§1.4). `Inferred` **The relation is the reverse of what "read instead of reconstruct" would
suggest**: the tree supplies *semantics and page attribution* that J24 infers; J24 supplies
*geometry* that the tree almost never declares. `Inferred` They are complements. A tagged
book could carry both and each would check the other — `block_type` against `/S`,
`page` against `/Pg`, `section_hierarchy` against `Sect`/`H*` nesting — which is three
cross-checks J24's own docstring wants (it went to elaborate lengths to derive `page` from the
block id precisely because Marker's `page` field lies; `/Pg` is a *third*, author-asserted
opinion on the same question).

`Observed` **Stale doc, worth a one-line fix**: `figure_coverage.py`'s header still says
"no block bboxes anywhere … Output bboxes exist only under a different output format or the
Python API, i.e. a converter rewrite." J24 performed that rewrite on 2026-09-01. The
docstring's stated ceiling on P-1's sensitivity is now liftable.

---

### 2.6 The analyst-phase audit's `run_page: null`

**Measured cause — simpler and more fixable than the brief implies.** `Observed`
`fidelity_audit.py:411`:

```python
runs = [r for r in _merge_runs(windows, failed, page=None)]
```

`page=None` is passed **literally**, and nothing fills it afterwards. By contrast the
convert-phase audit does fill it — `fidelity_audit.py:357,369`:

```python
for pnum, page in enumerate(witness_pages, start=1):
    ...
    for r in page_runs:
        r["page"] = pnum
```

`Observed` **The convert phase has a page axis; the analyst phase has none.**
`audit_analyst`'s reference is `prepare_output(marker_markdown)` — one flat concatenated
string with page boundaries already gone. The omission runs are offsets into that string.

**What is actually required**: a map from *character offset in the Marker markdown* → *page*.

**What the declared structure GIVES.** `Inferred` **Not this, directly.** The tree maps
*PDF page* → *text*; the missing map is *markdown offset* → *page*. Structure could supply it
only if the pipeline used the tree to *segment* the markdown in the first place.

**What J24 GIVES.** `Inferred` **Exactly this.** Every block record already carries `html` and
a corrected absolute `page`. Aligning the Marker markdown against the ordered `html` of the
blocks yields an offset→page index, and `_merge_runs` becomes able to name a page — filling
the `run_page` field on all 25 (of 634 true) analyst runs in the 2026-08-31 held manifest.

`Inferred` **So the J24→audit bridge is the fix here, and it works on every book, tagged or
not.** The structure tree's contribution is a *cross-check* on the resulting page numbers for
the tagged subset (`/Pg` as a third opinion), not the mechanism.

---

### 2.7 The fidelity audit's witness

Today: `extract_witness()` → `page.get_text()` per page → `prepare_witness()` → windows →
containment scoring. `Observed` `witness_label` is `"pymupdf"` on the clean lane,
`"embedded-ocr"` on the scan lane.

**Could the structure tree be a better witness? — measured, four ways.**

#### (a) It carries text the current witness cannot reach

`Observed` (`probe_g_page0.py`) WTPDF 1.0: **175 declared `/Alt` strings; 47 of them (26.9 %)
appear nowhere in the concatenation of `get_text()` over all 57 pages.** Numerator 47,
denominator 175, conditions: exact substring test after `.strip()`, whole-document witness.
Among the missing: `' cube root of x '` (a formula rendered as an image),
`'PDF Association logo'`, and every table-of-contents `/Alt`.
`Observed` `/ActualText`: 93 declared, **0** absent — the replacement text matched the glyph
text on this specimen.

`Inferred` **This is the structural answer to the brief's question.** The current witness is a
*glyph reader*. Text that a tagged PDF stores as an attribute rather than as glyphs is
invisible to it — no threshold change reaches it. The tree reads it in 0.089 ms/element.

#### (b) It knows a Figure from a Table from a heading

`Observed` WTPDF's tree declares 183 headings (`H2`–`H6`), 10 `Table`, 3 `Figure`, 10
`Caption`, 26 `L`/105 `LI`, 11 `Code`, 7 `TOC`/45 `TOCI`. `Observed` The current witness sees
one undifferentiated character stream per page.
`Inferred` **What that measures that the current witness structurally cannot**: *per-role*
survival. "97 % of body text survived but 4 of 10 tables lost their header row" is not
expressible today — `doc_survival` is a single weighted scalar over uniform word windows, so
a lost table row and a lost sentence are the same event. Roles would let the verdict policy
weigh them differently, which is the shape the Repair Bench needs.

#### (c) It knows the author's reading order

`Verified` (`probe_k_order.py`, whitespace-stripped concatenated character stream per page,
declared depth-first vs pymupdf's default geometric order):

| file | pages compared | identical stream | **differ** |
|---|---|---|---|
| Well-Tagged-PDF-WTPDF-1.0 | 57 | 55 | **2 (3.5 %)** |
| ISO_32000-2_sponsored_EC3 (first 60 pp) | 60 | 45 | **15 (25 %)** |
| File_Portal_System_of_Operations | 42 | 42 | **0** |

Both WTPDF divergences are **true resequencings** — identical character multisets, different
order. **Negative controls**: self-compare identical = True; reversed-declared identical =
False, on all three files.

The concrete case, WTPDF cover:

```
declared (author):     1 Application Note · 2 Well-Tagged PDF (WTPDF) · 3 Version 1.0.0 ·
                       4 2024-02 · 5 Using Tagged PDF for Accessibility and Reuse in PDF 2.0 ·
                       6 PDF Reuse TWG · 7 & PDF/UA TWG · 8 © 2024 PDF Association –
                       9 pdfa.org · 10 This work is licensed under CC-BY-4.0
geometric (witness):   1 Application Note · 2 Version 1.0.0 · 3 2024-02 ·
                       4 "Well-Tagged PDF (WTPDF)Using Tagged PDF for Accessibility and Re…" ·
                       5 © 2024 PDF Association – pdfa.org ·
                       6 "This work is licensed under CC-BY-4.0 PDF Reuse TWG & PDF/UA TWG"
```

The witness demotes the title to fourth, glues it to the subtitle, and glues the authoring
group onto the licence line. `Inferred` ISO 32000-2 14.8.2.5.1 makes the depth-first
traversal of the structure tree the **authoritative** logical reading order, explicitly
licensed to diverge from paint order. `Inferred` The current witness's order is a *guess of
the same kind Marker makes*; the tree's is a *declaration*. Scoring a reconstruction against
another reconstruction is the weaker of the two experiments.

#### (d) It separates artifacts from real content — declared, not guessed

`Observed` (`probe_l_artifact.py`) `prepare_witness()` step 5 strips a line appearing on
`>= max(2, 40 % of pages)`. A tagged PDF instead declares running heads and folios as
artifacts (ISO 32000-2 14.8.2.2, p761–762; two mechanisms, `/Artifact BMC…EMC` or the
`Artifact` element, Table 375 p785). Fragments outside every StructElem in Door A **are** that
declaration.

| file | inside tree | outside (declared artifact) | heuristic ALSO strips | heuristic over-strips real content |
|---|---|---|---|---|
| WTPDF 1.0 (57 pp) | 1531 | **57** | **0 / 57 (0 %)** | 1 (`.`) |
| Tagged BPG (72 pp) | 1571 | **79** | **0 / 79 (0 %)** | 1 (`}`) |
| ISO-14289-2 (51 pp) | 1712 | **51** | 47 / 51 (**92 %**) | 3, incl. `© ISO 2024 – All rights reserved` |

`Observed` **The heuristic catches 0 % on two of three specimens.** The cause is visible in
the data: each running head embeds its own page number —
`'PDF Association — Well-Tagged PDF (WTPDF)29'`, `'© 2023 PDF Association 14'` — so **every
line is unique** and the 40 %-repeat rule never fires. 136 artifact fragments across two files
are being fed to the audit as real content that Marker legitimately drops.
`Observed` And on the file where the heuristic *does* fire, it over-strips 3 lines of real
tagged content.

**Verdict on the witness.** `Inferred` The structure tree is a **strictly better witness on
the tagged subset** — it reaches text the glyph reader cannot (a), scores per role (b),
carries a declared rather than guessed order (c), and separates artifacts by declaration
rather than by a 40 % heuristic that measurably misses (d). `Observed` It is **not available**
on 35 of 57 files, including every scanned book in the corpus.
`Inferred` **Therefore: augment, do not replace.** `witness_label` already exists and already
varies by lane (`"pymupdf"` / `"embedded-ocr"`); a third value plus a density gate (§1.8) is
the shape of the change. `Intended` — nothing here has been built or wired.

---

## 3. What Marker RECONSTRUCTS that a tagged PDF already DECLARES

`Observed` Marker's `BlockTypes` enum
(`C:/Users/Bndit/ml/marker-env/Lib/site-packages/marker/schema/__init__.py`) has **28**
values. `Observed` MuPDF's role-mapped standard vocabulary has **60**. Field for field, using
J24's `block_type` as the join:

| Marker `BlockTypes` | how Marker gets it | PDF 2.0 declares it as | clause |
|---|---|---|---|
| `Document` | wrapper | `Document`, `DocumentFragment` | 14.8.4.3 |
| `Page` | pseudo-block | *(page tree, not structure)* | 7.7.3 p117–124 |
| `SectionHeader` | layout model + font-size ranking | `H`, `H1`–`H6`, `Title` | 14.8.4.5 |
| *(section nesting → `section_hierarchy`)* | inferred from heading levels | `Part`, `Sect`, `Div`, `Aside` | 14.8.4.3 |
| `Text` | layout model | `P` | 14.8.4.5 |
| `TextInlineMath` | layout + math detector | `P` + inline `Formula` | 14.8.4.6/.7 |
| `ListItem` | layout model, bullet detection | `L` / `LI` / `Lbl` / `LBody` (+ `ListNumbering`) | 14.8.4.6, Table 383 |
| `ListGroup` | clustering of ListItems | `L` (declared parent) | 14.8.4.6 |
| `Table` | table-recognition model | `Table` (+ `THead`/`TBody`/`TFoot`) | 14.8.4.8.3 p783 |
| `TableCell` | grid inference from cell boxes | `TR` / `TH` / `TD` | 14.8.4.8.3 |
| *(header row)* | **inferred from position/style** | **`TH` + `/Scope` + `/Headers`** | 14.8.5.7 Table 384 p806–808 |
| *(merged cells)* | inferred from box geometry | **`/ColSpan`, `/RowSpan`** | 14.8.5.7 |
| `TableGroup` | clustering | `Table` + `Caption` | 14.8.4.8.3 |
| `Figure` / `Picture` | layout model region crop | `Figure` (+ `/Alt`, `/ActualText`, `/AF`) | 14.8.4.8.5 |
| `FigureGroup`/`PictureGroup` | clustering | `Figure` + `Caption` | 14.8.4.8.5 |
| `Caption` | proximity to figure/table | `Caption` | 14.8.4.8 |
| `Equation` | math detector | `Formula` | 14.8.4.8.4 |
| `Code` | monospace-font heuristic | `Code` *(PDF 2.0)* | 14.8.4.5 |
| `Footnote` | position + size heuristic | `FENote` *(PDF 2.0)*, `Note` | 14.8.4.5 |
| `Reference` | pattern | `Reference`, `BibEntry` | 14.8.4.7 |
| `PageHeader` / `PageFooter` | position heuristic | **`Artifact` / `/Pagination`** | 14.8.2.2 p761–763, Table 375 p785 |
| `TableOfContents` | heading + leader-dot heuristic | `TOC` / `TOCI` | 14.8.4.6 |
| `Form` | layout model | `Form` (+ `/PrintField`) | 14.8.4.8.6 |
| `Line` / `Span` / `Char` | glyph clustering | `Span`, `Em`, `Strong`, `Sub`, `Quote` | 14.8.4.7 |
| *(link target)* | not reconstructed | `Link` + `/Annot` (173 here) | 14.8.4.7 |
| *(language)* | not reconstructed | `/Lang` per element (28 here) | 14.8.4 |
| `Handwriting` | vision model | **nothing** | — |
| `ComplexRegion` | model's *uncertainty* class | **nothing** | — |
| *(reading order)* | geometric column/flow analysis | **depth-first tree traversal** | **14.8.2.5.1 p764–765** |
| *(`polygon`, `bbox`)* | layout model — **its real product** | `/A /Layout /BBox`, **0.15 % of elements** | 14.8.5, Table 384 |

**Reading the table.**
`Inferred` **24 of Marker's 28 block types have a declared PDF 2.0 counterpart.** Two do not
(`Handwriting`, `ComplexRegion`) and two are structural bookkeeping (`Page`, `Char`).
`Observed` Four things a tagged PDF declares are things Marker **does not reconstruct at all**:
`/Scope` + `/Headers` cell-header association, `/Lang`, `Link` targets, and the
`Artifact`/real-content distinction as a *declaration* rather than a position heuristic.
`Verified` One thing Marker reconstructs that a tagged PDF essentially **never** declares:
**geometry**. That is precisely J24's payload, and it is why J24 and a structure lane are
complements rather than rivals.

---

## 4. Residue — what I did not read, could not verify, or approximated

- **Not read:** the five parser reports were read only where I needed a clause citation
  (`grep`), not end to end. Clause numbers here are quoted from those reports, not
  re-derived from the standards PDFs. `Unknown` whether any citation is mis-transcribed at
  the source.
- **Not measured:** the `/StructParents → ParentTree` reverse map (ISO 32000-2 14.7.5.4).
  I used `/Pg`, which covers 67.4 % of elements; the remaining 32.6 % would need the
  ParentTree route and I did not exercise it. Every claim that "the tree gives a page for
  every element" is `Inferred`, not `Observed`.
- **Not measured:** MCID-level walking (`/K` int → `BDC … EMC` in the content stream).
  I reached glyphs via Door A, which does that walk internally. Whether a
  hand-rolled MCID walk agrees with Door A is **UNREAD**.
- **Not measured:** `/AF` associated files. I did not check whether any specimen carries one.
  The SYM-053 `/AF` path is `Inferred` from AN002 via a parser report only.
- **Not measured:** anything about Marker's *actual* behaviour on a tagged PDF. I read
  `BlockTypes` and `marker_blocks.py`; I ran **no** conversion. Every "Marker CURRENTLY DOES"
  row is `Observed`-from-source or `Inferred`, never `Observed`-from-a-run. No GPU touched.
- **Single-specimen numbers:** the 9.145 pt bbox deviation is n = 1 element in 1 file — the
  only non-degenerate declared `/BBox` in it. It shows the two boxes *can* differ and what
  kind of difference it is; it is not a distribution.
- **Sampling that does not promote:** the corpus survey ran a **full** xref walk but only the
  **first 25 pages** of Door A per file. The `stext` column is therefore a floor, not a count.
  The reading-order table covers WTPDF (all 57), ISO 32000-2 (**first 60 of 1023**) and
  File_Portal (all 42) — the 25 % divergence figure describes 60 pages, not the book.
- **Quoted, not re-measured:** the 2.78 s/page convert rate (from MEMORY.md), the SYM-056
  counts (61 / 900 s / 49.9 %), the SYM-067 `max_trigram` 205, and the SYM-053 pixel
  statistics all come from the registers. Tagged `Unknown` where they appear.
- **Not exercised:** the density gate proposed in §1.8, the artifact-aware witness in §2.7,
  and the J24→`run_page` bridge in §2.6 are **`Intended`** — designs, not builds. Nothing was
  wired, and no threshold in this repo was changed.
- **Bug I introduced and caught:** `probe_e_raw.py` reported "2281 of 2281 elements carry
  `/Alt`" because `('null','null')` is truthy. Superseded by `probe_f_fixed.py` (175 / 2060).
  `probe_e_raw.py` is left on disk **wrong**, as the negative control on my own method.
- **Deviations from the brief**, all four in §2.2 and §2.5: SYM-054's identity, the NUM-5 fix,
  the literal `page=None`, and `figure_coverage.py`'s stale docstring.
