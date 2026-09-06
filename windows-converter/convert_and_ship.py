"""Desktop GPU converter (Phase 4 slice 1): PDF -> Marker -> bundle -> ThinkPad staging.

The output bundle is format-identical to linux-converter's (docs/12 contract): the name
budget, frontmatter, link rewrite, manifest keys, and dot-then-atomic delivery all mirror
converter/bundle.py so the existing exporter consumes it with zero ThinkPad changes.

Run with the marker-env interpreter:
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe convert_and_ship.py <pdf> [--dry-run]

Engine routing (docs/11 policy table): probe the text layer with pymupdf; an adequate
layer that self-identifies as OCR (glyphless/invisible fonts) is untrusted and re-read
via --strip_existing_ocr; an adequate real layer is trusted (Marker default); no layer
means Marker's own need-based OCR fires. Batch cap 32 everywhere OCR may run (the
force-OCR VRAM-fill stall, docs/11 Phase 1).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

import fp_paths
# J24: the block-record sidecar's PURE half (page correction + merge). Imported at module level
# on purpose — marker_blocks defers every `marker` import into main(), so this costs nothing and
# cannot make the converter unimportable when the engine is broken.
import marker_blocks
from events import emit

# ---------- Survival Audit hooks (docs/15) — report-only, never raise ----------

def _audit_convert_safe(src, body: str, lane: str, tmp_dir: Path, manifest: dict) -> None:
    """Score the convert stage (PDF witness vs Marker markdown) into manifest['fidelity'].
    Report-only: the verdict is recorded but gates nothing. An audit failure must never
    fail the conversion (docs/15 §8)."""
    try:
        import fidelity_audit as fa
        assets_dir = tmp_dir / "assets"
        asset_count = sum(1 for _ in assets_dir.iterdir()) if assets_dir.exists() else None
        conv = fa.audit_convert(src, body, lane, asset_count=asset_count)
        manifest["fidelity"] = fa.build_fidelity_block(conv, None)
        tw = conv["tripwires"]
        name = getattr(src, "name", str(src))
        # NUM-3: `runs` stays the SHOWN (capped) count for wire compatibility; runs_total is
        # the truth beside it (SYM-066: the night "25" hid 634)
        emit("audit", "scored", source=name, phase="convert", kind=conv["kind"],
             doc_survival=conv["doc_survival"], runs=len(conv["runs"]),
             runs_total=conv.get("runs_total"),  # review M2: an absent total stays None —
             # a fallback to the SHOWN count asserted the cap was the count
             degeneration=tw["degeneration"], verdict=manifest["fidelity"]["verdict"])
        if manifest["fidelity"]["verdict"] != "pass":
            emit("audit", "flagged", source=name, phase="convert",
                 verdict=manifest["fidelity"]["verdict"])
    except Exception as exc:  # noqa: BLE001 — telemetry must never break the line
        emit("audit", "error", phase="convert", error=str(exc)[:150])


def _audit_analyst_safe(marker_body: str, analyst_body: str, manifest: dict, name: str = "") -> None:
    """Score the analyst stage (Marker doc vs analyst output) into manifest['fidelity'].
    Report-only; never raises (docs/15 §8)."""
    try:
        import fidelity_audit as fa
        an = fa.audit_analyst(marker_body, analyst_body)
        fid = manifest.get("fidelity")
        if fid and "convert" in fid:
            fid["analyst"] = an
            fid["verdict"] = fa.compute_verdict(fid["convert"], an)
        else:
            verdict = "fail" if (an["doc_survival"] < fa.ANALYST_DOC_FAIL
                                 or any(r["words"] >= fa.ANALYST_RUN_WORDS for r in an["runs"])) else "pass"
            manifest["fidelity"] = {"version": fa.SCHEMA_VERSION, "analyst": an, "verdict": verdict}
        emit("audit", "scored", source=name, phase="analyst",
             doc_survival=an["doc_survival"], runs=len(an["runs"]),
             runs_total=an.get("runs_total"),  # M2: None over a masquerading fallback
             verdict=manifest["fidelity"]["verdict"])
        if manifest["fidelity"]["verdict"] == "fail":
            emit("audit", "flagged", source=name, phase="analyst", verdict="fail")
    except Exception as exc:  # noqa: BLE001
        emit("audit", "error", phase="analyst", error=str(exc)[:150])


MARKER = Path(r"C:\Users\Bndit\ml\marker-env\Scripts\marker_single.exe")
# J24 (signed Rab 2026-09-01): the block-record sidecar — a marker_single drop-in that renders
# the SAME built document twice (markdown, then chunks) so page/polygon/bbox stop being computed
# and thrown away. See marker_blocks.py's docstring for why it is a subprocess and not an import:
# _run_marker's stall monitor, tree-kill, pipe drain and page-scaled timeout are all
# subprocess-shaped, and none of them change here.
MARKER_BLOCKS = Path(__file__).resolve().with_name("marker_blocks.py")
# DERIVED from MARKER, never retyped (SYM-039's rule): the sidecar must run under the SAME
# interpreter marker_single.exe wraps, or it imports a different marker than the one measured.
MARKER_PYTHON = MARKER.with_name("python.exe")
# The kill-switch. `FP_BLOCKS=off` puts this file back on marker_single.exe byte for byte —
# no lever file, because a lever is a promise to keep it working, and this is the escape hatch
# for the case where it is NOT working. Costs nothing when unset (the normal case).
BLOCKS_ENV = "FP_BLOCKS"
BLOCKS_BUNDLE_FILE = "blocks.json"  # the name inside the bundle, beside manifest.json
# J33 (signed Rab 2026-09-05: name = "<bundle_name>.marker.txt", vault OUT — same shape as
# BLOCKS_BUNDLE_FILE's lever, docs/54 §4 slot 3). A non-".md" suffix on purpose: it sidesteps
# every "exactly one .md" guard in the pipeline (six of them, docs/54 §3) rather than teaching
# each one a second filename.
MARKER_BODY_SUFFIX = ".marker.txt"
ANCHOR = fp_paths.root("anchor")
PENDING = fp_paths.root("pending")  # deferred-analyst queue (widget card)
HELD = fp_paths.root("held")  # audit-failed bundles (enforce mode; assay card)
AUDIT_MODE_FILE = fp_paths.root("audit_mode")  # report | enforce (docs/15 §12)
REMOTE = "rab@archlinux"
REMOTE_STAGING = "~/file-portal/library/staging"
MIN_CHARS_PER_PAGE = 100  # provisional, same value + revisit-note as the ThinkPad's
RECOGNITION_BATCH = 32
CONVERTER_VERSION = "0.1.0-desktop"
# Stage A (docs/18 §5.1, decided 2026-07-31): progress frozen this long while Marker still
# runs = the stall signature → kill early. Generous vs the longest legitimate quiet phase
# (model load ~1-2 min); both wedge species (S48 pipe-deadlock, S45 VRAM-thrash) freeze for hours.
STALL_FROZEN_S = 900

# Recovery ladder for deterministic stall handling. On a stall we first retry with one lower
# recognition batch and then split the range in half. Both actions are bounded and observable
# via `convert` events; when both still fail, the slice fails the job as before.
STALL_RETRY_SPLIT_MIN_PAGES = 50  # lever-waiver: Rab signed OK-17 2026-08-30; review evidence: stalls are VRAM-state-driven, a split below this cannot help
STALL_RETRY_MAX_SPLITS = 2        # lever-waiver: Rab signed OK-17; bounds the ladder at 9 Marker invocations per slice
STALL_RECOVERY_BATCH = 4          # lever-waiver: Rab signed OK-17; recovery-only memory-relief value, deliberately BELOW CHUNK_BATCH_ALLOWED — never a lever choice (review 2026-08-30)


class _MarkerRunError(RuntimeError):
    """Base marker-runtime failure with structured diagnostics."""


class _MarkerStallError(_MarkerRunError):
    """Raised when Marker progress is frozen while still running."""

    def __init__(self, message: str, *, frozen_s: int, elapsed_s: int,
                 source: str, page_range: str | None, signature: dict) -> None:
        super().__init__(message)
        self.frozen_s = frozen_s
        self.elapsed_s = elapsed_s
        self.source = source
        self.page_range = page_range
        self.signature = signature


class _MarkerTimeoutError(_MarkerRunError):
    """Raised when the outer timeout fires while Marker is still running."""

    def __init__(self, message: str, *, elapsed_s: int, pages: int, timeout_s: int) -> None:
        super().__init__(message)
        self.elapsed_s = elapsed_s
        self.pages = pages
        self.timeout_s = timeout_s


# S42: live convert progress (docs/16 §8 #3). The widget's line.rs reads this file while a
# convert holds the .gpu-lock; the Room shows the real Marker/surya stage + per-page count.
# ENTIRELY best-effort: writing/parsing this must never affect the conversion (see convert()).
PROGRESS_FILE = fp_paths.root("convert_progress")
# surya/tqdm bar, e.g. "Recognizing Layout:  33%|###3      | 1/3 [00:04<00:09, 4.67s/it]".
# Indeterminate bars ("Detecting bboxes: 0it [...]") simply don't match and are skipped.
_TQDM_RE = re.compile(r"([A-Za-z][\w ()/-]*?):\s*(\d{1,3})%\|[^|]*\|\s*(\d+)\s*/\s*(\d+)")


def _write_progress(stage: str, pct: int, n: int, total: int,
                    context: dict | None = None) -> None:
    try:
        record = {
            "v": 2, "writer_pid": os.getpid(),
            "stage": stage, "pct": pct, "n": n, "total": total,
            "frac": max(0.0, min(1.0, pct / 100.0)),
        }
        record.update(context or {})
        PROGRESS_FILE.write_text(json.dumps(record), encoding="utf-8")
    except OSError:
        pass  # progress is cosmetic — a write failure must never matter


class _ProgressLiveness:
    """Thread-safe semantic liveness, independent of the best-effort progress file.

    ANY change to the valid (stage, n, total) tuple refreshes liveness, including an n
    regression or total change at a stage boundary.  Repeating the identical tuple does not.
    The stdout reader remains the only observer; the monitor only reads this small state.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._last: tuple[str, int, int] | None = None
        self._changed_at = clock()

    def observe(self, stage: str, pct: int, n: int, total: int,
                context: dict | None = None) -> bool:
        key = (stage, n, total)
        with self._lock:
            if key == self._last:
                return False
            self._last = key
            self._changed_at = self._clock()
        _write_progress(stage, pct, n, total, context)
        return True

    def age(self) -> float:
        with self._lock:
            return max(0.0, self._clock() - self._changed_at)


def _clear_progress() -> None:
    try:
        PROGRESS_FILE.unlink()
    except OSError:
        pass


# Stage E (docs/19 §5): the ledger-fed promise, written ONCE at convert start so the widget can
# project it verbatim. Python is the only authority on the estimate (blind spot #1: never derive
# the same number twice in two languages); line.rs reads this file, it never recomputes it.
ESTIMATE_FILE = fp_paths.root("convert_estimate")


