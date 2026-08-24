---
title: Governance & Records
section: Governance
last-verified: 2026-08-23
verified-against: c56d486
sources: [CLAUDE_README.md, SYMPTOM-INDEX.md, OPEN-TASKS.md, .claude/skills/muster/close.sh, .claude/skills/muster/SKILL.md, .claude/skills/wiki/SKILL.md, .agents/skills/muster/SKILL.md, observability/glass_detector.py, observability/dispositions.json, coordination/authorship.md, coordination/relay.md, coordination/selftest.sh, docs/45-s105-circle-findings.md]
---

# Governance & Records

**If you read nothing else:** the project governs itself with two hand-maintained record organs
(the Change Ledger inside `CLAUDE_README.md`, and `SYMPTOM-INDEX.md`), one register of not-done
(`OPEN-TASKS.md` — currently **untracked in git**), three gates that can actually exit 1
(`close.sh`, `wiki.sh check`, `glass_detector.py --since <pin> --enforce`), and a coordination
layer (relay + ⟨claimed⟩ authorship stamps). The teeth are unevenly distributed: the ledger has
no parser or validator, the symptom index's status column can contradict its own update clauses,
and docs/45's Family 1 — the sentence describes the *neighbour* of the probe — is the standing
failure mode that no gate yet checks. Trust exit codes and cited probes; never a status cell.


> **S108 update (2026-08-23):** close.sh gained two sections this session, both warn-only until armed: DOCTOR (artifact-vs-measurement parity — the check docs/45 §6.2 named as missing) and CENSUS (promised tripwires vs fixtures on disk). The register was committed to git and struck per §H rule 1; the relay is now bidirectional (Codex returned four entries 2026-08-23).

## 1 · The Change Ledger — the HARD clock

Lives at `CLAUDE_README.md:1120` (`grep -n "## Change Ledger"`). **114 rows in 2 machine
lanes — 101 Desktop, 13 ThinkPad** (numerator: lines matching `^\| 20` after line 1120 of the
CRLF-stripped file; denominator: the whole ledger table; re-counted 2026-08-23 at 1790554 via
`tr -d '\r' < CLAUDE_README.md | sed -n '1120,$p' | grep -cE '^\| 20'`, lanes via awk on col 2).
A row commits: `| Date (UTC) | Machine | Milestones closed | Docs touched | Closing SHA |`
(CLAUDE_README.md:1126), appended only **after** the closing commit exists; the SHA *is* the
closing commit, verified with `git merge-base --is-ancestor <SHA> HEAD` (CLAUDE_README.md:1122-1124).
The session cell must open `S<n>:` — muster's parser keys on it (coordination/authorship.md:18-20).
It is prose with no validator; this branch already carries a reverted row (`git log --oneline -1
8dbe801`), making it the least mechanically defended contract in the repo.

**The two-clock protocol:** the ledger's newest per-lane row is the HARD clock; the SOFT clock is
the `cookie-tally.md` header mirrored by the memory library's `MEMORY.md` TIME-STATE line
(out-of-repo; `~/.claude/CLAUDE.md` MUSTER step 2). Both are read verbatim at open
(.claude/skills/muster/open.sh:118, "[1] GROUND — the clocks") and must advance together at close
(.claude/skills/muster/SKILL.md:195). Disagreement means a rewind, fork, or blind session —
reconcile before working.

## 2 · SYMPTOM-INDEX.md — retrieval by symptom

**52 rows, SYM-001–SYM-052** (`tr -d '\r' < SYMPTOM-INDEX.md | grep -cE '^\| *SYM-'` = 52;
last row at :81). Keyed on what the system is *doing*, never on which session produced it
(SYMPTOM-INDEX.md:3-4); fixed rows stay — recurrence is what is guarded against (:7-9).

⚠ **Read whole rows, never the status column.** Status cells accrete dated `Update` clauses that
can reverse the leading verdict: SYM-032/033/041/042 still open with `open`/`OPEN` up front while
their own update clauses record S94 signing and building the fix (SYMPTOM-INDEX.md:65,66,71,72);
OPEN-TASKS.md §C flags exactly these four as falsely open, repair queued as its F3.

## 3 · OPEN-TASKS.md — the register of not-done

