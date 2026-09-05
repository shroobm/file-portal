# File Portal

A local-first document library pipeline on two machines you own. Drop a PDF on the Windows
desktop; Marker converts it to markdown on the GPU; a local model annotates it; a survival audit
measures how much of the source text actually survived and holds anything that fails; what you
bless lands as a note in a git-backed Obsidian vault on the Linux machine. Nothing leaves the two
machines unless you turn on the analyst's optional Gemini Flash backend, which is off by standing
rule and sends chunk text to Google's API when it is on. Nothing lands unproven.

```
 Windows desktop (RTX 3080)                            Linux machine (ThinkPad)
 ┌──────────────────────────────────────────┐          ┌───────────────────────────────┐
 │ drop/ ─► Marker (clean lane │ scan lane) │          │ staging/ ─► exporter          │
 │        ─► analyst (local qwen3, fenced)  │  tar over│   pass, or flag + bless.json  │
 │        ─► survival audit, pymupdf witness│ ───────► │   ─► vault/ (bare git ─►      │
 │        ─► pass │ flag │ fail ─► held/    │ Tailscale│      Obsidian Library)        │
 │ widget: Dock · Room · Wall · Repair Bench│   SSH    │ allocator: sorted/ (origins)  │
 └──────────────────────────────────────────┘          └───────────────────────────────┘
```

## State today

Measured on 2026-09-05 from the library, the event stream and the registers on the desktop.

| What | Count | Denominator and conditions |
|---|---|---|
| Works converted | 10 | distinct titles under `anchor/`, 27 bundle directories including re-runs and copies |
| Sources audited | 12 | distinct `source` values on `scored` events in `events.jsonl`; 8 works, four of them scored under both their `.pdf` name and their re-run name |
| Audit verdicts | 0 pass · 4 flag · 19 fail | one line per `scored` event; a book can be scored more than once |
| Held bundles | 7 | directories under `held/` |
| Vault notes | 6 | markdown files in the Obsidian Library; one reached the vault by a human bless of a `flag` (2026-07-31), four were exported before the survival audit existed and carry no verdict, one was scored `fail` and shipped on 2026-07-30, the day before the exporter's verdict guard; none by a `pass` |
| Record | 897 commits · 122 ledger rows · 59 session records · 57 docs | this branch at the commit that wrote this file: `git rev-list --count HEAD`; dated rows of the Change Ledger in `CLAUDE_README.md`, both blocks; every entry under `sessions/` (57 closeouts, 2 data files); every top-level entry under `docs/` (52 files, 5 folders) |
| Known failures | 74 symptoms filed · 54 errors logged | `SYMPTOM-INDEX.md`, `ERROR-BIN.md` |

The audit has not passed a book yet. That is the honest headline: the pipeline converts, annotates,
measures and refuses, and the `held/` folder is where its refusals live until a human repairs the
book at the Repair Bench or signs a policy. The current frontier is the analyst stage: the local
model rewrites and occasionally deletes paragraphs under a prompt that forbids it, and the audit
catches it (`docs/54-repair-road/`).

## Two ways in

**Run the pipeline** (the current system, end to end): read
[`docs/20-file-portal-manual.md`](docs/20-file-portal-manual.md), then
[`docs/18`](docs/18-levers-and-heartbeats.md) §5.4 for the bless rail and §3 for the levers, and
[`docs/15-survival-audit.md`](docs/15-survival-audit.md) for what a verdict means. The desktop
needs a Python environment with `marker-pdf`, `surya-ocr`, `pymupdf` and `rapidfuzz`
(`windows-converter/`), Ollama with a local model for the analyst, and the Tauri widget
(`windows-widget/`, adopted as a built executable whose hash you verify by hand). The Linux side
runs the converter/exporter as a `systemd --user` service (`linux-converter/`).

**Route files** (the original tool, still in daily use): set up Tailscale SSH between the machines
([`docs/02`](docs/02-tailscale-setup.md)), install the allocator
([`linux-receiver/README.md`](linux-receiver/README.md)), run the widget's portal tiles. Files
dropped on a tile stream over `tailscale ssh` and are sorted under the receiving user's home. No
open ports, no sudo on either end.

## Repository layout

