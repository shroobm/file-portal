export const meta = {
  name: 'verify-tickets-j31-j33',
  description: 'Refute the measured solutions behind three proposed tickets (re-audit a repaired held bundle; analyst-gate normalisation; retain the Marker markdown) before they reach the register: 3 Sonnet refuter lanes + 1 Fable verifier',
  phases: [{ title: 'Refute' }, { title: 'Verify' }],
}
const REPO = 'C:/Users/Bndit/Projects/file-portal'
const SP = 'C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad'
const OUT = SP + '/verify-tickets'

const GROUND = `
GROUND (docs/47). You are one lane of an adversarial verification fleet for Rab's local PDF->markdown pipeline
("File Portal", ${REPO}, branch feat/library-pipeline at 11c9af1). Rab's order tonight: "If there is something you
find development worth, make it a ticket, find the solution for the ticket before you propose it." The builder
(Fable) measured three solutions on the held book "Investment Valuation, University Edition" (held bundle
C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e — verdict fail; manifest fidelity.convert.doc_survival 0.9334,
fidelity.analyst.doc_survival 0.9402 with runs_total 404; analyst program "readability", model qwen3:8b) and drafted
three tickets. Your job is to BREAK the measurements and the ticket wording. A claim you could not break after a
real attempt is CONFIRMED; broken is REFUTED; partly, PARTIAL.

HARD RULES
- READ-ONLY on ${REPO} and on C:/Users/Bndit/ml/library (never write, stage, commit, push there; never run the
  converter, the widget, marker, or ollama; no GPU). Write ONLY under ${OUT}/<lane>/ (create it).
- Interpreters: NEVER bare 'python' (Store stub). C:/Users/Bndit/ml/marker-env/Scripts/python.exe for anything importing
  fidelity_audit or analyst (pymupdf, rapidfuzz); C:/Users/Bndit/.local/bin/python3.12.exe otherwise. Paths go in
  FILES with forward slashes, never in python -c. PYTHONIOENCODING=utf-8. Absolute paths always (Bash cwd persists).
- Tag every claim Observed / Verified / Inferred / Unknown / UNREAD. A failed probe is never a negative observation.
  Every number names numerator, denominator, conditions. Run a NEGATIVE CONTROL and name it. Declare residue.
- PLANTED DECOY: exactly one statement in your lane's section below is FALSE on purpose. Find it by measurement,
  name it in decoy_report, do not propagate it.

MATERIALS (read-only): the rebuilt Marker (pre-analyst) reference = the converter's own slice cache
C:/Users/Bndit/ml/library/.chunk-work/14c66834bdfeaa2e/slice-*/slice.md (7 files; the converter joins them with
"\\n\\n" — convert_and_ship.py:1456), copied to ${SP}/univ4e-marker/. The builder's scripts and JSON:
${SP}/univ4e_classify.py (+.json), univ4e_classify2.py (+.json), univ4e_chunks.py (+.json), univ4e_repair_sandbox.py
and the sandbox copy ${SP}/univ4e-sandbox/ (repaired md + fidelity.reaudit.json). Do not trust them; re-derive.
Key code: ${REPO}/windows-converter/fidelity_audit.py (audit_analyst = EXACT substring containment of 12-word
windows of prepare_output(marker) in prepare_output(analyst); compute_verdict; audit_convert),
${REPO}/windows-converter/analyst.py (fence/_chunks/_chunk_hash/_load_journal; prompts/readability.txt),
${REPO}/windows-converter/convert_and_ship.py (ship(), the slice merge ~1259-1456, the CHUNK_WORK sweep ~1275),
${REPO}/linux-converter/converter/exporter.py (the supersede guard + bless marker ~215-345, SHIP_BLOCKS_TO_VAULT),
${REPO}/windows-widget/src-tauri/src/assay.rs (bless ~332-425: eligibility is read from the EVENT STREAM),
${REPO}/prototypes/repair-bench/bench.py, docs/15-survival-audit.md §12, docs/18 §5.4, docs/19.

THE THREE DRAFT TICKETS (verify the wording against what you measure):
J31 — RE-AUDIT A REPAIRED HELD BUNDLE. Mechanism: a converter entry "--reaudit <held sha16>": (1) read the held md +
manifest; (2) audit_convert(source pdf, md, lane) -> new convert block (builder measured 48 s on this book, 1372
pages scored); (3) keep fidelity.analyst as measured at run time (historical: the analyst ran on the pre-repair
text); fold provenance fidelity.reaudit {ts, by, reason, repairs ledger digest, from: old convert numbers + verdict};
(4) verdict = compute_verdict(new convert, old analyst); (5) emit audit/scored with stage "reaudit" so the widget's
bless eligibility (event stream) sees the new verdict; (6) re-ship via the existing ship() so the exporter's startup
sweep sees the new manifest; exporter unchanged. Measured: replacing the line-8776 math-OCR runaway with the printed
derivation -> degeneration 1 -> 0 blocks, convert stage alone 'flag' (doc_survival 0.9271, 257 pages flagged,
runs_total 570), overall verdict still 'fail' on the analyst block. Policy slot for Rab: may a human repair change
the convert-stage verdict.
J32 — THE ANALYST-STAGE GATE COUNTS ESCAPES AS REWRITES. Measured against the rebuilt reference: 2,420 of 40,438
windows fail as shipped (0.9402, 404 runs — reproduces the manifest exactly); unescaping Marker's backslash escapes
that qwen drops -> 1,763 failed (0.9564); + punctuation-free -> 1,288 (0.9695); + space-free -> 1,141 (0.9718,
120 runs, max run 588 words). The remaining ~2.8 % are real rewordings by qwen3:8b under readability ("Do NOT
reword"), spread over 412 of 957 chunks (246 chunks carry 80 %; rejected chunks account for 10 windows; front matter
intact: 'figure N.N' mentions 664 marker / 662 held, 'table N.N' 599 / 595). Proposal (mechanical, analyst stage only,
convert stage byte-identical): audit_analyst compares after unescape + punctuation-free + space-free on both sides and
names the normalisation in the block. Gate change -> Rab's signature. Denominator: ONE book, because only one Marker
reference exists on disk.
J33 — RETAIN THE MARKER MARKDOWN WITH THE BUNDLE. Today the pre-analyst text lives only in the slice cache
(LATEST-BOOK retention: swept when the next book starts chunking). Proposal: the converter writes the merged Marker
text beside the bundle md as <name>.marker.md into held/anchor and the shipped tar; the exporter keeps it OUT of the
vault (blocks.json precedent, SHIP_BLOCKS_TO_VAULT); the bench reads it as a reference pane. Cost +3.5 MB per book
on disk, 0 in the vault.
`
const LANE_SCHEMA = { type: 'object', properties: {
  lane: { type: 'string' }, report_file: { type: 'string' },
  claims: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'PARTIAL', 'UNREAD'] }, evidence: { type: 'string' }, tag: { type: 'string' } }, required: ['claim', 'verdict', 'evidence', 'tag'] } },
  measurements: { type: 'array', items: { type: 'string' } }, negative_control: { type: 'string' },
  defects: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['BLOCKER', 'MAJOR', 'MINOR', 'NOTE'] }, where: { type: 'string' }, what: { type: 'string' }, evidence: { type: 'string' }, remedy: { type: 'string' } }, required: ['severity', 'where', 'what', 'evidence', 'remedy'] } },
  ticket_wording_fixes: { type: 'array', items: { type: 'string' } },
  decoy_report: { type: 'string' }, residue: { type: 'string' } },
  required: ['lane', 'report_file', 'claims', 'measurements', 'negative_control', 'defects', 'ticket_wording_fixes', 'decoy_report', 'residue'] }

