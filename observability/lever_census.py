#!/usr/bin/env python3
"""observability/lever_census.py -- the LEVERS gate's blind classes, listed WARN-ONLY (SYM-096; S184).

close.sh [5] LEVERS is regex-shaped: it sees `NAME = 0.42` (and the Rust/JS declaration forms) in the lines ADDED
since the pin and reports the ones with no lever and no waiver. It cannot see a number written any other way, and
docs/18 §2's law ("a number that decides something is a LEVER, not a constant") does not care how the number is
written. SYM-096 declared the classes the regex cannot see -- a dict literal's value, a call's parameter default, a
tuple element -- and this census walks them by the Python AST:

  compare   a numeric literal as an operand of a comparison       `if survival < 0.995:`
  default   a numeric literal as a function parameter's default   `def f(x, floor=0.8):`
  dict      a numeric literal as a dict literal's value            `{"cap": 25}`
  sequence  a numeric literal inside a tuple/list/set literal      `LIMITS = (0.5, 0.8)`

Only the ADDED lines of the diff since `--since <ref>` are read (the regex gate's own scope), only `*.py`, and a
line carrying `lever-waiver:` with substance after the colon is skipped (the gate's own waiver form). 0, 1, -1 and 2
are not counted (an index, a boolean, a pair, a half -- never a threshold). It PRINTS and never blocks: the S108
standard -- a listing, warn-only; arming is Rab's. It never imports converter code and never opens the live pipeline.

    python observability/lever_census.py --since <ref>      # the listing, exit 0 always
    python observability/lever_census.py --since <ref> --count   # one line: the count

Limits, said: a number reached through a NAME (`floor = 0.8; if x < floor`) is the regex gate's class, not this one's;
a comparison against a call (`< len(x)`) carries no literal and is not listed; a literal in a comprehension's
condition is a `compare` like any other; a literal inside an f-string is text and invisible to both.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_VALUES = {0, 1, -1, 2}
WAIVER = re.compile(r"lever-waiver:\s*\S")
CLASSES = ("compare", "default", "dict", "sequence")
# POLICY law 2: a selftest's expected values are assertions, not levers (`assert x == 0.5`); this census names the
# exemption explicitly and, in --all mode, prints how many files it skipped
EXEMPT = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_selftest\.py|selftest\.py)$")
TREE_ROOTS = ("windows-converter", "observability", "linux-converter", "linux-receiver", "linux-dashboard", "prototypes")


def added_lines(ref: str, root: Path = ROOT) -> dict[str, set[int]]:
    """{path: {line numbers ADDED since ref}} for *.py, read from `git diff -U0`'s hunk headers."""
    out = subprocess.run(["git", "-C", str(root), "diff", "-U0", f"{ref}..HEAD", "--", "*.py"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise RuntimeError(f"git diff failed: {out.stderr.strip()[:200]}")
    added: dict[str, set[int]] = {}
    path = None
    for line in out.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            added.setdefault(path, set())
        elif line.startswith("@@") and path is not None:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or 1)
                added[path].update(range(start, start + count))
    return {p: ls for p, ls in added.items() if ls}


def _num(node: ast.AST):
    """The numeric value of a literal (or a negated literal), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _num(node.operand)
        return -v if v is not None else None
    return None


def census_source(text: str, lines: set[int] | None = None) -> list[dict]:
    """The findings in one Python source: [{cls, line, value, text}] -- restricted to `lines` when given."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    src = text.splitlines()
    found: list[dict] = []

    def keep(node: ast.AST, cls: str, value) -> None:
        ln = getattr(node, "lineno", None)
        if ln is None or (lines is not None and ln not in lines) or value in SKIP_VALUES:
            return
        line_text = src[ln - 1] if ln - 1 < len(src) else ""
        if WAIVER.search(line_text):
            return
        found.append({"cls": cls, "line": ln, "value": value, "text": line_text.strip()[:100]})

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for operand in [node.left, *node.comparators]:
                v = _num(operand)
                if v is not None:
                    keep(operand, "compare", v)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            for d in [*args.defaults, *args.kw_defaults]:
                if d is None:
                    continue
                v = _num(d)
                if v is not None:
                    keep(d, "default", v)
        elif isinstance(node, ast.Dict):
            for val in node.values:
                v = _num(val) if val is not None else None
                if v is not None:
                    keep(val, "dict", v)
        elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for elt in node.elts:
                v = _num(elt)
                if v is not None:
                    keep(elt, "sequence", v)
    # one finding per (line, value, cls) -- a literal can sit in a tuple inside a compare
    seen, uniq = set(), []
    for f in found:
        k = (f["line"], f["value"], f["cls"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return sorted(uniq, key=lambda f: (f["line"], f["cls"]))


def census_since(ref: str, root: Path = ROOT) -> list[dict]:
    rows: list[dict] = []
    for path, lines in added_lines(ref, root).items():
        p = root / path
        if not p.exists() or EXEMPT.search(path.replace("\\", "/")):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for f in census_source(text, lines):
            rows.append({"path": path, **f})
    return rows


def census_all(root: Path = ROOT) -> tuple[list[dict], int]:
    """Every tracked *.py under the pipeline's roots, whole files (the historical measure, not the gate's scope);
    returns (rows, exempt_count)."""
    out = subprocess.run(["git", "-C", str(root), "ls-files", "--", *[f"{r}/*.py" for r in TREE_ROOTS]],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    rows, exempt = [], 0
    for path in out.stdout.splitlines():
        if EXEMPT.search(path):
            exempt += 1
            continue
        try:
            text = (root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for f in census_source(text):
            rows.append({"path": path, **f})
    return rows, exempt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--since", default="HEAD", help="the pin; only lines ADDED since it are read")
    ap.add_argument("--count", action="store_true", help="print one line: the count")
    ap.add_argument("--all", action="store_true", help="the whole tracked tree, not the diff (the historical measure)")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    if a.all:
        rows, exempt = census_all(Path(a.root))
        by = {c: sum(1 for r in rows if r["cls"] == c) for c in CLASSES}
        print(f"lever census (AST, whole tree): {len(rows)} numeric literal(s) in the regex gate's blind classes — "
              f"{' · '.join(f'{c} {n}' for c, n in by.items())} · selftests exempt: {exempt} file(s)")
        if not a.count:
            for r in rows:
                print(f"  {r['cls']:8s} {r['path']}:{r['line']}  {r['value']!r}  {r['text']}")
        return 0
    try:
        rows = census_since(a.since, Path(a.root))
    except RuntimeError as e:
        print(f"lever census UNREAD — {e}")
        return 0
    if a.count:
        print(f"lever census (AST, warn-only): {len(rows)} numeric literal(s) in the regex gate's blind classes since {a.since}")
        return 0
    if not rows:
        print(f"lever census (AST, warn-only): no numeric literal in a compare/default/dict/sequence position added since {a.since}")
        return 0
    print(f"lever census (AST, warn-only): {len(rows)} numeric literal(s) in the regex gate's blind classes since {a.since} — "
          f"docs/18 §2: a number that decides something is a lever; name it or waive it in-line")
    for r in rows:
        print(f"  {r['cls']:8s} {r['path']}:{r['line']}  {r['value']!r}  {r['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