| Path | What it is |
|---|---|
| `wiki/` | **The map. Start at [`wiki/INDEX.md`](wiki/INDEX.md)** — the LLM-navigable index of the whole project, every claim cited, every page stamped. |
| `docs/` | The knowledge base. `docs/20` is the operator textbook; `docs/00`–`docs/09` describe the original file-routing tool only (see Origins). `docs/50`–`docs/55` are the ticket board, the census, the PDF-structure study, the lead hunt, the repair road and the register sweep. |
| `windows-converter/` | Desktop-side conversion: Marker with clean and scan lanes, the fenced analyst pass, the survival audit, block sidecars, shipping to Linux staging. Eight of the fourteen modules carry a `*_selftest.py`; the survival audit (`fidelity_audit.py`) and `analyst.py` are exercised through sibling selftests, `room_chat.py` through `room_chat_acceptance.py`. |
| `windows-widget/` | The Tauri desktop app: portal tiles plus the Dock, Room, Wall and Bench surfaces. |
| `linux-converter/` | The user-level converter and **exporter**: the supersede guard ("pass, or flag with bless"), the vault writer, seam receipts. |
| `linux-receiver/` · `linux-dashboard/` | The allocator service and the optional GTK4 browser for `sorted/`. |
| `prototypes/` | Quarantined explorations with zero pipeline coupling, notably `repair-bench/`, the human-in-the-loop repair tool, and `mission-control/`. |
| `observability/` | The glass: event schema registry, dispositions, the glitch detector and its acceptance suite. |
| `coordination/` | The two-model bus: `relay.md`, the ACK gate, authorship stamps, the disclosure standard. |
| `sessions/` | One structured closeout per development session ([`docs/21`](docs/21-session-closeout-contract.md)). |
| `windows-remote/` | Remote-access setup and lockdown scripts for the desktop ([`docs/17`](docs/17-remote-access-runbook.md)). |
| `scripts/` | One-off setup helpers: Tailscale SSH, the Arch bootstrap, the Windows dev environment. |
| `codex/` · `dumps/` | Codex's own workshop (`private/` is gitignored), and the heavy dumps — transcripts, evidence, QA — with their own ledger. |
| `OPEN-TASKS.md` · `SYMPTOM-INDEX.md` · `ERROR-BIN.md` | The registers: what is not done, what the system does when it is wrong, and what the agent got wrong. |
| `CLAUDE_README.md` · `AGENTS.md` · `llms.txt` | The cross-machine mission brief with the Change Ledger, and machine-facing navigation. |
| `.claude/skills/` | The executable protocol: `muster` (open and close with two clocks), `relay-gate`, `wiki`, `echo`. |

## How the project governs itself

The code is half of the repository; the other half is a record built to survive rewinds, power
cuts and two AI lanes working in parallel.

- **Two clocks.** Every session opens by checking that the git ledger in `CLAUDE_README.md` and
  the memory library's tally agree, and closes by advancing both together (`.claude/skills/muster/`).
- **Registers, not memory.** Open work lives in `OPEN-TASKS.md`; failures are keyed by what you
  notice in `SYMPTOM-INDEX.md`; the agent's own mistakes are banked with cause and remedy in
  `ERROR-BIN.md`. Rows are never rewritten, only annotated with dated notes.
- **The tag law.** Every claim in a record carries Observed, Verified, Inferred, Unknown or
  Historical, and a number is re-measured, never quoted.
- **Sign-by-slot.** Policy changes, gate changes and anything touching the vault are the owner's
  signature; a session builds on signed scope without re-asking.
- **Two model lanes.** Claude and Codex share one bus (`coordination/relay.md`) with digests,
  claimed stamps and silence recorded as unread, never as agreement.
- **Fleets under a law.** Multi-agent work follows `docs/47`: ground, deviation is the report,
  every claim tagged, a negative control, declared residue. The fleets since `docs/52` add planted
  decoys and an independent verifier last.

The verified list of everything still open, grouped by who can move it, is
`docs/55-register-sweep/open-list-2026-09-04.md`.

## Origins

The project began on 2026-06-25 as a file router: drag-and-drop "portal" widgets for the Windows
desktop that push files to a Linux machine over a [Tailscale](https://tailscale.com) tailnet, where
a small user-level service sorts them into the right folder, with no open ports, no privileged
daemon and no third-party relay. That tool is built and in use. `docs/00`–`docs/09` describe it and
nothing else; [`docs/08-roadmap.md`](docs/08-roadmap.md) tracks that era only and its checkboxes
lag reality. The pipeline began on this branch on 2026-06-29 with the plan in
[`docs/10`](docs/10-library-pipeline-plan.md) and a Linux-side converter the next day; PR #1 merged
the branch into master on 2026-07-13 and the desktop GPU lane followed on 2026-07-18.
[`CHANGELOG.md`](CHANGELOG.md) plus the Change Ledger are the record of what shipped when.

## Licence

The code in this repository is MIT, see [`LICENSE`](LICENSE). The pipeline runs on third-party
components under their own licences, and they are not all permissive: `marker-pdf` and `surya-ocr`
are GPL-3.0-or-later with model weights under a modified OpenRAIL-M that limits commercial use;
`pymupdf` is AGPL-3.0 or a commercial licence from Artifex. Read
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) before deploying this beyond personal use.
