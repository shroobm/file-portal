---
title: History & Iterations
section: System
last-verified: 2026-08-23
verified-against: 1790554
sources: [CLAUDE_README.md, OPEN-TASKS.md, docs/00-overview.md, docs/08-roadmap.md, docs/10-library-pipeline-plan.md, docs/13-control-room-design.md, docs/19-opus5-execution-plan.md, docs/21-session-closeout-contract.md, docs/29-the-observability-complex.md, docs/32-proxy-substitution.md, docs/45-s105-circle-findings.md, sessions/]
---

# History & Iterations

**The project is seven eras deep in under two months. It began 2026-06-25 as a file-router
(drag a file onto a tile, a Linux box sorts it), grew a GPU conversion factory, a Control
Room face, an observability doctrine, a vault with an adoption law — and then spent its
newest era (S97–S106, ten sessions in ~48 hours) building governance machinery while the
product card stayed byte-identical (docs/45-s105-circle-findings.md:80-86). Era 7 opened
2026-08-22/23 with the open-task register and this wiki. The authoritative event record is
the Change Ledger — 114 rows (`grep -cE '^\| 2026' CLAUDE_README.md`), table starting at
CLAUDE_README.md:1120 — plus 42 closeout files (`ls sessions/ | wc -l`, both machine lanes).
This page routes; it does not re-tell.**

## The eras

Dates are UTC ledger/commit dates. Eras 1–4 and 6–7 are roughly sequential; Era 5 is a
thread that runs across them. Ground each era via the cited rows before quoting details.

| # | Era | Dates | What shipped | Surviving artifact | Ground truth |
|---|---|---|---|---|---|
| 1 | File-router v0–v3 | 2026-06-25 → 07-08 | Tiles → Tailscale transport → allocator; L1–L6 + W5/W6 milestones | `windows-widget/` portal tiles, `linux-receiver/`, `linux-dashboard/` (dormant) | first commit `0a16117` 2026-06-25 (`git show -s --format='%h %as' 0a16117`); v0–v3 headings docs/08-roadmap.md:10-43; W5 transport row CLAUDE_README.md:1130 (`f9ad76a`) |
| 2 | Conversion factory | 2026-06-29 → 07-19 | docs/10 plan; L7–L12 converter engine + exporter; GPU/Marker revamp (docs/11-12); Gemini analyst | `windows-converter/convert_and_ship.py`, `linux-converter/` | docs/10 added `26e0a52` 2026-06-29, docs/11 `5e8b945` + docs/12 `27813dd` 2026-07-18 (`git log --diff-filter=A --follow`); L7–L10 row CLAUDE_README.md:1133 (`c718ed2`) |
| 3 | Control Room | 2026-07-19 → 07-23 | docs/13 projection design; S20+ build sessions; S34 graduates the Room onto the widget; docs/16 the face | `room.js`/`room.rs`, Dock⇄Room switch | docs/13 added `2eef57b` 2026-07-19; docs/13-control-room-design.md:3-5 (origin); S34 row CLAUDE_README.md:1167 (`5cfaec4`); docs/16 added `44d9157` 2026-07-22 |
| 4 | Observability & doctrine | 2026-08-09 → 08-15 | docs/21 closeout contract + SYMPTOM-INDEX + CI revived (S67); docs/29 + docs/32 diagnosis; glass detector (S78); muster (S79) | `observability/glass_detector.py`, `.claude/skills/muster/`, `SYMPTOM-INDEX.md` | S67 row CLAUDE_README.md:1200 (`fdc2f61`); docs/29 + docs/32 added 2026-08-14 (`99726d4`, `7c357b0`); S78 row :1211 (`a22a805`); S79 row :1972 (`2729a63`) |
| 5 | Vault & adoptions (thread) | 2026-07-11 → 08-20 | Exporter (L11–L12); vault loop closed; supersede rail (S43/S44/S50); bless rail + first blessed book (S56); widget adoptions S45 → S102 | `linux-converter/converter/exporter.py`, the vault, installed exe `4DCB73E2` | L11–L12 row CLAUDE_README.md:1136 (`10f6bc6`); vault-loop row :1137 (`fb2570d`); S56 row :1189 (`2bb9fa4`); exe lineage 7D403BD6 → 6CA0DEF0 → AFDB8355 *(never adopt)* → C3C05D49 → 4DCB73E2, docs/19-opus5-execution-plan.md:68-71 |
| 6 | Governance arc S97–S106 | 2026-08-20 → 08-21 | Think tank, relay, claim convention, concordance amendment, P-0/P-1 instruments, `close.sh` (S103), two Circles, modularity gate — and no product motion | `docs/45`, `.claude/skills/muster/close.sh`, `figure-triage` levers | 10 of 42 files in `sessions/` are `S97…S106-desktop-2026-08-20.md` (`ls sessions/`); rows CLAUDE_README.md:1992-2001; the open card byte-identical S97 → S105, docs/45-s105-circle-findings.md:80-86 |
| 7 | The register & the wiki | 2026-08-22 → open | `OPEN-TASKS.md` built at S107 open from all 42 closeouts; this wiki + [roadmap](roadmap.md) built 2026-08-23 | `OPEN-TASKS.md`, `wiki/` | OPEN-TASKS.md:7-8 (build statement); `ls wiki/` |

