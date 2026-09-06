"""VW-E2-R2 calibration-only structural source-region capture.

This module is deliberately report-only.  It records observed PDF primitives and
deterministically inferred structural candidates; it never asserts semantic truth.  Its
COMPLETE receipt is emitted only after the independent verifier and every frozen check
pass.  The command-line entry point is guarded by the
hash-bound ``docs/contracts/visual-witness-e2-packet-r2.json`` packet.

No model, network, GPU, converter, analyst, bundle mutation, or publication path is used.
Raw page pixels and extracted text live only in an event-scoped scratch lifetime and are
removed before the operational report is created once beneath an explicit external root.
"""

from __future__ import annotations

import bisect
import copy
import ctypes
import datetime as dt
import fnmatch
import hashlib
import importlib
import json
import math
import multiprocessing as mp
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from ctypes import wintypes
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

import pymupdf

sys.dont_write_bytecode = True


PACKET_RELATIVE_PATH = Path("docs/contracts/visual-witness-e2-packet-r2.json")
PACKET_SHA256 = "ebc047b8d963a8e3b92ebd7479055dbf78121fad93094f38c902ce9f92cc6769"
PACKET_BYTES = 110341
CAPTURE_SCHEMA_RELATIVE_PATH = Path("docs/contracts/visual-witness-e2-capture-v1.schema.json")
CAPTURE_SCHEMA_SHA256 = "569335ddfec3fa44588a277a17982838b6921df411e63116e1df5784233c63b7"
CAPTURE_SCHEMA_BYTES = 79747
REPOSITORY_SHA = "24bf5bb16631c1f0c3235b647a4f2c8cc5a8f3b7"
GIT_EXECUTABLE = Path(r"C:\Program Files\Git\mingw64\bin\git.exe")
GIT_EXECUTABLE_BYTES = 4_383_048
GIT_EXECUTABLE_SHA256 = "1a0043555d254618f2d56c936c3d9a1fbfb878bc878416a133c346bc7835eda9"
PARENT_CONTRACT_SHA256 = "3c2144d33079f7868e0bd3a8c1e4328a4797a1ac9fdb7b2d34ab32412a5fcfd1"
R1_SHA256 = "0bcabaf843ea54416f4111af8e1e3dbb88ef33d053e0829fcecc9162593832f0"
PRIVATE_MANIFEST_SHA256 = "e7299b50dd0d8ae5498ca13eb18c9a37c6bce5c38d24dd73351609e0c91a5c46"
EXPECTED_CONFIG_SHA256 = "8f11fc2000a8ffed65518853825ac3f8c954a44e30fd2960b9d6ba836c39e639"

# Native Git is a hash-bound local probe, not a member of the Python audit-hook domain.
# These controls deny helper, credential, protocol, hook, fsmonitor, submodule, pager, and
# external-diff escape by construction.  Only the explicitly matched read-only shapes below
# may reach Popen.
GIT_FIXED_ENVIRONMENT: tuple[tuple[str, str], ...] = (
    ("GCM_INTERACTIVE", "Never"),
    ("GIT_ALLOW_PROTOCOL", "file"),
    ("GIT_ASKPASS", ""),
    ("GIT_ATTR_SOURCE", "0000000000000000000000000000000000000000"),
    ("GIT_ATTR_NOSYSTEM", "1"),
    ("GIT_CONFIG", "NUL"),
    ("GIT_CONFIG_GLOBAL", "NUL"),
    ("GIT_CONFIG_NOSYSTEM", "1"),
    ("GIT_CONFIG_SYSTEM", "NUL"),
    ("GIT_EDITOR", ""),
    ("GIT_EXEC_PATH", "NUL"),
    ("GIT_LFS_SKIP_SMUDGE", "1"),
    ("GIT_NO_LAZY_FETCH", "1"),
    ("GIT_NO_REPLACE_OBJECTS", "1"),
    ("GIT_OPTIONAL_LOCKS", "0"),
    ("GIT_PAGER", ""),
    ("GIT_PROTOCOL_FROM_USER", "0"),
    ("GIT_SEQUENCE_EDITOR", ""),
    ("GIT_TERMINAL_PROMPT", "0"),
    ("NO_COLOR", "1"),
    ("PAGER", ""),
)
GIT_INHERITED_ENVIRONMENT_KEYS = ("SystemRoot", "WINDIR", "SystemDrive", "TEMP", "TMP")
GIT_FIXED_CONFIG: tuple[str, ...] = (
    "core.attributesFile=NUL",
    "core.fsmonitor=false",
    "core.hooksPath=NUL",
    "core.untrackedCache=false",
    "credential.helper=",
    "credential.interactive=never",
    "diff.external=",
    "fetch.recurseSubmodules=false",
    "gc.auto=0",
    "maintenance.auto=false",
    "protocol.allow=never",
    "protocol.file.allow=always",
    "submodule.recurse=false",
)

BOUND_PUBLIC_FILES: tuple[tuple[str, str], ...] = (
    ("docs/contracts/visual-witness-corpus-v1.schema.json", "0639e232311d7e0ee155c83806781010b6b437f6a80fec659c7493409df1b940"),
    ("docs/contracts/visual-witness-region-v1.schema.json", "531b9ac22b302792ee66e1cecd1f94dd8385f5ca7904f26c0f31ee96c1d78d73"),
    ("docs/contracts/visual-witness-event-receipt-v1.schema.json", "ae057c25216cbbe64c551752faa7ae603137343746dbacb46f990d69736e7b4f"),
    ("docs/contracts/visual-witness-e1-contract-v1.json", PARENT_CONTRACT_SHA256),
    ("docs/contracts/visual-witness-e2-packet-r1.json", R1_SHA256),
    (str(CAPTURE_SCHEMA_RELATIVE_PATH).replace("\\", "/"), CAPTURE_SCHEMA_SHA256),
)

ALLOWED_CASE_IDS = ("VW-T01", "VW-T02", "VW-T03")
HELD_OUT_CASE_IDS = frozenset(("VW-H01", "VW-H02", "VW-H03"))
DECLARED_CALIBRATION_PAGES = 753
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

FORMAT_ID = "visual-witness-e2-operational-report-v1"
RECORD_KIND = "visual-witness-capture-intermediate"
IMPLEMENTATION_FORMAT_REVISION = 1

DOMAINS = {
    "config": b"file-portal/vw-e2-config/r2\0",
    "primitive": b"file-portal/vw-e2-primitive/r2\0",
    "candidate": b"file-portal/vw-e2-candidate/r2\0",
    "relationship": b"file-portal/vw-e2-relationship/r2\0",
    "capture_payload": b"file-portal/vw-e2-capture-core/r2\0",
    "report": b"file-portal/vw-e2-report/r2\0",
    "protected_tree": b"file-portal/vw-e2-protected-tree/r2\0",
    "semantic_subject": b"file-portal/vw-e2-semantic-subject/r2\0",
    "semantic_check": b"file-portal/vw-e2-semantic-check/r2\0",
    "semantic_checks": b"file-portal/vw-e2-semantic-checks/r2\0",
    "report_id_subject": b"file-portal/vw-e2-report-id-subject/r2\0",
    "independent_verifier": b"file-portal/vw-e2-independent-verifier/r2\0",
    "probe": b"file-portal/vw-e2-probe/r2\0",
}

DPI = 192
SCALE_NUMERATOR = 8
SCALE_DENOMINATOR = 3
MAX_RENDER_PIXELS = 60_000_000
MAX_RENDER_AXIS_PX = 1_001_023
TILE_SIZE = 1024
TILE_STRIDE = 819
TILE_OVERLAP = 205
MIN_SCRATCH_FREE = 8_589_934_592
SCRATCH_HARD_CAP = 2_147_483_648

CLASS_ORDER = ("raster", "vector", "stroke-cluster", "scan-component", "text-block", "table")
CLASS_RANK = {name: rank for rank, name in enumerate(CLASS_ORDER)}
RULE_IDS = {
    "raster": "VW2-R2-RASTER-1",
    "vector": "VW2-R2-VECTOR-1",
    "stroke-cluster": "VW2-R2-STROKE-1",
    "scan-component": "VW2-R2-SCAN-1",
    "text-block": "VW2-R2-TEXT-1",
    "table": "VW2-R2-TABLE-1",
    "fusion": "VW2-R2-FUSION-1",
    "boundary": "VW2-R2-BOUNDARY-1",
}

# Every numeric discriminator below is frozen by VW-E2-R2.
VECTOR_MIN_STROKE_PT = 0.375
STROKE_DILATION_PX = 1
RASTER_COMPONENT_GAP_PX = 1
SCAN_MIN_UNION_FRACTION = 0.90
SCAN_MAX_EDGE_INSET = 0.05
TABLE_AXIS_TOLERANCE_PX = 1
TABLE_MIN_SEGMENT_EXTENT_PX = 4
TABLE_MERGE_AXIS_TOLERANCE_PX = 1
TABLE_MERGE_GAP_PX = 2
TABLE_MIN_HORIZONTAL_TRACKS = 3
TABLE_MIN_VERTICAL_TRACKS = 3
TABLE_MIN_INTERSECTION_FRACTION = 0.80
TABLE_MIN_CLOSED_CELLS = 4
TABLE_MIN_TEXT_CELLS = 4
TABLE_MIN_TEXT_ROWS = 2
TABLE_MIN_TEXT_COLUMNS = 2
ROUND_TRIP_TOLERANCE_PT = 0.375

TEXT_METHOD = "page.get_text('dict',flags=199,sort=false)"
IMAGE_METHOD = "page.get_image_info(hashes=true,xrefs=false)"
DRAWING_METHOD = "page.get_drawings(extended=false)"
CAPTURED_TEXT_METHOD = "native-overlap-block-concat-v1"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EVENT_CHILD_PIDS: set[int] = set()
EVENT_CHILD_EXITED_PIDS: set[int] = set()
EVENT_OBSERVED_DESCENDANT_PIDS: set[int] = set()
EVENT_MEASURED_GIT_HEADS: set[str] = set()
ACTIVE_ROOTS: OutputRoots | None = None  # assigned only after ROOTS-VERIFIED
ACTIVE_RUN_ID: str | None = None
ACTIVE_VERIFIER: subprocess.Popen[bytes] | None = None
LAST_COMPLETED_GATE = "START"


@dataclass
class EventActivityCounters:
    network_call_count: int = 0
    gpu_call_count: int = 0
    instrumentation_ready: bool = False
    reconciled_child_processes: int = 0
    native_git_expected_processes: int = 0
    native_git_reconciled_processes: int = 0
    native_git_attestations: list[dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        self.network_call_count = 0
        self.gpu_call_count = 0
        self.instrumentation_ready = False
        self.reconciled_child_processes = 0
        self.native_git_expected_processes = 0
        self.native_git_reconciled_processes = 0
        self.native_git_attestations.clear()


EVENT_ACTIVITY = EventActivityCounters()
_EVENT_AUDIT_INSTALLED = False
_EVENT_AUDIT_ACTIVE = False
_GPU_AUDIT_TOKENS = (
    "cuda", "nvcuda", "cudnn", "nvml", "nvidia-smi", "rocm", "hip", "opencl", "pycuda", "cupy",
)


def _event_activity_audit(event: str, args: tuple[Any, ...]) -> None:
    if not _EVENT_AUDIT_ACTIVE:
        return
    if event.startswith("socket."):
        EVENT_ACTIVITY.network_call_count += 1
        raise PermissionError("VW event network operation denied")
    lowered = " ".join(str(value).casefold() for value in args)
    gpu_attempt = (
        event in ("ctypes.dlopen", "subprocess.Popen", "os.system")
        and any(token in lowered for token in _GPU_AUDIT_TOKENS)
    ) or (
        event == "import"
        and any(lowered.startswith(token) or f" {token}" in lowered for token in ("cupy", "pycuda"))
    )
    if gpu_attempt:
        EVENT_ACTIVITY.gpu_call_count += 1
        raise PermissionError("VW event GPU operation denied")


def install_event_activity_audit() -> None:
    global _EVENT_AUDIT_INSTALLED, _EVENT_AUDIT_ACTIVE
    if not hasattr(sys, "addaudithook"):
        raise VWStop("UNREAD", "Python audit instrumentation unavailable")
    if not _EVENT_AUDIT_INSTALLED:
        sys.addaudithook(_event_activity_audit)
        _EVENT_AUDIT_INSTALLED = True
    _EVENT_AUDIT_ACTIVE = True
    EVENT_ACTIVITY.instrumentation_ready = True


def event_activity_snapshot() -> dict[str, Any]:
    return {
        "instrumentation_ready": EVENT_ACTIVITY.instrumentation_ready,
        "network_call_count": EVENT_ACTIVITY.network_call_count,
        "gpu_call_count": EVENT_ACTIVITY.gpu_call_count,
    }


def reconcile_event_activity(snapshot: Mapping[str, Any]) -> None:
    if set(snapshot) != {"instrumentation_ready", "network_call_count", "gpu_call_count"}:
        raise VWStop("UNREAD", "event activity counter shape unread")
    if snapshot.get("instrumentation_ready") is not True:
        raise VWStop("UNREAD", "child event activity instrumentation unavailable")
    network_count, gpu_count = snapshot.get("network_call_count"), snapshot.get("gpu_call_count")
    if type(network_count) is not int or type(gpu_count) is not int or min(network_count, gpu_count) < 0:
        raise VWStop("UNREAD", "child event activity counters unread")
    EVENT_ACTIVITY.network_call_count += network_count
    EVENT_ACTIVITY.gpu_call_count += gpu_count
    EVENT_ACTIVITY.reconciled_child_processes += 1


def require_event_activity_reconciled(expected_child_processes: int) -> None:
    if not EVENT_ACTIVITY.instrumentation_ready:
        raise VWStop("UNREAD", "producer event activity instrumentation unavailable")
    if EVENT_ACTIVITY.reconciled_child_processes != expected_child_processes:
        raise VWStop("UNREAD", "event child activity counters were not fully reconciled")
    if EVENT_ACTIVITY.network_call_count or EVENT_ACTIVITY.gpu_call_count:
        raise VWStop("VW-CLEANUP", "event-local network or GPU attempt was denied")
    native_expected = EVENT_ACTIVITY.native_git_expected_processes
    native_reconciled = EVENT_ACTIVITY.native_git_reconciled_processes
    attestations = EVENT_ACTIVITY.native_git_attestations
    if native_expected <= 0:
        raise VWStop("UNREAD", "native Git probe accounting was not exercised")
    if native_reconciled != native_expected or len(attestations) != native_expected:
        raise VWStop("UNREAD", "native Git probe accounting was not fully reconciled")
    attested_pids: set[int] = set()
    for attestation in attestations:
        if set(attestation) != {
            "argument_shape", "arguments", "binary_bytes", "binary_sha256", "controls_sha256",
            "deny_by_construction", "descendant_pids", "exit_code", "pid", "repo_root",
            "stderr_bytes", "stderr_sha256", "stdout_bytes", "stdout_sha256",
        }:
            raise VWStop("UNREAD", "native Git probe attestation shape was unread")
        pid = attestation.get("pid")
        if type(pid) is not int or pid <= 0:
            raise VWStop("UNREAD", "native Git probe PID accounting was unread")
        attested_pids.add(pid)
        try:
            repo_root = Path(attestation["repo_root"])
            arguments = tuple(attestation["arguments"])
            shape = _git_probe_shape(arguments)
            expected_controls = _git_controls_sha256(repo_root, arguments)
        except (KeyError, TypeError, ValueError, VWStop) as exc:
            raise VWStop("UNREAD", "native Git probe attestation could not be replayed") from exc
        if (
            attestation["argument_shape"] != shape
            or attestation["binary_bytes"] != GIT_EXECUTABLE_BYTES
            or attestation["binary_sha256"] != GIT_EXECUTABLE_SHA256
            or attestation["controls_sha256"] != expected_controls
            or attestation["deny_by_construction"] is not True
            or attestation["exit_code"] != 0
            or attestation["stderr_bytes"] != 0
            or attestation["stderr_sha256"] != EMPTY_SHA256
            or type(attestation["stdout_bytes"]) is not int
            or attestation["stdout_bytes"] < 0
            or not isinstance(attestation["stdout_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", attestation["stdout_sha256"]) is None
        ):
            raise VWStop("UNREAD", "native Git probe attestation did not match frozen controls")
        descendants = attestation["descendant_pids"]
        if (
            not isinstance(descendants, list)
            or any(type(item) is not int or item <= 0 for item in descendants)
            or descendants != sorted(set(descendants))
            or not set(descendants) <= EVENT_OBSERVED_DESCENDANT_PIDS
        ):
            raise VWStop("UNREAD", "native Git descendant accounting was unread")
    if not attested_pids <= EVENT_CHILD_PIDS or not attested_pids <= EVENT_CHILD_EXITED_PIDS:
        raise VWStop("UNREAD", "native Git direct-child lifecycle was not fully recorded")
    if not EVENT_CHILD_PIDS <= EVENT_CHILD_EXITED_PIDS:
        raise VWStop("UNREAD", "event direct-child lifecycle was not fully reconciled")

SEMANTIC_CHECK_NAMES = (
    "canonical-json-and-array-order",
    "report-id",
    "capture-payload-hash",
    "packet-parent-schema-config-binding",
    "case-order-uniqueness",
    "case-census-arithmetic",
    "page-count-contiguity",
    "status-null-reason-coherence",
    "source-bundle-hashes",
    "page-map-coherence",
    "bbox-order-range-transform",
    "render-rgb-arithmetic",
    "tile-id-bbox-reference",
    "tile-rgb-arithmetic",
    "tile-union-coverage",
    "primitive-kind-attributes-geometry",
    "primitive-id",
    "candidate-class-basis-evidence",
    "candidate-source-references",
    "candidate-id",
    "class-procedure-completeness",
    "class-census-reconciliation",
    "relationship-reference-geometry-id",
    "edge-recovery-reference-containment",
    "crop-rgb-arithmetic",
    "captured-text-state-hash",
    "metric-arithmetic",
    "resource-worker-reconciliation",
    "protected-tree-digest",
    "privacy-heldout-cleanup-redaction",
    "independent-verification-binding",
    "semantic-unread-boundary",
    "output-root-realpath-containment",
    "residue-privacy-census",
)

SCOPE_ENUM = frozenset(
    (
        "event", "source", "bundle", "page", "raster-procedure", "vector-procedure",
        "stroke-cluster-procedure", "scan-component-procedure", "text-procedure",
        "table-procedure", "output-root", "scratch-root", "privacy", "cleanup",
        "protected-tree", "independent-verifier", "resource-probe", "system-global-census",
    )
)
DETAIL_BY_REASON = {
    "GROUND-DRIFT": "ground-drift",
    "AUTHORITY-MISSING": "authority-missing",
    "VW-SOURCE-HASH": "source-hash-mismatch",
    "VW-BODY-HASH": "body-hash-mismatch",
    "VW-ASSET-HASH": "asset-hash-mismatch",
    "VW-CONFIG-HASH": "config-hash-mismatch",
    "VW-PAGE-MAP-UNREAD": "page-map-unread",
    "VW-RENDER-UNREAD": "render-unread",
    "VW-TILE-GAP": "tile-gap",
    "VW-CROP-BOUNDS": "crop-bounds",
    "VW-COORDINATE-UNREAD": "coordinate-unread",
    "VW-RASTER-DIGEST-UNREAD": "raster-digest-unread",
    "VW-VECTOR-GEOMETRY-UNREAD": "vector-geometry-unread",
    "VW-DEPENDENCY-DRIFT": "dependency-drift",
    "VW-HELDOUT-CONTAMINATION": "heldout-contamination",
    "VW-PROTECTED-TREE": "protected-tree-change",
    "VW-PRIVACY": "privacy-rejection",
    "VW-CLEANUP": "cleanup-failure",
    "VW-IDENTITY": "identity-mismatch",
    "VW-NEGATIVE-CONTROL": "negative-control-failed",
    "VW-UNAUTHORIZED-THRESHOLD": "unauthorized-threshold",
    "UNREAD": "procedural-unread",
}
DETAIL_ENUM = frozenset(
    (*DETAIL_BY_REASON.values(), "outside-event-process-scope", "optional-gpu-probe-unread",
     "evidence-root-unread", "scratch-root-unread", "root-reparse", "root-overlap",
     "output-create-failed", "verifier-unread", "event-child-port", "part-file-remains")
)


class VWStop(RuntimeError):
    """A packet-defined STOP or procedural-UNREAD boundary."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class SourceIdentityContext:
    """Opaque proof that an enclosing case source passed the frozen hash gate."""

    sha256: str


def measured_source_identity(source: Mapping[str, Any]) -> SourceIdentityContext:
    hashes = [source.get(name) for name in ("manifest_sha256", "recorded_actual_sha256", "observed_sha256")]
    if (
        source.get("status") != "measured"
        or source.get("all_hashes_match") is not True
        or len(set(hashes)) != 1
        or not isinstance(hashes[0], str)
        or re.fullmatch(r"[0-9a-f]{64}", hashes[0]) is None
    ):
        raise VWStop("VW-SOURCE-HASH", "source identity context is not measured and hash-equal")
    return SourceIdentityContext(hashes[0])


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VWStop("GROUND-DRIFT", f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes, *, reason: str = "GROUND-DRIFT") -> Any:
    """Load UTF-8 JSON, rejecting duplicate keys and non-finite constants."""

    def bad_constant(value: str) -> None:
        raise VWStop(reason, f"non-finite JSON constant {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=bad_constant,
        )
    except VWStop:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VWStop(reason, f"invalid UTF-8 JSON: {exc}") from exc


def strict_json_file(path: Path, *, reason: str = "GROUND-DRIFT") -> Any:
    return strict_json_bytes(path.read_bytes(), reason=reason)


def _assert_finite_json(value: Any, trail: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise VWStop("GROUND-DRIFT", f"non-finite value at {trail}")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise VWStop("GROUND-DRIFT", f"non-string object key at {trail}")
            _assert_finite_json(child, f"{trail}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_finite_json(child, f"{trail}[{index}]")


def canonical_json_bytes(value: Any) -> bytes:
    _assert_finite_json(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VWStop("GROUND-DRIFT", f"value is not canonical-JSON serializable: {exc}") from exc


def domain_hash(domain: str, value: Any, *, prefixed: bool) -> str:
    """Hash one of the packet's exact canonical-JSON identity projections."""

    try:
        prefix = DOMAINS[domain]
    except KeyError as exc:
        raise VWStop("GROUND-DRIFT", f"unknown identity domain {domain!r}") from exc
    digest = sha256_bytes(prefix + canonical_json_bytes(value))
    return f"sha256:{digest}" if prefixed else digest


def config_sha256(frozen_configuration: Mapping[str, Any]) -> str:
    projection = dict(frozen_configuration)
    if "config_sha256" in projection:
        raise VWStop("GROUND-DRIFT", "frozen_configuration must not contain config_sha256")
    return domain_hash("config", projection, prefixed=False)


def primitive_id(primitive: Mapping[str, Any]) -> str:
    projection = {
        key: primitive[key]
        for key in (
            "source_sha256",
            "page_1based",
            "kind",
            "method",
            "bbox_pdf_pt",
            "bbox_px_half_open",
            "identity_attributes",
        )
    }
    return domain_hash("primitive", projection, prefixed=True)


def candidate_id(candidate: Mapping[str, Any]) -> str:
    projection = {
        key: candidate[key]
        for key in (
            "source_sha256",
            "page_1based",
            "bbox_pdf_pt",
            "bbox_px_half_open",
            "classes",
            "config_sha256",
            "source_primitive_ids",
        )
    }
    return domain_hash("candidate", projection, prefixed=True)


def relationship_id(relationship: Mapping[str, Any]) -> str:
    projection = {
        key: relationship[key]
        for key in ("source_candidate_id", "target_candidate_id", "kind")
    }
    return domain_hash("relationship", projection, prefixed=True)


def capture_payload_sha256(capture_payload: Mapping[str, Any]) -> str:
    projection = dict(capture_payload)
    projection.pop("capture_payload_sha256", None)
    return domain_hash("capture_payload", projection, prefixed=False)


def report_id(report: Mapping[str, Any]) -> str:
    projection = dict(report)
    projection.pop("report_id", None)
    return domain_hash("report", projection, prefixed=True)


def _fixed_decimal(value: float | int | Decimal, places: int) -> str:
    numeric = Decimal(str(value))
    if not numeric.is_finite():
        raise VWStop("VW-CROP-BOUNDS", "non-finite PDF coordinate")
    quantum = Decimal(1).scaleb(-places)
    numeric = numeric.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if numeric == 0:
        numeric = abs(numeric)
    return format(numeric, f".{places}f")


def point_string(value: float | int | Decimal) -> str:
    return _fixed_decimal(value, 6)


def normalized_string(value: float | int | Decimal) -> str:
    return _fixed_decimal(value, 9)


def lexical_case_guard(
    case_ids: Sequence[Any], *, resolver_spy: Callable[[str], None] | None = None
) -> tuple[str, ...]:
    """Reject forbidden/unknown IDs before *any* manifest-supplied path operation.

    ``resolver_spy`` is intentionally called only after all IDs have passed.  The self-test
    uses it as a negative control for the ordering guarantee.
    """

    if not isinstance(case_ids, (list, tuple)):
        raise VWStop("VW-HELDOUT-CONTAMINATION", "case selection must be a lexical sequence")
    checked: list[str] = []
    for raw in case_ids:
        if not isinstance(raw, str):
            raise VWStop("VW-HELDOUT-CONTAMINATION", "non-string case ID")
        if raw in HELD_OUT_CASE_IDS:
            raise VWStop("VW-HELDOUT-CONTAMINATION", f"held-out case ID {raw} is forbidden")
        if raw not in ALLOWED_CASE_IDS:
            raise VWStop("VW-HELDOUT-CONTAMINATION", f"case ID {raw!r} is outside calibration")
        if raw in checked:
            raise VWStop("VW-HELDOUT-CONTAMINATION", f"duplicate case ID {raw}")
        checked.append(raw)
    if tuple(checked) != tuple(case_id for case_id in ALLOWED_CASE_IDS if case_id in checked):
        raise VWStop("VW-HELDOUT-CONTAMINATION", "calibration IDs must use canonical order")
    if resolver_spy is not None:
        for case_id in checked:
            resolver_spy(case_id)
    return tuple(checked)


@dataclass(frozen=True, order=True)
class Box:
    """Finite half-open rectangle; floats are permitted before pixel quantisation."""

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x0, self.y0, self.x1, self.y1)):
            raise VWStop("VW-CROP-BOUNDS", "non-finite rectangle")

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def positive(self) -> bool:
        return self.x1 > self.x0 and self.y1 > self.y0

    def intersect(self, other: "Box") -> "Box | None":
        result = Box(max(self.x0, other.x0), max(self.y0, other.y0), min(self.x1, other.x1), min(self.y1, other.y1))
        return result if result.positive() else None

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    def contains(self, other: "Box") -> bool:
        return self.x0 <= other.x0 and self.y0 <= other.y0 and self.x1 >= other.x1 and self.y1 >= other.y1

    def expand(self, amount: float) -> "Box":
        return Box(self.x0 - amount, self.y0 - amount, self.x1 + amount, self.y1 + amount)

    def clip(self, width: float, height: float) -> "Box":
        return Box(max(0.0, self.x0), max(0.0, self.y0), min(width, self.x1), min(height, self.y1))

    def integer_tuple(self) -> tuple[int, int, int, int]:
        return (int(self.x0), int(self.y0), int(self.x1), int(self.y1))


def box_union(boxes: Iterable[Box]) -> Box:
    materialized = list(boxes)
    if not materialized:
        raise VWStop("VW-CROP-BOUNDS", "cannot union an empty rectangle set")
    return Box(
        min(box.x0 for box in materialized),
        min(box.y0 for box in materialized),
        max(box.x1 for box in materialized),
        max(box.y1 for box in materialized),
    )


def boxes_touch_with_gap(left: Box, right: Box, gap: float) -> bool:
    return not (
        left.x1 + gap < right.x0
        or right.x1 + gap < left.x0
        or left.y1 + gap < right.y0
        or right.y1 + gap < left.y0
    )


def rect_strings(box: Box) -> list[str]:
    return [point_string(value) for value in (box.x0, box.y0, box.x1, box.y1)]


def normalized_rect_strings(box: Box, width: int, height: int) -> list[str]:
    if width <= 0 or height <= 0:
        raise VWStop("VW-CROP-BOUNDS", "non-positive render dimensions")
    return [
        normalized_string(box.x0 / width),
        normalized_string(box.y0 / height),
        normalized_string(box.x1 / width),
        normalized_string(box.y1 / height),
    ]


def axis_starts(length: int, *, tile_size: int = TILE_SIZE, stride: int = TILE_STRIDE) -> list[int]:
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (length, tile_size, stride)):
        raise VWStop("VW-TILE-GAP", "axis parameters are not exact integers")
    if length <= 0 or length > MAX_RENDER_AXIS_PX or tile_size < 1 or stride < 1:
        raise VWStop("VW-TILE-GAP", f"invalid axis length {length}")
    starts: list[int] = []
    start = 0
    while start + tile_size < length:
        starts.append(start)
        start += stride
    starts.append(max(0, length - tile_size))
    return sorted(set(starts))


def make_tiles(page_1based: int, width: int, height: int) -> list[dict[str, Any]]:
    if isinstance(page_1based, bool) or not isinstance(page_1based, int) or not (1 <= page_1based <= 999999):
        raise VWStop("VW-TILE-GAP", "page ordinal cannot be encoded in the frozen tile ID")
    tiles: list[dict[str, Any]] = []
    for top in axis_starts(height):
        for left in axis_starts(width):
            right = min(width, left + TILE_SIZE)
            bottom = min(height, top + TILE_SIZE)
            tiles.append(
                {
                    "tile_id": f"p{page_1based:06d}-x{left:06d}-y{top:06d}",
                    "bbox_px_half_open": [left, top, right, bottom],
                }
            )
    return tiles


def exact_union_area(rectangles: Sequence[Box]) -> int:
    """Exact set-union area for integer half-open rectangles."""

    if not rectangles:
        return 0
    xs = sorted({int(box.x0) for box in rectangles} | {int(box.x1) for box in rectangles})
    area = 0
    for x0, x1 in zip(xs, xs[1:]):
        if x1 <= x0:
            continue
        intervals: list[tuple[int, int]] = []
        for box in rectangles:
            if box.x0 < x1 and box.x1 > x0:
                intervals.append((int(box.y0), int(box.y1)))
        if not intervals:
            continue
        intervals.sort()
        covered = 0
        lo, hi = intervals[0]
        for next_lo, next_hi in intervals[1:]:
            if next_lo <= hi:
                hi = max(hi, next_hi)
            else:
                covered += hi - lo
                lo, hi = next_lo, next_hi
        covered += hi - lo
        area += (x1 - x0) * covered
    return area


