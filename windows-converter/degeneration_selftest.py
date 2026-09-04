"""Tripwires for SYM-067 / J29 — the table-aware degeneration gate (signed Rab 2026-09-04).

Run with the marker-env interpreter (fidelity_audit imports pymupdf and rapidfuzz at module
level):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe degeneration_selftest.py

NO GPU, no marker, no ollama, no real book, no PDF. Every body here is a synthetic string —
CPU only, safe to run beside a live conversion. Nothing writes anywhere.

Each tripwire names what breaks if it fires:
  D1  a real loop still trips          — POSITIVE CONTROL, with and without the gate; a gate
                                          that also silences the Beer class is not a gate
  D2  the sparse grid no longer trips  — DECOY: the same body MUST trip on the pre-J29 path
                                          (strip_table_rows=False). Asserting both proves the
                                          gate does work, not that the body was harmless
  D3  lines address the shipped body   — the loop after a blanked table reports the line its
                                          text is on, md_lines is unchanged, and the pre-J29
                                          path now reports the same line (the off-by-one on a
                                          leading newline is fixed on both paths)
  D4  the honest shape                 — `table_rows_stripped` is present and exact, 0 on a
                                          body with no tables; every pre-J29 key survives
  D5  the DECLARED blind spot          — a loop that emits ONLY table rows is invisible to the
                                          gate (the repeated-line check never counted | rows
                                          either, docs/15 §9.2). Asserted so a future change
                                          is deliberate, not accidental
  D6  glued prose still trips          — a loop paragraph with table rows glued to it (no blank
                                          line) keeps its prose and trips
  D7  the verdict path is untouched    — compute_verdict reads tripwires.degeneration and
                                          nothing else from this block
  D8  CRLF rows are rows               — the count and the verdict do not depend on the line
                                          terminator; md_lines is identical to the LF body
  D9  fences are NOT parsed            — a pipe row inside ``` is blanked too (line-shaped rule,
                                          the same declared choice as latex_balance L8)
  D10 a lone pipe is not a row         — "a | b" and "|x" are prose; only |…| rows are blanked
  D11 an interleaved loop still trips  — FLEET LANE B (wf_1e69e60b-b45): a loop whose lines vary
                                          per repetition and are interleaved one-to-one with pipe
                                          rows must trip. Blanking a row to an EMPTY line split it
                                          into sub-200-char fragments (flagged False, 0 blocks);
                                          blanking to a whitespace line keeps one paragraph
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import fidelity_audit as fa  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


LOOP = ("the stage of " * 300).strip()                       # Beer-class: zlib low, trigram 298
SPARSE = "| Item | Value | Note |\n|---|---|---|\n" + "\n".join("| | | |" for _ in range(60))
PROSE = ("Discount the expected cash flows at the cost of capital and compare the present value "
         "with the market price; the difference is the margin of safety the analyst reports.")

# ---------- D1: positive control ----------
print("D1 a real loop still trips (positive control)")
r_new = fa.degeneration(LOOP)
r_old = fa.degeneration(LOOP, strip_table_rows=False)
check(r_new["flagged"] and r_old["flagged"], "the Beer-class loop trips with AND without the gate")
check(r_new["worst"][0]["max_trigram"] >= fa.DEGEN_TRIGRAM_MAX
      and r_new["worst"][0]["zlib"] < fa.DEGEN_ZLIB_MAX, "…on both halves of the AND (trigram and zlib)")
check(r_new["table_rows_stripped"] == 0, "…and a body with no tables strips 0 rows")

# ---------- D2: the decoy ----------
print("D2 the sparse grid no longer trips — and DID trip on the old path")
s_new = fa.degeneration(SPARSE)
s_old = fa.degeneration(SPARSE, strip_table_rows=False)
check(s_old["flagged"] and s_old["blocks_total"] == 1,
      "DECOY: the empty-cell grid trips the pre-J29 path (zlib crushed + '| | |' trigram)")
check(not s_new["flagged"] and s_new["blocks_total"] == 0,
      "the same grid does NOT trip the gate (0 blocks)")
check(s_new["table_rows_stripped"] == 62, "…and reports exactly 62 rows blanked (header + separator + 60)")

# ---------- D3: lines address the shipped body ----------
print("D3 lines address the shipped body")
BODY = PROSE + "\n\n" + SPARSE + "\n\n" + PROSE + "\n" + SPARSE + "\n\n\n" + LOOP + "\n"
expected_line = BODY.index(LOOP[:20])
expected_line = BODY.count("\n", 0, expected_line) + 1
b_new = fa.degeneration(BODY)
b_old = fa.degeneration(BODY, strip_table_rows=False)
check(b_new["flagged"] and b_new["blocks_total"] == 1, "one block trips: the loop, not the grids")
check(b_new["worst"][0]["line"] == expected_line,
      f"the loop reports the line its text starts on ({expected_line})")
check(b_old["worst"] and b_old["worst"][-1]["line"] == expected_line or
      any(w["line"] == expected_line for w in b_old["worst"]),
      "the pre-J29 path reports the same line for the loop (leading-newline fix on both paths)")
check(b_new["md_lines"] == b_old["md_lines"] == BODY.count("\n") + 1,
      "md_lines is the shipped body's line count on both paths")

# ---------- D4: the honest shape ----------
print("D4 the honest shape")
KEYS = {"flagged", "repeated_lines", "md_lines", "worst", "blocks_total", "worst_capped_at",
        "table_rows_stripped"}
check(set(r_new) == KEYS, "every pre-J29 key survives and table_rows_stripped is added")
check(r_new["worst_capped_at"] == 10 and isinstance(r_new["table_rows_stripped"], int),
      "the caps are unchanged and the count is an int, never null")

# ---------- D5: the declared blind spot ----------
print("D5 the DECLARED blind spot: a loop that emits only table rows")
ROWLOOP = "\n".join("| the stage of the stage of the stage of the stage |" for _ in range(80))
rl_new = fa.degeneration(ROWLOOP)
rl_old = fa.degeneration(ROWLOOP, strip_table_rows=False)
check(rl_old["flagged"], "the pre-J29 path saw it (trigram over the pipes)")
check(not rl_new["flagged"] and rl_new["table_rows_stripped"] == 80,
      "DECLARED: the gate blanks it and does not trip — a row-only loop is residue, not a catch")

# ---------- D6: glued prose still trips ----------
print("D6 glued prose still trips")
GLUED = LOOP + "\n" + "\n".join("| | |" for _ in range(30))
g = fa.degeneration(GLUED)
check(g["flagged"] and g["blocks_total"] == 1 and g["worst"][0]["line"] == 1,
      "the prose half of a glued paragraph trips at line 1")

# ---------- D7: the verdict path is untouched ----------
print("D7 the verdict path is untouched")
clean = {"kind": "fidelity", "doc_survival": 1.0, "pages_flagged": [], "runs": [],
         "tripwires": {"degeneration": False}}
bad = dict(clean, tripwires={"degeneration": True})
check(fa.compute_verdict(clean, None) == "pass" and fa.compute_verdict(bad, None) == "fail",
      "degeneration True → fail, False → pass, nothing else read from the block")
src = Path(fa.__file__).read_text(encoding="utf-8")
cv = src[src.index("def compute_verdict"):src.index("def build_fidelity_block")]
check("table_rows_stripped" not in cv, "compute_verdict's source cannot even name the new key")

# ---------- D8: CRLF rows are rows ----------
print("D8 CRLF rows are rows")
CR = BODY.replace("\n", "\r\n")
c = fa.degeneration(CR)
check(c["table_rows_stripped"] == b_new["table_rows_stripped"], "the same rows are blanked under CRLF")
check(c["flagged"] and c["blocks_total"] == 1 and c["md_lines"] == b_new["md_lines"],
      "…same verdict, same block count, same md_lines")

# ---------- D9: fences are NOT parsed ----------
print("D9 fences are NOT parsed (line-shaped rule, declared)")
FENCED = "```\n| a | b |\n| c | d |\n```\n" + PROSE
f = fa.degeneration(FENCED)
check(f["table_rows_stripped"] == 2, "two pipe rows inside a fence are blanked (declared)")

# ---------- D10: a lone pipe is not a row ----------
print("D10 a lone pipe is not a row")
LONE = "either a | b holds\n|x starts with a pipe\nthe norm \\left| v \\right| is prose\n" + PROSE
lo = fa.degeneration(LONE)
check(lo["table_rows_stripped"] == 0, "'a | b', '|x' and '\\left| v \\right|' are prose, 0 rows")
check(fa._blank_table_rows("  | a |  \n")[1] == 1, "leading/trailing spaces around a row still count it")

# ---------- D11: an interleaved, per-line-varying loop still trips (fleet lane B) ----------
print("D11 a per-line-varying loop interleaved with table rows still trips")
INTER = "\n".join(f"the stage of the stage of the stage {i}\n| x | y |" for i in range(120)) + "\n"
it_new = fa.degeneration(INTER)
it_old = fa.degeneration(INTER, strip_table_rows=False)
check(it_new["flagged"] and it_new["blocks_total"] == 1 and it_new["worst"][0]["line"] == 1,
      "the gate keeps the 120 prose lines in ONE paragraph and trips it at line 1")
check(it_old["flagged"], "…and the pre-J29 path saw it too (no regression either way)")
check(it_new["table_rows_stripped"] == 120, "…with all 120 rows counted as blanked")
# the mechanism the fleet broke, made falsifiable: an EMPTY-line blanking fragments the loop
frag = fa.degeneration(INTER.replace("| x | y |", ""))
check(not frag["flagged"], "DECOY: the same body with rows replaced by EMPTY lines does NOT trip — the fragmentation lane B found")

# ---------- verdict ----------
n_checks = len(re.findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"), re.M))
total = len(FAILURES)
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
if FAILURES:
    print("Failed:")
    for f_ in FAILURES:
        print(f"  - {f_}")
sys.exit(1 if FAILURES else 0)
