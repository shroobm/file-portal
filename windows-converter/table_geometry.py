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
import unicodedata
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
    for ln in lines:
        s = ln.lstrip()
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


def has_pipe(line: str) -> bool:
    return "|" in line.replace("\\|", "")


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


def is_repair_line(line: str) -> bool:
    return line.startswith("![[assets/_repair") or line.startswith("<!-- repair ") or line.startswith("<!-- transcribed ")


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
            row = lines[k]
            if is_repair_line(row) or not has_pipe(row):
                issues.append({"line": k + 1, "reason": "this line touches the table's last row, so a renderer folds it in as a garbled row — put a blank line before it"})
            else:
                c = len(cells(row))
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
    title_fragments: bool = False    # S151 E3: the first row is a spanning title CHOPPED into short cells above the real header
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
    wrapped_labels: list = field(default_factory=list)   # S152 E1: [[line, line+1]] — a row label wrapped over two rows
    title_pieces: bool = False       # S152 E2: the first row is a spanning title chopped into LONG pieces beside empty cells
    index_like: bool = False         # S152 E4: a back-of-book index read as a table (entries ending in page numbers, no headings)


_PAGE_REF = re.compile(r"[A-Za-z].*,\s*\d+(?:\s*[-–]\s*\d+)?\s*$")   # an index entry: words, a comma, a page or a page range


def _index_like(header: list[str], body: list[list[str]]) -> bool:
    """S152 E4 (the panel: p.421 is an index, no table; the copy has two 36-row tables there; the block record calls them Table):
    a text signature for the index — at most three columns, fifteen or more body rows, three in five filled cells an ENTRY
    (words, a comma, a page number or range: `Contact networks, 13`, `IR contacts, 100-102`). A numeric data table's cells
    carry no words before their numbers; a table of prose carries no page numbers. The first cut also asked the header row
    to be entry-shaped and named 6 of the anchor's 18 index tables — the continued heads (`Catalyst (Cont.)`, `Telephone`)
    are not entries; the body's shape is the signature."""
    if not (1 <= len(header) <= 3) or len(body) < 10:   # 10: the anchor's shortest index fragment holds 13 rows
        return False
    cells_ = [c for r in body for c in r if c]
    if not cells_:
        return False
    refs = sum(1 for c in cells_ if _PAGE_REF.search(BR.sub(" ", c).strip()))
    # 0.35, not 0.6 (measured on the anchor's index pages): an index entry wraps onto a second line as often as not (`Index of
    # Leading Economic` / `Indicators, U.S., 327`), so barely half the cells end in a page reference; a numeric table's cells
    # match none (no words before the number) and a prose table's none (no page numbers), so the floor is far above both
    return refs >= 0.35 * len(cells_)


_PIECE_END = re.compile(r"(?:\b[A-Za-z]|-|\b(?:of|and|the|for|to|in|on|or|a|an|by|with|per|from|your))\s*$", re.I)


def _pieces_signal(pieces: list[str]) -> bool:
    """S152 E2: do consecutive pieces read as ONE phrase cut between cells? A piece ending in a lone letter (`…Your I`), a hyphen
    or a preposition, or the next piece starting lowercase, says so; two real headings beside an empty corner (`Lipstick on a
    Pig | Reputation Builder`) show no such signal."""
    ps = [BR.sub(" ", c).strip() for c in pieces]
    for p, q in zip(ps, ps[1:]):
        if not p or not q:
            continue
        if _PIECE_END.search(p) or q[0].islower():
            return True
    return False


_CONT_END = re.compile(r"(?:\(|-|\b(?:of|and|the|for|to|in|on|or|a|an|by|with|per|from))\s*$", re.I)


def _wrapped_pair(a: list[str], b: list[str], ncols: int) -> bool:
    """S152 E1 (the panel's finding on p.204 / p.206): a row label printed on two or three lines arrives as TWO rows — the first
    holding only the label's first line (every data cell empty), the second the label's rest and the data. The second row's
    label must READ as a continuation (a lowercase start or a closing bracket: `index)`, `and Benefits`) or the first must end
    open (a bracket, a hyphen, a preposition); a section row (`II. Buy-Side Only Role` over `Inbound call…`, Title Case, no
    signal) is not a wrap, nor is a label that ends a sentence. The table must hold a label column and at least two data
    columns, and the first line must end in a letter or an open bracket / hyphen: the book's INDEX (two columns of entries
    ending in page numbers, `leading of, 141–143` over `meeting documentation,`) has the shape and is not one — the first dry run
    folded nine index entries into their neighbours and the rule was tightened on that measurement."""
    if ncols < 3 or not a or not b or not a[0] or not b[0]:
        return False
    if any(c for c in a[1:]) or not any(c for c in b[1:]):
        return False
    la, lb = BR.sub(" ", a[0]).strip(), BR.sub(" ", b[0]).strip()
    if not la or not lb or la.endswith((".", ":")):
        return False
    if not (la[-1].isalpha() or la[-1] in "(-["):
        return False
    return lb[0].islower() or lb[0] in ")]" or bool(_CONT_END.search(la))


def _bare(cell: str) -> str:
    """A cell with its <br>, spaces, punctuation and combining marks removed — what an OCR pass left of a letter."""
    s = BR.sub("", cell)
    return "".join(ch for ch in s if ch.isalnum())


def _pieces(cell: str) -> list[str]:
    """The cell split on <br> and whitespace, each piece bared — the glyphs an OCR pass stacked or spaced."""
    return [_bare(p) for p in re.split(r"<br\s*/?>|\s+", cell, flags=re.I) if p != ""]


def _stray_mark(cell: str) -> bool:
    """S154 E6 — a rail-column cell that is a mark and no letter (`_`, `.`, `-`: the OCR's read of a rotated label's stem or
    rule), so nothing survives baring; a label lifted over it clears it. A bullet-shaped glyph is the dots repair's, not this."""
    return bool(cell) and cell not in STRAY_DOTS and cell != DOT and _bare(cell) == ""


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
    # S151 E3: the title chopped into fragments across the header cells (`Start | with th | s sour | ce to ir | …`): three or
    # more filled cells, every one short (eight glyphs or fewer once bared), none a phrase, above a fuller real header
    if (body and not t.title_row and len(filled_first) >= 3 and all(len(_bare(c)) <= 8 for c in filled_first)
            and sum(1 for c in body[0] if c) >= len(filled_first) + 1):
        t.title_fragments = True
    # S152 E2: the title chopped into LONG pieces (p.72: `Quality of Self-Side | Analyst Based on Your I | Prior Experience`
    # beside empty cells, above the real headings) — two or more filled cells, at least one empty, the next row as full or
    # fuller, and a continuation signal across the pieces
    if (body and not t.title_row and not t.title_fragments and len(filled_first) >= 2 and len(filled_first) < len(header)
            and sum(1 for c in body[0] if c) >= max(3, len(filled_first)) and _pieces_signal([c for c in header if c])):
        t.title_pieces = True
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
                runs.append("".join(cur))
                cur = []
        if cur:
            runs.append("".join(cur))
        t.letter_runs = runs
        t.letters_in_order = "".join(runs)
    # S152 E4: an index read as a table (a signature, no repair — the census names it; the layer leaves it alone)
    t.index_like = _index_like(header, body)
    # S152 E1: a row label wrapped over two rows (the pair's 1-based file lines)
    for i in range(len(body) - 1):
        if _wrapped_pair(body[i], body[i + 1], len(header)):
            t.wrapped_labels.append([d + 2 + i, d + 3 + i])
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


# ---- the repair half (S150 E3): the word check, the proposals, the invariant, the pass ---------------------------
#
# The layer proposes a table's shape repairs from the signatures above, applies them on a copy, and keeps the result
# only when `grid_invariant` holds between the table before and after — Rab's law for the class: nothing outside the
# label column changes but a stray bullet glyph, the bullet matrix is the same set of cells, the rows are the same but
# for a title lifted to a caption, and a label must FIT the letters the OCR read. The same invariant is what the
# acceptor (edit_whitelist, rung "table-geometry") applies to a model's edit of a table, so one law guards both roads.

TITLE_MIN = 20          # a spanning title is a phrase (≥ 20 characters with a space); "Significance" above "F" is a stacked heading


def fold_letters(s: str) -> str:
    """Letters as the word check compares them: NFKD with the combining marks dropped, casefolded; a digit or any glyph
    that is not a plain letter becomes the wildcard `?` (an OCR confusion may stand for any letter: `6` for C, `Ϋ́` for Y)."""
    out = []
    for ch in unicodedata.normalize("NFKD", s):
        if unicodedata.combining(ch) or ch.isspace():
            continue  # a two-word label (`COSTS MGMT`, two rails the OCR ran together) compares as its letters
        ch = ch.casefold()
        out.append(ch if "a" <= ch <= "z" else "?")
    return "".join(out)


CONFUSIONS = {"0": "o", "1": "il", "2": "z", "3": "e", "4": "a", "5": "s", "6": "cgb", "7": "t", "8": "b", "9": "g"}


def read_pattern(letters: str) -> list:
    """The letters as the OCR read them, one entry per glyph: a Latin letter → itself; a digit → the letters an OCR pass confuses
    it with (`6` → c, g, b — never any letter, which let MOST fit `6OST` beside COSTS); an accented letter → its base; a glyph
    with no base → None (any letter). Whitespace and combining marks dropped."""
    out = []
    for ch in unicodedata.normalize("NFKD", letters):
        if unicodedata.combining(ch) or ch.isspace():
            continue
        c = ch.casefold()
        if "a" <= c <= "z":
            out.append(c)
        elif c in CONFUSIONS:
            out.append(CONFUSIONS[c])
        else:
            out.append(None)
    return out


def _lcs(a, b: str) -> int:
    """Longest common subsequence of a read pattern (`read_pattern`, or a plain string) against a word; a None entry matches
    any letter, a string entry any of its letters."""
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            hit = ca is None or (cb in ca)
            cur.append(max(prev[j], cur[j - 1], prev[j - 1] + (1 if hit else 0)))
        prev = cur
    return prev[-1]


def collapse_doubles(s: str) -> str:
    """`LLO` read for LOW — a letter the OCR saw twice across a row boundary: adjacent duplicates collapse to one."""
    out = []
    for ch in s:
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def letters_fit(letters: str, word: str) -> tuple[bool, str]:
    """Does the word contain the letters the OCR read, in order, but for ONE confusion and any number of missing letters?
    The check that bounds the resolver: `SARTEGΫ` fits STRATEGY (6 of 7 in order), `HGH` fits HIGH, `LLO` fits LOW,
    `RlvĖNUE` fits REVENUE; `RlvĖNUE` does not fit COSTS."""
    a, b = read_pattern(letters), fold_letters(word)
    if len(b) < 2 or "?" in b:
        return False, "the word is not letters"
    if len(a) < 2:
        return False, "fewer than two letters read"
    if len(b) < len(a) - 1:
        return False, "more letters read (%d) than the word holds (%d)" % (len(a), len(b))
    # S151 E1: a read must hold at least half the word's letters — `UE` is not CAUSE, `lvĖN` is not INVESTMENTS
    if len(a) < (len(b) + 1) // 2:
        return False, "too few letters read (%d) for a word of %d" % (len(a), len(b))
    # S151 E1 (S150's loss: `LABEL` for `LLO` passed as two of three letters in order): a read of three letters or fewer
    # must fit EXACTLY, after the doubled-letter collapse — one confusion is a third of the evidence
    a2 = _collapse_pattern(a)
    need = len(a) if len(a) <= 3 else len(a) - 1
    need2 = len(a2) if len(a2) <= 3 else len(a2) - 1
    # S151 E1 run 3 (Observed): `LLO` read as LOST because "Lost Opportunity" sat in the matrix's rows — a short read (three
    # letters or fewer) may be at most ONE letter short of its word: LOW for `LO`, never LOST
    if len(a) <= 3 and len(b) - len(a) > 1:
        return False, "a short read (%d letters) may be one letter short of its word, not %d" % (len(a), len(b) - len(a))
    k = _lcs(a, b)
    if k >= need:
        return True, "%d of %d letters in order" % (k, len(a))
    if len(a2) != len(a):
        if len(a2) <= 3 and len(b) - len(a2) > 1:
            return False, "a short read (%d letters) may be one letter short of its word, not %d" % (len(a2), len(b) - len(a2))
        k2 = _lcs(a2, b)
        if k2 >= need2:
            return True, "%d of %d letters in order (a doubled letter collapsed)" % (k2, len(a2))
    return False, "%d of %d letters in order" % (k, len(a))


