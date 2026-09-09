# `prototypes/` — the quarantine section

Experimental builds and design explorations that are **deliberately quarantined from the
pipeline**: nothing in here is imported, spawned, watched, shipped, or run by the live
system (widget, converter, exporter, watcher). CI does not touch it. It is safe to keep,
safe to ignore, and safe to delete.

**Why it exists.** Rab asked (2026-07-21) for a place to record development explorations
"passively — so if someone wants it they can have it in the quarantined section," each
given a **category** and a **name**, without any risk to the production pipeline. This is
that place. A prototype graduates into the real system only by an explicit, separate
decision — never by living here.

## Layout

```
prototypes/
  <category>/
    <name>/
      <files…>        # the prototype itself (self-contained where possible)
      DESIGN.md       # what it is, the research/references behind it, the decisions
```

## Index

| Category | Name | What it is | Status |
|---|---|---|---|
| `control-panel` | `opsroom` | A professional control-panel / dashboard representation of the pipeline — pipeline segmentation, a live transit viewer, the Survival Audit, live numbers and progress bars. Self-contained `opsroom.html`; opens in any browser; zero dependencies. Design lineage: Project Cybersyn's Operations Room (Beer + Bonsiepe) × the Claude Design System × modern observability practice. | Prototype — awaiting Rab's verdict |
| `repair-bench` | *(itself)* | **Stage G (docs/19 §7): "the human IS the vision model."** Source-PDF page ⇄ markdown side-by-side, navigated by the audit's flagged zones; drag-crop or paste a screenshot → `assets/_repair_pN_k.png` embedded `![[…]]` at the zone with `manifest["repairs"]` provenance; re-score is a preview only. `bench.py` (stdlib + pymupdf) + `bench.html` + `acceptance.py`; `README.md` is its design record. **Deviation from the mocked-data rule, by signed design:** it operates on real held bundles when a human runs it (`--sandbox` for trials) — the quarantine here means the pipeline never depends on or triggers it. | Prototype — 26/26 acceptance on a sandbox of the real Valentine; awaiting Rab's first real repair (graduation criteria: docs/19 §7) |
| `analyst-lab` | `edit-whitelist` | **S119 R1 (2026-09-09): the diff-whitelist ACCEPTOR** — word-level opcodes between the analyst input and its candidate; accept only edits that normalise equal under a stated whitelist (escapes, link re-syntax, markup, hyphen joins, ligature repairs, reflow), revert everything else; plus `classify.py`, which attributes every failed 12-word window of the real audit to an edit class. Measured on the real 492 DDIA pairs with the real `fidelity_audit.audit_analyst`: shipped 0.9718/49 → FULL whitelist 0.9817/24 (0.9968/1 under ladder v3c), STRICT 0.9998/0; controls accept-all = shipped byte-for-byte, accept-none = the sidecar. Candidate for `analyst.process` (OPEN-TASKS J46) — the whitelist is a policy Rab signs. | quarantined; measured |
| `analyst-lab` | `reference-repair` | **S119 R1: where Marker's reference damage is born** — pdfium's char→Unicode fallback maps the PDF's OpenType-named ligature glyphs (f_i, f_f, f_l, T_h, f_t) to punctuation codes when ToUnicode is silent (MuPDF resolves them to U+FB01…); the `!` hyphen is the PDF's own ToUnicode; a vocabulary-gated repair of the Marker body (ligatures, hyphens, split links) with its per-rule audit effect, and a measured one-sided-normalisation trap (a cite rule on one side only makes the audit WORSE, 0.9234). Candidate for an upstream pdftext fix or a pre-analyst repair (J48). | quarantined; measured |
| `analyst-lab` | `decoding` | **S119 R2: the model as a sampler** — the shipped local request sends NO temperature (qwen3:8b's Modelfile 0.6 / top_p 0.95 / top_k 20 applies); one gated GPU experiment under the watcher's chat-hold (40 hardest DDIA chunks, shipped vs greedy+seed, ≤90 generations): byte-identical 28/40, same survival 36/40, greedy repeats 5/5, 7 of 12 paragraph deletions reproduce to the digit — the model deletes on purpose; the draw is ≤0.3 pp. Plus the lost-window decomposition on 451 aligned pairs (62.4 % the audit's: cite anchors 29.8, ligatures 18.4, escapes 14.2; 37.6 % the model's) and the document audit under ladders v2/v3/v3b/v3c (0.9718 → 0.9897/20). J49 (pin the sampler and record it). | quarantined; measured |
| `analyst-lab` | `rule-analyst` | **S119 R2: does the stated job need an LLM?** The program asks for four things (hyphen joins, heading levels, paragraphs intact, image tokens intact). A ~40-line rule pass does them byte-identically elsewhere and scores 1.0/0 runs on the real gate; on DDIA the input has 0 hyphenation splits and the LLM performed 0 joins and 0 level changes yet changed 426 of 451 chunks (removed 348 headings, added 383). Whether the analyst's purpose is the stated job or the unstated "make it readable" is Rab's (J47). | quarantined; measured |

## Rules

- **No pipeline coupling.** A prototype must not read, write, or trigger anything the live
  system depends on. Static/self-contained or clearly-mocked data only.
- **Category + name.** Every prototype lives under `prototypes/<category>/<name>/`.
- **Document it.** Each carries a `DESIGN.md` — what it is, the references, the decisions —
  so it stands on its own if revisited later.
- **Disposable by default.** If it's rejected, it stays here as a record or is deleted; it
  never leaks into the pipeline.
