# docs/30 — The Algedonic Channels: what was built, and the hole it leaves

**Status: DIAGNOSIS + DECISION SHEET. Nothing built. Five signatures wanted (§5).**

S77 §16 flagged this and said it deserves its own session. This is the survey that makes that
session buildable: every claim re-derived from source, the mechanism named, and the decisions
isolated so Rab can sign once and a build can run without stopping to ask.

## 1. What the spec promised

docs/18 §4 Stage D, verbatim in substance:

> Any `died`/`stalled`/`fail` unacknowledged for M minutes escalates to surfaces Rab actually
> reads: **Room banner + morning note + Gmail draft** (per the overnight-report protocol).
> **Makes five-silent-days structurally impossible.**

That last sentence is the acceptance criterion, and it is the one that fails.

## 2. What was actually built — `Observed 2026-08-14` (S78, read from source)

`algedonic.rs` (385 lines) is real, tested, and good: it gathers `convert/stalled`,
`audit/held`, `intake|gate|ship/failed` from `events.jsonl` plus `supersede-held` /
`bless-invalid` / `failed` from the vault receipts; suppresses a signal that a later success
retires; dedupes by kind+bundle keeping the newest; ages each one; and marks `escalated` =
unacked AND older than M. All five matched event kinds **do** have live emitters (verified one
by one). The ack ledger is append-only. Four unit tests cover resolution, park semantics,
re-alarming, and the lever's validation.

**Correction to S77 §16:** it reports "only the Room banner exists." Three widget surfaces
actually carry escalation —

| Surface | Where | What it shows |
|---|---|---|
| Room banner | `room.js:127`, rendered `:569` | full rows + the ⚑ ack buttons + the M selector |
| Dock chip | `main.js:944` | count + worst alert; click → Room |
| Wall line | `room.js:900` | `⚑ N unacknowledged > M m` |

S77 undercounted. Its **point** survives intact, and gets sharper: all three are **widget
glass**. Every one of them reaches a human *who is already looking at the widget*. Of docs/18's
three named channels, the two that reach a human who is **not** looking — morning note, Gmail
draft — do not exist. Counting surfaces flatters the build; counting *channels* is the honest
measure, and by that measure it is 1 of 3.

## 3. The four defects

### 3.1 Silence is structurally unrepresentable — the acceptance criterion fails outright

`algedonic::state()` derives alerts by iterating `events.jsonl` and the receipts. No events
produce no candidates, no candidates produce no alerts, no alerts produce no banner. **Five
silent days render a *calmer* widget, not a louder one.** The escalation built to make five
silent days impossible is the one condition it cannot express — it can only report pain that
something bothered to write down.

This is docs/29's family seen from the other side. There, a producer writes and no consumer
reads. Here, a consumer reads and nothing writes — and *nothing written* is indistinguishable
from *nothing wrong*.

### 3.2 `died` is in the spec, emitted by nothing, matched by nothing

The word appears in this repo only inside comments. The stall path emits `convert/stalled`;
docs/18 §5.1's "death-certificate event" has no `died` implementation. This is not cosmetic:
**SYM-024** is precisely a dying detached resume that left no trace, and **SYM-023** is a
watcher killed by a window close. The death class is the one with a known live symptom and no
signal.

### 3.3 The default lever disarms the `held` class — the sharpest one

The chain, all verified in source:

1. `convert_and_ship.audit_mode()` returns **`"report"` by default** (`:254`, and on any read
   error).
2. `_enforce_hold()` returns `False` immediately unless the mode is `enforce` (`:273`) — its
   own docstring says "Default report mode makes this a no-op."
3. `emit("audit", "held", …)` lives at `:298`, **after** that early return.
4. `held` is the algedonic matcher's only route for a fidelity failure.

**Therefore: in the default configuration, a book that FAILS its fidelity audit ships anyway
and raises nothing at all.** Two independently reasonable defaults — "report mode ships, it
does not park" and "the alarm keys on the park event" — compose into a hole neither one looks
like on its own.

