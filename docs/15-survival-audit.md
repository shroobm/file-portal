# docs/15 — The Survival Audit (conversion fidelity gate)

**Status:** DRAFT spec, written 2026-07-19 by the Fable 5 design session (think-tank commission from Rab).
**Implementation:** pending — the implementing session commits this file at session open, then builds to it.
**Design authority:** this spec is the decision record. Closed questions in §1 are CLOSED — implement, don't redesign.

---

## 0. Problem

The pipeline has no measurement of how much of a source PDF survives into the Marker
markdown, or how much of the Marker markdown survives the qwen formatting pass. The
user currently takes fidelity on faith, and the user (who built the system) knows the
faith is unwarranted. The catastrophic failure mode for a library is **silent
omission**: dropped pages, dropped sections, quietly paraphrased paragraphs —
invisible at read time, invisible forever.

**Aim (in priority order):** (1) detect catastrophic loss, (2) localize suspect
regions so spot-checks are targeted instead of faith-based, (3) produce a trendable
number so engines/settings can be compared over time. NOT an aim: proving the copy
is identical to the source (impossible and undesirable — we *want* to lose page
headers, hyphenation, layout junk).

## 1. Decision summary — closed questions

**Chosen: window-survival containment.** Auto-generated presence tests (olmOCR-Bench
style) exhaustively covering an ephemeral witness extraction, recall-first,
per-stage strictness, fully deterministic.

Rejected alternatives (do not relitigate; reasons documented):

