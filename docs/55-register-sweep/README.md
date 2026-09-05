# docs/55 — The register sweep of 2026-09-04

*Rab: "how many tickets do we have open and that need to be done, all of it ... check the list, update it if need be."
Every live row of OPEN-TASKS.md and every OPEN row of SYMPTOM-INDEX.md was read whole and its premise checked
against HEAD bde007d by six Sonnet lanes (one per section group); a Fable verifier re-checked every row a lane
wanted to mark DONE / STALE / SUPERSEDED (60 checks: 54 confirmed, 3 overstated, 3 wrong — F4 and J7/J28 pulled
back to OPEN, SYM-046/047 pushed to FIXED) and spot-checked the rest. All six planted decoys were caught. Nothing
was run; every check was git log/show, grep and direct reads. The rows re-stamped carry a dated
 note appended to their first cell — the row text is never rewritten.*

-  — the verifier's report, grouped by owner.
-  — the rendered list: counts, the open rows by owner, the re-stamped rows.
-  — all seven agents' structured output ().

Counts at HEAD after the sweep: 121 open rows (3 of them PROPOSED), 17 done, 5 stale, 1 superseded; symptoms 28
open, 3 cells mislabelled OPEN while fixed in substance (SYM-032, SYM-046, SYM-047).
