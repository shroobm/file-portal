"""windows-converter/ligature_repair.py -- THE LIGATURE REPAIR (SYM-148, S211 Lane C).

PURE MODULE: stdlib only (re, unicodedata). No pymupdf, no rapidfuzz, no I/O -- same posture
as text_norm.py, for the same reason: this must be importable and testable without marker-env.

The mechanism (S210 E4 e4_notes.md ## 1, ligature_probe.py, Observed on McGill's photonic
thesis): pdftext (pdfium, Marker's text provider) resolves a font's fi / fl / ff / ffi / ffl
ligature GLYPH -- one glyph standing for two or three letters -- as its FIRST LETTER ALONE.
MuPDF (fidelity_audit's witness reader) resolves the same glyph to its full letters. So the
source's text layer (pages_raw, what fidelity_audit.extract_witness reads per page and what
fidelity_audit.audit_inventions calls the witness) carries the whole word, and Marker's
markdown -- built on pdftext's reading -- carries the word with one ligature's worth of
letters missing: "coefficient" -> "coefcient" (the "ffi" ligature reads as "f"), "define" ->
"defne" (the "fi" ligature reads as "f"), "configuration" -> "confguration", "effect" ->
"efect" (the "ff" ligature reads as "f"). 660 letters lost this way on the McGill thesis
alone, one class among the four audit_inventions.dropped_letter is named for (fidelity_audit.
py:596-612, audit_inventions -- "dropped_letter": one letter off a lost word, SYM-148;
_one_edit at fidelity_audit.py:506-517 is that measure's own one-edit test, read but not
reused here: this module repairs a NAMED mechanism -- a specific ligature swallowing a
specific run of letters at a specific position -- not "any word one edit from another").

This repair puts the letters back FROM THE SOURCE'S OWN TEXT LAYER (pages_raw) and removes
nothing: a word is only ever rewritten to a form the layer itself already contains, and only
when that form is the UNIQUE such reading (candidates() below) -- an ambiguous word (more than
one ligature-expansion sitting in the layer) is left exactly as Marker wrote it and reported,
never guessed at.

Public API (module contract, S211 Lane C):
  LIGATURES = ("ffi", "ffl", "ff", "fi", "fl")               # longest first
  vocabulary(pages_raw)          -> set[str]                  # the layer's own words
  candidates(word, vocab)        -> list[str]                 # distinct in-vocab expansions
  repair(markdown, pages_raw)    -> (markdown, record)        # the repair pass
"""

import re
import unicodedata

# Longest ligature strings first: "ffi"/"ffl" must be tried before "ff"/"fi"/"fl" so a genuine
# three-letter ligature loss is not masked by a shorter, wrong two-letter guess landing in the
# vocabulary first -- candidates() collects every distinct hit regardless of this order (order
# only fixes iteration, not which candidates get found), but longest-first is the documented,
# deterministic reading order the module contract names.
LIGATURES = ("ffi", "ffl", "ff", "fi", "fl")

# fidelity_audit.audit_inventions's own word regex (fidelity_audit.py:530): runs of 3+ "word"
# characters that are neither digits nor underscore -- unicode-aware, so an accented layer word
# still counts. Cited verbatim so this module's vocabulary matches the measure's vocabulary;
# if that line ever changes, this one is now provably stale rather than silently drifted.
_LAYER_WORD_RE = re.compile(r"[^\W\d_]{3,}")

# The markdown-side scan is ASCII-letters-only and word-bounded on purpose: ligatures are an
# English/Latin-alphabet typesetting artifact (fi/fl/ff/ffi/ffl), and "the word is letters
# only" is one of the repairable AND-conditions in the module contract below.
_MD_WORD_RE = re.compile(r"\b[A-Za-z]+\b")

# A fenced code block (```...```, non-greedy, DOTALL so a fence can span lines) is left
# untouched end to end -- split() below alternates [prose, fence, prose, fence, ..., prose].
_FENCE_RE = re.compile(r"(```.*?```)", re.S)

# Minimum length of a repaired word (module contract: "len(word) >= 4").
_MIN_REPAIR_LEN = 4