def _collapse_pattern(pat: list) -> list:
    out: list = []
    for p in pat:
        if not out or out[-1] != p:
            out.append(p)
    return out


# ---- the lexicon route (S151 E1): the word must be one the book itself uses ---------------------------------------
#
# S150 E4b measured the word route with a model and the letters-only bound: qwen3:8b returned the letters shuffled (SARTGEY),
# an echo (HGH), or a wrong word the letters admitted (LABEL for LOW) — four labels no better than the garble. The second
# bound: a label must be a word of the book's own prose that fits the letters; with the words per cell known, a run of rails
# the OCR left without a blank row between them (COSTS · MGMT · VALUATION as one run) is split where each word's letters end
# at a cell — the boundary the picture alone was thought to hold.

WORD = re.compile(r"[A-Za-zÀ-ž][A-Za-zÀ-ž'\-]{2,}")


def lexicon(lines: list[str]) -> dict:
    """The book's own words: every alphabetic token of three letters or more (folded, hyphens and apostrophes removed) with
    its count — table cells included, the rail cells excluded by their own length. A label must be one of these."""
    lex: dict = {}
    for ln in lines:
        for m in WORD.finditer(ln):
            w = fold_letters(m.group(0).replace("-", "").replace("'", ""))
            if len(w) >= 3 and "?" not in w:
                lex[w] = lex.get(w, 0) + 1
    return lex


def best_word(letters: str, lex: dict, min_len: int = 3, context=None) -> tuple:
    """(word, why) — the ONE lexicon word the letters fit best, or (None, why). Best = `fit_score` (the letters placed, less
    the read letters unplaced, less half the word's letters missed), plus one point when the word occurs in the rows the
    rail labels (`context`, folded words — a group label echoes its rows' own vocabulary: STRATEGY over STARTED for
    `SARTEGΫ`, whose rows ask how the strategy differs), then the commonest; a tie at the top is refused ("ambiguous")."""
    a = read_pattern(letters)
    if len(a) < 2:
        return None, "fewer than two letters read"
    scored = []
    for w, n in lex.items():
        if len(w) < min_len or len(w) < len(a) - 1 or len(w) > 2 * len(a):
            continue
        ok, why = letters_fit(letters, w)
        if ok:
            k = int(why.split(" of ")[0])
            bonus = 1.0 if (context and w in context) else 0.0
            scored.append((-(fit_score(len(a), k, len(w)) + bonus), -n, w, k))
    if not scored:
        return None, "no word of the book fits %r" % letters
    scored.sort()
    if len(scored) > 1 and abs(scored[0][0] - scored[1][0]) < 0.25:
        return None, "ambiguous: %s and %s fit %r alike" % (scored[0][2], scored[1][2], letters)
    top = scored[0]
    return top[2].upper(), "lexicon (%d of %d letters in order; %d candidate%s)" % (top[3], len(a), len(scored), "" if len(scored) == 1 else "s")


def fit_score(nread: int, placed: int, nword: int) -> float:
    """How well a word explains a read: the letters placed, less the read letters the word cannot place, less half the
    word's letters the OCR would have to have missed. COSTS explains `6OSTs` (5 − 0 − 0 = 5); MANAGEMENT explains `sMGMT`
    poorly (4 − 1 − 3 = 0); VALUATION explains `VAĀON` (5 − 0 − 2 = 3)."""
    return placed - (nread - placed) - (nword - placed) / 2.0


SEGMENT_MIN_SCORE = 1.25   # a word must explain its read this much better than leaving it (MIGHT for `MGMT` scores 1: refused). lever-waiver: Rab's word only; set S151 E1 on Valentine's three rotated rails (the truth's rails column: zero wrong labels at 1.25, MIGHT admitted at 1.0); moves on a re-measured rails column (a right word scoring under it, or a wrong one over it), never by taste


def boundary_collapse(cell_letters: list[str]) -> list[str]:
    """A letter the OCR read twice across a row boundary — `L` on one row, `L O` on the next, for LOW — is one letter: when a
    cell begins with the letter the previous cell ended with, the repeat is dropped (inside a cell nothing is touched)."""
    out: list[str] = []
    for c in cell_letters:
        # plain Latin letters only: `Ā` after `A` is not a repeat (it is TI merged by the OCR in VALUATION), `L` after `L` is
        if (out and c and out[-1] and out[-1][-1].isascii() and out[-1][-1].isalpha() and c[0].isascii() and c[0].isalpha()
                and out[-1][-1].lower() == c[0].lower()):
            c = c[1:]
        out.append(c)
    return out


def _glyphs(letters: str) -> list[str]:
    """The glyphs `read_pattern` keeps, one per pattern entry (NFKD, combining marks and whitespace dropped)."""
    out = []
    for ch in unicodedata.normalize("NFKD", letters):
        if unicodedata.combining(ch) or ch.isspace():
            continue
        out.append(ch)
    return out


GAP_COST = 1.0   # a stream letter no word of the book explains. lever-waiver: Rab's word only; set S151 E1 with SEGMENT_MIN_SCORE on the same three rails (a gap costs one placed letter); moves on a re-measured rails column (letters a word should have taken kept as read, or the reverse), never by taste


def words_from_stream(letters: str, lex: dict, min_len: int = 3, min_count: int = 2) -> tuple:
    """S151 E3: a stream of letters the OCR chopped into fragments (`Startwiththssourcetoirvesticatebeoremetinamanagement1`)
    segmented into the book's words by a dynamic programme over the letter positions — each word fitted by `letters_fit`
    over a stretch of the stream (two letters short to one long), scored by `fit_score`, an unexplained letter costing
    GAP_COST and kept as read; a trailing digit (a footnote mark) is set aside and kept. Only words the book uses at least
    `min_count` times count — the fragments themselves are tokens of the body (`vestic`, `etina`) and must not explain
    themselves. Returns (pieces, explained, total): the words as the lexicon spells them and the gap letters in order;
    explained counts the letters a word explains."""
    tail = ""
    while letters and letters[-1].isdigit():
        tail = letters[-1] + tail
        letters = letters[:-1]
    glyphs = _glyphs(letters)
    pat = read_pattern(letters)
    n = len(pat)
    by_first: dict = {}
    for w, cnt in lex.items():
        if len(w) >= min_len and cnt >= min_count:
            by_first.setdefault(w[0], []).append(w)
    best: list = [None] * (n + 1)   # best[p] = (score, explained, items)
    best[0] = (0.0, 0, [])
    for p in range(n):
        if best[p] is None:
            continue
        s, ex, items = best[p]
        gap = (s - GAP_COST, ex, items + [("g", glyphs[p])])
        if best[p + 1] is None or gap[0] > best[p + 1][0]:
            best[p + 1] = gap
        firsts = pat[p] if isinstance(pat[p], str) else "abcdefghijklmnopqrstuvwxyz"
        for f in set(firsts):
            for w in by_first.get(f, ()):
                for k in range(max(min_len, len(w) - 2), min(n - p, len(w) + 1) + 1):
                    sub = "".join(glyphs[p:p + k])
                    ok, why = letters_fit(sub, w)
                    if not ok:
                        continue
                    placed = int(why.split(" of ")[0])
                    sc = fit_score(k, placed, len(w))
                    if sc < SEGMENT_MIN_SCORE:
                        continue
                    cand = (s + sc, ex + k, items + [("w", w)])
                    if best[p + k] is None or cand[0] > best[p + k][0]:
                        best[p + k] = cand
    if best[n] is None:
        return ([tail] if tail else []), 0, n + len(tail)
    pieces: list = []
    for kind, val in best[n][2]:
        if kind == "w":
            pieces.append(val)
        elif pieces and isinstance(pieces[-1], list):
            pieces[-1].append(val)
        else:
            pieces.append([val])
    out = ["".join(x) if isinstance(x, list) else x for x in pieces]
    if tail:
        out.append(tail)
    return out, best[n][1], n + len(tail)


def phrases(lines: list[str]) -> list[str]:
    """The book's own phrases a chopped title could be: every table cell of twenty characters or more and every heading line —
    a continued exhibit repeats its title, and the repeat is the best reading of the fragments."""
    out: dict = {}
    mask = fence_mask(lines)
    for k, ln in enumerate(lines):
        if mask[k]:
            continue
        s = ln.strip()
        if s.startswith("#") and len(s.lstrip("# ")) >= 20:
            out[s.lstrip("# ").strip()] = 1
        elif has_pipe(ln) and not DELIM.match(ln):
            # every pipe row, a table's or an orphan's (the held copy's continued half is the S149 split: its title row is an
            # orphan pipe row, and it is the phrase the first half's fragments need)
            for c in cells(ln):
                c = BR.sub(" ", c).strip()
                if len(c) >= 20:
                    out[c] = 1
    return list(out)


def best_phrase(stream: str, candidates: list[str], floor: float = 0.85) -> tuple:
    """(phrase, why) — the ONE phrase of the book whose letters the fragment stream holds in order, `floor` of both lengths at
    least (the confusions a chopped title carries — `th s` for this, `ir vestic ate` for investigate — are few against fifty
    letters); a second phrase within two letters of the best is a tie, refused."""
    pat = read_pattern(stream)
    if len(pat) < 12:
        return None, "the stream is too short for a phrase (%d letters)" % len(pat)
    scored = []
    for ph in candidates:
        b = fold_letters(ph)
        if not b or abs(len(b) - len(pat)) > 0.35 * len(pat):
            continue
        k = _lcs(pat, b)
        if k >= floor * len(pat) and k >= floor * len(b):
            scored.append((k, ph))
    if not scored:
        return None, "no phrase of the book holds the fragments' letters (%d) in order" % len(pat)
    scored.sort(reverse=True)
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 2 and fold_letters(scored[0][1]) != fold_letters(scored[1][1]):
        return None, "ambiguous: two phrases of the book fit the fragments alike"
    k, ph = scored[0]
    return ph, "the book's own phrase (%d of %d letters in order)" % (k, len(pat))


