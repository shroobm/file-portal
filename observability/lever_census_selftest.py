#!/usr/bin/env python3
"""Tripwires for observability/lever_census.py (SYM-096; S184). Hermetic: strings and a throwaway git repo in a temp dir;
never the shared checkout. Every case violates the property its guard stands for, and case (h) is the POSITIVE CONTROL
that the regex gate's own class is NOT this census's (a `NAME = 0.42` line is the gate's, not a blind-class literal).

  (a) the four classes each listed once from one source        (b) 0 / 1 / -1 / 2 never listed
  (c) a waived line (`# lever-waiver: <who/what>`) skipped     (c') a BARE waiver (no substance) is NOT a waiver
  (d) a negated literal keeps its sign                          (e) a syntax error reads as no findings, never a crash
  (f) `lines` restricts to the added lines                      (g) the diff mode reads only ADDED lines from a real repo
  (h) NEGATIVE CONTROL: `NAME = 0.42` alone yields nothing here (the regex gate's class)
  (i) a selftest path is exempt in the diff mode (POLICY law 2)

WHAT THIS FILE DOES: a script-style selftest for observability/lever_census.py (imported as `lc`). It feeds source
strings to lc.census_source() and builds a throwaway git repo in a temp directory to test lc.census_since(). It
prints one ok/BAD line per case, removes the temp repo, and exits 1 if any case failed, else 0. Run directly.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lever_census as lc  # noqa: E402

# -- setup: make lever_census importable; lists of failed and executed case names --
failed: list[str] = []
ran: list[str] = []


def case(name, cond, detail=""):
    """Record and print one case: ok if `cond` is true, else BAD with `detail`; failures are added to `failed`."""
    ran.append(name)
    print(("  ok   " if cond else "  BAD  ") + name + ("" if cond else f": {detail}"))
    if not cond:
        failed.append(name)


# -- string-source cases (a), (b), (d), (h): SRC is DATA parsed by the census, one literal per blind class --
SRC = '''import math
LIMIT = 0.42
def f(x, floor=0.8, n=3):
    if x < 0.995 and n > 2:
        return {"cap": 25, "one": 1}
    return (0.5, 0.9), [7, -3]
'''
rows = lc.census_source(SRC)
by = {}
for r in rows:
    by.setdefault(r["cls"], []).append(r["value"])
case("(a) the four classes each listed from one source (compare 0.995, default 0.8 + 3, dict 25, sequence 0.5/0.9/7/-3)",
     by.get("compare") == [0.995] and sorted(by.get("default", [])) == [0.8, 3] and by.get("dict") == [25]
     and sorted(by.get("sequence", [])) == [-3, 0.5, 0.9, 7], by)
case("(b) 0 / 1 / -1 / 2 are never listed (`n > 2`, `'one': 1`)", all(r["value"] not in (0, 1, -1, 2) for r in rows), rows)
case("(h) NEGATIVE CONTROL: `LIMIT = 0.42` — the regex gate's own class — is NOT in this census",
     all(r["value"] != 0.42 for r in rows), rows)
case("(d) a negated literal keeps its sign (-3 in the list)", any(r["value"] == -3 for r in rows), rows)

# the fixtures are WHOLE statements: the first draft's bodiless `if` was a SyntaxError and (c) passed vacuously — (c') caught it
WAIVED = "if x < 0.7:  # lever-waiver: Rab only; moves on a measured corpus\n    pass\n"
BARE = "if x < 0.7:  # lever-waiver:\n    pass\n"
case("(c0) the waiver fixtures parse (a bodiless `if` would make (c) vacuous)", lc.census_source("if x < 0.7:\n    pass\n") != [])
case("(c) a waived line with substance after the colon is skipped", lc.census_source(WAIVED) == [], lc.census_source(WAIVED))
case("(c') a BARE `# lever-waiver:` is not a waiver — the line is listed", len(lc.census_source(BARE)) == 1, lc.census_source(BARE))
case("(e) a syntax error reads as no findings, never a crash", lc.census_source("def (:\n") == [])
case("(f) `lines` restricts to the given line numbers", [r["line"] for r in lc.census_source(SRC, lines={4})] == [4],
     lc.census_source(SRC, lines={4}))

# (g)+(i): a throwaway repo — a committed file, then lines ADDED, then the diff census
tmp = Path(tempfile.mkdtemp(prefix="fp-lever-census-"))
try:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def g(*args):
        """Run `git -C <temp repo> <args>` with a fixed identity; raises on a non-zero exit; returns the result."""
        return subprocess.run(["git", "-C", str(tmp), *args], capture_output=True, text=True, env=env, check=True)

    # build the repo: a base commit, then a second commit that adds literals and a selftest file (which must be exempt)
    g("init", "-q")
    (tmp / "windows-converter").mkdir()
    mod = tmp / "windows-converter" / "mod.py"
    mod.write_text("def f(x):\n    return x\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-q", "-m", "base")
    base = g("rev-parse", "HEAD").stdout.strip()
    mod.write_text("def f(x, floor=0.8):\n    if x < 0.995:\n        return x\n    return x\n", encoding="utf-8")
    st = tmp / "windows-converter" / "mod_selftest.py"
    st.write_text("assert 1 < 0.995\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-q", "-m", "added")
    since = lc.census_since(base, tmp)
    vals = sorted(r["value"] for r in since)
    case("(g) the diff mode lists the ADDED lines' literals from a real repo (0.8 default, 0.995 compare) and nothing older",
         vals == [0.8, 0.995] and all(r["path"] == "windows-converter/mod.py" for r in since), since)
    case("(i) a selftest path is exempt in the diff mode (POLICY law 2)", all("selftest" not in r["path"] for r in since), since)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if failed:
    print(f"TRIPWIRES DISARMED — {len(failed)} failed of {len(ran)}: {failed}")
    raise SystemExit(1)
print(f"ALL TRIPWIRES FIRED — {len(ran)}/{len(ran)}")
