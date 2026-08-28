# The Bus Standard — how two models coordinate without collision

**Signed by Rab 2026-08-24.** His design, not a model's: one channel, halting receive.

## The invariant

**All cross-model coordination is an append to one file — `coordination/relay.md` — and a model
halts while parsing the other's message. You cannot collide with someone you are halted for.**

Communication and synchronization are the same act. This is CSP (communicating sequential
processes) reached from the bureaucracy end: no shared mutable state, only messages over a
channel with rendezvous semantics.

## The six rules

1. **One bus.** Everything cross-model goes through `relay.md`. No side channels, no second bus.
   The `ack-<model>.json` sidecars are not channels — they are the *lock state on the channel*.
2. **Halt while parsing.** `working` and `blocked-on-ack` are the lock, not a status. A model does
   not act on a shared thing until it has parsed, **restated**, and digest-verified the peer's
   message. The restatement is what makes the halt real: you cannot be done parsing without
   proving you parsed.
3. **Appends never erase.** The worst two writers can do to each other on an append-only log is
   misorder — never destroy. Corrections append and link; history is never repaired in place.
4. **Digests never trust.** Every confirmation independently re-derives the digest from the log.
   Interleaving or tampering is *detected*, not trusted away.
5. **Everything else is a turn.** Nobody schedules turn-taking; at most one side acts on a shared
   thing at a time, and that falls out of rules 1 and 2. `gate.py status` shows whose turn it is.
6. **Disagreement terminates without forced alignment.** After two complete reciprocal rounds,
   with both round-one receipts recorded before the first round-two send, preserve both readings
   and both probes only when all four receipts are no later than the terminal disposition, then let
   close proceed, subject to the unchanged
   `blocked-on-rab`, open-escalation, and FULL STOP boundary in the relay-gate skill. Requiring
   agreement makes concession the cheapest route to close. Exact normalized final readings are
   convergence, not disagreement; semantic equivalence remains human judgment.

## Mechanical transaction boundary

Every gate command that mints and appends a same-lane message (`post`, `escalate`, and
`preserve-disagreement`) holds one stable OS advisory transaction lock from its fresh reads and
guard/revalidation through id allocation, append/readback, and sidecar publication. Thus two
cooperating processes cannot mint the same relay id or publish one command over the other's whole
sidecar. Disagreement preservation revalidates its cited chain inside that transaction, records
the source entry digests, and binds the origin occupant into its canonical notice and request
digest. Orphan adoption requires the terminal id to be globally unique and unallocated in every
sent, escalation, and disagreement record; a later occupant is recorded as adopter, not rewritten
as origin.

The stable ignored lock file is atomically initialized and carries one strict, fsynced pending
append intent. An exact retry of `post`, `escalate`, or `preserve-disagreement` resumes before the
append or adopts the already-appended canonical entry under its original id; a conflicting retry
refuses. The intent clears only after the relay and exact sidecar publication are re-verified.
Pending or malformed intents block ordinary sidecar mutation and make `status` fail closed:
an orphan post is not delivery or idle, and an orphan escalation imposes **FULL STOP**.

This is **bounded exact-retry recovery for cooperating process crashes, not power-loss
durability**. Relay append and sidecar replace remain two filesystem publications. Filesystem or
hardware loss may invalidate either publication; the advisory lock cannot compel a bypassing
writer and promises no rollback. Terminal disagreement records also remain subject to strict
status/replay verification: an absent, forged, duplicated, or malformed terminal is `RED`/`UNREAD`,
never `PRESERVED`. Occupant provenance is normalized and bounded to 3–200 characters. Because
relay timestamps are minute-granular, an equal-time round-one receipt and first round-two send is
conservatively refused; semantic chronology needs finer evidence or human authority.

## Artifacts outside the bus

Work products (the seam exports, `codex/`, the wiki) are written outside the channel. One sentence
covers them: **nothing lands in shared space except announced through the channel, with the writer
halted until confirmed.** Single-writer-per-artifact then follows from the announcements
themselves — no ownership registry required.

## Why there is no territory registry

An earlier draft proposed static path ownership, leases, and a registry. Rab's correction stands
on the evidence: the one real collision — the duplicate ticket `T-003`, 2026-08-24 — did not
happen *in* the relay. It happened because a model **acted between halts**, on a 90-second-stale
board read. Strict halting makes that class impossible; `gate.py`'s GUARD A is that halt
mechanized for the actor who broke discipline. Territory machinery would have prevented nothing
that halting does not already prevent. **The withdrawn draft is recorded here so it is not
re-invented.**

## Implementation

- `coordination/RELAY-ACK-PROTOCOL.md` — the wire format and the prompt contract
- `.claude/skills/relay-gate/` — the mechanism (the selftest prints its live tripwire count;
  do not copy a hand-maintained count here)
- `coordination/CODEX-RESIDENCY.md` — the standard applied to shared workspace
