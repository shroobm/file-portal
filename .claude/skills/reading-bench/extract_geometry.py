"""extract_geometry.py <bundle_dir> <out.json> [--pages 161,31,…] [--pdf <source.pdf>] [--render <dpi>] — step 1.

Reads a bundle's blocks.json (J24's per-block records) and manifest.json, read-only, and writes a compact dataset for the
page: a handful of pages with every block's id/type/bbox/polygon/hierarchy and a text snippet, the page boxes, the
block-type census, the timing, the manifest's fidelity and analyst numbers. Nothing is invented: a missing number stays
missing and the page renders it UNREAD. Refuses a blocks.json whose records carry no polygon (that is not J24's shape).

--pdf <path> (S129, Rab: "embed the real pages underneath … as an overlay"): render each chosen page from the SOURCE PDF
with PyMuPDF at --render dpi (default 96) and carry it as a PNG data URI, with the dpi, the PDF page index used
(the block's corrected `page` is the 0-based PDF index) and the PDF's own page rect, checked against the block page box.
A bundle ships figure crops, not page renders — the render can only come from the PDF, and the page says so. Without
--pdf, or if the PDF or PyMuPDF is absent, pages carry no image and the bench draws geometry alone. Exit 1 on refusal.
"""
import base64
import collections
import io
import json
import re
import sys


def render_pages(pdf_path, page_indexes, dpi):
    """Render the given 0-based pages to PNG data URIs. Returns {index: {...}} or {} with a reason when it cannot."""
    try:
        import fitz  # PyMuPDF (the marker-env has it; the fidelity witness is pymupdf)
    except ImportError:
        return {}, "PyMuPDF not importable in this interpreter"
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:  # noqa: BLE001 — the reason is reported, never rendered as an image
        return {}, f"could not open {pdf_path}: {e}"
    out = {}
    zoom = dpi / 72.0
    for p in page_indexes:
        if p < 0 or p >= doc.page_count:
            out[p] = {"error": f"PDF has {doc.page_count} pages; index {p} is out of range"}
            continue
        page = doc[p]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        out[p] = {
            "data_uri": "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii"),
            "dpi": dpi, "px": [pix.width, pix.height], "pdf_page_index": p,
            "pdf_rect": [round(page.rect.width, 1), round(page.rect.height, 1)],
        }
    return out, None


def snippet(html, n=160):
    t = re.sub(r"<[^>]+>", " ", html or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] + ("…" if len(t) > n else "")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    bundle, out = sys.argv[1].rstrip("/\\"), sys.argv[2]
    want = None
    if "--pages" in sys.argv:
        want = [int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",") if x.strip()]
    pdf = sys.argv[sys.argv.index("--pdf") + 1] if "--pdf" in sys.argv else None
    dpi = int(sys.argv[sys.argv.index("--render") + 1]) if "--render" in sys.argv else 96
    try:
        d = json.load(io.open(bundle + "/blocks.json", encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"REFUSED: {bundle}/blocks.json unreadable ({e})")
        sys.exit(1)
    recs = d.get("blocks") if isinstance(d, dict) else None
    if not isinstance(recs, list) or not recs or "polygon" not in recs[0] or "bbox" not in recs[0]:
        print("REFUSED: blocks.json is not J24's shape (no blocks list with polygon + bbox records)")
        sys.exit(1)
    by_page = collections.defaultdict(list)
    for r in recs:
        by_page[r.get("page")].append(r)

    def first_page_with(kind, exclude):
        for p in sorted(k for k in by_page if k is not None):
            if p in exclude:
                continue
            if any(r.get("block_type") == kind for r in by_page[p]):
                return p
        return None

    if want:
        chosen = [p for p in want if p in by_page]
    else:
        chosen = []
        for kind in ("Table", "FigureGroup", "Code", "TableOfContents", "ListGroup"):
            p = first_page_with(kind, chosen)
            if p is not None:
                chosen.append(p)
        for p in sorted(k for k in by_page if k is not None):
            if p in chosen:
                continue
            kinds = {r.get("block_type") for r in by_page[p]}
            if "SectionHeader" in kinds and "PageFooter" in kinds and "Text" in kinds and len(by_page[p]) >= 5:
                chosen.append(p)
                break
        if not chosen:
            chosen = sorted(k for k in by_page if k is not None)[:3]

    page_info = d.get("page_info") or {}
    pages = []
    for p in chosen:
        info = page_info.get(str(p), {})
        blocks = []
        for r in by_page[p]:
            blocks.append({
                "id": r.get("id"), "type": r.get("block_type"), "bbox": [round(float(x), 1) for x in r["bbox"]],
                "polygon": [[round(float(x), 1), round(float(y), 1)] for x, y in r["polygon"]],
                "hier": r.get("section_hierarchy") or {}, "text": snippet(r.get("html", "")),
                "page_raw": r.get("page_field_raw"),
            })
        pages.append({"page": p, "box": info.get("bbox"), "blocks": blocks})

    hdr_text = {}
    by_id = {r.get("id"): r for r in recs}
    for pg in pages:
        for b in pg["blocks"]:
            for hid in b["hier"].values():
                if hid not in hdr_text:
                    h = by_id.get(hid)
                    hdr_text[hid] = snippet(h.get("html", ""), 80) if h else "(header not in the block list)"

    render_meta = {"pdf": pdf, "dpi": dpi if pdf else None, "reason": None if pdf else "no --pdf given: geometry alone"}
    if pdf:
        imgs, why = render_pages(pdf, [pg["page"] for pg in pages], dpi)
        render_meta["reason"] = why
        for pg in pages:
            im = imgs.get(pg["page"])
            if im and "data_uri" in im:
                box = pg.get("box") or [0, 0, 0, 0]
                im["box_matches_pdf"] = abs((box[2] - box[0]) - im["pdf_rect"][0]) < 1.0 and abs((box[3] - box[1]) - im["pdf_rect"][1]) < 1.0
                pg["image"] = im
            elif im:
                pg["image_error"] = im.get("error")

    census = collections.Counter(r.get("block_type") for r in recs).most_common()
    try:
        manifest = json.load(io.open(bundle + "/manifest.json", encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    data = {
        "render": render_meta,
        "book": manifest.get("source") or bundle.rsplit("/", 1)[-1],
        "bundle": bundle,
        "pages": pages, "headers": hdr_text, "census": census,
        "totals": {"blocks": d.get("blocks_total", len(recs)), "pages": d.get("pages_with_blocks", len(by_page)),
                   "page_min": d.get("page_min"), "page_max": d.get("page_max"),
                   "page_raw_disagreements": d.get("page_field_raw_disagreements")},
        "timing_s": d.get("timing_s"),
        "manifest": {k: manifest.get(k) for k in ("source", "source_sha256", "lane", "pages", "engine") if k in manifest},
        "fidelity": manifest.get("fidelity") or {}, "analyst": manifest.get("analyst") or {},
    }
    io.open(out, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
    print(f"pages chosen: {chosen} · blocks on them: {sum(len(p['blocks']) for p in pages)} · "
          f"census kinds: {len(census)} · fidelity keys: {sorted(data['fidelity'].keys())} · {out}")


if __name__ == "__main__":
    main()
