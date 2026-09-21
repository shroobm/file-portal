# -*- coding: utf-8 -*-
"""ocr_dial_selftest.py — the tripwires for B33's dial (S209 E8, record-only). Run with the marker-env interpreter
(convert_and_ship imports pymupdf at module level); FP_PIPELINE is pointed at a temp dir BEFORE import so the ledger and
every root land in quarantine (SYM-010: never the live dirs). Cases: the bars accumulate by distinct total, a prefixed
stage counts, another stage does not; ocr_dial sums and divides by the pages it is given; estimate_from_ledger names its
heavy neighbours (> OCR_HEAVY_LINES_PER_PAGE) and STILL includes their pace (no exclusion — Rab's signature); a light
ledger names 0; a ledger without the key names 0 (an old row is not a heavy row). Prints `==== ocr_dial selftest: N/N ====`."""
import json
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="ocr-dial-selftest-")
os.environ["FP_PIPELINE"] = _TMP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_and_ship as cas  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + str(detail)[:160]) if (detail and not cond) else ""))


# 1 · the bars
cas._OCR_BARS.clear()
cas._note_ocr_bar("Recognizing Layout", 3)
cas._note_ocr_bar("Recognizing Text", 170)
cas._note_ocr_bar("Recognizing Text", 170)
cas._note_ocr_bar("slice 2/5 · Recognizing Text", 901)
cas._note_ocr_bar("Detecting bboxes", 12)
case("bars accumulate by distinct total, a prefixed stage counts, other stages do not", cas._OCR_BARS == [170, 901], cas._OCR_BARS)
d = cas.ocr_dial(178)
case("ocr_dial sums the bars and divides by the pages given", d["lines"] == 1071 and d["bars"] == [170, 901] and d["lines_per_page"] == 6.0, d)
cas._OCR_BARS.clear()
case("no bars → 0 lines, 0.0 per page (measured, not None) and an empty list", cas.ocr_dial(50) == {"lines": 0, "bars": [], "lines_per_page": 0.0}, cas.ocr_dial(50))
case("pages 0 → lines_per_page None (no base), never 0", cas.ocr_dial(0)["lines_per_page"] is None, cas.ocr_dial(0))

# 2 · the estimator names heavy neighbours and excludes none
rows = [
    {"lane": "clean", "chars_per_page": 3000, "s_per_page": 12.8, "ocr_lines_per_page": 132.0},   # RBC's shape (chars set so it is a nearest-3 neighbour of 2860)
    {"lane": "clean", "chars_per_page": 4300, "s_per_page": 11.27, "ocr_lines_per_page": 64.0},   # C-31's shape
    {"lane": "clean", "chars_per_page": 4899, "s_per_page": 1.92, "ocr_lines_per_page": 0.0},     # CIBC's shape
    {"lane": "clean", "chars_per_page": 1300, "s_per_page": 1.51},                                 # an old row, no key
    {"lane": "scan", "chars_per_page": 900, "s_per_page": 5.4, "ocr_lines_per_page": 40.0},       # another lane
]
cas.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
cas.LEDGER_FILE.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
est = cas.estimate_from_ledger(178, "clean", 2860)
case("three clean neighbours: two heavy named, the median STILL carries their pace (no exclusion)",
     est is not None and est["ocr_heavy_neighbours"] == 2 and est["samples"] == 3 and est["s_per_page"] == 11.27, est)
cas.LEDGER_FILE.write_text("".join(json.dumps(r) + "\n" for r in rows[2:4]), encoding="utf-8")
est2 = cas.estimate_from_ledger(178, "clean", 2860)
case("a light ledger (CIBC, an old row without the key) names 0 heavy", est2 is not None and est2["ocr_heavy_neighbours"] == 0 and est2["samples"] == 2, est2)
# S211 (S210 CORRECTIONS row 11): the dial reaches the LEDGER ROW from the manifest's own `ocr_dial` key — from 2026-09-20
# to S211 the lane's boolean rebound `ocr`, the manifest carried False and every row read None. The record is filed on the
# temp ledger (FP_PIPELINE) and read back; the negative control is a manifest with only the boolean.
cas.LEDGER_FILE.write_text("", encoding="utf-8")
_m = {"source": "dial.pdf", "source_sha256": "d" * 64, "pages": 10, "lane": "clean", "engine": "marker", "chars_per_page": 3000,
      "ocr": False, "ocr_dial": {"lines": 1320, "bars": [1320], "lines_per_page": 132.0}}
cas._ledger_record(_m, 128.0, 8000)
_row = json.loads(cas.LEDGER_FILE.read_text(encoding="utf-8").strip().splitlines()[-1])
case("the manifest's ocr_dial reaches the ledger row: ocr_lines 1320, 132.0 per page (S210 row 11's fix)",
     _row.get("ocr_lines") == 1320 and _row.get("ocr_lines_per_page") == 132.0, _row)
cas.LEDGER_FILE.write_text("", encoding="utf-8")
_m2 = dict(_m)
del _m2["ocr_dial"]
cas._ledger_record(_m2, 128.0, 8000)
_row2 = json.loads(cas.LEDGER_FILE.read_text(encoding="utf-8").strip().splitlines()[-1])
case("NEGATIVE CONTROL: a manifest with only the boolean `ocr` reads ocr_lines None (the defect's shape), never a number",
     _row2.get("ocr_lines") is None and _row2.get("ocr_lines_per_page") is None, _row2)
print("==== ocr_dial selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
