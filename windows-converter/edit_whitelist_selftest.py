# -*- coding: utf-8 -*-
"""edit_whitelist_selftest.py — the tripwire for edit_whitelist.py (J46, S140; docs/32 §6: a guard born today gets its
tripwire today). Two CONTROLS first (accept-all returns the candidate byte-for-byte; accept-none returns the input's
words), then one case per whitelist rung with its NEGATIVE control (the edit the rung must NOT admit), then the classes
the whitelist reverts by policy (numeral, deletion, insertion, substitution, punctuation/case — Rab's slot), the S140
promotion fix (a reverted deletion keeps its whitespace), and tally(). The count is derived from the cases, never typed.
Run: C:/Users/Bndit/ml/marker-env/Scripts/python.exe windows-converter/edit_whitelist_selftest.py   (rapidfuzz lives there)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit_whitelist as ew  # noqa: E402

results = []


def case(name, ok, note=""):
    results.append(bool(ok))
    print("  [%2d] %s %s%s" % (len(results) - 1, "ok " if ok else "RED", name, ("  — " + note) if note else ""))


def rec(inp, cand, rungs=ew.FULL, policy="whitelist"):
    return ew.reconcile(inp, cand, rungs, policy)


# ---- controls
inp = "The 81 cats sat.\n\nDi\"cult unex- pected `code` [[2\\]](#p-1) %ere."
cand = "The 18 cats sat quietly.\n\nDifficult unexpected code [2](#p-1) There. /no_think"
text, log = rec(inp, cand, ew.FULL, "all")
case("CONTROL accept-all returns the candidate byte-for-byte", text == cand and all(a for _, a, _, _ in log))
text, log = rec(inp, cand, set(), "none")
case("CONTROL accept-none returns the input's words", text.split() == inp.split() and not any(a for _, a, _, _ in log))
case("CONTROL a token-identical pair returns the candidate (whitespace is the candidate's)",
     rec("a b\n\nc", "a b\nc")[0] == "a b\nc" and rec("a b\n\nc", "a b\nc")[1] == [])

# ---- the rungs, each with its negative
t, lg = rec("a\\_b and c", "a_b and c")
case("escape: a removed markdown backslash-escape is accepted", t == "a_b and c" and lg[0][0] == "escape" and lg[0][1])
t, lg = rec("run \\rm now", "run rm now")
case("escape NEGATIVE: `\\rm` -> `rm` is not an escape and is reverted", t == "run \\rm now" and not lg[0][1])
t, lg = rec("see [[2\\]](#page-1) here", "see [2](#page-1) here")
case("link: a re-syntaxed citation with the same URL is accepted", t == "see [2](#page-1) here" and lg[0][1])
t, lg = rec("see [t](http://a) here", "see [t](http://b) here")
case("link NEGATIVE: a re-targeted URL is reverted", t == "see [t](http://a) here" and not lg[0][1])
t, lg = rec("see [t](http://a) here", "see t here")
case("link NEGATIVE: a dropped link is reverted", t == "see [t](http://a) here" and not lg[0][1])
t, lg = rec("see [An Overview](http://a) and more", "see An Overview](http://a) and more")
case("markup NEGATIVE: a dropped opening `[` of a link is reverted (link structure is not markup; DDIA references, S140)",
     t == "see [An Overview](http://a) and more" and not any(acc for _, acc, _, _ in lg))
t, lg = rec("## Title here", "Title here")
case("markup: a dropped heading mark is accepted", t == "Title here" and lg[0][1] and lg[0][0] == "markup")
t, lg = rec("a *bold* word", "a bold word")
case("markup: dropped emphasis is accepted", t == "a bold word" and lg[0][1])
t, lg = rec("an unex- pected turn", "an unexpected turn")
case("hyphen: a line-end hyphen join is accepted", t == "an unexpected turn" and lg[0][1] and lg[0][0] == "hyphen")
t, lg = rec("a well-known case", "a wellknown case")
case("hyphen NEGATIVE: dropping a compound's hyphen (no whitespace after it) is reverted", t == "a well-known case" and not lg[0][1])
# the rung's blind spot, named: `well- known` (hyphen + space + lowercase) IS the shape of a line-end hyphenation in
# Marker's output, so the rung joins it — a compound broken across a line is indistinguishable from a hyphenated word
t, lg = rec("a well- known case", "a wellknown case")
case("hyphen BLIND SPOT (documented): `well- known` -> `wellknown` is accepted as a line-end join", t == "a wellknown case" and lg[0][1])
t, lg = rec("it was Di\"cult", "it was Difficult")
case("ligature: `Di\"cult` -> `Difficult` is accepted", t == "it was Difficult" and lg[0][1] and lg[0][0] == "ligature")
t, lg = rec("%ere it is", "There it is")
case("ligature: a word-start garble `%ere` -> `There` is accepted", t == "There it is" and lg[0][1])
t, lg = rec("it was Di\"cult", "it was Dicult")
case("ligature NEGATIVE: a dropped garble with no replacement is reverted", t == "it was Di\"cult" and not lg[0][1])
t, lg = rec("it is ne", "it is fine")
case("ligature NEGATIVE: `ne` -> `fine` (no garble to replace) is reverted and named", t == "it is ne" and not lg[0][1] and lg[0][0] == "substitution")
t, lg = rec("an unexpect edly long", "an unexpectedly long")
case("reflow: a moved word boundary is accepted", t == "an unexpectedly long" and lg[0][1] and lg[0][0] == "reflow")

# ---- what the policy reverts
t, lg = rec("the 81 cats", "the 18 cats")
case("numeral: a changed numeral is reverted and named", t == "the 81 cats" and not lg[0][1] and lg[0][0] == "numeral")
t, lg = rec("I thought, so it goes", "so it goes")
case("deletion at the chunk start is reverted WITH its space (S140 promotion fix)", t == "I thought, so it goes" and lg[0][0] == "deletion")
t, lg = rec("para one.\n\npara two.\n\npara three.", "para one.\n\npara three.")
case("deletion of a paragraph is reverted with its paragraphing", t == "para one.\n\npara two.\n\npara three.")
t, lg = rec("the end", "the")
case("deletion at the chunk end is reverted", t == "the end")
t, lg = rec("a heading here", "a heading here /no_think")
case("insertion: a leaked `/no_think` is reverted and named", t == "a heading here" and not lg[0][1] and lg[0][0] == "insertion")
t, lg = rec("cost (minimizing risk)", "cost (minim,izing risk)")
case("substitution: `(minimizing` -> `(minim,izing` is reverted (S119's catch)", t == "cost (minimizing risk)" and not lg[0][1])
t, lg = rec("E SCAPING the room", "ESCAPPING the room")
case("substitution: `E SCAPING` -> `ESCAPPING` (Zero to One's misspelling) is reverted", t == "E SCAPING the room" and not lg[0][1])
t, lg = rec("one. two", "one, two")
case("punctuation: `.` -> `,` is reverted (Rab's slot)", t == "one. two" and not lg[0][1] and lg[0][0] == "punctuation/case")
t, lg = rec("the Case", "the case")
case("case: a case change is reverted (Rab's slot)", t == "the Case" and not lg[0][1] and lg[0][0] == "punctuation/case")

# ---- mixed and the tally
t, lg = rec(inp, cand)
tl = ew.tally(lg)
case("the mixed pair: whitelisted edits accepted (as hunks), the rest reverted each on its own",
     t == "The 81 cats sat.\n\nDifficult unexpected code [2](#p-1) There." and tl["reverted"].get("numeral") == 1
     and tl["reverted"].get("punctuation/case") == 1 and tl["reverted"].get("insertion") == 2
     and sum(tl["accepted"].values()) >= 2, "got %r %r" % (t, tl))
case("tally counts every log entry once", sum(tl["accepted"].values()) + sum(tl["reverted"].values()) == len(lg))
case("STRICT reverts a ligature repair FULL accepts", rec("it was Di\"cult", "it was Difficult", ew.STRICT)[0] == "it was Di\"cult")

n, ok = len(results), sum(results)
print("edit_whitelist selftest: %d/%d green%s" % (ok, n, "" if ok == n else "  *** RED ***"))
sys.exit(0 if ok == n else 1)
