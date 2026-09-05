"""Tripwires for the stall-recovery ladder (OK-17, signed Rab 2026-08-30).

Run with the marker-env interpreter (convert_and_ship imports pymupdf at module level):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe convert_and_ship_selftest.py

Every Marker run is a monkeypatched stub — no GPU, no real PDF, safe to run beside a live
conversion. FP_PIPELINE is pointed at a temp dir BEFORE import so every fp_paths root
(events, lever file, chunk work) lands in quarantine (SYM-010: never the live dirs).

Each tripwire names what breaks if it fires:
  T1  ladder order/termination     — a wrong ladder retries at the batch that just failed
  T2  split bound/termination      — an unbounded split loops a stalled book forever
  T3  asset survival across split  — the rmtree bug: split output loses the left half's figures
  T4  batch honesty                — records say lever batch while the output came from batch 4
  T5  cost honesty                 — the estimator learns a rate that flatters itself
  T6  stage-string honesty         — a healthy convert reads as "retry 1/N" on the Room
  T7  vocabulary parity            — an event exists that the Room and manual cannot speak
  T8  invocation bound + outer cap — the ladder's worst case silently exceeds its signed bound
  T10 zero-stall negative control  — recovery bookkeeping leaks into the healthy path
"""

import ast
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).parent
QUARANTINE = Path(tempfile.mkdtemp(prefix="fp-selftest-"))
os.environ["FP_PIPELINE"] = str(QUARANTINE)
sys.modules.setdefault("marker", types.SimpleNamespace(__version__="test"))
sys.path.insert(0, str(HERE))

import convert_and_ship as cas  # noqa: E402  (env must be set first)

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def stall(elapsed: float = 30.0) -> cas._MarkerStallError:
    return cas._MarkerStallError(
        "stub stall", frozen_s=900, elapsed_s=elapsed, source="stub.pdf",
        page_range=None, signature={"vram_mib": 9999})


class MarkerStub:
    """Scripted _run_marker: `plan` maps (page_range, attempt#-for-that-range) to 'ok'/'stall'.

    Unlisted keys succeed. Records every call (page_range, batch, progress_prefix). On success
    it materializes out_dir with the asset names it is told to, absolute-page style.
    """

    def __init__(self, plan: dict | None = None, wall: float = 50.0,
                 assets_per_range: dict | None = None):
        self.plan = plan or {}
        self.wall = wall
        self.assets = assets_per_range or {}
        self.calls: list[dict] = []
        self.seen: dict = {}

    def __call__(self, engine_src, engine_stem, out_root, extra, pages, source_name,
                 page_range=None, progress_prefix="", progress_context=None):
        batch = None
        args = list(extra)
        for i, a in enumerate(args):
            if a == "--recognition_batch_size" and i + 1 < len(args):
                batch = int(args[i + 1])
        n = self.seen[page_range] = self.seen.get(page_range, 0) + 1
        self.calls.append({"page_range": page_range, "batch": batch,
                           "prefix": progress_prefix, "attempt": n,
                           "context": progress_context})
        if self.plan.get((page_range, n), "ok") == "stall":
            raise stall()
        out_dir = Path(out_root) / engine_stem
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in self.assets.get(page_range, []):
            (out_dir / name).write_bytes(b"png")
        return out_dir, f"[md {page_range} b{batch}]", self.wall, 4321


class EmitRecorder:
    def __init__(self):
        self.events = []

    def __call__(self, stage, event, **fields):
        self.events.append((f"{stage}/{event}", fields))

    def named(self, key):
        return [f for k, f in self.events if k == key]


def with_stub(stub):
    cas._run_marker = stub
    rec = EmitRecorder()
    cas.emit = rec
    return rec


REAL_RUN_MARKER = cas._run_marker
REAL_OLLAMA_UNLOAD = cas._ollama_unload  # T17 no-ops it (no network on a stub run)
SLICE_ARGS = ["--recognition_batch_size", "8"]


def run_slice(stub, start=0, end=199, batch=8):
    rec = with_stub(stub)
    out_root = QUARANTINE / "work" / "marker-out"
    result = cas._run_slice_with_retries(
        "stub.pdf", QUARANTINE / "stub.pdf", "stub", out_root,
        SLICE_ARGS, end - start + 1, start, end, batch)
    return result, rec, stub


# ---------- T0: semantic progress liveness ----------
print("T0 semantic progress liveness")
clock = [100.0]
live = cas._ProgressLiveness(clock=lambda: clock[0])
check(live.observe("layout", 10, 1, 10), "first valid tuple refreshes liveness")
clock[0] = 120.0
check(not live.observe("layout", 10, 1, 10), "identical tuple does not refresh liveness")
check(live.age() == 20.0, "identical tuple preserves original semantic age")
check(live.observe("layout", 0, 0, 10), "n regression IS a valid semantic transition")
clock[0] = 130.0
check(live.observe("layout", 0, 0, 12), "total change IS a valid semantic transition")
clock[0] = 140.0
check(live.observe("recognition", 0, 0, 12), "stage change IS a valid semantic transition")
record = json.loads(cas.PROGRESS_FILE.read_text(encoding="utf-8"))
check(record["v"] == 2 and record["writer_pid"] == os.getpid(),
      "progress receipt carries v2 and writer pid")


# ---------- T1: ladder order, dedupe, termination ----------
print("T1 ladder batches")
check(cas._slice_retry_batches(8) == [8, 4], "lever 8 -> [8, 4]")
check(cas._slice_retry_batches(16) == [16, 8, 4], "lever 16 -> [16, 8, 4]")
check(cas._slice_retry_batches(32) == [32, 8, 4], "lever 32 -> [32, 8, 4]")
check(cas._slice_retry_batches(4) == [4], "recovery batch 4 -> [4] (split children get one shot)")
check(all(b >= cas.STALL_RECOVERY_BATCH for b in cas._slice_retry_batches(32)),
      "no rung below the signed recovery batch")

# ---------- T2: split bound + termination on an unrecoverable stall ----------
print("T2 split termination")
stub = MarkerStub(plan={})
stub.plan = {k: "stall" for k in [(pr, n) for pr in
             ("0-199", "0-99", "100-199", "0-49", "50-99", "100-149", "150-199")
             for n in (1, 2, 3)]}
rec = with_stub(stub)
try:
    cas._run_slice_with_retries("stub.pdf", QUARANTINE / "stub.pdf", "stub",
                                QUARANTINE / "work" / "marker-out",
                                SLICE_ARGS, 200, 0, 199, 8)
    check(False, "always-stall raises instead of returning")
except cas._MarkerStallError:
    check(True, "always-stall raises instead of returning")
check(len(stub.calls) <= 9, f"invocations bounded ({len(stub.calls)} <= 9)")
depths = [f["split_depth"] for f in rec.named("convert/slice_split")]
check(depths and max(depths) <= cas.STALL_RETRY_MAX_SPLITS,
      "split depth never exceeds STALL_RETRY_MAX_SPLITS")

# 50-page range: too small to split — must raise after the ladder, no split event
stub2 = MarkerStub(plan={("0-49", 1): "stall", ("0-49", 2): "stall"})
rec2 = with_stub(stub2)
try:
    cas._run_slice_with_retries("stub.pdf", QUARANTINE / "stub.pdf", "stub",
                                QUARANTINE / "work" / "marker-out",
                                SLICE_ARGS, 50, 0, 49, 8)
    check(False, "min-pages range refuses to split")
except cas._MarkerStallError:
    check(not rec2.named("convert/slice_split"), "min-pages range refuses to split")

# ---------- T3: assets survive the split's rmtree; partition is exact ----------
print("T3 asset survival across split")
stub = MarkerStub(
    plan={("0-199", 1): "stall", ("0-199", 2): "stall"},
    assets_per_range={"0-99": ["_page_010_Figure_1.jpeg"],
                      "100-199": ["_page_150_Figure_2.jpeg"]})
(md, kept, wall, mib, meta), rec, stub = run_slice(stub)
check([p.name for p in kept] == ["_page_010_Figure_1.jpeg", "_page_150_Figure_2.jpeg"],
      "both halves' assets returned, left before right")