292 lines (`wc -l`), sections §0 answer + §A–§H (`grep -E '^## '`). Addressable ids: **43 A + 31 B
+ 8 D + 11 F table rows** (grep `^\| *[A-Z]-?[0-9]+` by prefix) **+ §C's roll call of 14 open and
4 falsely-open SYM rows + §E's 7-item P-slate ≈ 118**. Sections: A awaiting Rab's signature ·
B mechanical · C open symptom rows · D delegated-never-collected · E the P-0…P-6 slate ·
F record-integrity repairs · G what is NOT open · H how the file stays true.

⚠ **UNTRACKED in git**: `git status --short` → `?? OPEN-TASKS.md` (re-run 2026-08-23). The
register of everything not done is itself unprotected — a clone, rewind, or clean checkout loses
it. Its §H states its own rot law: never quote a status from the file; open the cited source.

## 4 · The skills — the executable gates

**muster** (.claude/skills/muster/): open.sh 298 lines (clocks, live state), close.sh 183,
muster.sh, selftest.sh (20 cases, 0–18 + 27, incl. 15-18 on the close). `close.sh <pin>` prints VALUES, never
✓; UNREAD never blocks and never claims clean; **only a MEASURED red exits 1** (close.sh:17-19).
Its exit-1 gates:
- PIN missing (:38-39) or unresolvable (:44-45)
- DIFF: uncommitted (non-untracked) changes since the pin (:55)
- GLASS: `glass_detector.py --since <pin> --enforce` red (:65-66)
- RUST: fmt / clippy / test red — only when `windows-widget/` changed since the pin (:88-89)
- CI: run for HEAD completed with a non-success conclusion, via the stored credential (:123)

The **LEVERS** section ([5], :130-177) — docs/18 §2's modularity gate, reporting threshold-shaped
constants added with no lever and no waiver — "prints VALUES and never blocks" (:134-135): **it
cannot exit non-zero**. PUSH (:179) is likewise informational. Exit is `exit "$red"` (:183).

**echo** (.claude/skills/echo/): sweep.sh grounds a deep commission mechanically, the append-only
lexicon.md maps Rab's words to project terms, and work STOPS for his word before interpretation.

**wiki** (.claude/skills/wiki/ — new, itself untracked at HEAD: `?? .claude/skills/wiki/`).
Its laws (SKILL.md table): INDEX ≤120 lines, page ≤200, every page in INDEX, every relative link
resolves, stamps `last-verified` + `verified-against` (a real ancestor of HEAD), `*.private.md`
never tracked (the repo is public); `wiki.sh check` exits 1 on any measured red.

⚠ **The `.agents/` trap** — an untracked divergent copy at .agents/skills/{echo,muster}:
the muster copy has **no close.sh** (`ls .agents/skills/muster/`), its selftest.sh is the
pre-S103 build missing all four close cases (diff vs .claude copy: `251a252,312`), and its
SKILL.md points at a wrong path `bash .Codex/skills/muster/open.sh` (.agents/skills/muster/SKILL.md:23)
and prescribes the glass detector **without `--enforce`** (:89) — the exact SYM-046 form. A
session loading skills from `.agents/` gets a muster whose selftest passes all-green while the
mechanical close does not exist.

## 5 · The glass detector — signed silence

`observability/glass_detector.py` (519 lines) + `dispositions.json` + `acceptance.py`. Three
states: renderer-referenced · signed silence · GLITCH, "fatal under --enforce"
(glass_detector.py:17). **11 signed silences** in dispositions.json (9 INTERNAL, 1 EVIDENCE,
1 REPORT; `grep -c '"disposition":'` = 11), across 3 lanes: bench, widget, converter.
⚠ **A bare run exits 0 while listing glitches** — SYM-046 (SYMPTOM-INDEX.md:75). The only form
whose exit code means anything is `--since <pin> --enforce` (glass_detector.py:338, :463), which
is exactly what close.sh runs (close.sh:60-73).

## 6 · The docs map — all 46 files, one line each

46 files, 00–45 (42 .md + 4 .html; `ls docs/`). Genre tags are judgment from title + skim.

