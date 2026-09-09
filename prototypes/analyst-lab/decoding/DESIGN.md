# `analyst-lab/decoding` — is the analyst's loss the sampler, or the model?

**Category** `analyst-lab` · **Name** `decoding` · **Status** prototype, quarantined
(prototypes/README.md: nothing in the pipeline imports, spawns or reads it) · **Born** S119
(2026-09-09), Fable lane R2 of Rab's three-sources commission — source (2) *"the model is a
sampler, not a copier"*. Sibling: `../rule-analyst/`.

## What it is

Four read-only tools over the held DDIA 2e bundle `fc1f068c3a8eeb63` (J33's sidecar = the
analyst's input; the shipped `.md` = qwen3:8b's output; `manifest.analyst.chunk_scores` = J41's
per-chunk survival) and ONE bounded GPU experiment:

| File | What it does |
|---|---|
| `ddia_pairs.py` | rebuilds the 492 chunks with the pipeline's own `analyst.fence` + `analyst._chunks`, checks the sidecar's sha256 against `manifest.marker_body`, aligns each chunk's shipped output, and PROVES the alignment by re-deriving the manifest's `s` to 4 dp (450 passed chunks match; 24 chunks unaligned and excluded, named in its output) |
| `edit_taxonomy.py` | over the 451 aligned passed pairs: what the model changed (edit census) and WHY each lost 12-word window was lost (escape / ligature / citation anchor / reword / partial / deletion), plus a clean numeral census |
| `decoding_experiment.py` | the GPU experiment under the mandatory hold protocol (below) |
| `analyze_results.py` | the per-setting table, a-vs-b identity, determinism, manifest-vs-today |

Book text never enters this directory: `results.json`, `taxonomy.json`, `analysis.json` carry
numbers only; the generations live in `$TEMP/r2/gen_results.jsonl`.

## The shipped request, read from the code (`Verified`, two shapes)

`analyst._generate` sends `{"model": "qwen3:8b", "stream": false, "keep_alive": "30m",
"prompt": ..., "options": {"num_ctx": 8192}, "think": false}` — **no temperature, no seed**
(`windows-converter/analyst.py`, the body literal). What fills the gap is the model's baked
Modelfile: `ollama show qwen3:8b` → `temperature 0.6 · top_p 0.95 · top_k 20 · repeat_penalty
1` (Observed 2026-09-09, ollama 0.33.2). So the analyst has been sampling at **0.6**, the
Qwen team's *thinking-mode* recommendation, on a `think: false` copy-edit task. The brief's
GROUND line G1 ("temperature 0.2 pinned") is refuted by both shapes. The Gemini backend does
pin `generationConfig.temperature 0.2` (G2 confirmed) — the two backends are not the same
sampler.

## Research (each claim `Inferred` from the cited page until reproduced here; dates = read date)

- **ollama `/api/generate`** — `docs/api.md` (github.com/ollama/ollama, read 2026-09-09):
  options include `temperature`, `seed`, `top_k`, `top_p`, `repeat_penalty`, `num_ctx`;
  *"For reproducible outputs, set `seed` to a number"*; `think` is *"should the model think
  before responding"* (bool or level); `keep_alive` default `5m`, and *"an empty prompt … with
  `keep_alive` set to 0"* unloads; `system` *"overrides what is defined in the Modelfile"*.
- **Qwen3 best practices** — huggingface.co/Qwen/Qwen3-8B (read 2026-09-09): thinking mode
  *"Temperature=0.6, TopP=0.95, TopK=20, and MinP=0. DO NOT use greedy decoding"*;
  non-thinking mode *"Temperature=0.7, TopP=0.8, TopK=20, and MinP=0"*. The greedy warning is
  about reasoning collapse / endless repetition, not about copy fidelity; the repetition risk is
  exactly what J34's inflation guard already fences.
