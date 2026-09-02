# ISO 32000-2:2020(E) — Clauses 14.6 (Marked Content) & 14.7 (Logical Structure)
Slice owner: pages 735–760 of `iso32000-2.txt` (14.6 starts p735, 14.7 starts p737, 14.8 starts p760 — not
this slice, cited only where 14.7 defers to it). Background read outside the assigned range, because 14.7
normatively depends on it: **7.7.3.3 Page objects** (p119–122) and **7.9.6/7.9.7 Name/Number trees**
(p134–138). 7.7.2 Document catalog dictionary (StructTreeRoot/MarkInfo entries) is referenced by 14.7 but
was NOT re-read in full — its two relevant keys (`StructTreeRoot`, `MarkInfo`) are described secondhand at
14.7.2/14.7.1 and are named as residue below.

All page numbers below are the PDF's own printed page numbers baked into the marker
`--------- PAGE n ---------` in the source text file, which is also the physical/ISO page — verified by
reading the printed footer number on each cited page (e.g. p738 footer reads "723").

---

## Part A — 14.6 Marked Content

### 14.6.1 General (p735–736)
Marked-content operators (PDF 1.2) tag a portion of a **content stream** — not the structure tree — as
being "of interest." Two categories, both **shall**:
- `MP`, `DP` — a single marked-content **point** (no extent, no bracket).
- `BMC`, `BDC`, `EMC` — **bracket** a marked-content **sequence** of complete graphics objects (not raw
  bytes — "a sequence not simply of bytes... but of complete graphics objects," p735 NOTE 1).

