# VERIFIED — the verifier's pass over the eight agents

Verifier: Fable (claude-fable-5-1), the ninth lane. Written 2026-09-02, read-only against
`C:/Users/Bndit/Projects/file-portal` (nothing modified; my scripts live in `out/verify/`).
Every claim below carries its tag. Every number I state was re-measured by me unless it says
`quoted`. Verification was against SOURCE text files and re-run commands, never against another
agent's summary.

Pins. Repo HEAD at my start and end: **`2f3de1d`** (`git rev-parse HEAD`; `git status` = ` M
coordination/ack-codex.json` + `?? .codex/`, neither mine). That is **6 commits past `f41dd1e`**,
the HEAD our-work.md was written at, and 21 past the session pin `14a526b`
(`git rev-list --count`). One of the six is titled *"RETRACTION: the staged 1CF604CD existed"*
— see F1. Interpreter for every probe: `C:/Users/Bndit/ml/marker-env/Scripts/python.exe`
(Python 3.12.13, pymupdf 1.28.0 / MuPDF 1.29.0, `TEXT_COLLECT_STRUCTURE == 256`, marker-pdf
1.10.2, transformers 4.57.6 — all `Observed`). No GPU touched; every probe is CPU-only by
construction and I re-read each one before running it.

---

## 1. FINDINGS, most-severe-first

### F1 — WRONG, and it reached the principal: our-work.md §1 J20 "the staged `1CF604CD` does not exist on disk"
`Verified`. our-work.md tagged this `Observed` and named the path
`windows-widget/target/release/file-portal-widget.exe`. Commit **`79d8b46`** (Rab's tree,
2026-09-02 01:41 −04:00) retracts it: the artifact was at **`src-tauri/target/release/`**
(mtime 08-31 18:11); "an ls on the wrong directory and a whole-tree find that silently truncates
before Projects/ were promoted to a negative that reached the principal and the register —
ERR-2026-09-02-048, PROBE-SHAPE. The rebuild launched on that premise overwrote the artifact
before a preservation copy could be taken." our-work.md repeated `f41dd1e`'s negative without an
independent probe. Consequence chain, all `Observed` in `git show`: `79d8b46` rebuild GREEN,
staged `E7C5A47A`; **`be3b44c` J20 STRUCK — `E7C5A47A` adopted by Rab's hand, hash matches both
sides.** our-work.md §5.4 ("the replacement rebuild has not been run") is therefore also dead.
*This is the one item in the eight reports that was wrong, tagged Observed, and acted on.*

### F2 — WRONG headline count: mapping.md "22 of 57 PDFs in Downloads carry a `/StructTreeRoot`; 35 do not"
`Verified`, two shapes. (a) I re-ran `probe_h_survey.py` end to end; the output is
**byte-identical** to `survey.tsv` (`diff` empty). (b) I counted it: **56 data rows** (57 is the
line count including the header), **27 with a tree, 29 without**. Collapsing the four
`(pages, elems)` signatures that recur (TS 32005 ×3, ISO 32000-2 ×2, Declarations ×2, SDT ×3)
gives **21 distinct works with a tree**. So "~39 % born-digital" (§0) is **27/56 = 48 % by file,
21/50 = 42 % by distinct work**; "not available on 35 of 57" (§2.7) is **29 of 56**; "of the 22
files with a tree" (§2.3) is 27. design.md §6.3 repeats "22 of 57" — inherited, and design.md's
own residue says it did not re-measure WTPDF-side numbers. The qualitative conclusion (every
scanned working-corpus book has no tree) survives: I confirmed each named file's `-` row.

### F3 — WRONG on 3 of 4 files, and a new tooling defect: mapping.md §1.8 trap 2 "`/MarkInfo /Marked` is not the gate"
`Verified`, three reads per file (`verify/markinfo_and_manifest.py`). `Document.markinfo` in
pymupdf 1.28.0 returns `{'Marked': False, …}` for **bojieli, the three SDT files and "Untitled
document"** whose catalog dictionary literally reads `<</Type/MarkInfo/Marked true>>`
(`xref_get_key(cat,"MarkInfo")`, and `xref_get_key(cat,"MarkInfo/Marked") == ('bool','true')`).
Mechanism, `Observed` in `pymupdf/__init__.py:5855-5867`: the property splits the dict string on
`/` and does `key, value = v.split()` on each piece; the bare `Type` token has no value, the
unpack raises, and the method **returns the all-False defaults**. Any MarkInfo dict with a key
before `/Marked` reads as untagged. **survey.tsv's `Marked` column is unreliable for those five
rows.** What survives: `ISO_TS_32003-2023` genuinely carries `<</Marked false>>` with 393
StructElem (`Verified` by xref), so the trap stands on **n = 1, not n = 4**, and design.md §2.4's
"`Verified` corollary" stands on that one file. Same family as the `('null','null')` trap
mapping.md itself banked — this one belongs in ERROR-BIN beside it.