check(all(p.is_file() for p in kept), "returned asset paths still EXIST after return")
child_ranges = [c["page_range"] for c in stub.calls if c["page_range"] != "0-199"]
check(child_ranges == ["0-99", "100-199"], "split partitions exactly (no gap, no overlap)")
check(md == "[md 0-99 b4]\n\n[md 100-199 b4]", "markdown merged in page order")
check(meta["split"] is True and meta["recovered"] is True, "split meta flags honest")
check(meta["retry_wall_s"] == 60.0, "retry_wall sums both failed depth-0 attempts")

# ---------- T4: batch honesty — meta names the batch that PRODUCED the output ----------
print("T4 batch honesty")
stub = MarkerStub(plan={("0-199", 1): "stall"})
(md, kept, wall, mib, meta), rec, stub = run_slice(stub, batch=16)
check(meta["batch"] == 8, "stall at 16 -> output batch recorded as 8")
check(meta["attempts"] == 2 and meta["recovered"] is True, "attempts/recovered honest")
check(stub.calls[0]["batch"] == 16 and stub.calls[1]["batch"] == 8,
      "marker really received 16 then 8")
check(rec.named("convert/slice_retry_succeeded")[0]["batch"] == 8,
      "slice_retry_succeeded names the winning batch")

# ---------- T5: cost honesty through _convert_chunked ----------
print("T5 cost honesty")
cas.CHUNK_BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
cas.CHUNK_BATCH_FILE.write_text("8\n", encoding="utf-8")
work = QUARANTINE / "t5-work"
work.mkdir(parents=True, exist_ok=True)
sha = "ab" * 32
extra = ["--recognition_batch_size", "8"]
seed = cas.CHUNK_WORK / sha[:16] / "slice-00000-00199"
seed.mkdir(parents=True, exist_ok=True)
(seed / "slice.md").write_text("[resumed slice 1]", encoding="utf-8")
(seed / "_page_005_Figure_0.jpeg").write_bytes(b"png")
(seed / ".done").write_text(json.dumps({
    "source_sha256": sha, "page_range": "0-199", "wall_s": 100.0, "batch": 8,
    "engine_args": list(extra), "marker_version": "test"}) + "\n", encoding="utf-8")
stub = MarkerStub(plan={("200-399", 1): "stall"},
                  assets_per_range={"200-399": ["_page_250_Figure_0.jpeg"]})
rec = with_stub(stub)
md, assets_dir, total_wall, peak, chunking, stats = cas._convert_chunked(
    "stub.pdf", QUARANTINE / "stub.pdf", "stub", work,
    QUARANTINE / "t5-work" / "marker-out", extra, 400, sha)
check(stats["cost_s"] == 180.0, f"cost_s = win 50 + retry 30 + resumed 100 ({stats['cost_s']})")
check(stats["retry_wall_s"] == 30.0, "retry_wall_s surfaced")
check(stats["resumed_slices"] == 1, "resumed slice counted")
check(stats["pages_converted_this_run"] == 200, "honest denominator: 200 pages this run")
check(total_wall == 50.0, "total_wall stays winning-attempt-only")
check(md == "[resumed slice 1]\n\n[md 200-399 b4]", "resumed + fresh markdown merged in order")
check((assets_dir / "_page_005_Figure_0.jpeg").is_file()
      and (assets_dir / "_page_250_Figure_0.jpeg").is_file(),
      "assets from resumed AND recovered slices merged")
ev = rec.named("convert/slice")
fresh = [f for f in ev if not f.get("resumed")][0]
check(fresh["batch"] == 4 and fresh["lever_batch"] == 8 and fresh["recovered"] is True,
      "slice event: batch=4 (actual), lever_batch=8, recovered")

# ---------- T6: stage-string honesty ----------
print("T6 stage-string honesty")
stub = MarkerStub(plan={("0-199", 1): "stall"})
(_, _, _, _, meta), rec, stub = run_slice(stub)
check("retry" not in stub.calls[0]["prefix"], "attempt 1 carries no 'retry' label")
check("retry 2/" in stub.calls[1]["prefix"], "attempt 2 says retry 2/N")
check(stub.calls[1]["context"]["attempt"] == 2
      and stub.calls[1]["context"]["batch"] == 4
      and stub.calls[1]["context"]["page_range"] == "0-199",
      "progress context carries structured attempt, batch, and range")

# ---------- T7: vocabulary parity (converter -> shared surfaces -> manual) ----------
print("T7 vocabulary parity")
vocab = (HERE.parent / "windows-widget" / "src" / "event-vocab.js").read_text(encoding="utf-8")
room = (HERE.parent / "windows-widget" / "src" / "room.js").read_text(encoding="utf-8")
dock = (HERE.parent / "windows-widget" / "src" / "main.js").read_text(encoding="utf-8")
manual = (HERE.parent / "docs" / "22-engineering-manual.html").read_text(encoding="utf-8")
LADDER_VOCAB = ["convert/stalled", "convert/slice_retry", "convert/slice_retry_succeeded",
                "convert/slice_split", "convert/timeout", "convert/chunk_batch_invalid",
                "convert/chunk_batch_unreadable", "convert/asset_range_warning",
                "convert/slice", "convert/converted", "intake/failed"]
for key in LADDER_VOCAB:
    check(f'"{key}"' in vocab, f"shared event-vocab.js speaks {key}")
check('from "./event-vocab.js"' in room and 'from "./event-vocab.js"' in dock,
      "Room and Dock both import the shared vocabulary")
for name in ["slice_retry_succeeded", "slice_split", "timeout", "chunk_batch_invalid",
             "chunk_batch_unreadable", "asset_range_warning", "retry_wall_s",
             "pages_converted_this_run",
             # NUM batch (review m4): the manual-parity guard must SEE the new vocabulary
             "ocr_invisible_ratio", "pages_this_run", "runs_total",
             "chunks_generated", "goodput_accepted_tok_s"]:
    check(name in manual, f"docs/22 names {name}")
src = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
emitted = set(re.findall(r'emit\("convert", "([a-z_]+)"', src))
for name in ("stalled", "slice_retry", "slice_retry_succeeded", "slice_split", "timeout"):
    check(name in emitted, f"converter really emits {name}")

# ---------- T8: worst-case invocation bound derived from the constants ----------
print("T8 invocation bound + outer cap")


def worst_invocations(batch, depth=0):
    ladder = len(cas._slice_retry_batches(batch))
    if depth >= cas.STALL_RETRY_MAX_SPLITS:
        return ladder
    return ladder + 2 * worst_invocations(cas.STALL_RECOVERY_BATCH, depth + 1)


check(worst_invocations(32) == 9,
      f"worst case from constants = 9 marker invocations ({worst_invocations(32)})")
watcher = (HERE / "watch_and_convert.py").read_text(encoding="utf-8")
m = re.search(r'FP_CONVERT_TIMEOUT_S", "(\d+)"', watcher)
check(m is not None and int(m.group(1)) >= 21600,
      "watcher outer cap >= the old 6 h flat (never silently lowered)")
check("taskkill" in watcher and "/T" in watcher, "watcher timeout kills the TREE, not the pid")

# ---------- T9: split monitor cadences and drain boundary ----------
print("T9 monitor cadences + drain boundary")
src = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
check("proc.wait(timeout=5)" in src, "process completion/stall monitor cadence is 5 s")
check("next_gpu_sample = time.perf_counter() + 30" in src,
      "GPU subprocess sampling remains on a separate 30 s cadence")
check("for line in pipe" in src and "for _ in pipe" in src,
      "stdout drain and decode-failure drain remain present")

# ---------- T10: zero-stall negative control ----------
print("T10 zero-stall negative control")
stub = MarkerStub(assets_per_range={"0-199": ["_page_003_Figure_0.jpeg"]})
(md, kept, wall, mib, meta), rec, stub = run_slice(stub)
check(meta == {"batch": 8, "attempts": 1, "retry_wall_s": 0.0,
               "recovered": False, "split": False}, "healthy meta is exactly baseline")
check(not any(k.startswith("convert/slice_retry") or k == "convert/slice_split"
              for k, _ in rec.events), "no recovery events on a healthy slice")
check(len(stub.calls) == 1 and "retry" not in stub.calls[0]["prefix"],
      "one invocation, unlabelled")
check(kept and kept[0].is_file(), "healthy-path assets also materialized (same contract)")

