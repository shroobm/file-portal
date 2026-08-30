"""Independent, CPU-only VW-E2-R2 fixed-sample verifier.

The producer gives this program one canonical JSON request over an anonymous child
stdin pipe.  It rereads the exact public contracts, the VW-T03 source bytes, and page
210, then independently recomputes the frozen tile and identity probes.  Its only
output is one authenticated canonical JSON wrapper over stdout; it writes no file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import pymupdf


PACKET_RELATIVE = Path("docs/contracts/visual-witness-e2-packet-r2.json")
SCHEMA_RELATIVE = Path("docs/contracts/visual-witness-e2-capture-v1.schema.json")
PACKET_SHA256 = "ebc047b8d963a8e3b92ebd7479055dbf78121fad93094f38c902ce9f92cc6769"
PACKET_BYTES = 110341
SCHEMA_SHA256 = "569335ddfec3fa44588a277a17982838b6921df411e63116e1df5784233c63b7"
SCHEMA_BYTES = 79747
CONFIG_SHA256 = "8f11fc2000a8ffed65518853825ac3f8c954a44e30fd2960b9d6ba836c39e639"
VERIFIER = "codex-independent-verifier-v1"
PROBE_ID = "vw-e2-r2-independent-sample-v1"
DOMAINS = {
    "config": b"file-portal/vw-e2-config/r2\0",
    "capture": b"file-portal/vw-e2-capture-core/r2\0",
    "checks": b"file-portal/vw-e2-semantic-checks/r2\0",
    "primitive": b"file-portal/vw-e2-primitive/r2\0",
    "candidate": b"file-portal/vw-e2-candidate/r2\0",
    "relationship": b"file-portal/vw-e2-relationship/r2\0",
    "evidence": b"file-portal/vw-e2-independent-verifier/r2\0",
}
PLANTED_GAP_RECTANGLES = [
    [0, 0, 3, 1],
    [0, 2, 3, 3],
    [0, 1, 1, 2],
    [2, 1, 3, 2],
]
PLANTED_GAP_EXPECTED_AREA = 8
PLANTED_GAP_VALID_PIXELS = 9
CASE_ORDER = ("VW-T01", "VW-T02", "VW-T03")
CLASS_ORDER = ("raster", "vector", "stroke-cluster", "scan-component", "text-block", "table")
RULE_IDS = {
    "raster": "VW2-R2-RASTER-1",
    "vector": "VW2-R2-VECTOR-1",
    "stroke-cluster": "VW2-R2-STROKE-1",
    "scan-component": "VW2-R2-SCAN-1",
    "text-block": "VW2-R2-TEXT-1",
    "table": "VW2-R2-TABLE-1",
}
_ACTIVITY = {"instrumentation_ready": False, "network_call_count": 0, "gpu_call_count": 0}
_AUDIT_INSTALLED = False
_AUDIT_ACTIVE = False
_GPU_AUDIT_TOKENS = (
    "cuda", "nvcuda", "cudnn", "nvml", "nvidia-smi", "rocm", "hip", "opencl", "pycuda", "cupy",
)


def _activity_audit(event: str, args: tuple[Any, ...]) -> None:
    if not _AUDIT_ACTIVE:
        return
    if event.startswith("socket."):
        _ACTIVITY["network_call_count"] += 1
        raise PermissionError("VW verifier network operation denied")
    lowered = " ".join(str(value).casefold() for value in args)
    if event in ("ctypes.dlopen", "subprocess.Popen", "os.system") and any(
        token in lowered for token in _GPU_AUDIT_TOKENS
    ):
        _ACTIVITY["gpu_call_count"] += 1
        raise PermissionError("VW verifier GPU operation denied")


def install_activity_audit() -> None:
    global _AUDIT_INSTALLED, _AUDIT_ACTIVE
    if not hasattr(sys, "addaudithook"):
        raise VerifyUnread("Python audit instrumentation unavailable")
    if not _AUDIT_INSTALLED:
        sys.addaudithook(_activity_audit)
        _AUDIT_INSTALLED = True
    _AUDIT_ACTIVE = True
    _ACTIVITY["instrumentation_ready"] = True


def activity_snapshot() -> dict[str, Any]:
    return dict(_ACTIVITY)


class VerifyUnread(RuntimeError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerifyUnread("duplicate JSON member")
        result[key] = value
    return result


def load_json_bytes(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(VerifyUnread(value)),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerifyUnread("JSON input unread") from exc


def load_json(path: Path) -> Any:
    try:
        return load_json_bytes(path.read_bytes())
    except OSError as exc:
        raise VerifyUnread("JSON input unread") from exc


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _projection_hash(domain: str, value: Any, *, tagged: bool = False) -> str:
    value_hash = digest(DOMAINS[domain] + canonical(value))
    return "sha256:" + value_hash if tagged else value_hash


def _file_identity(path: Path, byte_count: int, expected: str) -> bool:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise VerifyUnread("bound public bytes unread") from exc
    return len(raw) == byte_count and digest(raw) == expected


def exact_union_area(rectangles: Sequence[Sequence[int]]) -> int:
    parsed: list[tuple[int, int, int, int]] = []
    for rectangle in rectangles:
        if (
            not isinstance(rectangle, list)
            or len(rectangle) != 4
            or any(isinstance(value, bool) or not isinstance(value, int) for value in rectangle)
        ):
            raise VerifyUnread("tile rectangle shape unread")
        x0, y0, x1, y1 = rectangle
        if x0 < 0 or y0 < 0 or x0 >= x1 or y0 >= y1:
            raise VerifyUnread("tile rectangle bounds unread")
        parsed.append((x0, y0, x1, y1))
    xs = sorted({edge for rectangle in parsed for edge in (rectangle[0], rectangle[2])})
    area = 0
    for x0, x1 in zip(xs, xs[1:]):
        intervals = sorted((y0, y1) for left, y0, right, y1 in parsed if left < x1 and right > x0)
        if not intervals:
            continue
        lo, hi = intervals[0]
        covered = 0
        for next_lo, next_hi in intervals[1:]:
            if next_lo <= hi:
                hi = max(hi, next_hi)
            else:
                covered += hi - lo
                lo, hi = next_lo, next_hi
        covered += hi - lo
        area += (x1 - x0) * covered
    return area


def _rgb_slice(raw: bytes, width: int, bbox: Sequence[int]) -> bytes:
    if len(raw) % (width * 3):
        raise VerifyUnread("render RGB shape unread")
    height = len(raw) // (width * 3)
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise VerifyUnread("tile slice unread")
    stride = width * 3
    return b"".join(raw[y * stride + x0 * 3 : y * stride + x1 * 3] for y in range(y0, y1))


def _verify_page_210(source_path: Path, source: Mapping[str, Any], retained: Mapping[str, Any]) -> bool:
    try:
        raw_source = source_path.read_bytes()
    except OSError as exc:
        raise VerifyUnread("VW-T03 source unread") from exc
    if digest(raw_source) != source.get("observed_sha256"):
        return False
    try:
        document = pymupdf.open(stream=raw_source, filetype="pdf")
        if document.page_count < 210:
            return False
        page = document[209]
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(8 / 3, 8 / 3),
            colorspace=pymupdf.csRGB,
            alpha=False,
            annots=True,
            clip=page.rect,
        )
        render = bytes(pixmap.samples)
        width, height = int(pixmap.width), int(pixmap.height)
        if int(pixmap.x) != 0 or int(pixmap.y) != 0 or int(pixmap.n) != 3 or bool(pixmap.alpha):
            return False
        if retained.get("render") != {
            "status": "measured",
            "width_px": width,
            "height_px": height,
            "valid_page_pixels": width * height,
            "rgb_bytes": len(render),
            "rgb_sha256": digest(render),
            "encoding": "RGB8-row-major-no-padding",
            "reason_codes": [],
        }:
            return False
        tiles = retained.get("tiles")
        if not isinstance(tiles, list) or exact_union_area([tile["bbox_px_half_open"] for tile in tiles]) != width * height:
            return False
        for tile in tiles:
            tile_raw = _rgb_slice(render, width, tile["bbox_px_half_open"])
            if tile.get("rgb_bytes") != len(tile_raw) or tile.get("rgb_sha256") != digest(tile_raw):
                return False
        return True
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        raise VerifyUnread("VW-T03 page 210 API unread") from exc


def _canonical_object_unique(items: Sequence[Any]) -> bool:
    return len({canonical(item) for item in items}) == len(items)


def _sorted_unique_strings(items: Any) -> bool:
    return isinstance(items, list) and all(isinstance(item, str) for item in items) and items == sorted(set(items))


def _disposition_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    reason, evidence = item.get("reason_code"), item.get("evidence_sha256")
    return (
        item.get("scope"), (0, "") if reason is None else (1, reason), item.get("blocking"),
        item.get("detail_code"), (0, "") if evidence is None else (1, evidence),
    )


def _recursive_payload_order(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "reason_codes" and not _sorted_unique_strings(child):
                return False
            if key in ("conflicts", "unreads") and (
                not isinstance(child, list) or child != sorted(child, key=_disposition_key)
            ):
                return False
            if not _recursive_payload_order(child):
                return False
    elif isinstance(value, list):
        return all(_recursive_payload_order(child) for child in value)
    return True


def _candidate_deep_order(candidate: Mapping[str, Any], tile_by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    recovery = candidate["edge_recovery"]
    relation_rank = {"equals-min-boundary": 0, "equals-max-boundary": 1, "straddles": 2}
    direction_rank = {"negative": 0, "positive": 1, "both": 2}
    touches = recovery["touched_internal_edges"]
    touch_key = lambda item: (
        0 if item["axis"] == "x" else 1, item["coordinate_px"],
        relation_rank[item["relation"]], direction_rank[item["neighbor_direction"]],
    )
    if touches != sorted(touches, key=touch_key) or not _canonical_object_unique(touches):
        return False
    recovery_ids = recovery["recovery_tile_ids"]
    if any(tile_id not in tile_by_id for tile_id in recovery_ids):
        return False
    if recovery_ids != sorted(
        set(recovery_ids),
        key=lambda tile_id: (
            tile_by_id[tile_id]["bbox_px_half_open"][1],
            tile_by_id[tile_id]["bbox_px_half_open"][0], tile_id,
        ),
    ):
        return False
    if not _sorted_unique_strings(candidate["captured_text"]["source_text_primitive_ids"]):
        return False
    for evidence in candidate["class_evidence"]:
        if not _sorted_unique_strings(evidence["source_primitive_ids"]):
            return False
        if evidence["rule_id"] != RULE_IDS["table"]:
            continue
        measurements = evidence["measurements"]
        if not _sorted_unique_strings(measurements["eligible_segment_ids"]):
            return False
        for axis_name in ("horizontal_tracks", "vertical_tracks"):
            tracks = measurements[axis_name]
            for track in tracks:
                if not _sorted_unique_strings(track["member_primitive_ids"]):
                    return False
            key = lambda track: (
                track["axis_px"], track["extent_start_px"], track["extent_end_px"],
                tuple(track["member_primitive_ids"]),
            )
            if tracks != sorted(tracks, key=key) or not _canonical_object_unique(tracks):
                return False
        cells = measurements["closed_cells"]
        if any(not _sorted_unique_strings(cell["text_primitive_ids"]) for cell in cells):
            return False
        if cells != sorted(cells, key=lambda cell: (cell["row_index_0based"], cell["column_index_0based"], cell["cell_id"])):
            return False
        if not _canonical_object_unique(cells) or not _sorted_unique_strings(measurements["occupied_cell_ids"]):
            return False
    return True


def _canonical_payload_order(payload: Mapping[str, Any]) -> bool:
    """Independently enforce the packet order that precedes sample selection."""
    try:
        cases = payload["cases"]
        if payload["case_census"]["case_ids"] != list(CASE_ORDER):
            return False
        if not isinstance(cases, list) or [case["case_id"] for case in cases] != list(CASE_ORDER):
            return False
        primitive_rank = {"raster": 0, "vector": 1, "text": 2}
        provenance_names = (
            "engine_list_index_0based", "drawing_list_index_0based", "drawing_seqno_observed",
            "item_list_index_0based", "emitted_edge_index_0based", "engine_number_observed",
        )
        for case in cases:
            markdown = case["bundle"]["markdown"]
            if (
                not markdown or markdown[0].get("phase") != "raw-marker"
                or markdown[0].get("variant_ordinal") != 0
                or [item.get("phase") for item in markdown[1:]] != ["analyst"] * (len(markdown) - 1)
                or [item.get("variant_ordinal") for item in markdown[1:]] != list(range(len(markdown) - 1))
            ):
                return False
            assets = case["bundle"]["asset_filename_page_ids_0based"]
            if [item["asset_ordinal"] for item in assets] != list(range(len(assets))) or not _canonical_object_unique(assets):
                return False
            pages = case["pages"]
            if not isinstance(pages, list) or [page["page_1based"] for page in pages] != list(range(1, len(pages) + 1)):
                return False
            if [item["class"] for item in case["class_census"]] != list(CLASS_ORDER):
                return False
            for page in pages:
                tiles = page["tiles"]
                if tiles != sorted(
                    tiles,
                    key=lambda item: (
                        item["bbox_px_half_open"][1], item["bbox_px_half_open"][0], item["tile_id"],
                    ),
                ) or not _canonical_object_unique(tiles):
                    return False
                tile_by_id = {item["tile_id"]: item for item in tiles}
                if len(tile_by_id) != len(tiles):
                    return False
                primitives = page["primitive_facts"]
                if primitives != sorted(
                    primitives,
                    key=lambda item: (
                        primitive_rank[item["kind"]], *item["bbox_px_half_open"], item["primitive_id"],
                    ),
                ) or not _canonical_object_unique(primitives):
                    return False
                candidates = page["region_candidates"]
                if candidates != sorted(candidates, key=lambda item: item["candidate_id"]) or not _canonical_object_unique(candidates):
                    return False
                relationships = page["relationships"]
                if relationships != sorted(
                    relationships,
                    key=lambda item: (
                        item["source_candidate_id"], item["target_candidate_id"], item["kind"],
                    ),
                ) or not _canonical_object_unique(relationships):
                    return False
                if [item["class"] for item in page["class_procedures"]] != list(CLASS_ORDER):
                    return False
                for primitive in primitives:
                    provenance = primitive["source_evidence"]["provenance_records"]
                    provenance_key = lambda item: tuple(
                        -1 if item[name] is None else item[name] for name in provenance_names
                    )
                    if provenance != sorted(provenance, key=provenance_key):
                        return False
                    if len({canonical(item) for item in provenance}) != len(provenance):
                        return False
                for candidate in candidates:
                    classes = candidate["classes"]
                    if classes != [name for name in CLASS_ORDER if name in set(classes)]:
                        return False
                    expected_rules = [RULE_IDS[name] for name in classes]
                    if candidate["class_basis"] != expected_rules:
                        return False
                    if [item["rule_id"] for item in candidate["class_evidence"]] != expected_rules:
                        return False
                    if not _canonical_object_unique(candidate["class_evidence"]):
                        return False
                    for key in ("source_primitive_ids", "intersecting_tile_ids"):
                        if candidate[key] != sorted(set(candidate[key])):
                            return False
                    if not _candidate_deep_order(candidate, tile_by_id):
                        return False
        return _recursive_payload_order(payload)
    except (KeyError, TypeError, ValueError):
        raise VerifyUnread("canonical payload order unread")


def _identity_chain(payload: Mapping[str, Any]) -> bool:
    first: tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]] | None = None
    for case in payload.get("cases", []):
        source_sha = case.get("source", {}).get("observed_sha256")
        for page in case.get("pages", []):
            candidates = {item.get("candidate_id"): item for item in page.get("region_candidates", [])}
            primitives = {item.get("primitive_id"): item for item in page.get("primitive_facts", [])}
            relationships = page.get("relationships", [])
            if relationships:
                relation = relationships[0]
                candidate = candidates.get(relation.get("source_candidate_id"))
                if candidate is None or not candidate.get("source_primitive_ids"):
                    raise VerifyUnread("first relationship identity chain unread")
                primitive = primitives.get(sorted(candidate["source_primitive_ids"])[0])
                if primitive is None:
                    raise VerifyUnread("first relationship primitive unread")
                first = (relation, candidate, primitive, {"source_sha": source_sha, "page": page})
                break
        if first is not None:
            break
    if first is None:
        raise VerifyUnread("no first relationship; substitution forbidden")
    relation, candidate, primitive, context = first
    source_sha, page = context["source_sha"], context["page"]
    primitive_projection = {
        "source_sha256": source_sha,
        "page_1based": page["page_1based"],
        "kind": primitive["kind"],
        "method": primitive["method"],
        "bbox_pdf_pt": primitive["bbox_pdf_pt"],
        "bbox_px_half_open": primitive["bbox_px_half_open"],
        "identity_attributes": primitive["identity_attributes"],
    }
    candidate_projection = {
        "source_sha256": source_sha,
        "page_1based": page["page_1based"],
        "bbox_pdf_pt": candidate["bbox_pdf_pt"],
        "bbox_px_half_open": candidate["bbox_px_half_open"],
        "classes": candidate["classes"],
        "config_sha256": payload["config_sha256"],
        "source_primitive_ids": candidate["source_primitive_ids"],
    }
    relationship_projection = {
        "source_candidate_id": relation["source_candidate_id"],
        "target_candidate_id": relation["target_candidate_id"],
        "kind": relation["kind"],
    }
    return (
        primitive["primitive_id"] == _projection_hash("primitive", primitive_projection, tagged=True)
        and candidate["candidate_id"] == _projection_hash("candidate", candidate_projection, tagged=True)
        and relation["relationship_id"] == _projection_hash("relationship", relationship_projection, tagged=True)
    )


def verify_request(request: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    conflicts: set[str] = set()
    unread = False
    payload = request.get("capture_payload")
    checks = request.get("ordinary_semantic_checks")
    if not isinstance(payload, dict) or not isinstance(checks, list):
        raise VerifyUnread("verifier request shape unread")
    verifier_code_sha = digest(Path(__file__).read_bytes())
    try:
        if not _file_identity(repo_root / PACKET_RELATIVE, PACKET_BYTES, PACKET_SHA256):
            conflicts.add("GROUND-DRIFT")
        if not _file_identity(repo_root / SCHEMA_RELATIVE, SCHEMA_BYTES, SCHEMA_SHA256):
            conflicts.add("GROUND-DRIFT")
        if request.get("verifier_code_sha256") != verifier_code_sha:
            conflicts.add("GROUND-DRIFT")
        packet = load_json(repo_root / PACKET_RELATIVE)
        configuration = packet.get("frozen_configuration") if isinstance(packet, dict) else None
        if not isinstance(configuration, dict) or _projection_hash("config", configuration) != CONFIG_SHA256:
            conflicts.add("GROUND-DRIFT")
        if payload.get("config_sha256") != CONFIG_SHA256:
            conflicts.add("VW-CONFIG-HASH")
        payload_projection = dict(payload)
        payload_projection.pop("capture_payload_sha256", None)
        if payload.get("capture_payload_sha256") != _projection_hash("capture", payload_projection):
            conflicts.add("VW-IDENTITY")
        checks_sha = _projection_hash("checks", checks)
        if request.get("semantic_checks_sha256") != checks_sha:
            conflicts.add("VW-IDENTITY")
        cases = {case.get("case_id"): case for case in payload.get("cases", [])}
        t03 = cases.get("VW-T03")
        if not isinstance(t03, dict) or len(t03.get("pages", [])) < 210:
            raise VerifyUnread("VW-T03 page 210 absent")
        canonical_order = _canonical_payload_order(payload)
        if not canonical_order:
            conflicts.add("VW-NEGATIVE-CONTROL")
        source_path = request.get("vw_t03_source_path")
        if not isinstance(source_path, str) or not Path(source_path).is_absolute():
            raise VerifyUnread("VW-T03 path unread")
        retained_page_210 = t03["pages"][209]
        if retained_page_210.get("page_1based") != 210:
            conflicts.add("VW-NEGATIVE-CONTROL")
        if not _verify_page_210(Path(source_path), t03["source"], retained_page_210):
            conflicts.add("VW-NEGATIVE-CONTROL")
        if canonical_order and not _identity_chain(payload):
            conflicts.add("VW-NEGATIVE-CONTROL")
        planted_area = exact_union_area(PLANTED_GAP_RECTANGLES)
        if planted_area != PLANTED_GAP_EXPECTED_AREA or planted_area == PLANTED_GAP_VALID_PIXELS:
            conflicts.add("VW-NEGATIVE-CONTROL")
    except VerifyUnread:
        unread = True

    if conflicts:
        status, reasons = "CONFLICT", sorted(conflicts)
    elif unread:
        status, reasons = "UNREAD", ["UNREAD"]
    else:
        status, reasons = "Verified-independent", []
    result = {
        "verifier": VERIFIER,
        "status": status,
        "probe_id": PROBE_ID,
        "verifier_code_sha256": verifier_code_sha,
        "packet_sha256": PACKET_SHA256,
        "capture_schema_sha256": SCHEMA_SHA256,
        "capture_payload_sha256": payload.get("capture_payload_sha256"),
        "semantic_checks_sha256": request.get("semantic_checks_sha256"),
        "evidence_sha256": None,
        "reason_codes": reasons,
    }
    if status != "UNREAD":
        projection = dict(result)
        projection.pop("evidence_sha256")
        result["evidence_sha256"] = _projection_hash("evidence", projection)
    return result


def _create_new(path: Path, value: Any) -> None:
    raw = canonical(value) + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
    except OSError as exc:
        raise VerifyUnread("verifier output create failed") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VW-E2-R2 fixed independent verifier")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--stdio", action="store_true", required=True)
    args = parser.parse_args(argv)
    result: Mapping[str, Any] | None = None
    exit_code = 3
    try:
        install_activity_audit()
        raw = sys.stdin.buffer.read(268_435_457)
        if len(raw) > 268_435_456 or not raw.endswith(b"\n"):
            raise VerifyUnread("verifier stdin request unread")
        request = load_json_bytes(raw[:-1])
        if canonical(request) + b"\n" != raw:
            raise VerifyUnread("verifier stdin request is not canonical")
        result = verify_request(request, args.repo_root.resolve(strict=True))
        exit_code = 0 if result["status"] == "Verified-independent" else 2
    except BaseException:
        exit_code = 3
    wrapper = {"activity": activity_snapshot(), "result": result}
    sys.stdout.buffer.write(canonical(wrapper) + b"\n")
    sys.stdout.buffer.flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
