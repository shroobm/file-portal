# ISO 32000-2:2020(E) — Text Extraction, Images, Page Tree, Associated Files
Dense reference. Source: `iso32000-2.txt` (local extracted text; page numbers below are the
extracted-file's `--------- PAGE N ---------` markers, matching the brief's own page citations,
**not** the ISO-printed footer numbers, which run ~15 lower in this range — e.g. extracted p.371
carries printed footer "356"). Clause numbers are ISO's own. All four assigned clauses read to
their end (next L2/L1 heading) except 7.7, where only 7.7.3 (page tree) was read per brief scope.

Tag key used throughout: **[S]**=shall, **[SH]**=should, **[M]**=may, **[I]**=informative/note.

---

## PART 1 — Clause 9.10, Extraction of text content (p.370–374)
*(with 9.3.6 Text rendering mode, p.318–320, and 9.10's own cross-refs, as required supporting
context — flagged `[9.3.6]` inline; NOT itself inside the 9.10–8.9–7.7–14.13 slice boundary,
included because the brief names it directly)*

### 9.10.1 General (p.370–371)
Distinguishes **rendering** text (painting glyphs) from **extracting the information content** of
text (searching, indexing, export). [I] Unicode identifies *characters*, not *glyphs* — a font's
glyphs and a document's Unicode meaning are formally two different things connected only by
whatever mapping the PDF supplies.

Two supplementary mechanisms exist when a font's own encoding isn't a standard/named one:
- **ToUnicode** CMap stream in the font dictionary (PDF 1.2; detailed in 9.10.3). [M] optional.
- **ActualText** entry on a structure element or marked-content sequence (14.9.4 "Replacement
  text" — *outside this slice*, in clause 14.7 Logical structure) [M] may be used to specify text
  content directly, overriding what the glyphs would otherwise decode to.

### 9.10.2 Mapping character codes to Unicode values (p.371–372)
**THE FORMAL ALGORITHM.** A PDF processor tries these in priority order:
1. **[S] If a ToUnicode CMap is present, use it.** (highest priority, always wins if present)
2. If the font is simple and its glyph-selection uses a glyph *name*, look that name up in the
   Adobe Glyph List (AGL) / AGL for New Fonts.
3. If the font is composite (Type 0) using a predefined CJK CMap (Table 116, excluding
   Identity‑H/‑V) or a CIDFont with an Adobe-* registered character collection: map code→CID via
   the font's CMap, derive `registry–ordering–UCS2` CMap name from CIDSystemInfo, map CID→Unicode
   via that second CMap.
4. **[S/critical] "If these methods fail to produce a Unicode value, there is no way to determine
   what the character code represents, in which case a PDF processor may choose a character code
   of their choosing."** (p.371–372) — i.e., extraction is formally allowed to emit *garbage* with
   no signal that it did so. There is no defined "extraction failed" sentinel in the base spec.
5. **[S] "Tagged PDF documents, in particular, shall provide at least one of these methods"**
   (cross-ref 14.8.2.6 "Unicode mapping in tagged PDF", outside this slice) — i.e. a conforming
   tagged PDF is *obligated* to make text Unicode-mappable by one of the three positive routes.
   All 16 File Portal specimens are tagged PDFs per the brief, so this "shall" formally applies to
   every one of them.

Absence of ToUnicode is **not by itself** evidence of anything abnormal — an ordinary embedded
font with a standard/named encoding extracts correctly via route 2 with no ToUnicode entry at
all. Only exhaustion of *all three* routes (step 4) is the spec's "we cannot know what this
character means" state.

### 9.10.3 ToUnicode CMaps (p.372–374)
- **[S]** Follows ordinary CMap syntax (9.7.5) per Adobe Technical Note #5014, with restrictions:
  only pertinent stream-dict entry is `UseCMap`; **[S]** must contain
  `begincodespacerange`/`endcodespacerange` consistent with the font's encoding (simple font ⇒
  1-byte codespace); **[S]** must use `beginbfchar`/`endbfchar`/`beginbfrange`/`endbfrange` to map
  codes → Unicode sequences in **UTF-16BE**.
