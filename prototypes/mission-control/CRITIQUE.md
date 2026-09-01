# CRITIQUE — adversarial review of the three mission-control panels

**Reviewer stance:** a panel is dishonest until checked. Every finding below was checked against the
*rendering logic* or the *painted DOM*, not against a comment. Claims are tagged
**[Observed]** (I ran it or read it), **[Inferred]** (I reasoned it), **[Intended]** (the panel's own
stated design, not exercised by me).

**Method.** All three panels served over `http://127.0.0.1` from their own directory, and again from a
route that 404s `voyage.js` to simulate the module-blocked (`file://`) case. Findings drawn from:
computed CSS on painted nodes; `document.body.innerText` scans; the browser network log; a line-diff of
each panel's embedded model against `voyage.js`; and a node audit of the model itself. Nothing was
modified. **I review; I do not repair.**

---

## CROSS-CUTTING

### X1 · A verification that did not run is painted as a green PASS — Panels A and B
**[Observed]** Served from an origin where `import('./voyage.js')` fails:

- **`panel-a-opsroom.html:3046`** — the `catch` sets `modelCheck = { ok: true, msg: 'NOT VERIFIED — …' }`.
  Rendered at **`:3061`** as `r.ok ? '▮ PASS' : '◆ FAIL'`, counted at **`:3057`**.
  The glass reads, verbatim:
  > `NEGATIVE CONTROL — 10 OF 10 CHECKS PASS`
  > `▮ PASS  NC-8  NOT VERIFIED — the browser refused to load ./voyage.js as a module…`

- **`panel-b-telemetry.html:1120`** — `out.push([DRIFT !== 'DRIFT', …])`. When the import throws,
  `DRIFT` is `null`, and `null !== 'DRIFT'` is `true`. The glass reads:
  > `PASS  F · model source  embedded snapshot (import blocked: …)`

- **`panel-c-small-multiples.html:2956`** — the `.catch()` writes a **neutral** line (class `chkline`,
  leading em-dash, no tick) saying the inlined copy is *"IN USE AND UNVERIFIED at runtime"*, and that
  line is **excluded from the PASS headline's arithmetic**. **[Observed]** This is correct, and it is
  the behaviour A and B must adopt.

This is docs/34 rule 4 applied to a check instead of a duration: *a verification nobody performed
renders UNREAD, never green, and never counts toward a total.* Both A and B publish a green mark, in
the panel's own MEASURED glyph, on work that did not happen — in the section whose entire purpose is to
prove the panel is not doing exactly that.

### X2 · The model's own `chunks_total.display` carries `"+ 0 failed"`, and every panel repeats it
**[Observed]** `voyage.js:1754` — `display: '957 chunks (641 resumed + 316 generated; 928 passed + 29
rejected + 0 failed)'`, `honest: true`. Present verbatim on all three glasses. Negative-control entry #4
(*"0 failed" as an all-clear*) is therefore unenforced everywhere.
Panel A goes further: **`panel-a-opsroom.html:2888`** uses `[/\b0 failed\b(?!\))/i, …]` — a negative
lookahead written specifically so the control cannot see this occurrence. That is a test tuned around
its subject. *Mitigation, on all three:* `analyst.chunks_failed`'s honest display ("0 recorded — run-1
failures are UNREAD by construction") is also on every glass, so the all-clear reading is contradicted
in the same section.

### X3 · `analyst.tokens_output_total` declares a numerator and denominator that do not describe its own percentage
**[Observed]** `voyage.js`: display `"279,174 tok generated over 316 calls; 275,162 accepted, 4,012
discarded (1.4%)"`; `num` = 279174 tok, `den` = 316 calls. The `1.4%` is 4,012 ÷ 279,174 — neither of
the declared sides. Field is `honest: true`, so no panel treats it as a defect.
Panel C prints num/den **directly beneath** the number, making the contradiction visible on the glass;
A and B put it one hop away (tooltip / drawer). docs/34 rule 1. No panel flags it.

