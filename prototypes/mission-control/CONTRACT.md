# CONTRACT — the rules the three panels obey

**You are drawing one real voyage.** Damodaran *Investment Valuation* 4e, 1377 pages, dropped
2026-08-31T21:30:12Z, HELD 2026-09-01T04:56:33Z. It failed. The power cut out at chunk 641. The
machine rebooted itself and then sat idle for an hour and three quarters because nothing restarts
the pipeline. **85.2 % of the voyage produced no events at all.** None of that is a rendering
problem to be smoothed away — it *is* the thing being displayed.

Import the model, never the fixture:

```js
import VOYAGE, { TIMELINE, FIELDS, ALARMS, render, dishonest } from './voyage.js';
```

`voyage.js` reads nothing at runtime. Every number in it is a **measure record**:

```
{ value, unit, num, den, conditions, population, evidence, honest, display, naive, census, defect }
```

---

## Rule 0 — the only rule that has no exceptions

> **Render `field.display`. Never render `field.value`.**

`value` is the raw number as the pipeline wrote it. `display` is the sentence that is true.
Use `render('convert.leg2.s_per_page')` if you want it in one call. If you find yourself writing
`${f.value}${f.unit}`, stop — you have just re-created the bug this glass exists to kill.

`field.naive` is what a careless panel *would* have printed. **It is the negative control.**
If any string your panel emits equals a `naive` string, your panel is lying. Grep for it.

---

## Rule 1 — docs/34, measurement language

1. **Every number names its numerator, its denominator and its conditions.** They are on the
   record (`f.num`, `f.den`, `f.conditions`). Numerator and denominator go in the visible label
   or one hop away (tooltip/expand); conditions may be one hop away but must be reachable.
2. **Never a bare rate.** Not `2.78 s/pp` — `2.78 s/pp (3834.2 s ÷ 1377 pp converted this run)`.
3. **A ratio prints both its sides. A percentage prints its base.** `pct()` does this for you.
4. **A duration nobody reported renders `UNREAD`. Never `0.0`. Never a blank. Never an em-dash
   that could be mistaken for a zero.**
5. **A rate whose denominator is zero renders `UNDEFINED`,** and says what the denominator was.
6. **Populations may never be mixed.** Three exist (`VOYAGE.populations`):
   `whole-book` (957 chunks / 1377 pp, both runs) · `this-run` (316 chunks, 0 pp) ·
   `prior-run` (641 chunks — **no duration, no tokens, no VRAM, permanently UNREAD**).
   A `whole-book` numerator over a `this-run` denominator is the single most common lie in this
   system. Any field carrying `population: 'mixed'` is a defect, not a measurement.

---

## Rule 2 — the error-structure protocol

Every surfaced defect carries three parts, and `f.defect` already holds them:

| part | answers | not |
|---|---|---|
| **reason** | what the issue is — the classified signature | not the raw metric |
| **highlight** | where, exactly — line, page, event index | not "somewhere near here" |
| **solution** | what the operator does about it | not "investigate further" |

A FAIL badge with no reason beside it is a protocol violation. This voyage's verdicts have
reasons and they are **not the obvious ones**:

- **Convert FAIL** ← the **degeneration tripwire** (24 blocks; worst at line 5524, 34,523 chars,
  zlib 0.023). **Not** because survival was 0.9334. Survival below 0.97 and 241 flagged pages are
  *localizers* and reach at most `flag`. Only two signals in the whole system can reach `fail`.
- **Analyst FAIL** ← **two** independent gates, either sufficient: containment 0.9402 < 0.995,
  **and** a 576-word omission run ≥ the 25-word threshold (23× over).

---

## Rule 3 — EEMUA 191 / ISA-18.2, alarms

1. **Every alarm has a defined operator response.** `ALARMS[].response`. No response, no alarm.
2. **Priority reflects consequence AND time-to-act**, not how alarming the number looks.
   There are 3 priority-1s across 7.5 hours. That is absorbable. Keep it that way.
3. **An operator who cannot absorb the alarm load ignores all of it.** The census has 179
   dishonest numerations. They are *not* alarms. Localizers (241 flagged pages, 29 fence
   rejections) live in a drill-down, never in the alarm strip.
4. **Two of the six alarms never fired, and they are the important ones** —
   `ALM-LIVENESS` (5 h 02 m with no event) and `ALM-IDLE-AFTER-REBOOT` (1 h 45 m of a healthy
   idle machine). Draw them as *absent instrumentation*, visibly distinct from alarms that fired.
   They are the finding.

