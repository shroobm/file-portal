# -*- coding: utf-8 -*-
"""ligature_repair_selftest.py -- tripwires for ligature_repair.repair/candidates/vocabulary
(SYM-148, S211 Lane C). Hermetic: pages_raw as plain strings, markdown as plain strings -- no
PDF, no pipeline, stdlib only (matches ligature_repair.py's own posture; run under the uv
python, never marker-env). Each case violates the property its rule stands for: a word the
layer already carries stays untouched (the negative control); a word with two candidate
expansions in the layer is refused, not guessed at, and named under skipped_ambiguous; a word
under the length floor is never repaired even when its single candidate is unambiguous;
fenced code and URLs/paths are never touched; case is preserved per occurrence; an empty layer
changes nothing. Prints "N/N ok"."""
import sys

import ligature_repair as lr

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name,
                               ("  <- " + str(detail)[:200]) if (detail and not cond) else ""))


# A small shared "layer" (pages_raw): the correctly-spelled source text, as MuPDF would read it
# -- ligatures intact, unlike pdftext's first-letter-alone reading this module repairs.
LAYER = [
    "The coefficient of restitution was measured for each material and the definition of a "
    "finite sequence, which mathematicians define precisely, follows the configuration "
    "described above, whose effect on the differently shaped samples was noted.",
    "A government fiat currency differs from a flat tax in its origin, and off the record the "
    "ratio of assets to liabilities stayed of interest to the auditors.",
]

# 1 · the three specimen repairs named in the contract: coefcient/defne/confguration
r_md, rec = lr.repair(
    "The coefcient of restitution and the defne given for confguration were both cited.",
    LAYER,
)
case("coefcient -> coefficient, defne -> define, confguration -> configuration",
     r_md == "The coefficient of restitution and the define given for configuration were both cited.",
     r_md)
case("all three land in record.repairs with count 1 each, words_repaired 3, occurrences 3",
     {(x["from"], x["to"], x["count"]) for x in rec["repairs"]} ==
     {("coefcient", "coefficient", 1), ("defne", "define", 1), ("confguration", "configuration", 1)}
     and rec["words_repaired"] == 3 and rec["occurrences"] == 3, rec)

# 2 · efect -> effect (the "ff" ligature)
r_md2, rec2 = lr.repair("The efect was small but measurable.", LAYER)
case("efect -> effect (the ff ligature)", r_md2 == "The effect was small but measurable.", r_md2)

# 3 · case preserved: Title, UPPER, lower
r_md3, rec3 = lr.repair("Defne it. DEFNE it again. now defne it once more.", LAYER)
case("Defne -> Define (Title), DEFNE -> DEFINE (UPPER), defne -> define (lower), all three occurrences counted",
     r_md3 == "Define it. DEFINE it again. now define it once more."
     and rec3["repairs"] == [{"from": "defne", "to": "define", "count": 3}], r_md3)

# 4 · ambiguous: "fat" resolves to BOTH "fiat" and "flat" in this layer -- refused, not guessed
r_md4, rec4 = lr.repair("It read as a fat statement to the committee.", LAYER)
case("an ambiguous word (fat -> fiat or flat, both in the layer) is left exactly as written",
     r_md4 == "It read as a fat statement to the committee.", r_md4)
case("...and is named under skipped_ambiguous with both candidates, and makes no repair entry",
     rec4["skipped_ambiguous"] == [{"from": "fat", "candidates": ["fiat", "flat"]}]
     and rec4["repairs"] == [] and rec4["words_repaired"] == 0, rec4)

# 5 · negative control: a word already in the layer is untouched even though the layer ALSO
# carries a longer word sharing its letters ("of" and "off" both real, both present) -- "of"
# must never be treated as a dropped-letter reading of "off" or of anything else
r_md5, rec5 = lr.repair("The ratio of the fund was of interest.", LAYER)
case("a word already in the layer (of) is untouched -- no repair, no skip -- even with `off` also in the layer",
     r_md5 == "The ratio of the fund was of interest."
     and rec5["repairs"] == [] and rec5["skipped_ambiguous"] == [], rec5)

# 6 · a fenced code block is never touched, even though it carries a repairable-looking word
FENCED = "Outside confguration text.\n\n```\ndef f(confguration):\n    return confguration\n```\n\nMore confguration outside."
r_md6, rec6 = lr.repair(FENCED, LAYER)
case("occurrences inside the fenced block are untouched; only the two outside are repaired",
     "```\ndef f(confguration):\n    return confguration\n```" in r_md6
     and r_md6.count("configuration") == 2 and r_md6.count("confguration") == 2  # the 2 fenced survive verbatim
     and rec6["repairs"] == [{"from": "confguration", "to": "configuration", "count": 2}], r_md6)

# 7 · a URL/path carrying the word is never touched (contains '/' and '.')
r_md7, rec7 = lr.repair(
    "See http://example.com/confguration.html and also plain confguration in prose.", LAYER)
case("a URL token (/, ., :) is left untouched; the same word in plain prose is repaired",
     "http://example.com/confguration.html" in r_md7
     and r_md7.endswith("and also plain configuration in prose.")
     and rec7["repairs"] == [{"from": "confguration", "to": "configuration", "count": 1}], r_md7)

