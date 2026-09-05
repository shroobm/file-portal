"""windows-converter/text_norm.py -- the pure normalisation ladder (docs/15 SS3, docs/54 J32-A).

PURE MODULE: no pymupdf, no rapidfuzz, no I/O. This is deliberate -- analyst.py imports this
module too (J32-B's per-chunk survival guard, analyst.py:299 process()), and analyst.py must
never be forced to carry fidelity_audit's heavy witness-extraction dependencies just to check
whether a chunk survived its own rewrite. fidelity_audit.py imports its PUBLIC pure names back
from here (prepare_output, make_windows, _merge_runs, is_cjk, the window constants) so its own
callers (audit_convert, the docs/54 verification scripts, every selftest that reaches `fa.X`)
see the identical byte-for-byte behaviour they always did -- audit_convert's numbers must not
move (J32-A ticket, coordinator's acceptance).

Two families of function live here:

  1. The SHARED core (moved verbatim from fidelity_audit.py, J32-A): _common/_finalize/
     _strip_markdown/prepare_output, make_windows/_merge_runs/is_cjk, and the window
     constants. audit_convert (witness-vs-Marker) keeps using these exactly as before.

  2. The NORMALISATION LADDER (new, J32-A/B): unescape/punct_free/space_free, and
     chunk_survival -- the per-chunk input-window containment measure J32-B's accept-time
     guard calls (analyst.py:299). These exist because the analyst-stage comparison
     (fidelity_audit.audit_analyst, and now the chunk-level guard) was counting Marker's own
     backslash escapes, punctuation and spacing choices as LOSS: qwen3:8b routinely rewrites
     `\\(1960-2023\\)` to `(1960-2023)` or moves a comma, and prepare_output alone has no way
     to see those as the same text (docs/54-repair-road/README.md SS2: ~3.7x over-count in
     windows, ~7x on Univ 4e). The ladder is applied on BOTH sides of every comparison it
     touches, so it can only narrow disagreement, never manufacture it.
"""

import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------------------
# Window constants (docs/15 SS4). Unchanged from fidelity_audit.py's originals.
# ---------------------------------------------------------------------------
WINDOW_WORDS = 12          # non-overlapping window size (word path)
WINDOW_MIN_WORDS = 6       # keep a short final window if at least this many words
CJK_WINDOW_CHARS = 24      # char-n-gram window for CJK (no word boundaries)
CJK_WINDOW_MIN = 12

_CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ가-힯]")
_QUOTES = str.maketrans({
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "–": "-", "—": "-", "‐": "-", "‑": "-", "«": '"', "»": '"',
})
_DEHYPHEN = re.compile(r"(\w)-\n(\w)")
_WS = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# The shared core (docs/15 SS3), moved verbatim from fidelity_audit.py -- do not change this
# section's behaviour without re-measuring audit_convert (the fidelity_audit_selftest /
# degeneration_selftest / latex_balance_selftest battery is the control).
# ---------------------------------------------------------------------------
def _common(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_QUOTES)
    text = _DEHYPHEN.sub(r"\1\2", text)
    return text


def _finalize(text: str) -> str:
    return _WS.sub(" ", text.casefold()).strip()


def _strip_markdown(t: str) -> str:
    t = re.sub(r"!\[\[[^\]]*\]\]", " ", t)                 # ![[assets/img]] embeds
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)            # ![alt](url) images
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)              # [[wikilink]] -> inner
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)         # [text](url) -> text
    t = re.sub(r"<[^>\n]+>", " ", t)                       # html tags
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", " ", t)           # headings
    t = re.sub(r"(?m)^\s*>\s?", " ", t)                    # blockquote markers
    t = re.sub(r"(?m)^\s*`{3,}.*$", " ", t)                # fenced-code marker lines
    t = re.sub(r"(?m)^\s*\|?[\s:|-]{3,}\|?\s*$", " ", t)   # table separator rows
    t = t.replace("|", " ")                                # table pipes
    t = re.sub(r"[*_~`]", "", t)                           # emphasis / inline-code markers
    return t


def prepare_output(markdown: str) -> str:
    return _finalize(_strip_markdown(_common(markdown)))


def is_cjk(text: str) -> bool:
    sample = re.sub(r"\s", "", text)[:4000]
    if not sample:
        return False
    return len(_CJK.findall(sample)) / len(sample) > 0.3


def make_windows(text: str, cjk: bool) -> list[str]:
    if cjk:
        s = text.replace(" ", "")
        out = [s[i:i + CJK_WINDOW_CHARS] for i in range(0, len(s), CJK_WINDOW_CHARS)]
        return [w for w in out if len(w) >= CJK_WINDOW_MIN]
    words = text.split()
    out = []
    for i in range(0, len(words), WINDOW_WORDS):
        chunk = words[i:i + WINDOW_WORDS]
        if len(chunk) >= WINDOW_MIN_WORDS:
            out.append(" ".join(chunk))
    return out


