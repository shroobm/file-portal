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
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

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
        emit("audit", "scored", source=name, phase="convert", kind=conv["kind"],
             doc_survival=conv["doc_survival"], runs=len(conv["runs"]),
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
             verdict=manifest["fidelity"]["verdict"])
        if manifest["fidelity"]["verdict"] == "fail":
            emit("audit", "flagged", source=name, phase="analyst", verdict="fail")
    except Exception as exc:  # noqa: BLE001
        emit("audit", "error", phase="analyst", error=str(exc)[:150])


MARKER = Path(r"C:\Users\Bndit\ml\marker-env\Scripts\marker_single.exe")
ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
PENDING = Path(r"C:\Users\Bndit\ml\library\pending")  # deferred-analyst queue (widget card)
HELD = Path(r"C:\Users\Bndit\ml\library\held")  # audit-failed bundles (enforce mode; assay card)
AUDIT_MODE_FILE = Path(r"C:\Users\Bndit\ml\library\audit-mode.txt")  # report | enforce (docs/15 §12)
REMOTE = "rab@archlinux"
REMOTE_STAGING = "~/file-portal/library/staging"
MIN_CHARS_PER_PAGE = 100  # provisional, same value + revisit-note as the ThinkPad's
RECOGNITION_BATCH = 32
CONVERTER_VERSION = "0.1.0-desktop"
# Stage A (docs/18 §5.1, decided 2026-07-31): progress frozen this long while Marker still
# runs = the stall signature → kill early. Generous vs the longest legitimate quiet phase
# (model load ~1-2 min); both wedge species (S48 pipe-deadlock, S45 VRAM-thrash) freeze for hours.
STALL_FROZEN_S = 900

# S42: live convert progress (docs/16 §8 #3). The widget's line.rs reads this file while a
# convert holds the .gpu-lock; the Room shows the real Marker/surya stage + per-page count.
# ENTIRELY best-effort: writing/parsing this must never affect the conversion (see convert()).
PROGRESS_FILE = Path(r"C:\Users\Bndit\ml\library\.convert-progress.json")
# surya/tqdm bar, e.g. "Recognizing Layout:  33%|###3      | 1/3 [00:04<00:09, 4.67s/it]".
# Indeterminate bars ("Detecting bboxes: 0it [...]") simply don't match and are skipped.
_TQDM_RE = re.compile(r"([A-Za-z][\w ()/-]*?):\s*(\d{1,3})%\|[^|]*\|\s*(\d+)\s*/\s*(\d+)")


def _write_progress(stage: str, pct: int, n: int, total: int) -> None:
    try:
        PROGRESS_FILE.write_text(json.dumps({
            "stage": stage, "pct": pct, "n": n, "total": total,
            "frac": max(0.0, min(1.0, pct / 100.0)),
        }), encoding="utf-8")
    except OSError:
        pass  # progress is cosmetic — a write failure must never matter


def _clear_progress() -> None:
    try:
        PROGRESS_FILE.unlink()
    except OSError:
        pass


# Stage E (docs/19 §5): the ledger-fed promise, written ONCE at convert start so the widget can
# project it verbatim. Python is the only authority on the estimate (blind spot #1: never derive
# the same number twice in two languages); line.rs reads this file, it never recomputes it.
ESTIMATE_FILE = Path(r"C:\Users\Bndit\ml\library\.convert-estimate.json")


def _write_estimate_safe(source: str, pages: int, lane: str, chars: float) -> dict | None:
    """File the conversion's PROMISE beside its progress: the similarity estimate the ledger can
    back, or an honest absence. Best-effort in every direction — the promise must never cost
    the conversion (S42 rule)."""
    try:
        est = estimate_from_ledger(pages, lane, chars)
        payload = {"source": source, "pages": pages, "lane": lane}
        if est:
            payload.update(est)
            emit("convert", "estimate", source=source, eta_s=est["eta_s"],
                 s_per_page=est["s_per_page"], basis=est["basis"], samples=est["samples"])
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
CHUNK_BATCH_FILE = Path(r"C:\Users\Bndit\ml\library\chunk-batch.txt")
CHUNK_BATCH_ALLOWED = (8, 16, 32)
CHUNK_BATCH_DEFAULT = 16
# Completed slices live HERE, not in the run's temp dir, because resume must survive the process
# that made them: keyed by (source_sha16, page_range) exactly as the spec requires.
CHUNK_WORK = Path(r"C:\Users\Bndit\ml\library\.chunk-work")


