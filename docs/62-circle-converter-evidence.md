# 62 — Circle: the converter's evidence base (S159, 2026-09-16) — claims against their receipts, statuses against the code, the laws against the numbers

*A Circle per `.claude/skills/circle/SKILL.md`, commissioned by Rab's word (Desk c898160c 02:03:40Z: "Conduct scope on and against evidences…"; Desk bd61cb8f 02:12:12Z: "Are you able to do all three?" — the third reading, bounded to the converter). Written against a named commit (the frozen-commit rule): the audited tree is `feat/library-pipeline` at **5bdf77b** (docs/61 with §10 and §10.10; the record through E4). Assessment, not change: the lanes edited nothing; the gate in §7 says what a repair may be and who signs it. Fable (Claude Opus 5) held Phases 0–3 and 5–8; three Sonnet lanes held Phase 4, read-only, no internet, no engine, no PDF, a plant each.*

## §0 Substrate (Phase 0)

The muster ran at the open (02:04Z, exit 0; both clocks at S158 `6c4fe91`/`2ecc1ac`); the symptom index read (133 rows, 34 open); the working tree clean but for `.codex/`; the last milestone the S158 close. The Desktop rebooted at 22:50:32Z the evening before (a power cut) with nothing lost — checked against three remotes.

## §1 Intent (Phase 1) — the falsifiable questions

The deliverable class is **assessment**. The questions:
1. **Do the record's measured claims about the converter match their receipts?** — the numbers in docs/60 §2, docs/45, docs/41 §0 and the S157 conversion episodes, each against the private JSON, the manifests, the measurement outputs.
2. **Do the symptom index's conversion rows' statuses match the code at HEAD?** — for every row marked fixed/resolved: the fix present, born when, tripwired how, reflected on the shelf.
3. **Do the converter's numbers obey the project's own laws?** — docs/34 (numerator · denominator · conditions) and docs/21's tag law over every measured number in docs/60 §2 and docs/61 §4/§10; and do the criteria contradict themselves?

## §2 Reference (Phase 2) — what "good" was defined to mean, quoted

