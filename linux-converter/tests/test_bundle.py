"""Unit tests for bundle assembly: link rewriting, frontmatter, collision naming, and the
atomic anchor+staging publish."""

from datetime import datetime, timezone

from converter import bundle


class TestRewriteImageLinks:
    def test_absolute_extraction_path_becomes_assets_embed(self):
        md = "before ![](/home/rab/file-portal/library/staging/.part-x/assets/x.pdf-1-0.png) after"
        assert bundle.rewrite_image_links(md) == "before ![[assets/x.pdf-1-0.png]] after"

    def test_alt_text_and_title_are_dropped(self):
        md = '![figure 1](assets/media/image1.png "the title")'
        assert bundle.rewrite_image_links(md) == "![[assets/image1.png]]"

    def test_external_urls_are_left_alone(self):
        md = "![logo](https://example.com/logo.png)"
        assert bundle.rewrite_image_links(md) == md

    def test_non_image_links_are_left_alone(self):
        md = "[a link](somewhere.md) and ![img](pic.png)"
        assert bundle.rewrite_image_links(md) == "[a link](somewhere.md) and ![[assets/pic.png]]"


class TestFrontmatter:
    def test_scan_lane_stamps_ocr_fields(self):
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


class TestClampName:
    def test_short_names_pass_through_unchanged(self):
        assert bundle.clamp_name("Designing Freedom - Stafford Beer") == (
            "Designing Freedom - Stafford Beer"
        )

    def test_long_name_is_clamped_to_byte_budget(self):
        # 80 bytes: Inbox/<slug60>--<sha8>/<stem80>.md = 160 bytes vault-relative (L15).
        clamped = bundle.clamp_name("x" * 300)
        assert len(clamped.encode("utf-8")) <= 80

    def test_clamp_never_splits_a_codepoint(self):
        # 79 ASCII bytes + a 3-byte codepoint straddling the 80-byte boundary.
        clamped = bundle.clamp_name("x" * 79 + "€" * 5)
        assert len(clamped.encode("utf-8")) <= 80
        clamped.encode("utf-8").decode("utf-8")  # round-trips: no broken tail byte

    def test_clamp_strips_trailing_dots_and_spaces(self):
        assert not bundle.clamp_name("y" * 79 + ". more").endswith((" ", "."))


class TestUniquePath:
    def test_free_path_is_returned_as_is(self, tmp_path):
        assert bundle.unique_path(tmp_path / "book") == tmp_path / "book"

    def test_file_collision_appends_suffix_before_extension(self, tmp_path):
        (tmp_path / "a.pdf").touch()
        assert bundle.unique_path(tmp_path / "a.pdf") == tmp_path / "a (1).pdf"

    def test_directory_collision_appends_suffix(self, tmp_path):
        (tmp_path / "book").mkdir()
        (tmp_path / "book (1)").mkdir()
        assert bundle.unique_path(tmp_path / "book") == tmp_path / "book (2)"


class TestPublish:
    def _make_tmp_bundle(self, staging):
        tmp = staging / ".part-book"
        (tmp / "assets").mkdir(parents=True)
        (tmp / "book.md").write_text("# hi")
        (tmp / "assets" / "img.png").write_bytes(b"png")
        (tmp / "manifest.json").write_text("{}")
        return tmp

    def test_bundle_lands_in_both_destinations(self, tmp_path):
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
        anchor, staging = tmp_path / "anchor", tmp_path / "staging"
        anchor.mkdir()
        staging.mkdir()
        bundle.publish(self._make_tmp_bundle(staging), "book", anchor, staging)
        anchor_dest, staging_dest = bundle.publish(
            self._make_tmp_bundle(staging), "book", anchor, staging
        )
        assert anchor_dest == anchor / "book (1)"
        assert staging_dest == staging / "book (1)"
