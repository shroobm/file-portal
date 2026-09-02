# ISO 32000-2:2020(E) §14.8 Tagged PDF & §14.9 Repurposing/Accessibility — Dense Reference

Source: `iso32000-2.txt` (PDF Association sponsored copy w/ Errata Collection 3, June 2026).
**Page citations in this file are the `--------- PAGE N ---------` markers in that .txt**, i.e. this
particular file's PDF page index — NOT the standard's own printed page numbers (which run ~15
lower; e.g. this file's PAGE 760 = printed page "745"). §14.8 begins PAGE 760; §14.9 begins PAGE
811; §14.10 "Web capture" (deprecated in PDF 2.0, out of scope for this slice) begins PAGE 817 —
confirmed by direct read, not assumed from the brief.

Normative-level tags used throughout: **[S]** = shall (mandatory), **[SH]** = should (recommended,
non-mandatory), **[M]** = may (permitted), **[N]** = NOTE/informative (no normative force).

---

## 0. What Tagged PDF is, in one paragraph

Tagged PDF (14.8.1, PDF 1.4, PAGE 760) is a stylised use of PDF layered on the logical-structure
framework of §14.7 (not in this slice — structure-element dictionary entries like `ID`, `Ref`,
`PhoneticAlphabet`, `Phoneme` and Table 355 itself live there and are cited but not defined here).
A tagged PDF **[S]** contains a mark information dictionary with `Marked = true`. Its purpose is
declarative, not prescriptive: it gives a processor enough information to make its own repurposing
choices (extraction, reflow, search/index, format conversion, accessibility) — it does not mandate
what the processor does with the content (14.8.2.2.1, PAGE 761).

**This is the crux of the File Portal question**: a tagged, born-digital PDF already carries an
author-asserted structure tree. Marker reconstructs the same category of information (block types,
reading order, bounding boxes) from pixels. Where the tags exist, they are a *ground truth witness*,
not merely a hint — subject to the caveats in §8 below on what 14.9 actually licenses a repurposing
tool to trust.

---

## 1. §14.8.2 Page content rules

### 1.1 Real content vs. Artifacts (14.8.2.2, PAGE 761–762)

- **Real content** [def, PAGE 761]: graphics objects, annotations, form fields intentionally
  introduced by the author, necessary to understand the document.
- **Artifacts**: everything else — PDF-writer pagination/layout mechanics, or author decoration
  irrelevant to understanding content.
- **[S]** Where artifacts are placed in the structure tree, they **shall** use the `Artifact`
  structure type and **shall not** be treated as real content (PAGE 761).
- **[S]** Any content *not* included in the structure tree is an artifact by definition, tag or no
  tag (14.8.2.2.2, PAGE 762).
- **[SH]** Tagged PDF documents should use `Lang`, `Alt`, `ActualText`, `E` (all defined fully in
  §14.9) to support accessibility (PAGE 761).
- A PDF processor **[M]** may legitimately: disregard uninteresting content (skip Link annots),
  treat an element as an opaque terminal (an illustration), or substitute an element with its `Alt`
  text (PAGE 761) — Tagged PDF's whole job is to make those choices *possible*, not to force one.

**Artifact marking mechanisms** (14.8.2.2.2, PAGE 762) — two methods, either sufficient:
1. Marked-content wrapper: `/Artifact BMC ... EMC`, or with a property list `/Artifact <<...>> BDC ... EMC`.
2. The `Artifact` structure element type in the structure tree (for artifacts that need positional
   context relative to real content, e.g. line numbers — PDF 2.0 addition).

**Table 363 — Artifact property list (marked-content form), PAGE 762–763**

| Key | Type | Value |
|---|---|---|
| `Type` | name | *(optional)* One of `Pagination` \| `Layout` \| `Page` \| `Background`. Pagination = running heads/folios/Bates numbers. Layout = footnote rules, ornaments. Page = production aids (cut marks, colour bars). Background = template images/patterns spanning full page or full parent element. |
| `BBox` | rectangle | *(optional)* left/bottom/right/top in default user space. |
| `Attached` | array | *(optional, pagination & full-page background only)* 1–4 of `Top`\|`Bottom`\|`Left`\|`Right` — page edges (crop box) the artifact is logically attached to. Both `Left`+`Right` ⇒ full-width; both `Top`+`Bottom` ⇒ full-height. Non-full-page background artifacts take dimensions from parent structural element. |
| `Subtype` | name | *(optional, PDF 1.7, only when `Type=Pagination`)* `Header`\|`Footer`\|`Watermark`\|`PageNum`\|`LineNum`\|`Redaction`\|`Bates` (last 4 PDF 2.0). Extensible per Annex E. |
| — | — | `Alt`, `ActualText`, `E`, `Lang` from §14.9 may also appear in an artifact's property list; e.g. `ActualText` can carry the literal page number for a `PageNum` artifact or the Bates number for `Bates`. |

**Converter implication**: `Artifact`-tagged content (any `Type`) is the single clearest
"exclude from markdown output" signal ISO 32000-2 gives a converter — running heads, page
numbers, watermarks, cut marks, decorative rules and full-page background images/patterns are
declared non-content. A converter that emits page-number lines or watermark text into markdown
body is contradicting an explicit author assertion, not merely making a stylistic choice.

### 1.2 Soft hyphens (14.8.2.3, PAGE 763–764)

- **[S]** The writer shall distinguish soft hyphens (incidental, line-break-induced, Unicode
  U+00AD) from hard hyphens (U+002D) unambiguously, via the Unicode-mapping mechanisms of
  14.8.2.6.
- **[N]** Some languages need more than a single substitute character on hyphenation (spelling
  changes on break) — handled via `ActualText` (worked example: German "Drucker" → "Druk-"/"ker",
  PAGE 816).

### 1.3 Hidden/invisible content (14.8.2.4, PAGE 764)

- **[S]** For tagged PDF purposes, page content **shall** include *all* graphics objects in their
  entirety, regardless of visibility (clipped, colour-matched to background, or occluded).
- **[N]** Invisible elements can become visible on repurposing; a TTS engine could choose to speak
  invisible text.
- **Converter implication**: an OCR-layer / invisible-text-span decision about what is "real"
  content cannot be delegated to visibility heuristics per this clause — Tagged PDF's own model
  says visibility is irrelevant to whether content is real. (Relevant to SYM-054's font-name/ratio
  heuristic — see §10.)

### 1.4 Page content order vs. logical content order — READING ORDER (14.8.2.5, PAGE 764–765)

This is the clause that answers "what determines reading order" for a converter.

- **[S]** *Page content order* shall be defined by the sequencing of graphics objects within the
  page's content stream (i.e., paint order, not necessarily reading order).
- **[S]** *Logical content order* — the order for semantic purposes — shall be defined by a
  **depth-first traversal of the structure tree**. This is *the* reading-order signal.
- **[SH]** Page content order *should* coincide with logical content order, but is not required to
  — visual overlap can force reverse paint order; a headline can span two facing pages; two
  articles can interleave their beginnings on one page while continuing separately later (PAGE 764,
  NOTE 2's three named cases).
- **[S]** Content within a single marked-content sequence shall itself be in logical content order.
- **[N]** Artifacts *not* enclosed in an `Artifact` structure element are not part of logical
  content order at all — only structure elements participate in it (PAGE 764).
- **Converter implication**: the correct algorithm for "what order do I emit blocks in" is
  structure-tree depth-first traversal, **not** content-stream order and **not** raw
  top-to-bottom/left-to-right bounding-box sort. A converter that infers order purely from
  y-then-x bbox position (as a layout-model reconstruction typically must, absent tags) is
  reproducing *page content order*, which the standard explicitly says need not match reading
  order. For a tagged source, the structure tree is authoritative; for an untagged/reconstructed
  source there is no declared logical order at all, only an inferred one — a materially different
  epistemic status that a converter's provenance metadata should distinguish.

### 1.5 Sequencing of annotations (14.8.2.5.2, PAGE 765)

- Annotations are **not** interleaved in the content stream; they live in the page's `Annots`
  array. Their position in logical content order comes from the structure tree.
- Structure types `Annot`, `Link`, `Form` (see §4.5 Table 368/369 below) explicitly bind a
  marked-content sequence to its corresponding annotation via an object-reference dictionary.

### 1.6 Reverse-order show strings (14.8.2.5.3, PAGE 765)

- `ReversedChars` marked-content tag: characters inside are stored in reverse order (RTL font
  workaround for scripts like Arabic/Hebrew using LTR-glyph-origin fonts). **[S]** To extract/read
  aloud correctly, the *individual characters within each show string* shall be reversed (if
  multiple show strings, only within each, not across).
- **[S]** Leading/trailing SPACE (word-break) permitted; **interior SPACE forbidden** inside a
  `ReversedChars` block.
- **Converter implication**: naive left-to-right text extraction inside a `ReversedChars` region
  produces backwards words unless this tag is honoured.

### 1.7 Unicode mapping & word breaks (14.8.2.6, PAGE 766–767)

- **[SH]** should map every character code in content/appearance streams to a Unicode value.
- **[S]** shall map to Unicode every character code belonging to a structure element **except**
  where an `Alt`/`ActualText` entry applies to that content instead.
- **[SH]** Private Use Area Unicode values should only be used when no other value is available.
- **[S]** Any whitespace that would separate words in plain text shall be present in the tagged
  representation (14.8.2.6.2, PAGE 766–767) — word identification is **[S]** unrelated to how text
  happens to be grouped into show strings; a word break at the end of a show string still needs an
  explicit SPACE/word-break character in the stream.
- **Converter implication**: word/line segmentation should walk the Unicode character stream (as
  augmented by `ActualText`), not glyph positioning/font-change heuristics — those are explicitly
  named as things a correctly-tagged PDF frees a processor from needing (PAGE 767, NOTE 1).

---

## 2. §14.8.3 Basic layout model (PAGE 767–769) — condensed

Informative framing model, not itself a markdown-relevant vocabulary, but the four structure-type
categories it defines are load-bearing for §4 below:

1. **Grouping elements** — organize hierarchy, hold no content directly, no layout effect.
2. **Block-level structure elements (BLSEs)** — lay out content in the *block-progression*
   direction (stacked).
3. **Inline-level structure elements (ILSEs)** — lay out content within a BLSE in the
   *inline-progression* direction (packed into lines).
4. Some types (`Figure`, `Link`, `Annot`, `Form`, `Formula`, `Caption`, `Title`, `FENote`) are
   context-dependent: grouping, BLSE, or ILSE depending on where they're used. Rule (14.8.4.1, PAGE
   769): if used *inside* a block-level element it's inline; otherwise it's block-level.

**Progression direction** (14.8.3.3, PAGE 768): terms are writing-system-neutral — *before/after*
(block direction) and *start/end* (inline direction), not up/down/left/right. In `LrTb` (Western)
writing mode before=top, after=bottom, start=left, end=right. Controlled by the `WritingMode`
layout attribute (§3 below). BLSEs stack before→after within a reference area; ILSEs pack
start→end within a line, which is itself a synthesized BLSE.

**Reference area / content vs. allocation rectangle** (14.8.3.2, 14.8.5.4.5, PAGE 767, 787–788):
a reference area is the inferred frame content is placed in (a column, a table's/cell's bbox, a
floating element's bbox) — not explicit in the PDF, inferred from context. Each BLSE/ILSE has a
*content rectangle* (from its content's shape, bounds its children) and an *allocation rectangle*
(content rectangle + surrounding border/spacing, governs positioning vs. neighbours).

---

## 3. §14.8.4 STANDARD STRUCTURE TYPES — complete vocabulary (PAGE 769–786)

**Nesting rule (14.8.4.1–.2, PAGE 769–770)**: every structure element **[S]** shall have a type
matching a Standard Structure Type or be role-mapped to one. Parent-child nesting rules live in
Annex L (not in this slice — cite as external reference). Category-determination rule for
context-dependent types: inside a block-level element ⇒ inline; otherwise ⇒ block-level.
Document/Grouping elements that are non-empty **[S]** contain only further Document/Grouping/Block
elements (never inline elements or content directly); Inline elements **[S]** may contain other
inline elements but no other structure-element category.

Legend for the emission column: what a **markdown (or markdown+minimal-HTML) converter honouring
the tag** should do. "Drop" = do not emit as visible markdown content (the element still gates
what descends from it).

### 3.1 Document-level (Table 364, PAGE 771) — Category: **Document**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Document` | Encloses one logical document. A PDF may nest several (mail-merge letters, conference-proceedings papers). | Document boundary marker (e.g. `---` separator + optional frontmatter); may carry its own XMP metadata stream (**[M]**) for that nested document. |
| `DocumentFragment` | *(PDF 2.0)* Encloses a logical document **fragment** — structure may be incomplete, starting mid-hierarchy (e.g. at H2, or mid-list). | Same as `Document` but converter should not assume a title/H1 exists; heading-level inference (for bare `H` elements — see below) restarts its "depth" count at each `Document`/`DocumentFragment` boundary. |

**[S]** Within each `Document`/`DocumentFragment`, all heading elements shall be *either* all `Hn`
or all `H` — never mixed (14.8.4.3, PAGE 771; formalised again at `H`'s own entry, PAGE 775).

### 3.2 Grouping-level (Table 365, PAGE 772–773) — Category: **Grouping**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Part` | Groups elements *without* regard to hierarchy (front/back matter, TOC, body, ad section, a magazine spread, a group of form fields or Figures, publisher's indicia). Semantic equivalent of `Div`. Inherits containment rules of nearest non-`Part` ancestor. | Transparent — drop the wrapper, recurse into children with parent context unchanged. May emit a comment/anchor if downstream navigation needs the boundary. |
| `Sect` | Groups elements *with* regard to hierarchy (clauses, article components, recipe sections). | Transparent for markdown emission (no native "section" primitive), but is the structural signal for inferring nested heading depth for bare `H` elements. |
| `Div` | Orthogonal-to-semantics grouping; role-map target for custom tags with no better standard mapping, or for attaching non-semantic attributes (e.g. a `Lang` change with no semantic import). Inherits containment of nearest non-`Div` ancestor. | Transparent; if it only carries `Lang`, propagate language metadata but emit no markdown syntax. |
| `Aside` | *(PDF 2.0)* Content distinct from its parent's main flow — callouts, sidebars, article commentary, textbook background boxes. | Blockquote / callout block (e.g. `> ...` or a fenced "aside" admonition) — visually and semantically separated from the surrounding flow, unlike `Div`. |
| `NonStruct` | Grouping with **no** structural significance — purely a grouping convenience. **[SH]** should *not* be interpreted or exported to other formats; **[S]** its descendants shall still be processed normally. | Drop the wrapper entirely (do not even treat as a transparent container marker); recurse into and emit children exactly as if `NonStruct` were absent. |

### 3.3 Block-level (Table 366, PAGE 774–776) — Category: **Block**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `P` | Paragraph — "any low-level division of content", not necessarily prose. | Markdown paragraph (blank-line-separated text block). |
| `Hn` (n≥1, unsigned int, no leading zero, no prefix/suffix — `H7` valid, `h7`/`H07`/`H-7`/`H_7` invalid) | Heading at explicit level n. | `#` × n heading. |
| `H` | Heading whose level is **derived from structure-tree nesting depth** within the enclosing `Document`/`DocumentFragment`, not stated explicitly. **[SH]** should be first child of its parent structure element; **[S]** shall be the *only* heading element in that parent. Used mainly for machine-generated / strictly-controlled documents. | Converter must count nesting depth from the nearest enclosing `Document`/`DocumentFragment` to compute the heading level, then emit `#`×depth. This is a **structural inference step**, not a direct attribute read. |
| `Title` | *(PDF 2.0)* High-level division title (book/brochure/leaflet title; article/section/chapter title). **[SH]** should occur once per parent grouping element, at/near the start. | Top-level `#`/frontmatter `title:` at the appropriate scope (document title → H1/YAML frontmatter; section title → that section's heading). |
| `FENote` | *(PDF 2.0)* Footnote/endnote — content read at the reader's discretion, not inline. Reference *should* exist from the citing content via a `Link` (structure destination in its link annotation) or via `Ref` on the structure element. | Markdown footnote (`[^n]` marker at the reference point + `[^n]: text` definition block), keyed by the `Ref`/`Link` association. |

### 3.4 Sub-block level (Table 367, PAGE 776–777) — Category: **Inline** (despite the name)

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Sub` | *(PDF 2.0)* Sub-division inside a block element, used in an inline context (a verse in a poem/scripture, a numbered line, a source-code line, a postal-address line). May contain a `Lbl` for a line/verse number. **[SH]** if used once inside a block, *all* sibling content in that block should also be wrapped in `Sub`. | Line-preserving emission (hard line break between `Sub` siblings) rather than paragraph reflow — e.g. inside a poem or address block; source-code lines → fenced code block, one `Sub` per line. |

### 3.5 General inline-level (Table 368, PAGE 777–780) — Category: **Inline** (context-dependent for 3)

**[S]** Any inline element occurs 0+ times inside its parent; siblings (other inline elements or
actual content) may occur in any combination/order unless restricted by type (14.8.4.7.1, PAGE
777).

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Lbl` | Label distinguishing content from siblings: list bullet/number, heading chapter number, definition-list term, key in a key-value pair, TOC chapter/page number, form-field label, footnote reference glyph, question/answer cue. | Usually **drop** for ordered/unordered lists (markdown auto-generates the marker) unless the literal label text carries information the auto-marker loses (e.g. non-sequential numbering) — then preserve verbatim. For definition lists / key-value pairs, emit as the term/key (e.g. bold prefix). |
| `Span` | Generic inline run with no inherent characteristics — a delimiter for attributed text ranges (e.g. a `Lang`-tagged foreign word) or a role-map fallback target for custom inline types the reader doesn't understand. | No markdown syntax of its own — pass through contained text; apply only the effect of whatever attribute it carries (e.g. wrap in a `<span lang="...">` only if language marking must survive; otherwise plain text). |
| `Em` | *(PDF 2.0)* Emphasis — changes sentence meaning, language-dependent; stress level = count of ancestor `Em` elements. | `*text*` (single) / nested emphasis for multiple ancestor `Em`s. |
| `Strong` | *(PDF 2.0)* Strong importance/seriousness/urgency. | `**text**`. |
| `Link` | Association between enclosed content and a link annotation (12.5.6.5) — HTML-hyperlink-equivalent. Children: content items/ILSEs (not other Links) sharing identical `A`/`Dest`/`PA`, plus exactly one object reference to the link annotation. An `SD` entry in the annotation's `GoTo`/`GoToR` action can target a structure element directly, not just a page area. | `[text](target)` — target resolved from the associated annotation's action (URI, or a `Dest`/`SD` structure destination resolved to an anchor). |
| `Annot` | Association with 1+ non-link, non-widget PDF annotations (all same subtype if >1) — OR a mechanism to include those annotations in the tree. Examples: markup annotations (deletion/insertion/modification requests), highlighted content. | Not primary flow content — typically an inline marginal note/comment marker (e.g. a footnote-style comment) rather than body text; **[S]** must never be used for `Link` or `Form`/widget annotations. |
| `Form` | Association with a widget annotation, or inclusion mechanism for one. **[S]** every widget annotation that is real content shall be wrapped in `Form`. Often contains a `Lbl` for the field's label. Non-interactive form fields tagged this way carry a `PrintField` attribute (§5.4 below). | Field placeholder: text-value fields → the field's text content inline; checkbox/radio → `[x]`/`[ ]`; push-button → button-label text. |

**[N] (2020 change, PAGE 779)**: `Link` and `Annot` category definitions were redefined in this
edition — a converter reading pre-2020 tagged PDFs against this table should be aware the
categorization rules shifted.

### 3.6 Ruby & Warichu (Table 369, PAGE 780–781) — Category: **Inline**

For Japanese/Chinese pronunciation glosses (ruby) and interlinear comments (warichu).

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Ruby` | Wraps an entire ruby assembly. **[S]** contains one `RB` followed by either one `RT`, or the 3-element sequence `RP, RT, RP`. **[S]** shall not break across lines. | HTML `<ruby><rb>base</rb><rt>gloss</rt></ruby>` if HTML passthrough allowed; else `base(gloss)` parenthetical fallback. |
| `RB` | Ruby base text (full-size). May contain text/other inline elements/mixture. | The primary displayed text. |
| `RT` | Ruby annotation text (smaller, adjacent to base). | The gloss — superscript/parenthetical depending on target format. |
| `RP` | Ruby punctuation — used only when ruby can't render in ruby style and falls back to a normal comment or warichu; typically a single paren char. | Emit the literal bracketing character **only** in the non-ruby-capable fallback path; suppressed when native ruby rendering is used. |
| `Warichu` | Wraps an entire warichu (2-line interlinear comment) assembly. **[S]** contains 3-element sequence `WP, WT, WP`. May wrap across lines per JIS X 4051-2004. | Parenthetical inline comment, e.g. `base (comment)`. |
| `WT` | Warichu text — the small 2-line comment. | The comment text. |
| `WP` | Warichu punctuation surrounding `WT` — typically a paren; **[M]** per JIS X 4051-2004 may be rendered as a ¼-em space instead of a literal paren, formatter's discretion. | Literal bracket or a thin space, per above. |

### 3.7 Lists (Table 370, PAGE 781–782) — Category: **Block or Inline**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `L` | List — semantically related items. **[S]** if a `Caption` is present it must be first or last child. Governed by `ListNumbering`/`ContinuedList`/`ContinuedFrom` attributes (§5.4 below). Covers bulleted/numbered lists, TOCs, indexes, dictionaries, key-value lists. | Markdown list block — `-`/`*` for unordered, `1.` for ordered, chosen from `ListNumbering`. |
| `LI` | One list-item member; children in any order/combination. Often carries a `Lbl` for its marker. | One markdown list item line (with the `Lbl`, if preserved per §3.5, folded into the marker position). |
| `LBody` | The actual content of a list item (e.g. the definition/translation in a dictionary list). | The text following the item marker. |

**[S]** Hierarchical (nested) lists: a child `L` must be a **direct child** of its parent `L`, or
be inside a `Div` that itself belongs to the parent `L` (14.8.4.8.2, PAGE 782). **[N]** A list
appearing *inside* an `LBody` is not part of that hierarchy (it's just nested content).

**Converter implication**: nested markdown-list indentation should follow this direct-child-or-Div
rule, not raw visual indentation.

### 3.8 Tables (Table 371, PAGE 782–783) — Category: **Block** for `Table`; internal types have no independent category (scoped to a `Table`)

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Table` | 2-D logical grid of cells, possibly with complex substructure. **[S]** `Caption` (if present) must be first or last child. | GFM markdown table (`\| \| \|` + header separator row) for simple grids; fall back to HTML `<table>` when row/col-spans or `THead`/`TBody`/`TFoot` grouping can't be expressed in GFM. |
| `TR` | A row of `TH`/`TD` cells. | One markdown table row. |
| `TH` | Header cell describing 1+ rows/columns/both. Attributes: `RowSpan`, `ColSpan`, `Headers`, `Scope`, `Short` (§5.6). | Header-row cell (GFM header row, or `<th scope="...">` in HTML fallback when spans exist). |
| `TD` | Data cell. Attributes: `RowSpan`, `ColSpan`, `Headers`. | Body-row cell. |
| `THead` | *(optional)* Group of `TR`s forming the header. Optional even when header rows exist — their presence doesn't require this wrapper. | Signals which `TR`s become the GFM header row (there can be only one in GFM — multi-row headers need HTML fallback). |
| `TBody` | *(optional)* Group of `TR`s forming the main body. | Body rows. |
| `TFoot` | *(optional)* Group of `TR`s forming the footer. | Body rows in GFM (no native footer) — HTML `<tfoot>` if fidelity to footer semantics matters. |

**Table header-association algorithm (14.8.4.8.3, PAGE 783)** — this is *the* normative procedure
for computing which header(s) apply to any given cell when the `Headers` attribute is absent:

> **[S]** From the current cell, search toward the first cell in the direction implied by the
> current `WritingMode`. Stop when: (a) the table edge is reached; (b) a data cell is found after a
> header cell; or (c) a header cell with an explicit `Headers` attribute is found (its listed
> headers are appended to the list being built). Any header cell found along the way whose
> (implicit or explicit) `Scope` is `Both`, `Row`, or `Column` is appended to the header list —
> **most-specific-to-most-general order**.

**[S]** If `Headers` *is* specified on a cell, this implicit search is bypassed for that cell —
`Headers` gives an explicit, ordered (row IDs then column IDs, most-specific-first) list of `TH`
element `ID`s. **[S]** `Headers`-attributed headers apply recursively: a data cell's effective
headers = its own `Headers` array **plus** the `Headers` arrays of any `TH` cells named in that
array, recursively (14.8.5.7, PAGE 807).

**Converter implication**: a converter cannot correctly assign row/column semantics to a table cell
by position alone once row/col-spans or an explicit `Headers` array are present — it must either
implement this search algorithm or (safer, cheaper) preserve the `TH`/`TD`/`Scope`/`Headers` tags
verbatim into an HTML-table fallback rather than flattening to GFM, which has no header-cell-to-
data-cell association model beyond "first row is the header."

### 3.9 Caption (Table 372, PAGE 783–784) — Category: **Grouping or Block**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Caption` | Caption for a table, list, image, formula, media object, or (in principle, nested) a group of such. **[S]** must be first or last child of the captioned element; **[S]** at most one per parent (nesting across levels is fine — e.g. a group caption plus per-image captions). | Italic line adjacent to the table/image (e.g. `*caption text*` immediately below a markdown image, or a table's trailing caption line). |

### 3.10 Figure (Table 373, PAGE 784) — Category: **Grouping, Block, or Inline**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Figure` | Encloses complete graphics object(s) — image, drawing, or chart (chart *including* its axis-value text). **[S]** shall not appear between `BT`/`ET` (i.e., never inside a text object). May have logical substructure (nested `Figure`s); repurposing tools **[M]** may treat it as visually opaque without examining internals. **[SH]** should carry a `BBox` when it appears whole on one page. **[SH]** should carry `Alt` *or* `ActualText` — `Alt` describes the graphic; `ActualText` gives exact text-equivalent when the graphic *is* text (e.g. a stylised drop-cap image). | `![alt](src)` — `alt` from `Alt`/`ActualText`; `src`/crop region from `BBox` + page image. A chart's axis-label text (declared part of the `Figure`) should be folded into the alt text or a caption, not silently dropped. |

### 3.11 Formula (Table 374, PAGE 784–785) — Category: **Grouping, Block, or Inline**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Formula` | A mathematical equation (or part), chemical formula, or mathematical proof. **[S]** shall not appear between `BT`/`ET`. May have logical substructure (nested `Formula`s, or inline-tagged internal parts — e.g. for MathML). Repurposing tools **[M]** may treat it as visually opaque. **[SH]** should carry `BBox` when whole-page. **[SH]** should carry `Alt` or `ActualText` (same Alt=description / ActualText=exact-text-equivalent split as `Figure`). | `$...$`/`$$...$$` (LaTeX) if a MathML substructure (namespace `http://www.w3.org/1998/Math/MathML`, element `math`, §6 below) is present and convertible; else fall back to `Alt`/`ActualText` as plain text, or an image crop from `BBox` as last resort. |

### 3.12 Artifact (Table 375, PAGE 785) — Category: **Grouping, Block, or Inline**

| Type | Meaning | Markdown converter should emit |
|---|---|---|
| `Artifact` | *(PDF 2.0)* Encloses non-real content that nonetheless needs a structure-tree position for context (e.g. line numbers on a page, so authors can place them positionally without forcing readers to consume them as logical content). **[SH]** a tagged-PDF processor should normally **ignore** all direct/indirect descendants of an `Artifact` element. | **Drop.** Do not emit into markdown body. (This is the same "exclude" signal as the marked-content-sequence form of Artifact in §1.1/Table 363 — two mechanisms, one semantic.) |

---

## 4. §14.8.5 Standard structure attributes (PAGE 786–811) — condensed to what a converter needs

### 4.1 Attribute owners & resolution order (14.8.5.2–.3, PAGE 786–788)

**Table 376 — standard attribute owners** (`O` entry on an attribute object, PAGE 786–787):
`Layout` (layout params), `List` (list numbering), `PrintField` (non-interactive form fields),
`Table` (cell organization), `Artifact` (Artifact-specific), plus format-export owners:
`XML-1.00`, `HTML-3.20`/`4.01`/`5.00`, `OEB-1.00`, `RTF-1.05`, `CSS-1`/`2`/`3`, `RDFa-1.10`,
`ARIA-1.1`. **[S]** a format-specific owner's attributes apply only when processing for that
format, and **[S]** override the corresponding `Layout`/`List`/`PrintField`/`Table`/`Artifact`
value when both exist.

**[S] Attribute resolution priority** (14.8.5.3, PAGE 787–788) — first applicable wins:
1. Format-specific owner's value (if processing for that format), excluding Layout/PrintField/Table/List/Artifact.
2. `Layout`/`PrintField`/`Table`/`List`/`Artifact`-owned value on the element's own `A` entry.
3. Value from the class map referenced by the element's `C` entry.
4. Inherited resolved value of the parent element (only if attribute is inheritable).
5. The attribute's default value.

**[N]** No semantic distinction exists between explicit and inherited values — the tree logically
has every attribute fully bound at every element (14.8.5.3, PAGE 788). `Lang`, `Alt`, `ActualText`,
`E` do **not** live in attribute dictionaries at all — they're direct entries on the structure
element dictionary or a `Span` property list (§6 and §7 below).

### 4.2 Layout attributes (14.8.5.4, PAGE 788–800) — summary, not full attribute-by-attribute detail

Table 377 (PAGE 788–790) maps ~25 layout attributes to the structure-element categories they apply
to (any element / any BLSE / BLSEs-with-text / Figure-Form-Formula-Table / TH-TD / any ILSE /
grouping-elements-for-columns / vertical-text / ruby-text) and whether each is inheritable.
Selected attributes most relevant to a markdown converter's decisions (full definitions PAGE
790–802 — condensed here since visual/CSS-fidelity attributes like `BorderStyle`, `Padding`,
`GlyphOrientationVertical` etc. carry no markdown-syntax consequence and are not reproduced
verbatim):

- **`Placement`** (name, not inheritable, PAGE 791): `Block` (default for BLSEs) / `Inline`
  (default for ILSEs) / `Before` / `Start` / `End` — the last three make an element *float* out of
  normal stacking to an edge of its reference area. **Converter implication**: a floating element
  (drop-cap, pull-quote, marginal figure) may need to be re-anchored near its logical reference
  point in a linear markdown output rather than emitted exactly where paint order would place it.
- **`WritingMode`** (name, inheritable, PAGE 792): `LrTb`/`RlTb`/`TbRl`/`TbLr`/`LrBt`/`RlBt`/
  `BtRl`/`BtLr` — governs block/inline progression direction (Western/Arabic-Hebrew/CJK/Mongolian/
  Berber/Batak systems respectively) and, for tables, whether rows stack in the block direction and
  cells pack in the inline direction — i.e. WritingMode determines whether a table should be read
  L→R or R→L, which a markdown table's row/column order must respect.
- **`TextAlign`** (name, inheritable, BLSEs w/ text, PAGE 796): `Start`/`Center`/`End`/`Justify` —
  no markdown-syntax consequence typically (markdown doesn't carry alignment except per-column in
  GFM tables — see `BlockAlign`/`InlineAlign` below for cells specifically).
  `BlockAlign`/`InlineAlign` (table cells, PAGE 797–798) govern content alignment within a cell —
  translatable to GFM's `:---:`-style column alignment markers when uniform across a column.
  `TBorderStyle`/`TPadding` (cell border/padding) carry no markdown consequence.
- **`BBox`** (rectangle, not inheritable; Figure/Form/Formula/Table, PAGE 796): bounding box for
  elements whose content shouldn't reflow. **[SH]** present when the element doesn't lend itself to
  visual rearrangement (explicitly named: `Figure`, `Formula`). This is the crop-source for a
  Figure→markdown-image conversion, and — per the File Portal J24 ticket — the persisted
  page+bbox block record is exactly this data recovered from Marker's own reconstruction.
- **`ListNumbering`** — actually a *List* attribute, see 4.3 below (misfiled by table location, not
  by this reference).

### 4.3 List attributes (14.8.5.5, Table 382, PAGE 803–804)

| Key | Value |
|---|---|
| `ListNumbering` (name, inheritable) | `None` (arbitrary `Lbl` text, no numbering scheme) \| `Unordered` (PDF 2.0, bullets unspecified) \| `Description` (PDF 2.0, term/definition list) \| `Disc`\|`Circle`\|`Square` (bullet shapes) \| `Ordered` (PDF 2.0, numbering unspecified) \| `Decimal`\|`UpperRoman`\|`LowerRoman`\|`UpperAlpha`\|`LowerAlpha`. **[S]** A list is unordered *unless* `ListNumbering` is one of `Ordered`/`Decimal`/`UpperRoman`/`LowerRoman`/`UpperAlpha`/`LowerAlpha`. Alphabet for `UpperAlpha`/`LowerAlpha` follows the prevailing `Lang`. |
| `ContinuedList` (boolean, PDF 2.0) | Whether this `L` continues a previous list elsewhere in the tree (default `false`). If `ContinuedFrom` absent, continuation is assumed from the preceding list at the same hierarchy level. |
| `ContinuedFrom` (ID/byte string, PDF 2.0) | The specific list `ID` this one continues (e.g. a numbered list interrupted by an intervening paragraph, resuming its count). |

**Converter implication**: `ContinuedList`/`ContinuedFrom` is the correct signal for "this ordered
list's numbering should resume from N, not restart at 1" — a case markdown renderers otherwise get
wrong by default.

### 4.4 PrintField attributes (14.8.5.6, Table 383, PAGE 804–806)

For **non-interactive** forms (fields converted to flat content, or authored print-and-fill).
`Role`: `rb` radio / `cb` checkbox / `pb` push-button / `tv` text-value (content of the `Form`
element *is* the field's value text) / `lb` listbox. `Checked`: `on`/`off`/`neutral` for
radio/checkbox state. `Desc`: alternate field name (parallel to interactive fields' `TU`).
**[SH]** semantic groupings of non-interactive fields (e.g. a radio group + its label) should be
wrapped in a `Part`.

### 4.5 Table attributes (14.8.5.7, Table 384, PAGE 806–808) — the accessibility-critical set

| Key | Applies to | Meaning |
|---|---|---|
| `RowSpan` / `ColSpan` (integer, not inheritable, default 1) | `TH`/`TD` | Cell spans N rows/columns in the `WritingMode`-implied direction. |
| `Headers` (array of byte strings, not inheritable) | `TH`/`TD` | Explicit list of `TH` element `ID`s serving as this cell's headers — row IDs then column IDs, most-specific-first. **[S]** overrides the implicit search algorithm (§3.8 above) for that cell. **[S]** applies recursively through chained `TH.Headers`. |
| `Scope` (name: `Row`\|`Column`\|`Both`, not inheritable, PDF 1.5) | `TH` only | Explicit header scope. **[S]** default when absent: first-row-and-column ⇒ `Both`; first-row-only ⇒ `Column`; first-column-only ⇒ `Row`; otherwise ⇒ `Both`. |
| `Summary` (text string, not inheritable, PDF 1.7, restored 2020) | `Table` only | Prose summary of the table's purpose/structure, for non-visual rendering (speech/braille). |
| `Short` (text string, not inheritable, PDF 2.0) | `TH` only | Abbreviated form of the header cell's content, so a screen reader doesn't re-read a long header for every cell in its row/column. |

**Converter implication**: `Summary` is a ready-made table caption/alt-text source when no
`Caption` element is present; `Short` is the correct source for a compact GFM header cell when the
full `TH` content would be unwieldy inline.

### 4.6 Artifact attributes (14.8.5.8, Table 385, PAGE 808–810)

Parallel to the Table 363 marked-content-sequence form (§1.1) but for the `Artifact` *structure
element*'s own attribute object: `Type` (`Pagination`\|`Layout`\|`Page`\|`Inline` — note: `Inline`
here, not `Background`, differs slightly from Table 363's set; `Inline` artifacts are ones with
logical-structure context, e.g. `LineNum`/`Redaction` subtypes), `BBox`, `Subtype` (`Header`\|
`Footer`\|`Watermark`\|`PageNum`\|`Bates`\|`LineNum`\|`Redaction`, only meaningful when
`Type=Pagination` or `Inline`).

---

## 5. §14.8.6 Namespaces & role maps (PAGE 810–811) — condensed

- **[S]** Every structure element in a tagged PDF shall be in at least one of: the **PDF 2.0
  standard structure namespace** (`http://iso.org/pdf2/ssn`), the **PDF 1.7 standard structure
  namespace** (`http://iso.org/pdf/ssn`, = ISO 32000-1's Clause 14.8 vocabulary — this is the
  **default** when no `NS` entry is given), or an "other" namespace per 14.8.6.3.
- **[S]** Non-standard structure types shall be role-mapped (via the structure tree root's
  `RoleMap`, or a namespace's own `RoleMapNS`) to a standard type, transitively if needed.
- **14.8.6.3 Other namespaces**: MathML 3.0 is the one domain-specific namespace ISO 32000-2
  itself names — namespace name `http://www.w3.org/1998/Math/MathML`, element type `math`
  (deliberately lowercase, matching MathML's own convention). **[S]** its namespace must be
  explicitly declared when used. Other domain namespaces are permitted but must satisfy the
  role-mapping requirement above (i.e. an unrecognised custom namespace's elements must still map
  back to a standard type a generic processor understands).

**Converter implication (Annex L not in this slice)**: a converter should treat `RoleMap`
resolution as a required pre-pass — any tag name outside the ~41 standard types in §3 must be
resolved through the role map before the converter's per-type emission table (§3) can be applied;
an unresolved custom tag with no role-map entry is a spec violation in the source, worth surfacing
as a defect rather than silently guessing its category.

---

## 6. §14.9 Repurposing and accessibility support (PAGE 811–817)

### 6.1 General (14.9.1, PAGE 811)

States the accessibility feature set PDF provides for screen-reader/TTS vocalization: natural
language (§6.2), alternate descriptions (§6.3), replacement text (§6.4), abbreviation/acronym
expansion (§6.5), pronunciation hints (§6.6).

### 6.2 Natural language specification — `Lang` (14.9.2, PAGE 811–815)

**Hierarchy of `Lang` sources**, highest to lowest precedence for a piece of content
(14.9.2.1/.3, PAGE 811, 814):
1. Document catalog's `Lang` — document-wide default (applies to content-stream text *and* text
   strings: metadata, outline entries, OCG names).
2. Structure element's own `Lang` entry — **[S]** if absent, inherits from nearest ancestor
   structure element that has one.
3. Marked-content sequence's `Lang` (via a `Span`-tagged property list) — for content **outside**
   the structure hierarchy; a nested marked-content sequence inside a structure element defers to
   *that element's* language, not the outer marked-content `Lang`.
4. Per-text-string Unicode language-escape sequence (7.9.2.2.2) — overrides everything above for
   that specific string.

**[S]** Where structured content is nested inside non-structured content with a different `Lang`,
the **structure element's** language wins (14.9.2.3, PAGE 814).

**Language identifiers** (14.9.2.2, PAGE 812): **[S]** either the empty string (language unknown)
or a BCP 47 Language-Tag; **[S]** case-insensitive matching required even though convention writes
language codes lowercase / country codes uppercase. **[SH]** non-linguistic content should use
`zxx` (BCP 47).

**Multi-language text arrays** (14.9.2.4, PAGE 815–816, PDF 1.5): pairs of `(lang-id, text)`;
**[S]** no language id repeats; empty-string id = default fallback text. **[S]** Matching:
exact case-insensitive match first; else longest-available **prefix** match (`en` matches array
entry `en-US`, but `en-US` does **not** match a bare `en` or an unrelated `en-GB` entry) — a
hyphen must immediately follow the matched prefix in the array's id for prefix-match to count.

### 6.3 Alternate descriptions — `Alt` (14.9.3, PAGE 815–816)

- May be attached to: a structure element (`Alt` entry in the structure-element dictionary), a
  marked-content sequence (`Alt` in a `Span`-tagged property list, PDF 1.5), or any annotation
  lacking its own text representation (via its `Contents` entry).
- **[S]** For annotation types that normally *do* display text, `Contents` **is** the source of the
  alternate description (i.e. reuse, don't duplicate).
- **`Alt` semantics: a complete word-or-phrase substitution** for the current element — treated as
  a full replacement of meaning, at word-boundary granularity. **[S]** if consecutive elements each
  carry `Alt`, a word break is inferred between them.
- Interactive form fields have a parallel mechanism: `TU` on the field dictionary (12.7) — an
  alternative field name, **[S]** used in place of the actual name by an interactive UI.

### 6.4 Replacement text — `ActualText` (14.9.4, PAGE 816–817)

- May be attached to a structure element (`ActualText` entry, PDF 1.4) or a marked-content
  sequence (via `Span` property list, PDF 1.5).
- **`ActualText` semantics: a character-for-character replacement**, not a description — the exact
  text a person would perceive when viewing the content (e.g. resolving a ligature glyph, an
  illuminated-manuscript inline graphic-as-letter, or a hyphenation-induced spelling change). **[S]**
  if consecutive elements/sequences each carry `ActualText`, **no** word break is inferred between
  them (contrast with `Alt`'s explicit word-break rule above — this is the operative distinction).
- May carry a Unicode language-escape sequence overriding the prevailing `Lang` for that
  replacement text specifically.

### 6.5 Expansion of abbreviations/acronyms — `E` (14.9.5, PAGE 817)

- May be attached to a structure element (`E` entry) or a `Span`-tagged marked-content property
  list.
- **`E` semantics: a word-or-phrase substitution**, treated (like `Alt`) as separated from
  surrounding text by an implied word break. Worked example: "Dr." tagged `E="Doctor"` before a
  name, and a *separate* "Dr." tagged `E="Drive"` after a street name — same source text, different
  expansion, disambiguated by context via the tag rather than by NLP guesswork.
- **[N]** Some abbreviations conventionally aren't expanded (e.g. "XYZ" — leave as-is, or spell out
  "X Y Z" defensively) — `E` is optional, not mandatory, per abbreviation.

### 6.6 Pronunciation hints (14.9.6, PAGE 817)

Structure-element entries `PhoneticAlphabet` and `Phoneme` (defined in Table 355, §14.7 — outside
this slice), plus a document-wide `PronunciationLexicons` entry on the structure tree root, may
supply explicit pronunciation guidance for TTS. **[N]** a PDF processor is **not required** to
process these hints (informative-only mechanism, no shall).

---

## 7. `Alt` vs `ActualText` vs `E` — the comparison a converter must get right

| Property | What it replaces | Granularity | Word-break behaviour between consecutive tagged runs | Typical use | Converter emission |
|---|---|---|---|---|---|
| `Alt` | Non-textual content (images, formulas) that has no natural text form | Whole word/phrase | **Break implied** between consecutive `Alt`-bearing elements | Image/figure/formula description | Markdown `alt` text of `![]()`, or descriptive caption text |
| `ActualText` | Textual content represented in a non-standard glyph form (ligatures, illuminated capitals, hyphenation spelling changes) | Exact character-for-character substitute | **No break implied** — treated as continuous text | Recovering the "real" text stream for extraction/search/TTS | The literal text to place in the markdown body **instead of** attempting to transcribe the glyphs directly |
| `E` | Abbreviations/acronyms | Whole word/phrase expansion | **Break implied**, same as `Alt` | TTS-correct expansion ("Dr." → "Doctor" vs. "Drive" by context) | Optional: either keep the abbreviation as written (typical for markdown body text) or substitute the expansion when the target reader is TTS/audio rather than visual |

All three are also legal on a `Span`-tagged marked-content property list (content **outside** the
structure hierarchy), not only on structure elements — a converter that only reads structure-tree
entries and ignores `Span` marked-content property lists will miss these when authors used the
lighter-weight mechanism.

---

## 8. What §14.9 explicitly licenses a repurposing tool to rely on

Synthesizing 14.9.1–14.9.6 and the cross-references into §14.8: a **conformant tagged PDF**
licenses a repurposing/accessibility tool to:

1. Use the **structure tree's depth-first order** as logical reading order, in preference to
   content-stream paint order (14.8.2.5.1) — this is the single most consequential license for a
   converter, since it says the tree, not geometry, is authoritative when the two disagree.
2. Use `Lang` (at whatever level in the 4-tier hierarchy applies) rather than language-detection
   heuristics, for any span of text (14.9.2).
3. Substitute `Alt` for non-textual content wholesale, and know it's a phrase-level substitution
   with an implied word boundary on either side (14.9.3).
4. Substitute `ActualText` for the actual glyph stream and know it's a lossless character-level
   recovery with **no** implied word boundary — i.e. safe to splice directly into a running text
   extraction (14.9.4).
5. Use `E` to recover a TTS-correct expansion **without** needing NLP disambiguation — the
   disambiguation was already done by the author at tagging time (14.9.5).
6. Rely on the Unicode character stream (as augmented by `ActualText`) for word-boundary detection,
   because **[S]** whitespace that separates words in plain text is required to be present in the
   tagged stream (14.8.2.6.2) — i.e. it need **not** fall back to font/glyph-position heuristics.
7. Treat any `Artifact`-tagged content (either mechanism, §1.1/§3.12) as safely excludable from the
   real-content stream — this exclusion is an author assertion, not an inference the tool has to
   make itself.
8. Treat `TH`/`Scope`/`Headers` as a complete, order-preserving specification of row/column header
   association (14.8.4.8.3/14.8.5.7) — sufficient to reproduce correct cell semantics **without**
   re-deriving them from table geometry.
9. **[N]** — What it is *not* licensed to assume: that page content order equals logical order
   (explicitly may diverge, 14.8.2.5.1); that pronunciation hints are honoured by any given
   processor (14.9.6, explicitly not required); or that a `NonStruct`-wrapped subtree carries any
   interpretable structural meaning beyond its processed descendants (14.8.4.4).

---

## 9. Requirements register (selected — full text embedded in §1–§7 above with page cites)

Level tags: shall=**S**, should=**SH**, may=**M**.

| # | Clause | Page | Level | Statement (condensed) | Binds |
|---|---|---|---|---|---|
| R1 | 14.8.1 | 760 | S | Tagged PDF doc shall contain mark info dict with `Marked=true`. | writer |
| R2 | 14.8.2.2.1 | 761 | S | Artifacts placed in the structure tree shall use the `Artifact` type, never as real content. | writer |
| R3 | 14.8.2.2.2 | 762 | S | Content not in the structure tree is an artifact regardless of explicit tagging. | reader/processor |
| R4 | 14.8.2.4 | 764 | S | Tagged-PDF page content shall include all graphics objects in full, irrespective of visibility. | processor |
| R5 | 14.8.2.5.1 | 764 | S | Page content order shall be defined by content-stream sequencing. | writer |
| R6 | 14.8.2.5.1 | 764 | S | Logical content order shall be defined by depth-first traversal of the structure tree. | reader/processor |
| R7 | 14.8.2.5.1 | 764 | S | Content within one marked-content sequence shall itself be in logical order. | writer |
| R8 | 14.8.2.5.3 | 765 | S | Within `ReversedChars`, only the characters of each show string (not cross-string) shall be reversed for extraction. | processor |
| R9 | 14.8.2.5.3 | 765 | S | `ReversedChars` blocks shall not contain interior whitespace/word-break characters. | writer |
| R10 | 14.8.2.6.1 | 766 | S | Every char code belonging to a structure element shall map to Unicode, except where `Alt`/`ActualText` applies. | writer |
| R11 | 14.8.2.6.2 | 766-767 | S | Whitespace separating words in plain text shall be present in the tagged char stream even at show-string boundaries. | writer |
| R12 | 14.8.4.1 | 769 | S | Every structure element shall have a type matching a Standard Structure Type or be role-mapped to one. | writer |
| R13 | 14.8.4.3 | 771 | S | Within one `Document`/`DocumentFragment`, headings shall be uniformly `Hn`-style or uniformly `H`-style, never mixed. | writer |
| R14 | 14.8.4.5 (`H`) | 775 | SH/S | `H` should be first child of its parent; shall be the only heading element in that parent. | writer |
| R15 | 14.8.4.5 (`Title`) | 775 | SH | `Title` should occur once, near the start, per parent grouping element. | writer |
| R16 | 14.8.4.7.1 | 777 | S | Inline structure elements may occur any number of times; unrestricted ordering with content unless the type itself restricts it. | writer |
| R17 | 14.8.4.7.2 (`Link`) | 779 | S | `Link` children sharing `A`/`Dest`/`PA` must be identical across all non-annotation children; exactly one object reference to the link annotation. | writer |
| R18 | 14.8.4.7.2 (`Form`) | 779 | S | Every real-content widget annotation shall be wrapped in a `Form` structure element. | writer |
| R19 | 14.8.4.7.2 (`Annot`) | 779 | S | `Annot` shall never be used for link or widget annotations. | writer |
| R20 | 14.8.4.8.2 (`L`) | 782 | S | Nested `L` elements shall be a direct child of the parent `L`, or inside a `Div` belonging to that `L`. | writer |
| R21 | 14.8.4.8.3 (Table 371) | 782 | S | `Caption` on `Table`/`L` shall be first or last child. | writer |
| R22 | 14.8.4.8.3 | 783 | S | Implicit header-search algorithm (§3.8) applies when `Headers` is absent; explicit `Headers` overrides it. | processor |
| R23 | 14.8.4.8.5 (`Figure`) | 784 | S | `Figure` shall not appear between `BT`/`ET`. | writer |
| R24 | 14.8.4.8.5 (`Figure`) | 784 | SH | `Figure` should carry `BBox` (single-page, whole figure) and `Alt` or `ActualText`. | writer |
| R25 | 14.8.4.8.6 (`Formula`) | 784-785 | S/SH | Same shall-not-in-BT/ET and should-carry-BBox/Alt-or-ActualText rules as `Figure`. | writer |
| R26 | 14.8.4.8.7 (`Artifact`) | 785 | SH | A tagged-PDF processor should ignore descendants of an `Artifact` structure element. | processor |
| R27 | 14.8.5.7 (`Headers`) | 807 | S | Effective headers of a cell = its own `Headers` array + recursively the `Headers` arrays of any named `TH` cells. | processor |
| R28 | 14.8.5.7 (`Scope`) | 807 | S | Default `Scope` when absent is computed from row/column position (first-row-and-col=Both, first-row=Column, first-col=Row, else Both). | processor |
| R29 | 14.8.6.2 | 810 | S | Every structure element shall be in a standard namespace (default PDF 1.7 `.../pdf/ssn`) or role-mapped into one. | writer |
| R30 | 14.9.2.2 | 812 | S | Language identifiers shall be BCP 47 tags or empty string; matching shall be case-insensitive. | processor |
| R31 | 14.9.2.3 | 814 | S | Where structured content nests inside differently-`Lang`-tagged unstructured content, the structure element's `Lang` takes precedence. | processor |
| R32 | 14.9.2.4 | 815 | S | Multi-language array: no repeated language id; matching is exact-then-longest-valid-prefix. | processor |
| R33 | 14.9.3 | 815-816 | — (def) | `Alt` = complete word/phrase substitution; word break implied between consecutive `Alt`-tagged runs. | processor |
| R34 | 14.9.4 | 816 | — (def) | `ActualText` = exact character-for-character replacement; **no** word break implied between consecutive runs. | processor |
| R35 | 14.9.4 | 816 | S | If two+ consecutive elements/sequences carry `ActualText`, no word break shall be inferred between them. | processor |

*(Full normative text for every listed item, plus every attribute-table entry not tabulated at R1–R35, is reproduced verbatim in §1–§7 above with its own page citation — this register is a navigation aid, not a substitute.)*

---

## 10. Relevance to File Portal's named defects

- **The core open question (born-digital tagged PDFs)**: §1.4 and §8 item 1 are the direct
  answer — for a *conformant* tagged PDF, the structure tree's depth-first order is the
  **declared, author-asserted reading order**, explicitly licensed to be trusted ahead of geometric
  reconstruction, and explicitly allowed to *diverge* from paint/content-stream order in named
  cases (overlap, facing-page headlines, interleaved articles). Marker's reconstructed block+bbox
  records (recovered per **J24**) are the geometric-inference analogue of exactly what the
  structure tree declares — for a tagged source, the tree is available as an independent witness
  *against* Marker's reconstruction, not merely as another source of the same kind of guess. — tag:
  **Inferred** (I read the normative text; whether the 16 specimen PDFs' structure trees are
  well-formed enough to *actually* use this way is untested by me — see Residue).
- **SYM-053** (asset reference exists but is blank/words-gone): §3.10 `Figure`'s `Alt`-vs-
  `ActualText` split (14.8.4.8.5, PAGE 784) is precisely the mechanism that would let a tagged
  source distinguish "this is decorative/opaque" from "this is a hand-drawn diagram whose exact
  text content is X" — if the source PDF actually populated `Alt`/`ActualText` on the offending
  `Figure`, a converter reading tags would recover the words SYM-053 says are lost; if it did not,
  the tag data is simply absent and this clause offers no remedy, only the *shape* of where the
  remedy would live. — tag: **Inferred** (I have not checked whether any specimen PDF's `Figure`
  elements carry populated `Alt`/`ActualText`; that is a data question outside my slice).
- **SYM-056** (61 unterminated `\begin{array}` from table-heavy pages): §3.8 + §4.5 (`Table`/`TR`/
  `TH`/`TD`/`Headers`/`Scope`/`RowSpan`/`ColSpan`) is the complete, closed vocabulary a tagged
  source would supply for reconstructing a table *without* needing to infer a LaTeX-array
  structure from geometry at all — reading tags bypasses the whole class of malformed-LaTeX-array
  failure by not generating LaTeX from a table in the first place when a tag-derived GFM/HTML table
  is available. — tag: **Inferred**.
- **SYM-067** (degeneration tripwire false-positives on empty-cell table grids): the `Headers`/
  `Scope` algorithm (§3.8, R22/R27/R28) and `RowSpan`/`ColSpan` give a tagged source an
  unambiguous way to represent a genuinely sparse/empty-cell grid (an empty `TD` is still a
  present, addressable cell with defined headers) — distinguishable in principle from the
  degenerate-repetition pattern the tripwire is presumably keying on. Whether *this specific*
  tripwire logic keys on cell-content repetition vs. cell*-count* is outside this slice's evidence.
  — tag: **Inferred**, weakly (I have not read the tripwire's implementation).
- **SYM-054** (OCR-layer majority-vote via font-name regex + invisible-span ratio, destroying the
  deciding measurement): §1.3 (14.8.2.4, PAGE 764) is directly on point — the standard's own model
  says visibility (glyphless/invisible fonts included) has **no bearing on whether content is
  real**; "invisible" is not a Tagged-PDF category at all, only "real content" vs. "Artifact" is.
  A font-name regex proxying for "this is an OCR text layer, ignore it" is answering a different
  question than Tagged PDF's own vocabulary asks, and — critically — for a *tagged* source, the
  `Artifact` type (§3.12) is the standard's actual mechanism for declaring "ignore this," making
  font-name-regex inference unnecessary when tags are present and trustworthy. — tag: **Inferred**.
- **The fidelity audit's witness (pymupdf raw text extraction)**: pymupdf's plain-text extraction
  recovers page content order (or its own internal glyph-order heuristic) — it does **not**
  perform the structure-tree depth-first traversal this clause defines as logical content order
  (§1.4), and does not distinguish real content from Artifacts (§1.1/§3.12) or apply `ActualText`
  substitution (§7) unless separately coded to do so. A witness built this way will, on a tagged
  PDF whose page-order and logical-order diverge (a case the standard names as expected, not
  pathological), disagree with a structure-tree-derived reading even when the structure-tree
  reading is the *more* correct one — an audit-fidelity false-negative risk baked into the choice
  of witness, not a defect in the converter being audited. — tag: **Inferred** (I have not read
  pymupdf's extraction implementation or the audit code; this is reasoned from what pymupdf's
  documented `get_text()` behavior is generally understood to do, not from having opened its
  source in this task).
- **J24** ("run_page: null" — the analyst-phase audit can't anchor an omission run to a page): the
  persisted block records this ticket recovered are (per the brief) page+bbox pairs from Marker's
  reconstruction. A tagged source's structure tree does not, by itself, carry page numbers on
  every element either — the page association comes from the `Pg` entry on marked-content-
  reference dictionaries and the `K` (kids) array's implicit page-content-item linkage (defined in
  §14.7, outside this slice) — so closing the `run_page: null` gap by reading tags would need that
  §14.7 machinery, not §14.8/14.9 alone. — tag: **Inferred**, flagged as needing the §14.7 slice to
  complete.

## 11. Residue — what I did not verify

- **Not read**: §14.7 "Logical structure" (structure-element dictionary Table 355, structure tree
  root Table 354, namespace dictionary, `K`/kids/MCR mechanics, `ID`/`Ref` entries, page-association
  machinery) — cited by name throughout my slice but defined earlier in the standard, outside my
  assigned pages. Every place above that says "(Table 355, §14.7 — outside this slice)" is a named
  gap, not a silent one.
- **Not read**: Annex L (parent-child nesting rules table) and Annex M (namespace differences) —
  both referenced normatively by 14.8.4.2 and 14.8.6.1 respectively, neither included in PAGE
  760–817.
- **Not read**: §14.10 onward (Web Capture, Optional Content, page boundaries/piece info,
  measurement/geospatial, associated files) — confirmed out of my responsibility by direct
  observation of where 14.10's header actually falls (PAGE 817, immediately after 14.9.6), not
  merely by trusting the brief's page-range framing, which (as noted at the top) does not exactly
  match the clause boundary the brief itself states.
- **Not verified against the 16 specimen PDFs**: nothing in this file was cross-checked against
  any actual File Portal specimen's structure tree, `Alt`/`ActualText` population rate, or
  `Headers`/`Scope` usage. Every "relevance" claim in §10 is **Inferred** from the standard's text
  alone, not **Observed** in specimen data — I did not open any specimen PDF, examine its
  `StructTreeRoot`, or run pymupdf/any tool against it. That verification is the natural next step
  for whoever picks this file up, and is explicitly not something I can promote to Observed without
  doing it.
- **Not verified**: pymupdf's actual extraction algorithm (whether/how it orders text, whether it
  has any structure-tree awareness at all in the version File Portal uses) — the witness claim in
  §10 is reasoned from the standard's definitions plus general knowledge of what "raw text
  extraction" conventionally means, not from reading pymupdf's source or File Portal's audit code.
- **Errata layer**: this copy carries "Errata Collection 3 – June 1, 2026" annotations (per the
  file's own PAGE 1–2 front matter); those are inline PDF annotations in the *original* PDF this
  .txt was extracted from, and this .txt extraction gives no visual indication of which passages
  carry a pending/accepted/completed erratum marker. I have transcribed the *base* text as
  extracted; I have not attempted to detect or flag which specific sentences might be subject to an
  unresolved erratum. Two explicit "(2020)" editorial notes were caught and flagged inline (Div/Part
  clarification changes, Link/Annot recategorization, Attached-key reinstatement, CSS-owner
  renumbering, Summary-key restoration) because the source text itself flagged them as such — no
  additional errata-scanning was performed beyond what the base text already narrates.
