# 21 — The Session Closeout Contract

*Rab's commission, 2026-08-09, drafted from the receiver (Linux) lane. This document defines how
every File Portal session ends. It exists because the project's expensive failures were never
lost code — they were lost **knowledge**: a defect rediscovered, an assumption re-litigated, a
session that cold-started and re-fought a settled battle.*

---

## 0. The premise

**The session is provenance, not the unit of truth.**

A session number answers *when* and *who*. It must never be the only key under which knowledge is
filed, because the future reader does not know which session to look in — they know only what the
system is *currently doing wrong*. Knowledge filed by session is knowledge retrievable only by
someone who already knows the answer.

The durable objects are four:

| Object | Question it answers |
|---|---|
| **Decision** | why is it this way, and what was rejected |
| **Change** | what is materially different now |
| **Finding** | what did we learn about reality |
| **Failure** | what did it look like when it was wrong |

Each carries an **epistemic status**. Sessions come and go; these four outlive them.

## 1. Epistemic status — the vocabulary

Every claim in a closeout carries exactly one tag. **The tag is part of the claim; an untagged
claim is not a claim, it's prose.**

| Tag | Means | Admission price |
|---|---|---|
| **Observed** | I saw it happen, this session, with my own tool call | cite the command and what it printed |
| **Verified** | Observed **and** independently cross-checked by a second, differently-shaped method | cite both, and say why the second doesn't share the first's assumptions |
| **Inferred** | reasoned from evidence, not witnessed | state the evidence and what would falsify it |
| **Intended** | designed to be true; not yet exercised | say who can exercise it |
| **Unknown** | identified as unresolved | say what would resolve it |
| **Historical** | was true at a stated time; may not be now | carry the date, always |

**The cardinal rule: never promote inference to fact.** An `Inferred` claim does not become
`Observed` because it was written down confidently, because it survived a session, or because it
sounds right. Promotion happens only by producing the evidence the higher tag charges.

**Verified is expensive on purpose.** S60's lesson: a fake Marker that held the same assumption
as the code confirmed a broken merge. Two checks that share an assumption are one check. If the
second method can't fail independently, the claim is `Observed`, not `Verified`.

**Downgrade is free and expected.** A tag you cannot pay for gets lowered, silently, without
apology. Lowering a tag is the system working.

## 2. Two tiers — because a ceremony that fails under load fails when it matters

Eighteen sections per session will be skipped on the night it matters most. This is not a
hypothetical: `CLAUDE_README.md:193` records that the arc's power cuts *"kept ending sessions
before close-out."* So the contract is tiered.

**CORE — mandatory, every session, no exceptions, including aborted ones.** Six sections. If the
session died mid-flight, the core is written from whatever is true at the moment of death.

- §1 Session Intent
- §7 Implementation Delta
- §8 Decision Ledger
- §10 Known Failures
- §15 Symptom Signatures → **into the index**
- §18 Next Entry Point

**EXTENDED — required when the session shipped code, changed a contract, or touched anything
irreversible.** The remaining twelve. A docs-only or investigation-only session may omit them.

**The abort clause:** a session that cannot write its core writes a single line — *"aborted at
<state>, nothing shipped, next entry point unchanged"* — and that line is a valid closeout. An
honest stub beats a missing ceremony, and both beat a fabricated one.

## 3. Derived vs. authored — do not hand-write what a command can produce

Half of these sections are mechanically derivable. Deriving them costs one tool call and cannot
lie; authoring them costs judgment and can. **Never author a derivable section** — the same rule
that governs the memory library.

| Section | Source |
|---|---|
| 2. Starting State | the MUSTER output, verbatim |
| 3. Development Chain | `git log --oneline <last ledger SHA>..HEAD` |
| 5. Observable Contract | the *census* half only: `python observability/glass_detector.py --since <last ledger SHA>` (docs/29 §5.1 — the keys this session introduced). The items themselves stay authored: a command can prove a measured value reaches nobody, never that a human should care |
| 7. Implementation Delta | `git diff --stat <last ledger SHA>..HEAD` + one line of intent per file |
| 9. Evidence | the actual command transcripts — quoted, not paraphrased |
| 17. Current State | live reads (unit state, vault tip, staging, receipts, exe hash) |