### F4 — WRONG number, and the field name is wrong: mapping.md §2.6 "all 25 (of 634 true) analyst runs in the 2026-08-31 held manifest"
`Verified` by reading `C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/manifest.json`:
`fidelity.analyst = {doc_survival 0.9402, runs_total 404, runs_capped_at 25}`, 25 runs,
**25/25 with `page: null`**; `fidelity.convert = {witness "pymupdf", doc_survival 0.9334,
runs_total 531, runs_capped_at 25}`, 25 runs, 0/25 null (first run page 757). **634** is
SYM-066's 2026-08-30 figure (`SYMPTOM-INDEX.md:85`), not this manifest's. The field is
`page`, not `run_page` (the brief and mapping.md both say `run_page: null`).

### F5 — RESOLVED: our-work.md FIND-4, the 404 / 531 collision — the record is wrong at one line
Same read as F4. **531 = convert-phase `runs_total`; 404 = analyst-phase `runs_total`.**
our-work.md's `Inferred` reading is CONFIRMED and it could not have been Observed from the repo
(the manifest is outside it). The defect is in the record: `sessions/S114-desktop-2026-08-31.md:259`
says the analyst audit resolves as "`25 of 531 · partial · unseen 506`" — for the analyst phase it
is **25 of 404, unseen 379**. `OPEN-TASKS.md:423` (J19) attaches 531 to the convert phase, which
is correct. Codex's controls (60/531, 101/100) are synthetic and unaffected.

### F6 — WRONG citations, both Opus reports: BBox "(14.8.5, Table 384)"
`Verified` against `iso32000-2.txt`: **Table 384 = "Standard table attributes"** (L57552, PAGE
807). BBox is a *Layout* attribute: **Table 377 "Standard layout attributes"**, PAGE 788–789, row
"Figure, Form, Formula and Table elements / BBox / No [inheritable]" (L56497-56500), clause
**14.8.5.4**. mapping.md §1.4 and §2.5, design.md §3.2 all cite 384. The substance (BBox optional,
Figure "should have a BBox attribute", PAGE 784 L56190-56191, **should**) is CONFIRMED.

### F7 — WRONG clause: design.md D4 and `gate_real.py`'s comment, NonStruct "ISO 32000-2 14.8.4.3"
`Verified`: 14.8.4.3 is **Document level structure types** (PAGE 770). NonStruct is
**14.8.4.4 Grouping level, Table 365, PAGE 773** (L55528-55539): "should not be interpreted or
exported to other document formats. Its descendants **shall** be processed normally … **shall**
inherit the containment requirements and limitations of its parent element." The design's
substance — flatten, do not score — is exactly what the text licenses. The clause number is not.

### F8 — WRONG on several rows, and not transcribed from anywhere: mapping.md §3's clause column
`Verified` against the ISO table captions (`Table 364` PAGE 771 … `Table 370` PAGE 781,
`Table 382` PAGE 805, `Table 383` PAGE 806):
- `ListItem` / `ListGroup` → "14.8.4.6, Table 383" — **lists are Table 370, PAGE 781
  (14.8.4.8.2); Table 383 is PrintField attributes.**
- `TableOfContents` → "TOC / TOCI, 14.8.4.6" — **TOC/TOCI are not in ISO 32000-2's 14.8.4 at
  all**; they are unique PDF 1.7 grouping elements (TS 32005 Table 2, ts32005 report Part 1.4).
- `Code` → "Code *(PDF 2.0)*, 14.8.4.5" — **`Code` appears in no row of Tables 364–370
  (0 `^Code$` lines in PAGE 769–786)**; it is a unique PDF 1.7 inline element (TS 32005
  Table 3). `Reference`/`BibEntry` "14.8.4.7" — same: PDF 1.7-only.
- `Part / Sect / Div / Aside` → "14.8.4.3" — grouping is 14.8.4.4.
mapping.md's residue says clause numbers were "quoted from those reports"; the parser reports do
not contain these assignments. The 24-of-28 overlap *conclusion* is not in question — the
lookups are. `FENote (PDF 2.0)`, `Title (PDF 2.0)`, `Aside (PDF 2.0)`, `Artifact` element
(Table 375 PAGE 785), 14.8.2.5.1, 14.8.4.8.3, 14.8.4.8.5, 14.8.5.7 are CONFIRMED.

### F9 — OVERSTATED page column: pdfua-wtpdf.md
The report states its convention ("physical PDF page as marked by the PAGE N breaks") and then
does not follow it. `Verified` by locating 13 clauses: UA-1 §7.x cites are **printed folios**
(§7.1 "p.4" = PAGE 11; §7.3 "p.5" = PAGE 12; §7.4.2 "p.6" = PAGE 13) while its Cl.5 "p.10" is a
PAGE marker; UA-2 cites drift from 0 (§8.2.5.12 "p.17" = PAGE 17) to **−7** (§8.4.2 "p.20" =
PAGE 27; §8.10.1 "p.29" = PAGE 37; §8.12.3 "p.34" = PAGE 41; §8.2.5.26 "p.20" = PAGE 22); WT
cites are printed (§8.2.5.28.2 "p.23" = PAGE 26; Appendix C "p.53" = PAGE 56). **Every clause
number I checked resolved to text with the stated content and the stated normative level** —
the page numbers are the unreliable half. design.md §2.3–2.4 quotes those pages.