# 7b · a bare filesystem path (colon + backslash-free forward slash form, and a Windows drive
# colon) is likewise left untouched
r_md7b, rec7b = lr.repair("The file at C:/temp/confguration.md was read; confguration elsewhere.",
                           LAYER)
case("a Windows-drive path token (colon, slash, dot) is untouched; the same word in prose is repaired",
     "C:/temp/confguration.md" in r_md7b
     and r_md7b.endswith("configuration elsewhere.")
     and rec7b["repairs"] == [{"from": "confguration", "to": "configuration", "count": 1}], r_md7b)

# 8 · a sentence-final period does NOT block repair (only an EMBEDDED dot, as in a path or an
# abbreviation, marks a token as protected) -- this is the module's own documented reading of
# "URLs / paths containing ... '.'", distinct from an ordinary full stop
r_md8, rec8 = lr.repair("This is the confguration.", LAYER)
case("a plain sentence-ending period does not stop the word before it from being repaired",
     r_md8 == "This is the configuration.", r_md8)

# 9 · a 3-letter word is NEVER repaired, even with exactly one unambiguous candidate in the
# layer (len(word) >= 4 is a hard floor, independent of the ambiguity check in case 4)
LAYER_SHORT = LAYER + ["A rare proper noun fion appears once in this appendix only."]
r_md9, rec9 = lr.repair("It was a fon of some kind.", LAYER_SHORT)
case("candidates('fon', vocab) finds exactly one hit (fion) -- the ambiguity gate alone would allow it",
     lr.candidates("fon", lr.vocabulary(LAYER_SHORT)) == ["fion"], None)
case("...but a 3-letter word is never repaired regardless: markdown unchanged, no repair, no skip entry for it",
     r_md9 == "It was a fon of some kind."
     and rec9["repairs"] == [] and rec9["skipped_ambiguous"] == [], rec9)

# 10 · the same word is repaired everywhere it occurs, and counted right
MANY = "confguration confguration. Another confguration here, and one more confguration."
r_md10, rec10 = lr.repair(MANY, LAYER)
case("the same corrupted word is repaired at all four occurrences, count == 4",
     r_md10.count("configuration") == 4 and r_md10.count("confguration") == 0
     and rec10["repairs"] == [{"from": "confguration", "to": "configuration", "count": 4}], r_md10)

# 11 · no layer at all (empty pages_raw) -> no change, and the record says why
r_md11, rec11 = lr.repair("The confguration was never checked against anything.", [])
case("an empty pages_raw makes no change to the markdown",
     r_md11 == "The confguration was never checked against anything.", r_md11)
case("...and the record carries note == 'no layer' with every other key at its empty/zero shape",
     rec11 == {"repairs": [], "words_repaired": 0, "occurrences": 0,
               "skipped_ambiguous": [], "vocabulary_words": 0, "note": "no layer"}, rec11)

# 12 · vocabulary(): the layer's own words, lower-cased, matching fidelity_audit's word_re
# shape (runs of 3+ letters; a 2-letter token like "of" is itself in vocab only because "of"
# is 2 letters -- wait: fidelity_audit's word_re is {3,}, so "of" must NOT be in vocabulary()
vocab = lr.vocabulary(LAYER)
case("vocabulary() keeps only 3+ letter runs (fidelity_audit.py:530's own floor) -- 'of' (2 letters) is excluded",
     "of" not in vocab and "off" in vocab and "coefficient" in vocab and "definition" in vocab, sorted(vocab)[:20])
case("vocabulary() is lower-cased regardless of source case",
     lr.vocabulary(["A CAPITALIZED Definition Of Something"]) == {"capitalized", "definition", "something"},
     lr.vocabulary(["A CAPITALIZED Definition Of Something"]))

# 13 · candidates(): the pure expansion function, independent of repair()'s length/ambiguity
# gates -- exercises LIGATURES order and "distinct" (no duplicate entries)
case("candidates('coefcient', vocab-with-coefficient) finds exactly ['coefficient']",
     lr.candidates("coefcient", {"coefficient"}) == ["coefficient"], None)
case("candidates() is case-insensitive on its `word` argument",
     lr.candidates("COEFCIENT", {"coefficient"}) == ["coefficient"], None)
case("candidates() on a word with no 'f' at all is empty",
     lr.candidates("banana", {"banana"}) == [], None)
case("candidates() finds nothing when no expansion lands in vocab",
     lr.candidates("xfyz", {"somethingelse"}) == [], None)

# 14 · LIGATURES is exactly the five forms, longest first, as the contract names them
case("LIGATURES == ('ffi', 'ffl', 'ff', 'fi', 'fl')", lr.LIGATURES == ("ffi", "ffl", "ff", "fi", "fl"), lr.LIGATURES)

# 15 · repairs sorted by count desc (a second, less-frequent repair in the same pass)
MIXED = "confguration confguration defne."
r_md15, rec15 = lr.repair(MIXED, LAYER)
case("repairs sorted by count desc: confguration (2) before defne (1)",
     [x["from"] for x in rec15["repairs"]] == ["confguration", "defne"], rec15["repairs"])

print("==== ligature_repair selftest: %d/%d ====" % (ok, n))
print("%d/%d ok" % (ok, n))
sys.exit(0 if ok == n else 1)
