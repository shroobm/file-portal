#!/usr/bin/env python3
"""observability/label_corrections_check.py [<register.md>] [--repo <dir>] [--selftest] — the guard rail on the label
corrections register (S218 E8 wave 4; Rab's word of 2026-10-03 20:53:49Z: "guard rails so that you know that it was changed
and what it was changed from and to in future sessions"). For every `### C-nnn · <path> · …` row of the register, read the
file from the repo and require: every `NEW: ` line present in the file as a whole line (whitespace-stripped), and no
`OLD: ` line still present; a row whose NEW is the single word `DELETED` requires only the OLD lines absent. Prints one
line per row and a summary; exit 0 every row holds · 1 at least one row does not (or a file is missing) · 2 usage.
`--selftest` writes a temporary file and register with a true row, a false row (the old line still there) and a
deleted row, and requires the check to pass the true register and refuse the false one. Reads only (the selftest writes
under a temporary directory it removes).
"""

from __future__ import annotations

import io
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTER = os.path.join(HERE, "label_corrections.md")
HEADING = re.compile(
    r"^### (C-[A-Z]*\d+) · (\S+) · (.*)$"
)  # C-001 public rows; C-P01 the private register's


def parse(text: str) -> list[dict]:
    """The register's rows: {id, path, old: [..], new: [..]} in file order; text outside a row is ignored."""
    rows: list[dict] = []
    cur = None
    for ln in text.splitlines():
        m = HEADING.match(ln.strip())
        if m:
            cur = {"id": m.group(1), "path": m.group(2), "old": [], "new": []}
            rows.append(cur)
            continue
        if cur is None:
            continue
        if ln.startswith("OLD: "):
            cur["old"].append(ln[5:].strip())
        elif ln.startswith("NEW: "):
            cur["new"].append(ln[5:].strip())
    return rows


def check(rows: list[dict], repo: str, quiet: bool = False) -> int:
    """Check every row against the files under repo; print one line per row; return the number of bad rows."""
    bad = 0
    for r in rows:
        p = os.path.join(repo, r["path"])
        if not os.path.isfile(p):
            if not quiet:
                print("BAD %s %s | file missing" % (r["id"], r["path"]))
            bad += 1
            continue
        lines = [
            ln.strip()
            for ln in io.open(p, encoding="utf-8", errors="replace").read().splitlines()
        ]
        deleted = r["new"] == ["DELETED"]
        old_left = [o for o in r["old"] if o in lines]
        new_missing = [] if deleted else [n for n in r["new"] if n not in lines]
        ok = not old_left and not new_missing and (deleted or r["new"]) and r["old"]
        if not quiet:
            print(
                "%s %s %s | old lines still present: %d | new lines missing: %d%s"
                % (
                    "ok " if ok else "BAD",
                    r["id"],
                    r["path"],
                    len(old_left),
                    len(new_missing),
                    ""
                    if (r["old"] and (deleted or r["new"]))
                    else " | malformed row (no OLD or no NEW)",
                )
            )
        if not ok:
            bad += 1
    if not quiet:
        print("register: %d row(s), %d bad" % (len(rows), bad))
    return bad


def selftest() -> int:
    """A true row, a false row and a deleted row against a temporary file; the check must pass the first and refuse the second."""
    d = tempfile.mkdtemp(prefix="label_corr_")
    try:
        os.makedirs(os.path.join(d, "pkg"))
        io.open(os.path.join(d, "pkg", "m.py"), "w", encoding="utf-8").write(
            "# new comment\nx = 1\n# still here\n"
        )
        true_reg = (
            "### C-001 · pkg/m.py · test · abc\nOLD: # old comment\nNEW: # new comment\nPROOF: x\nWHY: y\n"
            "### C-002 · pkg/m.py · test · abc\nOLD: # gone comment\nNEW: DELETED\nPROOF: x\nWHY: y\n"
        )
        false_reg = "### C-003 · pkg/m.py · test · abc\nOLD: # still here\nNEW: # replaced it\nPROOF: x\nWHY: y\n"
        missing_reg = "### C-004 · pkg/none.py · test · abc\nOLD: # a\nNEW: # b\n"
        private_reg = "### C-P01 · pkg/m.py · test · abc\nOLD: # old comment\nNEW: # new comment\nPROOF: x\nWHY: y\n"
        results = [
            ("the true register passes", check(parse(true_reg), d, quiet=True) == 0),
            (
                "the false register (old line still present, new line absent) is refused",
                check(parse(false_reg), d, quiet=True) == 1,
            ),
            (
                "a missing file is refused",
                check(parse(missing_reg), d, quiet=True) == 1,
            ),
            (
                "a row with no NEW is malformed and refused",
                check(
                    parse("### C-005 · pkg/m.py · t · a\nOLD: # old comment\n"),
                    d,
                    quiet=True,
                )
                == 1,
            ),
            (
                "the shipped register parses to at least one row",
                len(parse(io.open(DEFAULT_REGISTER, encoding="utf-8").read())) >= 1,
            ),
            (
                "a private-register id (C-P01) parses and passes",
                len(parse(private_reg)) == 1
                and check(parse(private_reg), d, quiet=True) == 0,
            ),
        ]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    n_ok = 0
    for name, ok in results:
        print("  %s  %s" % ("ok  " if ok else "FAIL", name))
        n_ok += ok
    print("label_corrections_check selftest: %d/%d" % (n_ok, len(results)))
    return 0 if n_ok == len(results) else 1


def main(argv: list[str]) -> int:
    """Parse the arguments, run the selftest or the check, return the exit code."""
    if "--selftest" in argv:
        return selftest()
    repo = argv[argv.index("--repo") + 1] if "--repo" in argv else os.path.dirname(HERE)
    reg = next((a for a in argv if a.endswith(".md")), DEFAULT_REGISTER)
    if not os.path.isfile(reg):
        print(
            "usage: label_corrections_check.py [<register.md>] [--repo <dir>] [--selftest]  (register not found: %s)"
            % reg
        )
        return 2
    rows = parse(io.open(reg, encoding="utf-8").read())
    return 1 if check(rows, repo) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