def check_tile_union(
    width: int,
    height: int,
    tiles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    boxes = [Box(*map(float, tile["bbox_px_half_open"])) for tile in tiles]
    covered = exact_union_area(boxes)
    valid = width * height
    if covered != valid:
        raise VWStop("VW-TILE-GAP", f"tile union {covered} does not equal valid page pixels {valid}")
    if any(not box.positive() or box.x0 < 0 or box.y0 < 0 or box.x1 > width or box.y1 > height for box in boxes):
        raise VWStop("VW-TILE-GAP", "base tile lies outside the rendered page")
    return {
        "status": "measured",
        "numerator_name": "valid rendered page pixels covered by at least one declared base tile",
        "numerator": covered,
        "denominator_name": "valid rendered page pixels on attempted readable pages",
        "denominator": width * height,
        "value": covered / (width * height),
        "conditions": {
            "render_dpi": DPI,
            "tile_size_px": TILE_SIZE,
            "stride_px": TILE_STRIDE,
            "readable_pages": 1,
            "unread_pages": 0,
        },
        "reason_codes": [],
    }


def connected_components(
    primitives: Sequence[Mapping[str, Any]],
    *,
    bbox_key: str,
    gap: float,
) -> list[list[Mapping[str, Any]]]:
    """Canonical transitive components independent of input duplication/order."""

    unique = {str(item["primitive_id"]): item for item in primitives}
    ordered = [unique[key] for key in sorted(unique)]
    parent = list(range(len(ordered)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    for left in range(len(ordered)):
        left_box = Box(*map(float, ordered[left][bbox_key]))
        for right in range(left + 1, len(ordered)):
            right_box = Box(*map(float, ordered[right][bbox_key]))
            if boxes_touch_with_gap(left_box, right_box, gap):
                union(left, right)
    groups: dict[int, list[Mapping[str, Any]]] = {}
    for index, primitive in enumerate(ordered):
        groups.setdefault(find(index), []).append(primitive)
    return [groups[root] for root in sorted(groups, key=lambda root: groups[root][0]["primitive_id"])]


def _box(value: Any) -> Box:
    if isinstance(value, Box):
        return value
    if hasattr(value, "x0"):
        values = (value.x0, value.y0, value.x1, value.y1)
    else:
        if isinstance(value, (str, bytes)):
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle is not a four-number sequence")
        try:
            values = tuple(value)
        except TypeError as exc:
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle is not iterable") from exc
        if len(values) != 4:
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle does not have four members")
    converted: list[float] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float, str)):
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle member is not an exact numeric primitive")
        try:
            numeric = float(item)
        except ValueError as exc:
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle member is not numeric") from exc
        if not math.isfinite(numeric):
            raise VWStop("VW-COORDINATE-UNREAD", "rectangle member is non-finite")
        converted.append(numeric)
    return Box(*converted)


def _xy(value: Any) -> tuple[float, float]:
    if hasattr(value, "x"):
        values = (value.x, value.y)
    else:
        if isinstance(value, (str, bytes)):
            raise VWStop("VW-COORDINATE-UNREAD", "point is not a two-number sequence")
        try:
            values = tuple(value)
        except TypeError as exc:
            raise VWStop("VW-COORDINATE-UNREAD", "point is not iterable") from exc
        if len(values) != 2:
            raise VWStop("VW-COORDINATE-UNREAD", "point does not have two members")
    converted: list[float] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float, str)):
            raise VWStop("VW-COORDINATE-UNREAD", "point member is not an exact numeric primitive")
        try:
            numeric = float(item)
        except ValueError as exc:
            raise VWStop("VW-COORDINATE-UNREAD", "point member is not numeric") from exc
        if not math.isfinite(numeric):
            raise VWStop("VW-COORDINATE-UNREAD", "point member is non-finite")
        converted.append(numeric)
    return (converted[0], converted[1])


def _api_box(value: Any) -> Box:
    try:
        raw = (value.x0, value.y0, value.x1, value.y1) if hasattr(value, "x0") else tuple(value)
    except (AttributeError, TypeError) as exc:
        raise VWStop("VW-COORDINATE-UNREAD", "API rectangle is not iterable") from exc
    if len(raw) != 4 or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in raw):
        raise VWStop("VW-COORDINATE-UNREAD", "API rectangle shape/type mismatch")
    return _box(raw)


def _api_xy(value: Any) -> tuple[float, float]:
    try:
        raw = (value.x, value.y) if hasattr(value, "x") else tuple(value)
    except (AttributeError, TypeError) as exc:
        raise VWStop("VW-COORDINATE-UNREAD", "API point is not iterable") from exc
    if len(raw) != 2 or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in raw):
        raise VWStop("VW-COORDINATE-UNREAD", "API point shape/type mismatch")
    return _xy(raw)


def point_pair(value: Any) -> list[str]:
    x, y = _xy(value)
    return [point_string(x), point_string(y)]


def matrix_strings(matrix: Any) -> list[str]:
    values = tuple(matrix) if not hasattr(matrix, "a") else (
        matrix.a,
        matrix.b,
        matrix.c,
        matrix.d,
        matrix.e,
        matrix.f,
    )
    if len(values) != 6:
        raise VWStop("VW-COORDINATE-UNREAD", "affine matrix does not have six members")
    return [point_string(value) for value in values]


def mupdf_box_to_pdf_user(box: Box, cropbox_position: Any, mediabox_y1: float) -> Box:
    """Apply the packet's explicit CropBox-local to PDF-user-space formula."""

    crop_x, crop_y = _xy(cropbox_position)
    return Box(
        crop_x + box.x0,
        mediabox_y1 - crop_y - box.y1,
        crop_x + box.x1,
        mediabox_y1 - crop_y - box.y0,
    )


def _transform_xy(x: float, y: float, matrix: Any) -> tuple[float, float]:
    if hasattr(matrix, "a"):
        return (
            x * float(matrix.a) + y * float(matrix.c) + float(matrix.e),
            x * float(matrix.b) + y * float(matrix.d) + float(matrix.f),
        )
    a, b, c, d, e, f = map(float, matrix)
    return (x * a + y * c + e, x * b + y * d + f)


def mupdf_box_to_render_px(box: Box, rotation_matrix: Any, width: int, height: int) -> Box:
    rotated = [
        _transform_xy(x, y, rotation_matrix)
        for x, y in ((box.x0, box.y0), (box.x1, box.y0), (box.x1, box.y1), (box.x0, box.y1))
    ]
    scale = Decimal(SCALE_NUMERATOR) / Decimal(SCALE_DENOMINATOR)
    x0 = int((Decimal(str(min(x for x, _ in rotated))) * scale).to_integral_value(rounding=ROUND_FLOOR))
    y0 = int((Decimal(str(min(y for _, y in rotated))) * scale).to_integral_value(rounding=ROUND_FLOOR))
    x1 = int((Decimal(str(max(x for x, _ in rotated))) * scale).to_integral_value(rounding=ROUND_CEILING))
    y1 = int((Decimal(str(max(y for _, y in rotated))) * scale).to_integral_value(rounding=ROUND_CEILING))
    result = Box(max(0, x0), max(0, y0), min(width, x1), min(height, y1))
    if not result.positive():
        raise VWStop("VW-CROP-BOUNDS", f"zero-area transformed bbox {result}")
    return result


def assert_pixel_round_trip(pixel_box: Box, original_box: Box, derotation_matrix: Any) -> None:
    inverse_scale = Decimal(SCALE_DENOMINATOR) / Decimal(SCALE_NUMERATOR)
    points = []
    for x, y in (
        (pixel_box.x0, pixel_box.y0),
        (pixel_box.x1, pixel_box.y0),
        (pixel_box.x1, pixel_box.y1),
        (pixel_box.x0, pixel_box.y1),
    ):
        scaled_x = float(Decimal(str(x)) * inverse_scale)
        scaled_y = float(Decimal(str(y)) * inverse_scale)
        points.append(_transform_xy(scaled_x, scaled_y, derotation_matrix))
    reconstructed = Box(
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )
    for observed, expected in zip(reconstructed.integer_tuple(), original_box.integer_tuple()):
        # The integer tuple comparison below is only an early gross-error guard; exact
        # tolerance is checked against the floating edges immediately afterwards.
        if abs(observed - expected) > 2:
            raise VWStop("VW-COORDINATE-UNREAD", "pixel-to-MuPDF round trip grossly diverged")
    if any(
        abs(observed - expected) > ROUND_TRIP_TOLERANCE_PT + 1e-9
        for observed, expected in zip(
            (reconstructed.x0, reconstructed.y0, reconstructed.x1, reconstructed.y1),
            (original_box.x0, original_box.y0, original_box.x1, original_box.y1),
        )
    ):
        raise VWStop("VW-COORDINATE-UNREAD", "pixel-to-MuPDF round trip exceeds 0.375pt")


def page_coordinate_context(page: Any, width: int, height: int) -> dict[str, Any]:
    media = _api_box(page.mediabox)
    crop_position = page.cropbox_position
    _api_xy(crop_position)
    rotation = page.rotation
    if isinstance(rotation, bool) or not isinstance(rotation, int):
        raise VWStop("VW-COORDINATE-UNREAD", "page rotation is not an exact integer")
    if rotation not in (0, 90, 180, 270):
        raise VWStop("VW-COORDINATE-UNREAD", f"unsupported rotation {rotation}")
    cropbox = _api_box(page.cropbox)
    local_width = cropbox.width
    local_height = cropbox.height
    if local_width <= 0 or local_height <= 0 or not media.positive():
        raise VWStop("VW-COORDINATE-UNREAD", "page media/CropBox is not positive-area")
    local_crop = Box(0.0, 0.0, local_width, local_height)
    local_media = Box(-float(crop_position.x), -float(crop_position.y), media.width - float(crop_position.x), media.height - float(crop_position.y))
    return {
        "local_bounds": local_crop,
        "cropbox_position": crop_position,
        "mediabox_y1": float(media.y1),
        "rotation_matrix_object": page.rotation_matrix,
        "derotation_matrix_object": page.derotation_matrix,
        "media_box_mupdf_pt": rect_strings(local_media),
        "crop_box_mupdf_pt": rect_strings(local_crop),
        "media_box_pdf_user_space_pt": rect_strings(mupdf_box_to_pdf_user(local_media, crop_position, float(media.y1))),
        "crop_box_pdf_user_space_pt": rect_strings(mupdf_box_to_pdf_user(local_crop, crop_position, float(media.y1))),
        "rotation_degrees": rotation,
        "coordinate_derivation": {
            "status": "measured",
            "pdf_user_formula_id": "cropbox-position-plus-x-mediabox-y1-minus-cropbox-y-minus-y-v1",
            "cropbox_position_mupdf_pt": point_pair(crop_position),
            "mediabox_y1_mupdf_pt": point_string(media.y1),
            "render_transform_method": "page.rotation_matrix",
            "rotation_matrix": matrix_strings(page.rotation_matrix),
            "derotation_matrix": matrix_strings(page.derotation_matrix),
            "transformation_matrix_used": False,
            "input_claim_status": "Observed",
            "derived_claim_status": "Verified-self",
            "reason_codes": [],
        },
        "render_width": width,
        "render_height": height,
    }


def _primitive_record(
    *,
    source_context: SourceIdentityContext,
    page_1based: int,
    kind: str,
    method: str,
    geometry: Mapping[str, Any],
    bbox_mupdf: Box,
    context: Mapping[str, Any],
    identity_attributes: Mapping[str, Any],
    source_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    local = bbox_mupdf.intersect(context["local_bounds"])
    if local is None:
        raise VWStop("VW-CROP-BOUNDS", "primitive lies wholly outside the CropBox")
    pdf_box = mupdf_box_to_pdf_user(local, context["cropbox_position"], context["mediabox_y1"])
    px_box = mupdf_box_to_render_px(
        local,
        context["rotation_matrix_object"],
        int(context["render_width"]),
        int(context["render_height"]),
    )
    assert_pixel_round_trip(px_box, local, context["derotation_matrix_object"])
    record: dict[str, Any] = {
        "source_sha256": source_context.sha256,
        "page_1based": page_1based,
        "kind": kind,
        "method": method,
        "geometry": dict(geometry),
        "bbox_mupdf_unrotated_pt": rect_strings(local),
        "bbox_pdf_pt": rect_strings(pdf_box),
        "bbox_px_half_open": list(px_box.integer_tuple()),
        "source_claim_status": "Observed",
        "derived_geometry_claim_status": "Verified-self",
        "identity_attributes": dict(identity_attributes),
        "source_evidence": dict(source_evidence),
    }
    record["primitive_id"] = primitive_id(record)
    record.pop("source_sha256")
    record.pop("page_1based")
    return record


def _provenance(
    *,
    engine_list_index: int,
    engine_number: Any = None,
    drawing_index: Any = None,
    drawing_seqno: Any = None,
    item_index: Any = None,
    edge_index: Any = None,
) -> dict[str, Any]:
    def integer_or_none(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise VWStop("VW-IDENTITY", "primitive provenance is not a nonnegative exact integer")
        return value

    if isinstance(engine_list_index, bool) or not isinstance(engine_list_index, int) or engine_list_index < 0:
        raise VWStop("VW-IDENTITY", "engine list index is not a nonnegative exact integer")

    return {
        "drawing_list_index_0based": integer_or_none(drawing_index),
        "drawing_seqno_observed": integer_or_none(drawing_seqno),
        "emitted_edge_index_0based": integer_or_none(edge_index),
        "engine_list_index_0based": engine_list_index,
        "engine_number_observed": integer_or_none(engine_number),
        "item_list_index_0based": integer_or_none(item_index),
    }


def _deduplicate_primitives(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record["primitive_id"]
        if key not in by_id:
            by_id[key] = record
            continue
        existing = by_id[key]
        left = {k: v for k, v in existing.items() if k not in ("geometry", "source_evidence")}
        right = {k: v for k, v in record.items() if k not in ("geometry", "source_evidence")}
        if canonical_json_bytes(left) != canonical_json_bytes(right):
            raise VWStop("VW-IDENTITY", f"primitive collision for {key}")
        left_evidence = {k: v for k, v in existing["source_evidence"].items() if k != "provenance_records"}
        right_evidence = {k: v for k, v in record["source_evidence"].items() if k != "provenance_records"}
        if canonical_json_bytes(left_evidence) != canonical_json_bytes(right_evidence):
            raise VWStop("VW-IDENTITY", f"primitive evidence collision for {key}")
        existing["geometry"] = min(
            (existing["geometry"], record["geometry"]),
            key=canonical_json_bytes,
        )
        provenance = existing["source_evidence"]["provenance_records"] + record["source_evidence"]["provenance_records"]
        unique = {canonical_json_bytes(item): item for item in provenance}

        def provenance_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
            names = (
                "engine_list_index_0based",
                "drawing_list_index_0based",
                "drawing_seqno_observed",
                "item_list_index_0based",
                "emitted_edge_index_0based",
                "engine_number_observed",
            )
            return tuple((-1 if item[name] is None else item[name]) for name in names)

        existing["source_evidence"]["provenance_records"] = sorted(unique.values(), key=provenance_key)
    kind_rank = {"raster": 0, "vector": 1, "text": 2}
    return sorted(
        by_id.values(),
        key=lambda item: (kind_rank[item["kind"]], *item["bbox_px_half_open"], item["primitive_id"]),
    )


def extract_raster_primitives(
    page: Any, source_context: SourceIdentityContext, page_1based: int, context: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    infos = page.get_image_info(hashes=True, xrefs=False)
    if not isinstance(infos, list):
        raise VWStop("VW-RASTER-DIGEST-UNREAD", "image occurrence API result is not a list")
    for index, info in enumerate(infos):
        if not isinstance(info, dict):
            raise VWStop("VW-RASTER-DIGEST-UNREAD", "image occurrence is not an object")
        digest = info.get("digest")
        if not isinstance(digest, bytes) or len(digest) != 16:
            raise VWStop("VW-RASTER-DIGEST-UNREAD", f"image occurrence {index} has no 16-byte MD5 digest")
        width_px = info.get("width")
        height_px = info.get("height")
        if not isinstance(width_px, int) or not isinstance(height_px, int) or width_px < 1 or height_px < 1:
            raise VWStop("VW-RASTER-DIGEST-UNREAD", f"image occurrence {index} has invalid dimensions")
        engine_number = info.get("number")
        if isinstance(engine_number, bool) or not isinstance(engine_number, int) or engine_number < 0:
            raise VWStop("VW-RASTER-DIGEST-UNREAD", f"image occurrence {index} number is not an exact integer")
        evidence = {
            "provenance_records": [_provenance(engine_list_index=index, engine_number=engine_number)],
            "digest_algorithm": "md5",
            "observed_stroke_width_pdf_pt": None,
            "stroke_width_disposition": None,
            "text_extraction_method": None,
            "engine_version": None,
            "claim_status": "Observed",
        }
        records.append(
            _primitive_record(
                source_context=source_context,
                page_1based=page_1based,
                kind="raster",
                method=IMAGE_METHOD,
                geometry={"kind": "bbox-only"},
                bbox_mupdf=_api_box(info["bbox"]),
                context=context,
                identity_attributes={
                    "digest_algorithm": "md5",
                    "digest_hex": digest.hex(),
                    "height_px": height_px,
                    "width_px": width_px,
                },
                source_evidence=evidence,
            )
        )
    return (_deduplicate_primitives(records), len(infos))


def extract_text_primitives(
    page: Any, source_context: SourceIdentityContext, page_1based: int, context: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, bytes], dict[str, int]]:
    result = page.get_text("dict", flags=199, sort=False)
    blocks = result.get("blocks") if isinstance(result, dict) else None
    if not isinstance(blocks, list):
        raise VWStop("VW-RENDER-UNREAD", "text dictionary has no block array")
    records: list[dict[str, Any]] = []
    ephemeral: dict[str, bytes] = {}
    type_census: dict[str, int] = {}
    for engine_index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} is not an object")
        block_type = block.get("type")
        if isinstance(block_type, bool) or not isinstance(block_type, int) or block_type < 0:
            raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} type is not an exact integer")
        type_census[str(block_type)] = type_census.get(str(block_type), 0) + 1
        if block_type != 0:
            # Type-1 blocks may contain raw image bytes; do not retain or inspect them.
            continue
        lines = block.get("lines")
        if not isinstance(lines, list):
            raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} has no line array")
        line_strings: list[str] = []
        for line in lines:
            spans = line.get("spans") if isinstance(line, dict) else None
            if not isinstance(spans, list):
                raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} has invalid spans")
            pieces: list[str] = []
            for span in spans:
                if not isinstance(span, dict) or not isinstance(span.get("text"), str):
                    raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} span has invalid text")
                pieces.append(span["text"])
            line_strings.append("".join(pieces))
        text = "\n".join(line_strings)
        raw = text.encode("utf-8")
        engine_number = block.get("number")
        if isinstance(engine_number, bool) or not isinstance(engine_number, int) or engine_number < 0:
            raise VWStop("VW-RENDER-UNREAD", f"text block {engine_index} number is not an exact integer")
        evidence = {
            "provenance_records": [_provenance(engine_list_index=engine_index, engine_number=engine_number)],
            "digest_algorithm": None,
            "observed_stroke_width_pdf_pt": None,
            "stroke_width_disposition": None,
            "text_extraction_method": TEXT_METHOD,
            "engine_version": str(pymupdf.__version__),
            "claim_status": "Observed",
        }
        if not raw or not text:
            continue
        record = _primitive_record(
            source_context=source_context,
            page_1based=page_1based,
            kind="text",
            method=TEXT_METHOD,
            geometry={"kind": "bbox-only"},
            bbox_mupdf=_api_box(block["bbox"]),
            context=context,
            identity_attributes={
                "utf8_sha256": sha256_bytes(raw),
                "utf8_bytes": len(raw),
                "unicode_codepoints": len(text),
            },
            source_evidence=evidence,
        )
        records.append(record)
        ephemeral[record["primitive_id"]] = raw
    records = _deduplicate_primitives(records)
    ephemeral = {item["primitive_id"]: ephemeral[item["primitive_id"]] for item in records}
    return (records, ephemeral, type_census)


def _width_disposition(path: Mapping[str, Any]) -> tuple[float | None, float, str, bool]:
    path_type = path.get("type")
    if path_type not in ("s", "f", "fs"):
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"unknown drawing type {path_type!r}")
    fill_only = path_type == "f"
    raw = path.get("width")
    if fill_only:
        return (None, VECTOR_MIN_STROKE_PT, "fill-only-fallback", True)
    if raw is None:
        return (None, VECTOR_MIN_STROKE_PT, "fallback-missing", False)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "non-numeric drawing width")
    try:
        observed = float(raw)
    except (TypeError, ValueError) as exc:
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "non-numeric drawing width") from exc
    if not math.isfinite(observed) or observed < 0:
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"invalid drawing width {raw!r}")
    if observed == 0:
        return (point_string(0.0), VECTOR_MIN_STROKE_PT, "fallback-zero", False)
    return (observed, observed, "observed-positive", False)


def _edge_identity(p0: Any, p1: Any) -> dict[str, Any]:
    endpoints = sorted((point_pair(p0), point_pair(p1)), key=lambda item: tuple(item))
    return {"endpoints": endpoints}


def _vector_record(
    *,
    source_context: SourceIdentityContext,
    page_1based: int,
    context: Mapping[str, Any],
    item_type: str,
    geometry: Mapping[str, Any],
    identity_geometry: Mapping[str, Any],
    hull_points: Sequence[Any],
    observed_width: float | str | None,
    effective_width: float,
    disposition: str,
    fill_only: bool,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    coordinates = [_xy(point) for point in hull_points]
    if not coordinates:
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "empty vector hull")
    half = effective_width / 2.0
    bbox = Box(
        min(x for x, _ in coordinates) - half,
        min(y for _, y in coordinates) - half,
        max(x for x, _ in coordinates) + half,
        max(y for _, y in coordinates) + half,
    )
    observed_string = None if observed_width is None else point_string(observed_width)
    return _primitive_record(
        source_context=source_context,
        page_1based=page_1based,
        kind="vector",
        method=DRAWING_METHOD,
        geometry=geometry,
        bbox_mupdf=bbox,
        context=context,
        identity_attributes={
            "effective_stroke_width_pdf_pt": point_string(effective_width),
            "fill_only": fill_only,
            "geometry": dict(identity_geometry),
            "item_type": item_type,
            "observed_stroke_width_pdf_pt": observed_string,
        },
        source_evidence={
            "provenance_records": [dict(provenance)],
            "digest_algorithm": None,
            "observed_stroke_width_pdf_pt": observed_string,
            "stroke_width_disposition": disposition,
            "text_extraction_method": None,
            "engine_version": None,
            "claim_status": "Observed",
        },
    )


def extract_vector_primitives(
    page: Any, source_context: SourceIdentityContext, page_1based: int, context: Mapping[str, Any]
) -> list[dict[str, Any]]:
    drawings = page.get_drawings(extended=False)
    if not isinstance(drawings, list):
        raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "drawing API result is not a list")
    records: list[dict[str, Any]] = []
    for drawing_index, drawing in enumerate(drawings):
        if not isinstance(drawing, dict):
            raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"drawing {drawing_index} is not an object")
        sequence = drawing.get("seqno")
        if sequence is not None and (isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0):
            raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"drawing {drawing_index} seqno is invalid")
        observed_width, effective_width, disposition, fill_only = _width_disposition(drawing)
        items = drawing.get("items")
        if not isinstance(items, list):
            raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"drawing {drawing_index} has no item list")
        for item_index, item in enumerate(items):
            if not isinstance(item, tuple) or not item or not isinstance(item[0], str):
                raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", f"drawing {drawing_index} item {item_index} has invalid shape")
            item_type = item[0]
            common = {
                "engine_list_index": drawing_index,
                "drawing_index": drawing_index,
                "drawing_seqno": sequence,
                "item_index": item_index,
            }
            if item_type == "l" and len(item) == 3:
                p0, p1 = item[1], item[2]
                _api_xy(p0)
                _api_xy(p1)
                canonical_endpoints = sorted((point_pair(p0), point_pair(p1)), key=tuple)
                records.append(
                    _vector_record(
                        source_context=source_context,
                        page_1based=page_1based,
                        context=context,
                        item_type="l",
                        geometry={"kind": "line", "p0": canonical_endpoints[0], "p1": canonical_endpoints[1]},
                        identity_geometry=_edge_identity(p0, p1),
                        hull_points=(p0, p1),
                        observed_width=observed_width,
                        effective_width=effective_width,
                        disposition=disposition,
                        fill_only=fill_only,
                        provenance=_provenance(**common),
                    )
                )
                continue
            if item_type == "re" and len(item) == 3:
                orientation = item[2]
                if isinstance(orientation, bool) or not isinstance(orientation, int):
                    raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "rectangle orientation is not an exact integer")
                rect = _api_box(item[1])
                corners = ((rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1))
                parent_bbox = rect_strings(rect)
                for edge_index, (p0, p1) in enumerate(zip(corners, corners[1:] + corners[:1])):
                    canonical_endpoints = sorted((point_pair(p0), point_pair(p1)), key=tuple)
                    records.append(
                        _vector_record(
                            source_context=source_context,
                            page_1based=page_1based,
                            context=context,
                            item_type="re",
                            geometry={
                                "kind": "rectangle-edge",
                                "p0": canonical_endpoints[0],
                                "p1": canonical_endpoints[1],
                                "parent_bbox": parent_bbox,
                                "edge_index": edge_index,
                            },
                            identity_geometry=_edge_identity(p0, p1),
                            hull_points=(p0, p1),
                            observed_width=observed_width,
                            effective_width=effective_width,
                            disposition=disposition,
                            fill_only=fill_only,
                            provenance=_provenance(edge_index=edge_index, **common),
                        )
                    )
                continue
            if item_type == "qu" and len(item) == 2:
                quad = item[1]
                try:
                    corners = (quad.ul, quad.ur, quad.lr, quad.ll)
                except AttributeError as exc:
                    raise VWStop("VW-VECTOR-GEOMETRY-UNREAD", "quad lacks ul/ur/lr/ll points") from exc
                for point in corners:
                    _api_xy(point)
                parent_vertices = [point_pair(point) for point in corners]
                for edge_index, (p0, p1) in enumerate(zip(corners, corners[1:] + corners[:1])):
                    canonical_endpoints = sorted((point_pair(p0), point_pair(p1)), key=tuple)
                    records.append(
                        _vector_record(
                            source_context=source_context,
                            page_1based=page_1based,
                            context=context,
                            item_type="qu",
                            geometry={
                                "kind": "quad-edge",
                                "p0": canonical_endpoints[0],
                                "p1": canonical_endpoints[1],
                                "parent_vertices": parent_vertices,
                                "edge_index": edge_index,
                            },
                            identity_geometry=_edge_identity(p0, p1),
                            hull_points=(p0, p1),
                            observed_width=observed_width,
                            effective_width=effective_width,
                            disposition=disposition,
                            fill_only=fill_only,
                            provenance=_provenance(edge_index=edge_index, **common),
                        )
                    )
                continue
            if item_type == "c" and len(item) == 5:
                p0, c1, c2, p1 = item[1:]
                for point in (p0, c1, c2, p1):
                    _api_xy(point)
                identity_geometry = {"points": [point_pair(point) for point in (p0, c1, c2, p1)]}
                records.append(
                    _vector_record(
                        source_context=source_context,
                        page_1based=page_1based,
                        context=context,
                        item_type="c",
                        geometry={
                            "kind": "cubic-curve",
                            "p0": point_pair(p0),
                            "c1": point_pair(c1),
                            "c2": point_pair(c2),
                            "p1": point_pair(p1),
                        },
                        identity_geometry=identity_geometry,
                        hull_points=(p0, c1, c2, p1),
                        observed_width=observed_width,
                        effective_width=effective_width,
                        disposition=disposition,
                        fill_only=fill_only,
                        provenance=_provenance(**common),
                    )
                )
                continue
            raise VWStop(
                "VW-VECTOR-GEOMETRY-UNREAD",
                f"unsupported drawing item {item_type!r} at drawing {drawing_index} item {item_index}",
            )
    return _deduplicate_primitives(records)


def render_page_rgb(page: Any) -> tuple[bytes, int, int, dict[str, Any]]:
    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(SCALE_NUMERATOR / SCALE_DENOMINATOR, SCALE_NUMERATOR / SCALE_DENOMINATOR),
        colorspace=pymupdf.csRGB,
        alpha=False,
        annots=True,
        clip=page.rect,
    )
    width, height = int(pixmap.width), int(pixmap.height)
    if int(pixmap.x) != 0 or int(pixmap.y) != 0:
        raise VWStop("VW-RENDER-UNREAD", f"pixmap origin is ({pixmap.x},{pixmap.y}), expected (0,0)")
    pixels = width * height
    if width < 1 or height < 1 or width > MAX_RENDER_AXIS_PX or height > MAX_RENDER_AXIS_PX:
        raise VWStop("VW-RENDER-UNREAD", "render axis outside packet bounds")
    if pixels < 1 or pixels > MAX_RENDER_PIXELS:
        raise VWStop("VW-RENDER-UNREAD", f"render pixel count {pixels} outside packet bounds")
    raw = bytes(pixmap.samples)
    if int(pixmap.n) != 3 or bool(pixmap.alpha) or int(pixmap.stride) != width * 3 or len(raw) != pixels * 3:
        raise VWStop("VW-RENDER-UNREAD", "render is not tightly packed alpha-free RGB8")
    return (
        raw,
        width,
        height,
        {
            "status": "measured",
            "width_px": width,
            "height_px": height,
            "valid_page_pixels": pixels,
            "rgb_bytes": len(raw),
            "rgb_sha256": sha256_bytes(raw),
            "encoding": "RGB8-row-major-no-padding",
            "reason_codes": [],
        },
    )


def rgb_slice(raw: bytes, page_width: int, bbox: Sequence[int]) -> bytes:
    if isinstance(page_width, bool) or not isinstance(page_width, int) or page_width < 1:
        raise VWStop("VW-CROP-BOUNDS", "invalid page width")
    row_bytes = page_width * 3
    if len(raw) < row_bytes or len(raw) % row_bytes:
        raise VWStop("VW-CROP-BOUNDS", "page RGB byte count is inconsistent with width")
    page_height = len(raw) // row_bytes
    x0, y0, x1, y1 = map(int, bbox)
    if not (0 <= x0 < x1 <= page_width and 0 <= y0 < y1 <= page_height):
        raise VWStop("VW-CROP-BOUNDS", f"invalid RGB slice bbox {bbox}")
    return b"".join(raw[y * row_bytes + x0 * 3 : y * row_bytes + x1 * 3] for y in range(y0, y1))


def populate_tile_hashes(raw: bytes, width: int, height: int, page_1based: int) -> list[dict[str, Any]]:
    tiles = make_tiles(page_1based, width, height)
    for tile in tiles:
        tile_raw = rgb_slice(raw, width, tile["bbox_px_half_open"])
        tile["rgb_bytes"] = len(tile_raw)
        tile["rgb_sha256"] = sha256_bytes(tile_raw)
    return tiles


def box_gap(left: Box, right: Box) -> int:
    x_gap = max(0, int(left.x0) - int(right.x1), int(right.x0) - int(left.x1))
    y_gap = max(0, int(left.y0) - int(right.y1), int(right.y0) - int(left.y1))
    return max(x_gap, y_gap)


def graph_edge_count(primitives: Sequence[Mapping[str, Any]], gap: int) -> int:
    count = 0
    for left_index, left in enumerate(primitives):
        left_box = _box(left["bbox_px_half_open"])
        for right in primitives[left_index + 1 :]:
            if box_gap(left_box, _box(right["bbox_px_half_open"])) <= gap:
                count += 1
    return count


def _evidence(rule_id: str, ids: Sequence[str], measurements: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "source_primitive_ids": sorted(set(ids)),
        "claim_status": "Inferred",
        "semantic_truth_status": "UNREAD",
        "measurements": dict(measurements),
    }


def point_to_render_int(point: Any, rotation_matrix: Any) -> tuple[int, int]:
    x, y = _xy(point)
    x, y = _transform_xy(x, y, rotation_matrix)
    scale = Decimal(SCALE_NUMERATOR) / Decimal(SCALE_DENOMINATOR)
    return (
        int((Decimal(str(x)) * scale).to_integral_value(rounding=ROUND_HALF_EVEN)),
        int((Decimal(str(y)) * scale).to_integral_value(rounding=ROUND_HALF_EVEN)),
    )


def _interval_gap(left: tuple[int, int], right: tuple[int, int]) -> int:
    return max(0, left[0] - right[1], right[0] - left[1])


