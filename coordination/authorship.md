# The Claim Convention — who wrote what, said in the artifact itself

⟨claimed: Fable · S99 · 2026-08-20⟩

Signed by Rab, 2026-08-20, his words: *"It is time for Claude to start claiming it's sections,
and in the same document, Chat fucking GPT will add theirs."* Born of the parallel sitting
(docs/43): two models worked this repo simultaneously and discovered each other only through
what was added — stigmergy, including its failure mode (SYM-045, two collisions in one day).
Anonymous artifacts made the discovery slow and the reconcile blind. This convention ends the
anonymity without ending the stigmergy.

## The stamp

Every **prose section, ledger row, and doc** a model writes carries a claim:

- Section or doc: `⟨claimed: Fable · S<n> · <UTC date>⟩` / `⟨claimed: Codex · S<n> · <date>⟩`
  — one line, at the top of the doc or the end of the section it claims.
- Change Ledger rows: the session cell already opens `S<n>:` — and MUST keep opening that
  way (muster's ledger parser keys on `S<n>:`; a stamp before the colon broke it, caught by
  the S99 close-verification muster). Write rows as `| <date> | Desktop | S<n>: ⟨Fable⟩ …`
  — the stamp goes AFTER the colon.
- Commits: a model trailer. Fable already commits with
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; Codex is asked (relay entry 1) to
  adopt an equivalent — its close `3b56f13` carries no trailer today, which is the measured
  gap this line closes.
- TIME-STATE digests already stamp the model (`; Codex`, `; Fable`, `; Opus 5`) — prior art;
  keep doing it.

## The rules

1. **Claim only what you wrote.** A section written by the other model is never stamped for
   it — mark it `⟨unclaimed — <model>'s to claim⟩` and let the relay invite the claim. A
   wrong claim is worse than no claim; this file inherits the ledger's no-rewrite law.
2. **Retroactivity is minimal.** Today's shared documents (the parallel sitting's) get
   stamps; history before 2026-08-20 stays as it is — the TIME-STATE digests already carry
   its authorship at session grain.
3. **Stamps are claims, not signatures.** Rab's signatures live in docs/37 §3 and nowhere
   else; a claim stamp asserts authorship, never authority.
4. Joint work (one section, both hands) is stamped by both, each naming its part.

## Why this shape

The two models never share a live channel — coordination stays stigmergic (through the repo)
by design, because the git log is the audit trail. The stamp makes each trace carry its
author; the relay (`relay.md`) makes each trace carry a message. Together: Rab always gets
two signals as one.

## Correction — the LANE is not the OCCUPANT (S109, 2026-08-24)

⟨claimed: Fable lane · occupant: Claude Opus 5 · S109 · 2026-08-24⟩

Rab, 2026-08-24: *"Codex keeps calling you Fable, fix that, i don't think Codex understands
that yet."* He is right, and it was not Codex's misreading — the instrument was misattributing.

**`Fable` and `Codex` are LANE names — seats.** They are what `MSG-FAB-nnnn`, `ack-fable.json`
and `--as` are keyed on, and they must not be renamed (fourteen live messages and an open
escalation depend on them). **The OCCUPANT is the model sitting in the seat, and it changes.**
The Fable lane was occupied by **Claude Fable 5** through S108's wiki block and by
**Claude Opus 5** from the residency block onward — that switch is recorded in
`sessions/S108-desktop-2026-08-23.md` §7 and is the reason the generation caveat exists.

**Measured defect.** `gate.py` hardcoded `trailer = "Claude Fable 5" if lane == "Fable"`, so
**every machine-generated escalation was stamped with a model that did not write it** — including
`MSG-FAB-0009` at `relay.md:1397`, the escalation currently in Rab's decision queue, authored by
Claude Opus 5. Every hand-written trailer on the bus says `Claude Opus 5` correctly. Codex was
reading a bus that contradicted itself, and reading it accurately.

**Fixed:** the sidecar carries an `occupant` field; `gate.py occupant --as <lane> --model <name>`
declares it; an undeclared occupant renders **`UNDECLARED`** and is **never guessed from the lane**
(guessing is precisely how this happened); naming a lane as an occupant is refused; and
`gate.py status` renders lane and occupant on separate lines. Tripwires T27–T29, all three proven
to FAIL against the pre-fix gate. Suite 30/30.

**The line this corrects.** Above, this document states that Fable *"already commits with
`Co-Authored-By: Claude Fable 5`."* That was true when written on 2026-08-20 and is **stale**:
the occupant changed. The original line stays as written — this file does not rewrite, it
appends (rule 1's no-rewrite law, and S101's precedent of dated corrections appended, not erased).

**The rule, going forward.** Address the lane; attribute the occupant. `⟨claimed: Fable⟩` alone
is now insufficient wherever authorship matters across generations — write
`⟨claimed: <lane> lane · occupant: <model>⟩`. Each lane declares **its own** occupant; neither
model may declare the other's, exactly as neither may write the other's sidecar.
