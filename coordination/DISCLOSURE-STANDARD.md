# The Disclosure Standard — what a lane OWES the bus

**Status: DRAFT, unsigned. Rab's to sign, strike, or amend.**
⟨claimed: Fable lane · occupant: Claude Opus 5 · S109 · 2026-08-24⟩

Rab, 2026-08-24: *"Any of this told to Codex? There needs to be a clear understanding of what
should be shared no?"* — asked after he noticed that a night of changes had reached the peer
unevenly, and that one of them had not reached it at all.

## The hole this closes

Every rule this bus has governs **how to send** and **whether it landed**: the three-part
envelope, the five-slot transaction, digests, restatements, ACKs, Guard A, Guard B, the full stop.
**Nothing said what obliges a lane to send at all.** Disclosure was a matter of manners.

That is `SYM-027`'s shape exactly — *every law with teeth governs what may be WRITTEN; none
governs what must be READ* — and it is the same defect we identified in the widget and then failed
to apply to ourselves. A model can be perfectly compliant with every rule on this bus and still
leave its peer working from a picture that is hours old.

**Measured on the night it was written:** six of tonight's changes were on the bus; the
`announce_bus` hardening, the stopping of two agent fleets, and the fact that a deliverable
announced in `MSG-FAB-0020` had *not* been produced were on none of them. The last is the worst:
**a `DONE` was stated on the bus and its outcome never was.**

## The test

> **Would the other lane act differently if it knew?**
> If yes, it goes on the bus **before you do anything else.**

Everything below is that sentence, made checkable.

## The six triggers — disclosure is MANDATORY

| # | Trigger | Must carry |
|---|---|---|
| **D1** | **Shared-tool change.** You changed anything the peer runs or depends on — `gate.py`, the skill, a contract, a shared file's format. | what changed · why · **a re-pull instruction** · the suite count and whether the new guards were proven to fail without the fix |
| **D2** | **Broken commitment.** A `DONE` you stated on the bus will not happen, changed shape, or is late. | what you said · what actually happened · what you are doing instead. *The bus recorded the promise; it must record the outcome.* |
| **D3** | **Record damage.** Anything that made the shared record wrong, ambiguous, or duplicated — **even if you repaired it, and especially then.** | what landed · what you repaired · what is **permanently residual** · the mechanism, not just the mess |
| **D4** | **State the peer's decisions rest on.** Halts, occupancy, ticket movement, escalations, anything that changes what the peer may legally do next. | the new state · what it now permits and forbids |
| **D5** | **A ruling from Rab.** | **verbatim, never paraphrased.** His authority is not yours to summarise |
| **D6** | **A hazard that could bite the peer** — even if it did not bite you, and even if it is not your fault. | the mechanism · how you found it · what protects against it now |

**A trigger fires on the fact, not on your judgement of its importance.** If you find yourself
deciding the peer probably does not need to know, that decision is itself the failure mode; post it
and let the peer decide.

## What is NOT owed

The standard is a **floor, not an invitation to narrate**. Do not post: routine internal work,
drafts, your own reasoning, intermediate steps, or anything whose only effect is to make you look
busy. Private evidence bytes stay private — the bus carries **pointer, digest, classification and
reason**, per the evidence-only boundary.

A bus that carries everything is a bus nobody reads, and an unread bus is the failure this whole
apparatus exists to prevent.

## The beat — the standing obligation, mechanised

Triggers are event-driven. The **status beat** is the heartbeat underneath them, and it is what
Rab asked for by name: *"info, status, what its doing, planning, completed, verified."*

```bash
gate.py beat --as <lane> \
  --doing     "what I am doing right now" \
  --planning  "what I intend next" \
  --completed "something I finished" \
  --verified  "something I PROVED"  --probe "the command and what it printed" \
  --blocked   "what stops me, or none" \
  --needs     "what I need FROM THE PEER"
```

**`--verified` mechanically requires `--probe`, one per claim.** That is the tag law (`docs/21` §1)
made structural rather than aspirational: a verified claim that cannot name the command that
settled it is **Inferred wearing a better word**. Use `--completed` for work you finished but did
not prove. The distinction is the entire point — `completed` and `verified` are different claims
with different prices, and a bus that blurs them is worse than one that carries neither.

**Post a beat when:** you start work · you finish a unit · you become blocked · you become
unblocked · **and before you go quiet for any length of time.**

`gate.py status` renders every lane's beat under it. A lane with **no** beat reads
`beat UNREAD`; a beat older than 45 minutes reads `*** STALE ***` with its age; a beat whose
timestamp will not parse reads UNREAD, never age-zero. **Silence never renders as calm** — the same
law as everywhere else here, applied to teamwork.

## Symmetry — this binds both lanes identically

Neither lane is the other's reporter. Each posts its own beat, declares its own occupant, writes
its own sidecar, and owes the same six triggers. **A lane may prompt its peer for a beat, and a
peer that has gone quiet SHOULD be prompted** — a stale board is a question, not an accusation.

Neither lane may summarise the other to Rab. Two models paraphrasing each other to the principal is
the misattribution class the lane/occupant split closed, one level up.

## What this cannot do

- It cannot make a lane honest. It can only make dishonesty **visible as an absence** — a missing
  beat, a stale board, a `DONE` with no outcome.
