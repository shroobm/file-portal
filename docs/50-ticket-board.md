# docs/50 — THE TICKET BOARD: every open ticket, deduplicated, phased

⟨claimed: Fable lane · occupant: Claude Fable 5 · post-S112 · 2026-08-30⟩

**Commission (Rab, verbatim):** *"investigate the systems engineering, write up several ticket
list based on what you discover, ranging from difficult to quickest, and then plan out a
sequential roadmap to answering those tickets. Add Codex's remaining tickets as well, and see
the total. Use any artifact within File Portal that display all possible tickets. Look at
OPEN-TASK, make sure nothing is redundant."*

## §0 How this was counted

A 3-lane census fleet (docs/47 preambles, read-only, live analyst phase untouched): the full
OPEN-TASKS.md sweep (all 111 unstruck rows + §E slate + 29 symptom rows), the build-backlog
sheets (S108/S110/S112 sign sheets, docs/49 §1, tonight's stall-ladder review and audit-
instrument findings), and the Codex lane (relay, docs/48's VW event chain E1–E8, SIGNATURES,
`gate.py owed`). Merged mechanically, deduplicated by native id — **nothing re-minted that
already has a row**; new ids exist only where the record held work with no home (WAT-1, EST-1,
AUD-1/2/3, BEN-1, VW-E2-CMD, CDX-SIG-STALE, FAB-ACK-GAP, CDX-NEXTID, T-009-BOARD,
CDX-ACK-GAP). Difficulty S/M/L/XL is judgment, `Inferred`, uncalibrated by any measured build.

## §1 THE TOTAL

