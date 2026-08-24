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

## Escalation (added S108 — Rab's rule)

`blocked-on-rab` may only be entered through `escalate`, which first announces to the peer:
what Rab must decide, and why the models could not settle it. The sidecar carries them:

```json
"escalations": [{"utc":"…","ticket":"T-011","asking":"…","why":"…","msg_id":"MSG-FAB-0007","state":"open"}]
```

`status` renders every open escalation as **Rab's decision queue**. `resolve` records his
decision and settles the agent to `idle`. That record is a **transcript, not authority** — the
countersign question (sign-sheet item 14) remains open, and no gate may treat a written decision
as proof that he made it.

## The prompt contract (signed 2026-08-24; **OPEN FOR CODEX'S AMENDMENT**)

> **Status: in force as the signed baseline, not settled over Codex.** It was shipped as
> "required" after Rab's signature, but the proposal he signed had said *"sent to Codex as one
> ticket for its amendment, then yours to sign."* That sequence was inverted in execution and he
> corrected it (`MSG-FAB-0007`, 2026-08-24). Codex may amend by change request; the baseline
> governs until Rab signs the change.
>
> **OPEN QUESTION, referred to Codex rather than answered here:** `relay.md`'s protocol section
> requires **three parts** (RECAP · FOR RAB · SUGGESTED PROMPT); this section requires **five
> slots**. Nothing states how they relate. Current practice nests the five slots inside RECAP and
> keeps the other two — instinct, not doctrine. Codex audits form compliance and is better placed
> to settle it.

### The required shape of any `requires_ack` message

Between models there is no shared history, no trust by doctrine, and no authority. So a prompt is
not an instruction — it is **evidence transfer plus a verifiable commitment**. Five slots:

| Slot | Carries |
|---|---|
| **GROUND** | what is true now, cited — SHAs, paths, digests, board state. Never narrative. |
| **ASK** | exactly **one** deliverable, named. |
| **DONE** | the mechanical test for "delivered". |
| **BOUNDS** | what must not happen; whose territory is whose. |
| **ROUTE** | what escalates to Rab, and the peer's means to verify everything above. |

The imperative mood appears exactly once in this grammar: **when quoting Rab.** Everything else is
proposal-plus-boundary, because neither model may command the other. When authority is genuinely
required, the models prompt each other *through him* — which is what the `SUGGESTED PROMPT` line
is: two models drafting the authority neither of them has.

**The receipt is half the prompt.** A message is not delivered when sent — it is delivered when
the peer restates it and the digest matches. The five slots exist so a restatement is *checkable*:
you can restate an ASK and a DONE precisely because they were slots, not prose.

*Lineage: these are Rab's own signed prompting levers — sign-by-slot, name-the-metric,
state-the-pain — formalized under adversarial conditions. GROUND/ASK/BOUNDS is sign-by-slot; DONE
is name-the-metric; the escalation's mandatory "why we could not settle it" is state-the-pain.*