### F10 — OVERSTATED precision: mapping.md §1.6 "+0.42 ms/page (+25 %)"
`Verified` by re-running `probe_j_tables.py` on the same file, same machine: witness
`get_text()` **1.19 ms/page**, dict+STRUCT **1.72 ms/page**, delta **+0.53 ms/page (+45 %)**;
xref walk **0.074 ms/elem** (vs 0.089). A single-run timing quoted to two decimals. The shape
(sub-millisecond on a 57-page text-only spec) holds; the number must not be quoted. design.md D1
already showed it does not survive real books — my re-run: **Ashby +3.66, Beer +115.73,
claude-code +15.04 ms/page** (vs +3.93 / +110.55 / +14.13), Damodaran NOT-FOUND under
`Downloads` alone, as design.md's residue says.

### F11 — OVERSTATED by omission: design.md §2.3 offers `/MarkInfo /Suspects` as "one additional spec-grounded input"
`Verified`: ISO 32000-2 Table 353 (PAGE 738, L50961) marks Suspects **"(Optional; PDF 1.6;
deprecated in PDF 2.0)"**, and UA-2 Cl.6.2 says a conforming file "should not contain any feature
that is deprecated in ISO 32000-2". design.md says UA-2 dropped it (CONFIRMED: **0** occurrences
of "Suspects" in `pdfua2.txt`; 1 in `pdfua1.txt`, L474 PAGE 11 "shall have a Suspects value of
false", immediately after the raster-conversion sentence — CONFIRMED) but not that the base
standard deprecates it. On any PDF 2.0 source the flag is absent by design; the lever is more
one-sided than stated.

### F12 — STALE (true when written, superseded): our-work.md FIND-1, §5.1, §5.3, §5.4
- FIND-1 glass detector RED: `Verified` true at `f41dd1e` (`git show f41dd1e:observability/
  dispositions.json` has **0** `blocks_engine`) and **disposed at `7a33c55`** (EVIDENCE, signed
  2026-09-02). Re-run at HEAD: `--since 14a526b --enforce` and `--since c9b6cb1 --enforce` both
  **exit 0, "no unsigned glitches"**.
- §5.1 / §5.3 (J21 + J19 register repairs): discharged in **`c354bce`**; J19, J20, J21 are
  struck rows now. The Gmail draft is named in the J19 row "pending Rab's waiver-or-go" — still
  open.
- §4 "J24's row still reads SEMANTIC, un-updated": **still true at `2f3de1d`** (`OPEN-TASKS.md:428`,
  "SEMANTIC (converter change - Rab's signature)", not struck, no signature note).

### F13 — minor
- our-work.md FIND-3 "`blocks_error` (7 sites …)" lists six line numbers and `grep` finds exactly
  **6** emits (`:683 :945 :1233 :1369 :1454 :1527`). Substance CONFIRMED: `blocks` has **0** hits
  in `main.js` and `room.js`.
- mapping.md §1.1 "60-value `FZ_STRUCTURE_*` enum": `pymupdf.mupdf` exposes **58** such constants
  (including INVALID); mapping.md lists 57 names.
- mapping.md §2.6 cites `fidelity_audit.py:411` for the analyst `page=None`; it is **:414**
  (`:411` is the empty-windows early return). `git log` shows no change to the file since the
  pin, so it was off when written.
- ts32005 report: `node verify_table5.js` reproduces **1,193 cross-checks**; it reports
  **48 mismatches** (the report does not state the count). One of them — `Artifact → child
  Figure` with no reverse entry — touches `Figure`, presented as a full-confidence row.
- mapping.md tagged two things `Inferred` that were `Observable` in the source text on this disk:
  BPG §4.2.6.2 "empty cells are always TD cells, never TH cells" (`tagged-bpg.txt` L1614, PAGE 33)
  and AN002 §4.2.2–4.2.4 `AFRelationship = Alternative/Data` (`an002-af.txt` L356-373, PAGE 11).

---

## 2. REPRODUCTIONS — every empirical claim the Opus agents made, re-run