### X4 · `ALM-LIVENESS` is internally contradictory and only Panel B commits to a number
**[Observed]** The model's `title` frames the alarm on events ("no event for 5h 02m"); its `response`
frames it on `.analyst-progress.json` **mtime**. Those imply different firing instants.
**`panel-b-telemetry.html:800`** resolves it silently to last-event + 300 s and prints
`WOULD HAVE FIRED 22:40:15Z … 4h 53m 45s later` (**`:820`**).
**[Inferred]** An alarm implementing the response *as written* watches the progress file, which was
being rewritten until the ~01:38Z power cut, so it fires ≈01:43Z and the detection lateness is ≈1h 51m,
not 4h 53m 45s. Panel B overstates by roughly three hours, in mono type, with no note that the instant
is panel-derived. A prints the model's own `at`; C prints only `∅ NEVER FIRED`.
**Deviation is the report:** the contradiction is in the model, not in Panel B — but Panel B is the only
panel that converts it into a number, and it does not say so.

### X5 · `dead` is a subset of `dark`, and nothing states the containment
**[Observed]** `dead` (6,960 s: power-cut 617 s + dead-idle 6,343 s) lies **entirely inside** `dark-1`
(18,133 s). All three panels draw them as separate lanes on one shared axis, which communicates
containment correctly. None of them says it in words. On A and B this is latent risk; on C it has
already produced an error (**C1**).

---

## PANEL A — `panel-a-opsroom.html`

### A1 · SEVERE — the panel's published glyph key stamps testimony and absence as MEASURED
**[Observed]**
- **`:58`** `.m-honest::before{content:"▮ ";…}`
- **`:2329`** `class: 'm ' + (f.honest ? 'm-honest' : 'm-repaired')`
- **`:2552`** the visible legend: `▮ MEASURED   ▲ REPAIRED FOR THE GLASS   ? UNREAD`

Computed `::before` on `span.m[data-field="span.dead"]` — evidence **`testimony`** — is `"▮ "`.
Same for `span.dark`, evidence **`absence`**. So the room-scale figure

> `▮ 1h 56m 00s machine down or idle (testimony, ±minutes)`

— the power cut and the unattended-reboot idle, which **no machine recorded** — wears the same
MEASURED mark as `convert.leg1.wall_s`, which seven slice events attest to the tenth of a second.

The glyph is bound to `honest` (is the raw value safe to print?) when the vocabulary it publishes is
about `evidence` (who witnessed it?). CONTRACT Rule 5: *"Drawing it in the same ink as measured work is
the worst lie available on this glass."* The panel's file-header grammar at **`:13–17`** declares
`▯ testimony`, and `▯` is used correctly on the rails — but never on a measure card, and `▯` never
appears in the legend the operator can actually read.

### A2 · SEVERE — see X1. `:3046`, rendered `:3061`, counted `:3057`.

### A3 · MEDIUM — the room-scale lead may be any substring, and three leads are bare figures
**[Observed]** `BIG()` at **`:2344`**; NC-2 at **`:2943`** tests only `display.includes(lead)` —
containment, not equality. Painted leads include:

| field | lead in giant type |
|---|---|
| `span.dark` | `85.2%` |
| `audit.convert.doc_survival` | `0.9334` |
| `audit.analyst.doc_survival` | `0.9402` |

At the 5 m reading distance this panel is explicitly built for (`:11`, the `--macro`/`--supra` clamps),
the only legible token is a bare percentage or a bare four-digit ratio. docs/34 rules 2 and 3 are
satisfied only by the smaller sentence beneath. And the two `doc_survival` leads are *typographically
identical objects*: the contract's "never place them on one axis" is honoured structurally (NC-6
confirms separate cards, and at 1145 px they are 455 px apart vertically) but defeated typographically —
two 4-digit decimals in the same weight, same size, same colour, one page apart, measuring different
things with different matchers against different references.

### A4 · LOW — the negative control cannot see the tooltip layer
**[Observed]** `assertedText()` at **`:2906`** builds its scan text from `clone.innerText`, which
excludes `title` attributes. `conditionsOf()` at **`:2311`** writes raw `num.value` / `den.value` into
the `title` of every measure. Those are labelled `NUMERATOR:` / `DENOMINATOR:`, so they are not lies —
but the entire tooltip layer, which is where the raw numbers live, sits outside NC-1. Panel C's
TreeWalker scan (`:2822`) includes hidden text and is strictly stronger.

**Credit where due, checked not assumed:** NC-1b (**`:2929`**) proves every node exempted from NC-1 is
byte-identical to a `conditions` or `defect` string in the model — the exemption cannot smuggle
panel-authored prose. That is the discipline Panel B is missing (**B2**). Panel A's rail widths sum to
**exactly 100.0000 %** with two dark voids at 67.708 % and 17.456 %; all six alarms carry a DO line; the
two never-fired alarms sit in their own box with `◇` and `NEVER FIRED — NO INSTRUMENT`.

