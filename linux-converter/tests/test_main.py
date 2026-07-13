"""Lane-topology tests against a real ConvertHandler on a temp root -- no watcher, _convert is
called directly with real files, and outcomes are asserted on the filesystem and status feed.
The OCR conversion itself (Scan lane end-to-end) needs tesseract language data, so it is
verified live on the service rather than here; these tests pin the routing decisions."""

import json
import re

import pymupdf
import pytest

from converter import exporter
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


def _write_text_pdf_with_image(path, chars=2000):
    # A digital page with an embedded figure -- the shape that trips L13: the Clean lane
    # keeps it (probe passes) AND the engine must write an image into assets/.
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), ("lorem ipsum dolor sit amet " * 100)[:chars], fontsize=10)
    pix = page.get_pixmap(dpi=48, clip=pymupdf.Rect(72, 60, 272, 120))
    page.insert_image(pymupdf.Rect(72, 500, 272, 560), pixmap=pix)
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

    def test_spaced_filename_with_image_converts(self, handler, paths):
        # L13: pymupdf4llm sanitizes spaces to underscores across its whole image output
        # path, directory components included. With the assembly dir keyed on the verbatim
        # stem, the first image write ENOENTs and the file quarantines. Every milestone
        # fixture before this one was space-free, which is how L1-L12 never caught it.
        src = paths.convert_inbox / "Designing Freedom - Stafford Beer.pdf"
        _write_text_pdf_with_image(src)

        handler._convert(src)

        assert not src.exists(), "source must be consumed, not quarantined"
        assert not list(paths.quarantine.iterdir())
        bundle_dir = paths.anchor / "Designing Freedom - Stafford Beer"
        md = (bundle_dir / "Designing Freedom - Stafford Beer.md").read_text()
        assert "  lane: clean" in md
        images = list((bundle_dir / "assets").glob("*.png"))
        assert images, "the embedded figure must be extracted into assets/"
        # Every embed in the markdown resolves to a file that actually exists on disk.
        for name in re.findall(r"!\[\[assets/([^\]]+)\]\]", md):
            assert (bundle_dir / "assets" / name).is_file(), name
        assert not list(paths.staging.glob(".part-*"))

    def test_long_filename_is_clamped(self, handler, paths):
        # ~225-byte Anna's Archive stems + derived .part-*.staging-copy names brush the
        # 255-byte component limit -- the published bundle name is clamped (L13 follow-on;
        # budget tightened to 80 bytes for Windows MAX_PATH, L15).
        stem = "long " * 50  # 250 bytes, spaced
        src = paths.convert_inbox / f"{stem}.pdf"
        _write_text_pdf(src)

        handler._convert(src)

        assert not src.exists()
        (bundle_dir,) = [p for p in paths.anchor.iterdir()]
        assert len(bundle_dir.name.encode("utf-8")) <= 80

    def test_interior_paths_fit_windows_budget(self, handler, paths):
        # L15: the vault is consumed on Windows, where the 260-char MAX_PATH covers the FULL
        # path. The bundle dir was already slug-clamped, but interior names re-derived from
        # the raw stem: a 200-byte .md and ~230-byte engine-named asset PNGs pushed real
        # vault paths past 330 chars (Textor ingest, fd0e50a). Budget: every emitted path,
        # vault-relative under Inbox/<slug>--<sha8>/, stays <= 160 bytes.
        # ~230 bytes, the real Textor-ingest shape (must stay <= 251 so <stem>.pdf can
        # exist on ext4 at all).
        stem = ("Judgement and Truth in Early Modern Political Philosophy - Anna " * 4)[:230]
        assert 200 < len(stem.encode("utf-8")) <= 251 - len(".pdf")
        src = paths.convert_inbox / f"{stem}.pdf"
        _write_text_pdf_with_image(src)

        handler._convert(src)

        assert not src.exists(), "source must be consumed, not quarantined"
        assert not list(paths.quarantine.iterdir())
        (bundle_dir,) = [p for p in paths.anchor.iterdir()]
        vault_dir = exporter.INBOX_REL / f"{exporter.slugify(bundle_dir.name)}--{'0' * 8}"
        for f in bundle_dir.rglob("*"):
            if f.is_file():
                rel = vault_dir / f.relative_to(bundle_dir)
                assert len(str(rel).encode("utf-8")) <= 160, rel
        # The engine-visible source link is a conversion detail, never published: the
        # bundle root holds exactly the note, the manifest, and assets/.
        assert {p.name for p in bundle_dir.iterdir()} == {
            f"{bundle_dir.name}.md",
            "manifest.json",
            "assets",
        }
        md = (bundle_dir / f"{bundle_dir.name}.md").read_text()
        images = list((bundle_dir / "assets").glob("*.png"))
        assert images, "the embedded figure must be extracted into assets/"
        for name in re.findall(r"!\[\[assets/([^\]]+)\]\]", md):
            assert (bundle_dir / "assets" / name).is_file(), name

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
