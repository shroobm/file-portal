# docs/55 — The register sweep of 2026-09-04

*Rab: "how many tickets do we have open and that need to be done, all of it ... check the list, update it if need be."
Every live row of `OPEN-TASKS.md` and every OPEN row of `SYMPTOM-INDEX.md` was read whole and its premise checked
against HEAD `bde007d` by six Sonnet lanes (one per section group); a Fable verifier re-checked every row a lane
wanted to mark DONE / STALE / SUPERSEDED (60 checks: 54 confirmed, 3 overstated, 3 wrong — F4, J7 and J28 pulled
back to OPEN; SYM-046 and SYM-047 pushed to fixed-in-substance) and spot-checked the rest. All six planted decoys
were caught. Nothing was run: every check was `git log`/`show`, grep and direct reads. The rows re-stamped carry a
dated `⟨status 2026-09-04: …⟩` note appended to their first cell — the row text itself is never rewritten.*

## Files

- `VERIFIED.md` — the verifier's report, grouped by owner.
- `open-list-2026-09-04.md` — the rendered list: counts, the open rows by owner and effort, the re-stamped rows.
- `fleet-result.json` — all seven agents' structured output (`wf_081e7e5e-3c5`).

## Counts at HEAD after the sweep

| Register | Result |
|---|---|
| OPEN-TASKS rows read | 116 |
| still OPEN | 121 including 3 PROPOSED and the 31 symptom rows counted with them below |
| re-stamped DONE | A4 · A20 · A22 · B1 · B4 · B8 · B9 · D2 · J29 |
| re-stamped STALE | A49 · F6 · F10 · J4 · J6 |
| re-stamped SUPERSEDED | F5 (by A27) |
| SYMPTOM-INDEX open rows read | 31 |
| still open | 28 |
| fixed in substance, cell mislabelled | SYM-032 (`3446f7c`) · SYM-046 (`c9c0cf3`) · SYM-047 (`f045a66`) |

## By owner (open rows, both registers)

| Owner | Rows |
|---|---|
| Mechanical — a session can build it on the row's own words | 55 |
| Rab's signature — a decision only he makes | 53 |
| Rab's hands — adopt, run, observe, buy | 13 |
| Blocked on another row | 3 (A35 ← A13, A36 ← A35, SYM-035 ← SYM-022) |

The verifier's residue is in `VERIFIED.md`: nothing was executed, so J4's close.sh runtime and the muster
selftest tally rest on commit messages; vault-side facts (A41's vaulted half, B26's Valentine embed, J28's first
supersede) are out of reach from this repo.
