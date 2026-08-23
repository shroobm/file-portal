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
