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
