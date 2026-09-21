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
    check("S154: REVENUE LIFTED onto its group's first row (the 'Does the company…' row, one above its first letter), the run's cells blank, the questions untouched",
          tg.cells(L2[6])[0] == "REVENUE" and all(tg.cells(L2[k])[0] == "" for k in (7, 8, 9, 10)) and tg.cells(L2[6])[1].startswith("Does the company")
          and tg.cells(L2[7])[1] == "How does the company set pricing?", repr([L2[k][:30] for k in (6, 7)]))
    check("S154 NEGATIVE (the old placement): REVENUE is no longer on the run's first letter row", tg.cells(L2[7])[0] == "", repr(L2[7][:30]))
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
    # A[4] is the "Does the company…" row (row 2 of the table) and carries REVENUE since S154 (lifted), A[5] the first letter row (blank now), A[6] the wins/losses row inside the rail
    check("the fixture's rows are where the negatives expect them", "pricing power" in A[4] and A[4].startswith("| REVENUE") and tg.cells(A[5])[0] == "" and "customer wins" in A[6], repr(A[4:7]))
    check("invariant NEGATIVE: a cell outside column 1 reworded", not tg.grid_invariant(B, mutate(A, 4, lambda s: s.replace("pricing power", "pricing")))[0])
    check("invariant NEGATIVE: a • dropped (on a row inside the rail)", not tg.grid_invariant(B, mutate(A, 6, lambda s: s.replace("| • |", "|  |", 1)))[0])
    check("invariant NEGATIVE: a row dropped", not tg.grid_invariant(B, A[:6] + A[7:])[0])
    check("invariant NEGATIVE: a pipe dropped (the cell count changes)", not tg.grid_invariant(B, mutate(A, 4, lambda s: s.replace("| •", "•", 1)))[0])
    check("invariant NEGATIVE: a label that does not fit its letters (REVENUE -> COSTS, on the lifted row)", not tg.grid_invariant(B, mutate(A, 4, lambda s: s.replace("REVENUE", "COSTS")))[0])
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
    folds7 = [p for p in props7 if p["kind"] == "fold" and not p.get("header")]   # the header fold is [9]'s
    check("one wrapped-label fold proposed, naming both halves of the label", len(folds7) == 1 and folds7[0]["rows"] == [6, 7] and "manufacturing" in folds7[0]["why"] and "index)" in folds7[0]["why"], str(props7))
    after7 = tg.apply_table(RL, 0, 1, 6, folds7)
    check("applied: one row fewer, the label joined with a space, the data the second row's",
          len(after7) == 6 and tg.cells(after7[5])[0] == "lag1 (log of<br>manufacturing index)" and tg.cells(after7[5])[1] == "0.48", str(after7[-1]))
    ok7, why7, facts7 = tg.grid_invariant(RL[:7], after7)
    check("the invariant admits the fold and names it (rows 5-6 of the table, a wrapped label)", ok7 and len(facts7["folds"]) == 1 and facts7["folds"][0]["how"] == "a wrapped label", str((why7, facts7.get("folds"))))
    text7, rec7 = tg.geometry_pass(REG, None)
    check("geometry_pass folds it and the record says so (the stacked heading of [9] folds beside it: two rows fewer)",
          rec7["applied"] >= 1 and any("wrapped row label" in f["why"] for f in rec7["folds"]) and "manufacturing index)" in text7 and text7.count("\n") == REG.count("\n") - 2, str((rec7["folds"], rec7["refusals"])))
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
    print("[8] a caption chopped into long pieces beside empty cells (S152 E2, p.72)")
    P97 = ("|  |  | Quality of Self-Side | Analyst Based on Your I | Prior Experience |\n|---|---|---|---|---|\n"
           "|  |  | New and Unknown | Experienced and Bad | Experienced and Good<br>(or Great) |\n"
           "| y Stocks | Critical<br>to My<br>Stocks | Scan for key points in less than 2 minutes. | Scan for key points in less than 2 minutes. | Read ASAP. |\n"
           "| impact the Topics They Discuss Have on My Stocks | Could Be<br>or<br>Become<br>Critical | Scan for key points in 2 minutes; if warranted. | Scan for key points in less than 2 minutes to understand his or her perspective. | Read for less than 10 minutes. |\n"
           "| Impact t | Not<br>Critical | Send directly to recycling bin. | Send directly to recycling bin. | Read on your own time if you find it interesting or amusing. |\n\ntail")
    PL = P97.split("\n")
    c8 = tg.census(PL)[0]
    check("the reading half sees the pieces (title_pieces), not the one-cell title nor the short fragments", c8["title_pieces"] is True and c8["title_row"] is False and c8["title_fragments"] is False, str((c8["title_pieces"], c8["title_row"], c8["title_fragments"])))
    lex8 = tg.lexicon(PL + ["The quality of a sell-side analyst is judged on your prior experience with the analyst; the sell-side analyst again."])
    props8 = tg.propose(PL, None, lex8)
    cap8 = [p for p in props8 if p["kind"] == "caption"]
    check("the caption is the pieces joined as read (the book has no phrase holding them), the raw join on the record",
          len(cap8) == 1 and cap8[0]["text"] == "Quality of Self-Side Analyst Based on Your I Prior Experience" and cap8[0].get("fragments_joined") and "joined as read" in cap8[0]["how"], str(cap8))
    text8, rec8 = tg.geometry_pass(P97, None)
    L8 = text8.split("\n")
    check("geometry_pass admits it: the caption above, a blank, the real headings row as the header, the delimiter under it",
          any(c.get("fragments_joined") for c in rec8["captions"]) and L8[0].startswith("Quality of Self-Side") and L8[1] == "" and "New and Unknown" in L8[2] and tg.DELIM.match(L8[3]) is not None and not rec8["refusals"],
          str((rec8["captions"], rec8["refusals"], L8[:4])))
    check("NEGATIVE: two real headings beside an empty corner (Lipstick on a Pig | Reputation Builder) are not pieces — no signal",
          tg.census(LIPSTICK.split("\n"))[0]["title_pieces"] is False and not any(p["kind"] == "caption" for p in tg.propose(LIPSTICK.split("\n"), None, tg.lexicon(LIPSTICK.split("\n")))))
    check("NEGATIVE: short fragments stay the fragments shape (REG's stacked heading is neither pieces nor a title)", tg.census(RL)[0]["title_pieces"] is False and tg.census(RL)[0]["title_fragments"] is True)
    HEADS = "|  | Revenue and | Costs | Margin |\n|---|---|---|---|\n| A | 1 | 2 | 3 |\n| B | 4 | 5 | 6 |\n\ntail"
    check("NEGATIVE (the named risk): single-word heading pieces the book uses are refused by the guard even with a signal",
          not any(p["kind"] == "caption" for p in tg.propose(HEADS.split("\n"), None, {"revenue": 4, "costs": 4, "margin": 4, "and": 9})))
    print("[9] a stacked column heading folded into one heading row (S152 E3)")
    lex9 = {"standard": 3, "lower": 3, "upper": 3, "error": 3, "value": 3, "coefficients": 2, "intercept": 2}
    props9 = tg.propose(RL, None, lex9)
    hf = [p for p in props9 if p["kind"] == "fold" and p.get("header")]
    check("the regression's stacked heading proposes a HEADER fold (not a caption), naming both rows", len(hf) == 1 and hf[0]["rows"] == [1, 3] and "Standard" in hf[0]["why"] and not any(p["kind"] == "caption" for p in props9), str(props9))
    check("the join follows the page's typography: Standard Error, t Stat (the OCR's lone `1` dropped), P-value (no space after a hyphen), Lower 95%",
          tg._join_heading(tg.cells(RL[0]), tg.cells(RL[2])) == ["", "Coefficients", "Standard Error", "t Stat", "P-value", "Lower 95%", "Upper 95%", "Lower 95%", "Upper 95%"], str(tg._join_heading(tg.cells(RL[0]), tg.cells(RL[2]))))
    after9 = tg.apply_table(RL, 0, 1, 6, hf)
    check("applied: the header row is the joined heading, the delimiter under it, one row fewer", tg.cells(after9[0])[2] == "Standard Error" and tg.DELIM.match(after9[1]) is not None and tg.cells(after9[2])[0] == "Intercept" and len(after9) == 6, str(after9[:3]))
    ok9, why9, facts9 = tg.grid_invariant(RL[:7], after9)
    check("the invariant admits the header fold and names it", ok9 and len(facts9["folds"]) == 1 and facts9["folds"][0]["how"] == "a header fold", str((why9, facts9.get("folds"))))
    text9, rec9 = tg.geometry_pass(REG, None)
    L9 = text9.split("\n")
    check("geometry_pass: both folds on the regression table (the heading and the wrapped label), the record naming them",
          len(rec9["folds"]) == 2 and tg.cells(L9[0])[4] == "P-value" and "manufacturing index)" in text9 and text9.count("\n") == REG.count("\n") - 2, str((rec9["folds"], rec9["refusals"], L9[:2])))
    check("NEGATIVE: the chopped title (CHOPPED) is a caption, never a header fold", not any(p["kind"] == "fold" and p.get("header") for p in tg.propose((CHOPPED + "\n\n" + VALENTINE).split("\n"), None, tg.lexicon((CHOPPED + "\n\n" + VALENTINE).split("\n")))))
    check("NEGATIVE: a healthy header over a data row is not a stacked heading", not any(p["kind"] == "fold" for p in tg.propose(HEALTHY.split("\n"), None, {"a": 5, "b": 5, "c": 5})))
    smug9 = list(after9)
    smug9[0] = smug9[0].replace("Standard Error", "Standard Deviation")
    ok10, why10, _ = tg.grid_invariant(RL[:7], smug9)
    check("NEGATIVE: a heading not the exact join (Standard Deviation) is refused", not ok10, str(why10))
    print("[10] an index read as a table is named by the census (S152 E4 — a signature, no repair)")
    entries = ["| %s of, %d | %s, %d-%d |" % (w, 100 + i, w.capitalize(), 10 + i, 20 + i) for i, w in enumerate(["timing", "trend", "index", "industry", "inflation", "influencing", "information", "contacts", "hub", "source", "bloggers", "buy-side", "company", "data", "economic", "filter", "financial"])]
    INDEXT = "| timing/value of line item in, 200 | Information hub, 51-66 |\n|---|---|\n" + "\n".join(entries) + "\n\ntail"
    ci = tg.census(INDEXT.split("\n"))[0]
    check("two columns of entries ending in page numbers, an entry-shaped header row: index_like", ci["index_like"] is True, str(ci["index_like"]))
    check("NEGATIVE: the exhibit (a real table with headings) is not index_like; nor the regression; nor a two-column table of prose (p.239's shape)",
          tg.census(VALENTINE.split("\n"))[0]["index_like"] is False and tg.census(RL)[0]["index_like"] is False
          and tg.census(("| Value (or Cyclical) | Growth |\n|---|---|\n" + "\n".join("| item %d of the past. | size of the market. |" % k for k in range(20)) + "\n\ntail").split("\n"))[0]["index_like"] is False)
    text10, rec10 = tg.geometry_pass(INDEXT, None)
    check("the layer proposes nothing on an index (a signature only): the text unchanged", text10 == INDEXT and rec10["applied"] == 0)
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

    print("[11] S154 E6 — a rotated label begins at its GROUP's first row: the spans tile the body, the word is lifted, the invariant admits only that")
    rp = [p for p in tg.propose(V, resolver) if p["kind"] == "rail"]
    check("spans tile the body under the title row: REVENUE [6, 11] (from the first body row; the one blank row before COSTS goes up), COSTS MGMT [12, 14] (to the last row)",
          [(p["word"], p["rows"], p["span"]) for p in rp] == [("REVENUE", [7, 10], [6, 11]), ("COSTS MGMT", [12, 14], [12, 14])], str([(p["word"], p["rows"], p.get("span")) for p in rp]))
    check("the record says where each label was placed and its span", [(lb["word"], lb["placed"], lb["span"]) for lb in rec["labels"]] == [("REVENUE", 6, [6, 11]), ("COSTS MGMT", 12, [12, 14])], str(rec["labels"]))
    check("the invariant names the lift: REVENUE at row 2 of the table, lifted 1 row onto its run", facts["labels"][0]["word"] == "REVENUE" and facts["labels"][0]["row"] == 2 and facts["labels"][0]["lifted"] == 1, str(facts["labels"]))
    # the negatives, each a shape the first cut produced or could: onto the header row; onto a blank row with no run beneath; over another run's letters; over a filled cell
    def put(row, word):   # the row with its first cell set to word
        return "| " + word + " |" + row.split("|", 2)[2]
    hdr = list(A)
    hdr[2] = put(hdr[2], "REVENUE")
    hdr[4] = put(hdr[4], "")
    okh, whyh, _ = tg.grid_invariant(B, hdr)
    check("invariant NEGATIVE: a label on the HEADER row is refused (the first cut lifted REVENUE onto it under the title row — the selftest caught it)", not okh and any("header row" in w for w in whyh), str(whyh))
    norun = list(A)
    norun[4] = put(norun[4], "")
    norun[11] = put(norun[11], "REVENUE")
    okn, whyn, _ = tg.grid_invariant(B, norun)
    check("invariant NEGATIVE: a label on a blank row with no letter run beneath it is refused", not okn and any("no letter run" in w or "changed" in w for w in whyn), str(whyn))
    over = list(A)
    over[4] = put(over[4], "COSTS")
    okc, whyc, _ = tg.grid_invariant(B, over)
    check("invariant NEGATIVE: a label lifted over another run's letters is refused (COSTS over R-l-v-Ė-N-U-E)", not okc and any("does not fit" in w for w in whyc), str(whyc))
    Vf = list(V)
    Vf[5] = Vf[5].replace("|                  |", "| Note             |", 1)
    assert "pricing power" in Vf[5], Vf[5]
    tf, rf = tg.geometry_pass(chr(10).join(Vf), resolver, use_lexicon=False)
    Lf = tf.split(chr(10))
    check("apply never lifts over a filled, non-letter cell: with 'Note' on the group's first row REVENUE stays on its letter row, and the invariant still admits the pass",
          tg.cells(Lf[6])[0] == "Note" and tg.cells(Lf[7])[0] == "REVENUE" and rf["labels"][0]["placed"] == 7 and rf["refused"] == 0, str((Lf[6][:30], Lf[7][:30], rf["labels"], rf["refused"])))
    check("idempotent after the lift: a second pass proposes nothing", tg.propose(L2, resolver) == [])
    # p.107's shape: a stray mark (the OCR's read of the label's stem, an underscore) on the row above the letters
    Vs = list(V)
    Vs[5] = Vs[5].replace("|                  |", "| _                |", 1)
    assert "pricing power" in Vs[5], Vs[5]
    ts_, rs_ = tg.geometry_pass(chr(10).join(Vs), resolver, use_lexicon=False)
    Ls = ts_.split(chr(10))
    oks, whys, fs = tg.grid_invariant(Vs[2:14], Ls[2:15])
    check("a lift passes over a STRAY MARK (an underscore alone in the rail column) and clears it: REVENUE on the group's first row, the invariant names one stray cleared",
          tg.cells(Ls[6])[0] == "REVENUE" and rs_["labels"][0]["placed"] == 6 and oks and fs["labels"][0].get("strays_cleared") == 1, str((Ls[6][:30], rs_["labels"][0], oks, whys, fs["labels"])))
    check("_stray_mark: an underscore, a dot, a dash are marks; a letter, a bullet, an empty cell are not",
          all(tg._stray_mark(c) for c in ("_", ".", "-")) and not any(tg._stray_mark(c) for c in ("S", "F.", "•", "", "٠")))
    print("[12] S156 E1 — the reading of the page (vision.json, a sub-agent panel's sidecar) feeds the layer: a word, a span, a fragment label, a figure call")
    READING = {"format": "vision-reading/1", "produced_by": "selftest", "tables": [
        {"anchor": ["Does the company or its competitors have pricing power?"], "kind": "table",
         "rails": [{"word": "REVENUE", "rows": [1, 6]}, {"word": "COSTS", "rows": [7, 8]}, {"word": "MGMT", "rows": [9, 9]}]}]}
    tv, rv = tg.geometry_pass(VALENTINE + chr(10) + chr(10) + prose[0], None, vision=READING)   # the lexicon without MGMT: the reading lends it
    Lv = tv.split(chr(10))
    labs = {lb["word"]: lb for lb in rv["labels"]}
    check("the reading lends MGMT its word where the lexicon refused (letters fit): applied, how says vision",
          "MGMT" in labs and labs["MGMT"]["how"].startswith("vision") and rv["unresolved"] == 0, str((rv["labels"], rv["unresolved_rails"])))
    check("the reading's spans override the tiled spans: REVENUE [6, 11] from rows [1, 6], COSTS [12, 13], MGMT [14, 14]; the record counts them",
          labs["REVENUE"]["span"] == [6, 11] and labs["COSTS"]["span"] == [12, 13] and labs["MGMT"]["span"] == [14, 14] and rv["vision"]["spans"] == 3 and rv["vision"]["words"] == 1,
          str((labs, rv["vision"])))
    check("the record names the reading: format, tables_matched 1, no figure, nothing unmatched",
          rv["vision"]["format"] == "vision-reading/1" and rv["vision"]["tables_matched"] == 1 and rv["vision"]["figures"] == [] and rv["vision"]["unmatched"] == [], str(rv["vision"]))
    check("the invariant holds on the reading's output (three labels)", tg.grid_invariant(V[2:14], Lv[2:15])[0] and len(tg.grid_invariant(V[2:14], Lv[2:15])[2]["labels"]) == 3,
          str(tg.grid_invariant(V[2:14], Lv[2:15])[1]))
    # a reading that matches nothing changes nothing and says so
    NOPE = {"format": "vision-reading/1", "tables": [{"anchor": ["a sentence this book never printed"], "kind": "table", "rails": [{"word": "MGMT", "rows": [9, 9]}]}]}
    tn, rn = tg.geometry_pass(VALENTINE + chr(10) + chr(10) + prose[0], None, vision=NOPE)
    check("a reading with no matching anchor: tables_matched 0, MGMT stays unresolved, the text as without a reading",
          rn["vision"]["tables_matched"] == 0 and rn["unresolved"] == 1 and tn == tg.geometry_pass(VALENTINE + chr(10) + chr(10) + prose[0], None)[0], str(rn["vision"]))
    check("without a reading the record's vision is None", tg.geometry_pass(VALENTINE, None)[1]["vision"] is None)
    # the fragments: p.72's shape — a rotated phrase the OCR read in three pieces
    FRAG = chr(10).join(["Intro.", "", "|  | New and Unknown | Experienced and Bad |", "|---|---|---|",
                         "| y Stocks | Critical to My Stocks | Do the thing |", "| impact the Topics They Discuss Have on My Stocks | Could Be Critical | Do more |",
                         "| Impact t | Not Critical | Ignore |", "", "Outro."])
    RF = {"format": "vision-reading/1", "tables": [{"anchor": ["Critical to My Stocks"], "kind": "table",
                                                    "rails": [{"word": "Impact the Topics They Discuss Have on My Stocks", "rows": [1, 3]}]}]}
    tf, rf = tg.geometry_pass(FRAG, None, vision=RF)
    Lf = tf.split(chr(10))
    check("a rail the OCR read as three FRAGMENTS is proposed from the reading (every fragment a substring of the label), applied on row 1, the pieces blanked",
          rf["applied"] == 1 and rf["labels"][0]["how"].startswith("vision (fragments") and rf["vision"]["fragment_rails"] == 1
          and tg.cells(Lf[4])[0] == "Impact the Topics They Discuss Have on My Stocks" and tg.cells(Lf[5])[0] == "" and tg.cells(Lf[6])[0] == "",
          str((rf["labels"], rf["vision"], Lf[4][:60], Lf[5][:30])))
    check("the invariant admits the fragment run and names it", tg.grid_invariant(FRAG.split(chr(10))[2:7], Lf[2:7])[0]
          and tg.grid_invariant(FRAG.split(chr(10))[2:7], Lf[2:7])[2]["labels"][0].get("fragments") == 3, str(tg.grid_invariant(FRAG.split(chr(10))[2:7], Lf[2:7])[1]))
    PLANT = FRAG.replace("Have on My Stocks | Could", "Have on My Bonds | Could", 1)   # the S154 panel's own plant: a fragment the label does not contain
    tp, rp = tg.geometry_pass(PLANT, None, vision=RF)
    check("NEGATIVE (the plant): a fragment the label does not contain — 'Bonds' — is never proposed; the table stays as it came; the reading notes it unmatched",
          rp["applied"] == 0 and tp == PLANT and rp["vision"]["unmatched"] and "fragments" in rp["vision"]["unmatched"][0]["why"], str((rp["applied"], rp["vision"])))
    bad = list(Lf)
    bad[5] = "| Bonds | Could Be Critical | Do more |"
    okp, whyp, _ = tg.grid_invariant(FRAG.split(chr(10))[2:7], bad[2:7])
    check("invariant NEGATIVE: a fragment run whose after row carries a piece not in the label is refused", not okp and any("not all pieces" in w for w in whyp), str(whyp))
    # S156 E5 (a lens's finding): the negatives above do not tell an inverted containment test from the real one — a run of ONE
    # fragment does: real refuses "Bonds" for "Stocks" and admits "y Stocks"; an inverted test would do the opposite
    one_b = ["|  | New | Bad |", "|---|---|---|", "| Bonds | Critical to My Stocks | Do |"]
    one_a = ["|  | New | Bad |", "|---|---|---|", "| Impact the Topics They Discuss Have on My Stocks | Critical to My Stocks | Do |"]
    ok1, why1, _ = tg.grid_invariant(one_b, one_a)
    one_g = ["|  | New | Bad |", "|---|---|---|", "| y Stocks | Critical to My Stocks | Do |"]
    ok2, why2, f2 = tg.grid_invariant(one_g, one_a)
    check("invariant, one fragment: 'Bonds' under the label 'Impact … My Stocks' is REFUSED and 'y Stocks' is ADMITTED — the pair that tells an inverted containment test from the real one",
          not ok1 and any("not all pieces" in w for w in why1) and ok2 and f2["labels"] and f2["labels"][0].get("fragments") == 1, str((why1, why2, f2["labels"])))
    # the figure call: the quadrant's HIGH / LOW are axis labels, not rails — the reading silences the table
    FIG = chr(10).join(["Text.", "", "|  | Lipstick on a Pig | Reputation Builder |", "|---|---|---|", "| H<br>G<br>H | prose one | prose two |", "| L<br>O | prose three | prose four |", "", "More."])
    RG = {"format": "vision-reading/1", "tables": [{"anchor": ["Lipstick on a Pig"], "kind": "figure", "rails": []}]}
    tg_, rg = tg.geometry_pass(FIG + chr(10) + "The market is high and the mood is low and high again.", lambda letters, ctx: "HIGH", vision=RG)
    check("a table the reading calls a FIGURE gets no repair: applied 0, its rotated axis letters untouched, the record names the figure",
          rg["applied"] == 0 and rg["vision"]["figures"] == [[3, 6]] and "H<br>G<br>H" in tg_, str((rg["applied"], rg["vision"], rg["unresolved"])))
    tg2, rg2 = tg.geometry_pass(FIG + chr(10) + "The market is high and the mood is low and high again.", lambda letters, ctx: "HIGH", vision=None)
    check("NEGATIVE CONTROL: without the reading the same table IS repaired (HIGH resolved) — the figure call is the reading's alone", rg2["applied"] >= 1 and "HIGH" in tg2, str((rg2["applied"], rg2["labels"])))
    print("[13] S157 E1 — a second stacked heading inside a body SPLITS the table; the tail re-joined from the prose (p.175's shape)")
    P175 = chr(10).join(["Text above.", "",
        "| ANOVA | | | | | | | | |", "|---|---|---|---|---|---|---|---|---|",
        "| | | | | | Sig | gnificance | | |", "| | Df | SS | MS | F | | F | | |",
        "| Regression | 1.00 | 0.74 | 0.74 | 100 | .63 | 0.00 | | |", "| Residual | 52.00 | 0.38 | 0.01 | | | | | |", "| Total | 53.00 | 1.12 | | | | | | |",
        "| | | Standard | | P- | Lower | Upper | Lower | Upper |", "| | Coefficients | Error | t Stat | value | 95% | 95% | 95% | 95% |",
        "| Intercept | -4.26 | 0.71 | -5.96 | 0.00 | -5.69 | -2.82 | -5.69 | -2.82 |", "| log | | | | | | | | |", "| /manufacturin | | | | | | | | |",
        "", "Copyright McGraw-Hill and AnalystSolutions", "", "indev)", "", "3.58 0.36 10.03 0.00 2.86 4.29 2.86 4.29", "",
        "Using the regression tool, the standard error, the coefficients and the t stat matter; the value and the lower and upper bounds too.",
        "The standard error and the coefficients: the lower value, the upper value, the stat."])
    lx = tg.lexicon(P175.split(chr(10)))
    sp = tg.propose_splits(P175.split(chr(10)), lx)
    check("one split proposed at the stacked pair, the header the pair's fold, the tail re-joined from the label rows + the lone word + the numbers",
          len(sp) == 1 and sp[0]["header"] == ["", "Coefficients", "Standard Error", "t Stat", "P-value", "Lower 95%", "Upper 95%", "Lower 95%", "Upper 95%"]
          and sp[0]["rejoin"] and sp[0]["rejoin"]["row"] == ["log /manufacturin indev)", "3.58", "0.36", "10.03", "0.00", "2.86", "4.29", "2.86", "4.29"], str(sp))
    new13, ap13, rf13 = tg.split_pass(P175.split(chr(10)), lx)
    tb = tg.table_blocks(new13)
    check("applied: two tables after (ANOVA with its three rows; the coefficients with the Intercept row and the re-joined row), the prose lines consumed, the footer kept",
          len(ap13) == 1 and not rf13 and len(tb) == 2 and tg.cells(new13[tb[1][0]])[1] == "Coefficients" and tb[1][2] - tb[1][1] == 2
          and (chr(10) + "indev)" + chr(10)) not in chr(10).join(new13) and (chr(10) + "3.58 0.36") not in chr(10).join(new13) and "Copyright McGraw-Hill" in chr(10).join(new13), str((ap13, rf13, tb)))
    tt, rr = tg.geometry_pass(P175, None)
    check("geometry_pass runs the split first and records it; the two tables then get the ordinary pass (no refusal)", rr["splits"] and rr["splits"][0]["rejoined"]["row"][0] == "log /manufacturin indev)" and rr["splits_refused"] == [] and rr["refused"] == 0
          and rr["splits"][0]["rejoined"]["consumed_lines"] == [P175.split(chr(10)).index("indev)") + 1, P175.split(chr(10)).index("indev)") + 2, P175.split(chr(10)).index("3.58 0.36 10.03 0.00 2.86 4.29 2.86 4.29") + 1], str((rr["splits"], rr["splits_refused"], rr["refused"])))
    # negatives
    NUMPAIR = P175.replace("| | | Standard | | P- | Lower | Upper | Lower | Upper |", "| | 1.5 | Standard | | P- | Lower | Upper | Lower | Upper |")
    check("NEGATIVE: a number in the pair — no split", tg.propose_splits(NUMPAIR.split(chr(10)), lx) == [])
    NOABOVE = P175.replace("| Total | 53.00 | 1.12 | | | | | | |", "| Total | | | | | | | | |")
    check("NEGATIVE: no data row above the pair — no split", tg.propose_splits(NOABOVE.split(chr(10)), lx) == [])
    WRONGCOUNT = P175.replace("3.58 0.36 10.03 0.00 2.86 4.29 2.86 4.29", "3.58 0.36 10.03 0.00 2.86 4.29 2.86")
    spw = tg.propose_splits(WRONGCOUNT.split(chr(10)), lx)
    check("NEGATIVE: a prose line with the wrong token count — the split still proposed, the tail NOT re-joined (the label rows stay, the prose stays)", len(spw) == 1 and spw[0]["rejoin"] is None, str(spw))
    tw, rw = tg.geometry_pass(WRONGCOUNT, None)
    check("… and applied that way: two tables, the label rows kept, the prose kept", len(tg.table_blocks(tw.split(chr(10)))) == 2 and "3.58 0.36 10.03 0.00 2.86 4.29 2.86" in tw and "| /manufacturin |" in tw, str(rw["splits"]))
    bad = list(new13)
    kb = next(k for k, ln in enumerate(bad) if ln.startswith("| log /manufacturin indev) |"))
    bad[kb] = bad[kb].replace("| 3.58 |", "| 3.59 |", 1)
    okb, whyb = tg.split_invariant(P175.split(chr(10))[2:21], bad[2:tb[1][2] + 1], sp[0])
    check("invariant NEGATIVE: a re-joined number changed is refused", not okb and any("re-joined row" in w or "table B" in w for w in whyb), str(whyb))
    # the held copy's shape: the heading already stacked by the OCR in ONE row with <br>; the tail scattered over two prose lines
    # with a number lost — the split happens, the tail is NOT re-joined (a re-join would invent a number)
    P175B = chr(10).join(["indev)", "", "| | | | | | Si | gnificance | | |", "|---|---|---|---|---|---|---|---|---|", "| | Df | SS | MS | F | | F | | |",
        "| Regression | 1.00 | 0.74 | 0.74 | 100 | .63 | 0.00 | | |", "| Residual | 52.00 | 0.38 | 0.01 | | | | | |", "| Total | 53.00 | 1.12 | | | | | | |",
        "| | Coefficients | Standard<br>Error | t Stat | P.<br>value | Lower<br>95% | Upper<br>95% | Lower<br>95% | Upper<br>95% |",
        "| Intercept | -4.26 | 0.71 | -5.96 | 0.00 | -5.69 | -2.82 | -5.69 | -2.82 |", "| log<br>(manufacturing | | | | | | | | |", "",
        "0.00 2.86 4.29 2.86 4.29", "", "Copyright McGraw-Hill and AnalystSolutions", "", "3.58 0.36", "",
        "Using the regression tool, the standard error, the coefficients and the t stat matter; the value and the lower and upper bounds too.",
        "The standard error and the coefficients: the lower value, the upper value, the stat."])
    lxb = tg.lexicon(P175B.split(chr(10)))
    spb = tg.propose_splits(P175B.split(chr(10)), lxb)
    check("the held copy's shape: a ONE-row <br> heading splits the table (pair 1), the header unstacked, the scattered tail NOT re-joined",
          len(spb) == 1 and spb[0]["pair"] == 1 and spb[0]["header"][2] == "Standard Error" and spb[0]["header"][4] == "P. value" and spb[0]["rejoin"] is None, str(spb))
    newb, apb, rfb = tg.split_pass(P175B.split(chr(10)), lxb)
    check("… applied: two tables, the label row kept, both prose lines kept (nothing invented)", len(apb) == 1 and not rfb and len(tg.table_blocks(newb)) == 2
          and "| log<br>(manufacturing |" in chr(10).join(newb) and "0.00 2.86 4.29 2.86 4.29" in newb and "3.58 0.36" in newb, str((apb, rfb)))
    check("idempotent: a second split pass proposes nothing", tg.propose_splits(new13, lx) == [] and tg.propose_splits(newb, lxb) == [])
    check("a healthy table with a numeric body proposes no split", tg.propose_splits(HEALTHY.split(chr(10)), lx) == [] and tg.propose_splits(VALENTINE.split(chr(10)), lx) == [])
    print("[14] S157 E3 — trailing columns nothing fills are TRIMMED (p204-t1's shape: 2 real columns + 3 empty); nothing else")
    P204 = chr(10).join(["Exhibit 12.10 Regression Output for Lagged Values", "",
        "| Regression Statistics | |  |  |  |", "|-----------------------|-------|--|--|--|",
        "| Multiple R | 0.97  |  |  |  |", "| R-squared | 0.94  |  |  |  |", "| Adjusted R-square | 0.94  |  |  |  |",
        "| Standard Error | 0.03  |  |  |  |", "| Observations | 53.00 |  |  |  |", "", "The regression says little."])
    tp = tg.propose_trims(P204.split(chr(10)))
    check("one trim proposed: the last 3 of 5 columns", len(tp) == 1 and tp[0]["cols"] == 5 and tp[0]["drop"] == 3 and tp[0]["table"] == [3, 9], str(tp))
    new14, ap14, rf14 = tg.trim_pass(P204.split(chr(10)))
    tb14 = tg.table_blocks(new14)
    check("applied: one table of two columns, six rows, every cell kept, the delimiter's two segments the before's first two",
          len(ap14) == 1 and not rf14 and len(tb14) == 1 and all(len(tg.cells(new14[k])) == 2 for k in range(tb14[0][0], tb14[0][2] + 1) if k != tb14[0][1])
          and tg.cells(new14[tb14[0][2]]) == ["Observations", "53.00"] and new14[tb14[0][1]] == "|-----------------------|-------|"
          and new14[0] == "Exhibit 12.10 Regression Output for Lagged Values" and new14[-1] == "The regression says little.", chr(10).join(new14))
    tt, rr = tg.geometry_pass(P204, None)
    check("geometry_pass records the trim; no refusal; the table then passes the ordinary pass unchanged",
          rr["trims"] == [{"table": [3, 9], "cols": 5, "drop": 3, "why": "the last 3 of 5 columns hold nothing in 6 rows"}] and rr["trims_refused"] == [] and rr["refused"] == 0
          and "| Observations | 53.00 |" in tt and "|  |  |  |" not in tt, str((rr["trims"], rr["trims_refused"], rr["refused"])))
    check("idempotent: a second trim pass proposes nothing", tg.propose_trims(new14) == [])
    # negatives
    DOT = chr(10).join(["| a | b | |", "|---|---|---|", "| 1 | 2 | " + chr(8226) + " |", "| 3 | 4 | |"])
    check("NEGATIVE: a glyph in the last column (S78's 418 dots) — no trim", tg.propose_trims(DOT.split(chr(10))) == [])
    LEAD = chr(10).join(["| | b | c |", "|---|---|---|", "| | 2 | 3 |", "| | 4 | 5 |"])
    check("NEGATIVE: a leading empty column (a rail's column) — no trim", tg.propose_trims(LEAD.split(chr(10))) == [])
    RAG = chr(10).join(["| a | b | |", "|---|---|---|", "| 1 | 2 |", "| 3 | 4 | |"])
    check("NEGATIVE: ragged rows — no trim", tg.propose_trims(RAG.split(chr(10))) == [])
    FLOOR = chr(10).join(["| a | | |", "|---|---|---|", "| 1 | | |", "| 3 | | |"])
    fp = tg.propose_trims(FLOOR.split(chr(10)))
    check("the floor: a table whose every column but one is empty keeps two (one column dropped, not two)", len(fp) == 1 and fp[0]["drop"] == 1, str(fp))
    check("NEGATIVE: a table with a health issue is left alone", tg.propose_trims(["| a | b | |", "|---|---|", "| 1 | 2 | |"]) == []
          or not tg.health(["| a | b | |", "|---|---|", "| 1 | 2 | |"]), "health: " + str(tg.health(["| a | b | |", "|---|---|", "| 1 | 2 | |"])))
    bad = list(new14)
    bad[tb14[0][2]] = "| Observations | 53.01 |"
    okb, whyb = tg.trim_invariant(P204.split(chr(10))[2:9], bad[2:9], tp[0])
    check("invariant NEGATIVE: a kept cell changed is refused", not okb and any("not the before row cut" in w for w in whyb), str(whyb))
    bad2 = list(new14)
    bad2[tb14[0][1]] = "|---|---|"
    okc, whyc = tg.trim_invariant(P204.split(chr(10))[2:9], bad2[2:9], tp[0])
    check("invariant NEGATIVE: the delimiter's kept segments changed is refused", not okc and any("delimiter" in w for w in whyc), str(whyc))
    P204X = P204.replace("| Observations | 53.00 |  |  |  |", "| Observations | 53.00 |  | x |  |")
    okd, whyd = tg.trim_invariant(P204X.split(chr(10))[2:9], new14[2:9], tp[0])
    check("invariant NEGATIVE: a removed cell that was not blank is refused", not okd and any("not blank" in w for w in whyd), str(whyd))
    # the split's second table is trimmed after the split (the ANOVA of p.175 keeps 9 columns, 2 of them empty)
    tt2, rr2 = tg.geometry_pass(P175, None)
    anova = [ln for ln in tt2.split(chr(10)) if ln.startswith("| Regression |")]
    check("after the split, the ANOVA table's two empty trailing columns are trimmed (9 -> 7); the coefficients table keeps its 9",
          rr2["splits"] and len(rr2["trims"]) == 1 and rr2["trims"][0]["cols"] == 9 and rr2["trims"][0]["drop"] == 2
          and anova and len(tg.cells(anova[0])) == 7 and "| log /manufacturin indev) | 3.58 | 0.36 | 10.03 | 0.00 | 2.86 | 4.29 | 2.86 | 4.29 |" in tt2, str((rr2["trims"], anova)))
    check("no trim on a healthy table, on the rails fixture, on the reading fixture", tg.propose_trims(HEALTHY.split(chr(10))) == [] and tg.propose_trims(VALENTINE.split(chr(10))) == [], "")
    print("[15] S157 E15 — a run that is an INDEX is not a rail (Ashby's transition matrices; the shelf probe's false labels)")
    ASHBY1 = chr(10).join(["The matrix of transitions.", "",
        "| $\\downarrow$ | <br>3   | 4   | 5   | 6                      |", "|--------------|---------|-----|-----|------------------------|",
        "|              | <br>    |     |     | <br>0<br>0<br>0<br>1/2 |", "| 3            | <br>1/2 | 0   | 0   | 0                      |",
        "| 4            | <br>1/2 | 1/2 | 0   | 0                      |", "| 5            | <br>0   | 1/2 | 1/2 | 0                      |",
        "| 6            | <br>0   | 0   | 1/2 | 1/2                    |", "|              | <br>    |     |     |                        |", "",
        "The elastic band is elastic; elastic ideas add; ideas adds adds. Elastic ideas."])
    lx15 = tg.lexicon(ASHBY1.split(chr(10)))
    ps15 = tg.propose(ASHBY1.split(chr(10)), None, lx15)
    rails15 = [p for p in ps15 if p["kind"] == "rail"]
    check("R1: the row labels 3 4 5 6 are refused as digits, no word sought (the lexicon holds ELASTIC and the glyphs 3,4,5 read e,a,s)",
          rails15 and all(p["word"] is None and "digits" in (p["refused"] or "") for p in rails15), str(rails15))
    t15, r15 = tg.geometry_pass(ASHBY1, None)
    check("… and the pass leaves the matrix's row labels in place", "| 3            | <br>1/2 |" in t15 and "ELASTIC" not in t15 and r15["labels"] == [], str(r15["labels"]))
    ASHBY2 = chr(10).join(["Table 13/7/1.", "", "| ↓      | α      | β      | γ      |", "|--------|--------|--------|--------|",
        "| a<br>b | α<br>β | α<br>β | α<br>β |", "| c      | γ      | γ      | γ      |", "",
        "The ABC of regulation: ABC, abc and ABC again; the abc rule."])
    lx2 = tg.lexicon(ASHBY2.split(chr(10)))
    r2 = [p for p in tg.propose(ASHBY2.split(chr(10)), None, lx2) if p["kind"] == "rail"]
    check("R3: a stacked letter cell whose row is stacked alike across every column is refused as merged rows (a<br>b beside α<br>β)",
          r2 and all(p["word"] is None and "merged rows" in (p["refused"] or "") for p in r2), str(r2))
    # E22's verifier V1 found the first fixture never fired the rail signature (no blank between the runs) and the check passed
    # vacuously on `(not r3) or …` — the fixture is now the real Ashby shape (p.4455: a / blank / b / blank / c with the
    # probabilities split over two rows), the runs fire, and the check REQUIRES them refused
    ASHBY3 = chr(10).join(["| ↓ | a | b | c |", "|---|---|---|---|", "| a | 0. | 0. | 0. |", "| | 2 | 3 | 1 |", "| b | 0. | 0. | 0. |",
        "| | 8 | 7 | 5 |", "| c | | | 0.<br>4 |", "", "The abc rule; ABC; abc; the ABC of it."])
    lx3 = tg.lexicon(ASHBY3.split(chr(10)))
    r3 = [p for p in tg.propose(ASHBY3.split(chr(10)), None, lx3) if p["kind"] == "rail"]
    check("R2: a run whose every glyph is one of the table's own column headings is refused as a matrix index (three runs a, b, c — each fired, each refused)",
          len(r3) == 3 and all(p["word"] is None and "matrix index" in (p["refused"] or "") for p in r3), str(r3))
    # positive control: one digit among five glyphs is still a rail (6OSTs -> COSTS); the fixture's text holds the word
    COSTS = chr(10).join(["|  | Questions to be investigated | Company documents | Market data |", "|---|---|---|---|",
        "| 6 | Are there any major productivity initiatives? | • |  |", "| O<br>S<br>T | Where is the company making its major investments? | • | • |",
        "| s | What are the costs of the plan? |  | • |", "|  | How do the costs compare? | • |  |", "",
        "The costs of the plan; costs matter; the costs again."])
    tc, rc = tg.geometry_pass(COSTS, None)
    check("positive control: a digit among letters (6OSTs) is an OCR glyph, not a number — COSTS still resolves under R1",
          [lb["word"] for lb in rc["labels"]] == ["COSTS"], str((rc["labels"], rc["unresolved_rails"])))
    check("positive control: the FIG fixture's stacked rail beside prose is not 'merged rows' (R3 counts <br> stacking, not words)",
          tg._index_run(FIG.split(chr(10)), 2, [4], ["H<br>G<br>H"]) is None and tg._index_run(FIG.split(chr(10)), 2, [5], ["L<br>O"]) is None, "")
    print("[16] S157 E20 — a tail that duplicates the next table's head is the next table's (p.200's leaked ANOVA head)")
    P200 = chr(10).join(["Exhibit 12.7 Regression Output", "",
        "| Multiple R | 0.81 | |", "|--------------------|-------|--------------|", "| R-squared | 0.66 | |", "| Adjusted R-squared | 0.65 | |",
        "| Standard Error | 0.09 | |", "| Observations | 54.00 | |", "| ANOVA | | |", "| | | Significance |", "",
        "| ANOVA | | | | | | |", "|---|---|---|---|---|---|---|", "| | | | | | Sig | gnificance |", "| | Df | SS | MS | F | | F |",
        "| Regression | 1.00 | 0.74 | 0.74 | 100 | .63 | 0.00 |", "| Residual | 52.00 | 0.38 | 0.01 | | | |", "", "After."])
    lp = tg.propose_leaks(P200.split(chr(10)))
    check("one leak proposed: the two tail rows (ANOVA; Significance) duplicate the next table's head, the title anchoring it",
          len(lp) == 1 and lp[0]["drop"] == [9, 10] and lp[0]["table"] == [3, 10] and lp[0]["next"] == [12, 17], str(lp))
    n16, ap16, rf16 = tg.leak_pass(P200.split(chr(10)))
    tb16 = tg.table_blocks(n16)
    check("applied: the statistics table ends at Observations, the ANOVA table untouched, nothing else moved",
          len(ap16) == 1 and not rf16 and len(tb16) == 2 and tg.cells(n16[tb16[0][2]])[0] == "Observations" and n16[tb16[1][0]].startswith("| ANOVA |")
          and "| | | Significance |" not in n16 and "| | | | | | Sig | gnificance |" in n16 and n16[-1] == "After.", chr(10).join(n16))
    t16, r16 = tg.geometry_pass(P200, None)
    check("geometry_pass: the leak first, then the trim drops the emptied third column — 2 columns, 5 rows; the ANOVA keeps its 7",
          r16["leaks"] and r16["leaks_refused"] == [] and any(tr["table"][0] == 3 and tr["drop"] == 1 for tr in r16["trims"])
          and "| Observations | 54.00 |" in t16 and "| Multiple R | 0.81 |" in t16, str((r16["leaks"], r16["trims"])))
    check("idempotent: a second pass proposes no leak", tg.propose_leaks(n16) == [])
    # negatives
    NUM = P200.replace("| ANOVA | | |" + chr(10) + "| | | Significance |", "| Total | 53.00 | |" + chr(10) + "| | | Significance |")
    check("NEGATIVE: a tail row with a number is never a leak", tg.propose_leaks(NUM.split(chr(10))) == [])
    NOTITLE = P200.replace("| ANOVA | | |" + chr(10) + "| | | Significance |", "| Notes | | |" + chr(10) + "| | | Significance |")   # the tail line only (a bare replace also hit the next header)
    check("NEGATIVE: a tail row that is not the next table's title does not anchor a leak (Notes)", tg.propose_leaks(NOTITLE.split(chr(10))) == [])
    FAR = P200.replace("| | | Significance |" + chr(10) + "", "| | | Significance |" + chr(10) + chr(10) + "Some prose between." + chr(10) + chr(10) + "")
    check("NEGATIVE: a next table more than three lines away is not a neighbour", tg.propose_leaks(FAR.split(chr(10))) == [])
    bad = list(n16)
    bad[tb16[0][2]] = "| Observations | 54.01 | |"
    okl, whyl = tg.leak_invariant(P200.split(chr(10))[2:17], bad[2:15], lp[0])
    check("invariant NEGATIVE: a kept cell changed is refused", not okl and any("not the before table cut" in w for w in whyl), str(whyl))
    check("no leak on the healthy fixtures or p.175's split shape", tg.propose_leaks(HEALTHY.split(chr(10))) == [] and tg.propose_leaks(P175.split(chr(10))) == [], "")

    # ---- S160 E6: the STUBS — a header with no filled body cell, unframed to the prose it is; the lever OFF by default ----
    STUBS = "\n".join([
        "Some prose above.",
        "",
        "| Figure 7.5 Default Spreads and Ratings |",          # a caption box, header only (table 3-4)
        "|---|",
        "",
        "| Phi | loson | hv |",                                 # a chopped heading, three cells (table 6-7)
        "|---|---|---|",
        "",
        "| Announce ment Date |",                               # a chopped heading (the shelf's own shape), one all-blank body row (table 9-11)
        "|---|",
        "|  |",
        "",
        "| Company | Beta |",                                   # NEGATIVE: one filled body cell — a real table, not a stub (table 13-15)
        "|---|---|",
        "| Nike | 0.9 |",
        "",
        "|  |  |",                                              # NEGATIVE: a header of empty cells says nothing (table 17-18)
        "|---|---|",
        "",
        "Some prose below.",
    ])
    sl = STUBS.split(chr(10))
    up = tg.propose_unframes(sl)
    # the TRACE class — never proposed, always named: a stacked <br> cell (the crammed table's one cell) and a grid of blank rows
    TRACES = "\n".join([
        "| Company Name<br>Beta<br>Nike<br>0.9<br>Adidas<br>1.1 |",   # the crammed cell: 6 stacked pieces, 3 blank rows (table 1-5)
        "|---|",
        "|  |",
        "|  |",
        "|  |",
        "",
        "| 7 Buildings of better quality should command higher rents. |",   # a footnote with a grid of 12 blank rows (table 7-19)
        "|---|",
    ] + ["|  |"] * 12 + [
        "",
        "| TABLE 25.2<br> |",                                    # one non-blank piece and a trailing <br>: a FRAME, not a trace (table 21-23)
        "|---|",
        "|  |",
    ])
    tl = TRACES.split(chr(10))
    st = tg.find_stubs(tl)
    check("find_stubs classes the stacked cell and the blank grid as traces, the trailing-<br> caption as a frame",
          [(p["table"], p["class"], p["body_rows"], p["br_pieces"]) for p in st] == [([1, 5], "trace", 3, 6), ([7, 20], "trace", 12, 1), ([22, 24], "frame", 1, 1)],
          str([(p["table"], p["class"], p["body_rows"], p["br_pieces"]) for p in st]))
    check("the trace threshold is the shelf's split: STUB_TRACE_ROWS 2 (0–1 blank rows a frame; the shelf's traces start at 10)", tg.STUB_TRACE_ROWS == 2, str(tg.STUB_TRACE_ROWS))
    check("NEGATIVE: a trace is never proposed — only the frame is", [p["table"] for p in tg.propose_unframes(tl)] == [[22, 24]], str(tg.propose_unframes(tl)))
    tl_on, ta, tr, tp, tt = tg.unframe_pass(tl, apply=True)
    check("lever ON over the traces: the two traces stand byte-identical and are returned named; the frame is unframed to 'TABLE 25.2'",
          tl_on[:20] == tl[:20] and len(tt) == 2 and len(ta) == 1 and tl_on[21] == "TABLE 25.2" and len(tl_on) == 22, str((len(tt), len(ta), tl_on[20:])))
    tt_off, r_tr = tg.geometry_pass(TRACES, None)
    check("geometry_pass names the traces in the record (stub_traces, with body_rows and br_pieces) and counts them in stubs",
          r_tr["stubs"] == 3 and [(x["body_rows"], x["br_pieces"]) for x in r_tr["stub_traces"]] == [(3, 6), (12, 1)] and len(r_tr["unframes_proposed"]) == 1
          and tt_off == TRACES, str((r_tr["stubs"], r_tr["stub_traces"])))
    check("three stubs proposed and only three: the caption box, the chopped heading, the chopped heading with a blank row",
          [p["table"] for p in up] == [[3, 4], [6, 7], [9, 11]], str([p["table"] for p in up]))
    check("the caption box becomes its own line; a chopped heading stays chopped (space-joined, never guessed)",
          [p["text"] for p in up] == ["Figure 7.5 Default Spreads and Ratings", "Phi loson hv", "Announce ment Date"], str([p["text"] for p in up]))
    check("a caption Marker broke in two (`TABLE<br>25.2`, two pieces — the 4e's own) is a frame and reads `TABLE 25.2`",
          [(p["class"], p["br_pieces"], p["text"]) for p in tg.find_stubs(["| TABLE<br>25.2 |  |", "|---|---|", "|  |  |"])] == [("frame", 2, "TABLE 25.2")],
          str(tg.find_stubs(["| TABLE<br>25.2 |  |", "|---|---|", "|  |  |"])))
    check("NEGATIVE: a cell stacked THREE deep (`Company<br>Beta<br>Nike`) is a trace — the crammed class's signature (STUB_TRACE_PIECES 3)",
          tg.STUB_TRACE_PIECES == 3 and [(p["class"], p["br_pieces"]) for p in tg.find_stubs(["| Company<br>Beta<br>Nike |", "|---|", "|  |"])] == [("trace", 3)], "")
    check("body_rows counts the blank rows: 0, 0, 1", [p["body_rows"] for p in up] == [0, 0, 1], str([p["body_rows"] for p in up]))
    check("NEGATIVE: a table with one filled body cell is not a stub; NEGATIVE: an all-empty header is not proposed (nothing to write)",
          all(p["table"] not in ([13, 15], [17, 18]) for p in up), "")
    check("the lever is OFF (UNFRAME_STUBS False) — the module's default, his word to move", tg.UNFRAME_STUBS is False, str(tg.UNFRAME_STUBS))
    l_off, a_off, r_off, p_off, t_off0 = tg.unframe_pass(sl)
    check("lever OFF: nothing changes and every stub comes back proposed; no trace among these", l_off == sl and a_off == [] and r_off == [] and len(p_off) == 3 and t_off0 == [], str((len(a_off), len(p_off))))
    l_on, a_on, r_on, p_on, _t_on = tg.unframe_pass(sl, apply=True)
    check("lever ON: three unframes applied, none refused; the tables are gone and the prose stands",
          len(a_on) == 3 and r_on == [] and p_on == [] and tg.table_blocks(l_on) == [(8, 9, 10), (12, 13, 13)]
          and "Figure 7.5 Default Spreads and Ratings" in l_on and "Phi loson hv" in l_on and "Announce ment Date" in l_on
          and "| Nike | 0.9 |" in l_on, str((len(a_on), r_on, tg.table_blocks(l_on))))
    check("lever ON: the surviving lines are exactly the before lines with each stub's lines replaced by its one line",
          l_on == ["Some prose above.", "", "Figure 7.5 Default Spreads and Ratings", "", "Phi loson hv", "", "Announce ment Date", "",
                   "| Company | Beta |", "|---|---|", "| Nike | 0.9 |", "", "|  |  |", "|---|---|", "", "Some prose below."], str(l_on))
    before3 = sl[5:7]
    ok_u, why_u = tg.unframe_invariant(before3, ["Phi loson hv"], up[1])
    check("invariant admits the exact unframing", ok_u, str(why_u))
    ok_m1, why_m1 = tg.unframe_invariant(before3, ["Phi hv"], up[1])
    check("invariant NEGATIVE: a header cell dropped is refused", not ok_m1 and any("letters" in w for w in why_m1), str(why_m1))
    ok_m2, why_m2 = tg.unframe_invariant(before3, ["Philosophy"], up[1])
    check("invariant NEGATIVE: a guessed word (letters that were not there) is refused", not ok_m2, str(why_m2))
    ok_m3, why_m3 = tg.unframe_invariant(before3, ["Phi loson hv", ""], up[1])
    check("invariant NEGATIVE: two lines after is refused", not ok_m3 and any("one line" in w for w in why_m3), str(why_m3))
    ok_m4, why_m4 = tg.unframe_invariant(sl[12:15], ["Company Beta"], {"table": [13, 15]})
    check("invariant NEGATIVE: a filled body cell is refused (the table is not a stub)", not ok_m4 and any("not blank" in w for w in why_m4), str(why_m4))
    t_off, r_rec = tg.geometry_pass(STUBS, None)
    check("geometry_pass with the lever OFF: the text is byte-identical, the record names 3 stubs as proposed, 0 applied",
          t_off == STUBS and r_rec["stubs"] == 3 and len(r_rec["unframes_proposed"]) == 3 and r_rec["unframes"] == [] and r_rec["unframes_refused"] == [],
          str((t_off == STUBS, r_rec["stubs"], len(r_rec["unframes_proposed"]))))
    check("geometry_pass: the proposed record carries the line each stub would become",
          [x["text"] for x in r_rec["unframes_proposed"]] == ["Figure 7.5 Default Spreads and Ratings", "Phi loson hv", "Announce ment Date"], str(r_rec["unframes_proposed"]))
    saved = tg.UNFRAME_STUBS
    try:
        tg.UNFRAME_STUBS = True
        t_on, r_on2 = tg.geometry_pass(STUBS, None)
        check("geometry_pass with the lever ON: 3 applied, 0 refused, 0 proposed; the stubs are prose; the real table untouched",
              r_on2["stubs"] == 3 and len(r_on2["unframes"]) == 3 and r_on2["unframes_refused"] == [] and r_on2["unframes_proposed"] == []
              and "| Figure 7.5" not in t_on and "Figure 7.5 Default Spreads and Ratings" in t_on and "| Nike | 0.9 |" in t_on, str(r_on2["unframes"]))
    finally:
        tg.UNFRAME_STUBS = saved
    check("no stub on the healthy fixtures, Valentine's exhibit, p.175, p.200, p.204",
          all(tg.propose_unframes(x.split(chr(10))) == [] for x in (HEALTHY, VALENTINE, P175, P200, P204)), "")
    # S186 E1 (SYM-134): the header fused into the first DATA row — the specimen from held Data Science for Business, Table 10-2
    T102_BEFORE = ["*Table 10-2. Term count representation.*", "",
                   "|    | a | explain | hard | has | is | jazz | music | natural | rhythm | swing | to |",
                   "|----|---|---------|------|-----|----|------|-------|---------|--------|-------|----|",
                   "| d1 | 1 | 0       | 0    | 1   | 0  | 1    | 1     | 0       | 1      | 1     | 0  |",
                   "| d2 | 0 | 1       | 1    | 0   | 1  | 0    | 0     | 0       | 0      | 1     | 1  |",
                   "| d3 | 1 | 0       | 0    | 0   | 1  | 0    | 0     | 1       | 2      | 1     | 0  |"]
    T102_FUSED = ["*Table 10-2. Term count representation.*", "",
                  "| d1 | a 1 | explain 0 | hard 0 | has 1 | is 0 | jazz 1 | music 1 | natural 0 | rhythm 1 | swing 1 | to 0 |",
                  "|----|---|---------|------|-----|----|------|-------|---------|--------|-------|----|",
                  "| d2 | 0 | 1       | 1    | 0   | 1  | 0    | 0     | 0       | 0      | 1     | 1  |",
                  "| d3 | 1 | 0       | 0    | 0   | 1  | 0    | 0     | 1       | 2      | 1     | 0  |"]
    ok134, why134, _f = tg.grid_invariant(T102_BEFORE, T102_FUSED)
    check("SYM-134: a header row fused into the first DATA row is REFUSED by the invariant, the reason naming data",
          not ok134 and any("data" in w and "SYM-134" in w for w in why134), str(why134))
    check("SYM-134 POSITIVE CONTROL: a real stacked heading (letters under letters) is still a header fold",
          tg._fold_allowed(["", "Standard", "", "P-", "Lower"], ["Coefficients", "Error", "t Stat", "value", "95%"], header=True)[0], "")
    check("SYM-134 the refusal names the rule: `_fold_allowed(header=True)` on a numeric lower row",
          not tg._fold_allowed(["", "a", "explain"], ["d1", "1", "0"], header=True)[0], "")
    # S209 E13 — SYM-144 (found read-only by Codex, MSG-CDX-0086; replayed by the Fable lane): CIBC's 2025 annual report, marker
    # line 8672 — a DATA row the OCR stacked with <br> (`12,031<br>1,764<br>231<br>5,836`) under a BR-stacked label, read by
    # _heading_pair as a stacked HEADING because _is_num tested the whole cell; the join dropped the figures (12,031: 6 → 5).
    A144 = ["", "Total revenue<br>Provision for credit losses<br>Amortization and impairment (5)<br>Other non-interest expenses",
            "12,031<br>1,764<br>231<br>5,836", "6,902<br>166<br>2<br>3,520", "3,216<br>175<br>4<br>1,857"]
    B144 = ["", "Income (loss) before income<br>taxes<br>Income taxes (2)", "4,200<br>1,093", "3,214<br>873", "1,180<br>222"]
    ABOVE144 = ["2025", "Net interest income (2)<br>Non-interest income (3)(4)", "\\$<br>9,629<br>2,402", "\\$<br>2,960<br>3,942", "\\$ 2,205 \\$<br>1,011"]
    ok144, _j144, why144 = tg._heading_pair(A144, B144, ABOVE144, None)
    check("SYM-144: a <br>-stacked DATA row under a stacked label is NOT a stacked heading (the refusal names the number)",
          not ok144 and why144 == "a number in the pair", why144)
    check("SYM-144 `_has_num`: a stacked figure cell is numeric; a dollar-sign piece beside figures is numeric; a heading with a percent is not; a word is not",
          tg._has_num("12,031<br>1,764<br>231<br>5,836") and tg._has_num("\\$<br>9,629<br>2,402") and not tg._has_num("Lower<br>95%")
          and not tg._has_num("Standard") and tg._has_num("1"), "")
    check("SYM-144 POSITIVE CONTROL: the regression's stacked heading pair (words over words, a percent in the lower row) is still a heading",
          tg._heading_pair(["", "Standard", "", "P-", "Lower"], ["", "Error", "t Stat", "value", "95%"], ["x", "1.2", "0.3", "2.1", "0.5"], None)[0], "")
    ok144b, _j, why144b = tg._heading_row_br(["", "Total revenue<br>Provision", "12,031<br>1,764", "6,902<br>166", "3,216<br>175"], ["2025", "Net<br>income", "9,629<br>2,402", "2,960", "2,205"], None)
    check("SYM-144: the one-row <br> heading rule refuses a stacked DATA row the same way", not ok144b and why144b == "a number in the row", why144b)
    print("%s: %d/%d" % ("ALL OK" if not FAILS else "FAILED", N - FAILS, N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