# ---------- T11: OK-16 ollama unload — best-effort, event only on real work ----------
print("T11 ollama unload")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeUrllib:
    """Scripted urllib.request: records calls; ps_payload drives /api/ps; raises on demand."""

    def __init__(self, ps_payload=None, fail=False):
        self.ps_payload = ps_payload or {"models": []}
        self.fail = fail
        self.calls = []
        self.Request = _real_urllib.Request

    def urlopen(self, url_or_req, timeout=None):
        if self.fail:
            raise OSError("connection refused")
        url = url_or_req if isinstance(url_or_req, str) else url_or_req.full_url
        self.calls.append(url)
        return FakeResponse(json.dumps(self.ps_payload).encode("utf-8"))


_real_urllib = cas.urllib.request
try:
    rec = EmitRecorder()
    cas.emit = rec
    fake = FakeUrllib(ps_payload={"models": [{"name": "qwen3:8b"}, {"name": "nomic-embed"}]})
    cas.urllib.request = fake
    cas._ollama_unload()
    check(len([u for u in fake.calls if u.endswith("/api/generate")]) == 2,
          "one unload call per resident")
    ev = rec.named("convert/ollama_unloaded")
    check(len(ev) == 1 and ev[0]["count"] == 2 and ev[0]["models"] == ["qwen3:8b", "nomic-embed"],
          "event names what was freed")

    rec = EmitRecorder()
    cas.emit = rec
    cas.urllib.request = FakeUrllib(ps_payload={"models": []})
    cas._ollama_unload()
    check(not rec.events, "zero residents -> silent no-op, no event")

    rec = EmitRecorder()
    cas.emit = rec
    cas.urllib.request = FakeUrllib(fail=True)
    cas._ollama_unload()  # must not raise
    check(not rec.events, "unreachable ollama -> swallowed, no event, no raise")
finally:
    cas.urllib.request = _real_urllib
check('"convert/ollama_unloaded"' in vocab,
      "shared event-vocab.js speaks convert/ollama_unloaded")
check("ollama_unloaded" in (HERE.parent / "docs" / "22-engineering-manual.html").read_text(
    encoding="utf-8"), "docs/22 names ollama_unloaded")

# ---------- T12: A1 latest-book slice retention ----------
print("T12 slice retention (A1)")
rec = with_stub(MarkerStub(assets_per_range={}))
cas.CHUNK_BATCH_FILE.write_text("8\n", encoding="utf-8")
work12 = QUARANTINE / "t12-work"
work12.mkdir(parents=True, exist_ok=True)
sha_a = "aa" * 32
cas._convert_chunked("bookA.pdf", QUARANTINE / "a.pdf", "booka", work12,
                     work12 / "marker-out", ["--recognition_batch_size", "8"], 400, sha_a)
book_a = cas.CHUNK_WORK / sha_a[:16]
check(book_a.is_dir() and (book_a / "slice-00000-00199" / ".done").is_file(),
      "slices SURVIVE their own merge (post-convert deaths resume free)")
sha_b = "bb" * 32
work12b = QUARANTINE / "t12-work-b"
work12b.mkdir(parents=True, exist_ok=True)
cas._convert_chunked("bookB.pdf", QUARANTINE / "b.pdf", "bookb", work12b,
                     work12b / "marker-out", ["--recognition_batch_size", "8"], 400, sha_b)
check(not book_a.is_dir(), "a DIFFERENT book's start sweeps the previous book (disk bounded)")
check((cas.CHUNK_WORK / sha_b[:16]).is_dir(), "the new book's slices are the ones kept")

# ---------- T13: NUM-4 promise repairs ----------
print("T13 promise honesty (NUM-4)")
rec = with_stub(MarkerStub())
cas.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
cas.LEDGER_FILE.write_text(
    json.dumps({"lane": "clean", "s_per_page": 2.0, "chars_per_page": 1000}) + "\n"
    + json.dumps({"lane": "clean", "s_per_page": 4.0, "chars_per_page": 1100}) + "\n",
    encoding="utf-8")
est = cas.estimate_from_ledger(100, "clean", 1050)
check(est["s_per_page"] == 3.0, "TRUE median of 2 samples averages the pair (was: larger)")
check(est["basis"] == "similar", "basis 'similar' with >=2 neighbours")
cas.LEDGER_FILE.write_text(
    json.dumps({"lane": "clean", "s_per_page": 2.0, "chars_per_page": 1000}) + "\n",
    encoding="utf-8")
est1 = cas.estimate_from_ledger(100, "clean", 1050)
check(est1["basis"] == "single-sample", "basis names a 1-witness promise honestly")
# the resumable peek scopes the promise to THIS run's pages — and it is IDENTITY-AWARE
# (review M3: a presence-only peek promised 0 s for a whole book after a Marker upgrade)
sha13 = "cd" * 32
extra13 = ["--recognition_batch_size", "8"]
bw = cas.CHUNK_WORK / sha13[:16]
good = {"source_sha256": sha13, "engine_args": list(extra13), "marker_version": "test"}
for rng in ("00000-00199", "00200-00399"):
    d = bw / f"slice-{rng}"
    d.mkdir(parents=True, exist_ok=True)
    (d / ".done").write_text(json.dumps(good), encoding="utf-8")
stale13 = bw / "slice-00400-00599"
stale13.mkdir(parents=True, exist_ok=True)
(stale13 / ".done").write_text(json.dumps({**good, "marker_version": "OLD"}), encoding="utf-8")
check(cas._resumable_pages(sha13, 1000, extra13) == 400,
      "identity-matching .done slices count; the version-mismatched one does NOT (M3)")
check(cas._resumable_pages("ee" * 32, 1000, extra13) == 0, "no cache -> zero resumable")
rec = with_stub(MarkerStub())
cas._write_estimate_safe("t13.pdf", 1000, "clean", 1050, resumable_pages=400)
filed = json.loads(cas.ESTIMATE_FILE.read_text(encoding="utf-8"))
check(filed["pages_this_run"] == 600 and filed["resumed_pages_assumed"] == 400,
      "the promise names its resume assumption")
check(filed["eta_s"] == int(filed["s_per_page"] * 600),
      "ETA covers only the pages THIS run must convert (was: the whole book)")
ev13 = rec.named("convert/estimate")
check(ev13 and ev13[0]["pages_this_run"] == 600, "estimate event carries pages_this_run")

# ---------- T14: NUM-5 decision evidence ----------
print("T14 probe evidence (NUM-5)")
import pymupdf as _pm  # noqa: E402
_doc = _pm.open()
_page = _doc.new_page()
_page.insert_text((72, 72), "hello numeration census evidence")
_pdf14 = QUARANTINE / "t14.pdf"
_doc.save(str(_pdf14))
_doc.close()
chars14, pages14, ocr14, evd14 = cas.probe(_pdf14)
check(pages14 == 1 and not ocr14, "synthetic born-digital page probes clean")
check(set(evd14) == {"invisible_spans", "total_spans", "invisible_ratio", "ocr_font_trigger"},
      "probe returns the vote's evidence, not just its verdict")
check(evd14["invisible_ratio"] == 0.0 and evd14["ocr_font_trigger"] is None,
      "clean page: ratio 0.0, no font trigger")
src14 = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
check("ocr_invisible_ratio=" in src14, "the probe event emits the ratio")
check('"probe_evidence": ocr_evidence' in src14, "the evidence travels in the manifest")

# ---------- T15: NUM-6 analyst goodput ----------
print("T15 analyst goodput (NUM-6)")
import analyst  # noqa: E402
_real_gen, _real_unload = analyst._generate, analyst.unload
try:
    calls15 = [0]

    def fake_generate(prompt):
        calls15[0] += 1
        analyst._last_call.clear()
        analyst._last_call.update({"prompt_tokens": 100, "output_tokens": 40})
        if calls15[0] == 2:
            return "TAMPERED " + prompt[-20:]  # fence violation -> rejected
        return prompt.split("\n\n", 1)[-1] if "\n\n" in prompt else prompt

    analyst._generate = fake_generate
    analyst.unload = lambda: None
    body15 = "\n\n".join(f"paragraph {i} " + "word " * 40 for i in range(3))
    out15, meta15 = analyst.process(body15, backend="local")
    check(meta15["chunks_generated"] == meta15["chunks_passed"] + meta15["chunks_rejected"]
          + meta15["chunks_failed"], "generated = passed + rejected + failed (no resume here)")
    check(meta15["tokens_output_total"] == 40 * meta15["chunks_generated"],
          "output tokens aggregated across every paid call")
    check(meta15["tokens_accepted_output"] == 40 * meta15["chunks_passed"],
          "ONLY accepted chunks earn goodput tokens (rejected excluded)")
    check(meta15["goodput_accepted_tok_s"] is not None
          and meta15["goodput_conditions"].startswith("THIS-run accepted-output tokens"),
          "goodput present with its docs/34 conditions in the record")
    check(meta15["tokens_counted_calls"] == meta15["chunks_generated"]
          and meta15["tokens_prompt_counted_calls"] == meta15["chunks_generated"],
          "review M5: every token sum names its own denominator")

    def counterless_generate(prompt):
        analyst._last_call.clear()
        return prompt.split("\n\n", 1)[-1] if "\n\n" in prompt else prompt

    analyst._generate = counterless_generate
    _, meta15b = analyst.process("short body " + "word " * 30, backend="local")
    check(meta15b["tokens_output_total"] is None
          and meta15b["goodput_accepted_tok_s"] is None,
          "a counterless backend yields honest None, never invented zeros")