def vocabulary(pages_raw):
    """set of the layer's own words: every pages_raw page joined, NFKC-folded (so a literal
    ligature code point already sitting in the layer -- SYM-146's class, a different mechanism
    from this one -- reads as its plain letters before the words are collected, exactly as
    audit_inventions folds the witness at fidelity_audit.py:550), then fidelity_audit's own
    word regex (line 530, cited above), lower-cased. Built once by repair() and handed to
    candidates() per distinct word; a caller with only witness pages (no PDF) can still use
    this directly."""
    text = unicodedata.normalize("NFKC", " ".join(pages_raw or []))
    return {w.lower() for w in _LAYER_WORD_RE.findall(text)}


def candidates(word, vocab):
    """Every DISTINCT expansion of `word` (lower-cased first) that lands in `vocab`: for each
    'f' in the word, in turn, replace that single 'f' with each of LIGATURES (in LIGATURES'
    order) and keep the result when it is in vocab. "coefcient" has one 'f'; only inserting
    "ffi" there lands in a layer that carries "coefficient", so candidates() returns exactly
    one entry. "fat" has one 'f' too, but BOTH inserting "fi" ("fiat") and inserting "fl"
    ("flat") can land in a layer that carries both real words -- two entries, deliberately: an
    ambiguous word is for repair() to refuse, not for this function to arbitrate."""
    w = word.lower()
    found = []
    for i, ch in enumerate(w):
        if ch != "f":
            continue
        for lig in LIGATURES:
            cand = w[:i] + lig + w[i + 1:]
            if cand in vocab and cand not in found:
                found.append(cand)
    return found


def _apply_case(original, replacement):
    """Preserve `original`'s case pattern on `replacement` (which is always lower-case, coming
    straight out of vocab): UPPER -> UPPER, Title -> Title, lower -> lower (no change needed,
    replacement is already lower)."""
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _is_protected(token):
    """True when `token` (a whitespace-delimited run) looks like a URL or filesystem path and
    must not be scanned for repairable words: it contains '/' or ':' anywhere, or a '.' that is
    NOT the token's very last character (an embedded dot, as in a filename, a hostname, or an
    abbreviation like "e.g." -- versus an ordinary sentence-final period, which is common and
    must not silently block every last word of every sentence from ever being repaired)."""
    if "/" in token or ":" in token:
        return True
    dot = token.find(".")
    return dot != -1 and dot != len(token) - 1


def _scan(part, on_word):
    """Walk one prose segment (already outside any fenced code block) token by token
    (whitespace-delimited, so surrounding whitespace is reproduced exactly on rejoin),
    skipping protected (URL/path) tokens whole, and within every other token call
    `on_word(match)` -> replacement-or-None for each letters-only word match. Returns the
    (possibly rewritten) segment, rejoined byte for byte outside the touched spans."""
    pieces = re.split(r"(\s+)", part)
    for i, tok in enumerate(pieces):
        if not tok or tok.isspace() or _is_protected(tok):
            continue

        def _sub(m, _on_word=on_word):
            repl = _on_word(m.group(0))
            return repl if repl is not None else m.group(0)

        pieces[i] = _MD_WORD_RE.sub(_sub, tok)
    return "".join(pieces)