- **[S]** Simple fonts: codes are 1 byte in the ToUnicode CMap. CID-keyed fonts: codes may be 1, 2,
  or >2 bytes.
- A `dstString` may itself be a *sequence* of Unicode values (up to 512 bytes) — one source code
  can legitimately expand to a multi-character Unicode string (e.g. ligature `ffl` → three
  codepoints, worked example p.373, or CJK supplementary-plane characters via UTF-16 surrogate
  pairs, e.g. `<3A51>` → `<D840DC3E>`, p.373).
- `beginbfrange` with an array of `dstString`s: **[S]** if the array's element count ≠
  `srcCode2 − srcCode1 + 1`, "the result of mapping is undefined" (p.374).

### [9.3.6] Text rendering mode (p.318–320) — governs *visibility*, not *meaning*
Set by the `Tr` operator; **Table 104 — Text rendering modes** (p.319, full):

| Mode | Description |
|---|---|
| 0 | Fill text |
| 1 | Stroke text |
| 2 | Fill, then stroke text |
| **3** | **Neither fill nor stroke text (invisible)** |
| 4 | Fill text and add to path for clipping |
| 5 | Stroke text and add to path for clipping |
| 6 | Fill, then stroke text and add to path for clipping |
| 7 | Add text to path for clipping (no fill/stroke — visually invisible like 3, but still clips) |

**[S]** "The *e* and *f* components of Tm shall be updated for each glyph drawn when using text
rendering mode 3 or 7 in exactly the same way as would be done for other text rendering modes"
(p.319–320) — **invisible text still advances the text cursor and occupies real positions in text
space; it is a completely normal text-showing operation (`Tj`/`TJ`/`'`/`"`) that simply isn't
painted.** It is not a different kind of object, and it carries the *same* Unicode-mapping
obligations under 9.10.2 as visible text.

**PRINCIPLED TEST — direct answer to the brief's central question.** The spec supplies exactly two
independent, formally-defined signals relevant to "is this text an OCR overlay":
1. **Tr mode ∈ {3, 7}** at the point each glyph is shown — a **content-stream, per-text-run**
   property set by the `Tr` operator, cross-checkable per span (this is what pdfminer/pymupdf
   expose as `render_mode`/`flags` per span; it is *not* a font-dictionary property at all).
2. **ToUnicode-mapping success/failure** per 9.10.2 — whether the code maps to Unicode by any of
   the three defined routes.

These are orthogonal axes: visible text can lack a Unicode mapping (garbage under step 4); text
in mode 3/7 can have a perfectly good ToUnicode CMap (this is in fact the *normal, correct* shape
of an OCR text layer — Tesseract/ocrmypdf-style tools deliberately emit Tr‑3 glyphs *with* a
ToUnicode CMap so the layer is searchable/copyable while staying invisible under the raster
scan). **Neither signal is a font name.** I grepped the full spec text for the literal strings
`glyphless`, `OCR`, `optical character`, and `invisible` (as a naming convention rather than the
Table 104 description) — **zero hits for `glyphless` and `OCR`/`optical character` anywhere in
ISO 32000‑2.** [Observed: exhaustive grep, this file, both patterns, 0/0 matches.] "GlyphLessFont"
is a convention introduced by specific OCR tool implementations (Tesseract's PDF renderer and
tools built on it), not anything the standard defines, requires, or even acknowledges — it is one
tool family's naming habit for the synthetic font it invents to host invisible OCR glyphs.

**Consequence for SYM-054.** The current test — a font-name regex `/glyphless|invisible|ocr/`
plus "a ratio of invisible spans" — conflates a made-up, implementation-specific string
convention with the two real, spec-defined signals:
- It will **false-negative** on any OCR toolchain that names its synthetic font anything else
  (e.g. `OCR-Font`, an autogenerated hash name, or an embedded subset with a normal-looking
  `BaseFont` — nothing in the spec requires an OCR font to announce itself by name).
