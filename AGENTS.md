# AGENTS.md — operational contract for any coding agent in this repo

File Portal: a two-machine document factory (Windows widget + GPU converter, Linux
allocator + vault). Public repo, single operator (Rab). This file is the ONE tool-facing
instruction file; the knowledge layer it points into is the wiki.

## Read first

1. `wiki/INDEX.md` — the map. Read it, then at most two cited pages before acting.
2. Something looks broken → `SYMPTOM-INDEX.md` (grep by symptom; guards are named).
3. Asking "what's next" → `OPEN-TASKS.md` (§A needs the operator's signature; §B is mechanical).

## Two interpreters, and neither is on PATH by default

**Read this before running any command in this file.** Both were discovered the hard way, by
two different agents, ten minutes apart, on 2026-08-26.

- **`python` is NOT Python here.** Bare `python` resolves to the Microsoft Store shim and fails
  (exit 49). It does not error usefully — it prints a Store advertisement. The real interpreter:

  ```
  C:\Users\Bndit\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe
  ```

- **`bash` is Git Bash and may not be on PATH** in PowerShell-native shells. Every `.sh` in
  `.claude/skills/` needs it:

  ```
  C:\Program Files\Git\bin\bash.exe
  ```

Neither is a defect to report — they are the machine. A command that fails on either is
**UNREAD**, never a red gate: you have not measured the thing, you have failed to reach it.

## Commands that verify work

- Rust widget: `cd windows-widget/src-tauri && cargo fmt --check && cargo clippy && cargo test`
- Linux lanes (CI only — pytest/ruff are NOT installed on the Windows box): see `.github/workflows/ci.yml`
- Wiki integrity: `bash .claude/skills/wiki/wiki.sh check` (Git Bash — see prerequisites above)
- Session open/close: `.claude/skills/muster/` — but see hazards before running anything there.

## Standing hazards (each has burned a session)

- Claims are tagged: Observed (you re-measured it now) or Historical (transcribed). Never
  present an inference as an observation; when a document and reality disagree, reality wins.
- Repo markdown is largely CRLF — `tr -d '\r'` before anchored greps (SYM-029).
- Never `cat` `CLAUDE_README.md` or `CHANGELOG.md` (2,000+ lines each) — grep headings, read ranges.
- Exclude `windows-widget/src-tauri/target/` and `node_modules/` from every search (6.5 GB).
- Do NOT run `open.sh`/`close.sh` casually (network, SSH to the ThinkPad, stored credential),
  nor `card_mutex_selftest.py`/`deferral_gate_selftest.py` (real processes, the GPU mutex).
- `observability/glass_detector.py` bare exits 0 while listing glitches — only
  `--since <pin> --enforce` is honest (SYM-046).
- `.agents/` (if present, untracked) is a STALE skills mirror with a green banner and no
  close gate — resolve skills only from `.claude/skills/` (OPEN-TASKS B2).
  **Measured 2026-08-26:** 16 files, gitignored, and drifted on three —
  `open.sh`, `muster/SKILL.md`, and **`relay-gate/gate.py` (`a1246bd1` there vs
  `ab26a4f1` authoritative)**. That last one is the REFEREE of the two-model
  protocol: two copies means the `gate_rev` column can disagree with neither side
  being wrong. A `__pycache__/gate.cpython-312.pyc` sits beside it, so that copy
  **has been executed**. `close.sh` is absent entirely — an agent working from
  there cannot close a session at all.
- `OPEN-TASKS.md` may be untracked — never stash/checkout/clean it away.
- One process on the GPU, ever — the card mutex `Local\file-portal-card` enforces it.

## Conventions

- Every measured number names numerator, denominator, conditions (docs/34).
- Commits: descriptive message + model trailer (e.g. `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`);
  cross-model authorship claims per `coordination/authorship.md`.
- New/changed wiki pages follow `.claude/skills/wiki/SKILL.md`; the INDEX moves in the same commit.

## Working in parallel with the other model (the relay gate)

Two models share this repo (Fable = Claude, Codex). Handoffs that must be provably received
go through the **relay-gate skill**, not bare relay prose:

```bash
# NOT bare `python` — that is the Store shim (see "Two interpreters" above).
PY="C:\Users\Bndit\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
"$PY" .claude/skills/relay-gate/gate.py init --as Codex   # turn it on (your own sidecar)
"$PY" .claude/skills/relay-gate/gate.py inbox  --as Codex # what awaits your confirmation
"$PY" .claude/skills/relay-gate/gate.py status            # both sides at a glance
```

Read `.claude/skills/relay-gate/SKILL.md` for the contract and
`coordination/RELAY-ACK-PROTOCOL.md` for the wire format. Resolve the skill from
`.claude/skills/` — **never** from `.agents/`, which is a stale untracked mirror.

Rules that bind both models: `relay.md` is append-only (the qualifier lives in the sidecar) ·
you write only your own `ack-<model>.json` · a confirmation requires a restatement and an
independent digest check · a gate agent takes ONE ticket, delivers, and **stops** ·
`blocked-on-rab` may never be cleared by a model.