- 00 (guide) birth-era system overview
- 01 (guide) architecture: machines, lanes, data flow
- 02 (guide) Tailscale setup between the two machines
- 03 (guide) the Windows widget, birth era
- 04 (guide) the Linux receiver / allocator service
- 05 (guide) allocation rules (rules.toml)
- 06 (doctrine) the security model
- 07 (guide) development guide
- 08 (plan) roadmap
- 09 (guide) the Linux dashboard viewer
- 10 (plan) File Portal → Library Pipeline execution plan
- 11 (plan) GPU pipeline revamp — scope and phases
- 12 (plan) Phase 4 rewiring: the intake inversion
- 13 (doctrine) Control Room design — the projection law
- 14 (plan) remote projection: the phone as a window (design only)
- 15 (doctrine) the survival audit — the conversion fidelity gate
- 16 (doctrine) the Control Room becomes the widget's face (S34)
- 17 (guide) remote-access runbook: SSH + Sunshine over Tailscale
- 18 (doctrine) levers-and-heartbeats; §2 is close.sh's modularity gate
- 19 (doctrine) Opus 5 execution plan; :68 = the rebuild ritual (fmt leads)
- 20 (guide) the File Portal manual
- 21 (doctrine) the session closeout contract; epistemic tags
- 22 (showcase, html) engineering manual
- 23 (showcase, html) the life of a book + the transcribe repair
- 24 (showcase, html) the engine lever — investigation + simulator
- 25 (showcase, html) the design plan — mass, damping, one hero shot
- 26 (finding) the mass audit: findings and the gate
- 27 (plan) the acute loop diagnostic proposal
- 28 (plan) the repair ledger — what a rescore may honestly claim
- 29 (doctrine) the observability complex; §5 = glass detector + dispositions
- 30 (finding) the algedonic channels: built, and the hole left
- 31 (finding) Circle findings, S78
- 32 (doctrine) proxy substitution — symptom, condition, disease
- 33 (finding) Circle: does an embedded assistant fit File Portal?
- 34 (doctrine) the measurement language — numerator/denominator/conditions
- 35 (doctrine) the portal schema
- 36 (guide) the repository briefing — the subsystem map
- 37 (plan) the next-stage plan; §3 = the signature register
- 38 (guide) full system scope
- 39 (finding) memory-library inventory and analysis
- 40 (finding) the feedback-pathways think tank
- 41 (plan) conversion completeness — the P-0…P-6 integration plan
- 42 (finding) conversion-completeness research (the S97 external artifact)
- 43 (finding) the parallel sitting — two models, one session number
- 44 (plan) the S105 handoff — muster, then circle
- 45 (finding) the S105 Circle — the arc's three failure families

## 7 · docs/45's failure families

**F1** — the claim describes the *neighbour* of what was measured; no guard compares the sentence
to the probe (docs/45:35, :50-51). **F2** — recording discharges the obligation: the record is
honest and the duty dies there (docs/45:57). **F3** — plain engineering defects (docs/45:69).

## 8 · coordination/ — the two-model layer

- `relay.md` (200 lines): LLM-to-LLM recap, "two signals as one" — the newest entry addressed to
  your model is carried to Rab at open; you write yours back (UTC) before close (relay.md:1-9).
- `authorship.md` (46 lines): every prose section, ledger row, and doc a model writes carries
  `⟨claimed: <Model> · S<n> · <UTC date>⟩`; ledger session cells must open `S<n>:` (:14-20).
- `selftest.sh` (141 lines): the mechanical tripwire — entry shape, UTC stamps, the three
  required parts, the concordance amendment, carry-selection, ledger-row format (:2-8).

## Open items

- OPEN-TASKS.md §F — the record-integrity repair queue, esp. F3 (the four falsely-open SYM rows).
- OPEN-TASKS.md §A — the signature register: every decision a session may not make alone.
- SYM-046 (glass exit code) and SYM-045 (same-machine id collisions) — SYMPTOM-INDEX.md.
- docs/45 §6 bequest: Family 1 still has no check — nothing compares the artifact to the
  measurement; S106's closeout confirms the gap is live.
- Untracked governance surfaces at HEAD: OPEN-TASKS.md, .claude/skills/wiki/, .agents/ —
  tracking (or deleting the divergent .agents/ copy) is Rab's call.
