---
name: circle
description: Run one bounded audit Circle — a self-assessment or verification mission that recovers the signed criteria, observes reality read-only, decomposes into independent verification lanes run by subagents, reconciles their evidence, judges findings most-severe-first, gates mechanical fixes apart from semantic changes needing the user's signature, and closes with a durable record. Use this whenever the user asks to audit work against its plan or design, self-assess a build, verify "did we build what we said", run "the Circle" or "a circle" by name, commission an independent review of planned-vs-built-vs-current state, or asks whether finished work met its own criteria — even if they don't say "audit". Not for building new features or fixing a known bug directly.
---

# The Circle — a bounded, independently-verified assessment loop

One invocation = one Circle: a complete journey from commission to closed verdict.
The Circle answers a question; it does not silently become an implementation session.
Its power comes from three habits most reviews skip: recovering what "good" was *defined*
to mean before judging, verifying through independent lanes that don't share your
assumptions, and refusing to blend findings into fixes without an explicit gate.

Born of a real session (File Portal S74, 2026-08-13) where this exact shape caught a
photographed-but-unnoticed UI bleed, a self-created accessibility trap, a fabricated
metric, and two contradictions inside the plan's own text. The method found flaws in the
work AND in the criteria — that dual result is the standard to hold.

## Phase 0 — Substrate

Before trusting your own reasoning, verify the ground it stands on. If the project has a
bootstrap protocol (memory index, session ledgers, a symptom/failure index, integrity
checks), run it first and read the failure index. A defect rediscovered because you
skipped the index is a process failure, not bad luck. If no such protocol exists, at
minimum: confirm the working tree state, the branch, and the last recorded milestone
before making any claim about "what was built."

## Phase 1 — Intent

Restate the commission as one or more *falsifiable questions* ("did the implementation
match the design?", "did the design satisfy its own criteria?") and name the deliverable
class out loud:

- **Assessment** (default): the deliverable is findings. Touch nothing.
- **Change**: only if the user explicitly commissioned fixes. Even then, the gate in
  Phase 7 still separates what you may fix from what needs their signature.

An assessment that quietly starts editing has failed the commission even if the edits
are good.

## Phase 2 — Reference

Recover what "good" means from the record, never from memory: plans, charters,
acceptance criteria, signed decisions, prior session closeouts, git history. Quote the
governing sentences verbatim into your working notes — judgment against a paraphrase is
judgment against nothing.

While reading, collect the criteria's own internal contradictions. They are findings of
the first rank: a plan that bans "any motion longer than 400 ms" while its own demo
ships a 2.6 s loop has a defect in the *document*, and only the human can arbitrate it.
Ask "what did we previously say good means?" — never "does this look good?"

## Phase 3 — Observe

Inspect reality read-only: the running system, the source, screenshots the user
provided, live state. Log **anomalies, not defects** — an anomaly is an observation that
doesn't trivially fit the current model ("survival 1.000 beside a fail badge") and may
turn out to be correct behavior, a labeling problem, or a real bug. Deciding which is
Phase 5–6's job, on evidence.

Seed your own suspicions NOW, before delegating — you will hand them to the lanes as
hypotheses to confirm *or refute*, and you must be able to show they predate the
verdicts.

## Phase 4 — Decompose and delegate

Split verification into 2–4 independent lanes with non-overlapping scopes (e.g.,
plan-vs-built · element provenance · law/honesty sweep). Then move to altitude: design
the investigations, assign them, and do not duplicate them yourself.

Each lane brief must be:

- **Self-contained** — subagents start cold. Absolute paths, relevant SHAs, the governing
  laws quoted, the exact files in scope.
- **Double-loaded** — BOTH your seeded suspicions (to confirm or refute with evidence)
  AND an open sweep of the lane's whole territory. Targeted checks alone only find what
  you already suspect; the open sweep is where the dead element and the unwired tripwire
  turn up.
- **Verdict-free** — hand over the anomaly, not your guess about it.
- **Honesty-normed** — instruct "do not soften; rank most-severe-first; cite file:line;
  every finding needs a concrete failure scenario."
- **Methodologically different** where possible — two checks that share an assumption are
  one check. A byte-diff audit, a provenance trace, and a law sweep can each catch what
  the others structurally cannot.

Read-only lanes: give agents explicit "report findings, edit nothing" instructions.

## Phase 5 — Reconcile

Merge lane reports as they arrive. Convergence between independent lanes upgrades a
finding's confidence; conflict between lanes triggers another investigation cycle —
never average a disagreement away. Relay interim results to the user as lanes complete
(clearly labeled per-lane and final-for-that-lane), and never predict a pending lane's
results.

## Phase 6 — Judge

Rank findings most-severe-first using a graded vocabulary — a flat "issues list" hides
the difference between a broken law and an awkward label:

- **WITHSTOOD** — checked and clean (say so; absence of findings is a finding). *The word "HELD" is
  retired as a verdict (S108 rule 3, built S157): it meant both* blocked *and* withstood *in one release.*
- **BLOCKED** — the check could not run or could not reach its evidence; never a statement of cleanliness
- **VIOLATION** — breaks a stated law or criterion
- **EROSION** — the letter holds but the meaning is being spent thin
- **TENSION** — the criteria contradict themselves; human arbitration required
- **BLEED** — unintended interaction between components/surfaces
- **HONEST-BUT-CONFUSING** — true data, misleading presentation
- **FRAGILE** — correct today by accident of implementation
- **DEAD** — declared but unwired

Findings in your own recent work are first-class and lead the report — self-critique
that spares the self is worthless, and the user can tell. Every finding carries
file:line evidence and a concrete failure scenario.

## Phase 7 — Gate

Classify every actionable finding before anything is touched:

- **Mechanical** — the desired state is already unambiguous under existing signed
  criteria (a missing entry in a hide-list, an unescaped value, dead code). May be
  implemented *only if* the commission included change.
- **Semantic** — alters meaning, doctrine, thresholds, labels users have learned, or
  anything previously signed. Escalate with a recommendation; the human signs. Never
  implement these on your own authority, even when the fix seems obvious.
- **Evidence-insufficient** — loop back to investigation; do not guess.

Closing with zero mutation is a *success mode* of the Circle, not an incomplete one.

## Phase 8 — Close

Write the durable record in the project's own conventions (ledger row, closeout,
findings doc, memory note — whatever the project uses; at minimum one findings document
the next Circle can recover as its Phase-2 reference). The record is part of the exit
condition: recursive self-correction only works if models persist between Circles.