---

## Rule 4 — Tufte

1. **Maximise data-ink.** No chrome, no gradients on data, no 3-D anything.
2. **A number without a trend beside it is meaningless.** The seven leg-1 slice walls
   (428.8 / 385.6 / 772.2 / 809.2 / 742.3 / 533.1 / 163.0 s) are a shape, not seven numbers.
3. **Micro/macro.** Legible whole (`VOYAGE.headline`), inspectable at every point (241 flagged
   pages, 25 shown runs with excerpts, 10 shown degenerate blocks with line numbers).
4. **Small multiples** beat one clever chart.

---

## Rule 5 — the timeline is the spine, and most of it is a hole

`TIMELINE` tiles 21:30:12Z → 04:56:33Z exactly: contiguous, no overlap, no gap (asserted in
code). Four kinds of ink, and **they must not look alike**:

| kind | seconds | means |
|---|---|---|
| `work` / `audit` | measured | the machine reported it |
| `dark` | **22,808 s (85.2 %)** | zero events. Measured *by absence*. |
| `dead` | 6,960 s (testimony) | machine off, or powered and idle |
| `gap` | 208 s | the record does not explain it |

- **`evidence: 'absence'`** means the only fact is that nothing was recorded. Draw the void.
- **`evidence: 'testimony'`** — the power cut (~01:38Z), the 01:48:17Z reboot, the operator's
  ~03:34Z return — appears in `TIMELINE[dark-1].testimony`. **No event and no manifest field
  attests any of it.** It must be visibly distinct from machine-recorded time (dashed, ghosted,
  annotated "operator report"), and its boundaries are approximate. Drawing it in the same ink as
  measured work is the worst lie available on this glass.
- Do **not** draw a solid uninterrupted bar across the voyage. Do **not** interpolate through a
  dark zone.
- The analyst phase has **zero events in the entire fixture** — no `analyst/start`, no
  `analyst/done`, no heartbeat. Everything you know about it arrived in the manifest, afterwards.

---

## THE BANNED RAW VALUES

**Every field below, by name, from THIS voyage. The raw value must never reach the glass
unmodified.** Left is what the pipeline wrote; right is what you render. All 23 are
`honest: false` in `voyage.js` and enumerable via `dishonest()`.

### Convert leg 2 — it resumed 7/7 slices and converted nothing

| field | raw | render |
|---|---|---|
| `convert.leg2.wall_s` | `0.0` | **NO WORK THIS RUN** — 0 of 7 slices executed; the book's cost stands at 3834.2 s |
| `convert.leg2.s_per_page` | `0.0` | **UNDEFINED** — 0 pages converted this run *(N-059)* |
| `convert.leg2.s_per_page_this_run` | `0.0` | **UNDEFINED** — 0/0, guarded to 0÷1377 *(N-059; the repaired field lies too)* |
| `convert.leg2.peak_vram_mib` | `null` | **UNREAD** — nothing ran, so nothing was sampled *(N-066)* |
| `convert.leg1.peak_vram_mib` | `9395` | 9395 MiB, highest of ~128 samples at 30 s — a sampled max, not a peak *(N-066)* |

`cost_s` **3834.2** is the honest figure for this book and should lead wherever leg 2 appears.

### The analyst — the counters that exist nowhere in the event stream

| field | raw | render |
|---|---|---|
| `analyst.chunks_resumed` | `641` | 641 of 957 (67.0 %) carried from run 1 — their seconds and tokens **UNREAD**. *(N-005: silenced on every human channel; **mandatory** wherever `chunks_passed` or `duration_s` appears)* |
| `analyst.chunks_passed` | `928` | 928 of 957 (**whole book, both runs**) *(N-007)* |
| `analyst.chunks_rejected` | `29` | 29 of 957 (3.0 %, whole book) — run-2 share **UNREAD** *(N-008)* |
| `analyst.chunks_failed` | `0` | 0 **recorded** — run-1 failures UNREAD by construction *(N-009; failures are never journalled, so 0 is not an all-clear)* |
| `analyst.duration_s` | `4634.4` | 4634.4 s covering **316 generated** chunks (14.7 s/chunk); run 1's analyst seconds **UNREAD** *(N-013)* |
| `analyst.tokens_prompt_total` | `314311` | **≥** 314,311 tok over 316 counted calls — lower bound, cached prefills report none |

