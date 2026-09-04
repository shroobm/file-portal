# Lane D — Reconstructors and VLMs for the Bake-Off (spec #6)

GROUND: File Portal, offline-by-design, 1 RTX 3080 / 10GB / ~8.3GB free idle. No GPU used in
this lane — every number below is either read at source (WebFetch/WebSearch, tagged) or measured
CPU-only against Rab's own already-converted files. Nothing was downloaded or executed from an
untrusted source; the two things actually *run* were the repo's own `fidelity_audit.py` (read-only
invocation, not modified) and `du`/`find` against files already on Rab's disk.

## 0. The one thing I actually measured on a specimen

`windows-converter/fidelity_audit.py`'s CLI contract is `--pdf <path> --md <path> --lane
clean|scan` → it takes any markdown **string** and any PDF and returns a witness-comparison dict.
Nothing in that contract names Marker, an engine, or a model — so the claim "candidate X can be
scored by fidelity_audit.py unchanged" is not a hand-wave, it is Verified by direct execution:

```
PYTHONIOENCODING=utf-8 marker-env/python.exe fidelity_audit.py \
  --pdf ".../Investment Valuation ... Damodaran ... Fourth Edition ....pdf" \
  --md  ".../held/14c66834bdfeaa2e/Investment Valuation....Four.md" --lane clean
