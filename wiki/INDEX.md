# File Portal — the map

> **Descent contract:** read this file, then at most **two** cited pages before acting.
> Needing a third page means this index failed — record that as a defect, don't work around it.

File Portal turns dropped documents into an audited, git-versioned library across two
machines. This wiki is the navigable map of everything: each line below names the question
its page answers. Pages carry citations to ground truth; the registers stay the live queues.

**Read in this order:**
1. Any new session → [architecture.md](architecture.md), then the page for what you'll touch.
2. Something looks broken → [SYMPTOM-INDEX.md](../SYMPTOM-INDEX.md) first, then [operations.md](operations.md).
3. Asking "what's next" → [OPEN-TASKS.md](../OPEN-TASKS.md), ranked by [roadmap.md](roadmap.md).
4. Touching conversion or OCR → [conversion-quality.md](conversion-quality.md) before any change.
5. Maintaining this wiki → `.claude/skills/wiki/SKILL.md` (`/wiki`), gate: `wiki.sh check`.

## System

- [Architecture](architecture.md) — what holds the system up, what couples the lanes, and where the chokepoints are · Observed 2026-08-23
- [History & Iterations](history.md) — how it got here: the eras, what each shipped, what to read per era · Observed 2026-08-23
- [Side Projects & Frontier](side-projects.md) — what orbits the core (the custom-OCR challenger, prototypes, remote access, the memory library) and each one's seam in · Observed 2026-08-23

## Pipeline

- [Desktop Pipeline](pipeline-desktop.md) — what happens to a dropped PDF on the Windows GPU lane, stage by stage, and where it can stall · Observed 2026-08-23
- [Linux Pipeline & Vault](pipeline-linux.md) — how bundles travel, get allocated, and reach the vault; who may write the vault · Observed 2026-08-23
- [Conversion Quality & OCR](conversion-quality.md) — how fidelity is measured, what the instruments currently say, and what is banned by measurement · Observed 2026-08-23

## Product

- [Control Room (Widget)](control-room.md) — what the desktop app is: surfaces, boot order, the IPC contract, process supervision · Observed 2026-08-23
- [Repair Bench](repair-bench.md) — where failed conversions go for human repair, its seams, and its open defects · Observed 2026-08-23
- [A11y Conventions](a11y-conventions.md) — the framework-free accessibility conventions both human surfaces build against, and the two measured contrast failures to fix first · Observed 2026-08-23

## Operations

- [Operations Runbook](operations.md) — how to run, watch, and not break it: machines, processes, locks, resume semantics, hazards · Observed 2026-08-23

## Governance

- [Governance & Records](governance.md) — how the project governs itself: the ledger, the registers, the skills, and the map of all 46 docs · Observed 2026-08-23
- [Testing & CI](testing-and-ci.md) — what verifies what, where verification cannot reach, and what is safe to delegate to agents · Observed 2026-08-23
- [Security Posture](security.md) — the honest posture of a public repo: what is sound, what gaps remain, at what real severity · Observed 2026-08-23

## Roadmap & Profiles

- [Roadmap](roadmap.md) — where this is going: catalyst events C0–C6, the fiscal frame, and the standards it must meet · Observed 2026-08-23
- [Profiles — the system](profiles/README.md) — who works here, and how a profile's public and private layers split · Observed 2026-08-23
- [Profile — RAB](profiles/RAB.md) — the operator: role, working agreements, and what only he decides · Observed 2026-08-23

## Optional

- [README](../README.md) — the public front door: what File Portal is and why it exists.
- [The manual](../docs/20-file-portal-manual.md) — the operator textbook, every surface and lever.
- [CLAUDE_README](../CLAUDE_README.md) — session protocol + Change Ledger (very large; enter via [governance.md](governance.md), never read whole).
- [docs/](../docs) — the numbered design and finding records; the genre map lives in [governance.md](governance.md).
- [llms.txt](../llms.txt) / [AGENTS.md](../AGENTS.md) — the machine-facing pointers; both defer to this index.
