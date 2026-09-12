r"""edit_whitelist — the DIFF-WHITELIST ACCEPTOR (J46; S119 R1 measured, promoted S140, Rab signed C+A 2026-09-12).

Faithfulness by construction. After the fence, survival and ratio checks, `analyst.process` calls
`reconcile(chunk, candidate, FULL)` on every chunk it is about to accept:

  1. whitespace-tokenise both, keeping every token's offsets;
  2. word-level opcodes (rapidfuzz Levenshtein.opcodes on the two token lists, exact keys);
  3. for every non-equal opcode decide ACCEPT or REVERT: accept only if the two spans are
     EQUIVALENT under the stated whitelist normalisation N (below); otherwise splice the INPUT's
     span back in place of the candidate's;
  4. emit the reconciled chunk (the candidate's text with every non-whitelisted edit undone).

The whitelist N (applied to BOTH spans, then compared space-free):
  quotes      curly quotes / dashes unified to ASCII (text_norm's own _QUOTES map, NFKC) — always
  escape      markdown backslash-escapes removed (`\_` `\*` `\$` `\(` `\[` `\]` `\#` `\-` ...)
  link        `[text](url)` and Marker's `[[n\]](url)` collapse to their text; the URL MULTISET of
              the two spans must be equal (a link may be re-syntaxed, never re-targeted or dropped)
  markup      heading marks, emphasis `*`, boundary `_`, backticks, blockquote `>`, table pipes
              and separator dashes removed; square brackets removed (citation `[2]` == `2`)
  hyphen      a line-end hyphen glyph mis-mapped to `!` (S119 R1 a_probe3) or a real `-` followed
              by whitespace and a lowercase letter joins the two halves
  ligature    the INPUT's mis-mapped ligature glyphs (`!"#$&'%)` between letters, or before a
              lowercase word start) may be REPLACED by one of ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|
              st|Th|th in the candidate (`Di"cult` -> `Difficult`; `%ere` -> `There`); a
              required replacement, so a dropped quote mark alone is NOT a ligature repair
  reflow      space-free comparison: word boundaries may move (`unexpect edly` -> `unexpectedly`)
Everything else is REVERTED: word substitutions, deletions, insertions, numeral changes,
punctuation-only edits (`.` -> `,`), case changes. Rab's slot (S119, unchanged S140): the
whitelist IS the policy — which edits the analyst may make; punctuation/case stay reverted (on
*Zero to One* the analyst's misspelling `ESCAPPING` was a case/punctuation-shaped edit).

Policies: FULL = the whitelist above (what ships); STRICT = FULL minus {ligature, escape, link}
(reflow and markup only — the ceiling of "faithful by construction" under the audit as shipped);
"all" = accept everything (a control: must reproduce the candidate byte-for-byte); "none" =
accept nothing (a control: must reproduce the input's words).

Measured on the real 492 DDIA pairs (prototypes/analyst-lab/edit-whitelist/, results_acceptor.json,
S119): shipped 0.9718/49 -> FULL 0.9817/24 under the shipped ladder, 0.9968/1 under ladder v3c;
STRICT 0.9998/0; accept-all == shipped byte-for-byte; accept-none == the sidecar's words. Pure:
no I/O, no state; ≈ microseconds per chunk, 0 GPU. The selftest (edit_whitelist_selftest.py)
pins the two controls and one case per rung with its negative control.
"""
from __future__ import annotations

import collections
import re
import unicodedata

from rapidfuzz.distance import Levenshtein

import text_norm as tn

_WS_TOKEN = re.compile(r"\S+")
_QUOTES = tn._QUOTES
_ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|<>~\"'])")
_LINK = re.compile(r"\[(\[?[^\]\n]*\]?)\]\(([^)\n]*)\)")
_HYPHEN_JOIN = re.compile(r"(?<=[A-Za-z])[!\-­]\s+(?=[a-z])")
_GARBLE_IN = re.compile(r"(?<=[A-Za-z])[!\"#$&'%)](?=[a-z])")
_GARBLE_START = re.compile(r"(?<![A-Za-z])[!\"#$&'%](?=[a-z]{2,})")
LIG_ALT = "(?:ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|Th|th)"
_MARKUP = re.compile(r"(?m)^\s{0,3}#{1,6}\s*|`|\*|(?<!\w)_|_(?!\w)|^\s*>\s?|\||^\s*:?-{3,}:?\s*$")
_BRACKETS = re.compile(r"[\[\]]")
_WS = re.compile(r"\s+")
_DIGIT = re.compile(r"\d")

