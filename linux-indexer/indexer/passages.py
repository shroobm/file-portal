"""Body markdown -> passages, the indexer's unit. NOT the analyst's "chunk" (docs/34 §6: a
chunk is ~4,000 characters of book markdown); a passage is ~passage_chars characters of one
section, packed on paragraph boundaries.

What this survives, measured on the real vault (Observed 2026-09-09, six bundles): bodies from
50 KB to 1.1 MB; a 32,294-character single line (an OCR degeneration loop that IS in the
vault); 2,249-character table rows; two frontmatter shapes (`conversion:` only, or `analyst:`
followed by `conversion:`), closed by the first `---` line after line 1; Obsidian
`![[assets/...]]` embeds as the ONLY page signal (Marker names assets `_page_<N>_Figure_<k>`,
N 0-based); inline HTML (<sup>, <br>, <span>, comments). Frontmatter is stripped by a plain
fence scan, never a YAML loader (`~` nulls, timestamp coercion, a 64-hex sha that parses as a
float). Metadata comes from manifest.json, not from the frontmatter.

Page attribution is a HINT: the 1-based page of the nearest preceding figure embed, or absent.
The vault carries no per-block page data (blocks.json stays out by J28), so nothing here
promises a page it cannot know. Embed lines and HTML tags are removed from the text that is
embedded; everything else is kept verbatim.
"""

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_EMBED_RE = re.compile(r"!\[\[[^\]]*\]\]")
_PAGE_HINT_RE = re.compile(r"!\[\[assets/_page_(\d+)_")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_WS_RE = re.compile(r"[ \t]+")
_HEADING_JUNK_RE = re.compile(r"[*_`]+")


@dataclass(frozen=True)
class Passage:
    index: int
    text: str
    heading: str
    page_hint: int | None


def strip_frontmatter(text: str) -> str:
    """Drop a leading `---` ... `---` block. A body that does not open with the fence, or
    never closes it, is returned untouched -- guessing would eat prose."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _clean_heading(raw: str) -> str:
    return _WS_RE.sub(" ", _HEADING_JUNK_RE.sub("", raw)).strip()[:120]


def _paragraphs(body: str) -> list[tuple[str, str, int | None, bool]]:
    """(text, heading, page_hint, opens_section) per paragraph; heading and page are those in
    force when the paragraph STARTS, and a paragraph that begins with a heading opens a
    section -- the packer never glues it onto the tail of the previous passage, so a passage
    never borrows the heading that follows it."""
    out: list[tuple[str, str, int | None, bool]] = []
    heading = ""
    page: int | None = None
    buf: list[str] = []
    buf_heading = ""
    buf_page: int | None = None
    buf_opens = False

    def flush() -> None:
        if buf:
            out.append((" ".join(buf), buf_heading, buf_page, buf_opens))
            buf.clear()

    in_fence = False
    for line in _HTML_COMMENT_RE.sub(" ", body).split("\n"):
        hint = _PAGE_HINT_RE.search(line)
        if hint:
            page = int(hint.group(1)) + 1
        cleaned = _HTML_TAG_RE.sub("", _EMBED_RE.sub("", line)).strip()
        if cleaned.startswith("```"):
            in_fence = not in_fence  # a '#' line inside a code fence is code, not a heading
        if not cleaned:
            flush()
            continue
        match = None if in_fence else _HEADING_RE.match(cleaned)
        if match:
            # The line itself stays verbatim in the text (a 32K-char degenerate heading is still
            # body); only the metadata heading is cleaned and clipped.
            flush()
            heading = _clean_heading(match.group(2))
        if not buf:
            buf_heading, buf_page, buf_opens = heading, page, bool(match)
        buf.append(_WS_RE.sub(" ", cleaned))
    flush()
    return out


def _hard_split(text: str, limit: int) -> list[str]:
    pieces = []
    while len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit  # no usable whitespace: cut hard rather than shed a one-word crumb
        pieces.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        pieces.append(text)
    return pieces


def split_passages(body: str, passage_chars: int, passage_max_chars: int) -> list[Passage]:
    paragraphs = []
    for text, heading, page, opens in _paragraphs(body):
        for i, piece in enumerate(_hard_split(text, passage_max_chars)):
            paragraphs.append((piece, heading, page, opens and i == 0))
    passages: list[Passage] = []
    buf = ""
    buf_heading = ""
    buf_page: int | None = None
    for text, heading, page, opens in paragraphs:
        if buf and (opens or len(buf) + 2 + len(text) > passage_chars):
            passages.append(Passage(len(passages), buf, buf_heading, buf_page))
            buf = ""
        if not buf:
            buf_heading, buf_page = heading, page
            buf = text
        else:
            buf = f"{buf}\n\n{text}"
    if buf:
        passages.append(Passage(len(passages), buf, buf_heading, buf_page))
    return passages
