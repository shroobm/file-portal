# ISO/TS 32005 + Tagged PDF BPG + Extensions — converter reference

Slice: the namespace standard (ISO/TS 32005:2023), the practitioner guide (Tagged PDF Best
Practice Guide: Syntax v1.0.1, 2023), PDF Declarations (2019), and six PDF 2.0 application
notes/technical specifications. Built for File Portal's question: for a born-digital **tagged**
PDF, should the pipeline **read** the declared structure tree instead of (or as a witness
against) Marker's ML-reconstructed layout?

Page citations use each source's own **printed** page number (bottom-of-page numeral), not the
raw text-extraction page marker. Offsets used to convert (`printed = raw_extraction_page − N`),
each independently confirmed by locating the printed footer numeral in the raw dump:
ts32005.txt −7 · tagged-bpg.txt −1 · declarations.txt −4 · an001-bpc.txt −1 · an002-af.txt −4 ·
an003-metadata.txt −3. Clause numbers are the primary, unambiguous citation; page numbers are
the secondary cross-check. The three crypto TSs (32001/32002/32003) are cited by clause only —
they are 4-page documents with no page-numbering worth reconstructing (see Part 3).

Normative-level tagging follows BPG 2.6 / ISO usage: **shall** = required, **should** = strongly
recommended, **may** = permitted. Statements from ISO/TS 32005 and PDF Declarations use ISO's
own shall/should/may. The BPG itself declines to use "shall" (2.6, p.6) — its guidance is cast as
"it is recommended" / "semantically appropriate" / "semantically inappropriate", which this
reference tags **should** (recommended) or as an explicit inappropriate-marker; only where the
BPG quotes PDF/UA-1 verbatim does a real "shall" appear, and that is flagged.

---

## PART 1 — ISO/TS 32005:2023: PDF 1.7 + PDF 2.0 structure namespace inclusion

### 1.1 What this document is (clause 1, Scope, p.1)

A **Technical Specification** (not a full International Standard — TS status, first edition
2023-07), 40 printed pages, produced by ISO/TC 171/SC 2. It "specifies containment
requirements for tagged PDF documents that use the PDF 1.7 namespace and the PDF 2.0
namespace" and "extend[s], and entirely compl[ies] with, the rules and provisions already
specified for tagged PDF documents within ISO 32000-2" (cl.1, p.1). It governs **writers and
processors of tagged PDF that mix the PDF 1.7 and PDF 2.0 standard structure namespaces in one
document** — which is the default situation for any PDF 2.0 file, since 32000-2 makes the PDF
1.7 namespace the *default* namespace (BPG Annex B, A.1, p.69) and most real documents still use
PDF-1.7-only element types. Normative references: ISO 32000-1 (PDF 1.7), ISO 32000-2:2020 (PDF
2.0), and the *PDF Declarations* specification (cl.2, p.1).

Why it matters to a converter: **Table 5** (cl.7.2) is the complete parent-child containment
matrix across *both* namespaces at once — the single artifact a structure-tree reader needs to
validate "is this nesting legal" without holding two separate spec documents in its head. Part 1.6
below reconstructs it in full.

### 1.2 Terms (clause 3, p.1)

| Term | Definition | Clause |
|---|---|---|
| PDF 1.7 namespace | = "standard structure namespace for PDF 1.7" | 3.1 |
| PDF 2.0 namespace | = "standard structure namespace for PDF 2.0" | 3.2 |
| PDF 1.7 element | standard structure element type defined in the PDF 1.7 namespace | 3.3 |
| PDF 2.0 element | standard structure element type defined in the PDF 2.0 namespace | 3.4 |
| unique PDF 1.7 element | a structure element whose type is defined **solely** in the PDF 1.7 namespace | 3.5 |

### 1.3 Declaration of conformance (clause 4, p.2)

**may** (not shall): a PDF "may include a PDF declaration of conformance with this document." If
present it **shall** conform to *PDF Declarations* (cl.4, p.2). Table 1 (p.2) values, usable
directly against an XMP payload a converter parses:

| Key | Value |
|---|---|
| URI identifier | `https://pdfa.org/declarations#iso32005` |
| Mandatory field(s) | none |
| Standard | ISO/TS 32005 |
| Version | 1 |
| URI | `https://www.pdfa.org/resource/ISO-32005/` |
| Level | N/A |
| Technology Reliance | ISO 32000-2 |

**Checkable property**: an input PDF's XMP metadata (`pdfd:declarations` bag, see Part 3.1) can be
grep'd for `pdfa.org/declarations#iso32005` as a **self-reported** signal that the *producer*
claims namespace-mixing conformance — this is an assertion, not proof; PDF Declarations 1 (p.1
of that spec) is explicit that presence of a declaration does not guarantee conformance.

### 1.4 Namespace mixing rules (clause 5, pp.2–5)

- 5.1 General (p.2, **shall**): "PDF documents conforming to this document shall be versioned as
  PDF 2.0 using either the header or the value of the Version entry in the document's catalog
  dictionary (see ISO 32000-2:2020, 7.7.2)." NOTE: 32000-2 "does not restrict the interaction of
  the two namespaces" — TS 32005 exists purely to close that gap.
- 5.2 PDF 1.7 as a standalone namespace (p.2, **shall**): if *every* structure element in a
  document is a PDF 1.7 element (explicit, default-namespace, or role-mapped to one), ISO 32000-1
  containment rules apply and namespace declarations are not required — these elements are
  **exempt** from 5.3–5.5. The moment *any* element declares a namespace other than PDF 1.7 or the
  default, the *whole document* must conform to 5.3–5.5 (p.3, **shall**).
- 5.3 Elements defined in both namespaces (p.3, **shall**): any structure element whose type is
  common to both namespaces **shall use the PDF 2.0 namespace** and follow 32000-2:2020 Annex L
  plus this document's clause 5 (except where 5.2 exempts it). Converter implication: when a type
  name (e.g. `P`, `Table`, `Figure`) is common to both, the PDF 2.0 definition/containment rules
  govern, not the 1.7 ones, in a mixed document.
- 5.4 Elements defined solely in PDF 2.0 (p.3, **shall**): must explicitly declare the PDF 2.0
  namespace; may contain both unique-1.7 and 2.0 elements. Annex M of 32000-2 lists these (not
  reproduced here — out of this slice).
- 5.5 Elements defined solely in PDF 1.7 (pp.3–5): may be included; when included they **shall**
  conform to clause 5 and may be children of PDF 2.0 elements and may contain unique-1.7 or 2.0
  elements (5.5.1, **shall**). 5.5.2.1 (**shall**): since 32000-2 doesn't define these types
  directly (it defers to 32000-1), unique PDF 1.7 elements **shall** match the 32000-1
  descriptions and follow clause 5's containment rules.
  - **Table 2 — unique PDF 1.7 grouping elements** (5.5.2.2, p.4): `Art`, `BlockQuote`, `TOC`,
    `TOCI`, `Index`, `Private`. These **shall** be the *only* PDF 1.7-namespace grouping elements
    permitted (**shall**, p.4). Full descriptions: `Art` = self-contained narrative, articles
    should be disjoint (should-not-nest). `BlockQuote` = block-level quotation from another
    source; differs from `DocumentFragment` in permitting modification/contextualization (NOTE
    2); can both contain and be a child of `DocumentFragment` (NOTE 2, cross-refs 7.2). `TOC` = a
    list of `TOCI`/nested `TOC` entries; a flat-hierarchy TOC has only `TOCI` children, a
    multi-level one nests `TOC`; captioned sub-parts of one TOC level **shall** use `Part` to
    subdivide, each `Part` with its own `Caption` (**shall**, p.4). `TOCI` = one TOC entry.
    `Index` = sequence of entries with reference elements (`Reference`) pointing into the
    document body. `Private` = writer-private content; **structural significance unspecified,
    determined entirely by the writer**; neither `Private` nor its descendants (incl. content)
    have defined semantic significance and **may be ignored by processors** both on consumption
    and when exporting to other formats — this is the converter's explicit license to skip
    `Private` subtrees.
  - **Table 3 — unique PDF 1.7 inline-level elements** (5.5.2.3, p.5): `Quote`, `Note`,
    `Reference`, `BibEntry`, `Code`. Shall be the *only* PDF 1.7-namespace inline elements
    permitted. `Quote` = inline quotation (cf. block-level `BlockQuote`). `Note` = footnote/
    endnote, referenced from body text, may have `Lbl` child; placement (inline vs. end-of-page)
    is at writer discretion — Tagged PDF does not prescribe position in page-content order.
    `Reference` = citation to content elsewhere in the document. `BibEntry` = bibliography entry,
    may have `Lbl` child; no standard sub-types defined for author/work/publisher parts. `Code` =
    fragment of program text.
