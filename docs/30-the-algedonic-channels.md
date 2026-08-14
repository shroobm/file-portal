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

## 6. Why this is a session and not a patch

Decisions 1 and 4 change what the system *claims about itself*, and decision 2 touches an
outward-facing channel. Everything here is small in code and large in commitment. The survey is
done; the build is one signature away.
