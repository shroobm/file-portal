# PDF/UA-1, PDF/UA-2 & WTPDF — dense conformance reference

Built from three full-text reads (no sampling) of the sold copies in
`scratchpad/pdfua/`: `pdfua1.txt` (ISO 14289-1:2014, 25 pp), `pdfua2.txt`
(ISO 14289-2:2024, 51 pp), `wtpdf.txt` (WTPDF 1.0, 2024-02, 57 pp). Page
citations below are the physical PDF page as marked by the `--------- PAGE
N ---------` breaks in those three source files (not the printed folio
number, which differs from PAGE N by the front-matter offset — folio "1" of
UA-1's body text is PAGE 8 of the file, etc.). Clause numbers are the
documents' own. **Every normative "shall/should/may" below is transcribed,
not paraphrased**, except where marked `(paraphrase)`.

Legend: **UA1** = ISO 14289-1:2014 · **UA2** = ISO 14289-2:2024 · **WT** =
WTPDF 1.0 · **WT-R** = WTPDF, tagged `[Conformance level for reuse]` ·
**WT-A** = WTPDF, tagged `[Conformance level for accessibility]` · **WT-∅**
= WTPDF baseline (both levels, no tag).

---

## 1. What each document is

**UA1 — ISO 14289-1:2014 (PDF/UA-1).** International Standard. Second
edition, cancels/replaces ISO 14289-1:2012. Status: **normative, ISO-IS**.
Scope (Cl.1, p.8): specifies the use of **ISO 32000-1:2008 (PDF 1.7)** to
produce accessible electronic documents. Governs: file format requirements
(what a conforming *file* must contain, Cl.7), conforming-*reader*
requirements (Cl.8), and conforming-*assistive-technology* requirements
(Cl.9). Explicitly out of scope (Cl.1): conversion processes, UI/rendering
design, physical storage, hardware/OS (p.8).

**UA2 — ISO 14289-2:2024 (PDF/UA-2).** International Standard, first
edition. Status: **normative, ISO-IS**; **does not replace UA1** — "This
document does not replace ISO 14289-1... this document provides normative
guidance based on ISO 32000-2" (Introduction, p.7). Scope (Cl.1, p.8):
specifies use of **ISO 32000-2:2020 (PDF 2.0)**. Same four out-of-scope
categories as UA1, plus two new exclusions: "requirements specific to
content (beyond facilitating programmatic access and textual
representation)" and "requirements applying to specific classes... of
documents" (p.8). Governs file-format requirements only (Cl.8) — **UA2 drops
UA1's separate reader/AT-requirement clauses (Cl.8–9 of UA1) entirely**;
UA2 is a file-conformance spec only. `(Observed: no Cl.9-equivalent "AT
requirements" or Cl.8-equivalent "conforming reader requirements" appear
anywhere in UA2's table of contents or body.)`

**WT — Well-Tagged PDF (WTPDF) 1.0.** PDF Association "Application Note,"
2024-02, CC-BY-4.0, authored jointly by the **PDF Reuse TWG & PDF/UA TWG**.
Status: **industry guide / association-published specification**, not an
ISO standard — normative in the sense that it defines shall/should/may
requirements and a formal conformance-declaration mechanism, but it is not
an International Standard and carries no ISO document number. Scope (Cl.2,
p.5, "not the content itself... does not mandate or restrict processing of
the document in any manner"): describes how to build PDF 2.0 files that are
**both reusable and accessible**, via two independently-declarable
conformance levels (Cl.6.1). Explicitly: "This specification describes a
usage of PDF 2.0 (ISO 32000-2) that is compatible with PDF/UA-2 (ISO
14289-2)" (Introduction, p.4/PAGE 4).

**Why WT exists (the reuse/accessibility split), in the document's own
words** (Introduction, p.4): "There is a large overlap between the
requirements for reuse and accessibility. However, some requirements are
critical for reuse whereas others are critical for accessibility. This
document clearly identifies the requirements for each use-case via a
conformance level mechanism." This is the load-bearing fact for File
Portal: **WT is not a strictly-stronger superset of UA2.** Its body text is,
clause-for-clause, close to word-identical to UA2 §8.2–8.14 (same
subclause numbers 8.2.5.2–8.2.5.33) — but roughly a dozen individual
requirements that are unconditional `shall`s in UA2 are downgraded in WT's
baseline text to `should`, becoming `shall` again **only** under the
`[Conformance level for accessibility]` tag (§7, below).

---

## 2. Version identification & conformance declaration (Cl.5 in UA1/UA2; Cl.6.1 in WT)

| | UA1 (Cl.5, p.10) | UA2 (Cl.5, p.9–10) | WT (Cl.6.1, p.7 / App.C p.53) |
|---|---|---|---|
| Mechanism | XMP schema `pdfuaid`, ns `http://www.aiim.org/pdfua/ns/id/` | same ns URI, same prefix | **PDF Declarations** mechanism (`pdfd`, ns `https://pdfa.org/declarations/`), a *different, extensible* mechanism, orthogonal to `pdfuaid` |
| Required properties | `pdfuaid:part` (int, required) | `pdfuaid:part` = **2** (shall), `pdfuaid:rev` = 4-digit year (shall) | `pdfd:conformsTo` = `http://pdfa.org/declarations/wtpdf/#reuse1.0` **and/or** `#accessibility1.0`, one `<rdf:li>` per claimed level |
| Optional properties | `pdfuaid:amd`, `pdfuaid:corr` | — (dropped; `rev` replaces amd/corr) | `pdfd:claimData` (claimBy, claimDate, claimCredentials, claimReport) |
| Self-disclaiming clause | "do not by themselves determine conformance" (p.10) | "do not determine conformity with this document by themselves; these criteria are specified in Clause 6" (p.10) | not explicitly restated for `pdfd`, but WT Cl.6.2 carries the same substantive "content is not thereby guaranteed accessible" disclaimer (p.8) |
| Bridge to UA2 | n/a | n/a | **App.C (normative, p.53)**: a file conforming to WT's accessibility level that *also* wants to claim UA2 conformance **shall** additionally carry the UA2 `pdfuaid` schema (part=2, rev=2024) — i.e. **claiming WT-accessibility does not by itself constitute claiming UA2**; the two metadata schemas are separate and both must be present to claim both |

**Checkable property**: a WT file claiming *only* `#reuse1.0` (no
`#accessibility1.0` declaration, no `pdfuaid` block) has made **no**
UA1/UA2 claim at all, regardless of how well-tagged it otherwise is.

---

## 3. Conformance requirements (Cl.6 in all three) — the umbrella clause

**UA1 Cl.6.2 (p.3):** "Conforming files shall adhere to all requirements of
ISO 32000-1:2008 as modified by this part of ISO 14289... A conforming file
shall contain PDF/UA version identification... A conforming file shall
adhere to all file format provisions in Clause 7." Plus: "Features described
in PDF specifications prior to ISO 32000-1:2008 which are not explicitly
defined in ISO 32000-1 **should not** be used" (should, not shall).

**UA2 Cl.6.2 (p.10–11)**, materially identical in structure but adds:
- "a file **shall** adhere to all requirements of ISO/TS 32005" (NEW — see
  §4 below on why)
- "a file **should not** contain any feature that is deprecated in ISO
  32000-2" (NEW; UA1 has no deprecation concept since PDF 1.7 predates it)
- "an embedded file, if necessary to the understanding of the document,
  **shall** be accessible according to objectively verifiable standards,
  e.g. WCAG 2.2. If such an embedded file is a PDF file, it **shall**
  conform to the ISO 14289 series" (NEW — UA1 only says embedded files
  "should" be accessible "in its own right," §7.11)
- Explicit **out-of-scope-of-conformance** list (p.11), absent from UA1:
  "Conformity to PDF/UA alone does not ensure that the content of a
  document is accessible. Cases not covered by PDF/UA include: — where
  authors have used colour or contrast in an inaccessible manner; — where
  ECMAScript... can generate inaccessible results; — where text content is
  potentially inaccessible to those with certain cognitive impairments; —
  whether a particular content item is real content or artifact content."
  **This is a load-bearing deviation from UA1**, which *did* regulate some
  of this content-level territory directly (UA1 §7.1 bans flicker/flash per
  WCAG 2.3 and bans conveying information "by contrast, colour, format or
  layout... unless the content is tagged to reflect all intended meaning" —
  both **absent from UA2's Cl.8 body**, confirmed by full read; UA2 instead
  refers these out to WCAG via the PDF Declarations mechanism, §7.2).

**WT Cl.6.2 (p.7–8)**: same three `shall`s (32000-2, TS 32005, WCAG for
non-PDF embeds) reproduced verbatim, with the WCAG/embedded-file shall
explicitly scoped `[Conformance level for accessibility]` (i.e. **not**
required for reuse-only conformance). Same out-of-scope list as UA2,
verbatim.

**Why ISO/TS 32005 conformance is a new *shall* in UA2/WT** (UA2 NOTE 3,
p.11, WT NOTE 3, p.7–8, both verbatim): "while ISO 32000-2 did not deprecate
any structure types defined in PDF 1.7, ISO 32000-2:2020, Annex L provided
containment rules only for structure types defined in the PDF 2.0
namespace. ISO/TS 32005 expands these containment rules to cover both the
PDF 2.0 namespace and those elements unique to the PDF 1.7 namespace. By
adhering to the requirements of ISO/TS 32005, it is possible to include
both PDF 2.0 and PDF 1.7 structure types in files that conform to this
document." **Practical consequence**: neither UA2 nor WT is fully
self-contained on containment rules — a conformance checker needs ISO/TS
32005 (not in this slice; `residue`) to validate parent/child legality for
the full structure-type set.

---

## 4. UA2 beyond UA1 — the explicit delta list

Everything below is present in UA2's Cl.7–8 with **no UA1 analogue**, or
is a **materially changed** requirement versus the UA1 clause of the same
subject. `(Observed` against a full read of both documents.)