**Table 352 — Marked-content operators** (p736), operands → meaning:
| Operator | Operands | Level | Meaning |
|---|---|---|---|
| `MP` | `tag` | shall | point; tag names the role/significance |
| `DP` | `tag properties` | shall | point + property list (inline dict or a name resolved via the current resource dict's `Properties` subdictionary, 7.8.3) |
| `BMC` | `tag` | shall | begin sequence, closed by matching `EMC` |
| `BDC` | `tag properties` | shall | begin sequence + property list, closed by matching `EMC` |
| `EMC` | — | shall | end the innermost open `BMC`/`BDC` |

Normative constraints (all **shall** unless marked):
- Marked-content operators may appear **only between** graphics objects — never inside one, never between
  a graphics-state operator and its operands (p736).
- Sequences may nest, but each sequence **shall be entirely contained within a single content stream**
  (p736) — **a marked-content sequence cannot cross page boundaries** (NOTE 4, p736). A multi-stream
  `Contents` array (7.7.3.3) is treated as one logical stream for this rule (p736).
- `BMC`/`BDC`…`EMC` must nest **properly** with `BT`…`ET` text-object brackets — `BMC…BT…EMC…ET` is
  invalid; only fully-nested forms (`BMC…BT…ET…EMC` or `BT…BMC…EMC…ET`) are valid (p736–737, worked
  example both ways).
- Tag operand: **should** use second-class names registered per Annex E ("Extending PDF") to avoid
  collisions (p735). **The tag has no relation to Tagged PDF's structure types and is never rolemapped**
  (NOTE 3, p735) — this is a direct trap: a converter must not confuse a `BDC` tag (e.g. `/P`, `/Span`,
  `/Artifact`) with a `StructElem`'s `/S` structure type even when they share a name.
- (2020) Note 2, p737: indirect references (`10 0 R`) can never occur inside a content stream — so an
  inline property dict with indirect-object values **shall** instead be registered as a named resource in
  `Properties` and referenced by name (14.6.2).

### 14.6.2 Property lists (p737)
- The property list attached by `DP`/`BDC` is a dictionary of PDF-processor-meaningful data (private or
  standard). PDF processors **should** use each key consistently (same value type across uses, p737).
- If **all** values are direct objects, the dict **may** be written inline in the stream. If **any** value
  is an indirect reference, the dict **shall** instead be a named resource in `Properties` (7.8.3) and
  referenced by name (p737) — see 14.6.1 note above; this is where a structure element's `MCID` normally
  lives (`/P <</MCID 0>> BDC`, see 14.7.5.2 examples).
- Property lists are the shared plumbing for optional content (8.11), Tagged PDF (14.8), object metadata
  (14.3.2), and Associated Files on graphics objects (14.13.5) (NOTE 1, p737).

---

## Part B — 14.7 Logical Structure

### 14.7.1 General (p737–738)
- The structure hierarchy **shall** be a tree of `StructElem` dictionaries with `K` (kids) and `P`
  (parent) pointers, expressible like HTML/XML markup, but **stored separately from the page content,
  with pointers from each to the other** (p737–738) — the separation is the whole reason a "walk" is
  required instead of simple document order.
- `MarkInfo` entry in the document **Catalog** (7.7.2, not this slice) **shall** point to a mark
  information dictionary. **Table 353 — Entries in the mark information dictionary** (p738):

| Key | Type | Level | Meaning |
|---|---|---|---|
| `Marked` | boolean | optional, default `false` | document conforms to Tagged PDF (14.8) conventions |
| `UserProperties` | boolean | optional (PDF 1.6), default `false` | structure elements carry user-property attributes (14.7.6.4) exist somewhere in the tree |
| `Suspects` | boolean | optional (PDF 1.6, **deprecated PDF 2.0**), default `false` | if true, document may not fully conform to Tagged PDF even though `Marked=true` |

Converter-relevant read: `Marked=true` is the **necessary but not sufficient** gate for "trust the
structure tree" — `Suspects=true` (pre-2.0 producers) is an explicit self-declared caveat that must be
surfaced, not silently ignored, if present.

### 14.7.2 Structure hierarchy (p738–739)
Root: **`StructTreeRoot`**, located via the `StructTreeRoot` entry of the Catalog (7.7.2, not this
slice). **Table 354 — Entries in the structure tree root** (p738–739):

| Key | Type | Level | Meaning |
|---|---|---|---|
| `Type` | name | required | `/StructTreeRoot` |
| `K` | dict or array | optional | immediate child(ren) — structure elements |
| `IDTree` | name tree (7.9.6) | **required if** any struct elem has an `ID` | maps element identifiers → structure elements |
| `ParentTree` | number tree (7.9.7) | **required if** any struct elem contains content items | maps integer `StructParent`/`StructParents` keys → parent structure element(s); see 14.7.5.4 |
| `ParentTreeNextKey` | integer | optional | next unused `ParentTree` key |
| `RoleMap` | dict | optional | non-standard structure type name → nearest standard type (14.8.4, out of slice) |
| `ClassMap` | dict | optional | attribute-class name → attribute object(s) (14.7.6.2) |
| `Namespaces` | array | **required if** any struct elem has a namespace (`NS`) | array of namespace dicts (14.7.4.2), PDF 2.0 |
| `PronunciationLexicon` | array of file specs | optional, PDF 2.0 | XML PLS pronunciation lexicons (14.9.6) |
| `AF` | array of dicts | optional, PDF 2.0 | associated files for the whole tree (14.13) |

**Table 355 — Entries in a structure element dictionary** (`StructElem`, p739–742) — this is the node
type walked at every level of the tree:

| Key | Type | Level | Meaning |
|---|---|---|---|
| `Type` | name | optional | `/StructElem` if present; **if `K` holds a dict with no `Type` entry it shall be assumed to be a `StructElem`** (p740) |
| `S` | name | **required** | structure type (14.7.3) — e.g. would-be `P`, `Chap` in the worked example |
| `P` | dict, **indirect ref shall** | **required** | parent — another `StructElem` or the `StructTreeRoot` itself |
| `ID` | byte string | optional | element identifier, unique document-wide; keyed in `IDTree` |
| `Ref` | array | optional, PDF 2.0 | 0+ indirect refs to other struct elems this content *refers to* (footnotes, endnotes, sidebars) |
| `Pg` | dict, indirect ref shall | optional; **required if `K` is an integer or array containing integers** | the page object some/all of `K`'s content items render on |
| `K` | (various; see below) | optional | children: other `StructElem`s, and/or content items (integer MCID / MCR dict / OBJR dict), in any combination/order in an array |
| `A` | dict/stream or array of same | optional | attribute object(s) (14.7.6) |
| `C` | name or array | optional | attribute class name(s) (14.7.6.2) |
| `R` | integer, default 0 | optional, **deprecated PDF 2.0** | revision number (14.7.6.3) |
| `T` | text string | optional | human-readable title — specific ("Chapter 1"), not generic ("Chapter") |
| `Lang` | text string | optional (PDF 1.4) | natural-language id for this element's text, inherited unless overridden (14.9.2) |
| `Alt` | text string | optional | alternate/accessible description of element + children (14.9.3) |
| `E` | text string | optional (PDF 1.5) | expanded form of an abbreviation/acronym |
| `ActualText` | text string | optional (PDF 1.4) | **exact replacement text** for the content enclosed by this element and its children — as small a scope as possible (p741, 14.9.4) |
| `AF` | array of dicts | optional, PDF 2.0 | associated files for this element (14.13) |
| `NS` | dict, indirect ref | optional, PDF 2.0 | namespace this element belongs to (14.7.4); absent ⇒ default standard structure namespace (14.8.6, out of slice) |
| `PhoneticAlphabet` | name, default `ipa` | optional, PDF 2.0 | alphabet for a `Phoneme` property (14.9.6) |
| `Phoneme` | text string | optional, PDF 2.0 | pronunciation-hint exact replacement text, interpreted per `PhoneticAlphabet` |

**`K`'s polymorphism (p739–740)** — each item in `K` (or `K` itself if singular) is one of exactly four
kinds, and this is the branch point every tree-walker must implement:
1. Another `StructElem` dictionary → **recurse**, not a content item.
2. An **integer** → a marked-content identifier (`MCID`) denoting a marked-content sequence, implicitly on
   the page named by this element's own (or an ancestor's) `Pg`.