- 5.6 Role mapping (p.5, **shall**): custom element types **shall** have an explicitly defined
  namespace, except as exempted by 5.2.

### 1.5 Attributes (clause 6, pp.5–6)

- 6.1 General: 32000-2's structure-attribute mechanism (32000-2 14.7.6) extends 32000-1's with
  namespaces (32000-2 Table 360).
- 6.2 Attribute owners (p.5): attributes defined across the various "attribute owners" in
  32000-2 are a **superset** of 32000-1's. **may**: regardless of whether a structure element is
  unique-1.7 or 2.0, it may use any 32000-2-defined structure attribute, subject to that
  attribute's own restrictions.
- 6.3 Attribute namespaces (p.6, **may**): as an alternative to attribute owners, an attribute
  object identifying its owner *as a namespace* "may occur on any structure element regardless of
  that structure element's namespace."

### 1.6 Clause 7 — Table 4 legend + Table 5, the full parent-child matrix (pp.6–39)

7.1 General (p.6): 32000-2 14.8.4 defines the standard structure element types; 14.8.6
identifies the PDF 1.7 and PDF 2.0 namespaces; 32000-2 Annex L specifies PDF-2.0-only
hierarchical inclusion. **This document's 7.2 extends those rules to cover PDF 1.7 elements too**
— it is the union, not a replacement.

7.2 Hierarchical inclusion rules (p.6, **shall**): "PDF 1.7 elements and PDF 2.0 elements shall
not have child or parent PDF 1.7 elements or PDF 2.0 elements that are not explicitly listed in
Table 5." This **shall** also applies to role-mapped elements (except 5.2-exempt documents).

**Table 4 — legend for Table 5** (p.6):

| Value | Meaning |
|---|---|
| `∅` | shall not occur |
| `∅*` | shall not occur **unless the parent element is used as a grouping-level element** |
| `0..n` | may occur, 0 or more times (not required) |
| `1..n` | shall occur, 1 or more times (required, repeatable) |
| `0..1` | may occur, at most once |
| `‡` | containment governed by that structure type's own prose description, not this table |
| `[a]` | see 32000-2:2020, 14.8.4.7.3 for Ruby-specific containment provisions |
| `[b]` | see 32000-2:2020, 14.8.4.7.3 for Warichu-specific containment provisions |

**Table 5** itself (pp.7–39, "Parent-child relationships between the PDF 1.7 elements and PDF 2.0
elements") is a per-structure-type register of two columns — *Children* (what may nest directly
inside this type, with occurrence) and *Parents* (what this type may directly nest inside, with
occurrence). It covers 54 structure types including `StructTreeRoot` and the leaf pseudo-type
"content item" (real marked content, not a further structure element).

