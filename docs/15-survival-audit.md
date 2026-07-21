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
