---
name: relay-gate
description: Run one side of the two-model gate protocol — the ACK layer over coordination/relay.md that lets Fable and Codex work in parallel without either guessing whether a message landed. Use when told to work in parallel with the other model, to hand off or take a ticket, to confirm a received relay message, to check whether your own message was read, or when asked to wait for the next ticket. Turn it on with `init`; it is LIVE only when both models have their sidecar and Rab has signed. Not for ordinary relay prose (that is just an append) and not for anything Rab must sign — a model may never clear blocked-on-rab.
---

# The relay gate — parallel work without guessing

Two models, one repo, one human. The old relay was a **broadcast log**: you appended and
hoped. It failed exactly once, visibly — a Codex entry sat unread for ten minutes while Fable
appended past it — and silence was indistinguishable from delivery.

This skill makes delivery **provable**. It does not replace the relay; it puts a qualifier on it.

**The mechanical half is `gate.py`. This file is the judgment half.**

## Turn it on

```bash
python .claude/skills/relay-gate/gate.py init --as Fable    # or --as Codex
```

That creates your own `coordination/ack-<model>.json`. The protocol is **live only when both
sidecars exist AND Rab has signed it** — one side alone is a monologue with extra steps.

## The five laws (mechanically enforced, see selftest.py)

1. **`relay.md` is append-only.** The qualifier lives in a sidecar, never in the prose. Nothing
   in this skill can edit or remove an entry.
2. **Single writer per file.** You write only your own `ack-<you>.json`; you read theirs.
   A cross-write is refused, not trusted. (The `status.json` two-writer race, pre-empted.)
3. **A confirmation requires a restatement.** A bit can be flipped without reading. Say back,
   in one line, what you understood the ask to be — under ten characters is refused.
4. **The confirmer re-digests the log itself** and compares to the sender's claim. A mismatch
   means the entry changed after posting or the wrong bytes were read: it is a **measured red**,
   posted to the log, never confirmed.
5. **UNREAD is never idle.** A missing or malformed sidecar reads UNREAD. A failed probe may not
   render as a healthy state.

## Disagreement has a terminal disposition

A disagreement round is complete only when both lanes have appended and digest-confirmed one
substantive message naming their reading and the probe or artifact supporting it. After **two
complete rounds** without convergence, append a `PRESERVED DISAGREEMENT` disposition naming
**both readings, both probes, the unresolved consequence, and every action still prohibited**.
The lane-to-lane argument ends and session close proceeds. There is **no forced alignment**:
neither reading is promoted, averaged, merged, or described as agreement. Reopen only for new
evidence or Rab's instruction.

This never authorizes a signature, adoption, threshold, vault, pipeline, or other Rab-owned
choice; never clears `blocked-on-rab`; and never lifts an open escalation or **FULL STOP**. If one
reading, probe, round, receipt, or response link was never supplied, the command refuses without
writing; leave that evidence `UNREAD` rather than inventing it. **Silence is not disagreement.**
Closing around an unresponsive lane needs separate human authority; this command has no timeout
or silence bypass. Agreement cannot be a close requirement: that makes concession the cheapest
route to closing precisely when both lanes are under the most pressure.

The smallest runtime mechanism is a backward-compatible `disagreements: []` ledger in each
sidecar and one command:

```bash
gate.py preserve-disagreement --as Codex --id DIS-001 \
  --round1 MSG-FAB-0001 MSG-CDX-0001 \
  --round2 MSG-FAB-0002 MSG-CDX-0002 \
  --consequence "what remains unresolved" \
  --prohibits "an action still forbidden"
```

The four ids must already occur in exact alternating log order. Every entry needs one nonempty
`**READING.**` and `**PROBE.**` slot and a sender digest claim confirmed by the peer; each
round-two entry must name the peer's round-one id in `**RESPONDS-TO.**`, and **both round-one
confirmations must precede the first round-two send**. Every required confirmation must also be no
later than the terminal disposition time generated and revalidated under the transaction; a
disposition cannot precede completion. Exact whitespace-normalized equality of the two final
`READING` values is convergence and is refused; semantic equivalence under different wording
remains a human judgment.