---

## PANEL B — `panel-b-telemetry.html`

### B1 · SEVERE — the AS-OF thesis is false as implemented: the future stays on the glass at full brightness
**[Observed]** The panel's own claim, **`:19–21`**:
> *"Drag AS-OF back into the run and every analyst panel goes dark, because that is what the operator
> actually had."*

`paintManifestGating()` at **`:787`** dims only `[data-manifest]`, and there are exactly **two** such
elements in the file — **`:886`** and **`:913`**. At AS-OF = **01:00:00Z** (3 h 56 m before the manifest
existed, mid dark-zone-1), measured effective opacity of the painted nodes:

| field | recorded at | effective opacity | visible? |
|---|---|---|---|
| `audit.analyst.doc_survival` **0.9402** | 04:56:32Z | **1.00** | yes |
| `audit.analyst.runs` "25 shown of 404" | 04:56:32Z | **1.00** | yes |
| `convert.leg2.wall_s` / `.s_per_page` / `.peak_vram_mib` | 03:37:38Z | **1.00** | yes |
| `fidelity.reverse_sample`, `fidelity.asset_delta` | manifest | **1.00** | yes |
| `analyst.duration_s` **4634.4** | 04:56:33Z | 0.22 | yes |
| `analyst.chunks_passed` **928 of 957** | 04:56:33Z | 0.22 | yes |

`4634.4` and `928 of 957` remain in `document.body.innerText` at 22 % opacity (**`:790`**,
`el.style.opacity = known ? '1' : '.22'`) — dim, not dark. Everything else is untouched. Meanwhile the
banner on the same screen tells the operator *"From 22:35:15Z to 03:37:28Z the answer is nothing at
all."* The desk invites you to sit inside the five-hour silence and then shows you the verdict that
ended it. The gate is a hand-placed attribute on two containers, not a function of each field's own
evidence instant.

### B2 · SEVERE — check C prints "clean scan over the whole document text" after deleting the region where the banned strings are
**[Observed]**
- **`:1112`** `clone.querySelectorAll('[data-nc-exempt],#shipcheck,.drawer,script').forEach(n => n.remove());`
- **`:1119`** the sentence the operator reads: `clean scan over the whole document text`

Opening the inspector for `convert.leg2.s_per_page` puts the literal negative-control string
**`0.00 s/pp`** on the glass, together with **`:1074`** `wire value, raw, as the pipeline wrote it (not a
reading): 0 s/pp`. Both live inside `.drawer` — one of the four regions check C removes before scanning.
The `script` exclusion is explained in a code comment; the **`.drawer` exclusion is explained nowhere**,
and the claim on the glass is false as written. Panel A bounds its exemption with NC-1b; Panel B has no
equivalent.

*Secondary, and disclosed:* the footer at **`:1157`** concedes *"no code path in this file reads
`field.value` except the inspector's labelled wire-value line."* That is an admitted breach of CONTRACT
Rule 0 — the rule with no exceptions — but it is stated, labelled on the glass, and pedagogically
defensible. The false scan sentence is worse than the breach it conceals.

### B3 · MEDIUM — a panel-computed alarm rate over a mixed population
**[Observed]** **`:832`** paints: `6 alarms ÷ 7h 26m 21s = 0.81 per hour · 3 priority-1 · 2 of the 6
never fired because they do not exist`.
The numerator sums 4 annunciated alarms and 2 that do not exist. EEMUA 191's alarm-rate metric counts
alarms *presented to an operator*; the annunciated figure is 4 ÷ 7.44 h = **0.54/h**. This is not a
measure record — no `num`, no `den`, no `conditions`, no census tag — and it is the only alarm-load
number on the glass. Mitigated, but not repaired, by the caveat in the same line.

### B4 · MEDIUM — see X4. `:800` (`WOULD_FIRE`), `:820` (the printed instant and lateness).

### B5 · LOW — the ghost alarms *behave* like alarms that fired
**[Observed, from `paintAlarms()` at `:812`]** `style="${active ? '' : 'opacity:.3'}"` is applied to
every alarm, ghost or not, keyed on whether its instant (real, or fabricated per X4) has passed. During
REPLAY the two non-existent alarms arrive on the annunciator with exactly the animation of the four
real ones; only the `ABSENT INSTRUMENTATION` chip distinguishes them. CONTRACT Rule 3.4 asks for them to
be *visibly distinct from alarms that fired*. They are distinct in text, not in behaviour.
**[Intended, not exercised]** I read the replay path; I did not watch a full replay.

