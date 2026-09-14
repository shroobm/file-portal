"""table_geometry_selftest — the reading half's tripwires (S150). Every rule with a case and a negative control.
    python table_geometry_selftest.py
"""
from __future__ import annotations

import sys

import table_geometry as tg

FAILS = 0
N = 0


def check(name, cond, detail=""):
    global FAILS, N
    N += 1
    if cond:
        print("  ok   " + name)
    else:
        FAILS += 1
        print("  FAIL " + name + (" — " + detail if detail else ""))


VALENTINE = """Exhibit 8.2 Best Practice (Knowledge): Questions to Investigate before or during Interviews with Management (continued)

|                  | Start with this source to investigate before meeting management |    |    |    |    |    |    |    |    | ment |    |    |
|------------------|---|---|---|---|---|---|---|---|---|---|---|---|
|                  | Questions to be investigated | Company documents,<br>data, and website | Market data & news<br>provider | Industry trade journal or<br>website | Economic data | Company investor<br>relations contact | Sell-side report or model<br>(for buy-side analysts) | Customer of or supplier to the company | Information from<br>forecasting service | Consultant, expert, or company retiree | Sell-side analyst<br>(for the buy-side) | Appropriate to ask<br>executives at meeting |
|                  | Does the company or its competitors have pricing power? | • |  |  |  | • | • | • |  | • | • |  |
| R                | How does the company set pricing? |  |  |  |  | • |  | • |  | • | • | • |
| l v              | Have there been any major customer wins or losses recently? |  | • | • |  | • |  |  |  | • | ٠ | • |
| Ė<br>N           | Which factors are most likely to cause a material change in demand? |  |  |  |  | • | • | • | • | • | • | • |
| U<br>E           | Where will growth come from (economic, market share gains or new markets)? |  |  | • |  | • | • | • | • | • | • | • |
|                  | How is the company positioned in the highest and lowest margin market segments? |  |  | • |  | • | • | • |  | • | • | • |
| 6                | Are there any major productivity initiatives? For publicly-stated targets, are they net of inflation? | • |  |  |  | • |  |  |  |  | • | • |
| O<br>S<br>T      | Where is the company making its major investments? | • |  |  |  | • | • |  | • | • | • | • |
| M<br>G<br>M<br>T | How does the quality of this mangement team compare to its competition? |  |  |  |  |  |  | • |  | • | • |  |

Exhibit 8.3 includes a list."""

HEALTHY = "| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n\ntail"
RATING = "| grade | name |\n|---|---|\n| A | one |\n| B | two |\n| C | three |\n| D | four |\n\ntail"
# Valentine p.3622 (anchor copy): a column of ratio names — tokens, not rail letters — beside a <br>-wrapped cell
RATIOS = ("| Method | Pros | Cons |\n|---|---|---|\n| All multiples-based<br>methods (e.g.,<br>P/E) | simple | flawed |\n"
          "| P/E | understood | misleading |\n| PEG | growth | inputs |\n| P/FCF | cash | capex |\n| P/S | sales | margins |\n\ntail")
# Valentine p.4522: a 2×2 matrix whose first row is two real headings beside an empty corner, its rail HIGH / LOW stacked
LIPSTICK = ("|  | Lipstick on a Pig | Reputation Builder |\n|---|---|---|\n| H<br>G<br>H | delivered | did the work |\n"
            "|  | Reputation Killer | Lost Opportunity |\n|  |  |  |\n| L | not the work | did the work |\n| L<br>O | not conveyed | not conveyed |\n|  |  |  |\n\ntail")
# Valentine p.1552, the FIRST half of Exhibit 8.2: the title chopped into fragments across the header cells, the rail with an
# `_` artefact and letters missing (STRATEGY read S A R T E G Ϋ; FINANCIAL read F N A N Č Ĺ)
FIRST_HALF_COL1 = ["", "", "", "", "_", "S", "A", "R<br>T<br>E<br>G", "Ϋ́", "", "", "", "F.", "N<br>A<br>N", "Č.", "Ĺ"]
FIRST_HALF = ("|  |  | Start | with th | s sour | ce to ir |\n|---|---|---|---|---|---|\n|  | Questions to be investigated | Company documents | Market data | Industry | Economic |\n"
              + "\n".join("| %s | question %d | • |  | • |  |" % (c, i) for i, c in enumerate(FIRST_HALF_COL1)) + "\n\ntail")
# Valentine p.1552 as the anchor copy has it (S151 E3): the WHOLE title chopped into eleven header cells over the real header
CHOPPED = ("|  |  | Start | with th | s sour | ce to ir | vestic | ate be | ore m | etina | manag | ement | 1 |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
           "|  | Questions to be investigated | Company documents,<br>data, and website | Market data & news<br>provider | Industry trade journal or<br>website | Economic data | Company investor relations contact | Sell-side report or model<br>(for buy-side analysts) | Customer of or supplier<br>to the company | Information from<br>forecasting service | Consultant, expert, or company retiree | Sell-side analyst<br>(for the buy-side) | Appropriate to ask executives at meeting |\n"
           "|  | How does the company create value for its customers and shareholders? | • |  |  |  | ٠ |  | ٠ |  | • | ٠ |  |\n"
           "|  | What is the company's competitive advantage? | • |  |  |  | • |  | • |  | • | • |  |\n"
           "|  | What are the risks to the company maintaining its competitive advantage/returns? | • |  |  |  | ٠ |  | • |  | • | • | • |\n\ntail")
