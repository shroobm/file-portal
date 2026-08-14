# docs/29 — The Observability Complex

**What this is.** Rab's question, S77 (2026-08-14): *"how do we efficiently determine what
should be wired to the glass? … these aren't bugs, they should be considered glitches, because
the system was designed to be highly observable."*

That distinction is the whole document. A **bug** is a defect in what was built. A **glitch**,
here, is where the design's own stated intent — observability — failed to be realized, and
nothing noticed. Three read-only agent lanes measured the extent: **~83 fields** are computed,
persisted, and reach no human. This is not carelessness. It is structural, and the proof is
that it kept happening *during the investigation of itself*.

---

## 1. The diagnosis: the projection law is half a law

docs/13 states it: the widget *"renders and requests, never owns … any surface must be
reconstructible by reading the filesystem."*

Formally: **∀ surface s, ∃ file f such that s = project(f).** There is no quantifier over `f`.
Nothing anywhere in the corpus says *∀ measured value v, ∃ surface where v is visible*.

The asymmetry is **load-bearing, not accidental**. docs/16 uses that law as the safety argument
for autonomous building — "the pipeline is never touched." A law written to prove the UI
*cannot do harm* has no reason to require that it *do good*.

**The corpus-wide finding (S77 laws lane):** every law in this project with teeth governs what
may be **written** — to the vault, a manifest, the ledger, the DOM. **Not one law governs what
must be read.** The guarantees are all write-side; the human is on the read side; no law
crosses the boundary. The system has a rigorous theory of what makes evidence *admissible* and
no theory of what makes evidence *arrive*.

**The enabler:** a producer writes freely into a shared payload (`manifest.json`, `state()`),
and a consumer pays **zero mechanical cost** for ignoring a key. Silence is free.

## 2. Why the project cannot learn this reactively

~30 of the corpus's ~40 laws are **reactive** — each paid for by an incident (see docs/19's
header: "each one paid for in blood"). They govern *mechanism*, and they are the ones with
CODE and TEST behind them. ~10 are **designed in advance**; they govern *epistemics and
representation*, and they are enforced by PROSE and RITUAL alone.

The reactive engine only fires on failures that **announce themselves**: a hang, an exit code,
a wrong file, a red build. **A value shown to nobody raises nothing** — no exception, no bad
state; the disk is in fact perfect. So the mechanism that wrote thirty laws structurally cannot
fire on this class, and never has.

**Demonstrated, twice, in one night.** S76 named the pattern in its own closeout and then
shipped a fourth instance ninety minutes later, catching it only at close with a note asking the
future to care. S77 — this investigation — produced **two more** while measuring the first four.
Naming is prose; prose is the tier that fails.

## 3. The failure-mode taxonomy (predictive)

| Mode | Mechanism | Seen in |
|---|---|---|
| **A · Spec-narrowing** | One doc section justifies computing a value; the section that specs the *UI* enumerates a narrower set. Implementation follows the narrower section **faithfully** — nobody forgot. | `reverse_sample`, `page_coverage`, `asset_delta`, `garbage_rate` |
| **B · Grammar placeholder shadowed by a working twin** | A slot is added for pattern completeness while an older, different indicator already answers the same question. The symptom never bites, so only a structural audit finds it. | `#st-lib` (dead S34→S75, `#vault-bar` covered it) |
| **C · Partial fork** | A second consumer is built against a payload it already receives and implements only the subset resembling a pattern it knows, dropping siblings silently. | omission `runs` in the Bench (the widget rendered them fine) |
| **D · Acceptance-complete, UI-deferred** | "Done" is defined as a green acceptance suite, and no suite requires a UI consumer. | the S76 ledger routes; **S77's own rescore verdict** |

Mode A predicts where the next one appears: any field justified in a schema section but absent
from a UI section. Mode D predicts *when*: any backend-first build whose tests pass.

## 4. The law

> **The converse projection law.** Every value the pipeline measures and stores must have a
> **disposition**: a surface, an evidence card, a report — or a signed reason for its silence.
> A measurement with no reader is a defect of the same class as a number with no source.

Silence remains legitimate. What ends is silence **by default**. A disposition is a decision,
and decisions in this project are written down.

## 5. The complex: why one law is not enough

A law that must be *remembered* joins the ten that are enforced by nothing. This one needs
three parts working together.

### 5.1 The detector (mechanical, never forgets)

For every dict a producer returns or persists, walk its keys and confirm each is referenced by
at least one renderer. This is the whole check — the S77 lanes performed it by hand with
`grep`, which is proof it is automatable. It belongs in CI for the tracked trees and in the
closeout ritual for `prototypes/` (which CI may not touch).

**Cost of not having it, measured:** ~83 fields, including the detector purpose-built for the
system's stated catastrophic failure mode (§7).

### 5.2 The disposition (forced judgment, recorded)

Every flagged field is assigned exactly one:

| Disposition | Meaning | Home |
|---|---|---|
| **GLASS** | a live surface shows it | Dock / Room / Wall / Bench chip |
| **EVIDENCE** | shown when a card is deliberately opened | assay card, drill tree, zone panel |
| **REPORT** | end-of-run artifact, never polled | `REPAIRS.md`, receipts, morning note |
| **INTERNAL** | control flow only; a human never wants it | with a one-line reason |
| **DEAD** | nothing needs it — delete the producer | with the commit that removes it |

