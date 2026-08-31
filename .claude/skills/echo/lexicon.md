# The Echo Lexicon — Rab's words → the project's names

Append-only. One row per **confirmed** mapping — a mapping enters only via `/echo` Phase 7,
after Rab's word committed the reading that used it (SKILL.md is the only writer's contract;
no other surface appends here). Never edit a row in place; a mapping that turns out wrong gets
a new superseding row citing the old one. Provenance column carries the date and the prompt
fragment (or "seed" for the founding entries, harvested S98 from the recorded history —
each seed traces to a real prompt in the cookie ledger, a session closeout, or MEMORY.md).

| Rab's word / phrase | Project name(s) | Where it lands | Provenance |
|---|---|---|---|
| turnout (for conversions) | the four measurable properties: text survival (`doc_survival`) · figure coverage · no silent transmutation · measured operating points | docs/41 §0 | seed — 2026-08-20 S97 commission, decomposition confirmed by his GO |
| differ (a part of this task) | defer / delegate to a subagent | S97 §4a | seed — 2026-08-20 "You can differ a part of this task to the Opus" |
| the Opus | an Opus-model subagent, usually worktree-isolated, for investigation past the orchestrator | S97 §4a; docs/41 Appendix A | seed — 2026-08-20, executed as the grounding investigator |
| muster | the session-open protocol: `/muster`, `open.sh`, the two clocks | `.claude/skills/muster/` | seed — standing since S79 |
| sign / signed / GO | a register signature; his word on a filed slot | docs/37 §3 | seed — standing; the strongest form is by slot reference ("F-09 per-slice signed") |
| the card | the RTX 3080 — one-process law, `Local\file-portal-card` mutex | convert_and_ship.py `acquire_card_mutex` | seed — standing |
| cookie | a tally entry in the library's cookie-tally.md, header + ledger, mirrored in TIME-STATE | memory library | seed — standing since 2026-07-19 |
| lockstep | both clocks advance together at close: ledger row + TIME-STATE | session-bootstrap; CLAUDE.md | seed — standing |
| held (a book) | a `fail`-verdict bundle parked in `held/<sha16>` awaiting remedy | `_enforce_hold`, convert_and_ship.py | seed — standing |
| the bench | the Repair Bench prototype (zone repair, adjudication surface) | prototypes/repair-bench/ | seed — standing since S62 |
| the room / wall / dock / assay | the widget's four surfaces | docs/16; room.rs | seed — standing since S34–S63 |
| full context search (in a prompt) | the echo sweep: `sweep.sh` + term hits + lexicon lookup | `.claude/skills/echo/` | seed — 2026-08-20, his Reading-B commission's own phrase |
| what I think I may mean | the echo's readings (Phase 3) + preview (Phase 4) | `.claude/skills/echo/SKILL.md` | seed — 2026-08-20, his verbatim protocol signature |
| the two clocks | HARD (git ledger row) × SOFT (cookie tally / TIME-STATE) | CLAUDE.md muster block | seed — standing since the S33 timekeeping design |
| free up resources / little brother gaming | clean shutdown: widget + watcher + convert procs down, zero GPU load at session end | S42 standing instruction | seed — standing since 2026-07-23 |
| stigmergy | coordination through traces left in a shared environment — how concurrent instances discover each other (adopted for the parallel-sitting phenomenon) | docs/43; SYM-045 | confirmed 2026-08-20 — "A+ B with a convention" committed the reading that proposed it |
| claiming (its) sections | authorship stamps ⟨claimed: Fable⟩ / ⟨claimed: Codex⟩ on prose sections, ledger rows, docs | coordination/authorship.md | confirmed 2026-08-20 — "It is time for Claude to start claiming it's sections" |
| 2 signals as one | the relay: each model carries the other's newest message + suggested prompt to Rab at session open (UTC entries) | coordination/relay.md | confirmed 2026-08-20 — "user always gets 2 signals as one for coordination" (echoes his S74 law "2 signals are just 1", cookie #60) |
| the parallel sitting | 2026-08-20's concurrent Fable+Codex work under one session number, stigmergically discovered | docs/43; S97 §4a | confirmed 2026-08-20 — his "parallel process happening simultaneously from two separate desktop models" |
| production first layer (for Claude–Codex cooperation R&D) | a production-ready intellectual/specification layer: evidence, boundaries, interfaces, failure model, negative tests, and staged adoption gates — **no executable protocol, runtime integration, or implementation authority** | Reading A aligned in chat; `docs/21` §2; `docs/40` §§10–11 | confirmed 2026-08-23 — "A, but … I do want that simulation" selected Reading A while asking to understand, not yet build, the quarantined simulation |
| multi-agent repository governance | File Portal's session-governance layer: Change Ledger and two clocks, dated registers, relay-gate sidecars, and claimed authorship | `wiki/governance.md` §§1–4, §8 | confirmed 2026-08-28 — "A and then C" committed Reading A's terminology map |
| state persistence (in a framework comparison) | for File Portal: the HARD/SOFT clocks, Git ledger/register history, and relay sidecars; external runtime checkpointing remains a separately verified comparison dimension | `wiki/governance.md` §§1–3, §8 | confirmed 2026-08-28 — "A and then C" committed Reading A's terminology map |
| sub-agent provenance | claimed model/occupant authorship plus evidence-tagged delegation ground, negative controls, and residue | `wiki/governance.md` §§6, §8; `ERROR-BIN.md` §A | confirmed 2026-08-28 — "A and then C" committed Reading A's terminology map |
| documentation synthesis | the wiki index and numbered-doc/register map used to navigate source-backed project knowledge, not a claim that every file has been packed into model context | `wiki/INDEX.md`; `wiki/governance.md` §6 | confirmed 2026-08-28 — "A and then C" committed Reading A's terminology map |
| repair the tables and rows in symptom index | one uninterrupted, numerically ordered six-column `SYMPTOM-INDEX.md` table; retain the SYM-015 evidence row beside its parent; move the row-writing law below the table; preserve every row payload byte-for-byte | `SYMPTOM-INDEX.md`; Echo Reading A aligned in chat | confirmed 2026-08-28 — "A" selected Reading A for "repair the tables and rows in symptom index" |

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5) · S112 · 2026-08-28⟩

