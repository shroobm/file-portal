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