FULL = frozenset({"escape", "link", "markup", "hyphen", "ligature"})
STRICT = frozenset({"markup", "hyphen"})
CLASSES = ("reflow", "hyphen", "escape", "link", "markup", "ligature", "markup+link", "markup+escape",
           "mixed-whitelist", "punctuation/case", "numeral", "insertion", "deletion", "substitution")


def _urls(text: str, rungs) -> collections.Counter:
    # escapes come off BEFORE the link regex: Marker writes a citation as `[[2\]](#page-490-0)`
    # and the escaped bracket hides the link from a naive regex (S119 R1, first acceptor run)
    if "escape" in rungs:
        text = _ESC.sub(r"\1", text)
    return collections.Counter(u for _, u in _LINK.findall(text))


def norm(text: str, rungs) -> str:
    """The whitelist normalisation N under the given rungs, space-free."""
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    if "escape" in rungs:
        t = _ESC.sub(r"\1", t)
    if "link" in rungs:
        t = _LINK.sub(r"\1", t)
    if "markup" in rungs:
        t = _MARKUP.sub(" ", t)
        t = _BRACKETS.sub("", t)
    if "hyphen" in rungs:
        t = _HYPHEN_JOIN.sub("", t)
    return _WS.sub("", t)


def equivalent(a: str, b: str, rungs) -> bool:
    """True when span `a` (the input's) and span `b` (the candidate's) are the same text under the rungs."""
    # S140: link STRUCTURE is never markup — the two spans must carry the same number of `[text](url)` constructs
    # (a dropped opening `[` leaves `text](url)`, which the bracket-removing markup rung read as equal; the prototype's
    # coarse alignment hid it, the fine split exposed it on DDIA's references: 142 windows). Escapes come off first
    # because Marker writes a citation as `[[2\]](#page)`.
    ua, ub = _ESC.sub(r"\1", a), _ESC.sub(r"\1", b)
    if len(_LINK.findall(ua)) != len(_LINK.findall(ub)):
        return False
    # and the BRACKET BALANCE of a span may not change: `[An` vs `An` (one token of a link) is never equivalent,
    # while `[2]` vs `2` and `[[2\]](#p)` vs `[2](#p)` (balanced) still are
    if (ua.count("[") - ua.count("]"), ua.count("(") - ua.count(")")) != (ub.count("[") - ub.count("]"), ub.count("(") - ub.count(")")):
        return False
    if "link" in rungs and _urls(a, rungs) != _urls(b, rungs):
        return False
    na, nb = norm(a, rungs), norm(b, rungs)
    if na == nb:
        return True
    if "ligature" in rungs and (_GARBLE_IN.search(na) or _GARBLE_START.search(na)) and len(na) <= 600:
        # rebuild na as a regex where every garble char becomes the ligature alternation
        pat = ""
        for j, ch in enumerate(na):
            left = na[j - 1] if j else ""
            right = na[j + 1:j + 3]
            if ch in "!\"#$&'%)" and (
                (left.isalpha() and right[:1].islower()) or
                (not left.isalpha() and len(right) == 2 and right.islower() and right.isalpha())):
                pat += LIG_ALT
            else:
                pat += re.escape(ch)
        return re.fullmatch(pat, nb) is not None
    return False