finally:
    analyst._generate, analyst.unload = _real_gen, _real_unload

# ---------- T16: NUM-3 true counts beside caps ----------
print("T16 true counts beside caps (NUM-3)")
import fidelity_audit as fa  # noqa: E402
degen16 = fa.degeneration("para\n\n" + "\n\n".join(
    ("loop word trigram " * 40) for _ in range(14)))
check(degen16["blocks_total"] >= len(degen16["worst"]),
      "degeneration carries the TRUE flagged-block count")
check(degen16["worst_capped_at"] == 10 and len(degen16["worst"]) <= 10,
      "the exemplar list stays capped and NAMES its cap")
src16 = (HERE / "fidelity_audit.py").read_text(encoding="utf-8")
check('"runs_total": len(runs)' in src16, "the audit block carries runs_total pre-cap")
check("runs_total=" in src14, "audit/scored events emit runs_total beside the capped runs")

# ---------- T17: F3 — the INLINE analyst path emits its two events ----------
print("T17 inline analyst events (F3)")
CAS_SRC = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
FAKE_TAIL = "\n\nANALYST-APPENDED-TAIL"
# Every count DIFFERENT on purpose: an emit that aliases one field to another (generated <-
# passed is the natural slip) cannot survive a meta where no two numbers are equal.
FAKE_META = {
    "model": "fake-model", "backend": "local", "program": "fake-program",
    "chunks_passed": 7, "chunks_rejected": 2, "chunks_failed": 1,
    "chunks_resumed": 641, "chunks_generated": 10, "duration_s": 12.5,
    "goodput_accepted_tok_s": 33.75,
    # J32-B/SYM-074: chunks_rejected's breakdown — sums to 2 (chunks_rejected), each bucket a
    # DIFFERENT number so an emit that aliases one to another cannot survive this fixture.
    "rejections": {"fence": 1, "survival": 1, "think_leak": 0},
}


def _analyst_done_keys(func_name: str):
    """The key tuple inside `emit("analyst", "done", **{k: ... for k in (...)})`, read out of
    the SOURCE of the named function. Parity is checked against what the file really says —
    retyping the tuple here would make the two paths agree only with this test (SYM-001)."""
    fn = next((n for n in ast.walk(ast.parse(CAS_SRC))
               if isinstance(n, ast.FunctionDef) and n.name == func_name), None)
    if fn is None:
        return None
    for call in ast.walk(fn):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "emit" and len(call.args) == 2):
            continue
        if [getattr(a, "value", None) for a in call.args] != ["analyst", "done"]:
            continue
        for kw in call.keywords:
            if kw.arg is None and isinstance(kw.value, ast.DictComp):
                return [e.value for e in kw.value.generators[0].iter.elts]
    return None


INLINE_KEYS = _analyst_done_keys("convert")
RESUME_KEYS = _analyst_done_keys("apply_analyst")
check(INLINE_KEYS is not None and RESUME_KEYS is not None
      and set(RESUME_KEYS) <= set(INLINE_KEYS),
      "inline done carries every key the --resume path emits (parity-equal)")
# D-2 (S114, 2026-09-03): the builder's first cut pinned the ASYMMETRY (inline had chunks_resumed,
# apply_analyst did not) as if it were the invariant. The invariant is PARITY - the two emits are
# the same event and must carry the same keys - and N-005's key must ride BOTH. This check goes
# red if either side moves alone in either direction; watched failing by removing the key from
# apply_analyst's tuple (RED), then restoring it (GREEN).
check(INLINE_KEYS is not None and RESUME_KEYS is not None
      and set(INLINE_KEYS) == set(RESUME_KEYS)
      and "chunks_resumed" in INLINE_KEYS and "chunks_resumed" in RESUME_KEYS,
      "inline and --resume done emit IDENTICAL key sets, and both carry chunks_resumed (N-005)")


class FakeAnalyst:
    """sys.modules-injected stand-in for analyst.py — no ollama, no network, no GPU. Its
    process() returns a body of a DIFFERENT length on purpose: that is the decoy for `chars`,
    where the wrong answer (len(body) after the rebind) is the analyst's own OUTPUT size."""

    CHUNK_TARGET = 6000  # lever-waiver: a test double's attribute, not a decision - it mirrors the shape of analyst.CHUNK_TARGET (the real lever, analyst.py) so the stub's chunker signature matches; any value works, and moving the real lever does not move this

    def __init__(self, meta):
        self.meta = dict(meta)
        self.seen = []

    def process(self, body, backend="local"):
        self.seen.append((len(body), backend))
        return body + FAKE_TAIL, dict(self.meta)

    def load_rules(self):
        return {}

    def unload(self):
        return None


def _born_digital_pdf(path: Path) -> Path:
    """>= MIN_CHARS_PER_PAGE of type-0 text on one page, so route() takes the CLEAN lane —
    the scan lane would import marker.builders.document, which the stubbed marker has not."""
    doc = _pm.open()
    page = doc.new_page()
    for i in range(6):
        page.insert_text((72, 72 + 14 * i),
                         f"born-digital line {i} carrying enough characters to route clean")
    doc.save(str(path))
    doc.close()
    return path


def drive_inline(module, work_name: str, meta: dict = FAKE_META):
    """Run the REAL convert() end to end with use_analyst=True: the same Marker stub every
    other tripwire uses (no GPU), ollama unload no-op'd (no network), the analyst faked."""
    work = QUARANTINE / work_name
    work.mkdir(parents=True, exist_ok=True)
    # The source may NOT live inside work/: convert() copies it to work/<slugified stem>.pdf,
    # and a same-named source there is a copy onto itself (WinError 32, hit building this).
    pdf = _born_digital_pdf(QUARANTINE / f"{work_name}-inline.pdf")
    fake = FakeAnalyst(meta)
    rec = EmitRecorder()
    module._run_marker = MarkerStub()
    module.emit = rec
    module._ollama_unload = lambda: None
    prior = sys.modules.get("analyst")
    sys.modules["analyst"] = fake
    try:
        _tmp, bundle, _manifest = module.convert(pdf, work, use_analyst=True,
                                                 analyst_backend="local")
    finally:
        if prior is not None:
            sys.modules["analyst"] = prior
        else:
            sys.modules.pop("analyst", None)
    return rec, fake, bundle


rec17, fake17, bundle17 = drive_inline(cas, "t17-work")
starts17 = rec17.named("analyst/start")
dones17 = rec17.named("analyst/done")
check(len(starts17) == 1 and len(dones17) == 1,
      "the inline pass emits exactly one analyst/start and one analyst/done")
check([k for k, _ in rec17.events if k.startswith("analyst/")]
      == ["analyst/start", "analyst/done"], "start precedes done, in that order, once each")
pre17 = fake17.seen[0][0]          # what analyst.process was really handed
post17 = pre17 + len(FAKE_TAIL)    # what it handed back — the wrong answer for `chars`
check(bool(starts17) and starts17[0]["bundle"] == bundle17
      and starts17[0]["backend"] == "local",
      "start names the bundle and the backend the convert really used")
check(bool(starts17) and starts17[0]["chars"] == pre17,
      "start's chars is the body handed to analyst.process")
check(bool(dones17) and dones17[0].get("chars") == pre17,
      "done's chars is the PRE-analyst body, as apply_analyst measures it")
check(bool(dones17) and dones17[0].get("chars") != post17,
      f"decoy: done's chars is NOT the post-analyst body ({post17})")
