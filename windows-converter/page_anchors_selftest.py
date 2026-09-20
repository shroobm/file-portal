# -*- coding: utf-8 -*-
"""page_anchors_selftest.py — the anchors' tripwires (S209 E6). Hermetic: no files, no pipeline. Each case violates the
property its rule stands for: a page anchored on its first paragraph; a second run adds nothing (idempotent); a table-only
page gets the structured form (a bare `^pN` line after the table, a blank line each side) and a second run adds nothing; a hit
on a table row yields to the next-nearest hit; a contents list that quotes the next page's heading does not take its anchor;
a page whose first six blocks are short is anchored on a later one; a short key is accepted only when unique; a line inside
a fence is never anchored; a runaway fence (> MAX_FENCE
lines) does not swallow the book; a repeated running head does not drag the cursor past a page's real text (the nearest hit
wins); CRLF is kept. Prints `==== page_anchors selftest: N/N ====`, exit 0 green · 1 red."""
import sys

import page_anchors as pa

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  ← " + str(detail)[:140]) if (detail and not cond) else ""))


def block(page, text, kind="Text"):
    return {"page": page, "block_type": kind, "html": "<p>%s</p>" % text}


P1 = "The regulator can block only as much disturbance as it has variety to match, and no more than that."
P2 = "Feedback that is too brusque will make the rudder overshoot, and the ship will hunt about its course."
P3 = "A table of contributions to growth follows on this page, with four year columns and a memo line below."

# 1 · two pages anchored on their first paragraphs
md = "# Title\n\n%s\nSecond line of the paragraph.\n\n%s\n" % (P1, P2)
out, a, t = pa.anchor_markdown(md, [block(0, P1), block(1, P2)])
case("two pages anchored on their first paragraph's last line", a == 2 and t == 2 and "Second line of the paragraph. ^p1" in out and out.rstrip().endswith("^p2"), out[-120:])
# 2 · idempotent
out2, a2, _ = pa.anchor_markdown(out, [block(0, P1), block(1, P2)])
case("a second run adds nothing and changes nothing", a2 == 0 and out2 == out, a2)
# 3 · a table-only page gets the structured form: a bare ^pN line after the table, a blank line each side; idempotent
T1 = "<table><tr><td>Premium revenues for the operating account</td><td>31.5</td><td>32.9</td></tr><tr><td>Benefits paid out over the year</td><td>24.9</td><td>29.1</td></tr></table>"
md3 = "%s\n\n| Premium revenues for the operating account | 31.5 | 32.9 |\n|---|---|---|\n| Benefits paid out over the year | 24.9 | 29.1 |\n\nAfter the table.\n" % P1
out3, a3, t3 = pa.anchor_markdown(md3, [block(0, P1), block(1, T1, "Table")])
case("a table-only page is anchored in the structured form (own line after the table, blank lines around) and no row is touched",
     a3 == 2 and t3 == 2 and "^p1" in out3 and "| 29.1 |\n\n^p2\n\nAfter the table." in out3 and "| ^p" not in out3, out3)
out3c, a3c, _ = pa.anchor_markdown(out3, [block(0, P1), block(1, T1, "Table")])
case("the structured form is idempotent (a bare ^pN line is seen as the page's anchor)", a3c == 0 and out3c == out3, (a3c, out3c[-60:]))
md3b = "| %s |\n|---|\n| 1 |\n" % P1
out3b, a3b, _ = pa.anchor_markdown(md3b, [block(0, P1)])
case("a hit that lands on a table row is skipped (the id would break the table)", a3b == 0 and "^p" not in out3b, out3b)
# 4 · a fenced line is never anchored
md4 = "```\n%s\n```\n\n%s\n" % (P1, P2)
out4, a4, _ = pa.anchor_markdown(md4, [block(0, P1), block(1, P2)])
case("a line inside a fence is never anchored; the page after the fence is", a4 == 1 and ("%s ^p1" % P1) not in out4 and out4.rstrip().endswith("^p2"), out4)
# 5 · a runaway fence does not swallow the book
filler = "\n".join("filler line %d of the runaway region" % i for i in range(pa.MAX_FENCE + 5))
md5 = "```\n%s\n%s\n\n%s\n" % (filler, P1, P2)
out5, a5, _ = pa.anchor_markdown(md5, [block(0, P1), block(1, P2)])
case("an unbalanced fence longer than MAX_FENCE lines is not a fence — both pages anchored", a5 == 2, (a5, out5[-160:]))
# 6 · a repeated running head does not drag the cursor (the nearest hit wins)
HEAD = "Royal Bank of Canada Third Quarter report to shareholders running head"
md6 = "%s\n\n%s\n\n%s\n\n%s\n" % (HEAD, P1, HEAD, P2)
out6, a6, _ = pa.anchor_markdown(md6, [block(0, HEAD), block(0, P1), block(1, HEAD), block(1, P2)])
case("a repeated running head does not drag the cursor past the page's real text (both pages anchored in order)",
     a6 == 2 and out6.index("^p1") < out6.index("^p2"), out6)
