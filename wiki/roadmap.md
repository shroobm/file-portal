---
title: Roadmap — catalysts to a production system
section: Roadmap
last-verified: 2026-08-27
verified-against: 3cc7679
sources: [OPEN-TASKS.md, docs/08-roadmap.md, docs/37-next-stage-plan.md, docs/40-file-portal-feedback-pathways-think-tank.md, docs/41-conversion-completeness-plan.md, docs/45-s105-circle-findings.md]
---

> **Summary.** File Portal's governance measures correctness superbly and value not at all —
> across ~250k words of governing record there is one hit for "highest value" and zero for
> "user benefit" (measured 2026-08-22). This page is the missing organ: the ranked path from
> today's state (instruments ahead of wiring, nothing converted since S96, register at 118
> open items) to a serviceable, production-grade document-conversion system — expressed as
> **catalyst events**: gates with measurable done-whens, not dates. It supersedes docs/08
> (the v0–v3 file-router era) and extends docs/37 (the five-stage plan) upward to product level.

## The north star, and its metric

**A book dropped on the desktop reliably becomes a vaulted, faithful, searchable bundle —
with every loss named.** The metric is **vaulted books per week, with audit verdicts**.
Current value: **0/week — still zero, but NOT for the reason this page used to give.**
*(Re-measured `Observed` 2026-08-27. The superseded sentence read: "0/week over the last ~10
sessions — events.jsonl's last event is 2026-08-14 (137 events total)". Both of those figures
are now false.)*

- **The metric's VALUE is unchanged and correct: 0 vaulted books per week.** The vault holds
  **6** notes and the newest was written **2026-07-31** — 27 days ago.
  *(`find "$HOME/Documents/Obsidian/Obsidian and Zennotes Vault/Library" -name '*.md'` → 6,
  newest mtime 2026-07-31. Note the denominator: the notes live in SUBDIRECTORIES, so a
  `-maxdepth 1` count returns 0 and reads as an empty vault. It is not empty.)*
- **The evidence it cited is stale.** `events.jsonl` is at **147** events, not 137, and its
  last event is **2026-08-25T05:29:46Z**, not 2026-08-14.
- ⚠ **DO NOT READ THE ADVANCE AS PROGRESS ON THIS METRIC.** Ashby converted end to end and the
  auditor then **HELD** it on `verdict: fail`. The last event is literally `"event": "held"`.
  **`events.jsonl` advancing is not vaulting**, and treating `held` / `anchor` / `delivered` /
  `shipped` / `vaulted` as interchangeable phase claims is a named hazard on this project
  (Codex lane, `MSG-CDX-0014`, 2026-08-27). A future reader who "fixes" this number upward
  because the event count moved will have made exactly that error.
Every catalyst below exists to move that number or to make its quality claims true.

## The catalysts

| # | Catalyst | Done-when (measurable) | Register anchors |
|---|---|---|---|
| C0 | **The pipeline breathes** | one PDF converts end-to-end this week; events.jsonl advances; the held/ **5** (`Observed` 2026-08-27 — it was 4 when this row was written) get a disposition | §A38, §B (product clock) |
| C1 | **Reproducible ground** | `FP_PIPELINE` resolver replaces the 28 root literals; windows-converter gains a pinned manifest + joins CI; a documented venv makes local pytest possible | B-items: CI + literals |
| C2 | **A measured quality baseline** | poisoned bundles quarantined (SYM-050); figure_coverage wired (A4/A18 signed); a scored baseline published, every number with named denominators | §E slate 6–9, A4, A18 |
| C3 | **The challenger** (custom-OCR side project) | an alternative engine runs at the `_run_marker()` seam and is scored against C2's baseline; win or lose, deltas published | side-projects.md |
| C4 | **Operator-grade app** | bench under an auth token + DOM harness; input defects fixed (Ctrl+Z, arrow keys, 1 s render); one token system across the three UI palettes; fresh-machine install ≤ 30 min from README | A35/A36, B-items UI |
| C5 | **Standards & policy** | SECURITY.md + disclosure; Cargo.lock tracked + dependency audit in CI; license inventory for the vendored model stack; memory library gains a remote (A43); systemd hardening; SemVer + tagged releases | A43, security.md gaps |
| C6 | **The viability decision** | docs/40 §10's gates answered with evidence — G2 (exception layer) first per its own recommendation, then G3 (buyer/deliverable): product, or personal factory, priced either way | A33 |

