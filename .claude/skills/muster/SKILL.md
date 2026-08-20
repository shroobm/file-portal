---
name: muster
description: Open a File Portal session honestly — run the mechanical open (identity from the ledger, both clocks, live state, pinned closeout ref), then inherit the previous session at `Historical`, promote by re-measurement only what today will touch, sweep the symptom index, load the standing orders, and record intent BEFORE work in a new sessions/ closeout. Use at the start of any session in this repo, whenever the user says MUSTER, when asked "where were we", before touching the pipeline, the widget, the vault, or a held bundle, and before any session whose work will be recorded. Not for closing a session and not for auditing finished work (that is /circle).
---

# The MUSTER — how a File Portal session opens

One invocation = one session open, from cold start to a session that has recorded what it
intends to do before doing any of it.

This project's expensive failures were never lost code. They were **claims that outran their
evidence**: a count quoted from a document that had moved, a guard trusted because it was
green, a structure generalised from two sampled cells, a "current state" inherited from a
closeout written the day before. The open is where those enter, so the open is where they get
tagged.

**The mechanical half is a script. This file is the judgment half.** Nothing derivable is
written by hand (docs/21 §3), and nothing requiring judgment is faked by a grep (docs/21 §6).

## Run this first

```bash
bash .claude/skills/muster/open.sh
```

Exit 0 = the mechanical half is clean. **Exit 1 = an incident: reconcile it before any work.**
Paste the card into the reply **verbatim**. A summary of the card is a proxy for the card.

If it reports a **collision** — the derived session number is already named in tracked files —
stop and resolve it with Rab. It means either this session is misnumbered or an earlier one
wrote under a number it did not own; from here those are indistinguishable, and guessing
produces a record that lies about who did what.

## The tag law — the spine of the whole session

Every claim carries exactly one tag, and **the tag is an admission gate, not a label**: it
decides what the claim may be used for. Prices are docs/21 §1.

| Tag | Means | Admission price |
|---|---|---|
| **Observed** | I saw it, this session, with my own tool call | the command and what it printed |
| **Verified** | Observed **and** cross-checked by a differently-shaped second method | both, and why the second can fail independently |
| **Inferred** | reasoned from evidence, not witnessed | the evidence, and what would falsify it |
| **Intended** | designed to be true, not yet exercised | who can exercise it |
| **Unknown** | identified as unresolved | what would resolve it |
| **Historical** | was true at a stated time | the date, always |

Four rules follow, and they bind for the **whole session**, not just the open:

1. **A consequential act needs an `Observed` premise.** Consequential = an edit, an instruction
   to Rab, or a recorded claim. If the premise is `Inferred`, promote it first — print it,
   render it, look at it — or say the tag out loud in the reply.
2. **Sampling never promotes.** Printing 2 of 15 cells yields `Inferred` about 15, permanently,
   however strong the pattern looks. *(S78 §10.5: 13 "phantom empty columns" were the matrix's
   source columns, carrying 418 `•` marks. Two cells were inspected; the edit preceded the
   look.)*
3. **A number is re-measured, never quoted.** Every count S78 wrote was wrong within two
   commits (93→77→76; 13/13→19/19→18/19→21/21).
4. **A failed probe never renders as a negative observation.** If a check could not run, say
   UNREAD. `down`, `clean`, and `none` are readings, and a reading needs a probe that worked.
   *(Paid for by `open.sh`'s own first run: MSYS rewrote `/FI`, `tasklist` errored to stderr,
   the error was swallowed, and the card said `widget down` while PID 10048 was alive.)*

`Verified` is expensive on purpose. Two checks that share an assumption are one check (SYM-001).
**Downgrading a tag is free and expected** — it is the system working, not a failure.

## Phase 2 — Inherit, and stamp it all `Historical`

Read, and carry each item with the date it was true:

- the newest Change Ledger row (the card names it);
- the previous closeout `sessions/S<N-1>-*.md` — **§18 Next Entry Point** first, then §10 Known
  Failures, then §17 Current State;
- `SYMPTOM-INDEX.md`.