Everything else is authored, and authored sections are where tags matter most.

## 4. The eighteen sections

| # | Section | Tier | Holds |
|---|---|---|---|
| 1 | **Session Intent** | core | what this session set out to do, in one sentence, written *before* work begins and left unedited afterward — the gap between intent and outcome is itself a finding |
| 2 | **Starting State** | ext | MUSTER output; the clocks; what was already broken on arrival |
| 3 | **Development Chain** | ext | commits in order, each with why it exists — the narrative git can't hold |
| 4 | **Analogue + Boundary** | ext | the real-world system this imitates and **exactly how far** ("Okular's search, outline, thumbnails — *not* its annotation model"). The boundary is what stops a human reporting an unbuilt feature as a defect |
| 5 | **Observable Contract** | ext | 3–5 things a human should now see, each checkable in under a minute, each with its failure condition stated in advance. **An item that cannot fail is not an item**. Then run the detector (§3): every key it names leaves this session either rendered, or recorded in `observability/dispositions.json` with a disposition and a reason — docs/29 §5.4, same commit, because a later sweep only ever finds this class. *(Whether this section moves to **core** is docs/29 §8.4, unsigned. Today a session that ships no code may skip it, which is exactly how a stored-but-unshown value survives a closeout)* |
| 6 | **Deliberate Divergences** | ext | where we knowingly differ from the analogue or from the obvious approach, and why — so intent is never re-reported as bug |
| 7 | **Implementation Delta** | core | what is materially different: files, behaviours, contracts. Derived, then annotated |
| 8 | **Decision Ledger** | core | each decision, its rationale, **what was rejected and why**, and who signed it. Rejected options are the expensive half — they're what stops the next session re-proposing them |
| 9 | **Evidence** | ext | the transcripts. Tagged. Quoted verbatim, never summarized into confidence |
| 10 | **Known Failures** | core | what is broken *right now*, stated plainly, including anything this session broke and did not fix |
| 11 | **Unproven by Machine** | ext | claims only human hands can exercise — standing assignments, listed, not buried in prose |
| 12 | **Uncertainty Register** | ext | every `Unknown`: what we don't know, why it matters, what would resolve it. **An empty register on a hard session is a red flag, not an achievement** |
| 13 | **Dependencies / Assumptions** | ext | what this rests on that we did not verify — library behaviours, platform quirks, another machine's state. Each one is a future failure with a fuse |
| 14 | **Regression Surface** | ext | blast radius: what else touches what changed, and what would have to be re-checked if this is wrong |
| 15 | **Symptom Signatures** | core | for each failure: **what the system does when it's wrong**, written for a reader who has the symptom and not the cause. Goes into the index (§5) |
| 16 | **Recovery / Return Log** | ext | when a human found the defect: what they saw, in their words, and how long it took to reach the cause. This measures whether the index is working |
| 17 | **Current State** | ext | live state at close. Derived. `Historical` the moment it's written — tag it so |
| 18 | **Next Entry Point** | core | the exact first action of the next session: file, command, decision awaiting a signature. Not "continue Stage D" — *"run X, expect Y, if Z then …"*. This is the anti-cold-start guarantee and it is the single most valuable line in the document |

## 5. The symptom index — the load-bearing artifact

**`SYMPTOM-INDEX.md`, repo root, single file, fixed location, forever.**

Everything else in this contract is exhaust. The index is the product. It is the only section
whose absence is unrecoverable, because it is the only one designed for **backward retrieval**:

> A future engineer or Claude arrives holding a symptom — *"page numbers are wrong above the
> first slice"* — and no idea which session produced it. They grep the index by what the system
> is doing, and land on the cause, the guard, and the session that paid for it.

Rules:

1. **Keyed on the symptom, not the cause.** The row's first column is what you'd *notice*.
2. **Terse and greppable.** One row, one failure. This file is an index, not a narrative — the
   narrative lives in the session's closeout, which the row points to.