- **Determinism** — ollama issue #5321 (github, 2024-06-27, read 2026-09-09): with seed +
  temperature 0 *"the output from the first execution will be random"* and later runs
  consistent; the broader literature (e.g. mbrenndoerfer.com "Why Temperature=0 Doesn't
  Guarantee Determinism", read 2026-09-09) attributes residual variance to batching and
  floating-point kernel order. Measured here: see determinism rows below.
- **Verbatim copy fidelity** — arXiv 2601.03640 (Haque et al., 2026-01-07, read 2026-09-09):
  transcription errors *"can remain silent while producing syntactically valid programs"*
  under exact-string scoring. Minimal-edit GEC (arXiv 2506.13148, read 2026-09-09): LLMs
  *"produce more fluency-oriented rewrites instead"* of minimal edits — the over-editing
  tendency is a training property, not a sampling one. arXiv 2609.04061 (minimal code edits):
  *"a preservation instruction substantially reduces this behavior"* — the basis for setting (c).
- **Model alternatives that fit a 10 GB card** — ollama.com/library tags (read 2026-09-09):
  `qwen3:14b` 9.3 GB · `gemma3:12b-it-q4_K_M` 8.1 GB · `phi4:14b` 9.1 GB (IFEval ≈63 per
  bestllmfor.com's review, read 2026-09-09 — weak instruction following) · `mistral-nemo:12b`
  q4_0 7.1 GB / q4_K_M 7.5 GB · `qwen3:8b` 5.2 GB. Measured residency here: the 5.2 GB
  qwen3:8b file became a **6,295 MB** resident model and the card went 1,633 → 7,987 MiB at
  `num_ctx 8192` (+6,354 MiB). Scaling that overhead (×1.21), a 9.3 GB 14B would need ≈11 GB —
  it does not fit a 10,240 MiB card that the desktop already holds 1.6 GB of; a 12B at 7.1–8.1
  GB is marginal (≈8.6–9.8 GB). Falsifier: pull one and read `ollama ps`'s PROCESSOR column
  (100 % GPU vs a CPU/GPU split). No model was pulled (multi-GB downloads are out of scope).
  No public benchmark found that scores "copy-edit without rewording" on local models;
  ErrataBench (revise.io, updated 2026-08-26) scores proofreading *fix rates*, the opposite
  objective.

## The GPU protocol (as run)

(i) `.gpu-lock` and `chat-hold.json` both absent before any call, else UNREAD; (ii)
`chat-hold.json` written in `room_chat._hold_write`'s exact schema by the SAME process that
made the calls (`held_by research-R2`, its own pid, `port 0`, `model "qwen3:8b research"`,
`since`, `_why`) — the watcher's `chat_hold()` defers every convert while that pid lives and
reaps it when it dies; (iii) `finally:` unlink the hold + POST `keep_alive 0`; (iv) sequential
generations, never concurrent; (v) abort if `.gpu-lock` appears; (vi) nvidia-smi before /
during / after. Sample: the 20 lowest-survival passed chunks + the 12 survival-rejected + 8
random passed (`random.Random(7)`), 40 chunks × settings (a) shipped and (b) greedy
(temperature 0, seed 7), + (b) repeated on 5 + (c) greedy with a strict `system` line on 5 =
90 generations, the cap.

## Measured (`Observed` 2026-09-09 14:14–14:42 EDT, pid 11044, 90/90 generations, wall 1,669 s,
no abort; card 1,633 → 7,987 (during) → 1,661 MiB (after); `ollama ps` empty after the unload)

**Per setting** (survival = `text_norm.chunk_survival(input, output)`; numerals = content
digit-tokens of the input absent from the output, span anchors / `⟦IMG⟧` / link targets excluded):

| setting | n | mean s | median s | s < 0.80 | s = 1.0 | numeral-changed chunks / tokens | fence fail | think leak | s/chunk |
|---|---|---|---|---|---|---|---|---|---|
| (a) shipped request (baked T 0.6) | 40 | 0.8153 | 0.835 | 8 | 6 | 8 / 42 | 0 | 0 | 18.9 |
| (b) temperature 0, seed 7 | 40 | 0.8186 | 0.8367 | 8 | 7 | 10 / 46 | 0 | 0 | 18.2 |
| (b2) = (b) repeated | 5 | 0.8142 | 0.8163 | 1 | 0 | 0 / 0 | 0 | 0 | 17.1 |
| (c) (b) + strict `system` | 5 | 0.8298 | 0.8222 | 0 | 0 | 0 / 0 | 0 | 0 | 18.0 |

The sample is the 40 HARDEST chunks by construction (20 lowest passed + 12 rejected + 8
random), so the means are not the book's; the comparisons between columns are the result.

- **(a) vs (b), same chunk:** byte-identical output **28 of 40**; identical survival 36 of 40;
  mean Δ(b−a) **+0.0034**; b better on 2, worse on 2. Greedy decoding is not a different
  analyst: on a copy-edit prompt the 0.6-temperature distribution is already peaked enough
  that sampling reproduces the argmax 70 % of the time, chunk for chunk.
- **Determinism of (b):** 5 of 5 repeats byte-identical (the ollama #5321 "first run differs"
  shape did not appear; residency was warm from (a)).
- **The production run vs today's (a)** (same request shape, 28 passed chunks in the sample):
  identical survival **23 of 28**; mean Δ +0.0052; max |Δ| 0.1429 (chunk 166, 0.8367 → 0.9796).
  The loss a chunk carries is mostly a property of the chunk, not of the draw.
- **The 12 survival-rejected chunks, re-generated:** **7 of 12 reproduce the run's score to the
  digit under BOTH settings** (76 · 401 · 461 · 466 · 470 · 473 · 488 — 0.78 / 0.33 / 0.52 /
  0.69 / 0.29 / 0.73 / 0.03: the deletions are the model's *judgement*, and greedy makes the
  same one); **5 of 12 came back higher** (1 → 0.83, 82 → 1.0, 284 → 1.0, 290 → 0.96, 440 →
  0.94: those were sampling events). That is the cleanest split this lane has: of the
  concentrated deletions, ≈ 7/12 deterministic, ≈ 5/12 sampler.
- **Chunk 81 (J45's specimen):** the run wrote `person(10,`; today (a) and (b) are
  byte-identical to each other and both keep `person(100,` — the numeral corruption was a
  draw, not a policy. But greedy does not reduce numeral edits in aggregate (10 chunks vs 8).
- **(c) strict system line:** 2 of 5 improved (127: 0.7778 → 0.8148; 100: 0.8163 → 0.8571),
  3 unchanged, 0 numerals lost; n = 5, budget-bound — `Inferred` that a preservation
  instruction helps at the margin (consistent with arXiv 2609.04061), not measured at scale.

**The residual decomposed** (`edit_taxonomy.py`, 451 aligned passed pairs, 19,084 input
windows, **604 lost = 3.16 %**):

| lost-window class | windows | share | whose |
|---|---|---|---|
| cite-anchor (`[\[2\]](#page-49-0)` canonicalised; NEW rung) | 180 | 29.8 % | the audit |
| ligature-blind (J44 rung 2) | 111 | 18.4 % | the audit |
| escape-first (J44 rung 1 / SYM-076) | 86 | 14.2 % | the audit |
| reword / reflow (words present, window broken; partial_ratio ≥ 90) | 118 | 19.5 % | the model |
| partial (70–90) | 29 | 4.8 % | the model |
| deletion (< 70) | 80 | 13.2 % | the model |

**Document audit under successive ladders** (`ladder_probe.py`, `fidelity_audit.audit_analyst`,
both bindings patched): v2 **0.9718 / 49** (= manifest) → v3 0.9756 / 46 → v3b 0.9808 / 33 →
**v3c (+ cite-anchor) 0.9897 / 20**. Negative control: v3c scores a repaired citation 1.0 and a
deleted tail 0.5 — the rung cannot rescue a deletion. Still 0.53 pp short of the 0.995 gate.

Edit census (whole chunk, smallest transformation explaining the output): identical 25 · punct
41 · escape 4 · heading 1 · **other 380** of 451 — and 3,643 ladder-normalised input words are
absent from the outputs while 12,733 were added (the model pads: `<span>` anchors it rewrites,
bold it adds, list bullets it re-renders). Numerals: 14 chunks / 48 content tokens changed on the
shipped run (the S118 census of 145 / 691 was contaminated by page anchors — METER-CONFUSION,
now excluded).

**Marker's glyph substitutions (source 1's lane, counted here for the hand-over):** sidecar
`\_` 133 · `\*` 14 · cite links 483 well-formed + 326 broken · `%*` (= "Th") 52 · word-internal
`!` (= ff/ft/fi) 15 — the model repairs most (shipped: 20 / 5 / 264+184 / 30 / 10).

## Deviations recorded by this lane

- **G1 refuted** (the decoy): no temperature is sent; the model samples at its Modelfile 0.6.
- **The hold was reaped by my own negative control** (14:25:0x–14:25:31 EDT): a scratch probe
  re-implemented the watcher's read predicate with POSIX `os.kill(pid, 0)` — which on Windows
  is TerminateProcess or an access error that "reads as dead" — and `unlink`ed the live hold.
  The experiment process survived (the error branch fired); the gate stood open ≈ 30 s with the
  model resident; `drop/` was empty and `watcher.log` shows no event; the hold was restored with
  the experiment's live pid using the watcher's real probe (`OpenProcess` +
  `GetExitCodeProcess == STILL_ACTIVE`). PROBE-SHAPE + REGISTER-MISS: `watch_and_convert.
  pid_alive`'s docstring names this exact weapon. Filed for ERROR-BIN by the coordinator.
- The worktree spawned at `7c006f2`; reset to `e19e0e0` before any read (the fleet harness fault).
- 24 of 492 chunks could not be aligned to their shipped output by the head-locate rule
  (2, 3, 4, 6, 7, 64, 74, 108, 133, 176, 188, 228, 240, 325, 359, 434, 452, 455, 466, 467,
  468, 473, 488, 489) and are excluded from every per-pair number; the document-level numbers
  use the whole body and are unaffected.
- Two `watch_and_convert.py` and two `room_chat.py` processes are running (pids 26200/26428,
  38168/+1; each pair started in the same second — `Inferred` launcher + child, not two
  watchers). Not touched.