def _resumable_pages(source_sha: str, pages: int, extra: list[str]) -> int:
    """NUM-4: how many pages the slice cache will ACTUALLY resume, so the promise is scoped
    to the work in front of this run. Review M3: the first cut counted `.done` PRESENCE only,
    so a Marker upgrade or lane change (every cached slice failing identity at convert time)
    produced a 0-second promise for a multi-hour book — the failure mode that reads as
    completion. This peek now runs the SAME identity comparison as the resume gate
    (`_done_identity_mismatch`); a torn or mismatched `.done` simply doesn't count."""
    try:
        book_work = CHUNK_WORK / source_sha[:16]
        if not book_work.is_dir():
            return 0
        import marker  # marker-env only; the same version stamp the resume gate compares
        marker_version = getattr(marker, "__version__", "unknown")
        done_pages = 0
        for d in book_work.iterdir():
            m = re.fullmatch(r"slice-(\d{5})-(\d{5})", d.name)
            if not (m and (d / ".done").is_file()):
                continue
            try:
                prior = json.loads((d / ".done").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(prior, dict):
                continue
            if _done_identity_mismatch(prior, source_sha, extra, marker_version):
                continue
            done_pages += int(m.group(2)) - int(m.group(1)) + 1
        return min(done_pages, pages)
    except (OSError, ImportError):
        return 0


def _write_estimate_safe(source: str, pages: int, lane: str, chars: float,
                         resumable_pages: int = 0) -> dict | None:
    """File the conversion's PROMISE beside its progress: the similarity estimate the ledger can
    back, or an honest absence. Best-effort in every direction — the promise must never cost
    the conversion (S42 rule). NUM-4: the ETA covers only the pages THIS run must convert;
    `resumed_pages_assumed` records the peek so an optimistic promise is auditable."""
    try:
        pages_this_run = max(0, pages - resumable_pages)
        est = estimate_from_ledger(pages, lane, chars)
        payload = {"source": source, "pages": pages, "lane": lane,
                   "pages_this_run": pages_this_run,
                   "resumed_pages_assumed": resumable_pages}
        if est:
            est["eta_s"] = int(est["s_per_page"] * pages_this_run)
            payload.update(est)
            emit("convert", "estimate", source=source, eta_s=est["eta_s"],
                 s_per_page=est["s_per_page"], basis=est["basis"], samples=est["samples"],
                 pages_this_run=pages_this_run, resumed_pages_assumed=resumable_pages)
        else:
            payload["basis"] = "none"  # no evidence — the glass must say so, not guess
        ESTIMATE_FILE.write_text(json.dumps(payload), encoding="utf-8")
        return est
    except Exception:  # noqa: BLE001 — cosmetic bookkeeping, never the line's problem
        return None


def _clear_estimate() -> None:
    try:
        ESTIMATE_FILE.unlink()
    except OSError:
        pass


def _kill_tree(pid: int) -> None:
    """Kill a process AND its descendants. `proc.kill()` alone kills only the console-script /
    venv launcher on Windows — the real python underneath survives and keeps the GPU (the S48
    orphan class). taskkill /T walks the tree. Best-effort: the caller still proc.kill()s."""
    try:
        subprocess.run(["taskkill", "/pid", str(pid), "/t", "/f"],
                       capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001 — killing is a courtesy; the hard timeout still governs
        pass


# ---------- Stage D: chunking (docs/18 §5.2, spec SIGNED with Rab S57) ----------

# Lane-aware, because the lanes cost different VRAM: Valentine peaked ~8 GB at 465 scanned pp.
# Page counts come from the pymupdf probe, never from PDF metadata (which lies).
CHUNK_THRESHOLD_PAGES = {"clean": 600, "scan": 400}
# A lost slice costs ~10 min; each slice re-pays ~90 s of model load (~18 % overhead at
# clean-lane rates). Damodaran (1,356 pp) = 7 slices.
SLICE_PAGES = 200
# The slice recognition batch is a USER LEVER (Rab's framing: 8 "keeps it actually useful",
# 16 the go-faster default, 32 "if I really want to"). Backend truth is this file, re-read per
# slice so an edit mid-book takes effect at the next slice. Unchunked books keep RECOGNITION_BATCH.
CHUNK_BATCH_FILE = fp_paths.root("chunk_batch")
CHUNK_BATCH_ALLOWED = (8, 16, 32)
CHUNK_BATCH_DEFAULT = 16
# Completed slices live HERE, not in the run's temp dir, because resume must survive the process
# that made them: keyed by (source_sha16, page_range) exactly as the spec requires.
CHUNK_WORK = fp_paths.root("chunk_work")


_batch_warned = False  # chunk_batch diagnostics fire once per process, not once per slice


def chunk_batch() -> int:
    """The slice recognition batch lever. Anything unparseable or off-menu falls back to the
    default rather than handing Marker a number nobody chose."""
    global _batch_warned
    try:
        value = int(CHUNK_BATCH_FILE.read_text(encoding="utf-8").strip())
        if value in CHUNK_BATCH_ALLOWED:
            return value
        if not _batch_warned:   # once per process — re-read per slice by signed design (F-09),
            _batch_warned = True  # so a bad lever would otherwise spam one event per slice
            emit("convert", "chunk_batch_invalid", value=value,
                 allowed=",".join(map(str, CHUNK_BATCH_ALLOWED)),
                 fallback=CHUNK_BATCH_DEFAULT)
        return CHUNK_BATCH_DEFAULT
    except FileNotFoundError:
        return CHUNK_BATCH_DEFAULT  # no lever file = the normal pre-lever state, not an anomaly
    except (OSError, ValueError):
        if not _batch_warned:
            _batch_warned = True
            emit("convert", "chunk_batch_unreadable", fallback=CHUNK_BATCH_DEFAULT)
        return CHUNK_BATCH_DEFAULT


# ---------- the card mutex (SYM-033 / SYM-042; signed docs/37 §3.2, Rab 2026-08-17) ----------
#
# Unlike `.gpu-lock` — a write-only busy SIGNAL that only the watcher writes (SYM-032) — this
# is a named OS mutex the kernel enforces for EVERY converter entry: watcher child, --resume,
# --reanalyze, and hand runs (SYM-042's blind spot). Local\ namespace: all entries run in the
# one desktop session. Held for the process lifetime; the OS releases it at exit, and a dead
# holder surrenders it as WAIT_ABANDONED, which is safe to inherit here because the slice
# machinery already publishes atomically (.part -> rename; a torn .done re-converts).
CARD_MUTEX_NAME = os.environ.get("FP_CARD_MUTEX", "Local\\file-portal-card")


def acquire_card_mutex() -> object | None:
    """Blocks (LOUDLY, never silently) until this process owns the card. Returns the handle,
    or None on the one fail-open path: CreateMutexW itself failing, printed and emitted —
    availability over a guard the OS refused to make; the human gate (nvidia-smi, docs/19)
    still stands. Poll interval is env-tunable so the tripwire can run in milliseconds."""
    import ctypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = k32.CreateMutexW(None, False, CARD_MUTEX_NAME)
    if not handle:
        print(f"CARD MUTEX unavailable (CreateMutexW error {ctypes.get_last_error()}) — "
              f"proceeding UNGUARDED", flush=True)
        emit("convert", "card_mutex", state="unavailable")
        return None
    WAIT_ABANDONED, WAIT_TIMEOUT = 0x80, 0x102  # WAIT_OBJECT_0 = 0x00 (immediate acquire; no branch needed for it below)
    poll_ms = int(os.environ.get("FP_CARD_MUTEX_POLL_MS", "30000"))
    result = k32.WaitForSingleObject(handle, 0)
    if result == WAIT_TIMEOUT:
        print(f"CARD BUSY: another converter holds {CARD_MUTEX_NAME} — waiting", flush=True)
        emit("convert", "card_mutex", state="wait")
        while result == WAIT_TIMEOUT:
            result = k32.WaitForSingleObject(handle, poll_ms)
            if result == WAIT_TIMEOUT:
                print("CARD BUSY: still waiting …", flush=True)
    if result == WAIT_ABANDONED:
        # The prior holder died mid-hold. Ownership transferred to us; the on-disk state it
        # left is resumable by design, so proceeding is correct — but say so.
        print("CARD MUTEX inherited from a dead holder (WAIT_ABANDONED) — proceeding", flush=True)
        emit("convert", "card_mutex", state="inherited")
    return handle


def release_card_mutex(handle: object | None) -> None:
    """The tripwire's half — production holds to process exit and lets the OS release."""
    if handle:
        import ctypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.ReleaseMutex(handle)
        k32.CloseHandle(handle)


def should_chunk(pages: int, lane: str) -> bool:
    """docs/18 §5.2's lane-aware threshold. Unknown lanes take the stricter bar."""
    return pages > CHUNK_THRESHOLD_PAGES.get(lane, min(CHUNK_THRESHOLD_PAGES.values()))


def slice_ranges(pages: int, size: int = SLICE_PAGES) -> list[tuple[int, int]]:
    """Clean cuts, no overlap (v1: overlap reconciliation risks SILENT text loss, so the seam
    is recorded instead of smoothed). Returns 0-indexed inclusive [start, end] pairs, which is
    what Marker's --page_range speaks."""
    return [(s, min(s + size, pages) - 1) for s in range(0, pages, size)]


# Asset names carry the page they came from: `_page_413_Figure_0.jpeg`.
#
# **MEASURED, not assumed (S60, the Damodaran acceptance run):** under `--page_range`, Marker
# numbers assets by their ABSOLUTE page in the source PDF — a slice covering pages 200-399 emits
# `_page_200_…` through `_page_399_…`, not `_page_0_…`. Slices therefore never collide and
# nothing needs renumbering. The first cut of this stage assumed run-relative numbering and added
# the slice offset, which double-counted it: a 1,356-page book produced asset pages up to 2553,
# in bands of 400-599, 800-999, 1600-1799 … Links still resolved (filename and reference were
# shifted together, so no figure was lost) but every page number above slice 1 was a lie, which
# would have sent the Repair Bench to the wrong page forever.
#
# The synthetic harness could not catch it: the fake Marker emitted run-relative names because I
# wrote it from the same wrong assumption the code held. Only the real book could tell us.
_ASSET_PAGE = re.compile(r"^_page_(\d+)_")


def asset_page(name: str) -> int | None:
    """The absolute source page a Marker asset came from; None if the name isn't that shape."""
    m = _ASSET_PAGE.match(name)
    return int(m.group(1)) if m else None


def out_of_range_assets(names: list[str], start: int, end: int) -> list[str]:
    """Assets whose page falls outside the slice that produced them. Expected to be empty — this
    is the tripwire on the numbering behaviour above, so that if a future Marker switches to
    run-relative names the merge says so loudly instead of silently mislabelling every page."""
    return [n for n in names
            if (p := asset_page(n)) is not None and not (start <= p <= end)]


def _gpu_signature() -> dict:
    """Best-effort triage facts for a stall's death certificate: GPU util/mem at kill time.
    High util + near-full mem = the VRAM-thrash species; low util = deadlock/IO species.
    Facts only — classification is the reader's job. Never raises."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        util, used, total = (x.strip() for x in out.stdout.strip().split(",")[:3])
        return {"gpu_util_pct": int(util), "gpu_mem_used_mib": int(used),
                "gpu_mem_total_mib": int(total)}
    except Exception:  # noqa: BLE001
        return {}


OLLAMA_URL = os.environ.get("FP_OLLAMA_URL", "http://127.0.0.1:11434")


def _ollama_unload() -> None:
    """OK-16 (signed Rab 2026-08-30): release ollama's VRAM residents before Marker runs.

    Margin hygiene, not a wedge cure — measured 2026-08-31 on the Damodaran 600-799 band:
    the stall pinned 9,726/10,240 MiB with ZERO residents loaded (analyst dead 57 min,
    keep-alive long expired), so Marker alone can fill the card at batch 8. But S60 measured
    batch 16 peaking 9.8/10.2 on its own, so a ~2 GB resident turns ANY batch into that
    stall. Unloading costs the analyst one model reload later (~seconds against a multi-hour
    convert). Entirely best-effort: ollama absent, down, or slow must never delay or fail a
    conversion — silence is the normal case, the event fires only when something was freed."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=3) as r:
            models = [m.get("name") for m in json.load(r).get("models", []) if m.get("name")]
        for name in models:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=json.dumps({"model": name, "keep_alive": 0}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        if models:
            emit("convert", "ollama_unloaded", models=models, count=len(models))
    except Exception:  # noqa: BLE001 — an unreachable ollama is the normal case, not an anomaly
        pass


# ---------- Survival Audit enforcement lever (docs/15 §12) — default off ----------

def audit_mode() -> str:
    """report (default) = the verdict is recorded but the bundle ships anyway; enforce =
    a fidelity verdict of 'fail' parks the bundle instead of shipping. Mirrors
    analyst-mode.txt; re-read per bundle so the widget's report<->enforce toggle is live."""
    try:
        m = AUDIT_MODE_FILE.read_text(encoding="utf-8").strip().lower()
        return m if m in ("report", "enforce") else "report"
    except OSError:
        return "report"


def _raise_audit_verdict(bundle_dir: Path, bundle_name: str) -> None:
    """Raise a fidelity verdict of 'fail' on the algedonic line, WHATEVER audit-mode.txt says
    (docs/30 §5.4, SIGNED by Rab 2026-08-14: "Report means ship anyway, never stay silent").

    The hole this closes (docs/30 §3.3): two independently reasonable defaults — "report mode
    ships, it does not park" and "the alarm keys on the park event" — composed into one neither
    looked like alone. `audit/held` is emitted after `_enforce_hold`'s mode check, so under the
    default lever a book that FAILED its audit shipped and raised nothing at all. Latent rather
    than live on this machine only because audit-mode.txt happens to read `enforce` (docs/31
    §1.14); the lever is one click away from silence either way.

    Emitted from `_enforce_hold`'s doorway because that is the ONE chokepoint every ship path
    passes carrying its final verdict — the same reason that function reads the manifest off
    disk rather than trusting the in-memory copy (docs/28's chokepoint discipline). Strictly
    BEFORE the lever is consulted, so the lever cannot govern what gets written; strictly
    self-contained, so no fault here can change what enforcement then does (docs/15 §8).

    Fields are EXACTLY `audit/held`'s (bundle + source + verdict), for two reasons: the widget's
    dedupe key is the bundle, and both events fire for one book in enforce mode — algedonic.rs
    retires this one in favour of the park, so one book raises one alarm. And a new key would be
    a new undispositioned measurement (docs/29), which is the disease next door."""
    try:
        manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("fidelity", {}).get("verdict") != "fail":
            return
        emit("audit", "verdict_fail", bundle=bundle_name,
             source=manifest.get("source", bundle_name), verdict="fail")
    except Exception:  # noqa: BLE001 — the alarm must never cost a bundle (docs/15 §8)
        pass


def _enforce_hold(bundle_dir: Path, bundle_name: str, source_sha: str) -> bool:
    """If enforce mode AND the on-disk manifest's fidelity verdict is 'fail', park the
    bundle in held/<sha16>/ (with its manifest + assets) instead of shipping, and emit
    audit/held. Reads the manifest from disk so it sees the FINAL (post-analyst) verdict.
    Returns True if held. Default report mode makes the HOLD a no-op — but never the alarm
    (docs/30 §5.4; see _raise_audit_verdict above). Fails OPEN: any error ships the bundle
    (with its verdict-carrying manifest) rather than losing it, and emits audit/error —
    enforcement must never cost a conversion."""
    # docs/30 §5.4 — the verdict is a fact about the BOOK; the lever below only ever decided
    # what to do about it. Raised first, and never from inside the try that governs shipping.
    _raise_audit_verdict(bundle_dir, bundle_name)
    try:
        if audit_mode() != "enforce":
            return False
        manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("fidelity", {}).get("verdict") != "fail":
            return False
        HELD.mkdir(parents=True, exist_ok=True)
        dest = HELD / source_sha[:16]
        if dest.exists():
            # S65: a held bundle can carry HUMAN work now — Repair Bench repairs, a
            # .bench-bak (docs/19 §7). Parking must never destroy a human's repairs: a
            # repairs-bearing occupant keeps its slot and the incoming copy parks BESIDE
            # it, timestamped, both visible on the assay's held rows. (Found 2026-08-07,
            # hours before a live ⟲ re-run would have rmtree'd Valentine's first repair.)
            occupant_repairs = False
            try:
                occupant = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
                occupant_repairs = bool(occupant.get("repairs"))
            except Exception:  # noqa: BLE001 — unreadable manifest = treat as replaceable
                pass
            if occupant_repairs or any(dest.glob("*.bench-bak")):
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                dest = HELD / f"{source_sha[:16]}--superseded-{stamp}"
            else:
                shutil.rmtree(dest)
        shutil.copytree(bundle_dir, dest)
        emit("audit", "held", bundle=bundle_name,
             source=manifest.get("source", bundle_name), verdict="fail")
        print(f"HELD {bundle_name} — audit verdict=fail (enforce mode); not shipped", flush=True)
        return True
    except Exception as exc:  # noqa: BLE001 — enforcement must never lose a bundle
        emit("audit", "error", phase="enforce", error=str(exc)[:150])
        return False


# ---------- the ⟳ remedy's supersede intent (docs/15 §14.2) — best-effort, never raises ----------

# The widget's Assay writes drop/.supersede/<source>.json when Rab clicks ⟳ re-convert. A
# dot-prefixed SUBDIRECTORY, so the watcher (non-file + dotfile + non-.pdf skips), the widget's
# drop counters (.pdf only) and its drill tree (files only) are all blind to it by construction.
SUPERSEDE_DIR_NAME = ".supersede"


def _take_supersede_marker(src: Path) -> dict | None:
    """Consume the ⟳ remedy marker for `src`, if the Assay queued one (docs/15 §14.2).

    CONSUME-ONCE: the marker is deleted the moment it is read — before the conversion runs — so
    an intent can never outlive the click that authored it and latch onto some later drop of the
    same filename. Losing an intent (crash, failed convert) is the SAFE direction: the remedy
    then behaves exactly as it always did — the exporter dedup-skips — and Rab clicks ⟳ again.

    Best-effort in both directions: absent, malformed, or undeletable all yield None rather than
    disturbing the conversion."""
    marker = src.parent / SUPERSEDE_DIR_NAME / f"{src.name}.json"
    data = None
    try:
        if marker.is_file():
            data = json.loads(marker.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a malformed marker must never fail the line
        data = None
    try:
        # Deleted even when unreadable: a corrupt marker must not linger and re-fire later.
        marker.unlink(missing_ok=True)
    except OSError:
        pass
    return data if isinstance(data, dict) else None


def _stamp_supersede_safe(manifest: dict, marker: dict | None, source_sha: str, name: str) -> None:
    """Fold a consumed ⟳ marker into manifest['supersede'] — the opt-in provenance the ThinkPad
    exporter requires before it will REPLACE an already-vaulted note instead of skipping the
    re-convert (docs/15 §14.3, shipped S43). No marker => no field => the exporter's unchanged
    create-only dedup, so an accidental re-drop still skips, by construction.

    The sha guard drops the intent when the file actually converted is not the one the widget
    pointed at (same filename, different book). Never raises — provenance must never cost a
    conversion (docs/15 §8, the S42 fail-safe rule)."""
    try:
        if not marker:
            return
        expected = marker.get("source_sha256")
        if expected and expected != source_sha:
            print(f"SUPERSEDE ignored — marker sha {str(expected)[:16]} != actual "
                  f"{source_sha[:16]} (different file, same name)", flush=True)
            emit("audit", "supersede_ignored", source=name,
                 expected=str(expected)[:16], actual=source_sha[:16])
            return
        manifest["supersede"] = {
            "reason": marker.get("reason") or "audit-remedy",
            "from_verdict": marker.get("from_verdict") or "?",
            "requested_at_epoch_s": marker.get("requested_at_epoch_s"),
        }
        print(f"SUPERSEDE intent carried (from_verdict="
              f"{manifest['supersede']['from_verdict']}) — the exporter may replace the "
              f"vaulted note if this conversion passes the audit", flush=True)
        emit("audit", "supersede", source=name,
             from_verdict=manifest["supersede"]["from_verdict"], sha=source_sha[:16])
    except Exception as exc:  # noqa: BLE001 — provenance must never break the conversion
        emit("audit", "error", phase="supersede", error=str(exc)[:150])


# ---------- J24: the block records join the bundle (signed Rab 2026-09-01) ----------

def _attach_blocks_safe(tmp_dir: Path, manifest: dict, chunk_stats: dict, name: str) -> None:
    """Move the merged block records INTO the bundle and stamp their summary on the manifest.

    In the bundle's own directory, beside manifest.json, because that is the only way they
    travel: every downstream path — the anchor copytree, pending/<id>, held/<sha16>, and the
    `tar -cf - -C tmp_dir .` that ships to the ThinkPad — carries the whole directory. A file
    left in the work dir would exist for one process and then be gone.

    The manifest gets the COUNTS, never the blocks: manifest.json is read by hand and by the
    exporter, and a 1,377-page book's blocks are megabytes. `complete` is the honesty flag —
    false when a slice contributed none (a pre-J24 cached slice, a marker_single fallback, a
    failed chunk render), because a partial record that presented itself as whole would be
    SYM-053's own disease one level up.

    Never raises (docs/15 §8's fail-safe rule): with no blocks, or on any fault here, the bundle
    is byte-for-byte a pre-J24 bundle and the book ships exactly as it does today."""
    try:
        summary = chunk_stats.get("blocks")
        src = chunk_stats.get("blocks_path")
        if not summary or not src or not Path(src).is_file():
            return
        dest = tmp_dir / BLOCKS_BUNDLE_FILE
        shutil.copy2(src, dest)
        summary["bytes"] = dest.stat().st_size  # re-measured at its final resting place
        manifest["blocks"] = summary
        print(f"BLOCKS {summary['blocks_total']} records over "
              f"{summary['pages_with_blocks']} pages "
              f"(slices {summary['slices_with_blocks']}/{summary['slices_total']}, "
              f"complete={summary['complete']}, {summary['bytes']} bytes)", flush=True)
        emit("convert", "blocks", source=name, **{k: summary[k] for k in
             ("blocks_total", "pages_with_blocks", "page_min", "page_max",
              "page_unresolved", "slices_with_blocks", "slices_total", "complete", "bytes")})
        if not summary["complete"]:
            # Named out loud rather than left to be inferred from two counts: a downstream
            # reader that treats a partial record as the book would place highlights on the
            # pages it happens to have and stay silent about the rest.
            emit("convert", "blocks_partial", source=name,
                 slices_with_blocks=summary["slices_with_blocks"],
                 slices_total=summary["slices_total"],
                 page_unresolved=summary["page_unresolved"],
                 unreadable=summary.get("unreadable"))
    except Exception as exc:  # noqa: BLE001 — an addition may never cost a bundle
        emit("convert", "blocks_error", source=name, phase="attach", error=str(exc)[:150])


# ---------- J33: the Marker body sidecar (signed Rab 2026-09-05) ----------

def _write_marker_body_safe(tmp_dir: Path, bundle_name: str, body: str, manifest: dict,
                             name: str = "") -> None:
    """Write the PRE-analyst Marker body beside the bundle as `<bundle_name>.marker.txt`,
    mirroring `_attach_blocks_safe`'s shape exactly: never raises, the manifest gets COUNTS
    (bytes + sha256) never the payload, and on any fault the manifest key is simply absent —
    the book converts exactly as it did before J33 (docs/15 §8's fail-safe rule).

    Called with `body` at the SAME point `_audit_convert_safe` is (before the analyst branch,
    if any) — this is the exact text SYM-073 named as missing: the reference `audit_analyst`
    already compares against in memory (`marker_body` a few lines below, for a book converted
    inline) but that today exists on disk NOWHERE for such a book once `.chunk-work`'s
    LATEST-BOOK retention sweeps the slice cache. Because `tmp_dir` is copied whole to
    anchor/, pending/, held/ and the shipped tar (this function runs before every one of
    those copytree/tar sites), the sidecar rides everywhere the bundle goes — Verified for
    the anchor site (same `shutil.copytree(tmp_dir, ...)` idiom main() uses, exercised by
    T18); Inferred, not separately exercised, for pending/held/the shipped tar, which copy
    or tar the identical `tmp_dir` by the identical mechanism.

    No event is emitted on success: the manifest key IS the record (fewer undispositioned
    keys than a new `convert/marker_body` verb would add), per the coordinator's default in
    docs/54 §J33 step 1. A write fault prints a non-fatal line instead of an event — this
    sidecar is new plumbing with no live reader yet, so a failure here is not (yet) an
    operator-facing alarm; docs/15 §8 already guarantees it costs nothing."""
    tmp: Path | None = None
    try:
        dest = tmp_dir / f"{bundle_name}{MARKER_BODY_SUFFIX}"
        # R3 (verifier GO_AMENDED, 2026-09-05): encode BEFORE touching the destination — a
        # lone surrogate in `body` (an unpaired half of a UTF-16 surrogate pair, which UTF-8
        # cannot represent) must raise HERE, with nothing on disk yet, not after a partial
        # write_text has already left a 0-byte or truncated file behind. Then write atomically
        # via a same-directory .part + os.replace, so a crash mid-write never leaves a torn
        # file at the real name either.
        data = body.encode("utf-8")
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        tmp = None
        data = dest.read_bytes()  # re-measured at its final resting place (J24's own idiom)
        manifest["marker_body"] = {
            "file": dest.name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        print(f"MARKER-BODY {dest.name} ({manifest['marker_body']['bytes']} bytes)", flush=True)
    except Exception as exc:  # noqa: BLE001 — an addition may never cost a bundle
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001 — cleanup must never mask the original fault
                pass
        print(f"MARKER-BODY write failed (non-fatal, no sidecar this run): {exc}", flush=True)


# ---------- bundle contract, mirrored from linux-converter/converter/bundle.py ----------

_IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def rewrite_image_links(markdown: str) -> str:
    def _replace(match: re.Match) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "data:")):
            return match.group(0)
        return f"![[assets/{Path(target).name}]]"

    return _IMAGE_LINK.sub(_replace, markdown)


def clamp_name(name: str, max_bytes: int = 80) -> str:
    if len(name.encode("utf-8")) <= max_bytes:
        return name
    clamped = name.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return clamped.rstrip(" .") or "untitled"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60].rstrip("-") or "untitled"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_frontmatter(engine, lane, lane_reason, chars, ocr, ocr_dpi, converted_at, sha):
    lines = [
        "---",
        "conversion:",
        f"  engine: {engine}",
        f"  lane: {lane}",
        f"  lane_reason: {lane_reason}",
        "  chars_per_page_detected: " + ("~" if chars is None else f"{chars:.1f}"),
        f"  ocr: {'true' if ocr else 'false'}",
    ]
    if ocr_dpi is not None:
        lines.append(f"  ocr_dpi: {ocr_dpi}")
    lines += [
        f"  converted_at: {converted_at.isoformat(timespec='seconds')}",
        f"  source_sha256: {sha}",
        "---",
        "",
    ]
    return "\n".join(lines)


# ---------- probe + engine routing (docs/11 policy table) ----------

_OCR_FONT = re.compile(r"glyphless|invisible|ocr", re.IGNORECASE)


def probe(path: Path) -> tuple[float, int, bool, dict]:
    """chars/page, page count, whether the text layer is an OCR overlay, and THE EVIDENCE.

    OCR layers paint invisible text over the scan image: text render mode 3
    (`get_texttrace` span type 3). Verified live: the Beer book's 2013 Archive.org
    layer is 100% type-3 "Courier"; a born-digital Chromium print is type 0.
    Majority-of-spans rule so a stray invisible watermark can't flip a real layer;
    the font-name check (tesseract's GlyphLessFont etc.) is kept as a secondary.

    NUM-5 (signed 2026-08-31, census N054): the vote's numbers now SURVIVE the decision —
    the returned evidence dict carries invisible/total spans, the ratio, and which font (if
    any) short-circuited the vote, so the routing of every book is auditable from its record
    instead of being destroyed at the moment it decides."""
    invisible_spans = 0
    total_spans = 0
    ocr_font_trigger: str | None = None
    with pymupdf.open(path) as doc:
        pages = doc.page_count or 1
        total = 0
        for page in doc:
            total += len(page.get_text())
            for span in page.get_texttrace():
                total_spans += 1
                if span.get("type") == 3:
                    invisible_spans += 1
                if ocr_font_trigger is None and _OCR_FONT.search(str(span.get("font", ""))):
                    ocr_font_trigger = str(span.get("font", ""))[:60]
    ratio = (invisible_spans / total_spans) if total_spans else 0.0
    ocr_layer = ocr_font_trigger is not None or (total_spans > 0 and ratio > 0.5)
    evidence = {"invisible_spans": invisible_spans, "total_spans": total_spans,
                "invisible_ratio": round(ratio, 4), "ocr_font_trigger": ocr_font_trigger}
    return total / pages, pages, ocr_layer, evidence


def route(chars: float, ocr_fonts: bool) -> tuple[list[str], str, str]:
    """-> (extra marker args, lane, lane_reason)"""
    batch = ["--recognition_batch_size", str(RECOGNITION_BATCH)]
    if chars >= MIN_CHARS_PER_PAGE and ocr_fonts:
        return ["--strip_existing_ocr", *batch], "scan", "untrusted_ocr_layer"
    if chars >= MIN_CHARS_PER_PAGE:
        # Cap the batch on the clean lane too. Uncapped, Marker auto-scales its batch to
        # fill the card, so a figure-dense born-digital PDF balloons to the ~10 GB ceiling
        # and thrashes to a timeout (Cybernetics models book: 91 pp → 60-min DNF). The scan
        # lane's cap is exactly why Beer finished at 439 figure-heavy pp / ~7.9 GB peak.
        # Batch size governs only throughput/VRAM, never output.
        return [*batch], "clean", "text_layer_present"
    return [*batch], "scan", "no_text_layer"


# ---------- the conversion ledger (Rab's S57 requirement, docs/18 §5.2) ----------

# One learning record per successful conversion. The events stream already held most of these
# facts, but scattered across lines and stages; this is the shape the estimator reads, so a new
# book's promise comes from SIMILAR past works (same lane, nearest chars/pp) instead of one
# global median. Append-only, single writer (this converter), same discipline as events.jsonl.
LEDGER_FILE = fp_paths.root("conversion_ledger")


def _ledger_record(manifest: dict, cost_s: float, peak_mib: int,
                   resumed_slices: int = 0, run_wall_s: float | None = None,
                   retry_wall_s: float = 0.0) -> None:
    """File the learning record. `cost_s` is the book's TOTAL GPU cost including slices that were
    resumed from an earlier run — that is what a future estimate needs. `run_wall_s` keeps this
    run's own elapsed time alongside it, so the two never get confused later.
    Best-effort: a conversion is never lost to its own bookkeeping."""
    try:
        pages = manifest.get("pages") or 1
        chunking = manifest.get("chunking")
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": manifest.get("source"),
            "source_sha256": (manifest.get("source_sha256") or "")[:16],
            "pages": pages,
            "lane": manifest.get("lane"),
            "chars_per_page": round(manifest.get("chars_per_page_detected") or 0, 1),
            "wall_s": round(cost_s, 1),
            "s_per_page": round(cost_s / pages, 3),
            "run_wall_s": round(run_wall_s, 1) if run_wall_s is not None else None,
            "resumed_slices": resumed_slices,
            # OK-17: how much of wall_s was failed ladder attempts — already inside cost_s,
            # named so a reader can separate healthy rate from recovery spend
            "retry_wall_s": round(retry_wall_s, 1),
            "chunked": bool(chunking),
            "slices": (len(chunking["seams"]) + 1) if chunking else 1,
            "batch": chunking["batch"] if chunking else RECOGNITION_BATCH,
            "peak_vram_mib": peak_mib or None,
        }
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        emit("convert", "ledger_error", error=str(exc)[:150])


def estimate_from_ledger(pages: int, lane: str, chars_per_page: float) -> dict | None:
    """The similarity-based estimate (docs/18 §5.2): same-lane rows, nearest-≤3 by chars/pp,
    TRUE median of their s/page (even counts average the middle pair — the old middle-index
    pick returned the LARGER of two samples, biasing every promise upward; census N056).
    None when no same-lane evidence exists — a promise is only made when there is real
    evidence behind it. `basis` is a real discriminator now: "similar" (≥2 neighbours) or
    "single-sample" (1); the docstring's former phantom fallback branch is gone with it."""
    try:
        rows = [json.loads(line) for line in
                LEDGER_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    # `is not None`, not truthiness: a 0.0 rate is a real (if implausible) measurement, and
    # silently discarding it would make the estimator lie about how much evidence it has.
    same_lane = [r for r in rows
                 if r.get("lane") == lane and r.get("s_per_page") is not None]
    if not same_lane:
        return None
    neighbours = sorted(same_lane,
                        key=lambda r: abs((r.get("chars_per_page") or 0) - chars_per_page))[:3]
    rates = sorted(r["s_per_page"] for r in neighbours)
    n = len(rates)
    median = rates[n // 2] if n % 2 else round((rates[n // 2 - 1] + rates[n // 2]) / 2, 3)
    return {
        "s_per_page": median,
        "eta_s": int(median * pages),
        "basis": "similar" if n >= 2 else "single-sample",
        "samples": n,
        "from_lane": lane,
    }


# ---------- the monitored Marker run (one whole book, or one slice of one) ----------

def _blocks_enabled() -> bool:
    """Whether this run asks Marker for block records (J24). Re-read per invocation, so the
    escape hatch works mid-book the way the batch lever does — `FP_BLOCKS=off` and the very
    next slice is back on marker_single.exe.

    Both files must EXIST, checked here and not assumed: the sidecar is a repo file and the
    interpreter is derived from MARKER's own directory. If either is missing this returns False
    and the conversion runs exactly as it did before J24, having spent no GPU finding out."""
    if os.environ.get(BLOCKS_ENV, "").strip().lower() in ("0", "off", "no", "false"):
        return False
    return MARKER_BLOCKS.is_file() and MARKER_PYTHON.is_file()


def _marker_argv(engine_src: Path, out_root: Path, extra: list[str],
                 page_range: str | None) -> list[str]:
    """The one Marker invocation, as either the J24 sidecar or marker_single.exe.

    The ARGUMENTS are identical in both shapes on purpose — the sidecar parses them with
    marker's own click command, so `--strip_existing_ocr` and `--recognition_batch_size` resolve
    exactly as marker_single resolves them (they are crawler-synthesized options, absent from
    ConfigParser.common_options; see marker_blocks.py). The only difference on the far side of
    the pipe is that the sidecar keeps the built Document and renders it a second time, which
    costs no GPU because the document is already built.

    -u so the sidecar's own prints reach the drain immediately: `_run_marker`'s reader thread is
    also the liveness clock, and a buffered child looks frozen (the S48 lesson, one step over)."""
    engine_args = [str(engine_src), "--output_dir", str(out_root),
                   "--output_format", "markdown", *extra,
                   *(["--page_range", page_range] if page_range else [])]
    if _blocks_enabled():
        return [str(MARKER_PYTHON), "-u", str(MARKER_BLOCKS), *engine_args]
    return [str(MARKER), *engine_args]


def _slice_blocks_path(out_root: Path, start: int, end: int, split_depth: int = 0) -> Path:
    """Where one slice's harvested block records land, computed identically by the harvest and
    by the caller.

    A NAMED FUNCTION and not a `meta` key on purpose. `_run_slice_with_retries`'s meta is a
    CLOSED contract: tripwire T10 (the zero-stall negative control) asserts a healthy slice's
    meta equals its baseline dict exactly, so that recovery bookkeeping can never leak into the
    healthy path. Hanging a new product off it turns that tripwire red and costs the suite its
    meaning. The path lives beside the kept assets in `out_root.parent` for the same reason they
    do: the split path re-enters with the same `out_root` and rmtree's it (review CRITICAL /
    tripwire T3), so anything inside it is dangling by the time the caller reads it."""
    return out_root.parent / f".slice-blocks-{start:05d}-{end:05d}-d{split_depth}.json"


def _harvest_blocks(out_dir: Path, engine_stem: str, dest: Path) -> Path | None:
    """Copy this attempt's blocks file OUT of `out_root` to `dest`, exactly as the assets are
    copied out and for the same reason.

    `dest` is CLEARED first, always. A retry that falls back, or a slice that runs under
    FP_BLOCKS=off after one that did not, would otherwise leave the previous attempt's file
    standing at the same computed path and the caller would adopt it — blocks from the wrong
    attempt, presented as this one's. That is the confidently-wrong class this whole ticket is
    about, one level down.

    Returns None on absence — the NORMAL case for FP_BLOCKS=off, for a marker_single run, and
    for the selftest's MarkerStub, which materializes an out_dir with assets and no blocks.
    Never raises: an addition may not cost a slice."""
    try:
        dest.unlink(missing_ok=True)
        src = out_dir / f"{engine_stem}{marker_blocks.BLOCKS_SUFFIX}"
        if not src.is_file():
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest
    except OSError as exc:
        emit("convert", "blocks_error", phase="harvest", error=str(exc)[:150])
        return None


def _run_marker(engine_src: Path, engine_stem: str, out_root: Path, extra: list[str],
                pages: int, source_name: str, page_range: str | None = None,
                progress_prefix: str = "", progress_context: dict | None = None
                ) -> tuple[Path, str, float, int]:
    """Run Marker once under the S52 stall monitor and return (out_dir, markdown, wall, peak MiB).

    Extracted at S60 so the whole-book path and every chunked slice share ONE implementation of
    the hard-won parts: the draining reader thread (S48's pipe deadlock), the tree-kill (S48's
    orphan), the kill-early stall signature (S45/S48), and the page-scaled outer timeout (S45).
    `page_range` is Marker's own 0-indexed `--page_range`; `progress_prefix` labels the progress
    file so the Room can say which slice is running."""
    _clear_progress()
    captured: list[str] = []
    liveness = _ProgressLiveness()

    def _reader(pipe) -> None:
        try:
            for line in pipe:  # text mode: universal newlines split tqdm's \r refreshes into lines
                captured.append(line)
                try:
                    m = _TQDM_RE.search(line)
                    if m:
                        liveness.observe(f"{progress_prefix}{m.group(1).strip()}",
                                         int(m.group(2)), int(m.group(3)), int(m.group(4)),
                                         progress_context)
                except Exception:  # noqa: BLE001 — a parse fault must never stop the drain
                    pass
        except Exception:  # noqa: BLE001 — a reader fault must never break the convert — and it
            # must never stop DRAINING either: with stdout piped, a dead reader lets the 64 KB
            # pipe fill and Marker blocks on its next write, wedging the convert at zero CPU
            # (S48: the cp1252-decode deadlock; S45's "stall" was this wearing a VRAM costume).
            try:
                for _ in pipe:
                    pass
            except Exception:
                pass

    t0 = time.perf_counter()
    proc = subprocess.Popen(
        _marker_argv(engine_src, out_root, extra, page_range),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        # Marker inherits PYTHONIOENCODING=utf-8 (the watcher sets it), so the pipe carries
        # UTF-8 — but text=True alone decodes with the locale codepage (cp1252 here), and
        # surya's tqdm block glyphs contain bytes cp1252 cannot decode (0x8F et al.). The
        # strict-decode error killed the reader thread and deadlocked the pipe (S48).
        encoding="utf-8", errors="replace",
    )
    reader = threading.Thread(target=_reader, args=(proc.stdout,), daemon=True)
    reader.start()
    # The cap scales with the work in front of it: a flat 3600 s silently made any book over
    # ~1000 pages UNCONVERTIBLE (found S45 probing a 1,356-page Damodaran — 1.5-3.4 measured
    # s/page puts it at 34-77 min, straddling the old cap). 20 s/page is ~2.5x the worst rate
    # ever measured here (8.08 s/page, a dense 439-pp scan), so it still catches a genuine hang
    # while never punishing a book for being long. For a slice, `pages` is the SLICE's page
    # count, so each slice gets its own proportionate bound.
    timeout_s = max(3600, pages * 20)
    peak_mib = 0
    next_gpu_sample = time.perf_counter()

    def _kill_and_clear() -> None:
        _kill_tree(proc.pid)  # /T first — proc.kill() alone would orphan marker's real python
        proc.kill()
        proc.wait()
        reader.join(timeout=5)
        _clear_progress()

    # Stage A (docs/18 §4A; policy §5.1 "kill early", decided 2026-07-31): the wait is a monitor.
    # The reader's semantic (stage,n,total) tuple is the liveness signal.  File mtime was not:
    # tqdm can repeat an identical tuple and keep touching the file, hiding a real freeze.  The
    # in-memory clock also means a cosmetic write failure cannot falsely kill a healthy convert.
    # The process cadence is 5 s for operator responsiveness; GPU sampling remains 30 s because
    # nvidia-smi is a subprocess and must not become a new hot loop.
    while True:
        try:
            proc.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            pass
        elapsed = time.perf_counter() - t0
        if time.perf_counter() >= next_gpu_sample:
            peak_mib = max(peak_mib, _gpu_signature().get("gpu_mem_used_mib", 0))
            next_gpu_sample = time.perf_counter() + 30
        if elapsed >= timeout_s:
            sig = _gpu_signature()
            _kill_and_clear()
            # review 2026-08-30: the timeout got structured fields and emitted nothing — a
            # timeout kill was visible only as intake/failed exit 1. Now it names itself.
            emit("convert", "timeout", source=source_name, elapsed_s=int(elapsed),
                 pages=pages, timeout_s=timeout_s, page_range=page_range, **sig)
            raise _MarkerTimeoutError(f"marker timed out after {timeout_s}s ({pages} pages)",
                                     elapsed_s=int(elapsed), pages=pages, timeout_s=timeout_s)
        frozen_s = liveness.age()
        if frozen_s > STALL_FROZEN_S:
            sig = _gpu_signature()
            _kill_and_clear()
            emit("convert", "stalled", source=source_name, frozen_s=int(frozen_s),
                 elapsed_s=int(elapsed), page_range=page_range, **sig)
            raise _MarkerStallError(
                f"marker stalled: progress frozen {int(frozen_s)}s "
                f"(kill-early policy, docs/18 §5.1)",
                frozen_s=int(frozen_s), elapsed_s=int(elapsed), source=source_name,
                page_range=page_range, signature=sig)
    reader.join(timeout=5)
    _clear_progress()
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"marker exited {proc.returncode}: {''.join(captured).strip()[:500]}")
    out_dir = out_root / engine_stem
    md_files = list(out_dir.glob("*.md"))
    if len(md_files) != 1:
        raise RuntimeError(f"expected exactly one .md in {out_dir}, found {len(md_files)}")
    return out_dir, md_files[0].read_text(encoding="utf-8"), wall, peak_mib


def _with_batch(extra: list[str], size: int) -> list[str]:
    """`route()`'s args with the recognition batch replaced by the slice lever's value."""
    out = list(extra)
    for i, arg in enumerate(out):
        if arg == "--recognition_batch_size" and i + 1 < len(out):
            out[i + 1] = str(size)
            return out
    return [*out, "--recognition_batch_size", str(size)]


def _slice_retry_batches(start_batch: int) -> list[int]:
    """Order-preserving retry ladder for stall recovery.

    The user lever controls the first value (8/16/32). On a stall we progressively drop to
    4 for memory relief; the ladder is bounded and always terminates so the job never loops.
    """
    fallback = [start_batch]
    if start_batch > 8:
        fallback.append(8)
    fallback.append(STALL_RECOVERY_BATCH)
    deduped = []
    for value in fallback:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _run_slice_with_retries(source_name: str, engine_src: Path, engine_stem: str,
                           out_root: Path, extra: list[str], pages: int,
                           start: int, end: int, source_batch: int, split_depth: int = 0,
                           progress_prefix: str = "", slice_index: int | None = None,
                           slice_total: int | None = None, split_side: str | None = None
                           ) -> tuple[str, list[Path], float, int, dict]:
    """Run one slice with bounded stall retries and bounded split fallback.

    Returns (markdown, assets, wall_s, peak_mib, meta). `wall_s` is the WINNING attempt's
    wall only; meta = {batch, attempts, retry_wall_s, recovered, split} carries the honest
    remainder — the batch that actually produced the output, how many attempts it took, and
    the GPU seconds the failed attempts burned (review 2026-08-30: excluding them recreated
    the self-flattering estimator the file's own comments forbid). Returned asset paths are
    MATERIALIZED outside out_root — the split path re-enters with the same out_root and
    rmtree's it, so live paths into it would be dangling by the time the caller copies
    (review CRITICAL; tripwire T3). On repeated failure, recursively split the page range.
    Bounded by STALL_RETRY_MAX_SPLITS and STALL_RETRY_SPLIT_MIN_PAGES.
    """
    page_range = f"{start}-{end}"
    attempts = _slice_retry_batches(source_batch)
    last: Exception | None = None
    retry_wall = 0.0

    for attempt, batch in enumerate(attempts, 1):
        try:
            shutil.rmtree(out_root, ignore_errors=True)  # fresh output root each attempt
            slice_extra = _with_batch(extra, batch)
            # attempt 1 is the NORMAL run — labelling it "retry 1/N" made every healthy
            # convert read as degraded on the Room's stage row (review; tripwire T6)
            retry_seg = f"retry {attempt}/{len(attempts)} · " if attempt > 1 else ""
            out_dir, md, wall, mib = _run_marker(
                engine_src, engine_stem, out_root, slice_extra, pages,
                source_name, page_range=page_range,
                progress_prefix=f"{progress_prefix}{retry_seg}batch {batch} · ",
                progress_context={
                    "page_range": page_range,
                    "slice": slice_index,
                    "slices": slice_total,
                    "attempt": attempt,
                    "attempts": len(attempts),
                    "batch": batch,
                    "split_depth": split_depth,
                    "split_side": split_side,
                },
            )
            images = [p for p in sorted(out_dir.iterdir())
                      if p.suffix.lower() in (".jpeg", ".jpg", ".png")]
            keep = out_root.parent / f".slice-assets-{start:05d}-{end:05d}-d{split_depth}"
            shutil.rmtree(keep, ignore_errors=True)
            keep.mkdir(parents=True)
            kept: list[Path] = []
            for p in images:
                q = keep / p.name
                shutil.copy2(p, q)
                kept.append(q)
            # J24: the blocks leave by `_slice_blocks_path`, NOT in `kept` and NOT in `meta`.
            # Not `kept`, because that list is copied into the slice dir and merged into the
            # bundle's assets/ (T3 asserts its exact contents, and a .json among the figures
            # would be a silent contract change). Not `meta`, because T10 asserts the healthy
            # meta dict exactly — see `_slice_blocks_path`.
            _harvest_blocks(out_dir, engine_stem,
                            _slice_blocks_path(out_root, start, end, split_depth))
            if attempt > 1:
                emit("convert", "slice_retry_succeeded", source=source_name,
                     page_range=page_range, attempt=attempt, batch=batch)
            return md, kept, wall, mib, {"batch": batch, "attempts": attempt,
                                         "retry_wall_s": round(retry_wall, 1),
                                         "recovered": attempt > 1, "split": False}
        except _MarkerStallError as exc:
            last = exc
            retry_wall += exc.elapsed_s
            emit("convert", "slice_retry", source=source_name, page_range=page_range,
                 attempt=attempt, batch=batch, reason="stalled", frozen_s=exc.frozen_s,
                 elapsed_s=exc.elapsed_s, **exc.signature)
            continue
        # _MarkerTimeoutError and everything else propagate: a timeout already blew the
        # scaled 20 s/page bound, so retrying at a lower batch cannot help (review: the
        # former explicit re-raise handlers here read as policy while expressing none).

    # If the full slice still stalls after retries, recursively split once and continue.
    if split_depth >= STALL_RETRY_MAX_SPLITS or (end - start + 1) <= STALL_RETRY_SPLIT_MIN_PAGES:
        raise last or RuntimeError(f"slice stalled and retries exhausted: {page_range}")

    mid = (start + end) // 2
    if mid < start or mid >= end:
        raise last or RuntimeError(f"invalid split point while recovering slice: {page_range}")

    emit("convert", "slice_split", source=source_name, page_range=page_range,
         split_at=f"{start}-{mid}/{mid+1}-{end}", split_depth=split_depth + 1)

    left_md, left_imgs, left_wall, left_mib, left_meta = _run_slice_with_retries(
        source_name, engine_src, engine_stem, out_root, extra, pages=(mid - start + 1),
        start=start, end=mid, source_batch=STALL_RECOVERY_BATCH,
        split_depth=split_depth + 1,
        progress_prefix=f"{progress_prefix}split-left depth{split_depth+1}: ",
        slice_index=slice_index, slice_total=slice_total, split_side="left"
    )
    right_md, right_imgs, right_wall, right_mib, right_meta = _run_slice_with_retries(
        source_name, engine_src, engine_stem, out_root, extra, pages=(end - mid),
        start=mid + 1, end=end, source_batch=STALL_RECOVERY_BATCH,
        split_depth=split_depth + 1,
        progress_prefix=f"{progress_prefix}split-right depth{split_depth+1}: ",
        slice_index=slice_index, slice_total=slice_total, split_side="right"
    )
    # J24: the two halves' blocks merge into ONE file at THIS slice's path, so the caller reads
    # the same place whether the slice ran whole or was split. A plain concatenation is correct
    # here for the same reason it is correct across slices: the page numbers are already
    # absolute (marker_blocks.absolute_page_from_block_id carries the evidence). A half whose
    # blocks are missing contributes none — the split ladder is a stall RECOVERY path and must
    # not grow a way to fail.
    _merge_split_blocks(out_root, start, mid, end, split_depth)
    return (
        f"{left_md}\n\n{right_md}",
        [*left_imgs, *right_imgs],
        left_wall + right_wall,
        max(left_mib, right_mib),
        {"batch": min(left_meta["batch"], right_meta["batch"]),
         "attempts": left_meta["attempts"] + right_meta["attempts"],
         "retry_wall_s": round(retry_wall + left_meta["retry_wall_s"]
                               + right_meta["retry_wall_s"], 1),
         "recovered": True, "split": True},
    )


def _merge_split_blocks(out_root: Path, start: int, mid: int, end: int,
                        split_depth: int) -> None:
    """Fold a split slice's two halves into the parent slice's blocks path.

    `dest` is cleared first for the same staleness reason `_harvest_blocks` clears its own: the
    parent's pre-split attempts may have written there. Never raises (docs/15 §8's fail-safe
    rule) — a stall recovery that succeeded must not then fail on bookkeeping."""
    dest = _slice_blocks_path(out_root, start, end, split_depth)
    try:
        dest.unlink(missing_ok=True)
        halves = [p for p in (_slice_blocks_path(out_root, start, mid, split_depth + 1),
                              _slice_blocks_path(out_root, mid + 1, end, split_depth + 1))
                  if p.is_file()]
        if not halves:
            return
        # slices_total=2 even when only one half survived: `complete` then reads false, which is
        # the truth about a half-blind split.
        marker_blocks.merge_block_files(halves, dest, slices_total=2)
    except Exception as exc:  # noqa: BLE001 — an addition may not cost a recovered slice
        emit("convert", "blocks_error", phase="split_merge",
             page_range=f"{start}-{end}", error=str(exc)[:150])


def _done_identity_mismatch(prior: dict, source_sha: str, extra: list[str],
                            marker_version: str) -> list[str]:
    """Names every identity field a finished slice's `.done` does NOT match (empty = safe to
    resume). F-02's repair: `.done` used to be trusted by PRESENCE alone, so a slice converted
    from a different config could be silently merged into this book. `batch` is deliberately
    NOT an identity field: it is a performance knob (VRAM/speed), not an output-identity
    input — gating on it would invalidate good slices at every mid-book lever change, which
    is the lever's whole point (docs/37 §4 T2c). A missing field (legacy `.done`) reads as a
    mismatch: re-convert-and-log is cheap and correct."""
    fields = {"source_sha256": source_sha, "engine_args": list(extra),
              "marker_version": marker_version}
    return [key for key, want in fields.items() if prior.get(key) != want]


def _convert_chunked(source_name: str, engine_src: Path, engine_stem: str, work: Path,
                     out_root: Path, extra: list[str], pages: int,
                     source_sha: str) -> tuple[str, Path, float, int, dict, dict]:
    """Convert a long book in 200-page slices and merge (docs/18 §5.2, signed S57).

    Returns (merged markdown, merged assets dir, total wall, peak MiB, chunking manifest block).

    RESUME is the point of the whole design: each finished slice is published into
    `.chunk-work/<sha16>/slice-<start>-<end>/` OUTSIDE the run's temp dir, so a killed slice (or
    a killed process, or a reboot) costs only that slice — a re-run converts the missing ones and
    skips the rest. Publication is dot-dir-then-rename, so a half-written slice can never be
    mistaken for a finished one. Retention is LATEST-BOOK (A1, signed 2026-08-31): the slice
    dirs survive the merge and are swept only when a DIFFERENT book starts chunking — so a
    death in the analyst/audit/ship tail resumes the convert for free, and disk stays bounded
    to one book."""
    import marker  # marker-env only; version for provenance (the manifest stamp's twin)

    marker_version = getattr(marker, "__version__", "unknown")
    batch = chunk_batch()
    ranges = slice_ranges(pages)
    total = len(ranges)
    book_work = CHUNK_WORK / source_sha[:16]
    # A1 (signed Rab 2026-08-31): retention is LATEST-BOOK, swept here — not deleted on merge.
    # The night of 2026-08-30/31 paid the full 1377-pp convert TWICE because a post-convert
    # kill found the slices already consumed; keeping them until the next book starts makes
    # every post-convert death resumable for free, bounded to one book's disk.
    for sibling in (CHUNK_WORK.iterdir() if CHUNK_WORK.is_dir() else ()):
        if sibling.is_dir() and sibling.name != source_sha[:16]:
            shutil.rmtree(sibling, ignore_errors=True)
            print(f"SLICE CACHE: swept previous book {sibling.name}", flush=True)
    book_work.mkdir(parents=True, exist_ok=True)
    merged_assets = work / "merged-assets"
    merged_assets.mkdir(parents=True, exist_ok=True)
    print(f"CHUNKING {source_name}: {pages} pages -> {total} slices of {SLICE_PAGES} "
          f"(recognition batch {batch} at start, lever {CHUNK_BATCH_FILE.name}, "
          f"re-read per slice)", flush=True)
    emit("convert", "chunking", source=source_name, pages=pages, slices=total,
         slice_size=SLICE_PAGES, batch=batch)

    parts: list[str] = []
    # J24: one entry per slice that HAS blocks. Deliberately not one per slice — the gap is the
    # point: `slices_with_blocks` vs `slices_total` is how the merged record admits it is
    # partial (a slice cached by a pre-J24 run has slice.md and no blocks, and re-converting it
    # for an ADDITION would cost hours of GPU, which constraint 1 forbids).
    block_files: list[Path] = []
    total_wall = 0.0      # winning-attempt GPU time in THIS run (what the convert event reports)
    retry_wall = 0.0      # GPU time failed ladder attempts burned THIS run (review 2026-08-30:
                          # invisible before — the ledger understated the Damodaran by 46 %)
    resumed_wall = 0.0    # GPU time the resumed slices cost when they ran (the ledger wants it)
    resumed_count = 0
    converted_pages = 0   # pages actually converted in THIS run — the honest denominator
    peak_mib = 0
    for i, (start, end) in enumerate(ranges, 1):
        slice_dir = book_work / f"slice-{start:05d}-{end:05d}"
        # Resume admission (F-02's repair): a finished slice is reused only when its .done
        # RECORDS this job's identity — presence alone used to admit slices converted under a
        # different engine config or Marker version, silently mixing outputs into one book.
        prior: dict | None = None
        if (slice_dir / ".done").is_file():
            try:
                parsed = json.loads((slice_dir / ".done").read_text(encoding="utf-8"))
                prior = parsed if isinstance(parsed, dict) else None
            except (OSError, ValueError):
                prior = None
            stale = (_done_identity_mismatch(prior, source_sha, extra, marker_version)
                     if prior is not None else ["unparseable"])
            if stale:
                print(f"SLICE {i}/{total} pages {start}-{end}: STALE .done "
                      f"({', '.join(stale)}) - re-converting", flush=True)
                emit("convert", "slice_stale", source=source_name, slice=i, slices=total,
                     page_range=f"{start}-{end}", mismatch=stale)
                shutil.rmtree(slice_dir, ignore_errors=True)
                prior = None
        if prior is None:
            # F-09, SIGNED per-slice (Rab 2026-08-17, docs/37 §3.1): the lever is re-read for
            # EVERY slice, honoring the promise docs/18 §4, docs/20 and line.rs make — mid-book
            # VRAM steering is what the lever exists for (S60). The slice print, its event, and
            # its .done carry the value actually used; the CHUNKING banner and the manifest's
            # chunking.batch keep the run-start reading (docs/37 §4 T2a).
            slice_batch = chunk_batch()
            staging = book_work / f".part-{start:05d}-{end:05d}"
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(out_root, ignore_errors=True)  # Marker reuses <out_root>/<stem>
            print(f"SLICE {i}/{total} pages {start}-{end} (batch {slice_batch}) …", flush=True)
            md, imgs, wall, mib, meta = _run_slice_with_retries(
                source_name, engine_src, engine_stem, out_root, extra, end - start + 1,
                start, end, slice_batch, progress_prefix=f"slice {i}/{total} · ",
                slice_index=i, slice_total=total)
            total_wall += wall
            retry_wall += meta["retry_wall_s"]
            converted_pages += end - start + 1
            peak_mib = max(peak_mib, mib)
            # Assets keep the names Marker gave them: those are already ABSOLUTE page numbers
            # (see the note above — measured on the Damodaran run, not assumed), so slices cannot
            # collide and the markdown needs no rewriting either. The tripwire fires if that ever
            # stops being true, because silently mislabelled pages are the expensive failure.
            staging.mkdir(parents=True)
            (staging / "slice.md").write_text(md, encoding="utf-8")
            stray = out_of_range_assets([p.name for p in imgs], start, end)
            if stray:
                print(f"  WARNING: {len(stray)} asset(s) outside pages {start}-{end}, "
                      f"e.g. {stray[:3]} — Marker's asset numbering may have changed", flush=True)
                emit("convert", "asset_range_warning", source=source_name,
                     page_range=f"{start}-{end}", count=len(stray), examples=stray[:3])
            for img in imgs:
                shutil.copy2(img, staging / img.name)
            # J24, constraint 3 (a resumed slice must still contribute its blocks): the blocks
            # ride INSIDE the slice dir, published by the same dot-dir-then-rename below. So a
            # resumed slice reads them off disk exactly like it reads slice.md, and the merge
            # cannot tell a resumed slice from a fresh one — which is the property that makes a
            # power-cut resume contribute blocks without re-running the GPU.
            harvested = _slice_blocks_path(out_root, start, end)
            slice_blocks = harvested.is_file()
            if slice_blocks:
                try:
                    shutil.copy2(harvested, staging / "slice.blocks.json")
                except OSError as exc:
                    slice_blocks = False
                    emit("convert", "blocks_error", phase="slice_publish",
                         page_range=f"{start}-{end}", error=str(exc)[:150])
            # Identity fields (source_sha256, engine_args, marker_version) gate the next
            # resume; wall_s feeds the ledger; batch is FORENSIC only — never an admission
            # criterion (docs/37 §4 T2c: the lever must stay live mid-book). F-09 signed:
            # "the value actually used" — meta["batch"] is the batch that PRODUCED this
            # output; the lever reading it started from is lever_batch (review: today's
            # slice 4 ran at 4 and every record said 8).
            (staging / ".done").write_text(
                json.dumps({"source_sha256": source_sha, "page_range": f"{start}-{end}",
                            "wall_s": round(wall, 1), "batch": meta["batch"],
                            "lever_batch": slice_batch,
                            "retry_wall_s": meta["retry_wall_s"],
                            "engine_args": list(extra),
                            # J24 FORENSIC ONLY, never an admission criterion — same standing as
                            # `batch` above and for a sharper reason: adding blocks to
                            # _done_identity_mismatch would declare every pre-J24 cached slice
                            # stale and re-pay a 3,834 s convert to collect an ADDITION. Blocks
                            # degrade; they never re-convert.
                            "blocks": bool(slice_blocks),
                            # `blocks_engine`, not `engine`: the manifest already spends
                            # "engine" on the CONVERTER (marker vs the ThinkPad's), and two
                            # different meanings under one key is how a reader ends up sure of
                            # the wrong thing. This one names which invocation shape was asked
                            # for, so `blocks_engine: marker_blocks` with `blocks: false` reads
                            # as "asked and got nothing" rather than as an unexplained absence.
                            "blocks_engine": ("marker_blocks" if _blocks_enabled()
                                              else "marker_single"),
                            "marker_version": marker_version}) + "\n", encoding="utf-8")
            staging.rename(slice_dir)  # atomic publish: .done exists only on a complete slice
            emit("convert", "slice", source=source_name, slice=i, slices=total,
                 page_range=f"{start}-{end}", wall_s=round(wall, 1), batch=meta["batch"],
                 resumed=False,
                 **({"attempts": meta["attempts"], "recovered": True,
                     "retry_wall_s": meta["retry_wall_s"],
                     "lever_batch": slice_batch} if meta["recovered"] else {}))
        else:
            # A resumed slice costs this run nothing, but it DID cost the GPU when it ran, and
            # the ledger is trying to learn what a book of this shape actually takes. Counting
            # only the re-run would file a rate that gets quietly better every time a slice is
            # retried — an estimator that flatters itself (found on the Damodaran run: 1.69 s/pp
            # reported vs 1.94 s/pp truly spent).
            try:
                resumed_wall += float(prior.get("wall_s") or 0.0)
            except (ValueError, TypeError):
                pass
            resumed_count += 1
            print(f"SLICE {i}/{total} pages {start}-{end}: RESUMED (already converted)", flush=True)
            emit("convert", "slice", source=source_name, slice=i, slices=total,
                 page_range=f"{start}-{end}", resumed=True)
        parts.append((slice_dir / "slice.md").read_text(encoding="utf-8"))
        # J24: read from the PUBLISHED slice dir, not from meta — one line that serves the fresh
        # and the resumed slice identically, and that yields nothing (not an error) for a slice
        # cached before J24 existed.
        if (slice_dir / "slice.blocks.json").is_file():
            block_files.append(slice_dir / "slice.blocks.json")
        for img in sorted(slice_dir.iterdir()):
            if img.suffix.lower() in (".jpeg", ".jpg", ".png"):
                shutil.copy2(img, merged_assets / img.name)

    # Clean cuts: the seam is RECORDED, never smoothed. Overlap reconciliation in v1 risks
    # silent text loss, which is the one failure this factory refuses to trade for tidiness.
    # Seams are 1-based absolute page numbers of each slice's first page, after the first.
    chunking = {"slice_size": SLICE_PAGES, "batch": batch,
                "seams": [start + 1 for start, _ in ranges[1:]]}
    # A1: the slice dirs SURVIVE the merge (latest-book retention; swept when the NEXT book
    # starts). A kill anywhere after this line — analyst, audit, ship — resumes the convert
    # in seconds instead of re-paying hours.
    # cost_s = every GPU second this book has cost, including failed ladder attempts and
    # prior-run resumed slices — the number the estimator LEARNS from must not flatter itself
    stats = {"cost_s": round(total_wall + retry_wall + resumed_wall, 1),
             "retry_wall_s": round(retry_wall, 1),
             "resumed_slices": resumed_count,
             "pages_converted_this_run": converted_pages}
    # J24: the book-level merge. `slices_total=total` (not len(block_files)) is what lets the
    # record say `complete: false` instead of quietly presenting a subset as the whole book.
    # Fails soft in both directions: no block files at all -> no key in stats -> the bundle is
    # exactly a pre-J24 bundle; a merge fault -> a named event and the same outcome.
    if block_files:
        try:
            dest = work / BLOCKS_BUNDLE_FILE
            stats["blocks"] = marker_blocks.merge_block_files(
                block_files, dest, slices_total=total)
            stats["blocks_path"] = dest
        except Exception as exc:  # noqa: BLE001 — an addition may not cost a book
            emit("convert", "blocks_error", source=source_name, phase="book_merge",
                 error=str(exc)[:150])
    return "\n\n".join(parts), merged_assets, total_wall, peak_mib, chunking, stats


# ---------- the slice ----------

def convert(src: Path, work: Path, use_analyst: bool = False,
            analyst_backend: str = "local") -> tuple[Path, str, dict]:
    # Claim the ⟳ remedy intent FIRST (consume-once, docs/15 §14.2): read and delete before any
    # work happens, so a marker can never survive this conversion. Stamped into the manifest
    # further down, once the source sha is known and can be checked against it.
    supersede_marker = _take_supersede_marker(src)
    chars, pages, ocr_fonts, ocr_evidence = probe(src)
    extra, lane, lane_reason = route(chars, ocr_fonts)
    print(f"PROBE {src.name}: {chars:.1f} chars/page, {pages} pages, ocr_fonts={ocr_fonts}"
          f" -> lane={lane} ({lane_reason})", flush=True)
    # NUM-5: the routing vote's own numbers ride the probe event — a 50.1 % book and a 100 %
    # book no longer leave identical records, and a single-font short-circuit names itself.
    emit("convert", "probe", source=src.name, chars_per_page=round(chars, 1),
         pages=pages, lane=lane, lane_reason=lane_reason,
         ocr_invisible_ratio=ocr_evidence["invisible_ratio"],
         ocr_invisible_spans=ocr_evidence["invisible_spans"],
         ocr_total_spans=ocr_evidence["total_spans"],
         **({"ocr_font_trigger": ocr_evidence["ocr_font_trigger"]}
            if ocr_evidence["ocr_font_trigger"] else {}))
    # Convert from a short sanitizer-proof copy (the ThinkPad's L15 idiom): Marker derives
    # its output dir and asset names from the input stem.
    engine_stem = slugify(src.stem)[:40]
    engine_src = work / f"{engine_stem}{src.suffix.lower()}"
    shutil.copy2(src, engine_src)
    out_root = work / "marker-out"
    source_sha = sha256_of(src)  # needed up here now: slice resume is keyed by it

    # Stage E: the promise, filed before the work (docs/18 §5.2's promise-vs-actual pairing).
    # NUM-4 (signed 2026-08-31, census N055): the promise is filed AFTER the sha so it can see
    # how much of the book is already converted — the old order promised the FULL book and made
    # the glass count down hours for a resumed run that finishes in seconds.
    promised = _write_estimate_safe(src.name, pages, lane, chars,
                                    resumable_pages=_resumable_pages(source_sha, pages, extra))

    _ollama_unload()  # OK-16: clear VRAM residents before any Marker work (best-effort)

    # Stage D (docs/18 §5.2): long books convert in slices. The threshold is lane-aware because
    # the lanes cost different VRAM, and the page count is the probe's, never metadata.
    chunking = None
    if should_chunk(pages, lane):
        markdown, assets_dir, wall, peak_mib, chunking, chunk_stats = _convert_chunked(
            src.name, engine_src, engine_stem, work, out_root, extra, pages, source_sha)
    else:
        # SCOPE (review 2026-08-30): the unchunked path has NO stall-recovery ladder and no
        # .done resume — a short book that stalls hard-fails and re-pays everything. Named
        # here rather than silently implied; routing it through a 1-slice ladder is future
        # work, not an accident.
        out_dir, markdown, wall, peak_mib = _run_marker(
            engine_src, engine_stem, out_root, extra, pages, src.name,
            progress_context={"page_range": None, "slice": 1, "slices": 1,
                              "attempt": 1, "attempts": 1, "batch": None,
                              "split_depth": 0, "split_side": None})
        assets_dir = out_dir
        chunk_stats = {"cost_s": round(wall, 1), "retry_wall_s": 0.0,
                       "resumed_slices": 0, "pages_converted_this_run": pages}
        # J24: the short-book path's blocks are already whole — one slice, one file, written by
        # the sidecar beside the .md. Routed through the SAME merge so a 40-page book and a
        # 1,377-page book hand the manifest one identical shape, and one reader serves both.
        _one = out_dir / f"{engine_stem}{marker_blocks.BLOCKS_SUFFIX}"
        if _one.is_file():
            try:
                dest = work / BLOCKS_BUNDLE_FILE
                chunk_stats["blocks"] = marker_blocks.merge_block_files(
                    [_one], dest, slices_total=1)
                chunk_stats["blocks_path"] = dest
            except Exception as exc:  # noqa: BLE001 — an addition may not cost a book
                emit("convert", "blocks_error", source=src.name, phase="single_merge",
                     error=str(exc)[:150])
    print(f"CONVERTED in {wall:.1f}s ({wall / pages:.1f} s/page)", flush=True)
    # Stage E: the promise rides the `converted` event beside the actual, forever — the event
    # stream is where the estimator's honesty can be audited later (docs/19 §6 hygiene).
    # docs/34: s_per_page's honest denominator is the pages THIS run converted, not the
    # book's page count — a resumed run divided this-run seconds by all-book pages and
    # reported 1.97 s/pp on a book that truly cost ~7.2 (review 2026-08-30). Both rates are
    # emitted, each naming its denominator; retry_wall_s makes failed-attempt GPU time
    # visible instead of vanishing.
    # `or pages` guards the DIVISION only — the emitted count stays honest: an all-resumed
    # run converted 0 pages this run (caught live 2026-08-31 07:40:59, iteration 7 emitted
    # 1377 for a 1-second resume).
    true_run_pages = chunk_stats.get("pages_converted_this_run", pages)
    run_pages = true_run_pages or pages
    emit("convert", "converted", source=src.name, wall_s=round(wall, 1),
         s_per_page=round(wall / pages, 2), pages=pages,
         pages_converted_this_run=true_run_pages,
         s_per_page_this_run=round(wall / run_pages, 2),
         retry_wall_s=chunk_stats.get("retry_wall_s", 0.0),
         resumed_slices=chunk_stats.get("resumed_slices", 0),
         cost_s=chunk_stats.get("cost_s"),
         slices=(len(chunking["seams"]) + 1) if chunking else 1,
         peak_vram_mib=peak_mib or None,
         **({"promised_s_per_page": promised["s_per_page"],
             "promised_eta_s": promised["eta_s"],
             "estimate_basis": promised["basis"],
             "estimate_samples": promised["samples"]} if promised else {}))
    _clear_estimate()  # the promise's live audience (the convert bar) is done with it

    # Assemble the bundle in a dot-prefixed temp dir keyed on the source sha (L13 idiom).
    bundle_name = clamp_name(src.stem)
    tmp_dir = work / f".part-{source_sha[:16]}"
    assets = tmp_dir / "assets"
    assets.mkdir(parents=True)
    for img in sorted(assets_dir.iterdir()):
        if img.suffix.lower() in (".jpeg", ".jpg", ".png"):
            shutil.copy2(img, assets / img.name)
    converted_at = datetime.now(timezone.utc)
    ocr = lane == "scan"
    # The stamped DPI is DERIVED from the installed Marker, never retyped: the scan lane's OCR
    # really runs on the highres page renders (builders/document.py highres_image_dpi, "used
    # for OCR"; lowres 96 is layout-only) and this converter passes no override. The linux
    # lane's 300 is ITS engine's real setting — different engines, both stamps truthful
    # (coordination 2026-08-16T21-51 §2.2; SYM-039's rule: a hand-typed count drifts).
    if ocr:
        from marker.builders.document import DocumentBuilder  # marker-env only

        stamp_dpi = DocumentBuilder.highres_image_dpi
    else:
        stamp_dpi = None
    frontmatter = render_frontmatter(
        "marker", lane, lane_reason, chars, ocr, stamp_dpi, converted_at, source_sha
    )
    import marker  # marker-env only; version for provenance

    manifest = {
        "source": src.name,
        "source_sha256": source_sha,
        "engine": "marker",
        "lane": lane,
        "lane_reason": lane_reason,
        "chars_per_page_detected": chars,
        # NUM-5: the routing vote's evidence travels WITH the book — auditable forever
        "probe_evidence": ocr_evidence,
        "pages": pages,
        "converter_version": CONVERTER_VERSION,
        "marker_version": getattr(marker, "__version__", "unknown"),
        "converted_at": converted_at.isoformat(timespec="seconds"),
    }
    # Stage D: the seams travel WITH the book, forever. The audit scores the merged whole, and
    # the Repair Bench needs to know where the cuts were when a figure or a sentence looks wrong
    # near one (docs/18 §5.2). Absent on unchunked books, so nothing else has to change.
    if chunking:
        manifest["chunking"] = chunking
    # Rides every downstream path from here: the anchor copy, the pending/ card + resume, and
    # all three ship sites carry this same manifest, so nothing else needs to know about it.
    _stamp_supersede_safe(manifest, supersede_marker, source_sha, src.name)
    # J24: the block records join the bundle here, beside the manifest that describes them.
    _attach_blocks_safe(tmp_dir, manifest, chunk_stats, src.name)
    # The ledger learns from the book's TRUE cost, which includes any slices this run resumed
    # rather than re-ran (see _convert_chunked) — otherwise every retry teaches it to promise
    # a little more than the GPU can deliver.
    _ledger_record(manifest, chunk_stats["cost_s"], peak_mib,
                   resumed_slices=chunk_stats["resumed_slices"], run_wall_s=wall,
                   retry_wall_s=chunk_stats.get("retry_wall_s", 0.0))
    body = rewrite_image_links(markdown)
    # Survival Audit of the convert stage (docs/15) — before any analyst pass, so the
    # witness is scored against the raw Marker output. Report-only; never fails the line.
    _audit_convert_safe(src, body, lane, tmp_dir, manifest)
    # J33: the PRE-analyst body, byte-for-byte what audit_analyst will treat as `marker_body`
    # below (or what a --resume/--defer-analyst later run will need as J31's reference) —
    # written BEFORE the analyst branch so an un-analysed book gets the sidecar too.
    _write_marker_body_safe(tmp_dir, bundle_name, body, manifest, src.name)
    if use_analyst:
        # Marker has exited: the GPU is free for the analyst (Phase 2 serialization).
        import analyst

        print(f"ANALYST pass starting (link-fenced, backend={analyst_backend})...", flush=True)
        marker_body = body
        # F3 (signed Rab 2026-09-03): this INLINE path emitted NOTHING. The two analyst emits
        # lived only inside apply_analyst(), whose own docstring scopes it to the --resume
        # (widget card) path — so an ordinary `--analyst` convert left events.jsonl silent
        # through the LONGEST phase of the run (measured on the 7 h 26 m Damodaran 4e voyage:
        # 4 h 40 m + 1 h 18 m of silence), and the first-ever goodput_accepted_tok_s /
        # chunks_generated reached no glass at all. Same keys, same order as apply_analyst:
        # the two paths must stay parity-equal or the Room learns a vocabulary that only one
        # of them speaks (T7's standing rule).
        emit("analyst", "start", bundle=bundle_name, backend=analyst_backend,
             chars=len(marker_body))
        body, analyst_meta = analyst.process(body, backend=analyst_backend)
        # `chars` is the PRE-analyst body — apply_analyst measures the body it HANDED to
        # process(), never the one that came back. Inline, `body` has already been rebound by
        # the line above, so the honest witness is marker_body (a len(body) here would report
        # the analyst's output as its own input).
        # `.get`, not `meta[k]`: apply_analyst runs over a bundle already written to disk, but
        # this emit sits mid-convert, after hours of GPU and BEFORE the note and the manifest
        # are written. A KeyError from an older analyst.py's meta would cost the whole book to
        # say nothing. An absent key emits null — honest absence (docs/34), never a zero.
        emit("analyst", "done", bundle=bundle_name, chars=len(marker_body),
             **{k: analyst_meta.get(k) for k in
                ("backend", "program", "chunks_passed", "chunks_rejected",
                 "chunks_failed", "duration_s",
                 # NUM-6: the paid-call count and the docs/34 rate ride the event to the glass
                 "chunks_generated", "goodput_accepted_tok_s",
                 # N-005 (docs/51 census, glass_detector answer key §7.5): chunks_resumed is
                 # produced by analyst.process and silenced on every human channel — the
                 # frontmatter writer's whitelist below drops it and no event carried it. It
                 # rides HERE. It is a NEW key on this event: apply_analyst() does not carry
                 # it yet (out of this ticket's region — F3 owns the inline path only).
                 # DENOMINATOR TRAP (census N-007/N-013): duration_s is THIS run's wall while
                 # chunks_passed counts the WHOLE book across resumes. No rate may be derived
                 # from that pair — emit the fields, never a quotient.
                 "chunks_resumed",
                 # J32-B/SYM-074 (2026-09-05): chunks_rejected's breakdown by reason (fence /
                 # survival / think_leak) — T17 pins the key set on both emits, updated here.
                 "rejections")})
        manifest["analyst"] = analyst_meta
        _audit_analyst_safe(marker_body, body, manifest, name=src.name)
        frontmatter = frontmatter.replace(
            "---\n",
            f"---\nanalyst:\n  model: {analyst_meta['model']}\n"
            f"  backend: {analyst_meta.get('backend', 'local')}\n"
            f"  chunks_passed: {analyst_meta['chunks_passed']}\n"
            f"  chunks_rejected: {analyst_meta['chunks_rejected']}\n"
            f"  chunks_failed: {analyst_meta.get('chunks_failed', 0)}\n"
            f"  duration_s: {analyst_meta['duration_s']}\n"
            # J32-B (2026-09-05, coordinator's default: yes — one line a human reads without
            # opening manifest.json): the survival-guard rejection count alone. fence/think_leak
            # already show up as chunks_rejected minus chunks_passed minus chunks_failed reading
            # oddly if a reader wants JUST the new gate's toll; the full breakdown lives in
            # manifest.analyst.rejections and the analyst/done event, not retyped three ways here.
            f"  rejections_survival: {analyst_meta.get('rejections', {}).get('survival', 0)}\n"
            # J34 (signed Rab 2026-09-05, "1.5x reject"): the inflation guard's toll, the same
            # one-line rule as rejections_survival — a human reads whether the NEW gate fired
            # without opening manifest.json; the breakdown stays in manifest.analyst.rejections.
            f"  rejections_inflation: {analyst_meta.get('rejections', {}).get('inflation', 0)}\n",
            1,
        )
        print(f"ANALYST done: {analyst_meta}", flush=True)
    (tmp_dir / f"{bundle_name}.md").write_text(frontmatter + body, encoding="utf-8")
    (tmp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # The bundle STAYS in the ASCII .part-<sha16> dir locally: Windows bsdtar mangles
    # non-ASCII argv (CJK dir names arrive empty — hit live), so tar must only ever see
    # ASCII paths. The visible (possibly CJK) bundle name is applied by the REMOTE mv —
    # tailscale ssh carries Unicode argv correctly (verified in the same failure).
    return tmp_dir, bundle_name, manifest


def unique_anchor(dest: Path) -> Path:
    if not dest.exists():
        return dest
    n = 1
    while (candidate := dest.with_name(f"{dest.name} ({n})")).exists():
        n += 1
    return candidate


def ship(tmp_dir: Path, bundle_name: str, source_sha: str) -> None:
    """Stream the bundle contents (ASCII paths only on the local side) into a dot-prefixed
    remote assembly dir, then atomically rename it to the visible bundle name."""
    part = f"{REMOTE_STAGING}/.part-{source_sha[:16]}"
    remote_cmd = (
        f"rm -rf {part} && mkdir -p {part} && tar -xf - -C {part} && "
        f"mv {part} {REMOTE_STAGING}/{shell_quote(bundle_name)}"
    )
    tar = subprocess.Popen(
        ["tar", "-cf", "-", "-C", str(tmp_dir), "."], stdout=subprocess.PIPE
    )
    try:
        ssh = subprocess.run(
            ["tailscale", "ssh", REMOTE, remote_cmd],
            stdin=tar.stdout, capture_output=True, text=True, timeout=600,
        )
    finally:
        # If ssh died or timed out, tar is wedged writing into a dead pipe — kill it so
        # ITS timeout never masks the real (network) error. Learned live: an offline
        # ThinkPad surfaced as "tar timed out", burying the dial failure.
        if tar.poll() is None and (locals().get("ssh") is None or ssh.returncode != 0):
            tar.kill()
        tar.wait(timeout=600)
    if tar.returncode != 0 or ssh.returncode != 0:
        emit("ship", "failed", bundle=bundle_name, error=ssh.stderr.strip()[:150])
        raise RuntimeError(f"ship failed: tar={tar.returncode} ssh={ssh.returncode} "
                           f"{ssh.stderr.strip()[:300]}")
    print(f"SHIPPED {bundle_name} -> {REMOTE}:{REMOTE_STAGING}/", flush=True)
    emit("ship", "shipped", bundle=bundle_name, sha=source_sha[:16])


def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def apply_analyst(bundle_dir: Path, bundle_name: str, backend: str) -> dict:
    """Run the link-fenced analyst over an already-assembled bundle's markdown, updating
    the note's frontmatter and manifest in place. Used by the --resume (widget card) path."""
    import analyst

    md_path = bundle_dir / f"{bundle_name}.md"
    raw = md_path.read_text(encoding="utf-8")
    head, body = raw.split("---\n", 2)[1], raw.split("---\n", 2)[2]
    emit("analyst", "start", bundle=bundle_name, backend=backend, chars=len(body))
    new_body, meta = analyst.process(body, backend=backend)
    emit("analyst", "done", bundle=bundle_name, chars=len(body), **{k: meta.get(k) for k in
         ("backend", "program", "chunks_passed", "chunks_rejected",
          "chunks_failed", "duration_s",
          # NUM-6: the paid-call count and the docs/34 rate ride the event to the glass
          "chunks_generated", "goodput_accepted_tok_s",
          # N-005 / F3 D-2 (S114, 2026-09-03): mirrored from the inline path so the two emits stay
          # parity-equal - T17 pins the key set and goes red if either side moves alone. `.get`,
          # like the inline path, so an older analyst_meta can never KeyError the resume.
          "chunks_resumed",
          # J32-B/SYM-074 (2026-09-05): mirrored from the inline path, same parity rule.
          "rejections")})
    frontmatter = (
        f"---\nanalyst:\n  model: {meta['model']}\n  backend: {meta['backend']}\n"
        f"  chunks_passed: {meta['chunks_passed']}\n"
        f"  chunks_rejected: {meta['chunks_rejected']}\n"
        f"  chunks_failed: {meta['chunks_failed']}\n"
        f"  duration_s: {meta['duration_s']}\n"
        # J32-B (2026-09-05): mirrored from the inline path's frontmatter — see that site's
        # comment for why this one line and not the full breakdown.
        f"  rejections_survival: {meta.get('rejections', {}).get('survival', 0)}\n"
        # J34 (2026-09-05): mirrored from the inline path's frontmatter, same one-line rule.
        f"  rejections_inflation: {meta.get('rejections', {}).get('inflation', 0)}\n"
        + head + "---\n"
    )
    md_path.write_text(frontmatter + new_body, encoding="utf-8")
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["analyst"] = meta
    # Survival Audit of the analyst stage (docs/15) — augments the convert-stage block
    # written at conversion time. Report-only; never raises.
    _audit_analyst_safe(body, new_body, manifest, name=bundle_name)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return meta


def defer(tmp_dir: Path, bundle_name: str, manifest: dict, markdown_chars: int) -> str:
    """Park the bundle for the widget's pre-flight card — unless a standing rule
    (rules.json, written by the card's remember-my-choice control) already decides it.
    Returns what happened: "pending" | "auto-local"."""
    import analyst

    rules = analyst.load_rules()
    threshold = rules.get("auto_local_over_chunks")
    est_chunks = max(1, -(-markdown_chars // analyst.CHUNK_TARGET))
    if threshold is not None and est_chunks > int(threshold):
        emit("gate", "auto_routed", bundle=bundle_name, backend="local",
             est_chunks=est_chunks, rule=f"auto_local_over_chunks={threshold}")
        print(f"AUTO-ROUTE local (rule: >{threshold} chunks)", flush=True)
        meta = apply_analyst(tmp_dir, bundle_name, "local")
        print(f"ANALYST done: {meta}", flush=True)
        if _enforce_hold(tmp_dir, bundle_name, manifest["source_sha256"]):
            return "held"
        ship(tmp_dir, bundle_name, manifest["source_sha256"])
        return "auto-local"

    pend_id = manifest["source_sha256"][:16]
    PENDING.mkdir(parents=True, exist_ok=True)
    dest = PENDING / pend_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(tmp_dir, dest)
    card = {
        "id": pend_id,
        "bundle_name": bundle_name,
        "source": manifest["source"],
        "source_sha256": manifest["source_sha256"],
        "state": "pending",
        "created_at": manifest["converted_at"],
        "preflight": analyst.preflight(markdown_chars),
    }
    (PENDING / f"{pend_id}.json").write_text(
        json.dumps(card, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PENDING {pend_id} — awaiting analyst decision (widget card)", flush=True)
    emit("gate", "pending", bundle=bundle_name, id=pend_id,
         est_chunks=card["preflight"]["est_chunks"])
    return "pending"


def resume(pend_id: str, backend: str) -> None:
    """Widget card decision: analyst (or not) + ship a parked bundle, then clear it."""
    json_path = PENDING / f"{pend_id}.json"
    card = json.loads(json_path.read_text(encoding="utf-8"))
    bundle_dir = PENDING / pend_id
    card["state"] = "running"
    json_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    try:
        if backend in ("local", "gemini"):
            meta = apply_analyst(bundle_dir, card["bundle_name"], backend)
            print(f"ANALYST done: {meta}", flush=True)
            # Refresh the anchor copy so it matches what ships.
            anchor_dest = unique_anchor(ANCHOR / f"{card['bundle_name']} [analyst-{backend}]")
            shutil.copytree(bundle_dir, anchor_dest)
        if _enforce_hold(bundle_dir, card["bundle_name"], card["source_sha256"]):
            shutil.rmtree(bundle_dir)
            json_path.unlink()
            emit("gate", "resolved", id=pend_id, backend=backend, held=True)
            print(f"RESUMED+HELD {pend_id}", flush=True)
            return
        ship(bundle_dir, card["bundle_name"], card["source_sha256"])
        shutil.rmtree(bundle_dir)
        json_path.unlink()
        print(f"RESUMED+SHIPPED {pend_id}", flush=True)
        emit("gate", "resolved", id=pend_id, backend=backend)
    except Exception as exc:
        card["state"] = "failed"
        card["error"] = str(exc)[:300]
        json_path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
        emit("gate", "failed", id=pend_id, error=str(exc)[:150])
        raise


# ---------- the analyst-only re-run (docs/19 §3.1) ----------

def _anchor_copies(source: str) -> list[tuple[Path, dict, str]]:
    """Every anchored bundle whose manifest records `source`, newest first.

    Returns (bundle_dir, manifest, bundle_name). The bundle NAME comes from the .md file
    inside, never from the directory: `unique_anchor` may have suffixed the directory with
    " (1)" to avoid a collision, but the note keeps its true name and apply_analyst opens
    `<bundle_name>.md`."""
    out: list[tuple[Path, dict, str, float]] = []
    if not ANCHOR.is_dir():
        return []
    for entry in sorted(ANCHOR.iterdir()):
        if not entry.is_dir():
            continue
        try:
            manifest = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("source") != source:
            continue
        mds = [p for p in entry.glob("*.md")]
        if len(mds) != 1:
            continue  # not a bundle we can address by name
        out.append((entry, manifest, mds[0].stem, entry.stat().st_mtime))
    out.sort(key=lambda t: t[3], reverse=True)
    return [(d, m, n) for d, m, n, _ in out]


def reanalyze(source: str, backend: str) -> None:
    """Analyst-only re-run (docs/19 §3.1): re-run the analyst over an ALREADY-CONVERTED
    bundle and ship it as a supersede. **Marker never runs** — no GPU-hours are spent
    re-reading a PDF whose convert-phase audit already passed; the failure being remedied is
    the analyst's (the claude-code book: convert survival 0.991, analyst `fail` from qwen3
    looping in its own notes).

    Eligibility is decided HERE, not in the widget: the re-run must start from a bundle whose
    markdown is Marker output, i.e. a manifest with NO `analyst` block. Re-analyzing an
    analyst pass would feed the model its own degenerated text and compound the damage, so
    when only analyst OUTPUT survives this refuses out loud (an event, not a silent no-op) —
    the honest fix there is ⟳ re-convert, which rebuilds the Marker copy first.

    GPU exposure is exactly the proven `--resume` path's: the widget refuses to launch while
    the watcher holds `.gpu-lock`, and the watcher (whose queue this never touches) can still
    start a convert underneath a long analyst run. Same trade the pending card has run under
    since S18; the Room's analyst heartbeat makes the run visible while it happens."""
    copies = _anchor_copies(source)
    if not copies:
        emit("analyst", "rerun_refused", source=source, reason="no anchored bundle")
        sys.exit(f"REANALYZE refused: no anchored bundle records source {source!r}")
    pre = [c for c in copies if not c[1].get("analyst")]
    if not pre:
        emit("analyst", "rerun_refused", source=source, reason="only analyst output survives")
        # ASCII only: this string is printed to stderr, and a console left on cp1252 (any shell
        # without PYTHONIOENCODING=utf-8 — Rab's, when he runs it by hand) raises
        # UnicodeEncodeError on the glyphs the UI uses. A refusal must never fail to be read.
        sys.exit(
            f"REANALYZE refused: every anchored copy of {source!r} is already analyst output "
            "-- re-analyzing an analyst pass compounds its damage. Use re-convert instead "
            "(it rebuilds the Marker copy first)."
        )
    bundle_dir, manifest, bundle_name = pre[0]
    source_sha = manifest["source_sha256"]
    # Provenance for the supersede block = the verdict of the generation being REPLACED, which
    # is the newest ANALYZED copy (what actually reached the vault) — not simply the newest
    # record, which is often this pre-analyst input and would file a prettier verdict than the
    # note being overwritten ever had.
    analyzed = [c for c in copies if c[1].get("analyst")]
    from_verdict = ((analyzed[0] if analyzed else copies[0])[1].get("fidelity") or {}).get("verdict")
    print(f"REANALYZE {bundle_name} <- {bundle_dir.name} (backend={backend}, "
          f"from_verdict={from_verdict})", flush=True)
    emit("analyst", "rerun", source=source, bundle=bundle_name, backend=backend,
         from_verdict=from_verdict, sha=source_sha[:16])

    with tempfile.TemporaryDirectory(prefix="fp-reanalyze-") as work_str:
        work = Path(work_str) / bundle_name
        shutil.copytree(bundle_dir, work)
        try:
            meta = apply_analyst(work, bundle_name, backend)
        except Exception as exc:
            emit("analyst", "rerun_failed", source=source, bundle=bundle_name,
                 error=str(exc)[:150])
            raise
        print(f"ANALYST done: {meta}", flush=True)

        # The supersede intent: authored by the widget's ⟲ click exactly as ⟳ authors its
        # marker (docs/15 §14.2's contract — a named, opt-in exception, never a re-drop).
        # Same stamper, so the manifest shape and the audit/supersede event stay identical.
        manifest_path = work / "manifest.json"
        fresh = json.loads(manifest_path.read_text(encoding="utf-8"))
        _stamp_supersede_safe(
            fresh,
            {"reason": "analyst-rerun", "from_verdict": from_verdict,
             "source_sha256": source_sha,
             "requested_at_epoch_s": int(time.time())},
            source_sha, bundle_name,
        )
        manifest_path.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")

        # Keep the as-shipped copy for archaeology, beside (never over) the original.
        ANCHOR.mkdir(parents=True, exist_ok=True)
        anchor_dest = unique_anchor(ANCHOR / f"{bundle_name} [analyst-{backend} rerun]")
        shutil.copytree(work, anchor_dest)
        print(f"ANCHORED {anchor_dest}", flush=True)

        if _enforce_hold(work, bundle_name, source_sha):
            return
        ship(work, bundle_name, source_sha)


# ---------- J31: re-audit a repaired held bundle (D-1, signed Rab 2026-09-05) ----------

def _reaudit_skip_bench_files(_src, names):
    """copytree() filter for the J31 staging copy: everything under held/<ID> travels EXCEPT
    the Repair Bench's own working files — a *.bench-bak, repairs.jsonl, REPAIRS.md — which
    describe the repair SESSION, not the book. assets/, blocks.json and the J33 Marker-body
    sidecar all travel unfiltered, same as any other copytree."""
    return {n for n in names if n.endswith(".bench-bak") or n in ("repairs.jsonl", "REPAIRS.md")}


def reaudit(bundle_id: str, dry_run: bool = False) -> None:
    """J31 (D-1, verdict rule signed Rab 2026-09-05): re-audit a Repair-Bench-repaired held
    bundle (`held/<bundle_id>`, a sha16 or a `<sha16>--superseded-<stamp>` sibling) against
    BOTH references — the PDF witness (audit_convert) and the Marker body (audit_analyst) —
    computed on a `tempfile.TemporaryDirectory` staging COPY, never in place.

    CPU-ONLY SPAN: this never touches the GPU or ollama — Marker never runs, the analyst
    never runs, only pymupdf witness extraction (audit_convert) and text comparison
    (audit_analyst). `main()`'s `acquire_card_mutex()` still runs first for every entry
    (docs/37 §3.2's unconditional rule), which is harmless here: the mutex is held for a
    span that costs no GPU-hours.

    `--dry-run` runs the SAME staging-copy audit and PRINTS the verdict, but writes nothing
    back (neither copy of manifest.json), ships nothing, and emits NO EVENT AT ALL — not even
    a refusal. A dry-run `audit/scored` would become the newest such record `assay.rs::bless`
    reads, silently changing what a human bless click on some OTHER book means; a dry-run
    refusal event carries no such hazard by itself, but this function suppresses every emit
    uniformly under --dry-run so the flag means what it says: nothing observable happens.

    The historical `fidelity.convert` / `fidelity.analyst` blocks are NEVER touched — only
    `fidelity.final`, `fidelity.verdict` and `fidelity.reaudit` are added/updated. A human
    repair may then change a verdict, WITH provenance (`fidelity.reaudit.from`)."""
    # R1 (verifier GO_AMENDED, 2026-09-05): validate the ID BEFORE the filesystem is touched at
    # all — a `bundle_id` from an untrusted caller (e.g. a widget-relayed argument) must never
    # reach a `HELD / bundle_id` join that a `..`, an absolute path, or an embedded separator
    # could walk outside `held/`. This is a NAME, never a path.
    if (not bundle_id or bundle_id in (".", "..") or os.sep in bundle_id
            or (os.altsep and os.altsep in bundle_id) or Path(bundle_id).is_absolute()):
        sys.exit(f"REAUDIT refused: invalid ID {bundle_id!r} (a held/ directory NAME, never a "
                 "path)")
    held_dir = HELD / bundle_id
    # Belt-and-suspenders on the resolved path too: even an ID that passes the syntactic check
    # above must still land as a DIRECT CHILD of HELD once resolved (symlink/junction escape).
    if held_dir.resolve().parent != HELD.resolve():
        sys.exit(f"REAUDIT refused: {bundle_id!r} does not resolve under {HELD}")
    if not held_dir.is_dir():
        sys.exit(f"REAUDIT refused: no held bundle {bundle_id!r} at {held_dir}")
    manifest_path = held_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_sha = manifest["source_sha256"]
    old_verdict = (manifest.get("fidelity") or {}).get("verdict")
    # R4 (verifier GO_AMENDED, 2026-09-05): this verb re-audits an EXISTING fidelity verdict —
    # a bundle with no `fidelity.verdict` at all was never audited by this pipeline in the
    # first place, so there is no prior verdict for D-1 to compare a repair against.
    if not old_verdict:
        sys.exit(f"REAUDIT refused: {bundle_id!r} carries no prior fidelity.verdict — not a "
                 "bundle this verb is for")

    # REPAIRS.md is a Repair Bench REPORT, not the bundle's note (bench.py's own GENERATED_MD
    # exclusion, S79) — without it, a bench that had declared this patient done would make
    # every "exactly one .md" scan in the pipeline see two and refuse, this one included.
    md_candidates = sorted(p for p in held_dir.glob("*.md") if p.name != "REPAIRS.md")
    if len(md_candidates) != 1:
        sys.exit(f"REAUDIT refused: expected exactly one .md in {held_dir}, found "
                  f"{[p.name for p in md_candidates]}")
    bundle_name = md_candidates[0].stem

    pdf_path = fp_paths.root("drop_done") / manifest["source"]
    if not pdf_path.is_file():
        if not dry_run:
            emit("audit", "reaudit_refused", bundle=bundle_name, sha=source_sha[:16],
                 reason="pdf missing")
        sys.exit(f"REAUDIT refused: source PDF not found at {pdf_path} "
                 f"(drop/done/{manifest['source']!r}) — nothing changed")

    raw = md_candidates[0].read_text(encoding="utf-8")
    # The SAME split apply_analyst uses (:1723-ish): head, body = raw.split("---\n", 2)[1:3].
    parts = raw.split("---\n", 2)
    body = parts[2] if len(parts) == 3 else raw

    sidecar = held_dir / f"{bundle_name}{MARKER_BODY_SUFFIX}"
    reference_text: str | None = None
    reference_kind: str | None = None
    # R2 (verifier GO_AMENDED, 2026-09-05): the sidecar is an UNVERIFIED file living in a
    # human-editable held/ directory (a Repair Bench operator could touch it, or it could be
    # stale from a prior book at this name) — trust it as the reference ONLY when it matches
    # the manifest's OWN record of what J33 actually wrote (`marker_body.sha256`/`.bytes`),
    # never on its mere presence. A manifest with no `marker_body` key (a bundle converted
    # before J33 existed) gets the sidecar ignored the same way — there is nothing to verify it
    # against.
    mb = manifest.get("marker_body") or {}
    if sidecar.is_file() and mb.get("sha256"):
        data = sidecar.read_bytes()
        if (hashlib.sha256(data).hexdigest() == mb["sha256"]
                and len(data) == mb.get("bytes", len(data))):
            reference_text = data.decode("utf-8")
            reference_kind = "sidecar"
        else:
            print("REAUDIT: sidecar present but does not match manifest.marker_body — ignored",
                  flush=True)
    if reference_text is None:
        slice_dir = CHUNK_WORK / source_sha[:16]
        slices = sorted(slice_dir.glob("slice-*/slice.md")) if slice_dir.is_dir() else []
        if slices:
            reference_text = rewrite_image_links(
                "".join(p.read_text(encoding="utf-8") for p in slices)
            )
            reference_kind = "slice-cache"

    if reference_text is None and manifest.get("analyst"):
        # Never compute a prettier verdict by silently dropping the analyst stage: a book
        # that WAS analysed keeps needing an analyst-stage answer, refusal or not.
        if not dry_run:
            emit("audit", "reaudit_refused", bundle=bundle_name, sha=source_sha[:16],
                 reason="analyst reference unavailable")
        sys.exit(f"REAUDIT refused: no Marker-body reference for {bundle_name!r} (no "
                 f"{sidecar.name}, no slice cache under {CHUNK_WORK / source_sha[:16]}) and "
                 "the manifest carries an analyst block — nothing changed")

    import fidelity_audit as fa

    with tempfile.TemporaryDirectory(prefix="fp-reaudit-") as work_str:
        staging = Path(work_str) / bundle_name
        shutil.copytree(held_dir, staging, ignore=_reaudit_skip_bench_files)

        assets_dir = staging / "assets"
        asset_count = sum(1 for _ in assets_dir.iterdir()) if assets_dir.exists() else None
        conv = fa.audit_convert(pdf_path, body, manifest.get("lane", "clean"),
                                 asset_count=asset_count)
        an = fa.audit_analyst(reference_text, body) if reference_text is not None else None
        verdict = fa.compute_verdict(conv, an)

        fid = manifest.setdefault("fidelity", {})
        old_convert = fid.get("convert") or {}  # HISTORY — read only, never overwritten below
        final = {"convert": conv, "text_audited": "held-post-analyst", "reference": reference_kind}
        if an is not None:
            final["analyst"] = an
        fid["final"] = final
        fid["verdict"] = verdict

        repairs = manifest.get("repairs")
        repairs_digest = (
            hashlib.sha256(json.dumps(repairs, sort_keys=True).encode("utf-8")).hexdigest()
            if repairs is not None else None
        )
        fid["reaudit"] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "by": "convert_and_ship --reaudit",
            "reason": "repair-bench",
            "repairs_digest": repairs_digest,
            "from": {
                "verdict": old_verdict,
                "convert": {
                    "doc_survival": old_convert.get("doc_survival"),
                    "pages_flagged": len(old_convert.get("pages_flagged") or []),
                    "runs_total": old_convert.get("runs_total"),
                    "degeneration": (old_convert.get("tripwires") or {}).get("degeneration"),
                },
            },
        }

        print(f"REAUDIT {bundle_name} ({bundle_id}): from_verdict={old_verdict} -> "
              f"verdict={verdict} (reference={reference_kind})", flush=True)

        if dry_run:
            print("DRY-RUN: not writing, not shipping, no event emitted", flush=True)
            return

        # bless()-shaped fields, exactly _audit_convert_safe's own emit signature, phase
        # "final" / reason "reaudit" naming this as the re-audit's own scored record
        # (assay.rs::bless finds the NEWEST audit/scored for `source` — this IS that record
        # once it lands).
        emit("audit", "scored", source=manifest.get("source", bundle_name), phase="final",
             reason="reaudit", kind=conv["kind"], doc_survival=conv["doc_survival"],
             runs=len(conv["runs"]), runs_total=conv.get("runs_total"),
             degeneration=conv["tripwires"]["degeneration"], verdict=verdict)
        if verdict != "pass":
            emit("audit", "flagged", source=manifest.get("source", bundle_name),
                 phase="final", verdict=verdict)
        emit("audit", "reaudit", bundle=bundle_name, sha=source_sha[:16],
             from_verdict=old_verdict, verdict=verdict, reference=reference_kind,
             repairs_digest=repairs_digest)

        if verdict == "fail":
            # Every failure path leaves held/<ID> byte-unchanged except this manifest write.
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"REAUDIT {bundle_name}: still fail — stays held", flush=True)
            return

        # flag/pass: the same opt-in provenance authoring _stamp_supersede_safe already gives
        # ⟳ re-convert and --reanalyze — never a silent overwrite.
        _stamp_supersede_safe(
            manifest,
            {"reason": "reaudit", "from_verdict": old_verdict, "source_sha256": source_sha,
             "requested_at_epoch_s": int(time.time())},
            source_sha, bundle_name,
        )
        serialized = json.dumps(manifest, indent=2) + "\n"
        (staging / "manifest.json").write_text(serialized, encoding="utf-8")
        manifest_path.write_text(serialized, encoding="utf-8")

        # _enforce_hold is a no-op here (the on-disk verdict it re-reads is flag/pass, not
        # fail) — called anyway because it is the ONE chokepoint every ship path passes
        # (docs/15 §12's alarm doorway), not to change behavior.
        _enforce_hold(staging, bundle_name, source_sha)
        ship(staging, bundle_name, source_sha)

        # S65: never delete a human-repaired bundle. Rename beside itself, never over it —
        # if the rename fails (Windows: the bench may still hold a file open), leave the
        # held bundle in place with a printed warning rather than lose it.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        reshipped = HELD / f"{bundle_id}--reshipped-{stamp}"
        try:
            held_dir.rename(reshipped)
            print(f"REAUDIT {bundle_name}: shipped — held bundle renamed -> {reshipped.name}",
                  flush=True)
        except OSError as exc:
            print(f"REAUDIT {bundle_name}: shipped, but could not rename {held_dir} "
                  f"(left in place, not lost): {exc}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path, nargs="?")
    ap.add_argument("--dry-run", action="store_true", help="convert + bundle, do not ship")
    ap.add_argument("--analyst", action="store_true",
                    help="run the link-fenced LLM readability pass (docs/12 slice 2)")
    ap.add_argument("--backend", choices=["local", "gemini", "none"], default="local",
                    help="analyst backend: local qwen3 (air-gapped) or Gemini Flash (cloud)")
    ap.add_argument("--defer-analyst", action="store_true",
                    help="convert + park in pending/ for the widget pre-flight card; no ship")
    ap.add_argument("--resume", metavar="ID",
                    help="ship a pending bundle (widget decision), analyst per --backend")
    ap.add_argument("--reanalyze", metavar="SOURCE",
                    help="analyst-only re-run of an anchored bundle (docs/19 §3.1); Marker "
                         "never runs and the result ships as a supersede")
    ap.add_argument("--reaudit", metavar="ID",
                    help="J31 (D-1): re-audit a Repair-Bench-repaired held/<ID> bundle "
                         "against both references and, on flag/pass, ship it as a supersede; "
                         "CPU-only — never GPU, never ollama. --dry-run prints the verdict "
                         "and changes/ships/emits nothing")
    args = ap.parse_args()

    # The GPU span begins here for EVERY entry — convert, --resume, --reanalyze, --reaudit —
    # so the card is claimed before dispatch (docs/37 §3.2, signed; SYM-042's cover). Held to
    # process exit; the OS releases it. Harmless for --reaudit specifically: that span is
    # CPU-only (pymupdf witness extraction + text comparison, never Marker, never ollama), so
    # holding the mutex costs no GPU-hours — it is simply unconditional for every entry.
    acquire_card_mutex()

    if args.reaudit:
        reaudit(args.reaudit, dry_run=args.dry_run)
        return
    if args.resume:
        resume(args.resume, args.backend)
        return
    if args.reanalyze:
        if args.backend not in ("local", "gemini"):
            sys.exit("--reanalyze needs an analyst backend: local or gemini")
        reanalyze(args.reanalyze, args.backend)
        return
    if args.pdf is None:
        sys.exit("a PDF path is required unless --resume is given")
    src = args.pdf.resolve()
    if not src.is_file():
        sys.exit(f"not a file: {src}")

    with tempfile.TemporaryDirectory(prefix="fp-convert-") as work_str:
        work = Path(work_str)
        tmp_dir, bundle_name, manifest = convert(src, work, use_analyst=args.analyst,
                                                 analyst_backend=args.backend)
        ANCHOR.mkdir(parents=True, exist_ok=True)
        anchor_dest = unique_anchor(ANCHOR / bundle_name)
        shutil.copytree(tmp_dir, anchor_dest)
        print(f"ANCHORED {anchor_dest}", flush=True)
        if args.defer_analyst:
            md = (tmp_dir / f"{bundle_name}.md").read_text(encoding="utf-8")
            defer(tmp_dir, bundle_name, manifest, len(md))
        elif args.dry_run:
            print("DRY-RUN: not shipping", flush=True)
        elif not _enforce_hold(tmp_dir, bundle_name, manifest["source_sha256"]):
            ship(tmp_dir, bundle_name, manifest["source_sha256"])
    print(json.dumps({k: manifest[k] for k in
                      ("source", "source_sha256", "engine", "lane", "pages")}, indent=2))


if __name__ == "__main__":
    main()