def lexicon_segments(cell_letters: list[str], lex: dict, context=None) -> list:
    """A run of letter cells (their bared letters, one entry per cell, in row order) segmented into lexicon words: a list of
    (first_cell, last_cell, WORD, why) covering a prefix-free choice of cells; cells no word covers are left out (reported
    unresolved by the caller). Dynamic programming over the cell boundaries maximising the words' `fit_score` (an uncovered
    cell scores 0, a segment under SEGMENT_MIN_SCORE is refused), then the fewest words; a fragment under three letters is
    no evidence unless it is the whole run."""
    cell_letters = boundary_collapse(cell_letters)
    n = len(cell_letters)
    best: list = [None] * (n + 1)   # best[i] = (score, -words, segments) for cells[:i]; an uncovered cell scores 0
    best[0] = (0.0, 0, [])
    whole = len(read_pattern("".join(cell_letters)))
    for i in range(1, n + 1):
        cand = None
        if best[i - 1] is not None:      # leave cell i-1 uncovered
            s, w, segs = best[i - 1]
            cand = (s, w, segs)
        for j in range(0, i):
            if best[j] is None:
                continue
            letters = "".join(cell_letters[j:i])
            nread = len(read_pattern(letters))
            if nread < 3 and nread < whole:   # a fragment under three letters is no evidence unless it is the whole run (LLO, LO)
                continue
            word, why = best_word(letters, lex, context=context)
            if not word:
                continue
            placed = int(why.split("(")[1].split(" of ")[0])
            # the rows' vocabulary chooses BETWEEN words for the same cells (best_word); it never inflates a segment's own
            # score — run 4 (Observed): COST + SEGMENTS, each with a bonus, outscored COSTS over the same cells
            score = fit_score(nread, placed, len(fold_letters(word)))
            if score < SEGMENT_MIN_SCORE:   # a word that explains the read no better than leaving it alone
                continue
            s, w, segs = best[j]
            # S151 E1 run 3 (Observed): COST + SEGMENTS (4 + 2) outscored COSTS (5) over the same cells — a segmentation is
            # scored by each word's EXCESS over the bar, so two weak words never beat one strong one
            trial = (s + (score - SEGMENT_MIN_SCORE), w - 1, segs + [(j, i - 1, word, why)])
            if cand is None or trial[:2] > cand[:2]:
                cand = trial
        best[i] = cand
    return best[n][2] if best[n] else []


def _fragment_of(long: str, frag: str) -> bool:
    """`ment` beside `…before meeting management`: a chopped tail of the title, read twice."""
    f = _bare(frag).lower()
    return bool(f) and len(f) <= 5 and _bare(long).lower().endswith(f)


def _fold_text(t: str) -> str:
    """Lower-cased, whitespace-collapsed text for the reading's anchors and fragments."""
    return " ".join(t.lower().split())


def _vision_entry(lines: list[str], h: int, e: int, vision: dict | None):
    """S156 E1 — the reading's entry for this table block: the one whose every `anchor` snippet appears in the block's own
    text (case-folded, whitespace-collapsed) — never a line number, which the copy does not keep. None when no entry matches;
    the first match when several do (the writer keeps anchors distinctive)."""
    if not vision:
        return None
    blob = _fold_text(" ".join(lines[h:e + 1]))
    for entry in vision.get("tables", []):
        anchors = entry.get("anchor") or []
        if anchors and all(_fold_text(a) in blob for a in anchors):
            return entry
    return None


def _index_run(lines: list[str], h: int, r: list[int], cell_letters: list[str]) -> str | None:
    """S157 E15 — a letter run that is NOT a rotated label, said before any word is sought (Ashby's transition matrices:
    the row labels `3 4 5 6` read as ELASTIC through the glyph readings that rescue `6OSTs` → COSTS; `a<br>b` / `c` beside
    `α<br>β` / `γ` read as ABC). Returns the reason, or None when the run may be a rail.
    R1 more than half the glyphs are digits — numbers, not a rotated word (one digit in five, `6OSTs`, stays a rail);
    R2 every glyph is one of the table's own column headings — a matrix index (rows 3..6 under headings 3..6);
    R3 a stacked letter cell whose row's other cells are stacked to the same depth — merged rows, not a rail."""
    glyphs = "".join(_bare(c) for c in cell_letters)   # bared: spaces and <br> are not glyphs (the first cut counted a space and let 4 / D 5 through as ADDS)
    if glyphs:
        digits = sum(1 for ch in glyphs if ch.isdigit())
        if 2 * digits > len(glyphs):
            return "not a rotated word: %d of %d glyphs are digits" % (digits, len(glyphs))
    heads = {fold_letters(_bare(c)) for c in cells(lines[h])[1:] if _bare(c).strip()}
    pieces = [fold_letters(p) for c in cell_letters for p in (_pieces(c) or [c]) if p.strip()]
    if heads and pieces and all(p in heads for p in pieces):
        return "the run's glyphs are the table's own column headings (a matrix index)"
    # R3 counts <br> STACKING only (a prose cell's words are not pieces of a stack): every other filled cell of the row
    # stacked to the same depth, each of its parts short — a matrix's entries (`α<br>β`, `0.<br>4`), never wrapped prose
    def stack(cell):
        return [p.strip() for p in re.split(r"<br\s*/?>", cell, flags=re.I) if p.strip()]
    for k in r:
        cs = cells(lines[k])
        depth = len(stack(cs[0])) if cs else 0
        others = [stack(c) for c in cs[1:] if c.strip()]
        if depth >= 2 and others and all(len(o) == depth and all(len(p) <= 12 for p in o) for o in others):
            return "the row is stacked alike across every column (%d pieces): merged rows, not a rail" % depth
    return None


def _tile_spans(rails: list[dict], first_row: int, last_row: int) -> None:
    """S154 E6 — a rotated label is printed to begin at its GROUP's first row, not at the row the OCR put its first letter
    (Valentine p.108: REVENUE's letters sit on rows 2–5 of a group that begins at row 1; the scorer's placement measure read
    2 of 7 labels on their first row). The labels' spans tile the body rows in order: the first from the first body row, the
    last to the last, each group centred on its letters (the first cut split the blank rows between two runs at their midpoint
    and placed FINANCIAL a row early on p.107 — the scorer read it absent; measured into this shape). A run's letter rows never move. Sets p["span"] = [first, last] (1-based lines, like
    p["rows"]) on every rail proposal, resolved or not — an unresolved run still bounds its neighbours."""
    rs = sorted(rails, key=lambda p: p["rows"][0])
    for k, p in enumerate(rs):
        a, b = p["rows"]
        start = min(first_row if k == 0 else rs[k - 1]["span"][1] + 1, a)
        if k + 1 < len(rs):
            # a rotated label is printed CENTRED in its group (Valentine pp.107–108, every span read by the S154 panel):
            # the group runs below the letters by as much as it runs above them, never past the next run's first letter
            end = min(max(b + (a - start), b), rs[k + 1]["rows"][0] - 1)
        else:
            end = last_row
        p["span"] = [start, max(end, b)]