**Nothing read here may be used as `Observed`.** §17 is `Historical` by its own contract and is
routinely false by morning: on 2026-08-15 S78's §17 read *widget down · bench down* while both
had been up since 12:59. A session that opens on §17 opens on a picture of yesterday.

## Phase 3 — Promote only what today will touch

For each inherited fact this session intends to **act on**, re-measure it now and cite the
command. Everything not promoted stays `Historical` and **is not actionable**.

The cheap battery, by what is in scope:

| In scope | Promote with |
|---|---|
| observability / any closeout claim | `observability/acceptance.py`, then `glass_detector.py --since <pinned SHA>` |
| the widget | `cargo fmt --check` → `cargo clippy --all-targets -- -D warnings` → `cargo test`; the installed exe hash is on the card |
| a held bundle / the bench | the body sha and `undo_depth` from the bundle, before the first zone is opened |
| the pipeline | the card's live rows; `.gpu-lock` and `query user` before ANY GPU work (law 8 — the seat may be his brother's) |
| the receiver | the card's thinkpad row; anything deeper needs the ssh channel, and `UNREAD` is the honest answer when it is asleep |

## Phase 4 — Sweep the index, then step on the guards

Name the `SYMPTOM-INDEX.md` rows that intersect today's intent. **A defect rediscovered is a
MUSTER failure, not bad luck** (docs/21 §5 rule 4).

A row marked `fixed` is a `Historical` claim about a guard. If today's work depends on that
guard, **step on it** — violate the property and watch the alarm fire. A guard nobody has
watched fire is a proxy with a reputation (docs/32 §5).

## Phase 5 — Standing orders

State these as in force, each with its trigger, because they bind *after* the open:

- **Verify before instruct** — any "click X / do Y" is checked against current source first,
  never recalled. The ⚡ tile is a drag target; the watcher's control is the titlebar ⏻.
- **Read the page before editing it** — at the bench, read the bundle markdown Rab is reading,
  and look at the rendered page *before* the write, not after.
- **Adoption is Rab's hand** — build → print SHA-8 → he copies and launches (MSIX ghost laws).
- **One lab process on the card, ever** — check `nvidia-smi` / `.gpu-lock` before any GPU work.
- **Kill process trees**, never single PIDs. **Never chain GPU work with `;`** (SYM-021).
- **The link fence is non-negotiable** wherever an LLM touches markdown.
- **Repo markdown is CRLF** — slice it with `head`/`tail` only; `sed`/`awk`/`grep` strip CR,
  and a bare `grep` cannot even see them (SYM-029; `grep -U` can).