def label(a: str, b: str) -> str:
    """A class name for the record: the cheapest rung set that makes the spans equivalent, or the
    content class of a non-whitelisted edit."""
    # S140: the rungs first — a dropped `##` is a "markup" edit, not a "deletion" (the prototype named it by the
    # empty span and an accepted deletion read as an accepted content loss in the tally)
    if a.strip() and b.strip() and equivalent(a, b, set()):
        return "reflow"
    for name, rungs in (("hyphen", {"hyphen"}), ("escape", {"escape"}), ("link", {"link"}),
                        ("markup", {"markup"}), ("ligature", {"ligature"}),
                        ("markup+link", {"markup", "link"}), ("markup+escape", {"markup", "escape"})):
        if equivalent(a, b, rungs):
            return name
    if equivalent(a, b, FULL):
        return "mixed-whitelist"
    if not a.strip():
        return "insertion"
    if not b.strip():
        return "deletion"
    pa = re.sub(r"[^\w\s]", "", a).casefold().split()
    pb = re.sub(r"[^\w\s]", "", b).casefold().split()
    if "".join(pa) == "".join(pb):
        return "punctuation/case"
    da = [w for w in a.split() if _DIGIT.search(w)]
    db = [w for w in b.split() if _DIGIT.search(w)]
    if da != db and len(a.split()) == len(b.split()):
        return "numeral"
    return "substitution"


def reconcile(inp: str, cand: str, rungs=FULL, policy: str = "whitelist") -> tuple[str, list]:
    """Returns (reconciled text, edit log [(label, accepted, a_span, b_span)]). `policy`: "whitelist"
    (the rungs decide) | "all" (accept every edit — the candidate returns unchanged) | "none" (revert
    every edit — the input's words return, in the candidate's whitespace where they meet)."""
    ta = [(m.start(), m.end()) for m in _WS_TOKEN.finditer(inp)]
    tb = [(m.start(), m.end()) for m in _WS_TOKEN.finditer(cand)]
    wa = [inp[s:e] for s, e in ta]
    wb = [cand[s:e] for s, e in tb]
    if wa == wb and policy != "all":
        # token-identical: whitespace/paragraphing is the only difference; keep the candidate
        return cand, []
    ops = _hunks(_aligned(wa, wb), inp, cand, ta, tb, rungs, policy)
    out = []
    log = []
    prev_end_b = 0        # candidate offset after the last emitted candidate segment
    prev_end_a = 0
    first = True
    reverted_in = False   # the last emitted segment was the INPUT's (a reverted edit)
    for op in ops:
        tag, s0, s1, d0, d1 = op
        if tag == "equal":
            seg = cand[tb[d0][0]:tb[d1 - 1][1]]
            gap = cand[prev_end_b:tb[d0][0]] if not first else cand[:tb[d0][0]]
            if reverted_in and not gap:
                # S140 promotion fix: after a reverted DELETION the candidate has no whitespace between the
                # restored span and this segment (it never had the tokens) — the prototype emitted
                # "I thought,so"; the input's own gap keeps the space (or the paragraph break)
                gap = inp[prev_end_a:ta[s0][0]]
            out.append(gap + seg)
            prev_end_b = tb[d1 - 1][1]
            prev_end_a = ta[s1 - 1][1]
            first = False
            reverted_in = False
            continue
        a_span = inp[ta[s0][0]:ta[s1 - 1][1]] if s1 > s0 else ""
        b_span = cand[tb[d0][0]:tb[d1 - 1][1]] if d1 > d0 else ""
        if policy == "all":
            accept = True
        elif policy == "none":
            accept = False
        else:
            accept = equivalent(a_span, b_span, rungs) if (a_span or b_span) else True
        log.append((label(a_span, b_span), accept, a_span, b_span))
        if accept:
            if d1 > d0:
                gap = cand[prev_end_b:tb[d0][0]] if not first else cand[:tb[d0][0]]
                if reverted_in and not gap:
                    gap = inp[prev_end_a:ta[s0][0]] if s0 < len(ta) else " "
                out.append(gap + b_span)
                prev_end_b = tb[d1 - 1][1]
            # an accepted pure deletion emits nothing
            reverted_in = False
        else:
            if s1 > s0:
                # the input's own preceding whitespace (a reverted deletion keeps its paragraphing)
                gap = inp[prev_end_a:ta[s0][0]] if not first else inp[:ta[s0][0]]
                if d1 > d0 and not first:
                    gap = cand[prev_end_b:tb[d0][0]] or gap
                out.append(gap + a_span)
                reverted_in = True
            # a reverted pure insertion emits nothing
            if d1 > d0:
                prev_end_b = tb[d1 - 1][1]
        if s1 > s0:
            prev_end_a = ta[s1 - 1][1]
        first = False
    tail = cand[prev_end_b:] if tb else inp[prev_end_a:]
    out.append(tail)
    return "".join(out), log


