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
  space-free, in the candidate. `ANALYST_CHUNK_SURVIVAL_MIN = 0.50` (**0.80 since 2026-09-09**, Rab's "B" after
  DDIA 2e held at 0.9683 with a 264-word paragraph deleted from a chunk that passed at ≈0.56; basis = the
  09-05 measurement, 6 of 500 below 0.80 — the pre-move re-measure was impossible, see S118 §4) — below it, REJECT: the
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
| input-window survival (J32-B) | `ANALYST_CHUNK_SURVIVAL_MIN = 0.80` (0.50 from 2026-09-05 to 2026-09-09) | REJECT, `reason: "survival"` | after the fence passes |
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
Beside `rejections`, `manifest["analyst"]` also carries `chunk_scores` (J41, 2026-09-09): one
short-keyed row per finished chunk (`i`/`s`/`r`/`x`, manifest only — the journal itself still
dies with the work dir at the end of every run, `chunks_rejected`'s successor for a book that
PASSES) — see `observability/dispositions.json` under `converter:chunk_scores`.

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

### 12.1 Amendment — SIGNED 2026-09-12 (Rab, S131): a degenerate reference block is masked

*Appended, not edited: §12 above stands as signed 2026-07-20.*

**The finding (S130/S131, *Zero to One*, held `cb7e026f3fc02da8`).** Marker looped on page 1 and wrote a
2048-character heading (`# INTERNATIONAL PROPERTY AND ROUTE AND ROUTE…`, zlib 0.028, trigram 202; the PDF's own
text holds no "and route" at all). That block sits in the Marker body J33 retains as the analyst stage's
reference. The Repair Bench cut it from the shipped body, as it should; the near-exact gate then read the cut as a
420-word omission (survival 0.9848, a run ≥ 25 words) — **fail** — while a body that kept the block failed on
degeneration. The two signals of §12 had made a degeneration repair unshippable, and `bless` is written to refuse
a degeneration fail from either side.

**The rule.** Before the analyst stage's windows are built, every block of the reference that the audit's OWN
degeneration detector flags (the same per-paragraph test, uncapped, on the same table-blanked text) is blanked.
Nothing else in the gate moves: the levers stay 0.995 / 25 words, the normalisation ladder is untouched, and the
body side is never masked — a body that kept the disease still fails on the convert gate's tripwire. The analyst
block records what was masked as `reference_masked` (`blocks`: line, line_end, chars, zlib, max_trigram, excerpt;
`words`), so a verdict that leaned on the mask reads as such in the manifest and on the bench. Blanking glues the
block's neighbours together in the reference stream, so a body that kept the block (or put a heading in its place)
loses the windows that span that seam — a dip of a few words, never a run (case (k)). The repeated-line signal
(`repeated_lines`) is not masked: no specimen yet, and a case comes before the rule.

**Measured on the specimen** (`fidelity_audit.audit_analyst`, the repaired body against the sidecar): raw
reference survival 0.9892 with the one 420-word run; masked reference survival 0.9994, no run; verdict **pass**
with the convert gate's own pass (0.9939, 0 pages flagged, no degeneration). Tripwires: `analyst_audit_selftest.py`
cases (h)–(k), including the mask disabled as the watched negative control.

### 12.2 Amendment — SIGNED 2026-09-12 (Rab, S140, "C+A"): the diff-whitelist acceptor (J46)

*Appended, not edited: §12 and §12.1 stand as signed.*

**The finding (S119 R1, measured on the real 492 DDIA pairs; S131, *Zero to One*).** The analyst stage's guards
(the fence, the survival windows, the 1.5× ratio) are per-chunk thresholds: a candidate can pass all three and still
drop a sentence, halve a numeral (`81`), reword, or leak a control token (`/no_think`). On *Zero to One* eight such
holes (~560 words) reached the bench and were repaired by hand (`repairs.jsonl` seq 6–13). Every one was an edit the
analyst is not asked to make.

**The rule.** After the three guards, before a candidate is accepted, `edit_whitelist.reconcile(chunk, candidate,
FULL)` compares the two texts word by word and keeps an edit ONLY if the two spans are the same text under a stated
whitelist — backslash-escapes removed, a link re-syntaxed with the same URL multiset, heading/emphasis/table marks
and citation brackets removed, a line-end hyphen joined, a mis-mapped ligature glyph replaced by its ligature, a
word boundary moved (reflow). Everything else — a substitution, a deletion, an insertion, a numeral change, a
punctuation or case change — reverts to the input's words. **The whitelist IS the policy** (Rab's slot, S119,
unchanged S140): punctuation and case edits are reverted, and so is every substitution — on *Zero to One* the
analyst's `E SCAPING` → `ESCAPPING` is a substitution the whitelist reverts.
Link STRUCTURE is never markup: an edit may not change a span's bracket balance or its count of `[text](url)`
constructs (found at promotion: a dropped opening `[` had read as "markup", and the URL leaked into the text).