3. **The session number is always present** — provenance and history matter — but it is never the
   retrieval key.
4. **Read at session start.** MUSTER opens the index. A defect rediscovered is a MUSTER failure.
5. **Append-only in spirit.** A fixed defect is marked `fixed` with its guard, never deleted —
   the recurrence is the thing you're guarding against, and a deleted row can't warn anyone.
6. **A row's status carries an epistemic tag** like any other claim.

## 6. Anti-patterns — how this contract dies

- **Compliance collapse.** Eighteen sections becomes zero sections under pressure. Mitigation:
  the core is six, and the abort clause is always available.
- **Tag decoration.** Everything gets labelled `Verified` because it reads better. Mitigation:
  the admission price in §1. No citation → downgrade, on sight.
- **Prose mass mistaken for knowledge.** This project already writes very dense ledger rows.
  A 500-word paragraph is not retrievable. The index must stay terse.
- **Duplicating the repo.** Sections 3, 7, 9, 17 overlap git and CHANGELOG. They are **pointers
  and annotations**, never copies.
- **A write-only index.** If nobody reads it at open, every closeout was wasted. §5 rule 4 is the
  whole return on this investment.
- **Self-verifying textual checks.** *(Found by this document's first use, S67.)* Do not write an
  Observable Contract item that greps the closeout for its own epistemic tags. It cannot work: a
  grep cannot distinguish a claim from a discussion of claims, and every refinement of the pattern
  adds one more instance of that pattern to the file being searched. Three attempts failed in
  succession on S67. **An epistemic property is checkable only by a reader — route it to §11, not to
  a command.** Mechanical checks belong on mechanical facts (a count, a hash, a service state, an
  ancestor test); judgment checks belong to human hands. Confusing the two is how a check comes to
  share the blind spot of the thing it checks (SYM-001).

## 7. Where closeouts live

*(Gap found by the first real use of this document, 2026-08-09 — the spec defined the content and
forgot the location. Recorded rather than quietly patched, because a spec that needed a fix on
first contact is a finding about specs.)*

**One file per session: `sessions/S<N>-<machine>-<YYYY-MM-DD>.md`.**

The `CLAUDE_README.md` Change Ledger keeps its existing one-row-per-session form and gains a
pointer to the closeout file. Rationale: the ledger is already an index — dense, chronological,
and read top-to-bottom on activation. Pouring eighteen sections into it would make the shared
brain unreadable and trip §6's "prose mass mistaken for knowledge" anti-pattern on the very first
session. Index stays terse; narrative moves out; retrieval stays cheap.

Session numbers are **global and sequential across both machines**, not per-machine — verify the
next one with `grep -oE '\bS[0-9]{1,3}\b' CLAUDE_README.md | sort -t S -k2 -n | tail -1`, never by
assumption.

### The ledger row cap: 80 words

**A Change Ledger row may not exceed 80 words in its milestone column.** Not a guideline — a
number, so it can be checked:

```bash
sed -n '<line>p' CLAUDE_README.md | awk -F'|' '{print $4}' | wc -w
```

A row carries only: what shipped (one clause), what is open and whose it is, and **the pointer to
the closeout file**. Everything else — the narrative, the evidence, the divergences, the defects
found — lives in `sessions/`, which is the entire point of moving it there.

*Why a hard number:* S67 wrote this document's "prose mass mistaken for knowledge" anti-pattern
(§6) and then produced a **499-word** ledger row — 2.4× the S66 row it had criticized hours
earlier — and proposed to "watch whether S68 is shorter." An aspiration that survived its own
author by ninety minutes is not a constraint. The row was cut to comply. Rows written before this
cap stand as history; do not retro-edit another session's row.

If a row cannot be said in 80 words, that is evidence the closeout file is doing its job, not
evidence the cap is wrong.

## 8. What "done" looks like

The contract is working when: a defect is retrieved from the index rather than rediscovered; a
session's first action comes from §18 rather than from re-reading the codebase; and a human
report ("the page numbers are lying") reaches its cause in one grep.

It is failing when: closeouts are long and the index is empty; tags are uniformly high; or the
next session opens by asking "where were we?"