def propose(lines: list[str], resolver=None, lex: dict | None = None, vision: dict | None = None, notes: dict | None = None) -> list[dict]:
    """The shape repairs a table asks for, table by table, without touching a byte: a `caption` (a spanning title lifted
    above the table), a `rail` per letter run (the letters → the word the resolver gives, placed on the run's first row),
    a `dots` fix (stray bullet glyphs → `•` inside a table that has a bullet matrix). A table with a health issue is never
    proposed for. The word route (S151 E1): with a `lex` (the book's own words, `lexicon(lines)`) a run is segmented into
    lexicon words at cell boundaries — one `rail` proposal per word, `how` = "lexicon (…)" — and the cells no word covers
    stay as they are, reported; `resolver(letters, context) -> word | None` (the model) is asked only for what the lexicon
    left, and its answer must itself be a word of the lexicon that fits. Without either, every rail is reported unresolved.
    Every rail proposal carries its letters, its word and how it was resolved, so the record can list every label."""
    issue_lines = {x["line"] for x in health(lines)}
    out = []
    phrase_list = phrases(lines) if lex is not None else None
    for h, d, e in table_blocks(lines):
        if any(h + 1 <= ln <= e + 1 for ln in issue_lines):
            continue
        t = read_table(lines, h, d, e)
        header = cells(lines[h])
        if t.title_row:
            filled = sorted((c for c in header if c), key=len)
            long = filled[-1]
            if len(long) >= TITLE_MIN and " " in long:
                frag = filled[0] if len(filled) == 2 else ""
                dropped = bool(frag) and _fragment_of(long, frag)
                out.append({"kind": "caption", "table": [h + 1, e + 1], "line": h + 1,
                            "text": long if (not frag or dropped) else long + " " + frag, "fragment_dropped": dropped})
        elif t.title_fragments and lex is not None:
            # S151 E3: the fragments joined into one letter stream. Three readings in order of trust: (1) a phrase of the book
            # itself (a continued exhibit repeats its title) holding the letters in order; (2) the book's words read along the
            # stream, only when they explain seven letters in ten, three words or more, averaging five letters — a soup of short
            # words ("thesis our ceo ive") is refused; (3) the fragments joined as read — the header freed, the text left as the
            # OCR left it and said so. A row of short real headings (`Df | SS | MS | F`) reads as nothing and stays a header.
            frags = [c for c in header if c]
            stream = "".join(_bare(c) for c in frags)
            raw = " ".join(frags)
            # a stacked column heading (`Standard | 1 | P- | Lower | Upper` over `Error | t Stat | value | 95% | 95%`) has the same
            # shape, and its cells are WORDS the book uses elsewhere; a chopped title's cells mostly are not (`th`, `sour`, `ce`,
            # `ir`, `vesti`). Half or more of the three-letter cells being words the book uses twice → headings, no caption.
            longish = [fold_letters(_bare(c)) for c in frags if len(_bare(c)) >= 3]
            selfwords = sum(1 for w in longish if lex.get(w, 0) >= 2)
            headings = bool(longish) and 2 * selfwords >= len(longish)
            # S152 E1: the guard refuses the CAPTION only — the table's other proposals (a fold, a rail, the dots) still stand;
            # the first cut said `continue` here and a regression table lost its wrapped-label fold to it
            ph, why = (None, "a stacked heading, not a title") if headings else best_phrase(stream, phrase_list if phrase_list is not None else [])
            if headings:
                text = None
                # S152 E3: a stacked column heading — the header row and the first body row folded into ONE heading row by the
                # page's typography (`Standard` + `Error`, `P-` + `value`, `Lower` + `95%`); the invariant's header-fold clause
                out.append({"kind": "fold", "table": [h + 1, e + 1], "rows": [h + 1, d + 2], "header": True,
                            "why": "a stacked heading: %s over %s" % (" | ".join(frags)[:60], " | ".join(c for c in cells(lines[d + 1]) if c)[:60])})
            elif ph:
                text, how = ph, why
            else:
                pieces, explained, total = words_from_stream(stream, lex)
                words = [p for p in pieces if p in lex]
                if total and explained >= 0.7 * total and len(words) >= 3 and sum(len(w) for w in words) / len(words) >= 5:
                    text = " ".join(pieces)
                    text, how = text[0].upper() + text[1:], "the book's words along the stream (%d of %d letters explained)" % (explained, total)
                elif len(_bare(stream)) >= 20:
                    text, how = raw, "the fragments joined as read — no phrase or words of the book explain them (%s)" % why
                else:
                    text = None
            if text:
                out.append({"kind": "caption", "table": [h + 1, e + 1], "line": h + 1, "text": text, "fragment_dropped": False,
                            "fragments_joined": True, "raw": raw, "how": how})
        elif t.title_pieces and lex is not None:
            # S152 E2: the pieces of a chopped caption — a single-word piece the book uses twice is a heading (the guard as E3's);
            # the book's own phrase first, else the pieces joined as read (they are words already, so the join is the caption)
            pieces = [c for c in header if c]
            single = [fold_letters(_bare(c)) for c in pieces if " " not in BR.sub(" ", c).strip() and len(_bare(c)) >= 3]
            selfwords = sum(1 for w in single if lex.get(w, 0) >= 2)
            if not (single and 2 * selfwords >= len(single)):
                stream = "".join(_bare(c) for c in pieces)
                raw = " ".join(BR.sub(" ", c).strip() for c in pieces)
                ph, why = best_phrase(stream, phrase_list if phrase_list is not None else [])
                if ph:
                    text, how = ph, why
                elif sum(1 for c in pieces if " " in BR.sub(" ", c).strip()) >= 2:
                    text, how = raw, "the pieces joined as read — a caption chopped into cells (%s)" % why
                else:
                    text = None
                if text:
                    out.append({"kind": "caption", "table": [h + 1, e + 1], "line": h + 1, "text": text, "fragment_dropped": False,
                                "fragments_joined": True, "raw": raw, "how": how})
        for pair in t.wrapped_labels:
            # S152 E1: the two rows folded into one — the label joined with a space, the data the second row's
            out.append({"kind": "fold", "table": [h + 1, e + 1], "rows": list(pair),
                        "why": "a wrapped row label: %r + %r" % (cells(lines[pair[0] - 1])[0][:40], cells(lines[pair[1] - 1])[0][:40])})
        rails: list = []
        has_cap = any(p["kind"] == "caption" and p["table"] == [h + 1, e + 1] for p in out)   # by the title row OR the pieces route
        if t.letter_column:
            runs, run = [], []
            for k in range(d + 1, e + 1):
                c = cells(lines[k])
                if c and c[0] and _letterish(c[0]):
                    run.append(k)
                elif run:
                    runs.append(run)
                    run = []
            if run:
                runs.append(run)
            prev_end = d
            for r in runs:
                cell_letters = [_bare(cells(lines[k])[0]) for k in r]
                letters = "".join(cell_letters)
                context = [(cells(lines[k])[1] if len(cells(lines[k])[1:]) else "") for k in r[:3]]
                # S157 E15: a run that is an INDEX, not a rail — refused before any word is sought, on the record
                index_why = _index_run(lines, h, r, [cells(lines[k])[0] for k in r])
                if index_why is not None:
                    rails.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[0] + 1, r[-1] + 1], "letters": letters,
                                  "word": None, "how": "unresolved", "refused": index_why})
                    prev_end = r[-1]
                    continue
                if lex is not None:
                    # the group's own words (every cell but the rail's, on the rows from the previous run's end to this run's
                    # end — a rotated label starts above its first letter cell): a group label echoes its rows' vocabulary
                    ctx_words = set()
                    for k in range(prev_end + 1, r[-1] + 1):
                        for c in cells(lines[k])[1:]:
                            ctx_words.update(fold_letters(m.group(0)) for m in WORD.finditer(c))
                    prev_end = r[-1]
                    segs = lexicon_segments(cell_letters, lex, ctx_words)
                    covered = set()
                    for c0, c1, word, why in segs:
                        covered.update(range(c0, c1 + 1))
                        rails.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[c0] + 1, r[c1] + 1],
                                      "letters": "".join(cell_letters[c0:c1 + 1]), "word": word, "how": why, "refused": None})
                    left = [i for i in range(len(r)) if i not in covered]
                    if not left:
                        continue
                    # the cells no lexicon word covers: one unresolved proposal per maximal stretch (the model may be asked)
                    stretches, cur = [], []
                    for i in left:
                        if cur and i != cur[-1] + 1:
                            stretches.append(cur)
                            cur = []
                        cur.append(i)
                    if cur:
                        stretches.append(cur)
                    for st in stretches:
                        lt = "".join(cell_letters[st[0]:st[-1] + 1])
                        word, how = None, "unresolved"
                        refused = best_word(lt, lex, context=ctx_words)[1] if len(fold_letters(lt)) >= 2 else "fewer than two letters read"
                        if not refused.startswith(("ambiguous", "no word", "fewer")):
                            refused = "the word the lexicon offers explains the read no better than leaving it (%s)" % refused
                        if resolver is not None and len(fold_letters(lt)) >= 2:
                            got = resolver(lt, [(cells(lines[r[i]])[1] if len(cells(lines[r[i]])) > 1 else "") for i in st[:3]])
                            if got and all(fold_letters(g) in lex for g in got.split()):
                                ok, why = letters_fit(lt, got)
                                if ok:
                                    word, how, refused = got, "resolver, a word of the book (%s)" % why, None
                                else:
                                    refused = "the word %r does not fit the letters %r: %s" % (got, lt, why)
                            elif got:
                                refused = "the word %r is not a word of the book" % got
                        rails.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[st[0]] + 1, r[st[-1]] + 1],
                                      "letters": lt, "word": word, "how": how, "refused": refused})
                    continue
                word, how, refused = None, "unresolved", None
                if len(letters) < 2:
                    refused = "fewer than two letters"
                elif resolver is None:
                    refused = "no resolver"
                else:
                    got = resolver(letters, context)
                    if not got:
                        refused = "the resolver gave no word"
                    else:
                        ok, why = letters_fit(letters, got)
                        if ok:
                            word, how = got, "resolver (%s)" % why
                        else:
                            refused = "the word %r does not fit the letters %r: %s" % (got, letters, why)
                rails.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[0] + 1, r[-1] + 1], "letters": letters,
                              "word": word, "how": how, "refused": refused})
            # S154 E6: the spans, 1-based lines — the body runs from d+1 (0-based) to e; under a title row the real header sits
            # at d+1 and the body begins at d+2 (the first cut lifted REVENUE onto the header row: the selftest caught it)
            _tile_spans(rails, d + 2 + (1 if has_cap else 0), e + 1)
        entry = _vision_entry(lines, h, e, vision)
        if entry is not None and notes is not None:
            notes.setdefault("matched", []).append({"table": [h + 1, e + 1], "kind": entry.get("kind", "table")})
        if entry is not None and entry.get("kind", "table") == "table" and entry.get("rails"):
            # S156 E1 — the reading of the page lends a rail its WORD (where the lexicon and the resolver did not decide) and
            # its SPAN (the reading's rows, 1-based body rows under the real header, mapped onto the copy's rows); a rail the
            # reading names with no letter run beneath is proposed from its FRAGMENTS when every rail cell on those rows is a
            # substring of the label. Every claim still goes through the invariant.
            first_body = d + 1 + (1 if has_cap else 0)
            for vr in entry["rails"]:
                word = str(vr.get("word", "")).strip()
                rows = vr.get("rows") or []
                if not word or len(rows) != 2:
                    continue
                l0, l1 = first_body + int(rows[0]) - 1, first_body + int(rows[1]) - 1
                if l0 < first_body or l1 > e or l0 > l1:
                    if notes is not None:
                        notes.setdefault("unmatched", []).append({"table": [h + 1, e + 1], "word": word, "why": "rows outside the copy's body"})
                    continue
                hit = None
                for p in rails:
                    if letters_fit(p["letters"], word)[0] and (p["word"] is None or fold_letters(p["word"]) == fold_letters(word)):
                        hit = p
                        break
                if hit is None:
                    # S156 E5: every unresolved run overlapping the reading's rows is tried (the first cut stopped at the first)
                    for p in rails:
                        if p["word"] is None and not (p["rows"][1] < l0 + 1 or p["rows"][0] > l1 + 1) and letters_fit(p["letters"], word)[0]:
                            hit = p
                            break
                if hit is not None:
                    if hit["word"] is None:
                        hit["word"], hit["how"], hit["refused"] = word, "vision (a reading of the page; the letters fit)", None
                        if notes is not None:
                            notes["words"] = notes.get("words", 0) + 1
                    hit["span"] = [l0 + 1, l1 + 1]
                    hit["span_how"] = "vision"
                    if notes is not None:
                        notes["spans"] = notes.get("spans", 0) + 1
                    continue
                frags = [(k, _bare(cells(lines[k])[0]) and cells(lines[k])[0]) for k in range(l0, l1 + 1) if cells(lines[k]) and cells(lines[k])[0]]
                frags = [(k, c) for k, c in frags if c]
                label = _fold_text(word)
                if frags and all(not _letterish(c) and _fold_text(c) in label for _, c in frags):
                    rails.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [frags[0][0] + 1, frags[-1][0] + 1],
                                  "letters": " / ".join(c for _, c in frags), "word": word, "how": "vision (fragments of the label)",
                                  "refused": None, "span": [l0 + 1, l1 + 1], "span_how": "vision", "fragments": len(frags)})
                    if notes is not None:
                        notes["fragment_rails"] = notes.get("fragment_rails", 0) + 1
                elif notes is not None:
                    notes.setdefault("unmatched", []).append({"table": [h + 1, e + 1], "word": word, "why": "no letter run fits it and its rows are not fragments of it"})
        out.extend(rails)
        if t.dots_total and t.stray_dot_glyphs:
            out.append({"kind": "dots", "table": [h + 1, e + 1], "cells": t.stray_dot_glyphs})
    if vision:
        # S156 E1 — a table the reading calls a FIGURE gets no repair at all (its rotated axis labels are not rails)
        figures = set()
        for h, d, e in table_blocks(lines):
            entry = _vision_entry(lines, h, e, vision)
            if entry is not None and entry.get("kind") == "figure":
                figures.add((h + 1, e + 1))
        if figures:
            if notes is not None:
                notes["figures"] = [list(x) for x in sorted(figures)]
            out = [p for p in out if tuple(p["table"]) not in figures]
    return out


def _render_row(cs: list[str]) -> str:
    return "| " + " | ".join(c if "`" in c else c.replace("|", "\\|") for c in cs) + " |"


def _join_rows(a: list[str], b: list[str]) -> list[str]:
    """Two rows joined column by column: an empty side yields the other; two filled cells join with one space."""
    n = max(len(a), len(b))
    a = list(a) + [""] * (n - len(a))
    b = list(b) + [""] * (n - len(b))
    return [(x if not y else (y if not x else x + " " + y)) for x, y in zip(a, b)]


def _join_heading(a: list[str], b: list[str]) -> list[str]:
    """S152 E3: a STACKED column heading's two rows joined into one heading per column, by the page's own typography: an
    upper piece ending in a hyphen joins without a space (`P-` + `value` → `P-value`); an upper piece with no letter (`1`, the
    OCR's echo of the `t` the lower piece already carries in `t Stat`) above a lower piece of two or more words is dropped;
    otherwise one space (`Standard` + `Error`, `Lower` + `95%`)."""
    n = max(len(a), len(b))
    a = list(a) + [""] * (n - len(a))
    b = list(b) + [""] * (n - len(b))
    out = []
    for x, y in zip(a, b):
        xs, ys = BR.sub(" ", x).strip(), BR.sub(" ", y).strip()
        if not xs or not ys:
            out.append(x if not y else y if not x else x + " " + y)
        elif xs.endswith("-"):
            out.append(xs + ys)
        elif not any(ch.isalpha() for ch in xs) and len(ys.split()) >= 2:
            out.append(y)
        else:
            out.append(x + " " + y)
    return out


def _fold_allowed(a: list[str], b: list[str], header: bool) -> tuple[bool, str]:
    """A body fold may join only where at most one side is filled outside column 1 (a wrapped label carries no data of its
    own); a fold of the HEADER row with the first body row (S152 E3, a stacked heading) may join filled cells."""
    if header:
        # S186 E1 (SYM-134): a stacked heading's lower row carries WORDS (`Error` under `Standard`, `95%` under `Lower`); a lower
        # row whose filled cells outside column 1 are ALL numbers is the first DATA row — the model fused Table 10-2's header
        # (`a | explain | …`) with `d1 | 1 | 0 | …` into `d1 | a 1 | explain 0 | …` and this rule admitted it as a heading, so the
        # rung built to protect tables shipped a corrupted one that the plain acceptor would have reverted (held DSB, 2026-09-17).
        filled = [x for x in b[1:] if x and x.strip()]
        if filled and all(_is_num(x) for x in filled):
            return False, "the lower row is data (every filled cell outside column 1 is a number) — not a stacked heading (SYM-134)"
        return True, "a header fold"
    for j in range(1, max(len(a), len(b))):
        x = a[j] if j < len(a) else ""
        y = b[j] if j < len(b) else ""
        if x and y:
            return False, "column %d is filled on both rows (%r / %r) — not a wrapped label" % (j + 1, x[:20], y[:20])
    return True, "a wrapped label"


