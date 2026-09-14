"""table_geometry — the reading half of the table-geometry layer (S150, Rab signed 2026-09-14: "build the new analyst… see what
we gained, and lost, and what is still missing"). Pure functions, no I/O, no model, no GPU.

THE UNIT is the table a renderer reads (GFM, markdown-it, Obsidian's own parser near enough): a header line holding an unescaped
`|` whose NEXT line is a delimiter row (`|---|`), then every following NON-BLANK line until a blank one. A line touching the last row
becomes a row; a blank ends the table; a `|` inside a fenced code block is text. This is the same reading as the bench's
`_table_blocks` (prototypes/repair-bench/bench.py) and its page-side `tableHealth` (bench.html, tested by test_table_health.js);
the converter cannot import a prototype, so the reading lives here twice and each copy carries its own tests.

What it names, per table (`census(lines)`):
  rows/cols · the header/delimiter agreement · the health issues (the S149 rules) · the letter-column signature (a first column
  mostly empty whose filled cells are one to four letters or `<br>`-stacked letters — a rotated group label read letter by letter,
  Valentine's Exhibit 8.2) · `<br>` in header cells · the dot matrix (• per row, the total, the stray glyphs) · the title-row shape
  (a first row with one filled cell above the real header). Every number names what it counts; nothing here changes a byte.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

DELIM = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
BR = re.compile(r"<br\s*/?>", re.I)
DOT = "•"
STRAY_DOTS = ("٠", "·", "∙", "●", "◦", "*")          # glyphs an OCR pass reads for a bullet mark
LETTERISH = re.compile(r"^[A-Za-zÀ-ž]{1,4}$")         # a cell that is one to four letters (OCR confusions included)


# ---- the reading ------------------------------------------------------------------------------

def fence_mask(lines: list[str]) -> list[bool]:
    """True for every line inside a fenced code block (``` or ~~~, the fence lines included)."""
    mask, fence = [], None
    for l in lines:
        s = l.lstrip()
        if fence is None and (s.startswith("```") or s.startswith("~~~")):
            fence = s[:3]
            mask.append(True)
            continue
        if fence is not None:
            mask.append(True)
            if s.startswith(fence):
                fence = None
            continue
        mask.append(False)
    return mask


def has_pipe(l: str) -> bool:
    return "|" in l.replace("\\|", "")


def table_blocks(lines: list[str]) -> list[tuple[int, int, int]]:
    """Every table a renderer would read, as (header, delimiter, last) 0-based inclusive."""
    mask = fence_mask(lines)
    out, i, n = [], 0, len(lines)
    while i < n - 1:
        if (not mask[i] and lines[i].strip() and has_pipe(lines[i]) and not mask[i + 1] and DELIM.match(lines[i + 1])):
            e = i + 1
            while e + 1 < n and lines[e + 1].strip():
                e += 1
            out.append((i, i + 1, e))
            i = e + 1
        else:
            i += 1
    return out


def cells(row: str) -> list[str]:
    """The cells of a pipe row: a leading/trailing pipe is the edge, `\\|` and a pipe inside a code span are text."""
    t = row.strip().replace("\\|", "\x00")
    t = re.sub(r"`[^`]*`", lambda m: m.group(0).replace("|", "\x00"), t)
    parts = t.split("|")
    if parts and parts[0].strip() == "":
        parts.pop(0)
    if parts and parts[-1].strip() == "":
        parts.pop()
    return [p.replace("\x00", "|").strip() for p in parts]


def is_repair_line(l: str) -> bool:
    return l.startswith("![[assets/_repair") or l.startswith("<!-- repair ") or l.startswith("<!-- transcribed ")


# ---- the health (the S149 rules, the page's own twin) ---------------------------------------------

def health(lines: list[str]) -> list[dict]:
    """Every way a table breaks for a renderer, as {line (1-based), reason}."""
    issues, mask, covered = [], fence_mask(lines), set()
    n = len(lines)

    def pipe_row(k):
        return k < n and not mask[k] and lines[k].lstrip().startswith("|")

    for h, d, e in table_blocks(lines):
        covered.update(range(h, e + 1))
        want, dc = len(cells(lines[h])), len(cells(lines[d]))
        if want != dc:
            issues.append({"line": h + 1, "reason": "the header has %d cells and the delimiter row %d — a renderer does not treat this as a table at all" % (want, dc)})
            continue
        for k in range(d + 1, e + 1):
            l = lines[k]
            if is_repair_line(l) or not has_pipe(l):
                issues.append({"line": k + 1, "reason": "this line touches the table's last row, so a renderer folds it in as a garbled row — put a blank line before it"})
            else:
                c = len(cells(l))
                if c != want:
                    issues.append({"line": k + 1, "reason": "row has %d cells, the header has %d — %s" % (c, want, "the extra cells are dropped" if c > want else "the missing cells are blank")})
        j = e + 1
        while j < n and (lines[j].strip() == "" or is_repair_line(lines[j])):
            j += 1
        if j > e + 1 and pipe_row(j) and not (j + 1 < n and DELIM.match(lines[j + 1])):
            for k in range(e + 1, j):
                if lines[k].strip():
                    issues.append({"line": k + 1, "reason": "a non-table line inside the table — the table ends here for a renderer (the S149 split)"})
            q = j
            while pipe_row(q):
                covered.add(q)
                q += 1
            issues.append({"line": j + 1, "reason": "these rows are cut off from their header — a renderer shows them as plain text"})
    i = 0
    while i < n:
        if i in covered or not pipe_row(i):
            i += 1
            continue
        e = i
        while pipe_row(e + 1):
            e += 1
        covered.update(range(i, e + 1))
        j = e + 1
        while j < n and (lines[j].strip() == "" or is_repair_line(lines[j])):
            j += 1
        if e == i and j > e + 1 and j < n and DELIM.match(lines[j]) and not mask[j]:
            issues.append({"line": i + 1, "reason": "the table's header is cut from its delimiter row by the lines under it — a renderer shows plain text (the S149 split)"})
            for k in range(e + 1, j):
                if lines[k].strip():
                    issues.append({"line": k + 1, "reason": "a non-table line inside the table — the table ends here for a renderer (the S149 split)"})
            i = e + 1
            continue
        if DELIM.match(lines[i]):
            why = "a delimiter row (|---|) with no header row directly above it — the rows below render as plain text"
        elif e == i:
            why = "a lone pipe row — no delimiter row under it, so a renderer shows plain text"
        else:
            why = "the row under the header is not a delimiter row (|---|), so a renderer shows plain text"
        issues.append({"line": i + 1, "reason": why})
        i = e + 1
    issues.sort(key=lambda x: x["line"])
    return issues


# ---- the signatures (what the layer will repair, named before it exists) -----------------------------

@dataclass
class TableReading:
    first_line: int                 # 1-based, the header row
    last_line: int                  # 1-based
    rows: int                       # header + body rows
    cols: int                       # the header's cell count
    delimiter_cols: int
    header_delim_agree: bool
    row_cell_counts: list[int] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    title_row: bool = False          # the first row holds ONE filled cell and the next row looks like the real header
    header_br_cells: int = 0         # header cells carrying <br> (a rotated or wrapped column header)
    letter_column: bool = False      # column 1 mostly empty, its filled cells letters or <br>-stacked letters
    letter_column_cells: int = 0
    letters_in_order: str = ""       # the filled cells of column 1 concatenated top-down, <br> dropped
    letter_runs: list[str] = field(default_factory=list)   # each run of consecutive filled cells
    dots_total: int = 0
    dots_per_row: list[int] = field(default_factory=list)
    stray_dot_glyphs: int = 0
    empty_cells: int = 0
    filled_cells: int = 0


def _bare(cell: str) -> str:
    """A cell with its <br>, spaces, punctuation and combining marks removed — what an OCR pass left of a letter."""
    s = BR.sub("", cell)
    return "".join(ch for ch in s if ch.isalnum())


def _pieces(cell: str) -> list[str]:
    """The cell split on <br> and whitespace, each piece bared — the glyphs an OCR pass stacked or spaced."""
    return [_bare(p) for p in re.split(r"<br\s*/?>|\s+", cell, flags=re.I) if p != ""]


def _letterish(cell: str) -> bool:
    """A rotated letter read on its own: every piece of the cell is ONE glyph once bared (`R`, `l v`, `Ė<br>N`, `6` for C,
    `F.`, `Ϋ́`, `M<br>G<br>M<br>T`) and at least one glyph survives. `PEG`, `P/E` and `Yes` are tokens, never rail letters
    (the Method/Pros/Cons table of Valentine p.3622 was the false positive that drew this line)."""
    ps = _pieces(cell)
    return bool(ps) and all(len(p) <= 1 for p in ps) and any(len(p) == 1 for p in ps)


def read_table(lines: list[str], h: int, d: int, e: int) -> TableReading:
    rows = [cells(lines[k]) for k in range(h, e + 1) if k != d]
    header = rows[0] if rows else []
    delim = cells(lines[d])
    body = rows[1:]
    t = TableReading(first_line=h + 1, last_line=e + 1, rows=len(rows), cols=len(header),
                     delimiter_cols=len(delim), header_delim_agree=len(header) == len(delim),
                     row_cell_counts=[len(r) for r in rows])
    # the title row: ONE filled cell in the first row (a spanning title), or two where one is a chopped fragment of the other
    # (Valentine's "…before meeting management" + "ment"), and the second row filled like a real header (≥ 3 cells, more than
    # the first row's). Two real headings beside an empty corner cell (`| | Lipstick on a Pig | Reputation Builder |`) are a
    # header, not a title.
    filled_first = sorted((c for c in header if c), key=len)
    title_shape = len(filled_first) == 1 or (len(filled_first) == 2 and len(_bare(filled_first[0])) <= 5 and len(filled_first[1]) >= 20)
    if body and title_shape and sum(1 for c in body[0] if c) >= max(3, len(filled_first) + 1):
        t.title_row = True
    t.header_br_cells = sum(1 for c in header if BR.search(c))
    if t.title_row and body:
        t.header_br_cells = max(t.header_br_cells, sum(1 for c in body[0] if BR.search(c)))
    # column 1
    col1 = [r[0] if r else "" for r in body]
    if col1:
        filled = [c for c in col1 if c]
        letterish = [c for c in filled if _letterish(c)]
        empty_share = 1 - len(filled) / len(col1)
        # a rotated rail read letter by letter: at least two letter cells, four in five filled cells letters (an OCR
        # artefact like `_` may sit among them — Valentine's first half of Exhibit 8.2), and either blanks between the
        # runs (the rail spans rows the OCR left empty) or a <br>-stacked letter cell. A column of grades with blanks
        # would pass this signature: the signature names a candidate, the repair's word check must refuse it.
        stacked = any(len(_pieces(c)) >= 2 for c in letterish)
        if len(letterish) >= 2 and len(letterish) >= 0.8 * len(filled) and (empty_share >= 0.3 or stacked):
            t.letter_column = True
        t.letter_column_cells = len(letterish)
        runs, cur = [], []
        for c in col1:
            if c and _letterish(c):
                cur.append(_bare(c))
            elif cur:
                runs.append("".join(cur)); cur = []
        if cur:
            runs.append("".join(cur))
        t.letter_runs = runs
        t.letters_in_order = "".join(runs)
    # the dot matrix
    for r in rows:
        dots = sum(1 for c in r if c == DOT)
        t.dots_per_row.append(dots)
        t.dots_total += dots
        t.stray_dot_glyphs += sum(1 for c in r if c in STRAY_DOTS)
        t.filled_cells += sum(1 for c in r if c)
        t.empty_cells += sum(1 for c in r if not c)
    return t


def census(lines: list[str]) -> list[dict]:
    """One reading per table in the body (as dicts, ready for a CSV or JSON), issues attached by line."""
    issues = health(lines)
    out = []
    for h, d, e in table_blocks(lines):
        t = read_table(lines, h, d, e)
        t.issues = [x for x in issues if h + 1 <= x["line"] <= e + 1]
        out.append(asdict(t))
    return out


def orphan_runs(lines: list[str]) -> list[dict]:
    """Pipe-row runs a renderer will NOT read as a table (no delimiter under the header, a split, a lone row) — the tables the
    census cannot count because they are not tables any more; each with the reason from health()."""
    covered = set()
    for h, d, e in table_blocks(lines):
        covered.update(range(h, e + 1))
    mask = fence_mask(lines)
    out, i, n = [], 0, len(lines)
    while i < n:
        if i in covered or mask[i] or not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        e = i
        while e + 1 < n and not mask[e + 1] and lines[e + 1].lstrip().startswith("|"):
            e += 1
        out.append({"first_line": i + 1, "last_line": e + 1, "rows": e - i + 1})
        i = e + 1
    return out
