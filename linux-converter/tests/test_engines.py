"""Unit tests for dispatch and the text-layer probe. PDFs are generated with pymupdf so the
probe is exercised against real documents, not mocks."""

import pymupdf
import pytest

from converter import engines


@pytest.fixture
def text_pdf(tmp_path):
    """A born-digital one-pager with a real text layer."""
    path = tmp_path / "digital.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    text = "The quick brown fox jumps over the lazy dog. " * 20
    page.insert_text((72, 72), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def image_only_pdf(tmp_path):
    """A 'scan': a page whose text exists only as pixels, with no text layer."""
    src = pymupdf.open()
    page = src.new_page()
    page.insert_text((72, 72), "Scanned words that live only in pixels.", fontsize=14)
    pix = page.get_pixmap(dpi=150)
    src.close()

    path = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, pixmap=pix)
    doc.save(path)
    doc.close()
    return path


class TestResolveEngine:
    def test_pdf_and_epub_use_pymupdf(self):
        assert engines.resolve_engine("book.pdf").name == "pymupdf4llm"
        assert engines.resolve_engine("book.epub").name == "pymupdf4llm"

    def test_docx_uses_pandoc(self):
        assert engines.resolve_engine("paper.docx").name == "pandoc"

    def test_extension_match_is_case_insensitive(self):
        assert engines.resolve_engine("SHOUTY.PDF").name == "pymupdf4llm"
        assert engines.resolve_engine("Paper.DocX").name == "pandoc"

    def test_unknown_extension_has_no_engine(self):
        assert engines.resolve_engine("mystery.xyz") is None
        assert engines.resolve_engine("noext") is None


class TestProbe:
    def test_text_pdf_probes_well_above_threshold(self, text_pdf):
        assert engines.probe_chars_per_page(text_pdf) > 100

    def test_image_only_pdf_probes_near_zero(self, image_only_pdf):
        assert engines.probe_chars_per_page(image_only_pdf) < 10

    def test_unreadable_file_raises(self, tmp_path):
        garbage = tmp_path / "corrupt.pdf"
        garbage.write_bytes(b"not a pdf at all")
        with pytest.raises(Exception):
            engines.probe_chars_per_page(garbage)


class TestMarkdownYield:
    def test_per_page_average(self):
        assert engines.chars_per_page_of_markdown("x" * 300, 3) == 100.0

    def test_zero_pages_does_not_divide_by_zero(self):
        assert engines.chars_per_page_of_markdown("abc", 0) == 3.0


class TestOcrMode:
    """SYM-012 (S166): the Scan lane must DROP a source's prior OCR text, not keep it. pymupdf4llm's
    `force_ocr=True` spells FORCE_KEEP_OLD -- the opposite of what the name implies -- so the
    lane's flag is asserted by identity against the enum, with the engine call captured."""

    @pytest.fixture
    def captured(self, monkeypatch):
        calls = []

        def fake_to_markdown(path, **kwargs):
            calls.append((path, kwargs))
            return "# stub\n"

        monkeypatch.setattr(engines.pymupdf4llm, "to_markdown", fake_to_markdown)
        return calls

    @pytest.fixture
    def settings(self):
        from converter.config import Settings

        return Settings(min_chars_per_page=100, ocr_dpi=300, ocr_language="eng", image_dpi=96)

    def test_scan_lane_drops_prior_ocr_at_our_resolution(self, tmp_path, captured, settings):
        assert (
            engines.run_pymupdf(tmp_path / "s.pdf", tmp_path / "assets", "scan", settings)
            == "# stub\n"
        )
        ((_, kwargs),) = captured
        assert kwargs["use_ocr"] is engines.OCRMode.FORCE_DROP_OLD
        assert kwargs["ocr_dpi"] == settings.ocr_dpi
        assert kwargs["ocr_language"] == settings.ocr_language
        assert kwargs["write_images"] is True and kwargs["dpi"] == settings.image_dpi

    def test_clean_lane_keeps_the_text_layer_and_sets_no_ocr_dpi(
        self, tmp_path, captured, settings
    ):
        engines.run_pymupdf(tmp_path / "c.pdf", tmp_path / "assets", "clean", settings)
        ((_, kwargs),) = captured
        assert kwargs["use_ocr"] is engines.OCRMode.SELECT_KEEP_OLD
        assert "ocr_dpi" not in kwargs

    def test_the_discriminator_the_plan_docs_spelling_is_a_different_mode(self):
        # `force_ocr=True` maps to FORCE_KEEP_OLD; the assertion above would fail on it.
        assert engines.OCRMode.FORCE_KEEP_OLD is not engines.OCRMode.FORCE_DROP_OLD
        assert engines.OCRMode.FORCE_KEEP_OLD != engines.OCRMode.FORCE_DROP_OLD
