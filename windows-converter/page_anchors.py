# -*- coding: utf-8 -*-
"""page_anchors.py — Obsidian page anchors for a bundle's markdown, from its own blocks.json (S209 E6, 2026-09-20; Rab signed
the Desk proposal 7b1ef158 as (b): built into the line behind a lever, OFF until he turns it).

marker's markdown carries no page marks; blocks.json knows every block's page. `anchor_markdown` appends an Obsidian block
id ` ^p<N>` to the first paragraph of each page it can locate (a normalised-text match, so bold, links and whitespace do
not matter), idempotently — `[[Book#^p56]]` then resolves to that paragraph. Nothing else in the text is touched: a table
row is never anchored (the id would break the table), a fenced line never (a runaway fence longer than MAX_FENCE lines is
not a fence — the analyst's known fence slip), a page already carrying its id is left alone.

S209, the five zips measured (31 of 309 pages unanchored; `sittings/S209/anchor_why.py`): the rule searches ALL of a page's
text blocks; a hit whose line is a table row, or already carries another page's id (a contents list quoting the next pages'
headings took four CIBC pages), yields to the next-nearest hit; a page no text line can take gets the structured-block form
Obsidian documents for tables — the id on its own line after the table, a blank line before and after — found by the
table block's own text; a key shorter than MIN_KEY is accepted only when it is unique from the cursor on.

Ported from the tenant institution's app/vaultlinks.py (S7, proved on 22 books: 73–100 % of pages anchored; the nearest-hit
rule against repeated running heads; the runaway-fence rule from Naked Statistics' 33 ``` markers). The lever lives in
convert_and_ship.py (`anchors_at_ship()`), not here — this module is pure.

    python page_anchors.py <book.md> <blocks.json>     # prints anchored/pages; writes nothing
"""
from __future__ import annotations

import bisect
import io
import json
import re
import sys

ANCHOR_RE = re.compile(r"(?:^|\s)\^p(\d+)\s*$")          # a trailing ` ^pN`, or a bare `^pN` line (the form for tables)
BLOCK_ID_RE = re.compile(r"(?:^|\s)\^[A-Za-z0-9-]+\s*$")
TEXT_TYPES = ("Text", "SectionHeader", "ListItem", "ListGroup", "Caption", "TextInlineMath", "Footnote", "Handwriting")
TABLE_TYPES = ("Table", "TableGroup")
KEY_LEN = 48
MIN_KEY = 24
MIN_KEY_UNIQUE = 12        # a shorter key is accepted only when it occurs once from the cursor on (S209: 11 of 31 unanchored
                           # pages across five zips had nothing but short labels and footnote marks in their first six blocks)
MAX_FENCE = 120            # a fenced region longer than this is a runaway fence, not code
TABLE_REACH = 4            # a table block's key may land on the table's caption/header line; the rows start within this many lines


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


