---
title: Profiles — the system
section: Profiles
last-verified: 2026-08-23
verified-against: 1790554
sources: [.gitignore, .claude/skills/wiki/wiki.sh, coordination/authorship.md]
---

> **Summary.** A profile is the durable identity of anyone — human operator or model — who
> works on File Portal: their role, their working agreements, and what only they may decide.
> Every profile is **two layers**: a tracked public layer (this directory) and a gitignored
> `<Name>.private.md` layer for personal content and co-written notes. The split is not a
> convention, it is a gate: **this repository is public on GitHub**, so
> `wiki.sh check` treats a tracked private file as a measured red, and `new-profile`
> refuses to scaffold if the ignore rule (.gitignore, `wiki/profiles/*.private.md`) is missing.

## Why profiles exist

Working agreements in this project were scattered across a memory library (out of repo,
single-disk — register item A43) and 42 session closeouts. A profile is the one address
where "how does this person work, and what is theirs to decide" lives — so any model,
in any session, on any machine, can read it before acting.

## The two layers

| Layer | File | Tracked? | Holds |
|---|---|---|---|
| Public | `<Name>.md` | yes | role · working agreements · signature domains · interfaces |
| Private | `<Name>.private.md` | **never** | personal notes, preferences, anything identifying — co-written with any model, local to the machine |

The private layer is machine-local by design. If it must survive the machine, that is a
backup decision (see A43's class), never a commit.

## Creating a profile

```bash
bash .claude/skills/wiki/wiki.sh new-profile <Name>
```

Scaffolds both layers, verifies the ignore rule first, and prints the INDEX line to place.

## Agent profiles

Models that work this repo (Fable, Codex) claim authorship under
`coordination/authorship.md` (⟨claimed:⟩ stamps, commit trailers). An agent profile here
holds only what authorship.md does not: standing working agreements with the operator.
It points at authorship.md for identity; it never restates it.

## Current profiles

- [RAB](RAB.md) — owner, operator, signatory.

## Open items

- U1 (SKILL.md ladder): surface profiles in the widget once the wiki is navigable from the Room — Rab's signature.