d17 = dones17[0] if dones17 else {}
check(set(d17) == set(INLINE_KEYS or []) | {"bundle", "chars"},
      "done carries bundle + chars + exactly the source's key tuple, nothing invented")
check(d17.get("chunks_passed") == 7 and d17.get("chunks_rejected") == 2
      and d17.get("chunks_failed") == 1, "the three chunk verdicts travel unaltered")
check(d17.get("chunks_generated") == 10
      and d17.get("chunks_generated") != d17.get("chunks_passed"),
      "decoy: chunks_generated is the PAID-CALL count (10), never chunks_passed (7)")
check(d17.get("goodput_accepted_tok_s") == 33.75,
      "NUM-6: the docs/34 goodput rate reaches the stream from the inline path")
check(d17.get("chunks_resumed") == 641,
      "N-005: chunks_resumed rides the event (silenced on every human channel before F3)")
check(d17.get("rejections") == {"fence": 1, "survival": 1, "think_leak": 0},
      "J32-B/SYM-074: the rejections breakdown rides the event unaltered")
check(d17.get("duration_s") == 12.5 and d17.get("program") == "fake-program"
      and d17.get("backend") == "local",
      "duration_s, program and backend carried exactly as apply_analyst carries them")
TRAP17 = round(FAKE_META["chunks_passed"] / FAKE_META["duration_s"], 2)
check(TRAP17 not in [v for v in d17.values() if isinstance(v, (int, float))],
      f"decoy: no field equals chunks_passed/duration_s ({TRAP17}) — the N-007/N-013 trap "
      f"(this-run wall under a whole-book numerator) stays underived")

# An older analyst.py's meta lacks the NUM-6/N-005 counters. This emit sits mid-convert, after
# hours of GPU and BEFORE the note and manifest are written, so a KeyError here would cost the
# whole book to say nothing: the key set must survive, filled with honest nulls.
LEAN17 = {k: v for k, v in FAKE_META.items()
          if k not in ("chunks_generated", "goodput_accepted_tok_s", "chunks_resumed",
                       "rejections")}
try:
    rec17b, _f, _b = drive_inline(cas, "t17-work-lean", LEAN17)
    d17b = (rec17b.named("analyst/done") or [{}])[0]
except Exception as exc:  # noqa: BLE001 — a raise here IS the failure this check is for
    d17b = {"__raised__": repr(exc)[:120]}
check(bool(d17b) and set(d17b) == set(d17),   # bool(): two empty sets are not agreement
      f"an older analyst's meta still emits the FULL key set ({d17b.get('__raised__', '')})")
check(d17b.get("chunks_generated", 0) is None and d17b.get("goodput_accepted_tok_s", 0) is None
      and d17b.get("chunks_resumed", 0) is None and d17b.get("rejections", 0) is None,
      "a missing counter (or a pre-J32-B analyst's absent rejections breakdown) emits null — "
      "honest absence (docs/34), never an invented 0")

# Negative control: the SAME run with the two emit statements textually removed from convert().
# Blanking their line spans (not deleting them) keeps every other line number identical, so the
# control differs from the subject in exactly the two statements under test and nothing else.
NC_LINES = CAS_SRC.splitlines(keepends=True)
_nc_fn = next(n for n in ast.walk(ast.parse(CAS_SRC))
              if isinstance(n, ast.FunctionDef) and n.name == "convert")
_nc_removed = 0
for _n in ast.walk(_nc_fn):
    if (isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Call)
            and isinstance(_n.value.func, ast.Name) and _n.value.func.id == "emit"
            and _n.value.args and getattr(_n.value.args[0], "value", None) == "analyst"):
        for _ln in range(_n.lineno - 1, _n.end_lineno):
            NC_LINES[_ln] = "\n"
        _nc_removed += 1
check(_nc_removed == 2,
      f"the control really removed 2 analyst emit statements from convert() ({_nc_removed})")
nc = types.ModuleType("convert_and_ship_nc")
nc.__file__ = str(HERE / "convert_and_ship.py")
exec(compile("".join(NC_LINES), nc.__file__, "exec"), nc.__dict__)  # noqa: S102
rec_nc, _fnc, _bnc = drive_inline(nc, "t17-nc")
check(not [k for k, _ in rec_nc.events if k.startswith("analyst/")],
      "negative control: emits removed -> ZERO analyst events from the same run")
check(any(k == "convert/converted" for k, _ in rec_nc.events),
      "negative control really RAN the convert — this is silence, not a skipped path")
cas._ollama_unload = REAL_OLLAMA_UNLOAD


# ---------- T18: J33 — the Marker body sidecar ("<bundle_name>.marker.txt") ----------
print("T18 marker body sidecar (J33)")


class MarkerBodyFakeAnalyst:
    """Like T17's FakeAnalyst, but keeps the full INPUT text (not just its length) so the
    sidecar can be compared against exactly what analyst.process was handed — the decoy this
    ticket watches for is a sidecar that captured the analyst's OUTPUT instead of Marker's."""

    CHUNK_TARGET = 6000  # lever-waiver: shape-only test-double attribute, see T17's FakeAnalyst

    def __init__(self):
        self.seen_text = None

    def process(self, body, backend="local"):
        self.seen_text = body
        return body + "\n\nANALYST REWROTE THIS", {
            "model": "fake", "backend": backend, "program": "fake",
            "chunks_passed": 1, "chunks_rejected": 0, "chunks_failed": 0, "duration_s": 1.0,
        }

    def load_rules(self):
        return {}

    def unload(self):
        return None


def drive_marker_body(module, work_name: str, use_analyst: bool, fake=None):
    """Run the REAL convert() end to end (no GPU, no network) with or without the analyst
    branch, and return (tmp_dir, bundle_name, manifest, EmitRecorder)."""
    work = QUARANTINE / work_name
    work.mkdir(parents=True, exist_ok=True)
    pdf = _born_digital_pdf(QUARANTINE / f"{work_name}-inline.pdf")
    rec = EmitRecorder()
    module._run_marker = MarkerStub()
    module.emit = rec
    module._ollama_unload = lambda: None
    prior = sys.modules.get("analyst")
    if use_analyst:
        sys.modules["analyst"] = fake or MarkerBodyFakeAnalyst()
    try:
        tmp_dir, bundle, manifest = module.convert(pdf, work, use_analyst=use_analyst,
                                                    analyst_backend="local")
    finally:
        if prior is not None:
            sys.modules["analyst"] = prior
        elif use_analyst:
            sys.modules.pop("analyst", None)
    return tmp_dir, bundle, manifest, rec


# (a) + (b): the sidecar equals what analyst.process was HANDED, not what it returned; the
# manifest's bytes + sha256 match the file actually on disk.
fake18 = MarkerBodyFakeAnalyst()
tmp18, bundle18, manifest18, rec18 = drive_marker_body(cas, "t18-analyst", True, fake18)
sidecar18 = tmp18 / f"{bundle18}{cas.MARKER_BODY_SUFFIX}"
check(sidecar18.is_file(), "the sidecar file exists beside the bundle")
sidecar_text18 = sidecar18.read_text(encoding="utf-8")
check(sidecar_text18 == fake18.seen_text,
      "sidecar text equals the body HANDED to analyst.process (the marker_body, not its output)")
check(sidecar_text18 != fake18.seen_text + "\n\nANALYST REWROTE THIS",
      "decoy: the sidecar is NOT the post-analyst text")
mb18 = manifest18.get("marker_body")
check(bool(mb18) and mb18.get("file") == sidecar18.name, "manifest names the sidecar file")
raw18 = sidecar18.read_bytes()
check(mb18 is not None and mb18.get("bytes") == len(raw18),
      "manifest bytes matches the file's true on-disk size")
check(mb18 is not None and mb18.get("sha256") == hashlib.sha256(raw18).hexdigest(),
      "manifest sha256 matches the file's real digest")

# copytree-carries proof: every downstream site (anchor/pending/held/the shipped tar) copies
# or tars the SAME tmp_dir convert() returns, which already contains the sidecar written above
# convert()'s return — proven directly for the anchor site (main()'s own idiom); pending/held/
# ship copy or tar the identical tmp_dir by the identical mechanism (Inferred, not separately
# exercised here — declared as residue).
anchor_check18 = QUARANTINE / "t18-anchor-check" / bundle18
anchor_check18.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(tmp18, anchor_check18)
check((anchor_check18 / f"{bundle18}{cas.MARKER_BODY_SUFFIX}").is_file(),
      "the anchor copytree site (shutil.copytree(tmp_dir, ...), main()'s own idiom) carries "
      "the sidecar")

