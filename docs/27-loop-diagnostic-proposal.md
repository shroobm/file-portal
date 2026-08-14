# docs/27 — The acute loop diagnostic, and the remedy it unlocks

**Status: PROPOSAL — nothing ships unsigned.** Written S76 (2026-08-13) from Rab's
observation at the Repair Bench, looking at 2,051 characters of
`A. The state of the state of the state of the…`:

> *"How come the repair bench nor the audit categorizes these as errors. There needs to be
> an acute diagnostic for this structure of text that forms, it's a pattern."*

## 1. What the system already does (the premise, corrected)

The audit **did** catch this block. `fidelity_audit.degeneration()` flagged it — `zlib 0.022`
(gate: `< 0.20`) **AND** `max_trigram 157` (gate: `>= 40`) — which set `verdict: fail`, which
is why the book is parked in `held/` and never reached the vault. Enforce mode worked.

So the gap is not detection. It is **naming** and **remedy**.

## 2. What is actually missing

1. **No taxonomy.** The detector returns a boolean plus raw metrics. The zone chip reads
   `Zone 1 · 2.1k` — a size, not a kind. Nothing anywhere says *"token loop: the phrase
   `the state of` stamped 130 times."* Two structurally different failures (a paragraph
   token-loop and a contiguous repeated-line run) come out of two different code paths and
   are presented identically.
2. **No proportional remedy.** The only offered fix is the human gesture: find the page,
   drag a crop, embed the image. That is heavy machinery aimed at a defect that is
   mechanically identifiable and mechanically removable.
3. **The repair never removes the garbage.** Per the S62 law, repairs do not delete
   degenerate text. So even after a perfect human repair, the vaulted note still carries
   2,051 characters of `the state of the state of` — the noise ships.

## 3. The acute diagnostic — measured, not proposed on intuition

Probe over all 117 body paragraphs ≥400 chars of the S76 Beer (`scratchpad/loop_probe.py`,
read-only):

| measure | the loop | best legitimate paragraph | separation |
|---|---|---|---|
| **type–token ratio** (unique tokens ÷ tokens) | **0.0147** | 0.5190 | **35×, gap 0.5043** |
| **trigram uniqueness** (unique ÷ total trigrams) | **0.0148** | 0.9740 | 66× |
| zlib ratio (current gate) | 0.022 | 0.502 | 23× |
| max trigram (current gate) | 157 | 2 | — |

**Type–token ratio is the acute measure.** It is not a tuned threshold — it is a chasm with
nothing in it. One loop below 0.10; all 116 clean paragraphs above 0.51.

It is also **more acute than the current pair**, and this matters historically: zlib alone
false-fired on the Cybernetics table-dense book (0.11/0.15), which is exactly why the current
detector needs an `AND` with the trigram gate. Dense tables repeat *structure* but vary their
*words*, so their type–token ratio stays high — TTR separates loops from tables in **one**
measure where zlib needs a partner to avoid lying.

Proposed classification, carried in the manifest per zone:

- `kind: "token-loop"` — TTR < 0.10; report the dominant n-gram and its repeat count.
- `kind: "line-repeat"` — the existing contiguous-run detector (`DEGEN_LINE_REPEAT`).
- `kind: "degenerate-other"` — flagged but matching neither shape (keep the escape hatch).

## 4. The remedy this unlocks — and its gate

A token loop carries no information beyond its first instance. **Collapsing** it — keep the
head, keep the tail, replace the middle with one instance plus a provenance marker recording
what was removed — is a mechanical repair needing no human, no crop, and no GPU.

Measured cost on this patient: the loop is **2,051 of 211,392 body characters = 0.970 %** of
the document — landing precisely inside Rab's stated entropy-loss target of **0.01–1.00 %**,
while the *information* lost is approximately zero.

**Two jobs, and only one of them is mechanical — this distinction is the point:**

- **Removing the noise** (collapse) is mechanical, cheap, and safe.
- **Restoring the content** is not. The real text of that page exists only in the PDF image;
  the loop *replaced* it. That still needs the crop or the ⌨ transcribe gesture.

A collapse therefore never "fixes" a page — it makes the wreck legible and small, so the human
gesture that follows is aimed at something the size of a paragraph instead of a wall.

**This requires Rab's signature.** Collapse deletes text the converter produced from a
vault-bound document, which is a semantic change under the docs/26 gate. Two cautions found
while reading the actual block: the head (`A. The state of the…`) may be the start of a real
sentence, and the tail degrades into fragments (`…the state of th Ex S`) — so a collapse must
preserve head and tail and cut only the proven repeat, never blind-delete the paragraph.

## 5. Why this serves the operator-simplicity mission

Rab's standing brief (docs/26 §standing context): operating maturity is undiscovered, there is
no canonical example of a good repair, and the target is minimum operator work. This finding
gives that mission its first concrete lever — the bench currently asks a human to do a
page-sized job for a defect a regex can name in microseconds. Naming the pattern acutely, and
shrinking it before the human ever sees it, is the difference between *"repair this book"* and
*"look at this one paragraph."*

## 6. Awaiting signature

1. Add `kind` classification to the degeneration detector (report-only, no behaviour change).
2. Surface the kind on the zone chip and the assay card, replacing a bare byte count.
3. **Collapse** as a bench gesture — Rab's pen, per §4's cautions.
4. Whether a collapsed loop changes the audit verdict (recommendation: **no** — collapsing
   removes noise, it does not restore the lost content; the page still needs its image).
