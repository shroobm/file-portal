# docs/52 — The PDF structure study (declared structure vs what Marker reconstructs)

⟨claimed: Fable lane · occupant: Claude Fable 5.1 · S114 · 2026-09-02⟩

**What this is.** Rab's commission of 2026-09-02, verbatim: *"look at the stuff we had done, and I want
you to then look at all these pdfs. use a fleet of 5 sonnet 5 sub agents, and 3 opus 5 agents and 1
fable agent who verifies then and communicates with you."* The PDFs were the PDF 2.0 / PDF-UA /
tagged-PDF standards (17 files, 16 distinct by sha256, all tagged; ISO 32000-2 is 1,023 pages). The
question underneath: a tagged PDF **declares** its logical structure; Marker **reconstructs** it from
pixels — for born-digital tagged sources, should File Portal read the tree instead of, or as a witness
against, the layout model?

**Provenance, stated plainly.** Every file here was written by a subagent, not by the operator's
Fable. The first eight were then checked by a ninth agent (`model: fable`) **against the source text,
never against another agent's summary** — 45 load-bearing claims, 25 empirical claims re-run. Its
verdicts: **28 CONFIRMED · 7 WRONG · 9 OVERSTATED · 1 UNREAD**, 12 contradictions named. Read
`VERIFIED.md` first; it tells you which numbers in the other eight files may be quoted and which may not.

## The files, in reading order

| file | agent | what it is |
|---|---|---|
| **`VERIFIED.md`** | Fable (verifier) | the audit of the other eight, most-severe-first, and the brief to Rab — **start here** |
| `design.md` | Opus | the structure-first lane: T0–T3 probe in cost order, the ground-truth contract, the decoy, the smallest first step (J27) |
| `mapping.md` | Opus | pymupdf 1.28.0 *can* read the tree (two doors, measured); declared structure vs Marker, field by field; the witness proposal |
| `our-work.md` | Opus | the honest account of S114's own work from the repo; Codex's CDX-0043 controls (PASS) |
| `iso32000-2-structure.md` | Sonnet | ISO 32000-2 §14.6 marked content + §14.7 logical structure — the mechanics |
| `iso32000-2-tagged.md` | Sonnet | §14.8 tagged PDF + §14.9 accessibility — the vocabulary; 42 structure types with what a converter should emit |
| `iso32000-2-text-images.md` | Sonnet | §9.10 text extraction (the principled OCR-overlay test: Tr mode 3/7), §8.9 images, §7.7, §14.13 |
| `pdfua-wtpdf.md` | Sonnet | PDF/UA-1, PDF/UA-2, WTPDF 1.0 — 67 shalls; what a conformance declaration lets a converter skip |
| `ts32005-bpg-extensions.md` | Sonnet | ISO/TS 32005 namespace mapping (Table 5 reconstructed, 1,193 cross-checks, 48 mismatches), the Best Practice Guide inverted into checks, the extensions triaged |

Runnable probes the Opus agents and the verifier wrote — 26 files, read-only, no GPU — are in
`prototypes/pdf-structure/probes/` (quarantine; nothing imports them). `survey.tsv` there is the Downloads
corpus survey; **its `Marked` column is poisoned by the pymupdf trap in ERROR-BIN ERR-049 and must not
be quoted.**

## The three numbers that decide it (verifier-confirmed, with denominators)

- **19 pages of 4,307 (0.44 %)** of the corpus Rab has actually converted reach a conforming structure
  tree — 1 of 10 distinct works (bojieli). Every scanned book has no tree. Both 1,300-page Damodarans have
  no tree. Five of six clean-lane works have no `/StructTreeRoot` at all.
- **27 of 56 files in Downloads (48 %)** carry a tree — 21 distinct works. *(Both Opus reports said
  22/57 and ~39 %; the verifier re-ran the survey and counted.)*
- **47 of 175 `/Alt` strings (27 %)** in the WTPDF specimen appear nowhere in `get_text()` — text the
  current witness structurally cannot see, including a formula rendered as an image.

So: the instrument is real, pymupdf can already hold it, the decoy proves it reads the tree and not a
fallback — and it reaches almost none of the books that filed the defects. The design says so itself
(`design.md` §6.3). What Rab signs is in `VERIFIED.md`'s last section.

## Corrections this study forced on the S114 record

`S114:259` (the analyst audit is 25 of **404**, not 531); J24 struck with residue; **J28** filed (the
supersede export path never copies `blocks.json`); **ERR-049** (the `Document.markinfo` parse bug and
the `('null','null')` trap — both must be designed around before any `pdf_structure.py` exists).

Cost: 9 agents · 1.94 M subagent tokens · 350 tool calls · 71.7 min wall.