| population | count |
|---|---:|
| **Inventoried, unique** | **226** |
| − stale (premise dead; strike candidates for Rab's word) | 25 |
| − delivered by S112 (strike with evidence) | 6 |
| − duplicates folded onto a canonical id | 31 |
| **= LIVE tickets** | **164** |

**Live by difficulty:** quickest **86 S** · **54 M** · **18 L** · hardest **6 XL**.
**Live by blocker:** **92 blocked-on-rab** (56% — mostly signatures, not labor) ·
**61 open** (buildable without anyone's permission) · 4 signed-in-flight · 7 blocked-on-codex.

The single loudest fact in the census: **the majority of File Portal's backlog is a signature
queue, not a work queue.** One sitting of Rab's pen on the S-difficulty decision rows would
cut the live board nearly in half.

## §2 THE SEQUENTIAL ROADMAP

Phases are ordered by dependency and gate, not taste. Rab's three hard gates are marked ⛩.

- **P0 — Land tonight's book (now → tomorrow).** The Damodaran finishes → ⛩ **BEN-1** first
  live bench run (the one open gate on OK-0/1/2/7) · **S105-10-2** P-1 re-measured on the
  clean bundle (retires the oldest measurement debt) · signed **OK-16** ollama pre-convert
  unload · signed **OK-17 + WAT-1** — the stall-ladder fix bundle (CRITICAL split-rung asset
  loss, honest batch/cost records, retry labels, T1–T10 tripwires, watcher tree-kill + derived
  cap). *This doc + the S112 records are OK-17's written home; the review previously lived
  nowhere.*
- **P1 — Honest instruments (an evening of S-tickets, minimal signature).** **M6-R1**
  fail-closed capped-evidence decisions (**DONE `57a5da6`**) · **EST-1** one cost estimator,
  not two · **CDX-SIG-STALE**
  correction entry · **FAB-ACK-GAP** receipt the seven unconfirmed Codex messages · register
  repairs F1/F3/J17/J18 · quick symptom builds B6/B7/B8/B9/B13/J16.
- **P2 — Verdict semantics ⛩ (Rab's signatures; changes what `fail` means).** **AUD-2** gate
  degeneration on stripped markdown (SYM-067 — the empty-cell false positive that failed
  tonight's book) paired with **AUD-3**, a real structure-damage detector so the accidental
  catch isn't just released · **S110-D1** ship-with-losses-named vs audit-must-be-green — the
  one ruling the whole record says moves the north star · then the held/ pile: S108-7/S108-8,
  A38, A39 (Valentine, deferred by name five times), B26.
- **P3 — The Visual Witness chain ⛩.** FIRST: **VW-E2-CMD** — the operator run command lives
  only in a thread-scoped Codex artifact; the repo cannot run the calibration without
  recovering it (the census's largest gap). Then **VW-E2-CAL** (Rab's hand) → **VW-E2-VER**
  (frozen verifier) → **VW-E3-PKT** (Codex authors, unsigned display) → ⛩ **VW-E3-SIGN** →
  **VW-HEADEQ** + **VW-LEVERS** (Codex design debts) · board hygiene T-009-BOARD /
  CDX-ACK-GAP / CDX-NEXTID · then the sealed program E4→E8 (XL, sequential by contract).
- **P4 — Bench wave 2 (A49's remaining signatures).** **AUD-1 / M6-R2** pageable or
  identity-bound full-evidence review (M) → OK-8 zoom (S) → OK-3 prefetch (M) →
  **OK-4 search (M)** → **OK-5 text layer (L)** → OK-6 table tool (M, the SYM-003 weapon) →
  OK-11 watch/swap · OK-12 typed flags · OK-14 · OK-15 · OK-10 reviews panel.
- **P5 — Program-scale.** OK-13 paged reader · OK-9 unified undo · A44 hOCR side-input (XL) ·
  B10/SYM-049 stroke-geometry clustering · A2 stage-2 GO · **C0-CADENCE** (gated on D1) ·
  A35 bench doctrine · A33/docs-40 platform decision · E-P3 RETAS · B23 · A37 · A12 · B32 · D3.

Alongside all phases, **the signature queue** (57 pure-decision rows, mostly S) can drain in
any Rab sitting; and **the open pool** (42 buildable rows) feeds idle capacity.

## §3 Census findings that are themselves actionable

1. **VW-E2-CMD** — see P3; unrunnable-from-repo calibration is a single-point-of-failure on
   a thread artifact.
2. **CDX-SIG-STALE** — `SIGNATURES.md:284` still names producer `e7a3100a…`; the live file
   measures `a4c789d8…` (docs/48 agrees). Append-only fix: a correction entry.
3. **F3 vs SYM-032** — OPEN-TASKS says the false-open repair happened; the symptom cell still
   reads `open`. One file, two claims; needs a striking hand.
4. **OPEN-TASKS' own arithmetic is drifting again** — headline says 110, rows count 111 (A49
   appended without touching the headline; §H's predicted rot, second firing).
5. **Seven docs/49 §1 candidates carry no ticket** (tiles, cheap-nav wins, parallel text
   pre-extraction, PyMuPDF typography, XY-cut oracle, tagged-PDF sidecar, central-pixel rule)
   — inventoried as A49 sub-scope, deliberately not minted; they become tickets when signed.
6. **12 of Codex's 14 `gate.py owed` items are discharged-in-fact but never discharged on the
   board** — the mechanical `gate.py discharge` form is the fix; one (CDX-NEXTID's id-reuse
   hazard) is genuinely open.

## §4 Honesty box

Difficulty grades are `Inferred` throughout. The census lanes' own residue: `Historical` rows
taken as written where probing was expensive; `coordination/private/`, `.codex/`, and
S104–S110 closeouts beyond citations not swept — a ticket recorded only there is missing;
`gate.py owed` self-labels single-lane, and its discharge judgments inherit that discount.
The board is a **map of the record**, not a promise: nothing below starts without its gate,
and every strike/fold in §1's arithmetic awaits Rab's word before any register row moves.


## §5 The tables (generated from the census; canonical ids)

### P0 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| BEN-1 | First live-browser run of the four built OK tickets | S | blocked-on-rab | OK-0,OK-1,OK-2,OK-7 | sessions/S112-fable-sign-sheet.md:66-69 |
| OK-16 | Pre-convert ollama unload frees 1.5-2.0 GB VRAM | S | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:57 · built 46f7a68 |
| S105-10-2 | Re-measure P-1 on a clean post-S60 bundle | S | open | - | sessions/S105-desktop-2026-08-20.md:183; OPEN-TASKS.md:285 (D3 item 3) |
| WAT-1 | Watcher 6h cap and single-pid timeout kill | S | done-by-s113 | OK-17 | watch_and_convert.py:60 FP_CONVERT_TIMEOUT_S lever (default 28800) + :442 taskkill /T /F tree-kill — the row's old source cell described the pre-repair state |
| OK-17 | Review, fix, commit stall ladder; CRITICAL split-rung asset loss | M | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:58 · built 3d6775b (41-tripwire selftest) + fe2978c |

### P1 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| B13 | Bench UI has no triage/report/ledger buttons | S | open | - | OPEN-TASKS §B B13; S76 §18.4 |
| B6 | SYM-044 one-line fix: read importlib.metadata.version | S | open | - | OPEN-TASKS §B B6 |
| B7 | SYM-045 mechanical id preflight against collisions | S | open | - | OPEN-TASKS §B B7 |
| B8 | SYM-046 close check refusing an unscoped glass claim | S | open | - | OPEN-TASKS §B B8 |
| B9 | SYM-047 watcher writes a pid/parent file for the widget | S | open | - | OPEN-TASKS §B B9 |
| CDX-SIG-STALE | SIGNATURES.md still names superseded producer hash e7a3100a | S | open | - | SIGNATURES.md:284 vs docs/48:343 and live file measured a4c789d8… |
| EST-1 | Unify the two per-page cost estimators | S | open | - | windows-converter/convert_and_ship.py:632 (ledger cost_s) vs :1065 (converted event wall) |
| F1 | The Change Ledger table is physically split | S | open | - | OPEN-TASKS §F F1; `CLAUDE_README.md:1127,1972` |
| F3 | Four false OPENs in the symptom status column | S | open | - | OPEN-TASKS §F F3; SYM-032 still reads open |
| FAB-ACK-GAP | Fable never receipted MSG-CDX-0010/0021/0022/0023/0025/0026/0027 | S | open | - | coordination/ack-fable.json confirmed list |
| J16 | widget:age_s is computed and unrendered | S | open | - | OPEN-TASKS §J J16; `line.rs:106`, no JS reader |
| J17 | Ledger row cell shape is undocumented and unvalidated | S | open | - | OPEN-TASKS §J J17; `muster.sh:122-129` |
| J18 | UNREAD: did [3b]'s tail alarm fire on the malformed row | S | open | - | OPEN-TASKS §J J18; `Observed 2026-08-25` |

### P2 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| B26 | Remove the wrong-page embed in Valentine | S | open | - | OPEN-TASKS §B B26; S79 §18.5 |
| S108-7 | Four held/ bundle dispositions | S | blocked-on-rab | S110-D1 | sessions/S108-SIGN-SHEET.md:22 |
| S108-8 | SYM-050 physical disposition: leave flagged or quarantine | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:23 |
| S110-D1 | C0 done-when: ship-with-losses-named or audit-must-be-green | S | blocked-on-rab | - | sessions/S110-SIGN-SHEET.md:56 |
| A38 | A product session for held/ — five bundles undispositioned | M | blocked-on-rab | - | OPEN-TASKS §A A38; S83-85 §18 |
| A39 | The guided Valentine session — deferred by name five times | M | blocked-on-rab | - | OPEN-TASKS §A A39; S78 §18.4 |
| AUD-2 | Gate degeneration on stripped markdown, not raw | M | blocked-on-rab | - | SYMPTOM-INDEX.md:86 (SYM-067); windows-converter/fidelity_audit.py:264-313,371,436 |
| AUD-3 | Structure-damage detector replacing the false positive's accidental catch | M | open | AUD-2 | SYMPTOM-INDEX.md:86 (SYM-067 empty-cell grids, phantom columns, 30-row promotions) |

### P3 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| CDX-ACK-GAP | Codex owes digest-confirmation of MSG-FAB-0044…0049 | S | blocked-on-codex | - | coordination/ack-codex.json confirmed list ends at MSG-FAB-0043 |
| CDX-NEXTID | next_id() can reuse a message id after a sidecar rewind | S | open | - | MSG-CDX-0008 residual 2 (relay.md:2803); no register row exists |
| T-009-BOARD | Close T-009 on the board; clear stale Codex blocked-on-ack | S | blocked-on-rab | FAB-ACK-GAP | gate.py status (Codex state=blocked-on-ack ticket=T-009); MSG-CDX-0026; MSG-FAB-0048 |
| VW-E2-CMD | Recover the E2 operator run command into a durable private-layer home | S | blocked-on-codex | - | census 2026-08-30: docs/48:356 points at a thread-scoped Codex artifact; repo holds no inv |
| VW-E3-SIGN | Rab signs the exact VW-E3-R1 packet bytes | S | blocked-on-rab | VW-E3-PKT | docs/48:9,358; SIGNATURES.md:190; MSG-FAB-0048 "E3 UNSIGNED" |
| VW-HEADEQ | Decide head-equality assertion intent: ancestor check vs freeze seal | S | done-by-s113 | - | Ancestor semantics selected from packet rule; repair `583f752`; SYMPTOM-INDEX.md:84 (SYM-065) |
| VW-E2-CAL | Run the real VW-E2-R2 calibration; runs still zero | M | blocked-on-rab | - | sessions/S112-desktop-2026-08-28.md:212,271 |
| VW-E2-VER | Independently verify returned calibration evidence, emit COMPLETE receipt | M | blocked-on-rab | VW-E2-CAL | docs/48:357-358; windows-converter/visual_witness_verify.py (25,251 B, b5c5e7b3…) |
| VW-LEVERS | Convert ~31 frozen VW producer constants to levers next R-revision | M | blocked-on-codex | VW-E3-PKT | S112 §Close-gate dispositions (LEVERS 35, 4 waived); MSG-FAB-0049 |
| VW-E3-PKT | Author and hash unsigned VW-E3-R1 packet, display PROPOSED-UNSIGNED | L | blocked-on-codex | VW-E2-VER | docs/48:321-332; packet-r2 "unlock preparation—not execution—of VW-E3-R1"; S112 §8 |
| VW-E4 | Sealed-corpus event 4; function unnamed, CPU-only, last raw-ephemeral event | XL | blocked-on-rab | VW-E3-SIGN | docs/48:200,210; e1-contract cpu_only list ("VW-E4") |
| VW-E5 | Analyst-proposal validator: bind prompt/contract hashes, validate protected spans | XL | blocked-on-rab | VW-E4 | docs/48:56-63,210; e1-contract "VW-E5-validator" |
| VW-E6 | Read-only evidence review: side-effect-free reader plus intent ledger | XL | blocked-on-rab | VW-E5 | docs/48:64-68,210; e1-contract "VW-E6-read-only" |
| VW-E7 | First scored use of held-out VW-H01–H03 after all hashes sealed | XL | blocked-on-rab | VW-E6 | docs/48:111,211,229; e1-contract held_out_rule + gpu "VW-E7-model-samples" |
| VW-E8 | Production mutation; explicitly outside the current commission | XL | blocked-on-rab | VW-E7 | docs/48:31,344 (event_exit_rule spans E1–E8) |

### P4 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| AUD-1 (M6-R2) | Make every hidden run/zone reviewable through pageable evidence or identity-bound uncapped recomputation | M | blocked-on-rab | M6-R1 | SYM-066; MSG-FAB-0062; M6-R1 deliberately stops at fail-closed safety |
| OK-14 | Widget: forward-instead-of-die single instance | S | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:34,51 · signed+built 2026-08-31, 091ffd7 |
| OK-8 | Zoom ladder, fit modes, computed dpi, loupe | S | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:28,49 · signed+built 2026-08-31, be191bf |
| OK-10 | Reviews panel over repair sites | M | signed | OK-0 | sessions/S112-fable-sign-sheet.md:30,50 · signed 2026-08-31 (f8e89e7), banked MSG-FAB-0055 |
| OK-11 | Watch, reload, swap under the writing pipeline | M | signed | - | sessions/S112-fable-sign-sheet.md:31,50 · signed 2026-08-31 (f8e89e7), banked MSG-FAB-0055 |
| OK-12 | Observability grammar: typed flags, severity ladder, toasts | M | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:32,51 · signed+built 2026-08-31, be191bf |
| OK-15 | Graduate the completed quarantine evidence parcel into pipeline bundle evidence | M | blocked-on-rab | - | quarantine prototype `77d0361`; review close `8da7005`; peer delta PASS `MSG-FAB-0059`; sessions/S112-fable-sign-sheet.md:5-14,35,52 |
| OK-3 | Prefetch, priorities, cancellation by request-generation token | M | signed | - | sessions/S112-fable-sign-sheet.md:23,47 · signed 2026-08-31 (f8e89e7), banked MSG-FAB-0055 |
| OK-4 | The search suite: debounce, traversal, honest feedback | M | done-by-s113 | OK-5 | sessions/S112-fable-sign-sheet.md:24,48 · signed+built 2026-08-31, 0181636 |
| OK-6 | Table divider tool over char plus space rects | M | done-by-s113 | OK-5 | sessions/S112-fable-sign-sheet.md:26,49 · signed+built 2026-08-31, cd5b10e (shipped inert, caught+fixed 6dae0fb) |
| OK-5 | Text layer for the raster pane | L | done-by-s113 | - | sessions/S112-fable-sign-sheet.md:25,48 · signed+built 2026-08-31, 80df03b |

### P5 tickets

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| A33 | Pick one docs/40 §10 decision gate before platform build | M | blocked-on-rab | - | OPEN-TASKS §A A33; `docs/40` §10 |
| A12 | GLM bench second-reader — build or don't | L | blocked-on-rab | - | OPEN-TASKS §A A12; S84 §18.2 |
| A2 | Stage 2 GO — converter tests plus CI | L | blocked-on-rab | - | OPEN-TASKS §A A2; `docs/37` §1,§3.4 |
| A35 | The Repair Bench's operating doctrine is undiscovered | L | blocked-on-rab | A13 | OPEN-TASKS §A A35; `docs/26` |
| A37 | The scan-lane challenger — own design, A-B gate | L | blocked-on-rab | - | OPEN-TASKS §A A37; S84 §18.4 |
| B10 | SYM-049 clustering that follows stroke geometry | L | open | - | OPEN-TASKS §B B10 |
| B23 | 219 of 239 IV uncovered pages never adjudicated | L | open | - | OPEN-TASKS §B B23; `docs/45` §6.5 |
| B32 | Verify Codex's six product defects U01-U06 independently | L | open | - | OPEN-TASKS §B B32; completion-audit 2026-08-27 |
| C0-CADENCE | C0 output cadence; C0's third done-when clause still unmet | L | blocked-on-rab | D1 | S108:210; OPEN-TASKS.md:406,410 (J10/J14) |
| D3 | The next Circle collects docs/45 §6's five-item bequest | L | open | - | OPEN-TASKS §D D3; `docs/45` §6 |
| E-P3 | P-3 RETAS text-loss locator — never scheduled | L | open | - | OPEN-TASKS §E; `docs/41` |
| OK-13 | Paged markdown reading surface, server-paginated | L | signed | - | sessions/S112-fable-sign-sheet.md:33,51 · signed 2026-08-31 (f8e89e7), banked MSG-FAB-0055 |
| OK-9 | Unified undo command stack replacing three systems | L | signed | OK-0 | sessions/S112-fable-sign-sheet.md:29,50 · signed 2026-08-31 (f8e89e7), banked MSG-FAB-0055 |
| A44 | hOCR as a supplied side-input — intake contract change | XL | blocked-on-rab | - | OPEN-TASKS §A A44; `coordination/BRIEF-S109.md` |


## The signature queue (Rab's pen, no build blocked behind most)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| A1 | Asset posture on out-of-range assets: warn/fail/quarantine | S | blocked-on-rab | - | OPEN-TASKS §A A1; `docs/37` §3.3 |
| A10 | docs/34 rule 8 countersign | S | blocked-on-rab | - | OPEN-TASKS §A A10; S83 §18.4 |
| A13 | docs/26 F8 — ambient terracotta carve-out or desaturate | S | blocked-on-rab | - | OPEN-TASKS §A A13; `docs/26` |
| A14 | docs/26 F7/F13/F15 — amend the motion ban | S | blocked-on-rab | - | OPEN-TASKS §A A14; `docs/25` Part 3 |
| A15 | docs/26 F6 — relabel the fictional agreement lane | S | blocked-on-rab | - | OPEN-TASKS §A A15; `docs/26` |
| A19 | S105 #1 — stop opening a session per work item | S | blocked-on-rab | - | OPEN-TASKS §A A19; `sessions/S105` §10 |
| A23 | S105 #6 delete /echo the skill, keep the lexicon | S | blocked-on-rab | - | OPEN-TASKS §A A23 |
| A25 | S105 #8 narrow the tag law | S | blocked-on-rab | - | OPEN-TASKS §A A25 |
| A26 | S105 #9 invert glass's default to --enforce-on | S | blocked-on-rab | - | OPEN-TASKS §A A26; `glass_detector.py:338` |
| A27 | S105 #12 correct the S102/S103 ledger rows and CHANGELOG | S | blocked-on-rab | - | OPEN-TASKS §A A27 |
| A28 | S105 #13 sign docs/32 §5's three rules | S | blocked-on-rab | - | OPEN-TASKS §A A28; `docs/32:134` |
| A30 | Ctrl+Z dead in the Bench — built S108, ratification pending | S | blocked-on-rab | - | OPEN-TASKS §A A30; `0f0e83f` |
| A34 | Rab's narrated legend for the sketch's nodes | S | blocked-on-rab | - | OPEN-TASKS §A A34; S97 §18.3 |
| A40 | Cybernetics-stale copy plus Textor re-download and Marker swap | S | blocked-on-rab | - | OPEN-TASKS §A A40; S68-S73 §18 |
| A41 | Decide c5afd9edcf620fc6 — held and vaulted simultaneously | S | blocked-on-rab | - | OPEN-TASKS §A A41; S96 §18.4 |
| A42 | The windows-converter test decision | S | blocked-on-rab | - | OPEN-TASKS §A A42; S86 §18.4 |
| A43 | Give the memory library's git a remote | S | blocked-on-rab | - | OPEN-TASKS §A A43; S96 §18.7 |
| A48 | Resolve the two docs/36 §8 questions no row mirrors | S | blocked-on-rab | - | OPEN-TASKS §A A48; `docs/36` §8 |
| A7 | Generative-SR standing ban — record or defer-with-criteria | S | blocked-on-rab | - | OPEN-TASKS §A A7; `docs/37` §3.9 |
| A8 | SPOT_CHECK_EVERY 10 to 3-5 | S | blocked-on-rab | - | OPEN-TASKS §A A8; `docs/37` §3.5 |
| A9 | Stale-hold reap countersign | S | blocked-on-rab | - | OPEN-TASKS §A A9; S85 §8.2 |
| B2 | .agents/ — delete it or keep it marked; gate.py drift | S | blocked-on-rab | - | OPEN-TASKS §B B2; `.gitignore:71` |
| D1 | Ship-with-losses-named versus audit-must-be-green | S | blocked-on-rab | - | sessions/S110-SIGN-SHEET.md:56; S112:367 |
| D8 | Rab's hands: the S94 guard exercise plus P-0's figures line | S | blocked-on-rab | - | OPEN-TASKS §D D8; record conflict with S102 row |
| F11 | This register — work it down or delete it | S | blocked-on-rab | - | OPEN-TASKS §F F11 |
| F12 | SYM-051(b) cites 15.9 GB RAM; machine measures 31.9 GB | S | blocked-on-rab | - | OPEN-TASKS §F F12; `Observed 2026-08-25` |
| F9 | S96's untouched next-entry list needs explicit prioritization | S | blocked-on-rab | - | OPEN-TASKS §F F9; S97 §18.4 |
| S108-1 | Ratify the bench undo model (contenteditable, beforeinput) | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:11 |
| S108-10 | A43: private remote for the memory library | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:25 |
| S108-11 | S94 guard exercise, Rab's hands, 12-plus sessions overdue | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:31; sessions/S94-GUARD-EXERCISE-FORM.md |
| S108-12 | Atlas MANUAL-ACCEPTANCE plus two AA contrast fixes | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:32 |
| S108-13 | Policy: pack eviction priority on send-budget overflow | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:38 |
| S108-14 | Policy: countersign rule for agent-transcribed signatures | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:39 |
| S108-2 | Ratify P-1's out-of-band host (coverage_rescore.py) | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:12 |
| S108-3 | Ratify the G-lane trade: force-kill ends GPU run | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:13 |
| S108-4 | Ratify loopback token posture on 14 mutating routes | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:14 |
| S108-5 | Ratify token entropy: 28-hex, loopback-CSRF grade | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:15 |
| S108-9 | Arm DOCTOR and CENSUS gates in close.sh and CI | S | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:24 |
| S110-C1 | Tag decided at probe design, never at write-up | S | blocked-on-rab | - | sessions/S110-SIGN-SHEET.md:47 |
| S110-C2 | Rab names what the session is for, at open | S | blocked-on-rab | - | sessions/S110-SIGN-SHEET.md:48 |
| A11 | The wrapper decision — two engines or one | M | blocked-on-rab | - | OPEN-TASKS §A A11; S83 §18.3 |
| A16 | docs/26 F4+F5 — doc_survival fabricated 1.0, Wall hero | M | blocked-on-rab | - | OPEN-TASKS §A A16; `docs/26` |
| A17 | docs/26 F3 — terracotta colour policy, decide with slice 3 | M | blocked-on-rab | A13 | OPEN-TASKS §A A17; `docs/26` |
| A24 | S105 #7 cut the closeout contract to 6 sections | M | blocked-on-rab | - | OPEN-TASKS §A A24; `docs/21` |
| A3 | Stage 3 GO — the verified transport seam | M | blocked-on-rab | - | OPEN-TASKS §A A3; `docs/37` §3.4, `docs/08` |
| A31 | Post-close continuation — new session number or ledger form | M | blocked-on-rab | - | OPEN-TASKS §A A31; muster guards |
| A36 | Transcribe thresholds plus repair audit-credit | M | blocked-on-rab | A35 | OPEN-TASKS §A A36; S71/S72 §18 |
| A45 | Finish docs/30's open algedonic choices | M | blocked-on-rab | - | OPEN-TASKS §A A45; `docs/30:97-214` |
| A46 | Choose the Room queue-order contract | M | blocked-on-rab | - | OPEN-TASKS §A A46; `line.rs:82-98`, `room.js:155-172` |
| A5 | P-2 / #598 tripwire disposition | M | blocked-on-rab | - | OPEN-TASKS §A A5; `docs/37` §3.7 |
| A6 | DPI operating point (P-5) | M | blocked-on-rab | - | OPEN-TASKS §A A6; `docs/37` §3.8 |
| B31 | End-to-end manual test on real hardware | M | blocked-on-rab | - | OPEN-TASKS §B B31; `docs/08` v0/v1.5 |
| J13 | The phase-transition relay: tested, not adopted | M | blocked-on-rab | - | OPEN-TASKS §J J13; `docs/47` §8 |
| J7 | The disclosure standard and private-layer doctrine are drafts | M | blocked-on-rab | - | OPEN-TASKS §J J7; `DISCLOSURE-STANDARD.md` |
| S108-15 | Commission adversarial review of Concordance Lab dossier | M | blocked-on-rab | - | sessions/S108-SIGN-SHEET.md:40 |
| T-004 | Joint seam: EXTRACTED vs AUTHORED term comparison | M | blocked-on-rab | - | coordination/T-004-EXTRACTED-SCHEMA.md:23; S108:208; OPEN-TASKS.md:402 (J6) |
| D7 | ThinkPad lane: enrichment consumer, docs/14 Phase A window | L | blocked-on-rab | - | OPEN-TASKS §D D7; S43 ledger row |

## The open pool (unphased buildable work)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| B12 | SYM-034 capture Ollama's own server log at the stall | S | open | - | OPEN-TASKS §B B12 |
| B14 | MIN_SIDE_PT and MAX_PAGE_FRACTION unlevered and unwaived | S | open | - | OPEN-TASKS §B B14; `figure_coverage.py` |
| B20 | Vary -ub on the one engine before concluding | S | open | - | OPEN-TASKS §B B20; S82 §18.4 |
| B21 | Test the table-loop deliberately on one mapped page | S | open | - | OPEN-TASKS §B B21; S84 §18.3 |
| B27 | resume auto-detect-analyzed — the Desktop one-liner | S | open | - | OPEN-TASKS §B B27; memory open queue |
| B30 | README demo GIF; public-vs-private already decided public | S | open | - | OPEN-TASKS §B B30; `docs/08` v3 |
| D6 | Two coordination messages still carry status open | S | open | - | OPEN-TASKS §D D6; `coordination/messages/` |
| F4 | S82's ledger row date disagrees with its closeout filename | S | open | - | OPEN-TASKS §F F4; S96 §18.5 |
| F7 | Reconcile the .Codex versus .claude memory namespace | S | open | - | OPEN-TASKS §F F7; S95 §18.5, untracked `.codex/` |
| F8 | SYM-046's own account of which closeouts cited it is wrong | S | open | - | OPEN-TASKS §F F8; `docs/45` F4 |
| J1 | Three threshold constants with no lever and no waiver | S | open | - | OPEN-TASKS §J J1; `close.sh` LEVERS |
| OWED-MSG-CDX-0008 | Escalation-generator verification; two residual bus risks kept open | S | open | CDX-NEXTID | gate.py owed; ack-fable confirms; stale-T-007 residual settled, next_id residual NOT |
| SYM-058 | Dock reports a bare survival N with no phase named | S | open | - | SYMPTOM-INDEX SYM-058 |
| SYM-059 | Dock card implies converter survival caused the verdict | S | open | - | SYMPTOM-INDEX SYM-059 |
| SYM-060 | Analyst evidence in the payload the Dock never shows | S | open | - | SYMPTOM-INDEX SYM-060 |
| SYM-061 | Every failed card offers both remedies as equally evidenced | S | open | - | SYMPTOM-INDEX SYM-061 |
| SYM-062 | gate.py resolve accepts any ten-character sentence | S | blocked-on-codex | - | SYMPTOM-INDEX SYM-062 |
| A29 | S105 #14 put the governance suites in CI | M | open | - | OPEN-TASKS §A A29; `ci.yml` |
| A32 | The assay surface for the operator lever | M | open | A4 | OPEN-TASKS §A A32 |
| B11 | SYM-043 fix supersede/pending projection drift plus tripwire | M | open | - | OPEN-TASKS §B B11; S97 §18.1 |
| B15 | The omission-class bank entry — 18/18 runs unclassified | M | open | - | OPEN-TASKS §B B15; S79 §18.5 |
| B17 | Re-measure throughput with A-B-A on an idle card | M | open | - | OPEN-TASKS §B B17; `backend_parity.json` |
| B19 | The analyst has no llama.cpp call path | M | open | - | OPEN-TASKS §B B19; S80-82 §18 |
| B24 | Events rotation, verified_from stamps, cross-day date stamp | M | open | - | OPEN-TASKS §B B24; S68-S70 §18 |
| B28 | Windows half of the v2 feedback loop plus toasts | M | open | - | OPEN-TASKS §B B28; `docs/08` v2 |
| B29 | Package the widget and document second-machine install | M | open | - | OPEN-TASKS §B B29; `docs/08` v1 |
| B33 | Repair the two S111 close-gate evidence boundaries | M | open | - | OPEN-TASKS §B B33; SYM-063, SYM-064 |
| D4 | docs/32 §6's falsifiable prediction — uncollected 25 sessions | M | open | - | OPEN-TASKS §D D4; `docs/33` §4 |
| D5 | SYM-039's fixes, assigned to Desktop by the ThinkPad | M | open | - | OPEN-TASKS §D D5; wip-handoff §2.6 |
| E-P4 | P-4 LLM as adjudicator, never as searcher — never scheduled | M | open | - | OPEN-TASKS §E; `docs/41` |
| J12 | docs/47's four unexercised clauses have no tripwire | M | open | - | OPEN-TASKS §J J12; `docs/47` §7 |
| J14 | Ashby convert measurement debt plus the 61-array defect | M | open | - | OPEN-TASKS §J J14; MSG-CDX-0014 |
| J3 | A fleet law needs a process census, not just digests | M | open | - | OPEN-TASKS §J J3; SYM-054 |
| J4 | close.sh takes 8m37s — a close nobody can afford | M | open | - | OPEN-TASKS §J J4; `Observed 2026-08-24` |
| J5 | relay-room's NOT_YET suites are declared, not built | M | open | - | OPEN-TASKS §J J5; `prototypes/relay-room/test_room.py` |
| J6 | T-004's joint half blocked on the Codex lane | M | blocked-on-codex | - | OPEN-TASKS §J J6; `T-004-EXTRACTED-SCHEMA.md` |
| SYM-024 | Routed gate card produces no analyst; hardened, not root-caused | M | open | - | SYMPTOM-INDEX SYM-024 |
| SYM-053 | Scan-lane blank crop passes as a covered page | M | open | A44 | SYMPTOM-INDEX SYM-053 |
| SYM-055 | Digest function swappable to md5 while still labelled sha256 | M | open | - | SYMPTOM-INDEX SYM-055 |
| A47 | Adversarial challenge of all four docs/40 theses | L | signed | - | OPEN-TASKS §A A47; `relay.md:4310-4317` |
| A49 | Pick adoptions from the Okular digest — 4 of 15 picked | L | signed | - | OPEN-TASKS §A A49; `sessions/S112-fable-sign-sheet.md` |
| B3 | Observability standing debt — 57 unsigned glitches, 60 sites | L | open | - | OPEN-TASKS §B B3; `acceptance.py` census |

## Strike candidates (stale — premise dead, Rab's word strikes them)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| A20 | S105 #3 product clock on the card — built S108 | S | stale | - | OPEN-TASKS §A A20; S108 lane F |
| A22 | S105 #5 suspend the relay — signed KEPT, premise dead | S | stale | - | OPEN-TASKS §A A22; Codex returns 2026-08-23 |
| A4 | P-1 HOST variable — signed S108, built out-of-band | S | stale | - | OPEN-TASKS §A A4; `0fbb6e3` |
| B1 | acceptance.py RED 40/41 — resolved S108 | S | stale | - | OPEN-TASKS §B B1; `57abcd9` |
| B4 | windows-converter outside CI's lint set — resolved S108 | S | stale | - | OPEN-TASKS §B B4; S108 wave 1b |
| CDX-GATEREV | Codex monitor runs gate rev 349818a9; this shell runs 57187c87 | S | stale | - | gate.py status "*** running 349818a9, this shell runs 57187c87 ***" |
| F10 | Delete the stale pre-rewind survival-audit-spec.md | S | stale | - | OPEN-TASKS §F F10; file absent from disk |
| J15 | The debt gate under-counts by formatting | S | stale | - | OPEN-TASKS §J J15; `close.sh:384` both spellings |
| OWED-MSG-CDX-0002 | Residency recap; complete on Fable re-digest and confirm | S | stale | - | gate.py owed; ack-fable.json confirms MSG-CDX-0002; MSG-CDX-0007 recomputed digest match |
| OWED-MSG-CDX-0003 | T-006 mirror-test artifact; complete on the comparison report | S | stale | - | gate.py owed; discharged by MSG-CDX-0004 "T-006 closed: asymmetric output swap" |
| OWED-MSG-CDX-0004 | T-006 complete on Fable confirm or evidence-bearing correction | S | stale | - | gate.py owed; ack-fable.json confirms MSG-CDX-0004 |
| OWED-MSG-CDX-0005 | Lane occupancy plus private-boundary endorsement | S | stale | - | gate.py owed; ack-fable.json confirms MSG-CDX-0005 |
| OWED-MSG-CDX-0006 | T-005 freshness check; binary ENDORSE-UNCHANGED or AMEND-FIRST | S | stale | - | gate.py owed; discharged by MSG-CDX-0007 (ENDORSE-UNCHANGED delivered) |
| OWED-MSG-CDX-0007 | T-005 two-model review complete on Claude confirm or correct | S | stale | - | gate.py owed; discharged by MSG-FAB-0024 (Rab signed CR-CDX-0002, T-005 resolved), restate |
| OWED-MSG-CDX-0009 | Final stand-down on T-008; no unfinished deliverable | S | stale | - | gate.py owed (ack=n/a); the DONE slot is itself the terminal outcome |
| OWED-MSG-CDX-0010 | S110 return notice; no ticket taken | S | stale | FAB-ACK-GAP | gate.py owed (ack=n/a); terminal notice, self-reporting outcome |
| OWED-MSG-CDX-0011 | T-009 delivered on four-field Fable reply plus one Codex reply | S | stale | - | gate.py owed; discharged by MSG-CDX-0012 "T-009 COMPLETE" |
| OWED-MSG-CDX-0012 | T-009 completion understanding statement | S | stale | - | gate.py owed; terminal statement, ack-fable confirms MSG-CDX-0012 |
| OWED-MSG-CDX-0013 | Accept the split: Fable repairs, Codex verifies | S | stale | - | gate.py owed; enacted through S110/S111/S112 records; ack-fable confirms |
| OWED-MSG-CDX-0014 | SYM-056 semantic count corrected to 61 unmatched opens | S | stale | - | gate.py owed; outcome carried into OPEN-TASKS.md:410 (J14 cross-vendor correction) |
| OWED-MSG-CDX-0015 | Return all 23 pointer rows with landings and controls | S | stale | - | gate.py owed; discharged by MSG-CDX-0017 (5/23 land, 18/23 miss) |
| SYM-032 | .gpu-lock is write-only; status cell still falsely reads open | S | stale | - | SYMPTOM-INDEX SYM-032; §C, F3 |
| D2 | Codex re-measures P-1 on a clean bundle — collected S108 | M | stale | - | OPEN-TASKS §D D2; `0fbb6e3` |
| E-P1 | P-1 figure completeness built and wired S108 | M | stale | - | OPEN-TASKS §E; `0fbb6e3` |
| S108-6 | GO: C0, the first conversion; Rab names the book | M | stale | S110-D1 | sessions/S108-SIGN-SHEET.md:21 |

## Delivered by S113 (strike with evidence)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| M6-R1 | Repair Bench and widget fail closed on capped, missing, or malformed evidence totals; A1-A4 | M | done-by-s113 | NUM-3 | Rab signature; `57a5da6`; SYM-070; 78/78 + 85/85 + widget 35/35; **reviewed S114 (Fable, MSG-FAB-0065): PASS + F1 (display cap in the manifest verdict); Codex closed F1 + a second boundary loss in `12f0ca9` (CDX-0043); controls re-run PASS 2026-09-02 (MSG-FAB-0066)** |

## Delivered by S112 (strike with evidence)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| F6 | MEMORY.md at the read limit — compaction is Rab's call | S | done-by-s112 | - | OPEN-TASKS §F F6; MEMORY.md now 127 lines |
| OK-0 | UUID identity for every repair-site manifest record | S | done-by-s112 | - | sessions/S112-fable-sign-sheet.md:20,46 (docs/49 §1 #9, AU-09) |
| OK-1 | Viewport sidecar: position restore, history, per-viewport bookmarks | S | done-by-s112 | - | sessions/S112-fable-sign-sheet.md:21,46 (docs/49-okular-digest.md:53-71) |
| OK-2 | Placeholder paint plus progressive first render | S | done-by-s112 | - | sessions/S112-fable-sign-sheet.md:22,47 (docs/49-okular-digest.md:73-82) |
| OK-7 | Trim margins: auto edge scan plus manual rect | S | done-by-s112 | - | sessions/S112-fable-sign-sheet.md:27,49 (docs/49-okular-digest.md:158-165) |
| B5 | Nothing in this repo tests bench.html | M | done-by-s112 | - | OPEN-TASKS §B B5; `test_bench_page.py` |

## Fold list (duplicates — canonical id named)

| id | ticket | diff | status | depends | source |
|---|---|---|---|---|---|
| B16 | seams[] and reverse_sample referenced by zero renderers | S | open | - | OPEN-TASKS §B B16; SYM-027 |
| B26 | Remove the wrong-page embed in Valentine | S | open | - | OPEN-TASKS §B B26; S79 §18.5 |
| E-P0 | P-0 wiring slice built; its acceptance is unlogged | S | blocked-on-rab | - | OPEN-TASKS §E; `docs/41` |
| E-P6 | P-6 generative-SR standing ban — not recorded | S | blocked-on-rab | A7 | OPEN-TASKS §E; `docs/41` |
| F2 | The protocol has no form for post-close work | S | open | A31 | OPEN-TASKS §F F2; `b9d0586`, `a3aed9d` |
| F5 | Correct the S102/S103 ledger rows and CHANGELOG | S | blocked-on-rab | - | OPEN-TASKS §F F5 |
| SYM-034 | Ollama request never returns; cause unknown, exposure bounded | S | open | - | SYMPTOM-INDEX SYM-034 |
| SYM-044 | Every manifest carries marker_version unknown | S | open | - | SYMPTOM-INDEX SYM-044 |
| SYM-045 | A freshly filed id already exists twice | S | open | - | SYMPTOM-INDEX SYM-045 |
| SYM-046 | A bare glass exit 0 cited as proof of clean | S | open | - | SYMPTOM-INDEX SYM-046 |
| SYM-047 | Orphan watcher survives a force-kill of the widget | S | open | - | SYMPTOM-INDEX SYM-047 |
| SYM-051 | Claude Code closes mid-session; (b) rests on a wrong RAM figure | S | blocked-on-rab | - | SYMPTOM-INDEX SYM-051 |
| SYM-057 | Perfect analyst fidelity reported on an unmeasurable book | S | open | - | SYMPTOM-INDEX SYM-057 |
| SYM-063 | close.sh prints MEMORY UNREAD on a healthy memory repo | S | open | - | SYMPTOM-INDEX SYM-063 |
| SYM-064 | A close prints through RUST then hangs indefinitely | S | open | - | SYMPTOM-INDEX SYM-064 |
| SYM-065 | Resolve VW selftest 53/54 by-construction anchor freeze | S | done-by-s113 | - | Repair `583f752`; 54/54 after source commit; SYMPTOM-INDEX.md:84 |
| SYM-066 | Every big book reports exactly 25 omission runs | S | open | - | SYMPTOM-INDEX SYM-066 |
| B18 | Raise n to 20-30 before quoting any ratio | M | open | - | OPEN-TASKS §B B18 |
| E-P2 | P-2 the #598 tripwire — not built, disposition unsigned | M | blocked-on-rab | A5 | OPEN-TASKS §E; `docs/41` |
| E-P5 | P-5 DPI as a measured experiment — not built | M | blocked-on-rab | A6 | OPEN-TASKS §E; `docs/41` |
| J10 | C0 half-moved — held bundles still have no disposition | M | open | - | OPEN-TASKS §J J10; `Observed 2026-08-27` |
| SYM-035 | Fixed-arm order drift; bounded and measured, not eliminated | M | open | - | SYMPTOM-INDEX SYM-035 |
| SYM-039 | Hardcoded prose numbers contradict live code | M | open | - | SYMPTOM-INDEX SYM-039 |
| SYM-043 | Dock/Room says manual swap while handlers exist | M | open | - | SYMPTOM-INDEX SYM-043 |
| SYM-054 | Agent fleet leaks live servers; digest audit cannot see them | M | open | - | SYMPTOM-INDEX SYM-054 |
| SYM-056 | 61 unterminated array environments ship with status passed | M | open | - | SYMPTOM-INDEX SYM-056 |
| SYM-067 | Empty-cell false positive drives convert-stage fail verdicts | M | blocked-on-rab | - | SYMPTOM-INDEX SYM-067 |
| SYM-070 | Bench recommended bless from a fully triaged capped subset | M | done-by-s113 | - | M6-R1 `57a5da6`; SYMPTOM-INDEX SYM-070 |
| VW-E3 | Sign and execute VW-E3 | M | blocked-on-rab | VW-E2-CAL | sessions/S112-desktop-2026-08-28.md:153,176,362 |
| SYM-003 | Table-loop degeneration; the Bench is the response, not a fix | L | open | - | SYMPTOM-INDEX SYM-003 |
| SYM-027 | Glass debt: criteria 2 and 3 not met | L | open | - | SYMPTOM-INDEX SYM-027 |
| SYM-049 | Diagram on the page, absent from the bundle, uncaught | L | open | - | SYMPTOM-INDEX SYM-049 |

## Correction 2026-09-04 (post-close, S114) — rows left as written

- **AUD-2** and the **SYM-067** row above read `blocked-on-rab` and cite
  `windows-converter/fidelity_audit.py:264-313,371,436`. Rab signed the gate on 2026-09-04 and it is
  **BUILT as J29** (`8aa8936`, amended `d9bfaaa` after the verification fleet): pipe-table rows are
  blanked to whitespace before `degeneration()` measures the body (`_blank_table_rows`), the count rides
  as `table_rows_stripped`; 34-file corpus sweep, 3 verdict flips, all Damodaran 2025 4e; SYM-067 is
  **FIXED**. The old line cell is superseded; the functions are named at HEAD.

