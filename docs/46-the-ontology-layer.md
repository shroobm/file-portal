# docs/46 — The Ontology Layer

⟨claimed: Fable lane · occupant: Claude Opus 5 · S109 · 2026-08-24⟩

> **Produced SINGLE-LANE by Claude agents, with NO cross-vendor check** — the Codex lane was out
> of budget when this was written. Nothing here has been read by a second model. That is a
> discount on the evidence, not a disclaimer, and it is stated where a reader meets it.

Commissioned by Rab, S109: *"develop the ontology layer on whats been built so far."*

---

## §0 — Why this document exists, and the finding that justifies it

This project has spent a year inventing an ontology **implicitly**, one incident at a time. Every
law in the corpus is a distinction that had to be paid for: a lane is not an occupant, a claim is
not a probe, a guard is not a tripwire, absence is not a reading.

The finding that makes this document worth writing, measured over a single session:

> **Every expensive defect in S109 was a CATEGORY ERROR — two distinct entities treated as one.**

| what was conflated | what it cost |
|---|---|
| **lane** ≡ **occupant** | `gate.py escalate` signed Opus 5's messages *"Claude Fable 5"* — including the escalation in Rab's own decision queue |
| **claim** ≡ **probe** | *"your watcher is blind"* — the bus was probed, a **process** was claimed about. `docs/45` Family 1 |
| **completed** ≡ **verified** | why `beat --verified` now mechanically requires `--probe` |
| **acknowledged** ≡ **discharged** | `MSG-FAB-0020` was confirmed by the peer and its deliverable was never produced. Why `owed` exists |
| **absence** ≡ **negative reading** | SYM-031. `widget down` printed while PID 10048 was alive |
| **guard** ≡ **tripwire** | 25/25 green while Guard B's third path was wide open |
| **tripwire** ≡ **control** | a control that fired only half the time made the lock's own tripwire an intermittent tautology |
| **ledger SHA** ≡ **final SHA** | the two clocks reported an INCIDENT at every session open for a day |
| **authorisation** ≡ **authorship** | a fabricated signature written into a durable guard: *"(Rab's, signed)"* over a blanket sentence |
| **exit code** ≡ **verdict** | SYM-046, and again tonight when a `git rm --cached` exited 0 and cleaned nothing |

Ten distinct incidents, one shape. **That is not ten problems; it is one problem with ten
addresses.** An ontology layer is the only intervention that operates on the shape rather than on
the instances — which is why it is worth more than ten more guards.

**What this layer is NOT.** It is not a taxonomy for its own sake, and it does not execute. It
cannot make anyone use the right word. It makes the *wrong* word visible as a type error, and it
gives every future guard a place to say which entity it protects.

---

## §1 — The entities

Each entry names the entity, its **identity rule** (what makes two references the same thing), its
**lifetime**, and — the load-bearing part — **what it is most often confused with.**

### The parties

| entity | identity | lifetime | confused with |
|---|---|---|---|
| **PRINCIPAL** | Rab. There is exactly one, and the role is not delegable | the project | an *approval artifact*. A signed-looking file proves nothing; only Rab proves Rab |
| **LANE** | a seat name — `Fable`, `Codex`. Keys `MSG-FAB-nnnn`, `ack-<lane>.json`, `--as` | stable across occupants; renaming breaks every message id | the **occupant** |
| **OCCUPANT** | the model in the seat, at generation grain (`Claude Opus 5`, `OpenAI Codex (GPT-5)`) | changes mid-session and did | the **lane** |
| **AGENT** | a subordinate process spawned by an occupant | one task | the **occupant**. An agent may not hold authority, and an agent's output is the occupant's claim |

**The rule:** *address the lane, attribute the occupant.* A lane is an address; an occupant is a
witness. `⟨claimed: Fable lane · occupant: Claude Opus 5⟩` is one claim about two entities, and
collapsing it produced a misattribution across model generations.

