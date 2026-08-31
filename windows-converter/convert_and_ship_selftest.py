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
                 page_range=None, progress_prefix=""):
        batch = None
        args = list(extra)
        for i, a in enumerate(args):
            if a == "--recognition_batch_size" and i + 1 < len(args):
                batch = int(args[i + 1])
        n = self.seen[page_range] = self.seen.get(page_range, 0) + 1
        self.calls.append({"page_range": page_range, "batch": batch,
                           "prefix": progress_prefix, "attempt": n})
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
SLICE_ARGS = ["--recognition_batch_size", "8"]


def run_slice(stub, start=0, end=199, batch=8):
    rec = with_stub(stub)
    out_root = QUARANTINE / "work" / "marker-out"
    result = cas._run_slice_with_retries(
        "stub.pdf", QUARANTINE / "stub.pdf", "stub", out_root,
        SLICE_ARGS, end - start + 1, start, end, batch)
    return result, rec, stub


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

# ---------- T7: vocabulary parity (converter -> Room -> manual) ----------
print("T7 vocabulary parity")
room = (HERE.parent / "windows-widget" / "src" / "room.js").read_text(encoding="utf-8")
manual = (HERE.parent / "docs" / "22-engineering-manual.html").read_text(encoding="utf-8")
LADDER_VOCAB = ["convert/stalled", "convert/slice_retry", "convert/slice_retry_succeeded",
                "convert/slice_split", "convert/timeout", "convert/chunk_batch_invalid",
                "convert/chunk_batch_unreadable", "convert/asset_range_warning",
                "convert/slice", "convert/converted", "intake/failed"]
for key in LADDER_VOCAB:
    check(f'"{key}"' in room, f"room.js speaks {key}")
for name in ["slice_retry_succeeded", "slice_split", "timeout", "chunk_batch_invalid",
             "chunk_batch_unreadable", "asset_range_warning", "retry_wall_s",
             "pages_converted_this_run"]:
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
check('"convert/ollama_unloaded"' in room, "room.js speaks convert/ollama_unloaded")
check("ollama_unloaded" in (HERE.parent / "docs" / "22-engineering-manual.html").read_text(
    encoding="utf-8"), "docs/22 names ollama_unloaded")

# ---------- verdict ----------
cas._run_marker = REAL_RUN_MARKER
shutil.rmtree(QUARANTINE, ignore_errors=True)
total = sum(1 for _ in FAILURES)
n_checks = len(re.findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"), re.M))
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
sys.exit(1 if FAILURES else 0)
