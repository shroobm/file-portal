# OPEN TASKS — the register of what File Portal has NOT done

**Retrieve by what is undone, not by which session left it undone.** Companion to
`SYMPTOM-INDEX.md` (which answers *"what is going wrong"*); this file answers *"what was
promised and never delivered"*.

Built 2026-08-22 (S107 open) by sweeping **all 42 closeouts in `sessions/`** (S67→S106, both
machine lanes), the `CLAUDE_README.md` Change Ledger (114 rows, 89 Desktop-lane, S16→S106),
`docs/08`, `docs/26`, `docs/32`, `docs/37` §3, `docs/40`, `docs/41`, `docs/45`,
`SYMPTOM-INDEX.md`, `coordination/relay.md`, `coordination/messages/`, and the memory library.

## How to read this file

| tag | meaning |
|---|---|
| `Observed 2026-08-22` | **re-measured by the session that wrote this file.** A command was run; the result is quoted. |
| `Historical` | faithfully transcribed from the closeout that recorded it, **not** re-observed. It may have been done since. |
| `SEMANTIC` | needs Rab's signature. A session must not build it on its own judgment. |
| `MECHANICAL` | no signature needed — a session may just do it. |

**Two standing hazards this file inherits, per `docs/45` §1 Family 1:** a sentence here may
describe the *neighbour* of the thing it names, and a status column may be stale while the
row body is correct. **Before acting on any line, open the cited source.** Every line carries
one.

⚠ **This register is itself a governance artifact**, and `docs/45` M5 + the S105 §10 #4 debt
gate proposal both argue the project is producing governance faster than output. It was asked
for explicitly; it is listed in §F as something that should either earn its keep by being
*worked down* or be deleted.

---

## §0 The one-paragraph answer

**Nothing in the product has moved for ten sessions.** The muster card at
2026-08-22T03:45:02Z reads `held 4 · anchor 23 · pending 0 · drop 0 · events 137 · vault 6 ·
exe 4DCB73E2` — **byte-identical to S97's open card** (`Observed 2026-08-22`). No conversion
has run since S96. S97–S106 built: a think tank, a skill, a relay, a claim convention, an
amendment, a selftest, a wiring slice, an adoption, a figure-coverage module, a close script,
a Circle, a second Circle, a lever file, a modularity gate. **`docs/45` names this as the
finding, and this register is the enumeration of the work those sessions did not do.**

Counts: **43 open semantic decisions** (§A) · **31 mechanical items** (§B) · **14 genuinely
open symptom rows + 4 falsely-open ones** (§C) · **8 delegations never collected** (§D) ·
**7 of 7 slate items unfinished or unwired** (§E) · **11 record-integrity repairs** (§F).

> **RE-MEASURED 2026-08-27 — the line above is `Historical` (2026-08-22) and is left standing
> per this file's own no-rewrite habit. Measured today, by counting rows rather than recalling
> them:**
>
> | section | rows | struck | open |
> |---|---:|---:|---:|
> | §A semantic | 44 | 2 | **42** |
> | §B mechanical | 31 | 2 | **29** |
> | §D delegated | 8 | 1 | **7** |
> | §F record repairs | 12 | 0 | **12** |
> | §J opened S109 | 18 | 4 | **14** |
> | | | | **104 open** |
>
> **THE DENOMINATOR, because this number has a twin that counts something else.** `104` counts
> **rows in THIS FILE only**, after the day's 8 strikes. It is *not* comparable to the **147**
> reported to Rab on the same day, which counts distinct open items across **five surfaces** —
> this file *plus* `SYMPTOM-INDEX.md`, `sessions/S108-SIGN-SHEET.md`, `coordination/BRIEF-S109.md`
> §6, and `sessions/S110` §23. Both numbers are correct about different populations. They were
> published hours apart with neither naming its population, a sweep agent read them as a live
> contradiction in the tree, and it was right to — that is `docs/34`'s rule (**every measured
> number names its numerator, denominator and conditions**) broken by the session that was
> re-measuring this file to make it honest. Filed as `ERR-2026-08-27-012`.
>
> **Two things the old line got wrong, both structural, neither anyone's carelessness:**
> (1) **§A has 44 rows, not 43.** The count was written when §A ran A1..A43 with none struck;
> S109 then struck A21 *and* added A44, and the two changes cancelled. The number survived by
> coincidence, not by maintenance — which is precisely the rot §H predicts.
> (2) **§J's 18 rows were never in the headline at all**, and `open.sh` could not see them
> either: it counts ids in `[A-F]`, and J is outside that class. The muster card has been
> printing `94 item(s)` against a file holding **112**. That is J15's shape — a counter that
> reads one spelling of a marker — applied to the register instead of the symptom index.

> **Struck 2026-08-27** (each re-probed against the working tree by the striking session, never
> taken from a prior report): `A18` `B22` `B25` `D1` `J2` `J8` `J9` `J11`. **`J10` was NOT
> struck** — C0 half-moved and a strike would have claimed it closed. **`B17`/`B18` were NOT
> struck** — a finished n=30 A-B-A run exists on disk, gitignored and unnoticed, but its one
> named condition (idle card) is unrecorded, so it stays `Unknown`.

> **RE-MEASURED 2026-08-28 — current row population after the S111 filings below:** §A has
> 48 rows / 2 struck / **46 open**; §B 33 / 2 / **31**; §D 8 / 1 / **7**; §F 12 / 0 / **12**;
> §J 18 / 4 / **14**. Numerator: open rows in this file. Denominator: those five sections only.
> **110 open.** This does not revise the historical 147-item, five-surface census.

**Current signable surface outside that historical five-surface denominator:**
[`sessions/S110-SIGN-SHEET.md`](sessions/S110-SIGN-SHEET.md). Blocks A and B are signed; C1,
C2 and D1 remain open. Do not fold this sheet retroactively into the 147 census. A MUSTER card
field was considered and deliberately not added in S111: it would change the open/close gate for
a reachability repair that this primary register already supplies.

---

## §A AWAITING RAB'S SIGNATURE — semantic, a session may not decide these

### A.1 The signature register (`docs/37` §3) — items still OPEN at HEAD

| # | The decision | Options on the table | Fable's standing recommendation | Source |
|---|---|---|---|---|
| A1 | **Asset posture** on out-of-range assets | warn (today) ~or~ fail ~or~ quarantine | encode in Stage 2 | `docs/37` §3.3 |
| A2 | **Stage 2 GO** — converter tests + CI | go / hold | go; negative cases enumerated | `docs/37` §1, §3.4 |
| A3 | **Stage 3 GO** — the verified seam (per-file SHA-256 `inventory.json`, exporter verifies BEFORE commit, receipt binds the digest) | go / hold | go — closes the transport integrity half | `docs/37` §3.4, `docs/08` |
| A4 | **P-1 variable 1: HOST** | in-converter at `:998` (route to region-level coverage, extends card-lock) ~or~ out-of-band desktop re-score (zero lock cost, back-fills the whole corpus) | **SIGNED S108; BUILT out-of-band at `0fbb6e3`** — manifest/SHA-bound, report-only, zero GPU/card-lock cost; scan-lane subpage diagrams fail closed as UNREAD | `docs/37` §3.6, `docs/41` §2, S108 §5 |
| A5 | **P-2 / the #598 tripwire** disposition | join `docs/15` §12's fail list ~or~ flag-only localizer ~or~ receipt-note-only | flag-only until §9 calibration gives a false-alarm rate | `docs/37` §3.7 |
| A6 | **DPI operating point** (P-5) | one-book measured probe ~or~ per-page render-to-budget ~or~ leave it + record why | the one-book probe first; `ocr_dpi` stamp reworked in the same commit | `docs/37` §3.8 |
| A7 | **Generative-SR standing ban** (P-6) | record the ban ~or~ defer-with-criteria (ground-truth set + no-SR diff lane) | zero code either way — just record it | `docs/37` §3.9 |
| A8 | **SPOT_CHECK_EVERY** 10 → 3–5 | his number | 3–5 (ThinkPad S78 §12 argues it) | `docs/37` §3.5 |
| A9 | **Stale-hold reap countersign** | countersign / revise | — | `docs/37` §3.5, S85 §8.2 |
| A10 | **`docs/34` rule 8 countersign** | countersign / revise | — | `docs/37` §3.5, S83 §18.4 |
| A11 | **The wrapper decision** — two-engine steady state vs Ollama off the machine | two engines / one | §6.1 is the measurement; nothing further to measure | S83 §18.3 |
| A12 | **GLM bench second-reader** — zone-keyed accept/reject proposals carrying reason·highlight·solution | build / don't | build; the S84 probe is the existence proof (3/3 omission runs recovered, ~3 s/page) | S84 §18.2 |

