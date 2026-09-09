r"""Ask A, second half — REPAIR THE REFERENCE (quarantined prototype, zero pipeline coupling).

Where the damage is born (S119 R1, a_probe2/a_probe3, Observed): the DDIA PDF's subset fonts put
their ligature glyphs at codes 0x21-0x29 under OpenType glyph names (`/Differences [33 /f_l /f_k
/f_f_i /f_t /T_h /f_f ...]`) with NO ToUnicode entry for those codes. MuPDF (pymupdf) resolves
the glyph NAME and yields U+FB01 'ﬁ' etc.; pdfium's FPDFText_GetUnicode — pdftext's per-char
call, Marker's provider — yields the raw code: '!', '"', '#', '$', '&', ''', ')', '%'. So Marker's
body carries `Di"cult`, `#rst`, `pro'les`, `%ere`, `trade-o\$s`. Separately, the PDF's OWN
ToUnicode maps the hyphen glyph `/uni2010` at code 0x21 to U+0021 — BOTH extractors print `Chap!`
+ newline + `ter`; that one is the producer's error, not an extractor's.

This script repairs Marker's body (the J33 sidecar, read-only; the repaired text stays in memory
and in this directory) by four rules, each counted:
  R-lig   an in-word or word-initial garble (optionally Marker-escaped, `\$`) between/before
          letters is replaced by the ONE ligature expansion (ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|
          Th) that yields a word in the PDF's own vocabulary (pymupdf get_text over all 673
          pages, NFKC-decomposed, casefolded); ambiguous or unknown -> left alone and counted.
          Apostrophes before s/t/re/ll/ve/d/m are English contractions and are not tried.
  R-hyph  `x!` + whitespace + lowercase -> the halves joined when the join is in the vocabulary.
  R-link  `[A](url)! [b](url)` (a link split across the hyphenated line) -> `[Ab](url)` when the
          two URLs are identical (structural: no vocabulary needed).
  R-cite  Marker's `[[n\]](#page-x-y)` -> `[n](#page-x-y)` (the form the model writes and the
          ladder's link regex can see; same target, same text).
Then the REAL audit is run on (repaired sidecar, shipped body) and on (repaired sidecar, the
edit-whitelist acceptor's FULL reconciled body) — what the audit would read if the reference
had been repaired before the analyst ran (approximation: the model would then have had nothing
to repair, so its output would differ slightly from today's shipped body).
"""
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "edit-whitelist"))
from common import PDF, analyst, fa, load_bundle  # noqa: E402

LIGS = ["ffi", "ffl", "ff", "fi", "fl", "ft", "fk", "fj", "fb", "fh", "st", "Th"]
# the garble may carry Marker's own escape (`trade-o\$s`: the `$` glyph code, escaped by markdownify);
# an apostrophe followed by a contraction ending is English, not a glyph, and is not tried
_GARBLE_IN = re.compile(r"(?<=[A-Za-z])\\?(?:[!\"#$&%)]|'(?!(?:s|t|re|ll|ve|d|m)\b))(?=[a-z])")
# word-initial: `%ere` -> There (T_h), `#rst` / `"rst` -> first (a word-initial fi). `(#page-..)` anchors
# are excluded by the lookbehind; a real opening quote before a word is tried and falls through the
# vocabulary gate (`"the` -> `Ththe`/`fithe`/... never a word) — counted under "R-lig unknown", harmless.
_GARBLE_START = re.compile(r"(?<![A-Za-z(])\\?[!\"#$&%](?=[a-z]{2,})")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_HYPH = re.compile(r"([A-Za-z]+)!\s+([a-z]+)")
_LINK_SPLIT = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)!\s+\[([a-z][^\]\n]*)\]\(([^)\n]+)\)")
# Marker's citation form `[[2\]](#page-490-0)` (markdownify escapes the inner bracket); the model
# rewrites it as `[2](#page-490-0)` and the ladder's link regex sees only the second form
_CITE = re.compile(r"\[\[(\d+)\\\]\]\((#page-[0-9-]+)\)")


def pdf_vocabulary() -> set[str]:
    import pymupdf
    doc = pymupdf.open(str(PDF))
    vocab = set()
    for i in range(doc.page_count):
        t = unicodedata.normalize("NFKC", doc[i].get_text())
        t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
        for w in _WORD.findall(t):
            vocab.add(w.casefold())
    return vocab


