"""Offline tripwires for coverage_rescore.py. No live pipeline paths are read or written."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import pymupdf

import coverage_rescore as cr


def png_bytes(red: int, green: int, blue: int, size: int = 80) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
            ">I", zlib.crc32(kind + payload) & 0xFFFFFFFF
        )

    rows = b"".join(b"\x00" + bytes((red, green, blue)) * size for _ in range(size))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


class CoverageRescoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="fp-rescore-test-"))
        self.source_root = self.temp / "done"
        self.bundle = self.temp / "anchor" / "specimen"
        self.source_root.mkdir(parents=True)
        (self.bundle / "assets").mkdir(parents=True)

        self.pdf = self.source_root / "specimen.pdf"
        document = pymupdf.open()
        page1 = document.new_page()
        page1.insert_image(pymupdf.Rect(80, 80, 220, 220), stream=png_bytes(200, 20, 20))
        page2 = document.new_page()
        page2.insert_image(pymupdf.Rect(80, 80, 220, 220), stream=png_bytes(20, 200, 20))
        page3 = document.new_page()
        page3.insert_image(pymupdf.Rect(60, 80, 180, 200), stream=png_bytes(20, 20, 200))
        page3.insert_image(pymupdf.Rect(240, 80, 360, 200), stream=png_bytes(180, 80, 20))
        document.save(self.pdf)
        document.close()

        asset1 = "specimen_page_0_Figure_0.png"
        asset3 = "specimen_page_2_Figure_0.png"
        (self.bundle / "assets" / asset1).write_bytes(png_bytes(200, 20, 20))
        (self.bundle / "assets" / asset3).write_bytes(png_bytes(20, 20, 200))
        (self.bundle / "specimen.md").write_text(
            f"![[assets/{asset1}]]\n![[assets/{asset3}]]\n", encoding="utf-8"
        )
        (self.bundle / "manifest.json").write_text(
            json.dumps(
                {
                    "source": self.pdf.name,
                    "source_sha256": cr.sha256_file(self.pdf),
                    "lane": "clean",
                    "pages": 3,
                    "converted_at": "2026-08-23T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_resolves_source_by_manifest_and_preserves_inputs(self) -> None:
        before = tree_digest(self.temp)
        report = cr.run_rescore(self.bundle, source_root=self.source_root, use_hashes=False)
        after = tree_digest(self.temp)
        self.assertEqual(before, after)
        self.assertTrue(report["source_identity"]["match"])
        self.assertEqual(report["manifest"]["pages"], 3)

    def test_final_conversion_inventory_names_zero_and_partial_candidates(self) -> None:
        report = cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)
        inventory = report["final_conversion_inventory"]
        self.assertEqual(inventory["source_unique_embedded_raster_objects"], 4)
        self.assertEqual(inventory["bundle_asset_files"], 2)
        self.assertEqual(inventory["candidate_pages_with_source_rasters_and_zero_assets"], [2])
        self.assertEqual(inventory["candidate_pages_with_fewer_assets_than_source_rasters"], [3])
        self.assertEqual(inventory["references_missing_asset_file"], [])
        self.assertEqual(inventory["asset_files_without_markdown_reference"], [])

    def test_p1_and_raw_inventory_remain_separate(self) -> None:
        report = cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)
        p1 = report["p1_page_coverage"]
        inventory = report["final_conversion_inventory"]
        self.assertEqual(p1["pages_uncovered"], 1)
        self.assertEqual(inventory["candidate_zero_asset_page_count"], 1)
        self.assertEqual(inventory["candidate_partial_asset_page_count"], 1)
        self.assertIn("DIAGNOSTIC ONLY", inventory["conditions"]["interpretation"])

    def test_scan_lane_subpage_diagram_coverage_is_unread_not_a_raster_count(self) -> None:
        manifest_path = self.bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["lane"] = "scan"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report = cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)
        inventory = report["final_conversion_inventory"]
        self.assertEqual(inventory["candidate_status"], "UNREAD")
        self.assertIsNone(inventory["candidate_zero_asset_page_count"])
        self.assertIsNone(inventory["candidate_partial_asset_page_count"])
        self.assertIn("hand-drawn diagram", inventory["conditions"]["scan_lane_rule"])

    def test_source_sha_mismatch_refuses_measurement(self) -> None:
        manifest_path = self.bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(cr.RescoreUnread, "source identity mismatch"):
            cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)

    def test_markdown_reference_parity_bites(self) -> None:
        (self.bundle / "specimen.md").write_text(
            "![[assets/missing.png]]\n", encoding="utf-8"
        )
        report = cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)
        inventory = report["final_conversion_inventory"]
        self.assertEqual(inventory["references_missing_asset_file"], ["missing.png"])
        self.assertEqual(len(inventory["asset_files_without_markdown_reference"]), 2)

    def test_ambiguous_bundle_markdown_refuses(self) -> None:
        (self.bundle / "second.md").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(cr.RescoreUnread, "exactly one root markdown"):
            cr.run_rescore(self.bundle, pdf_path=self.pdf, use_hashes=False)

    def test_unicode_output_bypasses_legacy_windows_console_encoding(self) -> None:
        raw = io.BytesIO()
        legacy = io.TextIOWrapper(raw, encoding="cp1252")
        cr.write_utf8(legacy, "AI Agent：UNREAD — safe")
        legacy.flush()
        self.assertEqual(raw.getvalue().decode("utf-8"), "AI Agent：UNREAD — safe\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
