# -*- coding: utf-8 -*-
"""blank_assets_selftest.py — the tripwires of blank_assets.py (SYM-053, S188 E7): a white JPEG the size of the S108 specimen
reads blank and REFERENCED when the body names it (the positive control — the page that looks covered); a gradient PNG
does not read blank; a near-blank crop (std ≈ 0.5) reads blank under the lever and NOT under a lowered one — the NEGATIVE
CONTROL that shows the flag is the lever's, not a constant's; a corrupt .jpeg reads UNREAD and is never counted blank;
an unreferenced blank is blank but not referenced; no assets/ dir reads zero assets with every key present; the counts
carry NUM-3's cap beside the total; the CLI exits 1 on a bundle with a referenced blank, 0 on a clean one, 2 on usage.
Run with the marker-env interpreter (PIL). Exit 0 all fired · 1 any silent."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blank_assets as ba  # noqa: E402

try:
    from PIL import Image
except Exception as exc:  # noqa: BLE001
    print("UNREAD: PIL is not importable in this interpreter (%s) — run under marker-env" % type(exc).__name__)
    sys.exit(1)

fired, silent = 0, 0


def check(cond, label):
    global fired, silent
    print(("  ok    " if cond else "  RED   ") + label)
    if cond:
        fired += 1
    else:
        silent += 1


def _write(path, img):
    img.save(path)


with tempfile.TemporaryDirectory() as td:
    assets = os.path.join(td, "assets")
    os.makedirs(assets)
    # the S108 specimen's shape: 511x70 flat paper (240)
    _write(os.path.join(assets, "_page_128_Picture_15.jpeg"), Image.new("L", (511, 70), 240))
    # a real crop: a horizontal gradient 0..255
    grad = Image.new("L", (256, 40))
    grad.putdata([x % 256 for y in range(40) for x in range(256)])
    _write(os.path.join(assets, "_page_3_Figure_1.png"), grad)
    # a near-blank: paper (250) with ONE pixel at 200 on 100x100 -> sd = sqrt(1e-4) * 50 = 0.5 (the first draft's 2x2 dot at
    # 0 read sd 5 — four black pixels on paper are a real mark, and the lever rightly refused them)
    near = Image.new("L", (100, 100), 250)
    near.putpixel((50, 50), 200)
    _write(os.path.join(assets, "_page_9_Picture_2.png"), near)
    # an unreferenced blank
    _write(os.path.join(assets, "_page_1_Picture_0.jpeg"), Image.new("L", (474, 824), 255))
    # a corrupt "jpeg"
    with open(os.path.join(assets, "_page_5_Picture_9.jpeg"), "wb") as f:
        f.write(b"not an image at all")
    body = "text\n\n![](assets/_page_128_Picture_15.jpeg)\n\n![](assets/_page_3_Figure_1.png)\n\n![](assets/_page_9_Picture_2.png)\n"

    print("blank_assets — SYM-053's tripwire")
    r = ba.scan(assets, body)
    names = {b["name"]: b for b in r["blank"]}
    check(r["assets"] == 5 and r["read"] == 4 and r["unread_total"] == 1 and r["unread"][0]["name"] == "_page_5_Picture_9.jpeg",
          "(a) five files: four read, the corrupt one UNREAD by name — never counted blank")
    s = names.get("_page_128_Picture_15.jpeg")
    check(s is not None and s["referenced"] is True and s["width"] == 511 and s["height"] == 70 and s["extrema"] == [240, 240] and s["sd"] == 0.0,
          "(b) POSITIVE: the S108 specimen's shape (511x70 flat paper) reads blank, sd 0.00, extrema 240/240, REFERENCED by the body")
    check("_page_3_Figure_1.png" not in names,
          "(c) a real crop (a gradient) does not read blank")
    check("_page_9_Picture_2.png" in names and 0.0 < names["_page_9_Picture_2.png"]["sd"] < ba.BLANK_SD,
          "(d) a near-blank crop (paper with one dark dot, sd %s) reads blank under the lever" % (names.get("_page_9_Picture_2.png") or {}).get("sd"))
    r_low = ba.scan(assets, body, blank_sd=0.1)
    low_names = {b["name"] for b in r_low["blank"]}
    check("_page_9_Picture_2.png" not in low_names and "_page_128_Picture_15.jpeg" in low_names,
          "(e) NEGATIVE CONTROL: with the lever at 0.1 the near-blank is NOT blank and the flat specimen still is — the flag is the lever's")
    u = names.get("_page_1_Picture_0.jpeg")
    check(u is not None and u["referenced"] is False and r["blank_total"] == 3 and r["blank_referenced"] == 2,
          "(f) an unreferenced blank is blank, not referenced: blank_total 3, blank_referenced 2")
    check(r["blank_shown_cap"] == ba.BLANK_SHOWN_CAP and len(r["blank"]) <= r["blank_shown_cap"] and r["blank_sd"] == ba.BLANK_SD and r["mode"] == "flag",
          "(g) NUM-3: the shown list carries its cap beside the total; the lever's value and the mode travel in the record")
    r_none = ba.scan(os.path.join(td, "no-such-assets"), body)
    check(r_none["assets"] == 0 and r_none["blank_total"] == 0 and r_none["blank_referenced"] == 0 and set(r_none) == set(r),
          "(h) no assets/ dir: zero assets, every key present (the record's shape never depends on the count)")
    # the CLI: a bundle dir with the body and the assets
    with open(os.path.join(td, "book.md"), "w", encoding="utf-8") as f:
        f.write(body)
    py = sys.executable
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blank_assets.py")
    p1 = subprocess.run([py, here, td], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(p1.returncode == 1 and "referenced=2" in p1.stdout and "_page_128_Picture_15.jpeg" in p1.stdout,
          "(i) CLI: a bundle with a referenced blank exits 1 and names it (rc %s)" % p1.returncode)
    clean = os.path.join(td, "clean")
    os.makedirs(os.path.join(clean, "assets"))
    _write(os.path.join(clean, "assets", "_page_2_Figure_0.png"), grad)
    with open(os.path.join(clean, "book.md"), "w", encoding="utf-8") as f:
        f.write("![](assets/_page_2_Figure_0.png)\n")
    p0 = subprocess.run([py, here, clean], capture_output=True, text=True, encoding="utf-8", errors="replace")
    p2 = subprocess.run([py, here], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(p0.returncode == 0 and "blank=0" in p0.stdout and p2.returncode == 2,
          "(j) CLI: a clean bundle exits 0 (blank=0); usage exits 2")

print("%s (%d/%d)" % ("GREEN" if not silent else "RED", fired, fired + silent))
sys.exit(1 if silent else 0)