**Ordering rule:** C0 is immediate and repeats weekly. C1 gates C2 gates C3. C4 and C5 run
parallel to C2/C3. C6 is decided, not built. A catalyst closes only when its done-when is
demonstrated by a command or a hand-run exercise recorded in a closeout.

## The fiscal frame (founder view)

The real currency here is **operator time**, and it is measurable: S105 found the recent
cadence at ~8.7 minutes of product work per session against whole sessions of governance
(docs/45). Costs, honestly stated:

- **Sunk:** the GPU box, the ThinkPad, the tooling. No new hardware is required by C0–C5.
- **Recurring:** model tokens (sessions + analyst passes; Gemini rate-limited lanes measured
  in docs), electricity, and operator hours — the binding one.
- **The burn test:** every session that closes without moving a register item or the
  north-star metric is pure governance burn. docs/45 measured ten in a row.
- **Revenue:** deferred to C6 by design. docs/40 §10 already names the gate (G3
  buyer/deliverable) and warns against building federation/enterprise before evidence.
  Until C6, File Portal is a personal factory whose ROI is the vaulted library itself.
- Locale/pricing rules for any purchase live in the operator's private profile layer.

## Standards adoption (what "modern expectations" means here, concretely)

| Standard | State today (verified 2026-08-23) | Catalyst |
|---|---|---|
| Dependency pinning | linux lanes: pyproject; **windows-converter: none**; Cargo.lock gitignored | C1, C5 |
| Security disclosure | no SECURITY.md | C5 |
| Vulnerability scanning | none in CI | C5 |
| Model/data licensing | Marker, surya, granite-docling, qwen3 vendored — no inventory | C5 |
| Backup / DR | vault is bare-git; **memory library has NO remote** (A43) | C5 |
| Testing floor | live lane at zero CI; JS one unwired test | C1, C4 |
| Accessibility | never audited; known input defects on the bench | C4 |
| Versioning / releases | none — 537 commits on one branch, 448 ahead of master | C5 |
| LLM-navigable docs | this wiki + llms.txt | shipped V0 |

## Cadence laws (the anti-M5 rules — how this roadmap stays a roadmap)

1. **Product before governance, every session:** one register item or metric move lands
   before any doctrine work. (docs/45's finding, inverted into a rule.)
2. **The roadmap is reviewed at every catalyst close** — and only then rewritten.
3. **Wiki stamps move with the work** (`wiki.sh stale` at close).
4. **No new register without a reader:** any new tracking surface must name the mechanical
   process that consumes it, or it is not created. (This page's reader: the session-open
   "what's next" question; muster's standing orders.)

## Top risks

1. **Data loss via path mistakes** (SYM-010 class; 23 anchored + 4 held bundles) —
   mitigated by C1's scratch-root tripwire before any resolver merge.
2. **Poisoned evaluation** (SYM-050) — no challenger work before C2's quarantine.
3. **Orphaned GPU processes** (SYM-047; 2 unadopted spawn sites) — C1-adjacent fix, small.
4. **Memory library on one disk** (A43) — C5, but cheap enough to do any day.
5. **Sentence-layer failures in the record itself** (docs/45 Families) — the wiki's audit
   gate + close.sh's claim-vs-probe upgrade (bet 4 of the 2026-08-22 value map).

## Signatures this page needs from Rab

- Adopt this roadmap as the standing value-ranking organ (or amend the catalysts).
- C0 scope: the held/ **5**'s disposition. *(`Observed` 2026-08-27: "which book breathes first" is answered — Ashby breathed 2026-08-25 and was held on a fail verdict. The disposition is what remains.)*
- A4/A18 (figure-coverage wiring + map repair) to unlock C2.
- The C6 date-trigger: what evidence forces the viability decision.

## Open items

- The full open queue is OPEN-TASKS.md (untracked at last verify — committing it is itself a B-item).
- The 2026-08-22 value map (10 ranked bets with measurements) backs every rank here.
