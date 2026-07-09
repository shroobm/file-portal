"""Lane-topology tests against a real ConvertHandler on a temp root -- no watcher, _convert is
called directly with real files, and outcomes are asserted on the filesystem and status feed.
The OCR conversion itself (Scan lane end-to-end) needs tesseract language data, so it is
verified live on the service rather than here; these tests pin the routing decisions."""

import json

import pymupdf
import pytest

from converter.config import Paths
from converter.main import ConvertHandler
from converter.status import StatusWriter

CONFIG = """
[conversion]
min_chars_per_page = 100
ocr_dpi = 300
image_dpi = 96
"""


@pytest.fixture
def paths(tmp_path):
    p = Paths.from_root(tmp_path / "file-portal")
    p.ensure_exist()
    return p


@pytest.fixture
def handler(paths, tmp_path):
    settings_path = tmp_path / "converter.toml"
    settings_path.write_text(CONFIG)
    return ConvertHandler(paths, settings_path, StatusWriter(paths.logs / "status.json"))


def _events(paths):
    return json.loads((paths.logs / "status.json").read_text())["events"]


def _write_text_pdf(path, chars=2000):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), ("lorem ipsum dolor sit amet " * 100)[:chars], fontsize=10)
    doc.save(path)
    doc.close()


def _write_image_pdf(path):
    src = pymupdf.open()
    page = src.new_page()
    page.insert_text((72, 72), "pixels only", fontsize=14)
    pix = page.get_pixmap(dpi=96)
    src.close()
    doc = pymupdf.open()
    page = doc.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, pixmap=pix)
    doc.save(path)
    doc.close()


class TestCleanLane:
    def test_text_pdf_converts_to_anchor_and_staging(self, handler, paths):
        src = paths.convert_inbox / "digital.pdf"
        _write_text_pdf(src)

        handler._convert(src)

        assert not src.exists()  # source consumed on success
        md = (paths.anchor / "digital" / "digital.md").read_text()
        assert md.startswith("---\nconversion:\n")
        assert "  lane: clean" in md
        assert "  lane_reason: text_layer_present" in md
        assert (paths.staging / "digital" / "digital.md").exists()
        manifest = json.loads((paths.anchor / "digital" / "manifest.json").read_text())
        assert manifest["engine"] == "pymupdf4llm"
        assert manifest["source_sha256"]
        # Success emits no status event -- the allocator hop already showed green.
        assert not (paths.logs / "status.json").exists()

    def test_no_part_residue_after_success(self, handler, paths):
        src = paths.convert_inbox / "digital.pdf"
        _write_text_pdf(src)
        handler._convert(src)
        assert not list(paths.staging.glob(".part-*"))
        assert not list(paths.anchor.glob(".part-*"))


class TestReroute:
    def test_scanned_pdf_moves_to_scan_inbox_with_allocated_event(self, handler, paths):
        src = paths.convert_inbox / "scan.pdf"
        _write_image_pdf(src)

        handler._convert(src)

        assert not src.exists()
        assert (paths.convert_scan_inbox / "scan.pdf").exists()
        assert not list(paths.quarantine.iterdir())
        (event,) = _events(paths)
        assert event["action"] == "allocated"
        assert event["category"] == "convert"
        assert event["dest"] == "pipeline/convert-scan-inbox/scan.pdf"


class TestQuarantine:
    def test_unknown_extension_is_rejected(self, handler, paths):
        src = paths.convert_inbox / "mystery.xyz"
        src.write_text("?")

        handler._convert(src)

        assert (paths.quarantine / "mystery.xyz").exists()
        (event,) = _events(paths)
        assert event["action"] == "rejected"
        assert "no conversion engine" in event["reason"]

    def test_corrupt_pdf_is_rejected_not_rerouted(self, handler, paths):
        src = paths.convert_inbox / "corrupt.pdf"
        src.write_bytes(b"not a pdf")

        handler._convert(src)

        assert (paths.quarantine / "corrupt.pdf").exists()
        assert not list(paths.convert_scan_inbox.iterdir())
        (event,) = _events(paths)
        assert event["action"] == "rejected"

    def test_dotfiles_and_missing_files_are_ignored(self, handler, paths):
        dotfile = paths.convert_inbox / ".part-half-written.pdf"
        dotfile.write_bytes(b"partial")
        handler._convert(dotfile)
        handler._convert(paths.convert_inbox / "never-existed.pdf")
        assert dotfile.exists()  # untouched
        assert not (paths.logs / "status.json").exists()
