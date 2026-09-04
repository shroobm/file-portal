import os, re, json, pymupdf
DONE = r"C:/Users/Bndit/ml/library/drop/done"
_OCR_FONT = re.compile(r"glyphless|invisible|ocr", re.IGNORECASE)   # convert_and_ship.py:744 verbatim
MIN_CHARS_PER_PAGE = 100
print("pymupdf", pymupdf.__version__)
rows = []
for fname in sorted(os.listdir(DONE)):
    if not fname.lower().endswith(".pdf"): continue
    doc = pymupdf.open(os.path.join(DONE, fname))
    inv = tot = chars = 0; trig = None; modes = {}
    for page in doc:
        chars += len(page.get_text())
        for span in page.get_texttrace():
            tot += 1; t = span.get("type"); modes[t] = modes.get(t, 0) + 1
            if t == 3: inv += 1
            if trig is None and _OCR_FONT.search(str(span.get("font",""))): trig = str(span.get("font",""))[:60]
    ratio = inv/tot if tot else 0.0
    cpp = chars/(doc.page_count or 1)
    ocr_layer = trig is not None or (tot > 0 and ratio > 0.5)
    if cpp >= MIN_CHARS_PER_PAGE and ocr_layer: lane, why = "scan", "untrusted_ocr_layer"
    elif cpp >= MIN_CHARS_PER_PAGE: lane, why = "clean", "text_layer_present"
    else: lane, why = "scan", "no_text_layer"
    rows.append(dict(file=fname[:60], pages=doc.page_count, spans=tot, modes=modes, inv=inv, ratio=round(ratio,4),
                     chars_pp=round(cpp,2), font_trigger=trig, lane=lane, reason=why, producer=doc.metadata.get("producer",""), creator=doc.metadata.get("creator","")))
    doc.close()
for r in rows: print(json.dumps(r, ensure_ascii=False))
# Lane E probes
p = pymupdf.open(os.path.join(DONE, "Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Fourth Edition, 2023 -- Wiley & Sons, Incorporated, John.pdf"))
tr = p[10].get_texttrace(); m={}
for s in tr: m[s.get("type")] = m.get(s.get("type"),0)+1
print("LANE-E Damodaran p10 spans:", len(tr), "modes:", m, "StructTreeRoot:", p.xref_get_key(p.pdf_catalog(), "StructTreeRoot"), "producer:", p.metadata.get("producer"))
b = pymupdf.open(os.path.join(DONE, "BRAIN OF THE FIRM STAFFORD BEER (WITH OCR) ISBN 13 9780471162131.pdf"))
found = {}
for i in range(0, 12):
    tr = b[i].get_texttrace(); m = {}
    for s in tr: m[s.get("type")] = m.get(s.get("type"),0)+1
    found[i] = m
    rd = b[i].get_text("rawdict"); flags = set()
    for bl in rd["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln.get("spans", []): flags.add(sp.get("flags"))
    found[i]["rawdict_flags"] = sorted(flags)
print("LANE-E/C Beer pages 0-11 texttrace modes + rawdict flags:", json.dumps(found))
for pg in (30, 50, 100, 150):
    rd = b[pg].get_text("rawdict"); flags=set()
    for bl in rd["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln.get("spans", []): flags.add(sp.get("flags"))
    print("Beer rawdict flags page", pg, sorted(flags))