→ doc_survival: 0.9271, pages_scored: 1372   (POSITIVE — real converted book)
```
Negative control — same PDF, an unrelated one-line filler string as `--md`:
```
→ doc_survival: 0.0, pages_scored: 1372      (NEGATIVE — garbage text correctly cratered)
```
So the audit **discriminates** (0.0 vs 0.93, not a rubber stamp) and is **candidate-agnostic**
(only wants a markdown file + the source PDF). Any bake-off candidate that emits plain markdown
text clears this bar mechanically, with zero changes to the audit. One side-note, not chased
further here: my fresh 0.9271 differs from the manifest's stored 0.9334 for the *same* md/pdf
pair — pymupdf 1.28.0 here vs whatever version/commit converted it; residue for whoever owns
fidelity_audit.py version drift, not a Lane D finding.

Everything that follows is read-at-source (license files, HF file trees, GitHub API), not vendor
prose. No candidate model was loaded or run — that's the GPU lane's job, not this one.

---

## 1. Qwen3-VL (QwenLM/Qwen3-VL) — the primary candidate

**Sizes**: dense 2B/4B/8B/32B (Instruct + Thinking), MoE 30B-A3B/235B-A22B (Instruct + Thinking),
plus FP8 HF variants. Only 4B and 8B are 8.3GB-relevant.

**License at source** (fetched `LICENSE` directly, not the GitHub sidebar field):
> "License Name: Apache License 2.0 ... permits commercial use, modification, and distribution,
> provided you comply with attribution and notice requirements."
Confirmed also via `api.github.com/repos/QwenLM/Qwen3-VL` → `license.spdx_id: Apache-2.0`.

**GGUF exists and is official** (`Qwen/Qwen3-VL-4B-Instruct-GGUF`, `Qwen/Qwen3-VL-8B-Instruct-GGUF`
on HF, published by the Qwen org itself, not a community re-quant). Exact byte sizes from the HF
tree API:

| variant | LLM Q4_K_M | mmproj Q8_0 | combined | fits 8.3GB free? |
|---|---|---|---|---|
| Qwen3-VL-4B-Instruct | 2.497 GB (2,497,281,664 B) | 0.454 GB (453,974,304 B) | ~2.95 GB | yes, huge headroom for KV cache + vision tokens |
| Qwen3-VL-8B-Instruct | 5.028 GB (5,027,784,800 B) | 0.752 GB (752,289,728 B) | ~5.78 GB | yes, tighter but still under budget |

Run path: `llama-mtmd-cli` (llama.cpp's multimodal CLI) loading the quantized LLM + the mmproj
vision file together — this is llama.cpp's documented multimodal mechanism, not a hack.

**Document-parsing prompt**: the Qwen3-VL cookbook is referenced for document parsing
("layout position information and ... Qwen HTML format") but I could not pull the literal
prompt text out of the README fetch — the summarizer paraphrased rather than quoted it.
**Residue**: the exact recommended prompt string is UNREAD; before a real run, fetch
`qwen.readthedocs.io`'s document-parsing cookbook page directly (not summarized) or steal
zerox's prompt below, which is generic enough to reuse on any VLM.

**Emits**: free-form text — with the right prompt, markdown (possibly with embedded HTML tables,
per the cookbook's "Qwen HTML format" mention). Same interface shape as Marker's own output →
scoreable by fidelity_audit.py unchanged (Verified in §0, interface-level, not this model
specifically).

**Test quality**: did not find a `tests/` dir in `QwenLM/Qwen3-VL` (contents fetch 404'd) — this
is an inference/cookbook repo, not a library with a regression suite. **None found.**

**Headline number**: none quoted here — this is a general-purpose VLM, not a document-benchmark
paper; the number that matters is the one Rab would get from running it on Damodaran, not a
vendor OCR leaderboard entry.

**Verdict: MEASURE_NEXT.** Smallest next measurement: render one Damodaran page (one with a
flagged/degenerate table, e.g. page 3 or 9 from the existing `pages_flagged` list) to PNG with
pymupdf (already CPU-only, already in marker-env), run it through `llama-mtmd-cli` with the
4B Q4_K_M + mmproj, capture the markdown, and audit that single page against the same pymupdf
witness fidelity_audit.py already uses. That is a same-day, single-GPU-session, single-page
measurement — the cheapest real test on this whole roster.

---

## 2. Chandra OCR 2 (datalab-to/chandra) — already on the roster, refined and one risk added

Spec's own note says "on disk, 5B, needs a separate env." Both numbers needed correction:

**On-disk weights** (Verified, `du -b` byte-exact): `C:/Users/Bndit/ml/chandra/chandra-ocr-2/
model.safetensors` = **10,611,947,865 bytes = 9.88 GiB**, matching the spec's "10.6 GB BF16"
(decimal GB) — not 5B-sized at BF16. `config.json` states **9B params** on the HF card
(`datalab-to/chandra`), so the "5B" in the spec's parenthetical is stale/wrong; 9B is the number
at source.

**License at source — this is the real find.** Not Apache/MIT for the weights:
> GitHub badge: "Code License: Apache 2.0" / "Model License: OpenRAIL-M"
> HF card: license field literally `"openrail"`; repo prose: "a modified OpenRAIL-M license
> (free for research, personal use, and startups under $2M funding/revenue, cannot be used
> competitively with our API)."
File Portal is personal/local use, so this almost certainly clears — but it is categorically
different from the Apache-2.0 everything else on this roster carries, and it carries a
behavioral-use clause ("cannot be used competitively with our API") that Apache-2.0 does not.
Worth Rab's own eyes before anything built on Chandra ships anywhere.

**A architecture wrinkle worth flagging, not resolving here**: `config.json` on disk names
`model_type: "qwen3_5"` / `"qwen3_5_text"` with a `mamba_ssm_dtype: "float32"` field — i.e. the
backbone is a **hybrid Mamba/SSM + Transformer** architecture (Qwen3.5-class), not a plain
attention-only Qwen3-VL. The HF card's own tag says `qwen3_vl` — those two labels don't obviously
agree and I did not chase which is authoritative. This matters because:

**GGUF exists but only from third parties**, none from `datalab-to` itself (their own card only
documents `transformers`-local and `vllm`-remote paths, no llama.cpp mention at all):
`mradermacher/chandra-ocr-2-GGUF` → `chandra-ocr-2.Q4_K_M.gguf` = 3,066,385,440 B (2.86 GiB),
`chandra-ocr-2.Q4_K_S.gguf` = 2,921,468,960 B (2.72 GiB) — either would fit 8.3GB free with room
to spare **if it loads correctly**. But llama.cpp's support for hybrid Mamba/SSM+attention
architectures is new and has historically lagged behind novel arches by months; a random
quantizer account successfully *producing* a GGUF file does not prove llama.cpp can *run* it
correctly (garbled/degenerate output from an unsupported arch is a real, previously-seen failure
mode, not a hypothetical one). **This is Unknown, not Inferred-safe** — I did not download or
load it (no GPU, and downloading an unverified third-party quant of a bleeding-edge arch is
exactly the kind of untrusted-download this lane is told not to do without asking).

The lower-risk path to the same 8.3GB budget: upgrade `marker-env`'s `transformers` past 4.57.6
(the spec's own stated blocker) and load the on-disk BF16 safetensors at **bitsandbytes INT4**
(~9B params → roughly 5GB at INT4, well-trodden `transformers`+`bitsandbytes` path, not a novel
hybrid-arch GGUF gamble) instead of trusting a stranger's GGUF of a new SSM hybrid.

**Emits**: markdown, HTML, or JSON directly (HF card, quoted) → scoreable by fidelity_audit.py
unchanged, same as §0.

**Verdict: BAKE_OFF_CANDIDATE**, gated behind either (a) the transformers-upgrade + bitsandbytes
INT4 path (safer, more engineering), or (b) a load-test of the third-party GGUF (cheaper, riskier,
license and arch both unverified) — Rab's call which risk he'd rather spend first.

---

## 3. facebookresearch/nougat — alive-adjacent, not dead, math-native

**Maintenance**: `pushed_at 2025-02-21T16:38:00Z` → **559 days** before today (2026-09-03),
not archived. That is dormant by this project's own yardstick (everything in the MECHANICAL
TRIAGE table with 0–43 days since push was kept; Nougat's 559 sits closer to the *discarded*
xy-cut-tree's 2886 or BobLd's 1068 than to the keepers) — worth naming since the spec didn't
already discard it the way it pre-discarded the notebook wrapper.

**License — codebase vs weights split, same pattern as Chandra**:
> GitHub: "Nougat codebase is licensed under MIT."
> HF (`facebook/nougat-base` model card): license field `cc-by-nc-4.0` — **non-commercial**.
Personal/local use clears NC; redistribution or anything commercial would not.

**Size**: HF card states **0.3B params** for `nougat-base` (Donut architecture: Swin transformer
vision encoder + mBART text decoder) — trivially small, fits 8.3GB free by roughly 25x margin,
plausibly CPU-capable for occasional single-page runs even without the GPU.

**What it does for math**: purpose-built to output **Mathpix-Markdown (.mmd)** — its own README:
"understands LaTeX math and tables" and "we make use of the LaTeX tables" — i.e. this is a model
trained specifically to emit the `\begin{array}`-style LaTeX table/equation markup that spec #1's
Damodaran specimen and SYM-056's 61-unterminated-array problem are made of. That is a closer
match to spec #1's actual failure mode (LaTeX array balance) than any other candidate on this
roster, Chandra and Qwen3-VL included — worth stating plainly since the brief only asked "what
does it do for MATH-heavy pages Marker does not," and the honest answer is: it was trained on
scientific papers specifically to get LaTeX math/table markup right, which is precisely the
class of output SYM-056 is failing on.

The caveat: Damodaran is a *finance* textbook — its tables are mostly plain numeric grids, not
LaTeX equations, so Nougat's specific training distribution (arXiv-style scientific papers) is
a partial match at best for spec #1's actual specimen. It is a stronger fit for a *math-heavy*
specimen than for Damodaran specifically.

**Emits**: `.mmd` (markdown-compatible) file directly, or a markdown string via its own API →
scoreable by fidelity_audit.py unchanged (§0), highest-confidence fit on this roster since the
output shape is closest to Marker's own.

**Test quality**: not checked in depth (time-boxed); Nougat ships an eval script comparing
predicted `.mmd` against ground-truth `.mmd` with an edit-distance metric per the paper, but I
did not pull and quote a specific assertion — **residue, not verified to the "quote a test" bar.**

**Verdict: BAKE_OFF_CANDIDATE.** Tiny, offline, MIT code / CC-BY-NC-4.0 weights (flagged for
Rab), purpose-trained on exactly the LaTeX-table failure mode SYM-056 already named. Smallest
measurement: run `nougat` on one already-rendered page image from the SYM-056 corpus (the pages
already identified as unterminated `\begin{array}`) and diff its `.mmd` against Marker's own
output for the same page.

---

## 4. Florence-2 (microsoft/Florence-2-{base,large}) — real, cheap, licensed, NOT off-the-shelf ready

Rab's question was narrow: "is Florence-2 itself — MIT, ~0.8B — a document OCR reader worth a
bake-off slot?" Checked at source, the answer is **not without finetuning work nobody has signed
up for.**

**License**: HF card license field is literally `"mit"` — confirmed, no NC/RAIL surprise here,
the cleanest license on this whole roster.

**Sizes**: `Florence-2-base` = **0.23B params**, `Florence-2-large` = **0.77B params** (both
quoted verbatim from the HF card's own size table) — the "~0.8B" in the brief matches
`-large` exactly. Both are trivially small at 8.3GB (fp16 large ≈ 1.5GB).

**What it actually emits**: task-token strings — `<OCR>` returns plain text with no layout,
`<OCR_WITH_REGION>` returns text + bounding boxes. There is **no task token that emits a
reconstructed page as markdown or an HTML table** — Florence-2 is a general vision-language
model with OCR as one of ~15 task prompts, not a document-to-markdown pipeline. Getting from its
raw output to a fidelity_audit.py-scoreable `.md` file would require writing the block-assembly
and table-reconstruction logic yourself — Florence-2 supplies none of it.

**A vendor-quoting-itself trap, caught and worth flagging explicitly**: search results surfaced
"Florence-VL 3B/8B: DocVQA 82.1/84.9" as if it were Florence-2's own document benchmark. It is
not — Florence-VL (arXiv 2412.04424) is a *different, later, larger* model that reuses the
Florence name for its vision encoder, not Microsoft's original Florence-2 checkpoint. The only
number I could actually attribute to Florence-2-L itself is **TextVQA 81.5** (short-answer visual
QA on natural images, not full-page document reconstruction) — no denominator/benchmark for
page-level markdown or table fidelity exists for the pretrained checkpoint at all. Quoting the
82.1/84.9 number as "Florence-2's DocVQA score" — which the first search pass nearly did — would
have been exactly the un-denominated vendor number this project's reading protocol exists to
catch.

**Verdict: IDEA_ONLY.** Real, free, cheap, permissively licensed — but off-the-shelf it answers
short questions about an image, it does not reconstruct a page. Not a bake-off slot without
finetuning (out of scope here; `anyantudre/Florence-2` notebook that tried this is itself dead
per the spec's own discard list, and I found no successor).

---

## 5–7. The three pre-discarded repos, in the two lines each the brief asked for

**getomni-ai/zerox** — cloud-only (OpenAI/Azure/Bedrock/Gemini/Anthropic vision models, no local
weights of any kind; MIT license on the wrapper code itself). DISCARD as a candidate — it cannot
run offline, full stop. **Worth stealing**: its page-image→markdown system prompt, pulled
verbatim from `py_zerox/pyzerox/constants/prompts.py`:
> "Convert the following document to markdown. Return only the markdown with no explanation
> text. Do not include delimiters like ```markdown or ```html. RULES: - You must include all
> information on the page. Do not exclude headers, footers, or subtext. - Return tables in an
> HTML format. - Charts & infographics must be interpreted to a markdown format. Prefer table
> format when applicable. - Logos should be wrapped in brackets. Ex: <logo>Coca-Cola<logo> -
> Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY<watermark> - Page
> numbers should be wrapped in brackets. Ex: <page_number>14<page_number> or
> <page_number>9/22<page_number> - Prefer using ☐ and ☑ for check boxes."
This is directly reusable as the starting prompt for Qwen3-VL or Chandra above — it already
solves the "return tables as HTML" instruction that both those candidates would need anyway.

**run-llama/llama-parse-py** — cloud-only (LlamaParse SaaS). The repo itself is now
**deprecated**, observed directly on its own README: "are deprecated and will be maintained
until May 1, 2026," redirecting to `llama_cloud_services`. DISCARD — cloud, and now also
sunsetting. Nothing stealable found: no license, no output-format detail, and no prompt text
surfaced in the README (Unknown, not chased further — this is the least load-bearing of the
seven, and the repo is telling its own users to leave it).

**illuin-tech/colpali** — retrieval, not reconstruction. It produces multi-vector page-image
*embeddings* for query-to-page matching (ColBERT-style late interaction over a
PaliGemma/Qwen2/Qwen2.5/Qwen3/Qwen3.5-VL backbone depending on variant, 256M–4.5B params); it
does not emit text at all, so it **cannot** be scored by fidelity_audit.py's witness comparison
— there is no markdown for the audit to diff. DISCARD as a spec #6 candidate on that basis alone.
Codebase license MIT (verified, fetched `LICENSE` directly); model weights inherit their
backbone's license (Gemma license for the original PaliGemma-backed ColPali, Apache-2.0 for the
Qwen-backed variants) — mixed, check per-checkpoint. Real pytest suite exists
(`tests/{models,loss,compression,collators,interpretability,utils}`, further split per backbone
architecture under `tests/models/`) — Observed structure only, did not pull and quote a specific
assertion (residue). Repo is very active: `pushed_at 2026-09-01`, 2 days before today.

**The blank-crop question (SYM-053), asked directly — is ColPali real here or a stretch?**
A stretch, leaning toward not-real for this specific job. ColPali's embedding space is trained
end-to-end for semantic query-to-page matching (does this page answer this question), not
calibrated as a blankness/anomaly score — there is no published threshold, no training signal
for "blank," and nothing in the repo's own docs mentions classification or blank-detection as a
use case (checked directly, none found). A blank crop is already trivially detectable CPU-only,
zero-model, from pymupdf alone — pixel ink-coverage or `page.get_text()` length against a
threshold — at a cost of milliseconds and no VRAM at all. Reaching for a multi-vector VLM
embedding model to answer a question a five-line pixel-variance check already answers is the
wrong tool for SYM-053; note it and move on, exactly as the brief itself said to.

---

## Bake-off roster summary (spec #6's requested table)

| candidate | VRAM @ fits | license (at source) | emits | audit-scoreable unchanged | verdict |
|---|---|---|---|---|---|
| Qwen3-VL-4B-Instruct | ~2.95GB (Q4_K_M+mmproj Q8_0) | Apache-2.0 | text/markdown (prompted) | yes | MEASURE_NEXT |
| Qwen3-VL-8B-Instruct | ~5.78GB (Q4_K_M+mmproj Q8_0) | Apache-2.0 | text/markdown (prompted) | yes | MEASURE_NEXT |
| Chandra OCR 2 (BF16, on disk) | 9.88GB — does NOT fit as-is | Code Apache-2.0 / **Model OpenRAIL-M** (personal-use OK, competitive-use barred) | markdown/HTML/JSON | yes | BAKE_OFF_CANDIDATE (needs INT4 or unverified 3rd-party GGUF) |
| Chandra OCR 2 (community GGUF Q4_K_M) | 2.86GB, nominal | same as above + arch-support unverified | markdown/HTML/JSON | yes, if it loads | BAKE_OFF_CANDIDATE (Unknown: hybrid Mamba/SSM arch, llama.cpp support unverified) |
| nougat-base | ~1.5GB fp16 (0.3B) | Code MIT / **Weights CC-BY-NC-4.0** | .mmd (markdown, LaTeX math/tables) | yes | BAKE_OFF_CANDIDATE |
| Florence-2-large | ~1.5GB fp16 (0.77B) | MIT | task-token text, not page markdown | no (needs wrapper + no table logic exists) | IDEA_ONLY |
| zerox | n/a — cloud only | MIT (wrapper) | markdown (cloud VLM) | n/a, offline-disqualified | DISCARD (steal the prompt) |
| llama-parse-py | n/a — cloud only, deprecated | Unknown | Unknown | n/a, offline-disqualified | DISCARD |
| colpali (any variant) | 256M–4.5B, varies | MIT (code) / Gemma or Apache-2.0 (weights, per backbone) | embeddings only, no text | **no** — nothing for the audit to diff | DISCARD |

Marker remains the baseline throughout; nothing above ran on the GPU.

## Residue (things I did not chase, named so the next reader doesn't re-discover them blind)
- Qwen3-VL's actual document-parsing cookbook prompt: paraphrased by the fetch summarizer, not
  quoted verbatim — go to `qwen.readthedocs.io`'s cookbook page directly before a real run.
- Chandra's `qwen3_5` (on-disk config.json) vs `qwen3_vl` (HF card tag) naming disagreement:
  not resolved, flagged only.
- Whether the third-party Chandra GGUF quants actually load correctly under llama.cpp: not
  tested (would require a download this lane was told not to make unasked, of an unverified
  quant of a novel hybrid architecture).
- Nougat's own eval methodology: not pulled to the "quote one test" bar, time-boxed out.
- `llama-parse-py`'s license and output format: genuinely not found in two fetch attempts,
  left Unknown rather than guessed.