| Alternative | Why rejected |
|---|---|
| Global CER/WER via edit-distance alignment (ISRI/ocreval tradition) | Needs a *trusted, order-aligned* reference. pymupdf emits layout order; Marker deliberately reorders (columns, captions) → constant false alarms on correct output. Global % doesn't localize. |
| OmniDocBench protocol (NED + TEDS + CDM per component) | Built for hand-annotated benchmarks; per-book annotation cost is unpayable. Steal later only if tables/formulas start mattering. |
| LLM-as-judge (Marker's own benchmark uses one) | Non-deterministic (same book, different verdict), GPU cost per book, and structurally blind to the failure that matters most: fluent output with a missing paragraph reads fine. |
| Embedding similarity | Semantic smoothing hides verbatim omission of "summarizable" text; non-reproducible across model versions. |
| OCR confidence scores as quality proxy | Engine policy routes between converters with non-comparable confidence outputs → breaks cross-engine trending. |

**Key asymmetry (core design decision):** stage 1 (PDF→Marker) has an *imperfect*
witness → tolerant matching, agreement semantics. Stage 2 (Marker→qwen) has a
*perfect* reference (the Marker doc IS what the formatter was handed) → ruthless
near-exact gate. Scan lane has *no* trustworthy reference → same machinery, score
relabeled "agreement", looser thresholds, reference-free tripwires added.

**Recall primacy:** noise/duplication in output is visible at read time; omission is
invisible forever. Recall gates; precision gets a sampled tripwire only.

## 2. Witness

`fitz.open(pdf)` → `page.get_text()` per page (pymupdf, already in marker-env).
Seconds per book. The witness is **ephemeral**: extract, score, discard. Only
metrics persist (manifest block, §7). Nothing is doubled, nothing extra is vaulted.

- Clean lane: witness = born-digital text layer → metric kind `fidelity`.
- Scan lane (`lane=scan` or OCR-layer routing): witness = embedded OCR layer, which
  is itself machine output → metric kind `agreement` (two independent witnesses;
  where they agree confidence is earned, where they disagree we flag, we do not
  pretend to measure truth).

## 3. Normalization (both sides, in this order)

1. Unicode NFKC.
2. Unify quotes/dashes to ASCII (`""''–—` → `"'--`), ligatures decomposed (ﬁ→fi etc. — NFKC handles most).
3. De-hyphenate line breaks: `(\w)-\n(\w)` → `\1\2`.
4. Output side only: strip markdown syntax (heading `#`, emphasis `*_`, blockquote `>`, table pipes/rules, image/link syntax keeping anchor text, HTML tags, fenced-code markers).
5. Witness side only: **repeated-line strip** — drop any normalized line whose text
   recurs on ≥ 40% of pages (running headers, footers, page numbers). This single
   filter removes most false "loss".
6. Casefold.
7. Collapse all whitespace runs to single spaces.

**Analyst-stage ladder (J32-A, docs/54-repair-road/README.md §2, signed: Proposal A, 2026-09-05)
— steps 8-9, ANALYST STAGE ONLY (`audit_analyst`/`chunk_survival`; `audit_convert`'s witness
comparison never runs these, and its numbers do not move — see §9.4).** The near-exact
comparison above was counting Marker's OWN backslash escapes, punctuation and spacing choices
as loss: qwen3:8b routinely rewrites `\(1960-2023\)` to `(1960-2023)`, or moves a comma, and
steps 1-7 alone have no way to see those as the same text (measured ≈3.7x over-count in windows
on the anchor corpus, ≈7x on the held University 4e run). Both steps run on BOTH sides of every
analyst-stage comparison, so they can only narrow disagreement, never manufacture it:

8. **Unescape** (`text_norm.unescape`): strip a lone backslash immediately before a
   punctuation/symbol character (`\(`, `\)`, `\.`, ...). A backslash before a letter, digit or
   underscore is LEFT ALONE — that is LaTeX (`\rm`, `\alpha`), a content-bearing command, not an
   escape to undo. Chosen over the alternative shape that strips a backslash before ANY single
   character (docs/54-repair-road/scripts/A-ladder.py's `\\(.)`, which turns `\rm` into the bare
   letters `rm` — a real content change masquerading as agreement); the shape kept is the
   lookahead form from docs/54-repair-road/scripts/V-v_a.py:77-81 (`\\(?=[^\w\s])`), which deletes
   only the backslash and never touches what follows.
9. **Punct-free**: drop every character outside `[^\w\s]`, then collapse whitespace runs to one
   space (again). Applied identically to both sides, so a merge like `"e.g."` → `"eg"` costs
   nothing — the same merge happens to the reference and the candidate alike.

Containment for the analyst stage is then tested **space-free** on both the window and the
output stream (`w.replace(" ", "") not in out.replace(" ", "")`) — the CJK path already worked
this way; the word path is now unified onto the same rule instead of keeping two containment
tests that happened to agree. Window construction still runs on the SPACED, punct-free `ref`
(`make_windows`), so `words` counts in a run stay meaningful word counts, not character counts.

Every `audit_analyst` block (and J32-B's per-chunk `chunk_survival`, §6) carries a
`normalisation` record naming exactly which regex pair ran: `{"unescape": true,
"punct_free": true, "space_free": true, "regex_id": "j32a-v2"}` — a future change to either
regex is a version bump on `regex_id`, not a silent drift in what "near-exact" means (this is
exactly the rule R5 exercised: `j32a-v1` → `j32a-v2` when `punct_free` changed, §9.4).

## 4. Core algorithm

For each witness page (skip pages with < 15 normalized words — image-only/blank):

1. Cut **non-overlapping 12-word windows** (final short window kept if ≥ 6 words).
2. **Fast path:** Python substring test (`window in output_stream`) against the one
   normalized output stream. Expect the vast majority of windows to pass here.
3. **Fuzzy fallback** on miss: find the window's rarest word via a prebuilt
   word→positions index of the output stream; run `rapidfuzz.fuzz.partial_ratio`
   only against a ±window-length slice around each anchor occurrence (never against
   the whole document). Pass at **≥ 90**.
4. Page score = passed / total windows.
5. Merge adjacent failed windows into **runs**; a run ≥ 2 windows (~24+ words) is a
   reportable omission — record page, word count, and the run's first ~10 words as
   a human-readable excerpt. Isolated single-window failures are usually
   normalization noise; count them but don't excerpt them.

Doc score = window-weighted mean of page scores.

Split/merge tolerance is structural (we search a single normalized stream), so no
special alignment algorithm is needed.

## 5. Tripwires (deterministic, witness-free unless noted)

- **Degeneration:** any normalized line occurring > 20× in output, or output zlib
  compression ratio a strong outlier vs. the running baseline of prior books —
  catches OCR repetition loops (classic Marker/LLM-OCR failure; olmOCR 2 tests the
  same class).
- **Page-coverage ledger:** count of witness pages bearing text vs. witness pages
  with ≥ 1 surviving window. A page with text and zero survivors is a dropped page.
- **Asset ledger:** embedded raster count (pymupdf) vs. files in `assets/`. Report
  delta; images are out of scope for text survival but a large delta is a flag.
  **Amended 2026-08-20 (S101, P-0 — docs/41 §2):** the last clause is WRONG as written and is
  withdrawn. A large delta is *not* a flag: `Best Practices` (465-page scan, one image per
  page) reads **−416** and that means OCR worked; `Cybernetics` reads **+92** against **zero**
  image XObjects because its figures are vector drawings Marker cropped from the rendered page.
  The two counts are different KINDS of object and never match by construction, so the delta is
  a **count, not a coverage measure**, and it feeds no verdict — `compute_verdict` does not read
  it, correctly. What P-0 changed is only that the number now **reaches a human**: rendered on
  the Assay card in both surfaces (`room.js` `assetLedger`, `main.js` `assetLedgerLine`), both
  sides always shown, labelled "count only", absent rather than zero when unmeasured. Real
  figure **coverage** — does each source figure region have an output image overlapping it —
  is **P-1**, unsigned, and needs its own semantics (docs/41 §2 P-1).
- **Reverse-containment sample (anti-hallucination):** 200 random *output* windows
  sought in the witness (same matching rules). Low score = invented text. Sampled
  because precision is a tripwire, not a gate.
- **Scan lane only (reference-free, QuPipe-style):** dictionary-hit rate over output
  words (wordfreq or a bundled wordlist), garbage-token rate (tokens with no vowel /
  mixed-alnum junk).
- **Per-chunk input-window survival (J32-B, signed Rab 2026-09-05, ACCEPT-TIME, ANALYST
  STAGE):** the fence (`analyst.py`'s asset-token multiset check) proves the chunk's images
  survived; it sees neither a DELETED paragraph nor an INFLATED rewrite BY CONSTRUCTION (the
  held University 4e run's chunk 23/78 lost 361/308 words; chunk 296 read 673 words in, 5,164
  out). After the fence passes, `text_norm.chunk_survival` measures the fraction of the INPUT
  chunk's own 12-word windows (same normalisation ladder as §3 steps 8-9) that still turn up,
  space-free, in the candidate. `ANALYST_CHUNK_SURVIVAL_MIN = 0.50` — below it, REJECT: the
  original chunk ships and the rejection is recorded with `reason: "survival"` (§7 manifest
  schema, §9.4 measured). **This guard sees DELETION only** — a candidate that repeats or pads
  its input keeps every input window and scores ≈1.0 (measured: 2×/7× duplication → 1.0; J34,
  unsigned, is the inflation guard). Unlike every OTHER tripwire in this section, this ONE gates
  AT ACCEPT TIME, per-chunk, not report-only over the finished document — the accept/reject
  decision it feeds already existed (the fence); this is a second reason a chunk can reach it.
- **The `</think>` leak guard (SYM-074, ACCEPT-TIME, ANALYST STAGE):** qwen3:8b (a thinking
  model, asked `"think": false`) leaked a bare `</think>` into shipped text twice (held
  University 4e lines 8779 and 13744) — `_generate` returned `reply["response"].strip()` with no
  filter. Checked immediately after generation, BEFORE the fence, on both backends: if `<think>`
  or `</think>` occurs anywhere in the candidate, REJECT (`reason: "think_leak"`) — the whole
  chunk is suspect, never stripped-and-kept (docs/12: the analyst can only be rejected, never
  edited).
- **The inflation guard (J34, signed Rab 2026-09-05 "J34 1.5x reject", ACCEPT-TIME, ANALYST
  STAGE):** the survival guard above is DELETION-ONLY by construction. After it passes,
  `text_norm.word_ratio` measures output words / input words — raw whitespace-split on the fenced
  chunk and candidate, the exact measurement signed on (2026-08-30 University 4e journal: **500
  hash-matched passed records of 623 passed in the raw journal** — the 123 whose input hash no
  longer matches today's chunking are UNMEASURED, not measured (docs/34; S116 fleet lane A):
  chunk 296 = 5,170 / 681 = 7.59×, the next highest 1.18×, 1 of 500 above 1.25 / 1.5 / 2 / 3;
  re-measured against the SHIPPED function at S116: 1 of 500 rejected, chunk 296 at 7.5918,
  second highest 1.1750, 0 unmeasurable). **A CJK input** (no inter-word spaces; `is_cjk`, the
  same rule `make_windows` uses) is counted in non-whitespace CHARACTERS on both sides — R1 of the
  S116 verify fleet: under the word count a verbatim-doubled CJK chunk read 1.0 (`Observed`,
  selftest J34 (g) keeps that as its watched control). `ANALYST_CHUNK_INFLATION_MAX = 1.5` — above it,
  REJECT (`reason: "inflation"`), the original chunk ships. Strict `>`: 1.5 exactly passes. A chunk
  with 0 input words reports `ratio: null` and is NOT rejected. The ratio rides the journal on
  passed chunks too (beside `survival`), so the next calibration is read off the record rather
  than re-derived.

## 6. Stages and provisional thresholds

ALL thresholds ship in **report-only mode** until calibrated (§9). Numbers below are
priors, not law.

| Stage | Kind | Witness | Flag | Fail |
|---|---|---|---|---|
| convert (clean lane) | fidelity | pymupdf text layer | page < 0.85; doc < 0.97; any run ≥ 50 words | — (report-only until calibration; then promote doc-level criteria per Rab's sign-off) |
| convert (scan lane) | agreement | embedded OCR layer | page < 0.70; dict-hit < 0.80 | — (agreement never hard-fails; it flags zones) |
| analyst (qwen format) | containment | the Marker doc itself | — | doc < 0.995 OR any run ≥ 25 words |

Analyst-stage matching is **near-exact**: normalization only, no fuzzy fallback
(the reference is perfect; tolerance would only hide rewrites). An analyst FAIL
parks the bundle exactly like a pre-flight card does — the fence extended from
links to every sentence.

**Per-chunk accept-time gates (J32-B, SYM-074 — signed Rab 2026-09-05), the other side of the
analyst stage from the DOCUMENT-level `doc < 0.995` row above:** these run WHILE the book is
being analysed, one chunk at a time, and decide whether THIS chunk's candidate ships or the
original does.

| Guard | Threshold | Action | Checked |
|---|---|---|---|
| `</think>` leak (SYM-074) | the two literal ASCII tags, contiguous, case-sensitive (`<thinking>`, `</THINK>`, a tag split by a newline, or HTML-escaped are NOT caught — Observed, measured against the shipped guard: only the bare, contiguous, correctly-cased close tag fires; the observed qwen3:8b leak is exactly that bare close tag; widening is Rab's) | REJECT, `reason: "think_leak"` | before the fence |
| asset-token fence (pre-existing) | token multiset must match exactly | REJECT, `reason: "fence"` | after the leak check, before survival |
| input-window survival (J32-B) | `ANALYST_CHUNK_SURVIVAL_MIN = 0.50` | REJECT, `reason: "survival"` | after the fence passes |
| output/input word ratio (J34, 2026-09-05) | `ANALYST_CHUNK_INFLATION_MAX = 1.5` (strict `>`) | REJECT, `reason: "inflation"` | after survival passes |

A chunk with 0 scoreable input windows (a short chunk) reports `survival: null`, never `0.0` —
SYM-057's rule applies here too: an unmeasurable result must never read as a failing one, so it
is NOT rejected; a chunk with 0 input words reports `ratio: null` under the same rule. `chunks_rejected`
(§7) now means ALL FOUR reasons together (three until J34 landed, 2026-09-05); `rejections` (§7) is
the breakdown.

## 7. Manifest schema (Python owns this; widget only renders)

```json
"fidelity": {
  "version": 1,
  "convert": {
    "witness": "pymupdf | embedded-ocr",
    "kind": "fidelity | agreement",
    "doc_survival": 0.982,
    "pages_scored": 431,
    "pages_flagged": [211, 212],
    "runs": [
      { "page": 211, "words": 51, "excerpt": "the viable system model requires that every" }
    ],
    "tripwires": {
      "degeneration": false,
      "page_coverage": { "with_text": 431, "surviving": 431 },
      "asset_delta": 0,
      "reverse_sample": 0.99,
      "dict_hit": null
    }
  },
  "analyst": {
    "doc_survival": 0.998, "runs": [],
    "normalisation": { "unescape": true, "punct_free": true, "space_free": true,
                      "regex_id": "j32a-v2" }
  },
  "verdict": "pass | flag | fail"
}
```

**A sibling key, not this block** (J32-B/SYM-074, 2026-09-05): `manifest["analyst"]` (analyst.py's
own `process()` meta — `model`, `backend`, `chunks_passed`, `chunks_rejected`, `chunks_failed`,
`chunks_resumed`, `chunks_generated`, `duration_s`, the NUM-6 token/goodput fields) now also
carries `"rejections": {"fence": n, "survival": n, "think_leak": n, "inflation": n}` — the breakdown
behind `chunks_rejected` (the fourth bucket is J34, 2026-09-05). Both `analyst/done` event emits (the
inline path and `apply_analyst`'s `--resume` path) carry the same key, T17-pinned parity; the shipped
frontmatter gets two derived lines, `rejections_survival: n` and `rejections_inflation: n` (a human
reading the note itself, without opening `manifest.json`, sees whether either NEW gate fired at all).
The S61 chunk journal's records carry `survival` and, since J34, `ratio` beside `reason`.

## 8. Integration

- **Script:** `windows-converter/fidelity_audit.py`. CPU-only; must never touch the
  GPU. New dep: `rapidfuzz` into marker-env if absent (MIT, C-backed, tiny).
- **Long paths:** any read of the vault clone MUST be long-path-safe (`\\?\` prefix)
  — pre-L15 bundles keep ≥300-char paths (Textor = 349, reproduced ENOENT; see the
  2026-07-20 findings register in coordination/messages/).
- **Invocation:** by the watcher, after convert completes and after the analyst
  stage completes. An audit crash must NOT fail the conversion — wrap it; emit an
  `audit`/`error` event and continue the line.
- **Events:** emit `{"stage": "audit", "event": "scored" | "flagged" | "failed" | "error", ...}`
  into `events.jsonl` with doc_survival and run count.
- **Widget:** the verdict becomes a channel you can see and steer — full design record
  in **§13 (The Assay)**. Core law, restated: **terracotta ONLY on `fail`** — pass and
  flag never pulse. A number lives on the lever it informs (docs/13); serde-default empty
  = feature hidden (config-key pattern).
- **Vault:** the `fidelity` block rides the existing manifest.json through the
  unchanged exporter. No exporter changes in this build.

## 9. Calibration plan (FIRST action after the script runs)

1. Sources for all 4 vaulted books are in `C:\Users\Bndit\ml\library\drop\done\`;
   outputs are in the vault Library clone
   (`...\Obsidian and Zennotes Vault\Library\Inbox\...`). Brain of the Firm is
   scan-lane (agreement mode); the others exercise clean-lane + at least one
   analyst-formatted doc (Designing Freedom, marker+analyst-local).
2. Run the audit over all 4. Collect score distributions and EVERY reported run.
3. Present the flagged runs to Rab verbatim (excerpts, not just counts) — the tool
   must show its false alarms before it is allowed to pulse terracotta.
4. Set enforcement thresholds from that data; only then enable `fail` verdicts.
5. Record measured runtimes (expect: witness 5–15 s, audit seconds, < 1 min/book).

### 9.1 Pre-calibration data (measured 2026-07-20 UTC, degeneration tripwire prototype; full findings register: coordination/messages/2026-07-20T03-30--desktop-degeneration-findings-brain-of-the-firm.md)

Rab visually discovered degeneration loops in the vaulted Brain of the Firm; a
prototype of the §5 tripwire (zlib ratio + max repeated word-trigram per paragraph,
paragraphs ≥ 200 chars) was run over all 4 vaulted books. Results:

- **Brain of the Firm (scan lane): INFECTED.** ~140K of 1.14M chars (12.3%) in two
  zones — lines ~1594–1668 and ~2758–2814 of the vaulted md. Worst blocks: a
  32,294-char heading "## The Control of the Control of…" (trigram ×2,152, zlib
  0.003), a 29,477-char "## The Stage of the Stage of…" (×2,267), a 22,019-char
  block (×1,674). Adjacent paragraphs show OCR-misread words (drivation,
  clausitying, "We taw") → source is Marker's OCR decode stage, not the analyst.
  Same source page emitted multiple degraded copies (three "We saw in the last
  chapter how" variants) — duplication accompanies degeneration.
- **Designing Freedom / bojieli (CJK; zlib only) / Textor: clean.** Textor's single
  flag (zlib 0.433, trigram ×8, normal philosophy prose) is a false positive of the
  prototype's loose trigram threshold.
- **Threshold separation is clean in this corpus:** true loops have zlib ≤ 0.17 OR
  trigram ≥ 42; legitimate repetitive content (tables, TOCs, prose) sits at
  zlib ≥ 0.31 AND trigram ≤ 31. Production prior: flag at **zlib < 0.20 OR
  trigram ≥ 40** → zero false positives, catches every known-true loop. Calibrate
  further per §9, but start there, not at the prototype's (0.18 / 8).
- **Brain of the Firm is the labeled true-positive specimen** for §9: the audit must
  flag its two zones. Suggested S27 validation loop: audit catches it → re-convert
  (loops are typically nondeterministic; embedded OCR layer is fallback for the two
  zones) → audit passes → supersede-swap into the vault (Designing Freedom pattern).

### 9.2 Recalibration after the Cybernetics false positive (measured 2026-07-21)

The first NEW document dropped after the audit went live — a table-and-diagram-dense
cybernetics *models* book (Dubberly & Pangaro, 91 pp, born-digital clean lane) — tripped the
degeneration tripwire and, in `enforce` mode, was held. Reading the flagged content showed a
**false positive**: no OCR loops, only legitimate structure.

- **Two false-positive vectors, both confirmed by reading the held markdown:**
  1. *Dense markdown tables* tripped the **zlib** half. The flagged blocks were table regions —
     `| Result = EV Preserved<br>…` (zlib 0.111) and `| Participant A | Participant B | |---…`
     (zlib 0.153). Tables compress hard (structural `|`, `---`, `<br>`) but their **words vary
     → low trigram** (×28, ×10). Real loops (Beer) are trigram ×1,674–2,267.
  2. *Repeated section headings* tripped the **repeated-line** check — `#### a. goal of model`
     (×48), `b. description` (×30), `c. components and processes` (×35), one per model.
     Legitimate template structure, distributed through the document.

- **Recalibration (implemented in `fidelity_audit.degeneration()`):**
  - Block rule `OR` → **`AND`**: flag only when a block is BOTH `zlib < 0.20` AND `trigram ≥ 40`.
    Real loops satisfy both; tables (low trigram) and clean prose clear.
  - Repeated-line check: count the **longest contiguous run** of an identical non-blank,
    non-table line (`> DEGEN_LINE_REPEAT`), not total occurrences. A stuck loop repeats
    contiguously; headings/table rows recur but are distributed (run of 1).

- **Re-verified over all five documents** (Beer + Cybernetics + Designing Freedom + bojieli +
  Textor): Brain of the Firm still flags (zlib 0.003, trigram ×2,267); Cybernetics and the other
  three clear. **Zero false positives; the true positive preserved.** Separation is now enormous
  (table max trigram ×28 vs. loop min ×1,674).

- **Lesson for the register:** the trigram is the reliable loop discriminator (loops repeat
  *words*); zlib and total-line-repeats are confounded by legitimate dense structure (tables,
  templated headings). The §9.1 corpus had no table-dense document, so this class went
  unrepresented until the first live drop — exactly the "show its false alarms before it is
  allowed to pulse terracotta" safeguard (§9 step 3) doing its job.

### 9.3 The table-aware gate — SYM-067 → J29 (measured 2026-09-04, signed Rab)

The §9.2 recalibration cleared **dense** tables (their words vary → low trigram). A **sparse**
grid is the opposite case: `| | | |` rows repeat the same three tokens hundreds of times, so the
trigram half fires AND zlib crushes it — the loop signature, with no loop in it. First seen S112
on the Damodaran 2025 4e anchor: 26 flagged blocks, `repeated_lines` 0, zero decoder loops on
reading; the whole `fail` verdict rode on it (degeneration is the only convert-stage path to
`fail`, §12).

- **Repair** (`fidelity_audit._blank_table_rows`, J29): every pipe-table row (`^[ \t]*\|.*\|[ \t]*$`)
  is blanked to a whitespace-only line before the per-paragraph pass (a space, not an empty line —
  an empty line would split an interleaved loop into fragments; fleet lane B, D11), its line
  terminator kept, so `line` and `md_lines`
  still address the body as shipped; the count travels beside `blocks_total` as
  `table_rows_stripped`. The `strip_table_rows=False` path is kept only so
  `degeneration_selftest.py` can show the decoy tripping on the old path (D2).
- **Re-verified over the whole anchor + held corpus on disk** (34 markdown files, CPU, read-only):
  exactly three verdicts flip, all Damodaran 2025 4e bundles (26 → 0 blocks). The held University
  4e keeps **one** block — line 8776, `{1 - t}` × 441, SYM-056's unterminated `\begin{array}` —
  a real runaway that must stay flagged, and does. Brain of the Firm still flags (trigram ×2,267
  / ×143); Diagnosing, Ashby, Valentine keep their verdicts with fewer exemplar blocks.
- **Declared blind spot** (`degeneration_selftest.py` D5): a loop that emits ONLY table rows is
  invisible to the gate — the repeated-line check (§9.2) never counted `|` rows either. Residue,
  not a catch, until a specimen demands it.
- **Lesson for the register:** the trigram discriminator (§9.2) is reliable on *words*; a
  structural token repeated *as* words is the one way to fool it, and the repair is to take the
  structure out of the text before measuring, not to move the threshold.

### 9.4 The J32-A normalisation ladder (measured 2026-09-05, signed: Proposal A; **re-stamped
2026-09-05 for R5 v2**)

§3 steps 8-9 (unescape, punct-free) applied to the analyst-stage comparison only. **v1 shipped
with a defect** (below): `text_norm._PUNCT` was `[^\w\s]`, a superset that deleted every
backslash unconditionally — so `unescape`'s letter-vs-punctuation rule never reached a
comparison, and `\rm` compared equal to `rm` (the exact outcome the ticket rejected). **R5**
(verifier GO_AMENDED, 2026-09-05) changed `_PUNCT` to `[^\w\s\\]` (regex_id bumped
`j32a-v1` → `j32a-v2`) so only `unescape` may ever remove a backslash. Every number below is
v2, THIS run's (`fidelity_audit.audit_analyst`, marker-env interpreter, CPU, read-only against
`C:\Users\Bndit\ml\library`, `scratchpad/j32a_measure.py` + `scratchpad/j32a_univ4e_pin.py`
with their `sys.path` pointed at this checkout's `windows-converter/`) — not quoted from docs/54
or from this same section's own prior (v1) stamping:

| Pair | Before (doc_survival / runs_total) | After v2 (doc_survival / runs_total) | Verdict moved? |
|---|---|---|---|
| Investment Valuation, Damodaran 4e (2025) | 0.9525 / 234 | 0.9817 / 51 | no (fail → fail) |
| Best Practices, Valentine (analyst-local rerun) | 0.9303 / 89 | 0.9578 / 47 | no (fail → fail) |
| Diagnosing the System, Beer | 0.9791 / 1 | 0.9886 / 0 | no (fail → fail) |
| claude-code-up-and-running | 0.9493 / 14 | 0.9644 / 9 | no (fail → fail) |
| bojieli ai-agent-book (CJK) | UNREAD (no prior fidelity.analyst block on disk) | 0.9975 / 0 | n/a (pass) |
| Brain of the Firm (Beer, with OCR) | UNREAD (no prior fidelity.analyst block on disk) | 0.9732 / 31 | n/a (fail) |

**The "Before" column, corrected:** the stored `fidelity.analyst` block for Damodaran 2025 4e
and Valentine predates the `runs_total` key, so `len(runs)` (capped at 25) is not the true
total — this section previously reported 25/25 for both, which is that cap, not the count.
Re-measured against the SAME ref/out text with the BASE (pre-J32-A) module
(`git show 08a7742:windows-converter/fidelity_audit.py`, a self-contained file at that
revision): Damodaran 2025 4e is **234**, Valentine is **89** — the values now in the table.
`doc_survival` was never affected (it does not depend on the capped list).

`runs_total` moves per book for the same reason as before: escape/punctuation noise no longer
manufactures false run boundaries, and the ladder's word-count shift changes where a 12-word
window falls. **No verdict moved on any of the six** — every book still gated by
`ANALYST_DOC_FAIL = 0.995` exactly as before.

**THE PIN — held University 4e (`14c66834bdfeaa2e`)**, reference rebuilt from the LIVE library's
slice cache (`.chunk-work/14c66834bdfeaa2e/slice-*/slice.md`, concatenated in order, then
`rewrite_image_links` — the exact SYM-073-cause reproduction), read-only:

| | Before (pre-J32-A, from manifest.json) | After v2 (this run) |
|---|---|---|
| doc_survival | 0.9402 | **0.9807** |
| failed windows | 404 (denominator not carried pre-ladder) | 762 of 39,507 |
| runs_total | 404 | 82 |
| verdict | fail | fail (unchanged) |

**v1 (this section's own prior stamping) measured 0.9838 / 641 of 39,461 / 59 / fail** — quoted
here as `641`, not the `639` an earlier build report read (the verifier fleet independently
re-measured 641 twice; 639 was wrong). **v2 moves lower on doc_survival and higher on failed
windows/runs_total than v1** (0.9807 vs 0.9838; 762 vs 641; 82 vs 59) — expected, not a
regression: v1's punct_free was silently deleting every LaTeX backslash (`\rm`, `\alpha`, `\times`
and friends) as if it were punctuation, which let more windows match than should have; v2 keeps
those backslashes on both sides of the comparison (they are real content, not noise), so fewer
windows now falsely agree. **The verdict stays `fail`** either way: this book's analyst pass has
real paragraph deletions (docs/54 §2, SYM-074/J32-B below) that no version of the ladder
forgives — narrowing false loss was never meant to launder a real one.

**The v1 defect and its fix, reported rather than silently worked around (docs/47 rule 1):**
with v1's `punct_free` deleting every backslash unconditionally and always chained after
`unescape` (`punct_free(unescape(x))`), `unescape`'s letter-vs-punctuation distinction had **no
observable effect on the final compared strings** — `punct_free(unescape(x)) == punct_free(x)`
for any `x` (case (g)'s negative control in `analyst_audit_selftest.py` had to disable BOTH
rungs together to demonstrate a break under v1; disabling `unescape` alone changed nothing,
because `punct_free` was a superset action). **R5 fixes this**: `_PUNCT` now excludes the
backslash (`[^\w\s\\]`), so `unescape` is the only function that may ever remove one, and only
before punctuation — case (e) now asserts THROUGH `fa.audit_analyst` that `\rm` vs `rm` is a
real loss (`doc_survival < 1.0`) while the escape-only case (a) still survives at `1.0`; case
(e')'s negative control restores v1's regex and watches case (e) go falsely green. Disabling
`unescape` alone now also breaks case (a) (Observed: `doc_survival` 0.0) — the two rungs are
independent tripwires again, no longer one pipeline.

**A consequence outside this ticket's scope, flagged not fixed:** J32-B's own calibration pin
(§9.5 below) and OPEN-TASKS.md's J34 row both quote chunk 296's survival as measured by
`text_norm.chunk_survival` — the SAME function this fix changes, because `chunk_survival` chains
`punct_free(unescape(...))` exactly like `audit_analyst` does. Both were measured under v1;
re-measured against the now-fixed v2 module (`scratchpad/j32b_named_chunks.py`), chunk 296 reads
**0.159**, not v1's **0.7907** — the fix makes the guard SHARPER (v1's backslash-deletion was
inflating survival scores generally, not just for this chunk), so J34's headline number and its
"below 0.50: 2 of 500" / "below 0.60" counts are now stale. J34 is the coordinator's ticket
(OPEN-TASKS.md), not touched here; this is reported so whoever signs it next re-measures first.

### 9.5 The J32-B survival-guard calibration pin (measured 2026-09-05)

Replayed `.analyst-work/d58db211c41b0e17/chunks.jsonl` (the 2026-08-30 attempt, 646 records) read-
only against a rebuild of TODAY's chunking of the held University 4e marker body
(`analyst.fence`/`analyst._chunks` on the slice-cache reproduction), matched via the journal's own
hash validation (`analyst._load_journal`): **516 of 646 records validate against today's
chunks** (the other 130 were chunked differently that run — expected, not a discrepancy). Of the
**500 validated PASSED records**, running `text_norm.chunk_survival` on each (input = today's
matching chunk, output = the journal's shipped text) gives, **re-stamped 2026-09-05 for R5's v2
fix** (this table was measured under v1 when first written; `text_norm._PUNCT` changed since,
and `chunk_survival` uses it too — see docs/47 rule 1 and §9.4's consequence note above):

| Bucket (cumulative) | Count (v1, superseded) | Count v2 | of 500 |
|---|---|---|---|
| survival < 0.50 | 2 | **3** | 0.6% |
| survival < 0.80 | 5 | **6** | 1.2% |
| survival < 0.90 | 12 | **14** | 2.8% |

docs/54's expected neighbourhood at baseline normalisation was 5/32/100 of 500 — a citation, not
re-measured here (a DIFFERENT normalisation than this ladder, docs/54-repair-road/VERIFIED.md,
`Verified` there). The **3 chunks below 0.50 under v2** (23, 78, 296 — v1 undercounted at 2
because its punct_free was deleting backslashes on both sides, inflating some chunks' scores)
are exactly the population `ANALYST_CHUNK_SURVIVAL_MIN = 0.50` is built to catch — they were
SHIPPED as "passed" in the 2026-08-30 attempt (this guard did not exist yet) and would be
REJECTED under this ticket's guard today.

**This guard sees DELETION only:** a candidate that repeats or pads its input keeps every input
window and scores ≈1.0 (measured with `tn.chunk_survival`: 2× and 7× duplication of a 12-word
chunk both → 1.0). The runaway chunk 296 (681 words in → 5,170 out, per the 08-30 journal) scores
**0.159** under this (v2) ladder — v1 measured 0.7907 here too, now stale for the same reason as
the bucket table above — and **0.14** at docs/54's baseline normalisation (a citation,
`docs/54-repair-road/VERIFIED.md`, not re-measured here; a different, non-shipped normalisation).
Inflation is **J34** (OPEN-TASKS, PROPOSED, unsigned): output/input word ratio, chunk 296 =
**7.59×** vs the next-highest chunk at **1.18×** (re-confirmed this build — word-count ratios do
not depend on the punct_free regex, so this figure is unaffected by R5).

## 10. Deferred (add only when evidence demands)

Reading-order property checks (olmOCR-style before/after pairs) · TEDS for table
structure · CDM for formulas · LLM triage of flagged zones (optional, never a gate)
· convert-station live % (separate queue item, unrelated).

## 11. External grounding (research trail)

olmOCR-Bench / olmOCR 2 (Ai2): deterministic binary property checks over soft
metrics; unit-test rewards — the validated core this design extends from curated
benchmark to zero-touch production gate. OmniDocBench (CVPR 2025): component
metrics, adjacency-search-match split/merge tolerance. ISRI/ocreval: CER/WER
vocabulary. Marker's own benchmarks: heuristic alignment + LLM judge (corpus QA,
not per-artifact). Reference-free QE literature (QuPipe, HTR-without-GT,
confidence-proxy studies): scan-lane tripwires. Broder shingle containment:
the asymmetric-recall primitive. Full links in the design session transcript
(Fable 5, 2026-07-19).

## 12. Enforcement decision — SIGNED 2026-07-20 (Rab)

The §6 report-only priors are now calibrated (§9.1) and the enforcement policy is
**signed**. This closes the "awaiting threshold sign-off" gate that had blocked S28.

**What gates (→ `fail`):** exactly two signals, both structurally unambiguous.

1. **Degeneration** — OCR/LLM repetition-loop corruption (§5). Witness-free, so it gates
   on **either lane**. Thresholds `zlib < 0.20 OR max-word-trigram ≥ 40` per §9.1.
2. **Analyst near-exact loss** — the Marker doc is a perfect reference, so `doc < 0.995
   OR any run ≥ 25 words` is a rewrite, not reflow.

**What stays report-only (→ at most `flag`):** survival/agreement score, page-coverage
flags, omission runs, garbage rate, reverse sample. Acceptable books measured **0.76–0.96**
survival (legitimate reflow) — gating on them would false-fail good work and erode the
terracotta signal. They **localize**, they do not judge.

**Explicitly NOT adopted:** a clean-lane survival gate (e.g. `doc < 0.97`). Considered and
rejected for the reason above; revisit only if §9-style calibration on a clean-English
book ever justifies it. The clean-English `fail` threshold remains uncalibrated (no
clean-English book is vaulted).

**Verified 2026-07-20:** `compute_verdict` rewritten to the above and run over all four
vaulted books' markdown. Result — Brain of the Firm → `fail` (degeneration True; worst
block zlib 0.003, trigram ×2,267); Designing Freedom, bojieli, Textor → `pass`
(degeneration False). **Zero false positives**; the prototype's loose-threshold Textor
false alarm (§9.1) is correctly cleared. The verdict is now recorded honestly in every
manifest; the widget projects it (§13).

**Enforcement is an action, separated from the verdict.** `compute_verdict` always runs
and records the honest verdict. Whether a `fail` actually *parks* a bundle is a separate
lever — `audit_mode()` reading `C:\Users\Bndit\ml\library\audit-mode.txt`
(`report` | `enforce`, default **report**, mirroring `analyst-mode.txt`). In `enforce`, a
`fail` verdict moves the bundle to `…\ml\library\held\<sha16>\` (with its `fidelity`
block) and emits `audit/held` instead of shipping. The lever is flipped from the widget
(§13); wiring the hold into the ship paths + live-testing it on the Beer re-audit is part
of the dedicated build session (§13, "buildable now vs the build session").

## 13. The Assay — widget projection (design record, docs/13 grammar)

The audit becomes a channel the operator can **see** (observation) and **steer** (control).
Framed in the vocabulary of the books this pipeline is ingesting (Beer's VSM): the audit is
**System 3\*** — the sporadic channel that looks straight into operations, past a reporting
line that once said "all green" while 12.3% of a book dissolved; its terracotta pulse is the
**algedonic signal**, reaching the operator only when a hand is required; and it is a
**variety attenuator** — a whole book collapses to one glyph, expanding into evidence only
when it must. Design pitch (rendered in the widget's own language): the "Assay" artifact,
2026-07-20.

**Surfaces (all pure projection — Python owns the `fidelity` block, the widget renders it):**

- **`◎ assay` — a sixth line station**, between `✳ gate` and `⇈ ship` (where the audit
  runs). Carries a verdict dot: green `pass`, amber `flag`, **terracotta `fail` — the only
  one that pulses** — plus the last book's survival number. Standing observation in one glyph.
- **The assay card** (appears like a pre-flight card, on `flag`/`fail`; terracotta border on
  `fail`, amber on `flag`):
  - **the damage map** — the book as a track, the loop zones as terracotta bands; you *see
    where* the rot is (aim #2: localize, don't faith-check) instead of reading 400 pages.
  - **the runs, verbatim** — each suspect run's size, repeat count, and own first words
    (the tool shows its evidence — and its false alarms — before it is allowed to pulse).
  - **`report ⇄ enforce`** — the one control lever, writing `audit-mode.txt` (§12), exactly
    as the `✳` gate selector writes `analyst-mode.txt`.
  - **`⟳ re-convert`** — the remedy trigger (next slice, see below).
- **Ship receipt** (`last_receipt`) gains the fidelity verdict alongside convert/analyst.

**The remedy loop, honestly bounded.** `⟳ re-convert` re-runs the GPU lane and re-audits.
The vault swap **cannot** go through the pipeline: dedup skips an already-vaulted source
(THE SUPERSEDE GAP — exporter TODO, ThinkPad lane, phase-gated). So the remedy stages a
**manual content-replace** (the Designing Freedom `9e40b2b` pattern) until the exporter
supersede flow lands. Drawn as such in the design, not papered over.

**Buildable now vs the dedicated build session.** Everything above is *designed and specced*
here. The Tauri build itself is a dedicated session (the rebuild ritual — kill the widget
first, `cargo clippy -D warnings`, build, live-verify — can't be faked from a doc pass):

- *Now, verifiable Desktop-lane, done this session:* the verdict-policy change
  (`compute_verdict`), the `audit-mode.txt`/`held/` lever contract (above), verified against
  the corpus.
- *The build session:* the Rust commands (`assay_status` reading manifests → station+card
  state; `audit_mode_get/set`; receipt verdict), the frontend (station, card, damage map,
  enforce toggle), the CSS, wiring `_enforce_hold` into the ship/defer/resume paths, and the
  `⟳ re-convert` remedy + its manual-swap staging. Then live-test the Beer flag→re-convert→
  re-audit→supersede loop on the retained calibration specimen.

## 14. Closing the loop — the supersede export (design record, 2026-07-25)

§13's remedy loop dead-ends at **THE SUPERSEDE GAP**: `⟳ re-convert` re-runs the GPU lane on
the *same source PDF*, so the better bundle carries the **same `source_sha256`**, and the
exporter's dedup (`linux-converter/converter/exporter.py:129–141`) sees the SHA match and
`EXPORT-SKIP`s it — the improved copy is discarded and the degraded note never moves. Until now
the only fix was a **manual content-replace** in the Desktop clone (the Designing Freedom
`9e40b2b` pattern). This section designs the automatic path. **The build is ThinkPad-primary
(the exporter) with a Desktop companion (intent authoring); a dedicated session, not this one.**

**14.1 The core problem — SHA can't tell remedy from accident.** A deliberate remedy re-convert
and an accidental re-drop of the same PDF are *identical* by `source_sha256`. So supersede needs
an **explicit intent that travels in the manifest**, and — the invariant that keeps the create-only
contract (`exporter.py:14–20`) intact — that intent must be **authored by nothing but a deliberate
`⟳` click.** No marker ⇒ no field ⇒ exporter skips exactly as today. Accidental re-drops stay safe
by construction; supersede is a *named, opt-in exception*, never the default.

**14.2 The contract — one manifest field, authored on the Desktop.**

```json
"supersede": { "reason": "audit-remedy", "from_verdict": "fail" }
```

- `windows-widget/.../assay.rs::reconvert` (today `assay.rs:135–153` just copies `drop/done/X`
  → `drop/X`) additionally drops a companion marker, e.g. `drop/X.supersede.json`, carrying the
  vaulted note's prior verdict.
- `windows-converter/convert_and_ship.py` consumes the marker when it picks up `X` and stamps the
  `supersede` block into the manifest it already builds (`convert_and_ship.py:344–355`), then
  deletes the marker. The field is **absent** on every non-remedy conversion (serde/`.get()`
  default — same pattern as the `fidelity` block, §7).

**14.3 The exporter's supersede branch — locate-don't-assume, replace-in-place.** Replaces the
current dedup block. On a manifest that carries `supersede`:

1. **Verdict guard first (SIGNED — hard-refuse `fail`, §14.4).** If the *incoming* bundle's own
   `fidelity.verdict != "pass"`, do **not** supersede — log `EXPORT-SUPERSEDE-HELD` and keep the
   staging copy. A remedy that didn't actually fix the book must never overwrite the vault.
2. **Locate the live note.** `git grep -l -F <source_sha> main -- *manifest.json` in the **bare**
   repo → the manifest path(s). The note may have been **filed out of `Inbox/` by Rab** — the
   dedup comment (`exporter.py:19`) already anticipates this — so the target is *the located
   path's parent*, never a recomputed `Inbox/<slug>--<sha8>/`.
   - **0 matches:** intent said supersede but nothing is vaulted → fall through to a normal create,
     log the anomaly (`EXPORT-SUPERSEDE-MISS`).
   - **>1 match:** ambiguous — `EXPORT-FAIL`, keep staging. Never guess which note to overwrite.
3. **Preserve identity; replace contents only.** Keep the **existing note's `.md` filename and
   folder** (read it from `git ls-tree HEAD:<target_rel>` — the non-`manifest.json` file);
   write the new markdown under that *old* name, `git rm` the old `assets/`, add the new, overwrite
   `manifest.json`. A re-convert may compute a different slug — supersede must **not rename**, or
   `[[wikilinks]]` break and the note jumps folders.
4. **No-op guard.** If the new note bytes equal the vaulted note's (nothing improved), skip with a
   log — don't mint an empty supersede commit.
5. Commit `supersede: <slug> (audit-remedy, fail→pass)`, log line `EXPORT-SUPERSEDE`, then the
   **unchanged L12 gate** (push, `cat-file -e` the commit and every blob in the bare repo) before
   removing staging. Crash-safety mirrors the create path (`exporter.py:146–172`): a
   commit-but-no-push resumes by finding the new note sha already at `HEAD:<target_rel>` and
   re-pushing/re-verifying rather than re-copying.

**14.4 Decisions — SIGNED 2026-07-25 (Rab).**
- **Verdict guard = hard-refuse `fail`.** The exporter supersedes **only** on an incoming `pass`.
  A still-failing re-convert is held, never lands. The swap can never regress a note (§14.3 #1).
  (`pass-or-improved` was offered and *not* adopted — kept for a later revisit if a partial remedy
  is ever wanted.)
- **Intent is authored only by `⟳`.** Never by verdict, never by a re-drop, never a global mode.
- **Ambiguity refuses; a miss degrades to create** (§14.3 #2).

**14.5 The honest bound — plumbing may be necessary but not sufficient.** Beer failed on an OCR
decoder **loop** (§0, §12: 12.3% repetition). If today's Marker re-converts Beer to the *same*
loop, this export path is correct and still lands *nothing* — the incoming verdict stays `fail`
and the hard guard (14.4) holds it. Closing the loop *on Beer specifically* may therefore also need
a **convert-side change** (a degeneration-triggered OCR retry with different params — cf. the S32
`--recognition_batch_size 32` cap, or an OCR-DPI bump). That is a separate slice; the supersede
export is worth building regardless, because it is the missing rail every future remedy rides.
Drawn as such, not papered over.

**14.6 Build split — BOTH HALVES SHIPPED.**

| Side | File | Change | Status |
| --- | --- | --- | --- |
| **ThinkPad** | `linux-converter/converter/exporter.py` | the supersede branch (§14.3) | ✅ **S43** (`bd02fc0`) |
| Desktop | `windows-widget/.../assay.rs` | `⟳` authors the intent marker | ✅ **S44** |
| Desktop | `windows-converter/convert_and_ship.py` | consume marker → `manifest["supersede"]` | ✅ **S44** |

The manifest `supersede` field is the seam between the two machines. What remains is the **live Beer
test** on the retained calibration specimen (§14.5 caveat stands) — it needs the Desktop pipeline
running and a real vault write, so it is Rab's call, with him present.

**14.7 The marker — the Desktop contract (built S44).**

`⟳ re-convert` is the **only** thing in the system that authors supersede intent. It writes

```
<gpu_pipeline_dir>/drop/.supersede/<source-filename>.json
  { reason, source, from_verdict, source_sha256, requested_at_epoch_s }
```

- **Provenance is read from disk, not from the UI.** `assay.rs` looks up the source's newest manifest
  across `anchor/`/`pending/`/`held/` for `from_verdict` + `source_sha256`, so the intent records what
  the pipeline actually holds. A missing record costs only provenance — **the click is the intent**;
  the marker is still written (with nulls) and the remedy still runs.
- **Ordering is load-bearing.** The marker is written **before** the PDF is copied into `drop/`. The
  watcher polls every 5 s; a convert that began before the intent existed would ship as an ordinary
  create and the remedy would be **silently lost** to dedup. If the PDF copy fails the marker is
  rolled back. If the marker cannot be written the re-queue is **refused** — queueing a convert that
  provably cannot supersede would burn a GPU run to no effect.
- **Invisible by construction.** A dot-prefixed *subdirectory* clears all three existing scans with no
  change to any of them: the watcher skips non-files, dotfiles and non-`.pdf`; `line.rs::count_pdfs`
  counts only `.pdf` (so `drop_waiting` cannot be inflated); `room.rs::file_nodes` lists only files
  (so no phantom node appears in the Convert/Intake drill trees).
- **Consume-once.** `convert_and_ship._take_supersede_marker()` reads *and deletes* the marker at the
  top of `convert()`, before any work — so an intent can never outlive the click that authored it and
  latch onto a later drop of the same filename. A corrupt marker is deleted too. Losing an intent
  (crash, failed convert) is the **safe** direction: the remedy reverts to today's dedup-skip.
- **The sha guard** drops the intent when the file actually converted is not the one the widget
  pointed at (same filename, different book). Defense-in-depth rather than load-bearing: the exporter
  locates by the *incoming bundle's own real sha*, so even a mis-attached intent could only replace
  that file's own note, and only on a `pass`.
- **Fail-safe.** Both converter helpers are wrapped so they can never change a conversion's outcome
  (§8; the S42 rule for touching the core converter). Absent/failed intent ⇒ absent field ⇒ the
  exporter's unchanged create-only path.

*Residual case, stated honestly:* a marker written but never consumed (watcher off, PDF deleted by
hand) does persist. If that filename is later converted it would carry the intent — but the blast
radius is bounded by the exporter locating on the incoming bundle's real sha and requiring `pass`, so
the worst case is replacing that same source's own note with a better conversion of it.

## 15. The Marker body sidecar (J33, signed Rab 2026-09-05)

**Where it lives.** `windows-converter/convert_and_ship.py::_write_marker_body_safe` writes the
PRE-analyst Marker body — `body` at the exact point `_audit_convert_safe` sees it, before any
analyst branch — beside the bundle as `<bundle_name>.marker.txt`, into `tmp_dir` before that
directory is copied or tarred to every downstream site: the anchor copy, `pending/` (defer), or
`held/` + the shipped tar (Verified for the anchor site by `T18` in
`convert_and_ship_selftest.py`, same `shutil.copytree(tmp_dir, ...)` idiom `main()` uses;
Inferred, not separately exercised, for pending/held/the tar, which copy or tar the identical
`tmp_dir` by the identical mechanism). It is written unconditionally — a book converted with no
`--analyst` gets the sidecar too, since a repaired-later held bundle (J31) may need this
reference even if no analyst ever touched it. `manifest.json` gets COUNTS never the payload:
`marker_body: {file, bytes, sha256}` (mirroring `_attach_blocks_safe`'s J24 shape exactly). On
any fault the key is simply absent and the book converts exactly as it did before J33 — never an
exception (docs/15 §8's fail-safe rule; `T18` watches this by monkeypatching the write to raise
and by a negative control that removes the call entirely).

**Why this exists (SYM-073).** The manifest's `fidelity.convert` audits the PRE-analyst body; the
held `.md` is the POST-analyst text (§6/§7 above). A repaired held bundle (J31) needs to re-audit
against BOTH references, and the analyst reference is this exact PRE-analyst text — which, for a
book analysed inline (`--analyst`, the University Edition voyage), existed on disk nowhere but
`.chunk-work/<sha16>/slice-*/slice.md`, swept the moment the NEXT book starts chunking
(LATEST-BOOK retention). The sidecar is that reference, made durable.

**Why OUT of the vault (Rab's slot, 2026-09-05 — same shape as blocks.json/J28).** The name
itself, `.marker.txt` rather than `.marker.md`, sidesteps the whole class of "exactly one `.md`"
guards the pipeline carries (six named in the S115 brief: the exporter's supersede scan, the
Repair Bench's open scan and picker, `_anchor_copies`, `coverage_rescore.py`, `acceptance.py`;
`room.rs`'s file listing is cosmetic and lists every `.md` regardless) — none of them needed to
learn a second filename, because none of them match a `.txt` suffix. `linux-converter/converter/
exporter.py` keeps it off the vault exactly the way `blocks.json` is: `SHIP_MARKER_BODY_TO_VAULT
= False` (lever-waiver, flips only on Rab's word), `_marker_body_status`/`_record_marker_body`
fold `{present_in_bundle, shipped, bytes, file}` into the manifest BEFORE any vault write —
MERGED into the Desktop's `{file, bytes, sha256}`, never overwritten, because the sha256 is what
J31's `--reaudit` will need later to prove which text a repair was compared against —
`_skip_marker_body` keeps it out of the create-path copytree (composed with `_skip_blocks` via
`_combine_skip`, since `shutil.copytree` accepts only one `ignore` filter and either lever may be
OUT independently), and the L12 blob gate skips verifying a blob it was told not to create. Under
supersede, the sidecar is swapped exactly the way `blocks.json` is: dropped first under the OLD
note's name (`old_md_name`'s stem + `.marker.txt` — identity tracks the note, never the incoming
bundle's own slug), re-added only if the lever ships it — proven by
`linux-converter/tests/test_exporter.py`'s four J33 tests, mirroring J28's template
(`test_marker_body_held_is_recorded_and_sha256_survives_the_fold`,
`test_marker_body_ships_byte_identical_when_the_lever_says_in`,
`test_bundle_without_marker_body_records_absence`,
`test_supersede_marker_body_out_stale_sidecar_does_not_survive`).

**No new event.** The coordinator's default (docs/54 §J33 step 1): the manifest key IS the
record, so no `convert/marker_body` event verb was added — fewer undispositioned keys, no new
vocabulary for `event-vocab.js`/the manual, no new `T7`-style parity row. A write fault prints a
non-fatal line to stdout rather than emitting an event; there is no live reader of this key yet
for an event to reach.

**Cost, measured read-only on the live University Edition slice cache** (`held/14c66834bdfeaa2e`'s
`.chunk-work/14c66834bdfeaa2e/slice-*/slice.md`, 7 slices, 1,377 pages) — `Observed`, this
session, concatenating the slices in order (`sum(len(s.read_bytes()) for s in sorted(slices))`,
before `rewrite_image_links`, which only rewrites image targets and does not materially change
the byte count): **3,486,636 bytes ≈ 3.49 MB**, ≈ 2.53 KB/page for this book — in the same
neighbourhood as docs/54 §3's ≈ 3.46 MB / 3.49 MB-on-disk figure (that number was re-measured
here, not quoted). At 0 in the vault while the lever stays OUT — a goal the code now delivers on,
not merely a plan.

## 16. The re-audit road (J31, D-1 signed Rab 2026-09-05)

**The rule (D-1).** After a Repair Bench repair, `fidelity.final` — the REPAIRED held text
audited against BOTH references — is the verdict-bearing block:
`fidelity.verdict = compute_verdict(final.convert, final.get("analyst"))`. A human repair may
therefore change a verdict, but only WITH provenance: `fidelity.reaudit` names the old verdict,
the reason, and (when the manifest carries `repairs`) a digest of what was repaired. The
historical `fidelity.convert` and `fidelity.analyst` blocks are NEVER touched — they stay exactly
what they were the day the book converted, a record of what the pipeline itself first measured;
only `final`/`verdict`/`reaudit` are added.

**The verb.** `convert_and_ship.py --reaudit <held/<ID>>` (a sha16 or a
`<sha16>--superseded-<stamp>` sibling), dispatched in `main()` before `--resume`/`--reanalyze`,
under the SAME unconditional `acquire_card_mutex()` every entry takes (docs/37 §3.2) — harmless
here, since this whole span is **CPU-only**: `audit_convert`'s pymupdf witness extraction and
`audit_analyst`'s text comparison, never Marker, never ollama, never the GPU. Everything runs on
a `tempfile.TemporaryDirectory(prefix="fp-reaudit-")` staging COPY of `held/<ID>` — never in
place. The copy excludes the Repair Bench's own working files (`*.bench-bak`, `repairs.jsonl`,
`REPAIRS.md`) and keeps everything else (`assets/`, `blocks.json`, the J33 sidecar). The bundle's
own `.md` is found by the same "exactly one `.md`" scan every other site uses, EXCLUDING
`REPAIRS.md` by name (the S79 precedent, `prototypes/repair-bench/bench.py`'s `GENERATED_MD`) —
a held bundle whose repair session left a report behind must still resolve to one `.md`, not two.

**The two references.** The PDF witness is `drop/done/<manifest["source"]>` (via
`fp_paths.root("drop_done")`) — absent, and the re-audit REFUSES (`audit/reaudit_refused
{bundle, sha, reason: "pdf missing"}`, non-zero exit, held bundle untouched). The Marker
reference — what J33's sidecar exists FOR — is `<bundle_name>.marker.txt` if present in the held
bundle, else the slice cache (`.chunk-work/<sha16>/slice-*/slice.md`, concatenated in order and
`rewrite_image_links`-ed, exactly SYM-073's own reconstruction recipe); the block records which
one it used as `reference: "sidecar" | "slice-cache"`. If NEITHER exists and the manifest carries
an `analyst` block, the re-audit REFUSES (`reason: "analyst reference unavailable"`) — a book that
WAS analysed keeps needing an honest analyst-stage answer; dropping that stage to manufacture a
prettier verdict is exactly the failure mode D-1 exists to prevent. A book with no `analyst`
block at all (Valentine, Cybernetics) simply carries `reference: null` and no `final.analyst` —
honest absence, not a stand-in pass.

**The outcomes.** Still `fail`: the manifest is written back IN PLACE at `held/<ID>/manifest.json`
(the `final`/`reaudit` blocks land even on a still-fail attempt — the record of the attempt
itself, not only of a successful one) and nothing else happens — `_enforce_hold` is never called
(there is nothing fresh to park; a duplicate beside the existing occupant would only confuse the
assay), and `ship()` is never called. `flag`/`pass`: the SAME opt-in provenance authoring every
other remedy path uses (`_stamp_supersede_safe`, `{"reason": "reaudit", "from_verdict": <old>,
"source_sha256": <sha>, "requested_at_epoch_s": <now>}` — the exact shape `reanalyze()` already
stamps for its own remedy) is folded into the manifest, written to BOTH the staging copy and
`held/<ID>` itself, then `_enforce_hold(staging, ...)` (a no-op here — the on-disk verdict it
re-reads is the fresh flag/pass, not fail — kept only because it is the ONE chokepoint every ship
path passes, docs/15 §12's alarm doorway) and `ship(staging, ...)`. On a successful ship,
`held/<ID>` is renamed to `held/<ID>--reshipped-<stamp>` — **never deleted** (S65: a held bundle
may carry a human's repair work); if the rename fails (Windows: the bench may still hold a file
open) the bundle is left in place with a printed warning rather than lost.

**A flag re-audit ships to staging, but the exporter supersedes a vaulted note only after a human
bless** (`linux-converter/converter/exporter.py:402`, read and confirmed this build — CRLF, not
edited: `if not (verdict == "pass" or (verdict == "flag" and blessed is not None)): ... return`,
i.e. `pass` supersedes on its own, `flag` needs `bless.json`). The re-audit's own `audit/scored`
record above (`phase: "final"`, `reason: "reaudit"`) is exactly what that bless click reads —
`pass` supersedes a vaulted note on the exporter's next export sweep with no extra step; `flag`
waits for the human bless. **For the 7 held bundles today, none of which is vaulted, both fall
through to an ordinary create** — a re-audit that reaches `flag`/`pass` here ships a NEW note,
not a replacement, until the corresponding source is vaulted at least once (EXPORT-SUPERSEDE-MISS
— there is nothing yet for `flag`/`pass` to supersede).

**The events.** `audit/scored` fires with `phase: "final"`, `reason: "reaudit"`, and the exact
bless()-shaped fields `assay.rs::bless` needs from the newest such record for a source:
`source`, `kind`, `doc_survival`, `runs`, `runs_total`, `degeneration`, `verdict` — the same
signature `_audit_convert_safe`'s own emit uses, just naming this scoring's phase/reason.
`audit/flagged` follows when the verdict is not `pass`. Then `audit/reaudit {bundle, sha,
from_verdict, verdict, reference, repairs_digest}` names the whole attempt as one record, so a
reader never has to diff two `audit/scored` events to see what changed.

**`--dry-run` means nothing happens, at all.** The same staging-copy audit runs and the verdict
prints, but NOTHING is written back (neither the staging copy's manifest.json nor
`held/<ID>`'s), nothing ships, and **no event is emitted — not even a refusal**. The hazard this
avoids: `assay.rs::bless` finds the NEWEST `audit/scored` record for a source and trusts its
verdict; a dry-run `audit/scored` would become that newest record and silently change what a
later human bless click, on a book the dry-run never actually touched, is agreeing to. The
`--reaudit` implementation suppresses every emit uniformly under `--dry-run` (refusals included)
rather than trying to reason case-by-case about which specific event carries the hazard — a
flag named "dry" should mean dry, full stop.

**Two new event verbs.** `audit/reaudit` and `audit/reaudit_refused` — `windows-widget/src/
event-vocab.js` and `docs/22-engineering-manual.html` both name them (T19's vocabulary-parity
check, T7-shaped). `observability/schemas.json` picked up both automatically (A4's scope
includes `events.jsonl`) — `--write` then `--check` PASS, `schema_registry_selftest.py` 18/18.

**Dispositions.** Two GLITCHes surfaced under `glass_detector.py --since 08a7742 --enforce`:
`widget:from_verdict` and `widget:requested_at_epoch_s`, both pre-existing fields in
`assay.rs`'s own `⟳`/`⟲` marker-authoring code (docs/15 §14.2), pulled into `--since` scope only
because J31's new `_stamp_supersede_safe` call reuses the SAME key names — the exact
name-based `--since` mis-scoping already on record four times (docs/31 §5.2 item 7,
`widget:source_sha256`'s own entry). Dispositioned INTERNAL; `assay.rs` itself was not touched.
The J31-specific manifest keys (`final`, `reaudit`, `text_audited`, `reference`,
`repairs_digest`) never register as a key at all under this detector's harvester — the same
class J33's `marker_body` fell into (a bare `manifest[...] = {...}` assignment or an `emit()`
kwarg whose value is a variable, not a literal dict, is invisible to it); a bare disposition
entry for a key the harvester cannot see was tried and reverted (it manufactures a
stale-signature failure in `acceptance.py` instead of a real one — confirmed empirically, not
assumed).

**Tests.** `convert_and_ship_selftest.py` T19 (28 checks + a 2-check vocabulary-parity section +
a 2-check negative control watching the whole verb): the staging copy's exclusions/inclusions;
the historical blocks staying content-identical while the verdict moves under D-1's own control
(history says `fail`, `final` says `pass`); the bless()-shaped `audit/scored` fields and the
`audit/reaudit` event; a still-fail attempt writing in place without shipping; a flag/pass
attempt shipping the STAGING dir (never `held/`) and renaming to `--reshipped-`; THE REFERENCE
CONTROL (a decoy sidecar/held-body pair proves `audit_analyst` was handed the sidecar, never the
held `.md`); both refusal reasons (missing PDF, unavailable analyst reference) leaving the held
bundle byte-hashed-unchanged; `--dry-run` appending zero lines to the REAL `events.jsonl`
(the one check in the whole battery that does NOT monkeypatch `emit`, on purpose — dry-run's
claim is about the real writer, not a recorder standing in for it). Negative control: blanking
`fid["final"] = final` inside `reaudit()` and confirming the final block is really absent
(check (2) would go red against this mutation) while the verdict itself still computes
correctly — isolating the control to exactly the one removed line. Residual, found live during
this build and left as evidence the harness bites: the staging-copy assertions initially read
empty because `shutil.copytree` recurses into itself for subdirectories, so the naive "first
call wins" capture caught the nested `assets/` call, not the top-level one — fixed by matching
on source-path identity instead of call order (see `run_reaudit`'s `_spy_copytree`); a second,
independent bug (the md-discovery glob matching `REPAIRS.md` too) was caught by these SAME
tests before any manual inspection, cascading nearly every check in the block — real signal,
not a decorative harness.

**Not built this ticket (Rab's other slots, docs/54 §4):** J32 Proposals A/B (the normalised
analyst comparison and the per-chunk survival guard) and SYM-074 (the `</think>` leak filter)
are separate tickets in the fleet; `--reaudit` does not touch either. University Edition's own
road to the vault is unchanged by this ticket alone — it needs J32-B's deletion/inflation guard
restoring the lost paragraphs (from the Marker body J33 now retains) before a compliant re-run
of the analyst could pass the analyst-stage gate; `--reaudit` only makes that FUTURE repaired
book re-scoreable once it exists.