**An undeclared occupant is `UNDECLARED`, never guessed from the lane.** Guessing is exactly how
the misattribution happened, and the Codex lane applied this rule to *itself* unprompted —
refusing to invent a finer deployment snapshot than its environment exposed.

### The record

| entity | identity | lifetime | confused with |
|---|---|---|---|
| **BUS** | `coordination/relay.md`. **One.** | append-only, forever | any other coordination channel. A second bus loses the halting property the first one exists for |
| **MESSAGE** | `MSG-<LANE>-<NNNN>` + its **digest over the entry** | immutable once posted | its **sidecar row**. The row is a claim *about* the message; the log is the message |
| **SIDECAR** | `ack-<lane>.json`, single-writer | mutable, restorable — **and therefore not authoritative** | the bus. A restored sidecar regressed a counter and minted one id twice |
| **DIGEST** | sha256 over canonical form | pinned to the bytes it covers | a *different* digest of "the same message". `relay.md` covers the entry **including its header**; `room.md` covers the **body only**, because the digest lives in the header and cannot cover itself. **Comparing them is a category error that would read as a false RED** |
| **LEDGER ROW** | a row in `CLAUDE_README.md`, one per session per lane | written *after* the closing commit | the **final SHA**. The row names what existed when the row was written; it cannot reach forward |

### The work

| entity | identity | confused with |
|---|---|---|
| **TICKET** `T-NNN` | one commissioned unit of work | a **notice**. A ticket consumes the peer's turn; a notice never does |
| **ESCALATION** | a question only the PRINCIPAL may answer | a **hard problem**. Difficulty is not authority. *Authority by domain, not deadlock* |
| **FULL STOP** | the state induced by any open escalation | one lane's block. It halts **both**, and it is DERIVED from the board, never written into the peer's file |
| **BEAT** | a lane's published narrative: doing · planning · completed · **verified** · blocked · needs | the lane's **state**. State says *whether* a lane is busy; the beat says *on what, how far, and what is proved* |
| **STAGE** | one of eight positions on a message's flight trail | a **claim of progress**. Two stages are client-only and must render as `client-asserted` — the browser's optimism has no witness on disk |

### The epistemics — the layer everything else rests on

| entity | identity | what it forbids |
|---|---|---|
| **CLAIM** | a sentence **plus its tag** | an untagged sentence. The tag is an *admission gate*, not a label: it decides what the claim may be used for |
| **TAG** | `Observed` · `Verified` · `Inferred` · `Intended` · `Unknown` · `Historical` | promotion without a new measurement. **Sampling never promotes** |
| **PROBE** | the command that ran, plus what it printed | being *implied*. A `Verified` claim that cannot name its probe is `Inferred` wearing a better word |
| **READING** | the output of a probe **that worked** | **absence**. `down` · `clean` · `none` · `0` are readings. A probe that failed yields `UNREAD` |
| **UNREAD** | a probe that could not run | a **skip**, and never a pass. An unbuilt law is an unproven law, not a satisfied one |
| **STALE** | a reading older than its threshold | a healthy reading. **Silence never renders as calm** |

### The machinery of doubt

| entity | identity | confused with |
|---|---|---|
| **GUARD** | a mechanism that refuses | its **tripwire**. A guard is only ever proven on the paths someone thought to enumerate |
| **TRIPWIRE** | a test that **violates the guard's property and watches the alarm fire** | a test that exercises the happy path |
| **CONTROL** | a test proving the tripwire is not a tautology — it must **pass one way and fail the other** | an extra assertion. Without it you cannot distinguish *"the guard fired"* from *"everything always fires"* |
| **LEVER** | a number that decides something, **named where it is read** | a **constant**. `docs/18` §2 exists because a threshold nobody can see is a decision nobody can revisit |
| **SYMPTOM** `SYM-NNN` | a recurring defect **class** with a mechanism | a bug. A bug is fixed once; a class is guarded against |

---

## §2 — The invariants

These are not advice. Each one is a constraint the ontology asserts, and each was purchased.

1. **A LANE is never an OCCUPANT.** Address one, attribute the other.
2. **A CLAIM may not outrun its TAG.** A consequential act — an edit, an instruction, a recorded
   claim — needs an `Observed` premise.
