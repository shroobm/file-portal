# -*- coding: utf-8 -*-
"""page_anchors_selftest.py — the anchors' tripwires (S209 E6). Hermetic: no files, no pipeline. Each case violates the
property its rule stands for: a page anchored on its first paragraph; a second run adds nothing (idempotent); a table-only
page gets no anchor (the id would break the table); a line inside a fence is never anchored; a runaway fence (> MAX_FENCE
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
# 3 · a table-only page gets no anchor
md3 = "%s\n\n| a | b |\n|---|---|\n| 1 | 2 |\n" % P1
out3, a3, t3 = pa.anchor_markdown(md3, [block(0, P1), block(1, "| a | b |", "Table")])
case("a table-only page is not anchored (Table is not a text type) and the paragraph page is", a3 == 1 and t3 == 1 and "^p1" in out3 and "| 1 | 2 | ^p" not in out3, out3)
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
print("==== page_anchors selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
