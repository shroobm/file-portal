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
  "analyst": { "doc_survival": 0.998, "runs": [] },
  "verdict": "pass | flag | fail"
}
```

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