# 7 · CRLF kept
md7 = "%s\r\n\r\n%s\r\n" % (P1, P2)
out7, a7, _ = pa.anchor_markdown(md7, [block(0, P1), block(1, P2)])
case("CRLF markdown keeps its line endings and its anchors", a7 == 2 and "\r\n" in out7 and "\n\n" not in out7.replace("\r\n", ""), repr(out7[-40:]))
# 8 · a key too short is skipped, not mis-anchored
out8, a8, t8 = pa.anchor_markdown("short\n\n%s\n" % P2, [block(0, "short"), block(1, P2)])
case("a page whose only key is shorter than MIN_KEY is skipped (counted, not anchored)", a8 == 1 and t8 == 2, (a8, t8))
# 9 · a hit on a table row yields to the next-nearest hit on the same page
P4 = "Gross impaired loans were up from the prior quarter, primarily in the residential mortgages portfolio."
md9 = "| %s | 1 |\n|---|---|\n| x | 2 |\n\n%s\n" % (P1, P4)
out9, a9, _ = pa.anchor_markdown(md9, [block(0, P1), block(0, P4)])
case("a nearest hit on a table row yields to the next-nearest hit (the page is anchored on its paragraph)", a9 == 1 and out9.rstrip().endswith("%s ^p1" % P4) and "| ^p" not in out9, out9)
# 10 · a contents list quoting the next page's heading does not take that page's anchor
H2 = "Note 2 Significant accounting policies and estimates"
md10 = "Contents of the notes to the statements\n- Note 1 Basis of preparation and summary\n- %s\n\n## %s\n\n%s\n" % (H2, H2, P2)
out10, a10, _ = pa.anchor_markdown(md10, [block(0, "Contents of the notes to the statements"), block(1, H2, "SectionHeader"), block(1, P2)])
case("a contents list that quotes the next page's heading keeps its own id; the next page is anchored on its own text",
     a10 == 2 and "- %s ^p1" % H2 in out10 and out10.rstrip().endswith("^p2") and out10.count("^p") == 2, out10)
# 11 · a page whose first six blocks are short labels is anchored on the seventh
shorts = [block(0, "Total"), block(0, "Q3/26"), block(0, "n/a"), block(0, "(1)"), block(0, "Assets"), block(0, "Notes")]
out11, a11, _ = pa.anchor_markdown("Total\n\n%s\n" % P3, shorts + [block(0, P3)])
case("a page whose first six blocks are short is anchored on a later long block (all blocks searched)", a11 == 1 and out11.rstrip().endswith("^p1"), out11)
# 12 · a short key is accepted only when it is unique from the cursor on
md12 = "Impaired loans overview\n\n%s\n\nImpaired loans overview\n" % P2
out12a, a12a, _ = pa.anchor_markdown("Impaired loans overview\n\n%s\n" % P2, [block(0, "Impaired loans overview"), block(1, P2)])
out12b, a12b, _ = pa.anchor_markdown(md12, [block(0, "Impaired loans overview"), block(1, P2)])
case("a key between MIN_KEY_UNIQUE and MIN_KEY is accepted when unique and refused when it recurs",
     a12a == 2 and "Impaired loans overview ^p1" in out12a and a12b == 1 and "^p1" not in out12b, (a12a, a12b))
# 13 · a table whose header cells render in another order is found by a body row of its own (a markdown row is an html row)
T2 = ("<table><tr><td>2026</td><td>2025</td><td>Dollars in millions for the nine months ended July 31</td></tr>"
      "<tr><td>Canadian personal and business banking segment revenue</td><td>31.5</td><td>32.9</td></tr></table>")
md13 = "%s\n\n| Dollars in millions for the nine months ended July 31 | 2026 | 2025 |\n|---|---|---|\n| Canadian personal and business banking segment revenue | 31.5 | 32.9 |\n" % P1
out13, a13, _ = pa.anchor_markdown(md13, [block(0, P1), block(1, T2, "Table")])
case("a table whose header renders in another order is anchored by a body row (structured form after the table)",
     a13 == 2 and out13.rstrip().endswith("^p2") and "| 32.9 |\n\n^p2" in out13, out13)
# 14 · a list group (Marker's whole-list block) anchors on the list's last item, which Obsidian allows on a bullet
L1 = "<ul><li>For more, see the Business Outlook Survey of the second quarter and its methodology note</li><li>Second item</li></ul>"
md14 = "%s\n\n- For more, see the Business Outlook Survey of the second quarter and its methodology note\n- Second item\n" % P1
out14, a14, _ = pa.anchor_markdown(md14, [block(0, P1), block(1, L1, "ListGroup")])
case("a ListGroup page is anchored on the list's last item", a14 == 2 and out14.rstrip().endswith("- Second item ^p2"), out14)
# 15 · a table spanning two pages is one markdown block with one id (the first page's); the second page counts unanchored
TA = "<table><tr><td>Premium revenues for the operating account</td><td>31.5</td></tr></table>"
TB = "<table><tr><td>Benefits paid out over the year to claimants</td><td>24.9</td></tr></table>"
md15 = "%s\n\n| Premium revenues for the operating account | 31.5 |\n|---|---|\n| Benefits paid out over the year to claimants | 24.9 |\n" % P1
out15, a15, t15 = pa.anchor_markdown(md15, [block(0, P1), block(1, TA, "Table"), block(2, TB, "Table")])
case("a table spanning two pages carries one id — the first page's; the continuation page counts unanchored",
     a15 == 2 and t15 == 3 and out15.count("^p") == 2 and out15.rstrip().endswith("^p2") and "^p3" not in out15, out15)
print("==== page_anchors selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