Eras 1–2 are pre-session-numbering: the ledger's first row is 2026-07-07
(CLAUDE_README.md:1128, `d4841e0`); named sessions (S16+) begin at row :1149.

## Catalysts already passed

Worded as the ledger rows word them; SHA is the row's closing commit
(verify: `git merge-base --is-ancestor <SHA> HEAD`).

| Catalyst | When | Row / SHA |
|---|---|---|
| First transport milestone (W5) | 2026-07-08 | CLAUDE_README.md:1130 · `f9ad76a` |
| Converter engine built (L7–L10) | 2026-07-10 | CLAUDE_README.md:1133 · `c718ed2` |
| Vault consumption verified — pipeline loop closed end to end | 2026-07-11 | CLAUDE_README.md:1137 · `fb2570d` |
| First real ingest | 2026-07-12 | CLAUDE_README.md:1138 · `ef5a8e8` |
| First real ⚡ drop (439 pp) at the gate (S26) | 2026-07-19 | CLAUDE_README.md:1159 · `2b965ca` |
| Room graduation — Control Room becomes the widget's face (S34) | 2026-07-22 | CLAUDE_README.md:1167 · `5cfaec4` |
| First widget adoption (S45) | 2026-07-25 | CLAUDE_README.md:1178 · `c902a7b` |
| First blessed book — Cybernetics, vault note 6 (S56) | 2026-07-31 | CLAUDE_README.md:1189 · `2bb9fa4` |
| Closeout contract + SYMPTOM-INDEX + CI revived (S67) | 2026-08-09 | CLAUDE_README.md:1200 · `fdc2f61` |
| Muster born — the session learned to open itself (S79) | 2026-08-15 | CLAUDE_README.md:1972 · `2729a63` |
| `close.sh` born — the close grows teeth (S103) | 2026-08-20 | CLAUDE_README.md:1998 · `6466262` |

## Current state (measured 2026-08-23 at `1790554`)

- **537 commits** on HEAD (`git rev-list --count HEAD`).
- **master 1 / branch 448** — commits unique to each side of
  `git rev-list --left-right --count master...HEAD` (`feat/library-pipeline` carries 448
  commits master lacks; master holds 1 the branch lacks).
- **Nothing has converted since S96**: the pipeline event stream
  `C:\Users\Bndit\ml\library\events.jsonl` holds 137 lines total and its last line is
  stamped `2026-08-14T03:32:13+00:00` (`tail -1` + `wc -l`, re-run 2026-08-23); the
  product-motion diagnosis is OPEN-TASKS.md:34-40 (§0).
- Latest closed session: S106, row CLAUDE_README.md:2001, closing `8e2df7c`; eight commits
  sit after it up to HEAD (`git log --oneline 8e2df7c..HEAD`) — post-close bench work, its
  Circle (`3659ec7`), and record-layer rows.

## Reading paths

One line per era — which door to open first.

- **Era 1:** docs/00 (overview; its banner scopes it to "the first era — file routing",
  docs/00-overview.md:3-4) → docs/08 (the ancient v0–v3 roadmap) → docs/01–09 as needed.
- **Era 2:** docs/10 (the 4-part execution plan) → docs/11 (GPU revamp) → docs/12
  (phase-4 rewiring); current state lives in [pipeline-desktop](pipeline-desktop.md) and
  [pipeline-linux](pipeline-linux.md).
- **Era 3:** docs/13 (projection design) → docs/16 (the face); current state in
  [control-room](control-room.md).
- **Era 4:** docs/21 (how sessions end) → docs/29 (what belongs on the glass) → docs/32
  (symptom/condition/disease — its §6 left the prediction docs/45 scored).
- **Era 5:** docs/15 (survival audit — the vault's gatekeeper) → docs/19:66-74 (installed-exe
  lineage + rebuild ritual; trust the muster card over any prose hash line).
- **Era 6:** docs/45 **only** — it is the arc's own audit; do not reconstruct the arc from
  the ten closeouts when docs/45 already did. Then OPEN-TASKS.md §0.
- **Era 7:** OPEN-TASKS.md (what is undone) → [roadmap](roadmap.md) (what is next).

## Open items

- The full undone-work register: `OPEN-TASKS.md` — §0 for the era-6 diagnosis, §A43 for the
  memory library's missing remote, §E for the 7-item P-slate.
- Era-6 residue awaiting signature: `OPEN-TASKS.md` §A (43 semantic decisions) and §D
  (8 delegations never collected).
- Live failure modes by symptom: `SYMPTOM-INDEX.md` by SYM-### (see §C of OPEN-TASKS.md for
  which rows are genuinely open).
- The arc's full account, including the three failure families: docs/45 (pointed at, not
  duplicated here).