**Measured at promotion (S140, `prototypes/analyst-lab/edit-whitelist/promotion_check.py` for the controls, the FULL
audits and the class totals; `promotion_variants.py` for the STRICT and FULL−hyphen rows; the same 492 pairs).**
Controls: accept-all reproduces the shipped body byte-for-byte (0.9718/49); accept-none reproduces the sidecar's
words (1.0/0). FULL: **0.9822 / 24** under the shipped ladder, **0.9969 / 1** under ladder v3c (S119's prototype:
0.9817/24 and 0.9968/1); 1,914 edits accepted (hyphen 670 · markup 549 · escape 339 · markup+escape 184 · mixed 124 ·
reflow 19 · ligature 14 · link 14 · markup+link 1), 1,397 reverted (substitution 609 · punctuation/case 415 · deletion 316 ·
insertion 47 · numeral 10 — digit-for-digit; the prototype's "numeral 321" counted any token with a digit on one side);
no non-whitelisted class among the accepted. (The row before the S140 review read 0.9819/24, 1,919 / 1,390: the two
holes the review closed moved six accepts to the revert side.) STRICT (markup + hyphen, with the always-on quotes unification and the space-free reflow comparison): 1.0 / 0
under both ladders (`promotion_variants.py`; the S119 prototype's STRICT read 0.9998/0 with four seam windows).
The promoted module aligns on exact tokens between anchors and on normalised keys inside an edit region, and judges
a run of adjacent edits as one hunk before falling back to each — the S119 prototype's per-opcode judgement had
starved its own hyphen and reflow rungs (rapidfuzz splits a two-token merge into replace + delete: 1 reflow, 0
hyphen accepts on DDIA) and reverted good repairs beside a bad one.

**What the record carries.** `manifest.analyst.edits` — `accepted` and `reverted` by class, `chunks_reconciled`,
the `whitelist` in force; a passed row of `chunk_scores` gains `e: [accepted, reverted]` when the candidate carried
an edit at all (absent otherwise). The `analyst/done` event's key set is unchanged (T17). Cost ≈ microseconds per
chunk, no GPU. The acceptor changes the shipped TEXT, so `--reaudit` cannot measure it on a held book; a live run
does (S140's C: the re-analysis of the held *Zero to One* through J42's sidecar-aware `--reanalyze`).

**Reviewed (S140, three Sonnet lanes — Logic · Test · Readability — and a refuter; every high finding reproduced).**
Two holes closed the same hour: an apostrophe in a contraction had counted as a ligature garble (`wasn't` → `wasnfft`
would have shipped as a "repair"); two links inside one hunk could swap targets under a URL *multiset* test — the
invariant is the ordered sequence of URLs now. Residue the review named and this section keeps: a whitespace-free run
(a CJK sentence) is one token, so a hunk there that mixes a good edit with a bad one reverts whole; an apostrophe
between letters outside a contraction tail is still a garble candidate; `well- known` → `wellknown` is accepted as a
line-end join (a compound broken across a line is indistinguishable from a hyphenated word).

**Tripwires.** `edit_whitelist_selftest.py` (the two controls, one case per rung with its negative — `\rm` vs `rm`,
a re-targeted URL, a dropped garble with no replacement, `ne` → `fine` named — the reverted classes, the promotion
fix for a reverted deletion's whitespace, the hyphen rung's documented blind spot `well- known`); `analyst_selftest.py`
J46 (a)–(c) with `reconcile` replaced by identity as the watched negative control; J32-B (a) and J34 (b) re-read
under the signed policy (the hyphen join ships, the dropped commas and the four inserted words do not).

### 12.3 Amendment — on Rab's word 2026-09-13 (Desk bf4d5d05, S144): the witness's coverage floor

*Appended, not edited: §12 and §12.1–12.2 above stand as signed.*

**The finding (S142 E1 F5 / S143 E5, Valentine, held `b6fbdd75f6242f53`).** A 465-page scan with no text layer: the scan
lane's witness is the PDF's own OCR text, so the convert gate scored the one page that had any — `doc_survival 1.0 ·
pages_scored 1` — a pass-shaped number over one page in 465. The block printed its denominator (docs/34 holds) and the
verdict did not weigh it.

**The rule.** `audit_convert` now writes `pages_total` beside `pages_scored`. `compute_verdict` reads
`pages_scored / pages_total`; under `WITNESS_COVERAGE_FLOOR = 0.50` the convert gate is at most `flag` — a localiser
(§12: it never fails; degeneration and the analyst near-exact gate stand above it). A block without both counts (every
block written before S144) keeps the verdict it had. The case: `analyst_audit_selftest.py` (m) — 1 of 465 reads flag,
400 of 465 pass, 233 of 465 (0.501) pass, no counts unchanged, and a thin witness never lifts a degeneration fail.

**What it does not do.** It does not measure the pages the witness did not see — that is the gauge's instruments (a
second witness, the ink under the boxes; `measurement/ML-GAUGE-2026-09-13.md`); it only stops a 1.0 over one page from
reading as a pass.

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

### 12.4 Amendment — on Rab's word 2026-09-14 (chat, S150, "Protocol. Signed."): the table-geometry LAYER and CLASS

*Appended, not edited: §12–§12.3 stand as signed. The shipped whitelist (§12.2, FULL) is unchanged by this section — see the lever-waiver below.*

**The finding (S149; S150 E1–E2, measured on both Valentine copies).** A table reaches the analyst as ONE paragraph in one chunk (a pipe table has no blank line inside it) under a prompt that never mentions tables; the whitelist has no class for a shape repair, so a rotated label merged from its letters, a spanning title lifted to a caption or a stray bullet glyph made `•` all revert as substitutions and deletions — while a DROPPED PIPE ships through the markup rung (pipes and separator dashes are stripped for the comparison), leaving a row one cell short. Valentine's Exhibit 8.2 (pp.132–134): three rotated rails read letter by letter (`R l v Ė N U E · 6 O S T s · M G M T · V A Ā O N` for REVENUE / COSTS / MGMT / VALUATION; `S A R T E G Ϋ · F N A N Č Ĺ` for STRATEGY / FINANCIAL — letters missing; `H G H · L L O` for HIGH / LOW on p.367), a title read as one merged cell (`colspan="9"` in the block record) and chopped into fragments in the first half, `٠` for `•`. The census (private `measurement/evidence/s150-valentine-before/`): held 80 tables / anchor 81, every one renders; the only break in the book is the S149 split; the damage sits in a handful of tables.

**The layer — `windows-converter/table_geometry.py` (pure functions, no I/O).** The reading half names the table a renderer reads (`table_blocks`, `cells`, `health` — the S149 rules, the bench page's twin — `read_table`, `census`, `orphan_runs`) and the signatures: the letter column (every piece of a first-column cell ONE glyph, blanks between the runs or a `<br>`-stacked cell), the title-row shape, `<br>` headers, the dot matrix and its stray glyphs. The repair half: `propose` (a `caption` — the spanning title, ≥ 20 characters with a space, lifted above the table, its chopped tail dropped; a `rail` per letter run — the letters and the rows' own text go to a resolver, the word comes back on the run's first row with blanks under it; `dots` — stray glyphs → `•` inside a table that has a matrix), `letters_fit` (the word must contain the letters read, in order, but for ONE confusion and any number of missing letters; `SARTEGΫ` fits STRATEGY, `RlvĖNUE` fits REVENUE and not COSTS), `grid_invariant` (the law: one table on both sides, the same columns, the same rows but for a title lifted to a caption whose text sits above, every cell outside column 1 byte-identical or a stray glyph become `•`, column 1 changed only where a run became a fitting label with blanks under it), `geometry_pass` (propose → apply on a copy → keep only what the invariant admits; the record counts tables, proposals, applied / refused / unresolved, lists every label and caption). A table with a health issue is never touched: the S149 split is the bench's un-split road, not the layer's.

**The class — `edit_whitelist.FULL_TABLES`, rung `table-geometry`.** With the rung in force every table of the input is paired with the candidate's table at the same position (same count, same order) and judged WHOLE by `grid_invariant` before the word alignment sees the text: accepted as one edit or RESTORED from the input whole. So a model's rail repair is admitted when the law holds, and a dropped pipe, a lost row or a reworded cell is restored — the hazard the markup rung left open is closed under this policy. The counts ride `analyst.edits` under `table-geometry` beside escape / link / markup / hyphen / ligature; the layer's own applied / refused are added there too and `analyst.geometry` says which is which.

**The wiring — `analyst.process(markdown, backend, program, tables=None, resolver=None)`.** With `tables` on: the layer runs on the fenced text before the chunks are cut (an image token inside a table is text to it), the word route is the grid program `prompts/grid-word.txt` on the same backend (one short call per rail, `GRID_NUM_PREDICT` 24 tokens; `?`, a non-word, an empty reply or a backend error leave the rail as it is, reported unresolved), the acceptor runs `FULL_TABLES`, the resume key carries `+tables`, the record rides `analyst.geometry` (disposition `converter:geometry`, EVIDENCE). **Lever-waiver: `ANALYST_TABLES = False`** — the layer and the class are OFF in the pipeline and `FULL` is unchanged; the S150 dry run passes `tables=True` explicitly and ships nothing; entering the shipped whitelist is Rab's signature, as every whitelist change has been (§12.2).

**What it cannot do, named before the build (S150 §9a):** the rows a rotated label spans are UNREAD (the label goes on the run's first row; only the picture knows the extent); two rails the OCR ran together (no blank row between COSTS and MGMT) become one label phrase; a title chopped into header fragments is not read as a title; a resolver's word is BOUNDED by the letters, not proven — every label is listed in the record for the eye; a legitimate single-letter column with blanks passes the signature and is refused only by the word check; a split table is never touched. Tripwires: `table_geometry_selftest.py` (the Valentine exhibit, its first half, the p.367 matrix; a rating column, a ratio-name column, a two-heading header and a healthy table as negatives; the invariant's negatives — a cell reworded, a `•` dropped, a row dropped, a pipe dropped, a label that does not fit, a title dropped with no caption), `edit_whitelist_selftest.py` (the class both ways, the pipe hazard both ways, a caption, two tables judged apart, the counts-differ fall-through), `analyst_selftest.py` (the lever both ways, the resolver, a refused word).

#### 12.4.1 Addendum (S151, 2026-09-14) — the rail's word route is the book's own lexicon

S150 E4b measured the word route with the model and the letters-only bound: qwen3:8b returned the letters shuffled, an echo, or a wrong word the letters admitted — four labels no better than the garble. S151 E1 replaced the route: **a label must be a word the book itself uses.** `table_geometry.lexicon(lines)` is every alphabetic token of three letters or more in the body, with its count; a rail's cells are read as what the OCR's glyphs could be (`read_pattern`: a digit is its confusion set — `6` is c, g or b, never any letter; an accented letter its base); a word fits when it places the letters in order but for one confusion, holds at least half its letters in the read, and — for a read of three letters or fewer — fits exactly and is at most one letter longer (`LLO` → LOW, never LABEL, never LOST); the best word is the one that explains the read best (`fit_score`: placed − unplaced − half the missed), with the rows the rail labels breaking ties (STRATEGY over STARTED) and a tie within a quarter point refused; a run of rails the OCR left without a blank row between them is split at the cells where each word's letters end (`lexicon_segments`, a dynamic programme scored by each word's excess over the bar, so two weak words never beat one strong one); a letter read twice across a row boundary is one letter (`boundary_collapse`, plain Latin letters only); every proposal is admitted one at a time by `grid_invariant` (`apply_admitted`). The model is asked only for what the lexicon leaves, and its answer must itself be a word of the book. Measured on both Valentine copies: STRATEGY, FINANCIAL, REVENUE, COSTS, VALUATION, HIGH right; MGMT (an abbreviation) and LOW (LOW and LOG fit a two-letter read alike) left unresolved and said so; zero wrong labels. The lever (`ANALYST_TABLES`) and `FULL` are unchanged — Rab's slot.

#### 12.4.2 Addendum (S151 E3, 2026-09-14) — a title chopped into header fragments is read back through the book

S150's census named a MISSING signature: the first half of Valentine's Exhibit 8.2 carries its spanning title chopped by the OCR into eleven short header cells (`Start | with th | s sour | ce to ir | vestic | ate be | ore m | etina | manag | ement | 1`) above the real header, so a renderer shows the fragments as the column headings and the real headings as a data row. The reading half now sees the shape (`TableReading.title_fragments`: three or more filled first-row cells, each eight glyphs or fewer once bared, above a row with more filled cells). The proposer joins the fragments' letters into one stream and captions the table by three readings in order of trust, each named in the proposal's `how`: **(1) the book's own phrase** — every pipe-row cell and heading of twenty characters or more is a candidate (a continued exhibit repeats its title; in the held copy the repeat is an orphan pipe row, the S149 split, and it still counts), and the one phrase holding the stream's letters in order, 85 % of both lengths, is the caption (`best_phrase`; a second phrase within two letters is a tie, refused); **(2) the book's words along the stream** (`words_from_stream`, a dynamic programme over the letter positions with the rail route's `letters_fit` and `fit_score`, an unexplained letter costing one, only words the book uses twice — the fragments are tokens of the body and must not explain themselves), accepted only when the words explain seven letters in ten, three words or more, five letters on average — a soup of short words ("thesis our ceo ive") is refused; **(3) the fragments joined as read**, twenty letters or more, the header freed and the text left as the OCR left it, said so. Before any of it: a fragment row whose three-letter cells are, half or more, words the book uses twice is a stacked column heading (`Standard | 1 | P- | Lower | Upper` over `Error | t Stat | value | 95 % | 95 %`) and is refused — headings, no caption. The invariant admits a fragment caption when the letters the fragments hold are found in order, four in five, in the caption above. Measured on both Valentine copies with no model: the anchor's 1552 and the held copy's 1556 captioned "Start with this source to investigate before meeting management" (49 of 53 letters in order, the raw join kept on the record), the three regression tables kept their headers, nothing else changed (the diff against E1's output is the caption alone). Residue: the headings guard is the lexicon's; the stacked heading itself is not merged into one header row (`analyst/stacked-heading-rows`).

#### 12.4.3 Addendum (S151 E4, 2026-09-14) — the layer's repairs are scored against a ground truth read from the pages

Until E4 every "right" the table-geometry layer claimed was one reading of the page against the text. Now (private `measurement/`): a ground-truth format per printed table (`truth/FORMAT.md`: caption, one header row, the rails as words with row spans, the body grid, tags of the tag law); the pages rendered by pypdfium2 (`probes/render_pages.py`); a scorer (`probes/table_truth_score.py`, 18 tripwires) that locates a truth table in a copy by its text — a lost table reads "not located", never a neighbour's score — and scores it five ways with numerator, denominator and conditions: the caption (correct / partial / fragments / missing / wrong), the header (headings found, and where a renderer reads them), the rails (word / letters / wrong / absent), the DAS 2002 cell buckets against both denominators (correct / near / wrong / missed / split / merged / unmatched over the truth's cells, spurious over the copy's), TEDS and TEDS-S (Zhang–Shasha over HTML trees) and a GriTS-style factored alignment (not the reference 2-D-MSS, named so). The truth itself is read by a panel — three readers from the rendered page, the converter's text as a second reading only, one packet carrying a planted alteration every reader must refuse — and its reproducibility is measured before it scores anything (Todoran): on Valentine's 14 tables, identical shapes, cell agreement 100 % on 13, 206–207 of 208 on the dense matrix, the one disputed bullet settled by a zoomed look. Scored on both copies, BEFORE against E1's and E3's output: the layer moves every measure the right way on the tables it touches (p.132: caption fragments → correct, headings from a data row to the header, rails letters → words, TEDS 0.866 → 0.967, TEDS-S 0.938 → 1.000) and nothing on the eleven others; the held copy's split half reads "no table" at every stage, which is the un-split's price in a number. What the panel found beyond the layer: a bullet the converter missed, wrapped row labels split over two rows, a coefficients table lost to prose, a partial spanning caption not lifted, a figure and an index read as tables — each a register row. The lever and `FULL` unchanged — Rab's slot.

#### 9.3.1 Addendum (S151 E5, 2026-09-14) — the table-aware gate measured on Valentine's pages (B21)

The held Valentine copy's manifest (converted 2026-07-31, before J29) fails on degeneration with four worst zones; each was mapped to its PDF page, the page rendered (pypdfium2, scale 4) and read. Three zones are tables (Exhibit 8.2's two halves, printed pp. 107–108; Exhibit 3.3, pp. 35–36) — SYM-067's family, a table read as a loop. One is a real loop: on printed p. 117 the OCR turned the list line "assess a company's likely success or failure with a new product launch" into `the purpose of` × 115 (one 2,415-character block, zlib 0.182, trigram 115) — and the anchor conversion of the same PDF, three weeks later, looped on the same printed line. `degeneration()` today, rows blanked: held flagged on that one block (3 tables dropped, 0 loops lost); anchor the same. Rows kept: the anchor's worst block is Exhibit 15.1 (printed p. 219, a real table with a rotated `Critical for Success` rail) padded by the converter to 29,107 characters for 43 filled cells — zlib 0.03, `| | |` trigrams 66 — the specimen of why the AND gate alone did not clear a wide, mostly empty table and the blanking was needed. D5 (a loop emitting only table rows) not observed in this book. Residue: the loop stays in both copies (a body loop is the bench's or the vision route's, not the audit's); the July `degeneration_detail` stays in the manifest until a re-audit.

#### 12.4.4 Addendum (S152 E1, 2026-09-14) — a row label wrapped over two rows is folded back into one

S151's panel found a converter defect the census could not see: a row label printed on two or three lines (`lag1 (log of manufacturing index)`, `Compensation and Benefits`) arrives as two rows — the first with the label's first line and every data cell empty, the second with the rest and the data. The layer now proposes a **fold** (`_wrapped_pair`: the first row's only filled cell its label, the second's label a continuation — a lowercase start or a closing bracket — or the first ending open, the first not ending a sentence, a label column and at least two data columns, the first line ending in a letter or an open bracket), `apply_table` joins the two rows column by column and drops the second, and `grid_invariant` admits a fold only as the EXACT join of two adjacent rows — a body fold joining only where one side is empty, a fold of the header row with the first body row free to join filled cells (the stacked heading, E3). Measured on both Valentine copies with no model: the two labels folded, the diff against S151's output the two folds alone, the scorer's split cells 9 and 7 → 0, every other table unchanged. The first dry run folded nine index entries (two-column entries ending in page numbers, the next starting lowercase) — the rule was tightened on that measurement and both shapes are negatives. The lever and `FULL` unchanged — Rab's slot.

#### 12.4.5 Addendum (S152 E2, 2026-09-14) — a caption chopped into long pieces beside empty cells is joined back

A third shape of the chopped title: p.72's caption arrives as three LONG pieces in the first row beside empty cells (`Quality of Self-Side | Analyst Based on Your I | Prior Experience`), above the real headings — neither one filled cell (the title rule) nor short fragments (the fragments rule). `TableReading.title_pieces` sees it when two or more pieces sit beside an empty cell, the next row is as full or fuller, and the pieces carry a continuation signal (a piece ending in a lone letter, a hyphen or a preposition, or the next piece starting lowercase); the proposer applies the headings guard (single-word pieces the book uses twice are headings), then the book's own phrase, else the pieces joined as read; the invariant admits the caption by the fragment clause. Measured on both Valentine copies: the p.72 caption lifted above its table and the headings in the header row, nothing else changed; scored by the truth, the caption goes from missing to correct. Named risk: a two-heading header that happens to carry a continuation word would read as pieces — the guard catches single-word headings only. The lever and `FULL` unchanged — Rab's slot.

#### 12.4.6 Addendum (S152 E3, 2026-09-14) — a stacked column heading is folded into one heading row

A regression output prints each heading on two lines; the copy carries the upper line as the header row and the lower as the first data row (`Standard | 1 | P- | Lower | Upper` over `Coefficients | Error | t Stat | value | 95%`). S151 E3's headings guard told this shape from a chopped title and refused the caption; S152 E3 makes it a repair: a HEADER FOLD — the two rows joined into one heading row by the page's typography (`_join_heading`: one space between pieces; an upper piece ending in a hyphen joins without one, `P-value`; an upper piece with no letter above a two-word lower piece is the OCR's echo and drops, `t Stat`), the delimiter staying under the new header, and the invariant accepting, for the header row alone, the exact heading join and nothing else. Measured on both Valentine copies: p.179's headings 2 of 8 → 8 of 8 in the header row, the held copy's p.181 1 of 6 → 6 of 6; the anchor's p.181 lost its upper line in conversion (nothing to fold) and p.175's coefficients block is mid-table — both named, neither touched. With E1's wrapped-label fold on the same tables, TEDS rises again and no other table moves. The lever and `FULL` unchanged — Rab's slot.

#### 12.4.7 Addendum (S152 E4, 2026-09-14) — the index named by the census; the figure left to the page

S151's panel called p.421 an index (no table) and p.342 a figure; the copy has both as tables and the block record calls all of them `Table` (measured: no `Figure`, `Picture` or `TableOfContents` block on those pages), so the record cannot supply a census column. The reading half now carries a text signature for the index (`TableReading.index_like`: at most three columns, ten or more rows, at least 35 % of the filled cells an entry — words, a comma, a page number or range; the floor measured on the anchor's index tables, whose entry rate runs 0.39–0.74 because entries wrap onto second lines) — on both Valentine copies every index-like table sits in the index pages, none before it, and none of the panel's truth tables is named; the census reports the count and the lines; the layer proposes nothing there. A quadrant figure with a rotated rail and cells of prose has the same text shape as Exhibit 6.1 (a real table by every reader), so no text rule separates them: that call is the page's — the vision route (Rab's) or a reader panel — and is carried on the register as such. The lever and `FULL` unchanged — Rab's slot.

#### 12.4.8 Addendum (S154 E5, 2026-09-15) — the table-geometry lever is ON, on Rab's word

`ANALYST_TABLES = True` in `windows-converter/analyst.py` since S154 (his word "all signed" in chat, 2026-09-15 02:2xZ, over `coordination/BRIEF-S153-OPUS.md` §1.1). What it does: `analyst.process(tables=None)` now runs the table-geometry layer before the chunks on every book the watcher converts (§12.4–§12.4.7: caption · rail · dots · fold, every repair held to `grid_invariant`) and judges every table through the acceptor's `table-geometry` rung (`edit_whitelist.FULL_TABLES`); the rails' word route asks the book's own lexicon first and the grid program on the local backend only where the lexicon does not decide (one short call per rail, inside the analyst's own GPU run). Not retroactive: the held and anchored copies are as they were; the next converted book carries it. The measure: the census BEFORE/AFTER on that book and the scorer on any table the panel truthed — the evidence at the flip is one book, both copies (S150–S152). The tripwire: `analyst_selftest.py` S154 (a) asserts the default engages the layer (fires when the lever is off — watched firing on 2026-09-15); the resume key carries `+tables` under the lever, so a journal written for the off-state is not resumed. The lever's waiver in the code names his word and the measure; it moves back on his word only.

#### 12.4.9 Addendum (S154 E6, 2026-09-15) — a rotated label begins at its group's first row; the vision route's value, measured

The layer had written a rail's word on the first row that carried a letter and blanked the rest of the run; a rotated label is printed CENTRED in its group, whose first row is often above the OCR's first letter (Valentine p.108: REVENUE's letters on rows 2–5 of a group that begins at row 1). The scorer (private `table_truth_score.py`) now measures WHERE the word sits — `placed`, the truth row carrying it, and `placed_ok`, whether that is the span's first row — and read 2 of 7 resolved labels on their first row on both copies. Three Sonnet readers on the rendered pages (S154 E6's panel: no card, no internet, a planted packet all three caught) read every span identically to the S151 majority — 7 rails on 3 tables, 21 readings, 21 agreements — and p.342's quadrant as a figure, 3 of 3. With that truth the rule was measured into shape: `_tile_spans` gives every rail proposal a `span` — the groups tile the body rows, each centred on its letters (the group runs below the letters by as much as it runs above them, never past the next run's first letter; a midpoint split of the blank rows was the first cut and placed FINANCIAL a row early on p.107 — the scorer read it absent); `apply_table` lifts the word onto the span's first row when every rail cell down to the run is blank or a stray mark (`_stray_mark`: an underscore, a dot, a dash alone — the OCR's read of the label's stem), never onto the header row; `grid_invariant` admits a label on a blank row only with its letter run directly beneath, the letters fitting the word, the strays cleared and the run blank after — a label on the header row, on a blank row with no run beneath, or over another run's letters is refused (selftest §11, 130/130). Measured on both copies: labels on their first row 2 of 7 → 5 of 7; p.107 TEDS 0.967 → 0.980, p.108 0.979 → 0.998; no other table moved. The two left are what no text rule can give: MGMT (the book's lexicon lacks the abbreviation; the page prints it) and p.72's phrase rail in three fragments (not a letter run). That is the vision route's measured value — a per-book reading of the page (a vision model on the card, or Sonnet readers by API) would place 7 of 7 and name the figure; the route is Rab's decision (register: `analyst/vision-route-decision`).

#### 12.4.10 Addendum (S156 E1–E2, 2026-09-15) — the vision route, signed: a reading of the page feeds the layer

Rab's word (chat, 2026-09-15 ~04:2xZ): "signed, use sub agents" — the vision route's shape is SUB AGENTS: Sonnet readers on the rendered page images in a sitting, never a model on the card. Their finding travels with the book as a READING — `vision.json`, format `vision-reading/1` (the private `measurement/truth/VISION.md` says its shape): per table, an `anchor` (text the block itself carries), `kind` (table or figure), and `rails` (each label as printed with the first and last body row it spans). The layer consults it the way it consults the resolver (`geometry_pass(..., vision=)`): a rail's WORD is lent to a run the lexicon and the resolver left unresolved when the letters fit it (MGMT); its SPAN replaces the tiled span (§12.4.9); a rail with no letter run beneath is proposed from its FRAGMENTS when every rail cell on its rows is a substring of the label (p.72's phrase in three pieces) — and `grid_invariant`'s fragment clause refuses a piece the label does not contain (the panel's own plant, "Bonds" for "Stocks"); a table the reading calls a FIGURE gets no repair at all. Nothing a reading says can move a cell outside the rail column. The pipeline: `convert_and_ship` hands `<stem>.vision.json` beside the dropped PDF to the analyst and copies it into the bundle; `apply_analyst` (the J42 re-analysis) hands `<bundle>/vision.json`; a file that is not a reading is refused aloud and treated as absent; a book without a reading gets the text rules alone. The record: `meta["geometry"]["vision"]` (tables matched, words lent, spans taken, fragment rails, figures, unmatched entries). Tripwires: `table_geometry_selftest` §12 (the word, the span, the fragments with the plant as the negative, the figure with its negative control, a reading that matches nothing) 142/142; `analyst_selftest` S156 (a) 40/40; `convert_and_ship_selftest` S156 (the sidecar beside the PDF reaches the analyst and lands in the bundle; the bundle's sidecar reaches the re-analysis; a malformed or foreign JSON is refused) 254/254.

#### 12.4.11 Addendum (S157 E1, 2026-09-15) — a second stacked heading inside a body is a second table: the split pass

Exhibit 12.7's coefficients table (PDF page 200, printed p.175) had been lost since S151: Marker's table detection fuses it into the ANOVA table above it (its stacked heading `Standard | | P- | Lower | Upper` over `Coefficients | Error | t Stat | value | 95%` as two body rows, or — the held copy — as ONE row with `<br>` inside its cells), keeps the Intercept row and the label pieces, and drops the last row to prose (S155 E2 measured that the HTML-tables flag does not change it). The layer now runs a SPLIT pass before the per-table proposals (`propose_splits`, `apply_split`, `split_invariant`, `split_pass`): a body row pair with the first cell empty, no plain number in either (a `95%` heading is not a number), a data row directly above and the pair's own words half or more the book's words (S152 E3's test) — or one such row already stacked with `<br>` — SPLITS the table at that pair, the pair folded into the second table's header; the second table's tail — label-only rows, then past blank lines and one short digit-free non-table line (a page footer) a lone short line and a numbers line of exactly (columns − 1) numeric tokens — is RE-JOINED into one row and the prose lines consumed; a tail of any other shape is left as it is (the held copy's last row is scattered over two prose lines with `10.03` lost by the OCR — a re-join would invent a number). `split_invariant` admits only the exact re-partition: table A's header and rows are the before rows above the pair, table B's header is the pair's fold (or the `<br>` row unstacked), its rows the rest with the one re-joined row equal to the label pieces + the lone word + the prose numbers; nothing invented, nothing lost. Measured on both copies against the S151 truth: p200-t3 (the coefficients) anchor TEDS **0.149 → 0.996** (header 8/8, 17 of 18 cells; the one wrong cell is the label as the OCR spelt it, `log /manufacturin indev)` for `log (manufacturing index)`), held **0.247 → 0.742** (header 7/8; the scattered tail's eight numbers still missed); p200-t2 (the ANOVA, no longer carrying the coefficient rows) anchor 0.226 → 0.406, held 0.308 → 0.482; the twelve other tables unchanged. Tripwires: `table_geometry_selftest` §13 (both shapes; the wrong token count leaves the tail; a number in the pair, no data row above, a mutated re-joined number refused; idempotence; no split on a healthy table) 155/155. The residue: the label's OCR (`(manufacturing index)` read as `/manufacturin` + `indev)`) — a lexicon route for a row label, later; a scattered tail stays scattered.

#### 12.4.12 Addendum (S157 E3, 2026-09-15) — trailing columns nothing fills are Marker's padding: the trim pass

The S155 note on p204-t1 (raw Marker's HTML 0.786 where the pipeline's copy scored 0.550) was read as a lost row. The scorer's recall is 1.0 on every copy of that table: nothing is lost — the copy carries EXTRA columns. Marker pads a table with columns nothing fills (`Regression Statistics`: two real columns and three empty; the ANOVA six and two; fifteen of Valentine's 82 tables per copy, none with a leading empty column). The layer now runs a TRIM pass after the split pass and before the per-table proposals (`propose_trims`, `apply_trim`, `trim_invariant`, `trim_pass`): a table's trailing columns whose header cell and every body cell are blank are dropped and the delimiter row shortened with them, at least two columns kept, never a leading column (the rail column of pp.97/132/133 is empty in the truth's body and letters in the copy), never a table with a health issue or ragged rows, never a column with a glyph in it (S78 §10.5: the thirteen "phantom empty columns" that were a matrix's source columns carrying 418 dots — blank means blank). `trim_invariant` admits only the exact cut: the same rows, each after row equal to its before row with the last k cells removed, every removed cell blank, the delimiter's kept segments unchanged. Measured on both copies against the S151 truth (S157 E1's output as the before): anchor mean TEDS **0.745 → 0.818** (six of fourteen up, none down; p204-t1 0.550 → 1.000, p206-t1 0.688 → 0.880, p264-t1 0.559 → 0.699, the three ANOVA tables 0.406/0.511/0.606 → 0.501/0.579/0.686), held **0.783 → 0.856** (six up, none down; p200-t1 0.647 → 1.000, p204-t1 0.786 → 1.000); recall unchanged on every table; the census: 82 blocks each, filled cells unchanged (2,688 / 2,596), empty cells 610 → 411 and 602 → 397. Tripwires: `table_geometry_selftest` §14 (the shape; the record; a glyph in the column, a leading empty column, ragged rows, a health issue — no trim; the two-column floor; a kept cell changed, a delimiter segment changed, a removed cell not blank — refused; idempotence; the split's ANOVA trimmed after the split) 169/169. The residue: the anchor copy's p200-t1 (0.571) is a different fusion — the ANOVA's title row and half its stacked heading fused into the TAIL of the statistics table above it, so its last column is not empty; a split at a title-shaped body row, later.

#### 12.4.13 Addendum (S157 E15, 2026-09-15) — a run that is an INDEX is not a rail: three refusals before the word route

The shelf probe of S157 E5 printed `labels 4` for Ashby's *An Introduction to Cybernetics* and the lane read only the trims and splits beside it; read at E15, the four labels were the rail route's FALSE POSITIVES on a book with single-glyph row labels: a transition matrix's rows `3 4 5 6` read as the rotated word ELASTIC (the glyph readings that rescue `6OSTs` → COSTS — 3→e, 4→a, 5→s — turn a column of digits into any word of the book), `1 2 D 3 4 5` → IDEAS, `4` / `D 5` → ADDS, and the merged rows `a<br>b` / `c` beside `α<br>β` / `γ` → ABC — four tables of the book with their row labels blanked and a word placed on the first row, admitted by the invariant (the letters fit; the words are the book's). S151's "zero wrong labels" was measured on Valentine's seven rails and carried, at S154, into the lever ON for every book. The layer now REFUSES a letter run before any word is sought, on the record (`_index_run`): (R1) more than half the run's bared glyphs are digits — numbers, not a rotated word (one digit among five, `6OSTs`, stays a rail); (R2) every glyph of the run is one of the table's own column headings — a matrix index (rows a, b, c under headings a, b, c); (R3) a stacked letter cell whose row's other filled cells are stacked to the same `<br>` depth with short parts — merged rows, not a rail (a prose cell's words are not a stack: the first cut counted words and refused the p.367 quadrant's HIGH). Measured: Ashby's labels 4 → 0 on all three copies (the ten runs now carry their reasons in `unresolved_rails`), every other bundle on the shelf unchanged (33 compared), Valentine's six labels and its fourteen truths unchanged (anchor mean TEDS 0.818, held 0.856). Tripwires: `table_geometry_selftest` §15 (R1 on the 3-4-5-6 matrix with ELASTIC in the lexicon; R3 on the a-b / c merged rows; R2 on an a-b-c matrix; the positive controls — COSTS still resolves through its digit, the quadrant's stacked rail beside prose is not merged rows) 175/175. Residue: a matrix whose row labels are real words would still read as a rail (no such table on the shelf); the reading (§12.4.10) settles a doubtful block where a page is read.