1. **RISE principles** (UA2 §7.1, p.11–12): Reliable / Interoperable /
   Suitable / Equitable — an explicit accessibility philosophy, informative
   framing not present in UA1 at all.
2. **PDF Declarations mechanism** (UA2 §7.2.2, p.12): lets a UA2 file (or
   a portion, or a specific object) additionally claim conformance to
   *other* standards (WCAG 2.2, etc.) at arbitrary granularity, machine
   readable. No equivalent in UA1 (2014, predates the PDF Declarations
   spec, which is dated 2019).
3. **Document/DocumentFragment structure elements required** (§8.2.5.2,
   p.16): "The structure tree root... **shall** contain a single Document
   structure element as its only child... The namespace for that element
   shall be specified as the PDF 2.0 namespace." UA1 has no Document
   wrapper concept at all; UA1's structure tree root's children are
   whatever top-level tags the author used.
4. **H generic tag forbidden entirely** (§8.2.5.12, p.17): "Conforming
   files **shall** use the explicitly numbered heading structure types
   (H1-Hn) and **shall not** use the H structure type." UA1 §7.4.4 (p.9)
   instead **requires** H for "strongly structured documents" and forbids
   mixing (UA1: "All documents shall be either strongly or weakly
   structured, but not both"). **UA2 has no strongly/weakly-structured
   distinction at all** — dropped wholesale.
5. **No sequential-heading-level requirement** (§8.2.5.12 NOTE 2, p.17,
   verbatim): "Standards such as ISO 14289-1 include requirements on the
   use of sequential heading levels. This document does not... include
   such a requirement, but instead focuses on ensuring that correct
   semantics are provided." This directly **reverses** UA1 §7.4.2 (p.6),
   which is a hard three-bullet `shall`-set: H1 must be first if used;
   descending sequences must not skip a level (H1→H3 forbidden); level
   repeats and non-restarting increments are permitted. **A structure-first
   lane must not apply UA1's no-skip rule to a UA2/WT source file** — UA2
   heading level is instead validated by the requirement "Where a heading's
   level is evident, the heading level of the structure element enclosing
   it shall match that heading level" (§8.2.5.12, p.17) — a semantic-match
   test, not a sequence test.
6. **Full structure-type palette formalized** (§8.2.5.2–33, p.16–26): 32
   subclauses giving explicit shall/should requirements for Part, Art,
   Sect, Div, BlockQuote, TOC/TOCI, Aside, NonStruct, Sub, Lbl, Span, Quote,
   Em/Strong, Link/Reference, Annot, Form, Ruby, Warichu, List, Table,
   Caption, Figure, Formula, Index, BibEntry, Code, Artifact — full table
   in §6 below. UA1 by contrast only names Figure (§7.3), Headings (§7.4),
   Tables (§7.5), Lists (§7.6), Formula (§7.7), page headers/footers
   (§7.8), and Notes (§7.9) — a much smaller explicit set, deferring
   everything else to bare cross-reference into ISO 32000-1's tag tables.
7. **FENote replaces Note** (§8.2.5.14, p.17–18): "FENote effectively
   replaces the Note structure type specified in ISO 32000-1:2008,
   14.8.4.4.1. The Note standard structure type **shall not** be present in
   conforming files." Adds a dedicated `FENote` attribute owner (Table 2)
   with a `NoteType` key (`Footnote`/`Endnote`/`None`). UA1 §7.9 (p.7) only
   required a plain `Note` tag with a unique `ID`.
8. **Explicit layout structure-attribute regime** (§8.2.6.2, p.18–19):
   "structure elements **shall** include layout attributes in accordance
   with ISO 32000-2:2020, 14.8.5.4 to fully convey the semantics of a given
   use of colour, contrast, format or layout as necessary... Attributes
   **shall** be present when the relevant semantic property is present in
   the content, has semantic significance and differs from any default or
   inherited value." No analogue in UA1 whatsoever — UA1 §7.1 handles the
   colour/contrast/layout-semantics problem with a blanket ban instead
   ("Information shall not be conveyed by contrast, colour, format or
   layout... unless the content is tagged to reflect all intended
   meaning").
9. **ARIA/DPUB-ARIA role attributes** (§8.2.6.4, p.18–19): new
   `ARIA-1.1` attribute owner may extend or supply semantics on any
   structure element (e.g. `doc-bibliography`, `doc-glossary` roles). Not
   present in UA1.
10. **Table regularity mandated explicitly** (§8.2.5.26, p.20): "Tables
    **shall be regular**" and "Row groupings formed by THead, TBody and
    TFoot structure elements **shall be regular**" — both new. UA1 §7.5
    (p.6) never states a regularity requirement, only that tables "should
    include headers" and TH "should"/"shall" (conditionally) carry Scope.
11. **Headers-attribute completeness rule** (§8.2.5.26, p.20): "if the
    algorithm results in a header cell with an implicit or explicit Scope
    that cannot describe the header/cell relationships for all the cells
    in the table, then the Headers attribute **shall** be present for all
    cells to which a header applies" — with the explicit note "if the
    Headers attribute is used anywhere in the table, it is required for
    all cells in the table that have headers." No UA1 analogue (UA1's Scope
    requirement is the ceiling of its table-header regime).
12. **Real content vs Figure clarified — images-as-text need not be
    Figure** (§8.2.2 NOTE 7/EXAMPLE 8, p.13, verbatim): "Unlike ISO
    14289-1, this document clearly specifies that the use of images or
    vector-based drawings does not always require a Figure structure
    element... An image solely used to represent text with no illustrative
    purpose can be enclosed in a Span structure element with appropriate
    ActualText, as opposed to a Figure structure element." This is a
    **direct, named reversal** of UA1 §7.3 (p.5), which is unconditional:
    "Graphics objects, other than text objects, shall be tagged with a
    Figure tag."
13. **Per-annotation-type requirements, much finer-grained**
    (§8.9.2.4.1–20, p.26–29): 20 named subclauses (Text, Link, FreeText,
    Line/Square/Circle/Polygon/Polyline, TextMarkup, Caret, RubberStamp,
    Ink, Popup, FileAttachment, Sound/Movie, Screen, Widget, PrinterMark,
    TrapNetwork, Watermark, Redaction, Projection, 3D/RichMedia, Other) vs
    UA1's single general §7.18 (with light subtype carve-outs).
14. **Zero-size widgets forced to artifact** (§8.9.2.4.13, p.28): "a
    widget annotation of zero height and width **shall** be an artifact."
    New — explicitly framed around PAdES-B-LTA document-timestamp
    signature workflows (NOTE 1, p.28).
15. **Structure Destinations required for all intra-document links**
    (§8.8, p.24): "All destinations... whose target lies within the same
    document **shall** be structure destinations." UA1 has no equivalent
    clause; UA1 only regulates tab order via structure tree (§7.18.3).
16. **Form structure element cardinality** (§8.10.1, p.29): "A Form
    structure element **shall** enclose at most one widget annotation."
    New explicit constraint; UA1 §7.18.4 only requires nesting, not a
    1:1 cardinality bound.
17. **Deprecated-in-PDF-2.0 annotation types forbidden outright**: Sound,
    Movie (§8.9.2.4.11, "shall not be present"), TrapNetwork
    (§8.9.2.4.15). UA1's only comparable ban is TrapNet (§7.18.2), which
    UA2 also carries forward under its new "Trap network" subclause.
18. **XFA fully banned, not just dynamic XFA** (§8.10.1, p.29): "XFA
    forms... **shall not** be present." UA1 §7.15 (p.8) is materially
    weaker: "Static XFA forms **may** be used... Dynamic XFA forms
    **shall not** be used."
19. **No security/encryption clause.** UA1 §7.16 (p.8) requires an
    encrypted conforming file to set the 10th bit of the `P` key
    (assistive-technology-access permission bit). **Confirmed absent from
    UA2's Cl.8 body** by full read — UA2's table of contents has no
    "Security" entry and no encryption requirement appears anywhere in
    Cl.8. `(Observed absence, not merely unfound — full TOC and body were
    read.)`
20. **Article-threads requirement downgraded shall→should**: UA1 §7.12
    (p.8): "Article threads... **shall** reflect the logical reading
    order." UA2 §8.12.4 (p.34): "Article threads... if present, **should**
    reflect the logical content order," with an added NOTE: "Article
    threads are not considered a content reuse or accessibility
    technology."
21. **Page-labels requirement upgraded/sharpened**: UA1 §7.17 (p.8): page
    labels, if present, "**should** be semantically appropriate" (soft).
    UA2 §8.12.3 (p.34) splits this into two `shall`s: "it **shall**
    represent the same number as that perceived by a user" and "When a
    page's number is not equal to one plus the page's index, page labels
    **shall** be present" (i.e. page labels become mandatory, not merely
    recommended, the moment pagination isn't the trivial 1-based default).
22. **Redaction annotation requirements** (§8.9.2.4.17, p.28): new (PDF
    2.0 introduces Redaction as a first-class annotation subtype).
23. **PUA-Unicode restriction added** (§8.4.2, p.20): "such values in
    content streams **shall** be used only if no other valid Unicode value
    is available." UA1 §7.2 (p.5) permits PUA use with no such
    restriction ("Characters not included in the Unicode specification
    **may** use the Unicode private use area").
24. **Default document language mandated** (§8.4.4, p.20): "The default
    natural language for content and text strings **shall** be specified
    using the Lang entry, with a non-empty value, in the document catalog
    dictionary." UA1 §7.2 only requires that *changes* in language be
    declared — no UA1 clause requires a non-empty catalog-level default.

**Net read (paraphrase)**: UA2 is *stricter* on structural mechanics
(headings must be explicit and semantically matched rather than merely
sequential; tables must be regular; Document/DocumentFragment wrapping is
mandatory; layout attributes are mandatory when semantically significant;
XFA is fully banned) but *looser* on content-adjacent territory that UA1
tried to regulate directly (flicker/flash, colour-alone-conveys-meaning,
encryption/AT-access bit) — UA2 explicitly punts that territory to WCAG via
PDF Declarations instead of restating it as a PDF/UA `shall`.

---

## 5. WTPDF conformance-level split — reuse vs accessibility

WT defines two independently-declarable levels (§6.1, p.6–7), **not
mutually exclusive** (§6.1.1 NOTE, p.6: "the conformance levels defined in
this document never specify requirements that contradict... so it is
always possible to conform to all conformance levels within the same
file"). Every `[Conformance level for X]`-tagged paragraph is a *tightening*
of a `should`/`may`-level baseline into a `shall` for that level only, or
scopes an entire subclause to one level. Below is every such tag found in a
full read of WT §6–8 (paraphrase collapsed to one line each; clause+page
cited):

| WT clause | Baseline (both levels / WT-∅) | WT-A tightens to | WT-R tightens to |
|---|---|---|---|
| §6.2, p.8 | embedded non-PDF file accessibility | **shall** be WCAG-conformant if necessary to understanding | *(not tagged reuse)* |
| §7.2.2, p.9–10 | — | embedded non-PDF file **shall** carry a PDF Declaration for its accessibility standard | *(not tagged reuse)* |
| §8.2.5.25 List, p.21 | continuation Ref entry "should be present" | *(not tagged accessibility)* | Ref entry **shall** be present |
| §8.2.5.28.2 Figure, p.23 | Figure **should** have Alt or ActualText | Figure **shall** have Alt or ActualText | *(not tagged reuse — i.e. reuse-only conformance carries NO alt-text guarantee on Figures at all)* |
| §8.2.5.29.2 Formula, p.24 | non-math formula **should** have Alt/ActualText | Formula **shall** have Alt/ActualText | *(not tagged reuse — same gap)* |
| §8.4.3, p.28 | PUA-mapped content **should** have ActualText/Alt | **shall** | *(not tagged reuse)* |
| §8.7 Optional content, p.32–33 | *(clause opens: "The requirements defined in this subclause shall only apply to the conformance level for accessibility")* | full clause (OCG `Name` non-empty, `AS` key forbidden) applies | **does not apply at reuse level at all** |
| §8.9.2.3 Markup annotations, p.35–36 | RC/Contents "may [be] omit[ted]" | Contents **shall** be present when context insufficient | *(not tagged reuse)* |
| §8.9.2.4.7 Rubber stamp, p.36 | — | Contents **shall** describe intent if Name insufficient | *(not tagged reuse)* |
| §8.9.2.4.8 Ink, p.36 | — | Contents **shall** describe author's intent | *(not tagged reuse — freeform ink annotations carry no description guarantee at reuse level)* |
| §8.9.2.4.19 3D/RichMedia, p.39 | — | Contents **shall** carry alternate description | *(not tagged reuse)* |
| §8.9.4.1 Contents-as-alt-description, p.40 | — | entire mechanism scoped accessibility-only | *(not tagged reuse — reuse-level annotations have no alt-description obligation of any kind)* |
| §8.11.2 DisplayDocTitle, p.44–45 | — | ViewerPreferences/DisplayDocTitle **shall** = true | *(not tagged reuse — a reuse-only file need not force title display)* |
| §8.12.2 Outlines, p.45 | — | "longer documents **should** include an outline," scoped accessibility | *(not tagged reuse)* |
| §8.13.3 URI IsMap, p.46 | — | equivalent functionality **shall** be provided elsewhere | *(not tagged reuse)* |

**The pattern (paraphrase, load-bearing for File Portal)**: everything
about *where content sits in the tree and what type it is* (structure
types §8.2.5.2–33, table regularity, artifact identification, reading
order, Unicode/ToUnicode, font embedding) is **WT-∅ — required at both
levels, unconditionally**. Everything about *describing content for a
human who cannot perceive it directly* (Alt/ActualText completeness on
Figures and Formulas, annotation Contents/descriptions, DisplayDocTitle,
OCG naming) is **accessibility-level only**. A file honestly declaring only
`#reuse1.0` can be a structurally exemplary tagged PDF — reliable reading
order, regular tables, full Unicode round-trip — while having **zero**
figure alt-text and no annotation descriptions at all. **A structure-first
lane must check which WT level (if any) was declared before treating
Alt-text absence as a defect versus an in-spec state.**

---

## 6. Complete structure-type table (§8.2.5.2–8.2.5.33, UA2 p.16–26 = WT p.14–26, identical numbering/content)

One row per subclause. "Level" = WT tag if any (blank = WT-∅, required at
both WT levels; UA2 has no level concept, all its Cl.8.2.5 requirements are
unconditional). "Converter implication" is `(paraphrase, Inferred)` —
File-Portal-specific, not text of the standard.

| # | Type(s) | Key shall/should (UA2 clause, page) | WT level | Converter implication |
|---|---|---|---|---|
| 8.2.5.2 | `Document`, `DocumentFragment` | StructTreeRoot's **only** child **shall** be a single `Document` in the PDF 2.0 namespace, p.16 | ∅ | A structure-first witness for a UA2/WT source can locate the whole-document root unambiguously; UA1/plain-tagged sources have no such anchor |
| 8.2.5.3 | `Part` | should enclose content grouped for reasons unrelated to heading hierarchy, p.16 | ∅ | — |
| 8.2.5.4 | `Art` (Article) | self-contained article **shall** be enclosed in `Art`; its `Title` **shall** be inside it, p.17 | ∅ | — |
| 8.2.5.5 | `Sect` (Section) | heading covering a whole section **shall** be contained within that `Sect`, p.17 | ∅ | usable as a natural chunk boundary for the analyst-phase chunker |
| 8.2.5.6 | `Div` | may group elements sharing attributes; "provides no direct semantics of its own," p.17 | ∅ | safe to flatten/ignore for markdown conversion if no attributes of interest |
| 8.2.5.7 | `BlockQuote` | **shall** be used for block-level quoted content from another source, p.17 | ∅ | maps directly to Markdown `>` blockquote |
| 8.2.5.8 | `TOC`/`TOCI` | ToC entries **shall** use TOC/TOCI; each TOCI **shall** identify its target via `Ref`; leaders **shall** be artifacts, p.17 | ∅ | leaders (dot-fill) are guaranteed-artifact — safe to drop from extracted text without loss |
| 8.2.5.9 | `Aside` | **shall** enclose content outside the main flow (sidebars, side notes); parent **shall** be the deepest related ancestor, p.18 | ∅ | candidate source for File Portal's "sidebar/callout" rendering, if any |
| 8.2.5.10 | `NonStruct` | may be a role-map target meaning "not relevant," descendants keep their own semantics, p.18 | ∅ | safe pass-through node |
| 8.2.5.11 | `P` (Paragraph) | **shall** be used for any paragraph content; **each** paragraph in a multi-paragraph parent **shall** get its own `P`, p.18 | ∅ | direct 1:1 with Markdown paragraph breaks |
| 8.2.5.12 | `Hn` (H1–Hn) | explicit numbered headings **shall** be used; generic `H` **shall not** be used; level **shall match** evident level, p.17–18 | ∅ | **no sequential/no-skip check applies to UA2/WT sources** (contrast UA1, §4 item 5 above) |
| 8.2.5.13 | `Title` | **shall** be identified by `Title` type, **shall not** be identified as a heading, p.18 | ∅ | do not conflate with `dc:title` XMP metadata (explicit NOTE, no required match) |
| 8.2.5.14 | `FENote` (+`RB`/`RT` n/a here) | replaces `Note`; `Note` **shall not** be present; cross-refs **shall** use `Ref`, interactive refs **shall** use structure-destination links, p.17–18 | ∅ | `NoteType` attribute (`Footnote`/`Endnote`/`None`) is a should, not required — do not assume presence |
| 8.2.5.15 | `Sub` (Subdivision) | should identify semantic subdivisions within a block element, p.18/14 | ∅ | — |
| 8.2.5.16 | `Lbl` (Label) | labelling content **shall** be enclosed in `Lbl`, strongly associated as descendant of the shared grouping ancestor, p.19 | ∅ | direct source for list-marker / footnote-marker text, distinguishable from body text |
| 8.2.5.17 | `Span` | **shall** be used inline when no other inline type fits, attrs don't apply to parent, and semantics aren't conveyed via MC properties, p.19 | ∅ | catch-all inline wrapper; carries ActualText override candidates (images-as-text, §4 item 12) |
| 8.2.5.18 | `Quote` | **shall** identify inline-level quoted content (contrast `BlockQuote`), p.19 | ∅ | maps to Markdown inline quote styling if any |
| 8.2.5.19 | `Em`, `Strong` | used for emphasis only, **should not** be used for other purposes (e.g. marking keywords), p.19 | ∅ | direct Markdown `*em*`/`**strong**` mapping — but a converter should not assume all bold/italic *rendering* was tagged Em/Strong; some may be Span+attribute |
| 8.2.5.20 | `Link`, `Reference` | link annotation + its content **shall** be enclosed in one or the other; different targets **shall** be in separate elements; same-target multi-annotation links **shall** be in one element, p.19–20 | ∅ | `Link` = external, `Reference` = intra-document (should, not shall, per type choice) |
| 8.2.5.21 | `Annot` | usage governed by §8.9, p.20 | ∅ | see §8.9 rows below |
| 8.2.5.22 | `Form` | usage governed by §8.10, p.20 | ∅ | see Forms rows below |
| 8.2.5.23 | `Ruby`,`RB`,`RT`,`RP` | glosses **shall** use `Ruby`/`RB`/`RT` triad; parenthetical-style glosses **shall** use the 4-element `RB,RP,RT,RP` sequence; omitted-duplicate ruby chars **shall** get `ActualText` on `RT`, p.20–21 | ∅ | CJK-specific; low File Portal relevance unless specimens include ruby |
| 8.2.5.24 | `Warichu`,`WT`,`WP` | 3-element `WP,WT,WP` sequence required; **shall not** be used for non-warichu content, p.21 | ∅ | CJK-specific, low relevance |
| 8.2.5.25 | `L`,`LI`,`LBody` | labels **shall** be in `Lbl`; non-label content **shall** be in `LBody`; `ListNumbering` **shall** be present (not `None`) if `Lbl` present; continuation attrs **shall** be present when a list splits, p.21–22 | ∅ (Ref-entry tightened to shall at WT-R, p.21) | list numbering scheme is declared, not just visually implied — usable to reconstruct ordered vs unordered Markdown lists authoritatively |
| 8.2.5.26 | `Table`,`TR`,`TH`,`TD`,`THead`,`TBody`,`TFoot` | tables **shall be regular**; row groups **shall be regular**; `Scope` **shall** be specified when algorithm defaults are insufficient; `Headers` **shall** be present for all header-bearing cells if used anywhere in the table, p.20 | ∅ | **direct fix candidate for SYM-056/SYM-067** — see §9 below |
| 8.2.5.27 | `Caption` | **shall** enclose captioning content; **shall** be first child if consumed before its subject, last child if after, p.22 | ∅ | positional rule is checkable and gives caption/figure pairing for free |
| 8.2.5.28 | `Figure` | **shall** enclose all appearance-generating content incl. background; **should** have Alt or ActualText (UA2: unconditional **shall**; WT: **shall** only at WT-A, §5 above), p.22–23 | should→shall at WT-A only | **direct fix candidate for SYM-053** — see §9 below |
| 8.2.5.29 | `Formula` | math **shall** use presentation-MathML structure types and/or Associated File; non-math scientific formulae **shall** be enclosed in `Formula` and (UA2: shall / WT baseline: should→shall at WT-A) carry Alt or ActualText, p.23–24 | should→shall at WT-A (non-math case only; math case has no alt-text option, MathML *is* the machine-readable form) | — |
| 8.2.5.30 | `Index` | groups index content; each distinct index **shall** be a separate `Index` element, p.24–25 | ∅ | — |
| 8.2.5.31 | `BibEntry` | bibliography entries **shall** be enclosed in `BibEntry`; a bibliography section **shall** carry ARIA `doc-bibliography` role, p.25 | ∅ | — |
| 8.2.5.32 | `Code` | code fragments **shall** be enclosed in `Code`; textual representation **shall** be present if consumed as text, p.25–26 | ∅ | direct Markdown fenced-code-block mapping |
| 8.2.5.33 | `Artifact` | governed by §8.3, p.26 | ∅ | see §9 Artifacts below |

**Structure attributes (§8.2.6, UA2 p.18–19 = WT p.25–27)**: `General`
(8.2.6.1 — all ISO 32000-2 §14.7.6 attributes/owners may be used on any
element regardless of namespace); `Layout` (8.2.6.2 — mandatory-when-
semantically-significant, §4 item 8 above); `Table/List/PrintField/Artifact`
(8.2.6.3 — the four structure-type-specific attribute families, each
"shall use their respective attributes" when the corresponding structure
type is used); `ARIA` (8.2.6.4 — the `ARIA-1.1` owner, §4 item 9 above).
Annex B / Appendix B (informative, UA2 p.37–41, WT p.48–53) gives four
attribute-significance tables (layout-common, layout-block, layout-inline,
layout-column) plus list/PrintField/Table/Artifact attribute tables — same
content, same numbering, in both documents.

---

## 7. Annotations (§8.9, UA2 p.24–30 = WT p.34–40) — condensed

General rule (§8.9.2.1, p.25): annotations **shall** be in the structure
tree unless excluded by a following subclause; **shall** use the most
semantically appropriate type; substructure inside annotation **appearance
streams** via marked-content **shall not** be used (annotations are single
opaque whole-object structure elements, not internally sub-taggable).

Artifact carve-out (§8.9.2.2, p.25): any annotation *may* be an artifact;
**shall** be an artifact if `Invisible` flag is set, or `NoView` set with
`ToggleNoView` unset. `Hidden` flag alone does **not** imply artifact
status (explicit NOTE — Hidden changes during workflow, e.g. Widget
show/hide).

Order (§8.9.3, p.29–30): placed as close as possible to annotated content —
child/sibling of the enclosing structure element, or child of an
`Annot`/`Link`/`Reference` element. Every page with an annotation **shall**
carry a page-dictionary `Tabs` entry with value `A`, `W`, or `S` (UA1 §7.18.3
requires only `S`, and only if annotations present — UA2/WT relaxes the
allowed value set to three options).

Per-type table (all `shall follow §8.9.2.3` unless noted): Text (p.26),
Link (Contents **should**, content **shall** be contiguous in reading
order, p.26–27), FreeText (p.27), Line/Square/Circle/Polygon/Polyline
(p.27), TextMarkup (should split non-contiguous spans into separate
annotations, p.27), Caret (p.27), RubberStamp (Contents **shall** if Name
insufficient — WT-A only, p.27–28/36), Ink (Contents **shall** describe
intent — WT-A only, p.28/36), Popup (**shall not** be in structure tree,
p.28), FileAttachment (file-spec dict **shall** carry `AFRelationship`,
p.28), Sound/Movie (**shall not** be present, deprecated, p.28), Screen
(**shall** carry Contents, p.28), Widget (zero-size **shall** be artifact,
p.28), PrinterMark (**shall** be artifact, p.28), TrapNetwork (**shall
not**, deprecated, p.29), Watermark (follows §8.9.2.3 when real content,
p.29), Redaction (single logical redaction **shall** be one annotation
where QuadPoints permits, p.29), Projection (p.29), 3D/RichMedia (Contents
**shall** carry alt-description — WT-A only, p.29/39), Other/undefined
subtypes (**shall** meet all §8.9 requirements, p.29).

---

## 8. Forms (§8.10, UA2 p.30–33 = WT p.40–43) — condensed

Each widget **shall** be enclosed by a `Form` element unless it's an
artifact (§8.10.1, p.30); a `Form` element **shall** enclose **at most
one** widget (new cardinality rule vs UA1, §4 item 16); XFA **shall not**
be present (full ban, §4 item 18). Context for a widget is built from six
named sources (§8.10.2.1, p.31): surrounding real content, `Form`-element
position/grouping, field label, field `TU`, widget label, widget
`Contents` — and "the field's name (its T entry) does not contribute to
conveying the field's context" (explicit NOTE, p.31) — **T is not a
substitute for a label**. Labels **shall** be `Lbl` elements, direct
descendants of the `Form` (individual widget) or shared ancestor (grouped
widgets), §8.10.2.2 p.31. `Contents` **shall** be provided when label is
absent/insufficient (§8.10.2.3, p.31–32). Per-field-type rules:
button/push-button Contents **shall** reflect `CA`/`RC`/`AC`/`I`/`RI`/`IX`
intent (§8.10.3.2, p.32); text fields with `RV` **shall** also carry a
textually-equivalent `V` (§8.10.3.3, p.33); choice-field `Opt` text
**shall** sufficiently convey intent (§8.10.3.4, p.33); signature-field
widgets whose position is legally significant **shall** be real content
(not artifact) and the appearance **shall not** contradict the signature
dictionary's own metadata (§8.10.3.5, p.33). Non-interactive
(print-only) forms: **shall** be enclosed in `Form` with `PrintField`
attributes (§8.10.4, p.33–34).

---

## 9. Cross-cutting topics — deep-dive comparison

### 9.1 Alt-text / figures

- **UA1 §7.3 (p.5)**: "Figure tags **shall** include an alternative
  representation or replacement text" — unconditional. Graphics that don't
  represent meaningful content, or that are link backgrounds, **shall** be
  artifacts instead. Captions **shall** be tagged `Caption`.
- **UA2 §8.2.5.28.2 (p.22)**: Figure **shall** have Alt *or* ActualText
  (either satisfies) — same unconditional bottom line as UA1, but now an
  explicit either/or rather than "alternative representation." Also new:
  Figure elements using ActualText **shall** be within a semantically
  appropriate block-level element (p.22).
- **WT §8.2.5.28.2 (p.23)**: baseline **should**; **shall** only at
  WT-A. **A reuse-only WT file gives zero alt-text guarantee.**
- **Checkable property**: presence of `/Alt` or `/ActualText` key in the
  Figure structure element dictionary — but **content quality is
  unregulated** by all three documents (UA2 §7.1 EXAMPLE 1–4, p.11–12,
  explicitly disclaims content-quality regulation) — an Alt string of `"x"`
  satisfies the letter of the requirement.

### 9.2 Table headers

- **UA1 §7.5 (p.6)**: tables "should" include headers (soft); TH
  "should" have Scope, escalating to "shall" only "if the table's
  structure is not determinable via Headers and IDs" (conditional shall).
  No regularity requirement.
- **UA2/WT §8.2.5.26 (p.20 / p.15,21–22)**: regularity is now
  unconditional **shall** (both the table as a whole and any THead/TBody/
  TFoot row group); Scope **shall** be specified whenever the ISO
  32000-2 §14.8.4.8.3 default-Scope algorithm is insufficient; **and**, new,
  Headers-attribute completeness is all-or-nothing per table: "if the
  Headers attribute is used anywhere in the table, it is required for all
  cells in the table that have headers" (NOTE 4, p.20). This is
  mechanically the strongest, most checkable table requirement across all
  three documents.

### 9.3 Artifacts

- **UA1 §7.1 (p.4)**: "Artifacts... **shall not** be tagged in the
  structure tree" — binary, artifact-vs-tagged is exhaustive and mutually
  exclusive; artifact status is implied by *absence* from the tree.
- **UA2/WT §8.3 (p.19,26 / p.19,27–28)**: **two** legal artifact
  mechanisms now exist per ISO 32000-2 §14.8.2.2.2 — (a) a marked-content
  property-list artifact (no structure element, same as UA1's model) *or*
  (b) an **`Artifact` structure element inside the tree**. §8.3.1: "Any
  content... that is not real content **shall be explicitly identified**"
  (stronger than UA1's implicit-by-absence approach — explicitness is now
  mandatory, not merely a side effect). §8.3.2: "Where an artifact is
  **only meaningful in the context of** content in the structure tree, it
  **shall** be enclosed in an `Artifact` structure element" — i.e.
  contextually-anchored artifacts (the worked example: a legally-numbered
  line's line-number, nested inside the same `Sub` as the line's `P`) use
  the **in-tree** mechanism, not the marked-content-only mechanism.
  **A structure-first lane parsing a UA2/WT source cannot assume "not in
  the K-array" ⟺ "artifact"** the way it safely could for a UA1 source —
  it must also walk `Artifact`-typed structure elements and exclude their
  content from "real content" separately.

### 9.4 Reading order

- **UA1 §7.1/§7.2 (p.4–5)**: "Content shall be marked in the structure
  tree with semantically appropriate tags in a logical reading order" —
  stated, not elaborated.
- **UA2/WT §8.2.3 (p.14 / p.12–13)**: "The logical content order of
  structure elements and their contents... **shall be semantically
  correct**," explicitly equated to WCAG 2.2 SC 1.3.2 (NOTE 1). Critically,
  the standard **declines to define** "semantically correct" — "This
  document does not impose any understanding of what 'semantically
  correct' logical content order means to any given author... The author
  chooses the approach" (NOTE 2, p.14/p.13) — geography-first
  (top-down/left-right per script) and importance-first are both given as
  equally valid examples. **A structure-first lane gets an authoritative
  order (the K-array) but no independent means, from the standard alone,
  to judge whether that order is "correct"** — correctness is an authorial
  choice the standard defers to, not a checkable property.
- Artifact-content ordering is separately addressed (§8.2.3, p.14/p.13):
  artifact content **shall** preserve semantic order if it has one (e.g.
  digit order within a page-number artifact); some artifact content (table
  border paths) has **no** semantic order at all and ordering is moot.

### 9.5 Unicode mapping

- **UA1 §7.2 (p.5)**: character codes shall map to Unicode per 14.8.2.4.2;
  PUA characters *may* be used, no restriction on when.
- **UA1 §7.21.7 (p.12–13)**: `ToUnicode` CMap **shall** be present unless
  one of 4 named exemptions applies (predefined MacRoman/MacExpert/
  WinAnsi encodings; Type1/Type3 fonts using only Adobe-Glyph-List/Symbol
  names; Type0 fonts on Adobe-GB1/CNS1/Japan1/Korea1 collections;
  non-symbolic TrueType). Values **shall** be > 0 and not `U+FEFF`/`U+FFFE`.
- **UA2 §8.4.5.8 (p.22)**: same 4-exemption structure, same value
  restriction — **materially unchanged**, except the Type0 exemption list
  swaps `Adobe-Korea1` for `Adobe-KR-9` (character-collection naming
  update, not a substantive rule change).
- **UA2 §8.4.2 (p.20, NEW)**: PUA values in content streams **shall** be
  used "only if no other valid Unicode value is available" — a genuine
  new restriction absent from UA1.
- **UA2 §8.4.3 (p.20)**: ActualText **shall** be used "when it is
  necessary to convey an alternative set of Unicode codepoints than what
  is generated by a processor" based on ISO 32000-2 §9.10; PUA-mapped
  content **shall** carry ActualText or Alt (WT: should→shall only at
  WT-A). **This is the mechanism by which naive Unicode text extraction
  (e.g. pymupdf's default `get_text()`) can diverge from the standard's
  own notion of "the text"** — see §11 below.
- **UA2 §8.4.4 (p.20, NEW)**: document-level default `Lang` **shall** be
  non-empty in the catalog — no UA1 analogue (§4 item 24 above).

### 9.6 Metadata self-identification

| Property | UA1 | UA2 | WT |
|---|---|---|---|
| `dc:title` present, non-empty | shall (§7.1, p.4) | shall (§8.11.1, p.34) | shall, WT-∅ (§8.11.1, p.44) |
| `ViewerPreferences/DisplayDocTitle` = true | shall (§7.1, p.4) | shall (§8.11.2, p.34) | shall, **WT-A only** (§8.11.2, p.44–45) |
| `Suspects` = false | shall (§7.1, p.4) | **absent — no UA2 clause found** | absent (WT mirrors UA2's Cl.8 body) |
| `pdfuaid` schema | Clause 5, shall part=1 | Clause 5, shall part=2 & rev=year | not itself required; App.C: required **in addition to** `#accessibility1.0` PDF Declaration if the file wants to *also* claim UA2, p.53 |
| PDF Declarations (`pdfd`) | not defined (pre-dates spec) | optional, §7.2.2, p.12 | **required**, carries WT's own conformance-level claim, §6.1, p.6–7 |

`Suspects` absence in UA2 is worth flagging directly: UA1's `Suspects=false`
requirement is specifically about OCR/raster-conversion confidence — "Files
claiming conformance... shall have a Suspects value of false" (UA1 §7.1,
p.4, immediately following the raster-conversion-error-correction
sentence). UA2 has no restated equivalent anywhere in its Cl.8 (confirmed
by full read); **a UA2/WT-only conformance claim carries no
signal — positive or negative — about OCR-suspect content**, whereas a
UA1 claim does.

---

## 10. Synthesis — what a converter may assume vs. must still verify

**Zero-order fact, stated by the standards themselves, that must anchor
everything else**: the identification metadata **is a claim, not a proof**.
UA1 Cl.5 (p.10): "The values of the pdfuaid:part, pdfuaid:amd and
pdfuaid:corr properties **do not by themselves determine** conformance."
UA2 Cl.5 (p.10, quoted verbatim in §Quotable below): same disclaimer,
routing the actual criteria to Clause 6. **No mechanical check of the
metadata block alone can ever license "this file is conformant" as an
observation — at most it licenses "this file claims conformance," which is
an `Inferred`/unverified premise until the structure tree itself is walked.**
This is true for all three documents and is the single most important fact
for a structure-first lane's design.

### May assume (as a cheap, falsifiable working hypothesis) once the identification block for a given standard/level is present and structurally well-formed:

1. **The structure tree is intended to be exhaustive over real content**
   (UA2/WT §8.2.2: "All real content... shall be enclosed within
   semantically appropriate structure elements"). Content with no
   structure-element ancestor and no marked-content-artifact tag is either
   a conformance defect in the source or (for UA2/WT) may legitimately be
   an `Artifact`-structure-element-wrapped item still inside the K-array —
   so "not covered by a *content* structure type" is not the same test as
   "not in the K-array" (contrast UA1, where absence-from-tree alone was
   the artifact signal).
2. **K-array order is the intended reading order** (UA2/WT §8.2.3 shall;
   UA1 §7.1/§7.2 shall) — safe to use directly as chunk order instead of
   re-deriving order from geometry/bbox heuristics, *for the portion of
   the document that is real content*.
3. **Table cell/header relationships are fully determinable from Scope
   and/or Headers** for any UA2/WT-conformant table (§8.2.5.26 shall,
   both WT levels) — a structure-first witness can read TH/Scope/Headers
   directly instead of re-inferring the grid from row/column geometry, and
   can trust that regularity holds (equal logical cell counts per row
   after RowSpan/ColSpan).
4. **Fonts carry usable Unicode mappings** for extraction, except for the
   four named exemption classes (§9.5 above) — text extraction should be
   near-lossless without OCR fallback, *conditioned on checking which
   exemption (if any) applies per font* rather than assuming universally.
5. **A non-empty document-level `Lang` exists** (UA2/WT only, not UA1) —
   language-dependent NLP steps (hyphenation, tokenization) have an
   authoritative default to read instead of guessing.
6. **Figure/Formula Alt-or-ActualText exists** — but **only** if the claim
   is UA1, UA2, or WT-accessibility-level specifically; a WT-reuse-only
   claim licenses no such assumption (§5 table above).
7. **Widget/PAdES zero-size timestamp artifacts are pre-excluded** from
   real content (UA2/WT §8.9.2.4.13 shall) — no special-casing needed by
   the converter for those.

### Must still verify, regardless of any declared conformance:

1. **Whether the claim is even true.** Per the standards' own disclaimer
   above — run the structural checks; never skip them because metadata
   claims conformance.
2. **Which level was claimed, for WT sources specifically.** Reuse-only
   claims (§5) carry no Alt-text, no annotation Contents, no
   DisplayDocTitle, and no OCG-naming guarantee at all — a converter that
   flags "missing alt text" as a defect on a reuse-only-conformant file is
   mis-scoring a state the file's own declared conformance level permits.
3. **Content correctness, as distinct from mechanism presence.** All
   three documents explicitly disclaim regulating *content quality* — UA2
   §7.1 EXAMPLE 1–4 (p.11–12) lists line length, colour/contrast values,
   language choice, and font size as all "unregulated"; §6.2's
   out-of-scope list (p.11) names colour/contrast misuse, ECMAScript
   accessibility, and cognitive-load text directly as **not covered**
   by conformance. An Alt attribute containing a wrong or vacuous
   description is still a conformant Alt attribute. **A structure-first
   witness supplies presence and mechanism; it cannot supply correctness**
   — Marker's/the analyst's own judgment (or a human) is still needed to
   assess whether a declared Alt actually describes SYM-053-style content
   correctly.
4. **WCAG-style properties are never in scope**, declared or not — colour
   contrast, plain-language, flicker/flash (UA1 only — even UA1's own ban
   is content-level and unverifiable from structure alone), cognitive
   accessibility. A UA/WT claim (any level) says nothing about these.
5. **Whether the specific font/CMap/encoding rules actually hold**, since
   these are syntactic, mechanically checkable, and known to fail in
   nominally-conformant files from buggy authoring tools — don't defer
   this to the metadata claim; walk the font dictionaries directly (this
   is exactly the kind of check File Portal's converter is positioned to
   run cheaply, independent of the identification schema).
6. **Structure-tree well-formedness and containment legality per ISO/TS
   32005** (UA2/WT Cl.6.2 shall) — not fully specified in this three-
   document slice (residue below); a converter cannot validate PDF
   1.7-namespace-element-inside-PDF-2.0-namespace-parent legality from
   UA2/WT text alone.
7. **`Suspects`, where present, is a real (not metadata-only) signal for
   UA1 sources** — but its *absence of a true value* does not itself prove
   OCR-clean content (a writer can simply omit setting it, correctly or
   incorrectly), and **UA2/WT give no equivalent signal at all** — a
   structure-first lane loses this specific check entirely once a source
   is UA2/WT-only rather than UA1.
8. **Semantic correctness of reading order** — the K-array's order is
   authoritative *as the author's stated intent*, but the standard
   explicitly declines to define what "correct" order means (§9.4 above)
   — a structure-first witness can report "this is the declared order" but
   cannot independently certify "this order is right" the way it can
   certify, say, table regularity (which has a hard mathematical
   definition).

---

## 11. Relevance to File Portal's named open defects

`(All entries below are Inferred unless marked Observed — this session
read the three standards documents in full and did light, targeted greps
of the repo for grounding; it did not run the converter, the audit, or
inspect the 16 specimen PDFs' actual structure trees. See Residue.)`

- **SYM-053** (asset reference exists but is blank paper / diagram words
  gone) — `Inferred`. UA2/WT §8.2.5.28.1 (p.22/p.23) requires a Figure
  element to "enclose **all** content used to generate the final
  appearance, including background content," and §8.2.5.28.2 requires
  Alt-or-ActualText (unconditionally for UA1/UA2, WT-A only for WT). If a
  specimen is itself UA2/WT-A-conformant and tagged, its **own declared
  Alt text** is a second, independent witness for "what this figure is
  supposed to contain" that a structure-first lane could diff against
  Marker's OCR-derived "coverage" judgment — potentially catching
  exactly the blank-paper-but-referenced case SYM-053 names, since the
  source's own Alt text would describe content the rendered asset
  doesn't show. Untested against the actual specimens this session.

- **SYM-056** (61 unterminated `\begin{array}` from table-heavy pages) —
  `Inferred`. UA2/WT §8.2.5.26 (p.20) table-regularity and
  Scope/Headers-completeness requirements (§9.2 above) mean a
  UA2/WT-conformant source's own `Table`/`TR`/`TH`/`TD` tree is a
  ready-made, already-regular grid — a structure-first lane could emit
  correct Markdown/LaTeX table syntax by walking that tree directly
  instead of relying on Marker's layout-model table *reconstruction*
  (which is presumably where the malformed `\begin{array}` output
  originates). Not cross-checked against `windows-converter`'s actual
  table-rendering code this session.

- **SYM-067** (degeneration tripwire false-positives on empty-cell table
  grids) — `Inferred`. UA2/WT §8.2.5.26 NOTE 3 (p.20) states directly:
  "Some tables do not have headers" — and UA1's own reader-requirement
  §8.3 (p.14) independently defines legitimate emptiness: "A table cell is
  considered 'empty' if there is no data logically assignable to that
  cell." A structure-first lane reading a source's own TD/TH tree can
  distinguish a **declared**-legitimately-empty cell (no data assignable,
  matches the source's own tagging) from a **degenerate** Marker
  reconstruction (a grid that looks empty because table extraction
  failed) — addressing the tripwire's false-positive at the root rather
  than pattern-matching the *output* shape. Not tested against the
  tripwire's actual detection code this session.

- **SYM-054** (OCR-layer majority-vote font-name regex
  `/glyphless|invisible|ocr/`, decision destroyed at time of decision) —
  `Observed` (for the standards text) / `Inferred` (for applicability to
  this specific defect). UA1 §7.21.1 (p.10) and UA2/WT §8.4.5.1 (p.20)
  both explicitly define and require font-embedding/ToUnicode compliance
  for fonts "used exclusively with text rendering mode 3" — i.e. **glyphs
  painted invisibly**, which is precisely the OCR-text-under-image-layer
  mechanism SYM-054's heuristic is trying to detect via font-name pattern
  matching. Text-rendering-mode-3 is a **syntactic, directly-readable PDF
  property** (`Tr 3` in the content stream / the font's exclusive-usage
  pattern), not a naming convention — a structure-first check could
  authoritatively determine "is this text invisible-OCR-layer text" by
  reading actual rendering-mode usage instead of a font-name regex, which
  is a strictly weaker proxy (a font named anything could be used at mode
  3; a font matching the regex could be used at mode 0). This is a strong
  candidate for replacing the "majority vote... destroyed at the moment
  of decision" pattern with a directly re-derivable, re-checkable
  observation. Not cross-checked against `convert_and_ship.py`'s actual
  regex/ratio logic this session.

- **J24** (block records with page+bbox now persisted; audit still can't
  anchor an omission run to a page, `run_page: null`) — `Inferred`.
  UA2/WT Table B.2 (p.38/p.49, Annex B/App.B, informative) lists `BBox` as
  a standard layout attribute on Figure/Form/Formula/**Table** elements
  specifically, with the note "Current-generation assistive technology
  often relies on this attribute" — meaning a UA2/WT-tagged source PDF may
  **already carry** page-anchored bounding boxes on its own structure
  elements, independent of Marker's newly-recovered `.blocks.json`
  sidecar (`windows-converter/marker_blocks.py`, read this session,
  `Observed`). For born-digital tagged specimens, this could supply a
  **second, source-declared** page+bbox witness to cross-check Marker's
  recovered block geometry against — directly relevant to the audit's
  `run_page: null` gap this ticket names. This attribute is informative-
  table-only (not itself a `shall`, per Annex B's own framing) so its
  actual presence on any given specimen is unverified — genuinely
  `Unknown` until checked against the 16 specimens.

- **The fidelity audit's witness = pymupdf text extraction** — `Inferred`
  (this session did not read the audit's actual pymupdf invocation code).
  UA2/WT §8.4.3 (p.20) requires ActualText whenever "necessary to convey
  an alternative set of Unicode codepoints than what is generated by a
  processor" from raw glyph mapping — meaning a conformant source can
  **declare** that the "real" text differs from what plain glyph-to-Unicode
  extraction yields (ruby glosses, stretchable-character ligatures,
  images-as-text via Span+ActualText per §4 item 12, PUA-mapped glyphs).
  A pymupdf `get_text()`-style extraction that does not specifically
  resolve `/ActualText` from the structure tree will, on any specimen
  using this mechanism, diverge from the standard's own definition of
  "the text" — a structural gap in using plain text extraction as a
  fidelity witness that is independent of anything Marker or the analyst
  does. Flagging this as residue/risk for the audit design rather than a
  verified finding, since the actual witness code was not read this
  session.

---

## Residue

- **Not read**: ISO 32000-1:2008 and ISO 32000-2:2020 themselves (the base
  PDF specs both UA documents normatively incorporate by reference), ISO/TS
  32005 (structure-namespace containment rules — needed to validate
  parent/child legality across the PDF1.7/PDF2.0 namespace split, referenced
  as a `shall` by both UA2 and WT), the WAI-ARIA / DPUB-ARIA 1.0 module, the
  PDF Association's "PDF Declarations" registry document itself (beyond the
  two example snippets quoted inline in UA2 Annex A and WT Appendix A), and
  WCAG 2.2 — all cited normatively but out of this slice's three files.
- **Not checked**: none of File Portal's 16 specimen PDFs' actual structure
  trees were opened or inspected this session — every "relevance" item
  above is a standards-text-grounded hypothesis about what *could* be
  checked, not a result of having checked it. The `windows-converter`
  codebase was only lightly grepped (`marker_blocks.py` header read in
  full; `convert_and_ship.py`, the audit's witness code, the SYM-054
  regex, and the SYM-067 tripwire code were **not** opened this session).
- **Not cross-verified**: no second, differently-shaped method (e.g. an
  actual PDF parser run against a specimen) was used to check any claim
  in this document against a real file — every requirement above is
  `Observed` from the standards text alone, not `Verified` against a live
  PDF.
- **Faked**: nothing.