### A.2 The `docs/26` signature sheet — five decisions, open since 2026-08-13 (S75)

Deferred through **S76, S77, S78, S83, S84, S85** by name. Gates slice 3 (the Dock) and the
operator-simplicity discovery mission behind it.

| # | Finding | The decision | Recommendation |
|---|---|---|---|
| A13 | **F8** — ambient terracotta radial washes violate "nothing else may glow terracotta" | carve-out or desaturate | keep + sign the ambient-chrome carve-out (≤7–13 % clay, never animated, outside the summons grammar) |
| A14 | **F7 / F13 / F15** — `docs/25` bans motion > 400 ms with no carve-out while its own Part 3 requests a 2.6 s breathe | amend `docs/25` | "no *travel* motion > 400 ms; ambient opacity idles exempt; all motion collapses under reduced-motion" + fix the Part 3 active-wording and the compositor claim in the same pass |
| A15 | **F6** — "agreement lane": metric *kind* rendered in the lane slot; both rendered lanes are fictional | relabel | "scan lane · agreement witness" / "clean lane · fidelity witness" |
| A16 | **F4 + F5** — `doc_survival` **fabricated as 1.0 when nothing was measurable**; the Wall hero mixes metrics and inherits those fake 1.0s | fix + relabel | `null` not 1.0; `pages_scored` on the card; Wall avg windowed or relabelled "lifetime". **Own mini-session — touches Python + manifests** |
| A17 | **F3** — terracotta the *colour* now carries ≥5 meanings while glow stayed disciplined | colour policy | busy moves off clay; clay becomes summons-only in colour as well as glow. **Decide WITH slice 3 so Dock + rail change once** |

Also inside `docs/26` and unresolved: **F14** — slice 1's "60 fps trace" proof gate was never
machine-run, deliberately deferred to Rab's adoption. Big-screen + perf remain human gates.

### A.3 The S105 Circle's 14 — `sessions/S105` §10, "semantic, NOT applied"

`Observed 2026-08-22`: of the 14, **#2 was attempted at S106** (P-1 re-measured on a repaired
map — but *the repair is not wired*, so it moves to A18 below rather than closing); **#10 and
#11 are mechanical** and appear in §B; the remaining **11 are untouched**.

| # | Item | Verified state today |
|---|---|---|
| ~~A18~~ **STRUCK 2026-08-27 — BUILT** | **Wire the SYM-050 repair.** `true_page = id + 1 − 200×(id÷400)`, confirmed four independent ways at S106 | **BUILT S108 (`0fbb6e3`)** — narrow full-signature repair in memory; JSON names repaired/as-shipped map; clean control detector false at 1/1, poisoned IV detector true at 220/269 versus naive 30/269; SYM-050 resolved in source · `Observed 2026-08-27` — `git cat-file -t 0fbb6e3` = commit; `windows-converter/coverage_rescore.py` and `figure_coverage.py` both present in the tree |
| A19 | **#1 Stop opening a session per work item** — 8.7 min of committed work per session, each carrying a full closeout + ledger row + CHANGELOG + memory digest + two clock advances. *The arc's single largest cost* | `Historical` (S105) |
| A20 | **#3 A product clock on the open card** — last-conversion timestamp, amber when idle N sessions. Today the card **cannot tell a healthy idle pipeline from a dead one** | `Observed 2026-08-22` — the card still shows no timestamp **RESOLVED S108 (lane F)** — the Dock renders 'last pipeline event: <age>' with fresh/idle-N-days/UNREAD states, tail-read only. |
| ~~A21~~ **STRUCK S109 — BUILT** | **#4 A debt gate in `close.sh`** — refuse a new governance artifact while the OPEN SYM count exceeds its value at the last close. ~3 lines | `Observed 2026-08-22` — grep for debt / OPEN SYM in `close.sh` → no hits |
| A22 | **#5 Suspend the relay, delete the concordance amendment**; reinstate on Codex's first entry | `Observed 2026-08-22` — `relay.md` has **3 entries, all `⟨from: Fable⟩`, zero from Codex** **SIGNED S108: KEPT.** The founding premise (one participant) died 2026-08-23 — Codex returned four entries in one day. |
| A23 | **#6 Delete `/echo` the skill, keep the lexicon** — 1 commission in 7; the triviality carve-out invoked 6/6 | `Observed 2026-08-22` — `.claude/skills/` = `echo`, `muster`. Still there |
| A24 | **#7 Cut the closeout contract to 6 core sections + Evidence**, and mechanize `docs/21`'s own 80-word check | `Historical` (S105) |
| A25 | **#8 Narrow the tag law** to §Known Failures, §Evidence and status sentences — it is at zero compliance | `Historical` (S105) |
| A26 | **#9 Invert glass's default** — `--enforce` on, explicit `--report` to print. Removes SYM-046's whole class instead of ruling against it | `Observed 2026-08-22` — `--enforce` is still `action="store_true"`, opt-in (`glass_detector.py:338`) |
| A27 | **#12 Correct the S102/S103 ledger rows and CHANGELOG**, or rule that newer rows supersede older ones | `Historical` (S105) |
| A28 | **#13 Sign `docs/32` §5's three rules** — obeyed as law in 8 places; the doc itself says otherwise | `Observed 2026-08-22` — `docs/32:134` reads **"Not signed."** |
| A29 | **#14 Put the governance suites in CI** — muster, echo, coordination, figure-coverage, glass acceptance. *Today nothing checks the layer that checks everything* | `Observed 2026-08-22` — `ci.yml` runs python lint/test for the **three linux dirs only** + the rust job. Zero governance suites, zero windows-converter **SMALLEST SLICE S108** — observability/acceptance.py runs in CI (warn-only); the remaining governance suites stay queued. |

### A.4 New from S106