# (e): the no-analyst path also writes it.
tmp18b, bundle18b, manifest18b, _rec18b = drive_marker_body(cas, "t18-no-analyst", False)
check((tmp18b / f"{bundle18b}{cas.MARKER_BODY_SUFFIX}").is_file(),
      "a book converted WITHOUT --analyst also gets the sidecar")
check(bool(manifest18b.get("marker_body")), "manifest key present on the no-analyst path too")

# (c): fail-safe — monkeypatch the write to raise; convert still completes, the manifest key
# is simply absent, and no exception escapes to the caller.
_real_write_text = Path.write_text


def _raising_write_text(self, *a, **kw):
    if self.name.endswith(cas.MARKER_BODY_SUFFIX):
        raise OSError("disk full (simulated)")
    return _real_write_text(self, *a, **kw)


Path.write_text = _raising_write_text
try:
    tmp18c, bundle18c, manifest18c, _rec18c = drive_marker_body(cas, "t18-failsafe", False)
finally:
    Path.write_text = _real_write_text
check("marker_body" not in manifest18c,
      "a write fault leaves the manifest key absent, not a bad one")
check((tmp18c / f"{bundle18c}.md").is_file(),
      "the book converts exactly as it did before J33, despite the fault")
check(not (tmp18c / f"{bundle18c}{cas.MARKER_BODY_SUFFIX}").exists(),
      "and really did not leave a sidecar behind (a torn write is not a half-file)")

# (d): NEGATIVE CONTROL — the writer removed. Same blank-the-line-span technique T17 uses on
# convert()'s analyst emits, applied here to the _write_marker_body_safe call.
NC18_SRC = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
NC18_LINES = NC18_SRC.splitlines(keepends=True)
_nc18_fn = next(n for n in ast.walk(ast.parse(NC18_SRC))
                if isinstance(n, ast.FunctionDef) and n.name == "convert")
_nc18_removed = 0
for _n in ast.walk(_nc18_fn):
    if (isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Call)
            and isinstance(_n.value.func, ast.Name)
            and _n.value.func.id == "_write_marker_body_safe"):
        for _ln in range(_n.lineno - 1, _n.end_lineno):
            NC18_LINES[_ln] = "\n"
        _nc18_removed += 1
check(_nc18_removed == 1,
      f"the control really removed the _write_marker_body_safe call ({_nc18_removed})")
nc18 = types.ModuleType("convert_and_ship_nc18")
nc18.__file__ = str(HERE / "convert_and_ship.py")
exec(compile("".join(NC18_LINES), nc18.__file__, "exec"), nc18.__dict__)  # noqa: S102
tmp18d, bundle18d, manifest18d, _rec18d = drive_marker_body(nc18, "t18-nc", False)
check(not (tmp18d / f"{bundle18d}{cas.MARKER_BODY_SUFFIX}").exists(),
      "NEGATIVE CONTROL: writer removed -> no sidecar on disk")
check("marker_body" not in manifest18d, "NEGATIVE CONTROL: writer removed -> no manifest key")
check((tmp18d / f"{bundle18d}.md").is_file(),
      "negative control really ran the convert — this is absence, not a skipped path")


# ---------- T19: J31 — re-audit a repaired held bundle (D-1, signed 2026-09-05) ----------
print("T19 re-audit a repaired held bundle (J31)")
import fidelity_audit  # noqa: E402  (already in sys.modules; bare name to monkeypatch on)


class ReaudFakes:
    """sys.modules-free stand-in for fidelity_audit's two stage audits — no real PDF read,
    no real text comparison. compute_verdict stays REAL: these return controlled BLOCKS, and
    the real verdict logic decides pass/flag/fail from them, so the D-1 control (history says
    fail, the final blocks say otherwise) exercises the actual rule, not a stubbed answer."""

    def __init__(self, convert_result, analyst_result):
        self.convert_result = convert_result
        self.analyst_result = analyst_result
        self.convert_calls: list[dict] = []
        self.analyst_calls: list[dict] = []

    def audit_convert(self, pdf_path, markdown, lane, asset_count=None):
        self.convert_calls.append({"pdf_path": Path(pdf_path), "markdown": markdown,
                                    "lane": lane, "asset_count": asset_count})
        return self.convert_result

    def audit_analyst(self, marker_markdown, analyst_markdown):
        self.analyst_calls.append({"marker_markdown": marker_markdown,
                                    "analyst_markdown": analyst_markdown})
        return self.analyst_result


PASS_CONVERT = {"doc_survival": 0.99, "pages_flagged": [], "runs_total": 0, "runs": [],
                "kind": "fidelity", "tripwires": {"degeneration": False}}
PASS_ANALYST = {"doc_survival": 0.999, "runs": [], "runs_total": 0}
FAIL_ANALYST = {"doc_survival": 0.9, "runs": [], "runs_total": 40}  # < ANALYST_DOC_FAIL