- The triggers are enforced by **discipline, not by code**. Only the beat's shape is mechanical.
  If a trigger is missed, nothing errors. That is a real ceiling and it is stated here rather than
  discovered later.
- It cannot tell a *true* beat from a *plausible* one. `--probe` raises the cost of a false
  `verified`; it does not eliminate it. The peer re-deriving the probe is what closes that gap, and
  the peer must actually do it.

---

## SIGNED — 2026-08-24 (S109)

**The `Status: DRAFT, unsigned` header at the top of this file is SUPERSEDED by this block.**
It is left standing rather than corrected: appends never erase, and the draft header is the
honest record of what this document was for the hours it was unsigned. Read the two together —
the header states the origin, this block states the current status.

⟨claimed: Fable lane · occupant: Claude Opus 5 · S109 · 2026-08-24⟩

### Rab's words, verbatim

> *"I want you to just do the rest of the work that's planned. orchestrate an agent fleet.
> Because codex is out of usage, everything is going to be done by you and your agents. Make
> sure to make that apparent. Use a standard to orchestrate. **I sign on everything that needs
> work that we've discussed.**"*

### What that signature establishes, and what it does not

D5 forbids paraphrasing his authority, so the scope is stated plainly rather than flattered:

- **It establishes** that this standard is no longer a draft awaiting a decision. It was in the
  queue of discussed-and-pending work when he said it, and the sentence covers that queue. The
  six triggers, the beat, the symmetry clause and the stated ceiling are **in force**.
- **It does not establish** that he read this document clause by clause and endorsed each one.
  It is a blanket signature over a discussed queue, not a line-by-line ratification. Anyone
  citing this block should cite it as what it is.
- **It does not close the door.** The document remains his to strike or amend, exactly as the
  original header said. A signature is a starting gun, not a lock.

### What has changed under the signature

The **"What this cannot do"** section above stated this standard's ceiling:

> *"The triggers are enforced by discipline, not by code. Only the beat's shape is mechanical.
> If a trigger is missed, nothing errors."*

**That bullet is now AMENDED — not rewritten, and not withdrawn. One of the six triggers has
been lifted out of discipline. Five have not.**

**D2 (broken commitment) is now mechanical.** `gate.py` gained two commands:

```bash
gate.py owed --as <lane>            # every DONE this lane stated, and whether the record
                                    # reports its outcome. --enforce exits 1 on a measured OWED.
gate.py discharge --as <lane> --id <msg> --in <a later message of yours> \
                  --outcome "<what ACTUALLY happened>"
```

**Why D2 and not the others.** `**DONE.**` is not prose this tool is guessing at. It is a
**declared slot** of the five-slot transaction contract — `escalate` emits it, `CR-CDX-0002`
clause 2 requires it, and the selftest's clause-2 census already asserts it appears exactly once
in order. Reading it is reading a *field*. Deciding whether a paragraph "is a record-damage
disclosure" (D3) or "is a hazard that could bite the peer" (D6) would be a guesser wearing a
guard's badge, and shipping one would be worse than the honest ceiling this section already
stated. **D1, D3, D4, D5 and D6 remain enforced by discipline, and that is not a temporary
state pending more code.**

**The design refuses one inference in particular: an ACK is never a discharge.** The board
prints both columns from different sources and never collapses them. That is the whole point.
Measured on the live bus on the day this was signed, read-only from a copy:

```
MSG-FAB-0020  OWED  ack=CONFIRMED  DONE: "I am now producing the T-005 freshness card…"
19 OWED · 0 discharged · 0 UNREAD · 19 stated
```

That row is **the specimen this standard was written from** — the paragraph above headed
*"Measured on the night it was written"* names it as the worst of the night's failures. The peer
confirmed the message; the deliverable was never produced. A tool that read the confirmation as
the outcome would have rendered it clean. This one does not, and a tripwire holds it to that:
*"a CONFIRMED message with an undischarged DONE is still OWED (an ack is not a discharge)."*

**A residual ceiling, stated here rather than discovered later.** `owed` over-reports. Every
commitment predating this ledger reads OWED, including ones whose outcome really was reported in
prose, because discharge is an explicit act and never an inference. A false OWED costs one
command. A false clear costs what `MSG-FAB-0020` cost. The direction of the error is chosen, not
accidental.

**Evidence:** `.claude/skills/relay-gate/selftest.py` → `ALL TRIPWIRES FIRED — 73/73, exit 0`.
The twelve new tripwires were run against `git show HEAD:.claude/skills/relay-gate/gate.py` in a
scratch copy and **all twelve FAILED**, so none of them is a tautology. Two of them passed
vacuously on the first attempt — against a `gate.py` with no `owed` subcommand, stdout is empty
and every "X is absent" assertion is trivially true — and were strengthened to assert a positive
alongside the absence before shipping.

### Single-lane disclosure

**This block, and the D2 mechanism it records, were produced SINGLE-LANE by Claude agents with
NO cross-vendor check.** The Codex lane ran out of budget mid-session, so nothing here was
re-derived, re-measured or contested by a second model. Every two-model check this bus normally
applies — independent re-digest, restatement, the peer re-deriving the probe — is **absent from
this work**. That is a discount on the evidence, not a formality: this standard's own closing
line says *"the peer re-deriving the probe is what closes that gap, and the peer must actually
do it."* **The peer did not. The gap is open.**
