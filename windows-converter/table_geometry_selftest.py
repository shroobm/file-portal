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

    print("%s: %d/%d" % ("ALL OK" if not FAILS else "FAILED", N - FAILS, N))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
