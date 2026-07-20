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
REMOTE = "rab@archlinux"
REMOTE_STAGING = "~/file-portal/library/staging"
MIN_CHARS_PER_PAGE = 100  # provisional, same value + revisit-note as the ThinkPad's
RECOGNITION_BATCH = 32
CONVERTER_VERSION = "0.1.0-desktop"

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
        return [], "clean", "text_layer_present"
    return batch, "scan", "no_text_layer"


# ---------- the slice ----------

def convert(src: Path, work: Path, use_analyst: bool = False,
            analyst_backend: str = "local") -> tuple[Path, str, dict]:
    chars, pages, ocr_fonts = probe(src)
    extra, lane, lane_reason = route(chars, ocr_fonts)
    print(f"PROBE {src.name}: {chars:.1f} chars/page, {pages} pages, ocr_fonts={ocr_fonts}"
          f" -> lane={lane} ({lane_reason})", flush=True)
    emit("convert", "probe", source=src.name, chars_per_page=round(chars, 1),
         pages=pages, lane=lane, lane_reason=lane_reason)

    # Convert from a short sanitizer-proof copy (the ThinkPad's L15 idiom): Marker derives
    # its output dir and asset names from the input stem.
    engine_stem = slugify(src.stem)[:40]
    engine_src = work / f"{engine_stem}{src.suffix.lower()}"
    shutil.copy2(src, engine_src)
    out_root = work / "marker-out"
    t0 = time.perf_counter()
    proc = subprocess.run(
        [str(MARKER), str(engine_src), "--output_dir", str(out_root),
         "--output_format", "markdown", "--disable_tqdm", *extra],
        capture_output=True, text=True, timeout=3600,
    )
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"marker exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    out_dir = out_root / engine_stem
    md_files = list(out_dir.glob("*.md"))
    if len(md_files) != 1:
        raise RuntimeError(f"expected exactly one .md in {out_dir}, found {len(md_files)}")
    markdown = md_files[0].read_text(encoding="utf-8")
    print(f"CONVERTED in {wall:.1f}s ({wall / pages:.1f} s/page)", flush=True)
    emit("convert", "converted", source=src.name, wall_s=round(wall, 1),
         s_per_page=round(wall / pages, 2), pages=pages)

    # Assemble the bundle in a dot-prefixed temp dir keyed on the source sha (L13 idiom).
    source_sha = sha256_of(src)
    bundle_name = clamp_name(src.stem)
    tmp_dir = work / f".part-{source_sha[:16]}"
    assets = tmp_dir / "assets"
    assets.mkdir(parents=True)
    for img in sorted(out_dir.iterdir()):
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
    args = ap.parse_args()

    if args.resume:
        resume(args.resume, args.backend)
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
        else:
            ship(tmp_dir, bundle_name, manifest["source_sha256"])
    print(json.dumps({k: manifest[k] for k in
                      ("source", "source_sha256", "engine", "lane", "pages")}, indent=2))


if __name__ == "__main__":
    main()
