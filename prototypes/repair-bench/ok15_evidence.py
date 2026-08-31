"""Read-only OK-15 PDF evidence for the Repair Bench quarantine.

OK-15 adds five observations without changing conversion semantics:

* MuPDF diagnostics are drained at a page boundary and attributed to that page.
* logical PDF page labels are mapped to physical, one-based page ordinals.
* a disposable PDF copy has every optional-content group switched off before a
  tiny counterfactual diagnostic raster is captured beside the normal-view
  digest; neither the source nor Marker's input is modified, primary content is
  never presumed decorative, and the pixels are not retained.
* Xpdf ``pdftotext`` default reading order is compared with PyMuPDF block order.
* each page dictionary is probed for an optional embedded ``/Thumb`` image.

The output is evidence, not a gate. Missing tools, damaged objects, or failed
renders are explicit ``UNREAD`` states. This quarantine implementation never
changes a source PDF, held bundle, manifest, audit verdict, or conveyor state.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pymupdf


SCHEMA = "file-portal.ok15-evidence.v1"
CAPTURE_SCALE = 0.25  # 18 dpi: invokes the renderer without retaining a page image.
PDFTOTEXT_TIMEOUT_S = 180
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _warning_lines(*, reset: bool = True) -> list[str]:
    """Drain MuPDF's process-global warning buffer into stable, nonblank lines."""
    raw = pymupdf.TOOLS.mupdf_warnings(reset=1 if reset else 0) or ""
    return [line.strip() for line in str(raw).splitlines() if line.strip()]


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return _TOKEN_RE.findall(normalized)


def _text_from_blocks(page: Any) -> str:
    # sort=False is intentional: this is PyMuPDF's native block sequence, the
    # sequence the Xpdf default reading-order oracle is being compared against.
    return "\n".join(str(block[4]) for block in page.get_text("blocks", sort=False))


def _sequence_evidence(pymupdf_text: str, pdftotext_text: str) -> dict[str, Any]:
    left = _tokens(pymupdf_text)
    right = _tokens(pdftotext_text)
    left_counts = collections.Counter(left)
    right_counts = collections.Counter(right)
    exact = left == right
    same_multiset = left_counts == right_counts
    if exact:
        disposition = "exact"
    elif same_multiset:
        disposition = "order-only-difference"
    else:
        disposition = "content-and-or-order-difference"
    first_difference = next(
        (i for i, pair in enumerate(zip(left, right)) if pair[0] != pair[1]),
        min(len(left), len(right)) if len(left) != len(right) else None,
    )
    return {
        "status": "measured",
        "disposition": disposition,
        "sequences_equal": exact,
        "token_multisets_equal": same_multiset,
        "pymupdf_token_count": len(left),
        "pdftotext_token_count": len(right),
        "first_difference_token_0based": first_difference,
        "pymupdf_sequence_sha256": _sha256_bytes("\0".join(left).encode("utf-8")),
        "pdftotext_sequence_sha256": _sha256_bytes("\0".join(right).encode("utf-8")),
    }