_NONWORD = re.compile(r"[^\w]")
_LIGS_IN_KEY = re.compile(r"ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|th")


def _key(tok: str) -> str:
    """The alignment key of a token: its whitelist-normalised form with punctuation, case and the ligature sequences
    removed, so `sat.` and `sat`, `*bold*` and `bold`, `Case` and `case`, `Di"cult` and `Difficult` align as the SAME
    position and the edit between them is judged on its own one-token span. A key only STEERS the alignment — the
    judgement is `equivalent()` on the raw spans, so a wrong key can cost a revert, never buy an accept."""
    return _LIGS_IN_KEY.sub("", _NONWORD.sub("", norm(tok, FULL)).casefold())


def _split_region(wa, wb, s0, s1, d0, d1):
    """The fine split of ONE non-equal region [s0,s1)×[d0,d1): opcodes over the tokens' KEYS inside the region, every
    key-equal run re-split where the raw tokens differ (`sat.` vs `sat` becomes its own one-token edit)."""
    ka = [_key(w) for w in wa[s0:s1]]
    kb = [_key(w) for w in wb[d0:d1]]
    out = []
    for o in Levenshtein.opcodes(ka, kb):
        if o.tag != "equal":
            out.append((o.tag, s0 + o.src_start, s0 + o.src_end, d0 + o.dest_start, d0 + o.dest_end))
            continue
        s, d = s0 + o.src_start, d0 + o.dest_start
        n = o.src_end - o.src_start
        k = 0
        while k < n:
            same = wa[s + k] == wb[d + k]
            j = k
            while j < n and (wa[s + j] == wb[d + j]) == same:
                j += 1
            out.append(("equal" if same else "replace", s + k, s + j, d + k, d + j))
            k = j
    return out


def _aligned(wa, wb):
    """S140: EXACT-token opcodes first — the prototype's anchors, which keep the input's order over long repetitive
    text — then, inside each non-equal region only, the KEY alignment (`_split_region`) so `sat.` vs `sat` no longer
    swallows a paragraph. Aligning a whole chunk on keys was tried and reordered DDIA's references (142 windows
    failed with every word present): keys steer only between exact anchors now."""
    out = []
    exact = [(o.tag, o.src_start, o.src_end, o.dest_start, o.dest_end) for o in Levenshtein.opcodes(wa, wb)]
    i = 0
    while i < len(exact):
        if exact[i][0] == "equal":
            out.append(exact[i])
            i += 1
            continue
        j = i
        while j < len(exact) and exact[j][0] != "equal":  # adjacent non-equal ops are ONE region between anchors
            j += 1
        s0, s1, d0, d1 = exact[i][1], exact[j - 1][2], exact[i][3], exact[j - 1][4]
        if s1 - s0 > 1 or d1 - d0 > 1:
            out.extend(_split_region(wa, wb, s0, s1, d0, d1))
        else:
            out.append(("replace" if s1 > s0 and d1 > d0 else ("delete" if s1 > s0 else "insert"), s0, s1, d0, d1))
        i = j
    return out


def _hunks(ops, inp, cand, ta, tb, rungs, policy):
    """S140: the opcodes as (tag, s0, s1, d0, d1) tuples with every run of adjacent NON-EQUAL opcodes tried as ONE
    hunk first. rapidfuzz splits `unex- pected` -> `unexpected` into a replace (`unex-` -> `unexpected`) and a delete
    (`pected`); judged alone neither is whitelisted, so the S119 prototype's hyphen and reflow rungs almost never fired
    (its DDIA counts: reflow 1, hyphen 0). A hunk that is equivalent under the rungs is one accepted edit; a hunk that
    is not falls back to its opcodes judged one by one, so an independent good edit beside a bad one still survives."""
    raw = list(ops)
    out = []
    i = 0
    while i < len(raw):
        if raw[i][0] == "equal":
            out.append(raw[i])
            i += 1
            continue
        j = i
        while j < len(raw) and raw[j][0] != "equal":
            j += 1
        run = raw[i:j]
        if policy == "whitelist":
            s0, s1 = run[0][1], run[-1][2]
            d0, d1 = run[0][3], run[-1][4]
            out.extend(_peel(inp, cand, ta, tb, s0, s1, d0, d1, rungs, run=run))
        else:
            out.extend(run)
        i = j
    return out