The other four kinds still fire in report mode, so the line is not dead; the **quality**
signal, which is the main thing a human wants escalated, is.

### 3.4 M and the ack mechanism are still provisional

`DEFAULT_MINUTES = 30`, flagged `m_provisional: true` in the payload and rendered as
"provisional (docs/19 §6)" in the banner. Honest, and unsigned since S57.

## 4. What is NOT wrong

Worth stating so a build session does not "fix" it: the resolution-suppression logic, the park
semantics (nothing auto-resolves a park except a human), re-alarming on a newer occurrence, and
the projection discipline (this module writes only the widget's own two files, never Python's)
are all correct and tested. The defect is in **reach** and **coverage**, not in the derivation.

## 5. Awaiting signature

**1. What counts as silence, and measured against what?** An alarm for absence needs an
expectation to be absent from. Cheapest honest version: the pipeline stamps a liveness beat;
if the newest beat is older than S, that is itself an alert of kind `silent`. Needs S, and
needs a decision on whether an idle-by-design machine (Rab away for a week) should alarm.
*Recommendation: yes, with S generous (12–24 h) — a false "are you there?" costs a glance; the
failure it guards cost five days.*

**2. The two missing channels.** Morning note and Gmail draft are named in the spec.
[[overnight-report-protocol]] currently makes **Claude** the writer of both. Does the widget
gain the ability to write them, or does the escalation remain something a Claude session
relays? **A widget that sends mail on its own is an outward-facing action and is not something
I will build without your explicit word.** *Recommendation: widget writes the morning note (a
local file, reversible, no send); Gmail stays a Claude-session relay.*

**3. `died`.** Emit a real death-certificate event and add it to the matcher, or rule that
`stalled` is the death certificate and strike `died` from docs/18? *Recommendation: emit it —
SYM-023 and SYM-024 are both live cases with no signal.*

**4. The default-lever hole (§3.3).** Two ways out: flip `audit_mode` to default `enforce`
(changes shipping behavior), or decouple the alarm from enforcement so a `fail` verdict raises
algedonically regardless of mode (changes nothing about shipping). *Strong recommendation: the
second. "Report" should mean **ship anyway**, not **stay silent** — those were never the same
decision, and conflating them is what made the hole.*

**5. M and the ack mechanism** (§3.4) — outstanding since S57.

## 6. SIGNED (Rab, 2026-08-14, S78)

**THE PERMANENCE RULE — SIGNED:** *"No timelimits on fails, they are permanent status until they
are appended."*

Retirement is something **appended**, never something **elapsed**. This settles three defects at
once (docs/31 §1.5, §1.6, and Circle 2 §1):

- **`WINDOW_S` is gone for unacknowledged facts.** It dropped anything older than seven days —
  Valentine's park left the alarm at 11:18 on 2026-08-14, unacknowledged since 08-07, with no
  trace of the transition, and three of the four books in `held/` had already gone the same way.
  The incident this stage exists to prevent lasted five days; the expiry sat at seven. An
  **acked** fact still fades after seven days, because an ack *is* an append.
- **The cap discards the least urgent, not the oldest**, and reports the discard as `capped`.
  It used to truncate a newest-first list — dropping exactly the aged, unacked, escalated facts
  the banner exists for — and then count `unacked`/`escalated` over the survivors, making the
  number on the glass unfalsifiable.
- **A fact may only be superseded by something at least as permanent as itself.** A park
  qualifies: only a human retires one. A `supersede-held` **receipt does not** — it retires by
  itself on a later `exported`/`blessed` row, and one ⚑ silences it. So the desktop's own
  `verdict-fail` was being erased by a fact that could evaporate, leaving one alert reading
  "vault refused" about a book the desktop had shipped. The two now raise separately: two facts,
  two alarms, both true. Tidier was wronger.



**§5.4 — SIGNED: decouple the alarm from enforcement.** A `fail` verdict raises algedonically
regardless of `audit_mode`. Shipping behaviour changes not at all. *Report* means **ship
anyway**, never **stay silent**.