def apply_table(lines: list[str], h: int, d: int, e: int, props: list[dict]) -> list[str]:
    """The table's lines (h..e, 0-based) with the given proposals applied; an unchanged row keeps its bytes."""
    grid = {k: cells(lines[k]) for k in range(h, e + 1) if k != d}
    before = {k: list(v) for k, v in grid.items()}
    caption = None
    dropped: set = set()
    # S154 E6: a lifted label never lands on the header row — nor on the row that becomes the header under a caption
    floor = d + 2 if any(p["kind"] == "caption" for p in props) else d + 1
    for p in props:
        if p["kind"] == "fold":
            r0, r1 = p["rows"][0] - 1, p["rows"][1] - 1
            if r0 in grid and r1 in grid and r1 not in dropped:
                grid[r0] = _join_heading(grid[r0], grid[r1]) if r0 == h else _join_rows(grid[r0], grid[r1])
                dropped.add(r1)
        elif p["kind"] == "rail" and p.get("word"):
            r0, r1 = p["rows"][0] - 1, p["rows"][1] - 1
            s0 = p["span"][0] - 1 if p.get("span") else r0   # S154 E6: the group's first row, when the rail is blank down to the run
            s0 = max(s0, floor)
            if s0 < r0 and not all(grid.get(k) and (grid[k][0] == "" or _stray_mark(grid[k][0])) for k in range(s0, r0)):
                s0 = r0
            if r0 in grid and r1 in grid and grid[r0] and s0 in grid and grid[s0]:
                grid[s0][0] = p["word"]
                for k in range(s0 + 1, r1 + 1):
                    if grid.get(k):
                        grid[k][0] = ""
                p["placed"] = s0 + 1
        elif p["kind"] == "dots":
            for cs in grid.values():
                for j, c in enumerate(cs):
                    if c in STRAY_DOTS:
                        cs[j] = DOT
        elif p["kind"] == "caption":
            caption = p
    out = []
    order = list(range(h, e + 1))
    if caption and d + 1 <= e:
        # the title row goes; the second row becomes the header, so the delimiter row moves under it
        out.append(caption["text"])
        out.append("")
        order = [d + 1, d] + list(range(d + 2, e + 1))
    for k in order:
        if k in dropped:
            continue
        if k == d or grid[k] == before[k]:
            out.append(lines[k])
        else:
            out.append(_render_row(grid[k]))
    return out


def grid_invariant(before: list[str], after: list[str]) -> tuple[bool, list[str], dict]:
    """The class's law, checked on ONE table (its lines before and after; `after` may carry a caption above the table):
    one table on both sides; the same columns; the same rows but for a title row lifted to a caption whose text is above
    the table; every cell outside column 1 byte-identical, or a stray bullet glyph become `•`; column 1 changed only
    where a run of letter cells became one label on the run's first row with blanks under it, the label fitting the
    letters. Returns (ok, reasons, facts) — facts name what was compared, fixed and labelled."""
    reasons: list[str] = []
    facts: dict = {"cells_compared": 0, "dots_fixed": 0, "labels": [], "caption": None, "caption_lines": 0}
    tb, ta = table_blocks(before), table_blocks(after)
    if len(tb) != 1 or len(ta) != 1:
        return False, ["tables before %d, after %d — must be one and one" % (len(tb), len(ta))], facts
    (hb, db, eb), (ha, da, ea) = tb[0], ta[0]
    if before[db].strip() != after[da].strip():
        reasons.append("the delimiter row changed")
    rb = [cells(before[k]) for k in range(hb, eb + 1) if k != db]
    ra = [cells(after[k]) for k in range(ha, ea + 1) if k != da]
    lifted = 0
    if len(ra) < len(rb) and ha > 0:
        filled = sorted((c for c in rb[0] if c), key=len)
        above_raw = "".join(x for x in after[:ha])
        above = "".join(_bare(x) for x in after[:ha]).lower()
        frag_stream = "".join(_bare(c) for c in rb[0] if c)
        frag_pat = read_pattern(frag_stream)
        # a spanning title lifted whole (its bared text is above), or fragments joined and read as words (S151 E3: the letters
        # the fragments hold are found in order, four in five, in the caption above)
        if filled and len(filled) <= 2 and _bare(filled[-1]).lower() and _bare(filled[-1]).lower() in above:
            lifted = 1
            facts["caption"] = filled[-1]
            facts["caption_lines"] = ha
        elif filled and len(filled) >= 3 and frag_pat and _lcs(frag_pat, fold_letters(above_raw)) >= 0.8 * len(frag_pat):
            lifted = 1
            facts["caption"] = " ".join(c for c in rb[0] if c)
            facts["caption_lines"] = ha
    # S152 E1: the rows still missing after a lift must be FOLDS — an after row equal to the exact column-by-column join of
    # two adjacent before rows (nothing else may change in a fold; a body fold joins only where one side is empty, a
    # header fold — the header row with the first body row — may join filled cells: the stacked heading)
    rb2 = rb[lifted:]
    facts["folds"] = []
    if len(rb2) > len(ra):
        merged: list = []
        i = j = 0
        while i < len(rb2):
            is_header = i == 0 and lifted == 0
            if (j < len(ra) and i + 1 < len(rb2) and len(rb2) - i > len(ra) - j and rb2[i] != ra[j]
                    and (_join_rows(rb2[i], rb2[i + 1]) == ra[j] or (is_header and _join_heading(rb2[i], rb2[i + 1]) == ra[j]))):
                ok_fold, why = _fold_allowed(rb2[i], rb2[i + 1], header=is_header)
                if ok_fold:
                    facts["folds"].append({"rows": [i + 1 + lifted, i + 2 + lifted], "label": (ra[j][0] if ra[j] else "")[:40], "how": why})
                    merged.append(ra[j])
                    i += 2
                    j += 1
                    continue
                reasons.append("rows %d-%d folded but not admitted: %s" % (i + 1 + lifted, i + 2 + lifted, why))
            merged.append(rb2[i])
            i += 1
            j += 1
        rb2 = merged
    if len(rb2) != len(ra):
        if lifted == 0 and len(ra) < len(rb):
            reasons.append("a row was dropped (rows before %d, after %d) and no caption above carries the first row's text, no fold explains it" % (len(rb), len(ra)))
        else:
            reasons.append("rows before %d, after %d (lifted %d, folds %d)" % (len(rb), len(ra), lifted, len(facts["folds"])))
    n = min(len(ra), len(rb2))
    # every cell outside column 1, every row (a rail's rows included — the first version of this loop jumped over
    # them with the rail and compared 60 of 120 cells: the selftest's own negatives caught it)
    for i in range(n):
        b, a = rb2[i], ra[i]
        if len(a) != len(b):
            reasons.append("row %d has %d cells before and %d after" % (i + 1, len(b), len(a)))
            continue
        for j in range(1, len(b)):
            facts["cells_compared"] += 1
            if a[j] == b[j]:
                continue
            if b[j] in STRAY_DOTS and a[j] == DOT:
                facts["dots_fixed"] += 1
                continue
            reasons.append("row %d cell %d changed: %r -> %r" % (i + 1, j + 1, b[j][:40], a[j][:40]))
    # column 1: identical, a stray dot fixed, or a letter run become one label with blanks under it
    i = 0
    while i < n:
        b, a = rb2[i], ra[i]
        b1, a1 = (b[0] if b else ""), (a[0] if a else "")
        if b1 == a1:
            i += 1
            continue
        if b1 in STRAY_DOTS and a1 == DOT:
            facts["dots_fixed"] += 1
            i += 1
            continue
        if (b1 == "" or _stray_mark(b1)) and a1:
            # S154 E6: a label LIFTED onto the blank rows above its letter run (the group's first row): admitted only when
            # every row between is blank (or a stray mark, cleared) before and blank after, the run's letters fit the word,
            # and the run's cells are blank after
            if i == 0:
                reasons.append("column 1 row 1: %r placed on the header row" % a1[:40])
                i += 1
                continue
            m = i + 1
            strays = 1 if _stray_mark(b1) else 0
            while m < n and ((rb2[m][0] if rb2[m] else "") == "" or _stray_mark(rb2[m][0])) and (ra[m][0] if ra[m] else "") == "":
                strays += 1 if _stray_mark(rb2[m][0]) else 0
                m += 1
            if m < n and rb2[m] and rb2[m][0] and _letterish(rb2[m][0]) and ra[m] and ra[m][0] == "":
                k, letters = m, []
                while k < n and rb2[k] and rb2[k][0] and _letterish(rb2[k][0]) and ra[k] and ra[k][0] == "":
                    letters.append(_bare(rb2[k][0]))
                    k += 1
                ok, why = letters_fit("".join(letters), a1)
                if ok:
                    facts["labels"].append({"row": i + 1, "letters": "".join(letters), "word": a1, "fit": why, "lifted": m - i, "strays_cleared": strays})
                else:
                    reasons.append("column 1 rows %d-%d: the lifted label %r does not fit the letters %r (%s)" % (i + 1, k, a1[:40], "".join(letters), why))
                i = k
                continue
            reasons.append("column 1 row %d: %r placed on a blank row with no letter run beneath it" % (i + 1, a1[:40]))
            i += 1
            continue
        if b1 and not _letterish(b1) and not _stray_mark(b1) and a1 and a1 != b1:
            # S156 E1 — a FRAGMENT run (the OCR's pieces of a rotated phrase, `y Stocks` / `impact the Topics…` / `Impact t`)
            # replaced by one label and blanks: admitted only when every fragment is a substring of the label (case-folded,
            # whitespace-collapsed) — a fragment the label does not contain refuses the whole run
            k, frags = i, []
            while k < n and rb2[k] and rb2[k][0] and not _letterish(rb2[k][0]) and not _stray_mark(rb2[k][0]) and (k == i or (ra[k] and ra[k][0] == "")):
                frags.append(rb2[k][0])
                k += 1
            label = _fold_text(a1)
            bad = [f for f in frags if _fold_text(f) not in label]
            if frags and not bad:
                facts["labels"].append({"row": i + 1, "letters": " / ".join(frags), "word": a1, "fit": "fragments of the label (%d)" % len(frags), "fragments": len(frags)})
            else:
                reasons.append("column 1 rows %d-%d: the fragments %r are not all pieces of the label %r" % (i + 1, k, [f[:20] for f in (bad or frags)], a1[:40]))
            i = max(k, i + 1)
            continue
        if not (b1 and _letterish(b1) and a1):
            reasons.append("column 1 row %d changed: %r -> %r" % (i + 1, b1[:40], a1[:40]))
            i += 1
            continue
        k, letters = i, []
        while k < n and rb2[k] and rb2[k][0] and _letterish(rb2[k][0]) and (k == i or (ra[k] and ra[k][0] == "")):
            letters.append(_bare(rb2[k][0]))
            k += 1
        ok, why = letters_fit("".join(letters), a1)
        if ok:
            facts["labels"].append({"row": i + 1, "letters": "".join(letters), "word": a1, "fit": why})
        else:
            reasons.append("column 1 rows %d-%d: the label %r does not fit the letters %r (%s)" % (i + 1, k, a1[:40], "".join(letters), why))
        i = k
    return not reasons, reasons, facts


