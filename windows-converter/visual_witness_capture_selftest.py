"""Synthetic-only verifier and self-test for the VW-E2-R2 capture producer.

This file never resolves a corpus path.  Its schema engine implements only the JSON
Schema 2020-12 vocabulary used by the exact bound capture schema; unsupported keywords
are a hard test failure, not a silently ignored extension point.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import subprocess
import struct
import sys
import tempfile
import types
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from unittest import mock

import pymupdf

import visual_witness_capture as vw


SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "$schema",
        "$id",
        "$comment",
        "title",
        "$defs",
        "$ref",
        "type",
        "const",
        "enum",
        "format",
        "pattern",
        "minimum",
        "maximum",
        "minProperties",
        "minLength",
        "required",
        "properties",
        "additionalProperties",
        "minItems",
        "maxItems",
        "uniqueItems",
        "prefixItems",
        "items",
        "contains",
        "minContains",
        "maxContains",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
    }
)


@dataclass(frozen=True)
class SchemaFailure:
    path: str
    message: str


def _json_equal(left: Any, right: Any) -> bool:
    try:
        return vw.canonical_json_bytes(left) == vw.canonical_json_bytes(right)
    except vw.VWStop:
        return False


def _pointer(root: Mapping[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise AssertionError(f"unsupported non-local schema reference {reference!r}")
    value: Any = root
    for encoded in reference[2:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        value = value[token]
    return value


def _is_type(value: Any, type_name: str) -> bool:
    return {
        "null": value is None,
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "string": isinstance(value, str),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }[type_name]


def _valid_datetime(value: str) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def validate_schema(instance: Any, schema: Mapping[str, Any], *, root: Mapping[str, Any] | None = None, path: str = "$") -> list[SchemaFailure]:
    root = schema if root is None else root
    unknown = set(schema) - SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        raise AssertionError(f"unsupported schema keyword(s) at {path}: {sorted(unknown)}")
    if "$ref" in schema:
        return validate_schema(instance, _pointer(root, schema["$ref"]), root=root, path=path)
    failures: list[SchemaFailure] = []

    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_is_type(instance, name) for name in expected_types):
            return [SchemaFailure(path, f"expected type {expected_types}, got {type(instance).__name__}")]
    if "const" in schema and not _json_equal(instance, schema["const"]):
        failures.append(SchemaFailure(path, "does not equal const"))
    if "enum" in schema and not any(_json_equal(instance, item) for item in schema["enum"]):
        failures.append(SchemaFailure(path, "not in enum"))
    if isinstance(instance, str):
        if len(instance) < int(schema.get("minLength", 0)):
            failures.append(SchemaFailure(path, "shorter than minLength"))
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            failures.append(SchemaFailure(path, f"does not match {schema['pattern']!r}"))
        if schema.get("format") == "date-time" and not _valid_datetime(instance):
            failures.append(SchemaFailure(path, "not an RFC3339 UTC date-time"))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if not math.isfinite(instance):
            failures.append(SchemaFailure(path, "number is not finite"))
        if "minimum" in schema and instance < schema["minimum"]:
            failures.append(SchemaFailure(path, "below minimum"))
        if "maximum" in schema and instance > schema["maximum"]:
            failures.append(SchemaFailure(path, "above maximum"))

    if isinstance(instance, dict):
        if len(instance) < int(schema.get("minProperties", 0)):
            failures.append(SchemaFailure(path, "fewer than minProperties"))
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                failures.append(SchemaFailure(path, f"missing required member {key!r}"))
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                failures.extend(validate_schema(value, properties[key], root=root, path=f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                failures.append(SchemaFailure(path, f"unexpected member {key!r}"))
            elif isinstance(schema.get("additionalProperties"), dict):
                failures.extend(validate_schema(value, schema["additionalProperties"], root=root, path=f"{path}.{key}"))

    if isinstance(instance, list):
        if len(instance) < int(schema.get("minItems", 0)):
            failures.append(SchemaFailure(path, "fewer than minItems"))
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            failures.append(SchemaFailure(path, "more than maxItems"))
        if schema.get("uniqueItems"):
            encoded = [vw.canonical_json_bytes(item) for item in instance]
            if len(encoded) != len(set(encoded)):
                failures.append(SchemaFailure(path, "array items are not unique"))
        prefix = schema.get("prefixItems", [])
        for index, subschema in enumerate(prefix):
            if index < len(instance):
                failures.extend(validate_schema(instance[index], subschema, root=root, path=f"{path}[{index}]"))
        if isinstance(schema.get("items"), dict):
            start = len(prefix) if prefix else 0
            for index in range(start, len(instance)):
                failures.extend(validate_schema(instance[index], schema["items"], root=root, path=f"{path}[{index}]"))
        if "contains" in schema:
            matching = sum(not validate_schema(item, schema["contains"], root=root, path=path) for item in instance)
            minimum = int(schema.get("minContains", 1))
            maximum = schema.get("maxContains")
            if matching < minimum or (maximum is not None and matching > int(maximum)):
                failures.append(SchemaFailure(path, f"contains count {matching} outside [{minimum},{maximum}]"))

    for subschema in schema.get("allOf", []):
        failures.extend(validate_schema(instance, subschema, root=root, path=path))
    if "anyOf" in schema and not any(not validate_schema(instance, item, root=root, path=path) for item in schema["anyOf"]):
        failures.append(SchemaFailure(path, "matches no anyOf branch"))
    if "oneOf" in schema:
        matches = sum(not validate_schema(instance, item, root=root, path=path) for item in schema["oneOf"])
        if matches != 1:
            failures.append(SchemaFailure(path, f"matches {matches} oneOf branches"))
    if "not" in schema and not validate_schema(instance, schema["not"], root=root, path=path):
        failures.append(SchemaFailure(path, "matches forbidden not schema"))
    if "if" in schema:
        condition_matches = not validate_schema(instance, schema["if"], root=root, path=path)
        if condition_matches and "then" in schema:
            failures.extend(validate_schema(instance, schema["then"], root=root, path=path))
        if not condition_matches and "else" in schema:
            failures.extend(validate_schema(instance, schema["else"], root=root, path=path))
    return failures


def assert_bound_schema(report: Any, schema: Mapping[str, Any]) -> None:
    failures = validate_schema(report, schema)
    if failures:
        preview = "; ".join(f"{item.path}: {item.message}" for item in failures[:12])
        raise vw.VWStop("VW-IDENTITY", f"capture schema validation failed ({len(failures)}): {preview}")


def load_bound_schema(repo_root: Path) -> Mapping[str, Any]:
    path = repo_root / vw.CAPTURE_SCHEMA_RELATIVE_PATH
    raw = path.read_bytes()
    if len(raw) != vw.CAPTURE_SCHEMA_BYTES or vw.sha256_bytes(raw) != vw.CAPTURE_SCHEMA_SHA256:
        raise vw.VWStop("GROUND-DRIFT", "capture schema identity mismatch")
    schema = vw.strict_json_bytes(raw)
    if not isinstance(schema, dict):
        raise vw.VWStop("GROUND-DRIFT", "capture schema root is not an object")
    return schema


def _complete_receipt_fixture(repo_root: Path) -> tuple[dict[str, Any], Mapping[str, Any]]:
    packet = vw.strict_json_file(repo_root / vw.PACKET_RELATIVE_PATH)
    ordinary = [
        vw.semantic_check_object(
            name,
            status="pass",
            subject_sha256="1" * 64,
            validator_code_sha256="2" * 64,
        )
        for name in vw.ORDINARY_CHECK_NAMES
    ]
    independent = {
        "verifier": "codex-independent-verifier-v1",
        "status": "Verified-independent",
        "probe_id": "vw-e2-r2-independent-sample-v1",
        "verifier_code_sha256": "3" * 64,
        "packet_sha256": vw.PACKET_SHA256,
        "capture_schema_sha256": vw.CAPTURE_SCHEMA_SHA256,
        "capture_payload_sha256": "4" * 64,
        "semantic_checks_sha256": "5" * 64,
        "evidence_sha256": "6" * 64,
        "reason_codes": [],
    }
    report = {
        "capture_payload": {
            "case_census": {
                "declared": 3, "attempted": 3, "completed": 3, "unread": 0,
                "case_ids": list(vw.ALLOWED_CASE_IDS),
            }
        },
        "semantic_checks": ordinary,
        "run_observations": {
            "resources": {
                "cpu_seconds": 1.25, "wall_seconds": 2.5, "scratch_peak_bytes": 4096,
                "gpu_used": False, "network_used": False,
                "case_workers": [
                    {"case_id": case_id, "peak_working_set_bytes": 8192}
                    for case_id in vw.ALLOWED_CASE_IDS
                ],
            },
            "independent_verification": independent,
            "protected_tree": {"before_sha256": "7" * 64},
        },
    }
    report_bytes = vw.canonical_json_bytes(report) + b"\n"
    receipt = vw._build_receipt(
        packet=packet,
        report=report,
        report_bytes=report_bytes,
        report_sha256=vw.sha256_bytes(report_bytes),
        report_relative_path="synthetic/vw-e2-r2-synthetic-operational-report.json",
        repo_head_before="8" * 40,
        repo_head_after="8" * 40,
        negative_control_suite_identity=vw.execute_frozen_negative_controls(),
    )
    return receipt, packet


class SchemaEngineSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_bound_schema(Path(__file__).resolve().parents[1])

    def test_bound_schema_uses_only_supported_keywords(self) -> None:
        vocabulary = {
            key
            for node in _walk(self.schema)
            if isinstance(node, dict)
            for key in node
            if key.startswith("$") or key in SUPPORTED_SCHEMA_KEYWORDS
        }
        self.assertTrue(vocabulary <= SUPPORTED_SCHEMA_KEYWORDS)

    def test_duplicate_and_nonfinite_json_bite(self) -> None:
        with self.assertRaises(vw.VWStop):
            vw.strict_json_bytes(b'{"a":1,"a":2}')
        with self.assertRaises(vw.VWStop):
            vw.strict_json_bytes(b'{"a":NaN}')

    def test_schema_negative_additional_property_bites(self) -> None:
        definition = self.schema["$defs"]["tile"]
        tile = {
            "tile_id": "p000001-x000000-y000000",
            "bbox_px_half_open": [0, 0, 1, 1],
            "rgb_bytes": 3,
            "rgb_sha256": "0" * 64,
        }
        self.assertEqual([], validate_schema(tile, definition, root=self.schema))
        poisoned = dict(tile, invented=True)
        self.assertTrue(validate_schema(poisoned, definition, root=self.schema))

    def test_complete_receipt_validates_and_else_minproperties_bite(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        receipt, _packet = _complete_receipt_fixture(repo)
        receipt_schema = vw.assert_receipt_schema(repo, receipt)
        self.assertEqual([], validate_schema(receipt, receipt_schema))
        packet = vw.strict_json_file(repo / vw.PACKET_RELATIVE_PATH)
        scan = vw.retained_string_scan(receipt, packet=packet, schema=receipt_schema, private_dictionary=[])
        self.assertTrue(all(value == 0 for value in scan.values()), scan)
        wrong_else = copy.deepcopy(receipt)
        wrong_else["network"]["consent_receipt"] = {}
        self.assertTrue(validate_schema(wrong_else, receipt_schema))
        empty_consent = copy.deepcopy(receipt)
        empty_consent["network"] = {"used": True, "consent_receipt": {}}
        failures = validate_schema(empty_consent, receipt_schema)
        self.assertTrue(any("minProperties" in failure.message for failure in failures))


class FrozenCoreSelfTest(unittest.TestCase):
    def test_production_negative_control_suite_executes_and_nonbite_stops(self) -> None:
        self.assertEqual(vw.PACKET_SHA256, vw.execute_frozen_negative_controls())
        with mock.patch.object(vw, "check_tile_union", return_value={"status": "measured"}):
            with self.assertRaisesRegex(vw.VWStop, "VW-NEGATIVE-CONTROL"):
                vw.execute_frozen_negative_controls()

    def test_production_cli_missing_argument_has_no_argparse_leakage(self) -> None:
        capture = Path(__file__).with_name("visual_witness_capture.py")
        completed = subprocess.run(
            [
                sys.executable, "-B", str(capture),
                "--private-manifest", r"Z:\must-not-resolve\manifest.json",
                "--evidence-root", r"Z:\must-not-resolve\evidence",
                "--run-id", "synthetic-missing-negative",
            ],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        attempt = vw.strict_json_bytes(completed.stdout.rstrip(b"\n"), reason="UNREAD")
        self.assertEqual(vw.canonical_json_bytes(attempt) + b"\n", completed.stdout)
        self.assertEqual("START", attempt["last_completed_gate"])
        self.assertEqual("STOPPED", attempt["status"])
        self.assertEqual("AUTHORITY-MISSING", attempt["reason_code"])
        self.assertEqual([b"AUTHORITY-MISSING"], completed.stderr.splitlines())
        self.assertNotIn(b"usage", completed.stderr.lower())

    def test_production_cli_heldout_stop_is_minimal_and_pre_resolution(self) -> None:
        capture = Path(__file__).with_name("visual_witness_capture.py")
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(capture),
                "--private-manifest", r"Z:\must-not-resolve\manifest.json",
                "--evidence-root", r"Z:\must-not-resolve\evidence",
                "--scratch-root", r"Z:\must-not-resolve\scratch",
                "--run-id", "synthetic-heldout-negative",
                "--case-id", "VW-H01",
            ],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        attempt = vw.strict_json_bytes(completed.stdout.strip(), reason="UNREAD")
        self.assertEqual("visual-witness-e2-attempt-exit-v1", attempt["format_id"])
        self.assertEqual("START", attempt["last_completed_gate"])
        self.assertEqual("STOPPED", attempt["status"])
        self.assertEqual("VW-HELDOUT-CONTAMINATION", attempt["reason_code"])
        self.assertEqual(b"VW-HELDOUT-CONTAMINATION", completed.stderr.strip())

    def test_packet_and_configuration_binding(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        raw = (repo / vw.PACKET_RELATIVE_PATH).read_bytes()
        self.assertEqual(vw.PACKET_BYTES, len(raw))
        self.assertEqual(vw.PACKET_SHA256, vw.sha256_bytes(raw))
        packet = vw.strict_json_bytes(raw)
        self.assertEqual(vw.EXPECTED_CONFIG_SHA256, vw.config_sha256(packet["frozen_configuration"]))

    def test_half_even_and_negative_zero(self) -> None:
        self.assertEqual("1.234568", vw.point_string("1.2345675"))
        self.assertEqual("1.234566", vw.point_string("1.2345665"))
        self.assertEqual("0.000000", vw.point_string("-0.0000001"))
        self.assertEqual("0.000000000", vw.normalized_string("-0.0000000001"))

    def test_tile_properties_and_frozen_center_hole(self) -> None:
        for width, height in ((1, 1), (17, 31), (1024, 1024), (1025, 2047), (2501, 999)):
            tiles = vw.make_tiles(1, width, height)
            result = vw.check_tile_union(width, height, tiles)
            self.assertEqual(width * height, result["numerator"])
            self.assertEqual(1.0, result["value"])
        planted = [
            {"bbox_px_half_open": [0, 0, 3, 1]},
            {"bbox_px_half_open": [0, 2, 3, 3]},
            {"bbox_px_half_open": [0, 1, 1, 2]},
            {"bbox_px_half_open": [2, 1, 3, 2]},
        ]
        self.assertEqual(8, vw.exact_union_area([vw.Box(*item["bbox_px_half_open"]) for item in planted]))
        with self.assertRaisesRegex(vw.VWStop, "VW-TILE-GAP"):
            vw.check_tile_union(3, 3, planted)

    def test_source_identity_gate_and_id_domains(self) -> None:
        sha = "1" * 64
        source = {
            "status": "measured",
            "manifest_sha256": sha,
            "recorded_actual_sha256": sha,
            "observed_sha256": sha,
            "all_hashes_match": True,
        }
        self.assertEqual(sha, vw.measured_source_identity(source).sha256)
        poison = dict(source, observed_sha256="2" * 64)
        with self.assertRaisesRegex(vw.VWStop, "VW-SOURCE-HASH"):
            vw.measured_source_identity(poison)
        primitive = {
            "source_sha256": sha,
            "page_1based": 1,
            "kind": "text",
            "method": vw.TEXT_METHOD,
            "bbox_pdf_pt": ["0.000000", "0.000000", "1.000000", "1.000000"],
            "bbox_px_half_open": [0, 0, 3, 3],
            "identity_attributes": {"utf8_sha256": "2" * 64, "utf8_bytes": 1, "unicode_codepoints": 1},
        }
        manual = "sha256:" + hashlib.sha256(vw.DOMAINS["primitive"] + vw.canonical_json_bytes(primitive)).hexdigest()
        self.assertEqual(manual, vw.primitive_id(primitive))
        payload = {"event_id": "VW-E2", "capture_payload_sha256": "0" * 64}
        expected = hashlib.sha256(vw.DOMAINS["capture_payload"] + vw.canonical_json_bytes({"event_id": "VW-E2"})).hexdigest()
        self.assertEqual(expected, vw.capture_payload_sha256(payload))

    def test_heldout_guard_precedes_resolver(self) -> None:
        observed: list[str] = []
        with self.assertRaisesRegex(vw.VWStop, "VW-HELDOUT-CONTAMINATION"):
            vw.lexical_case_guard(["VW-T01", "VW-H01"], resolver_spy=observed.append)
        self.assertEqual([], observed)
        self.assertEqual(("VW-T01", "VW-T03"), vw.lexical_case_guard(["VW-T01", "VW-T03"], resolver_spy=observed.append))
        self.assertEqual(["VW-T01", "VW-T03"], observed)

    def test_two_pixel_gap_clusters_three_does_not(self) -> None:
        def primitive(identifier: str, bbox: list[int]) -> dict[str, Any]:
            return {"primitive_id": "sha256:" + identifier * 64, "bbox": bbox}

        at_two = [primitive("1", [0, 0, 1, 1]), primitive("2", [3, 0, 4, 1])]
        at_three = [primitive("1", [0, 0, 1, 1]), primitive("2", [4, 0, 5, 1])]
        self.assertEqual(1, len(vw.connected_components(at_two, bbox_key="bbox", gap=2)))
        self.assertEqual(2, len(vw.connected_components(at_three, bbox_key="bbox", gap=2)))

    def test_protected_inventory_mutation_bites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.pdf"
            path.write_bytes(b"before")
            files = [vw.ProtectedFile("VW-T01/source", path)]
            before_entries, before_digest = vw.protected_inventory(files)
            path.write_bytes(b"after")
            after_entries, after_digest = vw.protected_inventory(files)
            with self.assertRaisesRegex(vw.VWStop, "VW-PROTECTED-TREE"):
                vw.compare_protected_inventories(before_entries, before_digest, after_entries, after_digest)

    def test_blank_synthetic_page_completes_six_procedures(self) -> None:
        document = pymupdf.open()
        page = document.new_page(width=72, height=72)
        source_bytes = document.tobytes()
        sha = vw.sha256_bytes(source_bytes)
        source = {
            "status": "measured",
            "manifest_sha256": sha,
            "recorded_actual_sha256": sha,
            "observed_sha256": sha,
            "all_hashes_match": True,
        }
        capture = vw.capture_page(
            page,
            page_1based=1,
            source_observation=source,
            configuration_sha256=vw.EXPECTED_CONFIG_SHA256,
        )
        self.assertEqual([], capture.report["region_candidates"])
        self.assertEqual(list(vw.CLASS_ORDER), [item["class"] for item in capture.report["class_procedures"]])
        self.assertTrue(all(item["status"] == "measured" for item in capture.report["class_procedures"]))
        capture.clear()
        self.assertEqual(b"", capture.render_rgb)

    def test_frozen_page_map_fixtures_and_same_check_poison(self) -> None:
        sha = "1" * 64
        source = {
            "status": "measured",
            "manifest_sha256": sha,
            "recorded_actual_sha256": sha,
            "observed_sha256": sha,
            "all_hashes_match": True,
            "pages": 10,
        }
        inventory = {"status": "measured", "match": True, "count": 2}

        def assets(ids: Sequence[int]) -> list[dict[str, Any]]:
            return [
                {"asset_ordinal": ordinal, "page_id_0based": page_id, "bytes": 1, "sha256": "2" * 64}
                for ordinal, page_id in enumerate(ids)
            ]

        retained, page_map, blockers = vw.mechanical_page_map(
            source_observation=source,
            asset_inventory=inventory,
            asset_observations=assets([0, 10]),
            manifest_asset_count=2,
            chunking_slice_size=None,
        )
        self.assertEqual("untrustworthy", page_map["state"])
        self.assertTrue(blockers)
        self.assertEqual("UNREAD", retained[0]["source_page_relation"])

        source_sym = dict(source, pages=450)
        ids = [0, 199, 400, 599, 800]
        retained, page_map, blockers = vw.mechanical_page_map(
            source_observation=source_sym,
            asset_inventory={"status": "measured", "match": True, "count": 5},
            asset_observations=assets(ids),
            manifest_asset_count=5,
            chunking_slice_size=200,
        )
        self.assertEqual("repaired-sym050", page_map["state"])
        self.assertFalse(blockers)

        fresh = assets([0, 5, 9])
        retained = [
            {"asset_ordinal": 0, "page_id_0based": 0, "claim_status": "Observed", "source_page_relation": "UNREAD"},
            {"asset_ordinal": 1, "page_id_0based": 6, "claim_status": "Observed", "source_page_relation": "UNREAD"},
            {"asset_ordinal": 2, "page_id_0based": 9, "claim_status": "Observed", "source_page_relation": "UNREAD"},
        ]
        with self.assertRaisesRegex(vw.VWStop, "VW-PAGE-MAP-UNREAD"):
            vw.assert_retained_page_map(retained, fresh)


class BoundNativeGitProbeSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.original_activity = copy.deepcopy(vw.EVENT_ACTIVITY)
        self.original_children = set(vw.EVENT_CHILD_PIDS)
        self.original_exited = set(vw.EVENT_CHILD_EXITED_PIDS)
        self.original_descendants = set(vw.EVENT_OBSERVED_DESCENDANT_PIDS)
        self.original_heads = set(vw.EVENT_MEASURED_GIT_HEADS)
        self.original_audit_active = vw._EVENT_AUDIT_ACTIVE
        vw.EVENT_ACTIVITY.reset()
        vw.EVENT_CHILD_PIDS.clear()
        vw.EVENT_CHILD_EXITED_PIDS.clear()
        vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear()
        vw.EVENT_MEASURED_GIT_HEADS.clear()

    def tearDown(self) -> None:
        vw.EVENT_ACTIVITY = self.original_activity
        vw.EVENT_CHILD_PIDS.clear(); vw.EVENT_CHILD_PIDS.update(self.original_children)
        vw.EVENT_CHILD_EXITED_PIDS.clear(); vw.EVENT_CHILD_EXITED_PIDS.update(self.original_exited)
        vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear(); vw.EVENT_OBSERVED_DESCENDANT_PIDS.update(self.original_descendants)
        vw.EVENT_MEASURED_GIT_HEADS.clear(); vw.EVENT_MEASURED_GIT_HEADS.update(self.original_heads)
        vw._EVENT_AUDIT_ACTIVE = self.original_audit_active

    @staticmethod
    def _fake_process(pid: int, stdout: bytes):
        class FakeProcess:
            def __init__(self) -> None:
                self.pid = pid
                self.returncode = 0

            def poll(self) -> int:
                return self.returncode

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                del timeout
                return stdout, b""

            def kill(self) -> None:
                self.returncode = -9

        return FakeProcess()

    def test_allowed_probes_register_exit_and_exact_sanitized_controls(self) -> None:
        observed: list[tuple[list[str], dict[str, Any]]] = []
        head = vw.REPOSITORY_SHA
        processes = iter((self._fake_process(41001, (head + "\n").encode("ascii")), self._fake_process(41002, b"x\0")))

        def fake_popen(command: list[str], **kwargs: Any):
            observed.append((list(command), dict(kwargs)))
            return next(processes)

        clean_measurement = lambda known: vw.IsolationMeasurement(tuple(sorted(known)), (), ())
        vw.install_event_activity_audit()
        with mock.patch.object(vw.subprocess, "Popen", side_effect=fake_popen), mock.patch.object(
            vw, "_census_native_git_descendants", return_value=set()
        ), mock.patch.object(vw, "native_isolation_measurement", side_effect=clean_measurement), mock.patch.object(
            vw, "_bind_native_git_single_process_job", return_value=91001
        ), mock.patch.object(vw, "_resume_native_git_process"), mock.patch.object(
            vw, "_close_native_git_job"
        ):
            self.assertEqual((head + "\n").encode("ascii"), vw._git(self.repo, "rev-parse", "HEAD"))
            self.assertEqual(
                b"x\0",
                vw._git(self.repo, "diff", "--name-only", "-z", f"{vw.REPOSITORY_SHA}..{head}"),
            )

        self.assertEqual(2, len(observed))
        for command, kwargs in observed:
            self.assertEqual(str(vw.GIT_EXECUTABLE), command[0])
            self.assertIn("--no-pager", command)
            self.assertEqual(self.repo, kwargs["cwd"])
            self.assertIs(subprocess.DEVNULL, kwargs["stdin"])
            self.assertIs(subprocess.PIPE, kwargs["stdout"])
            self.assertIs(subprocess.PIPE, kwargs["stderr"])
            self.assertTrue(kwargs["creationflags"] & 0x00000004)
            environment = kwargs["env"]
            self.assertFalse(any(key.casefold() == "path" for key in environment))
            self.assertFalse(any(key.casefold() in ("home", "userprofile") for key in environment))
            for key, value in vw.GIT_FIXED_ENVIRONMENT:
                self.assertEqual(value, environment[key])
            for setting in vw.GIT_FIXED_CONFIG:
                self.assertIn(setting, command)
        self.assertIn("--no-ext-diff", observed[1][0])
        self.assertIn("--no-textconv", observed[1][0])
        self.assertEqual({41001, 41002}, vw.EVENT_CHILD_PIDS)
        self.assertEqual({41001, 41002}, vw.EVENT_CHILD_EXITED_PIDS)
        self.assertEqual(2, vw.EVENT_ACTIVITY.native_git_expected_processes)
        self.assertEqual(2, vw.EVENT_ACTIVITY.native_git_reconciled_processes)
        self.assertEqual(2, len(vw.EVENT_ACTIVITY.native_git_attestations))
        vw.require_event_activity_reconciled(0)

    def test_binary_hash_mismatch_and_disallowed_arguments_stop_before_spawn(self) -> None:
        with mock.patch.object(vw.subprocess, "Popen") as popen, mock.patch.object(
            vw, "stable_file_observation", return_value={"bytes": vw.GIT_EXECUTABLE_BYTES, "sha256": "0" * 64}
        ):
            with self.assertRaisesRegex(vw.VWStop, "VW-DEPENDENCY-DRIFT"):
                vw._git(self.repo, "rev-parse", "HEAD")
            popen.assert_not_called()
        with mock.patch.object(vw.subprocess, "Popen") as popen:
            for arguments in (
                ("fetch", "origin"),
                ("remote", "-v"),
                ("ls-remote", "origin"),
                ("status", "--porcelain=v1"),
            ):
                with self.subTest(arguments=arguments):
                    with self.assertRaisesRegex(vw.VWStop, "GROUND-DRIFT"):
                        vw._git(self.repo, *arguments)
            popen.assert_not_called()
        self.assertEqual(0, vw.EVENT_ACTIVITY.native_git_expected_processes)

    def test_exact_binary_ignores_injected_path_wrapper_and_runtime_inventory_binds_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trap = Path(temporary)
            sentinel = trap / "path-wrapper-called.txt"
            (trap / "git.cmd").write_text(
                f"@echo off\r\necho called>\"{sentinel}\"\r\nexit /b 91\r\n",
                encoding="utf-8",
            )
            (trap / "git.exe").write_bytes(b"not-an-executable")
            with mock.patch.dict(os.environ, {"PATH": str(trap)}, clear=False):
                output = vw._git(self.repo, "rev-parse", "HEAD")
                measured_head = output[:-1].decode("ascii")
                merge_base = vw._git(self.repo, "merge-base", vw.REPOSITORY_SHA, measured_head)
                vw._git(self.repo, "diff", "--name-only", "-z", f"{vw.REPOSITORY_SHA}..{measured_head}")
                vw._git(self.repo, "status", "--porcelain=v1", "--untracked-files=all", "-z")
            self.assertRegex(output, rb"^[0-9a-f]{40}\n$")
            self.assertEqual((vw.REPOSITORY_SHA + "\n").encode("ascii"), merge_base)
            self.assertFalse(sentinel.exists())
        self.assertEqual(4, vw.EVENT_ACTIVITY.native_git_expected_processes)
        self.assertEqual(4, vw.EVENT_ACTIVITY.native_git_reconciled_processes)
        self.assertEqual(vw.EVENT_CHILD_PIDS, vw.EVENT_CHILD_EXITED_PIDS)
        self.assertEqual(
            {"bytes": vw.GIT_EXECUTABLE_BYTES, "sha256": vw.GIT_EXECUTABLE_SHA256},
            vw._verified_git_executable_observation(),
        )

        def synthetic_observation(path: Path, _reason: str) -> dict[str, Any]:
            if Path(path) == vw.GIT_EXECUTABLE:
                return {"bytes": vw.GIT_EXECUTABLE_BYTES, "sha256": vw.GIT_EXECUTABLE_SHA256}
            return {"bytes": 1, "sha256": "1" * 64}

        synthetic_modules = [Path("python312.dll"), Path("_mupdf.pyd"), Path("mupdfcpp64.dll")]
        with mock.patch.object(vw, "_windows_process_module_paths", return_value=synthetic_modules), mock.patch.object(
            vw, "stable_file_observation", side_effect=synthetic_observation
        ):
            inventory = vw.runtime_module_inventory()
        git_entries = [entry for entry in inventory if entry["logical_name"] == "git_executable"]
        self.assertEqual(
            [{"logical_name": "git_executable", "bytes": vw.GIT_EXECUTABLE_BYTES, "sha256": vw.GIT_EXECUTABLE_SHA256}],
            git_entries,
        )

    def test_local_config_filter_control_triggers_but_production_status_does_not(self) -> None:
        self.assertIn(("GIT_CONFIG", "NUL"), vw.GIT_FIXED_ENVIRONMENT)
        self.assertIn(("GIT_ATTR_SOURCE", "0" * 40), vw.GIT_FIXED_ENVIRONMENT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            helper = root / "clean_filter.py"
            sentinel = root / "local-filter-called.txt"
            helper.write_text(
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_text('called', encoding='ascii')\n"
                "sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
                encoding="utf-8",
            )

            control_environment = os.environ.copy()
            for key in ("GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"):
                control_environment.pop(key, None)
            control_environment.update(
                {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never", "GIT_OPTIONAL_LOCKS": "0"}
            )

            def control_git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [
                        str(vw.GIT_EXECUTABLE),
                        "--no-pager",
                        "-c",
                        f"safe.directory={repository}",
                        *arguments,
                    ],
                    cwd=repository,
                    env=control_environment,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=20,
                    check=check,
                )

            control_git("init", "-q")
            payload = repository / "payload.txt"
            payload.write_text("base\n", encoding="utf-8")
            (repository / ".gitattributes").write_text("payload.txt filter=sentinel\n", encoding="utf-8")
            info_attributes = repository / ".git" / "info" / "attributes"
            info_attributes.write_text("payload.txt filter=sentinel\n", encoding="utf-8")
            control_git("add", "--", ".gitattributes", "payload.txt")
            command = " ".join(
                (
                    f'"{Path(sys.executable).as_posix()}"',
                    f'"{helper.as_posix()}"',
                    f'"{sentinel.as_posix()}"',
                )
            )
            control_git("config", "filter.sentinel.clean", command)
            control_git("config", "filter.sentinel.required", "true")
            configured = control_git("config", "--get", "filter.sentinel.clean")
            self.assertIn(helper.as_posix().encode("utf-8"), configured.stdout)
            # Same-size content forces status to compare through the configured clean filter
            # instead of declaring a size-only difference without invoking it.
            payload.write_text("next\n", encoding="utf-8")
            sentinel.unlink(missing_ok=True)
            control_status = control_git("status", "--porcelain=v1", "--untracked-files=all", "-z")
            self.assertIn(b"payload.txt", control_status.stdout)
            self.assertTrue(sentinel.is_file(), "normal local-config control did not invoke the harmless filter")

            sentinel.unlink()
            with self.assertRaisesRegex(vw.VWStop, "GROUND-DRIFT"):
                vw._git(
                    repository,
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                    "-z",
                )
            self.assertFalse(sentinel.exists(), "production Git loaded the repository-local filter helper")

    def test_missing_native_reconciliation_blocks_completion(self) -> None:
        vw.install_event_activity_audit()
        vw.EVENT_ACTIVITY.native_git_expected_processes = 1
        vw.EVENT_ACTIVITY.native_git_reconciled_processes = 0
        with self.assertRaisesRegex(vw.VWStop, "UNREAD"):
            vw.require_event_activity_reconciled(0)


class DirectRepositoryHeadSelfTest(unittest.TestCase):
    def test_symbolic_loose_and_worktree_commondir_packed_refs(self) -> None:
        self.assertEqual(vw.REPOSITORY_SHA, vw.resolve_repository_head_direct(Path(__file__).resolve().parents[1]))
        loose_oid = "1" * 40
        packed_oid = "2" * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            loose_repo = root / "loose"
            loose_ref = loose_repo / ".git" / "refs" / "heads" / "main"
            loose_ref.parent.mkdir(parents=True)
            (loose_repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            loose_ref.write_text(loose_oid + "\n", encoding="ascii")
            self.assertEqual(loose_oid, vw.resolve_repository_head_direct(loose_repo))

            worktree = root / "worktree"
            common = root / "common.git"
            admin = common / "worktrees" / "w1"
            worktree.mkdir()
            admin.mkdir(parents=True)
            (worktree / ".git").write_text(f"gitdir: {admin.as_posix()}\n", encoding="ascii")
            (admin / "HEAD").write_text("ref: refs/heads/packed\n", encoding="ascii")
            (admin / "commondir").write_text("../..\n", encoding="ascii")
            (common / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled sorted\n"
                f"{packed_oid} refs/heads/packed\n",
                encoding="ascii",
            )
            self.assertEqual(packed_oid, vw.resolve_repository_head_direct(worktree))

    def test_receipt_builder_observes_exact_persisted_report(self) -> None:
        old_oid = "3" * 40
        original_gate = vw.LAST_COMPLETED_GATE
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repo"
            reference = repository / ".git" / "refs" / "heads" / "main"
            reference.parent.mkdir(parents=True)
            (repository / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            reference.write_text(old_oid + "\n", encoding="ascii")
            output = root / "evidence"
            output.mkdir()
            report_path = output / "report.json"
            receipt_path = output / "receipt.json"
            order: list[str] = []

            def build_receipt(report_bytes: bytes, report_sha: str) -> Mapping[str, Any]:
                order.append("receipt-builder")
                self.assertTrue(report_path.is_file())
                self.assertEqual(report_path.read_bytes(), report_bytes)
                self.assertEqual(vw.sha256_bytes(report_bytes), report_sha)
                return {
                    "repo_head_after": old_oid,
                    "report_bytes": len(report_bytes),
                    "report_sha256": report_sha,
                }

            def validate_receipt(candidate: Mapping[str, Any]) -> None:
                order.append("receipt-validator")
                self.assertTrue(report_path.is_file())
                self.assertEqual(report_path.stat().st_size, candidate["report_bytes"])

            try:
                receipt = vw.persist_complete_output_payloads(
                    repo_root=repository,
                    expected_repo_head=old_oid,
                    report={"status": "prepared"},
                    report_path=report_path,
                    receipt_path=receipt_path,
                    receipt_builder=build_receipt,
                    receipt_validator=validate_receipt,
                )
            finally:
                vw.LAST_COMPLETED_GATE = original_gate
            self.assertEqual(["receipt-builder", "receipt-validator"], order)
            self.assertEqual(old_oid, receipt["repo_head_after"])
            self.assertEqual(vw.canonical_json_bytes(receipt) + b"\n", receipt_path.read_bytes())

    def test_concurrent_head_change_after_report_preserves_report_and_emits_attempt_exit(self) -> None:
        old_oid = "3" * 40
        new_oid = "4" * 40
        original_gate = vw.LAST_COMPLETED_GATE
        original_roots, original_run_id = vw.ACTIVE_ROOTS, vw.ACTIVE_RUN_ID
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repo"
            reference = repository / ".git" / "refs" / "heads" / "main"
            reference.parent.mkdir(parents=True)
            (repository / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            reference.write_text(old_oid + "\n", encoding="ascii")
            evidence_root, scratch_root = root / "evidence", root / "scratch"
            evidence_root.mkdir(); scratch_root.mkdir()
            run_id = "post-report-head-drift"
            evidence_run = evidence_root / run_id
            evidence_run.mkdir()
            roots = vw.OutputRoots(
                evidence_root=evidence_root,
                scratch_root=scratch_root,
                evidence_run=evidence_run,
                scratch_run=scratch_root / run_id,
                scratch_free_bytes_before=vw.MIN_SCRATCH_FREE + 1,
            )
            report_path = evidence_run / f"vw-e2-r2-{run_id}-operational-report.json"
            receipt_path = evidence_run / f"vw-e2-r2-{run_id}-receipt.json"

            def event_runner(**_kwargs: Any) -> Mapping[str, Any]:
                vw.ACTIVE_ROOTS = roots
                vw.ACTIVE_RUN_ID = run_id

                def build_receipt(report_bytes: bytes, report_sha: str) -> Mapping[str, Any]:
                    self.assertEqual(report_path.read_bytes(), report_bytes)
                    reference.write_text(new_oid + "\n", encoding="ascii")
                    return {"report_sha256": report_sha, "repo_head_after": old_oid}

                return vw.persist_complete_output_payloads(
                    repo_root=repository,
                    expected_repo_head=old_oid,
                    report={"status": "prepared"},
                    report_path=report_path,
                    receipt_path=receipt_path,
                    receipt_builder=build_receipt,
                    receipt_validator=lambda _candidate: None,
                )

            stdout_bytes = io.BytesIO()
            stdout_text = io.TextIOWrapper(stdout_bytes, encoding="utf-8", write_through=True)
            stderr_text = io.StringIO()
            original_stdout, original_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout_text, stderr_text
                exit_code = vw.main(
                    [
                        "--private-manifest", str(root / "unused.json"),
                        "--evidence-root", str(evidence_root),
                        "--scratch-root", str(scratch_root),
                        "--run-id", run_id,
                    ],
                    event_runner=event_runner,
                )
                stdout_text.flush()
                emitted = stdout_bytes.getvalue()
            finally:
                sys.stdout, sys.stderr = original_stdout, original_stderr
                vw.LAST_COMPLETED_GATE = original_gate
                vw.ACTIVE_ROOTS, vw.ACTIVE_RUN_ID = original_roots, original_run_id
            self.assertEqual(2, exit_code)
            self.assertEqual("GROUND-DRIFT\n", stderr_text.getvalue())
            attempt = vw.strict_json_bytes(emitted[:-1])
            self.assertEqual("STOPPED", attempt["status"])
            self.assertEqual("REPORT-CREATED", attempt["last_completed_gate"])
            self.assertTrue(report_path.is_file())
            self.assertFalse(receipt_path.exists())
            attempt_path = evidence_run / f"vw-e2-r2-{run_id}-attempt-exit.json"
            self.assertEqual(vw.canonical_json_bytes(attempt) + b"\n", attempt_path.read_bytes())

    def test_receipt_validation_failure_preserves_report_without_receipt(self) -> None:
        old_oid = "5" * 40
        original_gate = vw.LAST_COMPLETED_GATE
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repo"
            reference = repository / ".git" / "refs" / "heads" / "main"
            reference.parent.mkdir(parents=True)
            (repository / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            reference.write_text(old_oid + "\n", encoding="ascii")
            output = root / "evidence"
            output.mkdir()
            report_path, receipt_path = output / "report.json", output / "receipt.json"

            def reject_receipt(_candidate: Mapping[str, Any]) -> None:
                self.assertTrue(report_path.is_file())
                raise vw.VWStop("VW-IDENTITY", "synthetic receipt validation failure")

            try:
                with self.assertRaisesRegex(vw.VWStop, "VW-IDENTITY"):
                    vw.persist_complete_output_payloads(
                        repo_root=repository,
                        expected_repo_head=old_oid,
                        report={"status": "prepared"},
                        report_path=report_path,
                        receipt_path=receipt_path,
                        receipt_builder=lambda _raw, sha: {"report_sha256": sha},
                        receipt_validator=reject_receipt,
                    )
                self.assertEqual("REPORT-CREATED", vw.LAST_COMPLETED_GATE)
            finally:
                vw.LAST_COMPLETED_GATE = original_gate
            self.assertTrue(report_path.is_file())
            self.assertFalse(receipt_path.exists())


def _table_primitive(index: int, p0: tuple[int, int], p1: tuple[int, int]) -> dict[str, Any]:
    return {
        "primitive_id": "sha256:" + f"{index:064x}",
        "geometry": {"kind": "line", "p0": [vw.point_string(p0[0]), vw.point_string(p0[1])], "p1": [vw.point_string(p1[0]), vw.point_string(p1[1])]},
        "bbox_px_half_open": [min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]) + 1, max(p0[1], p1[1]) + 1],
    }


def _text_primitive(index: int, bbox: list[int]) -> dict[str, Any]:
    return {"primitive_id": "sha256:" + f"{index:064x}", "bbox_px_half_open": bbox}


class TableRuleSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.grid = []
        index = 1
        for y in (10, 50, 90):
            self.grid.append(_table_primitive(index, (10, y), (90, y)))
            index += 1
        for x in (10, 50, 90):
            self.grid.append(_table_primitive(index, (x, 10), (x, 90)))
            index += 1
        self.text = [
            _text_primitive(101, [50, 50, 60, 60]),
            _text_primitive(102, [160, 50, 170, 60]),
            _text_primitive(103, [50, 160, 60, 170]),
            _text_primitive(104, [160, 160, 170, 170]),
        ]
        self.parent = "sha256:" + "f" * 64
        self.identity = (1, 0, 0, 1, 0, 0)

    def test_four_cell_text_grid_is_inferred_not_truth(self) -> None:
        evidence = vw.table_candidate_evidence(self.grid, self.text, self.identity, self.parent)
        self.assertIsNotNone(evidence)
        assert evidence is not None
        self.assertEqual("Inferred", evidence["claim_status"])
        self.assertEqual("UNREAD", evidence["semantic_truth_status"])
        self.assertEqual(4, evidence["measurements"]["occupied_text_cells"])

    def test_rectangle_crosshair_empty_grid_and_raster_do_not_pass(self) -> None:
        rectangle = [
            _table_primitive(1, (10, 10), (90, 10)),
            _table_primitive(2, (90, 10), (90, 90)),
            _table_primitive(3, (90, 90), (10, 90)),
            _table_primitive(4, (10, 90), (10, 10)),
        ]
        crosshair = [_table_primitive(1, (10, 50), (90, 50)), _table_primitive(2, (50, 10), (50, 90))]
        self.assertIsNone(vw.table_candidate_evidence(rectangle, self.text, self.identity, self.parent))
        self.assertIsNone(vw.table_candidate_evidence(crosshair, self.text, self.identity, self.parent))
        self.assertIsNone(vw.table_candidate_evidence(self.grid, [], self.identity, self.parent))
        self.assertIsNone(vw.table_candidate_evidence([], self.text, self.identity, self.parent))

    def test_below_intersection_and_axis_displacement_do_not_pass(self) -> None:
        missing = self.grid[:-2]
        self.assertIsNone(vw.table_candidate_evidence(missing, self.text, self.identity, self.parent))
        displaced = copy.deepcopy(self.grid)
        displaced[0] = _table_primitive(1, (10, 10), (45, 10))
        displaced.append(_table_primitive(8, (45, 12), (90, 12)))
        self.assertIsNone(vw.table_candidate_evidence(displaced, self.text, self.identity, self.parent))

    def test_disconnected_flowchart_boxes_do_not_form_global_table(self) -> None:
        primitives: list[dict[str, Any]] = []
        index = 200
        for left, top in ((10, 10), (150, 10), (10, 150), (150, 150)):
            right, bottom = left + 30, top + 20
            for p0, p1 in (
                ((left, top), (right, top)), ((right, top), (right, bottom)),
                ((right, bottom), (left, bottom)), ((left, bottom), (left, top)),
            ):
                primitives.append(_table_primitive(index, p0, p1))
                index += 1
        labels = [
            _text_primitive(400 + i, [x, y, x + 5, y + 5])
            for i, (x, y) in enumerate(((70, 70), (200, 70), (70, 200), (200, 200)))
        ]
        self.assertIsNone(vw.table_candidate_evidence(primitives, labels, self.identity, self.parent))


def _measured_source(raw: bytes) -> dict[str, Any]:
    value = vw.sha256_bytes(raw)
    return {
        "status": "measured",
        "manifest_sha256": value,
        "recorded_actual_sha256": value,
        "observed_sha256": value,
        "all_hashes_match": True,
    }


class CoordinateRenderAndLocalitySelfTest(unittest.TestCase):
    def test_rotations_nonzero_cropbox_and_roundtrip(self) -> None:
        for rotation in (0, 90, 180, 270):
            document = pymupdf.open()
            page = document.new_page(width=160, height=120)
            page.set_cropbox(pymupdf.Rect(10, 20, 150, 110))
            page.set_rotation(rotation)
            page.draw_line((30, 40), (80, 70), width=1)
            raw = document.tobytes()
            capture = vw.capture_page(
                page,
                page_1based=1,
                source_observation=_measured_source(raw),
                configuration_sha256=vw.EXPECTED_CONFIG_SHA256,
            )
            self.assertEqual("measured", capture.report["status"])
            self.assertEqual(rotation, capture.report["rotation_degrees"])
            self.assertTrue(capture.report["primitive_facts"])
            capture.clear()

    def test_rgb_truncation_and_out_of_bounds_bite(self) -> None:
        with self.assertRaisesRegex(vw.VWStop, "VW-CROP-BOUNDS"):
            vw.rgb_slice(b"\x00" * 11, 2, [0, 0, 1, 1])
        with self.assertRaisesRegex(vw.VWStop, "VW-CROP-BOUNDS"):
            vw.rgb_slice(b"\x00" * 12, 2, [0, 0, 2, 3])

    def test_vector_unknown_is_local_to_dependent_procedures(self) -> None:
        document = pymupdf.open()
        page = document.new_page(width=72, height=72)
        raw = document.tobytes()
        failure = vw.VWStop("VW-VECTOR-GEOMETRY-UNREAD", "synthetic")
        with mock.patch.object(vw, "extract_vector_primitives", side_effect=failure):
            capture = vw.capture_page(
                page,
                page_1based=1,
                source_observation=_measured_source(raw),
                configuration_sha256=vw.EXPECTED_CONFIG_SHA256,
            )
        statuses = {item["class"]: item["status"] for item in capture.report["class_procedures"]}
        self.assertEqual("UNREAD", statuses["vector"])
        self.assertEqual("UNREAD", statuses["stroke-cluster"])
        self.assertEqual("UNREAD", statuses["table"])
        self.assertEqual("measured", statuses["raster"])
        self.assertEqual("measured", statuses["scan-component"])
        self.assertEqual("measured", statuses["text-block"])
        self.assertTrue(capture.report["unreads"])

    def test_exact_api_shape_rejects_string_and_bool(self) -> None:
        with self.assertRaisesRegex(vw.VWStop, "VW-COORDINATE-UNREAD"):
            vw._api_xy(("1", 2))
        with self.assertRaisesRegex(vw.VWStop, "VW-COORDINATE-UNREAD"):
            vw._api_box((0, False, 1, 2))


class BoundaryIdentityAndOutputSelfTest(unittest.TestCase):
    def test_output_root_asymmetric_collisions_roll_back_only_new_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            evidence, scratch = base / "evidence", base / "scratch"
            evidence.mkdir()
            scratch.mkdir()
            free = types.SimpleNamespace(free=vw.MIN_SCRATCH_FREE + 1)

            (scratch / "scratch-collision").mkdir()
            with mock.patch.object(vw.shutil, "disk_usage", return_value=free):
                with self.assertRaisesRegex(vw.VWStop, "VW-PRIVACY"):
                    vw.prepare_output_roots(
                        evidence_root=evidence, scratch_root=scratch,
                        run_id="scratch-collision", protected_paths=[],
                    )
            self.assertFalse((evidence / "scratch-collision").exists())
            self.assertTrue((scratch / "scratch-collision").is_dir())

            (evidence / "evidence-collision").mkdir()
            with mock.patch.object(vw.shutil, "disk_usage", return_value=free):
                with self.assertRaisesRegex(vw.VWStop, "VW-PRIVACY"):
                    vw.prepare_output_roots(
                        evidence_root=evidence, scratch_root=scratch,
                        run_id="evidence-collision", protected_paths=[],
                    )
            self.assertTrue((evidence / "evidence-collision").is_dir())
            self.assertFalse((scratch / "evidence-collision").exists())

    def test_output_root_second_create_error_rolls_back_new_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            evidence, scratch = base / "evidence", base / "scratch"
            evidence.mkdir()
            scratch.mkdir()
            original_mkdir = Path.mkdir

            def selective_mkdir(path: Path, *args: Any, **kwargs: Any) -> None:
                if path == scratch / "io-error":
                    raise PermissionError("synthetic")
                original_mkdir(path, *args, **kwargs)

            free = types.SimpleNamespace(free=vw.MIN_SCRATCH_FREE + 1)
            with mock.patch.object(vw.shutil, "disk_usage", return_value=free), mock.patch.object(Path, "mkdir", selective_mkdir):
                with self.assertRaisesRegex(vw.VWStop, "VW-PRIVACY"):
                    vw.prepare_output_roots(
                        evidence_root=evidence, scratch_root=scratch,
                        run_id="io-error", protected_paths=[],
                    )
            self.assertFalse((evidence / "io-error").exists())
            self.assertFalse((scratch / "io-error").exists())

    def test_output_root_rollback_failure_retains_typed_context_and_one_attempt_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            evidence, scratch = base / "evidence", base / "scratch"
            evidence.mkdir(); scratch.mkdir()
            run_id = "rollback-residue"
            scratch_collision = scratch / run_id
            scratch_collision.mkdir()
            sentinel = scratch_collision / "pre-existing.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            evidence_run = evidence / run_id
            original_rmdir = Path.rmdir

            def selective_rmdir(path: Path) -> None:
                if path == evidence_run:
                    raise PermissionError("synthetic rollback failure")
                original_rmdir(path)

            free = types.SimpleNamespace(free=vw.MIN_SCRATCH_FREE + 1)
            with mock.patch.object(vw.shutil, "disk_usage", return_value=free), mock.patch.object(Path, "rmdir", selective_rmdir):
                with self.assertRaises(vw.PartialRootFailure) as caught:
                    vw.prepare_output_roots(
                        evidence_root=evidence, scratch_root=scratch,
                        run_id=run_id, protected_paths=[],
                    )
            self.assertEqual("VW-CLEANUP", caught.exception.reason)
            self.assertEqual(evidence_run, caught.exception.context.evidence_run_created)
            self.assertIsNone(caught.exception.context.scratch_run_created)
            self.assertEqual("preserve", sentinel.read_text(encoding="utf-8"))
            def fail_with_partial_context(**_kwargs: Any) -> Mapping[str, Any]:
                vw.ACTIVE_RUN_ID = run_id
                raise caught.exception

            stdout_bytes = io.BytesIO()
            stdout_text = io.TextIOWrapper(stdout_bytes, encoding="utf-8", write_through=True)
            stderr_text = io.StringIO()
            original_stdout, original_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout_text, stderr_text
                exit_code = vw.main(
                    [
                        "--private-manifest", str(base / "unused.json"),
                        "--evidence-root", str(evidence),
                        "--scratch-root", str(scratch),
                        "--run-id", run_id,
                    ],
                    event_runner=fail_with_partial_context,
                )
                stdout_text.flush()
                emitted = stdout_bytes.getvalue()
            finally:
                sys.stdout, sys.stderr = original_stdout, original_stderr
            self.assertEqual(2, exit_code)
            self.assertEqual("VW-CLEANUP\n", stderr_text.getvalue())
            self.assertEqual("VW-CLEANUP", vw.strict_json_bytes(emitted[:-1])["reason_code"])
            retained = list(evidence_run.iterdir())
            self.assertEqual([f"vw-e2-r2-{run_id}-attempt-exit.json"], [item.name for item in retained])
            failure = vw.minimal_attempt_exit(status="FAILED", last_completed_gate="START", reason_code="VW-CLEANUP")
            self.assertFalse(vw.persist_partial_root_attempt_exit(caught.exception.context, run_id, failure))

    def test_four_tile_corner_recovery_hashes_whole_page_crop(self) -> None:
        width = height = 1100
        raw = bytes((index % 251 for index in range(width * height * 3)))
        tiles = vw.populate_tile_hashes(raw, width, height, 1)
        recovery = vw.edge_recovery(vw.Box(75, 75, 78, 78), tiles, width, height, raw)
        self.assertEqual("whole-page-recrop", recovery["boundary_resolution"])
        self.assertGreaterEqual(len(recovery["recovery_tile_ids"]), 4)
        expected = vw.rgb_slice(raw, width, recovery["recovery_bbox_px_half_open"])
        self.assertEqual(len(expected), recovery["recovery_rgb_bytes"])
        self.assertEqual(vw.sha256_bytes(expected), recovery["recovery_rgb_sha256"])

    def test_reversed_geometry_id_invariant_but_provenance_binds_payload(self) -> None:
        sha = "1" * 64
        projection = {
            "source_sha256": sha,
            "page_1based": 1,
            "kind": "vector",
            "method": vw.DRAWING_METHOD,
            "bbox_pdf_pt": ["0.000000", "0.000000", "1.000000", "1.000000"],
            "bbox_px_half_open": [0, 0, 3, 3],
            "identity_attributes": {
                "effective_stroke_width_pdf_pt": "1.000000", "fill_only": False,
                "geometry": {"endpoints": [["0.000000", "0.000000"], ["1.000000", "1.000000"]]},
                "item_type": "l", "observed_stroke_width_pdf_pt": "1.000000",
            },
        }
        identifier = vw.primitive_id(projection)
        base = {
            "primitive_id": identifier, "kind": "vector", "method": vw.DRAWING_METHOD,
            "geometry": {"kind": "line", "p0": ["0.000000", "0.000000"], "p1": ["1.000000", "1.000000"]},
            "bbox_mupdf_unrotated_pt": projection["bbox_pdf_pt"], "bbox_pdf_pt": projection["bbox_pdf_pt"],
            "bbox_px_half_open": projection["bbox_px_half_open"], "source_claim_status": "Observed",
            "derived_geometry_claim_status": "Verified-self", "identity_attributes": projection["identity_attributes"],
            "source_evidence": {
                "provenance_records": [vw._provenance(engine_list_index=0, drawing_index=0, item_index=0)],
                "digest_algorithm": None, "observed_stroke_width_pdf_pt": "1.000000",
                "stroke_width_disposition": "observed-positive", "text_extraction_method": None,
                "engine_version": None, "claim_status": "Observed",
            },
        }
        reverse = copy.deepcopy(base)
        reverse["geometry"]["p0"], reverse["geometry"]["p1"] = reverse["geometry"]["p1"], reverse["geometry"]["p0"]
        reverse["source_evidence"]["provenance_records"] = [vw._provenance(engine_list_index=1, drawing_index=1, item_index=0)]
        original = copy.deepcopy(base)
        merged = vw._deduplicate_primitives([base, reverse])
        self.assertEqual(1, len(merged))
        self.assertEqual(identifier, merged[0]["primitive_id"])
        first = {"primitive": original, "capture_payload_sha256": "0" * 64}
        second = {"primitive": merged[0], "capture_payload_sha256": "0" * 64}
        self.assertNotEqual(vw.capture_payload_sha256(first), vw.capture_payload_sha256(second))

    def test_create_new_and_minimal_exit_are_biting(self) -> None:
        expected_keys = {
            "format_id", "event_id", "event_revision", "packet_sha256", "created_at_utc", "status",
            "last_completed_gate", "reason_code", "claim_status", "schema_conformance", "next_event_authority",
        }
        exit_object = vw.minimal_attempt_exit(status="STOPPED", last_completed_gate="START", reason_code="GROUND-DRIFT")
        self.assertEqual(expected_keys, set(exit_object))
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "out.json"
            vw.create_new_json(target, exit_object)
            with self.assertRaisesRegex(vw.VWStop, "VW-CLEANUP"):
                vw.create_new_json(target, exit_object)

    def test_root_overlap_rejected_before_children(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            nested = root / "nested"
            nested.mkdir()
            with self.assertRaisesRegex(vw.VWStop, "VW-PRIVACY"):
                vw.prepare_output_roots(
                    evidence_root=root,
                    scratch_root=nested,
                    run_id="synthetic",
                    protected_paths=[],
                )
            self.assertFalse((root / "synthetic").exists())


def _load_verifier_module() -> Any:
    path = Path(__file__).with_name("visual_witness_verify.py")
    spec = importlib.util.spec_from_file_location("_vw_verify_selftest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeVerifierProcess:
    def __init__(self, *, returncode: int, stdout: bytes) -> None:
        self.pid = 99001
        self.returncode = returncode
        self._stdout = stdout
        self.observed_input: bytes | None = None

    def communicate(self, input: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]:
        del timeout
        self.observed_input = input
        return self._stdout, b""

    def poll(self) -> int:
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


def _transport_request_and_result(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "config_sha256": vw.EXPECTED_CONFIG_SHA256,
        "cases": [],
        "capture_payload_sha256": "0" * 64,
    }
    payload["capture_payload_sha256"] = vw.capture_payload_sha256(payload)
    checks: list[dict[str, Any]] = []
    checks_sha = vw.domain_hash("semantic_checks", checks, prefixed=False)
    verifier_code = vw.sha256_file(repo / "windows-converter/visual_witness_verify.py")
    request = {
        "capture_payload": payload,
        "ordinary_semantic_checks": checks,
        "semantic_checks_sha256": checks_sha,
        "verifier_code_sha256": verifier_code,
        "vw_t03_source_path": r"C:\synthetic.pdf",
    }
    result: dict[str, Any] = {
        "verifier": "codex-independent-verifier-v1",
        "status": "Verified-independent",
        "probe_id": "vw-e2-r2-independent-sample-v1",
        "verifier_code_sha256": verifier_code,
        "packet_sha256": vw.PACKET_SHA256,
        "capture_schema_sha256": vw.CAPTURE_SCHEMA_SHA256,
        "capture_payload_sha256": payload["capture_payload_sha256"],
        "semantic_checks_sha256": checks_sha,
        "evidence_sha256": None,
        "reason_codes": [],
    }
    projection = dict(result)
    projection.pop("evidence_sha256")
    result["evidence_sha256"] = vw.domain_hash("independent_verifier", projection, prefixed=False)
    return request, result


def _canonical_order_fixture() -> dict[str, Any]:
    classes = list(vw.CLASS_ORDER)
    census = [{"class": name, "reason_codes": []} for name in classes]
    procedures = [{"class": name, "reason_codes": []} for name in classes]
    tile_a = {"tile_id": "p000001-x000000-y000000", "bbox_px_half_open": [0, 0, 10, 10]}
    tile_b = {"tile_id": "p000001-x000010-y000000", "bbox_px_half_open": [10, 0, 20, 10]}
    source_ids = ["sha256:" + "1" * 64, "sha256:" + "2" * 64]
    tracks = [
        {"axis_px": 0, "extent_start_px": 0, "extent_end_px": 20, "member_primitive_ids": list(source_ids)},
        {"axis_px": 10, "extent_start_px": 0, "extent_end_px": 20, "member_primitive_ids": list(source_ids)},
    ]
    cells = [
        {"row_index_0based": 0, "column_index_0based": 0, "cell_id": "r000000-c000000", "text_primitive_ids": [source_ids[0]]},
        {"row_index_0based": 0, "column_index_0based": 1, "cell_id": "r000000-c000001", "text_primitive_ids": [source_ids[1]]},
    ]
    evidence = [
        {"rule_id": vw.RULE_IDS["vector"], "source_primitive_ids": list(source_ids)},
        {"rule_id": vw.RULE_IDS["stroke-cluster"], "source_primitive_ids": list(source_ids)},
        {
            "rule_id": vw.RULE_IDS["table"],
            "source_primitive_ids": list(source_ids),
            "measurements": {
                "eligible_segment_ids": list(source_ids),
                "horizontal_tracks": copy.deepcopy(tracks),
                "vertical_tracks": copy.deepcopy(tracks),
                "closed_cells": cells,
                "occupied_cell_ids": ["r000000-c000000", "r000000-c000001"],
            },
        },
    ]
    candidate = {
        "candidate_id": "sha256:" + "a" * 64,
        "classes": ["vector", "stroke-cluster", "table"],
        "class_basis": [vw.RULE_IDS["vector"], vw.RULE_IDS["stroke-cluster"], vw.RULE_IDS["table"]],
        "class_evidence": evidence,
        "source_primitive_ids": list(source_ids),
        "intersecting_tile_ids": [tile_a["tile_id"], tile_b["tile_id"]],
        "edge_recovery": {
            "touched_internal_edges": [
                {"axis": "x", "coordinate_px": 10, "relation": "straddles", "neighbor_direction": "both"},
                {"axis": "y", "coordinate_px": 10, "relation": "straddles", "neighbor_direction": "both"},
            ],
            "recovery_tile_ids": [tile_a["tile_id"], tile_b["tile_id"]],
            "reason_codes": [],
        },
        "captured_text": {"source_text_primitive_ids": list(source_ids), "reason_codes": []},
        "crop": {"reason_codes": []},
    }
    page = {
        "page_1based": 1,
        "tiles": [tile_a, tile_b],
        "primitive_facts": [],
        "region_candidates": [candidate],
        "relationships": [],
        "class_procedures": procedures,
        "render": {"reason_codes": []},
        "tile_union": {"reason_codes": []},
        "primitive_census": {"reason_codes": []},
        "unreads": [],
    }

    def case(case_id: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "bundle": {
                "markdown": [{"phase": "raw-marker", "variant_ordinal": 0, "reason_codes": []}],
                "asset_filename_page_ids_0based": [],
                "reason_codes": [],
            },
            "source": {"reason_codes": []},
            "pages": pages,
            "class_census": copy.deepcopy(census),
            "conflicts": [],
            "unreads": [],
        }

    payload = {
        "case_census": {"case_ids": list(vw.ALLOWED_CASE_IDS)},
        "cases": [case("VW-T01", [page]), case("VW-T02", []), case("VW-T03", [])],
        "metrics": {"declared_page_pixel_coverage": {"reason_codes": []}},
        "capture_payload_sha256": "0" * 64,
    }
    payload["capture_payload_sha256"] = vw.capture_payload_sha256(payload)
    return {
        "capture_payload": payload,
        "run_observations": {
            "producer": {"runtime_modules": [{"logical_name": "python312.dll", "bytes": 1, "sha256": "1" * 64}]},
            "resources": {
                "case_workers": [{"case_id": case_id, "reason_codes": []} for case_id in vw.ALLOWED_CASE_IDS],
                "reason_codes": [],
            },
            "residue": {"files": [], "processes": [], "ports": [], "gpu_owners": [], "inaccessible": []},
            "conflicts": [],
            "unreads": [],
        },
    }


class PrivacyProbeAndVerifierSelfTest(unittest.TestCase):
    def test_native_isolation_provider_empty_event_scope_is_measurable(self) -> None:
        measurement = vw.native_isolation_measurement(set())
        self.assertEqual((), measurement.event_pids)
        self.assertEqual((), measurement.live_event_pids)
        self.assertEqual((), measurement.owned_ports)

    def test_spawned_worker_audit_denies_and_reconciles_network_and_gpu_attempts(self) -> None:
        original = copy.deepcopy(vw.EVENT_ACTIVITY)
        original_children = set(vw.EVENT_CHILD_PIDS)
        original_exited = set(vw.EVENT_CHILD_EXITED_PIDS)
        try:
            vw.EVENT_ACTIVITY.reset()
            vw.install_event_activity_audit()
            network = vw.run_activity_probe_worker("network-loopback")
            gpu = vw.run_activity_probe_worker("gpu-library")
            self.assertGreaterEqual(network["network_call_count"], 1)
            self.assertGreaterEqual(gpu["gpu_call_count"], 1)
            self.assertEqual(2, vw.EVENT_ACTIVITY.reconciled_child_processes)
            with self.assertRaisesRegex(vw.VWStop, "VW-CLEANUP"):
                vw.require_event_activity_reconciled(2)
        finally:
            vw.EVENT_ACTIVITY.network_call_count = original.network_call_count
            vw.EVENT_ACTIVITY.gpu_call_count = original.gpu_call_count
            vw.EVENT_ACTIVITY.instrumentation_ready = original.instrumentation_ready
            vw.EVENT_ACTIVITY.reconciled_child_processes = original.reconciled_child_processes
            vw.EVENT_CHILD_PIDS.clear(); vw.EVENT_CHILD_PIDS.update(original_children)
            vw.EVENT_CHILD_EXITED_PIDS.clear(); vw.EVENT_CHILD_EXITED_PIDS.update(original_exited)

    def test_full_canonical_order_mutations_bite_producer_and_independent_verifier(self) -> None:
        verifier = _load_verifier_module()
        base = _canonical_order_fixture()
        self.assertTrue(vw._canonical_arrays(base))
        self.assertTrue(verifier._canonical_payload_order(base["capture_payload"]))

        def rehash(report: dict[str, Any]) -> None:
            report["capture_payload"]["capture_payload_sha256"] = vw.capture_payload_sha256(
                report["capture_payload"]
            )

        payload_mutations: list[Callable[[dict[str, Any]], None]] = [
            lambda report: report["capture_payload"]["cases"][0]["pages"][0]["region_candidates"][0]["edge_recovery"]["touched_internal_edges"].reverse(),
            lambda report: report["capture_payload"]["cases"][0]["pages"][0]["region_candidates"][0]["class_evidence"][2]["measurements"]["horizontal_tracks"].reverse(),
            lambda report: report["capture_payload"]["cases"][0]["source"].update(
                {"reason_codes": ["VW-CLEANUP", "UNREAD"]}
            ),
            lambda report: report["capture_payload"]["cases"].reverse(),
        ]
        for mutate in payload_mutations:
            poisoned = copy.deepcopy(base)
            mutate(poisoned)
            rehash(poisoned)
            self.assertFalse(vw._canonical_arrays(poisoned))
            self.assertFalse(verifier._canonical_payload_order(poisoned["capture_payload"]))

        residue_poison = copy.deepcopy(base)
        residue_poison["run_observations"]["residue"]["files"] = ["evidence-part-file", "event-scratch-child"]
        self.assertFalse(vw._canonical_arrays(residue_poison))

    def test_preverifier_subject_requires_actual_cleanup_and_protected_after(self) -> None:
        report = _canonical_order_fixture()
        observations = report["run_observations"]
        observations["producer"]["semantic_validator_code_sha256"] = "1" * 64
        observations["cleanup"] = {"verified": True}
        observations["protected_tree"] = {"identical": True}
        original_gate = vw.LAST_COMPLETED_GATE
        try:
            vw.LAST_COMPLETED_GATE = "PROTECTED-AFTER"
            with self.assertRaisesRegex(vw.VWStop, "VW-IDENTITY"):
                vw.build_preverifier_semantic_checks(report)
            vw.LAST_COMPLETED_GATE = "CLEANUP-VERIFIED"
            checks, _subject, digest = vw.build_preverifier_semantic_checks(report)
            self.assertEqual(len(vw.ORDINARY_CHECK_NAMES), len(checks))
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            observations["cleanup"]["verified"] = False
            with self.assertRaisesRegex(vw.VWStop, "VW-CLEANUP"):
                vw.build_preverifier_semantic_checks(report)
        finally:
            vw.LAST_COMPLETED_GATE = original_gate

    def test_verifier_pipe_transport_authenticates_bytes_activity_exit_and_result(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        request, valid_result = _transport_request_and_result(repo)
        original = copy.deepcopy(vw.EVENT_ACTIVITY)
        clean_activity = {"instrumentation_ready": True, "network_call_count": 0, "gpu_call_count": 0}

        def encoded(result: Any, activity: Mapping[str, Any] = clean_activity) -> bytes:
            return vw.canonical_json_bytes({"activity": dict(activity), "result": result}) + b"\n"

        def invocation(process: _FakeVerifierProcess) -> vw.VerifierInvocation:
            return vw.VerifierInvocation(process, 0)

        try:
            vw.EVENT_ACTIVITY.reset()
            nonzero = invocation(_FakeVerifierProcess(returncode=3, stdout=encoded(valid_result)))
            with self.assertRaisesRegex(vw.VWStop, "UNREAD"):
                vw._finish_verifier(nonzero, request, repo_root=repo)

            malformed = invocation(_FakeVerifierProcess(returncode=0, stdout=encoded(valid_result) + b"stale"))
            with self.assertRaisesRegex(vw.VWStop, "UNREAD"):
                vw._finish_verifier(malformed, request, repo_root=repo)

            wrong_evidence = copy.deepcopy(valid_result)
            wrong_evidence["evidence_sha256"] = "0" * 64
            evidence_invocation = invocation(_FakeVerifierProcess(returncode=0, stdout=encoded(wrong_evidence)))
            with self.assertRaisesRegex(vw.VWStop, "VW-NEGATIVE-CONTROL"):
                vw._finish_verifier(evidence_invocation, request, repo_root=repo)

            wrong_code = copy.deepcopy(valid_result)
            wrong_code["verifier_code_sha256"] = "0" * 64
            code_invocation = invocation(_FakeVerifierProcess(returncode=0, stdout=encoded(wrong_code)))
            with self.assertRaisesRegex(vw.VWStop, "GROUND-DRIFT"):
                vw._finish_verifier(code_invocation, request, repo_root=repo)

            wrong_config_request = copy.deepcopy(request)
            wrong_config_request["capture_payload"]["config_sha256"] = "0" * 64
            wrong_config_request["capture_payload"]["capture_payload_sha256"] = vw.capture_payload_sha256(
                wrong_config_request["capture_payload"]
            )
            config_invocation = invocation(_FakeVerifierProcess(returncode=0, stdout=encoded(valid_result)))
            with self.assertRaisesRegex(vw.VWStop, "VW-CONFIG-HASH"):
                vw._finish_verifier(config_invocation, wrong_config_request, repo_root=repo)

            attempted = invocation(_FakeVerifierProcess(
                returncode=3,
                stdout=encoded(valid_result, {"instrumentation_ready": True, "network_call_count": 1, "gpu_call_count": 0}),
            ))
            with self.assertRaisesRegex(vw.VWStop, "VW-CLEANUP"):
                vw._finish_verifier(attempted, request, repo_root=repo)

            vw.EVENT_ACTIVITY.network_call_count = 0
            valid_invocation = invocation(_FakeVerifierProcess(returncode=0, stdout=encoded(valid_result)))
            observed = vw._finish_verifier(valid_invocation, request, repo_root=repo)
            self.assertEqual(valid_result, observed)
            self.assertEqual(
                vw.canonical_json_bytes(request) + b"\n",
                valid_invocation.process.observed_input,
            )
        finally:
            vw.EVENT_ACTIVITY.network_call_count = original.network_call_count
            vw.EVENT_ACTIVITY.gpu_call_count = original.gpu_call_count
            vw.EVENT_ACTIVITY.instrumentation_ready = original.instrumentation_ready
            vw.EVENT_ACTIVITY.reconciled_child_processes = original.reconciled_child_processes

    def test_production_verifier_requires_gap_area_eight_and_config_identity(self) -> None:
        verifier = _load_verifier_module()
        repo = Path(__file__).resolve().parents[1]
        def empty_page(page_1based: int) -> dict[str, Any]:
            return {
                "page_1based": page_1based,
                "tiles": [],
                "primitive_facts": [],
                "region_candidates": [],
                "relationships": [],
                "class_procedures": [{"class": name} for name in verifier.CLASS_ORDER],
            }

        class_census = [{"class": name} for name in verifier.CLASS_ORDER]
        pages = [empty_page(index) for index in range(1, 211)]
        bundle = {
            "markdown": [{"phase": "raw-marker", "variant_ordinal": 0}],
            "asset_filename_page_ids_0based": [],
        }
        payload: dict[str, Any] = {
            "config_sha256": verifier.CONFIG_SHA256,
            "case_census": {"case_ids": list(verifier.CASE_ORDER)},
            "cases": [
                {"case_id": "VW-T01", "source": {}, "bundle": copy.deepcopy(bundle), "pages": [], "class_census": copy.deepcopy(class_census)},
                {"case_id": "VW-T02", "source": {}, "bundle": copy.deepcopy(bundle), "pages": [], "class_census": copy.deepcopy(class_census)},
                {"case_id": "VW-T03", "source": {}, "bundle": copy.deepcopy(bundle), "pages": pages, "class_census": copy.deepcopy(class_census)},
            ],
            "capture_payload_sha256": "0" * 64,
        }
        projection = dict(payload)
        projection.pop("capture_payload_sha256")
        payload["capture_payload_sha256"] = verifier._projection_hash("capture", projection)
        request = {
            "capture_payload": payload,
            "ordinary_semantic_checks": [],
            "semantic_checks_sha256": verifier._projection_hash("checks", []),
            "verifier_code_sha256": verifier.digest(Path(verifier.__file__).read_bytes()),
            "vw_t03_source_path": r"C:\synthetic.pdf",
        }
        unread_messages: list[str] = []
        original_unread = verifier.VerifyUnread

        class CapturedUnread(original_unread):
            def __init__(self, message: str) -> None:
                unread_messages.append(message)
                super().__init__(message)

        with mock.patch.object(verifier, "_file_identity", return_value=True), \
             mock.patch.object(verifier, "_verify_page_210", return_value=True), \
             mock.patch.object(verifier, "_identity_chain", return_value=True), \
             mock.patch.object(verifier, "VerifyUnread", CapturedUnread):
            valid = verifier.verify_request(copy.deepcopy(request), repo)
            self.assertEqual("Verified-independent", valid["status"], unread_messages)
            with mock.patch.object(verifier, "PLANTED_GAP_RECTANGLES", [[0, 0, 3, 1], [0, 2, 3, 3], [2, 1, 3, 2]]):
                area_seven = verifier.verify_request(copy.deepcopy(request), repo)
            self.assertEqual("CONFLICT", area_seven["status"])
            self.assertIn("VW-NEGATIVE-CONTROL", area_seven["reason_codes"])
            with mock.patch.object(verifier, "PLANTED_GAP_RECTANGLES", [[0, 0, 3, 3]]):
                area_nine = verifier.verify_request(copy.deepcopy(request), repo)
            self.assertEqual("CONFLICT", area_nine["status"])
            self.assertIn("VW-NEGATIVE-CONTROL", area_nine["reason_codes"])
            wrong_config = copy.deepcopy(request)
            wrong_config["capture_payload"]["config_sha256"] = "0" * 64
            wrong_projection = dict(wrong_config["capture_payload"])
            wrong_projection.pop("capture_payload_sha256")
            wrong_config["capture_payload"]["capture_payload_sha256"] = verifier._projection_hash("capture", wrong_projection)
            config_result = verifier.verify_request(wrong_config, repo)
            self.assertEqual("CONFLICT", config_result["status"])
            self.assertIn("VW-CONFIG-HASH", config_result["reason_codes"])
            reordered = copy.deepcopy(request)
            reordered["capture_payload"]["cases"] = list(reversed(reordered["capture_payload"]["cases"]))
            reordered_projection = dict(reordered["capture_payload"])
            reordered_projection.pop("capture_payload_sha256")
            reordered["capture_payload"]["capture_payload_sha256"] = verifier._projection_hash(
                "capture", reordered_projection
            )
            reordered_result = verifier.verify_request(reordered, repo)
            self.assertEqual("CONFLICT", reordered_result["status"])
            self.assertIn("VW-NEGATIVE-CONTROL", reordered_result["reason_codes"])

    def test_isolation_provider_transition_and_final_measurement_match(self) -> None:
        original_children = set(vw.EVENT_CHILD_PIDS)
        original_exited = set(vw.EVENT_CHILD_EXITED_PIDS)
        original_descendants = set(vw.EVENT_OBSERVED_DESCENDANT_PIDS)
        original_network = vw.EVENT_ACTIVITY.network_call_count
        original_gpu = vw.EVENT_ACTIVITY.gpu_call_count
        try:
            vw.EVENT_CHILD_PIDS.clear()
            vw.EVENT_CHILD_EXITED_PIDS.clear()
            vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear()
            vw.EVENT_ACTIVITY.reset()
            vw.EVENT_CHILD_PIDS.add(101)
            before_provider = lambda _known: vw.IsolationMeasurement((101, 102), (101,), ())
            before_hash, before_result, _before = vw.isolation_probe(
                "1" * 64, provider=before_provider, transitional_pids=(101,)
            )
            self.assertEqual(0, before_result["event_child_process_count"])
            after_provider = lambda _known: vw.IsolationMeasurement((101, 102), (), ())
            after_hash, after_result, _after = vw.isolation_probe("1" * 64, provider=after_provider)
            self.assertEqual(before_hash, after_hash)
            self.assertEqual(0, after_result["event_child_process_count"])
        finally:
            vw.EVENT_CHILD_PIDS.clear(); vw.EVENT_CHILD_PIDS.update(original_children)
            vw.EVENT_CHILD_EXITED_PIDS.clear(); vw.EVENT_CHILD_EXITED_PIDS.update(original_exited)
            vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear(); vw.EVENT_OBSERVED_DESCENDANT_PIDS.update(original_descendants)
            vw.EVENT_ACTIVITY.network_call_count = original_network
            vw.EVENT_ACTIVITY.gpu_call_count = original_gpu

    def test_isolation_provider_descendant_port_counter_and_unavailable_bite(self) -> None:
        original_children = set(vw.EVENT_CHILD_PIDS)
        original_descendants = set(vw.EVENT_OBSERVED_DESCENDANT_PIDS)
        original_network = vw.EVENT_ACTIVITY.network_call_count
        original_gpu = vw.EVENT_ACTIVITY.gpu_call_count
        try:
            vw.EVENT_CHILD_PIDS.clear(); vw.EVENT_CHILD_PIDS.add(201)
            vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear()
            vw.EVENT_ACTIVITY.reset()
            descendant = lambda _known: vw.IsolationMeasurement((201, 202), (201, 202), ())
            _digest, result, _measurement = vw.isolation_probe(
                "1" * 64, provider=descendant, transitional_pids=(201,)
            )
            self.assertEqual(1, result["event_child_process_count"])
            port_provider = lambda _known: vw.IsolationMeasurement((201,), (), (49152,))
            _digest, result, _measurement = vw.isolation_probe("1" * 64, provider=port_provider)
            self.assertEqual(1, result["event_child_port_count"])
            vw.EVENT_ACTIVITY.network_call_count = 1
            clean_provider = lambda _known: vw.IsolationMeasurement((201,), (), ())
            _digest, result, _measurement = vw.isolation_probe("1" * 64, provider=clean_provider)
            self.assertTrue(result["network_used"])

            def unavailable(_known: set[int]) -> vw.IsolationMeasurement:
                raise OSError("synthetic")

            with self.assertRaisesRegex(vw.VWStop, "UNREAD"):
                vw.isolation_probe("1" * 64, provider=unavailable)
        finally:
            vw.EVENT_CHILD_PIDS.clear(); vw.EVENT_CHILD_PIDS.update(original_children)
            vw.EVENT_OBSERVED_DESCENDANT_PIDS.clear(); vw.EVENT_OBSERVED_DESCENDANT_PIDS.update(original_descendants)
            vw.EVENT_ACTIVITY.network_call_count = original_network
            vw.EVENT_ACTIVITY.gpu_call_count = original_gpu

    def test_redaction_is_schema_location_aware_and_rejects_opaque_source_token(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        packet = vw.strict_json_file(repo / vw.PACKET_RELATIVE_PATH)
        schema = load_bound_schema(repo)

        def subject(value: str) -> dict[str, Any]:
            return {
                "capture_payload": {
                    "cases": [
                        {"bundle": {"page_map": {"formula": value}}}
                    ]
                }
            }

        exact_formula = "source page_1based = page_id_0based + 1 (mechanical filename map only)"
        allowed = vw.retained_string_scan(subject(exact_formula), packet=packet, schema=schema, private_dictionary=[])
        self.assertEqual(0, allowed["unlicensed_string_hits"])
        confidential = vw.retained_string_scan(subject("Confidential"), packet=packet, schema=schema, private_dictionary=[])
        self.assertEqual(1, confidential["unlicensed_string_hits"])
        packet_quote = packet["authority"]["verbatim_decision"]
        wrong_location_packet_value = vw.retained_string_scan(
            subject(packet_quote), packet=packet, schema=schema, private_dictionary=[]
        )
        self.assertEqual(1, wrong_location_packet_value["unlicensed_string_hits"])
        wrong_location_hash = vw.retained_string_scan(subject("a" * 64), packet=packet, schema=schema, private_dictionary=[])
        self.assertEqual(1, wrong_location_hash["unlicensed_string_hits"])

    def test_redaction_scanner_catches_path_base64_and_unlicensed_text(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        packet = vw.strict_json_file(repo / vw.PACKET_RELATIVE_PATH)
        schema = load_bound_schema(repo)
        poisoned = {
            "path": "C:\\private\\source.pdf",
            "blob": "A" * 100,
            "raw": "unlicensed raw sentence from a source",
        }
        result = vw.retained_string_scan(
            poisoned,
            packet=packet,
            schema=schema,
            private_dictionary=["c:\\private\\source.pdf"],
        )
        self.assertGreater(result["path_pattern_hits"], 0)
        self.assertGreater(result["base64_pattern_hits"], 0)
        self.assertGreater(result["private_identifiers_exposed"], 0)
        self.assertGreater(result["unlicensed_string_hits"], 0)

    def test_probe_and_semantic_unread_hashes_bite(self) -> None:
        first = vw.generic_probe_evidence(
            probe_id="cleanup-v1", probe_code_sha256="1" * 64, subject_sha256="2" * 64,
            status="pass", reason_codes=[], result_projection={"event_scratch_removed": True, "part_files_remaining": 0},
        )
        second = vw.generic_probe_evidence(
            probe_id="cleanup-v1", probe_code_sha256="1" * 64, subject_sha256="2" * 64,
            status="fail", reason_codes=["VW-CLEANUP"], result_projection={"event_scratch_removed": False, "part_files_remaining": 0},
        )
        self.assertNotEqual(first, second)
        unread = vw.semantic_check_object(
            "render-rgb-arithmetic", status="UNREAD", subject_sha256="3" * 64, validator_code_sha256="4" * 64
        )
        self.assertIsNone(unread["evidence_sha256"])
        self.assertEqual("UNREAD", unread["claim_status"])

    def test_independent_identity_chain_and_exact_gap_negative(self) -> None:
        verifier = _load_verifier_module()
        source_sha = "1" * 64
        primitive_projection = {
            "source_sha256": source_sha, "page_1based": 1, "kind": "text", "method": vw.TEXT_METHOD,
            "bbox_pdf_pt": ["0.000000", "0.000000", "1.000000", "1.000000"],
            "bbox_px_half_open": [0, 0, 3, 3],
            "identity_attributes": {"utf8_sha256": "2" * 64, "utf8_bytes": 1, "unicode_codepoints": 1},
        }
        primitive_id = vw.primitive_id(primitive_projection)
        candidate_projection = {
            "source_sha256": source_sha, "page_1based": 1,
            "bbox_pdf_pt": primitive_projection["bbox_pdf_pt"], "bbox_px_half_open": [0, 0, 3, 3],
            "classes": ["text-block"], "config_sha256": vw.EXPECTED_CONFIG_SHA256,
            "source_primitive_ids": [primitive_id],
        }
        source_candidate = vw.candidate_id(candidate_projection)
        target_candidate = "sha256:" + "f" * 64
        relationship_projection = {"source_candidate_id": source_candidate, "target_candidate_id": target_candidate, "kind": "intersects"}
        relationship = {**relationship_projection, "relationship_id": vw.relationship_id(relationship_projection)}
        primitive = {key: value for key, value in primitive_projection.items() if key not in ("source_sha256", "page_1based")}
        primitive["primitive_id"] = primitive_id
        candidate = {key: value for key, value in candidate_projection.items() if key not in ("source_sha256", "page_1based", "config_sha256")}
        candidate["candidate_id"] = source_candidate
        payload = {
            "config_sha256": vw.EXPECTED_CONFIG_SHA256,
            "cases": [{"case_id": "VW-T01", "source": {"observed_sha256": source_sha}, "pages": [{
                "page_1based": 1, "primitive_facts": [primitive],
                "region_candidates": [candidate, {"candidate_id": target_candidate, "source_primitive_ids": []}],
                "relationships": [relationship],
            }]}],
        }
        self.assertTrue(verifier._identity_chain(payload))
        payload["cases"][0]["pages"][0]["primitive_facts"][0]["identity_attributes"]["utf8_bytes"] = 2
        self.assertFalse(verifier._identity_chain(payload))
        planted = [[0, 0, 3, 1], [0, 2, 3, 3], [0, 1, 1, 2], [2, 1, 3, 2]]
        self.assertEqual(8, verifier.exact_union_area(planted))

    def test_synthetic_capture_payload_repeatability(self) -> None:
        document = pymupdf.open()
        page = document.new_page(width=144, height=144)
        page.draw_rect(pymupdf.Rect(20, 20, 124, 124), width=1)
        page.draw_line((20, 72), (124, 72), width=1)
        page.draw_line((72, 20), (72, 124), width=1)
        page.insert_text((30, 40), "synthetic", fontsize=9)
        source_bytes = document.tobytes(garbage=4, deflate=True)
        source = _measured_source(source_bytes)

        def capture_once() -> dict[str, Any]:
            with pymupdf.open(stream=source_bytes, filetype="pdf") as reopened:
                capture = vw.capture_page(
                    reopened[0], page_1based=1, source_observation=source,
                    configuration_sha256=vw.EXPECTED_CONFIG_SHA256,
                )
                report = copy.deepcopy(capture.report)
                capture.clear()
                return report

        first_page = capture_once()
        second_page = capture_once()
        self.assertEqual(vw.canonical_json_bytes(first_page), vw.canonical_json_bytes(second_page))
        self.assertTrue(first_page["primitive_facts"])
        self.assertTrue(first_page["region_candidates"])
        self.assertTrue(first_page["tiles"])
        self.assertEqual("measured", first_page["render"]["status"])

        def case(case_id: str, page_report: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "case_id": case_id, "procedure_status": "measured", "pages": [copy.deepcopy(page_report)],
                "class_census": vw.case_class_census([page_report]), "source": dict(source), "bundle": {},
                "blocking": False, "split": "calibration", "conflicts": [], "unreads": [],
            }

        first_cases = [case(case_id, first_page) for case_id in vw.ALLOWED_CASE_IDS]
        second_cases = [case(case_id, second_page) for case_id in vw.ALLOWED_CASE_IDS]
        first = vw.build_capture_payload(first_cases, vw.EXPECTED_CONFIG_SHA256)
        second = vw.build_capture_payload(second_cases, vw.EXPECTED_CONFIG_SHA256)
        self.assertEqual(vw.canonical_json_bytes(first), vw.canonical_json_bytes(second))
        self.assertEqual(first["capture_payload_sha256"], second["capture_payload_sha256"])

    def test_corrupt_pdf_maps_to_minimal_nonreceipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "corrupt.pdf"
            source_path.write_bytes(b"not a pdf")
            source_sha = vw.sha256_file(source_path)
            case_data = {
                "id": "VW-T01",
                "source_sha256_manifest": source_sha,
                "source_sha256_actual": source_sha,
                "source_bytes": source_path.stat().st_size,
                "pages": 1,
                "markdown_sha256": "1" * 64,
                "markdown_bytes": 0,
                "analyst_markdown": [],
                "asset_inventory_sha256": "2" * 64,
                "asset_count": 0,
            }
            case = vw.ResolvedCaseFiles(
                case=case_data,
                source=source_path,
                bundle_dir=root,
                bundle_manifest=root / "manifest.json",
                bundle_body=root / "body.md",
                raw_markdown=root / "raw.md",
                analyst_markdown=(),
                assets=(),
            )
            protected_before = [
                {"logical_id": "VW-T01/bundle-manifest", "bytes": 0, "sha256": "3" * 64}
            ]
            def corrupt_event_runner(**_kwargs: Any) -> Mapping[str, Any]:
                case_report, _resource, _assets = vw.run_case_worker(
                    case, protected_before, vw.EXPECTED_CONFIG_SHA256, root
                )
                vw.require_completed_cases([case_report])
                raise AssertionError("corrupt case completion gate returned")

            stdout_bytes = io.BytesIO()
            stdout_text = io.TextIOWrapper(stdout_bytes, encoding="utf-8", write_through=True)
            stderr_text = io.StringIO()
            original_stdout, original_stderr = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = stdout_text, stderr_text
                exit_code = vw.main(
                    [
                        "--private-manifest", str(root / "unused.json"),
                        "--evidence-root", str(root),
                        "--scratch-root", str(root / "unused-scratch"),
                        "--run-id", "corrupt-worker-exit",
                    ],
                    event_runner=corrupt_event_runner,
                )
                stdout_text.flush()
                emitted = stdout_bytes.getvalue()
            finally:
                sys.stdout, sys.stderr = original_stdout, original_stderr
            self.assertEqual(2, exit_code)
            self.assertEqual("VW-RENDER-UNREAD\n", stderr_text.getvalue())
            self.assertEqual(1, emitted.count(b"\n"))
            exit_object = vw.strict_json_bytes(emitted[:-1])
            self.assertEqual("UNREAD", exit_object["status"])
            self.assertEqual("VW-RENDER-UNREAD", exit_object["reason_code"])
            self.assertNotIn("schema", exit_object)
            self.assertNotIn("outputs", exit_object)
            self.assertNotEqual("COMPLETE", exit_object.get("status"))


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic-only VW-E2-R2 self-test")
    parser.add_argument("--schema-check-report", type=Path)
    args = parser.parse_args(argv)
    if args.schema_check_report is not None:
        schema = load_bound_schema(Path(__file__).resolve().parents[1])
        report = vw.strict_json_file(args.schema_check_report, reason="VW-IDENTITY")
        assert_bound_schema(report, schema)
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
