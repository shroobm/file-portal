---
name: wiki
description: Maintain the File Portal wiki at wiki/ — the LLM-navigable map of the whole project. Use when asked to add, update, verify, or navigate the wiki; when new work ships and needs recording ("add this to the wiki", "install this on the wiki", "new wiki page"); when creating an operator or agent profile; at session close to re-stamp pages the session touched; and whenever a reader asks "where do I learn about X in this repo" — the answer starts at wiki/INDEX.md. Not for the registers themselves (OPEN-TASKS.md and SYMPTOM-INDEX.md have their own laws) and not for session closeouts (docs/21).
---

# The Wiki — ideas as navigable space

The wiki is the project's **map layer**: one INDEX any model can read in a gulp, descending
into pages whose every load-bearing claim carries a citation back to ground truth. It exists
because this repo's records outgrew reading (docs/45 M5: 351 KB CLAUDE_README, 46 docs) —
the wiki does not add to that mass, it **routes** through it.

**The space metaphor is the design law.** The INDEX is the map. A page is an address. A
citation `(path:line)` is a road to ground truth. The registers (OPEN-TASKS.md,
SYMPTOM-INDEX.md) are the live queues — the wiki POINTS at them and never duplicates them,
because a duplicate becomes a second truth that rots.

**The mechanical half is a script. This file is the judgment half.**

## Run the gate

```bash
bash .claude/skills/wiki/wiki.sh check
```

Exit 1 = a measured red: an unmapped page, a dead link, a missing stamp, an oversize file,
or — worst — a tracked private layer. Fix before proceeding. UNREAD lines never claim clean.

## The laws (enforced by `check`; the numbers are the contract)

| Law | Value | Why |
|---|---|---|
| INDEX cap | 120 lines | the map must survive a small context window |
| Page cap | 200 lines | a page that outgrows this splits, or points |
| Membership | every page in INDEX | an unmapped page is invisible to every future reader |
| Links | every relative link resolves | a dead road is worse than no road |
| Stamps | `last-verified` + `verified-against` (a real ancestor of HEAD) | a claim without a date is a rumor |
| Privacy | `*.private.md` never tracked | **the repo is PUBLIC on GitHub** |

## The page contract (judgment)

- Frontmatter: `title`, `section`, `last-verified`, `verified-against`, `sources`.
- Open with a bold one-paragraph summary — the "if you read nothing else".
- Every load-bearing claim cites `(path:line)` or the command that proves it. Numbers name
  numerator, denominator, conditions (docs/34).
- End with `## Open items` — **pointers only** into the registers.
- Prefer omission over filler; an unverified claim is dropped or marked `(unverified)`.

## Workflows

**New page:** `bash .claude/skills/wiki/wiki.sh new <slug> "<Title>" <Section>` scaffolds the
frontmatter and prints the INDEX line. Placing that line — which section, what hook — is
judgment: write the hook so a model with no context knows whether to descend. Then fill the
page under the contract, run `check`, and re-run `selftest.sh` if you changed wiki.sh itself.

**New profile:** `bash .claude/skills/wiki/wiki.sh new-profile <Name>` scaffolds the tracked
public layer (role, working agreements, signature domains, interfaces) and the gitignored
`<Name>.private.md` — it refuses to run if the ignore rule is missing. Personal content goes
ONLY in the private layer. Agent profiles (Fable, Codex) point at `coordination/authorship.md`
rather than restating it.

**Recording an iteration:** when a session ships something real, update the touched pages'
content AND stamps (`last-verified` to today, `verified-against` to the closing SHA), and add
one line to `history.md`'s era table if the work opened or closed an era. `wiki.sh stale`
lists what lags.

**At close:** run `check`. It is not yet a close.sh gate (see the ladder) — run it by hand.

## The upgrade ladder (recorded intent, so upgrades are asked for, not re-invented)

- **U1** — Room/widget integration: the wiki navigable from the Control Room. Touches the
  42-command IPC surface in `main.rs` — **Rab's signature required** before wiring.
- **U2** — `close.sh` gains a `wiki check` gate, warn-only for one session, then armed.
- **U3** — muster's open surfaces `wiki.sh stale` so drift is seen at session start.
- **U4** — `llms.txt` at repo root (shipped with V0 if present — verify) kept in sync.
- **U5** — per-page verification trail: auditors append `verified-by` entries.

## Hazards this skill inherits

Repo markdown is largely CRLF — the script strips `\r` before measuring (SYM-029). Never
`cat` CLAUDE_README.md or CHANGELOG.md to build a page — grep headings, read ranges. The
untracked `.agents/` tree is not this skill's home; only `.claude/skills/wiki/` is real.
