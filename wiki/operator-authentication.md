---
title: How an operator authenticates a hold
section: Product
last-verified: 2026-10-05
verified-against: "10c32cf41bf4a72c5c4745cca42015b3ce64861c"
sources:
  - prototypes/repair-bench/bench.py
  - prototypes/repair-bench/test_textlayer_restore.py
  - prototypes/repair-bench/test_collapse_embedded.py
  - sessions/S220-desktop-2026-10-04.md
---

# How an operator authenticates a hold

Rab's word (2026-10-04 23:13Z): the credit for an audit and its repairs is earned by *authenticating
in sequence and showing the tooling* — the actual PDF read, the page viewed, the fix made in the seat
the local model would take, verified, efficiently — and by a lesson in the records. Three held papers
were taken through the [Repair Bench](repair-bench.md)'s own class (`Bench`, under the converter's
interpreter; every write through `_write_body`, the ledgered chokepoint) and this is what the sequence
costs and where it stops. The episodes: S220 E6 (nucl-ex, a footnote, four passes), E7 (the
text-layer gesture built), E8 (cond-mat.mtrl-sci, one pass). Observed in those records; the numbers
are theirs.

## The seven rules

1. **The page before the markdown.** Render the page (the Scanner's boxed replay or `page_png`) and
   READ it with your eyes before touching the body. The re-score measure (`rescore_preview`) is blind
   to a crop of the wrong region: it read "clear" after a crop that showed the paragraph above the
   footnote (E6, pass 1). Only the eye catches that.
2. **The whole paragraph against the page before deciding what was lost.** What is lost is usually
   smaller than the loop: E8's 200-repeat loop replaced ONE word ("EQUIFORMERV2,"); E6's 91 nested
   tabulars replaced one footnote. A head cut at 260 characters is not the head — E8's plan said four
   lines were lost; the tripwire's assertion said one word (S220 CORRECTIONS 97).
3. **A tool's refusal is information.** `collapse` refused E8's paragraph ("still reads as language");
   three read-only probes found the excerpt anchor (SYM-025) correct and the gate wrong (a loop
   embedded in prose fails a whole-paragraph type-token ratio). Fix the tool with its tripwire
   (`loop_gate`, `test_collapse_embedded.py`) — never hand-edit around it.
4. **The restoration's source, in order:** the page's own text layer (`restore_textlayer`: text,
   provenance `pdf-textlayer`, no model, no card) → a crop (`repair` with a rect: an image, for what
   is not text — a glyph, a diagram) → a model (`transcribe`/`assist`: the card, provenance
   `model`). The operator in the assist's seat uses the first two before the third, and never takes
   the card while PORTAL's line holds it.
5. **The rectangle from the word boxes** (`textlayer(n)`), never from a paper-size assumption or
   padded constants: E6 spent three passes learning that (an 842-pt height assumed for a 793.7-pt
   page; padded edges clipping a wrapped name and a neighbouring line).
6. **Verify mechanically where you can, by eye where you must.** The inserted words equal the page's
   words inside the rectangle (a multiset check, free); the region is the right one (the eye, not
   free). Both, every time.
7. **Budget two passes, record every write, leave the verdict alone.** The ledger is the evidence
   (`ledger_audit`: events = writes, the sha chain, `undo_depth`); the anchor copy and the fidelity
   block never move; the bench writes no verdict; the release is Rab's (the bless rail).

## The cost, measured

E8 — 8 min 12 s from the first probe to the act, 3 probes, 1 fix + 1 test before the first write,
2 gestures, 1 pass, 0 undos, 41 tool calls. E6 — 4 passes, 3 undos, 63 tool calls, one wrong region
and two wrong edges before a whole crop. The difference is rules 2 and 5.

## What the sequence does not do

Credit the repair in the audit (unsigned policy, docs/19 §10 / docs/28 §4); splice a restored word
back INTO the collapsed paragraph (the collapse keeps one loop instance as the marker; a splice
gesture is the next build, offered); see past the audit's evidence cap (25 of 97 runs shown on E8's
paper — `full-evidence review required`). The live queues for what is open stay in `OPEN-TASKS.md`
and `SYMPTOM-INDEX.md`; this page points, it does not duplicate.
