# docs/60 — The factory that audits itself: Fable's vision beside Rab's

*Written 2026-09-13 (S146 E1) on Rab's word — "Start having your own vision, you know mine, add to it." (Desk e34253e4). His north star is restated first, in his terms, so the additions can be read against it. Every addition names what would make it measurable and the first ticket that moves it. Tags as in docs/21: what is Observed today, what is Intended. Appends only; a struck item keeps its reason.*

## 1. Rab's north star, restated (Historical, from the records and the memory library)

1. **The factory.** A PDF dropped on the ⚡ tile becomes a vault-ready markdown bundle: converted (Marker), audited for fidelity (the analyst, the witnesses, a verdict), shipped over Tailscale, ingested by the exporter, blessed into the Obsidian vault. "The book ships" is the sentence the whole machine exists for.
2. **Nothing reaches him dressed as more than it is.** Every number carries its numerator, denominator and conditions (docs/34); every claim its tag; every record is written before the act and never erased.
3. **Two models, one bus, one human.** Codex verifies, Fable repairs; the relay's deliveries are proven, escalations halt both lanes, and Rab is the only authority on a threshold, a vault, an adoption.
4. **The phone.** A memory-following Claude dispatched from his phone over Tailscale; the Desk as the surface he reads on either device.
5. **The scans.** The ML gauge for scans-only PDFs: what "the model that works" would have to read, instrument by instrument, before anything is trained.

## 2. What I add (Intended unless marked)

### 2.1 Every stage names its own environment
A death on the card that cannot say whose memory the rest was (SYM-132) is a factory that cannot learn from its own failures. **Measurable:** every `timeout`/`stalled`/`converted` event carries the top committers on the card by name; the tracker's receipt lists the longest process in its own window (a census, IB-018). **First tickets:** `converter/gpu-signature-per-process` (S146 E3), `measurement/ceiling-moment-per-process`, the tracker's coverage self-test.

### 2.2 A verdict that is calibrated, and a scan that can pass
Today a scan-lane book CANNOT pass: the audit's agreement witness on a scan is the embedded OCR layer, which a scan does not have — Valentine's fresh anchor scores 1 of 465 pages and fails on the coverage floor (Observed 17:25Z, `fidelity.convert.pages_scored: 1`). The gauge already has the witness the audit lacks (Tesseract, S144 E3: pairs 0.930 over 442 pages, control 0.252). **Measurable:** the scan lane's verdict rests on a second witness with its coverage printed; the floor (0.50) and the pair threshold calibrated on labelled pages, with the calibration's n. **First tickets:** `audit/scan-lane-second-witness`, `gauge/calibrate-floor-on-labels`.

### 2.3 The evidence view travels with the hold
A held book arrives with its evidence card, its overlays and the engine's confidence per flagged page, so a bench session opens on the twenty pages that matter (Observed for Valentine, S145 E5–E7; not yet produced by the pipeline itself). **Measurable:** minutes from "held" to the first repair; the fraction of flagged pages that the bench actually repairs (precision of the attention rule). **First ticket:** `hold/attach-evidence-view`.

### 2.4 A label corpus that grows from every bench session
Every repair Rab makes at the bench is a labelled page (I5 has zero scan labels today, S144 E4). **Measurable:** labelled scan pages ≥ 1, then the gauge's instruments re-read against them (agreement, variability, confidence) with their precision/recall at the page level. **First ticket:** `gauge/labels-from-bench-repairs` (the bench's undo/redo journal as the label source).

### 2.5 Provenance for every lever and every ship
The lever that decides what reaches the vault has no writer on record (SYM-131). **Measurable:** every write to `audit-mode.txt` is an event with old/new/writer/reason; every `shipped`/`held` event names the mode it read; the first ingest reads the verdict (SYM-130). **First tickets:** `pipeline/audit-mode-provenance` (S146 E2), `exporter/ingest-verdict-guard` (E6).

### 2.6 Improvements he can feel
A change that is not visible from the Desk or the card within a minute is not finished. **Measurable:** every episode ends with one journal entry (`sessions/JOURNAL-autonomy-2026-09-13.md`) naming the place to look and the before/after; the Desk carries one line per entry. **First ticket:** `journal/autonomy-experiment` (S146 E1, this doc's twin).

### 2.7 The peer lane kept warm
Codex sleeps; the door brief (docs conv. `door-brief-convention`) is how it wakes without a handoff. **Measurable:** at every close a pointer entry names the records, the tickets and the registers as of that close; at Codex's first confirm after waking, zero questions it could have answered from the brief. **First ticket:** the pointer at every close (in force since MSG-FAB-0095).

### 2.8 The factory's own experiment log
Rab's experiment (S146) is itself an instrument: how far a lane goes on its own word, measured. **Measurable:** per sitting — episodes closed, tickets struck vs added, corrections filed against my own claims (C-rows), CI reds, reverts; the baseline rows (`measurement/baseline/S<N>.json`) already carry most of it. **First ticket:** `baseline/experiment-columns` (episodes, C-rows against self, reverts).

## 3. The order, by cost and reversibility

Provenance and guards first (2.5, 2.1 — small code, tripwired, reversible by one call); the evidence view and the second witness next (2.3, 2.2 — CPU, evidence files, no ship); the label corpus as Rab's bench sessions happen (2.4 — his hands, my instruments); the long GPU runs last and one at a time, sampled (the re-conversions), each under `enforce`.

## 4. What this is not

Not a plan to train a model: the gauge says what a model would have to read before one is trained, and the label corpus is the precondition. Not a lifting of the tag law or the record-first rule — the experiment removes Rab's signature from the loop, not the record from before the act. Not a claim about the phone (2.4 of his star): the Desk is the surface; the dispatch remains his build.

## 3. Corrections (appended 2026-09-16, S159 E5 — the Circle over the converter's evidence; the sections above stand as written)

- **§2.2's "Today a scan-lane book CANNOT pass: the audit's agreement witness on a scan is the embedded OCR layer, which a scan does not have"** is overstated. A FRESH scan has no layer (Valentine: 1 of 465 pages scored, the floor caps the verdict at flag). An OLD scan with an embedded layer IS scored — Diagnosing (scan lane, `lane_reason untrusted_ocr_layer`) scores 156 of 184 pages, well past the 0.50 floor, and fails on degeneration, not on the floor; its witness is the corrupt layer itself ("the witness lies", docs/61 §10.2). The scan lane has two failure classes, not one, and the gauge remedy fits the first.
- **§2.2's "pairs 0.930 over 442 pages, control 0.252"** names the page sample where docs/34 wants the denominator: the reading is **115,126 witness word-pairs found in the body of 123,791 = 0.9300**, over 442 of 465 pages scored (S144 E3, `agreement_probe.py`); the control 0.2524 is the same instrument against Zero to One's body. "442 pages" is where the pairs came from, not what 0.930 is a share of.
