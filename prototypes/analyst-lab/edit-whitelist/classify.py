r"""Ask B — classify every difference between the analyst's input and its shipped output, in the
AUDIT'S OWN VIEW (the j32a-v2 ladder: punct_free(unescape(prepare_output(x))), casefolded, words),
and attribute each FAILED 12-word window of the real document audit to the class of the edit(s)
that overlap it.

Alignment: word-level opcodes (rapidfuzz Levenshtein.opcodes on the two word lists; difflib
SequenceMatcher would give the same tags with a different tie-break) per aligned chunk pair.

Classes (one per opcode, tested in this order, first hit wins):
  reflow        the two spans are the same characters with different word boundaries
                ("institu tional" -> "institutional", "chap ter" -> "chapter"): the space-free
                containment already absorbs these; they cost NO window.
  escape        equal once every backslash is removed (SYM-076: the ladder keeps `\` before a
                letter, so `within\recursive` vs `withinrecursive`).
  ligature      the OUTPUT span is the INPUT span with fi/fl/ff/ffi/ffl/st sequences INSERTED
                (Marker's dropped ligature glyphs — `dicult` -> `difficult`) — asymmetric: the
                model added letters that a ligature glyph would supply, nothing else changed.
  link-syntax   equal once `page<digits>` fragments are removed (a broken `[..](#page-n-m)` whose
                URL leaked into the text on one side).
  numeral       same span length, the digit-bearing words differ (`person(100,` -> `person(10,`).
  deletion      the output span is empty.
  insertion     the input span is empty.
  substitution  anything else with both spans non-empty.
"""
import collections
import json
import re
import sys

from rapidfuzz.distance import Levenshtein

from common import analyst, fa, load_bundle, ladder, tn  # noqa: F401
from align import build_pairs

# the ligature glyphs this PDF's fonts carry under OpenType names (Differences arrays read with
# pymupdf, S119 R1 a_probe3: f_f_i f_f_l f_f f_i f_l f_t f_k T_h ...); casefolded because the
# ladder casefolds ("%ere" -> "ere" -> "there")
LIG_ALT = "(?:ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|th)"
_DIGIT = re.compile(r"\d")


def is_lig_repair(a: str, b: str) -> bool:
    """b == a with ligature sequences INSERTED at some positions (a shorter than b, nothing else)."""
    if not (0 < len(b) - len(a) <= 3 * max(1, len(a))) or len(a) > 400:
        return False
    pat = LIG_ALT + "?" + (LIG_ALT + "?").join(re.escape(ch) for ch in a) + LIG_ALT + "?"
    return re.fullmatch(pat, b) is not None


def classify(a_words: list[str], b_words: list[str]) -> str:
    a = "".join(a_words)
    b = "".join(b_words)
    if not a_words:
        return "insertion"
    if not b_words:
        return "deletion"
    if a == b:
        return "reflow"
    if a.replace("\\", "") == b.replace("\\", ""):
        return "escape"
    if is_lig_repair(a, b):
        return "ligature"
    if re.sub(r"page\d+", "", a) == re.sub(r"page\d+", "", b):
        return "link-syntax"
    ad = [w for w in a_words if _DIGIT.search(w)]
    bd = [w for w in b_words if _DIGIT.search(w)]
    if (ad or bd) and ad != bd and len(a_words) == len(b_words):
        return "numeral"
    return "substitution"


def opcodes_words(a_words, b_words):
    ops = Levenshtein.opcodes(a_words, b_words)
    return [(op.tag, op.src_start, op.src_end, op.dest_start, op.dest_end) for op in ops]