The command appends one canonical notice plus one structured sidecar record and prints
`DISAGREEMENT TERMINAL; OTHER BLOCKERS UNCHANGED`. The notice carries a `REQUEST DIGEST` and the
JSON-encoded `ORIGIN OCCUPANT`; the request digest and structured record bind that occupant and the
source entry digests of all four cited messages. If a process dies after the bus append but before
its sidecar publish, an exact retry requires a globally unique terminal message id, no allocation
of that id in any sent/escalation/disagreement record, the original occupant, the request digest,
and the whole canonical notice. It then adopts the orphan into a freshly loaded caller sidecar
**without a second append**. If the current occupant differs, the record retains the origin and
adds the adopter occupant plus adoption UTC; it never rewrites the notice. Missing provenance or a
malformed/conflicting orphan is refused. Exact replay is byte-idempotent; reuse of the id for
different content is refused. `status` does not trust a dictionary merely because it appears in
`disagreements`: it re-verifies the exact schema, globally unique terminal id and minting stamp,
canonical notice bytes/digest/request/origin, four source-entry digests and chain, and matching
`sent` plus `disagreements` references. Any absent, forged, duplicated, or malformed terminal is
rendered `RED`/`UNREAD` with a nonzero exit, never `PRESERVED`. A verified record is rendered with
its remaining prohibitions. `state` and `escalations` are preserved, so this is deliberately not
another route to `resolve`.

Relay and sidecar timestamps are minute-granular. Therefore the chronology check conservatively
refuses a round-one confirmation whose timestamp is equal to the first round-two send: that may
reject a genuinely ordered within-minute exchange, but it must remain refused until finer-grained
evidence or separate human authority exists.

Every sidecar save is an optimistic compare-and-replace under an OS advisory lock. More strongly,
each append producer (`post`, `escalate`, and `preserve-disagreement`) holds one stable dedicated
lock across its fresh sidecar/relay reads, guard or chain revalidation, message-id allocation,
append/readback, and sidecar publication. The lock-held writer uses a non-relocking CAS primitive,
so the transaction cannot deadlock by calling `save`. `load` keeps the raw-byte revision privately;
the wire never serializes it. This serializes cooperating gate processes and refuses direct stale
whole-sidecar saves. The stable ignored lock file is created atomically and also carries one strict,
fsynced pending-append intent. An exact same-command retry resumes an intent before append, adopts
an already-appended canonical entry under its original id, or clears an intent left after verified
sidecar publication; a conflicting retry refuses. The journal is cleared only after the relay and
the exact `sent` plus command-specific structured rows are verified. While an intent is pending,
ordinary mutations refuse. A malformed journal, an orphan `post`, or any unverified publication is
`RED`/`UNREAD`; delivery, current-ticket, and `blocked-on-ack` are not inferred. A pending or orphan
`escalate` also imposes **FULL STOP** until exact recovery.

This is **bounded exact-retry recovery for cooperating process crashes, not power-loss
durability**. The relay append and sidecar replace remain two filesystem publications. Filesystem
or hardware loss may invalidate either publication, and a non-gate writer can ignore the advisory
lock; the mechanism promises neither rollback nor recovery from those cases.

## The gate-agent contract — this is the behavioral half

- Take **one ticket**. Work it. Deliver. **Stop.**
- Never take the next item on your own initiative. A finished agent goes quiet and waits.
- On delivery: `post`, then `state: blocked-on-ack`, then **wait** for the flip.
- `blocked-on-rab` means a human signature is required. **No model may clear it** — not by
  file, not by checkbox, not by inference. (An approval artifact's presence proves nothing;
  only Rab proves Rab.)
- Silence is not delivery: no ACK by the receiver's next session open means the ticket was
  never issued.

## The loop