def apply_admitted(lines: list[str], h: int, d: int, e: int, props: list[dict]) -> tuple:
    """One table's proposals applied ONE AT A TIME, each kept only if the invariant admits the table with it added to those
    already kept (S151 E1: a single wrong label refused the whole batch — the caption and the dots with it — under the
    all-or-nothing apply). Returns (new_lines, admitted, refused, invariant_checks, dots_fixed)."""
    before = lines[h:e + 1]
    kept: list = []
    refused: list = []
    new = before
    checks = 0
    dots = 0
    for p in props:
        trial = apply_table(lines, h, d, e, kept + [p])
        checks += 1
        ok, reasons, facts = grid_invariant(before, trial)
        if ok:
            kept.append(p)
            new = trial
            dots = facts["dots_fixed"]
        else:
            refused.append(dict(p, refused="; ".join(reasons)))
    return new, kept, refused, checks, dots


# ---- S157 E1: the split pass — a second stacked heading inside a table's body is a second table -------------------------

_NUMTOK = re.compile(r"^[-+]?\d[\d,]*(\.\d+)?%?$|^[-+]?\.\d+%?$")


def _is_num(cell: str) -> bool:
    return bool(_NUMTOK.match(cell.strip()))


def _heading_pair(a: list[str], b: list[str], above: list[str], lex: dict | None) -> tuple[bool, list[str], str]:
    """Two body rows that are a STACKED HEADING of a second table (p.175: `Standard | | P- | Lower | Upper …` over
    `Coefficients | Error | t Stat | value | 95% …`): the first cell empty in both, no numeric cell in either, a data row
    (one numeric cell at least) directly above, and the joined heading's longer cells half or more the book's own words
    (S152 E3's test; without a lexicon a pair of at least three two-part headings is taken)."""
    if not a or not b or a[0].strip() or b[0].strip():
        return False, [], "the first cell is not empty"
    if any(_is_num(c) and not c.strip().endswith("%") for c in a + b):   # a heading may carry a percent (`Lower 95%`)
        return False, [], "a number in the pair"
    if not any(_is_num(c) for c in above):
        return False, [], "no data row above"
    joined = _join_heading(a, b)
    heads = [c for c in joined[1:] if c.strip()]
    if len(heads) < 3:
        return False, [], "fewer than three headings"
    if lex is not None:
        # the pair's own words (S152 E3 tested fragment cells, not joined ones): `Standard`, `Error`, `Coefficients`, `Stat`…
        longish = [fold_letters(w) for c in a[1:] + b[1:] for w in re.findall(r"[A-Za-z]{3,}", c)]
        words = sum(1 for w in longish if lex.get(w, 0) >= 2)
        if not longish or 2 * words < len(longish):
            return False, [], "the pair's words are not the book's words (%d of %d)" % (words, len(longish))
    pairs = sum(1 for x, y in zip(a[1:], b[1:]) if x.strip() and y.strip())
    if pairs < 2:
        return False, [], "fewer than two stacked pairs"
    return True, joined, "a stacked heading of %d headings (%d stacked pairs)" % (len(heads), pairs)


def _heading_row_br(a: list[str], above: list[str], lex: dict | None) -> tuple[bool, list[str], str]:
    """One body row that is a second table's heading already stacked by the OCR with `<br>` (the held Valentine copy's
    `Standard<br>Error | t Stat | P.<br>value | Lower<br>95%`): the first cell empty, no plain number, two or more cells with
    `<br>`, a data row above, the words the book's own."""
    if not a or a[0].strip() or not any(_is_num(c) for c in above):
        return False, [], "shape"
    if any(_is_num(c) and not c.strip().endswith("%") for c in a):
        return False, [], "a number in the row"
    if sum(1 for c in a if "<br>" in c) < 2:
        return False, [], "fewer than two stacked cells"
    joined = [" ".join(c.replace("<br>", " ").split()) for c in a]
    heads = [c for c in joined[1:] if c.strip()]
    if len(heads) < 3:
        return False, [], "fewer than three headings"
    if lex is not None:
        longish = [fold_letters(w) for c in a[1:] for w in re.findall(r"[A-Za-z]{3,}", c)]
        words = sum(1 for w in longish if lex.get(w, 0) >= 2)
        if not longish or 2 * words < len(longish):
            return False, [], "the row's words are not the book's words (%d of %d)" % (words, len(longish))
    return True, joined, "a stacked heading in one row (%d cells with <br>)" % sum(1 for c in a if "<br>" in c)


def _tail_rejoin(lines: list[str], rows: list[list[str]], k0: int, e: int, ncols: int) -> dict | None:
    """The second table's tail: label-only rows from k0 on (only the first cell filled), then — past blank lines and at most
    one short non-table line without a digit (a page footer) — a lone short line and a numbers line of exactly ncols − 1 numeric
    tokens. Returns {row, label_rows, consumed} or None."""
    tail = rows[k0:]
    if not tail or not all(r and r[0].strip() and not any(c.strip() for c in r[1:]) for r in tail):
        return None
    j, skipped, consumed = e + 1, 0, []
    while j < len(lines):
        ln = lines[j].strip()
        if ln == "":
            j += 1
            continue
        if ln.startswith("|"):
            return None
        if skipped == 0 and len(ln) <= 60 and not re.search(r"\d", ln) and " " in ln:
            skipped, j = 1, j + 1
            continue
        break
    if j >= len(lines):
        return None
    lone = lines[j].strip()
    if not lone or " " in lone or len(lone) > 24 or lone.startswith("|"):
        return None
    m = j + 1
    while m < len(lines) and lines[m].strip() == "":
        m += 1
    if m >= len(lines):
        return None
    toks = lines[m].strip().split()
    if len(toks) != ncols - 1 or not all(_is_num(t) for t in toks):
        return None
    label = " ".join(r[0].strip() for r in tail) + " " + lone
    consumed = list(range(j, m + 1))
    return {"row": [label] + toks, "label_rows": [k0 + 1, len(rows)], "consumed": consumed, "lone": lone, "numbers": toks}


def propose_splits(lines: list[str], lex: dict | None = None) -> list[dict]:
    """One proposal per table that holds a second stacked heading in its body: where to split, the second table's header, and
    the tail re-join if the shape is there. Line numbers 1-based like every other proposal."""
    out = []
    for h, d, e in table_blocks(lines):
        rows = [cells(lines[k]) for k in range(d + 1, e + 1)]
        if len(rows) < 4:
            continue
        ncols = len(cells(lines[h]))
        for i in range(1, len(rows)):
            pair = 2
            ok, joined, why = (False, [], "") if i + 1 >= len(rows) else _heading_pair(rows[i], rows[i + 1], rows[i - 1], lex)
            if not ok:
                ok, joined, why = _heading_row_br(rows[i], rows[i - 1], lex)
                pair = 1
            if not ok:
                continue
            body2 = rows[i + pair:]
            if not body2:
                break
            rej = None
            for k0 in range(len(body2)):
                rej = _tail_rejoin(lines, body2, k0, e, ncols)
                if rej:
                    rej["label_rows"] = [d + 1 + i + pair + k0 + 1, e + 1]
                    break
            out.append({"kind": "split", "table": [h + 1, e + 1], "at": [d + 1 + i + 1, d + 1 + i + pair], "pair": pair, "header": joined,
                        "why": why, "rejoin": rej})
            break
    return out


def apply_split(lines: list[str], p: dict) -> tuple[list[str], int, int]:
    """The lines with one split applied: (new_lines, region_start, region_end_exclusive) of the rewritten span (0-based)."""
    h, e = p["table"][0] - 1, p["table"][1] - 1
    i0 = p["at"][0] - 1
    d = h + 1
    a_rows = [lines[k] for k in range(d + 1, i0)]
    b_header = _render_row(p["header"])
    b_delim = "|" + "---|" * len(p["header"])
    b_rows_idx = list(range(i0 + p.get("pair", 2), e + 1))
    rej = p.get("rejoin")
    end = e + 1
    if rej:
        cut = rej["label_rows"][0] - 1
        b_rows = [lines[k] for k in b_rows_idx if k < cut] + [_render_row(rej["row"])]
        end = max(rej["consumed"]) + 1
        between = [lines[k] for k in range(e + 1, rej["consumed"][0])]   # blank lines and the footer, kept after the table
    else:
        b_rows = [lines[k] for k in b_rows_idx]
        between = []
    new = [lines[h], lines[d]] + a_rows + [""] + [b_header, b_delim] + b_rows + between
    return lines[:h] + new + lines[end:], h, h + len(new)


def split_invariant(before: list[str], after: list[str], p: dict) -> tuple[bool, list[str]]:
    """Admit a split only as the exact re-partition of the before table: table A = the before header and the rows above the
    pair; table B's header = the pair's fold; table B's rows = the rest, or the rest up to the label rows plus ONE row that is
    the label pieces joined with the lone word and the prose numbers in order; nothing else anywhere."""
    reasons = []
    bt = table_blocks(before)
    at = table_blocks(after)
    if len(bt) != 1 or len(at) != 2:
        return False, ["expected one table before and two after, saw %d and %d" % (len(bt), len(at))]
    (bh, bd, be), = bt
    (ah, ad, ae), (bh2, bd2, be2) = at
    brows = [cells(before[k]) for k in range(bd + 1, be + 1)]
    arows = [cells(after[k]) for k in range(ad + 1, ae + 1)]
    b2rows = [cells(after[k]) for k in range(bd2 + 1, be2 + 1)]
    i = p["at"][0] - p["table"][0] - 2   # the pair's first row, as a body index
    if cells(after[ah]) != cells(before[bh]):
        reasons.append("table A's header changed")
    if arows != brows[:i]:
        reasons.append("table A's rows are not the before rows above the pair")
    pair = p.get("pair", 2)
    want_hdr = _join_heading(brows[i], brows[i + 1]) if pair == 2 else [" ".join(c.replace("<br>", " ").split()) for c in brows[i]]
    if cells(after[bh2]) != want_hdr:
        reasons.append("table B's header is not the fold of the pair" if pair == 2 else "table B's header is not the <br> row unstacked")
    rest = brows[i + pair:]
    rej = p.get("rejoin")
    if rej:
        cut = (rej["label_rows"][0] - p["table"][0] - 2) - (i + pair)   # the first label row, as an index into the rest
        want = rest[:cut] + [rej["row"]]
        label = " ".join(r[0].strip() for r in rest[cut:]) + " " + rej["lone"]
        if rej["row"] != [label] + rej["numbers"]:
            reasons.append("the re-joined row is not the label pieces + the lone word + the prose numbers")
        if not all(r and r[0].strip() and not any(c.strip() for c in r[1:]) for r in rest[cut:]):
            reasons.append("the rows re-joined were not label-only rows")
    else:
        want = rest
    if b2rows != want:
        reasons.append("table B's rows are not the rest of the before rows (with the one re-joined row)")
    return not reasons, reasons


def split_pass(lines: list[str], lex: dict | None = None) -> tuple[list[str], list[dict], list[dict]]:
    """Every split admitted by split_invariant applied, bottom-up so line numbers hold. Returns (lines, applied, refused)."""
    props = propose_splits(lines, lex)
    applied, refused = [], []
    for p in sorted(props, key=lambda x: -x["table"][0]):
        h, e = p["table"][0] - 1, p["table"][1] - 1
        end = e + 1
        if p.get("rejoin"):
            end = max(p["rejoin"]["consumed"]) + 1
        new, s, t = apply_split(lines, p)
        ok, why = split_invariant(lines[h:end], new[s:t], p)
        if ok:
            lines = new
            applied.append(dict(p, admitted=True))
        else:
            refused.append(dict(p, refused="; ".join(why)))
    return lines, applied, refused