const LANES = [
  { key: 'A', label: 'refute:analyst-numbers', prompt: `${GROUND}
YOUR LANE: A — THE ANALYST-STAGE NUMBERS (J32's evidence).
Re-derive independently (your own script under ${OUT}/A/, not the builder's): rebuild the reference from the 7
slice.md files; mirror fidelity_audit.audit_analyst; you must land on 0.9402 and 404 runs or say why not. Then the
normalisation ladder (unescape; +punctuation-free; +space-free) with your own regexes — report each doc_survival,
failed count, runs, max run. Then the per-chunk attribution with analyst.fence + analyst._chunks (957 chunks) and
analyst._load_journal on C:/Users/Bndit/ml/library/.analyst-work/*/chunks.jsonl. Then the QUALITATIVE proof the
builder did not do: for chunks 23 and 78 (top prose losers), take the journal's output text for that chunk (the
journal 'text' field is the OUTPUT the run assembled) and diff it against the input chunk word by word — show 3
concrete rewordings each, or show they are not rewordings. Claims to break: (1) the mirror reproduces 0.9402 / 404;
(2) the ladder is 0.9564 / 0.9695 / 0.9718 with 1,763 / 1,288 / 1,141 failed; (3) the residual loss is spread over
412 of 957 chunks, 246 carry 80 %; (4) rejected chunks account for 10 windows; (5) the front matter (lists of
figures/tables) is intact — mentions 664/662 and 599/595; (6) the losses concentrate in the front matter's list of
figures (the builder's phrase in the draft); (7) the convert-stage numbers are untouched by the proposed analyst-only
normalisation — prove by construction from the code, not by assertion. Negative control: a window you plant that
the model certainly changed must fail every ladder step.` },
  { key: 'B', label: 'refute:reaudit-path', prompt: `${GROUND}
YOUR LANE: B — THE RE-AUDIT PATH (J31's mechanism).
Make your OWN sandbox copy of the held bundle under ${OUT}/B/ (copy the md + manifest, not assets), remove the
line-8776 runaway your own way (the bench's collapse gesture equivalent: delete the degenerate paragraph, or
transcribe), and re-run fidelity_audit.audit_convert(source pdf from C:/Users/Bndit/ml/library/drop/done/<manifest.source>,
repaired md, manifest lane) and compute_verdict with the manifest's analyst block. Claims to break: (1) degeneration
goes 1 -> 0 and the convert stage alone verdicts 'flag' (0.9271 ± drift, 257 flagged pages, runs_total 570); (2) the
overall verdict stays 'fail' because of the analyst block; (3) the exporter re-runs the audit on arrival, so a
re-shipped manifest would be re-scored on the ThinkPad anyway; (4) the widget's bless click reads eligibility from the
EVENT STREAM (assay.rs) — name exactly which event fields it reads and whether an 'audit/scored' with a new verdict is
sufficient, and whether the exporter's supersede guard reads only manifest verdict + bless.json + source sha;
(5) ship() can re-ship an existing bundle directory unchanged — read its signature and callers (convert_and_ship.py
~1688 and :1824) and say what a --reaudit entry must pass it; (6) keeping fidelity.analyst historical is the honest
choice — argue the alternative (re-running audit_analyst against the Marker reference with the same repair applied)
and measure it if the reference is at hand (${SP}/univ4e-marker). Negative control: the UNREPAIRED held md through
the same audit_convert must still trip degeneration.` },
  { key: 'C', label: 'refute:retain-marker', prompt: `${GROUND}
YOUR LANE: C — RETAINING THE MARKER MARKDOWN (J33) and the asset-name defect.
Claims to break: (1) the pre-analyst Marker text exists nowhere in the pipeline's outputs except the slice cache —
check held/, anchor/, pending/, the analyst journal (its 'text' is OUTPUT), the ThinkPad-bound tar (ship()), the
vault export shape; (2) the slice cache is swept when a DIFFERENT book starts chunking (convert_and_ship.py ~1275)
— quote the lines; (3) the exporter already ignores any *.marker.md file (builder's claim); (4) the cost is +3.5 MB
per book on disk — measure the 7 slice.md bytes and the merged size; (5) the merge is a plain "\\n\\n".join of
slice.md files and asset files are copied by name unchanged (~1456 and the copy2 loop) — yet the held md references
assets up to _page_2553_ while the book has 1,377 pages and span anchors stop at page-1205: FIND THE MECHANISM. Compare
each slice dir's asset filenames with its page range (slice-00000-00199 etc.) and the span ids inside its slice.md;
say whether the _page_N_ numbers are absolute, slice-relative, or something else, and whether any consumer (bench,
exporter, widget, analyst fence) derives a page from an asset name; (6) what the bench would need to show a reference
pane (bench.py reads which files; is a second md a one-line change or a design change); (7) the blocks.json precedent
in exporter.py (SHIP_BLOCKS_TO_VAULT, manifest blocks {present_in_bundle, shipped, bytes}) is the right shape for
marker_md — quote it. Negative control: a file you know the exporter DOES ship must show up in its ship list.` },
]

