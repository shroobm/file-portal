"""Passage splitting on the shapes the real vault holds (Observed 2026-09-09): two frontmatter
forms, headings, Obsidian embeds as the only page signal, inline HTML, a 30,000-character
single line. Pure functions, no fixtures."""

from indexer.passages import split_passages, strip_frontmatter

ANALYST_FM = (
    "---\nanalyst:\n  model: qwen3:8b\n  chunks_passed: 35\nconversion:\n  engine: marker\n"
    "  chars_per_page_detected: ~\n  source_sha256: 1234e5" + "0" * 58 + "\n---\n# Body\n\ntext\n"
)


def test_frontmatter_both_shapes_are_stripped_by_fence_scan():
    assert strip_frontmatter(ANALYST_FM) == "# Body\n\ntext\n"
    assert strip_frontmatter("---\nconversion:\n  lane: scan\n---\n![[assets/x.png]]\n") == (
        "![[assets/x.png]]\n"
    )


def test_frontmatter_absent_or_unclosed_is_left_alone():
    assert strip_frontmatter("# No fence\n\n---\n") == "# No fence\n\n---\n"
    assert strip_frontmatter("---\nnever: closed\n") == "---\nnever: closed\n"


def test_headings_and_page_hints_belong_to_the_passage_they_open():
    body = (
        "# One\n\nfirst paragraph\n\n![[assets/_page_0_Figure_0.jpeg]]\n\n## Two\n\nsecond "
        "paragraph\n\n![[assets/_page_7_Picture_2.jpeg]]\n\nthird paragraph\n"
    )
    got = split_passages(body, passage_chars=30, passage_max_chars=60)
    by_text = {p.text.split("\n")[0]: p for p in got}
    assert by_text["# One"].heading == "One" and by_text["# One"].page_hint is None
    assert by_text["## Two"].heading == "Two" and by_text["## Two"].page_hint == 1
    assert by_text["third paragraph"].heading == "Two"
    assert by_text["third paragraph"].page_hint == 8, "_page_7_ is 0-based -> page 8"
    assert [p.index for p in got] == list(range(len(got)))


def test_embeds_tags_and_comments_are_removed_from_the_text():
    body = (
        'Para with <sup>1</sup> note<br>and <span id="page-3-0"></span>anchor\n\n'
        "<!-- Start of picture text -->\n\n![[assets/_page_2_Figure_1.jpeg]]\n\nafter\n"
    )
    got = split_passages(body, passage_chars=200, passage_max_chars=400)
    joined = "\n\n".join(p.text for p in got)
    assert "<" not in joined and "![[" not in joined and "picture text" not in joined
    assert "Para with 1 noteand anchor" in joined


def test_a_degenerate_line_is_hard_capped():
    # Brain of the Firm line 1600: 32,294 characters of "## The Control of the Control of ..."
    body = "## " + "The Control of " * 2200 + "\n\nnormal paragraph\n"
    got = split_passages(body, passage_chars=800, passage_max_chars=1200)
    assert all(len(p.text) <= 1200 for p in got)
    assert sum(len(p.text) for p in got) > 30000, "nothing is dropped, only split"
    assert all(p.heading.startswith("The Control of") and len(p.heading) <= 120 for p in got[:-1])


def test_packing_respects_the_target_and_paragraph_boundaries():
    paragraphs = [f"paragraph number {i} with some filler words in it" for i in range(20)]
    got = split_passages("\n\n".join(paragraphs) + "\n", passage_chars=150, passage_max_chars=300)
    assert all(len(p.text) <= 150 for p in got)
    assert all(not p.text.startswith(" ") and "\n\n" in p.text for p in got[:-1])
    assert "\n\n".join(p.text for p in got) == "\n\n".join(paragraphs)


def test_empty_body_yields_no_passages():
    assert split_passages("", 800, 1200) == []
    assert split_passages("\n\n![[assets/_page_0_Figure_0.jpeg]]\n\n", 800, 1200) == []


def test_code_fence_lines_are_never_headings():
    body = "# Real\n\n```\n# not a heading\ncode\n```\n\nafter\n"
    got = split_passages(body, passage_chars=200, passage_max_chars=400)
    assert {p.heading for p in got} == {"Real"}


def test_hard_split_never_sheds_a_crumb():
    body = "# " + "H" * 1500 + "\n"
    got = split_passages(body, passage_chars=800, passage_max_chars=1200)
    assert [len(p.text) for p in got] == [1200, 302]
    assert all(p.heading.startswith("HHHH") for p in got)