| what | command (marker-env python, `out/`) | result | matches? |
|---|---|---|---|
| WTPDF xref walk | `probe_f_fixed.py` | 2281 objects · **2060** StructElem · /Pg 1388 · /C 819 · /Alt **175** · /A 175 · /ActualText **93** · /ID 86 · /Lang 28 · /T 3 · 28 types · /O owners Table 114 / Layout 20 / List 3 · declared BBox **3/2060**, one `[-32768 …]` · Figure xref **3** vs Door A **1** (both flag sets) | yes, exact |
| element → bbox walk | `probe_i_verify.py` | Figure xref 2378 page 26, declared BBox `(369.289 757.564 381.762 770.163)` → top-down `(369.29 71.73 381.76 84.33)`; Door A `(369.29 71.73 372.62 79.69)`; **max deviation 9.145 pt**; control-1 `<P>` **298.4 pt**; control-2 Ashby `('null','null')`, 0 struct blocks, 933 chars | yes, exact |
| Alt vs witness | `probe_g_page0.py` | 175 /Alt, **47 absent**; 93 /ActualText, **0 absent**; cover `'Creative Commons'`/`'PDF Association logo'` not in `get_text()` | yes |
| Door A whole-doc | `probe_d_walk.py` | **2112** instances · 57/57 pages · depth **7** · 27 raw / 23 std; RoleMap xref 394 maps Title, Author_, p, "P group big_" → P | yes |
| table from tree | `probe_j_tables.py` (1) | page 19, 1 Table, 2 TR, TH 3 / TD 1 / empty 0, markdown emitted | yes |
| cost on WTPDF | `probe_j_tables.py` (3) | 1.19 / 1.72 ms/page, +0.53; 0.074 ms/elem | shape yes, number no (F10) |
| reading order | `probe_k_order.py` | WTPDF **55/57** identical, 2 true resequencings (pp 0, 56); ISO first 60 **45/60**, 15 differ; File_Portal **42/42**; both negative controls behave | yes, exact |
| artifact boundary | `probe_l_artifact.py` | WTPDF 1531 / **57** / heuristic **0/57** / over-strip 1; BPG 1571 / **79** / **0/79** / 1; ISO-14289-2 1712 / 51 / **47/51** / 3 | yes, exact |
| corpus survey | `probe_h_survey.py` → `verify/survey_rerun.tsv` | **byte-identical to survey.tsv**; 56 rows, **27 YES / 29 no** | data yes; the report's 22/35 no (F2) |
| real-corpus gate | `gate_real.py` (needs `PYTHONIOENCODING=utf-8`; crashes on the bojieli row under cp1252) | **19 / 4307 = 0.44 %**; bojieli 2388 elems · 15 sem types · mcid 1.00 · 166 ms; Beer 2276 · 2 · 0.97 · 195 ms; Best Practices 1 elem → T1; 7/10 works exit at T0 | yes (timings ±15 %) |
| decoys | `decoy.py` | **GREEN 4/4**, exit 0; D1 mcids 2/2, D4 0/2 | yes |
| cost on real books | `cost_probe.py` | +3.66 / +115.73 / +15.04 ms/page; T0 0.8–3.2 ms/doc | yes (±5 %) |
| corpus method A | `corpus_probe.py` | 27 dirs / 10 works; Best Practices A=0 vs B=1 | yes |
| Door A density | `doora_probe.py` | bojieli 2428 elems · depth **14** · 50.64 ms/page (report 40.08 → full book 0.96 s vs 0.76 s; ratio to Marker 1.1–2.2 % vs 0.85–1.74 %) | shape yes, timing +26 % |
| ledger | `ledger_read.py` | 10 rows; every s/page value in design.md §5.2 present | yes, exact |
| bojieli roles | `roles.py` | NonStruct 1221 = **51.1 %**; P 302, Code 138, Link 120, LI 107, H3 94, TD 58, TR 22 | yes, exact |
| Codex's controls | `cdx0043_probe.py` at HEAD `2f3de1d` | **PASS**: 60/531 → partial · "60 of 531" · unseen 471; 101 vs cap 100 → malformed both ways, reason names the *producer* cap; 39/40/41/60 all partial; harness deliberate-fail caught; `LEGACY_RUN_CAP 25`; signature `(shown, raw_total, raw_cap, *, legacy_cap)`; `bench.py` unchanged since `f41dd1e`; `:474` `[:40]` at `46e6de4` → `self.runs()` at `12f0ca9` | yes |
| J24 selftest | `windows-converter/marker_blocks_selftest.py` | **GREEN 57/57**, watched-failing guard fires | yes |
| converter suite | `convert_and_ship_selftest.py` | **GREEN 85/85** | yes |
| glass detector | `observability/glass_detector.py --since 14a526b --enforce` (and `c9b6cb1`) | **exit 0** at HEAD (RED at `f41dd1e` per dispositions diff) | stale (F12) |
| spec grep | `grep -c` over `iso32000-2.txt` | 79,766 lines; `glyphless` 0 · `OCR` 0 · `optical character` 0 | yes |
| marker blindness | walk of `site-packages/marker/*.py` | **0** files mention StructTreeRoot/StructElem/COLLECT_STRUCTURE; `BlockTypes` = **28**; `providers/pdf.py` imports pypdfium2 + pdftext | yes |
| held manifest | direct read | convert 531 / analyst 404; `probe_evidence {invisible_spans 0, total_spans 157924, invisible_ratio 0.0, ocr_font_trigger null}` (NUM-5 live); analyst block `chunks_generated 316 · resumed 641 · passed 928 · rejected 29 · failed 0 · duration_s 4634.4 · goodput 59.37` — J19's numbers now Observed from the manifest, not the record | yes |