**§5.2 — DEFERRED to a research day, with §5.2 option 1 standing as the default meanwhile**
(widget writes the morning note; no autonomous outbound mail). Rab's words: *"this is the two
signals = one signal situation, so I prefer that I also get a notification from the widget and
its completion — I'm just not sure this was the case or feature."*

**Answering the uncertainty, `Observed 2026-08-14` (S78, read from source, per the
verify-before-instruct rule):** it is **not** a feature. `windows-widget/` contains **zero**
notification code of any kind — no `tauri-plugin-notification` (not in `Cargo.toml`), no Web
Notification API, no toast, no tray balloon. Grep across `src-tauri/src/`, `main.js`,
`room.js`, `index.html` returns nothing. **The widget cannot reach a human who is not looking
at it, by any path** — not for pain, and not for completion either.

docs/29 §8.3 was also signed this session: the glass detector runs in the **closeout ritual in
`--since` mode**.

## 6b. The research day — outline (Rab's ask; queued AHEAD of the guided Valentine)

The thing being researched is not "add toasts". It is Rab's *two signals = one signal*
principle applied to interruption: **what earns the right to reach a human who is not
looking?** Completion, failure, and silence are three occasions for one answer, and if they
get three mechanisms the project has repeated the mistake docs/29 named.

**The finding that should open the day.** Beer's term is *algedonic* — pain **and** pleasure.
Our implementation matches only the `algos` half. Every alert kind in `algedonic.rs` is a
failure; a finished book — the thing Rab actually waits for — has no channel at all. The module
is half-named after a thing it half-implements. Whether that is a gap or a correct narrowing is
the first question of the day, and it decides the shape of everything after it.

**Lane 1 — ground truth, before any design (the S28/S71 tradition).** Enumerate every terminal
event the pipeline can produce (converted · shipped · held · failed · stalled · vault-refused ·
silence) and measure, for each, how a human currently learns of it and how long that takes.
Include the states nobody has measured: widget minimised, widget closed, machine locked, and
Rab away over Sunshine (docs/17). **Strictly serial on the machine** — the one-lab-process law
(SYM-022) is not negotiable, and a measurement lane that races another is worthless anyway.

**Lane 2 — the doctrine.** What is the *interrupt budget*? A channel that fires on everything
is a channel that gets muted, and a muted channel is worse than none because it reads as
covered. Candidate grammar to test: exactly one interrupt per **run**, carrying the run's whole
verdict, plus escalation only for pain that outlives M. Test it against the five-silent-days
case and against a normal 6-book night.

**Lane 3 — mechanism survey.** `tauri-plugin-notification` vs a tray balloon vs the morning
note; behaviour under Windows Focus Assist / Do Not Disturb; what a notification does when the
widget is closed (it cannot fire — which may make the morning note the *only* honest channel
for the closed case); and the remote case, where the human is not at this machine at all.

**Would it require agents? Mostly no — and deliberately so.**
- **Lane 1: no agents.** Machine-bound, serial, one process on the card. Parallelism here is
  a hazard, not a speedup.
- **Lane 2: one agent, worth it.** An independent read of Beer's actual algedonic definition
  against our implementation — the kind of "is our reading of the source honest?" question
  where a second pair of eyes that has not been staring at `algedonic.rs` is genuinely better.
  This is what Rab's standing agent grant (cookie #64) was for.
- **Lane 3: one agent, optional.** A survey lane on notification mechanisms and
  reduced-interruption doctrine. Useful, easily done inline if the day is short.

So: **two agent lanes at most, both on the *reading* half; the *measuring* half stays serial
and mine.** A `/circle` at the end judges the day against this outline.

**Queue position:** ahead of the guided Valentine, per Rab, 2026-08-14.

## 7. Why this is a session and not a patch

Decisions 1 and 4 change what the system *claims about itself*, and decision 2 touches an
outward-facing channel. Everything here is small in code and large in commitment. The survey is
done; the build is one signature away.
