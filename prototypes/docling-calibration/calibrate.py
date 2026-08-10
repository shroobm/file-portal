"""prototypes/docling-calibration/calibrate.py — the S71 calibration run (S28->S30 tradition).

Measures granite-docling-258M on THIS machine's real corpus before any trust is extended:
per-page wall seconds, peak VRAM, DocTags/table emission, and (clean lane) witness agreement —
at BOTH scopes: full page (the engine-lever question) and crop (the Bench transcribe question).

Quarantined per the prototypes/ convention: the pipeline never imports this. Runs in the
isolated docling-env (never marker-env). Refuses to start while .gpu-lock exists — the
serialization law applies to lab benches too.

Usage:  docling-env\\Scripts\\python.exe calibrate.py --books claudecode,cybernetics [--fp16-ab]
Output: appends one JSON line per sample to results.jsonl (fsync'd — a killed run keeps its data).
"""

import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import pymupdf
import torch
from PIL import Image
from transformers import AutoProcessor

try:
    from transformers import AutoModelForImageTextToText as ModelCls
except ImportError:  # older transformers
    from transformers import AutoModelForVision2Seq as ModelCls

MODEL = "ibm-granite/granite-docling-258M"
DONE = Path(r"C:\Users\Bndit\ml\library\drop\done")
GPU_LOCK = Path(r"C:\Users\Bndit\ml\library\.gpu-lock")
OUT = Path(__file__).parent / "results.jsonl"
DPI = 144
PROMPT = "Convert this page to docling."

# The corpus, by the timeline's own casting: pages chosen for what each book is known for.
BOOKS = {
    "claudecode": {"pdf": "claude-code-up-and-running.pdf", "lane": "clean",
                   "pages": [5, 40], "crop_pages": [20]},
    "cybernetics": {"pdf": "Cybernetics_Book_of_Models-v4.6b-complete.pdf", "lane": "clean-figure",
                    "pages": [10, 40], "crop_pages": [25]},
    # S71 trim, recorded honestly: damodaran p900 was aborted >15 min into a token-wall
    # decode under desktop GPU contention — marginal value nil after p100 answered the table
    # question (tables:1, numeric J .9688). Scan PAGES dropped for the same reason: the
    # document-scope verdict was already decided by six measured page rows. What remains
    # matters: CROP scope — the Bench's own question.
    "damodaran": {"pdf": "Investment Valuation - Aswath Damodaran (4e, 2025).pdf", "lane": "clean-table",
                  "pages": [], "crop_pages": [100, 400]},
    "valentine": {"pdf": "Best Practices for Equity Research Analysts - James J Valentine (2011).pdf",
                  "lane": "scan-table", "pages": [], "crop_pages": [150]},
    "brain": {"pdf": "BRAIN OF THE FIRM STAFFORD BEER (WITH OCR) ISBN 13 9780471162131.pdf",
              "lane": "scan", "pages": [], "crop_pages": [100]},
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"\s+", " ", s).strip()


def window_survival(witness: str, output: str, w: int = 12) -> float | None:
    """Fraction of witness 12-word windows found verbatim in output (exact containment
    after normalization). The audit's idea, fuzzless — a floor, not the full metric."""
    wn, on = norm(witness).split(), norm(output)
    wins = [" ".join(wn[i:i + w]) for i in range(0, max(0, len(wn) - w), w)]
    if not wins:
        return None
    return round(sum(1 for x in wins if x in on) / len(wins), 4)


def numeric_jaccard(witness: str, output: str) -> float | None:
    """Multiset-lite: Jaccard over the sets of numeric tokens — the table-stakes tokens."""
    nums = lambda t: set(re.findall(r"\d[\d,.]*", t))
    a, b = nums(witness), nums(output)
    if not a and not b:
        return None
    return round(len(a & b) / max(1, len(a | b)), 4)


def doctags_to_md(tags: str, img) -> tuple[str, int]:
    from docling_core.types.doc import DoclingDocument
    from docling_core.types.doc.document import DocTagsDocument
    clean = tags.replace("<|end_of_text|>", "").strip()
    tables = clean.count("<otsl>")
    dt = DocTagsDocument.from_doctags_and_image_pairs([clean], [img])
    dd = DoclingDocument.load_from_doctags(dt, document_name="cal")
    return dd.export_to_markdown(), tables