Not reproduced (no command to re-run): the ts32005 report's printed-page offsets; `probe_e_raw.py`
(left wrong on purpose as its author's own negative control — I did not run it).

---

## 3. CLAIMS CHECKED against source — the load-bearing ones

Legend: C = CONFIRMED, W = WRONG, O = OVERSTATED, U = UNREAD.

| # | agent | claim | checked against | verdict |
|---|---|---|---|---|
| 1 | iso-tagged | 14.8.2.5.1: logical content order **shall** be a depth-first traversal of the structure tree | `iso32000-2.txt` L54991, PAGE 764: "shall be defined by a depth-first traversal of the document's logical structure hierarchy" | C |
| 2 | iso-tagged / design §3.1 | 14.8.2.2.2: content not in the tree is an artifact by definition | L54876, PAGE 762: "Any content that is not included in the structure tree is an artifact even when not enclosed in a marked-…" | C |
| 3 | iso-tagged R1 | 14.8.1: tagged PDF **shall** carry MarkInfo `Marked true` | L54752-54753, PAGE 760 | C |
| 4 | iso-tagged R24 / mapping | Figure **should** carry BBox and **should** carry Alt or ActualText (not shall) | L56190-56193, PAGE 784, both "should" | C |
| 5 | iso-structure | Table 353 Suspects deprecated in PDF 2.0 | L50961, PAGE 738 "(Optional; PDF 1.6; deprecated in PDF 2.0)" | C |
| 6 | iso-structure | Table 359 `StructParent`/`StructParents` at p750; 14.7.5.4 at p749 | L52462 PAGE 750; L52420 PAGE 749 | C |
| 7 | iso-tagged | 14.8.4.8.3 header-association algorithm at PAGE 783 | L56119-56133: "If the Headers attribute … is not specified … search towards the first cell … The search terminates when…" | C |
| 8 | iso-text-images | 9.3.6 / Table 104 mode 3 invisible, p318-319 | L22217 PAGE 318; L22248 PAGE 319 | C |
| 9 | mapping §1.4, §2.5; design §3.2 | BBox is in "Table 384" | Table 384 = table attributes PAGE 807; BBox is Table 377 PAGE 789 | W |
| 10 | design D4 / gate_real.py | NonStruct is ISO 32000-2 14.8.4.3 | 14.8.4.3 = Document level (PAGE 770); NonStruct = 14.8.4.4 / Table 365 PAGE 773 | W |
| 11 | mapping §3 | lists = "14.8.4.6, Table 383"; TOC/TOCI, Code (PDF 2.0), Reference, BibEntry in 14.8.4.x | Table 370 PAGE 781 = lists; Table 383 = PrintField; 0 `Code` rows in Tables 364-370; TS 32005 Tables 2-3 name them PDF 1.7-only | W |
| 12 | mapping §1.8 | 22 of 57 files have a tree, 35 do not | `survey.tsv` re-generated byte-identical: 56 rows, 27 / 29 | W |
| 13 | mapping §1.8 trap 2 | three SDT files read `Marked = False` | catalog `<</Type/MarkInfo/Marked true>>`; `Document.markinfo` mis-parses | W |
| 14 | mapping §1.8 trap 2 / design §2.4 | ISO_TS_32003 `Marked false` with 393 StructElem | `xref_get_key` → `<</Marked false>>`; survey row 393 | C |
| 15 | mapping §2.6 | "25 (of 634 true) analyst runs in the 08-31 held manifest" | held manifest: analyst `runs_total 404` | W |
| 16 | our-work FIND-4 (Inferred) | 531 is the convert-phase total, 404 the analyst-phase | held manifest `fidelity.convert.runs_total 531`, `fidelity.analyst.runs_total 404` | C (record `:259` wrong) |
| 17 | our-work J20 | staged `1CF604CD` does not exist on disk | `git show 79d8b46` — retracted, ERR-048; existed at `src-tauri/target/release/` | W |
| 18 | our-work FIND-1 | glass detector exits 1 on `--since 14a526b --enforce` | re-run at HEAD: exit 0; `7a33c55` disposed `blocks_engine`; at `f41dd1e` dispositions had 0 entries | C-then-stale |
| 19 | our-work FIND-2 | supersede path copies only .md, assets/, manifest.json; create path `copytree` | `exporter.py:352` copytree; `:449-453` rmtree assets, copytree assets, copyfile md, copyfile manifest — no `blocks.json`; `test_exporter.py` 0 × "blocks" | C (consequences still Inferred, unexercised) |
| 20 | our-work §2 | `marker_blocks_selftest.py` 57/57; `convert_and_ship_selftest.py` 85/85 | re-run | C |
| 21 | our-work §6 | Codex controls 60/531 and 101/100 | `cdx0043_probe.py` re-run at `2f3de1d` | C |
| 22 | our-work §0 | 14a526b..f41dd1e = 15 commits | `git rev-list --count` = 15 (HEAD is now 21) | C |
| 23 | mapping §2.2 / design D2 | SYM-054 is seven orphaned HTTP servers, not the OCR vote; the vote is census N-054 | `SYMPTOM-INDEX.md:73`; `docs/51-numeration-census.md:57,:279` | C |
| 24 | mapping §2.2 / design D3 | NUM-5 fixed the destroyed measurement; regex `:744`, `or` at `:775` | `convert_and_ship.py:744,:772,:775`; held manifest `probe_evidence` populated | C |
| 25 | mapping §2.6 | analyst `_merge_runs(…, page=None)` at `:411` | it is `:414` (`:411` is the empty-windows return) | O (line) |
| 26 | design §0 | Marker blind to the tree: 0 files in the marker package | walk of `site-packages/marker` | C |
| 27 | design §0 / §6.1 | 19 pages of 4,307 (0.44 %); 1 of 10 works; 9 of 27 dirs | `gate_real.py` + `corpus_probe.py` | C |
| 28 | design §7 | decoys GREEN 4/4, D4 MCID 0/2 | `decoy.py` exit 0 | C |
| 29 | design D1 | +3.93 / +110.55 / +14.13 ms/page | `cost_probe.py`: +3.66 / +115.73 / +15.04 | C (±5 %) |
| 30 | design §8 | J26 spoken for inside J24; next free id J27 | `OPEN-TASKS.md:428`; no J26/J27 rows | C |
| 31 | pdfua-wtpdf §4.4 | UA-2 8.2.5.12 **shall not** use `H` | `pdfua2.txt` L804-805, PAGE 17 | C (page right) |
| 32 | pdfua-wtpdf §4.10 | UA-2 8.2.5.26 "Tables **shall** be regular", p.20 | L1049, **PAGE 22** | C clause, W page |
| 33 | pdfua-wtpdf §5 / design §2.4 | WT 8.2.5.28.2 Figure **should** → **shall** at accessibility level only | `wtpdf.txt` L977-983, PAGE 26, verbatim | C |
| 34 | pdfua-wtpdf §2 / design §2.4 | UA-1/UA-2 Clause 5 "do not (by themselves) determine conformance"; WT Appendix C normative, pdfuaid part 2 rev 2024 | `pdfua1.txt` L397 PAGE 10; `pdfua2.txt` L366 PAGE 10; `wtpdf.txt` L2236-2245 PAGE 56 "(Normative)" | C |
| 35 | pdfua-wtpdf §9.6 / design §2.3 | UA-1 §7.1 Suspects=false after the raster sentence; UA-2 has no Suspects clause | `pdfua1.txt` L468-475 PAGE 11 (report says p.4); 0 hits in `pdfua2.txt` | C (page is folio) |
| 36 | pdfua-wtpdf §4.5 | UA-1 7.4.2 no-skip rule ("H1 H3 is not") | `pdfua1.txt` L537-549 PAGE 13 (report p.6) | C |
| 37 | design §3.2 | UA-2/WT §8.2.2 all real content **shall** be enclosed in structure elements | `pdfua2.txt` L524-525 PAGE 13 | C |
| 38 | mapping §2.2 | BPG 5.5.3.1 (p.65): invisible render-mode-3 text positionally matching a scan is the sanctioned pattern | `tagged-bpg.txt` L3087 PAGE 65 NOTE 1 "render mode 3 (invisible text)"; L3091-3093 "overlaid with invisible text where the text matches the position of the scanned text" | C |
| 39 | mapping §2.4 (Inferred) | BPG 4.2.6.2 empty cells always TD | `tagged-bpg.txt` L1614 PAGE 33 | C (was Observable) |
| 40 | ts32005 Part 2 | BPG declines "shall" (2.6) | `tagged-bpg.txt` L213-217 PAGE 7 | C |
| 41 | ts32005 Part 3.1 | Declarations: presence "does not guarantee" conformance | `declarations.txt` L94-95 PAGE 5 | C |
| 42 | iso-text-images | whole-spec grep glyphless/OCR/optical character = 0/0/0 over 79,766 lines | re-run | C |
| 43 | brief premise / design D5 | "all 16 specimen PDFs are tagged" | 18 Sep-2-dated standards files in Downloads (13 distinct), all `STRoot=YES` in the reproduced survey; no set of 16 identifiable | C for the files present; count U |

---

## 4. CONTRADICTIONS reconciled

1. **our-work.md vs commit `79d8b46`** — J20 exe "does not exist" vs "existed at src-tauri/target/release/". The commit wins; our-work.md restated a retracted negative as `Observed` (F1).
2. **survey.tsv `Marked` vs corpus_probe `Marked`** on bojieli (False vs true). The xref read wins; `Document.markinfo` is the broken instrument (F3). This also removes 3 of mapping.md's 4 trap-2 exhibits.
3. **mapping.md "22 of 57" vs its own survey.tsv "27 of 56"** (F2).
4. **mapping.md "634" vs the held manifest "404"** and **the session record's "25 of 531" for the analyst audit vs the manifest's 404** (F4, F5). our-work.md's inference was right; the record is wrong at one line.
5. **mapping.md / design.md "Table 384" vs ISO's Table 377** for BBox; **design.md "14.8.4.3" vs 14.8.4.4** for NonStruct (F6, F7).
6. **pdfua-wtpdf.md's stated page convention vs its page numbers** (F9). Clauses are right; pages are not.
7. **design.md D1 vs mapping.md §1.6** on cost: design.md already named this deviation; my re-run agrees with design.md and moves mapping.md's own number from +0.42 to +0.53 on the same file (F10).
8. **our-work.md FIND-1 vs HEAD**: RED then, GREEN now, because `7a33c55` disposed the key (F12) — staleness, not error.
9. **Two probes on Beer *Diagnosing***: `gate_real.py` refuses at T2 (2 semantic types); `doora_probe.py` says `tagged-hollow` (3 std types, 11.2 elem/pp). Same verdict (refuse), different reason string — the design quotes only the first. Not a contradiction in substance.
10. **ISO 32000-2 vs design.md on Suspects** — the standard deprecates it; the design lists it as an input (F11).

---

## 5. BRIEF FOR FABLE — to carry to Rab

Verifier lane (Fable, ninth agent) → operator's Fable → Rab. HEAD `2f3de1d` at both ends of my
pass; nothing in the repo touched. Most-severe-first.

**1. One negative reached you tagged Observed and was acted on — it was false.** `Verified`.
our-work.md §1 J20 repeated `f41dd1e`'s "the staged `1CF604CD` does not exist on disk" without
its own probe. Your commit `79d8b46` retracts it (existed at `src-tauri/target/release/`,
ERR-048, the rebuild overwrote it before a preservation copy). J20 is struck at `be3b44c`,
`E7C5A47A` adopted by your hand. Nothing further to do on J20; the lesson is the review lane's:
a negative it did not re-probe was passed through as Observed.

**2. The research corpus number is wrong in both Opus reports.** `Verified` by re-running the
survey (byte-identical output) and counting: **27 of 56** Downloads PDFs carry a structure tree
(29 do not; 21 distinct works after collapsing duplicate copies), not "22 of 57 / 35 without".
Born-digital-with-tree share is **48 % by file (27/56)**, not ~39 %. The conclusion that every
scanned book in the working corpus has no tree stands, file by file.

**3. A second pymupdf trap, and it took out 3 of 4 exhibits behind "Marked is not the gate".**
`Verified`, three reads per file. `Document.markinfo` in pymupdf 1.28.0 returns all-False when
the MarkInfo dict has any key before `/Marked` (it does `key, value = v.split()` on the bare
`Type` token, catches the exception, returns defaults — `pymupdf/__init__.py:5855-5867`). Five
files whose catalog says `<</Type/MarkInfo/Marked true>>` (bojieli, SDT ×3, Untitled) read
`Marked = False` in `survey.tsv`; that column must not be quoted. What survives:
`ISO_TS_32003` genuinely has `<</Marked false>>` with 393 StructElem — the trap stands on **1
file, not 4**. Same family as the `('null','null')` trap; both belong in ERROR-BIN before any
`pdf_structure.py` is written.

**4. The held manifest resolves the 404/531 collision — and the record is wrong at one line.**
`Verified` by reading `held/14c66834bdfeaa2e/manifest.json`: **convert `runs_total 531`,
analyst `runs_total 404`**, all 25 analyst runs `page: null`. our-work.md's Inferred reading
was right. `sessions/S114-desktop-2026-08-31.md:259` says the analyst audit is "25 of 531 ·
unseen 506"; it is **25 of 404, unseen 379**. mapping.md §2.6's "25 (of 634 true)" borrows
SYM-066's 08-30 number; also the field is `page`, not `run_page`. Codex's controls are synthetic
and unaffected. J19's goodput record (`generated 316 · resumed 641 · passed 928 · rejected 29 ·
failed 0 · 4634.4 s · 59.37 tok/s`) is now Observed from the manifest itself.

**5. Citations that will not look up.** `Verified` against `iso32000-2.txt`: BBox is Table 377
(Standard layout attributes, PAGE 788–789, clause 14.8.5.4), **not "Table 384"** (Standard table
attributes, PAGE 807) — mapping.md §1.4/§2.5 and design.md §3.2. NonStruct is **14.8.4.4 /
Table 365 PAGE 773**, not "14.8.4.3" (Document level) — design.md D4 and `gate_real.py`'s
comment; the substance ("descendants shall be processed normally … shall inherit the
containment requirements of its parent") is exactly what the design does. mapping.md §3's
clause column is partly composed, not transcribed: lists are Table 370 PAGE 781 (not "Table
383", which is PrintField); TOC/TOCI, `Code`, `Reference`, `BibEntry` are PDF 1.7-namespace-only
(TS 32005 Tables 2–3; 0 `Code` rows in ISO Tables 364–370) — the "24 of 28 overlap" reading
survives, the lookups do not. pdfua-wtpdf.md's page column drifts up to 7 pages from its own
stated convention (UA-1 §7.x are printed folios; UA-2 §8.4–8.12 cites are PAGE−7); every one of
13 clauses I located had the stated content and the stated shall/should.

**6. Numbers that hold, with denominators.** `Verified` by re-run: WTPDF 2060 StructElem, /Alt
175 (47/175 = 27 % absent from `get_text()`), /ActualText 93 (0 absent), declared BBox 3/2060
(one degenerate), Figure 3 in xref vs 1 via Door A, derived-vs-declared bbox deviation 9.145 pt
(n = 1 element), reading order resequenced 2/57 WTPDF pages and 15/60 ISO pages, artifact
heuristic catches 0/57 and 0/79 on two specimens; real converted corpus **19 pages of 4,307
(0.44 %)** reach a conforming tree (1 of 10 works, bojieli), 7 of 10 refused at the catalog
lookup, Beer *Diagnosing* refused at 2 semantic types (2276 elems, 179 Figure), Best Practices at
1 element / 465 pp; decoys 4/4 GREEN with D4 MCID 0/2 watched failing; cost on real books +3.7
to +116 ms/page (mapping.md's "+0.42 ms/page" is one run on a 57-page spec — my re-run of the
same file gives +0.53 — do not quote it); Codex's controls PASS at HEAD; selftests 57/57 and
85/85; glass detector exit 0 on both pins (RED at `f41dd1e`, disposed by your `7a33c55`).
Marker is blind to the tree (0 files in the package mention it). Structure-tree order is a
**shall** (14.8.2.5.1 PAGE 764); Figure Alt/BBox are **should** in ISO, **shall** in UA-2,
**shall only at the accessibility level** in WTPDF (verbatim, PAGE 26).

**7. One omission in the design.** `Verified`: ISO 32000-2 Table 353 marks `/Suspects`
"deprecated in PDF 2.0" (PAGE 738) and UA-2 6.2 says a conforming file should not contain
deprecated features — design.md §2.3 offers it as an input and only says UA-2 dropped it. On a
PDF 2.0 source it is absent by design. One-sided even in the direction the design allowed.

**8. Stale, not wrong.** our-work.md §5.1/§5.3 discharged at `c354bce` (J19/J21 struck); the
Gmail draft is still named in J19's row as pending your waiver-or-go. our-work.md §4 still true:
the J24 row reads "SEMANTIC (converter change - Rab's signature)" with no signature or build
note, un-struck, at `2f3de1d`. FIND-2 (supersede path copies .md + assets/ + manifest.json and
never `blocks.json`; `test_exporter.py` has 0 "blocks") is confirmed in source and still
unexercised — the Damodaran re-convert is the first bundle that walks that path.

**Residue.** I did not run a conversion, touch the GPU, read CI, or open Gmail. Timings are
single runs. I read the held manifest, which the review lane declared out of scope; read-only.
`gate_real.py` dies on the bojieli row under a cp1252 console — run with
`PYTHONIOENCODING=utf-8` or the one positive vanishes silently.

**What you sign — and only you.** (a) Whether J27 as scoped (measure the tree, route nothing,
three lines in the converter, decoys as selftest) is worth building for a lane that reaches
0.44 % of pages you have converted and ~48 % of the files sitting in Downloads — design.md §6.3
puts that judgement with you and does not dress it up; the thresholds inside it were fitted on
one positive example. (b) The three fixes that do not wait on it and each alter verdicts: the
SYM-056 `\begin{X}`/`\end{X}` balance check, SYM-067 `degeneration()` on stripped text, and
demoting the lane vote's `or` at `convert_and_ship.py:775`. (c) Record repairs: `S114:259`
(25 of 404), the J24 row's signature state, the J19 Gmail draft waiver. (d) Whether FIND-2 gets
a ticket before the next supersede. (e) Banking the two pymupdf traps in ERROR-BIN.

---

## 6. RESIDUE — what I did not read, could not verify, or approximated

- **Parser reports read, not re-derived end to end.** I verified 43 claims against source text
  and re-ran every command; I did not re-read all five parser reports clause by clause against
  the standards. Sampling never promotes: the 30 clauses I located say nothing about the ones
  I did not.
- **TS 32005 Table 5**: I reproduced the 1,193-check cross-validation (48 mismatches) but did not
  re-parse the column-major text myself; the 46/54 "full confidence" figure is the report's, and
  one mismatch touches `Figure`.
- **Timings** are single runs on a live desktop (±5–26 % against the reports). None of them is a
  distribution.
- **I read the held manifest** (`~/ml/library/held/14c66834bdfeaa2e`), which our-work.md declared
  out of its scope. Read-only; nothing under `Projects/file-portal` was modified. `git status` at
  end shows only the two pre-existing entries.
- **UNREAD**: the ParentTree route for the 32.6 % of WTPDF elements without `/Pg`; `/AF` on any
  specimen; MCID-level walking versus Door A; Marker's actual behaviour on a tagged PDF (no
  conversion run, no GPU); CI for any commit in the span; the Gmail account; whether in-tree
  `Artifact` *elements* (UA-2's second mechanism) exist in BPG or ISO-14289-2 — `probe_l` counts
  only the outside-tree form (WTPDF's S-tally has 0 `Artifact` elements, so its row is unaffected).
- **`probe_e_raw.py`** was not run (left wrong by its author as a control).
- **`gate_real.py` under a cp1252 console dies on the bojieli row before printing the headline** —
  the design's author must have run it under UTF-8; anyone re-running it needs
  `PYTHONIOENCODING=utf-8`. Declared because a silent crash there would have hidden the one
  positive.
- **Nothing faked.**

## Correction filed 2026-09-04 (the docs/53 lead hunt)

Row 12's neighbour above — "reading order resequenced 2/57 WTPDF pages and 15/60 ISO pages" — and
design.md §2.7c both describe **pymupdf's raw block order (the content stream) versus the declared
tree, not Marker versus the declared tree.** Lane A of docs/53 asserted the opposite mechanism
("OrderProcessor overwrites surya's position on every non-sliced page"); the coordinator marked it
WRONG and Fable re-read the installed package: `marker/builders/layout.py:140` sorts by surya layout
`position` (`surya/layout/__init__.py:97`, `position=z`); `marker/processors/order.py:17-22` skips
every page that is not `layout_sliced`. Marker's true order against a declared tree is UNREAD (J30).
The counts themselves are not withdrawn — only what they are counts *of*.

