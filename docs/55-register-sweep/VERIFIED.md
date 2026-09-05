# VERIFIED.md — register sweep, verifier lane (Fable), HEAD `bde007d`, 2026-09-04

READ-ONLY sweep. Six lane outputs re-checked; every DONE/STALE/SUPERSEDED re-measured against HEAD by the verifier; >=3 OPEN rows per lane spot-checked. Tags: Verified = re-measured by the verifier this pass; (lane) = the lane's evidence, not re-derived; Observed = seen directly, no commit to cite; UNREAD = could not be checked read-only.

## Counts

- Rows in the sweep: **147** (146 from the six lanes + SYM-039, which no lane's slice held).
- Status: OPEN **121** · DONE **17** · STALE **5** · SUPERSEDED **1** · PROPOSED **3**.
- **Tickets that still need doing (OPEN + PROPOSED): 124** — effort S 60 · M 40 · L 24.
- By owner (OPEN+PROPOSED): RAB_SIGNATURE 53 · RAB_HANDS 13 · MECHANICAL 55 · CODEX 0 · BLOCKED 3.
- SYMPTOM-INDEX: 28 rows whose Status cell reads open at HEAD (close.sh's DEBT grep sees the same number); **3 of them are fixed in substance and mislabelled** (SYM-032, SYM-046, SYM-047) → 25 truly open symptoms.

## Verdicts on the lanes' register-changing calls (DONE / STALE / SUPERSEDED)

| Row | Lane said | Verifier verdict | Final | Checked against |
|---|---|---|---|---|
| A4 | DONE | CONFIRMED | DONE | 0fbb6e3 ancestor; row cell; docs/50:320 |
| A20 | DONE | CONFIRMED | DONE | main.js:561,665 |
| A22 | DONE | CONFIRMED | DONE | relay.md 55 Codex entries |
| A49 | STALE | CONFIRMED | STALE | S112 sign sheet; 7 build SHAs ancestors |
| B1 | DONE | CONFIRMED | DONE | acceptance.py:46; 57abcd9 |
| B4 | DONE | CONFIRMED | DONE | ci.yml:69-72 |
| B8 | DONE | CONFIRMED (nuance: the close measures the form; no prose parser) | DONE | close.sh:58-71; c9c0cf3 |
| B9 | DONE | CONFIRMED (nuance: pid not parent; 300 s window) | DONE | watcher.rs:118-135,182,212; watch_and_convert.py:584; f045a66 |
| D2 | DONE | CONFIRMED | DONE | 0fbb6e3 ancestor |
| F3 | STALE | OVERSTATED — 1 of 4 remains | OPEN | git show 97906a3 (col 3 only); SYMPTOM-INDEX:51 col 5 |
| F4 | DONE | WRONG — S96 §18 item 5 is a list item, not a ruling | OPEN | sessions/S96:313; S82:21 open card 08-16T03:42Z vs file date 08-15 |
| F5 | SUPERSEDED | CONFIRMED (A27 is OPEN, not dispositioned) | SUPERSEDED | OPEN-TASKS:150; docs/50:218 |
| F6 | STALE | CONFIRMED | STALE | wc/sha256 of MEMORY.md: 172 / 21,315 / cf2ed96d |
| F7 | DONE | CONFIRMED | DONE | ~/.claude/settings.json:3; session-bootstrap.md:35; zero .Codex in library |
| F10 | STALE | CONFIRMED | STALE | ls/find/git log --all |
| J4 | STALE | CONFIRMED (runtime UNREAD) | STALE | close.sh at HEAD and 623fe0a; SKILL.md:257 |
| J6 | STALE | CONFIRMED | STALE | relay.md:3078,3154,3251,3302,3390; T-004 header; f045a66 |
| J7 | STALE | OVERSTATED — contested record (SIGNED block vs later bus entries) | OPEN | DISCLOSURE-STANDARD.md:109-165 (6a7b306); relay.md:3103,3154; private/README.md 4f88715 |
| J28 | DONE | OVERSTATED — build done, row's own done-when unmet | OPEN | row text at HEAD; 7a68be5 ancestor |
| J29 | DONE | CONFIRMED | DONE | 8aa8936, d9bfaaa ancestors; SYM-067 cell |
| SYM-032 | DONE | CONFIRMED (fixed, mislabelled) | DONE | cols 3 vs 5; 3446f7c; 97906a3 |
| SYM-046 | OPEN | WRONG — fixed in substance by close.sh [2] | DONE | close.sh:58-71; c9c0cf3 |
| SYM-047 | OPEN | WRONG — fixed in substance by f045a66 | DONE | watcher.rs; watch_and_convert.py:584 |
| SYM-066 | DONE | CONFIRMED | DONE | cell; fidelity_audit.py runs_capped_at |
| SYM-067 | DONE | CONFIRMED | DONE | 8aa8936 ancestor |
| SYM-071 | DONE | CONFIRMED | DONE | c151e68 ancestor |
| SYM-072 | DONE | CONFIRMED | DONE | ba036f9, d9bfaaa ancestors |

Spot-checked OPEN rows (all CONFIRMED OPEN): A1 lane — A8, A11, A23, A24, A26, A28, A29 · A2 lane — A30, A38 (count now 7), A43, A46 · B lane — B6, B10, B13, B19, B28, B33 · DF lane — D5, D6, F1, F8, F11 · J lane — J5, J10, J12, J16, J23 · S lane — SYM-003, SYM-044, SYM-056, SYM-057, SYM-063, SYM-064.

## Corrections to OPEN rows (no status change, text is stale)

- A38 / J10: held/ holds **7** bundles, not four/five.
- A27 carries F5; its `Historical (S105)` is an observation tag, not a disposition.
- B28: the polling/inline-display half is built (status.rs:35, main.js applyStatusEvent); only the toast half is open; docs/08 v2 checkbox stale.
- SYM-044 / B10 / SYM-057 / A26: cited line numbers drifted (:235/:1268/:1594; :513; :558; :342) — same facts.
- SYM-056: Guard column should cite `latex_balance()` (fidelity_audit.py:421, `91973a4`, report-only).
- J7: the record is contested, not settled either way — Rab's one word settles it.
- J28: BUILT `7a68be5` + DEPLOYED; only the first-supersede observation remains.
- F3: narrowed to one cell (SYM-032 col 5).
- Owners corrected from CODEX to MECHANICAL where no row or relay assigns Codex: B19, SYM-034, SYM-049, SYM-053 (Codex is named as SYM-053's finder only). A49's remainder (OK-3/9/10/11/13) IS Codex's by MSG-FAB-0055.

## Decoys

All six lanes caught their planted decoy and none propagated it (verifier re-measured each target): A1 — A11 unsigned (zero hits S110-S119; docs/50:249) · A2 — memory library has no remote (`git remote -v` empty) · B — marker_version still `getattr(...,'unknown')` ×3 and the held manifest reads `"unknown"` · DF — OPEN-TASKS.md present, 93,307 bytes, never deleted · J — J10 unstruck, held 7, C0 breathed S109 · S — SYM-003 OPEN, D5 declared blind spot. Verifier's own section: the one measured falsity is **'Six Sonnet lanes classified every row'** — SYM-039 (Status `open`, SYMPTOM-INDEX:58) was in no lane's slice (its fix rides on D5); 'Sonnet' itself is UNREAD — register_sweep.py/.json record no lane model.

## The full table, grouped by owner

### RAB_SIGNATURE — 54 rows (53 still to do)

| ID | Section | Status | Effort | Do now | Evidence [tag] | Register note |
|---|---|---|---|---|---|---|
| A1 | A.1 | OPEN | S | Rab picks warn/fail/quarantine for out-of-range assets; nothing else needed. | docs/50:209 blocked-on-rab; no S104-S114 record signs asset posture (lane; not re-probed) [Verified] |  |
| A2 | A.1 | OPEN | L | Rab says go/hold on Stage 2 (converter tests + CI); negative cases already enumerated. | docs/50:191 Stage 2 GO blocked-on-rab; unsigned since S94 (lane) [Verified] |  |
| A3 | A.1 | OPEN | M | Rab says go/hold on Stage 3 verified seam (SHA-256 inventory.json + exporter verify). | docs/50:253 Stage 3 GO blocked-on-rab (lane) [Verified] |  |
| A5 | A.1 | OPEN | M | Rab picks fail-list / flag-only-localizer / receipt-note-only for the #598 tripwire. | docs/50:258/383 blocked-on-rab, E-P2 not built (lane) [Verified] |  |
| A6 | A.1 | OPEN | M | Rab picks the DPI approach (one-book probe vs render-to-budget vs leave+record). | docs/50:259/384 blocked-on-rab; no DPI probe commit (lane) [Verified] |  |
| A7 | A.1 | OPEN | S | Rab records the generative-SR ban (or defers with a ground-truth criterion); zero code. | docs/50:227/368 blocked-on-rab (lane) [Verified] |  |
| A8 | A.1 | OPEN | S | Rab picks 3, 4 or 5 to replace SPOT_CHECK_EVERY=10 at exporter.py:69. | Verifier re-probe: linux-converter/converter/exporter.py:69 `SPOT_CHECK_EVERY = 10` at HEAD [Verified] |  |
| A9 | A.1 | OPEN | S | Rab countersigns or revises the already-built stale-hold reap policy. | watch_and_convert.py:400 emits stale-hold-reaped (built); countersign unrecorded, docs/50:229 (lane) [Verified] |  |
| A10 | A.1 | OPEN | S | Rab countersigns or revises docs/34 rule 8. | docs/50:210 blocked-on-rab (lane) [Verified] |  |
| A11 | A.1 | OPEN | M | Rab picks two-engine steady state vs Ollama-off-the-machine; §6.1 gives the measurement. | Verifier re-probe: zero hits for 'Ollama off the machine\|wrapper decision' in sessions/S110-S119; docs/50:249 blocked-on-rab [Verified] |  |
| A12 | A.1 | OPEN | L | Rab decides build/don't on the GLM zone-keyed second reader; S84 probe is the proof. | no second_reader module in any .py; docs/50:190 (lane) [Verified] |  |
| A13 | A.2 | OPEN | S | Rab signs the ambient-chrome carve-out (<=7-13% clay, never animated) or orders desaturation. | docs/26:55 F8 unsigned; docs/50:211 (lane) [Verified] |  |
| A14 | A.2 | OPEN | S | Rab signs the docs/25 motion-ban amendment (travel vs ambient-idle) in one pass. | docs/26:54 F7 unsigned; docs/50:212 (lane) [Verified] |  |
| A15 | A.2 | OPEN | S | Rab signs the relabel: 'scan lane · agreement witness' / 'clean lane · fidelity witness'. | docs/26:53 F6 unsigned; docs/50:213 (lane) [Verified] |  |
| A16 | A.2 | OPEN | M | Rab signs null-not-1.0 + pages_scored display; needs its own mini-session. | docs/26:51 F4; fidelity_audit.py 'else 1.0' still live; docs/50:250 (lane) [Verified] |  |
| A17 | A.2 | OPEN | M | Rab signs the terracotta colour policy together with A13 so Dock+rail change once. | docs/26:50 F3; docs/50:251 blocked_by A13 (lane) [Verified] |  |
| A19 | A.3 | OPEN | S | Rab rules on session-per-work-item cadence; recent sessions already batch without a ruling. | docs/50:214 blocked-on-rab; S113/S114 batch items in practice, no ruling (lane) [Observed] |  |
| A23 | A.3 | OPEN | S | Rab decides: delete /echo (keep the lexicon) — skill still present. | Verifier re-probe: `ls .claude/skills` = echo muster relay-gate wiki [Verified] |  |
| A24 | A.3 | OPEN | M | Rab signs the cut to 6 core sections + Evidence and the 80-word check. | Verifier re-probe: docs/21:95 '## 4. The eighteen sections' unchanged [Verified] |  |
| A25 | A.3 | OPEN | S | Rab signs narrowing the tag law to Known Failures, Evidence and status sentences. | docs/21 tag law still broad; docs/50:216 (lane) [Verified] |  |
| A26 | A.3 | OPEN | S | Rab signs inverting glass's default to enforce-on, --report to opt out. | Verifier re-probe: observability/glass_detector.py:342 `--enforce` store_true (opt-in; row's :338 drifted) [Verified] |  |
| A27 | A.3 | OPEN | S | Rab rules: correct the S102/S103 ledger rows/CHANGELOG, or newer rows supersede. | OPEN-TASKS:150 tag `Historical (S105)` is the observation tag, not a disposition; docs/50:218 blocked-on-rab; F5 is its duplicate [Verified] |  |
| A28 | A.3 | OPEN | S | Rab signs docs/32 §5's three rules, already obeyed in 8 places. | Verifier re-probe: docs/32:134 reads '**Not signed.**' [Verified] |  |
| A31 | A.4 | OPEN | M | Rab formalises a post-close continuation form, or blesses the informal 'post-close' convention. | no post-close ledger form in CLAUDE_README §Session Protocol; informal 'post-close:' prefix in use (lane; F2 twin) [Verified] |  |
| A33 | A.5 | OPEN | S | Rab picks one of G1-G6 from docs/40 §10 before any platform-shaped build. | docs/50:189 blocked-on-rab; no §10 gate signed (lane) [Verified] |  |
| A37 | A.5 | OPEN | L | Rab signs a design + Survival Audit A-B gate for the scan-lane challenger first. | docs/50:193 blocked-on-rab (lane) [Verified] |  |
| A38 | A.5 | OPEN | M | Rab commissions the held/ product session; count is now 7 bundles, not 4. | Verifier re-probe: `ls ~/ml/library/held` = 7 bundles (0d68f0e0 14c66834 21bfdffc 26bd434d b6fbdd75 b7b711d4 c5afd9ed); row says four, docs/50:144 five [Observed] |  |
| A39 | A.5 | OPEN | M | Rab schedules the guided Valentine session (deferred a sixth time). | no S110-S114 mention; docs/50:145 (lane) [Verified] |  |
| A40 | A.5 | OPEN | S | Rab decides the stale Cybernetics copy's fate and the Textor re-download. | docs/50:222 blocked-on-rab; possible overlap with A41 (lane) [Verified] |  |
| A41 | A.5 | OPEN | S | Rab checks the vault copy and releases/removes the held duplicate c5afd9edcf620fc6. | held/c5afd9edcf620fc6 present (verifier ls); vault half UNREAD (lane) [Observed] |  |
| A42 | A.5 | OPEN | S | Rab decides the windows-converter test-suite question (docs §8.3). | docs/50:224 blocked-on-rab (lane) [Verified] |  |
| A44 | A.5 | OPEN | L | Rab signs Stage 2 (intake-contract change) before hOCR alignment-gate work starts. | no hOCR code; docs/50:202 blocked-on-rab XL (lane) [Verified] |  |
| A45 | A.5 | OPEN | M | Rab signs docs/30 §5's algedonic questions (silence/liveness, morning-note vs Gmail, M/ack). | docs/30 §5 awaiting signature; docs/50:256 (lane) [Verified] |  |
| A46 | A.5 | OPEN | M | Rab chooses: keep filename-order queue, or authorise operator reordering. | Verifier re-probe: windows-widget/src/room.js:158 'ORDER control ... awaiting Rab's signature' [Verified] |  |
| A48 | A.5 | OPEN | S | Rab answers the 2 remaining docs/36 §8 questions. | docs/36 §8 unchanged; docs/50:226 (lane) [Verified] |  |
| B2 | B.1 | OPEN | S | Rab decides: delete .agents/ or keep it marked; the mirror's generator is unidentified. | .agents/ present, gitignored (.gitignore:71), generator unidentified (lane) [Observed] |  |
| B3 | B.1 | OPEN | L | Sign or dispose the ~57 pre-existing glitches; the --since gate cannot retire old debt. | count not re-measured (no runs); docs/50 lists 57 unsigned glitches (lane) [UNREAD] |  |
| D7 | D | OPEN | L | Rab greenlights (or not) the ThinkPad enrichment consumer and docs/14 Phase A phone window. | third clause self-corrected in the row; enrichment consumer + docs/14 Phase A unbuilt, docs/50:265 blocked-on-rab (lane) [Verified] |  |
| F2 | F | OPEN | S | Write the 'post-close:' prefix + same-row-narrative convention into the Session Protocol; Rab signs. | Session Protocol has no post-close rule; dozens of 'post-close:' commits since (lane; A31 twin) [Verified] |  |
| F9 | F | OPEN | S | Rab prioritises or discards S96's inherited next-entry list. | docs/50:235 blocked-on-rab; S97:267-268 (lane) [Verified] |  |
| F12 | F | OPEN | S | Ask Rab whether RAM was physically added since 2026-08-21; correct SYM-051(b) with the date. | docs/50:234 blocked-on-rab; nobody asked (lane) [Verified] |  |
| J6 | J | STALE | M | Rab decides whether T-004 proceeds; if yes, Codex's review of the EXTRACTED schema is step one. | Verifier: relay.md:3078/:3154 (MSG-FAB-0029/0030, 08-24/25) said 'blocked on your budget, not on Rab'; :3251/:3302 (MSG-FAB-0031/0033, 08-26/27) say 'T-004 … Rab's alone'; :3390 (MSG-CDX-0012, 08-27) 'remains UNREAD'; Codex's usage returned (f045a66 S113); T-004-EXTRACTED-SCHEMA.md still 'DRAFT, unsigned; Codex's review has not happened' (precondition) [Verified] | 2026-09-04 verifier (HEAD bde007d): STALE — Codex's usage returned in S113 (f045a66), so 'blocked on Codex's usage' is dead; the bus's last words are 'T-004 … Rab's alone' (relay.md:3302) and 'remains UNREAD' (:3390); the schema file still names Codex's review as the precondition. Attribution now: Rab's call, Codex's review first. |
| J7 | J | OPEN | S | Rab confirms or strikes the blanket-signature reading of DISCLOSURE-STANDARD.md §SIGNED; the bus later called it unsigned. | Verifier: DISCLOSURE-STANDARD.md:109-165 SIGNED block (6a7b306, 2026-08-24 20:21Z) reads Rab's blanket 'I sign on everything that needs work that we've discussed' as covering it and declares D1/D3-D6 discipline-only permanent by design; the same lane's relay entries later that day and next (relay.md:3103 MSG-FAB-0029 21:17Z; :3154 MSG-FAB-0030 08-25) say the standard and the private-layer doctrine 'remain unsigned and his'; coordination/private/README.md (4f88715) stands on Rab's quoted correction. Contested record — lane's STALE is OVERSTATED [Verified] |  |
| J10 | J | OPEN | M | Disposition the 7 held bundles (maiden voyage 14c66834bdfeaa2e among them); C0's third done-when unmet. | Verifier re-probe: OPEN-TASKS row `\| J10 \|` unstruck; held/ = 7 bundles; C0 breathed S109 per MEMORY (not S113) [Verified] |  |
| J13 | J | OPEN | M | Rab decides on the phase-transition relay; if yes, test N concurrent lanes first. | docs/47 §8 'TESTED, NOT ADOPTED'; N concurrent lanes Unknown (lane) [Verified] |  |
| J23 | J | OPEN | M | Rab signs or amends the 13 contested census dispositions. | Verifier re-probe: docs/51-numeration-census.md:701 '13 contested rows … until Rab signs' [Verified] |  |
| J25 | J | OPEN | L | Rab signs the converter bake-off design and the Qwen3-VL-4B download; then head-to-head on p.805. | row refined 2026-09-04; Qwen slot came back unsigned (lane) [Verified] |  |
| J31 | J | PROPOSED | M | Rab signs the D-1 verdict rule: re-audit a repaired held bundle against both references. | row says PROPOSE_AMENDED, UNSIGNED; docs/54 README + 5bea22a/bde007d at HEAD (verifier: SHAs ancestors) [Verified] |  |
| J32 | J | PROPOSED | M | Rab signs Proposal A (normalised analyst comparison) and/or B (per-chunk survival guard). | same fleet/commits; six-book ladder measured (lane) [Verified] |  |
| J33 | J | PROPOSED | L | Rab picks the sidecar shape and signs the vault-side OUT rule; then teach the six guards. | six exactly-one-.md guard sites not re-verified line by line (lane, UNREAD) [UNREAD] |  |
| SYM-027 | SYMPTOM-INDEX | OPEN | L | Disposition the remaining unsigned glass fields; wire or sign the silence of seams[]/reverse_sample. | cell OPEN with S93 update; no later commit (lane) [Verified] |  |
| SYM-051 | SYMPTOM-INDEX | OPEN | S | Rab accepts it as environmental residue and closes the row, or keeps it as a standing warning. | cell 'OPEN - environmental, not a code defect'; no guard possible for (a) (lane) [Verified] |  |
| SYM-062 | SYMPTOM-INDEX | OPEN | M | Rab defines/signs a verifiable human-authority artifact for gate.py resolve, or keeps it human-only. | cell OPEN; gate.py resolve gated only by len(decision)>=10 (lane) [Verified] |  |
| SYM-073 | SYMPTOM-INDEX | OPEN | L | Rab signs docs/54's J31 (verdict rule D-1) and J33 (retain the pre-analyst body) before the remedy is built. | cell 'OPEN — CAUSE FOUND 2026-09-04'; docs/54 J31/J33 PROPOSED, unsigned (verifier: 23fc659..bde007d ancestors) [Verified] |  |

### RAB_HANDS — 13 rows (13 still to do)

| ID | Section | Status | Effort | Do now | Evidence [tag] | Register note |
|---|---|---|---|---|---|---|
| A30 | A.4 | OPEN | S | Rab does one manual Ctrl+Z on the live bench to ratify 0f0e83f. | Verifier re-probe: sessions/S108-SIGN-SHEET.md:11 A30 row ends in blank ink `______`; 0f0e83f ancestor [Verified] |  |
| A34 | A.5 | OPEN | S | Rab narrates the S97 sketch's nodes 1-3, the stars, and the final circle. | no 'narrated legend' in S11x records; docs/50:221 (lane) [Verified] |  |
| A43 | A.5 | OPEN | S | Rab creates a private GitHub repo and pushes the memory library (S108 sheet item 10). | Verifier re-probe: `git remote -v` in the memory library prints nothing (HEAD b208369); S108 sign sheet item 10 blank [Verified] |  |
| B17 | B.4 | OPEN | M | Re-run the A-B-A throughput measurement on a confirmed-idle card with occupancy recorded. | backend_parity.json gitignored, mtime Aug 16 (lane) [Observed] |  |
| B18 | B.4 | OPEN | S | Confirm occupancy on the n=30 data (or re-run) and replace the withdrawn ratios; merge with B17. | same artifact as B17; n=30 exists, occupancy Unknown (lane) [Observed] |  |
| B20 | B.4 | OPEN | S | Vary -ub on one engine before any two-product conclusion (GPU run). | backend_parity.py:48-49 documents -ub gap, no sweep (lane) [Verified] |  |
| B23 | B.4 | OPEN | L | Adjudicate the 219 of 239 IV uncovered pages never reviewed. | docs/52-53 unrelated to the 219-page backlog; docs/50:195 open (lane) [Verified] |  |
| B29 | B.5 | OPEN | M | Package the widget and write second-machine install steps. | no second-machine install doc; C4559805 is same-machine adoption (lane) [Verified] |  |
| B30 | B.5 | OPEN | S | Add the README screenshot/GIF and finalise CONTRIBUTING.md (repo already public). | no CONTRIBUTING.md; no README GIF (lane) [Verified] |  |
| B31 | B.5 | OPEN | M | Run the end-to-end manual hardware test across v0 and v1.5. | docs/08:16,41 unchecked; docs/50:260 blocked-on-rab (lane) [Verified] |  |
| D8 | D | OPEN | S | Rab does the remaining eyes-on-glass items; cite S102 for the guard-exercise half. | S94 guard exercise recorded S102 (PID-based); other eyes-on-glass items unrecorded; docs/50:232 (lane) [Verified] |  |
| J28 | J | OPEN | S | Nothing to build; observe blocks.json ride the first real supersede (next J24-era re-drop), then strike. | Row at HEAD: 'BUILT 7a68be5 (OUT by Rab's decision) — DEPLOYED 2026-09-04T02:11Z … Row stays OPEN until that observation'; 7a68be5 ancestor (verifier); exporter _record_blocks on both paths (lane). Lane's DONE is OVERSTATED: the build is done, the row's own done-when (first real supersede observed) is not [Verified] |  |
| J30 | J | OPEN | M | Run marker_blocks.py on the WTPDF/ISO specimens (GPU) and compare block order to the declared tree. | S114:655 GPU slot came back unsigned; no marker_blocks run on WTPDF/ISO (lane) [Verified] |  |

### MECHANICAL — 76 rows (55 still to do)

| ID | Section | Status | Effort | Do now | Evidence [tag] | Register note |
|---|---|---|---|---|---|---|
| A4 | A.1 | DONE | S | Strike the row; it sits under 'items still OPEN' by inertia only. | Row's own cell: SIGNED S108, BUILT 0fbb6e3; 0fbb6e3 exists, ancestor of HEAD (git merge-base); docs/50:320 'stale' [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — SIGNED S108, BUILT `0fbb6e3` (ancestor of HEAD); docs/50:320 already 'stale'. Strike. |
| A20 | A.3 | DONE | S | Strike; built and resolved S108. | Verifier re-probe: windows-widget/src/main.js:561,665 render 'last pipeline event: ...'; row's own RESOLVED S108; docs/50:318 stale [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — main.js:561/665 render 'last pipeline event: <age>' (RESOLVED S108 lane F); docs/50:318 'stale'. Strike. |
| A22 | A.3 | DONE | S | Strike; signed KEPT, premise dead. | Verifier re-probe: `grep -c '⟨from: Codex'` relay.md = 55; row's own SIGNED S108 KEPT; docs/50:319 stale [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — SIGNED S108 KEPT; relay.md carries 55 ⟨from: Codex⟩ entries at HEAD. Strike. |
| A29 | A.3 | OPEN | M | Wire muster/echo/relay-gate/glass-acceptance selftests into CI; smallest slice already landed. | Verifier re-probe: ci.yml:92 figure_coverage_selftest, :99 acceptance.py (warn-only); no muster/relay-gate/echo suite in ci.yml [Verified] |  |
| A32 | A.4 | OPEN | M | Build the assay surface for the operator lever; A4 no longer blocks it. | A4 signed+built 0fbb6e3, so the blocker is gone; docs/50:289 'open' (lane) [Verified] |  |
| A47 | A.5 | OPEN | L | Run the adversarial-challenge fleet against docs/40 theses A-D and report; commission is signed. | docs/50:310 'signed' = commissioned S111, not executed; no fleet run/report found (lane) [Verified] |  |
| B1 | B.1 | DONE | S | Strike; fixed at 57abcd9. | Verifier re-probe: observability/acceptance.py:46 expects ('recent_audits','glass'); 57abcd9 ancestor of HEAD [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — acceptance.py:46 expects recent_audits=glass; `57abcd9` (41/41). Strike. |
| B4 | B.1 | DONE | S | Strike; windows-converter is in CI lint (warn-only). | Verifier re-probe: .github/workflows/ci.yml:69 'Lint (windows-converter, warn-only)' step, :72 `ruff check .` [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — ci.yml:69-72 lints windows-converter (RESOLVED S108 wave 1b). Strike. |
| B5 | B.1 | OPEN | M | Build the in-browser DOM test run for bench.html; the 19-test harness covers the named regressions. | test_bench_page.py exists (abe4830); no in-browser DOM run (lane) [Verified] |  |
| B6 | B.2 | OPEN | S | Replace the three getattr sites with importlib.metadata.version('marker-pdf'). | Verifier re-probe: convert_and_ship.py:235,1268,1594 `getattr(marker,'__version__','unknown')`; no importlib.metadata in any .py; held/14c66834bdfeaa2e/manifest.json:16 marker_version 'unknown' [Verified] |  |
| B7 | B.2 | OPEN | S | Build the id-preflight (re-read counter + grep the id) into muster.sh or echo/sweep.sh. | no id-preflight in muster.sh or echo/sweep.sh (lane) [Verified] |  |
| B8 | B.2 | DONE | S | Strike B8; flip SYM-046's Status cell to FIXED (close.sh [2], c9c0cf3). | Verifier read close.sh in full: [2] GLASS (lines 58-71) runs `glass_detector.py --since $PIN --enforce` and sets red=1 on failure; header :12-13 names SYM-046; born c9c0cf3 2026-08-20 (ancestor). No parser of the closeout's prose — none needed once the close measures the scoped form itself [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE in substance — close.sh [2] GLASS (`c9c0cf3`, 2026-08-20; header cites SYM-046) runs `--since <pin> --enforce` at every close and exits 1 on an unsigned glitch. The literal 'refuse a closeout whose CLAIM lacks the form' text-check is not built and is moot once the close measures the form itself. Strike; flip SYM-046 (docs/50:125 still 'open'). |
| B9 | B.2 | DONE | S | Strike B9; flip SYM-047's cell (f045a66); keep the hand census for a writer silent >300 s. | Verifier read watcher.rs:102-230,268-310 + watch_and_convert.py:214-236,548-590: watcher writes .intake-state.json {v:1, writer_pid} every poll tick (:584 inside the loop, POLL_S=5); widget intake_writer_pid() (:118, v==1, <=300 s old) + pid_alive(); status() :182 reports a live foreign writer 'running'; start() :212 refuses to spawn beside it; stop() tree-kills the writer; main.js:613-627 watcher_status at boot. f045a66 ancestor [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — `f045a66` (Conveyor State, 2026-08-31): the watcher's `.intake-state.json` carries writer_pid, refreshed every <=5 s (watch_and_convert.py:584); the widget reads it at boot (main.js:613, watcher.rs:182), refuses a second watcher beside a live writer (watcher.rs:212) and tree-kills it on stop. Residual: pid not parent; a writer silent >300 s (watcher.rs:128) is invisible — SYM-047's hand census stays for that case. Strike; flip SYM-047 (docs/50:126 still 'open'). |
| B10 | B.2 | OPEN | L | Build stroke-geometry clustering in figure_coverage.py; needs its own calibration. | Verifier re-probe: figure_coverage.py:513 `if _rect_area(r) <= 0: continue` (header :37 cites :300 — drifted) [Verified] |  |
| B11 | B.2 | OPEN | M | Fix the supersede copy in main.js/room.js and add a tripwire against 'pending' regressing. | main.js:934 / room.js:462 still 'swap: manual ... pending' (lane) [Verified] |  |
| B12 | B.2 | OPEN | S | Capture Ollama's own server log at a SYM-034 stall; only the client side exists. | no ollama server-log capture in backend_parity.py/analyst.py (lane) [Verified] |  |
| B13 | B.3 | OPEN | S | Add bench buttons wiring the proven /api/triage, /api/report, /api/ledger endpoints. | Verifier re-probe: no id=triage/report/ledger element in prototypes/repair-bench/bench.html [Verified] |  |
| B14 | B.3 | OPEN | S | Lever MIN_SIDE_PT and MAX_PAGE_FRACTION (env/CLI) and add a waiver path. | figure_coverage.py:103-104 MIN_SIDE_PT/MAX_PAGE_FRACTION unlevered (lane) [Verified] |  |
| B15 | B.3 | OPEN | M | Design and add the omission-class signature-bank entry. | no omission-class bank entry (lane) [Verified] |  |
| B16 | B.3 | OPEN | S | Wire seams[] and reverse_sample into at least one renderer. | seams[]/reverse_sample unreferenced in any renderer (lane) [Verified] |  |
| B19 | B.4 | OPEN | L | Build the analyst's llama.cpp call path with enable_thinking:false and IMG-marker-safe truncation. | Verifier re-probe: analyst.py:27 OLLAMA_URL hardcoded; row text names no Codex owner (owner corrected from lane's CODEX) [Verified] |  |
| B21 | B.4 | OPEN | S | Map one degeneration zone's lines to its page, render, probe. | docs/50:274 open; no mapped-page test (lane) [Verified] |  |
| B24 | B.5 | OPEN | M | Build events rotation, verified_from stamps, cross-day date stamp. | no verified_from / events rotation in src-tauri (lane) [Verified] |  |
| B26 | B.5 | OPEN | S | Remove the wrong-page embed in the Valentine bundle (vault-side read needed first). | Valentine bundle lives in the vault; UNREAD from this repo (lane) [UNREAD] |  |
| B27 | B.5 | OPEN | S | Build 'resume auto-detect-analyzed' (Desktop one-liner). | no 'auto-detect-analyzed' anywhere in code (lane) [Verified] |  |
| B28 | B.5 | OPEN | M | Add the toast/notification half only; status.json polling and inline display are built (docs/08 checkbox stale). | Verifier re-probe: status.rs:35 fetch_events exists (polling half built); zero 'toast' in main.js/room.js [Verified] |  |
| B32 | B.5 | OPEN | L | Verify U01-U06 against HEAD independently; U01 confirmed, U04 needs a Rust-side trace. | U01 re-probed present; U04 inconclusive; U02/03/05/06 unchecked (lane) [Observed] |  |
| B33 | B.5 | OPEN | M | Bound/force-noninteractive credential fill inside close.sh; distinguish 'not a repo' from 'ownership refused'. | Verifier read close.sh: :100 bare `git credential fill` (no timeout/env inside the script); :360-361 one generic 'not a git repo' branch [Verified] |  |
| D2 | D | DONE | S | Strike; collected S108. | Row's own COLLECTED S108 (0fbb6e3); 0fbb6e3 ancestor of HEAD (verifier) [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — COLLECTED S108 at `0fbb6e3` (ancestor of HEAD). Strike. |
| D3 | D | OPEN | L | Build the check that compares a recorded claim to the probe that produced it (docs/45 §6.2). | only §6.2 (Family-1 claim-vs-probe check) remains; nothing in S108-S114/docs/54 builds it (lane) [Verified] |  |
| D4 | D | OPEN | M | Run a Circle that counts guards-with-tripwire vs without, scoring docs/32 §6's prediction. | docs/32 §6/§7 'Not signed'; no scoring Circle run (lane) [Verified] |  |
| D5 | D | OPEN | S | Fix SYM-039's named drift instances (CLAUDE.md counts, SYM-014 guard) and flip its status. | Verifier re-probe: SYMPTOM-INDEX:58 SYM-039 Status cell `open` — fixes assigned to Desktop [Verified] |  |
| D6 | D | OPEN | S | Re-check both messages against reality and flip their status fields, or say why they stay open. | Verifier re-probe: both coordination/messages files line 6 `status: open` [Verified] |  |
| F1 | F | OPEN | S | Insert a matching header+separator directly above line 1972 so the second ledger block renders. | Verifier re-probe: CLAUDE_README.md:1126-1127 header+separator; :1972 bare pipe row (S79) after prose, no header; file is 2009 lines [Observed] |  |
| F3 | F | OPEN | S | Flip SYM-032's Status cell (col 5) to FIXED-S94 — 97906a3 wrote the verdict into col 3 — then correct F3's 'RESOLVED'. | Verifier: `git show 97906a3` changed SYM-032's Root-cause column (col 3) only; SYMPTOM-INDEX:51 col 5 still opens with `open` (symcols split); ffc7b8a fixed SYM-033/041/042 cols; docs/50:130,339 flag it. Lane's STALE is OVERSTATED: 1 of 4 remains [Verified] |  |
| F4 | F | OPEN | S | One-line annotation: S82 file named by local date, opened 2026-08-16T03:42Z UTC — or Rab rules it Historical. | Verifier: S96 §18 item 5 (sessions/S96:313) is a list item, not a 'leave as-is' ruling — lane's DONE is WRONG. S82 file header '2026-08-15', its open card 2026-08-16T03:42Z UTC (S82:21), ledger row dated 2026-08-16 (:1975): a Toronto-local vs UTC naming artifact; SKILL.md:181 names the file by date with no timezone [Verified] |  |
| F5 | F | SUPERSEDED | S | Strike F5 as A27's duplicate; A27 stays open for Rab. | OPEN-TASKS:150 A27 carries the same ask verbatim; A27 is OPEN (docs/50:218 blocked-on-rab); F5 :322 says bare 'open' [Verified] | 2026-09-04 verifier (HEAD bde007d): SUPERSEDED by A27 (same ask, OPEN-TASKS:150). A27 is still OPEN — its `Historical (S105)` is the observation tag, not a disposition. Strike F5. |
| F6 | F | STALE | S | Re-write the numbers (172 / 21,315, under the limit); keep M5 growth as a watch item, not a ticket. | Verifier re-measure: canonical MEMORY.md = 172 lines / 21,315 bytes / sha256 cf2ed96d…; under the ~200-line limit; compacted at the S112 (2026-08-30) and S113 (2026-09-01) closes per its own TIME-STATE [Verified] | 2026-09-04 verifier (HEAD bde007d): STALE — MEMORY.md re-measured 172 lines / 21,315 bytes (sha256 cf2ed96d…), under the ~200-line limit; compacted at the S112 and S113 closes. The 220/25,237 measurement no longer holds; docs/45 M5 growth remains a watch item. |
| F7 | F | DONE | S | Strike; cite the settings.json pin as the reconciliation. | Verifier: ~/.claude/settings.json:3 pins autoMemoryDirectory to the ~/.claude/... library; library session-bootstrap.md:35 records the pin (git baseline 0087a22, S96); zero `.Codex` mentions in the library; S95:48,161-163 recorded the ambiguity [Observed] | 2026-09-04 verifier (HEAD bde007d): DONE — one canonical namespace: `~/.claude/settings.json:3` autoMemoryDirectory → `~/.claude/projects/C--Users-Bndit-Documents-Claude-Code-Memory-Backup/memory`; the library's session-bootstrap.md:35 records it (baseline `0087a22`, S96); no `.Codex` path remains in the library (C:/Users/Bndit/.Codex is the Codex CLI's own home). Strike. |
| F8 | F | OPEN | S | Correct CLAUDE_README.md:1995's 'glass 0' in place and append S97's missing correction. | Verifier re-probe: CLAUDE_README.md:1995 S100 row still carries bare 'glass 0'; S97 correction absent (lane) [Verified] |  |
| F10 | F | STALE | S | Strike; the file is gone. | Verifier re-probe: `ls survival-audit-spec.md` absent; `find` none; `git log --all -- '*survival-audit-spec*'` empty (never tracked) [Observed] | 2026-09-04 verifier (HEAD bde007d): STALE — survival-audit-spec.md is absent from the tree and was never tracked (no deleting commit exists to cite; absence is the evidence). Strike. |
| F11 | F | OPEN | L | Keep working the register down row by row (this sweep is that); do not delete it. | Verifier re-probe: OPEN-TASKS.md present at HEAD, 93,307 bytes, never deleted (`git log --diff-filter=D` empty) [Observed] |  |
| J3 | J | OPEN | M | Build a fleet PROCESS census (list/kill live servers at run end) beside the digest census. | SYM-054 open; no process census in any selftest (lane) [Verified] |  |
| J4 | J | STALE | S | Re-time close.sh at the next close and name the slow step; the growing suites live in CI/selftests, not close.sh. | Verifier read close.sh at HEAD and at 623fe0a (2026-08-24): the only suites it runs are conditional cargo fmt/clippy/test (windows-widget touched) and the wiki selftest.sh (11 tripwires); muster/relay-gate/echo selftests are invoked per SKILL.md:257 'when muster.sh or open.sh changes', not at close; no commit ever added suites (git log -S selftest: only 0bec6a7 census). Runtime UNREAD (no runs) [Verified] | 2026-09-04 verifier (HEAD bde007d): STALE — close.sh never ran the three growing suites (at HEAD and at 623fe0a it runs only conditional cargo fmt/clippy/test + wiki selftest.sh, 11 tripwires); the muster/relay-gate/echo suites run per SKILL.md:257, not at close. The 8m37s is UNREAD read-only — re-time at the next close and name the step (cargo clippy on a cold target is the likely one). |
| J5 | J | OPEN | L | Build the live-server (T3/T4/T20/T21/T12), catcher-cycle (T24-27) and end-to-end T28 suites. | Verifier re-probe: prototypes/relay-room/test_room.py:61 NOT_YET = [T3,T4,T12,T20,T21,T24-T27_live,T28] [Verified] |  |
| J12 | J | OPEN | M | Give NEGATIVE CONTROL / RESIDUE / HONEST NULLS / anti-correlation each a violating case; fold wf_d92d7e9a-f2d's 3/3 decoys in. | Verifier re-probe: docs/47:127 'Intended — signed, unexercised' [Verified] |  |
| J14 | J | OPEN | M | Build the pre-analyst structural LaTeX validator SYM-056 calls for. | SYM-056 OPEN; latex_balance is report-only (91973a4), no pre-analyst gate (lane) [Verified] |  |
| J16 | J | OPEN | S | Render widget:age_s on the Room queue panel; wiring only, deploy is Rab's. | Verifier re-probe: observability/dispositions.json:352 census:N-099 GLASS [Verified] |  |
| J29 | J | DONE | S | Strike; built, signed, fleet-verified. | Verifier: 8aa8936 and d9bfaaa ancestors of HEAD; row cell 'BUILT 8aa8936 — signed Rab 2026-09-04'; SYM-067 cell FIXED with the same numbers [Verified] | 2026-09-04 verifier (HEAD bde007d): DONE — BUILT `8aa8936`, amended `d9bfaaa` (fleet wf_1e69e60b-b45 GO), signed Rab 2026-09-04; SYM-067 reads FIXED. Strike. |
| SYM-039 | SYMPTOM-INDEX (added by verifier — in no lane's slice) | OPEN | S | Fix the named drift instances (CLAUDE.md test counts, SYM-014 guard 200 vs 80) and flip the cell; D5 carries it. | Verifier: SYMPTOM-INDEX:58 Status `open` — fixes assigned to Desktop (wip-handoff §2.6); SYM-018's instance already struck in its own cell; CLAUDE.md counts / SYM-014 guard instances UNREAD [Observed] |  |
| SYM-003 | SYMPTOM-INDEX | OPEN | L | Build a real loop-vs-legitimate-table discriminator; J29 leaves table-row loops invisible (D5). | Verifier re-probe: Status cell OPEN; degeneration_selftest.py:22,110 declare D5 'a loop that emits ONLY table rows is invisible' — J29 fixed sparse-table false positives only [Verified] |  |
| SYM-024 | SYMPTOM-INDEX | OPEN | S | Wait for the next recurrence; resume-stderr.log now shows invoke-reject vs died resume. | cell `open` — hardened not root-caused; d74c0c1 ancestor (lane) [Verified] |  |
| SYM-032 | SYMPTOM-INDEX | DONE | S | Flip the Status cell (col 5) to FIXED-S94 to match col 3. | Verifier: col 3 'FIXED-S94 / residual-display-signal (verdict added S108 per F3…)', col 5 still opens `open` (symcols split); 3446f7c card mutex ancestor; 97906a3 edited col 3 only; docs/50:339 'stale' [Verified] | 2026-09-04 verifier (HEAD bde007d): FIXED-S94, cell mislabelled — `3446f7c` (card mutex) is an ancestor of HEAD; `97906a3` wrote the verdict into the Root-cause column while the Status column still opens with `open`. Flip col 5 to FIXED-S94 / residual-display-signal. |
| SYM-034 | SYMPTOM-INDEX | OPEN | L | Root-cause the single Ollama request stall (one observation, 300 s ceiling). | cell OPEN, cause unknown; row names no Codex owner (owner corrected from lane's CODEX) [Verified] |  |
| SYM-043 | SYMPTOM-INDEX | OPEN | S | Update main.js/room.js supersede copy; add a regression assertion. | cell OPEN; main.js/room.js copy unchanged (lane; B11 twin) [Verified] |  |
| SYM-044 | SYMPTOM-INDEX | OPEN | S | Replace the getattr stamp sites with importlib.metadata.version('marker-pdf') (B6 twin). | Verifier re-probe: getattr sites at convert_and_ship.py:235/1268/1594 (row cites :781/:979 — drifted); no importlib.metadata anywhere [Verified] |  |
| SYM-045 | SYMPTOM-INDEX | OPEN | M | Build the id-preflight in muster.sh / echo sweep.sh. | cell OPEN; no preflight built (lane; B7 twin) [Verified] |  |
| SYM-046 | SYMPTOM-INDEX | DONE | S | Flip the Status cell to FIXED (close.sh [2], c9c0cf3); keep the prose rule for closeouts written without close.sh. | Verifier: close.sh:58-71 [2] GLASS runs `--since $PIN --enforce`, red=1 on failure; header :12-13 names SYM-046; c9c0cf3 (2026-08-20, S103) ancestor; the row's 'no mechanical guard yet' predates it. Lane's OPEN is WRONG [Verified] | 2026-09-04 verifier (HEAD bde007d): FIXED in substance, cell mislabelled — close.sh [2] (`c9c0cf3`, 2026-08-20) runs `glass_detector.py --since <pin> --enforce` at every close and exits 1 on an unsigned glitch. Flip the cell; the closeout-prose rule stays as discipline. |
| SYM-047 | SYMPTOM-INDEX | DONE | S | Flip the Status cell to FIXED (f045a66) with the >300 s residual named; keep the hand census for it. | Verifier: f045a66 (2026-08-31) — watcher writes .intake-state.json writer_pid every <=5 s (watch_and_convert.py:584); widget checks it at boot (main.js:613 → watcher.rs:182) and refuses a second watcher beside a live writer (watcher.rs:212); stop() tree-kills it. Residual: pid not parent; writer silent >300 s invisible (watcher.rs:128). Lane's OPEN is WRONG [Verified] | 2026-09-04 verifier (HEAD bde007d): FIXED in substance, cell mislabelled — `f045a66` Conveyor State: the watcher's `.intake-state.json` carries writer_pid (refreshed every <=5 s); the widget refuses to start a second watcher beside a live writer and reports it at boot. Residual: pid not parent; a writer silent >300 s is invisible — the hand census stays for that case. Flip the cell. |
| SYM-049 | SYMPTOM-INDEX | OPEN | L | Build stroke-geometry-aware clustering in figure_coverage.py; calibrate on Cyb p34/p78 (B10 twin). | cell OPEN; figure_coverage.py:513 zero-area drop (verifier); row names no Codex owner (owner corrected) [Verified] |  |
| SYM-053 | SYMPTOM-INDEX | OPEN | L | Build rendered-source-region vs final-crop pixel comparison for scan-lane pages. | cell OPEN; no rendered-region vs crop detector; Codex named only as the finder (owner corrected from lane's CODEX) [Verified] |  |
| SYM-054 | SYMPTOM-INDEX | OPEN | M | Add an end-of-fleet-run process/port census beside the digest census. | cell `open`; no process census (lane; J3 twin) [Verified] |  |
| SYM-055 | SYMPTOM-INDEX | OPEN | S | Add the independently-computed-hash assertion + 64-hex length check to relay-gate/selftest.py. | cell OPEN; the one test case not added (lane) [Verified] |  |
| SYM-056 | SYMPTOM-INDEX | OPEN | M | Cite latex_balance() in the Guard column; build/sign the pre-analyst reject/flag gate. | Verifier re-probe: fidelity_audit.py:421 `def latex_balance` (91973a4, report-only) — Guard column's 'none exists anywhere' is stale; gate unbuilt [Verified] |  |
| SYM-057 | SYMPTOM-INDEX | OPEN | S | Return None/UNREAD (not 1.0) on empty windows and record the window count in the manifest. | Verifier re-probe: fidelity_audit.py:558 still returns {'doc_survival': 1.0, 'runs': []} on empty windows (row's :403 drifted); :513 `if total_windows else 1.0` [Verified] |  |
| SYM-058 | SYMPTOM-INDEX | OPEN | S | Label the Dock's survival number by phase at main.js:940. | cell OPEN Verified 2026-08-28; main.js:940 unlabelled (lane) [Verified] |  |
| SYM-059 | SYMPTOM-INDEX | OPEN | S | Split analyst vs converter verdicts at main.js:935-941; fixture where they diverge. | cell OPEN; main.js:935-941 composite verdict (lane) [Verified] |  |
| SYM-060 | SYMPTOM-INDEX | OPEN | S | Render or deliberately remove the exported `analyst` status field, with a contract test. | cell OPEN; dead `analyst` status field (lane) [Verified] |  |
| SYM-061 | SYMPTOM-INDEX | OPEN | M | Bind the primary remedy button to the evidenced failing phase (main.js:904-931). | cell OPEN; remedy buttons unbound (lane) [Verified] |  |
| SYM-063 | SYMPTOM-INDEX | OPEN | S | Preserve close.sh's git stderr/exit cause; distinguish absent repo from dubious ownership (B33 twin). | Verifier read close.sh:360-361 — one generic branch for absent-repo vs ownership-refused [Verified] |  |
| SYM-064 | SYMPTOM-INDEX | OPEN | S | Bound `git credential fill` with its own timeout in close.sh (B33 twin). | Verifier read close.sh:100 — `git credential fill` unbounded inside the script [Verified] |  |
| SYM-066 | SYMPTOM-INDEX | DONE | S | No action; cell already FIXED. | cell FIXED Verified S114; fidelity_audit.py:558/564 carry runs_capped_at (verifier grep) [Verified] | 2026-09-04 verifier (HEAD bde007d): already FIXED in the cell (runs_capped_at live, S114); no change. |
| SYM-067 | SYMPTOM-INDEX | DONE | S | No action; cell already FIXED (closes the sparse-table class only — see SYM-003). | cell FIXED 8aa8936; 8aa8936 + d9bfaaa ancestors (verifier) [Verified] | 2026-09-04 verifier (HEAD bde007d): already FIXED `8aa8936`/`d9bfaaa`; no change. Scope is the sparse-table false-positive class; SYM-003 stays open. |
| SYM-071 | SYMPTOM-INDEX | DONE | S | No action; cell already FIXED. | cell FIXED S114; c151e68 ancestor (verifier) [Verified] | 2026-09-04 verifier (HEAD bde007d): already FIXED `c151e68`; no change. |
| SYM-072 | SYMPTOM-INDEX | DONE | S | No action; cell already FIXED. | cell FIXED ba036f9; ba036f9 + d9bfaaa ancestors (verifier) [Verified] | 2026-09-04 verifier (HEAD bde007d): already FIXED `ba036f9`/`d9bfaaa`; no change. |
| SYM-074 | SYMPTOM-INDEX | OPEN | M | Add a fence-check rejecting </think> leaks, an analyst selftest case, and a corpus sweep (1 of 32 books checked). | cell 'OPEN — no guard'; 48cb7e2 ancestor; no fence-check commit since (lane) [Verified] |  |

### CODEX — 1 rows (0 still to do)

| ID | Section | Status | Effort | Do now | Evidence [tag] | Register note |
|---|---|---|---|---|---|---|
| A49 | A.5 (row physically under §B's header) | STALE | L | Rewrite A49 to point at the S112 sign sheet; OK-3/9/10/11/13 remain Codex's queue. | Verifier re-probe: sessions/S112-fable-sign-sheet.md marks OK-0/1/2/7 SIGNED+BUILT S112; 0181636 (OK-4) 80df03b (OK-5) cd5b10e (OK-6) be191bf (OK-8+12) 091ffd7 (OK-14) 77d0361+8da7005 (OK-15) all ancestors of HEAD; OK-3/9/10/11/13 signed, unbuilt (banked for Codex, MSG-FAB-0055) [Verified] | 2026-09-04 verifier (HEAD bde007d): STALE — 'Nothing built' is false: sign sheet shows 13/13 signed, OK-0/1/2/7 built S112, OK-4 `0181636`, OK-5 `80df03b`, OK-6 `cd5b10e`, OK-8+12 `be191bf`, OK-14 `091ffd7`, OK-15 `77d0361`+`8da7005`; OK-3/9/10/11/13 signed and unbuilt (Codex's queue, MSG-FAB-0055). Rewrite; row is also misfiled under §B's header. |

### BLOCKED — 3 rows (3 still to do)

| ID | Section | Status | Effort | Do now | Evidence [tag] | Register note |
|---|---|---|---|---|---|---|
| A35 | A.5 | OPEN | L | Blocked on A13 (docs/26 F8); bench doctrine session waits. | depends on A13 (docs/50:192), still unsigned (lane) [Verified] |  |
| A36 | A.5 | OPEN | M | Blocked on A35; deprioritised per the row's own text. | docs/50:255 depends A35 (lane) [Verified] |  |
| SYM-035 | SYMPTOM-INDEX | OPEN | L | Blocked on SYM-022; needs a concurrent-resident benchmark design. | cell OPEN; blocked on SYM-022's one-process rule (lane) [Verified] |  |

## Residue (declared, not resolved)

- No script, suite, pipeline, widget, marker, ollama or GPU was run; every check was git log/show/merge-base, grep/sed/cat, wc/sha256 and direct reads. Consequences: J4's 8m37s and the 67/67 selftest tally are UNREAD by me (the tally rests on d9bfaaa's commit message); B3's glitch count not re-measured.
- Vault-side facts are out of reach: A41's 'also vaulted' half, B26's Valentine embed, J28's live supersede observation.
- J33's six exactly-one-.md guard sites were not re-verified line by line (lane's UNREAD stands).
- The S lane's 20 'no commit since filing' rows (SYM-024/027/034/035/043/045/051/053/054/055/058-062) were accepted on their cell text + the lane's git-log check; I re-derived only SYM-003/044/046/047/056/057/063/064 from source.
- 'Six Sonnet lanes': the lane model is recorded nowhere I can read (the orchestration script and journal carry no model field) — UNREAD.
- Owner/effort are the verifier's judgment under the rubric, not Rab's signature; four CODEX attributions were overturned on the absence of any row/relay assignment.
- MUSTER: this is a read-only subagent; MEMORY.md was in context, and the S114 close `1ac3111` / row `1a91918` were verified ancestors of HEAD (HARD clock consistent with TIME-STATE); open.sh was not run, no clocks were advanced, no relay entry written.
- Register file line numbers: Python's universal-newline count drifts from sed/grep by one in places (mixed CRLF/LF: 400 CR bytes over 437 lines in OPEN-TASKS.md) — rows were addressed by ID, not by line, after that was noticed.
