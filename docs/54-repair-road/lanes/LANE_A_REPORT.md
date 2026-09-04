# Lane A — the analyst-stage numbers (J32's evidence)

Verifier for GROUND docs/47 fleet, verifying J32 against Investment Valuation University
Edition 4e (held `14c66834bdfeaa2e`). Read-only on file-portal and ml/library. All scripts
under `verify-tickets/A/`, all written from scratch against the pipeline's own
`fidelity_audit.py` / `analyst.py` (never importing or trusting the builder's
`univ4e_*` scripts — those were read only as a cross-check on divergence, explicitly not
trusted).

## Claim 1 — mirror reproduces 0.9402 / 404 (CONFIRMED, exact)
`mirror_audit.py` rebuilds the Marker reference from the 7 slice.md files
(`"\n\n".join`, verified byte-for-byte against `convert_and_ship.py:1419/1456`), loads the
shipped analyst.md, calls the real `fidelity_audit.audit_analyst`. Result: doc_survival
0.9402, runs_total 404 — bit-exact match to `manifest.json`'s `fidelity.analyst` block.
windows_total = 40,438 (also exact); failed = 2,420 exactly (ticket's own number).

## Claim 2 — ladder 0.9564/0.9695/0.9718, 1763/1288/1141 failed (PARTIAL)
`ladder.py`, own regexes (unescape = strip backslash before any char; punct-free =
`[^\w\s]` stripped; space-free = containment check only, windows unchanged):
  - unescape:     1,769 failed / 40,419 windows -> 0.9562  (ticket: 1,763 / 0.9564)
  - +punct-free:  1,169 failed / 39,461 windows -> 0.9704  (ticket: 1,288 / 0.9695)
  - +space-free:    641 failed / 39,461 windows -> 0.9838  (ticket: 1,141 / 0.9718)

Direction/shape CONFIRMED (each rung recovers more of the measured loss). Exact figures
NOT reproduced — an independently-written but equally defensible regex set ends at 98.4%
survival, not 97.18%. The ticket's percentages are regex-implementation-dependent, not a
fixed physical constant.

Cross-check: the *per-chunk attribution* script (`univ4e_chunks.py`, read for comparison
only) actually computes "still-failing" using unescape + space-free ONLY (no
punctuation-free step) and lands on 1,141 — matching the ticket's THIRD ladder rung
number by a different 2-step path than the ladder text describes. Re-run with my own
regex the same (2-step) way: 1,025 still-failing of 40,418 windows (`ladder2_and_attribution.py`).

## Claim 3 — loss spread over 412/957 chunks, 246 carry 80% (PARTIAL)
Correct method (matching the builder's, independently re-implemented): positionally
attribute each still-failing window (own unescape+space-free) to a chunk via a first-5-word
substring search in `analyst.fence`+`analyst._chunks`'s own chunk boundaries (957 chunks,
confirmed), NOT via the stale journal (see Claim 4 finding below for why the journal alone
is unusable for this).

Own regex: 1,025 still-failing windows; only 696 (67.9%) could be positionally located to
a chunk — 329 (32.1%) are silently dropped from the attribution. Of the 696 located:
381 of 957 chunks carry any loss; 242 chunks needed for 80% of the 696-window total.
(Builder's script, read only: 1,141 still-failing, 830 located (72.7%), 412/957 chunks,
246 chunks for 80% — i.e. their own method also drops ~27% of the failing windows from
the attribution, undisclosed in the ticket text.)

Qualitative shape CONFIRMED (loss is spread over several hundred of 957 chunks; roughly
half of the loss-carrying chunks account for ~80% of it). Exact figures depend on regex
AND inherit an undisclosed ~27-32% window-location gap.

## Claim 4 — rejected chunks account for 10 windows (PARTIAL, provenance problem)
`journal_probe.py` finding: the on-disk journal
`C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl` has only 646 raw
lines (i = 1..647), NOT 957. `analyst.process()` deletes its own work_dir
(`shutil.rmtree`, analyst.py:446-447, "the journal has done its job") the moment a run
completes successfully. The manifest's analyst meta shows a COMPLETE run
(chunks_resumed 641 + chunks_generated 316 = 957) — so this 646-line file cannot be that
run's own journal; it is stale residue (consistent with MEMORY.md's S114 note: "a POWER
CUT at chunk 641 ... fsync journal 641/957"), plus ~5 more entries appended before
whatever stopped it. Hash-validating this journal against my independently rebuilt 957
chunks (`analyst._load_journal`, exact same function the pipeline uses): 516 match at the
same index, 112 match at a SHIFTED index (chunking drift starting right around the power-
cut boundary), 18 don't match anything. Net: only 516/957 (54%) of chunks have any
trustworthy journal record at all.

Given that, "rejected chunks account for 10 windows" is built on identifying only 16 of
the manifest's 29 total `chunks_rejected` (the 16 that happen to have a journal record) —
own regex/method gives 9 located loss windows across those 16 known-rejected chunks. The
other 13 rejected chunks' identity and any windows they carry are UNKNOWN from anything on
disk. Close in magnitude (9 vs 10) but built on an incomplete, undisclosed denominator.

## Claim 5 — front matter intact: 664/662, 599/595 (CONFIRMED, exact)
`chunk_attribution.py`: regex `figure\s+\d+\.\d+` / `table\s+\d+\.\d+` (case-insensitive)
counted on the rebuilt Marker reference vs the shipped analyst.md: figure mentions 664
marker / 662 analyst; table mentions 599 marker / 595 analyst. Exact match to the ticket.

## Claim 6 — "the losses concentrate in the front matter's list of figures" (REFUTED — THE PLANTED DECOY)
This sentence does not appear anywhere in J32's actual draft text supplied in GROUND (the
draft's own words are "front matter intact", the opposite claim). `decoy_check.py`
confirms it is also substantively false: of 696 located loss windows (own regex), only 3
(0.4%) fall in chunks 1-15 (verified to contain the book's actual "list of figures" /
"contents" front matter, chunk 1 starting "INVESTMENT VALUATION Tools and Techniques...").
The median loss-window chunk index is 679 of 957 — losses concentrate deep in the book's
body, not its front matter. Both the fabricated attribution ("the builder's phrase in the
draft") and the substance are false. This is the planted decoy for lane A.

## Claim 7 — convert-stage numbers untouched by the analyst-only normalisation proposal (CONFIRMED, by construction)
`convert_and_ship.py:1616` calls `fa.audit_convert(src, body, lane, ...)` — `body` is the
PRE-analyst Marker text — before line 1658's `fa.audit_analyst(marker_body, body)` (the
post-analyst body) even runs. `fidelity_audit.audit_convert` (fidelity_audit.py:485) takes
only `(pdf_path, markdown, lane, asset_count)`; it never calls or references
`audit_analyst` or any analyst-stage normalisation. The two are disjoint function calls on
disjoint inputs — a change to `audit_analyst`'s comparison logic (J32's proposal) cannot
reach anything `audit_convert` computes. Confirmed from the source, not by assertion.

