# docling-calibration — the S71 calibration run

**Why this exists:** the S28→S30 tradition — no engine earns trust through literature claims;
it earns numbers on THIS machine's real corpus first, then Rab signs thresholds. This prototype
calibrated **granite-docling-258M** (IBM, DocTags) before the Bench's transcribe gesture was
allowed to use it, and before the docs/24 engine-lever question could be answered honestly.

## The environment (isolated by law)

The model runs in its **own venv** — never marker-env (the production lane's interpreter is
not a lab bench). Recipe, as run 2026-08-10:

```
uv venv C:\Users\Bndit\ml\docling-env --python 3.12
uv pip install --python C:\Users\Bndit\ml\docling-env\Scripts\python.exe ^
    torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv pip install --python C:\Users\Bndit\ml\docling-env\Scripts\python.exe ^
    transformers accelerate pillow docling-core pymupdf
```

- torch **2.11.0+cu128** — deliberately the same build marker-env runs (known-good on this box).
- The model (~500 MB) downloads from HF on first load into `%USERPROFILE%\.cache\huggingface`.
- Consumers: `calibrate.py` (this dir) and `prototypes/repair-bench/transcribe_worker.py`
  (the Bench's reading eye — process-per-request, VRAM returns on exit).

## Running

```
C:\Users\Bndit\ml\docling-env\Scripts\python.exe calibrate.py --books claudecode,cybernetics --fp16-ab
C:\Users\Bndit\ml\docling-env\Scripts\python.exe calibrate.py --books damodaran
C:\Users\Bndit\ml\docling-env\Scripts\python.exe calibrate.py --books valentine,brain
```

Refuses while `.gpu-lock` exists (the serialization law applies to lab benches too). Appends one
fsync'd JSON line per sample to `results.jsonl` — a killed run keeps its data. Books and page
choices are cast from the timeline: table-dense Damodaran/Valentine, clean claude-code,
figure-dense Cybernetics, degraded-scan Brain.

## What it measures, per sample

wall seconds · torch peak VRAM (the model's true appetite — driver-level usage is higher on a
lived-in desktop: browser/compositor contexts share the card) · DocTags length · `<otsl>` table
emissions · and on clean-lane samples two witness-agreement floors: exact 12-word **window
survival** and **numeric-token Jaccard** (both fuzzless — floors, not the audit's full metric).
Both scopes: full **page** at 144 dpi (the engine-lever question) and **crop** at 220 dpi — the
Bench's own crop dpi (the transcribe question).

## The findings (S71)

See `calibration-report.md` beside this file — the numbers that replaced docs/24's `[I]` bands,
including the headline: **crop scope ~2–3 s at ~650–750 MiB (Bench-viable), page scope 29–86 s
(NOT competitive with Marker on this card for whole documents)**. The synthetic middle-band
crops are a known limitation (real Bench crops target zones a human chose); the live G5 proof
covers that gap.