def make_held_bundle(sha16, name="paper", *, source=None, lane="clean",
                      old_verdict="fail", with_sidecar=True, with_slice_cache=False,
                      with_analyst_block=True, with_bench_files=True,
                      sidecar_text="MARKER BODY REFERENCE TEXT",
                      held_body="held post-analyst body text"):
    """A synthetic held/<sha16> bundle — enough of the real shape (manifest, .md, assets/,
    optional bench working files, optional sidecar/slice-cache) to drive reaudit() end to end
    without ever reading a real PDF (audit_convert is monkeypatched by every caller here)."""
    source = source or f"{name}.pdf"
    held_dir = cas.HELD / sha16
    if held_dir.exists():
        shutil.rmtree(held_dir)
    held_dir.mkdir(parents=True)
    (held_dir / "assets").mkdir()
    (held_dir / "assets" / "img.png").write_bytes(b"PNG")
    (held_dir / f"{name}.md").write_text(
        f"---\nsource_sha256: {sha16}\n---\n{held_body}\n", encoding="utf-8")
    manifest = {
        "source": source,
        "source_sha256": sha16,
        "lane": lane,
        "fidelity": {
            "version": 1,
            "convert": {"doc_survival": 0.93, "pages_flagged": [3, 7], "runs_total": 500,
                        "tripwires": {"degeneration": False}, "kind": "fidelity", "runs": []},
            "verdict": old_verdict,
        },
    }
    if with_analyst_block:
        manifest["analyst"] = {"model": "qwen3:8b", "chunks_passed": 900}
        manifest["fidelity"]["analyst"] = {"doc_survival": 0.94, "runs": [], "runs_total": 300}
    (held_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if with_sidecar:
        (held_dir / f"{name}{cas.MARKER_BODY_SUFFIX}").write_text(sidecar_text, encoding="utf-8")
    if with_slice_cache:
        slice_dir = cas.CHUNK_WORK / sha16 / "slice-00000-00099"
        slice_dir.mkdir(parents=True, exist_ok=True)
        (slice_dir / "slice.md").write_text(sidecar_text, encoding="utf-8")
    if with_bench_files:
        (held_dir / f"{name}.md.bench-bak").write_text("stale backup", encoding="utf-8")
        (held_dir / "repairs.jsonl").write_text('{"x": 1}\n', encoding="utf-8")
        (held_dir / "REPAIRS.md").write_text("# repairs\n", encoding="utf-8")
    done_dir = cas.fp_paths.root("drop_done")
    done_dir.mkdir(parents=True, exist_ok=True)
    (done_dir / source).write_bytes(b"%PDF-1.4 fake\n")
    return held_dir, manifest


def run_reaudit(module, bundle_id: str, *, convert_result, analyst_result, dry_run=False):
    """Drive the REAL reaudit() end to end: fidelity_audit's two stage audits monkeypatched
    (compute_verdict stays real), ship() stubbed and its calls recorded, emit() recorded, and
    the staging copy's file LIST captured at the moment shutil.copytree populates it (the
    TemporaryDirectory is gone by the time this returns)."""
    fakes = ReaudFakes(convert_result, analyst_result)
    rec = EmitRecorder()
    ship_calls: list[dict] = []

    def _stub_ship(tmp_dir, bundle_name, source_sha):
        ship_calls.append({"tmp_dir": Path(tmp_dir), "bundle_name": bundle_name,
                            "source_sha": source_sha})

    real_convert = fidelity_audit.audit_convert
    real_analyst = fidelity_audit.audit_analyst
    fidelity_audit.audit_convert = fakes.audit_convert
    fidelity_audit.audit_analyst = fakes.audit_analyst
    module.emit = rec
    real_ship = module.ship
    module.ship = _stub_ship
    captured_staging_files: list[str] = []
    real_copytree = shutil.copytree
    held_dir_path = (module.HELD / bundle_id).resolve()

    def _spy_copytree(src, dst, *a, **kw):
        result = real_copytree(src, dst, *a, **kw)
        # shutil.copytree recurses into itself for subdirectories (e.g. assets/), so the
        # FIRST call this spy sees is often a nested one, not held_dir -> staging — match on
        # identity (src resolves to held_dir), not call order.
        try:
            src_is_held_dir = Path(src).resolve() == held_dir_path
        except (TypeError, OSError):
            src_is_held_dir = False
        if src_is_held_dir and not captured_staging_files:
            captured_staging_files.extend(
                sorted(p.relative_to(dst).as_posix() for p in Path(dst).rglob("*")
                       if p.is_file())
            )
        return result

    shutil.copytree = _spy_copytree
    try:
        try:
            module.reaudit(bundle_id, dry_run=dry_run)
            raised = None
        except SystemExit as exc:
            raised = exc
    finally:
        fidelity_audit.audit_convert = real_convert
        fidelity_audit.audit_analyst = real_analyst
        module.ship = real_ship
        shutil.copytree = real_copytree
    return fakes, rec, ship_calls, raised, captured_staging_files


# (1) + (2) + (3) + (5) + (7): a healthy flag/pass re-audit on a bundle with a sidecar,
# bench files, and blocks.json.
held1, manifest1 = make_held_bundle("shaa1111111111111", name="paper1")
(held1 / "blocks.json").write_text('{"blocks": []}', encoding="utf-8")
fakes1, rec1, ships1, raised1, files1 = run_reaudit(
    cas, "shaa1111111111111", convert_result=PASS_CONVERT, analyst_result=PASS_ANALYST)

# (1) staging copy: bench files EXCLUDED, assets/blocks.json/sidecar INCLUDED.
check(raised1 is None, "(1) a healthy re-audit runs to completion, no refusal")
check("assets/img.png" in files1, "(1) staging copy carries assets/")
check("blocks.json" in files1, "(1) staging copy carries blocks.json")
check("paper1.marker.txt" in files1, "(1) staging copy carries the J33 sidecar")
check("paper1.md.bench-bak" not in files1, "(1) staging copy EXCLUDES the stale .bench-bak")
check("repairs.jsonl" not in files1, "(1) staging copy EXCLUDES repairs.jsonl")
check("REPAIRS.md" not in files1, "(1) staging copy EXCLUDES REPAIRS.md")

reshipped1 = sorted(cas.HELD.glob("shaa1111111111111--reshipped-*"))
check(len(reshipped1) == 1, "(5) held dir renamed to a single --reshipped-<stamp> sibling")
check(not (cas.HELD / "shaa1111111111111").exists(),
      "(5) the OLD held/<ID> path no longer exists under its own name")
final_manifest1 = (json.loads((reshipped1[0] / "manifest.json").read_text(encoding="utf-8"))
                    if reshipped1 else {})

# (2) final block + reaudit provenance present; HISTORICAL convert/analyst untouched; verdict
# computed from final (D-1 control: history says fail, final says otherwise -> flag/pass).
check(final_manifest1.get("fidelity", {}).get("convert") == manifest1["fidelity"]["convert"],
      "(2) the HISTORICAL convert block is content-identical before/after (never overwritten)")
check(final_manifest1.get("fidelity", {}).get("analyst") == manifest1["fidelity"]["analyst"],
      "(2) the HISTORICAL analyst block is content-identical before/after (never overwritten)")
check(final_manifest1.get("fidelity", {}).get("final", {}).get("convert") == PASS_CONVERT,
      "(2) fidelity.final.convert IS the new audit, distinct from history")
check(final_manifest1.get("fidelity", {}).get("verdict") == "pass",
      "(2) D-1: verdict is computed from FINAL (pass) even though history says fail")
reaudit_prov1 = final_manifest1.get("fidelity", {}).get("reaudit", {})
check(reaudit_prov1.get("from", {}).get("verdict") == "fail",
      "(2) reaudit provenance names the OLD (historical) verdict")
check(reaudit_prov1.get("from", {}).get("convert", {}).get("pages_flagged") == 2,
      "(2) reaudit provenance summarizes the historical convert block (pages_flagged COUNT)")
check(reaudit_prov1.get("reason") == "repair-bench" and reaudit_prov1.get("by") ==
      "convert_and_ship --reaudit", "(2) reaudit provenance names its own reason/author")

# (3) events: audit/scored phase=final carries source/verdict/degeneration (bless()-shaped);
# audit/reaudit carries from_verdict + verdict + reference.
scored_final1 = [f for k, f in rec1.events if k == "audit/scored" and f.get("phase") == "final"]
check(len(scored_final1) == 1, "(3) exactly one phase=final audit/scored event")
check(bool(scored_final1) and scored_final1[0].get("source") == manifest1["source"]
      and scored_final1[0].get("verdict") == "pass"
      and scored_final1[0].get("degeneration") is False,
      "(3) phase=final audit/scored carries source + verdict + degeneration (assay.rs::bless)")
reaudit_events1 = [f for k, f in rec1.events if k == "audit/reaudit"]
check(len(reaudit_events1) == 1, "(3) exactly one audit/reaudit event")
check(bool(reaudit_events1) and reaudit_events1[0].get("from_verdict") == "fail"
      and reaudit_events1[0].get("verdict") == "pass"
      and reaudit_events1[0].get("reference") == "sidecar",
      "(3) audit/reaudit carries from_verdict + verdict + reference")

# (5) flag/pass: ship() called with the STAGING dir (never held/), supersede stamped reason
# "reaudit".
check(len(ships1) == 1, "(5) ship() called exactly once on a flag/pass verdict")
check(bool(ships1) and ships1[0]["tmp_dir"] != held1 and "fp-reaudit-" in str(ships1[0]["tmp_dir"]),
      "(5) ship() received the STAGING (tempfile) dir, never held/<ID> itself")
check(final_manifest1.get("supersede", {}).get("reason") == "reaudit",
      "(5) supersede stamped with reason='reaudit'")
check(final_manifest1.get("supersede", {}).get("from_verdict") == "fail",
      "(5) supersede names the OLD verdict as from_verdict")

# (7) THE REFERENCE CONTROL: audit_analyst was handed the SIDECAR text, never the held .md —
# sidecar_text and held_body were planted DIFFERENT on purpose (the decoy).
check(len(fakes1.analyst_calls) == 1, "(7) audit_analyst called exactly once")
check(bool(fakes1.analyst_calls)
      and fakes1.analyst_calls[0]["marker_markdown"] == "MARKER BODY REFERENCE TEXT",
      "(7) audit_analyst's reference arg IS the sidecar text")
check(bool(fakes1.analyst_calls)
      and fakes1.analyst_calls[0]["marker_markdown"] != "held post-analyst body text\n",
      "(7) decoy: audit_analyst's reference arg is NOT the held .md body")
check(bool(fakes1.analyst_calls)
      and "held post-analyst body text" in fakes1.analyst_calls[0]["analyst_markdown"],
      "(7) audit_analyst's second arg IS the held-post-analyst body (frontmatter split correctly)")

# (4) still-fail: manifest written IN PLACE at held/<ID>, ship NOT called, no sibling created.
held2, manifest2 = make_held_bundle("shaa2222222222222", name="paper2")
fakes2, rec2, ships2, raised2, _files2 = run_reaudit(
    cas, "shaa2222222222222", convert_result=PASS_CONVERT, analyst_result=FAIL_ANALYST)
check(raised2 is None, "(4) a still-fail re-audit does not raise")
check(len(ships2) == 0, "(4) ship() is NOT called when the verdict stays fail")
check(not list(cas.HELD.glob("shaa2222222222222--reshipped-*")),
      "(4) no --reshipped- sibling on a still-fail verdict")
check(not list(cas.HELD.glob("shaa2222222222222--superseded-*")),
      "(4) no --superseded- sibling either (_enforce_hold never runs on a fresh fail)")
still_manifest2 = json.loads((cas.HELD / "shaa2222222222222" / "manifest.json")
                              .read_text(encoding="utf-8"))
check(still_manifest2.get("fidelity", {}).get("verdict") == "fail",
      "(4) the manifest IN PLACE at held/<ID> now carries the still-fail verdict")
check("final" in still_manifest2.get("fidelity", {}),
      "(4) the final block IS written even on a still-fail verdict (the record of the attempt)")

# (6) refusal: no sidecar + no slice cache + manifest HAS an analyst block -> refused, held
# bundle byte-unchanged (hashed before/after).
held3, manifest3 = make_held_bundle("shaa3333333333333", name="paper3",
                                     with_sidecar=False, with_slice_cache=False,
                                     with_analyst_block=True)


def _hash_dir(d):
    return sorted(
        (str(p.relative_to(d)), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in d.rglob("*") if p.is_file()
    )


before3 = _hash_dir(held3)
fakes3, rec3, ships3, raised3, _files3 = run_reaudit(
    cas, "shaa3333333333333", convert_result=PASS_CONVERT, analyst_result=PASS_ANALYST)
after3 = _hash_dir(held3)
check(isinstance(raised3, SystemExit) and bool(raised3.code), "(6) refusal exits non-zero")
check(before3 == after3, "(6) held bundle byte-unchanged (hashed) after a refusal")
check(len(fakes3.convert_calls) == 0 and len(fakes3.analyst_calls) == 0,
      "(6) neither audit runs at all on a refusal")
refused3 = [f for k, f in rec3.events if k == "audit/reaudit_refused"]
check(len(refused3) == 1 and refused3[0].get("reason") == "analyst reference unavailable",
      "(6) audit/reaudit_refused names reason='analyst reference unavailable'")
check(len(ships3) == 0, "(6) ship() never called on a refusal")

# (9) missing PDF -> refused, distinct reason, nothing runs.
held9, manifest9 = make_held_bundle("shaa9999999999999", name="paper9")
(cas.fp_paths.root("drop_done") / manifest9["source"]).unlink()
fakes9, rec9, ships9, raised9, _files9 = run_reaudit(
    cas, "shaa9999999999999", convert_result=PASS_CONVERT, analyst_result=PASS_ANALYST)
check(isinstance(raised9, SystemExit) and bool(raised9.code), "(9) missing PDF exits non-zero")
check(len(fakes9.convert_calls) == 0, "(9) audit_convert never called when the PDF is missing")
check(len(ships9) == 0, "(9) ship() never called")
refused9 = [f for k, f in rec9.events if k == "audit/reaudit_refused"]
check(len(refused9) == 1 and refused9[0].get("reason") == "pdf missing",
      "(9) audit/reaudit_refused names reason='pdf missing'")

# (8) --dry-run: no manifest write, no ship, ZERO events appended to the REAL events.jsonl
# (emit is NOT monkeypatched for this one check — the real writer is exercised).
held8, manifest8 = make_held_bundle("shaa8888888888888", name="paper8")
events_path8 = cas.fp_paths.root("events")
before_lines8 = (events_path8.read_text(encoding="utf-8").count("\n")
                 if events_path8.exists() else 0)
real_convert8, real_analyst8 = fidelity_audit.audit_convert, fidelity_audit.audit_analyst
fakes8 = ReaudFakes(PASS_CONVERT, PASS_ANALYST)
fidelity_audit.audit_convert = fakes8.audit_convert
fidelity_audit.audit_analyst = fakes8.audit_analyst
real_ship8 = cas.ship
ship_calls8: list = []
cas.ship = lambda *a, **k: ship_calls8.append(a)
try:
    cas.reaudit("shaa8888888888888", dry_run=True)
finally:
    fidelity_audit.audit_convert = real_convert8
    fidelity_audit.audit_analyst = real_analyst8
    cas.ship = real_ship8
after_lines8 = (events_path8.read_text(encoding="utf-8").count("\n")
                if events_path8.exists() else 0)
check(after_lines8 == before_lines8, "(8) --dry-run appended ZERO lines to the real events.jsonl")
check(len(ship_calls8) == 0, "(8) --dry-run never calls ship()")
manifest8_after = json.loads((cas.HELD / "shaa8888888888888" / "manifest.json")
                              .read_text(encoding="utf-8"))
check("final" not in manifest8_after.get("fidelity", {}),
      "(8) --dry-run writes NOTHING back to held/<ID>/manifest.json")
check(not list(cas.HELD.glob("shaa8888888888888--reshipped-*")),
      "(8) --dry-run creates no --reshipped- sibling")

# ---------- T19 vocabulary parity (audit/reaudit*, J31) ----------
print("T19 vocabulary parity")
vocab19 = (HERE.parent / "windows-widget" / "src" / "event-vocab.js").read_text(encoding="utf-8")
manual19 = (HERE.parent / "docs" / "22-engineering-manual.html").read_text(encoding="utf-8")
for key19 in ("audit/reaudit", "audit/reaudit_refused"):
    check(f'"{key19}"' in vocab19, f"shared event-vocab.js speaks {key19}")
for name19 in ("reaudit", "reaudit_refused"):
    check(name19 in manual19, f"docs/22 names {name19}")
src19 = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
emitted19 = set(re.findall(r'emit\("audit", "([a-z_]+)"', src19))
for name19 in ("reaudit", "reaudit_refused", "scored", "flagged"):
    check(name19 in emitted19, f"converter really emits audit/{name19}")

# ---------- NEGATIVE CONTROL for the whole verb ----------
# Blank `fid["final"] = final` inside reaudit() and watch check (2)'s "final block present"
# assertion go red — proving that check really watches this one line.
print("T19 negative control: fid['final'] = final removed")
NC19_SRC = (HERE / "convert_and_ship.py").read_text(encoding="utf-8")
NC19_LINES = NC19_SRC.splitlines(keepends=True)
_nc19_fn = next(n for n in ast.walk(ast.parse(NC19_SRC))
                if isinstance(n, ast.FunctionDef) and n.name == "reaudit")
_nc19_removed = 0
for _n in ast.walk(_nc19_fn):
    if (isinstance(_n, ast.Assign) and len(_n.targets) == 1
            and isinstance(_n.targets[0], ast.Subscript)
            and isinstance(_n.targets[0].value, ast.Name) and _n.targets[0].value.id == "fid"
            and isinstance(_n.targets[0].slice, ast.Constant)
            and _n.targets[0].slice.value == "final"):
        for _ln in range(_n.lineno - 1, _n.end_lineno):
            NC19_LINES[_ln] = "\n"
        _nc19_removed += 1
check(_nc19_removed == 1, f"the control really removed fid['final'] = final ({_nc19_removed})")
nc19 = types.ModuleType("convert_and_ship_nc19")
nc19.__file__ = str(HERE / "convert_and_ship.py")
exec(compile("".join(NC19_LINES), nc19.__file__, "exec"), nc19.__dict__)  # noqa: S102

held_nc, manifest_nc = make_held_bundle("shncncncncncncnc1", name="papernc")
_fakes_nc, _rec_nc, _ships_nc, _raised_nc, _files_nc = run_reaudit(
    nc19, "shncncncncncncnc1", convert_result=PASS_CONVERT, analyst_result=FAIL_ANALYST)
nc_manifest = json.loads((cas.HELD / "shncncncncncncnc1" / "manifest.json")
                          .read_text(encoding="utf-8"))
check("final" not in nc_manifest.get("fidelity", {}),
      "NEGATIVE CONTROL: with fid['final'] = final removed, the final block is really absent — "
      "check (2)'s 'fidelity.final.convert IS the new audit' assertion would fail against this")
check(nc_manifest.get("fidelity", {}).get("verdict") == "fail",
      "NEGATIVE CONTROL: verdict is still computed correctly (only the final BLOCK is missing, "
      "isolating the control to exactly the one removed line)")


# ---------- verdict ----------
cas._run_marker = REAL_RUN_MARKER
shutil.rmtree(QUARANTINE, ignore_errors=True)
total = sum(1 for _ in FAILURES)
n_checks = len(re.findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"), re.M))
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
sys.exit(1 if FAILURES else 0)