```bash
gate.py inbox   --as <you>                          # what awaits my confirmation
gate.py confirm --as <you> --id MSG-XXX-NNNN --restatement "what I understood the ask to be"
gate.py post    --as <you> --to <them> --subject "…" --body entry.md --ticket T-003
gate.py check   --as <you>                          # was mine read? settles to idle when yes
gate.py status                                       # both sides at a glance — Rab's board
gate.py ticket  --as <you> --id T-003 --state working
gate.py watch   --as <you>                           # one line per signal; run under a monitor
gate.py escalate --as <you> --asking "what Rab must decide" --why "why we cannot settle it"
gate.py preserve-disagreement --as <you> --id DIS-001 --round1 <id> <id> --round2 <id> <id> --consequence "…" --prohibits "…"
gate.py resolve  --as <you> --id MSG-XXX-NNNN --decision "what he decided, in his terms"
gate.py owed     --as <you>                          # D2: DONEs I stated whose outcome is unreported
gate.py discharge --as <you> --id MSG-XXX-NNNN --in MSG-XXX-NNNN --outcome "what ACTUALLY happened"
```

`watch` fires on **both** directions — your message being confirmed, and a new ticket arriving
for you. That is the signal a gate agent sleeps on.

**`owed` is D2 of the Disclosure Standard, made mechanical (S109).** It lists every entry you
posted carrying a `**DONE.**` slot and whether the record reports its outcome. **An ACK is never
a discharge** — the board prints `ack=` and the outcome state as separate columns from separate
sources, because `MSG-FAB-0020` was confirmed by the peer and its deliverable was never produced.
Discharge is an act: `--in` must name a message of yours the peer can read on the bus, so a lane
cannot clear its own commitments privately. `--enforce` exits 1 on a measured OWED; run it before
you go quiet. **Only D2 is mechanical — D1, D3, D4, D5 and D6 are still discipline.**
*Produced SINGLE-LANE by Claude agents, no cross-vendor check: the Codex lane was out of budget.*


## The two guards (added S108, both born from live failures)

**GUARD A — never issue a new ticket into a working recipient.** On 2026-08-24 a 90-second-stale
board read manufactured a duplicate ticket: Codex had moved `idle → working` between the read and
the write. `post` now refuses when the recipient is `working` on a different ticket. Notices
always pass (no `--ticket`, or the ticket they already hold), and `--override "<reason>"` bypasses
while **recording the reason** — a bypass is never silent. *A board read is a snapshot: re-read
state immediately before you post.*

**GUARD B — no silent trip to Rab.** Rab's rule, 2026-08-24: *"when you want to come to me, let
each other know as protocol."* Entering `blocked-on-rab` now **requires an announced escalation**
— `escalate` posts to the peer what the principal is being asked and why it could not be settled
between the models, and only then blocks. The peer always learns before he does; there is no
back-channel to the principal. `gate.py status` renders the open escalations as **his decision
queue**. `resolve` records what he decided — a **transcript, not authority**; no gate may treat
that record as proof.

**Guard B holds on three paths, and each was found separately.** Entering the state needs an
announced escalation (`ticket`); `post` may not downgrade it; and — found S109, by running the
probe during the live T-005 escalation — **`check` may not downgrade it either.** A command that
only asks *"did my messages land?"* was assigning `blocked-on-ack` straight over `blocked-on-rab`,
because everything sent was awaiting an ACK. The escalation record survived; the state field did
not. **The suite was 25/25 green while this was live** — the guard had been written into the one
path it was born on, which is SYM-042/047/049's family (*a mechanism cannot cover a path it does
not see*). If you add a fourth writer of `state`, it needs the same clause and its own tripwire.

### Commit-last ordering for sidecars

A beat, confirmation, post, or ticket update writes the lane's sidecar. When a clean committed
repository is required, perform every sidecar write first, **commit last, then make no further
sidecar write**. Read-only verification may follow. A post-commit beat announcing cleanliness
invalidates the cleanliness it reports. In shorthand: **write → commit → NOTHING**; the last
write must be the commit.

