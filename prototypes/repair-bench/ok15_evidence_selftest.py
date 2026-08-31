"""Hermetic OK-15 tripwires: synthetic PDFs only, no GPU or pipeline directories.

Run with the Marker environment (PyMuPDF is required):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe -B ok15_evidence_selftest.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import ok15_evidence as ev  # noqa: E402


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as doc:
        return ["\n".join(str(block[4]) for block in page.get_text("blocks", sort=False))
                for page in doc]


def fixture(path: Path, *, labels: bool = True, duplicate_labels: bool = False) -> None:
    doc = pymupdf.open()
    first = doc.new_page(width=200, height=200)
    first.insert_text((20, 35), "primary body survives")
    layer = doc.add_ocg("Optional primary or watermark unknown", on=True)
    first.insert_text((20, 75), "layer counterfactual", oc=layer)

    # A real image XObject, then the same image is named as page one's optional /Thumb.
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 4, 4), False)
    pix.clear_with(0x55)
    image_xref = first.insert_image(pymupdf.Rect(160, 160, 180, 180), stream=pix.tobytes("png"))

    second = doc.new_page(width=200, height=200)
    second.insert_text((15, 35), "left one two")
    second.insert_text((110, 35), "right three four")
    doc.new_page(width=200, height=200)
    if duplicate_labels:
        doc.set_page_labels([
            {"startpage": 0, "prefix": "A-", "style": "D", "firstpagenum": 1},
            {"startpage": 2, "prefix": "A-", "style": "D", "firstpagenum": 1},
        ])
    elif labels:
        doc.set_page_labels([
            {"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1},
            {"startpage": 2, "prefix": "", "style": "D", "firstpagenum": 1},
        ])
    doc.xref_set_key(doc.page_xref(0), "Thumb", f"{image_xref} 0 R")
    doc.save(path)
    doc.close()


class OK15EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="fp-ok15-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_all_five_probes_and_source_immutability(self) -> None:
        source = self.root / "five.pdf"
        fixture(source)
        before = file_sha(source)
        native = native_pages(source)
        oracle_pages = list(native)
        oracle_pages[1] = " ".join(reversed(ev._tokens(native[1])))
        drains = collections.deque([
            [], ["document-open-warning"], [],  # reset, source open, capture open
            [], ["page-one-source-warning"], [], ["page-one-ocg-warning"],
            [], [], [], [], [], [], [], [],
        ])

        def oracle(_path: Path, count: int) -> dict:
            self.assertEqual(3, count)
            return {
                "status": "measured",
                "pages": oracle_pages,
                "tool": {"status": "measured", "version": "synthetic Xpdf"},
            }

        report = ev.collect(
            source,
            before,
            pdftotext_probe=oracle,
            warning_reader=lambda: drains.popleft() if drains else [],
        )
        self.assertEqual(before, file_sha(source), "read-only collector changed source bytes")
        self.assertEqual("measured", report["status"])
        self.assertEqual(["i", "ii", "1"], [p["page_label"]["label"] for p in report["pages"]])
        self.assertEqual(3, report["summary"]["non_ordinal_label_pages"])
        self.assertEqual("present", report["pages"][0]["embedded_thumb"]["status"])
        self.assertFalse(report["pages"][0]["embedded_thumb"]["image_bytes_decoded"])
        self.assertEqual(1, report["summary"]["embedded_thumb_pages"])
        self.assertEqual("order-only-difference", report["pages"][1]["reading_order"]["disposition"])
        self.assertEqual(1, report["summary"]["reading_order_order_only_difference_pages"])
        self.assertTrue(report["document"]["ocg"]["capture_setup"]["all_groups_off_verified"])
        self.assertGreaterEqual(report["summary"]["ocg_variant_difference_pages"], 1)
        self.assertFalse(report["document"]["ocg"]["affects_source_or_marker_input"])
        self.assertFalse(report["pages"][0]["capture_raster"]["pixels_retained"])
        self.assertIn("page-one-source-warning",
                      report["pages"][0]["mupdf_warnings"]["source_page_probes"])
        self.assertIn("page-one-ocg-warning",
                      report["pages"][0]["mupdf_warnings"]["ocg_off_variant"])
        encoded = json.dumps(report)
        self.assertNotIn("primary body survives", encoded, "raw page text leaked into evidence")

    def test_no_label_definition_is_measured_ordinal_fallback(self) -> None:
        source = self.root / "fallback.pdf"
        fixture(source, labels=False)
        native = native_pages(source)
        report = ev.collect(
            source,
            file_sha(source),
            pdftotext_probe=lambda _p, _n: {
                "status": "measured", "pages": native, "tool": {"status": "measured"}
            },
        )
        self.assertEqual(["1", "2", "3"], [p["page_label"]["label"] for p in report["pages"]])
        self.assertTrue(all(p["page_label"]["source"] == "ordinal-fallback"
                            for p in report["pages"]))
        self.assertEqual(0, report["summary"]["non_ordinal_label_pages"])

    def test_duplicate_labels_map_to_lists(self) -> None:
        source = self.root / "duplicate.pdf"
        fixture(source, duplicate_labels=True)
        native = native_pages(source)
        report = ev.collect(
            source,
            file_sha(source),
            pdftotext_probe=lambda _p, _n: {
                "status": "measured", "pages": native, "tool": {"status": "measured"}
            },
        )
        self.assertEqual([1, 3], report["document"]["page_labels"]
                         ["label_to_pages_1based"]["A-1"])

    def test_oracle_unread_is_partial_not_false_zero(self) -> None:
        source = self.root / "oracle-unread.pdf"
        fixture(source)
        report = ev.collect(
            source,
            file_sha(source),
            pdftotext_probe=lambda _p, _n: {
                "status": "UNREAD", "reason": "synthetic timeout", "pages": None,
                "tool": {"status": "UNREAD"},
            },
        )
        self.assertEqual("partial", report["status"])
        self.assertEqual(0, report["summary"]["reading_order_pages_compared"])
        self.assertEqual(
            {"status": "UNREAD", "reason": "synthetic timeout"},
            report["document"]["reading_order_oracle"],
        )
        self.assertTrue(all(p["reading_order"]["status"] == "UNREAD" for p in report["pages"]))

    def test_wrong_oracle_page_count_is_unread(self) -> None:
        source = self.root / "wrong-count.pdf"
        fixture(source)
        report = ev.collect(
            source,
            file_sha(source),
            pdftotext_probe=lambda _p, _n: {
                "status": "measured", "pages": ["only one"],
                "tool": {"status": "measured"},
            },
        )
        self.assertEqual("partial", report["status"])
        self.assertEqual(0, report["summary"]["reading_order_pages_compared"])

    def test_source_identity_mismatch_refuses_before_probe(self) -> None:
        source = self.root / "identity.pdf"
        fixture(source)
        with self.assertRaisesRegex(RuntimeError, "identity mismatch before evidence"):
            ev.collect(source, "0" * 64)

    def test_cli_emits_one_json_record_from_isolated_process(self) -> None:
        source = self.root / "cli.pdf"
        fixture(source)
        proc = subprocess.run(
            [sys.executable, "-B", str(Path(ev.__file__)), "--pdf", str(source),
             "--source-sha256", file_sha(source)],
            capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(ev.SCHEMA, report["schema"])
        self.assertEqual(3, report["source"]["pages"])
        self.assertEqual(1, len(proc.stdout.strip().splitlines()),
                         "child must speak one canonical JSON record on stdout")

    @unittest.skipUnless(any(path.is_file() for path in ev._pdftotext_candidates()),
                             "no pdftotext executable on this host")
    def test_installed_pdftotext_default_mode_smoke(self) -> None:
        source = self.root / "xpdf-smoke.pdf"
        fixture(source)
        report = ev.collect(source, file_sha(source))
        self.assertEqual(3, report["summary"]["reading_order_pages_compared"])
        self.assertEqual("measured", report["producer"]["pdftotext"]["status"])
        self.assertIn("default reading order", report["producer"]["pdftotext"]["mode"])
        self.assertRegex(report["producer"]["pdftotext"]["version"], r"(?i)xpdf|pdftotext")

    def test_thumb_absent_malformed_and_nonimage_are_distinct(self) -> None:
        class FakeDoc:
            def __init__(self, value, is_image=True):
                self.value = value
                self.is_image = is_image

            def page_xref(self, _index):
                return 7

            def xref_get_key(self, _xref, _key):
                return self.value

            def xref_is_image(self, _xref):
                return self.is_image

        self.assertEqual("absent", ev._thumb_evidence(FakeDoc(("null", "null")), 0)["status"])
        self.assertEqual("UNREAD", ev._thumb_evidence(FakeDoc(("xref", "broken")), 0)["status"])
        self.assertEqual(
            "UNREAD", ev._thumb_evidence(FakeDoc(("xref", "9 0 R"), is_image=False), 0)["status"]
        )

    def test_sequence_dispositions_do_not_invent_a_score(self) -> None:
        exact = ev._sequence_evidence("alpha beta", "alpha beta")
        order = ev._sequence_evidence("alpha beta", "beta alpha")
        content = ev._sequence_evidence("alpha beta", "alpha gamma")
        self.assertEqual("exact", exact["disposition"])
        self.assertEqual("order-only-difference", order["disposition"])
        self.assertEqual("content-and-or-order-difference", content["disposition"])
        self.assertNotIn("score", exact)
        self.assertNotIn("verdict", exact)


if __name__ == "__main__":
    unittest.main(verbosity=2)