Then deliver the synthesis: direct answers to the Phase-1 questions FIRST, then the
ranked findings, then the gate split (what's mechanical, what awaits signature), then
what the next Circle inherits.

## The three rules imported at S108 (The Atlas Plan, path 11 — signed S108, built S157 E14, 2026-09-15)

1. **Frozen-commit immutable audit records.** A Circle's record is written against a named commit and never
   edited into a different verdict afterwards: a repair lands as a NEW commit and is re-audited by the next
   Circle. "Circle-003 cannot be converted into a pass retroactively." A closed record that later reads wrong
   gets a dated correction appended, never a rewrite.
2. **The aborted-lane law.** A lane that does not return — killed, timed out, out of budget, or returning
   nothing — is named in the record as NON-EVIDENCE for its scope, never silently absorbed into the others'
   findings and never counted as "no findings". Its scope is either re-run or reported as UNREAD.
3. **"HELD" is retired as a verdict word.** It meant both *blocked* and *withstood* in the same release of
   the atlas. Phase 6's vocabulary says **WITHSTOOD** (checked and clean) or **BLOCKED** (the check could not
   run); any other sense of "held" (a pipeline bundle in `held/`) is a noun of the system, not a verdict.

The tracked copy of this skill lives at `.claude/skills/circle/SKILL.md` in the File Portal repo; the
user-level copy at `~/.claude/skills/circle/SKILL.md` is a mirror of it, and `selftest.sh` beside the tracked
copy asserts the three rules are present and the retired word is absent from the verdict vocabulary.

## The Cycle inside the Circle

Effort allocation oscillates while the Circle runs: research rises with uncertainty,
contradiction, and unexplained observations; implementation is a *permissioned
consequence of epistemic closure* — confidence × authority × reversibility — never
"the next phase." A new contradiction discovered mid-implementation sends you back to
research without shame. Controller involvement concentrates at the boundaries (framing,
reconciliation, judgment, the gate); the middle belongs to the lanes.

## Looping

Each invocation is one Circle. For a recurring cadence, compose with the loop/schedule
facilities available in the session (e.g., a periodic `/circle <standing commission>`);
every recurrence starts at Phase 0 and inherits the previous Circle's closed record as
reference material. Do not carry an open Circle across invocations — close it, even if
the closure is "evidence insufficient, next Circle starts at Phase 3 with X."