def _merge_table_tracks(segments: Sequence[Mapping[str, Any]], orientation: str) -> list[dict[str, Any]]:
    ordered = sorted(segments, key=lambda item: item["primitive_id"])
    parent = list(range(len(ordered)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            if abs(int(ordered[left]["axis_px"]) - int(ordered[right]["axis_px"])) <= TABLE_MERGE_AXIS_TOLERANCE_PX and _interval_gap(
                tuple(ordered[left]["extent"]), tuple(ordered[right]["extent"])
            ) <= TABLE_MERGE_GAP_PX:
                union(left, right)
    groups: dict[int, list[Mapping[str, Any]]] = {}
    for index, segment in enumerate(ordered):
        groups.setdefault(find(index), []).append(segment)
    tracks: list[dict[str, Any]] = []
    for members in groups.values():
        endpoint_axes: list[int] = []
        for member in members:
            endpoint_axes.extend(member["endpoint_axes"])
        axis = int(
            (Decimal(sum(endpoint_axes)) / Decimal(len(endpoint_axes))).to_integral_value(rounding=ROUND_HALF_EVEN)
        )
        tracks.append(
            {
                "axis_px": axis,
                "extent_end_px": max(int(member["extent"][1]) for member in members),
                "extent_start_px": min(int(member["extent"][0]) for member in members),
                "member_primitive_ids": sorted({str(member["primitive_id"]) for member in members}),
            }
        )
    return sorted(tracks, key=lambda item: (item["axis_px"], item["extent_start_px"], item["extent_end_px"], item["member_primitive_ids"]))


def table_candidate_evidence(
    vector_component: Sequence[Mapping[str, Any]],
    text_primitives: Sequence[Mapping[str, Any]],
    rotation_matrix: Any,
    parent_stroke_cluster_id: str,
) -> dict[str, Any] | None:
    segments: list[dict[str, Any]] = []
    for primitive in vector_component:
        geometry = primitive["geometry"]
        if geometry["kind"] not in ("line", "rectangle-edge", "quad-edge"):
            continue
        p0 = point_to_render_int(geometry["p0"], rotation_matrix)
        p1 = point_to_render_int(geometry["p1"], rotation_matrix)
        dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
        horizontal = dy <= TABLE_AXIS_TOLERANCE_PX and dx >= TABLE_MIN_SEGMENT_EXTENT_PX
        vertical = dx <= TABLE_AXIS_TOLERANCE_PX and dy >= TABLE_MIN_SEGMENT_EXTENT_PX
        if horizontal == vertical:
            continue
        if horizontal:
            segments.append(
                {
                    "primitive_id": primitive["primitive_id"],
                    "orientation": "horizontal",
                    "axis_px": int((Decimal(p0[1] + p1[1]) / Decimal(2)).to_integral_value(rounding=ROUND_HALF_EVEN)),
                    "endpoint_axes": [p0[1], p1[1]],
                    "extent": [min(p0[0], p1[0]), max(p0[0], p1[0])],
                }
            )
        else:
            segments.append(
                {
                    "primitive_id": primitive["primitive_id"],
                    "orientation": "vertical",
                    "axis_px": int((Decimal(p0[0] + p1[0]) / Decimal(2)).to_integral_value(rounding=ROUND_HALF_EVEN)),
                    "endpoint_axes": [p0[0], p1[0]],
                    "extent": [min(p0[1], p1[1]), max(p0[1], p1[1])],
                }
            )
    horizontal_tracks = _merge_table_tracks([item for item in segments if item["orientation"] == "horizontal"], "horizontal")
    vertical_tracks = _merge_table_tracks([item for item in segments if item["orientation"] == "vertical"], "vertical")
    if len(horizontal_tracks) < TABLE_MIN_HORIZONTAL_TRACKS or len(vertical_tracks) < TABLE_MIN_VERTICAL_TRACKS:
        return None

    def intersects(horizontal: Mapping[str, Any], vertical: Mapping[str, Any]) -> bool:
        return (
            horizontal["extent_start_px"] - TABLE_AXIS_TOLERANCE_PX
            <= vertical["axis_px"]
            <= horizontal["extent_end_px"] + TABLE_AXIS_TOLERANCE_PX
            and vertical["extent_start_px"] - TABLE_AXIS_TOLERANCE_PX
            <= horizontal["axis_px"]
            <= vertical["extent_end_px"] + TABLE_AXIS_TOLERANCE_PX
        )

    intersection_pairs = {
        (h_index, v_index)
        for h_index, horizontal in enumerate(horizontal_tracks)
        for v_index, vertical in enumerate(vertical_tracks)
        if intersects(horizontal, vertical)
    }
    possible = len(horizontal_tracks) * len(vertical_tracks)
    observed = len(intersection_pairs)
    fraction_decimal = Decimal(observed) / Decimal(possible)
    if fraction_decimal < Decimal("0.80"):
        return None
    extreme_counts = {
        "horizontal_max": sum((len(horizontal_tracks) - 1, v) in intersection_pairs for v in range(len(vertical_tracks))),
        "horizontal_min": sum((0, v) in intersection_pairs for v in range(len(vertical_tracks))),
        "vertical_max": sum((h, len(vertical_tracks) - 1) in intersection_pairs for h in range(len(horizontal_tracks))),
        "vertical_min": sum((h, 0) in intersection_pairs for h in range(len(horizontal_tracks))),
    }
    if any(value < 2 for value in extreme_counts.values()):
        return None

    closed_cells: list[dict[str, Any]] = []
    occupied_ids: list[str] = []
    occupied_rows: set[int] = set()
    occupied_columns: set[int] = set()
    for row in range(len(horizontal_tracks) - 1):
        for column in range(len(vertical_tracks) - 1):
            corners = ((row, column), (row, column + 1), (row + 1, column), (row + 1, column + 1))
            if not all(corner in intersection_pairs for corner in corners):
                continue
            bbox = [
                vertical_tracks[column]["axis_px"],
                horizontal_tracks[row]["axis_px"],
                vertical_tracks[column + 1]["axis_px"],
                horizontal_tracks[row + 1]["axis_px"],
            ]
            if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                continue
            text_ids: list[str] = []
            for text in text_primitives:
                text_box = _box(text["bbox_px_half_open"])
                centroid_x = (Decimal(int(text_box.x0)) + Decimal(int(text_box.x1))) / Decimal(2)
                centroid_y = (Decimal(int(text_box.y0)) + Decimal(int(text_box.y1))) / Decimal(2)
                if Decimal(bbox[0]) <= centroid_x < Decimal(bbox[2]) and Decimal(bbox[1]) <= centroid_y < Decimal(bbox[3]):
                    text_ids.append(text["primitive_id"])
            text_ids = sorted(set(text_ids))
            cell_id = f"r{row:06d}-c{column:06d}"
            occupied = bool(text_ids)
            if occupied:
                occupied_ids.append(cell_id)
                occupied_rows.add(row)
                occupied_columns.add(column)
            closed_cells.append(
                {
                    "bbox_px_half_open": bbox,
                    "cell_id": cell_id,
                    "column_index_0based": column,
                    "occupied": occupied,
                    "row_index_0based": row,
                    "text_primitive_ids": text_ids,
                }
            )
    if (
        len(closed_cells) < TABLE_MIN_CLOSED_CELLS
        or len(occupied_ids) < TABLE_MIN_TEXT_CELLS
        or len(occupied_rows) < TABLE_MIN_TEXT_ROWS
        or len(occupied_columns) < TABLE_MIN_TEXT_COLUMNS
    ):
        return None
    measurements = {
        "parent_stroke_cluster_id": parent_stroke_cluster_id,
        "eligible_segment_ids": sorted({item["primitive_id"] for item in segments}),
        "horizontal_tracks": horizontal_tracks,
        "vertical_tracks": vertical_tracks,
        "possible_intersections": possible,
        "observed_intersections": observed,
        "intersection_fraction": normalized_string(fraction_decimal),
        "extreme_support_intersection_counts": extreme_counts,
        "closed_cell_count": len(closed_cells),
        "closed_cells": closed_cells,
        "occupied_cell_ids": sorted(occupied_ids),
        "occupied_text_cells": len(occupied_ids),
        "occupied_text_rows": len(occupied_rows),
        "occupied_text_columns": len(occupied_columns),
        "grid_bbox_px_half_open": [
            vertical_tracks[0]["axis_px"],
            horizontal_tracks[0]["axis_px"],
            vertical_tracks[-1]["axis_px"],
            horizontal_tracks[-1]["axis_px"],
        ],
    }
    return _evidence(RULE_IDS["table"], measurements["eligible_segment_ids"], measurements)


def _intersecting_tiles(bbox: Box, tiles: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        tile["tile_id"]
        for tile in tiles
        if bbox.intersect(_box(tile["bbox_px_half_open"])) is not None
    )


def edge_recovery(
    bbox: Box,
    tiles: Sequence[Mapping[str, Any]],
    width: int,
    height: int,
    render_rgb: bytes,
) -> dict[str, Any]:
    x_edges = sorted({int(tile["bbox_px_half_open"][0]) for tile in tiles} | {int(tile["bbox_px_half_open"][2]) for tile in tiles})
    y_edges = sorted({int(tile["bbox_px_half_open"][1]) for tile in tiles} | {int(tile["bbox_px_half_open"][3]) for tile in tiles})
    touches: list[dict[str, Any]] = []

    def add(axis: str, edge: int, lo: int, hi: int) -> None:
        if edge in (0, width if axis == "x" else height) or not (lo <= edge <= hi):
            return
        if lo == edge:
            relation, direction = "equals-min-boundary", "negative"
        elif hi == edge:
            relation, direction = "equals-max-boundary", "positive"
        else:
            relation, direction = "straddles", "both"
        touches.append({"axis": axis, "coordinate_px": edge, "relation": relation, "neighbor_direction": direction})

    for edge in x_edges:
        add("x", edge, int(bbox.x0), int(bbox.x1))
    for edge in y_edges:
        add("y", edge, int(bbox.y0), int(bbox.y1))
    physical = bbox.x0 == 0 or bbox.y0 == 0 or bbox.x1 == width or bbox.y1 == height
    unique_touches = {canonical_json_bytes(item): item for item in touches}
    relation_rank = {"equals-min-boundary": 0, "equals-max-boundary": 1, "straddles": 2}
    direction_rank = {"negative": 0, "positive": 1, "both": 2}
    touches = sorted(
        unique_touches.values(),
        key=lambda item: (
            0 if item["axis"] == "x" else 1,
            item["coordinate_px"],
            relation_rank[item["relation"]],
            direction_rank[item["neighbor_direction"]],
        ),
    )
    if not touches:
        return {
            "status": "measured",
            "touched_internal_edges": [],
            "recovery_tile_ids": [],
            "recovery_bbox_px_half_open": None,
            "recovery_rgb_bytes": None,
            "recovery_rgb_sha256": None,
            "candidate_strictly_contained": False,
            "physical_page_edge_exception": physical,
            "boundary_resolution": "not-required",
            "claim_status": "Verified-self",
            "reason_codes": [],
        }

    intersecting = [tile for tile in tiles if bbox.intersect(_box(tile["bbox_px_half_open"])) is not None]
    if not intersecting:
        raise VWStop("VW-TILE-GAP", "candidate has no intersecting base tile")
    x_starts = sorted({int(tile["bbox_px_half_open"][0]) for tile in tiles})
    y_starts = sorted({int(tile["bbox_px_half_open"][1]) for tile in tiles})

    def adjacent(starts: Sequence[int], edge: int) -> set[int]:
        index = bisect.bisect_left(starts, edge)
        result: set[int] = set()
        if index > 0:
            result.add(starts[index - 1])
        if index < len(starts):
            result.add(starts[index])
        return result

    neighbor_x: set[int] = set()
    neighbor_y: set[int] = set()
    for touch in touches:
        if touch["axis"] == "x":
            neighbor_x.update(adjacent(x_starts, int(touch["coordinate_px"])))
        else:
            neighbor_y.update(adjacent(y_starts, int(touch["coordinate_px"])))
    intersecting_x = {int(tile["bbox_px_half_open"][0]) for tile in intersecting}
    intersecting_y = {int(tile["bbox_px_half_open"][1]) for tile in intersecting}
    selected_by_id = {str(tile["tile_id"]): tile for tile in intersecting}
    for tile in tiles:
        x0, y0 = int(tile["bbox_px_half_open"][0]), int(tile["bbox_px_half_open"][1])
        if (x0 in neighbor_x and y0 in intersecting_y) or (y0 in neighbor_y and x0 in intersecting_x):
            selected_by_id[str(tile["tile_id"])] = tile
    selected = sorted(
        selected_by_id.values(),
        key=lambda tile: (tile["bbox_px_half_open"][1], tile["bbox_px_half_open"][0], tile["tile_id"]),
    )
    recovery_box = box_union(_box(tile["bbox_px_half_open"]) for tile in selected).intersect(Box(0, 0, width, height))
    if recovery_box is None:
        raise VWStop("VW-TILE-GAP", "recovery crop is outside the page")
    strict = recovery_box.contains(bbox) and (
        recovery_box.x0 < bbox.x0 or recovery_box.y0 < bbox.y0 or recovery_box.x1 > bbox.x1 or recovery_box.y1 > bbox.y1
    )
    if not strict and not physical:
        raise VWStop("VW-TILE-GAP", "recovery tile union does not strictly contain candidate")
    recovery_raw = rgb_slice(render_rgb, width, recovery_box.integer_tuple())
    return {
        "status": "measured",
        "touched_internal_edges": touches,
        "recovery_tile_ids": [str(tile["tile_id"]) for tile in selected],
        "recovery_bbox_px_half_open": list(recovery_box.integer_tuple()),
        "recovery_rgb_bytes": len(recovery_raw),
        "recovery_rgb_sha256": sha256_bytes(recovery_raw),
        "candidate_strictly_contained": strict,
        "physical_page_edge_exception": physical,
        "boundary_resolution": "whole-page-recrop",
        "claim_status": "Verified-self",
        "reason_codes": [],
    }


def captured_text_for_candidate(
    bbox: Box,
    text_primitives: Sequence[Mapping[str, Any]],
    ephemeral_text: Mapping[str, bytes],
) -> dict[str, Any]:
    selected = sorted(
        (
            primitive
            for primitive in text_primitives
            if bbox.intersect(_box(primitive["bbox_px_half_open"])) is not None
        ),
        key=lambda item: item["primitive_id"],
    )
    aggregate = bytearray()
    block_bytes = 0
    codepoints = 0
    ids: list[str] = []
    for primitive in selected:
        primitive_key = primitive["primitive_id"]
        raw = ephemeral_text[primitive_key]
        aggregate.extend(primitive_key.encode("utf-8"))
        aggregate.extend(b"\0")
        aggregate.extend(struct.pack(">Q", len(raw)))
        aggregate.extend(raw)
        ids.append(primitive_key)
        block_bytes += len(raw)
        codepoints += len(raw.decode("utf-8"))
    return {
        "status": "measured",
        "kind": "native" if ids else "empty",
        "method": CAPTURED_TEXT_METHOD,
        "source_text_primitive_ids": ids,
        "utf8_sha256": sha256_bytes(bytes(aggregate)),
        "utf8_bytes": block_bytes,
        "unicode_codepoints": codepoints,
        "persistence": "ephemeral-regenerate-from-source",
        "claim_status": "Verified-self",
        "semantic_truth_status": "UNREAD",
        "reason_codes": [],
    }


def _candidate_record(
    *,
    source_context: SourceIdentityContext,
    page_1based: int,
    configuration_sha256: str,
    classes: Sequence[str],
    evidence: Sequence[Mapping[str, Any]],
    primitives: Sequence[Mapping[str, Any]],
    tiles: Sequence[Mapping[str, Any]],
    render_rgb: bytes,
    width: int,
    height: int,
    text_primitives: Sequence[Mapping[str, Any]],
    ephemeral_text: Mapping[str, bytes],
) -> dict[str, Any]:
    ordered_classes = [name for name in CLASS_ORDER if name in set(classes)]
    ordered_evidence = sorted(evidence, key=lambda item: CLASS_RANK[next(name for name, rule in RULE_IDS.items() if rule == item["rule_id"])])
    mupdf_bbox = box_union(_box(item["bbox_mupdf_unrotated_pt"]) for item in primitives)
    pdf_bbox = box_union(_box(item["bbox_pdf_pt"]) for item in primitives)
    px_bbox = box_union(_box(item["bbox_px_half_open"]) for item in primitives)
    source_ids = sorted({item["primitive_id"] for item in primitives})
    record: dict[str, Any] = {
        "source_sha256": source_context.sha256,
        "page_1based": page_1based,
        "classes": ordered_classes,
        "class_basis": [RULE_IDS[name] for name in ordered_classes],
        "class_evidence": [dict(item) for item in ordered_evidence],
        "claim_status": "Inferred",
        "semantic_truth_status": "UNREAD",
        "bbox_mupdf_unrotated_pt": rect_strings(mupdf_bbox),
        "bbox_pdf_pt": rect_strings(pdf_bbox),
        "bbox_px_half_open": list(px_bbox.integer_tuple()),
        "bbox_normalized": normalized_rect_strings(px_bbox, width, height),
        "config_sha256": configuration_sha256,
        "source_primitive_ids": source_ids,
        "intersecting_tile_ids": _intersecting_tiles(px_bbox, tiles),
        "edge_recovery": edge_recovery(px_bbox, tiles, width, height, render_rgb),
    }
    crop_raw = rgb_slice(render_rgb, width, record["bbox_px_half_open"])
    record["crop"] = {
        "status": "measured",
        "encoding": "RGB8-row-major-no-padding",
        "width_px": int(px_bbox.width),
        "height_px": int(px_bbox.height),
        "rgb_bytes": len(crop_raw),
        "rgb_sha256": sha256_bytes(crop_raw),
        "persistence": "ephemeral-regenerate-from-source",
        "reason_codes": [],
    }
    record["captured_text"] = captured_text_for_candidate(px_bbox, text_primitives, ephemeral_text)
    record["candidate_id"] = candidate_id(record)
    record.pop("source_sha256")
    record.pop("page_1based")
    record.pop("config_sha256")
    return record


def _component_candidate_id(
    *,
    source_context: SourceIdentityContext,
    page_1based: int,
    configuration_sha256: str,
    classes: Sequence[str],
    primitives: Sequence[Mapping[str, Any]],
) -> str:
    return candidate_id(
        {
            "source_sha256": source_context.sha256,
            "page_1based": page_1based,
            "bbox_pdf_pt": rect_strings(box_union(_box(item["bbox_pdf_pt"]) for item in primitives)),
            "bbox_px_half_open": list(
                box_union(_box(item["bbox_px_half_open"]) for item in primitives).integer_tuple()
            ),
            "classes": [name for name in CLASS_ORDER if name in set(classes)],
            "config_sha256": configuration_sha256,
            "source_primitive_ids": sorted({str(item["primitive_id"]) for item in primitives}),
        }
    )


def build_candidates(
    *,
    source_context: SourceIdentityContext,
    page_1based: int,
    configuration_sha256: str,
    primitives: Sequence[Mapping[str, Any]],
    text_ephemeral: Mapping[str, bytes],
    tiles: Sequence[Mapping[str, Any]],
    render_rgb: bytes,
    width: int,
    height: int,
    rotation_matrix: Any,
    families: frozenset[str] = frozenset(("raster", "vector", "text")),
    enable_table: bool = True,
) -> list[dict[str, Any]]:
    raster = [item for item in primitives if item["kind"] == "raster"]
    vector = [item for item in primitives if item["kind"] == "vector"]
    text = [item for item in primitives if item["kind"] == "text"]
    eligible_table_text = [
        item
        for item in text
        if any(not character.isspace() for character in text_ephemeral[item["primitive_id"]].decode("utf-8"))
    ]
    candidates: list[dict[str, Any]] = []

    for component in (connected_components(raster, bbox_key="bbox_px_half_open", gap=RASTER_COMPONENT_GAP_PX) if "raster" in families else []):
        ids = sorted(item["primitive_id"] for item in component)
        occurrences = sum(len(item["source_evidence"]["provenance_records"]) for item in component)
        classes = ["raster"]
        evidence = [_evidence(RULE_IDS["raster"], ids, {"image_occurrence_count": occurrences})]
        union_bbox = box_union(_box(item["bbox_px_half_open"]) for item in component)
        union_area = exact_union_area([_box(item["bbox_px_half_open"]) for item in component])
        fraction = Decimal(union_area) / Decimal(width * height)
        insets = [
            Decimal(int(union_bbox.x0)) / Decimal(width),
            Decimal(int(union_bbox.y0)) / Decimal(height),
            Decimal(width - int(union_bbox.x1)) / Decimal(width),
            Decimal(height - int(union_bbox.y1)) / Decimal(height),
        ]
        if fraction >= Decimal("0.90") and all(value <= Decimal("0.05") for value in insets):
            classes.append("scan-component")
            evidence.append(
                _evidence(
                    RULE_IDS["scan-component"],
                    ids,
                    {
                        "raster_union_pixels": union_area,
                        "valid_page_pixels": width * height,
                        "page_union_fraction": normalized_string(fraction),
                        "edge_insets_normalized": [normalized_string(value) for value in insets],
                    },
                )
            )
        candidates.append(
            _candidate_record(
                source_context=source_context,
                page_1based=page_1based,
                configuration_sha256=configuration_sha256,
                classes=classes,
                evidence=evidence,
                primitives=component,
                tiles=tiles,
                render_rgb=render_rgb,
                width=width,
                height=height,
                text_primitives=text,
                ephemeral_text=text_ephemeral,
            )
        )

    for component in (connected_components(vector, bbox_key="bbox_px_half_open", gap=2) if "vector" in families else []):
        ids = sorted(item["primitive_id"] for item in component)
        classes = ["vector"]
        evidence = [
            _evidence(
                RULE_IDS["vector"],
                ids,
                {"supported_primitive_count": len(ids), "unknown_item_count": 0},
            )
        ]
        edge_count = graph_edge_count(component, 2)
        if len(ids) >= 2:
            classes.append("stroke-cluster")
            evidence.append(
                _evidence(
                    RULE_IDS["stroke-cluster"],
                    ids,
                    {
                        "component_size": len(ids),
                        "graph_edge_count": edge_count,
                        "maximum_undilated_gap_px": 2,
                    },
                )
            )
        base = _candidate_record(
            source_context=source_context,
            page_1based=page_1based,
            configuration_sha256=configuration_sha256,
            classes=classes,
            evidence=evidence,
            primitives=component,
            tiles=tiles,
            render_rgb=render_rgb,
            width=width,
            height=height,
            text_primitives=text,
            ephemeral_text=text_ephemeral,
        )
        if "stroke-cluster" in classes and enable_table:
            table_evidence = table_candidate_evidence(component, eligible_table_text, rotation_matrix, base["candidate_id"])
            if table_evidence is not None:
                classes.append("table")
                final_parent_id = _component_candidate_id(
                    source_context=source_context,
                    page_1based=page_1based,
                    configuration_sha256=configuration_sha256,
                    classes=classes,
                    primitives=component,
                )
                table_evidence["measurements"]["parent_stroke_cluster_id"] = final_parent_id
                evidence.append(table_evidence)
                base = _candidate_record(
                    source_context=source_context,
                    page_1based=page_1based,
                    configuration_sha256=configuration_sha256,
                    classes=classes,
                    evidence=evidence,
                    primitives=component,
                    tiles=tiles,
                    render_rgb=render_rgb,
                    width=width,
                    height=height,
                    text_primitives=text,
                    ephemeral_text=text_ephemeral,
                )
                if base["candidate_id"] != final_parent_id:
                    raise VWStop("VW-IDENTITY", "table parent candidate identity did not stabilize")
        candidates.append(base)

    for primitive in (text if "text" in families else []):
        raw = text_ephemeral[primitive["primitive_id"]].decode("utf-8")
        count = sum(not char.isspace() for char in raw)
        if count == 0:
            continue
        candidates.append(
            _candidate_record(
                source_context=source_context,
                page_1based=page_1based,
                configuration_sha256=configuration_sha256,
                classes=["text-block"],
                evidence=[
                    _evidence(
                        RULE_IDS["text-block"],
                        [primitive["primitive_id"]],
                        {"nonwhitespace_codepoints": count},
                    )
                ],
                primitives=[primitive],
                tiles=tiles,
                render_rgb=render_rgb,
                width=width,
                height=height,
                text_primitives=text,
                ephemeral_text=text_ephemeral,
            )
        )
    return sorted(candidates, key=lambda item: item["candidate_id"])


def _base_family(candidate: Mapping[str, Any]) -> str:
    classes = candidate["classes"]
    matches = [name for name in ("raster", "vector", "text-block") if name in classes]
    if len(matches) != 1:
        raise VWStop("VW-IDENTITY", f"candidate does not have exactly one base family: {classes}")
    return matches[0]


def build_relationships(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    ordered = sorted(candidates, key=lambda item: item["candidate_id"])
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            if _base_family(left) == _base_family(right):
                continue
            left_box, right_box = _box(left["bbox_px_half_open"]), _box(right["bbox_px_half_open"])
            intersection = left_box.intersect(right_box)
            if intersection is None:
                continue
            equal = left_box.integer_tuple() == right_box.integer_tuple()
            if equal:
                source, target, kind = left, right, "coincident"
            elif left_box.contains(right_box):
                source, target, kind = left, right, "contains"
            elif right_box.contains(left_box):
                source, target, kind = right, left, "contains"
            else:
                source, target, kind = left, right, "intersects"
            area = int(intersection.area)
            if area < 1:
                continue
            source_box = _box(source["bbox_px_half_open"])
            target_box = _box(target["bbox_px_half_open"])
            record: dict[str, Any] = {
                "source_candidate_id": source["candidate_id"],
                "target_candidate_id": target["candidate_id"],
                "kind": kind,
                "intersection_area_px": area,
                "source_overlap_fraction": normalized_string(Decimal(area) / Decimal(int(source_box.area))),
                "target_overlap_fraction": normalized_string(Decimal(area) / Decimal(int(target_box.area))),
                "claim_status": "Verified-self",
            }
            record["relationship_id"] = relationship_id(record)
            relationships.append(record)
    return sorted(
        relationships,
        key=lambda item: (item["source_candidate_id"], item["target_candidate_id"], item["kind"]),
    )


def class_procedures(
    candidates: Sequence[Mapping[str, Any]],
    unread_by_class: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    unread_by_class = {} if unread_by_class is None else dict(unread_by_class)
    return [
        (
            {
                "class": name,
                "status": "UNREAD",
                "candidate_count": None,
                "blocking": True,
                "reason_codes": [unread_by_class[name]],
                "semantic_truth_status": "UNREAD",
            }
            if name in unread_by_class
            else {
                "class": name,
                "status": "measured",
                "candidate_count": sum(name in candidate["classes"] for candidate in candidates),
                "blocking": False,
                "reason_codes": [],
                "semantic_truth_status": "UNREAD",
            }
        )
        for name in CLASS_ORDER
    ]


def unread_record(reason_code: str, scope: str, detail_code: str, *, blocking: bool = True) -> dict[str, Any]:
    if scope not in SCOPE_ENUM:
        raise VWStop("VW-PRIVACY", "UNREAD scope is not packet-licensed")
    if detail_code not in DETAIL_ENUM:
        raise VWStop("VW-PRIVACY", "UNREAD detail code is not packet-licensed")
    return {
        "reason_code": reason_code,
        "scope": scope,
        "blocking": blocking,
        "detail_code": detail_code,
        "evidence_sha256": None,
    }


def unread_coverage(reason_code: str) -> dict[str, Any]:
    return {
        "status": "UNREAD",
        "numerator_name": "valid rendered page pixels covered by at least one declared base tile",
        "numerator": None,
        "denominator_name": "valid rendered page pixels on attempted readable pages",
        "denominator": None,
        "value": None,
        "conditions": {
            "render_dpi": DPI,
            "tile_size_px": TILE_SIZE,
            "stride_px": TILE_STRIDE,
            "readable_pages": 0,
            "unread_pages": 1,
        },
        "reason_codes": [reason_code],
    }


def unread_page(page_1based: int, reason_code: str, detail_code: str | None = None) -> dict[str, Any]:
    unread = unread_record(reason_code, "page", detail_code or DETAIL_BY_REASON[reason_code])
    return {
        "page_1based": page_1based,
        "status": "UNREAD",
        "media_box_mupdf_pt": None,
        "crop_box_mupdf_pt": None,
        "media_box_pdf_user_space_pt": None,
        "crop_box_pdf_user_space_pt": None,
        "rotation_degrees": None,
        "render": {
            "status": "UNREAD",
            "width_px": None,
            "height_px": None,
            "valid_page_pixels": None,
            "rgb_bytes": None,
            "rgb_sha256": None,
            "encoding": "RGB8-row-major-no-padding",
            "reason_codes": [reason_code],
        },
        "tiles": [],
        "tile_union": unread_coverage(reason_code),
        "primitive_facts": [],
        "primitive_census": {
            "status": "UNREAD",
            "image_occurrences": None,
            "text_blocks": None,
            "vector_primitives": None,
            "reason_codes": [reason_code],
        },
        "region_candidates": [],
        "relationships": [],
        "class_procedures": [
            {
                "class": name,
                "status": "UNREAD",
                "candidate_count": None,
                "blocking": True,
                "reason_codes": [reason_code],
                "semantic_truth_status": "UNREAD",
            }
            for name in CLASS_ORDER
        ],
        "unreads": [unread],
    }


@dataclass
class PageCapture:
    report: dict[str, Any]
    render_rgb: bytes = field(repr=False)
    ephemeral_text: dict[str, bytes] = field(repr=False)

    def clear(self) -> None:
        self.render_rgb = b""
        self.ephemeral_text.clear()


def capture_page(
    page: Any,
    *,
    page_1based: int,
    source_observation: Mapping[str, Any],
    configuration_sha256: str,
) -> PageCapture:
    if configuration_sha256 != EXPECTED_CONFIG_SHA256:
        raise VWStop("VW-CONFIG-HASH", "capture invoked with non-frozen configuration hash")
    source_context = measured_source_identity(source_observation)
    render_rgb, width, height, render = render_page_rgb(page)
    context = page_coordinate_context(page, width, height)
    tiles = populate_tile_hashes(render_rgb, width, height, page_1based)
    tile_union = check_tile_union(width, height, tiles)
    unreads: list[dict[str, Any]] = []
    unread_by_class: dict[str, str] = {}

    def block(reason: str, classes: Sequence[str]) -> None:
        for class_name in classes:
            unread_by_class.setdefault(class_name, reason)
            scope = {
                "raster": "raster-procedure",
                "scan-component": "scan-component-procedure",
                "vector": "vector-procedure",
                "stroke-cluster": "stroke-cluster-procedure",
                "text-block": "text-procedure",
                "table": "table-procedure",
            }[class_name]
            unreads.append(unread_record(reason, scope, DETAIL_BY_REASON.get(reason, "procedural-unread")))

    raster: list[dict[str, Any]] = []
    vector: list[dict[str, Any]] = []
    text: list[dict[str, Any]] = []
    ephemeral_text: dict[str, bytes] = {}
    image_occurrences = 0
    text_type_census: dict[str, int] = {}
    primitive_failures = False
    try:
        raster, image_occurrences = extract_raster_primitives(page, source_context, page_1based, context)
    except VWStop as exc:
        primitive_failures = True
        block(exc.reason, ("raster", "scan-component"))
    try:
        text, ephemeral_text, text_type_census = extract_text_primitives(page, source_context, page_1based, context)
    except VWStop as exc:
        primitive_failures = True
        # Candidate overlap text is a required candidate field. If native text cannot
        # be observed, no structural candidate procedure can complete truthfully.
        block(exc.reason, CLASS_ORDER)
    try:
        vector = extract_vector_primitives(page, source_context, page_1based, context)
    except VWStop as exc:
        primitive_failures = True
        block(exc.reason, ("vector", "stroke-cluster", "table"))
    primitives = _deduplicate_primitives([*raster, *vector, *text])
    candidates: list[dict[str, Any]] = []

    def build_family(family: str, affected: Sequence[str]) -> None:
        if any(name in unread_by_class for name in affected):
            return
        try:
            candidates.extend(
                build_candidates(
                    source_context=source_context,
                    page_1based=page_1based,
                    configuration_sha256=configuration_sha256,
                    primitives=primitives,
                    text_ephemeral=ephemeral_text,
                    tiles=tiles,
                    render_rgb=render_rgb,
                    width=width,
                    height=height,
                    rotation_matrix=context["rotation_matrix_object"],
                    families=frozenset((family,)),
                    enable_table="table" not in unread_by_class,
                )
            )
        except VWStop as exc:
            block(exc.reason, affected)

    build_family("raster", ("raster", "scan-component"))
    build_family("vector", ("vector", "stroke-cluster", "table"))
    build_family("text", ("text-block",))
    candidates.sort(key=lambda item: item["candidate_id"])
    try:
        relationships = build_relationships(candidates)
    except VWStop as exc:
        block(exc.reason, CLASS_ORDER)
        candidates = []
        relationships = []

    unread_unique = {canonical_json_bytes(item): item for item in unreads}
    unreads = sorted(
        unread_unique.values(),
        key=lambda item: (
            item["scope"], item["reason_code"], item["blocking"], item["detail_code"],
            "" if item["evidence_sha256"] is None else item["evidence_sha256"],
        ),
    )
    report = {
        "page_1based": page_1based,
        "status": "measured",
        "media_box_mupdf_pt": context["media_box_mupdf_pt"],
        "crop_box_mupdf_pt": context["crop_box_mupdf_pt"],
        "media_box_pdf_user_space_pt": context["media_box_pdf_user_space_pt"],
        "crop_box_pdf_user_space_pt": context["crop_box_pdf_user_space_pt"],
        "rotation_degrees": context["rotation_degrees"],
        "render": render,
        "tiles": sorted(tiles, key=lambda item: (item["bbox_px_half_open"][1], item["bbox_px_half_open"][0], item["tile_id"])),
        "tile_union": tile_union,
        "primitive_facts": primitives,
        "primitive_census": (
            {
                "status": "UNREAD",
                "image_occurrences": None,
                "text_blocks": None,
                "vector_primitives": None,
                "reason_codes": sorted({item["reason_code"] for item in unreads}) or ["UNREAD"],
            }
            if primitive_failures
            else {
                "status": "measured",
                "image_occurrences": image_occurrences,
                "text_blocks": text_type_census.get("0", 0),
                "vector_primitives": len(vector),
                "reason_codes": [],
            }
        ),
        "region_candidates": candidates,
        "relationships": relationships,
        "class_procedures": class_procedures(candidates, unread_by_class),
        "unreads": unreads,
    }
    return PageCapture(report=report, render_rgb=render_rgb, ephemeral_text=ephemeral_text)


def _json_skip_ws(raw: bytes, index: int) -> int:
    while index < len(raw) and raw[index] in b" \t\r\n":
        index += 1
    return index


def _json_string_end(raw: bytes, index: int) -> int:
    if index >= len(raw) or raw[index] != 0x22:
        raise VWStop("GROUND-DRIFT", "expected JSON string")
    index += 1
    while index < len(raw):
        byte = raw[index]
        if byte == 0x22:
            return index + 1
        if byte == 0x5C:
            index += 2
        else:
            index += 1
    raise VWStop("GROUND-DRIFT", "unterminated JSON string")


def _json_value_end(raw: bytes, index: int) -> int:
    index = _json_skip_ws(raw, index)
    if index >= len(raw):
        raise VWStop("GROUND-DRIFT", "missing JSON value")
    if raw[index] == 0x22:
        return _json_string_end(raw, index)
    if raw[index] in (0x7B, 0x5B):
        opener = raw[index]
        closer = 0x7D if opener == 0x7B else 0x5D
        depth = 1
        index += 1
        while index < len(raw) and depth:
            if raw[index] == 0x22:
                index = _json_string_end(raw, index)
                continue
            if raw[index] == opener:
                depth += 1
            elif raw[index] == closer:
                depth -= 1
            elif raw[index] in (0x7B, 0x5B) and raw[index] != opener:
                # Recursively skip the other container kind so mixed nesting is exact.
                index = _json_value_end(raw, index)
                continue
            index += 1
        if depth:
            raise VWStop("GROUND-DRIFT", "unterminated JSON container")
        return index
    end = index
    while end < len(raw) and raw[end] not in b",]} \t\r\n":
        end += 1
    if end == index:
        raise VWStop("GROUND-DRIFT", "empty JSON scalar")
    # Validate the scalar without interpreting any neighboring private object.
    strict_json_bytes(raw[index:end])
    return end


def _json_object_members(raw: bytes, start: int, end: int) -> dict[str, tuple[int, int]]:
    index = _json_skip_ws(raw, start)
    if index >= end or raw[index] != 0x7B:
        raise VWStop("GROUND-DRIFT", "expected JSON object")
    index += 1
    members: dict[str, tuple[int, int]] = {}
    while True:
        index = _json_skip_ws(raw, index)
        if index >= end:
            raise VWStop("GROUND-DRIFT", "unterminated JSON object")
        if raw[index] == 0x7D:
            if index + 1 != end:
                raise VWStop("GROUND-DRIFT", "trailing bytes after JSON object")
            return members
        key_end = _json_string_end(raw, index)
        key = strict_json_bytes(raw[index:key_end])
        if not isinstance(key, str) or key in members:
            raise VWStop("GROUND-DRIFT", f"duplicate or invalid JSON member {key!r}")
        index = _json_skip_ws(raw, key_end)
        if index >= end or raw[index] != 0x3A:
            raise VWStop("GROUND-DRIFT", "missing JSON member colon")
        value_start = _json_skip_ws(raw, index + 1)
        value_end = _json_value_end(raw, value_start)
        members[key] = (value_start, value_end)
        index = _json_skip_ws(raw, value_end)
        if index >= end:
            raise VWStop("GROUND-DRIFT", "unterminated JSON object")
        if raw[index] == 0x2C:
            index += 1
            continue
        if raw[index] != 0x7D:
            raise VWStop("GROUND-DRIFT", "expected JSON object comma or close")


def _json_array_elements(raw: bytes, start: int, end: int) -> list[tuple[int, int]]:
    index = _json_skip_ws(raw, start)
    if index >= end or raw[index] != 0x5B:
        raise VWStop("GROUND-DRIFT", "expected JSON array")
    index += 1
    elements: list[tuple[int, int]] = []
    while True:
        index = _json_skip_ws(raw, index)
        if index >= end:
            raise VWStop("GROUND-DRIFT", "unterminated JSON array")
        if raw[index] == 0x5D:
            if index + 1 != end:
                raise VWStop("GROUND-DRIFT", "trailing bytes after JSON array")
            return elements
        value_end = _json_value_end(raw, index)
        elements.append((index, value_end))
        index = _json_skip_ws(raw, value_end)
        if index >= end:
            raise VWStop("GROUND-DRIFT", "unterminated JSON array")
        if raw[index] == 0x2C:
            index += 1
            continue
        if raw[index] != 0x5D:
            raise VWStop("GROUND-DRIFT", "expected JSON array comma or close")


@dataclass(frozen=True)
class CalibrationManifest:
    raw_sha256: str
    raw_bytes: int
    root_text: str
    asset_inventory_hash_algorithm: str
    cases: tuple[Mapping[str, Any], ...]


def select_calibration_manifest(raw: bytes, selected_case_ids: Sequence[Any]) -> CalibrationManifest:
    """Parse only selected calibration objects; held-out values are structurally skipped."""

    selected = lexical_case_guard(selected_case_ids)
    if len(raw) != 11_294 or sha256_bytes(raw) != PRIVATE_MANIFEST_SHA256:
        raise VWStop("GROUND-DRIFT", "private manifest byte identity mismatch")
    root_start, root_end = _json_skip_ws(raw, 0), len(raw)
    while root_end > root_start and raw[root_end - 1] in b" \t\r\n":
        root_end -= 1
    members = _json_object_members(raw, root_start, root_end)
    for required in ("root", "asset_inventory_hash_algorithm", "cases"):
        if required not in members:
            raise VWStop("GROUND-DRIFT", f"private manifest lacks {required!r}")
    root_text = strict_json_bytes(raw[slice(*members["root"])])
    algorithm = strict_json_bytes(raw[slice(*members["asset_inventory_hash_algorithm"])])
    if not isinstance(root_text, str) or not isinstance(algorithm, str):
        raise VWStop("GROUND-DRIFT", "private manifest root/algorithm has wrong type")
    case_spans = _json_array_elements(raw, *members["cases"])
    found: dict[str, Mapping[str, Any]] = {}
    seen_ids: set[str] = set()
    for start, end in case_spans:
        case_members = _json_object_members(raw, start, end)
        if "id" not in case_members:
            raise VWStop("GROUND-DRIFT", "manifest case lacks lexical id")
        case_id = strict_json_bytes(raw[slice(*case_members["id"])])
        if not isinstance(case_id, str) or case_id in seen_ids:
            raise VWStop("GROUND-DRIFT", "manifest case id invalid or duplicated")
        seen_ids.add(case_id)
        if case_id in HELD_OUT_CASE_IDS:
            # Do not decode, normalize, stat, or otherwise inspect another field.
            continue
        if case_id not in ALLOWED_CASE_IDS:
            raise VWStop("VW-HELDOUT-CONTAMINATION", f"manifest contains unknown case id {case_id!r}")
        if case_id in selected:
            record = strict_json_bytes(raw[start:end])
            if record.get("split") != "calibration":
                raise VWStop("GROUND-DRIFT", f"{case_id} does not have calibration split")
            found[case_id] = record
    if set(found) != set(selected):
        raise VWStop("GROUND-DRIFT", "selected calibration cases are missing")
    return CalibrationManifest(
        raw_sha256=sha256_bytes(raw),
        raw_bytes=len(raw),
        root_text=root_text,
        asset_inventory_hash_algorithm=algorithm,
        cases=tuple(found[case_id] for case_id in selected),
    )


def _git_probe_shape(arguments: Sequence[str]) -> str:
    candidate = tuple(arguments)
    if any(not isinstance(item, str) for item in candidate):
        raise VWStop("GROUND-DRIFT", "bounded Git probe arguments have the wrong type")
    if candidate == ("rev-parse", "HEAD"):
        return "rev-parse-head"
    if (
        len(candidate) == 3
        and candidate[:2] == ("merge-base", REPOSITORY_SHA)
        and candidate[2] in EVENT_MEASURED_GIT_HEADS
    ):
        return "merge-base-anchor-measured-head"
    if (
        len(candidate) == 4
        and candidate[:3] == ("diff", "--name-only", "-z")
        and candidate[3].startswith(REPOSITORY_SHA + "..")
        and candidate[3][len(REPOSITORY_SHA) + 2 :] in EVENT_MEASURED_GIT_HEADS
    ):
        return "diff-anchor-measured-head"
    if candidate == ("status", "--porcelain=v1", "--untracked-files=all", "-z"):
        return "status-porcelain-v1-untracked-all"
    raise VWStop("GROUND-DRIFT", "bounded Git probe arguments are not allowlisted")


def _verified_git_executable_observation() -> dict[str, Any]:
    if not GIT_EXECUTABLE.is_file():
        raise VWStop("VW-DEPENDENCY-DRIFT", "bound Git executable is missing")
    try:
        observation = stable_file_observation(GIT_EXECUTABLE, "VW-DEPENDENCY-DRIFT")
    except VWStop as exc:
        raise VWStop("VW-DEPENDENCY-DRIFT", "bound Git executable could not be verified") from exc
    if observation != {"bytes": GIT_EXECUTABLE_BYTES, "sha256": GIT_EXECUTABLE_SHA256}:
        raise VWStop("VW-DEPENDENCY-DRIFT", "bound Git executable identity mismatch")
    return observation


def _git_sanitized_environment() -> dict[str, str]:
    environment: dict[str, str] = {}
    for key in GIT_INHERITED_ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value:
            environment[key] = value
    environment.update(dict(GIT_FIXED_ENVIRONMENT))
    return environment


def _git_command(repo_root: Path, arguments: Sequence[str]) -> tuple[list[str], dict[str, str]]:
    shape = _git_probe_shape(arguments)
    command = [str(GIT_EXECUTABLE), "--no-pager", "-c", f"safe.directory={repo_root}"]
    for setting in GIT_FIXED_CONFIG:
        command.extend(("-c", setting))
    actual_arguments = list(arguments)
    if shape == "diff-anchor-measured-head":
        actual_arguments[1:1] = ["--no-ext-diff", "--no-textconv"]
    command.extend(actual_arguments)
    return command, _git_sanitized_environment()


def _git_controls_sha256(repo_root: Path, arguments: Sequence[str]) -> str:
    command, environment = _git_command(repo_root, arguments)
    return sha256_bytes(
        canonical_json_bytes(
            {
                "argv": command,
                "environment": {key: environment[key] for key in sorted(environment)},
                "inherits_path": False,
                "child_process_isolation": "suspended-job-active-process-limit-1-v1",
                "policy": "vw-e2-r2-local-git-deny-by-construction-v1",
            }
        )
    )


def _census_native_git_descendants(root_pid: int) -> set[int]:
    try:
        parents = _windows_process_parent_map()
    except VWStop:
        raise
    except BaseException as exc:
        raise VWStop("UNREAD", "native Git descendant census unavailable") from exc
    descendants: set[int] = set()
    changed = True
    while changed:
        changed = False
        parent_scope = {root_pid, *descendants}
        for pid, parent in parents.items():
            if parent in parent_scope and pid != root_pid and pid not in descendants:
                descendants.add(pid)
                changed = True
    EVENT_OBSERVED_DESCENDANT_PIDS.update(descendants)
    return descendants


class _JobBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", wintypes.DWORD),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wintypes.DWORD),
        ("scheduling_class", wintypes.DWORD),
    ]


class _JobIoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _JobExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _JobBasicLimitInformation),
        ("io_info", _JobIoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


def _bind_native_git_single_process_job(pid: int) -> int:
    """Assign a still-suspended Git process to a no-descendant Windows Job Object."""

    if os.name != "nt" or type(pid) is not int or pid <= 0:
        raise VWStop("UNREAD", "native Git Job Object binding was unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_job = kernel32.CreateJobObjectW
    create_job.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    create_job.restype = wintypes.HANDLE
    set_information = kernel32.SetInformationJobObject
    set_information.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    set_information.restype = wintypes.BOOL
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    assign_process = kernel32.AssignProcessToJobObject
    assign_process.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    assign_process.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    job = create_job(None, None)
    if not job:
        raise VWStop("UNREAD", "native Git Job Object creation failed")
    process_handle: int | None = None
    try:
        limits = _JobExtendedLimitInformation()
        limits.basic_limit_information.limit_flags = 0x00000008 | 0x00002000
        limits.basic_limit_information.active_process_limit = 1
        if not set_information(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise VWStop("UNREAD", "native Git Job Object limit assignment failed")
        process_handle = open_process(0x0001 | 0x0100 | 0x1000, False, pid)
        if not process_handle:
            raise VWStop("UNREAD", "native Git suspended process handle was unavailable")
        if not assign_process(job, process_handle):
            raise VWStop("UNREAD", "native Git could not enter the no-descendant Job Object")
        return int(job)
    except BaseException:
        close_handle(job)
        raise
    finally:
        if process_handle:
            close_handle(process_handle)


def _resume_native_git_process(pid: int) -> None:
    """Resume the single primary thread of a process created suspended by this module."""

    if os.name != "nt":
        raise VWStop("UNREAD", "native Git suspended-thread resume was unavailable")

    class ThreadEntry32(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("usage", wintypes.DWORD),
            ("thread_id", wintypes.DWORD),
            ("owner_process_id", wintypes.DWORD),
            ("base_priority", wintypes.LONG),
            ("delta_priority", wintypes.LONG),
            ("flags", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    invalid = ctypes.c_void_p(-1).value
    if snapshot in (None, invalid):
        raise VWStop("UNREAD", "native Git thread snapshot failed")
    first = kernel32.Thread32First
    first.argtypes = (wintypes.HANDLE, ctypes.POINTER(ThreadEntry32))
    first.restype = wintypes.BOOL
    next_entry = kernel32.Thread32Next
    next_entry.argtypes = (wintypes.HANDLE, ctypes.POINTER(ThreadEntry32))
    next_entry.restype = wintypes.BOOL
    open_thread = kernel32.OpenThread
    open_thread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_thread.restype = wintypes.HANDLE
    resume_thread = kernel32.ResumeThread
    resume_thread.argtypes = (wintypes.HANDLE,)
    resume_thread.restype = wintypes.DWORD
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    entry = ThreadEntry32()
    entry.size = ctypes.sizeof(entry)
    thread_ids: list[int] = []
    try:
        if not first(snapshot, ctypes.byref(entry)):
            raise VWStop("UNREAD", "native Git primary thread was unread")
        while True:
            if int(entry.owner_process_id) == pid:
                thread_ids.append(int(entry.thread_id))
            if not next_entry(snapshot, ctypes.byref(entry)):
                if ctypes.get_last_error() != 18:
                    raise VWStop("UNREAD", "native Git thread enumeration failed")
                break
    finally:
        close_handle(snapshot)
    if len(thread_ids) != 1:
        raise VWStop("UNREAD", "native Git suspended process did not have exactly one primary thread")
    thread = open_thread(0x0002, False, thread_ids[0])
    if not thread:
        raise VWStop("UNREAD", "native Git primary thread handle was unavailable")
    try:
        previous_count = int(resume_thread(thread))
        if previous_count != 1:
            raise VWStop("UNREAD", "native Git primary thread suspend count was unexpected")
    finally:
        close_handle(thread)


def _close_native_git_job(job_handle: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    if not close_handle(wintypes.HANDLE(job_handle)):
        raise VWStop("VW-CLEANUP", "native Git Job Object handle cleanup failed")


def _git(repo_root: Path, *arguments: str) -> bytes:
    # Argument rejection and binary identity verification both happen before any process exists.
    shape = _git_probe_shape(arguments)
    try:
        repo_root = Path(repo_root).resolve(strict=True)
    except OSError as exc:
        raise VWStop("GROUND-DRIFT", "bounded Git repository root is unread") from exc
    if not repo_root.is_dir():
        raise VWStop("GROUND-DRIFT", "bounded Git repository root is not a directory")
    binary_observation = _verified_git_executable_observation()
    command, environment = _git_command(repo_root, arguments)
    controls_sha = _git_controls_sha256(repo_root, arguments)
    process: subprocess.Popen[bytes] | None = None
    job_handle: int | None = None
    stdout = b""
    stderr = b""
    descendants: set[int] = set()
    pid: int | None = None
    try:
        try:
            process = subprocess.Popen(
                command,
                cwd=repo_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | 0x00000004,
                close_fds=True,
            )
        except OSError as exc:
            raise VWStop("GROUND-DRIFT", f"bounded Git probe failed before PID assignment: {type(exc).__name__}") from exc
        if process.pid is None:
            try:
                process.kill()
                process.communicate(timeout=5.0)
            except BaseException:
                pass
            raise VWStop("UNREAD", "bounded Git probe PID was unread")
        pid = int(process.pid)
        EVENT_CHILD_PIDS.add(pid)
        EVENT_ACTIVITY.native_git_expected_processes += 1
        try:
            job_handle = _bind_native_git_single_process_job(pid)
            _resume_native_git_process(pid)
        except BaseException as exc:
            try:
                process.kill()
                process.communicate(timeout=5.0)
            except BaseException:
                pass
            if process.poll() is not None:
                EVENT_CHILD_EXITED_PIDS.add(pid)
            if isinstance(exc, VWStop):
                raise
            raise VWStop("UNREAD", f"native Git Job Object setup failed: {type(exc).__name__}") from exc
        deadline = time.monotonic() + 20.0
        try:
            while True:
                descendants.update(_census_native_git_descendants(pid))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, 20.0)
                try:
                    stdout, stderr = process.communicate(timeout=min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        except BaseException as exc:
            try:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5.0)
            except BaseException:
                pass
            if process.poll() is not None:
                EVENT_CHILD_EXITED_PIDS.add(pid)
            if isinstance(exc, VWStop):
                raise
            raise VWStop("UNREAD", f"bounded Git probe did not complete: {type(exc).__name__}") from exc
        finally:
            if process.poll() is not None:
                EVENT_CHILD_EXITED_PIDS.add(pid)
        descendants.update(_census_native_git_descendants(pid))
        residue = native_isolation_measurement({pid, *descendants})
        EVENT_OBSERVED_DESCENDANT_PIDS.update(residue.event_pids)
        if residue.live_event_pids or residue.owned_ports:
            raise VWStop("VW-CLEANUP", "native Git child or port residue remains")
        if process.returncode != 0:
            raise VWStop("GROUND-DRIFT", f"bounded Git probe exited {process.returncode}")
        if stderr != b"":
            raise VWStop("GROUND-DRIFT", "bounded Git probe emitted stderr")
        if shape in ("rev-parse-head", "merge-base-anchor-measured-head"):
            if re.fullmatch(rb"[0-9a-f]{40}\n", stdout) is None:
                raise VWStop("GROUND-DRIFT", "bounded Git identity output was not exact")
        if shape == "rev-parse-head":
            EVENT_MEASURED_GIT_HEADS.add(stdout[:-1].decode("ascii", "strict"))
        EVENT_ACTIVITY.native_git_attestations.append(
            {
                "argument_shape": shape,
                "arguments": list(arguments),
                "binary_bytes": binary_observation["bytes"],
                "binary_sha256": binary_observation["sha256"],
                "controls_sha256": controls_sha,
                "deny_by_construction": True,
                "descendant_pids": sorted(descendants),
                "exit_code": int(process.returncode),
                "pid": pid,
                "repo_root": str(repo_root),
                "stderr_bytes": len(stderr),
                "stderr_sha256": sha256_bytes(stderr),
                "stdout_bytes": len(stdout),
                "stdout_sha256": sha256_bytes(stdout),
            }
        )
        EVENT_ACTIVITY.native_git_reconciled_processes += 1
        return stdout
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.communicate(timeout=5.0)
            except BaseException:
                pass
        if pid is not None and process is not None and process.poll() is not None:
            EVENT_CHILD_EXITED_PIDS.add(pid)
        if job_handle is not None:
            _close_native_git_job(job_handle)


def verify_repository_ground(repo_root: Path) -> tuple[Mapping[str, Any], str]:
    repo_root = repo_root.resolve(strict=True)
    packet_path = repo_root / PACKET_RELATIVE_PATH
    schema_path = repo_root / CAPTURE_SCHEMA_RELATIVE_PATH
    packet_raw, schema_raw = packet_path.read_bytes(), schema_path.read_bytes()
    if len(packet_raw) != PACKET_BYTES or sha256_bytes(packet_raw) != PACKET_SHA256:
        raise VWStop("GROUND-DRIFT", "R2 packet identity mismatch")
    if len(schema_raw) != CAPTURE_SCHEMA_BYTES or sha256_bytes(schema_raw) != CAPTURE_SCHEMA_SHA256:
        raise VWStop("GROUND-DRIFT", "capture schema identity mismatch")
    for relative, expected in BOUND_PUBLIC_FILES:
        path = repo_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise VWStop("GROUND-DRIFT", f"bound public file mismatch at {relative}")
    head = _git(repo_root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    merge_base = _git(repo_root, "merge-base", REPOSITORY_SHA, head).decode("ascii", "strict").strip()
    if merge_base != REPOSITORY_SHA:
        raise VWStop("GROUND-DRIFT", "packet repository anchor is not an ancestor of HEAD")
    packet = strict_json_bytes(packet_raw)
    configuration = packet.get("frozen_configuration") if isinstance(packet, dict) else None
    if not isinstance(configuration, dict):
        raise VWStop("GROUND-DRIFT", "packet lacks frozen_configuration")
    measured_config = config_sha256(configuration)
    if measured_config != EXPECTED_CONFIG_SHA256:
        raise VWStop("VW-CONFIG-HASH", f"configuration hash {measured_config} does not match packet correction")
    if sys.version_info[:3] != (3, 12, 13):
        raise VWStop("VW-DEPENDENCY-DRIFT", f"Python version is {sys.version_info[:3]}")
    if str(pymupdf.__version__) != "1.28.0" or tuple(pymupdf.mupdf_version_tuple) != (1, 29, 0):
        raise VWStop("VW-DEPENDENCY-DRIFT", "PyMuPDF/MuPDF version mismatch")
    allowed_dirty = {
        *packet["write_scope"]["new_repository_files"],
        *packet["write_scope"]["allowed_repository_updates"],
    }
    concurrent_patterns = tuple(packet["repository_anchor"]["concurrent_lane"]["mutable_path_rules"])
    if head != REPOSITORY_SHA:
        changed = [
            path
            for path in _git(repo_root, "diff", "--name-only", "-z", f"{REPOSITORY_SHA}..{head}")
            .decode("utf-8", "surrogateescape")
            .split("\0")
            if path
        ]
        if any(not any(fnmatch.fnmatchcase(path, pattern) for pattern in concurrent_patterns) for path in changed):
            raise VWStop("GROUND-DRIFT", "descendant HEAD changes overlap or exceed concurrent-lane scope")
    pre_existing = packet["repository_anchor"]["pre_existing_dirty_ground"]
    pre_existing_paths: set[str] = set()
    for item in pre_existing:
        path_text = item["path"]
        path = repo_root / path_text
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise VWStop("GROUND-DRIFT", f"fixed pre-existing dirty ground changed at {path_text}")
        pre_existing_paths.add(path_text)
    porcelain = _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all", "-z").decode("utf-8", "surrogateescape")
    parts = [entry for entry in porcelain.split("\0") if entry]
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        if len(entry) < 4:
            entries.append(("??", "malformed-status-entry"))
            index += 1
            continue
        status, path = entry[:2], entry[3:]
        entries.append((status, path))
        index += 1
        if "R" in status or "C" in status:
            if index >= len(parts):
                entries.append(("??", "malformed-rename-entry"))
                break
            entries.append((status, parts[index]))
            index += 1
    unexpected: list[str] = []
    for _status, raw_path in entries:
        path = raw_path.replace("\\", "/")
        permitted = (
            path in allowed_dirty
            or path in pre_existing_paths
            or any(fnmatch.fnmatchcase(path, pattern) for pattern in concurrent_patterns)
        )
        if not permitted:
            unexpected.append(path)
    if unexpected:
        raise VWStop("GROUND-DRIFT", f"unexpected dirty path count {len(set(unexpected))}")
    return packet, measured_config


def _is_reparse(path: Path) -> bool:
    stat = os.lstat(path)
    attributes = getattr(stat, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def strict_final_path(path: Path, *, directory: bool | None = None) -> Path:
    lexical = Path(os.path.abspath(os.fspath(path)))
    if not lexical.exists():
        raise VWStop("VW-PRIVACY", "required root/path does not exist")
    lexical_chain = [lexical, *lexical.parents]
    for existing in lexical_chain:
        if existing.exists() and _is_reparse(existing):
            raise VWStop("VW-PRIVACY", "reparse point in pre-resolution path ancestry")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise VWStop("VW-PRIVACY", "required root/path does not exist") from exc
    if directory is True and not resolved.is_dir():
        raise VWStop("VW-PRIVACY", "required directory is not a directory")
    if directory is False and not resolved.is_file():
        raise VWStop("VW-PRIVACY", "required file is not a regular file")
    anchor = Path(resolved.anchor)
    current = anchor
    for part in resolved.parts[1:]:
        current = current / part
        if _is_reparse(current):
            raise VWStop("VW-PRIVACY", "reparse point in protected path ancestry")
    return resolved


def _canonical_windows(path: Path) -> str:
    return str(path).replace("/", "\\").rstrip("\\").casefold()


def paths_related(left: Path, right: Path) -> bool:
    left_key, right_key = _canonical_windows(left), _canonical_windows(right)
    return left_key == right_key or left_key.startswith(right_key + "\\") or right_key.startswith(left_key + "\\")


@dataclass(frozen=True)
class OutputRoots:
    evidence_root: Path
    scratch_root: Path
    evidence_run: Path
    scratch_run: Path
    scratch_free_bytes_before: int


@dataclass(frozen=True)
class PartialRootContext:
    evidence_run_created: Path | None
    scratch_run_created: Path | None
    cleanup_failure_ids: tuple[str, ...]


class PartialRootFailure(VWStop):
    def __init__(self, context: PartialRootContext, detail: str):
        super().__init__("VW-CLEANUP", detail)
        self.context = context


def prepare_output_roots(
    *,
    evidence_root: Path,
    scratch_root: Path,
    run_id: str,
    protected_paths: Sequence[Path],
) -> OutputRoots:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise VWStop("VW-PRIVACY", "run id is not opaque")
    if not evidence_root.is_absolute() or not scratch_root.is_absolute():
        raise VWStop("VW-PRIVACY", "output roots must be explicit absolute paths")
    evidence = strict_final_path(evidence_root, directory=True)
    scratch = strict_final_path(scratch_root, directory=True)
    protected = [strict_final_path(path) for path in protected_paths]
    for left in (evidence, scratch):
        for right in protected:
            if paths_related(left, right):
                raise VWStop("VW-PRIVACY", "output root overlaps another or a protected path")
    if paths_related(evidence, scratch):
        raise VWStop("VW-PRIVACY", "evidence and scratch roots overlap")
    free = shutil.disk_usage(scratch).free
    if free < MIN_SCRATCH_FREE:
        raise VWStop("GROUND-DRIFT", f"scratch free bytes {free} below frozen minimum")
    evidence_run, scratch_run = evidence / run_id, scratch / run_id
    evidence_created = False
    scratch_created = False
    try:
        evidence_run.mkdir(mode=0o700)
        evidence_created = True
        scratch_run.mkdir(mode=0o700)
        scratch_created = True
    except OSError as exc:
        # Roll back only children created by this call.  A pre-existing collision is
        # never removed, and cleanup proceeds in reverse creation order.
        cleanup_failures: list[str] = []
        if scratch_created:
            try:
                scratch_run.rmdir()
            except OSError:
                cleanup_failures.append("scratch-child-remains")
        if evidence_created:
            try:
                evidence_run.rmdir()
            except OSError:
                cleanup_failures.append("evidence-child-remains")
        if cleanup_failures:
            context = PartialRootContext(
                evidence_run if evidence_created and evidence_run.exists() else None,
                scratch_run if scratch_created and scratch_run.exists() else None,
                tuple(cleanup_failures),
            )
            raise PartialRootFailure(context, "new run child rollback failed") from exc
        detail = "run child already exists" if isinstance(exc, FileExistsError) else "failed to create run children"
        raise VWStop("VW-PRIVACY", detail) from exc
    return OutputRoots(evidence, scratch, evidence_run, scratch_run, free)


def stable_file_observation(path: Path, reason_code: str) -> dict[str, Any]:
    path = strict_final_path(path, directory=False)
    before = os.stat(path, follow_symlinks=False)
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                byte_count += len(chunk)
    except OSError as exc:
        raise VWStop(reason_code, "protected regular file could not be read") from exc
    after = os.stat(path, follow_symlinks=False)
    identity_before = (before.st_size, before.st_mtime_ns, getattr(before, "st_ino", 0))
    identity_after = (after.st_size, after.st_mtime_ns, getattr(after, "st_ino", 0))
    if identity_before != identity_after or byte_count != before.st_size:
        raise VWStop(reason_code, "protected regular file changed during read")
    return {"bytes": byte_count, "sha256": digest.hexdigest()}


def stable_small_file_bytes(path: Path, reason_code: str, *, maximum_bytes: int = 16 * 1024 * 1024) -> tuple[bytes, dict[str, Any]]:
    path = strict_final_path(path, directory=False)
    before = os.stat(path, follow_symlinks=False)
    if before.st_size > maximum_bytes:
        raise VWStop(reason_code, "structured metadata file exceeds bounded size")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise VWStop(reason_code, "structured metadata file could not be read") from exc
    after = os.stat(path, follow_symlinks=False)
    if (
        (before.st_size, before.st_mtime_ns, getattr(before, "st_ino", 0))
        != (after.st_size, after.st_mtime_ns, getattr(after, "st_ino", 0))
        or len(raw) != before.st_size
    ):
        raise VWStop(reason_code, "structured metadata file changed during read")
    return raw, {"bytes": len(raw), "sha256": sha256_bytes(raw)}


def _stable_git_metadata_bytes(path: Path, *, maximum_bytes: int, label: str) -> bytes:
    try:
        raw, _observation = stable_small_file_bytes(
            path,
            "GROUND-DRIFT",
            maximum_bytes=maximum_bytes,
        )
    except VWStop as exc:
        raise VWStop("GROUND-DRIFT", f"Git {label} was not a stable bounded regular file") from exc
    if b"\0" in raw:
        raise VWStop("GROUND-DRIFT", f"Git {label} contained NUL")
    return raw


def _single_git_metadata_line(raw: bytes, *, label: str) -> str:
    if raw.endswith(b"\r\n"):
        body = raw[:-2]
    elif raw.endswith(b"\n"):
        body = raw[:-1]
    else:
        body = raw
    if not body or b"\r" in body or b"\n" in body:
        raise VWStop("GROUND-DRIFT", f"Git {label} was not one bounded line")
    try:
        return body.decode("ascii", "strict")
    except UnicodeDecodeError as exc:
        raise VWStop("GROUND-DRIFT", f"Git {label} was not ASCII") from exc


def _validated_git_metadata_directory(path: Path, *, label: str) -> Path:
    try:
        return strict_final_path(path, directory=True)
    except VWStop as exc:
        raise VWStop("GROUND-DRIFT", f"Git {label} directory was unread") from exc


def _validated_git_ref_name(ref_name: str) -> str:
    if (
        not ref_name.isascii()
        or len(ref_name) > 1024
        or not ref_name.startswith("refs/")
        or ref_name.endswith(("/", "."))
        or ".." in ref_name
        or "@{" in ref_name
        or any(character in ref_name for character in " ~^:?*[\\")
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in ref_name)
    ):
        raise VWStop("GROUND-DRIFT", "Git HEAD symbolic ref path was invalid")
    components = ref_name.split("/")
    if (
        len(components) < 2
        or any(not component or component.startswith(".") or component.endswith(".lock") for component in components)
    ):
        raise VWStop("GROUND-DRIFT", "Git HEAD symbolic ref component was invalid")
    return ref_name


def _git_object_id_line(raw: bytes, *, label: str) -> str:
    candidate = _single_git_metadata_line(raw, label=label)
    if re.fullmatch(r"[0-9a-f]{40}", candidate) is None:
        raise VWStop("GROUND-DRIFT", f"Git {label} object id was invalid")
    return candidate


def _resolve_repository_git_directories(repo_root: Path) -> tuple[Path, Path, Path]:
    try:
        repo_root = strict_final_path(repo_root, directory=True)
    except VWStop as exc:
        raise VWStop("GROUND-DRIFT", "repository root was unread during direct HEAD resolution") from exc
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        git_dir = _validated_git_metadata_directory(dot_git, label="directory")
    elif dot_git.is_file():
        pointer = _single_git_metadata_line(
            _stable_git_metadata_bytes(dot_git, maximum_bytes=4096, label="gitdir pointer"),
            label="gitdir pointer",
        )
        if not pointer.startswith("gitdir: "):
            raise VWStop("GROUND-DRIFT", "Git gitdir pointer prefix was invalid")
        target_text = pointer[len("gitdir: ") :]
        if not target_text or len(target_text) > 3072:
            raise VWStop("GROUND-DRIFT", "Git gitdir pointer target was invalid")
        target = Path(target_text)
        git_dir = _validated_git_metadata_directory(
            target if target.is_absolute() else dot_git.parent / target,
            label="gitdir target",
        )
    else:
        raise VWStop("GROUND-DRIFT", "repository .git control path was missing")

    common_dir = git_dir
    common_pointer = git_dir / "commondir"
    if common_pointer.exists():
        common_text = _single_git_metadata_line(
            _stable_git_metadata_bytes(common_pointer, maximum_bytes=4096, label="commondir pointer"),
            label="commondir pointer",
        )
        if len(common_text) > 3072:
            raise VWStop("GROUND-DRIFT", "Git commondir pointer target was invalid")
        common_target = Path(common_text)
        common_dir = _validated_git_metadata_directory(
            common_target if common_target.is_absolute() else git_dir / common_target,
            label="commondir target",
        )
    return repo_root, git_dir, common_dir


def resolve_repository_head_direct(repo_root: Path) -> str:
    """Resolve HEAD without a child process, using only stable bounded Git metadata reads."""

    _repo_root, git_dir, common_dir = _resolve_repository_git_directories(repo_root)

    head_text = _single_git_metadata_line(
        _stable_git_metadata_bytes(git_dir / "HEAD", maximum_bytes=4096, label="HEAD"),
        label="HEAD",
    )
    if re.fullmatch(r"[0-9a-f]{40}", head_text) is not None:
        return head_text
    if not head_text.startswith("ref: "):
        raise VWStop("GROUND-DRIFT", "Git HEAD was neither detached nor symbolic")
    ref_name = _validated_git_ref_name(head_text[len("ref: ") :])

    loose_candidates = [git_dir / Path(*ref_name.split("/"))]
    if common_dir != git_dir:
        loose_candidates.append(common_dir / Path(*ref_name.split("/")))
    for candidate in loose_candidates:
        if candidate.exists():
            return _git_object_id_line(
                _stable_git_metadata_bytes(candidate, maximum_bytes=4096, label="loose ref"),
                label="loose ref",
            )

    packed_refs = common_dir / "packed-refs"
    if not packed_refs.exists():
        raise VWStop("GROUND-DRIFT", "Git symbolic HEAD ref was absent from loose and packed refs")
    packed_raw = _stable_git_metadata_bytes(packed_refs, maximum_bytes=16 * 1024 * 1024, label="packed-refs")
    target_bytes = ref_name.encode("ascii")
    matches: list[str] = []
    for raw_line in packed_raw.splitlines():
        if not raw_line or raw_line.startswith(b"#"):
            continue
        if raw_line.startswith(b"^"):
            if re.fullmatch(rb"\^[0-9a-f]{40}", raw_line) is None:
                raise VWStop("GROUND-DRIFT", "Git packed-refs peeled line was invalid")
            continue
        if raw_line.count(b" ") != 1:
            raise VWStop("GROUND-DRIFT", "Git packed-refs record shape was invalid")
        object_id, packed_name = raw_line.split(b" ", 1)
        if re.fullmatch(rb"[0-9a-f]{40}", object_id) is None or not packed_name:
            raise VWStop("GROUND-DRIFT", "Git packed-refs record was invalid")
        if packed_name == target_bytes:
            matches.append(object_id.decode("ascii"))
    if len(matches) != 1:
        raise VWStop("GROUND-DRIFT", "Git packed symbolic HEAD ref was absent or duplicated")
    return matches[0]


def require_repository_head_direct(repo_root: Path, expected_head: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", expected_head) is None:
        raise VWStop("GROUND-DRIFT", "expected repository HEAD was invalid")
    observed = resolve_repository_head_direct(repo_root)
    if observed != expected_head:
        raise VWStop("GROUND-DRIFT", "repository HEAD changed after the final child-process probe")
    return observed


PROTECTED_LOGICAL_ID_RE = re.compile(
    r"^(?:manifest|VW-T0[1-3]/(?:source|bundle-body|bundle-manifest|raw-markdown|analyst-markdown/(?:0|[1-9][0-9]*)|asset/(?:0|[1-9][0-9]*)))$"
)


@dataclass(frozen=True)
class ProtectedFile:
    logical_id: str
    path: Path = field(repr=False)

    def __post_init__(self) -> None:
        if PROTECTED_LOGICAL_ID_RE.fullmatch(self.logical_id) is None:
            raise VWStop("VW-PROTECTED-TREE", f"invalid protected logical id {self.logical_id!r}")


def protected_inventory(files: Sequence[ProtectedFile]) -> tuple[list[dict[str, Any]], str]:
    logical_ids = [item.logical_id for item in files]
    if len(logical_ids) != len(set(logical_ids)):
        raise VWStop("VW-PROTECTED-TREE", "duplicate protected logical id")
    inventory: list[dict[str, Any]] = []
    for item in sorted(files, key=lambda entry: entry.logical_id):
        observation = stable_file_observation(item.path, "VW-PROTECTED-TREE")
        inventory.append(
            {
                "logical_id": item.logical_id,
                "bytes": observation["bytes"],
                "sha256": observation["sha256"],
            }
        )
    digest = sha256_bytes(DOMAINS["protected_tree"] + canonical_json_bytes(inventory))
    return inventory, digest


def compare_protected_inventories(
    before_entries: Sequence[Mapping[str, Any]],
    before_digest: str,
    after_entries: Sequence[Mapping[str, Any]],
    after_digest: str,
) -> None:
    if before_digest != after_digest or canonical_json_bytes(before_entries) != canonical_json_bytes(after_entries):
        raise VWStop("VW-PROTECTED-TREE", "protected logical inventory changed")


def ordinal_asset_inventory(asset_paths: Sequence[Path]) -> tuple[bytes, list[dict[str, Any]]]:
    """Recompute the E1 ordinal leaf-filename inventory without locale sorting."""

    sorted_paths = sorted(asset_paths, key=lambda path: path.name)
    records = bytearray()
    observations: list[dict[str, Any]] = []
    for ordinal, path in enumerate(sorted_paths):
        observation = stable_file_observation(path, "VW-ASSET-HASH")
        records.extend(path.name.encode("utf-8"))
        records.extend(b"\0")
        records.extend(str(observation["bytes"]).encode("ascii"))
        records.extend(b"\0")
        records.extend(observation["sha256"].encode("ascii"))
        records.extend(b"\n")
        page_match = re.fullmatch(
            r"^.*_page_([0-9]+)_(Figure|Picture)_([0-9]+)\.(jpe?g|png)$",
            path.name,
            re.IGNORECASE,
        )
        observations.append(
            {
                "asset_ordinal": ordinal,
                "page_id_0based": int(page_match.group(1)) if page_match else None,
                "bytes": observation["bytes"],
                "sha256": observation["sha256"],
            }
        )
    return bytes(records), observations


@dataclass(frozen=True)
class ResolvedCaseFiles:
    case: Mapping[str, Any]
    source: Path = field(repr=False)
    bundle_dir: Path = field(repr=False)
    bundle_manifest: Path = field(repr=False)
    bundle_body: Path = field(repr=False)
    raw_markdown: Path = field(repr=False)
    analyst_markdown: tuple[Path, ...] = field(repr=False)
    assets: tuple[Path, ...] = field(repr=False)

    @property
    def case_id(self) -> str:
        return str(self.case["id"])


def resolve_case_files(manifest: CalibrationManifest) -> tuple[ResolvedCaseFiles, ...]:
    manifest_root = strict_final_path(Path(manifest.root_text), directory=True)

    def supplied(text: Any, *, directory: bool) -> Path:
        if not isinstance(text, str) or not text:
            raise VWStop("GROUND-DRIFT", "calibration path is absent")
        candidate = Path(text)
        if not candidate.is_absolute():
            candidate = manifest_root / candidate
        return strict_final_path(candidate, directory=directory)

    resolved: list[ResolvedCaseFiles] = []
    for case in manifest.cases:
        case_id = case["id"]
        if case_id not in ALLOWED_CASE_IDS:
            raise VWStop("VW-HELDOUT-CONTAMINATION", "non-calibration case reached path resolver")
        source = supplied(case["source_path"], directory=False)
        bundle_dir = supplied(case["bundle_path"], directory=True)
        raw_markdown = supplied(case["markdown_path"], directory=False)
        bundle_manifest = strict_final_path(bundle_dir / "manifest.json", directory=False)
        bodies = sorted(
            (path for path in bundle_dir.iterdir() if path.is_file() and path.suffix.casefold() == ".md"),
            key=lambda path: path.name,
        )
        if len(bodies) != 1:
            raise VWStop("VW-BODY-HASH", f"{case_id} bundle has {len(bodies)} direct Markdown bodies")
        assets_dir = bundle_dir / "assets"
        if not assets_dir.exists():
            asset_paths: tuple[Path, ...] = ()
        else:
            assets_root = strict_final_path(assets_dir, directory=True)
            children = list(assets_root.iterdir())
            if any(not child.is_file() or _is_reparse(child) for child in children):
                raise VWStop("VW-ASSET-HASH", f"{case_id} assets are not direct regular files")
            asset_paths = tuple(strict_final_path(path, directory=False) for path in sorted(children, key=lambda path: path.name))
        analyst_records = case.get("analyst_markdown")
        if not isinstance(analyst_records, list):
            raise VWStop("GROUND-DRIFT", f"{case_id} analyst_markdown is not an array")
        analyst_paths = tuple(supplied(item["path"], directory=False) for item in analyst_records)
        resolved.append(
            ResolvedCaseFiles(
                case=case,
                source=source,
                bundle_dir=bundle_dir,
                bundle_manifest=bundle_manifest,
                bundle_body=strict_final_path(bodies[0], directory=False),
                raw_markdown=raw_markdown,
                analyst_markdown=analyst_paths,
                assets=asset_paths,
            )
        )
    return tuple(resolved)


def protected_files_for_run(manifest_path: Path, cases: Sequence[ResolvedCaseFiles]) -> tuple[ProtectedFile, ...]:
    result = [ProtectedFile("manifest", strict_final_path(manifest_path, directory=False))]
    for case in cases:
        prefix = case.case_id
        result.extend(
            (
                ProtectedFile(f"{prefix}/source", case.source),
                ProtectedFile(f"{prefix}/bundle-body", case.bundle_body),
                ProtectedFile(f"{prefix}/bundle-manifest", case.bundle_manifest),
                ProtectedFile(f"{prefix}/raw-markdown", case.raw_markdown),
            )
        )
        result.extend(
            ProtectedFile(f"{prefix}/analyst-markdown/{ordinal}", path)
            for ordinal, path in enumerate(case.analyst_markdown)
        )
        result.extend(ProtectedFile(f"{prefix}/asset/{ordinal}", path) for ordinal, path in enumerate(case.assets))
    return tuple(result)


def observe_source(case: ResolvedCaseFiles) -> dict[str, Any]:
    observation = stable_file_observation(case.source, "VW-SOURCE-HASH")
    expected_manifest = case.case.get("source_sha256_manifest")
    recorded_actual = case.case.get("source_sha256_actual")
    expected_bytes = case.case.get("source_bytes")
    expected_pages = case.case.get("pages")
    hashes_match = (
        isinstance(expected_manifest, str)
        and isinstance(recorded_actual, str)
        and expected_manifest == recorded_actual == observation["sha256"]
    )
    if not hashes_match or observation["bytes"] != expected_bytes:
        raise VWStop("VW-SOURCE-HASH", f"{case.case_id} source hash/byte observation mismatch")
    try:
        with pymupdf.open(case.source) as document:
            pages = int(document.page_count)
    except Exception as exc:
        raise VWStop("VW-RENDER-UNREAD", f"{case.case_id} source document cannot be opened") from exc
    if pages != expected_pages:
        raise VWStop("VW-SOURCE-HASH", f"{case.case_id} source page count mismatch")
    return {
        "status": "measured",
        "manifest_sha256": expected_manifest,
        "recorded_actual_sha256": recorded_actual,
        "observed_sha256": observation["sha256"],
        "bytes": observation["bytes"],
        "pages": pages,
        "all_hashes_match": True,
        "reason_codes": [],
    }


def observe_markdown(path: Path, *, phase: str, ordinal: int, expected_sha256: str, expected_bytes: int) -> dict[str, Any]:
    observed = stable_file_observation(path, "VW-BODY-HASH")
    match = observed["sha256"] == expected_sha256 and observed["bytes"] == expected_bytes
    if not match:
        raise VWStop("VW-BODY-HASH", f"{phase} Markdown observation mismatch")
    return {
        "phase": phase,
        "variant_ordinal": ordinal,
        "status": "measured",
        "expected_sha256": expected_sha256,
        "observed_sha256": observed["sha256"],
        "bytes": observed["bytes"],
        "match": True,
        "reason_codes": [],
    }


def observed_asset_inventory(case: ResolvedCaseFiles) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records, observations = ordinal_asset_inventory(case.assets)
    digest = sha256_bytes(records)
    expected = case.case.get("asset_inventory_sha256")
    expected_count = case.case.get("asset_count")
    if digest != expected or len(observations) != expected_count:
        raise VWStop("VW-ASSET-HASH", f"{case.case_id} ordinal asset inventory mismatch")
    inventory = {
        "status": "measured",
        "expected_sha256": expected,
        "observed_sha256": digest,
        "count": len(observations),
        "match": True,
        "reason_codes": [],
    }
    return inventory, observations


def observe_bundle(
    case: ResolvedCaseFiles,
    source_observation: Mapping[str, Any],
    protected_before_entries: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    before_by_id = {str(item["logical_id"]): item for item in protected_before_entries}
    logical_id = f"{case.case_id}/bundle-manifest"
    if logical_id not in before_by_id:
        raise VWStop("VW-PROTECTED-TREE", f"protected BEFORE lacks {logical_id}")
    expected_manifest_sha = before_by_id[logical_id]["sha256"]
    manifest_raw, manifest_observation = stable_small_file_bytes(case.bundle_manifest, "VW-BODY-HASH")
    if manifest_observation["sha256"] != expected_manifest_sha:
        raise VWStop("VW-BODY-HASH", f"{case.case_id} bundle manifest changed after protected BEFORE")
    manifest = strict_json_bytes(manifest_raw, reason="VW-BODY-HASH")
    if not isinstance(manifest, dict):
        raise VWStop("VW-BODY-HASH", f"{case.case_id} bundle manifest is not an object")
    expected_source_sha = case.case.get("source_sha256_manifest")
    observed_source_sha = manifest.get("source_sha256")
    if (
        source_observation.get("status") != "measured"
        or source_observation.get("manifest_sha256") != expected_source_sha
        or not isinstance(observed_source_sha, str)
        or re.fullmatch(r"[0-9a-f]{64}", observed_source_sha) is None
        or observed_source_sha != expected_source_sha
    ):
        raise VWStop("VW-SOURCE-HASH", f"{case.case_id} bundle manifest source binding mismatch")
    markdown: list[dict[str, Any]] = [
        observe_markdown(
            case.raw_markdown,
            phase="raw-marker",
            ordinal=0,
            expected_sha256=case.case["markdown_sha256"],
            expected_bytes=case.case["markdown_bytes"],
        )
    ]
    analyst_records = case.case["analyst_markdown"]
    for ordinal, (path, expected) in enumerate(zip(case.analyst_markdown, analyst_records)):
        markdown.append(
            observe_markdown(
                path,
                phase="analyst",
                ordinal=ordinal,
                expected_sha256=expected["sha256"],
                expected_bytes=expected["bytes"],
            )
        )
    asset_inventory, asset_observations = observed_asset_inventory(case)
    chunking = manifest.get("chunking")
    slice_size = chunking.get("slice_size") if isinstance(chunking, dict) else None
    retained_ids, page_map, blockers = mechanical_page_map(
        source_observation=source_observation,
        asset_inventory=asset_inventory,
        asset_observations=asset_observations,
        manifest_asset_count=int(case.case["asset_count"]),
        chunking_slice_size=slice_size,
    )
    bundle = {
        "status": "measured",
        "manifest_sha256_expected": expected_manifest_sha,
        "manifest_sha256_observed": manifest_observation["sha256"],
        "manifest_source_sha256_expected": expected_source_sha,
        "manifest_source_sha256_observed": observed_source_sha,
        "markdown": markdown,
        "asset_inventory": asset_inventory,
        "asset_filename_page_ids_0based": retained_ids,
        "page_map": page_map,
        "reason_codes": [],
    }
    return bundle, blockers, asset_observations


def mechanical_page_map(
    *,
    source_observation: Mapping[str, Any],
    asset_inventory: Mapping[str, Any],
    asset_observations: Sequence[Mapping[str, Any]],
    manifest_asset_count: int,
    chunking_slice_size: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    parsed = [item for item in asset_observations if item["page_id_0based"] is not None]
    records = [
        {
            "asset_ordinal": int(item["asset_ordinal"]),
            "page_id_0based": int(item["page_id_0based"]),
            "claim_status": "Observed",
            "source_page_relation": "UNREAD",
        }
        for item in parsed
    ]
    source_ready = (
        source_observation.get("status") == "measured"
        and source_observation.get("all_hashes_match") is True
        and len(
            {
                source_observation.get("manifest_sha256"),
                source_observation.get("recorded_actual_sha256"),
                source_observation.get("observed_sha256"),
            }
        )
        == 1
    )
    inventory_ready = (
        asset_inventory.get("status") == "measured"
        and asset_inventory.get("match") is True
        and asset_inventory.get("count") == manifest_asset_count == len(asset_observations)
        and len(parsed) == len(asset_observations)
    )
    blocking: list[dict[str, Any]] = []
    if not source_ready or not inventory_ready:
        blocking.append(unread_record("VW-PAGE-MAP-UNREAD", "bundle", "page-map-unread"))
        return (
            records,
            {"state": "unread", "formula": None, "claim_status": "UNREAD", "reason_codes": ["VW-PAGE-MAP-UNREAD"]},
            blocking,
        )
    source_pages = int(source_observation["pages"])
    ids = [record["page_id_0based"] for record in records]
    if all(0 <= page_id < source_pages for page_id in ids):
        return (
            records,
            {
                "state": "as-shipped-verified",
                "formula": "source page_1based = page_id_0based + 1 (mechanical filename map only)",
                "claim_status": "Inferred",
                "reason_codes": [],
            },
            [],
        )
    sym050 = (
        source_pages > 200
        and bool(ids)
        and any(page_id >= source_pages for page_id in ids)
        and any(page_id >= 400 for page_id in ids)
        and all((page_id // 200) % 2 == 0 for page_id in ids)
        and (chunking_slice_size is None or (isinstance(chunking_slice_size, int) and not isinstance(chunking_slice_size, bool) and chunking_slice_size == 200))
    )
    repaired = [page_id - 200 * (page_id // 400) for page_id in ids]
    if sym050 and all(0 <= page_id < source_pages for page_id in repaired):
        return (
            records,
            {
                "state": "repaired-sym050",
                "formula": "source page_1based = page_id_0based + 1 - 200*(page_id_0based//400) (mechanical SYM-050 repair only)",
                "claim_status": "Inferred",
                "reason_codes": [],
            },
            [],
        )
    blocking.append(unread_record("VW-PAGE-MAP-UNREAD", "bundle", "page-map-unread"))
    return (
        records,
        {
            "state": "untrustworthy",
            "formula": None,
            "claim_status": "Inferred",
            "reason_codes": ["VW-PAGE-MAP-UNREAD"],
        },
        blocking,
    )


def assert_retained_page_map(records: Sequence[Mapping[str, Any]], fresh_asset_observations: Sequence[Mapping[str, Any]]) -> None:
    fresh = [
        {
            "asset_ordinal": int(item["asset_ordinal"]),
            "page_id_0based": int(item["page_id_0based"]),
            "claim_status": "Observed",
            "source_page_relation": "UNREAD",
        }
        for item in fresh_asset_observations
        if item["page_id_0based"] is not None
    ]
    if canonical_json_bytes(records) != canonical_json_bytes(fresh):
        raise VWStop("VW-PAGE-MAP-UNREAD", "retained filename-derived page map differs from fresh protected parse")


def execute_frozen_negative_controls() -> str:
    """Execute every packet-frozen same-check fixture through production functions."""

    gap_tiles = [
        {"bbox_px_half_open": [0, 0, 3, 1]},
        {"bbox_px_half_open": [0, 2, 3, 3]},
        {"bbox_px_half_open": [0, 1, 1, 2]},
        {"bbox_px_half_open": [2, 1, 3, 2]},
    ]
    if exact_union_area([_box(item["bbox_px_half_open"]) for item in gap_tiles]) != 8:
        raise VWStop("VW-NEGATIVE-CONTROL", "frozen gap fixture area differs")
    try:
        check_tile_union(3, 3, gap_tiles)
    except VWStop as exc:
        if exc.reason != "VW-TILE-GAP":
            raise VWStop("VW-NEGATIVE-CONTROL", "frozen gap fixture had another disposition") from exc
    else:
        raise VWStop("VW-NEGATIVE-CONTROL", "frozen gap fixture did not bite")

    def source(pages: int) -> dict[str, Any]:
        sha = "0" * 64
        return {
            "status": "measured", "manifest_sha256": sha, "recorded_actual_sha256": sha,
            "observed_sha256": sha, "pages": pages, "all_hashes_match": True,
        }

    def inventory(count: int) -> dict[str, Any]:
        return {"status": "measured", "match": True, "count": count}

    def assets(ids: Sequence[int]) -> list[dict[str, int]]:
        return [
            {"asset_ordinal": ordinal, "page_id_0based": page_id}
            for ordinal, page_id in enumerate(ids)
        ]

    _records, gross, blockers = mechanical_page_map(
        source_observation=source(10), asset_inventory=inventory(2),
        asset_observations=assets((0, 10)), manifest_asset_count=2, chunking_slice_size=None,
    )
    if gross["state"] != "untrustworthy" or not blockers or blockers[0]["reason_code"] != "VW-PAGE-MAP-UNREAD":
        raise VWStop("VW-NEGATIVE-CONTROL", "gross page-map fixture did not bite")

    fresh = assets((0, 5, 9))
    poisoned = [
        {"asset_ordinal": 0, "page_id_0based": 0, "claim_status": "Observed", "source_page_relation": "UNREAD"},
        {"asset_ordinal": 1, "page_id_0based": 6, "claim_status": "Observed", "source_page_relation": "UNREAD"},
        {"asset_ordinal": 2, "page_id_0based": 9, "claim_status": "Observed", "source_page_relation": "UNREAD"},
    ]
    try:
        assert_retained_page_map(poisoned, fresh)
    except VWStop as exc:
        if exc.reason != "VW-PAGE-MAP-UNREAD":
            raise VWStop("VW-NEGATIVE-CONTROL", "in-range page-map poison had another disposition") from exc
    else:
        raise VWStop("VW-NEGATIVE-CONTROL", "in-range page-map poison did not bite")

    _records, repaired, blockers = mechanical_page_map(
        source_observation=source(450), asset_inventory=inventory(5),
        asset_observations=assets((0, 199, 400, 599, 800)), manifest_asset_count=5,
        chunking_slice_size=200,
    )
    repaired_ids = [page_id - 200 * (page_id // 400) for page_id in (0, 199, 400, 599, 800)]
    if repaired["state"] != "repaired-sym050" or blockers or repaired_ids != [0, 199, 200, 399, 400]:
        raise VWStop("VW-NEGATIVE-CONTROL", "SYM-050 positive fixture did not pass")
    return PACKET_SHA256


def _windows_process_module_paths() -> list[Path]:
    if os.name != "nt":
        raise VWStop("VW-DEPENDENCY-DRIFT", "runtime module inventory requires Windows")
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    process = kernel32.GetCurrentProcess()
    list_modules_all = 0x03
    needed = ctypes.c_ulong()
    capacity = 256
    while True:
        modules = (ctypes.c_void_p * capacity)()
        if not psapi.EnumProcessModulesEx(
            process,
            ctypes.byref(modules),
            ctypes.sizeof(modules),
            ctypes.byref(needed),
            list_modules_all,
        ):
            raise VWStop("VW-DEPENDENCY-DRIFT", "EnumProcessModulesEx failed")
        count = needed.value // ctypes.sizeof(ctypes.c_void_p)
        if count <= capacity:
            break
        capacity = count + 32
    paths: list[Path] = []
    for module in modules[:count]:
        buffer = ctypes.create_unicode_buffer(32768)
        length = psapi.GetModuleFileNameExW(process, module, buffer, len(buffer))
        if length:
            paths.append(Path(buffer.value))
    return paths


def runtime_module_inventory() -> list[dict[str, Any]]:
    main_buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.WinDLL("kernel32", use_last_error=True).GetModuleFileNameW(None, main_buffer, len(main_buffer)):
        raise VWStop("VW-DEPENDENCY-DRIFT", "GetModuleFileNameW failed")
    logical_paths: dict[str, Path] = {
        "git_executable": GIT_EXECUTABLE,
        "python_executable": Path(sys.executable),
        "python_process_image": Path(main_buffer.value),
        "pymupdf_package_init": Path(pymupdf.__file__),
    }
    for name, module in sorted(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file or not name.startswith("pymupdf"):
            continue
        path = Path(module_file)
        if path.suffix.casefold() in (".pyd", ".dll"):
            logical_paths[f"pymupdf_extension.{path.name.casefold()}"] = path
    loaded_paths = _windows_process_module_paths()
    native_patterns = ("python3*.dll", "_mupdf*.pyd", "_extra*.pyd", "mupdfcpp*.dll")
    for path in loaded_paths:
        basename = path.name.casefold()
        if any(fnmatch.fnmatchcase(basename, pattern) for pattern in native_patterns):
            logical_paths[basename] = path
    names = [path.name.casefold() for path in loaded_paths]
    if not any(fnmatch.fnmatchcase(name, "python3*.dll") for name in names):
        raise VWStop("VW-DEPENDENCY-DRIFT", "loaded python3 native component is missing")
    if not any(fnmatch.fnmatchcase(name, "_mupdf*.pyd") for name in names):
        raise VWStop("VW-DEPENDENCY-DRIFT", "loaded _mupdf native component is missing")
    if not any(fnmatch.fnmatchcase(name, "mupdfcpp*.dll") for name in names):
        raise VWStop("VW-DEPENDENCY-DRIFT", "loaded mupdfcpp native component is missing")
    inventory: list[dict[str, Any]] = []
    for logical_name, path in sorted(logical_paths.items()):
        observation = (
            _verified_git_executable_observation()
            if logical_name == "git_executable"
            else stable_file_observation(path, "VW-DEPENDENCY-DRIFT")
        )
        inventory.append({"logical_name": logical_name, **observation})
    if len(inventory) < 7:
        raise VWStop("VW-DEPENDENCY-DRIFT", f"runtime inventory has only {len(inventory)} entries")
    return inventory


def producer_observation(repo_root: Path, configuration_sha256: str) -> dict[str, Any]:
    selftest = repo_root / "windows-converter/visual_witness_capture_selftest.py"
    if not selftest.is_file():
        raise VWStop("VW-DEPENDENCY-DRIFT", "semantic validator code file is missing")
    return {
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "pymupdf_version": str(pymupdf.__version__),
        "mupdf_version": ".".join(map(str, pymupdf.mupdf_version_tuple)),
        "runtime_modules": runtime_module_inventory(),
        "capture_code_sha256": sha256_file(Path(__file__)),
        "semantic_validator_code_sha256": sha256_file(selftest),
        "capture_schema_sha256": CAPTURE_SCHEMA_SHA256,
        "packet_sha256": PACKET_SHA256,
        "config_sha256": configuration_sha256,
    }


def case_class_census(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    census: list[dict[str, Any]] = []
    for class_name in CLASS_ORDER:
        procedures = [
            next(item for item in page["class_procedures"] if item["class"] == class_name)
            for page in pages
        ]
        unread_reasons = sorted({reason for procedure in procedures for reason in procedure["reason_codes"]})
        if any(procedure["status"] == "UNREAD" for procedure in procedures):
            census.append(
                {
                    "class": class_name,
                    "procedure_status": "UNREAD",
                    "candidate_count": None,
                    "blocking": True,
                    "semantic_truth_status": "UNREAD",
                    "reason_codes": unread_reasons or ["UNREAD"],
                }
            )
        else:
            census.append(
                {
                    "class": class_name,
                    "procedure_status": "measured",
                    "candidate_count": sum(int(procedure["candidate_count"]) for procedure in procedures),
                    "blocking": False,
                    "semantic_truth_status": "UNREAD",
                    "reason_codes": [],
                }
            )
    return census


def aggregate_coverage(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pages = [page for case in cases for page in case["pages"]]
    readable = [page for page in pages if page["tile_union"]["status"] == "measured"]
    unread = [page for page in pages if page["tile_union"]["status"] == "UNREAD"]
    numerator = sum(int(page["tile_union"]["numerator"]) for page in readable)
    denominator = sum(int(page["tile_union"]["denominator"]) for page in readable)
    base = {
        "numerator_name": "valid rendered page pixels covered by at least one declared base tile",
        "denominator_name": "valid rendered page pixels on attempted readable pages",
        "conditions": {
            "render_dpi": DPI,
            "tile_size_px": TILE_SIZE,
            "stride_px": TILE_STRIDE,
            "readable_pages": len(readable),
            "unread_pages": len(unread),
        },
    }
    if denominator < 1:
        return {
            "status": "UNREAD",
            **base,
            "numerator": None,
            "denominator": None,
            "value": None,
            "reason_codes": sorted({reason for page in unread for reason in page["tile_union"]["reason_codes"]}) or ["UNREAD"],
        }
    return {
        "status": "measured",
        **base,
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator,
        "reason_codes": [],
    }


def build_capture_payload(cases: Sequence[Mapping[str, Any]], configuration_sha256: str) -> dict[str, Any]:
    ordered = sorted(cases, key=lambda case: ALLOWED_CASE_IDS.index(case["case_id"]))
    if [case["case_id"] for case in ordered] != list(ALLOWED_CASE_IDS):
        raise VWStop("VW-IDENTITY", "capture payload cases are not exact calibration set")
    completed = sum(case["procedure_status"] == "measured" for case in ordered)
    payload: dict[str, Any] = {
        "event_id": "VW-E2",
        "event_revision": "VW-E2-R2",
        "packet_sha256": PACKET_SHA256,
        "parent_contract_sha256": PARENT_CONTRACT_SHA256,
        "capture_schema_sha256": CAPTURE_SCHEMA_SHA256,
        "config_sha256": configuration_sha256,
        "case_census": {
            "declared": 3,
            "attempted": 3,
            "completed": completed,
            "unread": 3 - completed,
            "case_ids": list(ALLOWED_CASE_IDS),
        },
        "cases": ordered,
        "metrics": {"declared_page_pixel_coverage": aggregate_coverage(ordered)},
        "capture_payload_sha256": "0" * 64,
        "next_event_authority": "UNSIGNED",
    }
    payload["capture_payload_sha256"] = capture_payload_sha256(payload)
    return payload


def unread_source_observation(case: ResolvedCaseFiles, reason_code: str) -> dict[str, Any]:
    return {
        "status": "UNREAD",
        "manifest_sha256": case.case["source_sha256_manifest"],
        "recorded_actual_sha256": case.case["source_sha256_actual"],
        "observed_sha256": None,
        "bytes": None,
        "pages": None,
        "all_hashes_match": None,
        "reason_codes": [reason_code],
    }


def unread_bundle_observation(
    case: ResolvedCaseFiles,
    reason_code: str,
    protected_before_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    before_by_id = {str(item["logical_id"]): item for item in protected_before_entries}
    manifest_entry = before_by_id.get(f"{case.case_id}/bundle-manifest")
    if manifest_entry is None:
        raise VWStop("VW-PROTECTED-TREE", "cannot construct truthful unread bundle without protected manifest BEFORE")
    markdown = [
        {
            "phase": "raw-marker",
            "variant_ordinal": 0,
            "status": "UNREAD",
            "expected_sha256": case.case["markdown_sha256"],
            "observed_sha256": None,
            "bytes": None,
            "match": None,
            "reason_codes": [reason_code],
        }
    ]
    markdown.extend(
        {
            "phase": "analyst",
            "variant_ordinal": ordinal,
            "status": "UNREAD",
            "expected_sha256": item["sha256"],
            "observed_sha256": None,
            "bytes": None,
            "match": None,
            "reason_codes": [reason_code],
        }
        for ordinal, item in enumerate(case.case["analyst_markdown"])
    )
    return {
        "status": "UNREAD",
        "manifest_sha256_expected": manifest_entry["sha256"],
        "manifest_sha256_observed": None,
        "manifest_source_sha256_expected": case.case["source_sha256_manifest"],
        "manifest_source_sha256_observed": None,
        "markdown": markdown,
        "asset_inventory": {
            "status": "UNREAD",
            "expected_sha256": case.case["asset_inventory_sha256"],
            "observed_sha256": None,
            "count": None,
            "match": None,
            "reason_codes": [reason_code],
        },
        "asset_filename_page_ids_0based": [],
        "page_map": {"state": "unread", "formula": None, "claim_status": "UNREAD", "reason_codes": ["VW-PAGE-MAP-UNREAD"]},
        "reason_codes": [reason_code],
    }


def _peak_working_set() -> int:
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise VWStop("VW-DEPENDENCY-DRIFT", "GetProcessMemoryInfo failed")
    return int(counters.PeakWorkingSetSize)


def scratch_tree_bytes(root: Path) -> int:
    total = 0
    for directory, subdirectories, files in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        if _is_reparse(directory_path):
            raise VWStop("VW-PRIVACY", "reparse point appeared in event scratch")
        for name in subdirectories:
            if _is_reparse(directory_path / name):
                raise VWStop("VW-PRIVACY", "reparse child appeared in event scratch")
        for name in files:
            path = directory_path / name
            if _is_reparse(path):
                raise VWStop("VW-PRIVACY", "reparse file appeared in event scratch")
            total += path.stat().st_size
    return total


def capture_case(
    case: ResolvedCaseFiles,
    protected_before_entries: Sequence[Mapping[str, Any]],
    configuration_sha256: str,
    scratch_run: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    started_wall, started_cpu = time.perf_counter(), time.process_time()
    scratch_peak = scratch_tree_bytes(scratch_run)
    fresh_asset_observations: list[dict[str, Any]] = []
    try:
        source = observe_source(case)
        bundle, bundle_unreads, fresh_asset_observations = observe_bundle(case, source, protected_before_entries)
        pages: list[dict[str, Any]] = []
        with pymupdf.open(case.source) as document:
            if document.page_count != case.case["pages"]:
                raise VWStop("VW-SOURCE-HASH", f"{case.case_id} page count changed before capture")
            for page_index in range(document.page_count):
                try:
                    capture = capture_page(
                        document[page_index],
                        page_1based=page_index + 1,
                        source_observation=source,
                        configuration_sha256=configuration_sha256,
                    )
                    pages.append(capture.report)
                    capture.clear()
                except VWStop as exc:
                    pages.append(unread_page(page_index + 1, exc.reason))
                scratch_peak = max(scratch_peak, scratch_tree_bytes(scratch_run))
                if scratch_peak > SCRATCH_HARD_CAP:
                    raise VWStop("VW-CLEANUP", "event scratch exceeded hard cap")
        unreads = list(bundle_unreads) + [item for page in pages for item in page["unreads"]]
    except VWStop as exc:
        source = unread_source_observation(case, exc.reason)
        bundle = unread_bundle_observation(case, exc.reason, protected_before_entries)
        pages = [unread_page(page_1based, exc.reason) for page_1based in range(1, int(case.case["pages"]) + 1)]
        unreads = [
            unread_record(exc.reason, "event", DETAIL_BY_REASON.get(exc.reason, "procedural-unread")),
            *[item for page in pages for item in page["unreads"]],
        ]
    procedure_status = "UNREAD" if unreads else "measured"
    report = {
        "case_id": case.case_id,
        "split": "calibration",
        "source": source,
        "bundle": bundle,
        "procedure_status": procedure_status,
        "blocking": procedure_status == "UNREAD",
        "pages": pages,
        "class_census": case_class_census(pages),
        "conflicts": [],
        "unreads": sorted(unreads, key=lambda item: (item["scope"], item["reason_code"], item["blocking"], item["detail_code"])),
    }
    resource = {
        "case_id": case.case_id,
        "status": "measured",
        "wall_seconds": time.perf_counter() - started_wall,
        "cpu_seconds": time.process_time() - started_cpu,
        "peak_working_set_bytes": _peak_working_set(),
        "scratch_peak_bytes": scratch_peak,
        "reason_codes": [],
    }
    return report, resource, fresh_asset_observations


def _case_worker_entry(
    connection: Any,
    case: ResolvedCaseFiles,
    protected_before_entries: Sequence[Mapping[str, Any]],
    configuration_sha256: str,
    scratch_run: Path,
) -> None:
    EVENT_ACTIVITY.reset()
    try:
        install_event_activity_audit()
        value = capture_case(case, protected_before_entries, configuration_sha256, scratch_run)
        connection.send(("ok", value, event_activity_snapshot()))
    except BaseException as exc:
        reason = exc.reason if isinstance(exc, VWStop) else "UNREAD"
        connection.send((
            "error",
            {"reason_code": reason, "detail_code": type(exc).__name__},
            event_activity_snapshot(),
        ))
    finally:
        connection.close()


def run_case_worker(
    case: ResolvedCaseFiles,
    protected_before_entries: Sequence[Mapping[str, Any]],
    configuration_sha256: str,
    scratch_run: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    context = mp.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    worker = context.Process(
        target=_case_worker_entry,
        args=(child_connection, case, list(protected_before_entries), configuration_sha256, scratch_run),
        name=f"vw-e2-{case.case_id}",
    )
    worker.start()
    if worker.pid is None:
        raise VWStop("VW-DEPENDENCY-DRIFT", "case worker did not receive a PID")
    EVENT_CHILD_PIDS.add(int(worker.pid))
    child_connection.close()
    try:
        while not parent_connection.poll(1.0):
            if not worker.is_alive():
                worker.join()
                raise VWStop("UNREAD", f"{case.case_id} worker exited before returning evidence")
        message = parent_connection.recv()
        if not isinstance(message, tuple) or len(message) != 3:
            raise VWStop("UNREAD", f"{case.case_id} worker activity evidence unread")
        status, value, activity = message
        if not isinstance(activity, dict):
            raise VWStop("UNREAD", f"{case.case_id} worker activity evidence unread")
        reconcile_event_activity(activity)
    except EOFError as exc:
        raise VWStop("UNREAD", f"{case.case_id} worker pipe closed") from exc
    finally:
        parent_connection.close()
        worker.join()
        if worker.pid is not None and worker.exitcode is not None:
            EVENT_CHILD_EXITED_PIDS.add(int(worker.pid))
    if worker.exitcode != 0 or status != "ok":
        reason = value.get("reason_code", "UNREAD") if isinstance(value, dict) else "UNREAD"
        raise VWStop(reason, f"{case.case_id} fresh worker failed")
    return value


def _activity_probe_worker_entry(connection: Any, probe: str) -> None:
    EVENT_ACTIVITY.reset()
    try:
        install_event_activity_audit()
        try:
            if probe == "network-loopback":
                import socket

                candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    candidate.connect(("127.0.0.1", 9))
                finally:
                    candidate.close()
            elif probe == "gpu-library":
                ctypes.WinDLL("nvcuda.dll")
            else:
                raise ValueError("unknown activity probe")
        except PermissionError:
            pass
        connection.send(event_activity_snapshot())
    finally:
        connection.close()


def run_activity_probe_worker(probe: str) -> dict[str, Any]:
    """Hermetic production instrumentation probe; every operation is denied by the child audit hook."""
    context = mp.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    worker = context.Process(target=_activity_probe_worker_entry, args=(child_connection, probe))
    worker.start()
    if worker.pid is None:
        raise VWStop("UNREAD", "activity probe worker PID unread")
    EVENT_CHILD_PIDS.add(int(worker.pid))
    child_connection.close()
    try:
        if not parent_connection.poll(20.0):
            raise VWStop("UNREAD", "activity probe worker timeout")
        snapshot = parent_connection.recv()
    finally:
        parent_connection.close()
        worker.join(timeout=5.0)
        if worker.is_alive():
            worker.kill()
            worker.join()
        if worker.pid is not None and worker.exitcode is not None:
            EVENT_CHILD_EXITED_PIDS.add(int(worker.pid))
    if worker.exitcode != 0 or not isinstance(snapshot, dict):
        raise VWStop("UNREAD", "activity probe worker evidence unread")
    reconcile_event_activity(snapshot)
    return snapshot


def run_all_case_workers(
    cases: Sequence[ResolvedCaseFiles],
    protected_before_entries: Sequence[Mapping[str, Any]],
    configuration_sha256: str,
    scratch_run: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    reports: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    fresh_assets: dict[str, list[dict[str, Any]]] = {}
    for expected_id, case in zip(ALLOWED_CASE_IDS, cases):
        if case.case_id != expected_id:
            raise VWStop("VW-IDENTITY", "case worker order is not canonical")
        report, resource, observations = run_case_worker(
            case,
            protected_before_entries,
            configuration_sha256,
            scratch_run,
        )
        reports.append(report)
        resources.append(resource)
        fresh_assets[case.case_id] = observations
    return reports, resources, fresh_assets


def require_completed_cases(case_reports: Sequence[Mapping[str, Any]]) -> None:
    for case in case_reports:
        if case.get("procedure_status") != "measured" or case.get("unreads") or case.get("conflicts"):
            unreads = case.get("unreads")
            reason = unreads[0]["reason_code"] if isinstance(unreads, list) and unreads else "UNREAD"
            raise VWStop(reason, "calibration case did not complete")


class SemanticFailure(VWStop):
    """One exact named semantic predicate failed or was procedurally unread."""

    def __init__(self, name: str, reason: str, *, unread: bool = False):
        super().__init__(reason, name)
        self.name = name
        self.unread = unread


CHECK_REASON_CODES = {
    "canonical-json-and-array-order": "VW-IDENTITY",
    "report-id": "VW-IDENTITY",
    "capture-payload-hash": "VW-IDENTITY",
    "packet-parent-schema-config-binding": "GROUND-DRIFT",
    "case-order-uniqueness": "VW-IDENTITY",
    "case-census-arithmetic": "VW-IDENTITY",
    "page-count-contiguity": "VW-IDENTITY",
    "status-null-reason-coherence": "UNREAD",
    "source-bundle-hashes": "VW-SOURCE-HASH",
    "page-map-coherence": "VW-PAGE-MAP-UNREAD",
    "bbox-order-range-transform": "VW-COORDINATE-UNREAD",
    "render-rgb-arithmetic": "VW-RENDER-UNREAD",
    "tile-id-bbox-reference": "VW-TILE-GAP",
    "tile-rgb-arithmetic": "VW-TILE-GAP",
    "tile-union-coverage": "VW-TILE-GAP",
    "primitive-kind-attributes-geometry": "VW-IDENTITY",
    "primitive-id": "VW-IDENTITY",
    "candidate-class-basis-evidence": "VW-IDENTITY",
    "candidate-source-references": "VW-IDENTITY",
    "candidate-id": "VW-IDENTITY",
    "class-procedure-completeness": "UNREAD",
    "class-census-reconciliation": "VW-IDENTITY",
    "relationship-reference-geometry-id": "VW-IDENTITY",
    "edge-recovery-reference-containment": "VW-TILE-GAP",
    "crop-rgb-arithmetic": "VW-CROP-BOUNDS",
    "captured-text-state-hash": "VW-IDENTITY",
    "metric-arithmetic": "VW-IDENTITY",
    "resource-worker-reconciliation": "VW-DEPENDENCY-DRIFT",
    "protected-tree-digest": "VW-PROTECTED-TREE",
    "privacy-heldout-cleanup-redaction": "VW-PRIVACY",
    "independent-verification-binding": "VW-NEGATIVE-CONTROL",
    "semantic-unread-boundary": "UNREAD",
    "output-root-realpath-containment": "GROUND-DRIFT",
    "residue-privacy-census": "VW-CLEANUP",
}
ORDINARY_CHECK_NAMES = tuple(
    name for name in SEMANTIC_CHECK_NAMES if name not in ("report-id", "independent-verification-binding")
)


def _semantic_assert(name: str, condition: bool, *, unread: bool = False) -> None:
    if not condition:
        raise SemanticFailure(name, CHECK_REASON_CODES[name], unread=unread)


def _schema_engine(repo_root: Path) -> Any:
    module_name = "_visual_witness_capture_schema_engine"
    if module_name in sys.modules:
        return sys.modules[module_name]
    module_path = repo_root / "windows-converter/visual_witness_capture_selftest.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise VWStop("VW-DEPENDENCY-DRIFT", "semantic validator module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.modules.setdefault("visual_witness_capture", sys.modules[__name__])
    spec.loader.exec_module(module)
    return module


def assert_capture_schema(repo_root: Path, report: Mapping[str, Any]) -> None:
    engine = _schema_engine(repo_root)
    schema = engine.load_bound_schema(repo_root)
    engine.assert_bound_schema(report, schema)


def _canonical_object_unique(items: Sequence[Any]) -> bool:
    return len({canonical_json_bytes(item) for item in items}) == len(items)


def _sorted_unique_strings(items: Any) -> bool:
    return isinstance(items, list) and all(isinstance(item, str) for item in items) and items == sorted(set(items))


def _disposition_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    reason = item.get("reason_code")
    evidence = item.get("evidence_sha256")
    return (
        item.get("scope"),
        (0, "") if reason is None else (1, reason),
        item.get("blocking"),
        item.get("detail_code"),
        (0, "") if evidence is None else (1, evidence),
    )


def _recursive_order_contract(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "reason_codes" and not _sorted_unique_strings(child):
                return False
            if key in ("conflicts", "unreads", "inaccessible"):
                if not isinstance(child, list) or child != sorted(child, key=_disposition_key):
                    return False
                if key == "inaccessible" and not _canonical_object_unique(child):
                    return False
            if not _recursive_order_contract(child):
                return False
    elif isinstance(value, list):
        return all(_recursive_order_contract(child) for child in value)
    return True


def _candidate_deep_order(candidate: Mapping[str, Any], tile_by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    recovery = candidate["edge_recovery"]
    touches = recovery["touched_internal_edges"]
    relation_rank = {"equals-min-boundary": 0, "equals-max-boundary": 1, "straddles": 2}
    direction_rank = {"negative": 0, "positive": 1, "both": 2}
    def touch_key(item):
        return (
            0 if item["axis"] == "x" else 1,
            item["coordinate_px"],
            relation_rank[item["relation"]],
            direction_rank[item["neighbor_direction"]],
        )
    if touches != sorted(touches, key=touch_key) or not _canonical_object_unique(touches):
        return False
    recovery_ids = recovery["recovery_tile_ids"]
    if any(tile_id not in tile_by_id for tile_id in recovery_ids):
        return False
    expected_recovery = sorted(
        set(recovery_ids),
        key=lambda tile_id: (
            tile_by_id[tile_id]["bbox_px_half_open"][1],
            tile_by_id[tile_id]["bbox_px_half_open"][0],
            tile_id,
        ),
    )
    if recovery_ids != expected_recovery:
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
            def track_key(track):
                return (
                    track["axis_px"], track["extent_start_px"], track["extent_end_px"],
                    tuple(track["member_primitive_ids"]),
                )
            if tracks != sorted(tracks, key=track_key) or not _canonical_object_unique(tracks):
                return False
        cells = measurements["closed_cells"]
        for cell in cells:
            if not _sorted_unique_strings(cell["text_primitive_ids"]):
                return False
        if cells != sorted(cells, key=lambda cell: (cell["row_index_0based"], cell["column_index_0based"], cell["cell_id"])):
            return False
        if not _canonical_object_unique(cells) or not _sorted_unique_strings(measurements["occupied_cell_ids"]):
            return False
    return True


def _canonical_arrays(report: Mapping[str, Any]) -> bool:
    payload = report["capture_payload"]
    cases = payload["cases"]
    if payload["case_census"]["case_ids"] != list(ALLOWED_CASE_IDS):
        return False
    if [case["case_id"] for case in cases] != list(ALLOWED_CASE_IDS):
        return False
    primitive_rank = {"raster": 0, "vector": 1, "text": 2}
    for case in cases:
        markdown = case["bundle"]["markdown"]
        if (
            not markdown
            or markdown[0].get("phase") != "raw-marker"
            or markdown[0].get("variant_ordinal") != 0
            or [item.get("phase") for item in markdown[1:]] != ["analyst"] * (len(markdown) - 1)
            or [item.get("variant_ordinal") for item in markdown[1:]] != list(range(len(markdown) - 1))
        ):
            return False
        assets = case["bundle"]["asset_filename_page_ids_0based"]
        if [item["asset_ordinal"] for item in assets] != list(range(len(assets))) or not _canonical_object_unique(assets):
            return False
        if [page["page_1based"] for page in case["pages"]] != list(range(1, len(case["pages"]) + 1)):
            return False
        if [item["class"] for item in case["class_census"]] != list(CLASS_ORDER):
            return False
        for page in case["pages"]:
            tiles = page["tiles"]
            if tiles != sorted(tiles, key=lambda item: (item["bbox_px_half_open"][1], item["bbox_px_half_open"][0], item["tile_id"])) or not _canonical_object_unique(tiles):
                return False
            tile_by_id = {item["tile_id"]: item for item in tiles}
            if len(tile_by_id) != len(tiles):
                return False
            primitives = page["primitive_facts"]
            if primitives != sorted(primitives, key=lambda item: (primitive_rank[item["kind"]], *item["bbox_px_half_open"], item["primitive_id"])) or not _canonical_object_unique(primitives):
                return False
            if page["region_candidates"] != sorted(page["region_candidates"], key=lambda item: item["candidate_id"]) or not _canonical_object_unique(page["region_candidates"]):
                return False
            if page["relationships"] != sorted(page["relationships"], key=lambda item: (item["source_candidate_id"], item["target_candidate_id"], item["kind"])) or not _canonical_object_unique(page["relationships"]):
                return False
            if [item["class"] for item in page["class_procedures"]] != list(CLASS_ORDER):
                return False
            for primitive in primitives:
                provenance = primitive["source_evidence"]["provenance_records"]
                names = (
                    "engine_list_index_0based", "drawing_list_index_0based", "drawing_seqno_observed",
                    "item_list_index_0based", "emitted_edge_index_0based", "engine_number_observed",
                )
                def key(item):
                    return tuple(-1 if item[name] is None else item[name] for name in names)
                if provenance != sorted(provenance, key=key) or len({canonical_json_bytes(item) for item in provenance}) != len(provenance):
                    return False
            for candidate in page["region_candidates"]:
                if candidate["classes"] != [name for name in CLASS_ORDER if name in set(candidate["classes"])]:
                    return False
                expected_rules = [RULE_IDS[name] for name in candidate["classes"]]
                if candidate["class_basis"] != expected_rules:
                    return False
                if [item["rule_id"] for item in candidate["class_evidence"]] != expected_rules:
                    return False
                if not _canonical_object_unique(candidate["class_evidence"]):
                    return False
                for name in ("source_primitive_ids", "intersecting_tile_ids"):
                    if candidate[name] != sorted(set(candidate[name])):
                        return False
                if not _candidate_deep_order(candidate, tile_by_id):
                    return False
    if not _recursive_order_contract(report):
        return False
    modules = report["run_observations"]["producer"]["runtime_modules"]
    if modules != sorted(modules, key=lambda item: item["logical_name"]) or not _canonical_object_unique(modules):
        return False
    if len({item["logical_name"] for item in modules}) != len(modules):
        return False
    observations = report["run_observations"]
    workers = observations["resources"]["case_workers"]
    if [item["case_id"] for item in workers] != list(ALLOWED_CASE_IDS):
        return False
    residue = observations["residue"]
    for name in ("files", "processes", "gpu_owners"):
        if not _sorted_unique_strings(residue[name]):
            return False
    if residue["ports"] != sorted(set(residue["ports"])):
        return False
    checks = report.get("semantic_checks")
    if checks is not None and [item["name"] for item in checks] != list(SEMANTIC_CHECK_NAMES):
        return False
    return True


def _box_strings_valid(values: Any) -> bool:
    return (
        isinstance(values, list)
        and len(values) == 4
        and all(isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{6}", value) for value in values)
        and float(values[0]) < float(values[2])
        and float(values[1]) < float(values[3])
    )


def validate_ordinary_semantics(
    report: Mapping[str, Any],
    *,
    repo_root: Path,
    roots: OutputRoots,
    fresh_assets: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    payload = report["capture_payload"]
    observations = report["run_observations"]

    _semantic_assert("canonical-json-and-array-order", _canonical_arrays(report))
    _semantic_assert("capture-payload-hash", payload["capture_payload_sha256"] == capture_payload_sha256(payload))
    _semantic_assert(
        "packet-parent-schema-config-binding",
        payload["packet_sha256"] == PACKET_SHA256
        and payload["parent_contract_sha256"] == PARENT_CONTRACT_SHA256
        and payload["capture_schema_sha256"] == CAPTURE_SCHEMA_SHA256
        and payload["config_sha256"] == EXPECTED_CONFIG_SHA256
        and observations["producer"]["packet_sha256"] == PACKET_SHA256
        and observations["producer"]["capture_schema_sha256"] == CAPTURE_SCHEMA_SHA256
        and observations["producer"]["config_sha256"] == EXPECTED_CONFIG_SHA256,
    )
    cases = payload["cases"]
    _semantic_assert("case-order-uniqueness", [case["case_id"] for case in cases] == list(ALLOWED_CASE_IDS))
    census = payload["case_census"]
    completed = sum(case["procedure_status"] == "measured" for case in cases)
    _semantic_assert(
        "case-census-arithmetic",
        census == {"declared": 3, "attempted": 3, "completed": completed, "unread": 3 - completed, "case_ids": list(ALLOWED_CASE_IDS)},
    )
    expected_pages = {"VW-T01": 104, "VW-T02": 184, "VW-T03": 465}
    _semantic_assert(
        "page-count-contiguity",
        all(
            len(case["pages"]) == expected_pages[case["case_id"]]
            and [page["page_1based"] for page in case["pages"]] == list(range(1, expected_pages[case["case_id"]] + 1))
            for case in cases
        ),
    )
    procedural_unread = any(
        case["procedure_status"] != "measured"
        or case["blocking"]
        or case["conflicts"]
        or case["unreads"]
        or any(page["status"] != "measured" or page["unreads"] for page in case["pages"])
        for case in cases
    )
    _semantic_assert("status-null-reason-coherence", not procedural_unread, unread=procedural_unread)

    source_bundle_ok = True
    for case in cases:
        source = case["source"]
        bundle = case["bundle"]
        source_bundle_ok &= (
            source["status"] == "measured"
            and source["all_hashes_match"] is True
            and len({source["manifest_sha256"], source["recorded_actual_sha256"], source["observed_sha256"]}) == 1
            and bundle["status"] == "measured"
            and bundle["manifest_sha256_expected"] == bundle["manifest_sha256_observed"]
            and bundle["manifest_source_sha256_expected"] == bundle["manifest_source_sha256_observed"] == source["observed_sha256"]
            and all(item["status"] == "measured" and item["match"] is True and item["expected_sha256"] == item["observed_sha256"] for item in bundle["markdown"])
            and bundle["asset_inventory"]["status"] == "measured"
            and bundle["asset_inventory"]["match"] is True
            and bundle["asset_inventory"]["expected_sha256"] == bundle["asset_inventory"]["observed_sha256"]
        )
    _semantic_assert("source-bundle-hashes", source_bundle_ok)
    try:
        for case in cases:
            assert_retained_page_map(
                case["bundle"]["asset_filename_page_ids_0based"],
                fresh_assets[case["case_id"]],
            )
            if case["bundle"]["page_map"]["state"] not in ("as-shipped-verified", "repaired-sym050"):
                raise VWStop("VW-PAGE-MAP-UNREAD", "page map is not completion-eligible")
    except (KeyError, VWStop):
        raise SemanticFailure("page-map-coherence", CHECK_REASON_CODES["page-map-coherence"])

    bbox_ok = True
    render_ok = True
    tile_ref_ok = True
    tile_rgb_ok = True
    tile_union_ok = True
    primitive_shape_ok = True
    primitive_id_ok = True
    candidate_basis_ok = True
    candidate_refs_ok = True
    candidate_id_ok = True
    class_complete_ok = True
    census_ok = True
    relationship_ok = True
    recovery_ok = True
    crop_ok = True
    text_ok = True
    for case in cases:
        source_sha = case["source"]["observed_sha256"]
        for page in case["pages"]:
            render = page["render"]
            width, height = render["width_px"], render["height_px"]
            render_ok &= (
                render["status"] == "measured"
                and isinstance(width, int) and isinstance(height, int)
                and 1 <= width <= MAX_RENDER_AXIS_PX and 1 <= height <= MAX_RENDER_AXIS_PX
                and width * height <= MAX_RENDER_PIXELS
                and render["valid_page_pixels"] == width * height
                and render["rgb_bytes"] == width * height * 3
            )
            bbox_ok &= all(_box_strings_valid(page[name]) for name in ("media_box_mupdf_pt", "crop_box_mupdf_pt", "media_box_pdf_user_space_pt", "crop_box_pdf_user_space_pt"))
            expected_tiles = make_tiles(page["page_1based"], width, height)
            retained_tile_projection = [{"tile_id": item["tile_id"], "bbox_px_half_open": item["bbox_px_half_open"]} for item in page["tiles"]]
            tile_ref_ok &= retained_tile_projection == expected_tiles
            tile_ids = {item["tile_id"] for item in page["tiles"]}
            tile_rgb_ok &= all(
                item["rgb_bytes"] == (item["bbox_px_half_open"][2] - item["bbox_px_half_open"][0]) * (item["bbox_px_half_open"][3] - item["bbox_px_half_open"][1]) * 3
                and re.fullmatch(r"[0-9a-f]{64}", item["rgb_sha256"]) is not None
                for item in page["tiles"]
            )
            try:
                union = check_tile_union(width, height, page["tiles"])
                tile_union_ok &= page["tile_union"] == union
            except VWStop:
                tile_union_ok = False
            primitives = {item["primitive_id"]: item for item in page["primitive_facts"]}
            for primitive in primitives.values():
                box = primitive["bbox_px_half_open"]
                bbox_ok &= isinstance(box, list) and len(box) == 4 and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height
                geometry = primitive["geometry"]
                primitive_shape_ok &= primitive["kind"] in ("raster", "vector", "text") and isinstance(geometry, dict)
                if primitive["kind"] == "vector" and geometry["kind"] in ("line", "rectangle-edge", "quad-edge"):
                    primitive_shape_ok &= [geometry["p0"], geometry["p1"]] == sorted([geometry["p0"], geometry["p1"]], key=tuple)
                projected = dict(primitive)
                projected.update(source_sha256=source_sha, page_1based=page["page_1based"])
                primitive_id_ok &= primitive["primitive_id"] == primitive_id(projected)
            candidates = {item["candidate_id"]: item for item in page["region_candidates"]}
            for candidate in candidates.values():
                candidate_box = _box(candidate["bbox_px_half_open"])
                classes = candidate["classes"]
                rules = [RULE_IDS[name] for name in classes]
                candidate_basis_ok &= candidate["class_basis"] == rules and [item["rule_id"] for item in candidate["class_evidence"]] == rules
                if "table" in classes:
                    table_evidence = next(item for item in candidate["class_evidence"] if item["rule_id"] == RULE_IDS["table"])
                    candidate_basis_ok &= table_evidence["measurements"]["parent_stroke_cluster_id"] == candidate["candidate_id"]
                candidate_refs_ok &= set(candidate["source_primitive_ids"]) <= set(primitives) and set(candidate["intersecting_tile_ids"]) <= tile_ids
                candidate_refs_ok &= candidate["intersecting_tile_ids"] == _intersecting_tiles(candidate_box, page["tiles"])
                projected_candidate = dict(candidate)
                projected_candidate.update(source_sha256=source_sha, page_1based=page["page_1based"], config_sha256=payload["config_sha256"])
                candidate_id_ok &= candidate["candidate_id"] == candidate_id(projected_candidate)
                recovery = candidate["edge_recovery"]
                if recovery["boundary_resolution"] == "not-required":
                    recovery_ok &= (
                        recovery["touched_internal_edges"] == [] and recovery["recovery_tile_ids"] == []
                        and recovery["recovery_bbox_px_half_open"] is None and recovery["recovery_rgb_bytes"] is None
                        and recovery["recovery_rgb_sha256"] is None and recovery["candidate_strictly_contained"] is False
                    )
                else:
                    recovery_box = _box(recovery["recovery_bbox_px_half_open"])
                    recovery_ok &= (
                        recovery["boundary_resolution"] == "whole-page-recrop"
                        and bool(recovery["touched_internal_edges"])
                        and set(recovery["recovery_tile_ids"]) <= tile_ids
                        and recovery_box.contains(candidate_box)
                        and (recovery["candidate_strictly_contained"] or recovery["physical_page_edge_exception"])
                        and recovery["recovery_rgb_bytes"] == int(recovery_box.area) * 3
                    )
                crop = candidate["crop"]
                crop_ok &= crop["status"] == "measured" and crop["width_px"] == int(candidate_box.width) and crop["height_px"] == int(candidate_box.height) and crop["rgb_bytes"] == int(candidate_box.area) * 3
                captured = candidate["captured_text"]
                text_ok &= set(captured["source_text_primitive_ids"]) <= set(primitives)
                if not captured["source_text_primitive_ids"]:
                    text_ok &= captured["kind"] == "empty" and captured["utf8_bytes"] == 0 and captured["unicode_codepoints"] == 0 and captured["utf8_sha256"] == EMPTY_SHA256
                else:
                    text_ok &= captured["kind"] == "native" and captured["utf8_bytes"] > 0 and captured["unicode_codepoints"] > 0
            class_complete_ok &= all(item["status"] == "measured" and item["blocking"] is False and item["reason_codes"] == [] for item in page["class_procedures"])
            for procedure in page["class_procedures"]:
                census_ok &= procedure["candidate_count"] == sum(procedure["class"] in candidate["classes"] for candidate in candidates.values())
            try:
                relationship_ok &= page["relationships"] == build_relationships(list(candidates.values()))
            except VWStop:
                relationship_ok = False
        expected_census = case_class_census(case["pages"])
        census_ok &= case["class_census"] == expected_census

    _semantic_assert("bbox-order-range-transform", bbox_ok)
    _semantic_assert("render-rgb-arithmetic", render_ok)
    _semantic_assert("tile-id-bbox-reference", tile_ref_ok)
    _semantic_assert("tile-rgb-arithmetic", tile_rgb_ok)
    _semantic_assert("tile-union-coverage", tile_union_ok)
    _semantic_assert("primitive-kind-attributes-geometry", primitive_shape_ok)
    _semantic_assert("primitive-id", primitive_id_ok)
    _semantic_assert("candidate-class-basis-evidence", candidate_basis_ok)
    _semantic_assert("candidate-source-references", candidate_refs_ok)
    _semantic_assert("candidate-id", candidate_id_ok)
    _semantic_assert("class-procedure-completeness", class_complete_ok, unread=not class_complete_ok)
    _semantic_assert("class-census-reconciliation", census_ok)
    _semantic_assert("relationship-reference-geometry-id", relationship_ok)
    _semantic_assert("edge-recovery-reference-containment", recovery_ok)
    _semantic_assert("crop-rgb-arithmetic", crop_ok)
    _semantic_assert("captured-text-state-hash", text_ok)
    _semantic_assert("metric-arithmetic", payload["metrics"]["declared_page_pixel_coverage"] == aggregate_coverage(cases))

    resources = observations["resources"]
    workers = resources["case_workers"]
    resource_ok = (
        resources["status"] == "measured"
        and [item["case_id"] for item in workers] == list(ALLOWED_CASE_IDS)
        and all(item["status"] == "measured" for item in workers)
        and resources["scratch_peak_bytes"] >= max(item["scratch_peak_bytes"] for item in workers)
        and resources["gpu_used"] is False and resources["network_used"] is False
    )
    _semantic_assert("resource-worker-reconciliation", resource_ok)
    protected = observations["protected_tree"]
    _semantic_assert(
        "protected-tree-digest",
        protected["algorithm"] == "sha256-domain-canonical-logical-inventory-v1"
        and protected["before_sha256"] == protected["after_sha256"]
        and protected["identical"] is True,
    )
    privacy, cleanup = observations["privacy"], observations["cleanup"]
    _semantic_assert(
        "privacy-heldout-cleanup-redaction",
        privacy["private_inputs"] is True
        and privacy["held_out_paths_resolved"] == 0
        and all(privacy[name] == 0 for name in ("persisted_raw_renders", "persisted_raw_tiles", "persisted_raw_crops", "persisted_raw_text", "private_identifiers_exposed"))
        and cleanup["event_scratch_removed"] is True and cleanup["part_files_remaining"] == 0
        and cleanup["verified"] is True and privacy["cleanup_probe_sha256"] == cleanup["evidence_sha256"],
    )
    allowed_global_unread = {
        "reason_code": "UNREAD", "scope": "system-global-census", "blocking": False,
        "detail_code": "outside-event-process-scope", "evidence_sha256": None,
    }
    _semantic_assert(
        "semantic-unread-boundary",
        observations["conflicts"] == [] and observations["unreads"] == []
        and observations["residue"]["inaccessible"] == [allowed_global_unread]
        and observations["status"] == "record-produced",
    )
    _semantic_assert(
        "output-root-realpath-containment",
        roots.evidence_run.parent == roots.evidence_root
        and roots.scratch_run.parent == roots.scratch_root
        and roots.evidence_run.name == roots.scratch_run.name
        and not paths_related(roots.evidence_root, roots.scratch_root),
    )
    residue = observations["residue"]
    _semantic_assert(
        "residue-privacy-census",
        residue["files"] == [] and residue["processes"] == [] and residue["ports"] == [] and residue["gpu_owners"] == []
        and residue["inaccessible"] == [allowed_global_unread],
    )


def pre_verifier_subject_sha256(report: Mapping[str, Any]) -> str:
    observations = copy.deepcopy(report["run_observations"])
    observations.pop("independent_verification", None)
    return domain_hash(
        "semantic_subject",
        {"capture_payload": report["capture_payload"], "run_observations": observations},
        prefixed=False,
    )


def semantic_check_object(
    name: str,
    *,
    status: str,
    subject_sha256: str,
    validator_code_sha256: str,
) -> dict[str, Any]:
    reasons = [] if status == "pass" else [CHECK_REASON_CODES[name]]
    evidence: str | None = None
    if status in ("pass", "fail"):
        evidence = domain_hash(
            "semantic_check",
            {
                "name": name,
                "status": status,
                "reason_codes": reasons,
                "subject_sha256": subject_sha256,
                "validator_code_sha256": validator_code_sha256,
            },
            prefixed=False,
        )
    return {
        "name": name,
        "status": status,
        "blocking": True,
        "claim_status": "UNREAD" if status == "UNREAD" else "Verified-self",
        "evidence_sha256": evidence,
        "reason_codes": reasons,
    }


def build_ordinary_semantic_checks(report: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    subject = pre_verifier_subject_sha256(report)
    validator_sha = report["run_observations"]["producer"]["semantic_validator_code_sha256"]
    checks = [
        semantic_check_object(name, status="pass", subject_sha256=subject, validator_code_sha256=validator_sha)
        for name in ORDINARY_CHECK_NAMES
    ]
    checks_sha = domain_hash("semantic_checks", checks, prefixed=False)
    return checks, subject, checks_sha


def build_preverifier_semantic_checks(report: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    if LAST_COMPLETED_GATE != "CLEANUP-VERIFIED":
        raise VWStop("VW-IDENTITY", "pre-verifier subject requires actual protected AFTER and cleanup")
    observations = report.get("run_observations")
    if not isinstance(observations, dict):
        raise VWStop("UNREAD", "pre-verifier observations unread")
    cleanup = observations.get("cleanup")
    protected = observations.get("protected_tree")
    if not isinstance(cleanup, dict) or cleanup.get("verified") is not True:
        raise VWStop("VW-CLEANUP", "pre-verifier cleanup observation is not actual and verified")
    if not isinstance(protected, dict) or protected.get("identical") is not True:
        raise VWStop("VW-PROTECTED-TREE", "pre-verifier protected AFTER is not actual and identical")
    return build_ordinary_semantic_checks(report)


def _literal_domain_hash(domain_text: str, value: Any) -> str:
    return sha256_bytes(domain_text.encode("utf-8") + b"\0" + canonical_json_bytes(value))


def generic_probe_evidence(
    *,
    probe_id: str,
    probe_code_sha256: str,
    subject_sha256: str,
    status: str,
    reason_codes: Sequence[str],
    result_projection: Mapping[str, Any],
) -> str:
    return domain_hash(
        "probe",
        {
            "probe_id": probe_id,
            "probe_code_sha256": probe_code_sha256,
            "subject_sha256": subject_sha256,
            "status": status,
            "reason_codes": list(reason_codes),
            "result_projection": dict(result_projection),
        },
        prefixed=False,
    )


def heldout_probe(capture_code_sha256: str) -> str:
    subject = _literal_domain_hash(
        "file-portal/vw-e2-probe-subject/heldout-selector-v1/r2",
        {
            "requested_case_ids": [*ALLOWED_CASE_IDS, *sorted(HELD_OUT_CASE_IDS)],
            "allowed_case_ids": list(ALLOWED_CASE_IDS),
            "forbidden_case_ids": sorted(HELD_OUT_CASE_IDS),
        },
    )
    result = {
        "accepted_calibration_case_ids": list(ALLOWED_CASE_IDS),
        "rejected_heldout_case_ids": sorted(HELD_OUT_CASE_IDS),
        "path_operations_before_rejection": 0,
    }
    return generic_probe_evidence(
        probe_id="heldout-selector-v1",
        probe_code_sha256=capture_code_sha256,
        subject_sha256=subject,
        status="pass",
        reason_codes=[],
        result_projection=result,
    )


@dataclass(frozen=True)
class IsolationMeasurement:
    event_pids: tuple[int, ...]
    live_event_pids: tuple[int, ...]
    owned_ports: tuple[int, ...]


IsolationProvider = Callable[[set[int]], IsolationMeasurement]


def _windows_process_parent_map() -> dict[int, int]:
    if os.name != "nt":
        raise VWStop("UNREAD", "event descendant measurement requires Windows")

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    create_snapshot.restype = wintypes.HANDLE
    first = kernel32.Process32FirstW
    first.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    first.restype = wintypes.BOOL
    next_entry = kernel32.Process32NextW
    next_entry.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    next_entry.restype = wintypes.BOOL
    snapshot = create_snapshot(0x00000002, 0)
    invalid = ctypes.c_void_p(-1).value
    if snapshot in (None, invalid):
        raise VWStop("UNREAD", "CreateToolhelp32Snapshot failed")
    result: dict[int, int] = {}
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        if not first(snapshot, ctypes.byref(entry)):
            raise VWStop("UNREAD", "Process32FirstW failed")
        while True:
            result[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            if not next_entry(snapshot, ctypes.byref(entry)):
                error = ctypes.get_last_error()
                if error != 18:  # ERROR_NO_MORE_FILES
                    raise VWStop("UNREAD", "Process32NextW failed")
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return result


def _network_order_port(raw_port: int) -> int:
    value = int(raw_port) & 0xFFFF
    return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)


def _windows_owner_port_rows() -> list[tuple[int, int]]:
    if os.name != "nt":
        raise VWStop("UNREAD", "event port measurement requires Windows")
    iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=True)

    class TCP4(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in (
            "state", "local_addr", "local_port", "remote_addr", "remote_port", "pid"
        )]

    class UDP4(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in ("local_addr", "local_port", "pid")]

    class TCP6(ctypes.Structure):
        _fields_ = [
            ("local_addr", ctypes.c_ubyte * 16), ("local_scope", wintypes.DWORD),
            ("local_port", wintypes.DWORD), ("remote_addr", ctypes.c_ubyte * 16),
            ("remote_scope", wintypes.DWORD), ("remote_port", wintypes.DWORD),
            ("state", wintypes.DWORD), ("pid", wintypes.DWORD),
        ]

    class UDP6(ctypes.Structure):
        _fields_ = [
            ("local_addr", ctypes.c_ubyte * 16), ("local_scope", wintypes.DWORD),
            ("local_port", wintypes.DWORD), ("pid", wintypes.DWORD),
        ]

    def rows(function_name: str, family: int, table_class: int, row_type: type[ctypes.Structure]) -> list[tuple[int, int]]:
        function = getattr(iphlpapi, function_name)
        function.argtypes = (
            ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
            wintypes.ULONG, wintypes.ULONG, wintypes.ULONG,
        )
        function.restype = wintypes.DWORD
        size = wintypes.DWORD(0)
        status = int(function(None, ctypes.byref(size), False, family, table_class, 0))
        if status not in (0, 122) or size.value < ctypes.sizeof(wintypes.DWORD):
            raise VWStop("UNREAD", f"{function_name} sizing failed")
        buffer = ctypes.create_string_buffer(size.value)
        status = int(function(buffer, ctypes.byref(size), False, family, table_class, 0))
        if status != 0:
            raise VWStop("UNREAD", f"{function_name} failed")
        count = int(wintypes.DWORD.from_buffer_copy(buffer.raw[:4]).value)
        required = 4 + count * ctypes.sizeof(row_type)
        if required > len(buffer):
            raise VWStop("UNREAD", f"{function_name} returned truncated rows")
        observed: list[tuple[int, int]] = []
        base = ctypes.addressof(buffer) + 4
        for index in range(count):
            row = row_type.from_address(base + index * ctypes.sizeof(row_type))
            port = _network_order_port(int(row.local_port))
            if port:
                observed.append((int(row.pid), port))
        return observed

    return [
        *rows("GetExtendedTcpTable", 2, 5, TCP4),
        *rows("GetExtendedTcpTable", 23, 5, TCP6),
        *rows("GetExtendedUdpTable", 2, 1, UDP4),
        *rows("GetExtendedUdpTable", 23, 1, UDP6),
    ]


def native_isolation_measurement(known_event_pids: set[int]) -> IsolationMeasurement:
    parents = _windows_process_parent_map()
    event = {int(pid) for pid in known_event_pids if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in event and pid not in event:
                event.add(pid)
                changed = True
    live = event & set(parents)
    ports = {port for pid, port in _windows_owner_port_rows() if pid in event}
    return IsolationMeasurement(tuple(sorted(event)), tuple(sorted(live)), tuple(sorted(ports)))


def isolation_probe(
    capture_code_sha256: str,
    *,
    provider: IsolationProvider | None = None,
    transitional_pids: Iterable[int] = (),
) -> tuple[str, dict[str, Any], IsolationMeasurement]:
    provider = native_isolation_measurement if provider is None else provider
    try:
        measurement = provider(set(EVENT_CHILD_PIDS) | set(EVENT_OBSERVED_DESCENDANT_PIDS))
    except VWStop:
        raise
    except BaseException as exc:
        raise VWStop("UNREAD", "event isolation provider unavailable") from exc
    if not isinstance(measurement, IsolationMeasurement):
        raise VWStop("UNREAD", "event isolation provider returned the wrong type")
    event_pids = tuple(sorted(set(measurement.event_pids)))
    live = tuple(sorted(set(measurement.live_event_pids)))
    ports = tuple(sorted(set(measurement.owned_ports)))
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in (*event_pids, *live)):
        raise VWStop("UNREAD", "event isolation provider returned an invalid PID")
    if any(isinstance(item, bool) or not isinstance(item, int) or not 1 <= item <= 65535 for item in ports):
        raise VWStop("UNREAD", "event isolation provider returned an invalid port")
    if not set(live) <= set(event_pids):
        raise VWStop("UNREAD", "live event PID is absent from the measured event set")
    EVENT_OBSERVED_DESCENDANT_PIDS.update(event_pids)
    transitional = {int(pid) for pid in transitional_pids}
    if not transitional <= set(EVENT_CHILD_PIDS):
        raise VWStop("UNREAD", "transitional PID is not a recorded event child")
    surviving = sorted(set(live) - transitional)
    network_calls = EVENT_ACTIVITY.network_call_count
    gpu_calls = EVENT_ACTIVITY.gpu_call_count
    if min(network_calls, gpu_calls) < 0:
        raise VWStop("UNREAD", "event activity counter is invalid")
    pid_digest = _literal_domain_hash("event_pid_set_sha256", list(event_pids))
    port_digest = _literal_domain_hash("event_port_set_sha256", list(ports))
    subject = _literal_domain_hash(
        "file-portal/vw-e2-probe-subject/isolation-v1/r2",
        {
            "event_pid_set_sha256": pid_digest,
            "event_port_set_sha256": port_digest,
            "network_call_count": network_calls,
            "gpu_call_count": gpu_calls,
        },
    )
    result = {
        "event_child_process_count": len(surviving),
        "event_child_port_count": len(ports),
        "gpu_used": gpu_calls > 0,
        "network_used": network_calls > 0,
    }
    passed = not surviving and not ports and network_calls == 0 and gpu_calls == 0
    evidence = generic_probe_evidence(
        probe_id="isolation-v1",
        probe_code_sha256=capture_code_sha256,
        subject_sha256=subject,
        status="pass" if passed else "fail",
        reason_codes=[] if passed else ["VW-CLEANUP"],
        result_projection=result,
    )
    return evidence, result, measurement


def cleanup_probe(capture_code_sha256: str, run_id: str, *, removed: bool, part_files: int) -> str:
    prefix = f"vw-e2-r2-{run_id}-"
    subject = _literal_domain_hash(
        "file-portal/vw-e2-probe-subject/cleanup-v1/r2",
        {
            "run_id": run_id,
            "scratch_child_id": "event-scratch-child",
            "part_file_prefix": prefix,
            "part_file_suffix": ".part",
        },
    )
    result = {"event_scratch_removed": removed, "part_files_remaining": part_files}
    return generic_probe_evidence(
        probe_id="cleanup-v1",
        probe_code_sha256=capture_code_sha256,
        subject_sha256=subject,
        status="pass" if removed and part_files == 0 else "fail",
        reason_codes=[] if removed and part_files == 0 else ["VW-CLEANUP"],
        result_projection=result,
    )


def _private_dictionary(manifest: CalibrationManifest, cases: Sequence[ResolvedCaseFiles]) -> tuple[list[str], str]:
    values: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and value:
            values.add(value.replace("/", "\\").casefold())

    add(manifest.root_text)
    for case in cases:
        add(case.case.get("title"))
        for path in (
            case.source, case.bundle_dir, case.bundle_manifest, case.bundle_body,
            case.raw_markdown, *case.analyst_markdown, *case.assets,
        ):
            add(str(path))
            add(path.name)
    ordered = sorted(values)
    return ordered, _literal_domain_hash("file-portal/vw-e2-private-dictionary/r2", ordered)


def _string_leaves(value: Any, pointer: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield pointer or "/", value
    elif isinstance(value, dict):
        for key in sorted(value):
            encoded = key.replace("~", "~0").replace("/", "~1")
            yield from _string_leaves(value[key], f"{pointer}/{encoded}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_leaves(child, f"{pointer}/{index}")


def _schema_pointer_tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        return []
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _schema_expand_nodes(node: Any, root: Mapping[str, Any], seen: set[int] | None = None) -> list[Mapping[str, Any]]:
    if not isinstance(node, dict):
        return []
    seen = set() if seen is None else set(seen)
    marker = id(node)
    if marker in seen:
        return []
    seen.add(marker)
    expanded: list[Mapping[str, Any]] = [node]
    reference = node.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/"):
        target: Any = root
        try:
            for token in reference[2:].split("/"):
                target = target[token.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            return expanded
        expanded.extend(_schema_expand_nodes(target, root, seen))
    for keyword in ("allOf", "anyOf", "oneOf"):
        for child in node.get(keyword, []) if isinstance(node.get(keyword), list) else []:
            expanded.extend(_schema_expand_nodes(child, root, seen))
    for keyword in ("if", "then", "else"):
        child = node.get(keyword)
        if isinstance(child, dict):
            expanded.extend(_schema_expand_nodes(child, root, seen))
    unique: dict[int, Mapping[str, Any]] = {}
    for item in expanded:
        unique[id(item)] = item
    return list(unique.values())


def _schema_nodes_at_pointer(schema: Mapping[str, Any], pointer: str) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [schema]
    for token in _schema_pointer_tokens(pointer):
        next_candidates: list[Mapping[str, Any]] = []
        for candidate in candidates:
            for node in _schema_expand_nodes(candidate, schema):
                properties = node.get("properties")
                if isinstance(properties, dict) and isinstance(properties.get(token), dict):
                    next_candidates.append(properties[token])
                if token.isdecimal():
                    index = int(token)
                    prefix = node.get("prefixItems")
                    if isinstance(prefix, list) and index < len(prefix) and isinstance(prefix[index], dict):
                        next_candidates.append(prefix[index])
                    items = node.get("items")
                    if isinstance(items, dict):
                        next_candidates.append(items)
        candidates = next_candidates
        if not candidates:
            return []
    expanded: list[Mapping[str, Any]] = []
    for candidate in candidates:
        expanded.extend(_schema_expand_nodes(candidate, schema))
    return expanded


_BROAD_OPAQUE_PATTERNS = frozenset(
    (
        r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
        r"^[A-Za-z0-9_.:-][A-Za-z0-9_.:-]{0,127}$",
    )
)


def _contract_path(value: Mapping[str, Any], *tokens: str) -> Any:
    current: Any = value
    for token in tokens:
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current


def _packet_location_license(pointer: str, text_value: str, packet: Mapping[str, Any]) -> bool:
    """Apply only packet grammars explicitly bound to this retained location."""
    probes = _contract_path(packet, "frozen_configuration", "privacy_and_residue_probes")
    if not isinstance(probes, dict):
        return False
    if pointer.endswith("/scope"):
        scopes = probes.get("scope_enum")
        if isinstance(scopes, list) and text_value in scopes:
            return True
    if pointer.endswith("/detail_code"):
        details = probes.get("detail_code_enum")
        if isinstance(details, list) and text_value in details:
            return True
    residue = probes.get("residue_id_enum")
    residue_pointer_to_key = {
        r"/run_observations/residue/files/[0-9]+": "files",
        r"/run_observations/residue/processes/[0-9]+": "processes",
        r"/run_observations/residue/gpu_owners/[0-9]+": "gpu_owners",
    }
    if isinstance(residue, dict):
        for pattern, key in residue_pointer_to_key.items():
            values = residue.get(key)
            if re.fullmatch(pattern, pointer) and isinstance(values, list) and text_value in values:
                return True

    projection = _contract_path(packet, "failure_exit_contract", "complete_receipt_exact_projection")
    if not isinstance(projection, dict):
        return False
    if pointer == "/authority/verbatim_decision":
        return text_value == _contract_path(packet, "authority", "verbatim_decision")
    if pointer in ("/authority/decision_source", "/authority/scope"):
        authority = projection.get("authority")
        key = pointer.rsplit("/", 1)[-1]
        return isinstance(authority, dict) and text_value == authority.get(key)
    if re.fullmatch(r"/case_census/case_ids/[0-9]+", pointer):
        case_ids = _contract_path(packet, "read_scope", "calibration_case_ids")
        return isinstance(case_ids, list) and text_value in case_ids
    test_match = re.fullmatch(r"/tests/([0-9]+)/(family|command_or_probe)", pointer)
    if test_match:
        tests = projection.get("tests")
        index, key = int(test_match.group(1)), test_match.group(2)
        return (
            isinstance(tests, list)
            and index < len(tests)
            and isinstance(tests[index], dict)
            and text_value == tests[index].get(key)
        )
    exact_receipt_locations = {
        "/mutation_receipt/comparison_probe": ("mutation_receipt", "comparison_probe"),
        "/independent_verification/verifier": ("independent_verification", "verifier"),
        "/independent_verification/probe": ("independent_verification", "probe"),
        "/blast_radius": ("blast_radius",),
    }
    if pointer in exact_receipt_locations:
        return text_value == _contract_path(projection, *exact_receipt_locations[pointer])
    return False


def _string_is_location_licensed(
    pointer: str,
    text_value: str,
    *,
    packet: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> bool:
    nodes = _schema_nodes_at_pointer(schema, pointer)
    if not nodes:
        return False
    for node in nodes:
        if "const" in node and text_value == node["const"]:
            return True
        if isinstance(node.get("enum"), list) and text_value in node["enum"]:
            return True
        pattern = node.get("pattern")
        if isinstance(pattern, str) and pattern not in _BROAD_OPAQUE_PATTERNS:
            try:
                if re.fullmatch(pattern, text_value):
                    return True
            except re.error:
                return False
        if node.get("format") == "date-time" and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            text_value,
        ):
            return True

    if _packet_location_license(pointer, text_value, packet):
        return True

    if pointer.endswith("/logical_name") and re.fullmatch(r"[A-Za-z0-9_.:-][A-Za-z0-9_.:-]{0,127}", text_value):
        return True
    if pointer.endswith("/engine_version") or pointer in (
        "/run_observations/producer/python_version",
        "/run_observations/producer/pymupdf_version",
        "/run_observations/producer/mupdf_version",
    ):
        return re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9_.-]+)?", text_value) is not None
    if pointer.endswith("/cell_id") or "/occupied_cell_ids/" in pointer:
        return re.fullmatch(r"r[0-9]{6}-c[0-9]{6}", text_value) is not None
    if pointer.endswith("/stroke_width_disposition"):
        return text_value in {"fill-only-fallback", "fallback-missing", "fallback-zero", "observed-positive"}
    if pointer.endswith("/bundle/page_map/formula"):
        return text_value in {
            "source page_1based = page_id_0based + 1 (mechanical filename map only)",
            "source page_1based = page_id_0based + 1 - 200*(page_id_0based//400) (mechanical SYM-050 repair only)",
        }
    if re.fullmatch(r"/tests/[0-9]+/evidence", pointer):
        return re.fullmatch(r"[0-9a-f]{64}", text_value) is not None
    if re.fullmatch(r"/outputs/[0-9]+/path", pointer):
        return re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}/vw-e2-r2-[A-Za-z0-9][A-Za-z0-9._-]{0,63}-operational-report\.json",
            text_value,
        ) is not None
    return False


def retained_string_scan(
    value: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    schema: Mapping[str, Any],
    private_dictionary: Sequence[str],
) -> dict[str, int]:
    path_hits = base64_hits = private_hits = unlicensed_hits = 0
    for pointer, text_value in _string_leaves(value):
        normalized = text_value.replace("/", "\\").casefold()
        is_hash = re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", text_value) is not None
        licensed = _string_is_location_licensed(pointer, text_value, packet=packet, schema=schema)
        if (
            re.search(r"(?i)(?:^|[^A-Za-z0-9])[A-Z]:[\\/]", text_value)
            or text_value.startswith("\\\\")
            or text_value.startswith("//")
            or re.match(r"(?i)^file:(?:/{2,3})", text_value)
        ):
            path_hits += 1
        if not licensed and not is_hash and len(text_value) > 80 and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", text_value):
            base64_hits += 1
        if any(private and (normalized == private or private in normalized) for private in private_dictionary):
            private_hits += 1
        if not licensed:
            unlicensed_hits += 1
    return {
        "path_pattern_hits": path_hits,
        "base64_pattern_hits": base64_hits,
        "private_identifiers_exposed": private_hits,
        "unlicensed_string_hits": unlicensed_hits,
    }


def redaction_probe(
    report: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    schema: Mapping[str, Any],
    private_dictionary: Sequence[str],
    private_dictionary_sha256: str,
    capture_code_sha256: str,
) -> tuple[str, dict[str, int]]:
    subject_observations = copy.deepcopy(report["run_observations"])
    subject_observations.pop("independent_verification", None)
    subject_observations["privacy"].pop("redaction_probe_sha256", None)
    subject_value = {"capture_payload": report["capture_payload"], "run_observations": subject_observations}
    scan = retained_string_scan(subject_value, packet=packet, schema=schema, private_dictionary=private_dictionary)
    result = {
        "private_identifiers_exposed": scan["private_identifiers_exposed"],
        "persisted_raw_renders": 0,
        "persisted_raw_tiles": 0,
        "persisted_raw_crops": 0,
        "persisted_raw_text": 0,
        "path_pattern_hits": scan["path_pattern_hits"],
        "base64_pattern_hits": scan["base64_pattern_hits"],
        "unlicensed_string_hits": scan["unlicensed_string_hits"],
    }
    redaction_subject = _literal_domain_hash("file-portal/vw-e2-redaction-subject/r2", subject_value)
    probe_subject = _literal_domain_hash(
        "file-portal/vw-e2-probe-subject/redaction-v1/r2",
        {
            "redaction_subject_sha256": redaction_subject,
            "private_dictionary_sha256": private_dictionary_sha256,
            "packet_sha256": PACKET_SHA256,
            "capture_schema_sha256": CAPTURE_SCHEMA_SHA256,
        },
    )
    passed = all(value == 0 for value in result.values())
    evidence = generic_probe_evidence(
        probe_id="redaction-v1",
        probe_code_sha256=capture_code_sha256,
        subject_sha256=probe_subject,
        status="pass" if passed else "fail",
        reason_codes=[] if passed else ["VW-PRIVACY"],
        result_projection=result,
    )
    return evidence, result


def _part_file_count(evidence_run: Path, run_id: str) -> int:
    prefix = f"vw-e2-r2-{run_id}-"
    count = 0
    for child in evidence_run.iterdir():
        if child.name.startswith(prefix) and child.name.endswith(".part"):
            count += 1
    return count


def cleanup_scratch(roots: OutputRoots, run_id: str) -> tuple[dict[str, Any], list[str]]:
    capture_sha = sha256_file(Path(__file__))
    if roots.scratch_run.exists():
        scratch_tree_bytes(roots.scratch_run)
        shutil.rmtree(roots.scratch_run)
    removed = not roots.scratch_run.exists()
    parts = _part_file_count(roots.evidence_run, run_id)
    evidence = cleanup_probe(capture_sha, run_id, removed=removed, part_files=parts)
    cleanup = {
        "event_scratch_removed": removed,
        "part_files_remaining": parts,
        "probe_code_sha256": capture_sha,
        "evidence_sha256": evidence,
        "verified": removed and parts == 0,
    }
    residue = ([] if removed else ["event-scratch-child"]) + ([] if parts == 0 else ["evidence-part-file"])
    return cleanup, sorted(set(residue))


def create_new_json(path: Path, value: Any) -> tuple[bytes, str]:
    raw = canonical_json_bytes(value) + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise VWStop("VW-CLEANUP", "output create-new failed") from exc
    observed = path.read_bytes()
    if observed != raw:
        raise VWStop("VW-IDENTITY", "persisted output reopen mismatch")
    return raw, sha256_bytes(raw)


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _base_run_observations(
    *,
    repo_root: Path,
    configuration_sha256: str,
    roots: OutputRoots,
    run_id: str,
    case_resources: Sequence[Mapping[str, Any]],
    protected_entries: Sequence[Mapping[str, Any]],
    protected_before: str,
    protected_after: str,
    cleanup: Mapping[str, Any],
    residue_files: Sequence[str],
    created_at_utc: str,
    isolation_evidence: str,
    isolation_result: Mapping[str, Any],
) -> dict[str, Any]:
    producer = producer_observation(repo_root, configuration_sha256)
    if (
        isolation_result.get("event_child_process_count") != 0
        or isolation_result.get("event_child_port_count") != 0
        or isolation_result.get("gpu_used") is not False
        or isolation_result.get("network_used") is not False
    ):
        raise VWStop("VW-CLEANUP", "measured event isolation is not clean")
    inaccessible = [
        {
            "reason_code": "UNREAD",
            "scope": "system-global-census",
            "blocking": False,
            "detail_code": "outside-event-process-scope",
            "evidence_sha256": None,
        }
    ]
    resources = {
        "status": "measured",
        "wall_seconds": sum(float(item["wall_seconds"]) for item in case_resources),
        "cpu_seconds": sum(float(item["cpu_seconds"]) for item in case_resources),
        "scratch_free_bytes_before": roots.scratch_free_bytes_before,
        "scratch_peak_bytes": max(int(item["scratch_peak_bytes"]) for item in case_resources),
        "gpu_used": isolation_result["gpu_used"],
        "network_used": isolation_result["network_used"],
        "isolation_evidence_sha256": isolation_evidence,
        "case_workers": [dict(item) for item in case_resources],
        "reason_codes": [],
    }
    return {
        "created_at_utc": created_at_utc,
        "producer": producer,
        "resources": resources,
        "privacy": {
            "private_inputs": True,
            "held_out_paths_resolved": 0,
            "persisted_raw_renders": 0,
            "persisted_raw_tiles": 0,
            "persisted_raw_crops": 0,
            "persisted_raw_text": 0,
            "private_identifiers_exposed": 0,
            "held_out_access_probe_sha256": heldout_probe(producer["capture_code_sha256"]),
            "cleanup_probe_sha256": cleanup["evidence_sha256"],
            "redaction_probe_sha256": "0" * 64,
        },
        "protected_tree": {
            "algorithm": "sha256-domain-canonical-logical-inventory-v1",
            "domain": "file-portal/vw-e2-protected-tree/r2\0",
            "record_encoding": "canonical JSON array of logical_id,bytes,sha256 sorted by logical_id; absolute paths, titles, and basenames omitted",
            "inventory_entry_count": len(protected_entries),
            "probe_code_sha256": producer["capture_code_sha256"],
            "before_sha256": protected_before,
            "after_sha256": protected_after,
            "identical": protected_before == protected_after,
        },
        "cleanup": dict(cleanup),
        "residue": {
            "files": sorted(set(residue_files)),
            "processes": [],
            "ports": [],
            "gpu_owners": [],
            "inaccessible": inaccessible,
        },
        "conflicts": [],
        "unreads": [],
        "status": "record-produced",
    }


@dataclass(frozen=True)
class VerifierInvocation:
    process: Any = field(repr=False)
    started_epoch_ns: int


VERIFIER_RESULT_KEYS = frozenset(
    (
        "verifier", "status", "probe_id", "verifier_code_sha256", "packet_sha256",
        "capture_schema_sha256", "capture_payload_sha256", "semantic_checks_sha256",
        "evidence_sha256", "reason_codes",
    )
)


def _start_verifier(repo_root: Path, roots: OutputRoots) -> VerifierInvocation:
    global ACTIVE_VERIFIER
    del roots
    verifier = repo_root / "windows-converter/visual_witness_verify.py"
    started_epoch_ns = time.time_ns()
    process = subprocess.Popen(
        [
            sys.executable,
            str(verifier),
            "--repo-root", str(repo_root),
            "--stdio",
        ],
        cwd=repo_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.pid is None:
        process.kill()
        raise VWStop("UNREAD", "verifier process has no PID")
    EVENT_CHILD_PIDS.add(int(process.pid))
    ACTIVE_VERIFIER = process
    return VerifierInvocation(process, started_epoch_ns)


def _validate_independent_result(
    result: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    if set(result) != VERIFIER_RESULT_KEYS:
        raise VWStop("VW-NEGATIVE-CONTROL", "independent verifier result keys differ")
    payload = request.get("capture_payload")
    checks = request.get("ordinary_semantic_checks")
    if not isinstance(payload, dict) or not isinstance(checks, list):
        raise VWStop("UNREAD", "independent verifier request shape unread")
    if payload.get("config_sha256") != EXPECTED_CONFIG_SHA256:
        raise VWStop("VW-CONFIG-HASH", "independent verifier request config differs")
    expected_payload_sha = capture_payload_sha256(payload)
    expected_checks_sha = domain_hash("semantic_checks", checks, prefixed=False)
    if payload.get("capture_payload_sha256") != expected_payload_sha:
        raise VWStop("VW-IDENTITY", "independent verifier request payload hash differs")
    if request.get("semantic_checks_sha256") != expected_checks_sha:
        raise VWStop("VW-IDENTITY", "independent verifier request check hash differs")
    verifier_code_sha = sha256_file(repo_root / "windows-converter/visual_witness_verify.py")
    expected = {
        "verifier": "codex-independent-verifier-v1",
        "status": "Verified-independent",
        "probe_id": "vw-e2-r2-independent-sample-v1",
        "verifier_code_sha256": verifier_code_sha,
        "packet_sha256": PACKET_SHA256,
        "capture_schema_sha256": CAPTURE_SCHEMA_SHA256,
        "capture_payload_sha256": expected_payload_sha,
        "semantic_checks_sha256": expected_checks_sha,
        "reason_codes": [],
    }
    if request.get("verifier_code_sha256") != verifier_code_sha:
        raise VWStop("GROUND-DRIFT", "requested verifier code identity differs")
    for name, expected_value in expected.items():
        if result.get(name) != expected_value:
            reason = "GROUND-DRIFT" if name in (
                "verifier", "probe_id", "verifier_code_sha256", "packet_sha256", "capture_schema_sha256"
            ) else "VW-NEGATIVE-CONTROL"
            raise VWStop(reason, f"independent verifier result {name} differs")
    projection = dict(result)
    evidence = projection.pop("evidence_sha256")
    expected_evidence = domain_hash("independent_verifier", projection, prefixed=False)
    if evidence != expected_evidence:
        raise VWStop("VW-NEGATIVE-CONTROL", "independent verifier evidence hash differs")
    return dict(result)


def _finish_verifier(
    invocation: VerifierInvocation,
    request: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    global ACTIVE_VERIFIER
    process = invocation.process
    request_bytes = canonical_json_bytes(request) + b"\n"
    try:
        stdout, stderr = process.communicate(input=request_bytes, timeout=60)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise VWStop("UNREAD", "independent verifier timeout") from exc
    finally:
        if process.pid is not None and process.poll() is not None:
            EVENT_CHILD_EXITED_PIDS.add(int(process.pid))
        if process.poll() is not None and ACTIVE_VERIFIER is process:
            ACTIVE_VERIFIER = None
    if stderr or not stdout.endswith(b"\n"):
        raise VWStop("UNREAD", "independent verifier pipe transport unread")
    wrapper = strict_json_bytes(stdout[:-1], reason="UNREAD")
    if canonical_json_bytes(wrapper) + b"\n" != stdout or not isinstance(wrapper, dict) or set(wrapper) != {"activity", "result"}:
        raise VWStop("UNREAD", "independent verifier pipe wrapper unread")
    activity = wrapper.get("activity")
    if not isinstance(activity, dict):
        raise VWStop("UNREAD", "independent verifier activity evidence unread")
    reconcile_event_activity(activity)
    if EVENT_ACTIVITY.network_call_count or EVENT_ACTIVITY.gpu_call_count:
        raise VWStop("VW-CLEANUP", "independent verifier attempted network or GPU activity")
    if process.returncode != 0:
        raise VWStop("UNREAD", "independent verifier exited nonzero")
    result = wrapper.get("result")
    if not isinstance(result, dict):
        raise VWStop("UNREAD", "independent verifier object unread")
    result = _validate_independent_result(result, request, repo_root=repo_root)
    return result


def _assemble_final_report(
    report: dict[str, Any],
    ordinary_checks: Sequence[Mapping[str, Any]],
    independent: Mapping[str, Any],
) -> dict[str, Any]:
    validator_sha = report["run_observations"]["producer"]["semantic_validator_code_sha256"]
    if independent.get("status") != "Verified-independent" or not isinstance(independent.get("evidence_sha256"), str):
        raise VWStop("VW-NEGATIVE-CONTROL", "independent verifier did not pass")
    binding = semantic_check_object(
        "independent-verification-binding",
        status="pass",
        subject_sha256=independent["evidence_sha256"],
        validator_code_sha256=validator_sha,
    )
    report_id_placeholder = {
        "name": "report-id",
        "status": "pass",
        "blocking": True,
        "claim_status": "Verified-self",
        "evidence_sha256": None,
        "reason_codes": [],
    }
    by_name = {item["name"]: dict(item) for item in ordinary_checks}
    by_name["independent-verification-binding"] = binding
    by_name["report-id"] = report_id_placeholder
    report["run_observations"]["independent_verification"] = dict(independent)
    report["semantic_checks"] = [by_name[name] for name in SEMANTIC_CHECK_NAMES]
    report["report_id"] = "sha256:" + "0" * 64
    subject_report = copy.deepcopy(report)
    subject_report.pop("report_id")
    report_id_check = next(item for item in subject_report["semantic_checks"] if item["name"] == "report-id")
    report_id_check.pop("evidence_sha256")
    subject_sha = domain_hash("report_id_subject", subject_report, prefixed=False)
    by_name["report-id"] = semantic_check_object(
        "report-id",
        status="pass",
        subject_sha256=subject_sha,
        validator_code_sha256=validator_sha,
    )
    report["semantic_checks"] = [by_name[name] for name in SEMANTIC_CHECK_NAMES]
    report["report_id"] = report_id(report)
    return report


def _load_bound_json(repo_root: Path, relative: Path, expected_bytes: int, expected_sha: str) -> Mapping[str, Any]:
    raw = (repo_root / relative).read_bytes()
    if len(raw) != expected_bytes or sha256_bytes(raw) != expected_sha:
        raise VWStop("GROUND-DRIFT", "bound schema identity mismatch")
    value = strict_json_bytes(raw)
    if not isinstance(value, dict):
        raise VWStop("GROUND-DRIFT", "bound schema root is not an object")
    return value


def assert_receipt_schema(repo_root: Path, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    schema_path = Path("docs/contracts/visual-witness-event-receipt-v1.schema.json")
    schema = _load_bound_json(repo_root, schema_path, 12483, "ae057c25216cbbe64c551752faa7ae603137343746dbacb46f990d69736e7b4f")
    engine = _schema_engine(repo_root)
    failures = engine.validate_schema(receipt, schema)
    if failures:
        raise VWStop("VW-IDENTITY", "event receipt schema validation failed")
    return schema


def _build_receipt(
    *,
    packet: Mapping[str, Any],
    report: Mapping[str, Any],
    report_bytes: bytes,
    report_sha256: str,
    report_relative_path: str,
    repo_head_before: str,
    repo_head_after: str,
    negative_control_suite_identity: str,
) -> dict[str, Any]:
    observations = report["run_observations"]
    resources = observations["resources"]
    independent = observations["independent_verification"]
    ordinary_checks = [item for item in report["semantic_checks"] if item["name"] in ORDINARY_CHECK_NAMES]
    checks_sha = domain_hash("semantic_checks", ordinary_checks, prefixed=False)
    if negative_control_suite_identity != PACKET_SHA256:
        raise VWStop("VW-NEGATIVE-CONTROL", "frozen negative-control suite was not executed successfully")
    if resources["gpu_used"] is not False or resources["network_used"] is not False:
        raise VWStop("VW-CLEANUP", "event activity counters are not clean")
    return {
        "schema": "file-portal.visual-witness.event-receipt",
        "schema_version": 1,
        "event_id": "VW-E2",
        "event_revision": "VW-E2-R2",
        "contract_sha256": PACKET_SHA256,
        "repo_head_before": repo_head_before,
        "repo_head_after": repo_head_after,
        "authority": {
            "actor": "Rab",
            "verbatim_decision": packet["authority"]["verbatim_decision"],
            "decision_source": "direct-user-instruction",
            "scope": "VW-E2-R2-only",
            "recorded_at_utc": packet["created_at_utc"],
        },
        "case_census": dict(report["capture_payload"]["case_census"]),
        "tests": [
            {"family": "capture-semantic-checks", "command_or_probe": "packet-semantic-validator", "status": "pass", "blocking": True, "negative_control": False, "evidence": checks_sha},
            {"family": "independent-sample", "command_or_probe": "vw-e2-r2-independent-sample-v1", "status": "pass", "blocking": True, "negative_control": False, "evidence": independent["evidence_sha256"]},
            {"family": "same-check-negative-controls", "command_or_probe": "frozen-negative-control-fixtures", "status": "pass", "blocking": True, "negative_control": True, "evidence": negative_control_suite_identity},
        ],
        "metrics": [],
        "outputs": [{"path": report_relative_path, "sha256": report_sha256, "bytes": len(report_bytes), "claim_status": "Verified-independent"}],
        "resources": {
            "cpu_seconds": resources["cpu_seconds"],
            "wall_seconds": resources["wall_seconds"],
            "peak_rss_bytes": max(item["peak_working_set_bytes"] for item in resources["case_workers"]),
            "scratch_peak_bytes": resources["scratch_peak_bytes"],
            "gpu_used": resources["gpu_used"],
            "gpu_receipt": None,
        },
        "network": {"used": resources["network_used"], "consent_receipt": None},
        "privacy": {"private_inputs": True, "persisted_raw_crops": 0, "persisted_raw_text": 0, "ephemeral_cleanup_verified": True},
        "mutation_receipt": {"protected_tree_digest_before_and_after": observations["protected_tree"]["before_sha256"], "comparison_probe": "protected-tree-v1", "identical": True},
        "residue": {"files": [], "processes": [], "ports": [], "gpu_owners": []},
        "independent_verification": {"verifier": "codex-independent-verifier-v1", "status": "Verified-independent", "probe": "vw-e2-r2-independent-sample-v1", "dissent": None},
        "conflicts": [],
        "unreads": [],
        "blast_radius": "report-only-no-converter-analyst-bundle-gate-ship-vault-ui-or-clock-mutation",
        "status": "COMPLETE",
        "next_event_authority": "UNSIGNED",
    }


def persist_complete_output_payloads(
    *,
    repo_root: Path,
    expected_repo_head: str,
    report: Mapping[str, Any],
    report_path: Path,
    receipt_path: Path,
    receipt_builder: Callable[[bytes, str], Mapping[str, Any]],
    receipt_validator: Callable[[Mapping[str, Any]], None],
) -> dict[str, Any]:
    """Persist report then receipt in the packet-frozen create and validation order."""

    global LAST_COMPLETED_GATE

    require_repository_head_direct(repo_root, expected_repo_head)
    prepared_report_bytes = canonical_json_bytes(report) + b"\n"
    prepared_report_sha = sha256_bytes(prepared_report_bytes)
    require_repository_head_direct(repo_root, expected_repo_head)

    report_bytes, report_sha = create_new_json(report_path, report)
    try:
        reopened_report = report_path.read_bytes()
    except OSError as exc:
        raise VWStop("VW-IDENTITY", "persisted operational report could not be reopened") from exc
    if (
        report_bytes != prepared_report_bytes
        or report_sha != prepared_report_sha
        or reopened_report != report_bytes
        or len(reopened_report) != len(report_bytes)
        or sha256_bytes(reopened_report) != report_sha
    ):
        raise VWStop("VW-IDENTITY", "persisted operational report bytes/hash/length mismatch")
    LAST_COMPLETED_GATE = "REPORT-CREATED"

    require_repository_head_direct(repo_root, expected_repo_head)
    receipt_value = receipt_builder(reopened_report, report_sha)
    if not isinstance(receipt_value, Mapping):
        raise VWStop("VW-IDENTITY", "receipt builder returned a non-object")
    receipt = dict(receipt_value)
    receipt_validator(receipt)
    require_repository_head_direct(repo_root, expected_repo_head)

    receipt_bytes, receipt_sha = create_new_json(receipt_path, receipt)
    try:
        reopened_receipt = receipt_path.read_bytes()
    except OSError as exc:
        raise VWStop("VW-IDENTITY", "persisted receipt could not be reopened") from exc
    if (
        reopened_receipt != receipt_bytes
        or len(reopened_receipt) != len(receipt_bytes)
        or sha256_bytes(reopened_receipt) != receipt_sha
    ):
        raise VWStop("VW-IDENTITY", "persisted receipt bytes/hash/length mismatch")
    return receipt


def run_event(
    *,
    repo_root: Path,
    private_manifest_path: Path,
    evidence_root: Path,
    scratch_root: Path,
    run_id: str,
    selected_case_ids: Sequence[str],
) -> dict[str, Any]:
    global ACTIVE_ROOTS, ACTIVE_RUN_ID, ACTIVE_VERIFIER, LAST_COMPLETED_GATE
    EVENT_CHILD_PIDS.clear()
    EVENT_CHILD_EXITED_PIDS.clear()
    EVENT_OBSERVED_DESCENDANT_PIDS.clear()
    EVENT_MEASURED_GIT_HEADS.clear()
    EVENT_ACTIVITY.reset()
    install_event_activity_audit()
    ACTIVE_ROOTS = None
    ACTIVE_RUN_ID = run_id
    ACTIVE_VERIFIER = None
    LAST_COMPLETED_GATE = "START"

    selected = lexical_case_guard(selected_case_ids)
    if selected != ALLOWED_CASE_IDS:
        raise VWStop("AUTHORITY-MISSING", "R2 COMPLETE requires the exact calibration set")
    repo_root = strict_final_path(repo_root, directory=True)
    packet, configuration_sha = verify_repository_ground(repo_root)
    repo_head_before = _git(repo_root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    negative_control_suite_identity = execute_frozen_negative_controls()
    LAST_COMPLETED_GATE = "GROUND-VERIFIED"

    manifest_path = strict_final_path(private_manifest_path, directory=False)
    manifest_raw, _manifest_observation = stable_small_file_bytes(manifest_path, "GROUND-DRIFT")
    manifest = select_calibration_manifest(manifest_raw, selected)
    cases = resolve_case_files(manifest)
    operational_paths: list[Path] = [repo_root, manifest_path.parent, Path(manifest.root_text)]
    for case in cases:
        operational_paths.extend((case.source, case.bundle_dir, case.raw_markdown, *case.analyst_markdown))
    roots = prepare_output_roots(
        evidence_root=evidence_root,
        scratch_root=scratch_root,
        run_id=run_id,
        protected_paths=operational_paths,
    )
    ACTIVE_ROOTS = roots
    LAST_COMPLETED_GATE = "ROOTS-VERIFIED"

    protected_files = protected_files_for_run(manifest_path, cases)
    before_entries, before_digest = protected_inventory(protected_files)
    LAST_COMPLETED_GATE = "PROTECTED-BEFORE"
    case_reports, case_resources, fresh_assets = run_all_case_workers(
        cases, before_entries, configuration_sha, roots.scratch_run
    )
    require_completed_cases(case_reports)
    capture_payload = build_capture_payload(case_reports, configuration_sha)
    LAST_COMPLETED_GATE = "CASES-CAPTURED"

    preliminary_after_entries, preliminary_after_digest = protected_inventory(protected_files)
    compare_protected_inventories(before_entries, before_digest, preliminary_after_entries, preliminary_after_digest)
    # Finish every native repository child before the retained isolation subject is measured.
    # No later step mutates the repository, so this remains the event's final HEAD observation.
    verify_repository_ground(repo_root)
    repo_head_after = _git(repo_root, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    verifier_invocation = _start_verifier(repo_root, roots)

    capture_sha = sha256_file(Path(__file__))
    verifier_pid = verifier_invocation.process.pid
    if verifier_pid is None:
        raise VWStop("UNREAD", "independent verifier PID unread")
    preliminary_isolation, preliminary_isolation_result, _preliminary_measurement = isolation_probe(
        capture_sha,
        transitional_pids=(int(verifier_pid),),
    )
    if (
        preliminary_isolation_result["event_child_process_count"]
        or preliminary_isolation_result["event_child_port_count"]
        or preliminary_isolation_result["network_used"]
        or preliminary_isolation_result["gpu_used"]
    ):
        raise VWStop("VW-CLEANUP", "event isolation did not pass before verifier request")
    if _part_file_count(roots.evidence_run, run_id) != 0:
        raise VWStop("VW-CLEANUP", "part file exists before finalization")
    cleanup, residue_files = cleanup_scratch(roots, run_id)
    if not cleanup["verified"] or residue_files:
        raise VWStop("VW-CLEANUP", "event scratch cleanup failed")
    after_entries, after_digest = protected_inventory(protected_files)
    compare_protected_inventories(before_entries, before_digest, after_entries, after_digest)
    LAST_COMPLETED_GATE = "PROTECTED-AFTER"
    created_at = _utc_now()
    observations = _base_run_observations(
        repo_root=repo_root,
        configuration_sha256=configuration_sha,
        roots=roots,
        run_id=run_id,
        case_resources=case_resources,
        protected_entries=before_entries,
        protected_before=before_digest,
        protected_after=after_digest,
        cleanup=cleanup,
        residue_files=residue_files,
        created_at_utc=created_at,
        isolation_evidence=preliminary_isolation,
        isolation_result=preliminary_isolation_result,
    )
    LAST_COMPLETED_GATE = "CLEANUP-VERIFIED"
    report: dict[str, Any] = {
        "format_id": FORMAT_ID,
        "capture_payload": capture_payload,
        "run_observations": observations,
    }
    capture_schema = _load_bound_json(repo_root, CAPTURE_SCHEMA_RELATIVE_PATH, CAPTURE_SCHEMA_BYTES, CAPTURE_SCHEMA_SHA256)
    private_values, private_sha = _private_dictionary(manifest, cases)
    redaction_hash, redaction_result = redaction_probe(
        report,
        packet=packet,
        schema=capture_schema,
        private_dictionary=private_values,
        private_dictionary_sha256=private_sha,
        capture_code_sha256=capture_sha,
    )
    if any(redaction_result.values()):
        raise VWStop("VW-PRIVACY", "phase-one retained scan rejected report")
    observations["privacy"]["redaction_probe_sha256"] = redaction_hash
    validate_ordinary_semantics(report, repo_root=repo_root, roots=roots, fresh_assets=fresh_assets)
    ordinary_checks, _subject_sha, checks_sha = build_preverifier_semantic_checks(report)
    verifier_sha = sha256_file(repo_root / "windows-converter/visual_witness_verify.py")
    request = {
        "capture_payload": capture_payload,
        "ordinary_semantic_checks": ordinary_checks,
        "semantic_checks_sha256": checks_sha,
        "verifier_code_sha256": verifier_sha,
        "vw_t03_source_path": str(next(case.source for case in cases if case.case_id == "VW-T03")),
    }
    independent = _finish_verifier(verifier_invocation, request, repo_root=repo_root)
    require_event_activity_reconciled(len(ALLOWED_CASE_IDS) + 1)

    actual_isolation, isolation_result, isolation_measurement = isolation_probe(capture_sha)
    if (
        isolation_result["event_child_process_count"]
        or isolation_result["event_child_port_count"]
        or isolation_result["network_used"]
        or isolation_result["gpu_used"]
    ):
        raise VWStop("VW-CLEANUP", "event child residue remains")
    if actual_isolation != observations["resources"]["isolation_evidence_sha256"]:
        raise VWStop("VW-IDENTITY", "projected isolation evidence did not match observed completion")
    if isolation_measurement.owned_ports:
        raise VWStop("VW-CLEANUP", "event child port residue remains")
    confirmed_after_entries, confirmed_after_digest = protected_inventory(protected_files)
    compare_protected_inventories(after_entries, after_digest, confirmed_after_entries, confirmed_after_digest)

    final_redaction_hash, final_redaction_result = redaction_probe(
        report,
        packet=packet,
        schema=capture_schema,
        private_dictionary=private_values,
        private_dictionary_sha256=private_sha,
        capture_code_sha256=capture_sha,
    )
    if final_redaction_hash != redaction_hash or any(final_redaction_result.values()):
        raise VWStop("VW-PRIVACY", "post-cleanup redaction subject changed")
    validate_ordinary_semantics(report, repo_root=repo_root, roots=roots, fresh_assets=fresh_assets)
    final_ordinary, _final_subject, final_checks_sha = build_ordinary_semantic_checks(report)
    if final_checks_sha != checks_sha or canonical_json_bytes(final_ordinary) != canonical_json_bytes(ordinary_checks):
        raise VWStop("VW-IDENTITY", "post-cleanup semantic subject changed")
    if independent.get("semantic_checks_sha256") != checks_sha:
        raise VWStop("VW-NEGATIVE-CONTROL", "independent verifier bound another semantic subject")
    if independent.get("status") != "Verified-independent":
        reason = independent.get("reason_codes", ["UNREAD"])[0]
        raise VWStop(reason, "independent verifier did not pass")
    LAST_COMPLETED_GATE = "INDEPENDENT-VERIFIED"

    report = _assemble_final_report(report, final_ordinary, independent)
    assert_capture_schema(repo_root, report)
    validate_ordinary_semantics(report, repo_root=repo_root, roots=roots, fresh_assets=fresh_assets)
    final_scan = retained_string_scan(report, packet=packet, schema=capture_schema, private_dictionary=private_values)
    if any(final_scan.values()):
        raise VWStop("VW-PRIVACY", "phase-two retained scan rejected report")
    report_name = f"vw-e2-r2-{run_id}-operational-report.json"
    report_path = roots.evidence_run / report_name
    receipt_path = roots.evidence_run / f"vw-e2-r2-{run_id}-receipt.json"

    def build_receipt(prepared_report_bytes: bytes, prepared_report_sha: str) -> Mapping[str, Any]:
        return _build_receipt(
            packet=packet,
            report=report,
            report_bytes=prepared_report_bytes,
            report_sha256=prepared_report_sha,
            report_relative_path=f"{run_id}/{report_name}",
            repo_head_before=repo_head_before,
            repo_head_after=repo_head_after,
            negative_control_suite_identity=negative_control_suite_identity,
        )

    def validate_receipt_for_persistence(candidate: Mapping[str, Any]) -> None:
        receipt_schema = assert_receipt_schema(repo_root, candidate)
        receipt_scan = retained_string_scan(
            candidate,
            packet=packet,
            schema=receipt_schema,
            private_dictionary=private_values,
        )
        if any(receipt_scan.values()):
            raise VWStop("VW-PRIVACY", "retained receipt scan rejected receipt")

    receipt = persist_complete_output_payloads(
        repo_root=repo_root,
        expected_repo_head=repo_head_after,
        report=report,
        report_path=report_path,
        receipt_path=receipt_path,
        receipt_builder=build_receipt,
        receipt_validator=validate_receipt_for_persistence,
    )
    return receipt


def minimal_attempt_exit(*, status: str, last_completed_gate: str, reason_code: str) -> dict[str, Any]:
    if status not in ("STOPPED", "FAILED", "UNREAD"):
        status = "FAILED"
    if last_completed_gate not in (
        "START", "GROUND-VERIFIED", "ROOTS-VERIFIED", "PROTECTED-BEFORE", "CASES-CAPTURED",
        "PROTECTED-AFTER", "CLEANUP-VERIFIED", "INDEPENDENT-VERIFIED", "REPORT-CREATED",
    ):
        last_completed_gate = "START"
    if reason_code not in DETAIL_BY_REASON:
        reason_code = "UNREAD"
    return {
        "format_id": "visual-witness-e2-attempt-exit-v1",
        "event_id": "VW-E2",
        "event_revision": "VW-E2-R2",
        "packet_sha256": PACKET_SHA256,
        "created_at_utc": _utc_now(),
        "status": status,
        "last_completed_gate": last_completed_gate,
        "reason_code": reason_code,
        "claim_status": "Observed",
        "schema_conformance": "UNREAD",
        "next_event_authority": "UNSIGNED",
    }


def _failure_status(reason: str) -> str:
    if reason == "UNREAD" or reason.endswith("-UNREAD") or reason in ("VW-RENDER-UNREAD", "VW-COORDINATE-UNREAD"):
        return "UNREAD"
    if reason in ("GROUND-DRIFT", "AUTHORITY-MISSING", "VW-HELDOUT-CONTAMINATION"):
        return "STOPPED"
    return "FAILED"


def persist_partial_root_attempt_exit(
    context: PartialRootContext,
    run_id: str,
    failure: Mapping[str, Any],
) -> bool:
    evidence_run = context.evidence_run_created
    if evidence_run is None or not evidence_run.is_dir() or _is_reparse(evidence_run):
        return False
    target = evidence_run / f"vw-e2-r2-{run_id}-attempt-exit.json"
    try:
        create_new_json(target, failure)
    except BaseException:
        return False
    return True


@dataclass(frozen=True)
class CLIArguments:
    repo_root: Path
    private_manifest: Path
    evidence_root: Path
    scratch_root: Path
    run_id: str
    case_id: tuple[str, ...]


def parse_cli_arguments(argv: Sequence[str] | None) -> CLIArguments:
    tokens = list(sys.argv[1:] if argv is None else argv)
    singles: dict[str, str] = {}
    cases: list[str] = []
    allowed = {
        "--repo-root", "--private-manifest", "--evidence-root", "--scratch-root",
        "--run-id", "--case-id",
    }
    index = 0
    while index < len(tokens):
        option = tokens[index]
        if option not in allowed or index + 1 >= len(tokens):
            raise VWStop("AUTHORITY-MISSING", "invalid command-line shape")
        value = tokens[index + 1]
        if not isinstance(value, str) or not value or value.startswith("--"):
            raise VWStop("AUTHORITY-MISSING", "invalid command-line value")
        if option == "--case-id":
            cases.append(value)
        else:
            if option in singles:
                raise VWStop("AUTHORITY-MISSING", "duplicate command-line option")
            singles[option] = value
        index += 2
    required = ("--private-manifest", "--evidence-root", "--scratch-root", "--run-id")
    if any(option not in singles for option in required):
        raise VWStop("AUTHORITY-MISSING", "required command-line option absent")
    if RUN_ID_RE.fullmatch(singles["--run-id"]) is None:
        raise VWStop("AUTHORITY-MISSING", "run id is not an opaque CLI value")
    return CLIArguments(
        repo_root=Path(singles.get("--repo-root", str(Path(__file__).resolve().parents[1]))),
        private_manifest=Path(singles["--private-manifest"]),
        evidence_root=Path(singles["--evidence-root"]),
        scratch_root=Path(singles["--scratch-root"]),
        run_id=singles["--run-id"],
        case_id=tuple(cases),
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    event_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> int:
    global ACTIVE_ROOTS, ACTIVE_RUN_ID, ACTIVE_VERIFIER, LAST_COMPLETED_GATE
    ACTIVE_ROOTS = None
    ACTIVE_RUN_ID = None
    ACTIVE_VERIFIER = None
    LAST_COMPLETED_GATE = "START"
    try:
        args = parse_cli_arguments(argv)
        case_ids = args.case_id or list(ALLOWED_CASE_IDS)
        runner = run_event if event_runner is None else event_runner
        receipt = runner(
            repo_root=args.repo_root,
            private_manifest_path=args.private_manifest,
            evidence_root=args.evidence_root,
            scratch_root=args.scratch_root,
            run_id=args.run_id,
            selected_case_ids=case_ids,
        )
        sys.stdout.buffer.write(canonical_json_bytes(receipt) + b"\n")
        sys.stdout.buffer.flush()
        return 0
    except BaseException as exc:
        reason = exc.reason if isinstance(exc, VWStop) else "UNREAD"
        partial_context = exc.context if isinstance(exc, PartialRootFailure) else None
        if ACTIVE_VERIFIER is not None:
            try:
                if ACTIVE_VERIFIER.poll() is None:
                    ACTIVE_VERIFIER.kill()
                ACTIVE_VERIFIER.communicate(timeout=5)
                if ACTIVE_VERIFIER.pid is not None:
                    EVENT_CHILD_EXITED_PIDS.add(int(ACTIVE_VERIFIER.pid))
            except BaseException:
                reason = "VW-CLEANUP"
            finally:
                ACTIVE_VERIFIER = None
        if partial_context is None and ACTIVE_ROOTS is not None and ACTIVE_RUN_ID is not None and ACTIVE_ROOTS.scratch_run.exists():
            try:
                cleanup_scratch(ACTIVE_ROOTS, ACTIVE_RUN_ID)
            except BaseException:
                reason = "VW-CLEANUP"
        failure = minimal_attempt_exit(
            status=_failure_status(reason),
            last_completed_gate=LAST_COMPLETED_GATE,
            reason_code=reason,
        )
        raw = canonical_json_bytes(failure) + b"\n"
        if partial_context is not None and ACTIVE_RUN_ID is not None:
            persist_partial_root_attempt_exit(partial_context, ACTIVE_RUN_ID, failure)
        elif ACTIVE_ROOTS is not None and LAST_COMPLETED_GATE != "START":
            try:
                create_new_json(
                    ACTIVE_ROOTS.evidence_run / f"vw-e2-r2-{ACTIVE_RUN_ID}-attempt-exit.json",
                    failure,
                )
            except BaseException:
                pass
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        sys.stderr.write(reason + "\n")
        sys.stderr.flush()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
