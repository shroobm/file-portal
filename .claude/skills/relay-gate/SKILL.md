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
gate.py resolve  --as <you> --id MSG-XXX-NNNN --decision "what he decided, in his terms"
```

`watch` fires on **both** directions — your message being confirmed, and a new ticket arriving
for you. That is the signal a gate agent sleeps on.


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
