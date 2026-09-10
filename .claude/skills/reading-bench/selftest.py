"""selftest.py — the Reading Bench's tripwire. Builds a SYNTHETIC bundle (two pages of J24-shaped blocks, a page_info, a
manifest with fidelity + analyst numbers), runs extract_geometry.py → build_page.py, and asserts the mechanical half:
the chosen pages, the block count inlined, the census, the dials' source numbers present verbatim in the page's data,
the <title>. Negative controls: a blocks.json without polygons is REFUSED (exit 1); a manifest without fidelity yields an
empty fidelity object so the page renders UNREAD (the page's UNREAD branch is asserted present in the source). Case 0 is
the positive control. Exit 1 on any red. It checks the scripts, not the rendered DOM — the look is a human's.

Run:  python .claude/skills/reading-bench/selftest.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


ENV = dict(os.environ, PYTHONIOENCODING="utf-8")  # the children print non-ASCII; a cp1252 console must not turn that into a crash


def run(args):
    return subprocess.run([PY] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)


def block(page, kind, x0, y0, x1, y1, n, hier=None, html="<p>words on the page</p>"):
    return {"id": f"/page/{page}/{kind}/{n}", "block_type": kind, "html": html, "page": page, "page_field_raw": page + 17,
            "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "bbox": [x0, y0, x1, y1],
            "section_hierarchy": hier or {}, "image_refs": []}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="reading-bench-")
    results = []

    def case(name, ok, extra=""):
        results.append(ok)
        print(f"  [{len(results)-1:>2}] {'ok ' if ok else 'RED'} {name} {extra}")

    try:
        bundle = os.path.join(tmp, "bundle")
        os.makedirs(bundle)
        blocks = [
            block(0, "SectionHeader", 76.3, 58.5, 131.4, 65.6, 0),
            block(0, "Table", 73.3, 71.3, 430.7, 186.0, 1, {"1": "/page/0/SectionHeader/0"}, "<table><tr><th>k</th></tr></table>"),
            block(0, "Text", 73.3, 200.0, 430.7, 600.0, 2, {"1": "/page/0/SectionHeader/0"}),
            block(0, "PageFooter", 73.3, 640.0, 430.7, 650.0, 3),
            block(1, "FigureGroup", 80.0, 80.0, 420.0, 300.0, 0),
            block(1, "Caption", 80.0, 305.0, 420.0, 320.0, 1),
            block(1, "Text", 80.0, 340.0, 420.0, 620.0, 2),
        ]
        bj = {"schema": 1, "blocks": blocks, "page_info": {"0": {"bbox": [0, 0, 504, 662]}, "1": {"bbox": [0, 0, 504, 662]}},
              "blocks_total": len(blocks), "pages_with_blocks": 2, "page_min": 0, "page_max": 1, "page_field_raw_disagreements": 7,
              "timing_s": {"build_document": 12.5, "pages": 2}}
        io.open(os.path.join(bundle, "blocks.json"), "w", encoding="utf-8").write(json.dumps(bj))
        manifest = {"source": "Synthetic Book.pdf", "source_sha256": "ab" * 32, "lane": "clean", "pages": 2, "engine": "marker",
                    "fidelity": {"version": 1, "verdict": "flag", "convert": {"witness": "pymupdf", "doc_survival": 0.9123, "pages_scored": 2, "pages_flagged": [1]}},
                    "analyst": {"model": "qwen3:8b", "chunks_generated": 5, "chunks_passed": 4, "chunks_rejected": 1,
                                "rejections": {"fence": 1, "survival": 0, "think_leak": 0, "inflation": 0}, "duration_s": 60.0, "goodput_accepted_tok_s": 12.34}}
        io.open(os.path.join(bundle, "manifest.json"), "w", encoding="utf-8").write(json.dumps(manifest))

        out_json = os.path.join(tmp, "geometry.json")
        out_html = os.path.join(tmp, "bench.html")
        p = run([os.path.join(HERE, "extract_geometry.py"), bundle, out_json])
        case("positive control: extract runs on a J24-shaped bundle", p.returncode == 0, p.stdout.strip()[-80:])
        d = json.load(io.open(out_json, encoding="utf-8")) if p.returncode == 0 else {}
        case("the Table page and the FigureGroup page are chosen", sorted(pg["page"] for pg in d.get("pages", [])) == [0, 1], str([pg["page"] for pg in d.get("pages", [])]))
        case("every block on the chosen pages is carried (7)", sum(len(pg["blocks"]) for pg in d.get("pages", [])) == 7)
        case("the census counts the whole book (Text 2)", dict(d.get("census", [])).get("Text") == 2, str(d.get("census")))
        case("the header text for the hierarchy id is resolved", "words on the page" in json.dumps(d.get("headers", {})))
        case("the fidelity numbers are carried verbatim (0.9123)", (d.get("fidelity", {}).get("convert") or {}).get("doc_survival") == 0.9123)
        case("the page box is carried (504 × 662)", d.get("pages", [{}])[0].get("box") == [0, 0, 504, 662])
        p2 = run([os.path.join(HERE, "build_page.py"), out_json, out_html])
        case("build_page writes the page", p2.returncode == 0 and os.path.exists(out_html), p2.stdout.strip()[-60:])
        html = io.open(out_html, encoding="utf-8").read() if os.path.exists(out_html) else ""
        case("the page is named The Reading Bench", "<title>The Reading Bench</title>" in html)
        case("the data is inlined (the synthetic book's name and a block id)", "Synthetic Book.pdf" in html and "/page/0/Table/1" in html)
        case("the UNREAD branch exists for a missing dial", "'UNREAD'" in html)
        case("no </script> inside the inlined data (escaped)", html.count("</script>") == 2)
        # negative: a blocks.json without polygons is refused
        bad = os.path.join(tmp, "bad")
        os.makedirs(bad)
        io.open(os.path.join(bad, "blocks.json"), "w", encoding="utf-8").write(json.dumps({"blocks": [{"id": "x", "block_type": "Text", "page": 0}]}))
        p3 = run([os.path.join(HERE, "extract_geometry.py"), bad, os.path.join(tmp, "bad.json")])
        case("NEGATIVE: a blocks.json without polygon/bbox is REFUSED (exit 1)", p3.returncode == 1 and "REFUSED" in p3.stdout)
        # negative: no manifest → empty fidelity, still builds (the page renders UNREAD)
        nom = os.path.join(tmp, "nomanifest")
        os.makedirs(nom)
        io.open(os.path.join(nom, "blocks.json"), "w", encoding="utf-8").write(json.dumps(bj))
        p4 = run([os.path.join(HERE, "extract_geometry.py"), nom, os.path.join(tmp, "nom.json")])
        d4 = json.load(io.open(os.path.join(tmp, "nom.json"), encoding="utf-8")) if p4.returncode == 0 else {"fidelity": "x"}
        case("NEGATIVE: no manifest → fidelity is EMPTY (the page will read UNREAD), never invented", p4.returncode == 0 and d4.get("fidelity") == {})
        # --pages selection
        p5 = run([os.path.join(HERE, "extract_geometry.py"), bundle, os.path.join(tmp, "sel.json"), "--pages", "1"])
        d5 = json.load(io.open(os.path.join(tmp, "sel.json"), encoding="utf-8")) if p5.returncode == 0 else {}
        case("--pages selects exactly the named page", [pg["page"] for pg in d5.get("pages", [])] == [1])
        # the page render layer (S129): without --pdf no image; with a synthetic PDF, each chosen page carries a PNG data URI
        case("no --pdf → no page image and the reason is named", not any("image" in pg for pg in d.get("pages", [])) and "geometry alone" in str(d.get("render", {}).get("reason")))
        html_noimg = html
        case("no --pdf → the page says UNREAD for the render, not a blank", "No page render" in html_noimg)
        try:
            import fitz  # PyMuPDF
            pdf = os.path.join(tmp, "synthetic.pdf")
            doc = fitz.open()
            for i in range(2):
                pg = doc.new_page(width=504, height=662)
                pg.insert_text((73, 80), f"synthetic page {i}", fontsize=14)
            doc.save(pdf)
            p6 = run([os.path.join(HERE, "extract_geometry.py"), bundle, os.path.join(tmp, "ren.json"), "--pdf", pdf, "--render", "40"])
            d6 = json.load(io.open(os.path.join(tmp, "ren.json"), encoding="utf-8")) if p6.returncode == 0 else {}
            imgs = [pg.get("image") for pg in d6.get("pages", [])]
            case("--pdf → every chosen page carries a PNG data URI at the asked dpi", all(i and i.get("data_uri", "").startswith("data:image/png;base64,") and i.get("dpi") == 40 for i in imgs) and len(imgs) == 2)
            case("--pdf → the PDF's page rect is checked against the block page box (504 × 662 matches)", all(i and i.get("box_matches_pdf") is True for i in imgs))
            p7 = run([os.path.join(HERE, "build_page.py"), os.path.join(tmp, "ren.json"), os.path.join(tmp, "ren.html")])
            html_img = io.open(os.path.join(tmp, "ren.html"), encoding="utf-8").read() if p7.returncode == 0 else ""
            case("--pdf → the page inlines the render and names its source", "data:image/png;base64," in html_img and "synthetic.pdf" in html_img)
            p8 = run([os.path.join(HERE, "extract_geometry.py"), bundle, os.path.join(tmp, "nopdf.json"), "--pdf", os.path.join(tmp, "missing.pdf")])
            d8 = json.load(io.open(os.path.join(tmp, "nopdf.json"), encoding="utf-8")) if p8.returncode == 0 else {}
            case("NEGATIVE: a missing PDF → no image, the reason carried, the build still succeeds", p8.returncode == 0 and not any("image" in pg for pg in d8.get("pages", [])) and "could not open" in str(d8.get("render", {}).get("reason")))
        except ImportError:
            print("  [ -- ] SKIP the render cases: PyMuPDF is not importable in this interpreter (run under the marker-env) — UNREAD, not green")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_ok = sum(results)
    print(f"reading-bench selftest: {n_ok}/{len(results)} green" + ("" if n_ok == len(results) else "  *** RED ***"))
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