## 2026-08-28 — visual-witness commission

| Rab's word / phrase | Project name(s) | Where it lands | Provenance |
|---|---|---|---|
| formatting libraries | a versioned formatting contract: protected-span parser, structure-aware chunker, candidate validator, and raw-chunk fallback — not a Markdown prettifier | `windows-converter/analyst.py`; `windows-converter/fidelity_audit.py` | confirmed 2026-08-28 — "A" selected the hybrid visual-witness reading |
| truncation / image slices | coverage-complete adaptive page tiling followed by fused source-page regions; tiles are a detector mechanism and may not discard pixels, text, or boundary-spanning candidates | proposed Visual Witness Map; `windows-converter/figure_coverage.py` | confirmed 2026-08-28 — "A" selected the hybrid visual-witness reading |
| pairs it with the converted captured text | a hash-bound regional evidence packet joining the source crop, native PDF text or independent OCR agreement/`UNREAD`, and an exact converted Markdown span | proposed Visual Witness Map; `prototypes/repair-bench/bench.py` | confirmed 2026-08-28 — "A" selected the hybrid visual-witness reading |

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5) · S112 · 2026-08-28⟩

## 2026-08-28 — visual-witness commission correction

| Rab's word / phrase | Project name(s) | Where it lands | Provenance |
|---|---|---|---|
| truncation / image slices (supersedes the preceding visual-witness row) | deterministic complete tiling of rendered page pixels under a signed configuration, followed by fused declared-region candidates; boundary hits are re-centered and unresolved page readability, model truncation, or semantic coverage remains `UNREAD` — this does **not** claim absolute semantic completeness | proposed Visual Witness Map; `windows-converter/figure_coverage.py` | corrected 2026-08-28 after independent plan review; Reading A remains unchanged |

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5) · S112 · 2026-08-28⟩

## 2026-08-30 — visual-witness revision and escalation

| Rab's word / phrase | Project name(s) | Where it lands | Provenance |
|---|---|---|---|
| R1 became R2 based on these added aspects | a corrective revision of the same event: preserve `VW-E2-R1` immutable as `STOPPED`, create `VW-E2-R2` with the verified missing report, structural-candidate, table, fusion, boundary, and negative-control rules, then develop and test that revision; it is not a second E2 aspect | `docs/contracts/visual-witness-e2-packet-r1.json`; `docs/contracts/visual-witness-e2-packet-r2.json` | confirmed 2026-08-30 — Rab directed the primary Echo reading after asking whether R2 was revised R1 or a different aspect |
| escalate the same ticket artifact updated, and ask for signature on E3 | after a verified `COMPLETE` E2-R2 receipt, update the existing nine-event observability artifact with R1/R2 history, display a separately hashed `VW-E3-R1` packet as `PROPOSED-UNSIGNED`, ask Rab for its signature, and stop without E3 execution | Visual Witness event artifact; VW-R1 event-transition law | confirmed 2026-08-30 — Rab's post-Echo corrective direction |

⟨claimed: Codex lane · occupant: OpenAI Codex (GPT-5) · S112 continuation · 2026-08-30⟩
| numeration | any stepping quantity in the pipeline: monotonic counters, gauges, daily resets — the census object | docs/51 (NUM-1) | 2026-08-31 "Any numeration that increases, decreases … each n+1 sequence" — Reading C signed "Signed, Both" |
| X amount of Omissions | the fidelity audit's `runs` count (SYM-066: display cap is not the count) | fidelity_audit.py:378 | 2026-08-31, same commission |
| caught or defined | emitted-somewhere vs should-exist-but-uncounted — census rows mark both | docs/51 (NUM-1) | 2026-08-31, same commission (Fable's reading, uncontested in the echo) |
| like the event streamer / live counter | a Room panel deriving live counter values from the feeds the Room already polls (projection, never authority) | room.js (NUM-2) | 2026-08-31 "map it to the glass … like the event streamer, i need that live counter" |