3. A **marked-content reference dictionary** (`MCR`, Table 357) → an explicit `MCID` + explicit page/stream.
4. An **object reference dictionary** (`OBJR`, Table 358) → an entire PDF object (XObject, annotation) as
   a content item.
Kinds 2–4 are **content items** and **shall be leaf nodes** — they shall not have further content items
nested inside them for structural purposes (p744–745, 14.7.5.1.1).

### 14.7.3 Structure types (p742–743)
- Every `StructElem` **shall** have an `S` structure type name. PDF defines standard types (14.8.4, out of
  this slice) but **writers are not required to adopt them** and may invent names, provided they follow
  Annex E naming guidance (p742).
- Where non-standard names are used, a `RoleMap` (in `StructTreeRoot`) **should** be provided mapping them
  toward the nearest standard equivalent; for namespaced elements, `RoleMapNS` (14.7.4.2) plays the same
  role.
- **A structure type shall always be mapped through the role map if a mapping exists for it — even when
  the name coincides with a standard type name** (p742) — this is a deliberate override rule: same-name
  does not mean same-semantics if remapped.
- Chains and cycles are explicit and legal: "the same structure type can occur as both a key and a value...
  circular chains... are explicitly permitted" (NOTE 2, p743). A processor **needs to** follow the chain
  until it recognizes a type or revisits one already seen (cycle-break condition, informative but load-
  bearing for implementers).
- Pre-1.5 PDFs never remap standard types (NOTE 3, p743) — a compatibility trap for role-map walkers on
  old files.

### 14.7.4 Namespaces (PDF 2.0) (p743–744)
- **14.7.4.1 General**: solves the pre-2.0 gap where custom structure types could only be identified by
  their `RoleMap` target, with no way to identify/exchange the custom tagset itself (p743).
- **14.7.4.2 Namespace dictionary**, **Table 356** (p744):

| Key | Type | Level | Meaning |
|---|---|---|---|
| `Type` | name | optional | `/Namespace` if present |
| `NS` | text string | required | namespace name, conventionally a URI (not required to resolve — used for uniqueness, NOTE 1 p743) |
| `Schema` | file spec | optional | schema file for the namespace, format unconstrained (NOTE 2, p744) |
| `RoleMapNS` | dict | optional | maps this namespace's structure types to another namespace's; value is a name (default standard namespace) **or** `[name, indirect-ref-to-target-NS-dict]` |

- Role mapping to a standard namespace may be **direct or transitive** through a chain of namespaces
  (NOTE 3, p744).
- When an attribute object's `O` entry (Table 360) is `NSO`, its `NS` entry names the owner; namespace
  names matching a standard owner in Table 376 (14.8.5, out of slice) **shall** be considered equivalent
  to that owner (p744).

### 14.7.5 Structure content

**14.7.5.1 General / Content items (p744–745)**
- A structure element's graphical content is one or more **content items** — graphical objects existing
  independently of the tree, associated to it as described below. Two kinds: marked-content sequences
  (14.7.5.2) and complete PDF objects (14.7.5.3).
- Hard restrictions (both **shall**, p745): (1) a marked-content sequence that is itself a content item
  shall not have another structural marked-content sequence nested inside it (non-structural marked
  content is fine nested inside); (2) a structural content item shall not `Do`-invoke an XObject that is
  itself a structural content item (reference-XObject import may drop this info per 8.10.4.3).

**14.7.5.2 Marked-content sequences as content items, Table 357 (MCR)** (p745–749)
- Mechanism: bracket with `BDC`…`EMC`; the `BDC` property list **shall** contain an `MCID` integer entry,
  unique within its content stream (p745). Worked minimal form: `/P <</MCID 0>> BDC ... EMC`.
- A `StructElem`'s `K` may reference such a sequence two ways:
  - **Table 357 — Entries in a marked-content reference dictionary (`MCR`)** (p746):

    | Key | Type | Level | Meaning |
    |---|---|---|---|
    | `Type` | name | required | `/MCR` |
    | `Pg` | dict, indirect ref | optional, **required if the parent `StructElem` has no `Pg`** | page the sequence renders on; overrides the element's own `Pg` |
    | `Stm` | stream, indirect ref | optional, **present only if the sequence is in a stream other than the page's** | the content stream (e.g. a form XObject or annotation appearance stream, 8.10/12.5.5) holding the sequence |
    | `StmOwn` | any, indirect ref | optional | the object that references `Stm` (e.g. the owning annotation) |
    | `MCID` | integer | required | the sequence's marked-content identifier within its stream |
  - **A bare integer** in `K` — shorthand for "`MCID` = this integer, on the page named by the enclosing
    `StructElem`'s `Pg`" — valid only for the common case of a sequence living in the page's own content
    stream.
- Form-XObject incorporation rules (p747–749, both **shall**): (a) if a `Do` that paints a form XObject is
  itself wrapped in a structural marked-content sequence, the **entire XObject's content** becomes part of
  that one structure element's content, as if inserted at the `Do` call — and the XObject **shall not**
  itself contain structural marked-content sequences (Example 4); (b) alternatively the **XObject's own
  content stream** may contain structural marked-content sequences (referenced via `MCR.Stm`), in which
  case the `Do` operator that paints it **shall not** itself be part of a structural content item (Example
  5). A form XObject painted by **multiple** `Do` invocations must use method (a), each invocation
  individually tied to its own structure element (p747).

