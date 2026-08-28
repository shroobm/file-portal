# The Bus Standard — how two models coordinate without collision

**Signed by Rab 2026-08-24.** His design, not a model's: one channel, halting receive.

## The invariant

**All cross-model coordination is an append to one file — `coordination/relay.md` — and a model
halts while parsing the other's message. You cannot collide with someone you are halted for.**

Communication and synchronization are the same act. This is CSP (communicating sequential
processes) reached from the bureaucracy end: no shared mutable state, only messages over a
channel with rendezvous semantics.

## The five rules

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
   preserve both readings and both probes and let close proceed, subject to the unchanged
   `blocked-on-rab`, open-escalation, and FULL STOP boundary in the relay-gate skill. Requiring
   agreement makes concession the cheapest route to close.

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
- `.claude/skills/relay-gate/` — the mechanism (24 tripwires, both directions)
- `coordination/CODEX-RESIDENCY.md` — the standard applied to shared workspace
