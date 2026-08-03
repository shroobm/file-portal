#!/usr/bin/env python
"""Acceptance harness for the Repair Bench (Stage G, docs/19 §7).

Drives the REAL `Bench` class over a SANDBOX copy of the REAL held Valentine bundle — real
zones, real source-PDF rasters, real provenance stamps — then one live HTTP round through the
same handler the browser uses. The REAL held bundle must come out byte-identical (hash-proven).

Run with the marker-env python (pymupdf + fidelity_audit's deps live there). Exit 0 = pass.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench as B  # noqa: E402

HELD_VAL = Path(r"C:\Users\Bndit\ml\library\held\b6fbdd75f6242f53")
PORT = 7078
# a valid 1×1 PNG — the smallest honest "screenshot"
TINY_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
                "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

results: list[tuple[str, bool]] = []


def check(name: str, cond: bool) -> None:
    results.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name, flush=True)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    md_real = next(p for p in HELD_VAL.iterdir() if p.suffix == ".md")
    before = {p.name: sha(p) for p in (md_real, HELD_VAL / "manifest.json")}

    # ---- 1. sandbox isolation ---------------------------------------------------------------
    bench = B.Bench(HELD_VAL, sandbox=True)
    check("sandbox lives under .sandbox/, not the held bundle",
          bench.dir != HELD_VAL and ".sandbox" in str(bench.dir))

    # ---- 2. state reads the real audit evidence ---------------------------------------------
    st = bench.state()
    check("all four of Valentine's zones on the bench", len(st["zones"]) == 4)
    check("verdict fail carried through", st["verdict"] == "fail")
    check("465 pages from the manifest", st["pages"] == 465)
    check("the real source PDF was found in drop/done/", st["pdf_available"])
    check("page guesses land inside the book",
          all(1 <= z["page_guess"] <= 465 for z in st["zones"]))
    check("no repairs yet → adjusted == original for every zone",
          all(z["adjusted_line"] == z["line"] for z in st["zones"]))

    # ---- 3. real raster ---------------------------------------------------------------------
    g = st["zones"][0]["page_guess"]
    png = bench.page_png(g)
    check(f"page {g} rasters to a real PNG", png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 4000)

    # ---- 4. the crop repair (zone @1579, the 9.5k-char table wreck) -------------------------
    z1 = next(z for z in st["zones"] if z["line"] == 1579)
    r1 = bench.repair(zone_line=1579, page=z1["page_guess"], rect=[0.08, 0.1, 0.92, 0.6],
                      note="acceptance: table wreck")
    body = bench.body().split("\n")
    check("crop asset exists with the collision-safe name",
          (bench.assets / r1["asset"]).is_file() and r1["asset"].startswith("_repair_p"))
    check("embed inserted immediately after the zone line",
          body[r1["inserted_after_line"] + 1] == f"![[assets/{r1['asset']}]]")
    reps = bench.manifest["repairs"]
    check("provenance stamped (zone, page, mode, by, ts)",
          reps[0]["zone_line"] == 1579 and reps[0]["mode"] == "crop"
          and reps[0]["by"] == "repair-bench" and "T" in reps[0]["ts"])

    # ---- 5. offset arithmetic under a SECOND repair at an EARLIER zone ----------------------
    z2 = next(z for z in bench.state()["zones"] if z["line"] == 619)
    check("zone below the first repair did not shift", z2["adjusted_line"] == 619)
    r2 = bench.repair(zone_line=619, page=z2["page_guess"], rect=[0.1, 0.2, 0.9, 0.7],
                      note="acceptance: earlier zone")
    st2 = bench.state()
    z1_after = next(z for z in st2["zones"] if z["line"] == 1579)
    check("later zone shifted by exactly the 3 inserted lines",
          z1_after["adjusted_line"] == 1579 + 3)
    body2 = bench.body()
    check("both embeds present in the body", body2.count("![[assets/_repair_p") == 2)
    check("zone chips know they are repaired",
          sum(1 for z in st2["zones"] if z["repaired"]) == 2)

    # ---- 6. the paste gesture ---------------------------------------------------------------
    r3 = bench.repair(zone_line=1715, page=130, image_b64=TINY_PNG_B64, note="pasted")
    check("pasted PNG accepted and stored", (bench.assets / r3["asset"]).is_file()
          and bench.manifest["repairs"][-1]["mode"] == "paste")
    try:
        bench.repair(zone_line=1715, page=130, image_b64=base64.b64encode(b"not a png").decode())
        check("non-PNG paste refused", False)
    except ValueError:
        check("non-PNG paste refused", True)

    # ---- 7. the re-score PREVIEW (runs the real fidelity_audit.degeneration) ---------------
    rs = bench.rescore_preview()
    check("re-score is explicitly a preview", rs["preview"] is True and "unsigned" in rs["note"])
    check("preview counts repairs against the original zones",
          rs["original_zones"] == 4 and rs["zones_with_repairs"] == 3 and rs["repairs"] == 3)
    check("degeneration re-ran on the CURRENT text",
          isinstance(rs["degeneration_now"]["flagged"], bool))

    # ---- 8. one live HTTP round through the real handler ------------------------------------
    server = ThreadingHTTPServer(("127.0.0.1", PORT), B.make_handler(bench))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    get = lambda p: urllib.request.urlopen(f"http://127.0.0.1:{PORT}{p}", timeout=15)  # noqa: E731
    check("GET / serves the bench UI", b"Repair Bench" in get("/").read())
    check("GET /api/state over the wire agrees",
          json.loads(get("/api/state").read())["sandbox"] is True)
    check("GET /api/page streams a PNG", get("/api/page?n=5").read()[:8] == b"\x89PNG\r\n\x1a\n")
    bad = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/repair",
                                 data=json.dumps({"zone_line": 1, "page": 1}).encode())
    try:
        urllib.request.urlopen(bad, timeout=15)
        check("invalid repair reports an error, never guesses", False)
    except urllib.error.HTTPError as e:
        check("invalid repair reports an error, never guesses",
              e.code == 500 and b"error" in e.read())
    server.shutdown()

    # ---- 9. the REAL held bundle is byte-identical ------------------------------------------
    after = {p.name: sha(p) for p in (md_real, HELD_VAL / "manifest.json")}
    check("REAL held Valentine untouched (md + manifest hashes)", before == after)
    check("sandbox kept a .bench-bak of the md",
          bench.md_path.with_suffix(".md.bench-bak").is_file())

    failed = [n for n, ok in results if not ok]
    print(f"\n{'PASS' if not failed else 'FAIL'} — {len(results) - len(failed)}/{len(results)} checks"
          + (f"; failed: {failed}" if failed else ""), flush=True)
    print(f"sandbox kept for inspection: {bench.dir}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