- docs/15 §12 (SIGNED 2026-07-20): "**What gates (→ fail):** exactly two signals, both structurally unambiguous. 1. **Degeneration** … Thresholds `zlib < 0.20 OR max-word-trigram ≥ 40` per §9.1. 2. **Analyst near-exact loss** … `doc < 0.995 OR any run ≥ 25 words`." "Acceptable books measured **0.76–0.96** survival (legitimate reflow) — gating on them would false-fail good work … They **localize**, they do not judge."
- docs/15 §9.2 (the recalibration): "Block rule `OR` → **`AND`**: flag only when a block is BOTH `zlib < 0.20` AND `trigram ≥ 40`."
- docs/34 (S81, the design law): every measured number names its numerator, denominator and conditions; "a ratio prints both its sides; a percentage prints its base; a duration nobody reported renders UNREAD, never 0.0".
- docs/21 §1 (the tag law): Observed · Verified · Inferred · Intended · Unknown · Historical; "a failed probe never renders as a negative observation"; "sampling never promotes".
- docs/60 §1 item 2 (Rab's north star): "**Nothing reaches him dressed as more than it is.**"
- The Circle's own rules (S108 path 11, built S157 E14): frozen-commit records; the aborted-lane law; "HELD" retired as a verdict.

**The criteria's internal contradiction, collected while reading (a finding of the first rank):** docs/15 §12's signed sentence states the degeneration rule as OR "per §9.1" while §9.2 amends it to AND and the code implements AND (`fidelity_audit.py:254-258`); docs/15 §17 (S158) records the reading. Arbitration is Rab's: the signed text or the code.

## §3 Observe (Phase 3) — anomalies logged before delegation, and the seeded suspicions

Anomalies (observations that did not fit the model, logged before any lane ran; the packets carrying them were committed at `e9225dd`, 02:4xZ, before the summons at 02:57Z):
- All 25 anchor manifests read `marker_version` absent/unknown while SYM-044 reads FIXED S151 E2.
- SYM-049's row says "Neither has an asset in the bundle"; the Book of Models' `assets/` holds five files on p.34/p.78.
- S157 E31's prose maps the 588-word run to p.1174 and the 432-word run to p.1036; the record's own V3-08 says the reverse.
- docs/60 §2.2 says "a scan-lane book CANNOT pass"; Diagnosing is a scan-lane book with 156 of 184 pages scored (it fails on degeneration, not the floor).
- docs/61 §4.1's "the loss is Marker's" and §10.2's withdrawal of it stand on one page, append-only.
- The 07-21 Cybernetics flag and the 08-01 IV flag are the instrument's, by date; a re-audit would clear them (unrun).
- docs/45's "37 ms/page · 72 · 4.6" has a receipt in prose; whether a timing file exists is unread.

The seeded suspicions handed to the lanes verdict-free: C1-01..09 (claims vs receipts), C2-01..09 (statuses vs code), C3-01..09 (the laws vs the numbers) — private `sittings/S159/e5/packets/`; one seed per lane is a plant (C1-09 an E20 number that never happened; C2-09 a SYM-138 that does not exist; C3-09 a §4.5 sentence that reads otherwise).

## §4 Decompose (Phase 4) — the lanes

Three Sonnet lanes, read-only, no internet, no engine, no PDF, the brief on file and law-checked before the summons (private `sittings/S159/e5_circle_brief.md`, commit e9225dd), each double-loaded (nine seeds to confirm or refute + an open sweep of its territory), verdict-free, honesty-normed, methodologically different: **C1 claim versus receipt** (byte-level: the number in the prose against the number in the file), **C2 status versus code** (code reading and git, never the row's own words), **C3 the laws against the numbers** (docs/34 and the tag law against each sentence). Workflow run `wf_44a9d01d-4e0` (02:57Z → 03:08Z): 3/3 lanes, 0 errors, 154 tool uses, 515,235 subagent tokens. Every plant caught by its bare id (C1-09 WRONG · C2-09 DEAD · C3-09 VIOLATION). The public tree before and after: clean. No lane aborted (the aborted-lane law has nothing to name).

## §5 Reconcile (Phase 5)

- **C1** inventoried ~90 measured claims, opened receipts for ~75, and found every S157-era number reproducing to the decimal (E1's TEDS, E3's means recomputed by hand from 14 + 14 per-table values, E20, E24's 293/76/0.7406 on both copies, E25's before/after, E28's eight books, E29's six held summaries incl. the 11 → 1 pairing named in the prose, E30's 49/10/39, E35's 104 + 203 `accounted` values thresholded by hand, E36 against the manifests). Two real findings: the S157 E31 sentence stands backwards (corrected later in the same record by V3-08; append-only leaves it); docs/45's ms/page numbers have no receipt but the S104 prose (the private receipts convention began at S154).
- **C2** found the code behind eight of nine seeded FIXED rows present with a tripwire (SYM-044 with its six cases — and the 25 "unknown" manifests are consistent with the row's own caveat: the fix stamps NEW conversions; every anchor predates S151; SYM-074/115 with the URL negative control; SYM-050 with "REPAIR BITES"; SYM-066's `runs_total` on three post-S114 manifests; SYM-133's three refusal rules; SYM-114's negative control). One EROSION: SYM-067 reads FIXED for a convert-stage symptom while the fix lives only on the Windows lane (the Linux gap is an OPEN ticket in the other register). One FRAGILE: the SYM-050 and SYM-066 rows' line citations drifted 68–143 lines. **And one refutation of a lane of this very sitting:** the SYM-049 row's "Neither has an asset in the bundle" STANDS — the assets `_page_34_*` / `_page_78_*` are Marker's zero-indexed page ids (`figure_coverage.py:720-735`: "ZERO-INDEXED, while audit pages … are 1-based", `per_page[int(m.group(1)) + 1]`) and belong to the row's own CONTROL pages p35/p79 ("p35 carries a near-identical arrow diagram, it DOES ship"); the E2 lane LD read the filename digit as the 1-based page, and §10.6 of docs/61 carried the error.
- **C3** found two live docs/34 violations on one line of docs/60 §2.2 ("a scan-lane book CANNOT pass … which a scan does not have" — the shelf's Diagnosing is a scan-lane book with an embedded layer scoring 156/184 and failing on degeneration; "pairs 0.930 over 442 pages" — 442 is the page sample, the ratio's denominator is 123,791 witness pairs, S144 E3), one TENSION for Rab (docs/15 §12's signed OR against §9.2's AND and the code's AND — every other post-signing change to §12 got a numbered amendment, this one did not), and one structural EROSION (docs/61's corrections in §8/§10 write no pointer back into the rows they correct — §4.1's withdrawn sentence, §5's C-levels, §2's four-level key all read wrong or thin to a reader who stops where a citation stops them). §10.10's ρ footnote closed C3-05 before the Circle read it.
- **Conflict between lanes** (Phase 5's rule: investigate, never average): the E2 lane LD (S159 E2, D-05) said SYM-049's sentence was false at page level; C2 says it stands by the zero-index convention. **The lane re-read the code (`figure_coverage.py:720-735`) and the bundle (`_page_34_` and `_page_35_` assets sit under the p.35 control's own section) — C2 is right; D-05 and docs/61 §10.6's sentence are wrong.** Convergence across lanes: C1-01 and C3-S1 are one pattern (append-only leaves the original wrong sentence citable); C2-03 and E1's ticket are one fact.

## §6 Judge (Phase 6) — most-severe-first, in the Circle's vocabulary

1. **TENSION — docs/15 §12 (signed 2026-07-20) states the degeneration rule as OR; §9.2 and the code are AND** (C3-01). A reader building from the signed section alone builds the rule that false-fired on the Cybernetics table-dense book. §17 (S158) records the reading and does not resolve it; every other post-signing change to §12 carries a numbered amendment (§12.1–§12.4). **Human arbitration: Rab's** (the signed text or the code).
2. **VIOLATION — docs/60 §2.2's "a scan-lane book CANNOT pass … the embedded OCR layer, which a scan does not have"** (C3-02) is contradicted by the shelf's own Diagnosing (a scan-lane book WITH a layer, 156/184 scored, failing on degeneration); the sentence's remedy list targets the wrong half for such a book. The document is Fable's own (S146); the correction is mechanical.
3. **VIOLATION — docs/60 §2.2's "pairs 0.930 over 442 pages"** (C3-07) swaps the page sample for the denominator: 115,126 of 123,791 witness word-pairs, over 442 of 465 pages (S144 E3). Mechanical.
4. **VIOLATION, this sitting's own — docs/61 §10.6's "SYM-049's row's 'neither has an asset in the bundle' is false at page level"** (C2-02's refutation): the assets are zero-indexed page ids; the row stands. A lane's off-by-one carried into the document by the lane that should have counted. Mechanical (an appended correction).
5. **EROSION — docs/61's corrections write no pointer back into the rows they correct** (C3-S1, C3-03, C3-08; C1-01's E31 sentence is the same class in the record): a reader who stops at "§4.1" gets a withdrawn causal claim; "§5" files four W classes as C; the record's E31 stands backwards. Mechanical: one blanket pointer at the head of §10 (as §8 item 1 did for AND/OR) — append-only.
6. **UNREAD — docs/45 F8's "IV 37 ms/page · Cybernetics 72 · Brain of the Firm 4.6"** (C1-06) rests on the S104 prose alone; no timing file exists on this machine (the private receipts convention began at S154). Evidence-insufficient: a re-measurement is a run (his card); the record can only say the number is unreceipted.
7. **EROSION — SYM-067 reads FIXED for a convert-stage symptom; the fix is Windows-only** (C2-03); the Linux gap is an OPEN row in OPEN-TASKS (`linux-converter/port-the-table-row-blanking`, S158) but the symptom row's status never says so. Mechanical: a dated scope note in the row's status cell.
8. **FRAGILE — SYM-050's and SYM-066's line citations drifted 68–143 lines** (C2-S1); the fixes are present by function name. Mechanical: a dated note in each status cell naming the function, not the line.
9. **HONEST-BUT-CONFUSING — S157 E31's page mapping stands backwards at its line** (C1-01), corrected 80 lines later by V3-08 and again in docs/61 §10.5; append-only forbids the edit. No action but the pointer class above.
10. **WITHSTOOD** — every S157 conversion number C1 opened (E1, E3, E15's quoted, E20, E24, E25, E28, E29, E30, E35, E36), docs/60 §2.4's zero, docs/45 §7–§8's counts; eight of nine FIXED rows with tripwires (C2), incl. SYM-044 (the 25 "unknown" manifests are pre-S151 by the row's own caveat); docs/61 §10.5's and §10.6's Inferred tags kept apart from Observed (C3-06, C3-04's full row names its 184 pp); §10.10's ρ footnote (C3-05).

Findings in the lane's own recent work lead: items 4 and 5 are S159's and S158's; item 2 and 3 are Fable's S146 document.

## §7 Gate (Phase 7)

| finding | class | disposition |
|---|---|---|
| 1 docs/15 §12 OR vs AND | **semantic** — a signed sentence | Escalated: recommend a numbered amendment §12.5 stating AND per §9.2 with the date and his signature; until then §17's reading stands. A named ticket for his word: `docs/amend-15-s12-degeneration-rule`. |
| 2, 3 docs/60 §2.2's two violations | mechanical — Fable's own document, append-only | Appended this sitting as docs/60 §3 (the corrections, with the numbers). |
| 4 docs/61 §10.6 SYM-049 | mechanical — this sitting's own error | Appended this sitting as docs/61 §10.11. |
| 5 the pointer gap | mechanical — append-only allows a pointer at the head of §10 | Appended this sitting inside §10.11: "the sections above are corrected here; read §10 before citing §2–§7". |
| 6 docs/45's unreceipted ms/page | evidence-insufficient | A dated note appended to docs/45 (the frozen-commit rule: a correction appended, never a rewrite); the re-measurement is his card. |
| 7 SYM-067's scope | mechanical — a dated note in the status cell | Appended this sitting. |
| 8 SYM-050 / SYM-066 stale cites | mechanical — a dated note naming the function | Appended this sitting. |
| 9 S157 E31 | none (append-only; already corrected twice) | — |

Closing with one semantic escalation and six mechanical appends (no code, no threshold, nothing signed touched) is the Circle's success mode.

## §8 Close (Phase 8) — the answers, and what the next Circle inherits

**The Phase-1 questions answered.** (1) The record's measured claims about the converter match their receipts wherever a receipt exists — ~75 of ~90 opened, all S157-era numbers exact; the exceptions are pre-receipt-convention prose (docs/45's timings) and one sentence corrected downstream (E31). (2) The symptom rows' FIXED statuses match the code at HEAD with tripwires for eight of nine seeded rows; SYM-067's status hides a Windows-only scope; two rows' line pointers are stale. (3) The converter's numbers obey docs/34 with two violations on one line of docs/60 §2.2 and the ρ footnote closed just before; the criteria contradict themselves once, in a signed sentence (docs/15 §12), and that is Rab's.

**The lane's own errors, first-class:** §10.6's SYM-049 sentence (an off-by-one carried without counting); §4.1's withdrawn sentence and §5's C-levels left without a pointer (the structural gap C3 named); the E31 mapping carried backwards into an E1 packet earlier this sitting.

**What the next Circle inherits:** the tree at the commit this record is written against; the escalation on docs/15 §12 (open until signed); the unreceipted docs/45 timings (open until run); the pointer convention (a corrections section states at its head that it corrects the sections above); C2's residue — ~90 further fixed/resolved rows never triaged for conversion relevance, a second pass's territory; C3's residue — §4.2/§4.4/§4.6–§4.9's ~30 numbered cells not swept against docs/34; C1's — E15's `shelf-before-E15.json`, E31's three other books, E29's per-page files.

*Provenance: S159 E5 (private `sittings/S159/e5/`: the brief, the packets with plants, `results.{json,md}`, the lane's re-check of the SYM-049 conflict at `figure_coverage.py:720-735`). Written by Fable (Claude Opus 5); nothing run; the card untouched.*
