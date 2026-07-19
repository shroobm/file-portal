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

MARKER = Path(r"C:\Users\Bndit\ml\marker-env\Scripts\marker_single.exe")
ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
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

def convert(src: Path, work: Path) -> tuple[Path, dict]:
    chars, pages, ocr_fonts = probe(src)
    extra, lane, lane_reason = route(chars, ocr_fonts)
    print(f"PROBE {src.name}: {chars:.1f} chars/page, {pages} pages, ocr_fonts={ocr_fonts}"
          f" -> lane={lane} ({lane_reason})", flush=True)

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
    (tmp_dir / f"{bundle_name}.md").write_text(
        frontmatter + rewrite_image_links(markdown), encoding="utf-8"
    )
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
    ssh = subprocess.run(
        ["tailscale", "ssh", REMOTE, remote_cmd],
        stdin=tar.stdout, capture_output=True, text=True, timeout=600,
    )
    tar.wait(timeout=60)
    if tar.returncode != 0 or ssh.returncode != 0:
        raise RuntimeError(f"ship failed: tar={tar.returncode} ssh={ssh.returncode} "
                           f"{ssh.stderr.strip()[:300]}")
    print(f"SHIPPED {bundle_name} -> {REMOTE}:{REMOTE_STAGING}/", flush=True)


def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="convert + bundle, do not ship")
    args = ap.parse_args()
    src = args.pdf.resolve()
    if not src.is_file():
        sys.exit(f"not a file: {src}")

    with tempfile.TemporaryDirectory(prefix="fp-convert-") as work_str:
        work = Path(work_str)
        tmp_dir, bundle_name, manifest = convert(src, work)
        ANCHOR.mkdir(parents=True, exist_ok=True)
        anchor_dest = unique_anchor(ANCHOR / bundle_name)
        shutil.copytree(tmp_dir, anchor_dest)
        print(f"ANCHORED {anchor_dest}", flush=True)
        if args.dry_run:
            print("DRY-RUN: not shipping", flush=True)
        else:
            ship(tmp_dir, bundle_name, manifest["source_sha256"])
    print(json.dumps({k: manifest[k] for k in
                      ("source", "source_sha256", "engine", "lane", "pages")}, indent=2))


if __name__ == "__main__":
    main()