def repair(text: str, vocab: set[str], rules=("lig", "hyph", "link")) -> tuple[str, dict]:
    """Default rules: lig + hyph + link. `cite` is NOT a default: measured (S119 R1) it makes the
    audit WORSE when applied to the reference alone (0.9718 -> 0.9234), because the shipped body
    still carries Marker's `[[n\\]](url)` form wherever the model left it — a markup-form
    normalisation must be applied to BOTH sides (the ladder), never to one. Kept as a rule so the
    trap stays measurable."""
    counts = collections.Counter()
    examples = collections.defaultdict(list)
    unknown_words = collections.Counter()

    def fix_garble(m: re.Match) -> str:
        s, e = m.start(), m.end()
        # the word around the garble, hyphenated compounds included (`trade-o\$s` -> `trade-offs`)
        ws = s
        while ws > 0 and (text_now[ws - 1].isalpha() or text_now[ws - 1] == "-"):
            ws -= 1
        we = e
        while we < len(text_now) and (text_now[we].isalpha() or text_now[we] == "-"):
            we += 1
        word = text_now[ws:we].strip("-")
        ws = text_now.index(word, ws) if word else ws
        rel, glen = s - ws, e - s
        hits = [lig for lig in LIGS if (word[:rel] + lig + word[rel + glen:]).casefold() in vocab]
        if len(hits) == 1:
            counts["R-lig repaired"] += 1
            if len(examples["R-lig"]) < 8:
                examples["R-lig"].append(f"{word} -> {word[:rel] + hits[0] + word[rel + glen:]}")
            return hits[0]
        counts["R-lig ambiguous" if len(hits) > 1 else "R-lig unknown"] += 1
        unknown_words[word] += 1
        return m.group(0)

    out = text
    if "lig" in rules:
        text_now = out
        out = _GARBLE_IN.sub(fix_garble, out)
        text_now = out
        out = _GARBLE_START.sub(fix_garble, out)

    def fix_hyph(m: re.Match) -> str:
        joined = m.group(1) + m.group(2)
        if joined.casefold() in vocab:
            counts["R-hyph joined"] += 1
            if len(examples["R-hyph"]) < 6:
                examples["R-hyph"].append(f"{m.group(0)!r} -> {joined}")
            return joined
        counts["R-hyph left"] += 1
        if len(examples["R-hyph left"]) < 6:
            examples["R-hyph left"].append(m.group(0))
        return m.group(0)

    def fix_link(m: re.Match) -> str:
        a, u1, b_, u2 = m.groups()
        if u1 == u2:
            counts["R-link joined"] += 1
            if len(examples["R-link"]) < 4:
                examples["R-link"].append(f"{m.group(0)[:50]!r} -> [{a + b_}]({u1})"[:120])
            return f"[{a + b_}]({u1})"
        counts["R-link left (urls differ)"] += 1
        return m.group(0)

    if "link" in rules:
        out = _LINK_SPLIT.sub(fix_link, out)
    if "hyph" in rules:
        out = _HYPH.sub(fix_hyph, out)
    if "cite" in rules:
        out, n = _CITE.subn(r"[\1](\2)", out)
        counts["R-cite rewritten"] += n
    examples["R-lig unknown (top)"] = [f"{w} x{n}" for w, n in unknown_words.most_common(10)]
    return out, {"counts": dict(counts), "examples": dict(examples)}


def main():
    b = load_bundle()
    vocab = pdf_vocabulary()
    print("PDF vocabulary (pymupdf, NFKC, casefold):", len(vocab), "distinct words")
    repaired, rep = repair(b["sidecar_text"], vocab)
    print("repair counts:", rep["counts"])
    for k, v in rep["examples"].items():
        print(f"  {k}: {v}")
    sidecar, shipped = b["sidecar_text"], b["shipped_body"]
    before = fa.audit_analyst(sidecar, shipped)
    after = fa.audit_analyst(repaired, shipped)
    print(f"\naudit_analyst(sidecar, shipped):          doc_survival {before['doc_survival']}  runs {before['runs_total']}")
    print(f"audit_analyst(REPAIRED sidecar, shipped): doc_survival {after['doc_survival']}  runs {after['runs_total']}")
    per_rule = {}
    for rule in ("lig", "hyph", "link", "cite"):
        r1, _ = repair(sidecar, vocab, rules=(rule,))
        a1 = fa.audit_analyst(r1, shipped)
        per_rule[rule] = (a1["doc_survival"], a1["runs_total"])
        print(f"   rule {rule} alone: doc_survival {a1['doc_survival']}  runs {a1['runs_total']}")
    # combined with the acceptor (edit-whitelist FULL policy) — reference repaired AND edits gated
    from acceptor import FULL, run_policy
    from align import build_pairs
    pairs, _ = build_pairs(b)
    fenced_out, embeds_out = analyst.fence(shipped)
    body_full, _ = run_policy(pairs, embeds_out, "whitelist", FULL, "FULL")
    comb = fa.audit_analyst(repaired, body_full)
    print(f"audit_analyst(REPAIRED sidecar, acceptor-FULL body): doc_survival {comb['doc_survival']}  runs {comb['runs_total']}"
          f"  {'CLEARS 0.995' if comb['doc_survival'] >= 0.995 else 'below the 0.995 gate'}")
    for r in sorted(comb.get("runs") or [], key=lambda r: -(r.get("words") or 0))[:4]:
        print("     open run:", r.get("words"), "|", (r.get("excerpt") or "")[:90])
    # negative control: the vocabulary-gated rules with an EMPTY vocabulary must change nothing
    same, rep0 = repair(sidecar, set(), rules=("lig", "hyph"))
    print("control (empty vocabulary, rules lig+hyph): text unchanged =", same == sidecar, rep0["counts"])
    json.dump({"vocab": len(vocab), "repair": rep["counts"], "before": (before["doc_survival"], before["runs_total"]),
               "after": (after["doc_survival"], after["runs_total"]), "per_rule": per_rule,
               "repaired_plus_acceptor_full": (comb["doc_survival"], comb["runs_total"])},
              open(Path(__file__).with_name("results_repair.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