| # | Item | Why it is his |
|---|---|---|
| A30 | **Ctrl+Z is dead in the Bench after any Enter.** The `innerHTML` rebuild orphans Blink's undo stack and the browser still reports undo as available | the fix is either a real custom undo model or reverting to a textarea — a product-shape choice **BUILT S108 (`0f0e83f`) — ratification on the sign sheet**: native-undo path (contenteditable='true' + beforeinput), plaintext-only MODE was the killer; Ctrl+Z measured alive through Enter. |
| A31 | **Post-close continuation: new session number, or a ledger continuation form?** The two-clock protocol has **no representation for work performed after a session's ledgered close.** S106 tried to file a second row; both muster guards correctly refused it (`S106b:` → parse fail; a second `S106:` → order fail), and the row was reverted | repo-structural; the guards are working as designed, the protocol has the hole |
| A32 | **The assay surface for the operator lever** — blocked behind A4 (P-1's host) | depends on a signature |

### A.5 Product & platform direction

| # | Item | Source |
|---|---|---|
| A33 | **Pick one `docs/40` §10 decision gate before any platform build.** G1 trace view · **G2 exception layer (recommended first)** · G3 buyer/deliverable · G4 transport risk · G5 federation · G6 enterprise. *Do not build federation, PDF/UA, RBAC or a broker before that evidence* | `docs/40` §10, S97 §18.2 |
| A34 | **Rab's narrated legend** for the sketch's nodes `1`–`3`, the stars, and the final circle — can promote or falsify the S97 interpretations without touching code | S97 §18.3 |
| A35 | **The Repair Bench's operating doctrine is UNDISCOVERED** — no canonical example of a good repair exists. The operator-simplicity discovery mission is queued *after* the `docs/26` sheet resolves | `docs/26` "Standing context", S75/S76/S83 §18 |
| A36 | **Transcribe thresholds** + **repair audit-credit** — unsigned since S71/S72, deliberately deprioritized until the bench doctrine session | S71 §18.2, S72 §18.3 |
| A37 | **The scan-lane challenger** — bigger surgery, own design, Survival Audit A-B gate | S84 §18.4 |
| A38 | **A product session for `held/`** — 4 books are held right now; the Beer's three signed GLM recoveries are its natural start | S83/S84/S85 §18 |
| A39 | **The guided Valentine session** — *deferred by name in S76, S77, S78-desktop, S78-thinkpad, and S79.* Remove the wrong-page embed, re-diagnose zones 1–2 as a matrix, zone 4's structure, zone 3's collapse last | S78 §18.4 |
| A40 | **Cybernetics-stale copy's fate** · **Textor re-download + Marker upgrade swap** — standing since S68, never resolved | S68–S73 §18 "standing queue" |
| A41 | **Decide `c5afd9edcf620fc6`** — held and vaulted simultaneously | S96 §18.4 |
| A42 | **The windows-converter test decision** (§8.3) — awaiting his word since S86 | S86 §18.4 |
| A43 | **Give the memory library's git a remote, or fold it into the Drive mirror.** It is local-only; a disk loss takes it | S96 §18.7 |
| A44 | **hOCR AS A SUPPLIED SIDE-INPUT** (Rab's design, 2026-08-25). An hOCR file is obtained externally and paired with the PDF at intake; the Analyst gains an INDEPENDENT expectation of what should be on the page, turning it from a reader into a comparator — which is the hole `docs/45` named (*nothing compares a claim to the probe that produced it*). Closes, if built: **SYM-053 becomes mechanical** (hOCR words inside a bbox that marker exported as a degenerate blank crop = a contradiction a machine can see, where it currently takes a human visual pass) · **per-REGION text survival** instead of a document-level score · **SYM-049** gets positive evidence for a fragmented diagram · and the 2-up gutter question becomes a reading-order check rather than 295 pages of human reading. **ACCEPTANCE CRITERION #1, and nothing is trusted before it: THE ALIGNMENT GATE.** hOCR bboxes live in the coordinate space of whatever produced them, often a DIFFERENT scan with its own crop, skew and offset. Align on high-confidence anchors per page, measure the residual, and **mark the pairing `UNREAD` rather than comparing when the residual is bad.** Silent misalignment producing confident garbage is **SYM-050** — the doubled-offset bundle that made 19 of 20 adjudicated verdicts FALSE. **#2: provenance is load-bearing** — `hocr_source` + `hocr_sha256` + the residual into the manifest. An hOCR from a Surya-family engine is CORRELATED and worth little (SYM-001). Unsourced hOCR is `Unknown`, not "reference". **#3: a disagreement is a FLAG WITH A LOCATION, never a verdict** — hOCR is a reference, not ground truth, and is often WORSE than Surya on hard text. Note the precedent: `docs/15` §5's "a large delta is a flag" was **WITHDRAWN at S101**; what makes this different is that the delta is bbox-anchored and `x_wconf`-weighted — a pointer to a place, not a score. That distinction decides whether this fixes that finding or repeats it. **UI (Rab's design):** hOCR is OPTIONAL in the drop box; dropping a PDF offers "confirm" or "supply hOCR", and an hOCR drop zone appears. ⚠ **It must not block intake** — today intake is fire-and-forget, and a modal turns a forgotten confirmation into a pipeline that looks alive and does nothing (`events.jsonl` frozen 11 days is what that looks like from outside). Land it in **`pending`**, a counter ALREADY on the muster card, so a forgotten pairing surfaces at every open; or give the dialog a countdown default. **Validate the pairing AT THE BOX** (page counts + a one-page text-overlap sample) and refuse with a reason, rather than failing deep in the run. **Blast radius:** changes the INTAKE CONTRACT, the most load-bearing surface in the pipeline, and touches both renderers where **SYM-043** is already open for copy lagging mechanism. Stage 2, signature required, not a tonight item | Rab in conversation 2026-08-25 (S109 second sitting); design notes in `sessions/S109` §19 and `coordination/BRIEF-S109.md` |

| A45 | **Finish `docs/30`'s still-open algedonic choices and decide whether to run its deferred research day:** silence/liveness, morning-note versus Gmail ownership, died versus stalled, and M/ack. Do not reopen §5.4, already signed; §5.2 remains deferred and the research day remains queued ahead of the guided Valentine | `docs/30:97-123,151-165,170-214`; commission preserved in S110 §28/§30 |
| A46 | **Choose the Room queue-order contract:** retain the current read-only filename order, or authorize operator reordering. If reordering is chosen, persistence and fairness are unresolved parts of its design, not requirements silently signed by this row | `windows-converter/watch_and_convert.py:196`; `windows-widget/src-tauri/src/line.rs:82-98`; `windows-widget/src/room.js:155-172`; commission preserved in S110 §28/§30 |
| A47 | **Rab's S111 commission: commission an independent adversarial challenge of all four `docs/40` theses A–D.** Each thesis already carries its author's own objections; the requested missing signal is a differently-prioritized reader and a falsifying probe. This is not A33, which chooses a §10 decision gate | authority: `sessions/S110-desktop-2026-08-26.md` §28/§30 and `coordination/relay.md:4310-4317`; thesis locations: `docs/40:270,300,312,324`; A33 above |
| A48 | **Resolve the two `docs/36` §8 questions that no other row mirrors:** where the briefing should live, and what the ThinkPad's untracked `CLAUDE.md` counts mean. Six of the eight questions are already represented by A8, A9, A10, A11, A12 and A42; do not duplicate them | `docs/36` §8; cross-check against A8–A12 and A42 |

**Negative control for this filing:** `docs/27` and `docs/28` were inspected and deliberately not
refiled; their work is already represented in the symptom/register record.

---

## §B MECHANICAL — no signature needed, a session may simply do these

| A49 | **Pick adoptions from the Okular digest** — `docs/49-okular-digest.md` §1 ranks 13 candidates (viewport sidecar, placeholder paint, prefetch, search suite, text layer, table tool, trim, zoom, unified undo, review panel, watch/swap, observability grammar, paged md reading surface) + ranked-out and pipeline extras, from 107 findings; 404 audit rows re-measured across the 7 code lanes, all MATCH (popplerweb lane unaudited, flagged); a critic pass filed 22 defects on the digest itself, folded in. Evidence `dumps/evidence/D0005`, sha256 `981f2959…`. Nothing built; each candidate names its bench pain and effort class. | SEMANTIC | `docs/49` §1, S112 Fable lane record, `Observed 2026-08-30` |
`Observed 2026-08-22` where a command is quoted.

### B.1 Standing reds and live hazards

| # | Item | Evidence |
|---|---|---|
| B1 | **`observability/acceptance.py` is RED: 40/41.** The failing row expects `recent_audits: GLITCH` but S94 rendered it, so it is now `glass`. One line, turns a standing red green | ran it today: `FAIL — 40/41 checks · failed: recent_audits: GLITCH (glass)` **RESOLVED S108 (`57abcd9`)** — the answer key caught up to S94: 41/41. |
| B2 | **`.agents/` — delete it or gitignore it.** It is a pre-S103 copy of the muster skill: **no `close.sh`**, zero mentions of `--enforce`/SYM-046/CI, points at a `.Codex/` path that does not exist, and its selftest prints `ALL TRIPWIRES FIRED — 22/22, exit 0`. **Any runtime that resolves skills from `.agents/` is running a blind close under a green banner**. **RE-MEASURED 2026-08-26 (S109 post-close), and the gitignore half of this item is DONE** (`.gitignore:71`): 16 files, and the drift is now specific -- `open.sh`, `muster/SKILL.md` and **`relay-gate/gate.py` (`a1246bd1` here vs `ab26a4f1` authoritative)** all differ; only `echo/lexicon.md` matches. **The `gate.py` drift is the one that matters: that file is the REFEREE of the two-model protocol and its own digest is the `gate_rev` the board prints, so two copies means two lanes can each be honest and still disagree about which protocol is running.** A `__pycache__/gate.cpython-312.pyc` sits beside it -- **this copy has been executed**, the drift is not hypothetical. **Remaining decision is Rab's: DELETE, or keep it marked.** A loud `.agents/00-STALE-DO-NOT-USE.md` was written on 2026-08-26 for the reader who skips `AGENTS.md` (untracked, like the directory). Deleting does not prevent recurrence if whatever generates the mirror runs again -- **fixing the generator is the only structural fix, and nobody has identified what creates it** | `ls .agents` → `skills/{echo,muster}`; `git check-ignore .agents` → **NOT ignored**; untracked in `git status` |
| B3 | **The observability standing debt: 57 unsigned glitches at 60 sites across 3 lanes.** SYM-027's criterion (3) has never been met | the acceptance run today printed the census |
| B4 | **`windows-converter/` is outside CI's lint set** — SYM-018's exact shape. `backend_parity.py`, `figure_coverage.py` and `convert_and_ship.py` ship unlinted | `ci.yml` lints `linux-receiver`, `linux-dashboard`, `linux-converter` only **RESOLVED S108 (wave 1b)** — windows-converter joined the CI python job (ruff + hermetic selftests, warn-only until CI observed green; deferral/card-mutex selftests excluded by name). |
| B5 | **Nothing in this repo tests `bench.html`.** "Bench acceptance 85/85" was cited in a commit whose entire diff is that file; the suite has not changed since 2026-08-14 and never loads the DOM | S106, and SYM-052's own row says no tripwire guards the regression **PARTIAL S108 (`abe4830`)** — 19-test stdlib headless harness with positive+negative controls (both S106 regressions are named fixtures); in-browser DOM run remains open. |

### B.2 Symptom fixes that are designed but unbuilt

| # | Item | Symptom |
|---|---|---|
| B6 | One-line fix: read `importlib.metadata.version` | SYM-044 |
| B7 | A mechanical **id preflight** so concurrent same-machine instances stop colliding on every monotonic counter | SYM-045 |
| B8 | A close-ritual check that **refuses a closeout whose glass claim lacks `--since <pin> --enforce`** | SYM-046 |
| B9 | The watcher writes a **pid/parent file** the widget can compare at boot (a Job Object cannot reach backwards over a process it never spawned) | SYM-047 |
| B10 | **Clustering that follows stroke geometry rather than bounding boxes** — zero-area connectors are dropped before clustering, so a spread-out diagram fragments and is missed. Two measured specimens (Cyb p34, p78). *Not a threshold nudge; needs its own calibration* | SYM-049 |
| B11 | Fix the supersede/pending **projection drift** in `main.js` + `room.js`, and add a tripwire that fails if "pending/manual" wording returns while the handlers exist | SYM-043, S97 §18.1 |
| B12 | Capture **Ollama's own server log** at the moment of the stall if SYM-034 recurs — today only the client side exists | SYM-034 |

### B.3 Instruments built but never wired to a human

*This is the project's most-repeated failure class — "instrument not wired", named at S76 and
committed again five times since.*

| # | Item | Source |
|---|---|---|
| B13 | **The bench UI has no buttons for triage / report / ledger** although `/api/triage`, `/api/report` and `/api/ledger` exist and are proven. Only the collapse and omission chips reached the glass | S76 §18.4 |
| B14 | **`MIN_SIDE_PT` and `MAX_PAGE_FRACTION` are unlevered and unwaived**, which makes `min_area_pt2`'s advertised 100–100000 range **inert**: at `min_area_pt2=100` all 18 newly-admitted Cybernetics clusters are killed by `MIN_SIDE_PT`, the report is byte-identical, and nothing warns | S106 |
| B15 | **The omission-class bank entry** — 18/18 runs on the Beer are unclassified; the signature bank is blind to text that *isn't there* | S79 §18.5 |
| B16 | **`seams[]` and `reverse_sample`** are referenced by zero renderers; `pages_scored` only as a positioning denominator | SYM-027 |

### B.4 Measurement debt

| # | Item | Source |
|---|---|---|
| B17 | **Re-measure throughput with the A-B-A control on an idle card.** The instrument is built and validated; a clean run is what is missing. **Do not quote 0.77×, 0.62×, 0.95× or 0.81× — all four are withdrawn** | S82 §18.2–3 · **STILL OPEN, and a candidate nobody has checked. `Observed 2026-08-27`:** `windows-converter/backend_parity.json` (mtime 2026-08-16 01:33) holds **four arms at n=30 each** — `ollama_think_false`, `llamacpp_jinja_default`, `llamacpp_jinja_nothink`, `ollama_recheck`. The `ollama_recheck` arm IS the A-B-A return leg, and n=30 meets B18's floor. **`Unknown` whether the card was idle** — the file records `ollama`/`llamacpp` versions and `llamacpp_load_s`, but no card-occupancy field, so the one condition B17 names cannot be read from the artifact. Resolved by re-running with occupancy recorded, or by finding the run's log. ⚠ The file is **gitignored** (`.gitignore:51`), so it is invisible to anyone reading the repo — which is plausibly why two sessions left these rows open beside a finished run. |
| B18 | **Raise `n` to ≥ 20–30** before any ratio is quoted. 5–8 of 266 chunks is `Inferred` about the book; the no-think arm runs ~5 s/chunk, so n=30 is ~3 min of card time | S80 §18.3, S81 §18.2 · **STILL OPEN, and a candidate nobody has checked. `Observed 2026-08-27`:** `windows-converter/backend_parity.json` (mtime 2026-08-16 01:33) holds **four arms at n=30 each** — `ollama_think_false`, `llamacpp_jinja_default`, `llamacpp_jinja_nothink`, `ollama_recheck`. The `ollama_recheck` arm IS the A-B-A return leg, and n=30 meets B18's floor. **`Unknown` whether the card was idle** — the file records `ollama`/`llamacpp` versions and `llamacpp_load_s`, but no card-occupancy field, so the one condition B17 names cannot be read from the artifact. Resolved by re-running with occupancy recorded, or by finding the run's log. ⚠ The file is **gitignored** (`.gitignore:51`), so it is invisible to anyone reading the repo — which is plausibly why two sessions left these rows open beside a finished run. |
| B19 | **The analyst has no llama.cpp call path.** It speaks Ollama `/api/generate` with a raw prompt; parity was measured against `/v1/chat/completions`. **Whatever is built must carry `enable_thinking:false`** or it silently reverts to the 6.5× arm — and a truncated rewrite drops trailing `⟦IMG-n⟧` and ships the un-analyzed original | S80 §18.4, S81 §18.3, S82 §18.5 |
| B20 | **Vary `-ub` on the one engine** before concluding anything about two products — Ollama runs `llama-server` internally, so this is one engine under two invocations | S82 §18.4 |
| B21 | **Test the table-loop deliberately**: map a degeneration zone's lines to its page, render, probe. One page answers what the S84 GLM probe did not | S84 §18.3 |
| ~~B22~~ **STRUCK 2026-08-27 — RESOLVED** | **The whole-file Bench render costs ~1 s per zone click and ~1.2 s per newline** at IV's size. The "105 ms" timed the lazy `innerHTML` assignment and excluded the forced layout | S106 **RESOLVED S108 (`f9585b3`)** — zone click is highlight-only when text is unchanged; the perf log now INCLUDES forced layout so the S106 measurement substitution cannot recur. · `Observed 2026-08-27` — commit `f9585b3` *"bench: B22 - zone clicks move the highlight, not the whole file"* |
| B23 | **219 of the 239 IV uncovered pages were never adjudicated**; the other four anchors were never measured at all; SYM-049's fragmentation class is verified for Cybernetics only | `docs/45` §6.5 |

### B.5 Long-standing build candidates

| # | Item | Source |
|---|---|---|
| B24 | **Events rotation + `verified_from` stamps**; **cross-day event-row date stamp** — build candidates carried in §18 from S68 through S70, never picked up | S68/S69/S70 §18 |
| ~~B25~~ **STRUCK 2026-08-27 — ROW WAS STALE WHEN WRITTEN** | **`room-chat` graduation**: `llama_server_exe` config key + **adopt the llama-server spawn into the watcher's Job Object** (a hard kill currently orphans it — the S37 lesson, un-applied here) | S79 §18.3 **ROW WAS STALE — corrected S108**: the graduation shipped at S85 (config.rs llama_server_exe + adopted spawn, verified at HEAD by lane G); the orphan claim was false when this register was built. · `Observed 2026-08-27` — `llama_server_exe` live at `windows-widget/src-tauri/src/chat.rs:8,62,64` |
| B26 | **Remove the wrong-page embed in Valentine** | S79 §18.5 |
| B27 | **`resume auto-detect-analyzed`** (Desktop one-liner) — ⚠ this line exists **nowhere else on this machine** than the memory open queue | memory `file-portal-project` |
| B28 | **Windows half of the v2 feedback loop**: the widget polls `status.json` and shows delivered → sorted → failed per transfer; **toast/notification** on complete or fail | `docs/08` v2 |
| B29 | **Package the widget** (`cargo tauri build`) and document install steps for a second machine | `docs/08` v1 |
| B30 | **Screenshot/demo GIF for the README**; decide public vs private repo and finalize `CONTRIBUTING.md` | `docs/08` v3 |
| B31 | **End-to-end manual test on real hardware** — open in `docs/08` v0 *and* v1.5 (dashboard with the allocator actively sorting) | `docs/08` |
| B32 | **Codex's completion audit exists, names seven source-cited product defects, and had reached NO register and NO relay entry before its S111 recovery.** `C:/Users/Bndit/Documents/Codex/2026-08-27/sca/outputs/file-portal-completion-audit-2026-08-27.md`, 37,957 bytes, 420 lines. Its three sibling reports were each announced on the bus; this one had not been. **U01** receiver startup backlog sweep — a restart with pre-existing inbox files must allocate exactly once (`linux-receiver/allocator/main.py:169-202`) · **U02** malformed widget config panics with no operator-visible remedy (`config.rs:112-120`, `main.rs:609-612`) · **U03** the vault-fixity service and timer exist but `linux-converter/scripts/install.sh:17-26` never installs them, so a fresh machine silently has no fixity checking · **U04** Room/Wall latest-event ordering is inverted — Rust returns newest-first while `room.js:952-953` takes the OLDEST of the bounded tail · **U05** receiver rule/config failure logs an exception and writes no terminal state, so the widget waits forever on a job that already died · **U06** the observability stale-signature control is history-dependent and fails when no exercising diff exists in 39 ancestors — a control that stops being able to fire, the same decay class as `close.sh`'s CI check. **U07 is filed separately as SYM-057.** | Filed as ONE row, not six: the detail lives in the audit and duplicating it here would grow the register by six for one document — exactly what B3 now measures. `Observed 2026-08-27` — the file was read by the Fable lane and U07 was independently verified at source; **U01–U06 are Reported, not Verified**, and each needs an independent probe before it is acted on |
| B33 | **Repair the two S111 close-gate evidence boundaries without changing their verdict semantics:** (1) bound `git credential fill` itself or force noninteractive credential lookup, because the later `curl --max-time 25` cannot stop an earlier `git-askpass` hang; (2) make the memory durability probe distinguish “not a Git repository” from Git refusing the repository because ownership/safe-directory identity is unresolved. Add negative controls for an interactive helper and a dubious-ownership repo. | `Observed 2026-08-28` during S111 close; `SYM-063`, `SYM-064`; `.claude/skills/muster/close.sh` CI and MEMORY sections |

---

## §C OPEN SYMPTOM ROWS — `SYMPTOM-INDEX.md`

**25 genuinely open after the S111 Dock, relay-authority, and close-gate filings.** Retrieval keys are in the
index; this is the roll call. The prior 14-row sentence omitted SYM-053–SYM-057; S111 adds
SYM-058–SYM-064.

`SYM-003` (Repair Bench is the response, not a fix) · `SYM-024` (resume stderr hardened, not
root-caused) · `SYM-027` (glass debt — criteria 2 and 3 NOT MET) · `SYM-034` (cause unknown,
exposure bounded) · `SYM-035` (bounded and measured, not eliminated) · `SYM-039` (fixes
assigned to Desktop by the ThinkPad handoff §2.6) · `SYM-043` · `SYM-044` · `SYM-045` ·
`SYM-046` · `SYM-047` · `SYM-049` · `SYM-051` (environmental) · `SYM-053` ·
`SYM-054` · `SYM-055` · `SYM-056` · `SYM-057` · `SYM-058` · `SYM-059` · `SYM-060` ·
`SYM-061` · `SYM-062` · `SYM-063` · `SYM-064`.

**⚠ 1 FALSELY open — `Observed 2026-08-28`.** `SYM-032` still reads `open` in the status
column while its own body records S94 signing and building it. `SYM-033`, `SYM-041`, and
`SYM-042` were repaired to `FIXED-S94` in S108; F3 below records that completed repair.

---

## §D DELEGATED AND NEVER COLLECTED

*This is the section the commission asked for by name.*

| # | Delegated to | The ask | State |
|---|---|---|---|
| ~~D1~~ **STRUCK 2026-08-27 — COLLECTED** | **Codex** | Four asks, standing since S99: adopt a **model trailer** on its commits · **claim its S97 sections** per `coordination/authorship.md` · write **`docs/43` §3** in its own words · **leave a relay entry back** | **COLLECTED S108.** `6ae112f` claims the Codex S97 sections and writes `docs/43` §3; all four parcel commits carry `Model: OpenAI Codex`; Codex returned the final evidence route to Fable at relay timestamp `2026-08-23T21:58Z`. Historical baseline preserved: the relay had zero Codex returns when this row was built S107 · `Observed 2026-08-27` — `6ae112f` exists; 8 commits carry the `Model: OpenAI Codex` trailer |
| D2 | **Codex** | The one probe Fable could not run: **re-measure P-1 on a CLEAN post-S60 bundle** independently and say whether SYM-050 holds | **COLLECTED S108 (`0fbb6e3`, S108 §5).** Clean post-S60 control: numerator 1 covered figure page / denominator 1 source-figure page = 1.0000, detector false, map as-shipped. Poisoned IV positive control: 220/269 = 0.8178 after repair versus 30/269 = 0.1115 naive, detector true. One clean specimen never promotes to a population claim. Stafford scan p129 then proved the separate blind spot: the mapped asset is blank while two hand-drawn callouts are missing (SYM-053) |
| D3 | **The next Circle** | **`docs/45` §6, the bequest — 5 items.** (1) re-check `docs/32` §6's prediction (2) *does Family 1 have a check yet — what compares a claim to the probe that produced it?* (3) re-measure P-1 clean — **COLLECTED CORPUS-WIDE 2026-08-31 (post-S112 night)**: all 24 anchor bundles via coverage_rescore.py, sessions/S112-p1-corpus-sweep.jsonl. IV book: 220/269 figure-pages covered (49 uncovered, map REPAIRED — the poisoned 239/0.1115 headline is formally replaced); Ashby 14/23 (9 uncovered, worst in library); Book of Models 56/57; born-digital small books full; scan lane fails closed UNREAD by A4 rule (Brain/Best-Practices/DIAGNOSING); Designing-with-Freedom UNREAD (source PDF absent). SYM-050 detector fired NOWHERE except the known IV specimen (4) P-2 now has multiple specimens across **different** failure modes (5) the explicit UNREAD list | S106's Circle collected part of it and **refuted item 4's own framing** (see §E). **§6.2 remains fully open: nothing compares a claim to its probe.** S106 proved it again by shipping a rule it had not measured |
| D4 | **The next Circle (S79's)** | **`docs/32` §6's falsifiable prediction**, bequeathed via `docs/33` §4 | **Uncollected for 25 sessions.** Confirmed 5×, scored 0×. `docs/45` calls this its own most severe finding |
| D5 | **Desktop, from ThinkPad** | SYM-039's fixes, assigned via `coordination/messages/2026-08-16T21-51…wip-handoff` §2.6 | SYM-039 still `open` |
| D6 | **Cross-machine** | Two coordination messages still carry `status: open`: `2026-07-05T0910Z--linux-to-desktop--windows-work-brief` and `2026-08-17T03-05--desktop-to-linux--familiarization-complete-and-the-fork-reconciled` | `Observed 2026-08-22` via a status grep over `coordination/messages/` |
| D7 | **ThinkPad lane** | Phase-gated and awaiting an explicit go: **enrichment consumer** (schema-constrained outputs) · **`docs/14` Phase A phone window** · the **Desktop half of the supersede seam** (`assay.rs` ⟳ marker + `convert_and_ship` consume) so a real remedy produces a real swap | the S43 ledger row records the Desktop half as NOT done; the memory open queue carries the rest · **PARTIAL CORRECTION `Observed` 2026-08-27 — the third clause is FALSE and has been for ~4 weeks.** The **Desktop half of the supersede seam is BUILT, both halves.** The widget WRITES the marker (`assay.rs:22` `SUPERSEDE_DIR`, `:210`, `:329`) and the converter CONSUMES it (`convert_and_ship.py:405` `_take_supersede_marker`, `:430` `_stamp_supersede_safe`, `:384` the `--superseded-` destination). Landed `6a6fce0` **2026-07-25** (consume) and `e5bdd20` **2026-07-31** (write) — `git log -S` on each symbol. And it is TESTED across the seam: `assay.rs:646` exercises the converter's `_take_supersede_marker`, *"proving both halves agree on the actual bytes"* — a cross-side test, not two same-side ones (SYM-001). **The row's cited evidence is the S43 ledger row, which was true when written and has not been re-measured since.** The other two clauses — enrichment consumer, `docs/14` Phase A phone window — are NOT corrected here and remain as written; I did not probe them. Row NOT struck for that reason. Found by the S67–S110 closeout sweep; verified independently before this edit. |
| D8 | **Rab's hands** | The S94 guard exercise: minimize + relaunch (expect restore-and-front, no twin) · Room styling under CSP · Recent audits panel · chat page · boot log · one PID · **P-0's figures line on a real book** · the widget-restart "engineer question" **fourth ask** (pending since S89) | ⚠ **RECORD CONFLICT — do not restate either side without re-measuring.** `MEMORY.md` says the S94 guard exercise is still `Unknown` and unlogged; the **S102 ledger row says "S94 single-instance guard exercised and HELD (Unknown→Observed)"**. Both cannot be right |

---

## §E THE CONVERSION-COMPLETENESS SLATE — `docs/41`, register items 6–9

| item | state |
|---|---|
| **P-0** the wiring slice | **BUILT S101** and rendered on both surfaces. Its acceptance — *Rab looks at the figures line on a real book* — is D8, unlogged |
| **P-1** figure/vector completeness | **BUILT S102, vetoed S104, re-measured S106, WIRED S108 (`0fbb6e3`).** A18's narrow repair and A4's out-of-band host now have 30/30 + 8/8 tripwires. Remaining limit now has a real specimen: Stafford PDF p129 contains two large hand-drawn callouts, while its sole mapped final asset is a constant-color blank strip; page-level coverage falsely called the page covered. Scan-lane rendered-region versus final-crop coverage remains UNREAD/OPEN (SYM-053); B14's inert-constant disposition remains separate |
| **P-2** the #598 tripwire | **NOT BUILT.** Disposition unsigned (A5). Specimen count is contested: S106 claimed "8 specimens across 3 failure modes"; **its own Circle found that is a count no surface enumerates** — of the five "confirmed lost figures", 9.3 is the *only* clean loss, 9.1/9.2 are present **as pipe tables** (the p84 fidelity class), 12.3 is partial, 3.1 was S105's "destroyed in place" |
| **P-3** RETAS / Flexible Character Accuracy — the text-loss locator | **NOT BUILT, never scheduled** |
| **P-4** LLM as adjudicator, never as searcher | **NOT BUILT, never scheduled** |
| **P-5** DPI as a measured experiment | **NOT BUILT** — decision A6 |
| **P-6** generative-SR standing ban | **NOT RECORDED** — decision A7. Zero code either way |

**⚠ Numbers not to quote without re-measuring**, per the S105 and S106 Circles: `uncovered 309`
(arithmetically impossible) · `5.6 ms/page` (an unshipped build; shipped is 37 ms/page IV,
72 Cybernetics) · `82 %` promotion (the pre-precedence build; shipped is **167 of 239 = 70 %**) ·
`FIVE confirmed lost figures` (the probe measures **image-asset absence**, not lost content) ·
every Investment Valuation figure computed before the map repair.

---

## §F RECORD-INTEGRITY REPAIRS

| # | Item | State |
|---|---|---|
| F1 | **The Change Ledger table is physically split.** Header at `CLAUDE_README.md:1126`; the S79+ rows sit at EOF (from ~line 1972) with **no table header**, after S43's narrative prose. The newest rows do not render as a table | `Observed 2026-08-22`, unrepaired since S96 §18.1 flagged it |
| F2 | **The protocol has no form for post-close work** (A31). S106's four post-close commits — `4d06588`, `c7e3812`, `d7ffd11`, `3659ec7` — **reach no permanent surface**; they are recorded only in the S106 closeout's addendum because the ledger physically refused them | `Observed 2026-08-22`; CI observed green on `c3e1f8b` |
| F3 | **Four false `OPEN`s** in the SYMPTOM-INDEX status column (§C) | `Observed 2026-08-22`, unrepaired since S96 §18.2 **RESOLVED S108 (`ffc7b8a` + `97906a3`)** — three verdicts folded, SYM-032 gained the verdict its cell never had; trails preserved. |
| F4 | **`S82`'s ledger row is dated 2026-08-16; its closeout file is `S82-desktop-2026-08-15.md`** | `Historical` (S96 §18.5) |
| F5 | **Correct the S102/S103 ledger rows and CHANGELOG**, or rule that newer rows supersede (A27) | open |
| F6 | **`MEMORY.md` is at ~200 lines — the read limit** — and has silently dropped pointers before. Compaction is Rab's call (S96 ruled the block must not be relocated). *That growth IS `docs/45`'s M5 finding, live* | `Historical` (S105). **Observed 2026-08-28:** canonical `MEMORY.md` is **220 physical lines / 25,237 bytes**, SHA-256 `958296A202D878D46577213A5B4DECCD3C58686FBF7CE71A93CCE9036FB9880F` — 20 lines beyond its ~200-line read limit. No compaction was performed; the disposition remains Rab's decision and the protected block was not moved. |
| F7 | **Reconcile the `.Codex` vs `.claude` canonical memory namespace** before migrating or duplicating memory data | S95 §18.5 |
| F8 | **SYM-046's own account is wrong**: "three closeouts cited it" — S100 never cited glass; its hollow claim is in its **ledger row**, which nobody corrected, and the correction appended to S100 corrects a claim that closeout never made. S97's glass line was also hollow and got no correction at all | `docs/45` F4 |
| F9 | **S96's untouched next-entry list** was inherited `Historical` by S97 and **still requires explicit prioritization rather than silent displacement** | S97 §18.4 |
| F10 | **The stale pre-rewind `survival-audit-spec.md`** in the working dir — superseded by `docs/15`, deletable, Rab's call | memory `file-portal-project` |
| F11 | **This register** — work it down or delete it (see the header warning) | new today |
| F12 | **`SYM-051(b)` cites "RAM 15.9 GB total"; the machine measures 31.9 GB.** Its whole memory-exhaustion argument rests on `0.7 GB free, 95.6 pct used` against a 15.9 GB total. Measured `2026-08-25T03:5xZ`: `Win32_OperatingSystem` reports **32,698 MB total, 11,121 MB free, 66.0 pct used**. Either RAM was added since 2026-08-21 or the original reading was wrong — **from here those are indistinguishable and a session may not guess.** SYM-039's class: a hardcoded number in prose contradicting a live probe. If it is an upgrade, it partially CLOSES SYM-051(b) and that row must say so | `Observed 2026-08-25` (S109 second sitting, process census). **Resolve by asking Rab whether RAM was added**, then correct the row in place with the date — do not silently overwrite evidence |

---

## §G WHAT IS *NOT* OPEN — so nobody re-opens it

- **The Opsroom prototype verdict.** Superseded — the Room shipped at S34. The memory open
  queue's "(a) verdict on the Opsroom" line is `Historical`; S96 corrected it.
- **The S32 installer question** — long closed.
- **The exporter supersede flow** — BUILT at S43 (`bd02fc0`), live-fired S50/S56. ~~*The Desktop
  half of the seam is what remains* (D7).~~ **CORRECTED `Observed` 2026-08-27: it does NOT remain.** Both halves have been in the tree since `e5bdd20` (2026-07-31), with a cross-side test at `assay.rs:646`. This bullet sits in §G — the section whose whole job is to stop work being re-opened — and it was itself the thing that needed closing. See D7.
- **F-09 semantics** (SYM-041) and **the card mutex** (SYM-042) — signed and built at S94,
  despite what the status column says.
- **`muster.sh` unversioned** — closed at S79.
- **SYM-030, SYM-048, SYM-052** — fixed.
- **`docs/15` §5 "a large delta is a flag"** — WITHDRAWN on evidence at S101. Do not cite it.
- **§9.1's "zero false alarms"** and **S82's four throughput ratios** — withdrawn.

---

## §H HOW THIS FILE STAYS TRUE

It will rot. `docs/45` Family 1 predicts exactly how: a line here will keep describing the
*neighbour* of what it names. Two cheap defences:

1. **Every close that resolves a line here strikes it in the same commit** — the same rule
   `docs/29` §5.4 applies to measurements.
2. **Never quote a status from this file into a claim.** Open the cited source. That is
   `docs/45` §6.2's open question in its smallest useful form.

---

## §I THE MAINTENANCE PROTOCOL — signed by Rab, S109 (2026-08-24)

His words: *"I need a task list that is dated, and that is updated in every session as part of
protocol, opening session checks it, closing sessions adds upon it, muster makes it mandatory to
check it."*

**Why it needed saying.** This register was built at S107 and **the protocol had never once
referenced it** — measured 2026-08-24: `OPEN-TASKS` appeared **0 times** in `muster/SKILL.md`,
`open.sh` and `close.sh`. It was a register nothing forced you through, which is a shrine, not a
spine. Its own header (line 26) already warned it "should either earn its keep by being worked
down or be deleted."

**Now mechanical, in three places:**

| where | what it does |
|---|---|
| `open.sh` `[2b]` | prints **counts, never a checkmark** — open items, symptom rows and open symptoms, relay entries — each with **when it was last written**. A register untouched for 2+ days prints `*** not written in Nd — is it still true? ***`. A tick would say the file exists; a count says how much is open, and **a count that never falls is visible as a count that never falls.** |
| `close.sh` `[8]` REGISTER | reports whether this file was written since the pin. **Every session either strikes an item or adds one; a session that did neither must SAY SO in its closeout rather than imply it.** Warn-only for one session, then armed. |
| `close.sh` `[8b]` DEBT | **§A21, finally built** — the open-SYM count now vs at the pin, with the direction named. It PRINTS, it does not block: a threshold that stopped a close on its first run would be tuned away by the second. |

**DATING RULE.** Every item carries the date it was **last verified**, not the date it was
written. `Observed <date>` means a command was run that day and its result quoted. `Historical`
means transcribed and **not** re-measured. An undated item is an item nobody has looked at.

**§A21 is now struck** — it proposed the debt gate on 2026-08-22 and sat unbuilt in the very list
it was designed to bound. Built S109.

---

## §J OPENED IN S109 (2026-08-24) — from the session's own gates, on their first run

*The register's first entries under its own protocol are the debts that protocol found. All
`Observed 2026-08-24` — each was printed by a gate, not recalled.*

| # | Item | Class | Source |
|---|---|---|---|
| J1 | **3 threshold-shaped constants added with no lever and no waiver**: `BEAT_STALE_MIN`, `GATE_TIMEOUT_S`, `MIRROR_MAX_ATTEMPTS`. docs/18 §2: a number that decides something is a LEVER, not a constant | MECHANICAL | `close.sh` LEVERS, `Observed 2026-08-24` |
| ~~J2~~ **STRUCK 2026-08-27 — CLEARED** | **1 unsigned observability glitch since `4862be1`** — GLASS RED at close | MECHANICAL | `close.sh` GLASS `--enforce`, `Observed 2026-08-24` · `Observed 2026-08-27` — `glass_detector.py --since ab544d1 --enforce` → `no unsigned glitches`, exit 0. Scoped form per SYM-046. The detector's own caveat stands: *reads as clean is not the same as is clean* |
| J3 | **SYM-054**: an agent fleet leaks live servers and a file-digest audit cannot see them. A fleet law needs a PROCESS census the way it already has a digest census | MECHANICAL | `SYMPTOM-INDEX.md`, `Observed 2026-08-24` |
| J4 | **`close.sh` now takes 8m37s** (measured, `time`). It runs three suites that have grown from 22→83, 38→48, and 0→43 cases. A close nobody can afford to run is a close nobody runs | MECHANICAL | `Observed 2026-08-24` |
| J5 | **relay-room's `NOT_YET` list**: the live-server suite (T3/T4/T20/T21/T12), the catcher-cycle suite (T24-T27) and the end-to-end T28 are unbuilt. Declared, not hidden — but declared is not done | MECHANICAL | `prototypes/relay-room/test_room.py`, `Observed 2026-08-24` |
| J6 | **`T-004`'s joint half** is blocked on the Codex lane's usage — **not on Rab**. Its EXTRACTED schema half is published for review | SEMANTIC (blocked) | `coordination/T-004-EXTRACTED-SCHEMA.md`, `Observed 2026-08-24` |
| J7 | **The disclosure standard and the private-layer doctrine** remain drafts. Only D2 of six triggers is mechanical; D1/D3/D4/D5/D6 are discipline | SEMANTIC | `coordination/DISCLOSURE-STANDARD.md`, `Observed 2026-08-24` |
| ~~J8~~ **STRUCK 2026-08-27 — CLOSED BY DECLARATION** | **`MSG-FAB-0018` names two entries on the bus, permanently** — the residue of the 17:25Z live-bus incident. Appends never erase; it is declared, not repairable | RECORD (closed by declaration) | `coordination/relay.md`, `Observed 2026-08-24` · `Observed 2026-08-27` — its own Class cell already said so; striking makes that visible instead of leaving it in the open count. `MSG-FAB-0018` still appears 11× in `relay.md` and always will — appends never erase |
| ~~J9~~ **STRUCK 2026-08-27 — PREMISE DEAD** | **The bus is DORMANT** — Codex out of usage. Its lane will read STALE indefinitely; `MSG-FAB-0029` records why so the silence is not read as a fault | RECORD | `Observed 2026-08-24` · `Observed 2026-08-27` — the bus is NOT dormant. Codex posted `MSG-CDX-0012` at 05:50Z, sent=12, and completed T-009 both directions |
| J10 | **C0 HAS STILL NOT BREATHED.** `drop/` empty, watcher not running, widget down. Recommended first book: Ashby, *An Introduction to Cybernetics* — the ancestor of every Beer volume already in the corpus | **THE ONLY ONE THAT MOVES THE SENTENCE** | `Observed 2026-08-24` · **PARTIALLY OVERTAKEN, `Observed 2026-08-27` — NOT struck.** The sentence "has still not breathed" is now FALSE: Ashby converted end-to-end and `events.jsonl` went 137 → **147** (last event `2026-08-25T05:29:46Z`). But C0's own done-when has three clauses and only two are met — the held/ bundles still have **no disposition**, and there are **five**, not four. Striking this row would claim C0 is closed. It is not. |
| ~~J11~~ **STRUCK 2026-08-27 — CORRECTED** | **A fabricated duration in `docs/46`'s opening line**: "spent a year" where the measured span is **60 days** (first commit `0a16117` 2026-06-25 → 2026-08-24). Inferred from artifact VOLUME — 109 sessions, 46 docs, 54 symptom rows — and rendered as elapsed TIME. Wrong by 6×, inside the document whose thesis is that every defect here is a category error; **session count ≡ elapsed time** is one. Corrected in place. **Found only because Rab asked "where are you getting the year timeline?"** — no probe in the session would have caught a number nothing was required to measure | RECORD (closed) | `docs/46:15`, `Observed 2026-08-24` · `Observed 2026-08-27` — `grep -c 'spent a year' docs/46-the-ontology-layer.md` → **0**; the text now reads `60 days` |
| J12 | **`docs/47`'s four unexercised clauses.** The subagent orchestration law is SIGNED and only its GROUND clause has a tripwire (3/3, `wf_72b1dfce-055`). `NEGATIVE CONTROL`, `DECLARE YOUR RESIDUE`, `HONEST NULLS` and the verifier anti-correlation rule are `Intended` — signed, untested. By this repo's own rule each is a proxy with a birth certificate until it has a case that VIOLATES its property | MECHANICAL | `docs/47` §7, `Observed 2026-08-25` |
| J13 | **The phase-transition relay: TESTED, NOT ADOPTED** (Rab: "Don't implement that, just test it"). Works live and bidirectionally from both a background agent and a workflow lane. Six constraints recorded in `docs/47` §8. **Two are decisions, not facts:** (a) `SendMessage` is DEFERRED and a lane that does not `ToolSearch select:SendMessage` first reports a FALSE NEGATIVE — "no relay channel exists"; (b) `to:"main"` is documented "background subagents only" yet workflow lanes accept it, so the restriction is unenforced and **could start being enforced**. **UNTESTED: N concurrent lanes** — both probes were single-lane; ordering and interleaving are `Unknown`, and the mutation run had five | SEMANTIC (adoption is Rab's) | `docs/47` §8, `Observed 2026-08-25` |
| J14 | **C0 BREATHED — and the book failed its convert-phase audit.** `events.jsonl` moved off 137 for the first time since 2026-08-14. Ashby, *An Introduction to Cybernetics*, 156 PDF pages = **295 printed pages (2-up landscape, 842×595 pt)**. Convert: 1088.7 s wall, **6.98 s/PDF-page vs 4.719 promised**, peak VRAM 9427 MiB — and **contaminated**: a 24-agent fleet ran across its first half (SYM-035's hazard), so treat it as an UPPER BOUND, not a measurement. Audit: `doc_survival 0.8582`, **`degeneration: True`, verdict `fail`**. Then, in the analyst lane, chunks generating ~15 min against a 13.9 s/chunk mean (**60x**) at 93 % GPU / 286 W. **First attributed to SYM-003 (table-loop disease); that attribution is WITHDRAWN** -- one of the two measured specimens contains ZERO pipe characters. Root cause found and filed as **SYM-056**: the converter emits **40 unterminated `array` environments** in this book (79 begin / 39 end, 28 of 112 chunks), with 36-character runaway column specs. All 28 carry `status: passed` -- the audit scores content, not structural validity. **It is in the SHIPPED corpus too**: the anchored Investment Valuation bundle reads delta 3 | MECHANICAL / measurement debt | `Observed 2026-08-25`, events.jsonl 140-143 **CROSS-VENDOR CORRECTION 2026-08-27 (Codex lane, `MSG-CDX-0014`, independently reproduced from primary bytes):** the figure **60** is the **strict-literal** delta only (`\begin{array}` = 126 minus `\end{array}` = 66) and must be labelled as such wherever it appears. The **semantic** count is **61 unmatched opens** — a whitespace-aware byte-order stack finds 127 opens, 66 closes, **zero stray closes**. The literal rule misses one opener written as `\begin` + **CRLF** + `{array}` while still counting its closer, so it under-reports by one. **"60 unterminated arrays" as a semantic claim is FALSIFIED; the honest number is 61, which is worse by one.** Controls run by Codex: balanced canonical and CRLF-split fixtures each return zero unmatched; a planted missing close returns one; removing one real close moves 61→62 and appending one moves 61→60; a second independent implementation reproduced the hashes, the counts, the anomalous token at body line 4,183 / raw line 4,200, and all five controls. ⚠ **The causal link to the timed-out analyst chunks 103/106/115 is `UNREAD`, not established** — those chunks are absent from the journal by design. ⚠ Codex also asks that `held`, `anchor`, `delivered`, `shipped` and `vaulted` not be used interchangeably as phase claims without separate evidence. **Its standing note on the guard: the guard stays cost-justified, but its test must include whitespace-separated TeX commands or it inherits the same blind spot.** Body denominator: 691,965 bytes / 5,926 lines, sha256 `5880bed650…`. *(Filed by the Fable lane on Codex's evidence, per the 2026-08-27 split: Codex verifies, Fable edits its own registers. Same defect family as `ERROR-BIN.md` ERR-004 — a probe whose assumption about token adjacency was narrower than the data, on a CRLF file.)* |
| J15 | **THE DEBT GATE UNDER-COUNTS BY FORMATTING.** `close.sh:330` counts open symptoms with ``grep -oU '| `open`'`` -- a single literal rendering. `SYMPTOM-INDEX.md` uses at least three (`` `open` ``, `**OPEN**`, `**OPEN.**`), so **this session's card read `open SYM 3 -> 4 (+1)` while the true figure was +3** (SYM-054 counted; SYM-055 and SYM-056 invisible). **Measured corpus-wide at filing: `` `open` `` appears 4x, `**OPEN**` 12x, `**OPEN.**` 1x -- the gate sees 4 of ~17 markers.** The gate convicted this session for adding debt AND under-reported that debt by two-thirds, in the same line. SYM-039's family, in a gate one day old. **Do not fix by reformatting the rows to suit the grep** -- that adapts the evidence to the instrument. Fix the pattern, then re-run against the pin to confirm the number moves. | MECHANICAL | `close.sh:330`, `Verified 2026-08-25` (pattern read + row formats counted) |
| J16 | **`widget:age_s` is unrendered and should not be.** `line.rs:106` computes, per PDF queued in `drop/`, the seconds since its mtime -- and no widget renderer reads it (`main.js`, `room.js`, `index.html`: zero references; the only other `age_s` in the tree is an unrelated key in `prototypes/relay-room/`). **It is neither INTERNAL nor DEAD**: *'this PDF has sat in drop/ for three hours'* is SYM-024's scenario exactly, and is the readout that would have shortened tonight's diagnosis while a book sat in `drop/` and `events.jsonl` did not move. Dispositioned **GLASS** in `observability/dispositions.json` with the debt named rather than classed INTERNAL to quiet the tool. Wiring site: a renderer need only display a value already present in the payload; it cannot affect the running adopted binary (4DCB73E2) until a rebuild. **A GLASS entry that outlives the session after next is itself a defect** -- this one has a name, a site and this row, so it can be collected | MECHANICAL (small; adoption is still Rab's hand) | `observability/dispositions.json`, `Verified 2026-08-25` (glass RED -> exit 0 after the disposition) |
| J17 | **A CLOSE WROTE A LEDGER ROW THAT THE MUSTER COULD NOT SEE.** The parser takes **SHA = the last non-empty cell**, matching `^[0-9a-fA-F]{7,40}$` ON ITS OWN (`muster.sh:122-129`). A row carrying its SHA *inside* the prose cell parses as `no-sha`, is discarded, and **the muster silently selects the PREVIOUS session** -- which is exactly the failure `muster.sh:99-105` describes in its own comment: *"a bad close wearing a rewind's clothing."* It happened at THIS close: the row carried its SHA in prose, and the card came back `TIME-STATE S109 vs ledger S108 -- INCIDENT`. Correct shape is **5 content cells**: date | machine | prose | files-touched | SHA. **Nothing documents this.** `docs/21` and the muster SKILL.md say *"ledger row (<=80 words)"* and never mention the cell structure, so it is learnable only by reading the awk or by breaking a close. **Fix: state the shape in SKILL.md's close section, and have `close.sh` structurally validate the newest row BEFORE the push.** | MECHANICAL | `muster.sh:122-129`, `Observed 2026-08-25` (broke it, then reconciled) |
| J18 | **UNREAD: did `[3b]`'s tail alarm fire on that malformed row?** It exists for exactly this case (`TAIL_ROWS=5`; the row was last of 117, so 117 > 112 should have tripped it). But I grepped `[3b]` OUT of my own output while reading the incident card, so **I never saw whether it fired** -- and a guard nobody has watched fire is a proxy with a reputation (`docs/32` §5). Resolve by reconstructing the malformed row in a scratch copy and running `muster.sh` against it. **Do NOT record this guard as working until someone has watched it.** | MECHANICAL (verification) | `Observed 2026-08-25` |
