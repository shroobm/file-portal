"""WHAT THIS FILE DOES: pytest tests for converter/bundle.py. Groups: image-link rewriting,
frontmatter rendering, name clamping, collision-free paths, and publishing a bundle into the anchor
and staging directories. Uses pytest's tmp_path only; touches no real pipeline directories.

Unit tests for bundle assembly: link rewriting, frontmatter, collision naming, and the
atomic anchor+staging publish."""

from datetime import datetime, timezone

from converter import bundle


# -- image link rewriting --
class TestRewriteImageLinks:
    """Tests for bundle.rewrite_image_links."""

    def test_absolute_extraction_path_becomes_assets_embed(self):
        """An absolute extraction path becomes an assets/ embed link."""
        md = "before ![](/home/rab/file-portal/library/staging/.part-x/assets/x.pdf-1-0.png) after"
        assert bundle.rewrite_image_links(md) == "before ![[assets/x.pdf-1-0.png]] after"

    def test_alt_text_and_title_are_dropped(self):
        """Alt text and the title are discarded in the rewritten embed."""
        md = '![figure 1](assets/media/image1.png "the title")'
        assert bundle.rewrite_image_links(md) == "![[assets/image1.png]]"

    def test_external_urls_are_left_alone(self):
        """Images pointing at http(s) URLs are not rewritten."""
        md = "![logo](https://example.com/logo.png)"
        assert bundle.rewrite_image_links(md) == md

    def test_non_image_links_are_left_alone(self):
        """Ordinary links stay as they are while images beside them are rewritten."""
        md = "[a link](somewhere.md) and ![img](pic.png)"
        assert bundle.rewrite_image_links(md) == "[a link](somewhere.md) and ![[assets/pic.png]]"


# -- frontmatter --
class TestFrontmatter:
    """Tests for bundle.render_frontmatter."""

    def test_scan_lane_stamps_ocr_fields(self):
        """The scan lane writes lane, reason, chars detected, OCR flag, DPI and source hash."""
        fm = bundle.render_frontmatter(
            engine="pymupdf4llm",
            lane="scan",
            lane_reason="no_text_layer",
            chars_per_page_detected=3.2,
            ocr=True,
            ocr_dpi=300,
            converted_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
            source_sha256="abc123",
        )
        assert fm.startswith("---\nconversion:\n")
        assert "  lane: scan" in fm
        assert "  lane_reason: no_text_layer" in fm
        assert "  chars_per_page_detected: 3.2" in fm
        assert "  ocr: true" in fm
        assert "  ocr_dpi: 300" in fm
        assert "  source_sha256: abc123" in fm

    def test_pandoc_output_has_no_ocr_dpi_and_null_chars(self):
        """A non-OCR pandoc result omits ocr_dpi and writes a null for chars detected."""
        fm = bundle.render_frontmatter(
            engine="pandoc",
            lane="clean",
            lane_reason="text_layer_present",
            chars_per_page_detected=None,
            ocr=False,
            ocr_dpi=None,
            converted_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
            source_sha256="abc123",
        )
        assert "  chars_per_page_detected: ~" in fm
        assert "  ocr: false" in fm
        assert "ocr_dpi" not in fm


# -- name clamping --
class TestClampName:
    """Tests for bundle.clamp_name (byte-length limit on bundle names)."""

    def test_short_names_pass_through_unchanged(self):
        """A name already within the limit is returned unchanged."""
        assert bundle.clamp_name("Designing Freedom - Stafford Beer") == (
            "Designing Freedom - Stafford Beer"
        )

    def test_long_name_is_clamped_to_byte_budget(self):
        """A 300-character name is cut to at most 80 UTF-8 bytes."""
        # 80 bytes: Inbox/<slug60>--<sha8>/<stem80>.md = 160 bytes vault-relative (L15).
        clamped = bundle.clamp_name("x" * 300)
        assert len(clamped.encode("utf-8")) <= 80

    def test_clamp_never_splits_a_codepoint(self):
        """The cut never lands inside a multi-byte character."""
        # 79 ASCII bytes + a 3-byte codepoint straddling the 80-byte boundary.
        clamped = bundle.clamp_name("x" * 79 + "€" * 5)
        assert len(clamped.encode("utf-8")) <= 80
        clamped.encode("utf-8").decode("utf-8")  # round-trips: no broken tail byte

    def test_clamp_strips_trailing_dots_and_spaces(self):
        """A clamped name does not end in a space or a dot."""
        assert not bundle.clamp_name("y" * 79 + ". more").endswith((" ", "."))


# -- collision-free paths --
class TestUniquePath:
    """Tests for bundle.unique_path (adds " (n)" when a name is taken)."""

    def test_free_path_is_returned_as_is(self, tmp_path):
        """A path that does not exist yet is returned unchanged."""
        assert bundle.unique_path(tmp_path / "book") == tmp_path / "book"

    def test_file_collision_appends_suffix_before_extension(self, tmp_path):
        """For an existing file the " (1)" goes before the extension."""
        (tmp_path / "a.pdf").touch()
        assert bundle.unique_path(tmp_path / "a.pdf") == tmp_path / "a (1).pdf"

    def test_directory_collision_appends_suffix(self, tmp_path):
        """For existing directories the number counts up to the first free one."""
        (tmp_path / "book").mkdir()
        (tmp_path / "book (1)").mkdir()
        assert bundle.unique_path(tmp_path / "book") == tmp_path / "book (2)"


# -- publishing into anchor and staging --
class TestPublish:
    """Tests for bundle.publish (copy a temp bundle into both destinations, then remove it)."""

    def _make_tmp_bundle(self, staging):
        """Create a small .part-book bundle (markdown, one image, manifest) under staging; return it."""
        tmp = staging / ".part-book"
        (tmp / "assets").mkdir(parents=True)
        (tmp / "book.md").write_text("# hi")
        (tmp / "assets" / "img.png").write_bytes(b"png")
        (tmp / "manifest.json").write_text("{}")
        return tmp

    def test_bundle_lands_in_both_destinations(self, tmp_path):
        """The bundle appears in anchor and staging with its files, and no .part- folder is left."""
        anchor, staging = tmp_path / "anchor", tmp_path / "staging"
        anchor.mkdir()
        staging.mkdir()
        tmp = self._make_tmp_bundle(staging)

        anchor_dest, staging_dest = bundle.publish(tmp, "book", anchor, staging)

        assert anchor_dest == anchor / "book"
        assert staging_dest == staging / "book"
        for dest in (anchor_dest, staging_dest):
            assert (dest / "book.md").read_text() == "# hi"
            assert (dest / "assets" / "img.png").read_bytes() == b"png"
        assert not tmp.exists()
        # No .part- residue anywhere.
        assert not list(staging.glob(".part-*"))

    def test_second_publish_of_same_name_renames(self, tmp_path):
        """Publishing the same name twice puts the second copy at "book (1)" in both places."""
        anchor, staging = tmp_path / "anchor", tmp_path / "staging"
        anchor.mkdir()
        staging.mkdir()
        bundle.publish(self._make_tmp_bundle(staging), "book", anchor, staging)
        anchor_dest, staging_dest = bundle.publish(
            self._make_tmp_bundle(staging), "book", anchor, staging
        )
        assert anchor_dest == anchor / "book (1)"
        assert staging_dest == staging / "book (1)"