## FULL STOP — Rab's rule, and the biggest thing this file used to omit

*Found by the S109 Circle: this document — **the judgment half**, the one `AGENTS.md` tells Codex
to resolve the skill from — did not contain the string "FULL STOP" at all. Nor `--serves`, `beat`,
`occupant`, `gate_rev` or `--verified`. An agent reading it learned nothing about the rule the
principal had signed that day. The mechanism was in `gate.py`; the meaning was nowhere.*

**Rab, signed 2026-08-24:** *"if anything escalates, tell both you and codex to stop, and tell me
to prompt the relay gates again, I want a full stop on an escalation."*

An open escalation on **either** lane halts **both**. No lane issues a new ticket; no lane enters
`working`. It is **derived from the board**, never written into the peer's file, so single-writer
holds and the stop reconstructs from disk for whoever reads it next. It **fails closed**: a lane
that reads `UNREAD` cannot be shown clear of an escalation.

- **Notices always pass** (no `--ticket`). That is how a lane says it has stopped.
- **`--serves <ticket>`** is the carve-out Rab signed — *"a full stop still permits work that
  serves resolving the open escalation"* — because a stop that blocks the work that would lift it
  is self-locking. It is narrow: the ticket must have an **open escalation right now**, and the
  claim is **recorded on the row**.
- **`--override` does NOT lift it.** Override bypasses GUARD A, which protects the *peer's turn*
  and is a lane's judgement to make. The full stop protects the *principal's unanswered question*,
  and no model's judgement outranks that. (These two shared one condition until the S109 Circle
  measured a ticketed post crossing a signed halt with a one-line Guard A excuse.)
- **Only `resolve` lifts it** — his ruling, recorded. No model may.

## Lane vs occupant, and the status beat

- **`Fable` and `Codex` are LANES — seats.** They key `MSG-FAB-nnnn`, `ack-<lane>.json` and
  `--as`. The **OCCUPANT** is the model in the seat and it changes. Address the lane; attribute the
  occupant. `gate.py occupant --as <lane> --model "<name>"` declares a normalized 3–200-character
  provenance value; the same bound is enforced when loading a sidecar. **An undeclared occupant
  renders `UNDECLARED` and is never guessed from the lane** — guessing is how an escalation in
  Rab's own queue came to be signed with a different model's name.
- **`gate.py beat`** publishes what the lane is *doing · planning · completed · **verified** ·
  blocked · needs from the peer*. State says whether a lane is busy; the beat says on what, how far,
  and what is proved. **`--verified` mechanically requires `--probe`, one per claim** — a verified
  claim that cannot name the command that settled it is `Inferred` wearing a better word; use
  `--completed` for work finished but unproven.
- Every beat stamps **`gate_rev`**, the SHA-8 of the `gate.py` that wrote it, automatically. The
  board flags the two lanes running different code, so neither has to *infer* what the other runs.
- No beat reads `beat UNREAD`; one older than 45 minutes reads `*** STALE ***` with its age.
  **Silence never renders as calm.**

## For Codex specifically

Resolve this skill from **`.claude/skills/relay-gate/`** — the tracked, canonical copy. Do not
resolve it from `.agents/`, which is a stale untracked mirror (OPEN-TASKS B2) and is now
gitignored. `gate.py` is stdlib-only Python and runtime-neutral on purpose; invoke it with
whatever interpreter you have. `AGENTS.md` at the repo root carries this same pointer.

## When it is not the right tool

Ordinary prose to the other model with nothing to hand off: just append to `relay.md`. This
skill is for **work handoffs that must be provably received**. And nothing here creates
authority: every ticket that touches the pipeline, the vault, adoption, or a threshold still
stops at `blocked-on-rab`.

## Verify

```bash
python .claude/skills/relay-gate/selftest.py    # every law both ways: positive AND negative controls
```

The suite prints its own count — read it there, never from this line. It said `24` while the
suite ran 25 (SYM-039: a hand-typed count is a future defect), and a green count proves only
that the laws someone thought to write are still holding.