**Reconstruction method and confidence** (residue-relevant — read before trusting the table):
the source PDF's table cells were extracted column-major (all Children-occurrence values, then
all Children-type-names, then all Parents-occurrence values, then all Parents-type-names, per
row) rather than row-major, because the underlying PDF table layout puts each column in its own
vertical run. This reference was reconstructed **mechanically** with a token-stream parser
(pairing each row's N occurrence-tokens with the following N type-name tokens) and then
**cross-validated**: every "X lists Y as a child with occurrence V" entry was checked against "Y
lists X as a parent with occurrence V" in the reverse direction (1,193 cross-checks). **46 of 54
structure types passed with zero discrepancies** and are presented below at full confidence.
**8 types — `Ruby`, `RB`, `RT`, `RP`, `Warichu`, `WT`, `WP`, and "content item"** — sit at a page
boundary (source pp.38–39) where the column-major extraction is genuinely ambiguous (the
Parents-list boundary for `WP` and the Children/Parents role for "content item" could not be
resolved from the text stream alone); they are marked **⚠LOW-CONFIDENCE PARSE** below and given
as extracted, but should be re-verified against the source PDF directly (or the compact
representation the standard's own Bibliography [1] points to:
`https://www.pdfa.org/resource/iso-ts-32005-hierarchical-inclusion-rules/`, PDF Association,
2022-11-10) before any converter encodes them as ground truth. This corner is Japanese ruby/
warichu typography — out of scope for File Portal's 16 English-language specimen PDFs, so the
low-confidence flag costs nothing operationally.

**Occurrence notation below**: a bare type name means occurrence `0..n` (the overwhelmingly
common case — omitted for density); any other occurrence is shown as `Type[value]` using the
Table 4 vocabulary above.

#### StructTreeRoot
- Children (1): Document[1]
- Parents (0): (none)

#### Document
- Children (27): Document, DocumentFragment, Part, Art, Div, Sect, TOC, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Link, Annot, Form, FENote, Index, L, Table, Figure, Formula, Artifact
- Parents (10): StructTreeRoot[1], Document, DocumentFragment, Part[‡], Div[‡], Aside, BlockQuote, NonStruct[‡], Private, Artifact

#### DocumentFragment
- Children (27): Document, DocumentFragment, Part, Art, Div, Sect, TOC, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Link, Annot, Form, FENote, Index, L, Table, Figure, Formula, Artifact
- Parents (17): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Note[∅*], Code[∅*], Link[∅*], Annot[∅*], FENote[∅*], Caption[∅*], Artifact

#### Part
- Children (33): Document[‡], DocumentFragment[‡], Part[‡], Art[‡], Div[‡], Sect[‡], TOC[‡], TOCI[‡], Aside[‡], BlockQuote[‡], NonStruct[‡], Private[‡], P[‡], Note[‡], Code[‡], Hn[‡], H[‡], Title[‡], Sub[‡], Lbl[‡], Link[‡], Reference[‡], Annot[‡], Form[‡], FENote[‡], Index[‡], L[‡], BibEntry[‡], Table[‡], Caption[‡], Figure[‡], Formula[‡], Artifact[‡]
- Parents (25): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOC, Aside, BlockQuote, NonStruct[‡], Private, Title, Note, Code, Link[∅*], Annot[∅*], Form[∅*], FENote, Index, LBody, BibEntry, Caption, Figure, Formula, Artifact

#### Div
- Children (52): Document[‡], DocumentFragment[‡], Part[‡], Art[‡], Div[‡], Sect[‡], TOC[‡], TOCI[‡], Aside[‡], BlockQuote[‡], NonStruct[‡], Private[‡], P[‡], Note[‡], Code[‡], Hn[‡], H[‡], Title[‡], Sub[‡], Lbl[‡], Em[‡], Strong[‡], Span[‡], Quote[‡], Link[‡], Reference[‡], Annot[‡], Form[‡], Ruby[‡], RB[‡], RT[‡], RP[‡], Warichu[‡], WT[‡], WP[‡], FENote[‡], Index[‡], L[‡], LI[‡], LBody[‡], BibEntry[‡], Table[‡], TR[‡], TH[‡], TD[‡], THead[‡], TBody[‡], TFoot[‡], Caption[‡], Figure[‡], Formula[‡], Artifact[‡]
- Parents (28): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Note, Code, Link, Annot, Form, FENote, Index, LI, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Art
- Children (27): DocumentFragment, Part, Div, Sect, TOC, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Lbl, Link, Annot, Form, FENote, Index, L, Table, Caption, Figure, Formula, Artifact
- Parents (21): Document, DocumentFragment, Part[‡], Div[‡], Sect, Aside, BlockQuote, NonStruct[‡], Private, Note, Hn[0..1], H[0..1], Link, Annot, FENote, LBody, TH, TD, Caption, Figure, Artifact

#### Sect
- Children (28): DocumentFragment, Part, Art, Div, Sect, TOC, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Lbl, Link, Annot, Form, FENote, Index, L, Table, Caption, Figure, Formula, Artifact
- Parents (23): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Note, Hn[0..1], H[0..1], Link, Annot, FENote, Index, LBody, TH, TD, Caption, Figure, Artifact

#### TOC
- Children (7): Part, TOC, TOCI, NonStruct, Private, Caption[0..1], Artifact
- Parents (13): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Artifact

#### TOCI
- Children (8): Div, TOC, NonStruct, Private, P, Lbl, Reference, Artifact
- Parents (6): Part[‡], Div[‡], TOC, NonStruct[‡], Private, Artifact

#### Aside
- Children (29): Document, DocumentFragment, Part, Art, Div, Sect, TOC, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Lbl, Link, Reference, Annot, Form, FENote, Index, L, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (18): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, NonStruct[‡], Private, Title, Note, Link[∅*], Annot[∅*], FENote, LBody, Caption, Figure, Formula, Artifact

#### BlockQuote
- Children (30): Document, DocumentFragment, Part, Art, Div, Sect, TOC, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Lbl, Link, Reference, Annot, Form, FENote, Index, L, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (19): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Note, Link[∅*], Annot[∅*], FENote, LBody, Caption, Figure, Formula, Artifact

#### NonStruct
- Children (53): Document[‡], DocumentFragment[‡], Part[‡], Art[‡], Div[‡], Sect[‡], TOC[‡], TOCI[‡], Aside[‡], BlockQuote[‡], NonStruct[‡], Private[‡], P[‡], Note[‡], Code[‡], Hn[‡], H[‡], Title[‡], Sub[‡], Lbl[‡], Em[‡], Strong[‡], Span[‡], Quote[‡], Link[‡], Reference[‡], Annot[‡], Form[‡], Ruby[‡], RB[‡], RT[‡], RP[‡], Warichu[‡], WT[‡], WP[‡], FENote[‡], Index[‡], L[‡], LI[‡], LBody[‡], BibEntry[‡], Table[‡], TR[‡], TH[‡], TD[‡], THead[‡], TBody[‡], TFoot[‡], Caption[‡], Figure[‡], Formula[‡], Artifact[‡], content item[‡]
- Parents (52): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, RB, RT, RP, Warichu, WT, WP, FENote, Index, L, LI, LBody, BibEntry, Table, TR, TH, TD, THead, TBody, TFoot, Caption, Figure, Formula, Artifact

#### Private
- Children (53): Document, DocumentFragment, Part, Art, Div, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H, Title, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, RB, RT, RP, Warichu, WT, WP, FENote, Index, L, LI, LBody, BibEntry, Table, TR, TH, TD, THead, TBody, TFoot, Caption, Figure, Formula, Artifact, content item
- Parents (51): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Form, Ruby, RB, RT, RP, Warichu, WT, WP, FENote, Index, L, LI, LBody, BibEntry, Table, TR, TH, TD, THead, TBody, TFoot, Caption, Figure, Formula, Artifact

#### Title
- Children (28): Part, Div, Aside, NonStruct, Private, P, Note, Code, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, L, BibEntry, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (12): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, BlockQuote, NonStruct[‡], Private, Link[∅*], Annot[∅*], Artifact

#### Sub
- Children (22): NonStruct, Private, Note, Code, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, L, BibEntry, Figure, Formula, Artifact, content item
- Parents (26): Part[‡], Div[‡], NonStruct[‡], Private, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, RB, RT, RP, WT, WP, FENote, LBody, Caption, Figure[∅*], Formula, Artifact

#### P
- Children (24): NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, L, BibEntry, Table, Figure, Formula, Artifact, content item
- Parents (25): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Note, Link[∅*], Annot[∅*], FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Note
- Children (34): DocumentFragment[∅*], Part, Art, Div, Sect, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Caption[∅*], Figure, Formula, Artifact, content item
- Parents (36): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Code
- Children (16): DocumentFragment[∅*], Part, Div, NonStruct, Private, Note, Em, Strong, Span, Link, Reference, Annot, FENote, BibEntry, Artifact, content item
- Parents (32): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, Form[∅*], FENote, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### Hn
- Children (24): Art[0..1], Sect[0..1], NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (20): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Link[∅*], Annot[∅*], Index, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### H
- Children (24): Art[0..1], Sect[0..1], NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (20): Document[0..1], DocumentFragment[0..1], Part[‡], Div[‡], Art[0..1], Sect[0..1], Aside[0..1], BlockQuote[0..1], NonStruct[‡], Private, Link[∅*], Annot[∅*], Index, LBody[0..1], TH[0..1], TD[0..1], Caption[0..1], Figure[0..1], Formula[0..1], Artifact[0..1]

#### Lbl
- Children (21): NonStruct, Private, Note, Code, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (32): Part[‡], Div[‡], Art, Sect, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Em, Strong, Span, Quote, Link, Reference, Annot, Form, FENote, LI, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Em
- Children (22): NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (32): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, RB, RT, RP, WT, WP, FENote, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Strong
- Children (22): NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (32): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, RB, RT, RP, WT, WP, FENote, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Span
- Children (22): NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (32): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, RB, RT, RP, WT, WP, FENote, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Quote
- Children (22): NonStruct, Private, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, BibEntry, Figure, Formula, Artifact, content item
- Parents (29): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, RB, RT, RP, WT, WP, FENote, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### Link
- Children (35): DocumentFragment[∅*], Part[∅*], Art, Div, Sect, Aside[∅*], BlockQuote[∅*], NonStruct, Private, P[∅*], Note, Code, Hn[∅*], H[∅*], Title[∅*], Sub, Lbl, Em, Strong, Span, Quote, Reference, Annot, Form[∅*], Ruby, Warichu, FENote, L[∅*], BibEntry, Table[∅*], Caption[∅*], Figure, Formula, Artifact, content item
- Parents (38): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Reference, Annot, RB, RT, RP, WT, WP, FENote, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Reference
- Children (14): NonStruct, Private, Note, Lbl, Em, Strong, Span, Link, Annot, FENote, BibEntry, Figure, Artifact, content item
- Parents (37): Part[‡], Div[‡], TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot[∅*], Form[∅*], RB, RT, RP, WT, WP, FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Annot
- Children (35): DocumentFragment[∅*], Part[∅*], Art, Div, Sect, Aside[∅*], BlockQuote[∅*], NonStruct, P[∅*], Note, Code, Hn[∅*], H[∅*], Title[∅*], Sub, Lbl, Em, Strong, Span, Quote, Link, Reference[∅*], Annot, Form[∅*], Ruby, Warichu, FENote, L[∅*], BibEntry, Table[∅*], Caption[∅*], Figure, Formula, Artifact, content item
- Parents (40): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, RB, RT, RP, WT, WP, FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Form
- Children (17): Part[∅*], Div, NonStruct, Private, Note, Code[∅*], Lbl, Reference[∅*], FENote, L[∅*], BibEntry, Table[∅*], Caption[0..1], Figure[∅*], Formula[∅*], Artifact, content item
- Parents (36): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link[∅*], Annot[∅*], RB, RT, RP, WT, WP, FENote, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### Ruby ⚠LOW-CONFIDENCE PARSE
- Children (6): NonStruct, Private, RB[[a]], RT[[a]], RP[[a]], content item
- Parents (24): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, FENote, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### RB ⚠LOW-CONFIDENCE PARSE
- Children (13): NonStruct, Private, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Artifact, content item[‡]
- Parents (5): Div[‡], NonStruct[‡], Private, Ruby[[a]], Artifact

#### RT ⚠LOW-CONFIDENCE PARSE
- Children (13): NonStruct, Private, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Artifact, content item[‡]
- Parents (5): Div[‡], NonStruct[‡], Private, Ruby[[a]], Artifact

#### RP ⚠LOW-CONFIDENCE PARSE
- Children (13): NonStruct, Private, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Artifact, content item[‡]
- Parents (5): Div[‡], NonStruct[‡], Private, Ruby[[a]], Artifact

#### Warichu ⚠LOW-CONFIDENCE PARSE
- Children (5): NonStruct, Private, WT[[b]], WP[[b]], content item
- Parents (24): Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, FENote, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### WT ⚠LOW-CONFIDENCE PARSE
- Children (13): NonStruct, Private, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Artifact, content item[‡]
- Parents (5): Div[‡], NonStruct[‡], Private, Warichu[[b]], Artifact

#### WP ⚠LOW-CONFIDENCE PARSE
- Children (13): NonStruct, Private, Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Figure, Artifact[‡]
- Parents (0): (none)

#### content item ⚠LOW-CONFIDENCE PARSE
- Children (5): Div[‡], NonStruct[‡], Private, Warichu[[b]], Artifact
- Parents (0): (none)

#### FENote
- Children (32): DocumentFragment[∅*], Part, Art, Div, Sect, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, L, Table, Caption[∅*], Figure, Formula, Artifact, content item
- Parents (36): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula, Artifact

#### Index
- Children (18): Part, Div, Sect, NonStruct, Private, P, Note, Hn, H, Reference, Annot, FENote, L, Table, Caption, Figure, Formula, Artifact
- Parents (18): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Note, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### L
- Children (6): NonStruct, Private, L, LI, Caption[0..1], Artifact
- Parents (27): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Link[∅*], Annot[∅*], Form[∅*], FENote, Index, L, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### LI
- Children (7): Div, NonStruct, Private, Lbl, LBody, Artifact, content item
- Parents (5): Div[‡], NonStruct[‡], Private, L, Artifact

#### LBody
- Children (34): Part, Art, Div, Sect, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Sub, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (5): Div[‡], NonStruct[‡], Private, LI, Artifact

#### BibEntry
- Children (17): Part, Div, NonStruct, Private, P, Note, Lbl, Em, Strong, Span, Link, Reference, Annot, FENote, Figure, Artifact, content item
- Parents (27): Part[‡], Div[‡], NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### Table
- Children (8): NonStruct, Private, TR, THead[0..1], TBody, TFoot[0..1], Caption[0..1], Artifact
- Parents (25): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, P, Note, Link[∅*], Annot[∅*], Form[∅*], FENote, Index, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### TR
- Children (5): NonStruct, Private, TH, TD, Artifact
- Parents (8): Div[‡], NonStruct[‡], Private, Table, THead, TBody, TFoot, Artifact

#### TH
- Children (30): Art, Div, Sect, NonStruct, Private, P, Note, Code, Hn, H[0..1], Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Figure, Formula, Artifact, content item
- Parents (5): Div[‡], NonStruct[‡], Private, TR, Artifact

#### TD
- Children (30): Art, Div, Sect, NonStruct, Private, P, Note, Code, Hn, H[0..1], Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Figure, Formula, Artifact, content item
- Parents (5): Div[‡], NonStruct[‡], Private, TR, Artifact

#### THead
- Children (4): NonStruct, Private, TR, Artifact
- Parents (5): Div[‡], NonStruct[‡], Private, Table[0..1], Artifact

#### TBody
- Children (4): NonStruct, Private, TR, Artifact
- Parents (5): Div[‡], NonStruct[‡], Private, Table, Artifact

#### TFoot
- Children (4): NonStruct, Private, TR, Artifact
- Parents (5): Div[‡], NonStruct[‡], Private, Table[0..1], Artifact

#### Caption
- Children (35): DocumentFragment[∅*], Part, Art, Div, Sect, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Figure, Formula, Artifact, content item
- Parents (22): Part[‡], Div[‡], Art, Sect, TOC[0..1], Aside[0..1], BlockQuote[0..1], NonStruct[‡], Private, Title[0..1], Note[∅*], Link[∅*], Annot[∅*], Form[0..1], FENote[∅*], Index, L[0..1], LBody[0..1], Table[0..1], Figure[0..1], Formula[0..1], Artifact[0..1]

#### Figure
- Children (35): Part, Art, Div, Sect, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Sub[∅*], Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (35): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form[∅*], WP, FENote, Index, LBody, BibEntry, TH, TD, Caption, Figure, Formula

#### Formula
- Children (33): Part, Div, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, Warichu, FENote, Index, L, BibEntry, Table, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (33): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Annot, Form[∅*], FENote, Index, LBody, TH, TD, Caption, Figure, Formula, Artifact

#### Artifact
- Children (53): Document, DocumentFragment, Part, Art, Div, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct, Private, P, Note, Code, Hn, H[0..1], Title, Sub, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, Ruby, RB, RT, RP, Warichu, WT, WP, FENote, Index, L, LI, LBody, BibEntry, Table, TR, TH, TD, THead, TBody, TFoot, Caption[0..1], Figure, Formula, Artifact, content item
- Parents (50): Document, DocumentFragment, Part[‡], Div[‡], Art, Sect, TOC, TOCI, Aside, BlockQuote, NonStruct[‡], Private, Title, Sub, P, Note, Code, Hn, H, Lbl, Em, Strong, Span, Quote, Link, Reference, Annot, Form, RB, RT, RP, WT, WP, FENote, Index, L, LI, LBody, BibEntry, Table, TR, TH, TD, THead, TBody, TFoot, Caption, Figure, Formula, Artifact

---

## PART 2 — Tagged PDF Best Practice Guide: Syntax (v1.0.1, 2023) — inverted for a converter

This guide (PDF Association PDF/UA TWG, CC-BY-4.0, 72 pp.) is written for *authors of* tagged
PDF. Per the brief, each "do this when creating" is inverted here into "check for this /
recognize this pattern when consuming" — the shape a Marker-alternative structure-tree reader
needs. The guide itself avoids "shall" (2.6, p.6) except when quoting PDF/UA-1 verbatim; its own
guidance is "recommended" / "semantically appropriate" throughout, tagged **should** below unless
marked otherwise.

### 2.1 General provisions (clause 3, pp.7–11)

- **3.2 Fundamentals (p.7)** — the single load-bearing requirement, quoted verbatim from PDF/UA-1
  cl.7.1 ¶2: **"Content shall be marked in the structure tree with semantically appropriate tags
  in a logical reading order."** This is the standard a structure-tree **witness** is measured
  against, and it is exactly what File Portal's own audit tries to approximate with pymupdf text
  order — a tagged PDF's own `StructTreeRoot`, read via depth-first traversal (3.2.2, p.8), *is*
  that logical reading order, author-asserted, for any PDF whose author actually tagged
  correctly. This is the crux of the pipeline question this brief opens: for a tagged PDF, the
  structure tree is a **stronger** reading-order witness than pymupdf's positional text
  extraction, which has no concept of logical (vs. visual/positional) order at all.
- **3.2.3 Unicode mapping (p.8)**: text **must** map to Unicode (32000-1, 14.8.2.4.2); where no
  mapping exists (e.g. a logo encoded as text) mapping to the Unicode Private Use Area is the only
  PDF/UA-1-conformant fallback, but this **loses semantic information** — `Alt`/`ActualText`
  should be used to recover it. **Converter check**: PUA codepoints (U+E000–U+F8FF) in extracted
  text are a signal to look for a sibling `Alt`/`ActualText` property rather than trust the raw
  codepoint.
- **3.4 Content spanning pages (p.9)**: a single logical paragraph split across two pages is
  **one** `<P>` structure element referenced by two separate marked-content sequences — the
  structure tree does not restart at a page break. **Converter check**: never assume one structure
  element = one page; join by structure-element identity, not by page.
  - **3.5 Empty structure elements (p.9)**: these are semantically acceptable to be empty: `TD`
  (maintain table structure), `LI` (maintain list structure), `Span` (ActualText for whitespace;
  metadata/attributes), `Div` (metadata/attributes only), `Document` (single blank-page doc),
  `NonStruct`/`Private` (arbitrary tagsets). All other types being empty is "semantically
  inappropriate" but the guide warns real-world files do it anyway and readers "should" handle it.
  **Converter check**: an empty `TD`/`LI` is not a defect signal; an empty `Figure`/`P`/`Table`
  probably is.
- **3.6 Role maps (pp.9–10)**: custom structure types **require** (implicit shall, quoting
  32000-1 Table 322) a `RoleMap` entry mapping them to a semantically-appropriate standard type.
  **Converter check**: resolve `RoleMap` before classifying any structure element — a
  `<DataTable>` role-mapped to `<Table>` should be treated as a `Table`, not skipped as unknown.
- **3.7 Artifacts (p.10)**: content marked `/Artifact` is explicitly **not** "real content" (page
  numbers, running headers/footers, decorative borders). "It is semantically inappropriate to
  contain semantic content within a marked content sequence tagged as artifact." **Converter
  check**: `/Artifact`-marked content is deliberately excluded from the reading-order witness —
  its *absence* from the structure tree is correct, not a coverage gap. 3.7.2 (p.10): page
  numbers specifically **must** be marked `Artifact` with a `Pagination` property-list entry.

### 2.2 Per-structure-type guidance, inverted (clause 4, pp.11–53)

Grouping elements (4.1, pp.11–20):
- **`Part`/`Art`/`Sect`/`Div`** (4.1.1, p.11): no detailed semantic-selection guidance exists in
  either ISO 32000-1 or PDF/UA — a converter **cannot** distinguish these four by structural
  position alone; treat as a nested-sectioning hierarchy of decreasing granularity with no fixed
  semantic meaning to recover, except `Div` = "a division... without semantic intent" (i.e. `Div`
  is the layout-only grouping element, closest analog to a converter's own synthetic wrapper).
- **`BlockQuote`** (4.1.2, p.12): block-level quote; can be used as either a plain block or a
  grouping element containing multiple `P`s. No structural marker distinguishes source; consumers
  "should" render distinguishably (styling / TTS voice change) — a converter emitting Markdown
  should use `>` blockquote syntax regardless of internal substructure.
- **`Caption`** (4.1.3, pp.13–14): **positional rule is load-bearing.** For `Table`/`L`/`TOC`,
  `Caption` **must be the first or last direct child** (only those two positions are legal — this
  becomes an explicit **shall** in PDF 2.0, Annex B A.3.2.2, p.70: "The Caption shall be the first
  or the last structure element inside its parent structure element. The number of captions cannot
  exceed 1."). For `Figure` (which current AT does not expect to have child structure elements),
  `Caption` is expected as an **immediately-adjacent sibling**, before or after. **Converter
  check**: to associate a caption with a `Figure`, `L`, `Table`, or `Formula`, check first/last
  child *and* immediately-preceding/following sibling — both patterns are valid and the guide
  explicitly recommends processors assume the association in either case (4.1.3.3, p.14).
- **`TOC`/`TOCI`** (4.1.4, pp.15–16): distinguished from `L`/`LI` by providing *references into
  the document* rather than distinct content — semantically closer to a navigation index than a
  list. No cap on the number of TOCs in one document (e.g. one for chapters, one for figures).
  **Deviation from spec the guide flags explicitly**: PDF 1.7 does **not** permit `Link` as a
  direct child of `TOCI` (32000-1 spec text), but the guide says "commonly do exist" anyway and
  processors "should" expect to encounter them (4.1.4.2/4.1.4.4, p.16) — a real-world-common
  violation the converter must tolerate, not reject.
- **`Index`** (4.1.5, pp.17–18): any structure type may in principle appear inside; typically
  organized as `L`/`LI` with a `Lbl` per letter/topic-group; heading elements inside `Index` are
  discouraged (to avoid confusion with the main body's TOC) though not forbidden.
- **`NonStruct`** (4.1.6, p.19): "has no substantive role or meaning" *for the element itself*,
  but its **children's** content and structure are real and significant — a converter **must
  recurse into** `NonStruct` and pass its children through, just skip attaching semantics to the
  `NonStruct` wrapper itself. Chiefly used to role-map otherwise-unmappable custom types.
- **`Private`** (4.1.7, p.20): unlike `NonStruct`, **both** the element and all its
  descendants/content are to be ignored by consumers — matches TS 32005 5.5.2.2's "may be ignored
  by processors" language exactly. **Converter check**: `Private` subtrees are a legitimate,
  intentional skip — do not flag their content as "missing" in a fidelity audit.

Block-level elements (4.2, pp.21–46):
- **`P`** (4.2.1, p.21): the default/fallback type — "a good backup choice when no other structure
  type is semantically appropriate, or as a fallback in role-mapping." One `P` = one paragraph;
  multiple paragraphs wrapped in a single `P`, or `P`s directly nested inside each other, are both
  "semantically inappropriate" (converter-side: treat nested/merged `P`s as a producer defect to
  flag, not a structure to preserve as-is).
- **`H1`–`H6`** (4.2.2, pp.22–25): PDF/UA-1 **requires** (real shall, quoting the standard)
  heading levels not be skipped, but the guide concedes well-structured real documents violate
  this and recommends tolerating it rather than rejecting the file. `H7`+ is **required** by
  PDF/UA-1 where semantically appropriate but undefined in PDF 1.7 — such levels **must** be
  role-mapped, either to `P` (if misrepresenting as a heading is worse) or to `H6` (if losing
  heading-ness is worse) — a genuine either/or the guide leaves to the mapper's judgment, not a
  fixed rule. **No subheading structure type exists** — subheadings use `P`/`Span` inside or
  after the `H#`. **Document titles have no dedicated PDF 1.7 structure type** — `H1` is the
  common convention but is *not* required to be unique to the title; if `H1` doubles as the title,
  only one `H1` may exist in the whole document for that usage to be valid (Example D, p.24) —
  otherwise multiple `H1`s are fine (Examples A–C). **Converter check for title detection**: the
  presence of exactly one `H1` in a document is a **weak** signal it may be the title, not
  conclusive; PDF 2.0 defines an explicit `Title` type role-mapped to `P` as the forward-looking
  convention (4.2.2.5, p.25; BPG Annex B A.3.2.1, p.69-70) — check `RoleMap` for a custom
  `Title`-named type mapped to `P` as a stronger signal. **WARNING (p.25)**: some PDF/UA tools
  insert **empty heading elements** purely to avoid a level-skip appearance — "this behavior
  cannot result in conformance" and a converter should treat an empty `H#` as noise, not content.
- **`H`** (4.2.3, p.26): "impractical" due to lack of tooling support; "use is not recommended."
  Effectively dead in practice — a converter encountering it should not expect rich guidance to
  exist for its handling elsewhere.
- **`Lbl`** (4.2.4, p.27): despite being *described* as block-level in PDF 1.7, it is "always an
  inline-level element in practice" (an acknowledged **spec defect, corrected in PDF 2.0**). Used
  far more broadly than HTML's `<label>` — any content that labels other content (bullets, list
  numbers, TOC chapter numbers, footnote markers, table-of-contents labels), always explicitly
  contained (unlike HTML where list markers are implied by list-type, not tagged).
- **`L`/`LI`/`LBody`** (4.2.5, pp.28–31): canonical structure is `L{ Caption?, LI{ Lbl?, LBody } }`
  with `Caption` (if present) **required to precede** all `LI`s (32000-1/PDF-UA-1 requirement,
  p.28). **The spec does not prohibit other nestings** and the guide explicitly says processors
  "should be able to handle various forms" including (a) an `LBody` whose content is itself an
  unrelated nested `L` (structurally sound), and (b) the HTML-borrowed but "incorrect" pattern of
  `L{ LI{ L{...} } }` (list nested directly inside `LI` without an intervening `LBody`) — the
  guide names this explicitly as commonly-encountered-but-wrong, so a converter should still parse
  it rather than reject. Consumers "should" treat bare content found as a direct `LI` child (no
  `LBody` wrapper) as if it were wrapped in one (4.2.5.3, p.31) — real-world tolerance rule.
- **`Table`/`TR`/`TH`/`TD`/`THead`/`TBody`/`TFoot`** (4.2.6, pp.32-33): **hard rules for a
  fidelity check**: (1) tables spanning multiple pages **must** be structured as one single
  `Table`, not several; (2) `TH` cells that are a *repeated header row/column* (pagination
  artifact of a multi-page table) **must be marked `Artifact`**, not left as live `TH` — so a
  witness that finds "duplicate header rows" in a multi-page table's structure tree is seeing a
  spec violation, not a repeated real header; (3) empty cells are **always** `TD`, never empty
  `TH`; (4) cells spanning rows/cols **require** `ColSpan`/`RowSpan` attributes — their absence
  on a visually-merged cell is a detectable defect; (5) an empty row/column used purely to
  visually separate two semantically-distinct tables is "semantically impermissible" — that
  pattern in the wild indicates the producer collapsed two tables into one `Table` element
  incorrectly, a defect the structure tree will *not* self-report (the table-ness is asserted, not
  derivable). `THead`/`TBody`/`TFoot` exist "primarily... to aid consuming software in
  repurposing paginated tables" — optional, not required for correctness.
- **`Span`** (4.2.7, p.34): no inherent semantics of its own; exists purely as an attribute
  carrier (`Lang`, `ActualText`, `Alt`, `E`, layout attributes). A converter should never expect
  `Span` alone to convey meaning — always inspect its attributes.
- **`Note`** (4.2.8, pp.35–38): footnote/endnote. Two competing real-world patterns exist and
  **both must be handled**: (A) `Note` nested as a **child of `Reference`'s containing
  structure**, appearing inline right after the `Reference` in reading order — canonical/preferred
  (4.2.8.1 Ex.A); (B) `Note` as a **sibling immediately following** the referencing structure
  element, *not* inside it — explicitly flagged as "not official, but well-known and otherwise
  high-quality agents are known to use this work-around" (Ex.B, p.36) — **converter must support
  both**. Association algorithm given explicitly (4.2.8.4, p.37): from a `Reference`'s `Lbl`
  content, **search forward** in reading order for the first `Note` whose own `Lbl` has matching
  content; reliable only when the label isn't reused elsewhere or the matching `Note` follows in
  reading order. This is a concrete, implementable cross-reference-resolution algorithm a
  converter can lift directly.
- **`Reference`** (4.2.9, pp.38–39): a `Reference` **containing** a `Lbl` child = points to a
  footnote/endnote/bibliography target (match by `Lbl` content, per above). A `Reference`
  **without** a `Lbl` child = a plain cross-reference (also the pattern inside `TOCI`/`Index`).
  This Lbl-presence test is the converter's disambiguation rule.
- **`BibEntry`** (4.2.10, p.40) / **`Code`** (4.2.11, p.41): both explicitly "support... by AT is
  not anticipated" — low real-world tooling investment, treat as thin wrappers (group-for-reuse
  only; `Code` implies "preferably represented precisely, without further modification" i.e.
  preserve whitespace/formatting literally, matching Markdown fenced-code semantics well).
- **`Link`** (4.2.12, pp.42–44): does **not** require enclosed content (PDF/UA-1). Multiple OBJRs
  (object references to annotations) inside one `Link` "should" share the same action — common
  when a URL wraps across lines and QuadPoints aren't used, generating several link annotations
  for one logical link; consumers should collapse these to a single presented link when targets
  match (4.2.12.3, p.43). For links spanning a page break, OBJRs "should" be logically adjacent.
- **`Annot`** (4.2.13, pp.45): wraps non-link, non-widget annotations. Markup annotations enclose
  both the marked-up content *and* an OBJR to the actual annotation (may nest); other annotation
  types typically enclose only the OBJR. Consumers should surface both the `Contents` key
  (annotation) and the `Alt` property (enclosing structure element) without duplicating — avoid
  presenting the same alt text twice.
- **`Quote`** (4.2.14, p.46): the **inline** counterpart to `BlockQuote` — inside a paragraph
  vs. a standalone block. Selection rule is purely "is this quote inside a paragraph/block
  element, or not."
- **`Ruby`/`RB`/`RT`/`RP`/`Warichu`/`WT`/`WP`** (4.2.15, p.47): Japanese-typography-specific;
  **"No guidance provided at this time."** Confirms these are out of scope for File Portal's
  English-language specimen set at the BPG's own admission, consistent with Part 1.6's
  low-confidence flag on the same cluster in Table 5.

Illustration elements (4.3, pp.48–53):
- **`Figure`** (4.3.1, pp.48–49): no PDF-1.7 mechanism to formally associate a `Figure` with its
  `Caption`, or group multiple figures under one caption — purely positional convention (adjacent
  sibling, as above). `Figure` without any `Caption` is common and legitimate (logos, decorative
  inline graphics). Both `Caption` and the `Figure`'s own `Alt` property "should" be surfaced to
  the user — **they are not redundant**, `Alt` is a substitute description, `Caption` is
  supplementary real content; a converter that only extracts one is dropping information the
  other doesn't carry.
- **`Formula`** (4.3.2, p.50): not math-only — usable for chemistry/physics too. **`Formula`
  requires an `Alt` attribute** (PDF/UA-1, real shall, cited as "PDF/UA-1, 7.7"). Individual
  symbols may or may not be separately wrapped depending on context. **Known ambiguity the
  converter must expect**: English usage of "figure" for a mathematical formula means math is
  "quite often" mis-tagged as `Figure` instead of `Formula` — semantically incorrect but common;
  processors "should be prepared to encounter this case" (4.3.2.3, p.50). **Converter check**:
  when auditing/witnessing formula content, check both `Formula` and `Figure`-typed elements for
  math-shaped `Alt` text.
- **`Form`** (4.3.3, pp.51–54): each `Form` structure element wraps exactly **one widget
  annotation**; a multi-widget field (e.g. a two-button radio group) needs multiple `Form`
  elements, tied together only by the AcroForm `T` (field name) key — **not** by any structure-tree
  relationship. No PDF mechanism formally links a `Lbl` to its `Form` field beyond adjacency/
  ordering. Out of scope for File Portal's document-conversion use case (no interactive forms
  expected in the specimen set) — noted for completeness only.

### 2.3 Attributes and properties (clause 5, pp.54–65)

**5.1 Layout attributes — Table 1 requirement levels (pp.54–58)**, condensed (three-tier scale:
Required / Required-if-semantic / Not required):

| Attribute | Applies to | Requirement | Default |
|---|---|---|---|
| `Placement` | any | Not required | Inline |
| `WritingMode` | any | **Required** | LrTb |
| `BackgroundColor` | any | Required if semantic | none |
| `BorderColor` | any | Required if semantic | current fill color |
| `BorderStyle` | any | Required if semantic | None |
| `BorderThickness` | any | Required if semantic | — |
| `Color` | any | Required if semantic | current fill color |
| `Padding` | any | Not required | — |
| `SpaceBefore`/`SpaceAfter` | BLSE / non-inline ILSE | Required if semantic | 0 |
| `StartIndent`/`EndIndent` | BLSE / non-inline ILSE | Required if semantic | 0 |
| `TextIndent`/`TextAlign` | BLSE containing text | Not required | — |
| `BBox` | Figure, Formula, Table | **Required** | — (AT often relies on this) |
| `Width`/`Height` | Figure/Formula/Table, TH/TD | Not required | — |
| `BlockAlign`/`InlineAlign` | TH/TD | Not required | — |
| `TBorderStyle` | TH/TD | Required if semantic | None |
| `TPadding` | TH/TD | Not required | — |
| `LineHeight` | ILSE / content-bearing BLSE | Not required | — |
| `BaselineShift` | ILSE / content-bearing BLSE | Required if semantic (e.g. super/subscript) | 0 |
| `TextDecorationColor` | ILSE / content-bearing BLSE | **Required** | current fill color |
| `TextDecorationThickness` | ILSE / content-bearing BLSE | Required if semantic | current stroke thickness |
| `TextDecorationType` | ILSE / content-bearing BLSE | **Required** | None |
| `RubyAlign`/`RubyPosition` | ILSE / content-bearing BLSE | Not required | — |
| `GlyphOrientationVertical` | ILSE / content-bearing BLSE | Required if semantic | Auto |

**5.1.2 Table 2 (p.58)**: `ColumnCount`/`ColumnGap`/`ColumnWidths` (grouping elements with
columns) — not required. `ListNumbering` (on `L`) — required if not `None`. `PrintField` `Role`/
`Checked`/`Desc` — all required (for flattened/pre-filled forms).

**5.2 ListNumbering (p.58)**: value `None` strongly implies the list uses `Lbl` content as
arbitrary/non-enumerated labels (HTML `<dl>`-analog) — a converter mapping to Markdown should
treat a `None`-numbered list as a definition list, not a bulleted/numbered one.

**5.4 Table attributes (pp.59–60)**: `Scope` is the simple case (row/column headers via keyboard
navigation convention: right-arrow=Row, down-arrow=Column). For complex/nested table headers,
`Headers`+`ID` are required — a `TH`'s `Headers` entry enumerates the `ID`s of cells it heads,
enabling nested header hierarchies. **Converter check**: presence of `Headers`/`ID` vs. bare
`Scope` signals simple-vs-complex table structure and which reconstruction strategy to use.

**5.5 Content properties (pp.60–65)** — the four keys, and this is the section most relevant to
SYM-053 (asset reference exists but the underlying content/words are gone):

| Property | Purpose |
|---|---|
| `Lang` | natural language of content + of `E`/`Alt`/`ActualText` values in the same context |
| `Alt` | alternate description for content with a **substantial non-textual** aspect |
| `ActualText` | the literal text a visually-text-perceived-but-not-text-encoded object represents |
| `E` | expansion of an abbreviation/acronym |

- **`Alt` vs. `ActualText` — the disambiguation rule (5.5.2/5.5.3, pp.61–63)**: `Alt` describes
  something whose appearance is fundamentally *not text* (a photo, a pie chart, clip art) — use
  depends on **visual appearance**, not underlying object type (ASCII art is visually a picture
  and needs `Alt` despite being literal characters). `ActualText` is for something **perceived as
  text** but not encoded as text (an image of a single word/character, hyphenation artifacts like
  "Dru-cker"→"ck" spanning a line break). Where **both** occur on one element, **both must be
  surfaced to the user** — they are not alternates of each other. Text-as-image should get
  `ActualText`, not `Alt` — "the Alt property is semantically inappropriate in this case and
  should be not defined" (5.5.2, p.61).
- **Scanned pages (5.5.3.1, p.65)**: "The use of either Alt or ActualText on a scanned page is
  almost always semantically inappropriate." The correct pattern is an invisible OCR text layer
  (render mode 3) positionally matching the scan, structured normally — **this directly explains
  the converter's existing render-mode-3 OCR-layer detection** (docs: segment-convert-marker
  engine table; SYM-054's font-name-regex heuristic) as the spec-sanctioned mechanism, not a
  workaround. Each semantically-significant figure *on* a scanned page should still get its own
  `Figure` wrapper.
- **Order of preference when text can't be encoded as real text objects (5.5.3.1, p.65)**: (1)
  `ActualText` on the content itself; (2) `ActualText` on an *empty* structure element, reserved
  specifically for whitespace characters. `ActualText` is scoped to content "that would otherwise
  be contained within a single structure element" (NOTE 2, p.65) — it does not span elements.
- **Symbolic/PUA caution (6.2, p.66)**: Unicode PUA usage is "discouraged, as no predefined
  meaning is associated with Unicode values in the PUA" — reinforces the 3.2.3 converter check
  above (PUA codepoint present ⇒ look for `ActualText`/`Alt` sibling, don't trust the codepoint's
  visual glyph as the meaning).

### 2.4 Other features + editing (clauses 6–8, pp.66–67)

- **6.1 Superscript/subscript (p.66)**: PDF 1.7 tagged PDF has **no explicit superscript/
  subscript semantic** — only the `BaselineShift` attribute as an unreliable proxy (text can shift
  for other reasons too). A converter cannot reliably detect super/subscript from tagging alone.
- **7.1 Digital signatures (pp.66–67)**: signature fields are often made functionally invisible
  (`/Rect [0 0 0 0]`) and per 7.1.1 (p.66, citing PDF/UA-1 cl.8.6) do **not** have to be included
  in the structure tree when zero-size/hidden/outside CropBox — readers must still provide
  separate-UI access, not force them into reading order. Out of scope for a Markdown-conversion
  pipeline; noted because it explains why a signature might be entirely absent from the structure
  tree without that being a defect.
- **Clause 8, Editing (p.67)**: merging/splitting tagged PDFs "requires that structure elements...
  connected with page content objects be handled appropriately"; deletion of content "should"
  cascade to deletion of the corresponding structure elements. Relevant only if File Portal ever
  mutates PDFs rather than just reading them (currently out of scope).

### 2.5 Annex A — the PDF/UA flag (p.68)

A minimal, directly-greppable XMP conformance signal: `pdfuaid:part` = `1` inside an
`rdf:Description` using namespace `http://www.aiim.org/pdfua/ns/id/`, alongside a mandatory
`dc:title`. **Checkable property**: presence of `pdfuaid:part` in document XMP is a strong,
narrowly-scoped conformance claim (unlike the broad PDF-Declarations bag) — specifically a claim
of PDF/UA-1 (accessibility) conformance, i.e. the producer is asserting exactly the "structure
tree is a trustworthy reading-order witness" property this brief is investigating.

### 2.6 Annex B — PDF 2.0 differences (pp.69–71)

- **A.1 (p.69)**: the Tagged-PDF data model is **unchanged** between 1.7 and 2.0 — same
  fundamental mechanism, richer typing. Key deltas: new PDF 2.0 namespace with new types; some
  1.7 types are **absent** from the 2.0 namespace (must fall back to the 1.7 namespace for those,
  per TS 32005 pt.1 above); many redefined element semantics; **explicit, complete parent-child
  rules** (vs. PDF 1.7's comparatively loose/undocumented rules) — this is precisely Table 5's
  origin story. MathML becomes a first-class PDF 2.0 namespace. Artifacts/Alt/ActualText concepts
  are "improved"; new artifact subtypes added; pronunciation hints become possible.
- **A.2 Namespaces (p.69)**: PDF 2.0's namespace mechanism additionally allows wiring in
  **external** vocabularies beyond ISO 32000 itself — named examples are Chemical Markup Language
  (CML) and Standard Music Description Language (SMDL). A converter parsing `NS` dictionaries
  should not assume every namespace URI is one of the two ISO ones.
- **A.3 (pp.69–71)**: the guide's own explicit recommendation — "it is strongly recommended that
  developers implementing PDF 1.7 also avail themselves of PDF 2.0, and especially Annex L
  therein" — i.e. even a PDF-1.7-only converter should use the PDF 2.0 containment rules (=
  Table 5 above) as best practice, not just for 2.0 files.
  - `H1`–`H6` (A.3.2.1, p.70): reiterates the `Title`-role-mapped-to-`P` forward-compatibility
    pattern from 4.2.2.5 — upgrading to PDF 2.0 later becomes "simply... deletion of this role
    map" once `Title` is a first-class type.
  - `Caption` (A.3.2.2, p.70): PDF 2.0 makes the first/last-child-only, ≤1-per-parent rule
    **explicit and normative** ("shall be the first or the last... The number of captions cannot
    exceed 1") where PDF 1.7 left it as convention only (see 4.1.3 above).
  - `Note`/`Reference` (A.3.2.3, pp.70–71): PDF 2.0 adds an explicit `Ref` key on the structure
    element dictionary to formally link a `Reference` to its `Note`, replacing the
    matching-`Lbl`-content heuristic from 4.2.8/4.2.9 with a direct pointer. `Reference` itself
    is **not** a PDF 2.0-namespace type (it stays PDF-1.7-only) but PDF 2.0 readers are required
    to support the PDF 1.7 default namespace regardless, and `Reference`+`Ref` can be combined
    for a namespace-hybrid element that works either way.

---

## PART 3 — Extensions triage

### 3.1 PDF Declarations (2019, PDF Association, CC-BY-4.0, 10 pp.) — MATTERS

A companion mechanism (not an ISO standard) for a PDF to **self-assert conformance** to any
external standard/profile via machine-readable XMP, independent of PDF technology itself. Two
lines: **matters directly** — it is the generic conformance-signal mechanism that TS 32005's own
Table 1 (Part 1.3 above) and the PDF/UA flag (Part 2.5 above) both instantiate, and a converter
wanting a fast pre-check of "does this PDF claim to be well-tagged" before trusting its structure
tree as witness should look here first.

- **Mechanism (cl.7, p.3)**: XMP inside the document's `Metadata` catalog entry (or elsewhere),
  namespace `http://pdfa.org/declarations/`, prefix `pdfd`. Root property `pdfd:declarations` is
  an **unordered `rdf:Bag`** of `Declaration` structures (Table 1, p.4, **required**), each with
  `pdfd:conformsTo` (URI, **required**) and optional `pdfd:claimData` (an array of `ClaimData`:
  `claimBy`, `claimDate`, `claimCredentials`, `claimReport` — all optional, Table 3, pp.5–6).
- **Scope rule (cl.7, p.3)**: claims at **document-level** metadata apply to the whole document
  but *not* to embedded/referenced content; claims at **object-level** metadata apply only to that
  object. A document may carry multiple claims at both levels simultaneously.
- **Explicit non-guarantee (cl.1, p.1, cl.2, p.1)**: "the presence of a PDF Declaration does not
  guarantee that the document conforms" — a malicious or simply inaccurate declaration is
  explicitly out of scope of the spec's own guarantees. **This is the single most important
  epistemic caveat for File Portal**: any conformance signal read this way is an **assertion by
  the producer**, tagged `Intended` at best, never `Verified`, until independently checked.
- **PDF/A context (cl.9, p.6)**: using PDF Declarations inside a PDF/A file requires an additional
  PDF/A extension-schema entry in the XMP.

### 3.2 AN001 — Black Point Compensation (2018, 5 pp.) — DOES NOT MATTER

Two lines: purely a **print/color-management** feature (`UseBlackPtComp` key in a graphics-state
parameter dictionary, values `ON`/`OFF`/`Default`) governing shadow-tone rendering intent for
print output. No relationship to structure, tagging, text extraction, or content fidelity —
confirmed by reading the full 5-page document; nothing here touches anything a Markdown converter
would ever encounter or need.

### 3.3 AN002 — Associated Files (2018, 10 pp.) — MATTERS, potentially significantly

Two lines up front: **this is a real find for the reconstruction-vs-witness question.** Associated
Files (32000-2, 14.13) let a PDF object — including a specific **structure element**, not just the
document as a whole — carry a machine-readable, typed link to an embedded or referenced file that
represents the *same content in another form*. For File Portal specifically: a `Figure` whose
underlying chart data or line-art source is embedded as an Associated File is recoverable
**losslessly**, without OCR or vision-model reconstruction, if the converter reads `AF` entries.

- **Mechanism (cl.2–3, pp.2–3)**: an `AF` entry on a PDF object (document catalog, page,
  annotation, XObject, or **structure element**) points to one or more file-specification
  dictionaries. Each carries a **required** `AFRelationship` entry, one of: `Source`, `Data`,
  `Alternative`, `Supplement`, `EncryptedPayload`, `FormData`, `Schema`, `Unspecified`, or a
  custom value. Embedded (as opposed to referenced/external) Associated Files additionally
  **require** a MIME-type `Subtype` entry (RFC 8118) and, if `Params` is present, **shall**
  specify the file's last-modified date.
- **The two use cases that matter most to a converter (cl.6, p.7)**:
  - **4.2.2 Equations (p.7)**: a `Figure` or Formula-bearing structure element associated with an
    embedded **MathML** file, `AFRelationship = Alternative`. If present, this is a **direct,
    machine-readable formula source** — strictly better than OCR/vision reconstruction of a
    rendered equation image, and directly relevant to BPG 4.3.2's guidance (Part 2.2 above) that
    `Formula` content is "quite often" mis-tagged as `Figure`.
  - **4.2.3 Graphs and charts (p.7)**: the **source data** behind a graph/chart may be an
    Associated File on the graphic object itself, `AFRelationship = Data`. This is the exact
    inverse of SYM-053 (an asset reference exists but the visual is blank/the words are gone) —
    if `Data`-relationship Associated Files exist, the underlying numbers survive independent of
    whatever happened to the rendered image.
  - **4.2.4 Line art figures (p.7)**: an alternative **SVG** representation of a line-art
    `Figure`, `AFRelationship = Alternative`, associated via `AF` on the structure element
    dictionary directly. Multiple Associated Files with different relationship values can coexist
    on one figure (e.g. both `Data` for the source numbers and `Alternative` for an SVG
    rendering).
- **Where to look (cl.6.1–6.2, pp.8–9)**: **most current implementations only associate at the
  document-catalog level** (`AF` entry in the catalog, cl.4.1, pp.4–6: whole-document source file,
  hybrid machine-readable data, packaged documents, archived emails, encrypted payloads) — the
  **object-level** association (cl.4.2, pp.6–7, where the Equations/Charts/Line-art cases above
  live) is explicitly the **less common** pattern; the guide itself frames catalog-level as "most"
  and object-level as the additional capability. **Practical implication**: don't assume absence
  of a document-level `AF` entry means no Associated Files exist — a converter must separately
  check for `AF` entries on individual structure-element dictionaries and XObjects, not just the
  catalog. There is no single "list all Associated Files" shortcut other than a full-tree walk
  (or the `EmbeddedFiles` name-tree cross-check, cl.6.1, p.8) — **PDF writers are recommended to
  additionally register every embedded file in the `EmbeddedFiles` names-tree entry precisely so
  that non-`AF`-aware consumers can still enumerate them** (cl.6.1, p.8) — a converter unaware of
  Associated Files semantics can still discover the raw files via that tree and correlate by
  filename/object reference afterward.
- **Risk noted by the spec itself (cl.5, p.8)**: `AF` entries can be silently dropped by a PDF
  editor that doesn't understand Associated Files when it re-saves a modified file — so their
  *absence* in a re-saved/processed PDF is not proof the original never had them.

### 3.4 AN003 — Metadata stream locations (2021, 10 pp.) — LOW RELEVANCE, one useful fact

Two lines: mostly a "where does XMP metadata live for object type X" reference (fonts, tiling/
shading patterns, marked content, structure elements, embedded files, Type 3 fonts, annotations,
optional content, rich media, 3D) — a producer/consumer interoperability note that doesn't change
what a converter extracts. One fact worth keeping: **structure elements themselves may carry a
`Metadata` XMP stream** (Table 5, p.9 of that doc, citing 32000-2 14.8.4.3/Table 355) — "usually
only used on document-level structure types" (`Document`/`DocumentFragment`) to embed metadata for
a logical sub-document nested inside a larger tagged PDF, but the mechanism is not formally
restricted to those types. Also useful: **object-level metadata for Associated Files belongs on
the file-specification dictionary itself** (p.8, cl. Marked content) — reinforces where to look
when correlating AN002's `AF`/`AFRelationship` data with any accompanying description metadata.

### 3.5 TS 32001 / TS 32002 / TS 32003 — cryptographic extensions — DO NOT MATTER

All three are confirmed, by reading each in full (4 printed pages of substantive content each; the
rest is ISO front/back matter), to be pure **digital-signature and encryption** extensions to
32000-2, and each states its own scope exclusions in near-identical language: "This document does
not specify... specific processes for converting paper or electronic documents to the PDF file
format... rendering... conformance validation..." (verbatim in all three Scope clauses).

- **TS 32001** (Scope cl.1): adds SHA3-256/384/512 and SHAKE256 as permitted `DigestMethod`/
  message-digest values for signature fields and signature dictionaries (extends 32000-2 Tables
  237, 256, 260).
- **TS 32002** (Scope cl.1): adds NIST P-curve, Brainpool, and Ed448/Ed25519 elliptic-curve
  families as signature algorithms.
- **TS 32003** (Scope cl.1): adds AES-GCM as an `Encrypt`-dictionary encryption filter (extends
  32000-2's `Filter`/`CF` mechanism).

None of the three touch the structure tree, tagging, content extraction, or reading order. The
**one operationally relevant residue**: if any File Portal specimen PDF is **encrypted** (using
AES-GCM per TS 32003) or carries a signature using one of these newer algorithms, pymupdf/
Marker's ability to even **open** the file for text/structure extraction depends on the PDF
library's support for these specific algorithms — a decryption/library-compatibility concern, not
a content-fidelity one, and out of this slice's remit to verify (no specimen PDF was checked for
encryption as part of this task — see Residue).

---

## Summary — direct answers to the pipeline's open question

1. **A tagged PDF's structure tree is a stronger reading-order witness than pymupdf's positional
   text extraction** for any document where BPG 3.2/PDF/UA-1's fundamental requirement was
   actually honored by the producer — the structure tree encodes *logical* order via depth-first
   traversal (BPG 3.2.2), which positional extraction cannot represent at all. This is not
   automatically true for every tagged PDF (the tag could be wrong/missing), so it is a
   **candidate witness to cross-check against**, not a blind replacement — exactly File Portal's
   own framing.
2. **TS 32005 Table 5 (Part 1.6) is the containment-validity checker** a converter needs to tell
   "is this parent/child nesting the structure tree claims actually legal" — usable as a
   negative-control gate (a nesting Table 5 marks `∅*`/absent is a tagging defect in the source,
   not something to silently accept as ground truth).
3. **Associated Files (Part 3.3) can defeat SYM-053 outright** for any specimen PDF that used them
   on figures/formulas/charts: `AFRelationship = Data`/`Alternative` on a structure element is a
   direct, lossless alternative to OCR/vision reconstruction — worth a one-time scan of all 16
   specimens for `AF` entries (document-catalog **and** object-level) before concluding the visual
   pipeline is the only source of figure content.
4. **`Alt`/`ActualText`/`Lang`/`E` (BPG 5.5, Part 2.3) are the structured alternative to whatever
   the OCR-layer "majority vote" heuristic (SYM-054) is trying to approximate** — a properly
   tagged PDF states directly, per span, whether content is real text, an image-of-text needing
   `ActualText`, or a non-textual illustration needing `Alt`, which is a categorical improvement
   over inferring it from a font-name regex and an invisible-glyph ratio.
5. **PDF Declarations / the PDF/UA flag (Parts 2.5, 3.1) give a cheap, fast, but
   producer-asserted-only pre-check** — grep the XMP for `pdfuaid:part` or
   `pdfa.org/declarations#...` before doing anything expensive, but never trust the presence of
   either as proof; treat it as `Intended`, not `Verified`, per this project's own epistemic tags.
