# -*- coding: utf-8 -*-
"""page_anchors.py — Obsidian page anchors for a bundle's markdown, from its own blocks.json (S209 E6, 2026-09-20; Rab signed
the Desk proposal 7b1ef158 as (b): built into the line behind a lever, OFF until he turns it).

marker's markdown carries no page marks; blocks.json knows every block's page. `anchor_markdown` appends an Obsidian block
id ` ^p<N>` to the first paragraph of each page it can locate (a normalised-text match, so bold, links and whitespace do
not matter), idempotently — `[[Book#^p56]]` then resolves to that paragraph. Nothing else in the text is touched: a table
row is never anchored (the id would break the table), a fenced line never (a runaway fence longer than MAX_FENCE lines is
not a fence — the analyst's known fence slip), a page already carrying its id is left alone.

Ported from the tenant institution's app/vaultlinks.py (S7, proved on 22 books: 73–100 % of pages anchored; the nearest-hit
rule against repeated running heads; the runaway-fence rule from Naked Statistics' 33 ``` markers). The lever lives in
convert_and_ship.py (`anchors_at_ship()`), not here — this module is pure.

    python page_anchors.py <book.md> <blocks.json>     # prints anchored/pages; writes nothing
"""
from __future__ import annotations

import io
import json
import re
import sys

ANCHOR_RE = re.compile(r" \^p(\d+)\s*$")
BLOCK_ID_RE = re.compile(r" \^[A-Za-z0-9-]+\s*$")
TEXT_TYPES = ("Text", "SectionHeader", "ListItem", "Caption", "TextInlineMath", "Footnote", "Handwriting")
KEY_LEN = 48
MIN_KEY = 24
MAX_FENCE = 120            # a fenced region longer than this is a runaway fence, not code


def _norm(s: str):
    """Lower-case alphanumerics only, with a map from each kept char back to its offset in `s`."""
    out = []
    idx = []
    for i, ch in enumerate(s):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
    return "".join(out), idx


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def anchor_markdown(md: str, blocks: list[dict]) -> tuple[str, int, int]:
    """Returns (markdown, pages_anchored, pages_total). Idempotent: a page already carrying ^p<N> is left alone."""
    nl = "\r\n" if "\r\n" in md else "\n"
    lines = md.split(nl)
    starts = []
    off = 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + len(nl)
    text = nl.join(lines)
    norm, idx = _norm(text)
    have = {int(m.group(1)) for ln in lines for m in [ANCHOR_RE.search(ln)] if m}
    by_page: dict[int, list[dict]] = {}
    for b in blocks:
        p = b.get("page")
        if p is None or b.get("block_type") not in TEXT_TYPES:
            continue
        by_page.setdefault(p, []).append(b)
    pages = sorted(by_page)
    cursor = 0
    anchored = 0
    fence_lines = set()
    open_at = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("```"):
            if open_at is None:
                open_at = i
            else:
                if i - open_at <= MAX_FENCE:
                    fence_lines.update(range(open_at, i + 1))
                open_at = None
    seen_keys = set()
    for p in pages:
        human = p + 1
        # the page's first candidates, each searched forward from the cursor; the NEAREST hit wins — a repeated running
        # head or a phrase that recurs later in the book must not drag the cursor past the page's real text
        found = []
        for b in by_page[p][:6]:
            key, _ = _norm(_plain(b.get("html", "")))
            key = key[:KEY_LEN]
            if len(key) < MIN_KEY or key in seen_keys:
                continue
            hit = norm.find(key, cursor)
            if hit >= 0:
                found.append((hit, key))
        if not found:
            continue
        hit, key = min(found)
        seen_keys.add(key)
        cursor = hit + len(key)
        if human in have:
            continue
        char = idx[hit]
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= char:
                lo = mid
            else:
                hi = mid - 1
        line_no = lo
        if line_no in fence_lines:
            continue
        end = line_no
        while end + 1 < len(lines) and lines[end + 1].strip() and (end + 1) not in fence_lines and not lines[end + 1].lstrip().startswith("|"):
            end += 1
        if lines[end].lstrip().startswith("|"):
            continue                          # a table row: the block id would break the table
        if BLOCK_ID_RE.search(lines[end]):
            continue                          # some other id already there; leave it
        lines[end] = lines[end].rstrip() + " ^p%d" % human
        have.add(human)
        anchored += 1
    return nl.join(lines), anchored, len(pages)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    md = io.open(argv[0], encoding="utf-8", newline="").read()
    blocks = json.load(io.open(argv[1], encoding="utf-8")).get("blocks", [])
    _out, n, total = anchor_markdown(md, blocks)
    print("%s: would anchor %d of %d pages (nothing written)" % (argv[0], n, total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
