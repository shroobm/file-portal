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
          rs["original_zones_shown"] == 4
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

    # ---- 8b. transcribe plumbing (S71) — model-free by design ------------------------------
    # The apply/undo/provenance rails are model-independent; they get checked here with a
    # fixed payload. The MODEL path is proven live in the session's G5 (a real crop through
    # the real worker) — two differently-shaped checks, per SYM-001, never a stub that
    # pretends to be granite-docling.
    z_first = st["zones"][0]["line"]
    body_before_t = bench.body()
    depth_before = len(bench._undo)
    reps_before = len(bench.manifest.get("repairs", []))
    later_pre = [z for z in bench.state()["zones"] if z["line"] > z_first]
    adj_before_t = later_pre[0]["adjusted_line"] if later_pre else None
    ta = bench.transcribe_apply(zone_line=z_first, page=3,
                                markdown="| a | b |\n|---|---|\n| 1 | 2 |",
                                gates={"parse_ok": True, "tables": 1}, secs=2.0,
                                rect=[.1, .1, .9, .5])
    check("transcribe_apply inserts text lines (no asset)",
          ta["record"]["asset"] is None and ta["record"]["mode"] == "transcribe"
          and ta["lines"] == 5 and ta["record"]["lines"] == 5)
    check("transcribe provenance carries model + gates",
          ta["record"]["model"] == "granite-docling-258M"
          and ta["record"]["gates"].get("tables") == 1)
    check("transcribe arms the undo stack", len(bench._undo) == depth_before + 1)
    check("transcribed table present in the body", "| a | b |" in bench.body())
    later = [z for z in bench.state()["zones"] if z["line"] > z_first]
    if later and adj_before_t is not None:
        check("zones below shifted by EXACTLY the record's lines (no double count)",
              later[0]["adjusted_line"] == adj_before_t + ta["lines"])
    u = bench.undo_ai()
    check("undo restores the body byte-identical after transcribe",
          bench.body() == body_before_t and u["kind"] == "transcribe")
    check("undo removed the transcribe record — provenance cannot desync",
          len(bench.manifest.get("repairs", [])) == reps_before
          and not any(r.get("mode") == "transcribe"
                      for r in bench.manifest.get("repairs", [])))
    try:
        bench.transcribe_apply(zone_line=z_first, page=3, markdown="   ")
        check("empty transcription refused as a discard", False)
    except ValueError:
        check("empty transcription refused as a discard", True)
    real_docling_py, real_gpu_lock = B.DOCLING_PY, B.GPU_LOCK
    try:
        B.DOCLING_PY = Path(r"C:\nonexistent\python.exe")
        # Isolate this branch from a real conversion. When .gpu-lock exists, production
        # correctly refuses at the earlier serialization gate and this setup-message probe
        # never reaches the condition it claims to test.
        B.GPU_LOCK = Path(r"C:\nonexistent\file-portal-gpu.lock")
        try:
            bench.transcribe(zone_line=z_first, page=3, rect=[.1, .1, .9, .5])
            check("missing docling-env refused with the setup message", False)
        except RuntimeError as exc:
            check("missing docling-env refused with the setup message",
                  "docling-env not found" in str(exc))
    finally:
        B.DOCLING_PY, B.GPU_LOCK = real_docling_py, real_gpu_lock

    # ---- 8c. the COLLAPSE gesture (S76, docs/27 — signed) ------------------------------------
    # A synthetic loop is appended to the SANDBOX body + a matching zone to the sandbox
    # manifest, so this section proves the gesture without depending on any particular real
    # bundle still carrying a wreck.
    check("type-token ratio separates a loop from prose",
          B.type_token_ratio("the state of " * 60) < 0.10
          and B.type_token_ratio(
              "Management is the profession of control and this sentence varies its words") > 0.5)
    check("find_cycle reports the shortest period, not a multiple",
          (B.find_cycle("A. " + "the state of " * 60) or (None,))[0] == 3)
    check("find_cycle refuses a short non-repeating passage",
          B.find_cycle("the quick brown fox jumped over the lazy dog and kept on running") is None)

    loop_para = "Q. The claim of the claim of " + "the claim of " * 90 + "th Ex"
    body_c = bench.body()
    loop_line = body_c.count("\n") + 2
    # even a test fixture goes through the chokepoint — that is the law (docs/28), and an
    # earlier draft of this suite proved it by smuggling a write and being caught
    bench._write_body(body_c + "\n\n" + loop_para + "\n", gesture="test-fixture",
                      note="synthetic loop for the collapse checks")
    det = (bench.manifest.setdefault("fidelity", {}).setdefault("convert", {})
           .setdefault("tripwires", {}).setdefault("degeneration_detail", {}))
    det.setdefault("worst", []).append(
        {"line": loop_line, "chars": len(loop_para), "zlib": 0.02, "max_trigram": 90,
         "excerpt": "Q. The claim of the claim of"})
    bench.manifest_path.write_text(json.dumps(bench.manifest, indent=2) + "\n", encoding="utf-8")
    bench.manifest = json.loads(bench.manifest_path.read_text(encoding="utf-8"))

    body_pre_c, reps_pre_c, undo_pre_c = bench.body(), len(bench.manifest["repairs"]), len(bench._undo)
    zc = next(z for z in bench.state()["zones"] if z["line"] == loop_line)
    check("SYM-025: the synthetic zone anchors by excerpt, not by its recorded line",
          zc["anchor"] == "excerpt")
    pv = bench.collapse(zone_line=loop_line, preview=True)
    check("collapse preview writes nothing", bench.body() == body_pre_c)
    check("collapse preview finds the 3-token cycle", pv["period_tokens"] == 3)

    rc = bench.collapse(zone_line=loop_line)["record"]
    check("collapse record: mode='collapse', no asset, SIGNED delta",
          rc["mode"] == "collapse" and rc["asset"] is None and "delta" in rc)
    check("_record_shift reads a collapse's signed delta, never the flat +3",
          B.Bench._record_shift(rc) == rc["delta"])
    check("the loop is gone but head and tail survive",
          "claim of the claim of the claim" not in bench.body()
          and "Q. The claim of" in bench.body() and "th Ex" in bench.body())
    check("collapse arms the undo stack", len(bench._undo) == undo_pre_c + 1)
    zc2 = next(z for z in bench.state()["zones"] if z["line"] == loop_line)
    check("a collapsed zone reports collapsed=True and repaired=False (it restored nothing)",
          zc2.get("collapsed") is True and zc2.get("repaired") is False)
    try:
        bench.collapse(zone_line=loop_line)
        check("collapsing an already-collapsed zone is refused", False)
    except ValueError:
        check("collapsing an already-collapsed zone is refused", True)
    uc = bench.undo_ai()
    check("undo restores the body byte-identical after collapse",
          uc["kind"] == "collapse" and bench.body() == body_pre_c)
    check("undo popped the collapse record — provenance cannot desync",
          len(bench.manifest.get("repairs", [])) == reps_pre_c)

    # ---- 8d. omission runs are damage too (S76, SYM-026) -------------------------------------
    # The audit records loops AND omission runs; only loops ever got chips. Runs are
    # page-anchored, so they need no line arithmetic — but where their excerpt STARTS with
    # text the output still has, that gives a precise place for a crop to land.
    st_runs = bench.state()["runs"]
    check("every run carries an anchor_line key (None is a legitimate answer)",
          all("anchor_line" in r for r in st_runs))
    check("every run carries a repaired flag", all("repaired" in r for r in st_runs))
    synth_body = bench.body()
    probe_line = next((i + 1 for i, ln in enumerate(synth_body.split("\n"))
                       if len(ln.split()) > 8), None)
    if probe_line:
        words = synth_body.split("\n")[probe_line - 1].split()[:5]
        fake_run = {"page": 1, "words": 40,
                    "excerpt": " ".join(words).lower() + " zzz lost material here"}
        check("a run whose excerpt opens with surviving text anchors to that line",
              bench._resolve_run_line(fake_run) == probe_line)
    check("a run of pure OCR noise anchors to nothing rather than guessing",
          bench._resolve_run_line({"page": 9, "words": 20,
                                   "excerpt": "cl$ms£ct4 <xi)v/^fc-c4fe'v(-6-h^tr"}) is None)
    check("a run with too little text is refused an anchor",
          bench._resolve_run_line({"page": 9, "words": 3, "excerpt": "a b"}) is None)

    # ---- 8e. the repair ledger (S76, docs/28 — signed) ---------------------------------------
    # The law: no body write may bypass the chokepoint. The manual ✎ save was the path that
    # used to leave NO trace at all — it is the one that matters most here.
    led0 = len(bench.ledger())
    check("the ledger file lives beside the bundle", bench.ledger_path.name == "repairs.jsonl")
    check("gestures so far are all on the ledger", led0 > 0)

    body_m = bench.body()
    lines_m = body_m.split("\n")
    victim = next(i for i, ln in enumerate(lines_m) if len(ln) > 60)
    removed_text = lines_m[victim]
    del lines_m[victim]
    ev = bench._write_body("\n".join(lines_m), gesture="manual-edit", note="acceptance")
    check("a manual edit files an event (the hole docs/28 closes)", len(ev) == 1)
    check("the event classifies it as a removal", ev[0]["kind"] == "removal")
    check("the removed text is archived VERBATIM in the ledger",
          removed_text in ev[0]["margin"]["removed"])
    check("the event carries the margin either side",
          "context_before" in ev[0]["margin"] and "context_after" in ev[0]["margin"])
    check("the event counts the characters removed",
          ev[0]["chars"]["removed"] == len(removed_text) and ev[0]["chars"]["added"] == 0)

    lines_m.insert(victim, "a brand new line that was never here before")
    ev2 = bench._write_body("\n".join(lines_m), gesture="manual-edit", note="acceptance")
    check("an insertion classifies as an addition", ev2[0]["kind"] == "addition")
    lines_m[victim] = "the same line, rewritten differently"
    ev3 = bench._write_body("\n".join(lines_m), gesture="manual-edit", note="acceptance")
    check("a rewrite classifies as an edit", ev3[0]["kind"] == "edit")

    check("a no-op write files nothing and burns no history",
          bench._write_body(bench.body(), gesture="manual-edit") == []
          and len(bench.ledger()) == led0 + 3)

    aud = bench.ledger_audit()
    check("the sha chain is intact", aud["intact"] and not aud["breaks"])
    check("the newest event matches the body on disk", aud["matches_disk"] is True)

    # a write that goes AROUND the chokepoint must be detectable — that is the whole point
    fm_x, body_x = B.split_frontmatter(bench.md_path.read_text(encoding="utf-8"))
    bench.md_path.write_text(fm_x + body_x + "\nsmuggled in behind the ledger\n",
                             encoding="utf-8")
    check("a write that bypasses the chokepoint is DETECTED",
          bench.ledger_audit()["matches_disk"] is False)
    bench._write_body(body_x, gesture="manual-edit", note="acceptance restore")
    aud2 = bench.ledger_audit()
    check("the body matches the ledger again after the bypass is recorded",
          aud2["matches_disk"] is True)
    check("but the bypass stays on the record FOREVER — an append-only ledger cannot forget",
          aud2["intact"] is False and len(aud2["breaks"]) == 1)

    # ---- 8f. ledger-driven undo, triage, the rescore split, the report (docs/28 §5.2–5.5) ----
    depth0 = bench.undo_depth()
    check("undo depth is ledger-derived, so it survives a restart", depth0 > 0)
    body_u = bench.body()
    lines_u = body_u.split("\n")
    lines_u.insert(2, "a line that will be walked back by the ledger")
    bench._write_body("\n".join(lines_u), gesture="manual-edit", note="undo probe")
    check("the new change is undoable", bench.undo_depth() == depth0 + 1)
    u = bench.undo_ledger()
    check("ledger undo restores the body byte-identical",
          bench.body() == body_u and u["undone"] is True)
    check("the undo is itself recorded — history is never erased",
          bench.writes()[-1][0]["gesture"] == "undo")
    check("undoing does not redo itself on the next press",
          bench.undo_depth() == depth0)

    zk = bench.zone_key(bench.state()["zones"][0])
    try:
        bench.triage(zk, "dismissed-noise", "")
        check("dismissing damage without a reason is refused", False)
    except ValueError:
        check("dismissing damage without a reason is refused", True)
    try:
        bench.triage(zk, "text-restored", "asserting a derived outcome")
        check("a DERIVED outcome cannot be asserted by hand", False)
    except ValueError:
        check("a DERIVED outcome cannot be asserted by hand", True)
    bench.triage(zk, "dismissed-noise", "the witness OCR was garbage here")
    zz = next(z for z in bench.state()["zones"] if bench.zone_key(z) == zk)
    check("an operator judgment shows on the site with its reason",
          zz["outcome"] == "dismissed-noise" and "garbage" in zz["outcome_reason"])

    cov = bench.coverage()
    check("coverage counts every shown located site once",
          cov["shown"] == len(bench.state()["zones"]) + len(bench.state()["runs"]))
    check("coverage separates shown addressed from shown open",
          cov["addressed_shown"] + cov["open_shown"] == cov["shown"])

    rs2 = bench.rescore_preview()
    check("the rescore reports measurement and coverage side by side, unblended",
          "degeneration_now" in rs2 and "coverage" in rs2)
    check("the rescore recommends rather than passes, and names the bless rail",
          "bless" in rs2["vault_recommendation"]["route"]
          and isinstance(rs2["vault_recommendation"]["eligible"], bool))
    check("open sites block the recommendation",
          rs2["vault_recommendation"]["eligible"] is False
          if cov["open_shown"] or cov["completeness"] != "complete" else True)

    rep = bench.repairs_report(write=True)
    check("REPAIRS.md is written beside the bundle",
          (bench.dir / "REPAIRS.md").is_file())
    check("the report states the entropy figure Rab set as the work measure",
          "% of the document" in rep["markdown"] and rep["entropy_pct"] >= 0)
    check("the report refuses to claim an image restored the TEXT",
          "still counts the passage missing" in rep["markdown"]
          and "Nothing was recovered and nothing is claimed" in rep["markdown"])

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