phase('Refute')
const lanes = (await parallel(LANES.map(l => () => agent(l.prompt, { label: l.label, phase: 'Refute', schema: LANE_SCHEMA, model: 'sonnet', effort: 'high' })))).filter(Boolean)
log(`refute lanes done: ${lanes.length}/3 — defects: ${lanes.map(l => l.lane.slice(0, 1) + ':' + l.defects.length).join(' ')}`)

const VERIFY_SCHEMA = { type: 'object', properties: {
  claims_checked: { type: 'array', items: { type: 'object', properties: { lane: { type: 'string' }, claim: { type: 'string' }, verdict: { type: 'string', enum: ['CONFIRMED', 'WRONG', 'OVERSTATED', 'UNREAD'] }, checked_against: { type: 'string' } }, required: ['lane', 'claim', 'verdict', 'checked_against'] } },
  measurements_rerun: { type: 'array', items: { type: 'string' } },
  defects_adjudicated: { type: 'array', items: { type: 'object', properties: { from_lane: { type: 'string' }, severity: { type: 'string', enum: ['BLOCKER', 'MAJOR', 'MINOR', 'NOTE', 'DISMISSED'] }, what: { type: 'string' }, remedy: { type: 'string' } }, required: ['from_lane', 'severity', 'what', 'remedy'] } },
  ticket_verdicts: { type: 'array', items: { type: 'object', properties: { ticket: { type: 'string' }, verdict: { type: 'string', enum: ['PROPOSE', 'PROPOSE_AMENDED', 'DO_NOT_PROPOSE'] }, amended_wording: { type: 'string' }, why: { type: 'string' } }, required: ['ticket', 'verdict', 'amended_wording', 'why'] } },
  decoys_caught: { type: 'string' }, report_file: { type: 'string' }, residue: { type: 'string' } },
  required: ['claims_checked', 'measurements_rerun', 'defects_adjudicated', 'ticket_verdicts', 'decoys_caught', 'report_file', 'residue'] }

phase('Verify')
const verify = await agent(`${GROUND}
YOUR ROLE: THE VERIFIER (last lane; the session model). Three Sonnet refuter lanes have reported (below). Trust none
of them: re-run at least two decisive probes per lane yourself (say which), adjudicate every defect, and for each of
the three draft tickets rule PROPOSE / PROPOSE_AMENDED / DO_NOT_PROPOSE with the exact amended wording Rab should read
(numbers with numerator, denominator, conditions; tags; the policy slot named). Each lane's GROUND carried one planted
false statement (A: "the losses concentrate in the front matter's list of figures"; B: "the exporter re-runs the audit
on arrival"; C: "the exporter already ignores any *.marker.md"); say which lanes caught theirs and whether any lane
propagated one. Write ${OUT}/VERIFIED.md. READ-ONLY on the repo and the library; no GPU.

LANE OUTPUTS:
${JSON.stringify(lanes, null, 1)}
`, { label: 'verify:fable', phase: 'Verify', schema: VERIFY_SCHEMA, effort: 'max' })
log(`verifier: ${verify ? verify.ticket_verdicts.map(t => t.ticket.slice(0, 3) + '=' + t.verdict).join(' ') : 'NULL'}`)
return { lanes, verify }