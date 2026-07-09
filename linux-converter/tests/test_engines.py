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