### B6 · LOW, latent — a zero where UNREAD belongs
**[Observed]** **`:697`** `const … age = le ? (t - T(le.ts)) / 1000 : 0;` then
`big.textContent = fmtDuration(age)` → `"0s"` when there is no record at all. Unreachable today only
because `scrub.min = 0` coincides with the first event's instant. docs/34 rule 4: a duration nobody
reported renders UNREAD.

**Credit where due, checked not assumed:** Panel B's `viewAge` sawtooth is the one continuous line on
any of these three glasses, and it is justified rather than asserted (**`:637`**): signal age is a
function of the event *timestamps*, exactly known at every instant, and interpolates no measurement.
`viewArr` draws empty 300 s buckets as a baseline tick and says *"an empty bucket is a measurement."*
The timeline inks are genuinely four different things (confirmed by computed style: work
`rgb(61,110,168)` solid; audit `rgb(74,125,120)` solid; dark `rgb(22,27,34)` + dashed; dead transparent
+ 135° hatch + purple dashed; gap a 90° hatch). The drawer is the best drill-down of the three — one
view carrying display, numerator, denominator, conditions, population, evidence, origin, the full
reason/highlight/solution triad, the negative control, and the labelled wire value.

---

## PANEL C — `panel-c-small-multiples.html`

### C1 · SEVERE — two overlapping intervals are added, yielding a duration larger than the panel's own total dark time
**[Observed]** **`:2768`**:
> *"Together they account for **6h 47m 56s** of this voyage: 5h 02m 13s during which a dead analyst was
> indistinguishable from a working one, and 1h 45m 43s during which a healthy idle machine was
> indistinguishable from a busy one."*

The 1h 45m 43s window (`dead-idle`, 01:48:17Z → ~03:34:00Z, 6,343 s) is **entirely inside** the
5h 02m 13s window (`dark-1`, 22:35:15Z → 03:37:28Z, 18,133 s). 18,133 + 6,343 = 24,476 s = 6h 47m 56s
**double-counts 6,343 seconds**. The true union is 18,133 s = **5h 02m 13s**.

Worse, 6h 47m 56s **exceeds the panel's own `span.dark` figure of 6h 20m 08s** (22,808 s) for *both*
dark zones combined, printed a few sections above on the same page. A reader who checks will find that
the two numbers cannot both be true.

Panel-authored, no measure record, no numerator, no denominator, no conditions; and it sums a
machine-measured absence with an operator-testified sub-interval of that same absence — CONTRACT Rule
1.6, populations may never be mixed. This is one sentence and it is the only severe defect on the most
honest of the three panels.

### C2 · MEDIUM — the 957-cell chunk field assigns identity the record does not contain
**[Observed]** Section 3: 957 cells, 641 hollow (`.cell.res`), 316 solid, ordered by journal position,
split at chunk 641. The manifest holds **counts**, never indices.
The panel says so, unprompted, at **`:2495`**: a `note-inf` block headed **"INFERRED, and the panel says
so."** — *"The manifest records COUNTS (641 / 316), never indices. Cell order here is journal order, and
the split is placed at the boundary the operator's testimony names… If the resume journal is not
contiguous, the boundary moves; the two counts do not."* And at **`:2500`** the 29 rejected chunks are
detached under `29 rejected · position UNREAD`, because *"painting these into the field above would
invent 29 locations the record does not contain."*

That is the right disclosure and it is why this is MEDIUM and not SEVERE. It remains the largest
inferred object on the page, and its cells use the same ink as the measured marks elsewhere, differing
only by fill.

### C3 · LOW — the self-check lives inside `requestAnimationFrame`, so a hidden tab renders section 9 as an empty box
**[Observed]** **`:2814`** `requestAnimationFrame(() => { try {`. In a background tab: heading
`9 · SELF-CHECK …` present, **zero** `.chkline` nodes, no `h3`, no PASS, no FAIL. Same URL fronted:
16 lines and the headline. **[Inferred]** cause: Chrome does not service rAF callbacks in hidden tabs.
This is exactly the silence the `catch` at **`:2967`** was written to prevent — *"An honesty panel that
cannot run its own honesty check must SAY SO, loudly, rather than rendering an empty box that reads as
silence."* The `catch` cannot fire, because the callback never runs.

