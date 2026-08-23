"""Out-of-band P-1 re-score for assembled Desktop conversion bundles.

This host is deliberately outside ``convert_and_ship.py``. It reads one source PDF and one
assembled ``anchor/<bundle>`` directory, calls the report-only P-1 instrument, and adds a
final-conversion inventory that makes P-1's sensitivity ceiling visible.

Two questions stay separate:

1. ``figure_coverage.coverage`` asks whether each source page with a figure-like region has at
   least one mapped bundle asset. It is page-level: three source figures and one asset count as
   covered.
2. ``final_conversion_inventory`` counts raw embedded PDF raster objects, output asset files,
   markdown references, and per-page count mismatches. Those are omission *candidates*, never a
   semantic missing-image verdict: source xrefs include furniture and one source object need not
   become exactly one bundle asset.

The program writes nothing. JSON and the human summary go to stdout. A manifest/source SHA
mismatch is UNREAD and exits non-zero rather than measuring the wrong duplicate bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import figure_coverage as fc


ASSET_SUFFIXES = {".jpeg", ".jpg", ".png"}
OBSIDIAN_ASSET_RE = re.compile(r"!\[\[assets/([^|\]]+)(?:\|[^\]]*)?\]\]", re.I)
MARKDOWN_ASSET_RE = re.compile(r"!\[[^\]]*\]\((?:\./)?assets/([^\s\)]+)(?:\s+[^\)]*)?\)", re.I)


class RescoreUnread(RuntimeError):
    """The requested observation cannot be admitted from the supplied paths."""


def write_utf8(stream, value: str) -> None:
    """Write one line without trusting the Windows console's legacy text encoding."""
    payload = (value + "\n").encode("utf-8")
    binary = getattr(stream, "buffer", None)
    if binary is not None:
        binary.write(payload)
        binary.flush()
    else:
        stream.write(value + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(bundle_dir: Path) -> dict:
    path = bundle_dir / "manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RescoreUnread(f"manifest unreadable at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RescoreUnread(f"manifest is not an object at {path}")
    return value


def resolve_source(bundle_dir: Path, pdf_path: Path | None, source_root: Path | None) -> tuple[Path, dict, str]:
    manifest = read_manifest(bundle_dir)
    manifest_name = manifest.get("source")
    manifest_sha = manifest.get("source_sha256")
    if not isinstance(manifest_name, str) or not manifest_name:
        raise RescoreUnread("manifest.source is absent or invalid")
    if not isinstance(manifest_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", manifest_sha):
        raise RescoreUnread("manifest.source_sha256 is absent or invalid")

    if pdf_path is None:
        if source_root is None:
            raise RescoreUnread("give --pdf or --source-root; source resolution is never guessed")
        pdf_path = source_root / manifest_name
    if not pdf_path.is_file():
        raise RescoreUnread(f"source PDF is absent at {pdf_path}")

    observed_sha = sha256_file(pdf_path)
    if observed_sha.lower() != manifest_sha.lower():
        raise RescoreUnread(
            "source identity mismatch: manifest "
            f"{manifest_sha.lower()} != observed {observed_sha.lower()} at {pdf_path}"
        )
    return pdf_path, manifest, observed_sha


def _normalize_reference(value: str) -> str:
    return Path(unquote(value).replace("\\", "/")).name


def markdown_asset_references(bundle_dir: Path) -> tuple[Path, list[str]]:
    markdown_files = sorted(bundle_dir.glob("*.md"))
    if len(markdown_files) != 1:
        raise RescoreUnread(
            f"bundle must contain exactly one root markdown file; observed {len(markdown_files)}"
        )
    markdown_path = markdown_files[0]
    try:
        text = markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RescoreUnread(f"bundle markdown unreadable at {markdown_path}: {exc}") from exc
    refs = [_normalize_reference(match) for match in OBSIDIAN_ASSET_RE.findall(text)]
    refs.extend(_normalize_reference(match) for match in MARKDOWN_ASSET_RE.findall(text))
    return markdown_path, refs


def source_raster_inventory(pdf_path: Path) -> dict:
    try:
        data = pdf_path.read_bytes()
    except OSError as exc:
        raise RescoreUnread(f"source PDF unreadable at {pdf_path}: {exc}") from exc

    per_page: dict[int, int] = {}
    unique_xrefs: set[int] = set()
    occurrences = 0
    try:
        with fc.pymupdf.open(stream=data, filetype="pdf") as document:
            page_count = len(document)
            for page_index, page in enumerate(document):
                images = page.get_images(full=True)
                occurrences += len(images)
                page_xrefs = {int(image[0]) for image in images}
                unique_xrefs.update(page_xrefs)
                if page_xrefs:
                    per_page[page_index + 1] = len(page_xrefs)
    except Exception as exc:
        raise RescoreUnread(f"source raster inventory failed for {pdf_path}: {exc}") from exc

    return {
        "pages_total": page_count,
        "unique_embedded_raster_objects": len(unique_xrefs),
        "embedded_raster_occurrences": occurrences,
        "pages_with_embedded_rasters": len(per_page),
        "per_page_unique_rasters": per_page,
    }


def repaired_asset_page_counts(bundle_dir: Path, coverage_report: dict) -> dict[int, int]:
    naive = fc.output_asset_pages(bundle_dir)["per_page"]
    detected = coverage_report.get("sym050_doubled_offset", {}).get("detected") is True
    if not detected:
        return dict(naive)
    repaired: dict[int, int] = {}
    for page, count in naive.items():
        true_page = fc.sym050_true_page(page)
        repaired[true_page] = repaired.get(true_page, 0) + count
    return repaired


def final_conversion_inventory(
    pdf_path: Path,
    bundle_dir: Path,
    coverage_report: dict,
    lane: str | None = None,
) -> dict:
    raster = source_raster_inventory(pdf_path)
    markdown_path, references = markdown_asset_references(bundle_dir)
    asset_files = sorted(
        path for path in (bundle_dir / "assets").iterdir()
        if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES
    ) if (bundle_dir / "assets").is_dir() else []

    file_names = {path.name.casefold(): path.name for path in asset_files}
    referenced_names = {name.casefold(): name for name in references}
    missing_files = sorted(referenced_names[key] for key in referenced_names.keys() - file_names.keys())
    unreferenced_files = sorted(file_names[key] for key in file_names.keys() - referenced_names.keys())

    asset_pages = repaired_asset_page_counts(bundle_dir, coverage_report)
    source_pages = raster["per_page_unique_rasters"]
    scan_lane = lane == "scan"
    if scan_lane:
        # A scanned book's source image is the whole page. Hand-drawn diagrams are subregions
        # inside that raster, so xref counts cannot tell whether Marker preserved them. Naming
        # every prose page a candidate would look comprehensive while answering the wrong
        # question. This class needs rendered-page-to-final-asset visual comparison.
        zero_asset_candidates = None
        partial_asset_candidates = None
        candidate_status = "UNREAD"
    else:
        zero_asset_candidates = sorted(
            page for page in source_pages if asset_pages.get(page, 0) == 0
        )
        partial_asset_candidates = sorted(
            page for page, source_count in source_pages.items()
            if 0 < asset_pages.get(page, 0) < source_count
        )
        candidate_status = "DIAGNOSTIC"

    return {
        "source_unique_embedded_raster_objects": raster["unique_embedded_raster_objects"],
        "source_embedded_raster_occurrences": raster["embedded_raster_occurrences"],
        "source_pages_with_embedded_rasters": raster["pages_with_embedded_rasters"],
        "bundle_asset_files": len(asset_files),
        "bundle_asset_pages": len(asset_pages),
        "markdown_file": markdown_path.name,
        "markdown_asset_references": len(references),
        "markdown_unique_asset_references": len(referenced_names),
        "references_missing_asset_file": missing_files,
        "asset_files_without_markdown_reference": unreferenced_files,
        "raw_unique_raster_minus_asset_files":
            raster["unique_embedded_raster_objects"] - len(asset_files),
        "candidate_pages_with_source_rasters_and_zero_assets": zero_asset_candidates,
        "candidate_pages_with_fewer_assets_than_source_rasters": partial_asset_candidates,
        "candidate_zero_asset_page_count": (
            len(zero_asset_candidates) if zero_asset_candidates is not None else None
        ),
        "candidate_partial_asset_page_count": (
            len(partial_asset_candidates) if partial_asset_candidates is not None else None
        ),
        "candidate_status": candidate_status,
        "conditions": {
            "source_unit": "unique PDF image xrefs; repeated furniture is deduplicated globally",
            "page_unit": "unique image xrefs observed on a source page",
            "output_unit": "JPEG/JPG/PNG files whose names map to a source page",
            "page_map": coverage_report.get("page_map"),
            "interpretation": (
                "DIAGNOSTIC ONLY — PDF raster objects, semantic figures, and bundle assets are "
                "not one-to-one. Candidate pages localize review; they do not prove omission."
            ),
            "p1_sensitivity_ceiling": (
                "P-1 remains page-level: a page with multiple source figures and one asset "
                "counts as covered."
            ),
            "scan_lane_rule": (
                "UNREAD — a hand-drawn diagram is a subregion of the full-page scan raster; "
                "xref/asset counts cannot measure whether it survived. Compare rendered source "
                "pages with final assets and their Markdown placement."
                if scan_lane else "not applicable"
            ),
            "write_effect": "NONE — source PDF and bundle are opened read-only; output is stdout",
        },
    }


def run_rescore(
    bundle_dir: Path,
    pdf_path: Path | None = None,
    source_root: Path | None = None,
    use_hashes: bool = True,
) -> dict:
    if not bundle_dir.is_dir():
        raise RescoreUnread(f"bundle directory is absent at {bundle_dir}")
    source, manifest, source_sha = resolve_source(bundle_dir, pdf_path, source_root)
    coverage_report = fc.coverage(source, bundle_dir, use_hashes=use_hashes)
    return {
        "bundle": bundle_dir.name,
        "source": source.name,
        "source_identity": {
            "manifest_sha256": manifest["source_sha256"].lower(),
            "observed_sha256": source_sha,
            "match": True,
        },
        "manifest": {
            "converted_at": manifest.get("converted_at"),
            "lane": manifest.get("lane"),
            "pages": manifest.get("pages"),
            "slice_size": (
                manifest.get("chunking", {}).get("slice_size")
                if isinstance(manifest.get("chunking"), dict) else None
            ),
        },
        "p1_page_coverage": coverage_report,
        "final_conversion_inventory": final_conversion_inventory(
            source, bundle_dir, coverage_report, lane=manifest.get("lane")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Out-of-band P-1 and final-conversion inventory")
    parser.add_argument("--bundle", required=True, type=Path)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--pdf", type=Path)
    source_group.add_argument("--source-root", type=Path)
    parser.add_argument("--no-hashes", action="store_true",
                        help="disable P-1 furniture digesting; reported in P-1 conditions")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()

    try:
        report = run_rescore(
            bundle_dir=arguments.bundle,
            pdf_path=arguments.pdf,
            source_root=arguments.source_root,
            use_hashes=not arguments.no_hashes,
        )
    except RescoreUnread as exc:
        write_utf8(sys.stderr, f"UNREAD — {exc}")
        return 2

    if arguments.json:
        write_utf8(sys.stdout, json.dumps(report, indent=1, ensure_ascii=False))
        return 0

    p1 = report["p1_page_coverage"]
    inventory = report["final_conversion_inventory"]
    lines = [report["bundle"]]
    lines.append(
        "  P-1 page coverage: "
        f"{p1['pages_with_source_figures'] - p1['pages_uncovered']}/"
        f"{p1['pages_with_source_figures']} covered · {p1['pages_uncovered']} uncovered · "
        f"map {p1['page_map']}"
    )
    if inventory["candidate_status"] == "UNREAD":
        lines.append(
            "  final-conversion candidate pages: UNREAD · "
            f"{inventory['conditions']['scan_lane_rule']}"
        )
    else:
        lines.append(
            "  final-conversion inventory: "
            f"{inventory['source_unique_embedded_raster_objects']} unique source raster objects · "
            f"{inventory['bundle_asset_files']} asset files · "
            f"{inventory['candidate_zero_asset_page_count']} zero-asset candidate pages · "
            f"{inventory['candidate_partial_asset_page_count']} partial-asset candidate pages"
        )
    lines.append(f"  {inventory['conditions']['interpretation']}")
    write_utf8(sys.stdout, "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