def repair(markdown, pages_raw):
    """Repair every uniquely-resolvable ligature-dropped word in `markdown` using the source's
    own text layer (pages_raw) as the sole authority for what a repaired word may become.
    Builds the vocabulary ONCE from all pages, then decides once per DISTINCT letters-only word
    in the (non-fenced, non-URL/path) markdown that contains 'f':

      - already in vocab              -> untouched (it is already what the source has)
      - > 1 distinct candidate        -> untouched; recorded under skipped_ambiguous
      - exactly 1 candidate AND
        len(word) >= 4 AND word is letters-only  -> repaired everywhere it occurs, case-
                                                     preserved per occurrence
      - anything else (0 candidates, or 1 candidate on a < 4 letter word) -> untouched,
                                                                              unreported

    Fenced code blocks (``` ... ```) and URL/path-shaped tokens are never scanned. Nothing is
    ever removed: a word is only ever grown into a form the layer already contains.

    Returns (repaired_markdown, record); record always carries every key below. An empty (or
    absent) pages_raw makes no change and returns the input markdown byte for byte, with
    record["note"] == "no layer"."""
    if not pages_raw:
        return markdown, {
            "repairs": [], "words_repaired": 0, "occurrences": 0,
            "skipped_ambiguous": [], "vocabulary_words": 0, "note": "no layer",
        }

    vocab = vocabulary(pages_raw)
    parts = _FENCE_RE.split(markdown)   # even indices: prose : odd indices: fenced, untouched

    # Pass 1 (decide): every distinct lower-cased candidate word, scanned from prose only. The
    # decide pass must walk the SAME protected-token territory the apply pass does (a plain
    # finditer over the whole segment would also scan inside URLs/paths) -- reusing _scan with
    # a collector, rather than a second hand-rolled walk, makes that true by construction.
    seen = set()

    def _collect(word):
        lw = word.lower()
        if "f" in lw:
            seen.add(lw)
        return None

    for i, part in enumerate(parts):
        if i % 2 == 1:
            continue
        _scan(part, _collect)

    decisions = {}          # lower word -> lower repaired word
    skipped_ambiguous = []
    for lw in sorted(seen):
        if lw in vocab:
            continue                                    # already correct: untouched
        cands = candidates(lw, vocab)
        if len(cands) > 1:
            skipped_ambiguous.append({"from": lw, "candidates": cands})
        elif len(cands) == 1 and len(lw) >= _MIN_REPAIR_LEN and lw.isalpha():
            decisions[lw] = cands[0]
        # else: 0 candidates, or a single candidate on a word under the length floor ->
        # left exactly as Marker wrote it, and not reported (nothing was decided about it).

    # Pass 2 (apply): every occurrence of a decided word, case-preserved, counted.
    counts = {}

    def _apply(word):
        lw = word.lower()
        to = decisions.get(lw)
        if to is None:
            return None
        counts[lw] = counts.get(lw, 0) + 1
        return _apply_case(word, to)

    out_parts = []
    for i, part in enumerate(parts):
        out_parts.append(part if i % 2 == 1 else _scan(part, _apply))
    new_markdown = "".join(out_parts)

    repairs = sorted(
        ({"from": lw, "to": to, "count": counts.get(lw, 0)} for lw, to in decisions.items()),
        key=lambda r: (-r["count"], r["from"]),
    )
    return new_markdown, {
        "repairs": repairs,
        "words_repaired": len(repairs),
        "occurrences": sum(r["count"] for r in repairs),
        "skipped_ambiguous": skipped_ambiguous,
        "vocabulary_words": len(vocab),
    }


def apply_repairs(text, repairs):
    """S211 E3 (McGill-1 ~148: the repair rewrote 660 dropped-letter words in the shipped body — `frst` → `first` ×35,
    `efcient` → `efficient` ×34 — and the inventions measure read IDENTICAL numbers on the repaired and the unrepaired
    bundle, because it counts the words in the bundle's blocks record, not the body): the SAME decided map applied to any
    other text of the same conversion (a block's html), so the record and the shipped text describe the same words.
    `repairs` is the record's own list [{from, to, count}]; the decision is never re-made here (nothing is grown that the
    body's repair did not grow), fenced code and URL/path tokens are skipped as in repair(), case kept per occurrence.
    Returns (new_text, occurrences)."""
    decisions = {r["from"]: r["to"] for r in (repairs or []) if r.get("from") and r.get("to")}
    if not decisions or not text:
        return text, 0
    n = [0]

    def _apply(word):
        to = decisions.get(word.lower())
        if to is None:
            return None
        n[0] += 1
        return _apply_case(word, to)

    parts = _FENCE_RE.split(text)
    out = [part if i % 2 == 1 else _scan(part, _apply) for i, part in enumerate(parts)]
    return "".join(out), n[0]


_TAG_RE = re.compile(r"(<[^>]+>)")


def apply_repairs_html(html, repairs):
    """apply_repairs over a block's html: the tags are split out first (a word beside a closing tag would otherwise read
    as a path — `frst</b>` carries a slash — and be skipped), the text between them repaired, the tags kept byte for byte.
    Returns (new_html, occurrences)."""
    if not html or not repairs:
        return html, 0
    total = 0
    parts = _TAG_RE.split(html)
    for i, part in enumerate(parts):
        if i % 2 == 0 and part:
            parts[i], n = apply_repairs(part, repairs)
            total += n
    return "".join(parts), total