def run_one(model, proc, img, max_new: int) -> tuple[str, float, float]:
    messages = [{"role": "user", "content": [{"type": "image"},
                                             {"type": "text", "text": PROMPT}]}]
    prompt = proc.apply_chat_template(messages, add_generation_prompt=True)
    inputs = proc(text=prompt, images=[img], return_tensors="pt").to("cuda")
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    out = model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
    secs = time.time() - t0
    vram = torch.cuda.max_memory_allocated() / 1024**2
    tags = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                             skip_special_tokens=False)[0]
    return tags, secs, vram


def record(rec: dict) -> None:
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(f"  -> {rec['book']} p{rec.get('page')} {rec['mode']} "
          f"{rec['dtype']}: {rec['secs']}s, {rec['vram_mib']} MiB, "
          f"surv={rec.get('window_survival')}, numJ={rec.get('numeric_jaccard')}, "
          f"tables={rec.get('tables')}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True)
    ap.add_argument("--fp16-ab", action="store_true")
    args = ap.parse_args()

    if GPU_LOCK.exists():
        print("REFUSED: .gpu-lock present — the line owns the card (serialization law).")
        return 2

    dtypes = [("bf16", torch.bfloat16)] + ([("fp16", torch.float16)] if args.fp16_ab else [])
    for dname, dt in dtypes:
        t0 = time.time()
        proc = AutoProcessor.from_pretrained(MODEL)
        model = ModelCls.from_pretrained(MODEL, dtype=dt).to("cuda")
        load_s = round(time.time() - t0, 1)
        print(f"[{dname}] loaded in {load_s}s", flush=True)

        for bid in args.books.split(","):
            b = BOOKS[bid]
            doc = pymupdf.open(DONE / b["pdf"])
            # full-page scope (the engine-lever question)
            for pno in b["pages"]:
                if pno >= len(doc):
                    continue
                page = doc[pno]
                pix = page.get_pixmap(dpi=DPI)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                tags, secs, vram = run_one(model, proc, img, 4096)
                md, tables = doctags_to_md(tags, img)
                wit = page.get_text() if b["lane"].startswith("clean") else ""
                record({"book": bid, "lane": b["lane"], "mode": "page", "page": pno,
                        "dtype": dname, "dpi": DPI, "img": list(img.size),
                        "secs": round(secs, 1), "vram_mib": round(vram),
                        "doctags_chars": len(tags), "md_chars": len(md), "tables": tables,
                        "window_survival": window_survival(wit, md) if wit else None,
                        "numeric_jaccard": numeric_jaccard(wit, md) if wit else None})
            # crop scope (the Bench transcribe question): middle band of the page
            for pno in b["crop_pages"]:
                if pno >= len(doc):
                    continue
                page = doc[pno]
                pix = page.get_pixmap(dpi=220)  # the Bench's own crop dpi
                full = Image.open(io.BytesIO(pix.tobytes("png")))
                w, h = full.size
                img = full.crop((int(w * .08), int(h * .30), int(w * .92), int(h * .62)))
                tags, secs, vram = run_one(model, proc, img, 1536)
                md, tables = doctags_to_md(tags, img)
                r = page.rect
                clip = pymupdf.Rect(r.width * .08, r.height * .30,
                                    r.width * .92, r.height * .62)
                wit = page.get_text(clip=clip) if b["lane"].startswith("clean") else ""
                record({"book": bid, "lane": b["lane"], "mode": "crop", "page": pno,
                        "dtype": dname, "dpi": 220, "img": list(img.size),
                        "secs": round(secs, 1), "vram_mib": round(vram),
                        "doctags_chars": len(tags), "md_chars": len(md), "tables": tables,
                        "window_survival": window_survival(wit, md) if wit else None,
                        "numeric_jaccard": numeric_jaccard(wit, md) if wit else None})
        del model
        torch.cuda.empty_cache()
        record({"book": "-", "mode": "load", "dtype": dname, "secs": load_s,
                "vram_mib": 0, "page": None})
    return 0


if __name__ == "__main__":
    sys.exit(main())