### C4 · LOW — "✓ PASS" heads a box whose last line says the model is unverified
**[Observed]** **`:2910`**. The heading's claim is correctly *scoped* — "no banned reading on this
glass; 12 of 12 mandatory truths present" — and the model line is neutral rather than green, so this is
far milder than **A2 / X1**. But a reader scanning for the tick sees a tick.

**Credit where due, checked not assumed:** Panel C's embedded model differs from `voyage.js` on
**zero** lines after unescaping the one documented backslash, and its declared
`sha256 9adce9756df578331f80e3eefc1371dbaeffffcd65b8dad69d998562f1f47468` **matches** the file
(`sha256sum` verified). Its self-check is the strictest of the three: **Tier A** is the contract's
literal equality test over every reading node against all 23 `naive` strings; **Tier B** is a substring
sweep with a *mechanically pre-declared* undecidability rule — a `naive` string that already occurs in
model-authored prose is named as undecidable rather than counted either way, and the four such fields
are listed on the glass. That is the honest version of the manoeuvre Panel A performs with a lookahead
(**X2**) and Panel B performs with a CSS selector (**B2**). Its scan reads text via a TreeWalker,
including hidden text, so it is stricter than what is on screen. Every card prints numerator,
denominator, conditions and the full defect triad inline. `glyph(f.evidence)` — Panel C binds its
provenance mark to **evidence**, which is precisely what Panel A gets wrong (**A1**).

---

## CHECKED AND FOUND HONEST — all three panels

- **Self-containment.** The only network request any panel makes, read from the browser's own network
  log, is same-directory `./voyage.js`. No CDN, no webfont, no `@import`, no `<link>`, no `fetch`, no
  XHR, no WebSocket, no image. Grep across all three for
  `createObjectURL|new Blob|new Worker|localStorage|sessionStorage|indexedDB|navigator.` — **zero
  hits**. The only `http://` strings in Panel C are the SVG namespace constant.
- **Model fidelity.** A: 1 differing line vs `voyage.js`, and it is a comment (the documented
  `</script>` escape). C: **0** differing lines, hash verified. B: JSON snapshot shows **0** differences
  against `JSON.parse(JSON.stringify(...))` of the live module's `VOYAGE`, `EVENTS`, `SOURCE_PDF` and
  `MANIFEST_ANALYST`.
- **The resume zeros.** No panel puts `0.0 s`, `0.00 s/pp`, `0 MiB` or a null VRAM on the glass as a
  leg-2 measurement. All three render `NO WORK THIS RUN` / `UNDEFINED` / `UNREAD` and lead with
  `cost_s 3834.2s`. The single `0.0s` on each glass is `convert.leg1.retry_wall_s` — a **true measured
  zero** — and each panel prints it with its condition ("zero retries, zero stalls, 7 of 7 slices
  first-attempt").
- **N-055 and N-064.** Both deviations-in-the-pipeline's-favour are reported on all three, not papered
  over.
- **N-028.** No panel prints a display cap alone. `531` and `404` are on all three glasses.
- **The dark zones.** Drawn as voids at true time scale by all three. Measured widths on the shared
  26,781 s axis: dark-1 **67.708 %**, dark-2 **17.456 %** — 85.16 % of the rail. Panel A's rail sums to
  exactly 100 %. No panel draws a solid uninterrupted bar. No panel interpolates a *measurement* through
  a dark zone.
- **Alarms / EEMUA 191.** Exactly **6** alarm states on each panel — the model's six, no more. **3
  priority-1** across 7 h 26 m: absorbable, and the contract's own budget. Every one of the 6 carries
  the model's `response` verbatim on all three glasses (Panel A's NC-4 checks it from the DOM; Panel C's
  `must` list checks `ALARMS.every(a => pageText.includes(a.response))`). **No panel promotes the 241
  flagged pages or the 29 fence rejections into the alarm strip** — they sit in localizer sections on
  all three, as Rule 3.3 requires. The 179 census numerations are nowhere raised as alarms.
- **Percentages.** Every measured percentage on Panel C prints its base on the adjacent num/den line
  (27 `%` occurrences on the glass: 11 measurements with bases, 16 inside quoted Damodaran excerpts).
  Panel A's are all inside model `display` strings or its own self-check geometry. The only bare
  percentages without an adjacent base are the three room-scale leads in **A3**.
- **`null` / `NaN` / `undefined`.** Zero occurrences on any glass except deliberate prose *about* nulls
  in Panel C's defect ledger.

---