# ---- S157 E20: the leaked head — a tail that duplicates the next table's head belongs to the next table ---------------

def _head_streams(lines: list[str], h2: int, d2: int, e2: int) -> tuple[set[str], str]:
    """The next table's head as (the set of its folded cells, its letters as one stream with doubled letters collapsed):
    the header and the first two body rows."""
    rows = [cells(lines[h2])] + [cells(lines[k]) for k in range(d2 + 1, min(e2, d2 + 2) + 1)]
    folded = {_fold_text(_bare_text(c)) for r in rows for c in r if c.strip()}
    stream = collapse_doubles("".join(fold_letters(_bare(c)) for r in rows for c in r if c.strip()))
    return folded, stream


def _bare_text(cell: str) -> str:
    return BR.sub(" ", cell).strip()


def _cell_in_head(cell: str, folded: set[str], stream: str) -> bool:
    t = _fold_text(_bare_text(cell))
    if not t:
        return True
    if t in folded:
        return True
    letters = collapse_doubles(fold_letters(_bare(cell)))
    return len(letters) >= 3 and letters in stream


def propose_leaks(lines: list[str]) -> list[dict]:
    """One proposal per table whose tail duplicates the next table's head (Marker's fusion of stacked tables, p.200 of
    Valentine): the rows to drop, 1-based, and why."""
    out = []
    blocks = table_blocks(lines)
    issue_lines = {x["line"] for x in health(lines)}
    for (h, d, e), (h2, d2, e2) in zip(blocks, blocks[1:]):
        if h2 - e > 3 or any(h + 1 <= ln <= e + 1 for ln in issue_lines):
            continue
        folded, stream = _head_streams(lines, h2, d2, e2)
        next_first = next((_fold_text(_bare_text(c)) for c in cells(lines[h2]) if c.strip()), "")
        rows = [cells(lines[k]) for k in range(d + 1, e + 1)]
        cut = len(rows)
        while cut > 1:
            r = rows[cut - 1]
            filled = [c for c in r if c.strip()]
            if not filled or any(_is_num(c) for c in filled) or not all(_cell_in_head(c, folded, stream) for c in filled):
                break
            cut -= 1
        if cut == len(rows):
            continue
        top_first = next((_fold_text(_bare_text(c)) for c in rows[cut] if c.strip()), "")
        if not next_first or top_first != next_first:
            continue   # the leaked TITLE must anchor the leak: the topmost dropped row opens with the next table's own first cell
        out.append({"kind": "leak", "table": [h + 1, e + 1], "drop": [d + 1 + cut + 1, e + 1], "next": [h2 + 1, e2 + 1],
                    "why": "%d tail row(s) duplicate the next table's head (title %r)" % (len(rows) - cut, next_first[:30])})
    return out


def apply_leak(lines: list[str], p: dict) -> list[str]:
    a, b = p["drop"][0] - 1, p["drop"][1] - 1
    return lines[:a] + lines[b + 1:]


def leak_invariant(before: list[str], after: list[str], p: dict) -> tuple[bool, list[str]]:
    """Admit a leak only as the exact cut: the table's header, delimiter and rows above the drop unchanged; the dropped rows
    exactly the tail; every dropped filled cell non-numeric and found in the next table's head; one body row kept at least.
    `before` runs from the table's header through the next table's last line; `after` the same span after the cut."""
    reasons = []
    tb, ta = table_blocks(before), table_blocks(after)
    if len(tb) != 2 or len(ta) != 2:
        return False, ["expected two tables before and after, saw %d and %d" % (len(tb), len(ta))]
    (hb, db, eb), (h2b, d2b, e2b) = tb
    (ha, da, ea), (h2a, d2a, e2a) = ta
    n_drop = p["drop"][1] - p["drop"][0] + 1
    keep = (eb - db) - n_drop
    if keep < 1:
        reasons.append("no body row kept")
    if [before[k] for k in range(hb, db + 1 + keep)] != [after[k] for k in range(ha, ea + 1)]:
        reasons.append("the kept table is not the before table cut at the tail")
    if [before[k] for k in range(h2b, e2b + 1)] != [after[k] for k in range(h2a, e2a + 1)]:
        reasons.append("the next table changed")
    folded, stream = _head_streams(before, h2b, d2b, e2b)
    for k in range(db + 1 + keep, eb + 1):
        for c in cells(before[k]):
            if c.strip() and (_is_num(c) or not _cell_in_head(c, folded, stream)):
                reasons.append("dropped cell %r is not the next table's head" % c[:30])
    return not reasons, reasons


def leak_pass(lines: list[str]) -> tuple[list[str], list[dict], list[dict]]:
    props = propose_leaks(lines)
    applied, refused = [], []
    for p in sorted(props, key=lambda x: -x["table"][0]):
        h, e2 = p["table"][0] - 1, p["next"][1] - 1
        new = apply_leak(lines, p)
        n_drop = p["drop"][1] - p["drop"][0] + 1
        ok, why = leak_invariant(lines[h:e2 + 1], new[h:e2 + 1 - n_drop], p)
        if ok:
            lines = new
            applied.append(dict(p, admitted=True))
        else:
            refused.append(dict(p, refused="; ".join(why)))
    return lines, applied, refused



# ---- S157 E3: the trim pass — trailing columns nothing fills are Marker's padding, not the page's ------------------------

TRIM_MIN_COLS = 2       # lever-waiver: Rab's word only; set S157 E3 — a table keeps at least two columns; a one-column table is a list, and a table whose every column
                        # but one is empty is a question for the reading, not a trim


def propose_trims(lines: list[str]) -> list[dict]:
    """One proposal per table whose last column(s) hold nothing — the header cell and every body cell blank — down to
    TRIM_MIN_COLS columns. A table with a health issue or ragged rows (a row with a different cell count) is left alone;
    a LEADING empty column is never touched (p097/p132/p133: the rail column is empty in the truth's body and letters in
    the copy). Line numbers 1-based like every other proposal."""
    issue_lines = {x["line"] for x in health(lines)}
    out = []
    for h, d, e in table_blocks(lines):
        if any(h + 1 <= ln <= e + 1 for ln in issue_lines):
            continue
        rows = [cells(lines[k]) for k in range(h, e + 1) if k != d]
        if not rows:
            continue
        nc = len(rows[0])
        if nc <= TRIM_MIN_COLS or any(len(r) != nc for r in rows):
            continue
        k = 0
        while nc - k > TRIM_MIN_COLS and all(not r[nc - 1 - k].strip() for r in rows):
            k += 1
        if k:
            out.append({"kind": "trim", "table": [h + 1, e + 1], "cols": nc, "drop": k,
                        "why": "the last %d of %d columns hold nothing in %d rows" % (k, nc, len(rows))})
    return out


def _delim_segments(row: str) -> list[str]:
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [x.strip() for x in s.split("|")]


def apply_trim(lines: list[str], p: dict) -> list[str]:
    """The lines with one trim applied: every row of the table re-rendered without its last `drop` cells; the delimiter
    row keeps its first (cols - drop) segments (an alignment mark stays with its column)."""
    h, e = p["table"][0] - 1, p["table"][1] - 1
    d = h + 1
    keep = p["cols"] - p["drop"]
    new = []
    for k in range(h, e + 1):
        if k == d:
            new.append("|" + "|".join(_delim_segments(lines[k])[:keep]) + "|")
        else:
            new.append(_render_row(cells(lines[k])[:keep]))
    return lines[:h] + new + lines[e + 1:]


def trim_invariant(before: list[str], after: list[str], p: dict) -> tuple[bool, list[str]]:
    """Admit a trim only as the exact cut: one table on both sides with the same number of rows; every after row equal to
    its before row with the last `drop` cells removed; every removed cell blank; at least TRIM_MIN_COLS columns kept; the
    delimiter's kept segments unchanged."""
    reasons = []
    tb, ta = table_blocks(before), table_blocks(after)
    if len(tb) != 1 or len(ta) != 1:
        return False, ["expected one table before and after, saw %d and %d" % (len(tb), len(ta))]
    (hb, db, eb), (ha, da, ea) = tb[0], ta[0]
    keep = p["cols"] - p["drop"]
    if keep < TRIM_MIN_COLS:
        reasons.append("fewer than %d columns would be kept" % TRIM_MIN_COLS)
    if eb - hb != ea - ha:
        reasons.append("rows before %d, after %d" % (eb - hb, ea - ha))
        return False, reasons
    if _delim_segments(after[da]) != _delim_segments(before[db])[:keep]:
        reasons.append("the delimiter row's kept segments changed")
    for i, (kb, ka) in enumerate(zip(range(hb, eb + 1), range(ha, ea + 1))):
        if kb == db:
            continue
        b, a = cells(before[kb]), cells(after[ka])
        if len(b) != p["cols"]:
            reasons.append("row %d has %d cells before, not %d" % (i + 1, len(b), p["cols"]))
            continue
        if a != b[:keep]:
            reasons.append("row %d is not the before row cut to %d cells" % (i + 1, keep))
        if any(c.strip() for c in b[keep:]):
            reasons.append("row %d: a removed cell was not blank (%r)" % (i + 1, [c[:20] for c in b[keep:] if c.strip()]))
    return not reasons, reasons


def trim_pass(lines: list[str]) -> tuple[list[str], list[dict], list[dict]]:
    """Every trim admitted by trim_invariant applied. Returns (lines, applied, refused)."""
    props = propose_trims(lines)
    applied, refused = [], []
    for p in sorted(props, key=lambda x: -x["table"][0]):
        h, e = p["table"][0] - 1, p["table"][1] - 1
        new = apply_trim(lines, p)
        ok, why = trim_invariant(lines[h:e + 1], new[h:e + 1], p)
        if ok:
            lines = new
            applied.append(dict(p, admitted=True))
        else:
            refused.append(dict(p, refused="; ".join(why)))
    return lines, applied, refused


UNFRAME_STUBS = False   # lever-waiver: Rab's word only; set S160 E6 OFF — a STUB (a header whose body has no filled cell: a caption box, a
                        # chopped heading, a footnote framed as a table — 64 of the shelf's 2,513, S157 E5) may also be the trace of a
                        # lost table body (S157 E7's judgement), and unframing would hide the trace; OFF the pass PROPOSES and the record
                        # names every stub with the line it would become, ON it applies what unframe_invariant admits; moves on his word


STUB_TRACE_ROWS = 2     # lever-waiver: Rab's word only; set S160 E6 from the shelf's own split — of its 64 stubs, 32 have 0–1 blank body
                        # rows (a caption, a chopped heading, a footnote, framed) and 32 have 10–37 (a grid table_rec detected whose
                        # cells came back empty: the trace of a lost body, or the crammed cell's 25 empty rows under its one stacked
                        # cell); nothing between. A stub at or over this many blank rows is a TRACE, named and never unframed
STUB_TRACE_PIECES = 3   # lever-waiver: Rab's word only; set S160 E6 from the shelf: a header cell stacked into this many non-blank `<br>`
                        # pieces is a table's worth of values in one cell (the crammed 8.2: 99 pieces; an exercise's ten-column head:
                        # 6) — the crammed class, a trace; a two-piece cell is a caption Marker broke in two (`TABLE<br>25.2`), a frame


