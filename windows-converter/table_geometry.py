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
                runs.append("".join(cur))
                cur = []
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


SEGMENT_MIN_SCORE = 1.25   # a word must explain its read this much better than leaving it (MIGHT for `MGMT` scores 1: refused)


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


def propose(lines: list[str], resolver=None, lex: dict | None = None) -> list[dict]:
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
                        out.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[c0] + 1, r[c1] + 1],
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
                        out.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[st[0]] + 1, r[st[-1]] + 1],
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
                out.append({"kind": "rail", "table": [h + 1, e + 1], "rows": [r[0] + 1, r[-1] + 1], "letters": letters,
                            "word": word, "how": how, "refused": refused})
        if t.dots_total and t.stray_dot_glyphs:
            out.append({"kind": "dots", "table": [h + 1, e + 1], "cells": t.stray_dot_glyphs})
    return out


def _render_row(cs: list[str]) -> str:
    return "| " + " | ".join(c if "`" in c else c.replace("|", "\\|") for c in cs) + " |"


def apply_table(lines: list[str], h: int, d: int, e: int, props: list[dict]) -> list[str]:
    """The table's lines (h..e, 0-based) with the given proposals applied; an unchanged row keeps its bytes."""
    grid = {k: cells(lines[k]) for k in range(h, e + 1) if k != d}
    before = {k: list(v) for k, v in grid.items()}
    caption = None
    for p in props:
        if p["kind"] == "rail" and p.get("word"):
            r0, r1 = p["rows"][0] - 1, p["rows"][1] - 1
            if r0 in grid and r1 in grid and grid[r0]:
                grid[r0][0] = p["word"]
                for k in range(r0 + 1, r1 + 1):
                    if grid.get(k):
                        grid[k][0] = ""
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
    if len(ra) == len(rb) - 1:
        filled = sorted((c for c in rb[0] if c), key=len)
        above = "".join(_bare(x) for x in after[:ha]).lower()
        if filled and len(filled) <= 2 and _bare(filled[-1]).lower() and _bare(filled[-1]).lower() in above:
            lifted = 1
            facts["caption"] = filled[-1]
            facts["caption_lines"] = ha
        else:
            reasons.append("a row was dropped (rows before %d, after %d) and no caption above carries the first row's text" % (len(rb), len(ra)))
    elif len(ra) != len(rb):
        reasons.append("rows before %d, after %d" % (len(rb), len(ra)))
    n = min(len(ra), len(rb) - lifted)
    # every cell outside column 1, every row (a rail's rows included — the first version of this loop jumped over
    # them with the rail and compared 60 of 120 cells: the selftest's own negatives caught it)
    for i in range(n):
        b, a = rb[i + lifted], ra[i]
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
        b, a = rb[i + lifted], ra[i]
        b1, a1 = (b[0] if b else ""), (a[0] if a else "")
        if b1 == a1:
            i += 1
            continue
        if b1 in STRAY_DOTS and a1 == DOT:
            facts["dots_fixed"] += 1
            i += 1
            continue
        if not (b1 and _letterish(b1) and a1):
            reasons.append("column 1 row %d changed: %r -> %r" % (i + 1, b1[:40], a1[:40]))
            i += 1
            continue
        k, letters = i, []
        while k < n and rb[k + lifted] and rb[k + lifted][0] and _letterish(rb[k + lifted][0]) and (k == i or (ra[k] and ra[k][0] == "")):
            letters.append(_bare(rb[k + lifted][0]))
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


def geometry_pass(text: str, resolver=None, use_lexicon: bool = True) -> tuple[str, dict]:
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
    props = propose(lines, counted if resolver is not None else None, lex)
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
        "labels": [{"rows": p["rows"], "letters": p["letters"], "word": p["word"], "how": p["how"]} for p in applied if p["kind"] == "rail"],
        "captions": [{"line": p["line"], "text": p["text"], "fragment_dropped": p["fragment_dropped"]} for p in applied if p["kind"] == "caption"],
        "unresolved_rails": [{"rows": p["rows"], "letters": p["letters"], "why": p["refused"]} for p in unresolved],
        "refusals": [{"kind": p["kind"], "table": p["table"], "why": p["refused"]} for p in refused],
        "dots_fixed": dots_fixed,
        "invariant_checks": checks,
        "resolver_calls": calls["n"],
        "lexicon_words": len(lex) if lex is not None else None,
    }
    return "\n".join(out_lines), record
