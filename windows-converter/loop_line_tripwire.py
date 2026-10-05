# -*- coding: utf-8 -*-
"""loop_line_tripwire.py — reproduce a converter loop on ONE named section, the converter's own way (S220 E9, 2026-10-05).

The defect it pins (Observed S220 E9, reading L): marker 1.10.2 reads a text block of more than 15 lines in LINE mode —
each of the detector's lines is its own slice through Surya's recognizer (task ocr_with_boxes, no hint, max_tokens 2048,
max_sliding_window 2148, the repeat guard blind above five distinct tokens). On cond-mat.mtrl-sci p. 13, block
/page/12/Text/8 (16 detector lines), line 11 — "terms of the many-body expansion (the EquiformerV2," — decodes as
"Equiporal " ×200 to the cap while the other fifteen lines read clean; the same block read WHOLE (one polygon, block mode)
reads clean with the word in place. The loop is a property of the line slice, not of the card's dtype or the batch: it
reproduced on the CPU in float32, batch 32, with the card hidden (1,982 s, the one line decoding to the cap).

What this script does: renders the page as marker does (flattened, no annotations; 96 dpi for the detector, 192 dpi for
the recognizer), runs the detector, keeps the lines (confidence > 0.8) whose centre lies inside the block, sends them
through the recognizer in marker's line-mode call, and reports which lines loop (`fixes.is_loop`). With `--control` it
also reads the block whole (block mode) — the negative control, which must NOT loop. The exit code answers `--expect`:
  --expect present   exit 0 when the named line loops (the converter's defect reproduced — the tripwire TRIPS),
  --expect absent    exit 0 when no line loops AND the lines still carry text (`--control` required: the line-mode read's
                     words must be at least 80 % of the block-whole control's — an empty recognizer is not "absent").
Any other outcome exits 1 and says why. A probe that could not run exits 2 and says UNREAD; it never says "absent".

WHAT IT TESTS, EXACTLY (S220 E9's verifier, 04:45Z): the RECOGNIZER's line-mode path — surya called the way marker's
OcrBuilder calls it, with marker's polygons. It does not go through marker's pipeline or through `fixes.LoopRetryOcrBuilder`,
so a remedy that lives in `fixes.py` (the ticket converter/loop-retry-line-mode) is NOT exercised by `--expect absent` here;
that remedy is tested by marker itself on the page (the card phase's reading M: `marker_single` with the lever armed) or by a
`--through-marker` mode this file does not have yet. A remedy that changes the slices or the recognizer call (a per-line cap,
a padded strip) IS exercised here. The looping line is named by its ordinal in the detector's top-to-bottom order, not by
its text; a detector change that re-orders the lines moves the ordinal.

Devices: `--device cpu` (the default) hides the card before torch is imported — slow (the looping line alone takes
~30 min on this box) but needs nothing; `--device cuda` takes the card mutex `Local\\file-portal-card` exactly as the
converter does and REFUSES when it is held — run it only in a window where the line is paused (one process on the card).

Run (never a bare `python`):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe windows-converter\\loop_line_tripwire.py "<pdf>" 13 315,54,562.5,243.6 \\
      --line 11 --expect present --control --out <dir>
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("pdf")
    p.add_argument("page", type=int, help="1-based page number")
    p.add_argument("bbox", help="the block's bbox in PDF points: x0,y0,x1,y1 (marker's frame)")
    p.add_argument("--line", type=int, required=True, help="the 1-based index (top to bottom) of the line expected to loop")
    p.add_argument("--expect", choices=("present", "absent"), required=True)
    p.add_argument("--control", action="store_true", help="also read the block whole (block mode) — it must not loop")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--dtype", choices=("float32", "bfloat16"), default=None, help="default: float32 on cpu, bfloat16 on cuda (the converter's)")
    p.add_argument("--batch", type=int, default=32, help="recognition batch size (the converter's is 32)")
    p.add_argument("--out", default=None, help="directory for the readings (JSON + the slices' boxes); default: no files")
    return p.parse_args(argv)


def take_card_mutex():
    """CreateMutexW + WaitForSingleObject(0) on Local\\file-portal-card, as convert_and_ship.py takes it; held for the process."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = k32.CreateMutexW(None, False, "Local\\file-portal-card")
    res = k32.WaitForSingleObject(handle, 0)
    if res == 0x102:
        return None
    return handle