def _pdftotext_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("FP_PDFTOTEXT")
    if configured:
        candidates.append(Path(configured))
    found = shutil.which("pdftotext")
    if found:
        candidates.append(Path(found))
    # The File Portal Windows host carries Xpdf here through Git for Windows.
    candidates.append(Path(r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _tool_version(executable: Path) -> str:
    proc = subprocess.run(
        [str(executable), "-v"], capture_output=True, timeout=10, check=False
    )
    raw = (proc.stdout or b"") + b"\n" + (proc.stderr or b"")
    lines = [line.strip() for line in raw.decode("utf-8", "replace").splitlines()
             if line.strip()]
    return lines[0][:200] if lines else f"exit {proc.returncode}; no version text"


def _run_pdftotext(pdf_path: Path, page_count: int) -> dict[str, Any]:
    executable = next((path for path in _pdftotext_candidates() if path.is_file()), None)
    if executable is None:
        return {
            "status": "UNREAD",
            "reason": "pdftotext executable not found",
            "pages": None,
            "tool": {"status": "UNREAD"},
        }
    try:
        tool = {
            "status": "measured",
            "name": executable.name,
            "path": str(executable),
            "sha256": _sha256_file(executable),
            "version": _tool_version(executable),
            "mode": "default reading order; -enc UTF-8 -eol unix",
        }
        proc = subprocess.run(
            [str(executable), "-enc", "UTF-8", "-eol", "unix", str(pdf_path), "-"],
            capture_output=True,
            timeout=PDFTOTEXT_TIMEOUT_S,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "status": "UNREAD",
                "reason": f"pdftotext exit {proc.returncode}: "
                          f"{proc.stderr.decode('utf-8', 'replace')[-300:]}",
                "pages": None,
                "tool": tool,
            }
        try:
            text = proc.stdout.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            return {
                "status": "UNREAD",
                "reason": f"pdftotext output is not UTF-8 at byte {exc.start}",
                "pages": None,
                "tool": tool,
            }
        pages = text.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        if len(pages) != page_count:
            return {
                "status": "UNREAD",
                "reason": f"pdftotext page boundary count {len(pages)} != PDF {page_count}",
                "pages": None,
                "tool": tool,
            }
        return {"status": "measured", "pages": pages, "tool": tool}
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "status": "UNREAD",
            "reason": f"pdftotext failed: {type(exc).__name__}: {exc}",
            "pages": None,
            "tool": {"status": "UNREAD", "path": str(executable)},
        }


def _thumb_evidence(doc: Any, page_index: int) -> dict[str, Any]:
    page_xref = doc.page_xref(page_index)
    key_type, value = doc.xref_get_key(page_xref, "Thumb")
    if key_type in ("null", "none") or not value or value == "null":
        return {"status": "absent"}
    if key_type != "xref":
        return {
            "status": "UNREAD",
            "reason": f"/Thumb has unsupported {key_type} value",
            "raw_value": str(value)[:120],
        }
    match = re.fullmatch(r"\s*(\d+)\s+\d+\s+R\s*", str(value))
    if not match:
        return {"status": "UNREAD", "reason": "could not parse /Thumb xref"}
    xref = int(match.group(1))
    if not doc.xref_is_image(xref):
        return {"status": "UNREAD", "xref": xref, "reason": "/Thumb target is not an image"}
    # Probe dictionary metadata only. /Thumb is optional and may maliciously point
    # at a full-resolution image; decoding it would turn a bounded probe into an
    # unbounded allocation. xref_object excludes the stream bytes.
    dictionary = doc.xref_object(xref, compressed=True)
    keys = {}
    for key in ("Width", "Height", "BitsPerComponent", "ColorSpace", "Filter"):
        key_type, key_value = doc.xref_get_key(xref, key)
        keys[key] = None if key_type in ("null", "none") else str(key_value)
    return {
        "status": "present",
        "xref": xref,
        "width": keys["Width"],
        "height": keys["Height"],
        "bits_per_component": keys["BitsPerComponent"],
        "colorspace": keys["ColorSpace"],
        "filter": keys["Filter"],
        "dictionary_sha256": _sha256_bytes(dictionary.encode("utf-8")),
        "image_bytes_decoded": False,
    }


def _ocg_inventory(doc: Any) -> dict[str, Any]:
    groups = []
    for xref, meta in sorted(doc.get_ocgs().items()):
        groups.append({
            "xref": int(xref),
            "name": str(meta.get("name") or ""),
            "initially_on": bool(meta.get("on")),
            "intent": list(meta.get("intent") or []),
            "usage": str(meta.get("usage") or ""),
        })
    return {
        "status": "measured",
        "group_count": len(groups),
        "groups": groups,
        "capture_policy": (
            "normal source view plus all-groups-OFF counterfactual on disposable evidence copy"
        ),
        "affects_source_or_marker_input": False,
        "semantic_use": "difference evidence only; no group is classified as decorative",
    }


def _open_capture_doc(pdf_path: Path, ocg: dict[str, Any], scratch: Path) -> tuple[Any | None, dict[str, Any]]:
    """Open the evidence render document, serializing OCG state only in scratch.

    PyMuPDF 1.28 changes the PDF layer dictionary in memory, but a live page render
    does not observe that new default until the document is serialized and reopened.
    The source is therefore opened a second time, changed, saved under the temporary
    directory, reopened, and later deleted with that directory.
    """
    if not ocg["groups"]:
        return None, {
            "status": "not-applicable",
            "mode": "no optional-content groups exist; no counterfactual document opened",
            "all_groups_off_verified": True,
            "groups_forced_off": 0,
        }
    derived = scratch / "ocg-off-evidence-copy.pdf"
    editor = None
    try:
        editor = pymupdf.open(str(pdf_path))
        xrefs = [item["xref"] for item in ocg["groups"]]
        editor.set_layer(-1, basestate="OFF", on=[], off=xrefs)
        editor.save(str(derived), garbage=0, deflate=False)
        editor.close()
        editor = None
        capture = pymupdf.open(str(derived))
        states = capture.get_ocgs()
        still_on = sorted(int(xref) for xref, meta in states.items() if meta.get("on"))
        if still_on:
            capture.close()
            return None, {
                "status": "UNREAD",
                "reason": f"OCG-off verification failed; still on: {still_on}",
                "all_groups_off_verified": False,
            }
        return capture, {
            "status": "measured",
            "mode": "serialized disposable copy",
            "all_groups_off_verified": True,
            "groups_forced_off": len(xrefs),
        }
    except Exception as exc:  # noqa: BLE001 - evidence records UNREAD
        if editor is not None:
            editor.close()
        return None, {
            "status": "UNREAD",
            "reason": f"OCG-off disposable copy failed: {type(exc).__name__}: {exc}",
            "all_groups_off_verified": False,
        }


def collect(
    pdf_path: Path,
    source_sha256: str,
    *,
    pdftotext_probe: Callable[[Path, int], dict[str, Any]] | None = None,
    warning_reader: Callable[[], list[str]] | None = None,
) -> dict[str, Any]:
    """Collect an OK-15 evidence record without retaining page pixels or source text."""
    pdf_path = Path(pdf_path)
    identity_before = _sha256_file(pdf_path)
    if source_sha256.lower() != identity_before:
        raise RuntimeError(
            f"source identity mismatch before evidence: expected {source_sha256[:16]}, "
            f"read {identity_before[:16]}"
        )
    drain_warnings = warning_reader or _warning_lines
    drain_warnings()
    source_doc = pymupdf.open(str(pdf_path))
    open_warnings = drain_warnings()
    page_count = source_doc.page_count
    try:
        ocg = _ocg_inventory(source_doc)
    except Exception as exc:  # noqa: BLE001 - preserve the other four probes
        ocg = {
            "status": "UNREAD",
            "group_count": None,
            "groups": [],
            "capture_policy": "UNREAD",
            "affects_source_or_marker_input": False,
            "semantic_use": "none; OCG inventory failed",
            "reason": f"OCG inventory failed: {type(exc).__name__}: {exc}"[:300],
        }
    oracle = (pdftotext_probe or _run_pdftotext)(pdf_path, page_count)
    if (oracle.get("status") == "measured"
            and (not isinstance(oracle.get("pages"), list)
                 or len(oracle["pages"]) != page_count)):
        oracle = {
            "status": "UNREAD",
            "reason": "pdftotext probe returned a measured result with wrong page cardinality",
            "pages": None,
            "tool": oracle.get("tool", {"status": "UNREAD"}),
        }
    pages: list[dict[str, Any]] = []
    labels: dict[str, list[int]] = {}
    label_unread = 0

    try:
        with tempfile.TemporaryDirectory(prefix="fp-ok15-") as temp_name:
            if ocg["status"] == "measured":
                capture_doc, capture_setup = _open_capture_doc(pdf_path, ocg, Path(temp_name))
            else:
                capture_doc, capture_setup = None, {
                    "status": "UNREAD", "reason": ocg.get("reason", "OCG inventory unavailable")
                }
            capture_open_warnings = drain_warnings()
            try:
                for page_index in range(page_count):
                    page_number = page_index + 1
                    drain_warnings()
                    record: dict[str, Any] = {"page": page_number}
                    pymupdf_text: str | None = None
                    source_pixmap = None
                    page = None
                    try:
                        page = source_doc.load_page(page_index)
                    except Exception as exc:  # noqa: BLE001
                        reason = f"page load failed: {type(exc).__name__}: {exc}"[:200]
                        label_unread += 1
                        record["page_label"] = {"status": "UNREAD", "reason": reason}
                        record["embedded_thumb"] = {"status": "UNREAD", "reason": reason}

                    if page is not None:
                        try:
                            raw_label = page.get_label()
                            label = raw_label or str(page_number)
                            record["page_label"] = {
                                "status": "measured",
                                "label": label,
                                "source": "pdf-page-label" if raw_label else "ordinal-fallback",
                            }
                            labels.setdefault(label, []).append(page_number)
                        except Exception as exc:  # noqa: BLE001
                            label_unread += 1
                            record["page_label"] = {"status": "UNREAD", "reason": str(exc)[:200]}
                        try:
                            record["embedded_thumb"] = _thumb_evidence(source_doc, page_index)
                        except Exception as exc:  # noqa: BLE001
                            record["embedded_thumb"] = {
                                "status": "UNREAD",
                                "reason": f"/Thumb probe failed: {type(exc).__name__}: {exc}"[:200],
                            }
                        try:
                            pymupdf_text = _text_from_blocks(page)
                        except Exception:
                            pymupdf_text = None
                        try:
                            source_pixmap = page.get_pixmap(
                                matrix=pymupdf.Matrix(CAPTURE_SCALE, CAPTURE_SCALE),
                                alpha=False,
                            )
                        except Exception:
                            source_pixmap = None

                    # This drain covers every MuPDF operation on the source page above:
                    # label lookup, /Thumb dictionary inspection, block text, and render.
                    # Keep the name broad so the report does not over-attribute a warning
                    # to the renderer when MuPDF may have emitted it from another probe.
                    source_page_warnings = drain_warnings()

                    if oracle.get("status") == "measured" and pymupdf_text is not None:
                        record["reading_order"] = _sequence_evidence(
                            pymupdf_text, oracle["pages"][page_index]
                        )
                    else:
                        reason = (oracle.get("reason") if oracle.get("status") != "measured"
                                  else "PyMuPDF block-order text unavailable")
                        record["reading_order"] = {
                            "status": "UNREAD",
                            "reason": str(reason or "reading-order oracle unavailable")[:300],
                        }

                    if source_pixmap is None:
                        record["capture_raster"] = {
                            "status": "UNREAD",
                            "reason": "source-view diagnostic render unavailable",
                        }
                    else:
                        source_capture = {
                            "width_px": source_pixmap.width,
                            "height_px": source_pixmap.height,
                            "rgb_sha256": _sha256_bytes(source_pixmap.samples),
                        }
                        record["capture_raster"] = {
                            "status": "measured",
                            "scale": CAPTURE_SCALE,
                            "equivalent_dpi": int(round(72 * CAPTURE_SCALE)),
                            "source_view": source_capture,
                            "pixels_retained": False,
                        }

                    ocg_warnings: list[str] = []
                    if ocg["status"] != "measured":
                        record["capture_raster"]["ocg_off_variant"] = {
                            "status": "UNREAD", "reason": ocg.get("reason", "OCG inventory unavailable")
                        }
                    elif not ocg["groups"]:
                        record["capture_raster"]["ocg_off_variant"] = {"status": "not-applicable"}
                    elif capture_doc is None:
                        record["capture_raster"]["ocg_off_variant"] = {
                            "status": "UNREAD",
                            "reason": capture_setup.get("reason", "capture document unavailable"),
                        }
                    else:
                        drain_warnings()
                        try:
                            capture_page = capture_doc.load_page(page_index)
                            pixmap = capture_page.get_pixmap(
                                matrix=pymupdf.Matrix(CAPTURE_SCALE, CAPTURE_SCALE),
                                alpha=False,
                            )
                            off_capture = {
                                "status": "measured",
                                "width_px": pixmap.width,
                                "height_px": pixmap.height,
                                "rgb_sha256": _sha256_bytes(pixmap.samples),
                                "groups_forced_off": ocg["group_count"],
                            }
                            if source_pixmap is not None:
                                off_capture["differs_from_source_view"] = (
                                    off_capture["rgb_sha256"] != source_capture["rgb_sha256"]
                                )
                            record["capture_raster"]["ocg_off_variant"] = off_capture
                        except Exception as exc:  # noqa: BLE001
                            record["capture_raster"]["ocg_off_variant"] = {
                                "status": "UNREAD",
                                "reason": (
                                    f"diagnostic render failed: {type(exc).__name__}: {exc}"
                                )[:300],
                            }
                        ocg_warnings = drain_warnings()
                    record["mupdf_warnings"] = {
                        "source_page_probes": source_page_warnings,
                        "ocg_off_variant": ocg_warnings,
                    }
                    pages.append(record)
            finally:
                if capture_doc is not None:
                    capture_doc.close()
    finally:
        source_doc.close()

    warning_pages = [item["page"] for item in pages
                     if item["mupdf_warnings"]["source_page_probes"]
                     or item["mupdf_warnings"]["ocg_off_variant"]]
    warning_count = sum(len(item["mupdf_warnings"]["source_page_probes"])
                        + len(item["mupdf_warnings"]["ocg_off_variant"])
                        for item in pages)
    thumb_pages = [item["page"] for item in pages
                   if item["embedded_thumb"]["status"] == "present"]
    non_ordinal = [item["page"] for item in pages
                   if item["page_label"].get("status") == "measured"
                   and item["page_label"].get("label") != str(item["page"])]
    reading = [item["reading_order"] for item in pages]
    measured_reading = [item for item in reading if item["status"] == "measured"]
    order_only = sum(item["disposition"] == "order-only-difference" for item in measured_reading)
    content_diff = sum(item["disposition"] == "content-and-or-order-difference"
                       for item in measured_reading)
    unread_render = sum(item["capture_raster"]["status"] == "UNREAD" for item in pages)
    ocg_difference_pages = sum(
        item["capture_raster"].get("ocg_off_variant", {}).get("differs_from_source_view") is True
        for item in pages
    )
    overall = "measured"
    page_probe_unread = any(
        item["page_label"].get("status") == "UNREAD"
        or item["embedded_thumb"].get("status") == "UNREAD"
        or item["reading_order"].get("status") == "UNREAD"
        or item["capture_raster"].get("status") == "UNREAD"
        or item["capture_raster"].get("ocg_off_variant", {}).get("status") == "UNREAD"
        for item in pages
    )
    if not pages:
        overall = "UNREAD"
    elif page_probe_unread or ocg["status"] == "UNREAD":
        overall = "partial"

    identity_after = _sha256_file(pdf_path)
    if identity_after != identity_before:
        raise RuntimeError(
            f"source changed during evidence collection: {identity_before[:16]} -> "
            f"{identity_after[:16]}"
        )

    return {
        "schema": SCHEMA,
        "status": overall,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"name": pdf_path.name, "sha256": source_sha256, "pages": page_count},
        "producer": {
            "pymupdf_version": getattr(pymupdf, "__version__", "unknown"),
            "mupdf_version": getattr(pymupdf, "mupdf_version", "unknown"),
            "pdftotext": oracle.get("tool", {"status": "UNREAD"}),
        },
        "document": {
            "open_warnings": open_warnings,
            "capture_open_warnings": capture_open_warnings,
            "reading_order_oracle": {
                "status": oracle.get("status", "UNREAD"),
                **({"reason": str(oracle.get("reason"))[:300]}
                   if oracle.get("reason") else {}),
            },
            "ocg": {**ocg, "capture_setup": capture_setup},
            "page_labels": {
                "status": "measured" if not label_unread else "partial",
                "label_to_pages_1based": labels,
                "unread_pages": label_unread,
            },
        },
        "summary": {
            "pages_total": page_count,
            "mupdf_warning_pages": len(warning_pages),
            "mupdf_warning_count": warning_count,
            "non_ordinal_label_pages": len(non_ordinal),
            "ocg_groups_forced_off_for_capture": ocg["group_count"]
                if capture_setup.get("status") == "measured" else None,
            "ocg_variant_difference_pages": ocg_difference_pages,
            "capture_pages_measured": page_count - unread_render,
            "reading_order_pages_compared": len(measured_reading),
            "reading_order_exact_pages": sum(item["disposition"] == "exact"
                                               for item in measured_reading),
            "reading_order_order_only_difference_pages": order_only,
            "reading_order_content_or_order_difference_pages": content_diff,
            "embedded_thumb_pages": len(thumb_pages),
        },
        "pages": pages,
    }


def compact(report: dict[str, Any]) -> dict[str, Any]:
    """Return the read-only projection suitable for the Bench operator surface."""
    return {
        "schema": report["schema"],
        "status": report["status"],
        "source_sha256": report["source"]["sha256"],
        "summary": report["summary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="read-only OK-15 Repair Bench evidence")
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    report = collect(args.pdf, args.source_sha256)
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
