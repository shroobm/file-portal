"""Lane-topology tests against a real ConvertHandler on a temp root -- no watcher, _convert is
called directly with real files, and outcomes are asserted on the filesystem and status feed.
The OCR conversion itself (Scan lane end-to-end) needs tesseract language data, so it is
verified live on the service rather than here; these tests pin the routing decisions."""

import json
import re
import time

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
        # The degeneration tripwire runs on every conversion (report mode) and its verdict
        # travels in the manifest -- a clean synthetic PDF must scan clean.
        assert manifest["degeneration"]["flagged"] is False
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


class _Event:
    """The shape watchdog hands a handler: is_directory + src_path (dest_path for a move)."""

    def __init__(self, path, is_directory=False):
        self.src_path = str(path)
        self.dest_path = str(path)
        self.is_directory = is_directory


class TestAllocatorHop:
    """SYM-011 (S166): the allocator's cross-watch rename is an UNPAIRED IN_MOVED_TO, which
    inotify/watchdog surface as a plain `created` event -- never `moved`, never `close_write`.
    A handler that only listened to moved/closed would never fire on a file the allocator
    just delivered. So `on_created` must convert, after a size-stability wait."""

    def test_created_event_converts_the_hop_after_the_stability_wait(
        self, handler, paths, monkeypatch
    ):
        waited = []
        real_wait = ConvertHandler._wait_until_stable
        monkeypatch.setattr(
            ConvertHandler,
            "_wait_until_stable",
            staticmethod(
                lambda p, interval=0.05, timeout=5.0: (
                    waited.append(p),
                    real_wait(p, interval, timeout),
                )
            ),
        )
        src = paths.convert_inbox / "hopped.pdf"
        _write_text_pdf(src)

        handler.on_created(_Event(src))

        assert waited == [src]  # the wait ran, on this file, before the conversion
        assert not src.exists()  # consumed: the hop was converted
        assert (paths.anchor / "hopped" / "hopped.md").exists()

    def test_created_event_for_a_directory_converts_nothing(self, handler, paths):
        sub = paths.convert_inbox / "a-folder"
        sub.mkdir()
        handler.on_created(_Event(sub, is_directory=True))
        assert sub.exists()
        assert not (paths.anchor / "a-folder").exists()
        assert not (paths.logs / "status.json").exists()

    def test_stability_wait_returns_only_once_the_size_holds(self, tmp_path):
        import threading

        target = tmp_path / "growing.bin"
        target.write_bytes(b"x" * 100)

        def grow():
            for _ in range(3):
                time.sleep(0.03)
                with open(target, "ab") as f:
                    f.write(b"y" * 100)

        t = threading.Thread(target=grow)
        t.start()
        ConvertHandler._wait_until_stable(target, interval=0.2, timeout=5.0)
        t.join()
        # The wait returned only after a whole interval passed with no growth: by then the
        # writer (three appends 30 ms apart) had finished, so the size it settled on is final.
        assert target.stat().st_size == 400

    def test_stability_wait_returns_at_once_for_a_missing_file(self, tmp_path):
        started = time.monotonic()
        ConvertHandler._wait_until_stable(tmp_path / "gone.pdf", interval=0.5, timeout=5.0)
        assert time.monotonic() - started < 0.4

    def test_negative_control_without_the_wait_a_half_written_hop_is_seen_partial(
        self, handler, paths, monkeypatch
    ):
        # What the wait exists for: a stub that returns at once lets `_convert` open a file that
        # is still being written. Here the "still writing" state is a truncated PDF; without
        # the wait the handler acts on it (quarantined as corrupt), the ordinary outcome of
        # acting on partial bytes. With the real wait and a finished file (the case above) the
        # same route converts. The two together show the wait is load-bearing.
        monkeypatch.setattr(
            ConvertHandler,
            "_wait_until_stable",
            staticmethod(lambda p, interval=0.5, timeout=60.0: None),
        )
        src = paths.convert_inbox / "half.pdf"
        whole = paths.convert_inbox / "whole.pdf"
        _write_text_pdf(whole)
        src.write_bytes(whole.read_bytes()[:200])
        whole.unlink()

        handler.on_created(_Event(src))

        assert (paths.quarantine / "half.pdf").exists()
        (event,) = _events(paths)
        assert event["action"] == "rejected"