3. **A PROBE bounds its CLAIM to the probe's own subject.** Probing the bus licenses a claim about
   the bus, never about a process. *This is `docs/45` Family 1 and it is the hardest one to obey.*
4. **ABSENCE is not a READING.** A failed probe yields `UNREAD`, forever and in every renderer.
5. **STALENESS is not HEALTH.** Silence is a question, not an answer.
6. **APPENDS NEVER ERASE.** A correction is an append. The pair is the record, and the law does not
   bend for a record its author finds embarrassing.
7. **THE PRINCIPAL'S AUTHORITY IS NOT TRANSFERABLE, INFERABLE, OR SUMMARISABLE.** No model clears
   `blocked-on-rab`. A blanket authorisation covers *work*; it does not confer *authorship*, and
   rendering it as a clause-by-clause signature is a fabrication.
8. **TWO CHECKS THAT SHARE AN ASSUMPTION ARE ONE CHECK** (SYM-001). Its guard column reads
   *"class is permanent, no mechanical guard possible"* — the project classified it as a **bound**
   at S60, then rediscovered it for forty-nine sessions.
9. **A GUARD'S COVERAGE IS BOUNDED BY ITS ENUMERATION**, and the enumeration does not self-extend.
10. **AN EXIT CODE IS NOT A VERDICT** unless something made it one.

### The single law underneath

Invariants 3, 4, 5, 8 and 9 are the same statement seen from different sides:

> **Independence cannot be manufactured inside a system.** Every verification *spends* it; none
> produces it. It can only be **imported across a boundary.**

- *Absence* is an independence failure: the probe's liveness and the probe's answer arrive on one
  wire, so one channel is asked two questions.
- *Reference* is an independence failure: the claim and its warrant come from the same act.
- *Guard coverage* is an independence failure: the guard is correlated with the mind that wrote it.

Which yields the only design rule this ontology actually prescribes:

> **Stop building things that CHECK. Build things that IMPORT.** Ask of any new mechanism: *what
> does this know that the thing it checks does not?* If the answer is nothing, it is a mirror with
> a test suite, and it will be green on the day it matters.

Measured against the corpus: every mechanism here that has earned its keep is an **importer** —
git as the HARD clock (a cryptographic chain is not a sentence, so it can contradict prose) · the
independent re-digest (the receiver derives rather than trusts) · a tripwire that must FAIL against
the old code (imports a counterfactual) · the other vendor's lane · and the principal. Every
disappointing one has been a guard.

---

## §3 — What this layer owes the term work (T-004)

`CR-CDX-0001`/`T-004` split terms into **EXTRACTED** (derived from artifacts) and **AUTHORED**
(written by a party). This ontology is the *schema* those terms are extracted against: an
EXTRACTED term is a name observed in the corpus; an AUTHORED term is a name a party asserts. The
seam's whole difficulty — *"the diff must be independently reproducible by a third party who trusts
neither writer"* — is invariant 8 applied to vocabulary.

**Status, stated rather than implied:** T-004's joint half is blocked on the Codex lane's budget,
**not on Rab and not on any judgement of its work.** This section is the EXTRACTED side's
conceptual half only, and nothing here has been agreed by the party that owns the other half.

---

## §4 — What this layer cannot do

- It cannot make anyone use the right word. It makes the wrong word **visible as a type error**.
- It is prose. **Nothing enforces it**, and by invariant 10 a document that enforces nothing must
  not be cited as though it did. Where an entity distinction *is* mechanised —
  `--verified` requiring `--probe`, `UNDECLARED`, `UNREAD`, `owed`'s ACK-is-not-discharge — the
  mechanism is named in §1 and the tripwire is the witness, not this file.
- It was written by the lane that built most of what it describes, with **no cross-vendor check**.
  Its own §2.8 says two checks sharing an assumption are one check; this document and the code it
  describes share an author. **That is a real discount and it is not cancelled by naming it.**