def _increasing_run(seq: list[int]) -> list[int]:
    """Indices of one longest strictly increasing subsequence of `seq` (patience sorting, stdlib only)."""
    tails: list[int] = []
    tails_idx: list[int] = []
    parent = [-1] * len(seq)
    for i, v in enumerate(seq):
        k = bisect.bisect_left(tails, v)
        if k == len(tails):
            tails.append(v)
            tails_idx.append(i)
        else:
            tails[k] = v
            tails_idx[k] = i
        parent[i] = tails_idx[k - 1] if k > 0 else -1
    out = []
    i = tails_idx[-1] if tails_idx else -1
    while i >= 0:
        out.append(i)
        i = parent[i]
    return out[::-1]


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
    tables: dict[int, list[dict]] = {}
    for b in blocks:
        p = b.get("page")
        if p is None:
            continue
        kind = b.get("block_type")
        if kind in TEXT_TYPES:
            by_page.setdefault(p, []).append(b)
        elif kind in TABLE_TYPES:
            tables.setdefault(p, []).append(b)
    pages = sorted(set(by_page) | set(tables))
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

    def line_of(char: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= char:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def is_row(i: int) -> bool:
        return lines[i].lstrip().startswith("|")

    # S209 E10 (NBC, 25 of 84 anchored and 13 of those on the WRONG page): a key that recurs in the book — a footnote
    # repeated on every segment page, a running section head — was taken at its nearest instance after the cursor, which
    # is a LATER page's when this page's own instance is absent (a table page whose text blocks are only its footnotes);
    # the cursor overshot and every page after read no-hit. Two rules: a key that occurs ONCE in the book leads and is
    # searched from the top (its position is its page's, wherever the cursor stands); and NO hit may pass the first
    # once-only text of any later page — the next page's own words are the fence. A page the fence empties stays
    # unanchored, which is honest; an anchor on another page's text is not.
    counts: dict[str, int] = {}

    def occurrences(key: str) -> int:
        if key not in counts:
            counts[key] = norm.count(key)
        return counts[key]

    def key_of(b: dict) -> str:
        key, _ = _norm(_plain(b.get("html", "")))
        return key[:KEY_LEN]

    # a once-only key can itself stand on the wrong page — the page's own instance lost, one instance on another page
    # kept (NBC's p.13 footnote survives only at p.3's) — and one such key would fence every page before it; the TRUSTED
    # once-only keys are the longest run whose positions increase with the pages, and only those lead or fence
    once_keys = []                        # (page, position, key), page order then position
    for p in pages:
        for b in by_page.get(p, []):
            key = key_of(b)
            if len(key) >= MIN_KEY_UNIQUE and occurrences(key) == 1:
                once_keys.append((p, norm.find(key), key))
    once_keys.sort()
    trusted = {(once_keys[i][0], once_keys[i][2]) for i in _increasing_run([pos for _, pos, _ in once_keys])}
    unique_at: dict[int, int] = {}
    for p, at, key in once_keys:
        if (p, key) in trusted and (p not in unique_at or at < unique_at[p]):
            unique_at[p] = at
    fence: dict[int, int] = {}
    ahead = len(norm) + 1
    for p in reversed(pages):
        fence[p] = ahead
        if p in unique_at:
            ahead = min(ahead, unique_at[p])

    seen_keys = set()
    inserts = []                          # (after_line, human): the structured form, applied last so line numbers hold
    table_ends = set()                    # tables already given an id (a table spanning pages is one markdown block)
    cursor = 0
    anchored = 0
    for p in pages:
        human = p + 1
        # every text block of the page is a candidate: a once-only key from the top, a recurring one forward from the
        # cursor; the once-only keys lead, then the NEAREST hit — a repeated running head or a phrase that recurs later
        # in the book must not drag the cursor past the page's real text, and nothing may pass the fence
        hits = []
        for b in by_page.get(p, []):
            key = key_of(b)
            if len(key) < MIN_KEY_UNIQUE or key in seen_keys:
                continue
            once = (p, key) in trusted
            hit = norm.find(key) if once else norm.find(key, cursor)
            if hit < 0 or hit >= fence[p]:
                continue
            if not once and len(key) < MIN_KEY and norm.find(key, hit + 1) >= 0:
                continue                  # a short key must be unique from here on, or it is a label that recurs
            hits.append((0 if once else 1, hit, key))
        hits.sort()
        hits = [(hit, key) for _, hit, key in hits]
        if hits:
            cursor = max(cursor, hits[0][0] + len(hits[0][1]))
            seen_keys.add(hits[0][1])
        if human in have:
            continue
        placed = False
        for hit, key in hits:
            line_no = line_of(idx[hit])
            if line_no in fence_lines:
                continue
            end = line_no
            while end + 1 < len(lines) and lines[end + 1].strip() and (end + 1) not in fence_lines and not is_row(end + 1):
                end += 1
            if is_row(end):
                continue                  # a table row: the block id would break the table — the next-nearest hit may not
            if BLOCK_ID_RE.search(lines[end]):
                continue                  # a line another page already holds (a contents list quoting this page's heading)
            lines[end] = lines[end].rstrip() + " ^p%d" % human
            have.add(human)
            anchored += 1
            placed = True
            seen_keys.add(key)
            break
        if placed:
            continue
        # no text line took the id: the page's tables, in Obsidian's form for a structured block — the id on its own
        # line after the table, a blank line before and after — the table found by its own cells' text
        for b in tables.get(p, []):
            hit, key = -1, ""
            for row in re.split(r"(?i)</tr>", b.get("html", "")):
                # a markdown row is an html row: a header's cells may render in another order (colspans), a body row's do not
                key, _ = _norm(_plain(row))
                key = key[:KEY_LEN]
                if len(key) < MIN_KEY:
                    continue
                hit = norm.find(key, cursor)
                if hit >= fence[p]:
                    hit = -1              # a row that recurs (a Total line) found only past the next page's own text
                if hit >= 0:
                    break
            if hit < 0:
                continue
            line_no = line_of(idx[hit])
            reach = 0
            while not is_row(line_no) and reach < TABLE_REACH and line_no + 1 < len(lines):
                line_no += 1
                reach += 1
            if not is_row(line_no) or line_no in fence_lines:
                continue
            end = line_no
            while end + 1 < len(lines) and is_row(end + 1):
                end += 1
            if end + 2 < len(lines) and not lines[end + 1].strip() and BLOCK_ID_RE.search(lines[end + 2]):
                continue                  # the table already carries an id
            if end in table_ends:
                continue                  # a table spanning pages is one block with one id: the first page's; later pages count unanchored
            table_ends.add(end)
            inserts.append((end, human))
            have.add(human)
            anchored += 1
            cursor = hit + len(key)
            break
    for end, human in sorted(inserts, reverse=True):
        piece = ["", "^p%d" % human]
        if end + 1 < len(lines) and lines[end + 1].strip():
            piece.append("")
        lines[end + 1:end + 1] = piece
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