def chunk_batch() -> int:
    """The slice recognition batch lever. Anything unparseable or off-menu falls back to the
    default rather than handing Marker a number nobody chose."""
    try:
        value = int(CHUNK_BATCH_FILE.read_text(encoding="utf-8").strip())
        return value if value in CHUNK_BATCH_ALLOWED else CHUNK_BATCH_DEFAULT
    except (OSError, ValueError):
        return CHUNK_BATCH_DEFAULT


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


def probe(path: Path) -> tuple[float, int, bool]:
    """chars/page, page count, and whether the text layer is an OCR overlay.

    OCR layers paint invisible text over the scan image: text render mode 3
    (`get_texttrace` span type 3). Verified live: the Beer book's 2013 Archive.org
    layer is 100% type-3 "Courier"; a born-digital Chromium print is type 0.
    Majority-of-spans rule so a stray invisible watermark can't flip a real layer;
    the font-name check (tesseract's GlyphLessFont etc.) is kept as a secondary.
    """
    invisible_spans = 0
    total_spans = 0
    ocr_font_seen = False
    with pymupdf.open(path) as doc:
        pages = doc.page_count or 1
        total = 0
        for page in doc:
            total += len(page.get_text())
            for span in page.get_texttrace():
                total_spans += 1
                if span.get("type") == 3:
                    invisible_spans += 1
                if not ocr_font_seen and _OCR_FONT.search(str(span.get("font", ""))):
                    ocr_font_seen = True
    ocr_layer = ocr_font_seen or (total_spans > 0 and invisible_spans / total_spans > 0.5)
    return total / pages, pages, ocr_layer


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
LEDGER_FILE = Path(r"C:\Users\Bndit\ml\library\conversion-ledger.jsonl")


