# -*- coding: utf-8 -*-
"""latex_structure_selftest.py — the tripwires of latex_structure.py (SYM-056, S168 E3): a balanced document is valid (the
positive control); the S109 specimen (`\\begin{array}{c*36}` with no close) reads unterminated 1 + runaway 1 and INVALID; a
strict-literal delta counts per environment (the MSG-CDX-0014 reading); an `\\end` that closes nothing is unopened; crossed
nesting is misordered though the counts balance (the counter alone would pass it — the walk catches it); a 36-`c` spec is
runaway and a 4-column one is not; the CLI exits 0 on a valid file and 1 on an invalid one; usage exits 2. NEGATIVE CONTROL:
the check run with MAX_SPEC_COLS raised past the specimen must NOT flag the runaway — the lever is what discriminates, and the
case shows the flag is the lever's, not a constant's. Exit 0 all fired · 1 any silent."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latex_structure as ls  # noqa: E402

N = FAILS = 0


def check(name, cond, detail=""):
    global N, FAILS
    N += 1
    if cond:
        print("  ok   " + name)
    else:
        FAILS += 1
        print("  BAD  " + name + (" — " + detail if detail else ""))


GOOD = "Text.\n\n$$\\begin{array}{cc} a & b \\\\ c & d \\end{array}$$\n\n\\begin{equation} x \\end{equation}\n\nMore.\n"
SPECIMEN = "para\n\n$$\\begin{array}{cccccccccccccccccccccccccccccccccccc} 1 & 2 \\\\ 3 & 4$$\n\nnext para\n"
r = ls.check(GOOD)
check("POSITIVE CONTROL: a balanced document with a 2-column array and an equation is valid", r["valid"] and r["begin"] == 2 and r["end"] == 2 and r["delta"] == {} and not r["runaway"], str(r))
r = ls.check(SPECIMEN)
check("SYM-056's specimen: begin{array} with 36 c's and no end reads unterminated 1, runaway 1, INVALID", (not r["valid"]) and r["delta"] == {"array": 1} and r["unterminated"] == 1 and len(r["runaway"]) == 1 and r["runaway"][0][1] == "array", str(r))
r = ls.check("\\begin{array}{c}\\begin{array}{c}\\end{array}\n\\begin{align}\\end{align}")
check("the strict-literal delta is per environment (array 2−1 = 1; align 1−1 = 0)", r["delta"] == {"array": 1} and r["begin"] == 3 and r["end"] == 2, str(r["delta"]))
r = ls.check("x \\end{array} y")
check("an end that closes nothing reads unopened 1 and misordered, INVALID", r["unopened"] == 1 and r["misordered"] and not r["valid"], str(r))
r = ls.check("\\begin{a}\\begin{b}\\end{a}\\end{b}")
check("crossed nesting: the counts balance (delta {}) but the walk names BOTH misorders — the counter alone would pass it", r["delta"] == {} and len(r["misordered"]) == 2 and not r["valid"], str(r["misordered"]))
r = ls.check("$$\\begin\r\n{array}{cc} 1 & 2 \\end{array}$$")
check("MSG-CDX-0014's split opener: `\\begin` + CRLF + `{array}` is COUNTED (begin 1, literal 0) so the pair balances — the strict-literal count kept beside it", r["begin"] == 1 and r["begin_literal"] == 0 and r["end"] == 1 and r["valid"], str(r))
r = ls.check("\\begin{tabular}{|l|c|c|r|} \\end{tabular}")
check("a 4-column spec with rules is not runaway (width 4)", r["valid"] and not r["runaway"], str(r))
r = ls.check("\\begin{array}{*{36}{c}} \\end{array}")
check("a `*{36}{c}` repeat spec reads width 36 and is runaway", len(r["runaway"]) == 1, str(r))
# NEGATIVE CONTROL — the lever
keep = ls.MAX_SPEC_COLS
ls.MAX_SPEC_COLS = 40
r = ls.check(SPECIMEN)
ls.MAX_SPEC_COLS = keep
check("NEGATIVE CONTROL: with MAX_SPEC_COLS raised to 40 the 36-c spec is NOT flagged (the flag is the lever's) — and the array is still unterminated", not r["runaway"] and r["unterminated"] == 1 and not r["valid"], str(r))
# the CLI
d = tempfile.mkdtemp(prefix="ls-")
good_p, bad_p = os.path.join(d, "good.md"), os.path.join(d, "bad.md")
open(good_p, "w", encoding="utf-8").write(GOOD)
open(bad_p, "w", encoding="utf-8").write(SPECIMEN)
here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latex_structure.py")
rg = subprocess.run([sys.executable, here, good_p], capture_output=True, text=True, encoding="utf-8")
rb = subprocess.run([sys.executable, here, good_p, bad_p], capture_output=True, text=True, encoding="utf-8")
ru = subprocess.run([sys.executable, here], capture_output=True, text=True, encoding="utf-8")
check("the CLI exits 0 on a valid file and prints `valid`", rg.returncode == 0 and "valid" in rg.stdout and "INVALID" not in rg.stdout, rg.stdout.strip()[-120:])
check("the CLI exits 1 when any file is INVALID and names it with its counts", rb.returncode == 1 and "bad.md: begin=1 (literal 1) end=0 delta={'array': 1} unterminated=1" in rb.stdout and "INVALID" in rb.stdout, rb.stdout.strip()[-160:])
check("no arguments: usage, exit 2", ru.returncode == 2 and "usage:" in ru.stdout)

print("latex_structure_selftest: %s" % ("GREEN (%d/%d)" % (N, N) if FAILS == 0 else "%d of %d FAILED" % (FAILS, N)))
sys.exit(1 if FAILS else 0)