#### 12.4.14 Addendum (S157 E20, 2026-09-15) — a tail that duplicates the next table's head is the next table's: the leaked head

E3's residue: the anchor copy's p200-t1 (`Regression Statistics`, its caption already lost by Marker) ended in two rows that belong to the ANOVA table under it — its title row `| ANOVA | | |` and half its stacked heading `| | | Significance |` — while the ANOVA table itself still carried both (`| ANOVA | … |`, `| … | Sig | gnificance |`); Marker's HTML mode made the same fusion (S155). A pass before the trim (`propose_leaks`, `apply_leak`, `leak_invariant`, `leak_pass`): walking up from a table's last body row, rows with no numeric cell whose every filled cell is found in the NEXT table's head (its header and first two body rows — the cell exactly, or its letters inside the head's letter stream with doubled letters collapsed: `Sig` + `gnificance` = `Significance`, the shape an exact duplicate rule refused at E3) are the leak; the topmost dropped row must open with the next table's own first header cell (the leaked TITLE anchors it — a `Notes` row does not); the next table within three lines; a body row kept at least. `leak_invariant` admits only that cut: the kept table is the before table cut at the tail, the next table unchanged, every dropped filled cell non-numeric and in the head. Measured: the anchor's p200-t1 TEDS **0.571 → 0.955** (the caption Marker dropped is the rest; the leak's removal empties the third column, which the trim then drops — 2 columns, 5 rows), the other thirteen truths and the held copy unchanged; on the shelf exactly one leak (this table; the other bundles' counts unchanged). Tripwires: `table_geometry_selftest` §16 (the shape; the pass order with the trim; idempotence; a number in the tail, a tail row that is not the next title, a next table too far — no leak; a kept cell changed — refused; nothing on the healthy fixtures or p.175's split shape) 184/184. Residue: a row that legitimately repeats the next table's title as its own last label would be dropped — none on the shelf; the leaked caption cannot be recovered (it is not in the copy).

## 17. The degeneration rule's two spellings (appended 2026-09-15, S158 E4/E5 — a reading, not a change)

§9.1 states the production prior as **`zlib < 0.20 OR max-word-trigram ≥ 40`**; §9.2 recalibrated it — "Block rule `OR` → **`AND`**: flag only when a block is BOTH `zlib < 0.20` AND `trigram ≥ 40`" — and §12 (signed 2026-07-20) still reads "Thresholds `zlib < 0.20 OR max-word-trigram ≥ 40` per §9.1". **The code is AND**: `windows-converter/fidelity_audit.py` ("AND, not OR (docs/15 §9.2): a loop is BOTH crushed-compressible AND has an extreme repeated word-trigram … The old zlib-OR path false-fired on the Cybernetics table-dense book"; `if ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX`), and the Linux port `linux-converter/converter/degeneration.py` carries the same AND with §9.1/§9.2 provenance. A reader of §12 alone would state the rule wrong — `docs/61-converter-model.md` did, and its §8 corrects it. §12's text stands as signed; this section records which spelling the code implements. (S158 E4, the verifier fleet's V2 lane; confirmed by the Fable lane's own grep.)

### 9.5 Re-measured on this corpus (appended 2026-09-17, S179 E1 — a reading; the thresholds unchanged, his)

**The question** (docs/64 §5; the register row `audit/degeneration-calibration-on-this-corpus`, S178): the tripwire read TRUE on 20 of the 29 desktop manifests that carry it (S178, Observed 02:52Z) and nobody had read whether they were loops. **The method** (`sittings/S179/e1_degeneration_read.py`, `e1_block_reader.py`; CPU only — `degeneration()` is a text function): every conversion under `anchor/` and `held/` (33) re-run on its bundle's markdown with the CURRENT rule (§9.3's table-aware gate, §9.2's `AND`), the manifest's verdict compared, and every flagged conversion's worst blocks READ in their markdown context and judged **LOOP** (the decoder stuck: a phrase repeated with no information between repeats) or **STRUCTURE** (information carried by each repeat).

**Re-run vs manifest: agree 24 · disagree 9.** The nine: **six manifests said TRUE and the current rule says FALSE** — Investment Valuation (1,356 pp) ×3, the Cybernetics Book of Models ×1, Diagnosing's held copy, Zero-to-One's bench-repaired copy: the historical flag fired on TABLE ROWS before §9.3's blanking (`table_rows_stripped` 4,604 on the Damodaran) — the false-alarm class J29 already removed; the manifests keep the old verdict (a manifest is a record, never rewritten). **Two manifests carry NO fidelity block and the current rule says TRUE** — Brain of the Firm ×2 (the §9.1 specimen, converted before the audit existed): `## The Stage of the Stage of the Stage …` (29,477 chars, zlib 0.003, max_trigram 2,267), `## The Control of the Control of …` (32,294 chars, trigram 2,152) — 19–20 blocks: the labeled true positive, confirmed on re-run.

**The fourteen that flag under the current rule, read:**

| book (pp, lane) | conversions flagged | the worst block, read | verdict |
|---|---|---|---|
| Diagnosing the System (184, scan) | 2 | `A. The state of the state of the state of …` — one 8-gram ×155 in 475 words; `… the control of the control of …` ×124 | **LOOP** |
| Zero-to-One (166, clean), before its bench repair | 2 | `# INTERNATIONAL PROPERTY AND ROUTE AND ROUTE AND ROUTE …` — ×199 in a heading | **LOOP** |
| Investment Valuation, University ed. (1,377, clean) | 3 | a 47,419-char block that is an HTML document (a fenced `html` block opening `<!DOCTYPE html>`) inside the markdown; a 21,870-char `$$\begin{array}{lll} {\rm ROC} + …` equation block, max_trigram 441 | **LOOP** (corruption either way) |
| Best Practices for Equity Research (465, scan) | 4 | a list paragraph (2,415 chars, zlib 0.182) whose tail reads `… of the purpose of the purpose of the purpose …` ×112 | **LOOP** (a stutter inside a list item — the block's head is fine, the loop is in its tail) |
| Ashby, An Introduction to Cybernetics (156, clean) | 3 | `A B A B B B A B A B …` (1,975 chars, zlib 0.023, trigram 326) — **the book's own Markov-chain protocols** (Ex. 1: "a protocol of 50 transitions"); a second protocol (`A A B B A B B …`, trigram 488); the third block the S109 runaway `\begin{array}{ccc…}` (36 `c`s — SYM-056's defect, not a loop) | **STRUCTURE** ×2 + a LaTeX runaway |

**The numbers (this corpus, the current rule):** flagged conversions 14 → LOOP **11** · STRUCTURE **3** (all three one book's); by distinct book 6 flagged → LOOP 5 (Diagnosing, Zero-to-One pre-repair, Investment Valuation University, Equity Research, Brain of the Firm) · STRUCTURE 1 (Ashby). **The false-alarm rate: 3 of 14 conversions (21 %), 1 of 6 books (17 %)** — every false alarm the same shape: a block of one-letter tokens (a symbol protocol, an exercise), which the trigram count reads as a stutter because the alphabet is two letters. The six historical false alarms (tables) are already remedied by §9.3 and do not fire under the current rule. **The zero-FP claim (§9.1's "calibrated on the vaulted corpus") does not hold on this corpus; it holds on prose** — every LOOP verdict above is a real loop, and the one STRUCTURE class is not prose.

**What this reading proposes (a gate change — Rab's; posted on the Desk 2026-09-17 S179 E2 in his shape):** a STRUCTURE exemption for blocks whose tokens are overwhelmingly single characters (e.g. ≥ 80 % of words of length ≤ 2 — a symbol sequence, never a sentence), applied BEFORE the zlib/trigram rule the way §9.3 blanks table rows; measured here it would clear Ashby's two protocols and touch none of the eleven loops (their repeats are words). The LaTeX runaway is SYM-056's flag's to name (S175), not this rule's. Until his word: the thresholds stand; the reading stands as the calibration on record.

### 9.6 Ladder v3 — escape-first, cite-anchor — BUILT behind a lever, OFF (appended 2026-09-17, S182 E1; J44 / SYM-076; the ON position his)

**What is built.** `text_norm.prepare_for(markdown, ladder)`: `j32a-v2` = `prepare_output` byte for byte (the suite's positive control: every shape it knows, `chunk_survival` and `audit_analyst` read what they read before); `j32a-v3` = two rungs BEFORE the markdown strip — an unescape whose lookahead includes `_` (`\\(?=[^\w\s]|_)`; `within\_recursive` vs `within_recursive` 0.0 → 1.0; `\rm` vs `rm` still a loss — R5 kept) and Marker's citation link target stripped on BOTH sides (`\(#page-[\d-]+\)`; `[\[n\]](#page-N-K)` vs `[n](#page-N-K)` a failed window → 1.0; a deleted tail still 0.5). The ligature-blind rung is NOT built: counterfactual until gated on a garble glyph in the input (Codex MSG-CDX-0047, accepted). **The lever:** `ladder.txt` under the pipeline root (roots.json `ladder`), read per audit by `fidelity_audit.audit_analyst` and per analyst pass by `analyst.process` through `ladder_lever.read_ladder()` — absent, unreadable or unknown reads `j32a-v2`; only the literal `j32a-v3` selects v3; the manifest's `normalisation.regex_id` names the ladder that RAN. `analyst_audit_selftest.py` (m)–(q): 20/20, with the rungs disabled as the watched negative control.

**Measured (2026-09-17 04:43Z, the REAL `audit_analyst` on held DDIA `fc1f068c3a8eeb63` — the sidecar the reference, the shipped body the candidate; 20,589 twelve-word windows; CPU, read-only; private `sittings/S182/e1_ddia_measure.txt`):**

| ladder | doc_survival | failed windows / 20,589 | runs_total | clears 0.995 |
|---|---|---|---|---|
| `j32a-v2` (shipped; reproduces the manifest to the digit) | 0.9718 | 581 | 49 | no |
| `j32a-v3` (escape-first + cite-anchor, no ligature rung) | **0.9845** | **319** | **33** | no |

**Reading.** 262 of the 581 failed windows (45 %) were the audit's own miscount — a repair the model made, scored as a loss. The verdict on DDIA does not move (0.9845 < 0.995): the residual 319 is content (J45's class: real deletions the acceptor J46 now reverts at accept time) plus the ligature class, which waits for its gate. S118's rung-1-only reading (0.9756/46) and S119's v3c (0.9897/20, ungated ligature) are superseded by this table for what is BUILT.

**What his word does.** One line — `j32a-v3` — into `C:\Users\Bndit\ml\library\ladder.txt`: every audit and every per-chunk guard from the next conversion runs v3, the manifests say so in `regex_id`, and `--reaudit fc1f068c3a8eeb63` re-scores DDIA for free (the sidecar is the reference). Until then the field runs v2 exactly as before this section was written.
