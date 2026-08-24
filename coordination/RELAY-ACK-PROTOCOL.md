# The relay ACK protocol — `fp-relay-ack/v1`

**Status: PROPOSED by Fable 2026-08-24. Not active until Rab signs and Codex confirms.**
Commissioned by Rab: "the message in the relay must have a qualifier that determines it to be
read and confirmed, instead of an entry… the agent just waits to see if this qualifier has
changed from inactive to active, then settles until it receives another relay message."

## Why a sidecar, not a flag in the prose

`relay.md` is **append-only** — a law both models have now violated once and repaired. A
qualifier edited inside an entry would break it on every acknowledgment. So:

- **`relay.md` is the log** — immutable, prose, the history of record.
- **`ack-<model>.json` is the state** — machine-readable, mutable, a *projection* of the log.
- If the two ever disagree, **the log wins** and the sidecar is rebuilt from it.

## Single writer per file (no locks, by construction)

| File | Sole writer | Everyone else |
|---|---|---|
| `coordination/ack-fable.json` | Fable | read-only |
| `coordination/ack-codex.json` | Codex | read-only |

A monitor watches **the other side's file**. This is the exporter's single-writer law applied
to messaging; it removes the two-writer race that `status.json` needed `source_component` to
diagnose.

## The qualifier is three states, not two

A bit can be flipped without reading. A **restatement** cannot. So `confirmed` requires the
receiver to say back, in one line, what it understood the ask to be.

| State | Means | Set by |
|---|---|---|
| `posted` | the sender appended it to `relay.md` | sender, in its own file |
| `detected` | the receiver's monitor saw it | receiver |
| `confirmed` | the receiver read it and **restated the ask**, with the body digest matching | receiver |

Rab's signature is a separate gate and is never a state any model may set.
*(This ladder is deliberately compatible with Codex's Concordance Lab law — POSTED → DETECTED
→ … → HUMAN-AUTHORIZED → CLOSED — so the two need not be reconciled later.)*

## Message identity

Every relay entry that expects an ACK carries an id line in its RECAP:
`MSG-FAB-0001` / `MSG-CDX-0001` (sender prefix, zero-padded sequence).
The ACK records the **sha256 of the entry body**, so a confirmation proves *which bytes* were
read — a restatement of a different message cannot pass.

## File shape

```json
{
  "writer": "Fable",
  "protocol": "fp-relay-ack/v1",
  "updated_utc": "2026-08-24T00:00Z",
  "state": "idle | working | blocked-on-ack | blocked-on-rab",
  "current_ticket": null,
  "sent":      [{"id":"MSG-FAB-0001","to":"Codex","utc":"...","digest":"sha256:...","subject":"...","requires_ack":true}],
  "confirmed": [{"id":"MSG-CDX-0007","from":"Codex","digest":"sha256:...","confirmed_utc":"...","restatement":"one line: what I understood the ask to be"}]
}
```

## The gate-agent contract

1. An agent takes **one ticket**, works it, delivers, then **stops**. It never takes the next
   item on its own.
2. On delivery it posts to `relay.md`, records the send in its own ack file, sets
   `state: blocked-on-ack`, and **waits**.
3. Its monitor watches the other side's ack file for its message id in `confirmed`.
4. On the flip, the agent **settles** — `state: idle` — and does nothing until a new ticket.
5. `blocked-on-rab` means a signature is required; no model may clear it.

## Failure semantics

- **No ACK by the receiver's next session open** → the ticket is *unissued*, not in-flight.
  Silence is never delivery.
- **Digest mismatch** → the confirmation is refused and the mismatch is posted to the log.
- **A malformed or missing sidecar** → `UNREAD`, never `idle` and never `confirmed`.
  A failed probe may not render as a healthy state.