- **A status sentence to Rab carries its probe** — the command and the output line it rests on,
  in the reply, at the moment of the claim. Three consecutive sessions an inference reached him
  dressed as an observation, and every one was a mid-work status sentence, never a closeout:
  S79 `.gpu-lock` "already exists" (untested), S81 a hung run called "healthy" off a process
  *name* (it was ollama's own engine), S82 "thermal" without a thermometer. The tag law lives or
  dies in live sentences; the closeout only performs the autopsy.
- **A guard born today gets its tripwire today** — docs/32 §6 has held five sessions running:
  the defect moves into whatever was built to enforce the rule (S79 seven-for-seven, S81's
  cache traps inside the instrument obeying the document that names them, S82's reference that
  was itself the forbidden single measurement). `selftest.sh` guards the open;
  `backend_parity_selftest.py` guards the instrument. A new guard without a test that violates
  its property is a proxy with a birth certificate.
- **Every measured number obeys `docs/34`** — the measurement language. Name the numerator and
  the denominator; never blend prefill with decode or cold with warm; give `n` and a spread; a
  ratio prints both its sides; a percentage prints its base; a duration nobody reported renders
  `UNREAD`, never `0.0`. The tag says what kind of claim it is, `docs/34` says what it counts, and
  a number needs both. *(S79's "+27 %" was unusable at S80's open not because it was wrong but
  because the sentence never said what had been counted.)*
- **Cookies get logged before other work** — header, ledger entry, and the TIME-STATE mirror.
- **The relay is carried at open, answered before close** (S99, Rab's convention: "two signals
  as one") — read `coordination/relay.md`'s newest entry addressed to your model and carry its
  FOR RAB text + SUGGESTED PROMPT to Rab in the first reply, attributed to the other model;
  write your own entry back (**UTC**) before the close, and claim what you write per
  `coordination/authorship.md`. Carry only what your lane has not carried before.
- **On any deep or ambiguous commission, `/echo` before interpretation** (item 10, S98) — and
  what his word confirms joins the lexicon.

## Phase 6 — Commission, and pin it before you know the outcome

Write `sessions/S<N>-<machine>-<YYYY-MM-DD>.md` **now**, before work, containing:

- **§1 Session Intent** — Rab's commission in his words, one sentence, and *left unedited for
  the rest of the session*. The gap between intent and outcome is itself a finding.
- **§2 Starting State** — the `open.sh` card, verbatim.
- **the pinned `--since <SHA>`** the closeout ritual will use.

Then commit it as the session's opening commit (`CLAUDE_README.md` §2 already requires an open
plan commit).

This is docs/28's chokepoint — *recording precedes action* — applied to the session itself, and
it is the phase that does the most work:

- docs/21 requires §1 to be *"written before work begins and left unedited afterward."* All
  **12 of 12** existing closeouts were first committed in their own **closing** commit, so
  intent has always in practice been authored by someone who already knew the outcome. Creating
  the file at open makes the requirement checkable: `git log --diff-filter=A` on the file must
  be the opening commit, and §1 must be byte-identical at close.
- Pinning `--since` before any result exists means the ref cannot later be chosen to suit one.
  *(S78 §10.1 picked it at close by `len(diff) > 500` and shipped a green report over a red
  suite.)*

## The close — the other end of the same contract

Not this skill's job to perform, but the open sets its terms, so state them at open:

1. The closeout's remaining core sections (§7, §8, §10, §15, §18) — six core sections, always,
   including for an aborted session, where one honest line is a valid closeout.
2. `git diff --name-only <pinned SHA>..HEAD` — every changed file accounted for in CHANGELOG or
   the ledger row.
3. `glass_detector.py --since <pinned SHA>` — every key it names leaves the session either
   rendered or dispositioned. Use the uv interpreter; bare `python` is the Store stub and exits
   49.
4. Ledger row (≤80 words) as a **separate follow-up commit** — never `--amend`, which orphans
   the SHA you just wrote.
5. Both clocks advanced together; §1 unedited; **no artifact carries a session number other
   than this session's**.
6. **The close pushes** (`git push`, after the ledger row). An unpushed close is how the
   2026-08-16 fork grew 52 commits deep: the ThinkPad numbered its sessions from the last row
   it could SEE. The open's origin row shows the backlog; the close is where it goes to zero.

## What this cannot see

A floor, not a proof — state these rather than let a clean card imply them:

- It cannot verify Rab's intent, only record it.
- It cannot see the ThinkPad when the ThinkPad is asleep, and says `UNREAD` — never `clean`.
- It cannot detect a lie in an inherited closeout. It can only refuse to promote one.
- It is **guidance**: a skill fires when invoked. A `SessionStart` hook calling `muster.sh` is
  the enforcement tier and is currently off, by Rab's standing choice.
- The collision check greps tracked text; a compressed asset can produce a spurious hit, and a
  human decides which hits are real.

## Tripwires

```bash
bash .claude/skills/muster/selftest.sh
```

Fifteen cases, each violating the property its guard stands for: out-of-order ledger rows, a
malformed newest row, a TIME-STATE stripped of its count beside a plausible decoy, a non-git
repo, a SHA that is not the ledger's, a far-future session number planted in prose, a failed
process probe, an unreachable receiver, a ThinkPad row planted mid-table with a higher session
number (the lane rule, born of the 2026-08-16 fork), and a forked / behind-only / ahead-only
origin (the origin rule, same birth). **Case 0 is a positive control** — without it the
suite cannot distinguish "the guard fired" from "everything always fires", which is the shape
of the tautology S78 shipped in this exact position.

Run it when `muster.sh` or `open.sh` changes, and whenever a clean card is about to be trusted
with something expensive.
