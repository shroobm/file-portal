"""WHAT THIS FILE DOES: a command-line worker that loads the granite-docling vision model, reads one cropped page
image (--image), converts it to markdown, scores the markdown against an optional witness text file (--witness), and
prints one JSON result line on stdout (exit 0 on a completed read, 1 on any error). It writes no files. It is started
as a subprocess by bench.py; entry point is main().

transcribe_worker.py — the Bench's reading eye (S71, docs/23 built).

granite-docling-258M reads ONE crop PNG and returns markdown + gate metrics as a single
JSON line on stdout. Runs ONLY under docling-env (never marker-env — the production lane's
interpreter is not a lab bench). Process-per-request by design: weights load, the crop is
read, the process exits, VRAM returns — keep_alive:0 as a process model. Calibrated S71:
crop-scope ~2-3 s, ~650-750 MiB peak (see prototypes/docling-calibration/).

Called by bench.py via subprocess. The pipeline never imports this (quarantine convention).
Gate metrics computed here (the worker holds both texts); REFUSAL semantics: ok=false when
DocTags fail to parse or the read is empty — the Bench falls back to the image-embed gesture.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata

# -- quiet the model libraries (environment defaults, set before they are imported) --
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

# -- the model and the instruction text sent with every crop --
MODEL = "ibm-granite/granite-docling-258M"
PROMPT = "Convert this page to docling."


# -- text-comparison gate metrics (witness text vs the model's markdown) --
def _norm(s: str) -> str:
    """Normalize text for comparison: Unicode NFKC, case-folded, whitespace collapsed to single spaces, trimmed."""
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"\s+", " ", s).strip()


def window_survival(witness: str, output: str, w: int = 12) -> float | None:
    """The audit's window idea, fuzzless: fraction of witness 12-word windows found verbatim
    in the output after normalization. A floor metric — exact only."""
    wn, on = _norm(witness).split(), _norm(output)
    # non-overlapping windows of w words taken from the witness (the step equals the window size)
    wins = [" ".join(wn[i:i + w]) for i in range(0, max(0, len(wn) - w), w)]
    if not wins:
        return None
    return round(sum(1 for x in wins if x in on) / len(wins), 4)


def numeric_jaccard(witness: str, output: str) -> float | None:
    """The link-fence's contract with digits: Jaccard over numeric-token sets — the
    highest-stakes tokens in table zones, permutation-invariant by construction."""
    def nums(t: str) -> set[str]:
        """Return the set of numeric tokens (digits with optional commas/dots) found in t."""
        return set(re.findall(r"\d[\d,.]*", t))
    a, b = nums(witness), nums(output)
    if not a and not b:
        return None
    return round(len(a & b) / max(1, len(a | b)), 4)


# -- entry point: one crop in, one JSON line out --
def main() -> int:
    """Parse the command line, run the model on --image, print one JSON record (ok, markdown, gates, timings, VRAM).

    Returns 0 when the read completed (even if ok is false), 1 when any exception was caught (an error JSON line
    is printed instead). Side effects: loads the model onto the GPU, reads the image (and witness) file, prints."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--witness", default=None, help="path to witness text (clean lane only)")
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16"])
    ap.add_argument("--max-new", type=int, default=1536)
    a = ap.parse_args()

    try:
        # heavy imports are deferred to here so a failure becomes the JSON error line below
        import torch
        from PIL import Image
        from transformers import AutoProcessor
        try:
            from transformers import AutoModelForImageTextToText as ModelCls
        except ImportError:
            from transformers import AutoModelForVision2Seq as ModelCls

        dt = torch.bfloat16 if a.dtype == "bf16" else torch.float16
        t0 = time.time()
        proc = AutoProcessor.from_pretrained(MODEL)
        model = ModelCls.from_pretrained(MODEL, dtype=dt).to("cuda")
        load_s = time.time() - t0

        img = Image.open(a.image).convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image"},
                                                 {"type": "text", "text": PROMPT}]}]
        prompt = proc.apply_chat_template(messages, add_generation_prompt=True)
        inputs = proc(text=prompt, images=[img], return_tensors="pt").to("cuda")
        torch.cuda.reset_peak_memory_stats()
        t1 = time.time()
        out = model.generate(**inputs, max_new_tokens=a.max_new, do_sample=False)
        gen_s = time.time() - t1
        vram = torch.cuda.max_memory_allocated() / 1024**2
        tags = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                                 skip_special_tokens=False)[0]
        clean = tags.replace("<|end_of_text|>", "").strip()

        # convert the model's DocTags output to markdown; a parse failure marks the read as refused
        parse_ok, md = True, ""
        tables = clean.count("<otsl>")
        try:
            from docling_core.types.doc import DoclingDocument
            from docling_core.types.doc.document import DocTagsDocument
            dtd = DocTagsDocument.from_doctags_and_image_pairs([clean], [img])
            md = DoclingDocument.load_from_doctags(
                dtd, document_name="crop").export_to_markdown()
        except Exception:  # noqa: BLE001 — a parse failure IS the gate result
            parse_ok = False

        # gate metrics: scored only when a non-empty witness file was given
        gates: dict = {"parse_ok": parse_ok, "tables": tables,
                       "window_survival": None, "numeric_jaccard": None}
        if a.witness and os.path.isfile(a.witness):
            wit = open(a.witness, encoding="utf-8").read()
            if wit.strip():
                gates["window_survival"] = window_survival(wit, md)
                gates["numeric_jaccard"] = numeric_jaccard(wit, md)

        # assemble the result record; ok is false when the parse failed or the markdown is empty
        ok = parse_ok and bool(md.strip())
        rec = {"ok": ok, "markdown": md, "doctags_chars": len(clean), "gates": gates,
               "secs": round(gen_s, 1), "load_s": round(load_s, 1),
               "vram_mib": round(vram), "model": MODEL.split("/")[-1], "dtype": a.dtype}
        if not ok:
            rec["error"] = ("DocTags failed to parse" if not parse_ok
                            else "the model read nothing usable from this region")
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 — one honest JSON error line, never a traceback
        print(json.dumps({"ok": False, "error": str(exc)[:400]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