`analyst.goodput_accepted_tok_s` **59.37** is **honest** — 275,162 accepted tok ÷ 4634.4 s, both
sides run 2. Ship its `conditions` string with it. It is **not** the book's throughput.

### The audits

| field | raw | render |
|---|---|---|
| `audit.convert.runs` | `25` | **25 shown of 531** (display cap 25) *(N-028 shape)* |
| `audit.analyst.runs` | `25` | **25 shown of 404** (display cap 25) |
| `audit.convert.doc_survival` | `0.9334` | 0.9334 **window**-survival, 12-word fuzzy windows, pymupdf witness; **both sides of the ratio UNREAD**; 1372 of 1377 pages scored |
| `audit.analyst.doc_survival` | `0.9402` | 0.9402 **verbatim containment** vs the Marker doc, exact match; both sides UNREAD |
| `audit.analyst.run_page` | `null` | **UNREAD** — the analyst audit has no page index; locate runs by excerpt only |

**The two `doc_survival` figures share a name and measure different things with different
matchers against different references. Never place them on one axis.**

### The localizers

| field | raw | render |
|---|---|---|
| `fidelity.degeneration.repeated_lines` | `0` | **UNREAD** — no line-run exceeded 20 repeats; the true maximum is suppressed *(N-029: a threshold reset, not a count)* |
| `fidelity.reverse_sample` | `0.765` | 153 of 200 sampled output windows found verbatim (exact match, seed 20260720) — **not** a hallucination rate, and gates nothing |
| `fidelity.asset_delta` | `76` | 308 asset files vs 232 embedded images (**+76, a surplus**, not a loss) |
| `fidelity.pages_scored` | `1372` | 1372 of **1377** — 5 pages silently excluded from every audit ratio |
| `fidelity.dict_hit` | `null` | **UNREAD** — not measured (wordfreq absent) |
| `fidelity.garbage_rate` | `null` | **UNREAD** — clean lane; the check applies to the scan lane only *(N/A ≠ unmeasured ≠ zero)* |
| `span.measured_work` | `8468.6` | 2 h 21 m 09 s of 7 h 26 m 21 s instrumented — the rest is **unmeasured, not idle**. **Never print a utilisation %**: run 1's analyst work is real and untimed. |

### Safe to render straight (19 fields, `honest()`)

`convert.leg1.wall_s` · `convert.leg1.s_per_page` · `convert.leg1.pages` ·
`convert.leg1.retry_wall_s` (a true measured zero — no stalls) · `convert.leg1.promise_delta` ·
`convert.leg2.pages_converted_this_run` · `convert.leg2.cost_s` · `convert.leg2.promised_eta_s` ·
`analyst.chunks_total` · `analyst.chunks_generated` · `analyst.goodput_accepted_tok_s` ·
`analyst.tokens_output_total` · `fidelity.pages_flagged` · `fidelity.page_coverage` ·
`fidelity.degeneration.blocks` · `span.voyage` · `span.dark` · `span.dead` ·
`audit.convert.degeneration` — **still with their conditions attached.** Honest means the raw
number is not a lie; it does not mean it may appear naked.

---

## Two deviations from the brief, in the pipeline's favour

Report them; do not paper over them.

1. **N-055 did not fire here.** The leg-2 estimate correctly declared `eta_s 0`,
   `pages_this_run 0`, `resumed_pages_assumed 1377`. The pre-work ETA did **not** promise the
   whole book on this resume.
2. **N-064's understatement is exactly zero on this book.** `cost_s` structurally drops
   `retry_wall_s` from resumed slices, but leg 1 recorded `retry_wall_s 0.0` and no slice was ever
   retried, so 3834.2 s is complete. Verified, not assumed.

Also honest here: `runs_total` (531 / 404) and `blocks_total` (24) both ride beside their capped
lists — the NUM-3 repair reached production. **Use them. There is no excuse for printing a cap.**

---

## Ship-check — read `VOYAGE.negativeControl` (15 entries) and confirm none of them is on your glass

The four that catch most panels:

- `"converted in 0.0s"` or `"0.00 s/pp"` anywhere on leg 2
- `"928 chunks in 4634.4s"` — book numerator, run denominator
- a solid uninterrupted timeline bar from 21:30Z to 04:56Z
- a FAIL badge with no reason, or an alarm with no operator response