def _merge_runs(windows: list[str], failed: list[bool], page) -> list[dict]:
    runs, i = [], 0
    while i < len(windows):
        if failed[i]:
            j = i
            while j < len(windows) and failed[j]:
                j += 1
            if j - i >= 2:  # RUN_MIN_WINDOWS (fidelity_audit.py) -- kept a bare 2 here so
                             # this module carries no dependency on fidelity_audit's constant
                span = windows[i:j]
                words = sum(len(w.split()) for w in span)
                runs.append({
                    "page": page,
                    "words": words,
                    "excerpt": " ".join(span[0].split()[:10]),
                })
            i = j
        else:
            i += 1
    return runs


# ---------------------------------------------------------------------------
# The normalisation ladder (J32-A, docs/54-repair-road/README.md SS2, signed: Proposal A).
#
# unescape() -- CHOICE AND WHY (ticket J32-A step 1): two shapes were on the table.
#
#   lane A (docs/54-repair-road/scripts/A-ladder.py):  re.sub(r"\\(.)", r"\1", t)
#   verifier   (docs/54-repair-road/scripts/V-v_a.py:77-81):  re.sub(r"\\(?=[^\w\s])", "", t)
#
# Lane A's `\\(.)` matches a backslash followed by ANY single character and replaces the
# WHOLE match with just that character -- it strips the backslash unconditionally, including
# before a LETTER. That is wrong: Marker emits genuine LaTeX macros this way (`\rm`, `\times`,
# `\alpha`), and a backslash there is not an escape to be undone, it is the command itself --
# stripping it changes `\rm` into the bare letters `rm`, a real content difference the ladder
# must never manufacture as "agreement". The verifier's shape uses a LOOKAHEAD: it consumes
# and deletes ONLY the backslash, and only when the very next character is neither a word
# character nor whitespace (`[^\w\s]` -- punctuation or symbol). A backslash before a letter,
# digit or underscore is left completely alone; `\(1960-2023\)` -> `(1960-2023)` (an escaped
# paren Marker adds around LaTeX-flavoured page ranges) but `\rm` stays `\rm`. This module
# takes the verifier's shape for that reason: it is the one that cannot mistake a formatting
# escape for a content-bearing command.
_UNESCAPE = re.compile(r"\\(?=[^\w\s])")
# punct_free(): DROP (not replace-with-space) every char outside \w\s, then collapse
# whitespace -- exactly the shape docs/54-repair-road/README.md J32-A step 1 specifies and
# lane A's script measured (A-ladder.py punct_free). Applied identically to both sides of
# every comparison this module feeds, so a merge like "e.g." -> "eg" costs nothing: the same
# merge happens to the reference and the candidate alike.
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def unescape(t: str) -> str:
    """Strip a lone backslash immediately before a punctuation/symbol character. A backslash
    before a letter/digit/underscore (LaTeX \\rm and friends) is left untouched -- see the
    module-level note above for why this shape was chosen over lane A's `\\(.)`."""
    return _UNESCAPE.sub("", t)


def punct_free(t: str) -> str:
    """Drop every character outside [\\w\\s], then collapse whitespace runs to one space."""
    return _WS.sub(" ", _PUNCT.sub("", t)).strip()


def space_free(t: str) -> str:
    """Strip ALL whitespace -- the final step of the ladder, used only for the containment
    test itself (never for window construction: windows stay word-split so `words` counts
    stay meaningful, per the ticket)."""
    return _WS.sub("", t)


def chunk_survival(input_text: str, output_text: str) -> float | None:
    """J32-B's per-chunk accept-time guard (analyst.py:299 process(), after the fence check
    passes): the fraction of the INPUT chunk's 12-word windows, built on the SAME normalisation
    ladder as J32-A's analyst-stage audit, that survive space-free containment in the
    normalised OUTPUT. `input_text`/`output_text` are the FENCED chunk and candidate (the
    ⟦IMG-n⟧ tokens are just more text to this ladder -- punct_free strips their brackets and
    hyphen but leaves `IMG` + the digits, identically on both sides, so a token substitution
    cannot masquerade as prose survival and cannot cost a real prose window either).

    Returns None -- not 0.0 -- when the input has no scoreable windows at all (a short chunk):
    SYM-057's rule is that an unmeasurable result must never read as a clean one, and here the
    caller's rule is the mirror image -- an unmeasurable result must never read as a FAILING
    one either, so `survival is None` must never be rejected."""
    ref = punct_free(unescape(prepare_output(input_text)))
    out = punct_free(unescape(prepare_output(output_text)))
    cjk = is_cjk(ref[:4000])
    windows = make_windows(ref, cjk)
    if not windows:
        return None
    out_flat = space_free(out)
    survived = sum(1 for w in windows if space_free(w) in out_flat)
    return round(survived / len(windows), 4)