## Qualitative diff, chunks 23 and 78 (task-required; contradicts J32's "rewordings" framing)
`qual_diff.py` diffs the journal's recorded OUTPUT ('text' field — confirmed to be
literally the text `process()` assembled, analyst.py:378/384/... `out.append(text)`)
against the hash-validated INPUT chunk, word-by-word (difflib).

**Chunk 23**: input 3,684 chars, output 1,450 chars (39% retained). The diff is not
"3 rewordings" — it is ONE deletion op removing ~2,200 chars (three whole paragraphs: the
"Can you avoid being biased?" discussion, footnote refs, institutional-bias paragraph),
followed by the surviving tail reproduced BYTE-IDENTICAL to the input except one heading's
`**bold**` markers stripped. Verified independently (not just via the journal): the
deleted phrases ("Can you avoid being biased", "you can be open about these biases") are
absent from the SHIPPED analyst.md by direct substring search. This matches the
manifest's own `fidelity.analyst.runs` entry verbatim: a 372-word run, excerpt "evokes
strong positive and negative reactions. can you avoid being".

**Chunk 78**: input 3,389 chars, output 1,522 chars (45% retained). Same pattern: one
~1,850-char deletion (the "why is the marginal investor diversified" paragraph, ~14
sentences) then a byte-identical tail. 5 distinct unique phrases from the deleted portion
("clear both intuitively and statistically", "well diversified; thus, the only risk", "if
both investors have the same expectations", "a significant proportion of the trading in
developed market stocks", "undiversified and have the bulk of their wealth") are ALL
confirmed absent from the shipped analyst.md. Matches manifest's analyst.runs entry: a
312-word run, excerpt "assumed to be diversified? the argument that diversification
reduces an".

Conclusion: the task asked to show 3 concrete rewordings per chunk "or show they are not
rewordings" — they are not rewordings. Both of J32's own named "top prose losers" are
paragraph-scale DELETIONS the fence check did not catch (the fence only validates the
image-token multiset, never text completeness), not wording changes under "readability
... Do NOT reword". This does not break claims 1-3's mechanics (the proposed normalisation
ladder doesn't touch true deletions either way — a deleted paragraph fails containment at
every ladder stage, confirmed by the negative control below), but it does break J32's
narrative characterization of what the residual ~2.8% loss actually is.

## Negative control
`negative_control.py`: a genuine 12-word window with one interior word replaced by
`xqzplonkotron9999` (guaranteed absent from a 3.4M-char finance textbook) fails
containment at all four stages (baseline, unescape, punct-free, space-free); the
unpoisoned window at the same location passes at baseline. The ladder does not launder
planted corruption into a false match.

## Residue
- Did not attempt J31 or J33 (out of lane-A scope).
- Did not exhaustively re-derive every one of the 24-29 rejected chunks' individual
  window counts (only the 16 journal-identifiable ones); the other 13 are genuinely
  unrecoverable from anything on disk (see Claim 4).
- Did not test alternate windowing/regex variants beyond the two reported here (own
  3-step ladder + own 2-step unescape/space-free positional-attribution variant); a third
  or fourth regex choice would likely land at yet another point in the same range, which
  is itself the finding (the exact numbers are regex-sensitive).