def main():
    b = load_bundle()
    pairs, stats = build_pairs(b)
    embeds = b["embeds"]
    # the audit's own windows over the sidecar, and which fail (recomputed exactly as audit_analyst does)
    ref = ladder(b["sidecar_text"])
    out = ladder(b["shipped_body"])
    ref_words = ref.split()
    windows = tn.make_windows(ref, tn.is_cjk(ref[:4000]))
    out_flat = tn.space_free(out)
    failed = [tn.space_free(w) not in out_flat for w in windows]
    n_fail = sum(failed)
    print(f"doc windows {len(windows)}  failed {n_fail}  doc_survival {round(1 - n_fail / len(windows), 4)}")

    # per-chunk word offsets in the SAME stream: unfence each chunk, ladder it, concatenate
    stream = []
    chunk_word_start = []
    for p in pairs:
        chunk_word_start.append(len(stream))
        stream.extend(ladder(analyst.unfence(p["input"], embeds)).split())
    print("per-chunk stream == doc stream:", stream == ref_words, len(stream), len(ref_words))
    if stream != ref_words:
        # find first divergence for the record
        j = next((i for i, (x, y) in enumerate(zip(stream, ref_words)) if x != y), min(len(stream), len(ref_words)))
        print("   first divergence at word", j, stream[j:j + 5], ref_words[j:j + 5])

    # classify every opcode, per chunk, in the ladder view of the UNFENCED pair
    edits = []          # (chunk i, class, a_start_global, a_end_global, a_words, b_words)
    class_counts = collections.Counter()
    class_words_in = collections.Counter()
    per_status = collections.Counter()
    for k, p in enumerate(pairs):
        a_words = ladder(analyst.unfence(p["input"], embeds)).split()
        b_words = ladder(analyst.unfence(p["output"], embeds)).split()
        if a_words == b_words:
            per_status[(p["status"], "identical")] += 1
            continue
        per_status[(p["status"], "differs")] += 1
        base = chunk_word_start[k]
        for tag, s0, s1, d0, d1 in opcodes_words(a_words, b_words):
            if tag == "equal":
                continue
            cls = classify(a_words[s0:s1], b_words[d0:d1])
            class_counts[cls] += 1
            class_words_in[cls] += s1 - s0
            edits.append((p["i"], cls, base + s0, base + max(s1, s0 + 1), a_words[s0:s1], b_words[d0:d1]))
    print("pairs by status/identity:", dict(per_status))
    print("edits by class (count of opcodes):", class_counts.most_common())
    print("input words touched by class:", class_words_in.most_common())

    # attribute failed windows to classes: a window [12k, 12k+12) fails; the edits overlapping it
    PRIORITY = ["deletion", "substitution", "numeral", "ligature", "escape", "link-syntax", "insertion", "reflow"]
    win_class = collections.Counter()
    win_examples = collections.defaultdict(list)
    by_chunk = collections.defaultdict(list)
    for e in edits:
        by_chunk[e[0]].append(e)
    # index edits by window
    edits_by_win = collections.defaultdict(list)
    for e in edits:
        w0 = e[2] // tn.WINDOW_WORDS
        w1 = (e[3] - 1) // tn.WINDOW_WORDS
        for w in range(w0, w1 + 1):
            edits_by_win[w].append(e)
    for w, f in enumerate(failed):
        if not f:
            continue
        cands = edits_by_win.get(w, [])
        classes = {e[1] for e in cands}
        if not classes:
            win_class["unexplained"] += 1
            win_examples["unexplained"].append((w, windows[w][:80]))
            continue
        primary = next(c for c in PRIORITY if c in classes)
        win_class[primary] += 1
        if len(win_examples[primary]) < 6:
            e = next(e for e in cands if e[1] == primary)
            win_examples[primary].append((w, e[0], " ".join(e[4])[:70], "->", " ".join(e[5])[:70]))
    print("\nFAILED WINDOWS BY PRIMARY CLASS (numerator: failed 12-word windows of the sidecar; "
          f"denominator {len(windows)} windows; conditions: j32a-v2 ladder, space-free containment "
          "against the whole shipped body, class = highest-priority edit overlapping the window):")
    for c, n in win_class.most_common():
        print(f"   {c:14s} {n:5d}  ({round(100 * n / len(windows), 3)} % of all windows, {round(100 * n / n_fail, 1)} % of failed)")
    for c in win_examples:
        for ex in win_examples[c][:4]:
            print("     ", c, ex)

    # windows that would fail under classes the audit SHOULD be blind to (ligature/escape/link) vs content
    audit_blind = sum(win_class[c] for c in ("ligature", "escape", "link-syntax", "reflow"))
    content = sum(win_class[c] for c in ("deletion", "substitution", "numeral", "insertion"))
    print(f"\naudit-blindness windows {audit_blind}  content windows {content}  unexplained {win_class['unexplained']}")
    print("if every audit-blindness window were forgiven: doc_survival ->",
          round(1 - (n_fail - audit_blind) / len(windows), 4))
    print("if every content window were reverted to the input (and blindness stayed): doc_survival ->",
          round(1 - (n_fail - content) / len(windows), 4))

    # numeral census, clean: per pair, multiset of digit-bearing ladder words in vs out
    num_chunks, num_tokens = 0, 0
    for k, p in enumerate(pairs):
        a_words = ladder(analyst.unfence(p["input"], embeds)).split()
        b_words = ladder(analyst.unfence(p["output"], embeds)).split()
        ca = collections.Counter(w for w in a_words if _DIGIT.search(w))
        cb = collections.Counter(w for w in b_words if _DIGIT.search(w))
        missing = ca - cb
        if missing:
            num_chunks += 1
            num_tokens += sum(missing.values())
    print(f"\nnumeral census (ladder words with a digit, input multiset minus output multiset): "
          f"{num_chunks} chunks / {num_tokens} tokens not found in the output (denominator 492 pairs)")

    json.dump({"doc_windows": len(windows), "failed": n_fail, "class_counts_opcodes": class_counts,
               "failed_windows_by_class": win_class, "pairs_status": {f"{k[0]}/{k[1]}": v for k, v in per_status.items()},
               "numeral_census": {"chunks": num_chunks, "tokens": num_tokens}, "align_stats": stats},
              open("results_classify.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
