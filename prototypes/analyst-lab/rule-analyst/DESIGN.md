# `analyst-lab/rule-analyst` — does the analyst's stated job need an LLM?

**Category** `analyst-lab` · **Name** `rule-analyst` · **Status** prototype, quarantined
(prototypes/README.md: nothing in the pipeline imports, spawns or reads it) · **Born** S119
(2026-09-09), Fable lane R2 of Rab's three-sources commission, source (2) *"the model is a
sampler, not a copier"*.

## What it is

`prompts/readability.txt` gives qwen3:8b four instructions: fix mid-word hyphenation splits
(`'unexpect edly' -> 'unexpectedly'`), normalize heading levels, keep paragraphs intact, keep
the `⟦IMG-n⟧` placeholders. `rule_analyst.py` does the first two **by rule** and leaves every
other byte alone, then measures itself — and the LLM — on the real DDIA 2e pairs from the held
bundle `fc1f068c3a8eeb63` (J33's sidecar `<name>.marker.txt` = the analyst's input; the shipped
`.md` = qwen3:8b's output, aligned per chunk by `../decoding/ddia_pairs.py`, whose alignment is
proven by re-deriving the manifest's per-chunk `s` to 4 dp on 450 passed chunks).

Rules:

| Rule | Shape | Guard |
|---|---|---|
| R-HYPHEN | `(\w)-\n(\w)` → `\1\2` | none needed — Marker's hard line-break hyphen |
| R-SPLIT | `a b` → `ab` | only if `ab` is in the document's own vocabulary (≥ 3 occurrences) **and** at least one of `a`, `b` is not — the self-dictionary keeps `data base` two words |
| R-HEADING | *measured, not applied* | what the LLM's "heading normalisation" was in practice is counted, not imitated |

## What was measured (`Observed`, `python rule_analyst.py`, 2026-09-09; interpreter
`marker-env`; all numbers over the 492 chunks rebuilt by `analyst.fence` + `analyst._chunks`
from the sidecar, the same code the pipeline runs)

- **The input contains 0 hard hyphenation splits** (`\w-\n\w`) and 4 `\w- \w`; R-SPLIT finds
  **0** candidates. The program's headline job has nothing to do on this book — Marker already
  joined them. (Negative control: `--selftest` plants `unexpect edly` and `data-\nbase` into
  DDIA prose; both detectors fire, the `data base` guard holds, and the repaired text scores
  survival 1.0 under the shipped ladder.)
- **Rule-based output: 0 chunks changed; per-chunk survival min 1.0, mean 1.0000 over 492;
  document `fidelity_audit.audit_analyst` = 1.0 / 0 runs** (the real gate function, sidecar vs
  rule-based body). The LLM's shipped body on the same function: 0.9718 / 49 (= the manifest).
- **The LLM, on 451 aligned passed chunks:** hyphen joins performed 0 of 0 possible; space-split
  joins 0 of 0; headings 712 in → 749 out, **level changed 0**, heading text removed 348 / added
  383 (it rewrites heading lines — mostly Marker's `<span id="page-N-K">` anchors and bold
  markers — it does not re-level them); **426 of 451 outputs differ from the rule-based output
  beyond whitespace.** Every one of those differences is outside the stated job.

## What it cannot do that the LLM did

Nothing the program asked for. What the LLM did *beyond* the ask — stripping page anchors,
unescaping `\_`, repairing ligatures, re-punctuating, rewording, deleting — is either
cosmetic (the anchors, the escapes: a rule could do those too if anyone signs them) or damage.
A rule cannot exercise "heading judgement", and on this book the LLM exercised none either
(0 level changes). List reflow was not asked for and is not measured here.

## Decisions

- Self-dictionary instead of an external wordlist: none is on the machine; the document's own
  vocabulary at ≥ 3 is a conservative guard that fires 0 times on DDIA and 1/1 on the plant.
- Byte-identity everywhere else: the point of the prototype is the survival-by-construction
  property; adding "helpful" rules would put it back in the LLM's failure class.
- Not wired to the pipeline. Graduation is a separate decision (Rab's): the finding is that the
  analyst stage's *stated* job is a ~40-line function, and the 3 % loss is entirely the cost of
  asking a language model to retype a book.

## Files

`rule_analyst.py` (the rules, the measurement, `--selftest`), `results.json` (numbers only,
no book text). Depends on `../decoding/ddia_pairs.py` for the pairs.