## RECOMMENDATION — graduate Panel C, with transplants

**Panel C is the most honest of the three**, and it is not close. Zero model drift with a verified hash;
the only self-check that handles its own unverifiability correctly; the only scan that reads hidden
text; a pre-declared undecidability rule instead of a tuned exemption; provenance bound to `evidence`
rather than to `honest`; numerator, denominator, conditions and defect triad inline on every card. Its
one severe defect (**C1**) is a single sentence of arithmetic.

Fix first, in C:
1. **`:2768`** — state the union (5h 02m 13s) or state the containment explicitly; do not sum.
2. **`:2814`** — move the self-check out of `requestAnimationFrame`, or have the empty box say so.
3. **`:2910`** — scope the PASS headline visibly, or withhold the tick until the model line resolves.

Then absorb:
- **From B** — the *age of the last record* as the primary readout, the replay, and the drawer's
  complete measure record. But re-implement the AS-OF gate as an **actual removal** (`NOT YET
  RECORDED` in place of the value), applied to **every** field whose evidence instant is later than
  AS-OF, derived from the field's own origin rather than from a hand-placed attribute on two
  containers (**B1**).
- **From A** — the two-rail spine (machine rail / testimony rail), the `◇` hollow-diamond absent-alarm
  treatment, the algedonic block, and **NC-1b's bounded-exemption proof**, which is the one control B
  most needs (**B2**).
- **From nobody** — a rule all three must adopt: *a check that did not run renders `—`/`UNREAD`, never
  a green PASS, and is excluded from the pass count* (**X1**). C already does this; A and B must.

Raise upstream in `voyage.js`, not in any panel: **X2** (`chunks_total.display` carrying "+ 0 failed"),
**X3** (`tokens_output_total`'s num/den vs its own 1.4 %), **X4** (ALM-LIVENESS's `title` and `response`
naming different watch targets, hence different firing instants), **X5** (declare `span.dead ⊂
span.dark` so no panel can sum them — C already did).

---

## RESIDUE — what I did not do, could not verify, or got wrong

- **No panel was opened from a real `file://` origin.** I simulated the module-blocked case with a local
  route that 404s `voyage.js`. The thrown error text differs from a CORS/opaque-origin refusal, but every
  panel's `catch` branch is origin-agnostic, so the PASS/UNVERIFIED behaviour is the same. That
  equivalence is **[Inferred]**, not observed.
- **One viewport pair only** (1145 px responsive, 1600 px emulated). No phone width; no projector aspect.
  **A3**'s severity is width-dependent and I measured it at one width; the two `doc_survival` leads were
  455 px apart vertically at 1145 px and I did not check whether a ≥2000 px layout puts them side by side.
- **Panel B's REPLAY was not run end to end**, and the `arr` / `lane` stream views were read, not
  watched. **B5** comes from `paintAlarms()`'s source, not from a recording.
- **One inspector drawer opened, not 42.** **B2** generalises from `convert.leg2.s_per_page` plus the
  shared code path.
- **No claim about the live pipeline source was verified.** Every `highlight` line quoting
  `convert_and_ship.py:1305`, `fidelity_audit.py:383`, `line.rs`, the 30 s VRAM sampling interval, the
  `~128 samples` figure or the `AUDIT_LAW` thresholds enters through `voyage.js`'s `evidence: 'source'`
  tag and I took it as given. The boundary permitted me to read those files; I did not.
- **Panel C's chunk-field split at 641 is untestable from the fixture.** I confirmed neither
  `voyage-events.jsonl` nor `voyage-manifest.json` contains the power-cut *instant* — only
  `chunks_resumed: 641`, a count. I could not test the resume-journal contiguity assumption the panel
  itself names.
- **True-scale was judged from `style.width` percentages and computed styles**, not from pixel
  measurement of a screenshot. The `min-width: 2px` clamp on sliver segments means painted widths are
  not exactly proportional; all three panels disclose this.
- **I got one thing wrong and corrected it.** My first reading of Panel C's empty self-check box
  attributed it to the module-blocked path. It was a background-tab `requestAnimationFrame` artifact of
  my own harness. I re-ran the same URL fronted, the box populated, and I have reported the finding
  (**C3**) with the corrected cause. Recording it here because it is the one place in this review where
  an artifact of my instrumentation nearly wore a finding's clothes.
- **Nothing was modified.** The only file I wrote in the repo is this one. Three throwaway node scripts
  and a static file server live in the session scratchpad, outside the repository.
