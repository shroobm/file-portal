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
# Port 0 = the OS assigns a genuinely free one. A hardcoded port once landed the harness on
# Rab's LIVE bench via Windows SO_REUSEADDR (2026-08-06 — his server answered sandbox=False;
# his fail-closed /api/repair refused the probe, but the lesson stands: never share a port).
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
    # BASELINE-AWARE (S65): the real Valentine is a LIVE patient — Rab's own repairs may
    # already be in her manifest (the first landed 2026-08-06, p234, his hands). The harness
    # measures RELATIVE to what it copied, never assuming a virgin bundle.
    base_reps = json.loads((HELD_VAL / "manifest.json").read_text(encoding="utf-8")) \
        .get("repairs", [])

    def base_shift(line: int) -> int:
        return sum(3 for r in base_reps if r.get("zone_line") is not None
                   and r["zone_line"] < line)

    # ---- 1. sandbox isolation ---------------------------------------------------------------
    bench = B.Bench(HELD_VAL, sandbox=True)
    base_embeds = bench.body().count("![[assets/_repair_p")
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
    check("adjusted == original + the baseline repairs' shifts",
          all(z["adjusted_line"] == z["line"] + base_shift(z["line"])
              for z in st["zones"]))

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
    check("zone below the first repair did not shift",
          z2["adjusted_line"] == 619 + base_shift(619))
    r2 = bench.repair(zone_line=619, page=z2["page_guess"], rect=[0.1, 0.2, 0.9, 0.7],
                      note="acceptance: earlier zone")
    st2 = bench.state()
    z1_after = next(z for z in st2["zones"] if z["line"] == 1579)
    check("later zone shifted by exactly the 3 inserted lines",
          z1_after["adjusted_line"] == 1579 + base_shift(1579) + 3)
    body2 = bench.body()
    check("both NEW embeds present in the body",
          body2.count("![[assets/_repair_p") == base_embeds + 2)
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
    zone_lines = {z["line"] for z in st["zones"]}
    expected_repaired = len({1579, 619, 1715}
                            | {r["zone_line"] for r in base_reps
                               if r.get("zone_line") in zone_lines})
    check("preview counts repairs against the original zones",
          rs["original_zones"] == 4
          and rs["zones_with_repairs"] == expected_repaired
          and rs["repairs"] == len(base_reps) + 3)
    check("degeneration re-ran on the CURRENT text",
          isinstance(rs["degeneration_now"]["flagged"], bool))

    # ---- 8. one live HTTP round through the real handler ------------------------------------
    server = ThreadingHTTPServer(("127.0.0.1", 0), B.make_handler(bench))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    get = lambda p: urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=15)  # noqa: E731
    check("GET / serves the bench UI", b"Repair Bench" in get("/").read())
    wire_state = json.loads(get("/api/state").read())
    check(f"GET /api/state over the wire agrees (got sandbox={wire_state.get('sandbox')!r}, "
          f"error={wire_state.get('error')!r})",
          wire_state.get("sandbox") is True)
    check("GET /api/page streams a PNG", get("/api/page?n=5").read()[:8] == b"\x89PNG\r\n\x1a\n")
    bad = urllib.request.Request(f"http://127.0.0.1:{port}/api/repair",
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