def _span_a(inp, ta, s0, s1):
    return inp[ta[s0][0]:ta[s1 - 1][1]] if s1 > s0 else ""


def _span_b(cand, tb, d0, d1):
    return cand[tb[d0][0]:tb[d1 - 1][1]] if d1 > d0 else ""


def _peel(inp, cand, ta, tb, s0, s1, d0, d1, rungs, depth=0, run=None):
    """A non-equal region [s0,s1)×[d0,d1) as a list of ops. Whole region equivalent → one accepted ("hunk"). Otherwise
    peel the LARGEST equivalent prefix pair (A[:i] ~ B[:j]) or suffix pair off and recurse on the remainder, so a
    merge with an insertion beside it (`unex- pected` + `quietly`) keeps its repair and reverts only the insertion.
    Bounded (regions ≤ 12×12 tokens, depth ≤ 6); beyond that the region is one op, judged whole by reconcile()."""
    m, n = s1 - s0, d1 - d0
    a_span, b_span = _span_a(inp, ta, s0, s1), _span_b(cand, tb, d0, d1)
    if (a_span or b_span) and equivalent(a_span, b_span, rungs):
        return [("hunk", s0, s1, d0, d1)]
    if m == 0 or n == 0 or (m == 1 and n == 1) or m > 12 or n > 12 or depth > 6:
        return [("replace" if m and n else ("delete" if m else "insert"), s0, s1, d0, d1)]
    best = None  # (size, i, j, side)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if i == m and j == n:
                continue
            if equivalent(_span_a(inp, ta, s0, s0 + i), _span_b(cand, tb, d0, d0 + j), rungs):
                if best is None or i + j > best[0]:
                    best = (i + j, i, j, "prefix")
            if equivalent(_span_a(inp, ta, s1 - i, s1), _span_b(cand, tb, d1 - j, d1), rungs):
                if best is None or i + j > best[0]:
                    best = (i + j, i, j, "suffix")
    if best is None:
        # no equivalent edge — the region's own ops, each tried with its next one or two (a merge rapidfuzz split
        # into replace + delete), else judged alone by reconcile()
        return _walk(inp, cand, ta, tb, run, rungs) if run else [("replace", s0, s1, d0, d1)]
    _, i, j, side = best
    if side == "prefix":
        return [("hunk", s0, s0 + i, d0, d0 + j)] + _peel(inp, cand, ta, tb, s0 + i, s1, d0 + j, d1, rungs, depth + 1)
    return _peel(inp, cand, ta, tb, s0, s1 - i, d0, d1 - j, rungs, depth + 1) + [("hunk", s1 - i, s1, d1 - j, d1)]


def _walk(inp, cand, ta, tb, run, rungs):
    out = []
    k = 0
    while k < len(run):
        took = False
        for w in (3, 2):
            if k + w <= len(run):
                s0, s1 = run[k][1], run[k + w - 1][2]
                d0, d1 = run[k][3], run[k + w - 1][4]
                a_span, b_span = _span_a(inp, ta, s0, s1), _span_b(cand, tb, d0, d1)
                if (a_span or b_span) and equivalent(a_span, b_span, rungs):
                    out.append(("hunk", s0, s1, d0, d1))
                    k += w
                    took = True
                    break
        if not took:
            out.append(run[k])
            k += 1
    return out


def tally(log: list) -> dict:
    """The edit log as counts by class: {"accepted": {class: n}, "reverted": {class: n}} — the manifest's
    `analyst.edits` sums these over the book; a chunk_scores row carries the two totals as "e"."""
    acc: collections.Counter = collections.Counter()
    rev: collections.Counter = collections.Counter()
    for lab, accepted, _, _ in log:
        (acc if accepted else rev)[lab] += 1
    return {"accepted": dict(acc), "reverted": dict(rev)}
