# GLM-OCR probe — S84

**Quarantined prototype** (disposable, zero pipeline coupling). Commissioned by Rab, S84:
*"the word, S84 is the GLM OCR probe."*

## What ran

`llama-server -hf ggml-org/GLM-OCR-GGUF` (Q8_0 950 MB + mmproj 484 MB, authorized download) on
the existing llama.cpp **b10448** install, port 7130, temperature 0.1 / top-k 1 per ggml-org OCR
guidance. **b10448 loads and serves the model** — the probe's first question, answered `Observed`.

Three pages of the held Beer (*Diagnosing the System*, scan lane, verdict `fail`, 18 omission
runs), rendered at 180 dpi from the `Verified` source PDF (`drop/done/…BEER.pdf`, sha256 =
the bundle key `b7b711d4…`):

- **p77** — the worst omission run (96 words the pipeline dropped)
- **p33** — an omission run whose garble reads like a figure/table (`r/auk£ 2, to^l industry`)
- **p50** — control, no recorded damage

Per-page cost (`Observed`, n=3, this card, b10448, Q8_0): prefill 4,052 tok ≈ 1.4–1.7 s, decode
212–379 tok at ~320–331 tok/s, **wall 2.5–2.9 s/page**. n=3 is `Inferred` about everything.

## What came back — checked against the bundle markdown, string by string

| page | finding |
|---|---|
| **p77** | **GLM recovered content the bundle does not contain**: "85% of public could not identify brand", "briefing of salesmen", "airport questionnaire" — all ABSENT from the bundle; the page's *typeset* line ("analytic vignettes of the transducers") IS in the bundle. Consistent reading: Marker captured the print and dropped the handwritten figure annotations; GLM read both. |
| **p33** | GLM's typeset content is all already IN the bundle — Marker handled this page's prose. The omission run here was the hand-drawn diagram itself; whether GLM's transcription faithfully covers the diagram labels is a judgment call against the PNG. |
| **p50** | 2 of 3 sampled GLM sentences match the bundle verbatim; one absent — either a GLM misread, a paraphrase, or a Marker miss. Adjudicate against the PNG. |

## What this does NOT establish

GLM's p77 text *reads* coherent. Whether it matches the page's actual handwriting is **the
human's call with the PNG beside it** — a coherent-looking hallucination is precisely the risk a
0.9B model carries, and the doctrine stands: the human is the vision authority. The vendor's
94.62 OmniDocBench stays `Historical`. Three pages promote nothing (docs/21 rule 2).

## The two decisions this feeds (both Rab's, neither taken here)

1. **Bench second-reader** — GLM drafts proposals for wreck-site zones; Rab accepts/rejects at
   the bench. p77 is the existence proof that recovery is sometimes possible at ~3 s/page.
2. **Scan-lane challenger** — a slot in the convert engine policy table, gated by the Survival
   Audit A-B against Marker on whole books. Bigger surgery; needs its own design.

Files: `beer-pNNN.png` (what the model saw; untracked — re-render from the source PDF at 180 dpi,
command above) · `glm-pNNN.md` (what it wrote; tracked — the probe's evidence).

## Verdicts (S84 close)

**Rab's eyes, pages 77, 76 and 114: "the handwriting checks out" / "checks out."** Three of three
adjudicated omission runs recovered faithfully — the existence proof is **signed**, not inferred.
The signature pattern across all five pages: Marker's scan lane kept the typeset print and
dropped Beer's handwritten figure content; GLM read both. The audit garble `r system three v`
resolved to "System Three*, V — 'management audit'".

**Flags accepted as flags**, not resolved: p76 "Mammal corporation" (Mammoth?) and "placards it
workers' demonstration" (at?) — the smoothing class the bench's accept/reject step exists for.

**Still untested, stated so it cannot be quietly assumed:** the SYM-003 **table-loop** hypothesis
— none of the five pages exercised a degeneration zone, only omission runs. Whole-book behaviour,
hallucination rate at scale, and clean-lane books likewise unprobed. Five pages promote nothing
beyond themselves (docs/21 rule 2).