def _ledger_record(manifest: dict, cost_s: float, peak_mib: int,
                   resumed_slices: int = 0, run_wall_s: float | None = None) -> None:
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
    """The similarity-based estimate (docs/18 §5.2): same lane first, then the nearest chars/pp
    neighbours, median of their s/page. Falls back to same-lane median, then None — a promise is
    only made when there is real evidence behind it."""
    try:
        rows = [json.loads(l) for l in
                LEDGER_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
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
    median = rates[len(rates) // 2]
    return {
        "s_per_page": median,
        "eta_s": int(median * pages),
        "basis": "similar",
        "samples": len(neighbours),
        "from_lane": lane,
    }


# ---------- the monitored Marker run (one whole book, or one slice of one) ----------

def _run_marker(engine_src: Path, engine_stem: str, out_root: Path, extra: list[str],
                pages: int, source_name: str, page_range: str | None = None,
                progress_prefix: str = "") -> tuple[Path, str, float, int]:
    """Run Marker once under the S52 stall monitor and return (out_dir, markdown, wall, peak MiB).

    Extracted at S60 so the whole-book path and every chunked slice share ONE implementation of
    the hard-won parts: the draining reader thread (S48's pipe deadlock), the tree-kill (S48's
    orphan), the kill-early stall signature (S45/S48), and the page-scaled outer timeout (S45).
    `page_range` is Marker's own 0-indexed `--page_range`; `progress_prefix` labels the progress
    file so the Room can say which slice is running."""
    _clear_progress()
    captured: list[str] = []

    def _reader(pipe) -> None:
        try:
            for line in pipe:  # text mode: universal newlines split tqdm's \r refreshes into lines
                captured.append(line)
                try:
                    m = _TQDM_RE.search(line)
                    if m:
                        _write_progress(f"{progress_prefix}{m.group(1).strip()}", int(m.group(2)),
                                        int(m.group(3)), int(m.group(4)))
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
        [str(MARKER), str(engine_src), "--output_dir", str(out_root),
         "--output_format", "markdown", *extra,
         *(["--page_range", page_range] if page_range else [])],
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

    def _kill_and_clear() -> None:
        _kill_tree(proc.pid)  # /T first — proc.kill() alone would orphan marker's real python
        proc.kill()
        proc.wait()
        reader.join(timeout=5)
        _clear_progress()

    # Stage A (docs/18 §4A; policy §5.1 "kill early", decided 2026-07-31): the wait is a monitor.
    # PROGRESS_FILE's mtime is the liveness signal Marker already emits; frozen too long while the
    # process still runs is the stall signature of BOTH wedge species (the S48 pipe-deadlock froze
    # it at zero CPU, the S45 VRAM-thrash at pinned GPU). Monitoring is best-effort and can never
    # fail a healthy convert (S42 rule); the scaled hard timeout stays as the outer bound.
    while True:
        try:
            proc.wait(timeout=30)
            break
        except subprocess.TimeoutExpired:
            pass
        elapsed = time.perf_counter() - t0
        # Stage D's conversion ledger wants peak VRAM, and this loop is already the thing that
        # watches the GPU — sample here rather than adding a second watcher.
        peak_mib = max(peak_mib, _gpu_signature().get("gpu_mem_used_mib", 0))
        if elapsed >= timeout_s:
            _kill_and_clear()
            raise RuntimeError(f"marker timed out after {timeout_s}s ({pages} pages)")
        try:
            frozen_s = time.time() - PROGRESS_FILE.stat().st_mtime
        except OSError:
            frozen_s = elapsed  # nothing written yet (model load etc.) — measure from start
        if frozen_s > STALL_FROZEN_S:
            sig = _gpu_signature()
            _kill_and_clear()
            emit("convert", "stalled", source=source_name, frozen_s=int(frozen_s),
                 elapsed_s=int(elapsed), page_range=page_range, **sig)
            raise RuntimeError(
                f"marker stalled: progress frozen {int(frozen_s)}s "
                f"(kill-early policy, docs/18 §5.1)")
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


def _convert_chunked(source_name: str, engine_src: Path, engine_stem: str, work: Path,
                     out_root: Path, extra: list[str], pages: int,
                     source_sha: str) -> tuple[str, Path, float, int, dict]:
    """Convert a long book in 200-page slices and merge (docs/18 §5.2, signed S57).

    Returns (merged markdown, merged assets dir, total wall, peak MiB, chunking manifest block).

    RESUME is the point of the whole design: each finished slice is published into
    `.chunk-work/<sha16>/slice-<start>-<end>/` OUTSIDE the run's temp dir, so a killed slice (or
    a killed process, or a reboot) costs only that slice — a re-run converts the missing ones and
    skips the rest. Publication is dot-dir-then-rename, so a half-written slice can never be
    mistaken for a finished one. The whole book's slice dir is removed once the merge succeeds:
    the bundle now holds everything, and these are gigabytes."""
    batch = chunk_batch()
    ranges = slice_ranges(pages)
    total = len(ranges)
    book_work = CHUNK_WORK / source_sha[:16]
    book_work.mkdir(parents=True, exist_ok=True)
    merged_assets = work / "merged-assets"
    merged_assets.mkdir(parents=True, exist_ok=True)
    slice_extra = _with_batch(extra, batch)
    print(f"CHUNKING {source_name}: {pages} pages -> {total} slices of {SLICE_PAGES} "
          f"(recognition batch {batch}, lever {CHUNK_BATCH_FILE.name})", flush=True)
    emit("convert", "chunking", source=source_name, pages=pages, slices=total,
         slice_size=SLICE_PAGES, batch=batch)

    parts: list[str] = []
    total_wall = 0.0      # GPU time spent in THIS run (what the convert event reports)
    resumed_wall = 0.0    # GPU time the resumed slices cost when they ran (the ledger wants it)
    resumed_count = 0
    peak_mib = 0
    for i, (start, end) in enumerate(ranges, 1):
        slice_dir = book_work / f"slice-{start:05d}-{end:05d}"
        if not (slice_dir / ".done").is_file():
            staging = book_work / f".part-{start:05d}-{end:05d}"
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(out_root, ignore_errors=True)  # Marker reuses <out_root>/<stem>
            print(f"SLICE {i}/{total} pages {start}-{end} …", flush=True)
            out_dir, md, wall, mib = _run_marker(
                engine_src, engine_stem, out_root, slice_extra, end - start + 1, source_name,
                page_range=f"{start}-{end}", progress_prefix=f"slice {i}/{total} · ")
            total_wall += wall
            peak_mib = max(peak_mib, mib)
            # Assets keep the names Marker gave them: those are already ABSOLUTE page numbers
            # (see the note above — measured on the Damodaran run, not assumed), so slices cannot
            # collide and the markdown needs no rewriting either. The tripwire fires if that ever
            # stops being true, because silently mislabelled pages are the expensive failure.
            staging.mkdir(parents=True)
            (staging / "slice.md").write_text(md, encoding="utf-8")
            imgs = [p for p in sorted(out_dir.iterdir())
                    if p.suffix.lower() in (".jpeg", ".jpg", ".png")]
            stray = out_of_range_assets([p.name for p in imgs], start, end)
            if stray:
                print(f"  WARNING: {len(stray)} asset(s) outside pages {start}-{end}, "
                      f"e.g. {stray[:3]} — Marker's asset numbering may have changed", flush=True)
                emit("convert", "asset_range_warning", source=source_name,
                     page_range=f"{start}-{end}", count=len(stray), examples=stray[:3])
            for img in imgs:
                shutil.copy2(img, staging / img.name)
            (staging / ".done").write_text(
                json.dumps({"source_sha256": source_sha, "page_range": f"{start}-{end}",
                            "wall_s": round(wall, 1), "batch": batch}) + "\n", encoding="utf-8")
            staging.rename(slice_dir)  # atomic publish: .done exists only on a complete slice
            emit("convert", "slice", source=source_name, slice=i, slices=total,
                 page_range=f"{start}-{end}", wall_s=round(wall, 1), resumed=False)
        else:
            # A resumed slice costs this run nothing, but it DID cost the GPU when it ran, and
            # the ledger is trying to learn what a book of this shape actually takes. Counting
            # only the re-run would file a rate that gets quietly better every time a slice is
            # retried — an estimator that flatters itself (found on the Damodaran run: 1.69 s/pp
            # reported vs 1.94 s/pp truly spent).
            try:
                prior = json.loads((slice_dir / ".done").read_text(encoding="utf-8"))
                resumed_wall += float(prior.get("wall_s") or 0.0)
            except (OSError, ValueError, TypeError):
                pass
            resumed_count += 1
            print(f"SLICE {i}/{total} pages {start}-{end}: RESUMED (already converted)", flush=True)
            emit("convert", "slice", source=source_name, slice=i, slices=total,
                 page_range=f"{start}-{end}", resumed=True)
        parts.append((slice_dir / "slice.md").read_text(encoding="utf-8"))
        for img in sorted(slice_dir.iterdir()):
            if img.suffix.lower() in (".jpeg", ".jpg", ".png"):
                shutil.copy2(img, merged_assets / img.name)

    # Clean cuts: the seam is RECORDED, never smoothed. Overlap reconciliation in v1 risks
    # silent text loss, which is the one failure this factory refuses to trade for tidiness.
    # Seams are 1-based absolute page numbers of each slice's first page, after the first.
    chunking = {"slice_size": SLICE_PAGES, "batch": batch,
                "seams": [start + 1 for start, _ in ranges[1:]]}
    shutil.rmtree(book_work, ignore_errors=True)
    stats = {"cost_s": total_wall + resumed_wall, "resumed_slices": resumed_count}
    return "\n\n".join(parts), merged_assets, total_wall, peak_mib, chunking, stats


# ---------- the slice ----------

def convert(src: Path, work: Path, use_analyst: bool = False,
            analyst_backend: str = "local") -> tuple[Path, str, dict]:
    # Claim the ⟳ remedy intent FIRST (consume-once, docs/15 §14.2): read and delete before any
    # work happens, so a marker can never survive this conversion. Stamped into the manifest
    # further down, once the source sha is known and can be checked against it.
    supersede_marker = _take_supersede_marker(src)
    chars, pages, ocr_fonts = probe(src)
    extra, lane, lane_reason = route(chars, ocr_fonts)
    print(f"PROBE {src.name}: {chars:.1f} chars/page, {pages} pages, ocr_fonts={ocr_fonts}"
          f" -> lane={lane} ({lane_reason})", flush=True)
    emit("convert", "probe", source=src.name, chars_per_page=round(chars, 1),
         pages=pages, lane=lane, lane_reason=lane_reason)
    # Stage E: the promise, filed before the work (docs/18 §5.2's promise-vs-actual pairing).
    promised = _write_estimate_safe(src.name, pages, lane, chars)

    # Convert from a short sanitizer-proof copy (the ThinkPad's L15 idiom): Marker derives
    # its output dir and asset names from the input stem.
    engine_stem = slugify(src.stem)[:40]
    engine_src = work / f"{engine_stem}{src.suffix.lower()}"
    shutil.copy2(src, engine_src)
    out_root = work / "marker-out"
    source_sha = sha256_of(src)  # needed up here now: slice resume is keyed by it

    # Stage D (docs/18 §5.2): long books convert in slices. The threshold is lane-aware because
    # the lanes cost different VRAM, and the page count is the probe's, never metadata.
    chunking = None
    if should_chunk(pages, lane):
        markdown, assets_dir, wall, peak_mib, chunking, chunk_stats = _convert_chunked(
            src.name, engine_src, engine_stem, work, out_root, extra, pages, source_sha)
    else:
        out_dir, markdown, wall, peak_mib = _run_marker(
            engine_src, engine_stem, out_root, extra, pages, src.name)
        assets_dir = out_dir
        chunk_stats = {"cost_s": wall, "resumed_slices": 0}
    print(f"CONVERTED in {wall:.1f}s ({wall / pages:.1f} s/page)", flush=True)
    # Stage E: the promise rides the `converted` event beside the actual, forever — the event
    # stream is where the estimator's honesty can be audited later (docs/19 §6 hygiene).
    emit("convert", "converted", source=src.name, wall_s=round(wall, 1),
         s_per_page=round(wall / pages, 2), pages=pages,
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
    frontmatter = render_frontmatter(
        "marker", lane, lane_reason, chars, ocr, 192 if ocr else None, converted_at, source_sha
    )
    import marker  # marker-env only; version for provenance

    manifest = {
        "source": src.name,
        "source_sha256": source_sha,
        "engine": "marker",
        "lane": lane,
        "lane_reason": lane_reason,
        "chars_per_page_detected": chars,
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
    # The ledger learns from the book's TRUE cost, which includes any slices this run resumed
    # rather than re-ran (see _convert_chunked) — otherwise every retry teaches it to promise
    # a little more than the GPU can deliver.
    _ledger_record(manifest, chunk_stats["cost_s"], peak_mib,
                   resumed_slices=chunk_stats["resumed_slices"], run_wall_s=wall)
    body = rewrite_image_links(markdown)
    # Survival Audit of the convert stage (docs/15) — before any analyst pass, so the
    # witness is scored against the raw Marker output. Report-only; never fails the line.
    _audit_convert_safe(src, body, lane, tmp_dir, manifest)
    if use_analyst:
        # Marker has exited: the GPU is free for the analyst (Phase 2 serialization).
        import analyst

        print(f"ANALYST pass starting (link-fenced, backend={analyst_backend})...", flush=True)
        marker_body = body
        body, analyst_meta = analyst.process(body, backend=analyst_backend)
        manifest["analyst"] = analyst_meta
        _audit_analyst_safe(marker_body, body, manifest, name=src.name)
        frontmatter = frontmatter.replace(
            "---\n",
            f"---\nanalyst:\n  model: {analyst_meta['model']}\n"
            f"  backend: {analyst_meta.get('backend', 'local')}\n"
            f"  chunks_passed: {analyst_meta['chunks_passed']}\n"
            f"  chunks_rejected: {analyst_meta['chunks_rejected']}\n"
            f"  chunks_failed: {analyst_meta.get('chunks_failed', 0)}\n"
            f"  duration_s: {analyst_meta['duration_s']}\n",
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
    emit("analyst", "done", bundle=bundle_name, chars=len(body), **{k: meta[k] for k in
         ("backend", "program", "chunks_passed", "chunks_rejected",
          "chunks_failed", "duration_s")})
    frontmatter = (
        f"---\nanalyst:\n  model: {meta['model']}\n  backend: {meta['backend']}\n"
        f"  chunks_passed: {meta['chunks_passed']}\n"
        f"  chunks_rejected: {meta['chunks_rejected']}\n"
        f"  chunks_failed: {meta['chunks_failed']}\n"
        f"  duration_s: {meta['duration_s']}\n" + head + "---\n"
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
    args = ap.parse_args()

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