- It will **false-positive** on any legitimately-named font whose BaseFont substring happens to
  match, with no structural check that the matched spans are actually Tr‑3/7.
- Per the brief, "the deciding measurement is destroyed at the moment of decision" — but Tr mode
  is exactly the number the spec already defines as decisive, and it is a number Marker/pymupdf
  content-stream parsing already has on hand per span (it's needed to render the page at all); the
  fix is to **persist and threshold on the Tr-mode ratio directly** (fraction of spans on a page
  with Tr∈{3,7}), instead of deriving a proxy from font names and then discarding the real value.
- A **secondary, corroborating** signal (not a substitute) is the ToUnicode-mapping-failure ratio
  from 9.10.2 — but note it is *not* the OCR signal itself: legitimate embedded fonts routinely
  lack ToUnicode and still extract fine via the AGL route, so "no ToUnicode" alone must not be
  read as "this is a scan."

---

## PART 2 — Clause 8.9, Images (p.269–285)

### 8.9.1 General (p.269–270)
Two ways to specify a raster image: an **image XObject** (stream object, painted via `Do`; also
reused for alternate images, image masks, and thumbnails) [M], or an **inline image** (`BI`/`ID`/
`EI` operators, content directly embedded in the content stream, ≤4096 bytes recommended) [M].

### 8.9.2–8.9.4 Image parameters, sample representation, coordinate system (p.270–273)
- **[S]** Four things fully specify a paintable image: format (w, h, components, bits/component),
  sample data, the image-space↔user-space correspondence (always the unit square, mapped by the
  CTM in effect when `Do` is invoked), and the sample→colour-space mapping (Decode).
- **[S]** Samples are packed MSB-first, n bits/component (n∈{1,2,4,8,16}); each **row** starts on a
  byte boundary; JPXDecode-filtered images may carry n implicitly in the codestream instead.
- **[S]** If `ImageMask` is false/absent: samples interpreted via the declared `ColorSpace`. **[S]
  if `ImageMask` is true**: samples are instead a **stencil mask** applied with the *graphics
  state's current nonstroking colour* — the image dictionary carries no colour information at all
  in this mode (8.9.6.2).
- Image space origin (0,0) is upper-left, w×h unit cells; maps to the unit square (0,0)-(1,1) of
  user space via the CTM — orientation/size/position are entirely controlled by `cm` before `Do`.

### 8.9.5 Image dictionaries — Table 87 (p.273–276, complete, entries relevant to SYM-053/8.9 slice)

| Key | Type | Norm | Meaning |
|---|---|---|---|
| Type | name | [M] | `XObject` if present |
| Subtype | name | [S]* | `Image`; required unless thumbnail-only use (2020 clarification) |
| Width, Height | integer | [S] | samples, both required |
| ColorSpace | name/array | [S]* | required except JPXDecode-filtered images; **not permitted for image masks** |
| BitsPerComponent | integer | [S]* | required except masks & JPXDecode; 1/2/4/8/16; must be 1 if `ImageMask` true and specified |
| Intent | name | [M] | rendering intent; ignored if `ImageMask` true |
| **ImageMask** | boolean | [M] | default **false**; if true → BitsPerComponent (if present) must be 1, and **Mask and ColorSpace shall not be specified** |
| **Mask** | stream/array | [M] | explicit-mask XObject *or* colour-key-mask range array; **shall not be present if `ImageMask` is true** |
| **Decode** | array | [M] | maps raw sample ints → colour-space values; see Table 88 defaults below; for masks: `[0 1]` or `[1 0]` only |
| Interpolate | boolean | [M] | default false; hint only, processor may ignore |
| Alternates | array | [M] | array of alternate-image dicts (8.9.5.4); not permitted on an alternate image itself |
| **SMask** | stream | [M] | soft-mask image (11.6.5.2, transparency — *outside slice*); **overrides both the graphics-state current soft mask and this image's own `Mask` entry** when present |
| SMaskInData | integer | [M] | JPXDecode-only; 0=ignore embedded soft-mask data, 1=use as shape/opacity, 2=premultiplied-with-opacity; nonzero ⇒ `SMask` must be absent |
| StructParent | integer | [S]* | required if the image is a structural content item — links image back to the structure tree (14.7.5.4, outside slice) |
| **AF** | array of dicts | [M] | (PDF 2.0) associated files for *this image XObject specifically*; see PART 4 |
| OC | dictionary | [M] | optional-content visibility gate; **[S] "If it is determined to be invisible, the entire image shall be skipped, as if there were no `Do` operator to invoke it"** (p.276) |

### 8.9.5.2 Decode arrays (p.276–278)
**[S]** Linear map `y = Dmin + x·(Dmax−Dmin)/(2ⁿ−1)`, x∈[0, 2ⁿ−1]. **Table 88 — Default decode
arrays** (complete): DeviceGray/CalGray `[0 1]`; DeviceRGB/CalRGB `[0 1 0 1 0 1]`; DeviceCMYK
`[0 1 0 1 0 1 0 1]`; Lab `[0 100 amin amax bmin bmax]`; ICCBased = ICC profile's own Range;
Indexed `[0 N]` (N=2ⁿ−1, passes index through unchanged); Pattern not permitted with images;
Separation `[0 1]`; DeviceN one pair per component. **[I]** `Dmin > Dmax` is a legal, spec-sanctioned
way to invert an image (e.g. DeviceGray `[1 0]`: sample 0 → white, sample max → black) — an
*inverted* Decode array is not itself an error signature.

### 8.9.5.4 Alternate images — Table 89 (p.279–280)
Image XObject may carry `Alternates`: array of `{Image (required stream), DefaultForPrinting
(bool), OC (dict)}`. **[S]** Selection algorithm (p.279–280, full, this document's 2020 revision):
if base has OC and is visible → render base, ignoring all `DefaultForPrinting`; if base OC says
invisible → scan `Alternates` in order for first with no OC key or OC-visible, render it (or
render nothing if none qualify); if base has no OC and printing → use first alternate with
`DefaultForPrinting=true`, else print the base. **[S]** Alternate images cannot themselves carry
an `Alternates` key (no nesting).

### 8.9.6 Masked images (p.280–282) — the object-level shape of "asset exists but is blank"
Four independent masking mechanisms, listed p.280–281, any of which can make a *present,
correctly-referenced* image XObject paint nothing (or paint over content) on the page:
1. **8.9.6.2 Stencil masking** (`ImageMask=true`): 1-bit/sample; **[S]** no ColorSpace entry
   permitted; Decode `[0 1]` (default) → sample 0 paints current colour, sample 1 leaves the page
   unchanged; Decode `[1 0]` reverses this. **A stencil mask whose sample data is all 1s is a
   fully-present, correctly-formed XObject that paints literally nothing** — indistinguishable at
   the dictionary level from a working stencil; only the sample bytes tell you.
2. **8.9.6.3 Explicit masking** (`Mask` = another image XObject used as a mask for a base image):
   base and mask need not share resolution; **[S]** they're overlaid via the shared unit-square
   mapping. A mask XObject that is present, well-formed, and entirely wrong (e.g. all "masked
   out") makes an otherwise-intact base image render as blank paper.
3. **8.9.6.4 Colour key masking** (`Mask` = `[min1 max1 … minN maxN]`, pre-Decode integer ranges):
   **[S]** a sample is masked (not painted, background shows through) if *every* component falls
   in its range. A range covering the full component domain masks 100% of the image. **[I]** Note
   (p.282): combined with a lossy `DCTDecode`/`JPXDecode` filter, decode artifacts can shift
   samples into or out of the masked range unpredictably — "possibly causing samples that were
   intended to be masked to be unexpectedly painted instead" (or vice versa).
4. **SMask / soft masking** (Table 87 entry, transparency model, 11.6.5.2 — outside this slice but
   directly on-point): an all-zero-alpha soft mask over a fully intact base image renders it
   invisible while the base image's own sample data — and any embedded/associated Unicode content
   — remains completely present in the file.
5. **OC (optional content) on the image XObject itself** (Table 87, p.276): **[S]** if the OC
   entry resolves to "not visible," a PDF processor must skip the `Do` invocation entirely, "as if
   there were no `Do` operator." Two conformant processors can legitimately disagree about whether
   an image renders if they resolve the OC configuration differently — a witness (pymupdf) and
   Marker's own renderer could reach different "is this page blank" conclusions from the *same*
   PDF for a spec-sanctioned reason.

**Key distinction for SYM-053 as filed.** The brief's phrasing bundles two different failure
modes:
- **(a) "the asset is blank paper"** — an image XObject that decodes, per one of the five
  mechanisms above, to no visible marks on the page. This is checkable purely at the object level
  (Decode direction + sample statistics; presence/values of Mask, SMask, OC) without needing to
  understand the image's *content*.
- **(b) "a hand-drawn diagram's words are gone"** — this is not a masking defect at all. A
  hand-drawn diagram baked into a raster Image XObject carries **no text-showing operators, no
  ToUnicode CMap, nothing PART 1's mechanism touches** — its "words" exist only as pixels. 8.9
  defines no concept of extracting characters from image samples; that is what an OCR/vision step
  is *for*, and it lives entirely outside the base object model. If that step doesn't run (or runs
  on the wrong region, or the diagram is one image among several on the page and only some get
  OCR'd), the words are lost for a *pipeline-stage* reason, not because anything is malformed at
  the PDF-object level. Conflating (a) and (b) under one symptom risks fixing the wrong layer:
  (a) is fixable by reading Decode/Mask/SMask/OC bytes already in the file; (b) requires running
  (or re-running, on the right crop) an OCR pass — there is nothing in the PDF object model to
  "read more carefully" for (b).

### 8.9.7 Inline images (p.282–285)
**[S]** `BI`…`ID`…`EI`, not nestable; **[S]** `Length`/`L` key must be present (PDF 2.0) and "should
not exceed 4096 bytes"; **[S]** ColorSpace restricted to DeviceGray/RGB/CMYK/limited-Indexed or a
name from the resource dict's ColorSpace subdictionary — no CIE-based or Pattern spaces; **[S]**
`JPXDecode`, `Crypt`, `JBIG2Decode` filters are **not permitted** on inline images. Full
abbreviation tables (91, 92) given for the CS/filter names — irrelevant to enrichment but relevant
if the pipeline ever needs to *parse* raw content streams itself rather than relying on a library.

---

## PART 3 — Clause 7.7.3, Page tree only (p.117–124)
*(7.7.1 General and 7.7.2 Document catalog dictionary were skimmed for orientation only, per the
brief's explicit page-tree-only scope; not reproduced here beyond the one paragraph needed for
context.)*

### 7.7.3.1 General (p.117)
**[S]** Two node kinds: intermediate **page tree nodes** and leaf **page objects**; **[S]** "a PDF
document can be regarded as a hierarchy... compliant PDF processors shall be prepared to handle
any form of tree structure built of such nodes" — no assumption of a flat or balanced tree is
safe.

### 7.7.3.2 Page tree nodes — Table 30, complete (p.118)

| Key | Type | Norm |
|---|---|---|
| Type | name | [S] `Pages` |
| Parent | dict (indirect) | [S] required except root; **not permitted** in root |
| Kids | array | [S] indirect refs to immediate children (page objects or other page-tree nodes only) |
| Count | integer | [S] number of leaf (page-object) descendants; **[S] "A PDF writer shall ensure that the value of the Count key is consistent with the number of entries in the Kids array and its descendants"** — Count is formally redundant with Kids but a writer must keep them consistent |

**[S]** Page tree structure is unrelated to the document's *logical* structure (chapters/sections —
that's 14.7, outside this slice). **[S] "PDF processors shall not be required to preserve the
existing structure of the page tree."** **[S] "A page tree shall not contain multiple indirect
references to the same page tree node"** (prevents duplicate-node cycles).

### 7.7.3.3 Page objects — Table 31, complete for structure-relevant entries (p.119–123)
Full key list (36 entries); the ones with direct bearing on this project:

| Key | Type | Norm | Meaning |
|---|---|---|---|
| Type | name | [S] | `Page` (or `Template` for named-page templates, no `Parent`) |
| Parent | dict (indirect) | [S] | immediate parent page-tree node |
| **Resources** | dict | [S], **inheritable** | required; if page needs none, must be an *empty dict* — omitting the entry (as opposed to supplying `<<>>`) signals inheritance from an ancestor, but **[SH]** writers should not rely on this for sharing |
| **MediaBox** | rectangle | [S], **inheritable** | physical medium bounds |
| CropBox | rectangle | [M], inheritable | visible-region clip; default = MediaBox |
| BleedBox/TrimBox/ArtBox | rectangle | [M] | production/trim/meaningful-content bounds; default = CropBox |
| **Contents** | stream/array | [M] | absent ⇒ page is empty; **[S]** if an array, streams are concatenated with ≥1 whitespace between, split points fall only at lexical-token boundaries and are **unrelated to the page's logical content**; **[S]** writers shall not create an empty `Contents` array |
| Rotate | integer | [M], inheritable | multiple of 90; default 0 |
| **Annots** | array | [M] | annotation dict refs on this page |
| **StructParents** | integer | [S]* | required if the page contains structural content items — the page's key into the structural parent tree (14.7.5.4, cross-clause) |
| AF | array of dicts | [M] | (PDF 2.0) page-level associated files — see PART 4 |
| DPart | dict | [S]*/[not-permitted] | required iff page falls inside a DPart range, otherwise forbidden |

**[S]** "All values shall be inherited as-is, without merging, even for composite data types" — an
inherited `Resources` dict is used *whole*, found by walking `Parent` links up from the page until
the first `Resources` entry, then stopping (no merge across levels). **[S]** In a Linearized PDF,
no inheritance is permitted — all inheritable attributes must be explicit on every page object.
**[S]** "A page tree shall not contain multiple indirect references to the same page object."

### 7.7.3.4 Inheritance of page attributes (p.123–124)
Covered inline above (inherited-as-is, search-and-stop semantics, Linearized-PDF exception).

**Relevance to J24 (page-anchoring the omission run).** [Inferred — 14.7/14.7.5.4 "Finding
structure elements from content items," which formally defines how a `StructParents` integer keys
into the structural parent tree, is outside this slice's clause scope and was not read.] What
*is* established here: every page object occupies one definite, well-formed position as a leaf of
the `Kids` tree (Table 30) — page ordinal is not ambiguous or optional at the object-model level;
it's simply "walk `Kids` arrays in document order and count leaves." If Marker's recovered block
records (J24) already carry a page number per block — which the brief states they do
("block records (page + bbox) now persisted") — then a `run_page: null` on the audit's omission
object is a *propagation* gap between two in-repo data structures, not a case where the page
identity is unavailable from the PDF itself. `StructParents` (Table 31, p.121) is the spec's own
formal page-to-structure-tree back-reference and would be the principled cross-check if the
pipeline ever wants to verify Marker's page assignment against the PDF's own declared structure
rather than against bbox/geometry heuristics alone — but confirming that mechanism's exact wiring
requires 14.7, unread here.

---

## PART 4 — Clause 14.13, Associated files (p.853–858)
*(7.11.3's `AFRelationship` value table, p.152, is quoted in full below as required supporting
context — it's the enum every `AF` entry in 14.13 depends on; that clause itself sits outside this
slice's four named boundaries.)*

### 14.13.1 General (p.853)
**[S]** Associated files link content in *other formats* to PDF objects via **file specification
dictionaries** (7.11.3) referenced through an **`AF`** key. Objects that may carry `AF` (list is
exhaustive per this subclause): document catalog (14.13.3), a **page dictionary** (14.13.4), a
graphics object via marked content (14.13.5), a structure element (14.13.6), an **XObject
dictionary** (14.13.7 — this is the same `AF` key already seen in Table 87 for images), a DParts
dictionary (14.13.8), an annotation dictionary (14.13.9), a metadata stream dictionary (14.3.2,
cross-ref). **[SH]** each file-spec dict "should include the `AFRelationship` key."

### 14.13.2 Embedded associated files (p.853–854)
**[S]** A file-spec for an associated file may point to an external file (`F`/`UF`) or an embedded
file stream (`EF`) — **[SH]** "the embedded form is recommended." **[SH]** the embedded-file-stream
dict should carry a `Params` dict with at least `ModDate`; **[S]** it **shall** include a valid
MIME `Subtype`, defaulting to `application/octet-stream` if unknown. **[M]** may additionally be
listed in the catalog's `EmbeddedFiles` name tree (7.7.4) to appear as a normal user-visible
attachment. Worked example (p.853–854, 3-item case): a text-processing source file tagged
`AFRelationship=Source` at the *catalog* level; a MathML rendering of an equation tagged
`Supplement`, associated with a structure element or form XObject; a spreadsheet source tagged
`Source` and a derived CSV tagged `Data`, both associated with the image/form XObject presenting a
chart — **this is the spec's own example of exactly the "derived-data sidecar attached to the
rendered asset" pattern the brief is asking about.**

### 14.13.3–14.13.9 — where AF may attach, one line each (p.854–856)
| Subclause | Host object | AFRelationship scope |
|---|---|---|
| 14.13.3 | Document catalog | whole document |
| **14.13.4** | **Page dictionary** (`AF` in Table 31) | that one page |
| 14.13.5 | Graphics object, via `BDC .../AF .../EMC` marked content with an `AF` tag | a content-stream span; **[S]** `DP`/`MP` point-operators **shall not** be paired with an `AF` tag (only bracketed `BDC…EMC` spans qualify) |
| 14.13.6 | Structure element dict | that logical element (spans pages) — **[SH]** "preferred instead of the use of explicit marked-content" (p.855) when writing |
| **14.13.7** | **XObject dictionary** (image or Type 1 form XObject; `AF` in Table 87) | that one XObject |
| 14.13.8 | DPart dictionary | that document part |
| 14.13.9 | Annotation dictionary | that annotation |

### 14.13.10 Associated file examples (p.856–858)
Three full worked examples given (document-level PPT source; content-stream-span-level DOC data
file via `/AF /NamedAF BDC`; a third continuing past the excerpt read here). Confirms the object
shapes: `/Type /Filespec /F (name) /UF (name) /AFRelationship <name> /EF <</F <embedded-stream-ref>>>`.

### [7.11.3] AFRelationship — full value enum (p.152, required cross-reference)
| Value | **[S]** shall be used when… |
|---|---|
| `Source` | this file *is* the original source material for the associated content |
| `Data` | this file represents information used to *derive* a visual presentation — spec's own example: "such as for a table or a graph" |
| `Alternative` | an alternative representation of the content (e.g. audio) |
| `Supplement` | a supplemental representation of the source/data "that may be more easily consumable" (spec's own example: a MathML rendering of an equation) |
| `EncryptedPayload` | an encrypted payload document |
| `FormData` | data associated with the document's AcroForm |
| `Schema` | a schema definition for the associated object |
| `Unspecified` | **default**; relationship unknown/none of the above fit — **[SH]** "to be used only when no other value correctly reflects the relationship" |

**[I]** Note 3 (p.152, quoted): "The value of `AFRelationship` does not explicitly provide any
processing instructions for a PDF processor. It is provided for information and semantic purposes
for those processors that are able to use such additional information" — i.e. it's advisory
metadata for a *reader*, not something the spec makes any downstream tool obligated to act on.

### Relevance: could `blocks.json` / the manifest legitimately be an AF?
**Yes, structurally.** Nothing in 14.13 restricts the *kind* of content an associated file may
carry beyond needing a MIME `Subtype` (JSON's registered type `application/json` fits directly,
falling back to `application/octet-stream` if a writer chose not to declare it). Two placements
match the pipeline's own granularity, exactly:
- **Whole-bundle manifest → catalog-level `AF`** (14.13.3), `AFRelationship=Supplement` (it's "a
  supplemental representation... that may be more easily consumable" than re-deriving the same
  facts from the raw PDF) or `Data` if it's closer to raw derived measurements than a consumable
  summary.
- **Per-page `blocks.json` (page + bbox records) → page-dictionary `AF`** (14.13.4, the `AF` key
  already listed in Table 31) — this is a **direct, page-for-page structural match** to what J24
  already persists (block records keyed by page + bbox); `AFRelationship=Data` fits best ("used to
  derive a visual presentation," which layout/bbox data literally is).
- Alternatively, **per-image block/asset-level facts → XObject-level `AF`** (14.13.7, Table 87)
  if a given block record is really about one specific image XObject rather than a whole page.

**The catch, stated plainly:** every mechanism in 14.13 attaches a file *to a PDF object the
pipeline is writing or re-writing* — it presumes the pipeline is producing (or round-tripping) a
PDF. File Portal's current output is markdown, not a PDF, so there is currently no PDF object for
`blocks.json` to attach *to* — this clause describes a legitimate destination for the data, not a
mechanism the pipeline can use today without also emitting an (or re-serializing the source) PDF.
If the pipeline ever ships an "enriched"/round-tripped PDF (e.g. an annotated or bundled export),
this is the spec-sanctioned, standards-legible channel for exactly the `blocks.json`/manifest
sidecar convention it already uses informally — with the added benefit that a page's own `AF`
entries survive independent of any out-of-band filename/directory convention.

---

## Residue — what was NOT read, could not verify, or was inferred beyond the literal slice
- **14.7 Logical structure / 14.7.5.4 "Finding structure elements from content items"** — the
  formal definition of `StructParents`/the structural parent tree, cross-referenced repeatedly
  (Table 31, Table 87, 9.10.1's ActualText) but not itself in this slice. Anything above framed as
  "the page-to-structure back-reference" for J24 is **Inferred** from the cross-references' plain
  wording, not **Observed** from reading 14.7 itself.
- **14.9.4 "Replacement text" (ActualText)** — named in 9.10.1 as the second Unicode-override
  mechanism; not read. I did not verify ActualText's own shall/should obligations or its precise
  precedence relative to ToUnicode.
- **11.6.5.2 "Soft-mask images"** — the actual mechanics of SMask alpha/luminosity computation;
  only the Table 87 dictionary-entry description was read, not the transparency-model clause
  itself. My SMask discussion under SYM-053 describes the *shape* of the defect (present XObject,
  hidden by mask) from the entry's own wording, not from the full soft-mask algorithm.
  **[Inferred, not Verified.]**
- **9.6.5 "Character encoding" / 9.7.5 "CMaps" / Adobe Technical Note #5014** — cited by 9.10 as
  the base mechanisms ToUnicode extends; not independently read. The claim that Tr-mode is exposed
  per-span by pymupdf/pdfminer is **[Inferred]** from general familiarity with those libraries, not
  from anything in this PDF spec text — it should be treated as a hypothesis to confirm against
  the actual libraries File Portal uses, not a spec-derived fact.
- **7.7.1/7.7.2** (General, Document catalog) were only skimmed for one orienting paragraph, per
  the brief's explicit "page tree only" instruction — no claims above rest on unread material from
  those subclauses beyond the one quoted sentence.
- I did **not** cross-check any of this against File Portal's actual source (`backend_parity.py`,
  the converter's font-name regex, the analyst-phase audit code, `blocks.json`'s real schema) —
  every SYM-053/054/J24 connection above is this document's normative text held up against the
  brief's own description of those symptoms, not a code read. Treat the "fix" framing as a
  spec-grounded **design recommendation**, not a verified diagnosis of the current implementation.
- Grep for `glyphless`/`OCR`/`optical character` was run over the **entire** extracted text file
  (all 79,766 lines), not just this slice — that negative result is a genuine whole-document
  observation, the one piece of this report with the strongest evidentiary weight.