# Valentine p.2502: a regression output whose stacked column headings (`Standard | 1 | P- | Lower | Upper` over `Error | t Stat |
# value | 95% | 95%`) have the fragment-row SHAPE — and are words the book uses
REGRESS = ("|  |  | Standard | 1 | P- | Lower | Upper | Lower | Upper |\n|---|---|---|---|---|---|---|---|---|\n"
           "|  | Coefficients | Error | t Stat | value | 95% | 95% | 95.0% | 95.0% |\n"
           "| Intercept | 0.74 | 0.12 | 6.1 | 0.00 | 0.50 | 0.98 | 0.50 | 0.98 |\n| X Variable | 1.00 | 0.21 | 4.8 | 0.00 | 0.58 | 1.42 | 0.58 | 1.42 |\n\ntail")


def main():
    print("[1] the reading: blocks, cells, fences")
    L = HEALTHY.split("\n")
    check("a clean table is one block (0,1,3)", tg.table_blocks(L) == [(0, 1, 3)])
    check("cells: edges dropped, escaped and code-span pipes kept", tg.cells("| a\\|b | `x|y` | c |") == ["a|b", "`x|y`", "c"])
    check("a table without leading pipes is a table", tg.table_blocks("a | b\n--- | ---\n1 | 2\n".split("\n")) == [(0, 1, 2)])
    check("pipes inside a fence are not a table", tg.table_blocks("```\n| a |\n|---|\n```".split("\n")) == [])
    check("a line touching the last row is inside the block", tg.table_blocks("| a |\n|---|\n| 1 |\nx\n\ny".split("\n")) == [(0, 1, 3)])

    print("[2] the health (the page's twin)")
    check("healthy: no issues", tg.health(L) == [])
    split = "| a | b |\n\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n|---|---|\n| 1 | 2 |\n".split("\n")
    hs = tg.health(split)
    check("the S149 split: header cut, the inserted lines, the orphan delimiter", [x["line"] for x in hs] == [1, 3, 4, 5], str(hs))
    hd = tg.health("| a | b | c |\n|---|---|\n| 1 | 2 | 3 |\n".split("\n"))
    check("header/delimiter disagreement named", len(hd) == 1 and "does not treat this as a table" in hd[0]["reason"])
    touch = tg.health("| a | b |\n|---|---|\n| 1 | 2 |\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n".split("\n"))
    check("a touching line is a garbled row", any(x["line"] == 4 and "touches" in x["reason"] for x in touch))
    check("a delimiter with no header", any("no header row" in x["reason"] for x in tg.health("para\n\n|---|---|\n| 1 | 2 |\n".split("\n"))))
    check("a repair block after the last row with its blank line is healthy", tg.health("| a |\n|---|\n| 1 |\n\n![[assets/_repair_p1_1.png]]\n<!-- repair p1 · repair-bench -->\n\ntail".split("\n")) == [])

    print("[3] the signatures on Valentine's exhibit (the fixture) and their negative controls")
    V = VALENTINE.split("\n")
    c = tg.census(V)
    check("one table read", len(c) == 1)
    t = c[0]
    check("the title row (one filled cell above the real header)", t["title_row"] is True)
    check("the header carries <br> cells (the rotated column headers)", t["header_br_cells"] >= 8, str(t["header_br_cells"]))
    check("the letter column is seen", t["letter_column"] is True)
    check("the letters arrive in reading order: R l v Ė N U E … 6 O S T M G M T", t["letters_in_order"] == "RlvĖNUE6OSTMGMT", t["letters_in_order"])
    check("two runs of letters (REVENUE… then COSTS/MGMT…)", t["letter_runs"] == ["RlvĖNUE", "6OSTMGMT"], str(t["letter_runs"]))
    check("the dot matrix counted (52 • by hand, one ٠)", t["dots_total"] == 52 and t["stray_dot_glyphs"] == 1, "%s / %s" % (t["dots_total"], t["stray_dot_glyphs"]))
    check("rows and columns", t["rows"] == 11 and t["cols"] == 13, "%s x %s" % (t["rows"], t["cols"]))
    r = tg.census(RATING.split("\n"))[0]
    check("negative control: a rating column A B C D is NOT a letter column (every row filled, no <br>)", r["letter_column"] is False)
    q = tg.census(RATIOS.split("\n"))[0]
    check("negative control: a column of ratio names (P/E, PEG, P/FCF, P/S beside a <br> cell) is NOT a letter column", q["letter_column"] is False and q["letter_column_cells"] == 0, str(q["letter_column_cells"]))
    lp = tg.census(LIPSTICK.split("\n"))[0]
    check("the 2×2 matrix: rail HIGH / LOW read H G H · L · L O (stacked letters, blanks between)", lp["letter_column"] is True and lp["letter_runs"] == ["HGH", "LLO"], str(lp["letter_runs"]))
    check("negative control: two real headings beside an empty corner are a header, not a title row", lp["title_row"] is False)
    fh = tg.census(FIRST_HALF.split("\n"))[0]
    check("the first half: the rail seen through the `_` artefact, letters missing (S A R T E G Ϋ · F N A N Č Ĺ)", fh["letter_column"] is True and fh["letter_runs"] == ["SARTEGΫ", "FNANČĹ"], str(fh["letter_runs"]))
    check("the first half: a title chopped into header fragments is NOT read as a title row (a MISSING signature, named)", fh["title_row"] is False)
    h = tg.census(HEALTHY.split("\n"))[0]
    check("negative control: a healthy table has no title row, no letters, no dots", not h["title_row"] and not h["letter_column"] and h["dots_total"] == 0)
    o = tg.orphan_runs("| a | b |\n\npara\n\n|---|---|\n| 1 | 2 |\n".split("\n"))
    check("orphan runs counted (a lone header, a headless run)", [x["rows"] for x in o] == [1, 2], str(o))

    print("[4] the repair half: the word check, the proposals, the invariant, the pass")
    check("letters_fit: SARTEGΫ fits STRATEGY (a letter missing, two swapped)", tg.letters_fit("SARTEGΫ", "STRATEGY")[0])
    check("letters_fit: RlvĖNUE fits REVENUE and not COSTS", tg.letters_fit("RlvĖNUE", "REVENUE")[0] and not tg.letters_fit("RlvĖNUE", "COSTS")[0])
    check("letters_fit: HGH/HIGH · LLO/LOW · 6OSTs/COSTS · VAĀON/VALUATION · FNANČĹ/FINANCIAL · MGMT/MGMT",
          all(tg.letters_fit(a, b)[0] for a, b in (("HGH", "HIGH"), ("LLO", "LOW"), ("6OSTs", "COSTS"), ("VAĀON", "VALUATION"), ("FNANČĹ", "FINANCIAL"), ("MGMT", "MGMT"))))
    check("letters_fit NEGATIVE: ABCD does not fit GRADE; one letter fits nothing; a non-word is refused",
          not tg.letters_fit("ABCD", "GRADE")[0] and not tg.letters_fit("A", "AND")[0] and not tg.letters_fit("HGH", "H1GH")[0])
    WORDS = {"RlvĖNUE": "REVENUE", "6OSTMGMT": "COSTS MGMT"}   # two rails the OCR ran together: the resolver answers a phrase
    resolver = lambda letters, ctx: WORDS.get(letters)  # noqa: E731
    props = tg.propose(V, resolver)
    kinds = sorted(p["kind"] for p in props)
    check("proposals on the exhibit: a caption, two rails, the dots", kinds == ["caption", "dots", "rail", "rail"], str(kinds))
    cap = next(p for p in props if p["kind"] == "caption")
    check("the caption is the spanning title, its chopped tail `ment` dropped", cap["text"].startswith("Start with this source") and cap["fragment_dropped"])
    rails = [(p["word"], p["rows"]) for p in props if p["kind"] == "rail"]
    check("the rails resolved on their rows: REVENUE 7-10, COSTS MGMT 12-14", rails == [("REVENUE", [7, 10]), ("COSTS MGMT", [12, 14])], str(rails))
    text, rec = tg.geometry_pass(VALENTINE, resolver, use_lexicon=False)   # [4] tests the resolver route alone; [5] the lexicon
    check("the pass applied all four, refused none, one invariant check per proposal (four), two resolver calls",
          rec["applied"] == 4 and rec["refused"] == 0 and rec["invariant_checks"] == 4 and rec["resolver_calls"] == 2, str(rec))
    after = tg.census(text.split("\n"))[0]
    check("AFTER: no letter column, no title row, no stray glyph, • up by one, one row fewer, 13 columns",
          not after["letter_column"] and not after["title_row"] and after["stray_dot_glyphs"] == 0 and after["dots_total"] == 53 and after["rows"] == 10 and after["cols"] == 13,
          str((after["letter_column"], after["title_row"], after["stray_dot_glyphs"], after["dots_total"], after["rows"], after["cols"])))
    L2 = text.split("\n")
    check("the caption above the table, a blank between, the real header then the delimiter",
          L2[2].startswith("Start with this source") and L2[3] == "" and "Questions to be investigated" in L2[4] and tg.DELIM.match(L2[5]) is not None, repr(L2[2:6]))
    check("REVENUE on the run's first row, the rail's other cells blank, the question cells untouched",
          tg.cells(L2[7])[0] == "REVENUE" and all(tg.cells(L2[k])[0] == "" for k in (8, 9, 10)) and tg.cells(L2[7])[1] == "How does the company set pricing?")
    B, A = V[2:14], L2[2:15]
    ok, reasons, facts = tg.grid_invariant(B, A)
    check("the invariant holds on the pass's own output (caption seen, 2 labels, 1 dot fixed, 120 cells compared)",
          ok and facts["caption"] and len(facts["labels"]) == 2 and facts["dots_fixed"] == 1 and facts["cells_compared"] == 120, str((reasons, facts)))
    check("idempotent: a second pass proposes nothing", tg.propose(L2, resolver) == [])
    text_none, rec_none = tg.geometry_pass(VALENTINE, None, use_lexicon=False)
    check("without a resolver: the rails are unresolved and reported; the caption and the dots still apply",
          rec_none["unresolved"] == 2 and rec_none["applied"] == 2 and rec_none["labels"] == [] and len(rec_none["unresolved_rails"]) == 2, str(rec_none))
    props_bad = tg.propose(V, lambda letters, ctx: "COSTS")
    check("a word that does not fit its letters is refused (REVENUE's letters offered COSTS)",
          any(p["kind"] == "rail" and p["word"] is None and "does not fit" in p["refused"] for p in props_bad))
    check("the resolver's `?` means no word: every rail unresolved", all(p["word"] is None for p in tg.propose(V, lambda s, c: "?") if p["kind"] == "rail"))
    check("a healthy table and a rating column propose nothing (the resolver is never asked)",
          tg.propose(HEALTHY.split("\n"), resolver) == [] and tg.propose(RATING.split("\n"), lambda s, c: "ABCD") == [])

    def mutate(rows, idx, fn):
        rows = list(rows)
        rows[idx] = fn(rows[idx])
        return rows
    # A[4] is the "Does the company…" row (row 2 of the table), A[5] the REVENUE row, A[6] the wins/losses row inside the rail
    check("the fixture's rows are where the negatives expect them", "pricing power" in A[4] and A[5].startswith("| REVENUE") and "customer wins" in A[6], repr(A[4:7]))
    check("invariant NEGATIVE: a cell outside column 1 reworded", not tg.grid_invariant(B, mutate(A, 4, lambda s: s.replace("pricing power", "pricing")))[0])
    check("invariant NEGATIVE: a • dropped (on a row inside the rail)", not tg.grid_invariant(B, mutate(A, 6, lambda s: s.replace("| • |", "|  |", 1)))[0])
    check("invariant NEGATIVE: a row dropped", not tg.grid_invariant(B, A[:6] + A[7:])[0])
    check("invariant NEGATIVE: a pipe dropped (the cell count changes)", not tg.grid_invariant(B, mutate(A, 4, lambda s: s.replace("| •", "•", 1)))[0])
    check("invariant NEGATIVE: a label that does not fit its letters (REVENUE -> COSTS)", not tg.grid_invariant(B, mutate(A, 5, lambda s: s.replace("REVENUE", "COSTS")))[0])
    check("invariant NEGATIVE: a cell inside the rail's rows reworded (the rows a rail spans are compared too)", not tg.grid_invariant(B, mutate(A, 6, lambda s: s.replace("customer wins", "wins")))[0])
    check("invariant NEGATIVE: the title row dropped with no caption above", not tg.grid_invariant(B, A[4:])[0])
    check("invariant: an unchanged table is admitted", tg.grid_invariant(B, B)[0])
    split = VALENTINE.replace("|------", "![[assets/_repair_p234_1.png]]\n<!-- repair p234 · repair-bench -->\n|------", 1).split("\n")
    check("a split table (a health issue) is never proposed for", tg.propose(split, resolver) == [] and tg.health(split) != [])

    print("[5] the lexicon route (S151 E1): a label must be a word the book itself uses")
    check("letters_fit, short reads exact: LLO fits LOW and not LABEL; HGH fits HIGH; LO fits LOW; UE does not fit CAUSE (half the word at least)",
          tg.letters_fit("LLO", "LOW")[0] and not tg.letters_fit("LLO", "LABEL")[0] and tg.letters_fit("HGH", "HIGH")[0]
          and tg.letters_fit("LO", "LOW")[0] and not tg.letters_fit("UE", "CAUSE")[0])
    check("a digit reads as its OCR confusions, not any letter: 6OST fits COSTS (6 → c) and not MOST in full; lvĖN does not fit INVESTMENTS",
          tg.letters_fit("6OST", "COSTS")[0] and tg.letters_fit("6OST", "MOST")[1].startswith("3 of 4") and not tg.letters_fit("lvĖN", "INVESTMENTS")[0],
          str((tg.letters_fit("6OST", "COSTS"), tg.letters_fit("6OST", "MOST"), tg.letters_fit("lvĖN", "INVESTMENTS"))))
    prose = ["The analyst weighs revenue, costs and management quality before valuation; strategy and financial questions come first.",
             "High and low marks; the label column; a table of P/E ratios."]
    lex = tg.lexicon(prose + ["| R | one |", "| l v | two |"])
    check("the lexicon holds the book's words with counts and never a rail cell", lex.get("revenue") == 1 and lex.get("management") == 1 and "r" not in lex and "lv" not in lex and lex.get("the", 0) >= 2)
    check("best_word: SARTEGΫ → STRATEGY, RlvĖNUE → REVENUE, FNANČĹ → FINANCIAL, VAĀON → VALUATION, HGH → HIGH, LLO → LOW",
          [tg.best_word(x, lex)[0] for x in ("SARTEGΫ", "RlvĖNUE", "FNANČĹ", "VAĀON", "HGH", "LLO")] == ["STRATEGY", "REVENUE", "FINANCIAL", "VALUATION", "HIGH", "LOW"],
          str([tg.best_word(x, lex) for x in ("SARTEGΫ", "RlvĖNUE", "FNANČĹ", "VAĀON", "HGH", "LLO")]))
    check("best_word: MGMT and ABCD find no word of the book", tg.best_word("MGMT", lex)[0] is None and tg.best_word("ABCD", lex)[0] is None)
    check("best_word: a tie at the top is refused, not guessed", tg.best_word("LO", {"low": 1, "lot": 1})[0] is None and "ambiguous" in tg.best_word("LO", {"low": 1, "lot": 1})[1])
    segs = tg.lexicon_segments(["6", "OST", "s", "MGMT", "VA", "Ā", "ON"], lex)
    check("lexicon_segments: the run COSTS·MGMT·VALUATION splits at the cells where each word's letters end; MGMT (no word) left out",
          [(a, b, w) for a, b, w, _ in segs] == [(0, 2, "COSTS"), (4, 6, "VALUATION")], str(segs))
    lex2 = dict(lex, mgmt=1)
    segs2 = tg.lexicon_segments(["6", "OST", "s", "MGMT", "VA", "Ā", "ON"], lex2)
    check("lexicon_segments: with MGMT in the book, all three words, all seven cells covered",
          [(a, b, w) for a, b, w, _ in segs2] == [(0, 2, "COSTS"), (3, 3, "MGMT"), (4, 6, "VALUATION")], str(segs2))
    props = tg.propose(V, None, lex2)
    rails = [(p["rows"], p["word"], p["how"][:7]) for p in props if p["kind"] == "rail"]
    check("propose with the lexicon: REVENUE rows 7-10, COSTS rows 12-13, MGMT row 14 — each on its own rows, no resolver asked",
          rails == [([7, 10], "REVENUE", "lexicon"), ([12, 13], "COSTS", "lexicon"), ([14, 14], "MGMT", "lexicon")], str(rails))
    props_typo = tg.propose(V, None, dict(lex, mangement=1))   # the book's own typo of management must not become MGMT's label
    check("a nine-letter word does not fit a four-letter read (MGMT is not MANGEMENT): the cell stays unresolved",
          any(p["kind"] == "rail" and p["letters"] == "MGMT" and p["word"] is None for p in props_typo), str([(p["letters"], p["word"]) for p in props_typo if p["kind"] == "rail"]))
    text2, rec2 = tg.geometry_pass(VALENTINE + "\n\n" + prose[0] + " Management (MGMT) matters.", None)
    L3 = text2.split("\n")
    check("geometry_pass with the book's own lexicon: three labels applied, none unresolved, no resolver call, lexicon counted",
          rec2["applied"] == 5 and rec2["unresolved"] == 0 and rec2["resolver_calls"] == 0 and rec2["lexicon_words"] > 20 and [lb["word"] for lb in rec2["labels"]] == ["REVENUE", "COSTS", "MGMT"], str(rec2))
    check("the run split where the words end: COSTS on the `6` row, MGMT on its own row, the cells between blank",
          tg.cells(L3[12])[0] == "COSTS" and tg.cells(L3[13])[0] == "" and tg.cells(L3[14])[0] == "MGMT", repr([L3[12][:30], L3[13][:30], L3[14][:30]]))
    check("the invariant admits the segmented run", tg.grid_invariant(V[2:14], L3[2:15])[0], str(tg.grid_invariant(V[2:14], L3[2:15])[1]))
    props_bad = tg.propose(V, lambda letters, ctx: "SARTGEY", lex)
    check("a resolver's shuffle is refused by the lexicon: SARTGEY is not a word of the book (the unresolved proposal says so)",
          any(p["kind"] == "rail" and p["word"] is None and "not a word of the book" in (p["refused"] or "") for p in props_bad), str([p for p in props_bad if p["kind"] == "rail"]))
    print("[6] the title chopped into header fragments (S151 E3)")
    fh2 = tg.census(FIRST_HALF.split("\n"))[0]
    check("the fragment title row is seen (title_fragments) and is not the one-cell title shape", fh2["title_fragments"] is True and fh2["title_row"] is False)
    ch = tg.census(CHOPPED.split("\n"))[0]
    check("the anchor's p.1552 shape: thirteen columns, eleven fragments read as a chopped title", ch["cols"] == 13 and ch["title_fragments"] is True and ch["title_row"] is False, str((ch["cols"], ch["title_fragments"])))
    check("a regression's stacked headings have the same SHAPE (the reading half says so; the proposer must refuse them)",
          tg.census(REGRESS.split("\n"))[0]["title_fragments"] is True)
    title = "Start with this source to investigate before meeting management"
    stream = "Startwiththssourcetoirvesticatebeoremetinamanagement1"
    ph, why = tg.best_phrase(stream, [title, "Questions to Investigate before or during Interviews with Management", "Exhibit 8.3 includes a list of the documents"])
    check("best_phrase: the book's own title holds the fragments' letters in order (a decoy title does not)", ph == title and "of 53 letters" in why, str((ph, why)))
    check("best_phrase NEGATIVE: a row of short headings is too short for a phrase; two alike phrases are a tie",
          tg.best_phrase("DfSSMSF", [title])[0] is None and tg.best_phrase(stream, [title, title + "s"])[0] is None)
    pieces, ex, tot = tg.words_from_stream("Startwiththssource1", {"start": 5, "with": 5, "this": 5, "source": 5, "the": 9})
    check("words_from_stream: a short stream read as the book's words, the footnote digit set aside", pieces == ["start", "with", "this", "source", "1"] and ex == 18 and tot == 19, str((pieces, ex, tot)))
    check("words_from_stream NEGATIVE: a word the book uses once (a fragment of itself) does not explain the stream",
          tg.words_from_stream("vesticate", {"vestic": 1, "ate": 1, "investigate": 3})[0] != ["vestic", "ate"])
    full = CHOPPED + "\n\n" + VALENTINE   # the continued half's title cell is the phrase the first half's fragments need
    props6 = tg.propose(full.split("\n"), None, tg.lexicon(full.split("\n")))
    cap6 = [p for p in props6 if p["kind"] == "caption" and p.get("fragments_joined")]
    check("propose: the fragment title becomes the book's own phrase as the caption, the raw join kept on the record",
          len(cap6) == 1 and cap6[0]["text"] == title and cap6[0]["raw"].startswith("Start with th s sour") and "own phrase" in cap6[0]["how"], str(cap6))
    text6, rec6 = tg.geometry_pass(full, None)
    L6 = text6.split("\n")
    check("geometry_pass: the fragment caption admitted by the invariant; the real header row now heads the table",
          any(c.get("fragments_joined") and c["text"] == title for c in rec6["captions"]) and L6[0] == title and L6[1] == "" and "Questions to be investigated" in L6[2] and tg.DELIM.match(L6[3]) is not None,
          str((rec6["captions"], rec6["refusals"], L6[:4])))
    lonely = FIRST_HALF.split("\n")   # no continued half: no phrase, the words along the stream are a soup → the raw join (≥ 5 fragments)
    props7 = tg.propose(lonely, None, tg.lexicon(lonely))
    cap7 = [p for p in props7 if p["kind"] == "caption"]
    check("without the book's phrase the fragments are joined as read and said so (the header freed, the text left as the OCR left it)",
          len(cap7) == 1 and cap7[0]["text"] == "Start with th s sour ce to ir" and "joined as read" in cap7[0]["how"], str(cap7))
    lexr = tg.lexicon((REGRESS + "\n\nThe standard error and the lower and upper bounds. Standard, lower, upper.").split("\n"))
    check("NEGATIVE: the regression's headings are words the book uses (Standard, Lower, Upper) — no caption, the header kept",
          not any(p["kind"] == "caption" for p in tg.propose(REGRESS.split("\n"), None, lexr)))
    regress = "|  |  |  |  | Si | gnificance |  |\n|---|---|---|---|---|---|---|\n|  | Df | SS | MS | F | F |  |\n| Regression | 1.00 | 0.74 | 0.74 | 100 | .63 | 0.00 |\n\ntail".split("\n")
    check("NEGATIVE: a stacked column heading split in two (Si | gnificance) is not a fragment title and gets no caption",
          tg.census(regress)[0]["title_fragments"] is False and not any(p["kind"] == "caption" for p in tg.propose(regress, None, {"significance": 3})))
    print("[7] a row label wrapped over two rows is folded back into one (S152 E1)")
    REG = ("|  |  | Standard | 1 | P- | Lower | Upper | Lower | Upper |\n|---|---|---|---|---|---|---|---|---|\n"
           "|  | Coefficients | Error | t Stat | value | 95% | 95% | 95% | 95% |\n"
           "| Intercept | -0.55 | 0.39 | -1.40 | 0.17 | -1.33 | 0.24 | -1.33 | 0.24 |\n"
           "| lag1 (log of<br>BNI intermodal<br>revenue) | 0.86 | 0.06 | 14.63 | 0.00 | 0.74 | 0.98 | 0.74 | 0.98 |\n"
           "| lag1 (log of<br>manufacturing |  |  |  |  |  |  |  |  |\n"
           "| index) | 0.48 | 0.26 | 1.83 | 0.07 | -0.05 | 1.00 | -0.05 | 1.00 |\n\ntail")
    RL = REG.split("\n")
    c7 = tg.census(RL)[0]
    check("the reading half sees the wrapped label as the pair of file lines 6 and 7", c7["wrapped_labels"] == [[6, 7]], str(c7["wrapped_labels"]))
    props7 = tg.propose(RL, None, {"standard": 3, "lower": 3, "upper": 3, "error": 3, "value": 3})
    folds7 = [p for p in props7 if p["kind"] == "fold"]
    check("one fold proposed, naming both halves of the label", len(folds7) == 1 and folds7[0]["rows"] == [6, 7] and "manufacturing" in folds7[0]["why"] and "index)" in folds7[0]["why"], str(props7))
    after7 = tg.apply_table(RL, 0, 1, 6, folds7)
    check("applied: one row fewer, the label joined with a space, the data the second row's",
          len(after7) == 6 and tg.cells(after7[5])[0] == "lag1 (log of<br>manufacturing index)" and tg.cells(after7[5])[1] == "0.48", str(after7[-1]))
    ok7, why7, facts7 = tg.grid_invariant(RL[:7], after7)
    check("the invariant admits the fold and names it (rows 5-6 of the table, a wrapped label)", ok7 and len(facts7["folds"]) == 1 and facts7["folds"][0]["how"] == "a wrapped label", str((why7, facts7.get("folds"))))
    text7, rec7 = tg.geometry_pass(REG, None)
    check("geometry_pass folds it and the record says so", rec7["applied"] >= 1 and len(rec7["folds"]) == 1 and "manufacturing index)" in text7 and text7.count("\n") == REG.count("\n") - 1, str((rec7["folds"], rec7["refusals"])))
    SECTION = ("| Participants | Purpose of Discussion | Typical Time Limit |\n|---|---|---|\n"
               "| I. Buy-Side and Sell-Side Roles |  |  |\n| Outgoing call to company management | A few follow-up questions | 10 to 30 minutes |\n"
               "| II. Buy-Side Only Role |  |  |\n| Inbound call from your portfolio manager | You are responding to a question(s). | 1 to 10 minutes |\n\ntail")
    check("NEGATIVE: a section row (Title Case, no continuation signal) over a data row is not a wrapped label — nothing proposed",
          tg.census(SECTION.split("\n"))[0]["wrapped_labels"] == [] and not any(p["kind"] == "fold" for p in tg.propose(SECTION.split("\n"), None, {})))
    DATA2 = RL[:5] + ["| Compensation | 1.47 |  |  |  |  |  |  |  |", "| and Benefits |  | 0.49 | 2.99 | 0.00 | 0.48 | 2.46 | 0.48 | 2.46 |", "", "tail"]
    check("NEGATIVE: a first row that holds data of its own is not a wrap", tg.census(DATA2)[0]["wrapped_labels"] == [])
    # the book's index (Observed on the first dry run: nine index entries folded into their neighbours — two columns of entries
    # ending in page numbers, the next entry starting lowercase): two columns, or a first line ending in a digit, is never a wrap
    INDEX = ("| timing/value of line item in, 200 | Information hub, 51-66 |\n|---|---|\n| leading of, 141–143 |  |\n| meeting documentation, | best practice skill for, 65-66 |\n"
             "| Ratings change |  |\n| catalyst for, valuation comp table | collection of, 51-52, 65 |\n\ntail")
    check("NEGATIVE: the index's two-column entries are not wrapped labels (two columns; a line ending in a page number)", tg.census(INDEX.split("\n"))[0]["wrapped_labels"] == [], str(tg.census(INDEX.split("\n"))[0]["wrapped_labels"]))
    INDEX3 = ("| a | b | c |\n|---|---|---|\n| prioritization of, 27-42 |  |  |\n| series, chart data deception | 1 | 2 |\n\ntail")
    check("NEGATIVE: three columns but a first line ending in a digit (an index entry) is not a wrap", tg.census(INDEX3.split("\n"))[0]["wrapped_labels"] == [])
    smuggled = list(after7)
    smuggled[5] = smuggled[5].replace("0.48", "0.84")
    ok8, why8, _ = tg.grid_invariant(RL[:7], smuggled)
    check("NEGATIVE: an edit smuggled into a fold is refused (the after row is not the exact join)", not ok8 and any("dropped" in w or "rows before" in w for w in why8), str(why8))
    forced = tg.apply_table(RL, 0, 1, 6, [{"kind": "fold", "table": [1, 7], "rows": [4, 5], "why": "planted"}])
    ok9, why9, _ = tg.grid_invariant(RL[:7], forced)
    check("NEGATIVE: a fold of two rows that both hold data is refused by the invariant (a body fold joins only where one side is empty)", not ok9 and any("filled on both rows" in w for w in why9), str(why9))
    text3, rec3 = tg.geometry_pass(VALENTINE, lambda letters, ctx: "REVENUE")
    check("without the word in the book's prose the resolver's REVENUE is refused too (the book must say it)",
          not any(lb["word"] == "REVENUE" for lb in rec3["labels"]) and any("not a word of the book" in u["why"] for u in rec3["unresolved_rails"]), str((rec3["labels"], rec3["unresolved_rails"])))
    check("fit_score: COSTS explains 6OSTs (5) better than MANAGEMENT explains sMGMT (0); VALUATION explains VAĀON (3)",
          tg.fit_score(5, 5, 5) == 5 and tg.fit_score(5, 4, 10) == 0 and tg.fit_score(5, 5, 9) == 3)
    # the two traps the real book set (S151 E1, Observed): the OCR swapped R and T so `SARTEGΫ` fits STARTED (s,a,r,t,e,d) better than
    # STRATEGY by the letters alone; `L | L O` across a row boundary fits ALLOW better than LOW; and MGMT is not a word of any prose
    trap = {"started": 3, "strategy": 3, "allow": 5, "low": 5, "might": 8, "high": 4}
    check("the context bonus: with the rows asking about strategy, SARTEGΫ → STRATEGY; without it the letters alone say STARTED (the trap, named)",
          tg.best_word("SARTEGΫ", trap, context={"strategy", "differ"})[0] == "STRATEGY" and tg.best_word("SARTEGΫ", trap)[0] == "STARTED",
          str((tg.best_word("SARTEGΫ", trap, context={"strategy"}), tg.best_word("SARTEGΫ", trap))))
    check("the boundary collapse: cells L | LO read as LO → LOW, not ALLOW", [(a, b, w) for a, b, w, _ in tg.lexicon_segments(["L", "LO"], trap)] == [(0, 1, "LOW")],
          str(tg.lexicon_segments(["L", "LO"], trap)))
    check("MGMT is not MIGHT: a word that explains the read by one point is refused (SEGMENT_MIN_SCORE)", tg.lexicon_segments(["MGMT"], trap) == [],
          str(tg.lexicon_segments(["MGMT"], trap)))
    check("HGH → HIGH still clears the bar", [(a, b, w) for a, b, w, _ in tg.lexicon_segments(["HGH"], trap)] == [(0, 0, "HIGH")])
    # S151 E1 run 3 (Observed): LOST, in the matrix's own rows, beat LOW for `L | L O`; COST + SEGMENTS beat COSTS over the same cells
    check("a short read may be one letter short of its word: L | LO → LOW even with LOST in the rows; LOT and LOW alike → ambiguous, unresolved",
          [(a, b, w) for a, b, w, _ in tg.lexicon_segments(["L", "LO"], {"low": 2, "lost": 9}, context={"lost"})] == [(0, 1, "LOW")]
          and tg.lexicon_segments(["L", "LO"], {"low": 2, "lot": 2}) == [] and "ambiguous" in tg.best_word("LO", {"low": 2, "lot": 2})[1],
          str((tg.lexicon_segments(["L", "LO"], {"low": 2, "lost": 9}, context={"lost"}), tg.best_word("LO", {"low": 2, "lot": 2}))))
    check("two weak words never beat one strong one: 6 | OST | s → COSTS, not COST + SEGMENTS (even with cost and segments in the rows)",
          [(a, b, w) for a, b, w, _ in tg.lexicon_segments(["6", "OST", "s", "MGMT"], {"costs": 3, "cost": 9, "segments": 2, "might": 4}, context={"segments", "cost"})] == [(0, 2, "COSTS")],
          str(tg.lexicon_segments(["6", "OST", "s", "MGMT"], {"costs": 3, "cost": 9, "segments": 2, "might": 4}, context={"segments", "cost"})))
    check("the boundary collapse leaves an accented glyph alone: VA | Ā | ON stays VAĀON (TI merged, not a repeat) → VALUATION",
          tg.boundary_collapse(["VA", "Ā", "ON"]) == ["VA", "Ā", "ON"] and [(a, b, w) for a, b, w, _ in tg.lexicon_segments(["VA", "Ā", "ON"], {"valuation": 2, "van": 9})] == [(0, 2, "VALUATION")],
          str(tg.lexicon_segments(["VA", "Ā", "ON"], {"valuation": 2, "van": 9})))
    # S151 E1 run 2 (Observed on the anchor copy): one wrong label refused the table's WHOLE batch — the caption and the dots with it;
    # proposals are admitted one at a time now
    good = tg.propose(V, resolver)
    bad = [dict(p, word="ZZZZ", how="a planted wrong word") if (p["kind"] == "rail" and p["rows"] == [7, 10]) else p for p in good]
    h0, d0, e0 = tg.table_blocks(V)[0]
    new, admitted, refused_, n_checks, dots = tg.apply_admitted(V, h0, d0, e0, bad)
    check("apply_admitted: a planted wrong label is refused alone; the caption, the dots and the other rail are admitted (4 checks)",
          len(refused_) == 1 and refused_[0]["word"] == "ZZZZ" and [p["kind"] for p in admitted] == ["caption", "rail", "dots"] and n_checks == 4 and dots == 1,
          str(([p["kind"] for p in admitted], [(p["kind"], p.get("word")) for p in refused_], n_checks, dots)))
    check("apply_admitted: the admitted table passes the invariant and keeps the wrong label's cells as they were",
          tg.grid_invariant(V[h0:e0 + 1], new)[0] and tg.cells(new[5])[0] == "R", repr(new[5][:24]))

    print("%s: %d/%d" % ("ALL OK" if not FAILS else "FAILED", N - FAILS, N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