**14.7.5.3 PDF objects as content items, Table 358 (OBJR)** (p749)
- Used when the **entire** object (an XObject or annotation) — not a subset of its content stream — is the
  content item.
- **Table 358 — Entries in an object reference dictionary (`OBJR`)** (p749):

  | Key | Type | Level | Meaning |
  |---|---|---|---|
  | `Type` | name | required | `/OBJR` |
  | `Pg` | dict, indirect ref | optional, **required if parent `StructElem` has no `Pg`** | page the object renders on; overrides element's own `Pg` |
  | `Obj` | any, indirect ref | required | the referenced object itself |

- If the same object is rendered on **multiple pages**, each rendering needs its own `OBJR` (one per page).
  If rendered multiple times on the **same** page and the renditions don't need distinguishing, a single
  `OBJR` covers all of them; to distinguish same-page renditions, fall back to per-`Do`-invocation marked-
  content sequences instead (NOTE 2, p749).

**14.7.5.4 Finding structure elements from content items — the reverse map, `ParentTree`** (p749–752)
This is the **only** path from a piece of page content *back* to its owning structure element, because "a
stream cannot contain object references" (p749) — a marked-content sequence has no way to point at its own
parent.
- `ParentTree` is a **number tree** (7.9.7) reached via `StructTreeRoot.ParentTree`. It **shall** contain
  one entry per (a) every object that is a content item of ≥1 structure element (`OBJR` targets), and (b)
  every content stream containing ≥1 structural marked-content sequence.
- **Table 359 — Additional dictionary entries for structure element access** (p750):

  | Key | Type | Level | Meaning |
  |---|---|---|---|
  | `StructParent` | integer | required for all objects that are structural content items in their entirety (PDF 1.3) | key of this object's `ParentTree` entry |
  | `StructParents` | integer | required for all content streams containing structural marked-content sequences (PDF 1.3) | key of this stream's `ParentTree` entry |

  **At most one of the two shall be present on a given object** — an object is either a whole content item
  or a container of marked-content-sequence content items, never both (p750).
- Value shape depends on the key's owner:
  - Owner is an **object-content-item** (`StructParent`) → `ParentTree` value is an **indirect reference to
    the one parent structure element** directly (14.7.5.4 bullet 1, p750; Example 1, p750–752).
  - Owner is a **content stream** (`StructParents`, e.g. a page's own `Contents`, or a form XObject's
    stream) → `ParentTree` value is an **array of indirect references**, one per marked-content sequence
    in that stream, **indexed by each sequence's own `MCID` as a zero-based array index** (14.7.5.4 bullet
    2, p750; Example 2, p751–752). Because the `MCID` doubles as an array index, `MCID`s **need to stay
    small** to avoid a sparse/wasteful array (NOTE, p750) — an implementer-facing size hint, not a hard
    ceiling.
- `ParentTreeNextKey` (Table 354) **shall** hold an integer greater than every key currently in use; each
  time a new `ParentTree` entry is added, the *current* `ParentTreeNextKey` value **shall** be used as its
  key, then incremented (p750).

### 14.7.6 Structure attributes

**14.7.6.1 General, Table 360** (p752–753)
- Any PDF processor may attach attribute objects (dict or stream) to any structure element, even one
  another processor authored; multiple processors may layer attributes onto the same element (p753).
