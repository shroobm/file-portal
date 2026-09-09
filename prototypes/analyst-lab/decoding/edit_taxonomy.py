"""prototypes/analyst-lab/decoding/edit_taxonomy.py -- WHAT did qwen3:8b change on DDIA, and which
changes cost survival windows? Over the aligned PASSED pairs (ddia_pairs), two censuses:

  1. EDIT census (raw text, whitespace-insensitive): every chunk whose output != input is classified
     by WHICH minimal transformations of the input reproduce the output. Applied cumulatively:
       span    -- Marker's `<span id="page-N-K"></span>` anchors removed
       escape  -- Marker's backslash escapes (`\\_`, `\\*`, `\\(`) removed
       heading -- heading marker lines rewritten (level or text) but the heading text kept
       punct   -- punctuation/quotes/spacing only (ladder punct_free equality)
       other   -- none of the above explains the remainder: wording, numerals, deletions, additions
  2. LOST-WINDOW census (the ladder, as the audit sees it): every input 12-word window that is NOT
     contained in the aligned output is classified:
       v3-escape   -- survives when `_` escapes are stripped before the markdown strip (J44 rung 1)
       v3b-ligature-- survives under the ligature-blind rung too (J44 rung 2)
       fuzzy>=90   -- rapidfuzz partial_ratio >= 90 against the output: a reword/reflow, the words are there
       fuzzy 70-90 -- partial: some of the window survives
       deletion    -- < 70: the window is gone
     plus the numeral check (input digit tokens missing from the output), per chunk.

Read-only; in-memory only; prints and writes taxonomy.json (numbers only, no book text).
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ddia_pairs  # noqa: E402
import text_norm as tn  # noqa: E402

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

SPAN = re.compile(r'<span id="[^"]*"></span>')
ESC = re.compile(r"\\(?=[^\w\s]|_)")
HEAD = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")
LIG = re.compile(r"ffi|ffl|fi|fl|ff")
NUM = re.compile(r"\d[\d,.]*\d|\d")
IMG = re.compile(r"⟦IMG-\d+⟧")
URL = re.compile(r"\]\([^)]*\)|https?://\S+")


def numeral_view(t: str) -> str:
    """digits that are CONTENT: strip span anchors, image tokens and link targets first."""
    return URL.sub("", IMG.sub("", SPAN.sub("", t)))
WS = re.compile(r"\s+")


def norm_ws(t: str) -> str:
    return WS.sub(" ", t).strip()


def classify_edit(inp: str, out: str) -> str:
    if norm_ws(inp) == norm_ws(out):
        return "identical"
    a, b = SPAN.sub("", inp), SPAN.sub("", out)
    if norm_ws(a) == norm_ws(b):
        return "span"
    a, b = ESC.sub("", a), ESC.sub("", b)
    if norm_ws(a) == norm_ws(b):
        return "escape"
    a, b = HEAD.sub("", a), HEAD.sub("", b)
    if norm_ws(a) == norm_ws(b):
        return "heading"
    if tn.punct_free(a) == tn.punct_free(b):
        return "punct"
    return "other"


CITE = re.compile(r"\(#page-[\d-]+\)")  # the anchor target of Marker's footnote/citation links


def prep(t: str, v3: bool = False, lig: bool = False, cite: bool = False) -> str:
    if cite:
        t = CITE.sub("", t)  # symmetric: `[\[2\]](#page-49-0)` and `[[2](#page-49-0)]` both -> `2`
    if v3:
        t = ESC.sub("", t)
    s = tn.punct_free(tn.unescape(tn.prepare_output(t)))
    if lig:
        s = LIG.sub("", s)
    return s


def main() -> None:
    m, chunks_in, outs, cs = ddia_pairs.pairs()
    edit = Counter()
    lost = Counter()
    n_pairs = 0
    windows_total = 0
    numeral_chunks = 0
    numeral_tokens = 0
    numeral_examples = []
    per_chunk_other = []
    words_removed = Counter(); words_removed_total = 0; words_added_total = 0
    for k, o in enumerate(outs):
        i = k + 1
        if o is None or cs[i].get("x"):
            continue
        c = chunks_in[k]
        n_pairs += 1
        edit[classify_edit(c, o)] += 1
        # lost windows under the shipped ladder
        ref = prep(c)
        out_flat = tn.space_free(prep(o))
        wins = tn.make_windows(ref, tn.is_cjk(ref[:4000]))
        windows_total += len(wins)
        out_v3 = tn.space_free(prep(o, v3=True))
        out_v3b = tn.space_free(prep(o, v3=True, lig=True))
        ref_v3 = prep(c, v3=True)
        ref_v3b = prep(c, v3=True, lig=True)
        wins_v3 = tn.make_windows(ref_v3, False)
        wins_v3b = tn.make_windows(ref_v3b, False)
        out_cite = tn.space_free(prep(o, v3=True, lig=True, cite=True))
        ref_cite = prep(c, v3=True, lig=True, cite=True)
        wins_cite = tn.make_windows(ref_cite, False)
        # the v3 ladders re-window, so match by index where counts agree, else by content
        for idx, w in enumerate(wins):
            if tn.space_free(w) in out_flat:
                continue
            w3 = wins_v3[idx] if idx < len(wins_v3) and len(wins_v3) == len(wins) else None
            w3b = wins_v3b[idx] if idx < len(wins_v3b) and len(wins_v3b) == len(wins) else None
            wc = wins_cite[idx] if idx < len(wins_cite) and len(wins_cite) == len(wins) else None
            if w3 is not None and tn.space_free(w3) in out_v3:
                lost["v3-escape"] += 1
            elif w3b is not None and tn.space_free(w3b) in out_v3b:
                lost["v3b-ligature"] += 1
            elif wc is not None and tn.space_free(wc) in out_cite:
                lost["cite-anchor (new rung)"] += 1
            elif fuzz is not None:
                sc = fuzz.partial_ratio(w, prep(o))
                if sc >= 90:
                    lost["fuzzy>=90 (reword/reflow)"] += 1
                elif sc >= 70:
                    lost["fuzzy 70-90 (partial)"] += 1
                else:
                    lost["deletion (<70)"] += 1
            else:
                lost["unclassified (no rapidfuzz)"] += 1
        a = Counter(NUM.findall(numeral_view(c)))
        b = Counter(NUM.findall(numeral_view(o)))
        miss = a - b
        wa = Counter(tn.punct_free(tn.prepare_output(c)).split())
        wb = Counter(tn.punct_free(tn.prepare_output(o)).split())
        removed = sum((wa - wb).values()); added = sum((wb - wa).values())
        wm = "0" if removed == 0 else "1-3" if removed <= 3 else "4-10" if removed <= 10 else "11-50" if removed <= 50 else ">50"
        words_removed[wm] += 1
        words_removed_total += removed; words_added_total += added
        if miss:
            numeral_chunks += 1
            numeral_tokens += sum(miss.values())
            if len(numeral_examples) < 8:
                numeral_examples.append((i, list(miss.items())[:3], list((b - a).items())[:3]))
    lost_total = sum(lost.values())
    print(f"aligned passed pairs: {n_pairs}; input windows {windows_total}; lost windows {lost_total} "
          f"({lost_total / windows_total * 100:.2f} % of these chunks' windows)")
    print(f"WORD multiset (ladder-normalised words): chunks by count of input words absent from output {dict(words_removed)}; total words removed {words_removed_total}, added {words_added_total}")
    print("EDIT census (chunk = smallest transformation explaining output):", dict(edit))
    print("LOST-WINDOW census:", {k: f"{v} ({v / lost_total * 100:.1f} %)" for k, v in lost.most_common()})
    print(f"numerals: {numeral_chunks} chunks with an input digit-token missing from output, {numeral_tokens} tokens; "
          f"examples (i, missing, extra): {numeral_examples}")
    (HERE / "taxonomy.json").write_text(json.dumps({
        "pairs": n_pairs, "windows_total": windows_total, "lost_total": lost_total,
        "edit_census": dict(edit), "lost_window_census": dict(lost),
        "numeral_chunks": numeral_chunks, "numeral_tokens": numeral_tokens,
        "numeral_examples": numeral_examples,
        "words_removed_buckets": dict(words_removed), "words_removed_total": words_removed_total, "words_added_total": words_added_total,
    }, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