### 5.3 The procedure (how to choose) — apply in order, stop when resolved

1. **Terminus or input?** If it exists only to feed another computation — a calibration
   constant, an accumulator, a matcher index, a coordination lock — it is **INTERNAL**, and
   correctly silent.
2. **Actionable — on this surface?** Would seeing it change what a human does next *here*?
   Test against the specific surface, not the concept: `#st-lib` was actionable in principle
   and not in practice, because `#vault-bar` already answered it.
3. **Verdict, localizer, or archive?** A verdict → the ambient glyph (terracotta only when a
   hand is required). A localizer → **EVIDENCE**, revealed when the card is open, never
   promoted to ambient chrome. An archive → **REPORT**.
4. **Does it already have a home — anywhere, live or archival?** If yes, that is correct
   routing, not silence. **Silence is a defect only when the answer is nowhere.** This is what
   makes the ledger's sha chains and verbatim margins correctly quiet: `REPAIRS.md` is their
   home by design.
5. **Would showing it require new pulsing chrome?** Then redesign into a quieter slot instead —
   as SYM-026's fix did with amber `◍` chips rather than a second terracotta.
6. **Density.** If its natural granularity is hundreds per document, aggregate before it earns
   glass: the count and the worst examples, never the full list.

**A glitch is precisely:** a real, actionable terminus (clears 1–2) whose step-4 answer is
*nowhere*. That is mechanically checkable, which is why §5.1 works.

### 5.4 The timing rule (what actually stops Mode D)

**A commit that adds a persisted or projected field must, in the same commit, either render it
or record its disposition.** Retrospective sweeps find glitches; only concurrency prevents them.
This is the same shape as docs/28's chokepoint — *recording precedes action* — applied to
measurement.

## 6. The family: one principle, three faces

S76 and S77 discovered the same idea three times in two days:

- **The chokepoint** (docs/28): recording precedes the write.
- **The ledger** (docs/28): no write escapes the record.
- **This** (docs/29): no measurement escapes a disposition.

> **Every act leaves an accounted trace, and the accounting is structurally impossible to skip.**

The first two govern the **write** side, where this project is strong. This one governs the
**read** side, which no law has ever governed. That is why it had to be rediscovered rather
than deduced.

## 7. What the census actually found (the standing debt)

Ranked by what a human would want most. Full tables in the S77 closeout.

1. **`/api/rescore`'s `vault_recommendation` + `coverage`** — the button that asks "is this book
   fit for the vault" fetches the answer and discards it. **Built S77, silent the same night.**
2. **`pages_scored` never printed** — the one number that unmasks a vacuous `survival 1.000`
   (docs/26 F4's mechanism).
3. **`manifest.chunking.seams[]`** — recorded *because* "the Repair Bench needs to know where
   the cuts were" (docs/18 §5.2); the Bench, built afterward, never reads it.
4. **The five-outcome triage is invisible** — `outcome`/`outcome_reason` on every zone and run,
   plus no control for `/api/triage`. **Built S77.**
5. **`chunks_resumed` + the live `resumed`/`eta_s` heartbeat** — the power-cut recovery, silenced
   on two independent channels (JS never reads `.analyst`; Rust drops the fields).
6. **`room_metrics.recent_audits[]`** — a ready-made "last 6 books" digest, rendered nowhere.
7. **`resume-stderr.log` has no click-to-open path** — created S76 to cure traceless failure,
   *it inherited the disease it was built to cure*; both sibling logs are in the 🗁 menu.
8. **`reverse_sample`** — the promised precision tripwire, never read by anything.
9. **receipts `note`** ("where did my book land in the vault") and `sha`.
10. **Bench repair provenance goes dark once persisted** (model, gates, secs, cycle, delta, rect).

Plus: a fully dead command (`audit_mode_get`, registered, never invoked); **`dict_hit` is a dead
gate** — a signed threshold (docs/15: flag below 0.80) whose input is hardcoded `None`, the exact
mirror image; and `runs` is truncated to `[:25]` at the source with no record of the discard.

**Also confirmed, and not a field-level glitch:** docs/18's algedonic escalation names three
channels — Room banner, morning note, Gmail draft. **Only the banner exists.** The escalation
built to make five silent days impossible terminates inside the one surface that requires a human
to already be looking, cannot represent *silence* (it iterates over events), and is disarmed by
the default lever position. That deserves its own session.

## 8. Awaiting signature

1. The converse projection law (§4) as stated.
2. The five dispositions (§5.2) and the six-step procedure (§5.3).
3. The timing rule (§5.4) — same-commit disposition — and whether the detector runs in CI, in
   the closeout ritual, or both.
4. Whether docs/21 §5's Observable Contract moves from EXTENDED to **CORE** tier. Today a session
   that ships no code may skip it entirely — which is exactly how a stored-but-unshown value
   survives a closeout.
5. The §7 debt: which items get wired, and in what order.