- **Table 360 — Entries common to all attribute object dictionaries** (p753):

  | Key | Type | Level | Meaning |
  |---|---|---|---|
  | `O` | name | required | owning processor/standard name; **shall be** `NSO`, `UserProperties`, one of the 14.8.5 standard owners, or an Annex-E-conformant custom name. If `O = NSO`, `NS` **shall** be present. |
  | `NS` | dict, indirect ref | required iff `O = NSO`; **not permitted otherwise** (PDF 2.0) | namespace owning these attributes (14.7.4) |

  All other keys in the attribute dict are `key: attributeValue` pairs (except `NS`, which is reserved —
  meaning an existing namespace literally named `NS` can't be used as an attribute key, per the NOTE p753).
- `StructElem.A` **shall** hold a single attribute object or an array of ≥1. When an array repeats `O`/`NS`
  across entries, **the later entry (array order) wins** on conflict (p753).

**14.7.6.2 Attribute classes** (p753–754)
- A **class map** (`StructTreeRoot.ClassMap`) is a dictionary: class-name → attribute object(s), letting
  many elements share one attribute object by reference instead of duplicating it.
- `StructElem.C` names the class(es) it draws from. **If both `A` and `C` specify the same attribute, `A`
  (direct) wins over `C` (class-derived)** (p753, repeated p742 in Table 355's description of `C`).
- (Informative) PDF attribute classes are unrelated to OOP classes — no inheritance semantics (NOTE, p753).

**14.7.6.3 Attribute revision numbers** (p754–755) — **the entire subclause is deprecated in PDF 2.0**
(explicit statement, p754). Mechanics for completeness (a legacy file may still carry them):
- `StructElem.R` (default 0) is the element's revision number, incremented by a processor that modifies
  the element or its content items (not by modifying an attached attribute object, p755).
- Each attribute object attached via `A`/`C` carries its own revision number, stored as a trailing integer
  paired with the object/class-name array element (single entry = revision 0, p754–755).
- Comparing an attribute object's stored revision against the element's current `R` lets a processor tell
  whether the attribute is stale (NOTE 4, p755).
- Mutually exclusive maintenance actions on major edits: increment `R`, **or** strip unknown attribute
  objects from `A`/`C` — **shall not do both** (p755).

**14.7.6.4 User properties, Tables 361–362** (p755–756)
- For non-appearance-affecting, per-instance data (CAD part numbers etc.) attached via an attribute object
  with `O = UserProperties`.
- **Table 361** (p755): `O` = `/UserProperties` (required); `P` = array of user-property dicts (required).
- **Table 362 — Entries in a user property dictionary** (p755–756):

  | Key | Type | Level | Meaning |
  |---|---|---|---|
  | `N` | text string | required | property name |
  | `V` | any | required | property value — writers **should** restrict to text/number/boolean; processors **should** display those and **should not** error on other types |
  | `F` | text string | optional | formatted display string (e.g. `($123.45)` for `-123.45`); absent ⇒ processor default format |
  | `H` | boolean, default `false` | optional | if `true`, hide from any attribute-presenting UI |

- A document using user properties **shall** set `MarkInfo.UserProperties = true` (p756) — a real
  precondition-check a converter can use to short-circuit scanning the whole tree for them.

### 14.7.7 Example of logical structure (p756–760)
A complete worked file: Catalog(1) → Pages(100) → Page 101 (Contents 201, `StructParents 0`) / Page 102
(Contents 202, `StructParents 1`) → `StructTreeRoot`(300, `RoleMap {Chap→Sect, Head1→H, Para→P}`,
`ClassMap {Normal→305}`, `ParentTree 400`, `ParentTreeNextKey 2`, `IDTree 403`) → `Chap`(301, `ID=Chap1`,
`T="Chapter 1"`) → [`Head1`(302, `ID=Sec1.1`, `A={Layout: SpaceAfter 25, SpaceBefore 0, TextIndent 12.5}`,
`K=0`), `Para`(303, `ID=Sec1.2`, `C=/Normal`, `K=[1, MCR{Pg=102, MCID=0}]` — spans two pages)] and a
sibling `Para`(304, `P=300` directly under root, `C=/Normal`, `A={Layout:TextAlign/Justify}` overriding the
class, `K=[1,2]`). `ParentTree`(400) is a two-entry number tree (`Nums [0 → 401, 1 → 402]`) where object
401 = `[302, 303]` (page-1 MCIDs 0,1 → their parents) and object 402 = `[303, 304, 304]` (page-2 MCIDs
0,1,2). `IDTree`(403→404) is a one-leaf name tree mapping `(Chap1)→301, (Sec1.1)→302, (Sec1.2)→303,
(Sec1.3)→304`. This example is the concrete instantiation of every table above and matches the "walk"
below step for step — **use it as the fixture** for a converter's own tree-walk unit test.

---

## Part C — Background clauses 14.7 depends on (read outside the assigned slice)

### 7.7.3.3 Page objects, Table 31 (p119–122) — only the entries 14.7 leans on
| Key | Type | Level | Meaning |
|---|---|---|---|
| `Contents` | stream or array | optional (absent ⇒ empty page) | the page's content stream(s); if an array, **shall** be treated as concatenated with ≥1 whitespace between, **shall not** be an empty array; division points are lexical-token boundaries only, unrelated to logical content (p120) |
| `StructParents` | integer | **required if page contains structural content items** (PDF 1.3) | the page's own key into `ParentTree` (14.7.5.4) |

(`MediaBox`/`CropBox` etc. also live here but are not part of this slice's normative scope — noted only as
the coordinate space that any bbox math over the page's content stream would need.)

### 7.9.6 Name trees, Table 36 (p134–137)
- A name tree is dictionary-like (key→value) but: keys are **strings**, keys are **ordered**, values may
  be any object type (streams/dicts/arrays/strings **should** be indirect refs; nulls/numbers/booleans/
  names **should** be direct), and the structure supports large collections without full in-memory load
  (p134).
- Node kinds, **Table 36** (p135): root has **exactly one** of `Kids` or `Names` (never both). If root has
  `Names`, it **is** the only node. If root has `Kids`, every other node is either intermediate
  (`Limits` + `Kids`) or leaf (`Limits` + `Names`).
  - `Names`: flat `[key1 val1 key2 val2 ...]`, keys **shall** be lexically sorted ascending; shorter keys
    sort before longer keys sharing a prefix (p135). Comparison is **byte-by-byte** — encoding is free as
    long as self-consistent (p135).
  - `Limits`: `[least, greatest]` string keys under this node (leaf: within its own `Names`; intermediate:
    across all descendant leaves) — **not permitted in root** (p135).
  - Key ranges across sibling `Names` entries **shall not overlap**; each covers one contiguous range
    (p135). Lookup = binary-descend via `Limits` to the owning leaf, then scan/binary-search `Names`.
- Used by `IDTree` (element-identifier → `StructElem`, 14.7.2/Table 354).

### 7.9.7 Number trees, Table 37 (p137–138)
- Identical mechanics to a name tree, except keys are **integers**, sorted **numerically**, and the
  leaf/root key-value array is named `Nums` instead of `Names` (p137). `Limits` here is `[least, greatest]`
  **integers**.
- Used by `ParentTree` (integer `StructParent`/`StructParents` → parent structure element(s), 14.7.5.4).

---

## Part D — THE WALK: structure element → glyphs & bounding box on the page

Two directions are needed, and ISO 32000-2 gives you a full mechanism for exactly one and a half of them.
This is the operationally load-bearing part of the brief.

### D1. Top-down: given a `StructElem`, find every glyph it owns

```
walk(elem, inherited_pg=None):
    pg = elem.Pg or inherited_pg          # 14.7.2 Table 355: Pg required if K holds int/array-of-int
    for item in as_list(elem.K):          # K is dict-or-array; normalize to a list (14.7.2 p739-740)
        if is_dict(item) and item.get('Type') not in (None omitted-ok, 'StructElem'):
            # not a StructElem unless Type absent (p740 rule) -- but if Type says MCR/OBJR, branch below
            pass
        match item:
            case StructElem dict (Type absent or 'StructElem'):
                walk(item, inherited_pg=pg)                       # recurse -- 14.7.2
            case integer mcid:
                sequence = find_BDC_by_MCID(pg.Contents, mcid)     # 14.7.5.2 -- own page's content stream
                collect(sequence)
            case MCR dict (Type == 'MCR'):                        # Table 357, 14.7.5.2
                target_pg  = item.Pg or pg                        # MCR.Pg overrides; required if elem has no Pg
                target_stm = item.Stm or target_pg.Contents        # explicit stream, else the page's own
                sequence = find_BDC_by_MCID(target_stm, item.MCID)
                collect(sequence)
            case OBJR dict (Type == 'OBJR'):                       # Table 358, 14.7.5.3
                target_pg = item.Pg or pg
                collect_whole_object(item.Obj, on_page=target_pg)  # e.g. paint the XObject / render the annot
```
`collect(sequence)` = extract the operators between the matching `BDC`…`EMC` for that `MCID` (or, for the
bare-`Pg`-implied form, between the `/…MCID n…BDC` and its `EMC`) from the target content stream. **The
structure tree gives you the MCID and the stream/page it lives in — it does NOT give you the byte offset,
the operator list, or a bounding box.** To actually get glyphs + a bbox you **shall** additionally run a
content-stream interpreter (a graphics-state machine — exactly what pymupdf/PDFMiner/Marker already do)
over that stream segment, tracking:
- the **CTM** (current transformation matrix, built from `cm`, and inside text objects also `Tm`/`Td`/`TD`/
  `T*`, per clause 9, not in this slice) at each `Tj`/`TJ`/path-painting operator inside the bracket;
- the **glyph advances** (font widths × font size × `Tm`) to get per-glyph origins, and the font's glyph
  outlines/ascent-descent (clause 9) to get a box height;
- accumulate a bounding box as the union of every marked object's transformed extent within the sequence.

This is the key finding for the operator: **14.6/14.7 solve "which MCIDs, on which page, belong to this
structure element" — they do not solve "what pixels those MCIDs cover."** The bbox is not a structure-tree
citizen at all in this slice; the nearest thing to a declared bbox is the `BBox` **Layout attribute**
(`14.8.5 Standard structure attributes`, out of range — p760+) which some (not all) writers optionally
attach as `A: {O: /Layout, BBox: [...]}`. Absent that attribute, bbox is *always* derived by content-stream
replay, never read off the tree.

### D2. Bottom-up: given a piece of content (a page, an MCID, an XObject), find its `StructElem`

This direction **is** fully specified in-slice (14.7.5.4, p749–752) and is the cheaper/more reliable
direction for a converter that already has Marker's own per-block page+bbox records (J24) and wants to
*attach* structure, rather than *derive* geometry:

```
find_parent(object_or_stream, mcid=None):
    key = object_or_stream.StructParent  or  object_or_stream.StructParents   # Table 359 -- exactly one present
    entry = ParentTree.lookup(key)                # number-tree descent via Limits, 7.9.7
    if object_or_stream had StructParent:          # whole-object content item (OBJR case)
        return entry                               # entry IS the indirect ref to the parent StructElem
    else:                                          # StructParents case -- a container stream
        return entry[mcid]                         # entry is an array; MCID is the zero-based index (p750)
```
- `key` comes from `StructParent` (single content-item object: annotation, XObject) or `StructParents`
  (a page or other stream holding marked-content sequences) — **never both on the same object** (Table 359,
  p750).
- `ParentTree.lookup` is a standard number-tree descent (7.9.7/Table 37): compare `key` against each node's
  `Limits`, descend into the child whose range contains it, until a leaf's `Nums` array is reached; binary-
  search that array for `key` (keys are sorted ascending, 7.9.7 p137).
- Converter implication: **every page object and every content-item-bearing stream/annotation must be
  scanned once for `StructParent`/`StructParents`**, and the `ParentTree` loaded once, to build an O(1)
  reverse index (`(stream_id, mcid) → StructElem` and `object_id → StructElem`) before this becomes cheap
  at scale — walking the number tree per lookup is only correct, not fast, for 16 specimens × many MCIDs
  each.

### D3. Composite recipe for a converter (what File Portal would actually implement)
1. Read `Catalog.MarkInfo.Marked` (7.7.2, not this slice) — if false or absent, there is no structure tree
   to trust; fall back to reconstruction (Marker's current path) entirely.
2. Load `Catalog.StructTreeRoot` (7.7.2) → `RoleMap`, `ClassMap`, `ParentTree`, `IDTree` (Table 354).
3. Build the reverse index once (D2's `ParentTree` flattened) rather than re-walking the number tree per
   MCID.
4. For each page: read its `Contents` stream(s) (7.7.3.3) and interpret them **once**, recording, for every
   `BDC …/MCID n… EMC` bracket encountered, (a) the `n`, (b) the operator span, (c) the accumulated CTM/bbox
   over that span (this is the same pass a bbox-producing renderer already makes — no second traversal is
   needed beyond what pymupdf/Marker's layout engine already does per page).
5. Resolve each `(page, mcid)` through the reverse index (step 3) to its owning `StructElem`; walk that
   element's `S` through `RoleMap` (14.7.3) to a standard type if remapped.
6. Now every rendered bbox+glyph run carries: a declared, author-asserted structure type (`S`/rolemapped),
   reading-order position (its index within its parent's `K`, which **is** the declared reading order — a
   PDF processor "navigate[s]... without knowing the producer's structural conventions," 14.7.1 p737, i.e.
   `K` order **is** the authored logical order, independent of physical page position), and any `Alt`/
   `ActualText`/`Lang` carried on the element or an ancestor.
7. Where `A`/`C` attribute objects are present (14.7.6), resolve `C` through `ClassMap` first, then let `A`
   override on key conflict (14.7.6.2 p753) — e.g. a `Layout`-owned `BBox` attribute, if present, is a
   second, author-declared bbox source that **should** be cross-checked against the content-stream-derived
   one from step 4 rather than trusted blindly (this attribute itself is defined in 14.8.5, outside this
   slice — flag it as a witness pending that clause's read).

---

## Part E — Requirements by level (consolidated)

**SHALL (binding, this slice):**
- Marked-content operators only between graphics objects; sequences properly nested with `BT/ET`; never
  cross page boundaries (14.6.1, p735–737).
- `BDC` for a structural content item **shall** carry an `MCID` property (14.7.5.2, p745).
- A `StructElem`'s `S` type is required (Table 355, p739); its `P` parent is required and an indirect ref
  (Table 355, p741); `Pg` is required whenever `K` contains an integer or array-of-integers (Table 355,
  p741).
- `MCR`/`OBJR` `Type` discriminator values (`/MCR`, `/OBJR`) required (Tables 357–358, p746, p749).
- At most one of `StructParent`/`StructParents` per object; the one present is required for that object's
  class of content item (Table 359, p750).
- `ParentTree` number-tree key assignment via `ParentTreeNextKey`, incremented after each use (14.7.5.4,
  p750).
- Content items are leaf nodes — no structural nesting inside a content item (14.7.5.1.1, p744–745).
- A structure type **shall always** be role-mapped when a mapping exists, even for same-named standard
  types (14.7.3, p742).
- Attribute object `O`/`NS` co-requirement: `NS` present iff `O = NSO` (Table 360, p753).
- `A` overrides `C` on conflicting attributes (14.7.6.2, p753); `Marked` **shall** be `true` in `MarkInfo`
  for a document to call itself Tagged PDF (14.8.1, p760, boundary of next slice — cited for context only).

**SHOULD (advisory, still load-bearing for a converter's trust model):**
- Tag names registered per Annex E (14.6.1, p735); `RoleMap` provided for non-standard types (14.7.3,
  p742); `ActualText` scoped as small as possible (Table 355, p741); user-property `V` restricted to
  text/number/boolean (Table 362, p755); attribute-revision maintenance picks *either* increment-R *or*
  strip-attributes, never both (14.7.6.3, p755, itself a deprecated mechanism).

**MAY (optional mechanisms a converter can ignore safely, but must not crash on):**
- Attribute revision numbers at all (deprecated PDF 2.0, 14.7.6.3, p754); `Suspects` flag (deprecated PDF
  2.0, Table 353, p738); namespaces beyond the default (14.7.4, PDF 2.0, p743–744); `PhoneticAlphabet`/
  `Phoneme` (PDF 2.0, p742).

**DEPRECATED IN PDF 2.0 (present only in legacy producers):**
- All of 14.7.6.3 Attribute revision numbers (p754, explicit).
- `MarkInfo.Suspects` (Table 353, p738).

---

## Part F — Structure-type table (complete for this slice: dictionary *types*, not Tagged-PDF role names)

The Tagged-PDF **standard structure type names** (`P`, `Span`, `Table`, `Figure`, …) belong to 14.8.4,
outside this slice — not reproduced here (see residue). What follows is every distinct **dictionary/PDF-
object type** that 14.6/14.7 define or constrain, i.e. the actual node kinds a converter's type-dispatch
must handle:

| Type name (`/Type`) | Category | Meaning | A markdown/JSON converter should emit |
|---|---|---|---|
| `/StructTreeRoot` | structure tree | root of the whole logical-structure hierarchy (Table 354) | not emitted directly — the implicit root of the converter's own document/section tree |
| `/StructElem` | structure tree node | one structural element; `Type` may be **omitted** and is still assumed `StructElem` if the dict has no `Type` (Table 355, p740) | a heading/paragraph/list/table/etc. node per its `S` (rolemapped), tagged with `Alt`/`ActualText`/`Lang` as metadata |
| `/MCR` | content-item pointer | marked-content reference: points at one `MCID` in one stream/page (Table 357) | resolved away — contributes the glyph run(s) it points to, not a node of its own |
| `/OBJR` | content-item pointer | object reference: points at one whole PDF object (annotation/XObject) as content (Table 358) | an embedded image/figure/form-field node, or an annotation's accessible content |
| `/Namespace` | namespace descriptor | identifies a custom structure-type tagset, PDF 2.0 (Table 356) | not emitted — used only to resolve `RoleMapNS` before choosing an emitted type |
| (mark info dict — no `/Type` key) | document-level flag dict | `Marked`/`UserProperties`/`Suspects` (Table 353) | not emitted — gates whether the converter trusts the tree at all |
| (attribute object dict/stream — no fixed `/Type`) | attribute container | `O`/`NS` + arbitrary attribute keys (Table 360); `O=UserProperties` variant adds `P` (Table 361) | layout/style hints (e.g. `TextAlign`, `BBox` once 14.8.5 is read) → converter formatting decisions, not prose content |
| (user property dict — no `/Type`) | leaf data | `N`/`V`/`F`/`H` (Table 362) | non-graphical per-instance metadata (e.g. a CAD part number) → a definition-list entry or frontmatter field, hidden if `H=true` |
| (name tree node — no `/Type`) | index structure | `Kids`/`Names`/`Limits` (Table 36, 7.9.6) — used as `IDTree` | not emitted — an index the converter consults, not content |
| (number tree node — no `/Type`) | index structure | `Kids`/`Nums`/`Limits` (Table 37, 7.9.7) — used as `ParentTree` | not emitted — the reverse index used to attach structure to already-extracted glyph runs |

---

## Residue (what this slice did not read, could not verify, or is deferring)

- **NOT READ**: 14.8 Tagged PDF in full (14.8.3–14.8.8, standard structure types Table (14.8.4), standard
  structure attributes incl. the `Layout`-owner `BBox` attribute (14.8.5), standard structure namespaces
  (14.8.6), pronunciation hints (14.9.6) beyond the pointers already cited) — out of this slice's assigned
  range (p760 is the boundary; this document read incidentally into the first ~2 paragraphs of 14.8.1/
  14.8.2.1 while confirming the boundary, and that incidental text is summarized only as "14.8 starts here,"
  never treated as normatively covered).
- **NOT READ**: 7.7.2 Document catalog dictionary in full — only its two keys `StructTreeRoot` and
  `MarkInfo` are used, by citation from within 14.7, never confirmed against the catalog's own table.
- **NOT READ**: clause 9 (Text) for the exact mechanics of `Tm`/`Td`/font-width glyph-advance math cited in
  Part D1 as "how a converter gets a bbox from a content-stream replay" — that arithmetic is asserted by
  reference to how pymupdf/Marker already do it, not re-derived from the ISO text.
  Tag: **Inferred** (the *existence* and *necessity* of that interpreter pass is Observed/normative from
  14.7.5.2's silence on geometry; the specific operator list is Inferred from general PDF knowledge, not
  re-verified against clause 9's text in this pass).
- **UNVERIFIED against a live specimen**: nothing in this document was checked against any of the 16
  project specimen PDFs' actual `StructTreeRoot` — this is a pure specification read, not an observation of
  File Portal's PDFs. A converter built from this document still needs a negative control: run it against a
  specimen with `MarkInfo.Marked = false` (or absent) and confirm it correctly falls back rather than
  reading `StructTreeRoot` garbage.
- **Table numbering**: all table numbers (351–362, 31, 36, 37) are Observed — copied verbatim from the
  source text's own captions, not renumbered or paraphrased.
