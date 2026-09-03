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

    CHUNK_TARGET = 6000

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
          if k not in ("chunks_generated", "goodput_accepted_tok_s", "chunks_resumed")}
try:
    rec17b, _f, _b = drive_inline(cas, "t17-work-lean", LEAN17)
    d17b = (rec17b.named("analyst/done") or [{}])[0]
except Exception as exc:  # noqa: BLE001 — a raise here IS the failure this check is for
    d17b = {"__raised__": repr(exc)[:120]}
check(bool(d17b) and set(d17b) == set(d17),   # bool(): two empty sets are not agreement
      f"an older analyst's meta still emits the FULL key set ({d17b.get('__raised__', '')})")
check(d17b.get("chunks_generated", 0) is None and d17b.get("goodput_accepted_tok_s", 0) is None
      and d17b.get("chunks_resumed", 0) is None,
      "a missing counter emits null — honest absence (docs/34), never an invented 0")

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


# ---------- verdict ----------
cas._run_marker = REAL_RUN_MARKER
shutil.rmtree(QUARANTINE, ignore_errors=True)
total = sum(1 for _ in FAILURES)
n_checks = len(re.findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"), re.M))
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
sys.exit(1 if FAILURES else 0)
