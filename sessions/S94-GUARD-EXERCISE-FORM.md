# The S94 Guard Exercise — acceptance form

⟨staged by S108, 2026-08-23, per the signed blank-ink pattern⟩

**Why this form exists:** the S94 single-instance guard has gone ~12 sessions with its
exercise unlogged (register D8 records the live conflict: MEMORY says unlogged, the S102
ledger row says exercised — both cannot be right). This form makes "nobody has run it"
visible as blank ink. Filled and dated by Rab's own hands at the real widget; no agent
may fill a line.

Exe under test (sha256 first-8): ______________  ·  Date: ____________  ·  Reviewer: RAB

| # | Exercise | Expected | PASS/FAIL | Note |
|---|---|---|---|---|
| 1 | Minimize the widget, launch the exe again | Restore-and-front; **no twin process** | ______ | |
| 2 | Room styling under CSP | Room renders styled (no CSP strip) | ______ | |
| 3 | Recent-audits panel | Populates from real events | ______ | |
| 4 | Chat page | Loads; assistant reachable | ______ | |
| 5 | Boot log | Config source is the boot log's claim (SYM-007 rule) | ______ | |
| 6 | Process table | Exactly **one** widget PID | ______ | |
| 7 | P-0 figures line on a real book | Renders count-not-coverage; null renders blank | ______ | |

Verdict (circle): **WITHSTOOD / BLOCKED** — "held" is retired per the S108 circle rules.
⟨correction 2026-09-05 (S115): "held" is NOT retired — the circle skill (`~/.claude/skills/circle/SKILL.md`, unchanged since 2026-08-13) still returns HELD as a verdict (line 101); the S108 circle rules were never imported (J37). The line above stands as written.⟩

On completion: strike register rows D8 and P-0's acceptance line in the same commit that
records this form's result (OPEN-TASKS §H rule 1).