def measure(text, is_loop):
    words = text.split()
    c = Counter(w.lower() for w in words)
    top = c.most_common(1)[0] if c else ("", 0)
    return {"chars": len(text), "words": len(words), "top_word": top[0], "top_count": top[1], "is_loop": bool(is_loop(text))}


def main(argv=None):
    a = parse_args(argv)
    if a.device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        os.environ["TORCH_DEVICE"] = "cpu"
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    bbox = [float(v) for v in a.bbox.split(",")]
    if len(bbox) != 4:
        print("UNREAD: --bbox needs four numbers")
        return 2
    try:
        import pypdfium2 as pdfium
        import torch
        from pdftext.pdf.utils import flatten as flatten_pdf_page
        from surya.common.surya.schema import TaskNames
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
        from surya.settings import settings as surya_settings
    except Exception as e:  # noqa: BLE001 — a missing model or package is UNREAD, never "absent"
        print("UNREAD: the converter's packages did not import (%s) — run under marker-env" % str(e)[:160])
        return 2
    sys.path.insert(0, HERE)
    import fixes  # noqa: E402

    if a.device == "cuda":
        if not torch.cuda.is_available():
            print("UNREAD: --device cuda but the card is not visible")
            return 2
        if take_card_mutex() is None:
            print("REFUSED: the card mutex Local\\file-portal-card is held — the line owns the card; run in a paused window")
            return 2
    elif torch.cuda.is_available():
        print("UNREAD: --device cpu but the card is still visible (CUDA_VISIBLE_DEVICES did not hide it)")
        return 2
    dtype = torch.float32 if (a.dtype or ("float32" if a.device == "cpu" else "bfloat16")) == "float32" else torch.bfloat16
    t0 = time.time()
    doc = pdfium.PdfDocument(a.pdf)
    if not 1 <= a.page <= len(doc):
        print("UNREAD: page %d is not in the PDF (%d pages)" % (a.page, len(doc)))
        return 2

    def render(dpi):
        pg = doc[a.page - 1]
        flatten_pdf_page(pg)
        pg = doc[a.page - 1]
        return pg.render(scale=dpi / 72, draw_annots=False).to_pil().convert("RGB"), pg.get_size()

    img96, (w_pt, h_pt) = render(96)
    img, _ = render(192)
    det = DetectionPredictor(device=a.device, dtype=torch.float32)
    good = [b for b in det([img96])[0].bboxes if (b.confidence or 0) > 0.8]
    sx, sy = img96.width / w_pt, img96.height / h_pt
    bx = [bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy]

    def inside(b):
        x0, y0, x1, y1 = b.bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return bx[0] <= cx <= bx[2] and bx[1] <= cy <= bx[3]

    k = img.width / img96.width
    lines = sorted([b for b in good if inside(b)], key=lambda b: (b.bbox[1], b.bbox[0]))
    polys = [[[int(max(0, min(pt[0] * k, img.width))), int(max(0, min(pt[1] * k, img.height)))] for pt in b.polygon] for b in lines]
    mode = "LINE" if len(polys) > 15 else "BLOCK"
    print("page %d · block %s pt · detector lines inside %d (> 15 → marker reads it in %s mode) · device %s · dtype %s · batch %d" % (
        a.page, bbox, len(polys), mode, a.device, str(dtype).replace("torch.", ""), a.batch), flush=True)
    if not polys:
        print("UNREAD: the detector found no line inside the block")
        return 2
    del det
    rec = RecognitionPredictor(FoundationPredictor(checkpoint=surya_settings.RECOGNITION_MODEL_CHECKPOINT, device=a.device, dtype=dtype))
    common = dict(recognition_batch_size=a.batch, sort_lines=False, math_mode=True, drop_repeated_text=False, max_sliding_window=2148, max_tokens=2048)
    t1 = time.time()
    res = rec(images=[img], task_names=[TaskNames.ocr_with_boxes], polygons=[polys], input_text=[[""] * len(polys)], **common)
    per = [(tl.text, measure(tl.text, fixes.is_loop)) for tl in res[0].text_lines]
    looping = [i + 1 for i, (_, m) in enumerate(per) if m["is_loop"]]
    print("line mode: %d lines · %.1f s · looping lines %s" % (len(per), time.time() - t1, looping or "none"), flush=True)
    for i, (tx, m) in enumerate(per, 1):
        print("  line %2d: %4d words · top %r x%d · %r%s" % (i, m["words"], m["top_word"], m["top_count"], tx[:70].replace("\n", " / "), "  <-- LOOP" if m["is_loop"] else ""), flush=True)
    control = None
    if a.control:
        t2 = time.time()
        sx2, sy2 = img.width / w_pt, img.height / h_pt
        poly = [[int(bbox[0] * sx2), int(bbox[1] * sy2)], [int(bbox[2] * sx2), int(bbox[1] * sy2)], [int(bbox[2] * sx2), int(bbox[3] * sy2)], [int(bbox[0] * sx2), int(bbox[3] * sy2)]]
        res2 = rec(images=[img], task_names=[TaskNames.ocr_with_boxes], polygons=[[poly]], input_text=[[""]], **common)
        control = measure(res2[0].text_lines[0].text, fixes.is_loop)
        print("control (the block whole, block mode): %.1f s · words %d · top %r x%d · is_loop %s" % (
            time.time() - t2, control["words"], control["top_word"], control["top_count"], control["is_loop"]), flush=True)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump({"pdf": a.pdf, "page": a.page, "bbox_pt": bbox, "device": a.device, "dtype": str(dtype), "batch": a.batch, "mode": mode,
                   "polys_192dpi": polys, "lines": [{"i": i + 1, "text": tx[:3000], **m} for i, (tx, m) in enumerate(per)], "looping": looping,
                   "control": control, "wall_s": round(time.time() - t0, 1)},
                  open(os.path.join(a.out, "tripwire_p%d.json" % a.page), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    present = a.line in looping
    others = [i for i in looping if i != a.line]
    if a.expect == "present":
        ok = present and not others and (control is None or not control["is_loop"])
        why = ("TRIPPED: line %d loops as the converter's output did" % a.line) if present else ("NOT TRIPPED: line %d did not loop" % a.line)
    else:
        if control is None:
            print("UNREAD: --expect absent needs --control (the content floor: an empty recognizer is not 'absent')")
            return 2
        line_words = sum(m["words"] for _, m in per)
        floor = 0.8 * control["words"]
        has_text = line_words >= floor
        ok = not looping and not control["is_loop"] and has_text
        why = ("ABSENT: no line loops · the lines carry %d words (floor %.0f of the control's %d)" % (line_words, floor, control["words"])) if not looping \
            else "PRESENT: lines %s loop" % looping
        if not has_text:
            why += " · the lines carry %d words, under the floor %.0f (the control's %d) — an empty read is not a remedy" % (line_words, floor, control["words"])
    if others:
        why += " · other looping lines %s (not expected)" % others
    if control is not None and control["is_loop"]:
        why += " · the CONTROL looped (the block whole) — the harness, not the slicing, is suspect"
    print("%s · expect %s · %s · %.1f s" % ("OK" if ok else "RED", a.expect, why, time.time() - t0), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