def find_stubs(lines: list[str]) -> list[dict]:
    """Every STUB table — a header + delimiter whose body has no filled cell (no body rows, or every body row blank in every
    cell) — classed: `frame` when the header is the whole content (fewer than STUB_TRACE_ROWS blank rows, no cell stacked into
    STUB_TRACE_PIECES or more `<br>` pieces) and may be unframed; `trace` when a header cell is stacked that deep (the crammed
    class, `converter/table-crammed-into-one-cell`) or the body is a grid of blank rows — the trace of a lost body (S157 E7),
    named in the record and never touched. `text` is the header's non-empty cells (`<br>` as a space, whitespace collapsed)
    joined by one space; nothing is guessed (`Phi loson hv` stays chopped — the S151 fragments route is a different pass). A
    header with no non-empty cell says nothing and is not a stub. Line numbers 1-based like every other proposal."""
    out = []
    for h, d, e in table_blocks(lines):
        body = [cells(lines[k]) for k in range(d + 1, e + 1)]
        if any(c.strip() for r in body for c in r):
            continue
        raw = cells(lines[h])
        head = [re.sub(r"\s+", " ", BR.sub(" ", c)).strip() for c in raw]
        words = [c for c in head if c]
        if not words:
            continue
        pieces = max((len([x for x in BR.split(c) if x.strip()]) for c in raw), default=0)
        klass = "trace" if (pieces >= STUB_TRACE_PIECES or len(body) >= STUB_TRACE_ROWS) else "frame"
        out.append({"kind": "unframe", "table": [h + 1, e + 1], "cols": len(head), "body_rows": len(body), "br_pieces": pieces,
                    "class": klass, "text": " ".join(words),
                    "why": "a header of %d cells with no filled body cell (%d blank row(s); %d stacked piece(s))" % (len(head), len(body), pieces)})
    return out


def propose_unframes(lines: list[str]) -> list[dict]:
    """One proposal per `frame` stub (find_stubs): unframed, the header's cells become one prose line and the delimiter and the
    blank row go. The `trace` stubs are never proposed."""
    return [p for p in find_stubs(lines) if p["class"] == "frame"]


def apply_unframe(lines: list[str], p: dict) -> list[str]:
    """The lines with one unframe applied: the table's lines replaced by the one prose line the proposal carries."""
    h, e = p["table"][0] - 1, p["table"][1] - 1
    return lines[:h] + [p["text"]] + lines[e + 1:]


def unframe_invariant(before: list[str], after: list[str], p: dict) -> tuple[bool, list[str]]:
    """Admit an unframe only as the exact unframing: one table before and none after; exactly one line after; that line equals the
    before header's non-empty cells (`<br>` as a space, whitespace collapsed) joined by a single space — every letter of the
    header survives, in order, and nothing else appears; every before body cell blank."""
    reasons = []
    tb = table_blocks(before)
    if len(tb) != 1:
        return False, ["expected one table before, saw %d" % len(tb)]
    if table_blocks(after):
        reasons.append("a table remains after")
    if len(after) != 1:
        reasons.append("expected one line after, saw %d" % len(after))
    h, d, e = tb[0]
    head = [re.sub(r"\s+", " ", BR.sub(" ", c)).strip() for c in cells(before[h])]
    want = " ".join(c for c in head if c)
    if not want:
        reasons.append("the header says nothing")
    if after and after[0] != want:
        reasons.append("the line is not the header's cells joined (%r vs %r)" % (after[0][:40], want[:40]))
    if any(c.strip() for k in range(d + 1, e + 1) for c in cells(before[k])):
        reasons.append("a body cell was not blank")
    if after and re.sub(r"\s+", "", after[0]) != re.sub(r"\s+", "", "".join(head)):
        reasons.append("the letters of the header and the line differ")
    return not reasons, reasons


def unframe_pass(lines: list[str], apply: bool | None = None) -> tuple[list[str], list[dict], list[dict], list[dict], list[dict]]:
    """With the lever on (`apply`, default UNFRAME_STUBS), every `frame` unframe admitted by unframe_invariant applied; with it
    off, nothing changes and every `frame` proposal comes back as proposed. The `trace` stubs come back named either way and
    are never touched. Returns (lines, applied, refused, proposed, traces)."""
    stubs = find_stubs(lines)
    traces = [p for p in stubs if p["class"] == "trace"]
    props = [p for p in stubs if p["class"] == "frame"]
    if not (UNFRAME_STUBS if apply is None else apply):
        return lines, [], [], [dict(p, proposed=True) for p in props], traces
    applied, refused = [], []
    for p in sorted(props, key=lambda x: -x["table"][0]):
        h, e = p["table"][0] - 1, p["table"][1] - 1
        new = apply_unframe(lines, p)
        ok, why = unframe_invariant(lines[h:e + 1], new[h:h + 1], p)
        if ok:
            lines = new
            applied.append(dict(p, admitted=True))
        else:
            refused.append(dict(p, refused="; ".join(why)))
    return lines, applied, refused, [], traces


def geometry_pass(text: str, resolver=None, use_lexicon: bool = True, vision: dict | None = None) -> tuple[str, dict]:
    """The layer over a whole markdown text: propose per table, apply on a copy, keep only what the invariant admits.
    Returns (text, record): the record counts tables, proposals, applied, refused and unresolved, lists every label and
    caption, and names the invariant's own tallies — the AFTER half of the measurement, written by the act itself.
    S151 E1: the book's own lexicon is the first word route (`use_lexicon`); the resolver is asked only for what it leaves."""
    lines = text.split("\n")
    calls = {"n": 0}

    def counted(letters, context):
        calls["n"] += 1
        return resolver(letters, context)

    lex = lexicon(lines) if use_lexicon else None
    # S157 E1: the SPLIT pass first — a second stacked heading inside a body is a second table (p.175's coefficients under the
    # ANOVA); the tail re-joined from the prose it fell into; each admitted by split_invariant; the two tables then get the
    # ordinary repairs below
    lines, splits_applied, splits_refused = split_pass(lines, lex)
    # S157 E3: the TRIM pass next — trailing columns nothing fills (Marker's padding: 15 of 82 Valentine tables) dropped,
    # each admitted by trim_invariant; after the split so a table born of it is trimmed too, before the proposals so a
    # caption or a rail is read on the page's own columns
    # S157 E20: the LEAKED HEAD before the trim — a tail that duplicates the next table's head is the next table's (p.200's
    # regression statistics carried the ANOVA's title and half its heading); the trim then sees the emptied column
    lines, leaks_applied, leaks_refused = leak_pass(lines)
    lines, trims_applied, trims_refused = trim_pass(lines)
    # S160 E6: the STUBS after the trim — a header with no filled body cell; the record names each with the prose line it would
    # become; the pass applies only under UNFRAME_STUBS (his word; OFF), each admitted by unframe_invariant
    lines, unframes_applied, unframes_refused, unframes_proposed, stub_traces = unframe_pass(lines)
    vnotes: dict = {}
    props = propose(lines, counted if resolver is not None else None, lex, vision=vision, notes=vnotes if vision else None)
    blocks = {(h + 1, e + 1): (h, d, e) for h, d, e in table_blocks(lines)}
    by_table: dict = {}
    for p in props:
        by_table.setdefault(tuple(p["table"]), []).append(p)
    applied, refused, unresolved = [], [], []
    out_lines, pos, checks, dots_fixed = [], 0, 0, 0
    for key in sorted(by_table):
        h, d, e = blocks[key]
        ps = by_table[key]
        unresolved.extend(p for p in ps if p["kind"] == "rail" and not p.get("word"))
        todo = [p for p in ps if p["kind"] != "rail" or p.get("word")]
        if not todo:
            continue
        new, admitted, refused_here, n_checks, dots = apply_admitted(lines, h, d, e, todo)
        checks += n_checks
        refused.extend(refused_here)
        if admitted:
            out_lines.extend(lines[pos:h])
            out_lines.extend(new)
            pos = e + 1
            applied.extend(admitted)
            dots_fixed += dots
    out_lines.extend(lines[pos:])
    record = {
        "tables": len(blocks),
        "with_signature": len(by_table),
        "proposals": len(props),
        "applied": len(applied),
        "refused": len(refused),
        "unresolved": len(unresolved),
        "labels": [{"rows": p["rows"], "span": p.get("span"), "span_how": p.get("span_how", "tiled"), "placed": p.get("placed", p["rows"][0]),
                    "letters": p["letters"], "word": p["word"], "how": p["how"]} for p in applied if p["kind"] == "rail"],
        "captions": [{"line": p["line"], "text": p["text"], "fragment_dropped": p["fragment_dropped"],
                      **({"fragments_joined": True, "raw": p["raw"], "how": p["how"]} if p.get("fragments_joined") else {})}
                     for p in applied if p["kind"] == "caption"],
        "folds": [{"rows": p["rows"], "why": p["why"]} for p in applied if p["kind"] == "fold"],   # S152 E1
        "splits": [{"table": p["table"], "at": p["at"], "header": p["header"], "why": p["why"],
                    "rejoined": ({"row": p["rejoin"]["row"], "consumed_lines": [k + 1 for k in p["rejoin"]["consumed"]]} if p.get("rejoin") else None)} for p in splits_applied],   # S157 E1; the lines 1-based like every other number in the record (E5's skeptic read them 0-based — they were)
        "splits_refused": [{"table": p["table"], "at": p["at"], "why": p["refused"]} for p in splits_refused],
        "trims": [{"table": p["table"], "cols": p["cols"], "drop": p["drop"], "why": p["why"]} for p in trims_applied],   # S157 E3
        "trims_refused": [{"table": p["table"], "cols": p["cols"], "drop": p["drop"], "why": p["refused"]} for p in trims_refused],
        "leaks": [{"table": p["table"], "drop": p["drop"], "next": p["next"], "why": p["why"]} for p in leaks_applied],   # S157 E20
        "leaks_refused": [{"table": p["table"], "drop": p["drop"], "why": p["refused"]} for p in leaks_refused],
        # S160 E6: every stub named — the `frame` ones (the lever OFF: proposed, the text untouched; ON: applied or refused) and
        # the `trace` ones (a stacked cell or a grid of blank rows: the trace of a lost body, never touched)
        "stubs": len(unframes_applied) + len(unframes_refused) + len(unframes_proposed) + len(stub_traces),
        "unframes": [{"table": p["table"], "cols": p["cols"], "body_rows": p["body_rows"], "text": p["text"][:120]} for p in unframes_applied],
        "unframes_refused": [{"table": p["table"], "cols": p["cols"], "why": p["refused"]} for p in unframes_refused],
        "unframes_proposed": [{"table": p["table"], "cols": p["cols"], "body_rows": p["body_rows"], "text": p["text"][:120]} for p in unframes_proposed],
        "stub_traces": [{"table": p["table"], "cols": p["cols"], "body_rows": p["body_rows"], "br_pieces": p["br_pieces"], "text": p["text"][:80]} for p in stub_traces],
        "unresolved_rails": [{"rows": p["rows"], "letters": p["letters"], "why": p["refused"]} for p in unresolved],
        "refusals": [{"kind": p["kind"], "table": p["table"], "why": p["refused"]} for p in refused],
        "dots_fixed": dots_fixed,
        "invariant_checks": checks,
        "resolver_calls": calls["n"],
        "lexicon_words": len(lex) if lex is not None else None,
        # S156 E1 — what the reading of the page (vision.json, a sub-agent panel's sidecar) did here, or None without one
        "vision": ({"format": vision.get("format"), "produced_by": vision.get("produced_by"), "tables_matched": len(vnotes.get("matched", [])),
                    "words": vnotes.get("words", 0), "spans": vnotes.get("spans", 0), "fragment_rails": vnotes.get("fragment_rails", 0),
                    "figures": vnotes.get("figures", []), "unmatched": vnotes.get("unmatched", [])} if vision else None),
    }
    return "\n".join(out_lines), record
