---
name: echo
description: Ground a deep or ambiguous commission BEFORE interpreting it — run the mechanical full-context sweep (repo, docs, register, symptom index, live pipeline state, term hits), map Rab's words onto project terminology via the append-only lexicon with citations, then render 2–4 readings + a concrete preview of the primary + one delta line per alternate, and STOP for his word. His affirmation commits ONE reading; only then does work proceed and the confirmed mappings join the lexicon. Use whenever a commission is deep, ambiguous, multi-session, or high-consequence (a build, a GO, anything touching pipeline/vault/adoption), whenever Rab asks "what do you think I mean", and whenever an interpretation would otherwise be chosen silently — doubt about whether a prompt is ambiguous IS the trigger. Not for trivial, mechanical, or unambiguous asks (those just execute), and never as a stall.
---

# The ECHO — how a commission is grounded before it is spent

Signed by Rab, 2026-08-20, his words: *"make those futures instance to tell me WHAT I THINK I
MAY MEAN, and then show me what that would look like, to gauge alignment! SO I CAN RE EVALUATE
MY PROMPT PRIOR TO COMMITTING TO IT"* — and Reading B's GO the same day: the full-context
sweep, the terminology map, and accuracy grounded in the git/repo and local desktop files, not
in the instance's recall. Register signature: docs/37 §3 item 10. Library twin:
`prompt-echo-protocol` in the memory library (the doctrine; this skill is its mechanization).

**The failure this skill exists inside:** interpretation drift — a reading of Rab's intent
chosen silently and discovered only after the work spent it (the fourth ask took four
attempts; S97's think-tank commission needed a scope-interpretation section written on its
behalf). The echo moves the alignment check BEFORE the spend. It is the read-side twin of the
docs/37 §3 signature register: the register makes his **decisions** explicit after options are
framed; the echo makes his **intentions** explicit before work begins.

**The mechanical half is a script. This file is the judgment half.** `sweep.sh` produces
values (never checkmarks — docs/32's proxy-substitution law applies here too); this file says
what to do with them.

## Phase 0 — the proportionality gate

Ask: is this commission **deep** (multi-step, multi-session), **ambiguous** (the prompt
supports more than one materially different execution), or **high-consequence** (a build, a
GO, a signature, anything touching the pipeline, the vault, adoption, or `held/`)?

- **No to all three** → do NOT echo. Execute. The echo must never tax trivial work — that
  failure mode would kill the protocol faster than drift would.
- **Yes to any** → continue to Phase 1.
- **Unsure** → that doubt IS the trigger. Continue to Phase 1.

An explicit slot-reference signature ("item 6: P-1 host (a), report-only") is by construction
unambiguous — record it and execute; that is the register working, not an echo case.

## Phase 1 — the mechanical sweep

```bash
bash .claude/skills/echo/sweep.sh <term> [term ...]
```

where each `<term>` is a load-bearing word or phrase from the commission (lowercase, one word
or a short quoted phrase). The script prints the CONNECTED STATE (ledger tip, levers, pipeline
counts, register open items, symptom tail, lexicon size) and, per term, hit counts + top file
paths across the repo AND the memory library. UNREAD rows mean the probe failed, never that
the state is clean — same discipline as muster's open card.

## Phase 2 — the terminology map

For every load-bearing word in the commission, in this order:

1. **Lexicon first** — `.claude/skills/echo/lexicon.md`. A confirmed mapping is citable as-is.
2. **Then the sweep's term hits** — read the top hits enough to name the project term the word
   lands on, with a `file:line` or `docs/NN §x` citation.
3. **Then declare UNMAPPED** — a word with no lexicon entry and no convincing hit is rendered
   `UNMAPPED`, never guessed. An unmapped load-bearing word is itself evidence the prompt
   needs his re-evaluation — say so.

The map row shape: `<his word> → <project name> (<citation>)`.

## Phase 3 — the readings

Two to four interpretations, primary first, **one sentence each**, each carrying what in the
repo supports it. Readings must be materially different executions, not paraphrases of one.
If only one reading honestly exists, say so and skip to Phase 6 with that single reading — the
echo still shows the preview, because "I understood you" and "you said what you meant" are
different facts and the preview tests the second.

## Phase 4 — the preview

For the **primary reading only**: what executing it would look like. A deliverable skeleton, a
plan outline, a mocked output slice, the first artifact fragment. Cheap enough to throw away,
concrete enough that misalignment is **visible** — a wrong preview is the protocol succeeding,
not failing.

## Phase 5 — the deltas

One line per alternate reading: what it would change downstream — different files touched,
different build order, different cost, different risk (name the live levers when they bite,
e.g. `audit=enforce` means a gating change parks books day one).

## Phase 6 — render the card and STOP

```
══════ ECHO · <UTC timestamp> ══════
YOUR WORDS       "<the load-bearing fragment, verbatim>"
TERMINOLOGY      <word> → <project name> (<citation>)        [one row per word; UNMAPPED declared]
CONNECTED STATE  <the sweep's values, condensed to what bears on this commission>
READING A (primary)  <one sentence>   [grounded: <citation>]
READING B            <one sentence>   [grounded: <citation>]
PREVIEW (A)      <the skeleton / mock / slice>
DELTAS           B: <one line> [· C: <one line>]
══════ your word commits one reading ══════
```

Then **STOP. No work commits before alignment.** This is the one place the skill overrides the
default bias to proceed: the entire point is that his word, not an inference, commits the
reading. Waiting here is the work.

## Phase 7 — on his word

1. Any affirmative on a reading commits that reading. A redirect is a new prompt — re-enter at
   Phase 0 (a re-echo after a redirect is usually cheap: the sweep is already done).
2. **Record the aligned reading as the intent** — in a session's closeout §1 (both his verbatim
   words AND the aligned reading), or restated in-chat for non-session work.
3. **Append the confirmed mappings to the lexicon** — append-only, dated, with the prompt
   fragment as provenance (format at the top of `lexicon.md`). This is how interpretation
   accuracy compounds instead of resetting each session. Only this phase appends; the lexicon
   has no other writer.
4. Proceed at full autonomy, as usual. The echo governs intake, nothing downstream.

## Composition

- **With muster:** muster opens the session honestly; echo grounds a commission honestly. When
  a session opens ON a commission, run muster first (identity, clocks), echo second, and let
  §1 record the aligned reading. Muster's open.sh is untouched by this skill.
- **With the register:** echo → aligned commission → options framed (docs/41-style frames) →
  his signature in docs/37 §3 → build. The echo never substitutes for a signature.
- **With /circle:** circle audits finished work against its criteria; echo aligns unstarted
  work with its intent. Opposite ends of the same honesty.

## The tripwire

`selftest.sh` — run it after any edit to this directory; a guard born today gets its tripwire
today. It proves the sweep runs green on the real repo, greps terms, fails loud on a missing
repo, and that the lexicon parses and this file still carries the stop rule.
