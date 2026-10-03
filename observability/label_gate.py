#!/usr/bin/env python3
"""observability/label_gate.py — the gate under a comment-only edit (S218 E8, Rab's word on the Desk, 2026-10-03: a swarm
labels the code "but the comments must not break the code"). A labelling lane may add comments, docstrings and blank
lines and NOTHING else. This gate makes that mechanical for Python:

  * the syntax tree with every docstring removed must be IDENTICAL before and after (a comment never reaches the tree;
    a docstring is the first statement of a module/class/function body and is stripped before the compare — so adding or
    rewording one passes, and any other change, one token, fails);
  * both sides must compile (py_compile), so a comment that swallowed a line or broke a string is caught by the compiler
    as well as by the tree;
  * the line count may only grow (a labelling lane deletes nothing).

    python observability/label_gate.py <path> [--base <git ref>]     # compares the working file with <ref>:<path> (default HEAD)
    python observability/label_gate.py <path> --against <other file>  # compares two files on disk
    python observability/label_gate.py --selftest                     # the gate against planted edits (docs/32 §5)

Exit 0 the edit is comment/docstring-only · 1 something else changed (the first differing node is named) · 2 usage or
unreadable · 3 a side does not parse. Read-only; stdlib; CRLF-safe (the tree does not see line endings).
"""
from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
import tempfile


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _skeleton(src: str) -> str:
    return ast.dump(_strip_docstrings(ast.parse(src)), include_attributes=False)


def _compiles(src: str, name: str) -> str | None:
    try:
        compile(src, name, "exec")
        return None
    except SyntaxError as e:
        return "%s: %s (line %s)" % (name, e.msg, e.lineno)


def _first_diff(a: str, b: str) -> str:
    i = 0
    n = min(len(a), len(b))
    while i < n and a[i] == b[i]:
        i += 1
    lo = max(0, i - 60)
    return "…%s… | …%s…" % (a[lo:i + 60], b[lo:i + 60])


def gate(before: str, after: str, name: str = "<file>") -> tuple[int, str]:
    """(exit code, one line). 0 = comment/docstring-only."""
    for side, src in (("before", before), ("after", after)):
        err = _compiles(src, "%s(%s)" % (name, side))
        if err:
            return 3, "DOES NOT COMPILE %s" % err
    if after.count("\n") < before.count("\n"):
        return 1, "LINES SHRANK %d -> %d (a labelling edit deletes nothing)" % (before.count("\n") + 1, after.count("\n") + 1)
    sa, sb = _skeleton(before), _skeleton(after)
    if sa != sb:
        return 1, "TREE CHANGED beyond comments/docstrings at: %s" % _first_diff(sa, sb)
    return 0, "OK comment/docstring-only (%d -> %d lines)" % (before.count("\n") + 1, after.count("\n") + 1)


def _read(p: str) -> str:
    return io.open(p, encoding="utf-8", errors="replace").read()


def _git_show(ref: str, path: str) -> str | None:
    repo = os.path.dirname(os.path.abspath(path))
    rel = os.path.basename(path)
    # walk up to the repo root so the path is repo-relative
    top = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        return None
    root = top.stdout.strip()
    rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    r = subprocess.run(["git", "-C", root, "show", "%s:%s" % (ref, rel)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def selftest() -> int:
    base = "import os\n\n\ndef f(x):\n    y = x + 1\n    return y\n\n\nclass C:\n    def m(self):\n        return 1\n"
    cases = [
        ("a comment line added", base.replace("    y = x + 1\n", "    # add one\n    y = x + 1\n"), 0),
        ("a docstring added to f", base.replace("def f(x):\n", "def f(x):\n    \"\"\"Add one.\"\"\"\n"), 0),
        ("a module docstring added", "\"\"\"The module.\"\"\"\n" + base, 0),
        ("a class docstring and a method docstring added", base.replace("class C:\n", "class C:\n    \"\"\"C.\"\"\"\n").replace("    def m(self):\n", "    def m(self):\n        \"\"\"One.\"\"\"\n"), 0),
        ("a section banner comment", base.replace("\n\nclass C:", "\n\n# ── the class ──\nclass C:"), 0),
        ("unchanged", base, 0),
        ("MUTANT a statement added", base.replace("    y = x + 1\n", "    y = x + 1\n    y += 1\n"), 1),
        ("MUTANT a constant changed", base.replace("x + 1", "x + 2"), 1),
        ("MUTANT a name changed", base.replace("def f(x)", "def f(z)"), 1),
        ("MUTANT a line deleted", base.replace("    y = x + 1\n    return y\n", "    return x + 1\n"), 1),
        ("MUTANT a comment that swallowed a line", base.replace("    y = x + 1\n", "    # y = x + 1\n"), 1),
        ("MUTANT a broken docstring", base.replace("def f(x):\n", "def f(x):\n    \"\"\"Add one.\n"), 3),
        ("MUTANT an import added", base.replace("import os\n", "import os\nimport sys\n"), 1),
        ("MUTANT a return value changed", base.replace("return 1", "return 2"), 1),
    ]
    bad = 0
    for name, after, want in cases:
        code, msg = gate(base, after, "selftest")
        ok = code == want
        bad += not ok
        print("%s %s -> %d (want %d) %s" % ("PASS" if ok else "FAIL", name, code, want, msg[:90]))
    print("════ label_gate selftest: %d/%d ════" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    after = _read(path)
    if "--against" in argv:
        before = _read(argv[argv.index("--against") + 1])
    else:
        ref = argv[argv.index("--base") + 1] if "--base" in argv else "HEAD"
        before = _git_show(ref, path)
        if before is None:
            print("UNREAD: %s not in %s (a new file has no base to compare)" % (path, ref))
            return 2
    code, msg = gate(before, after, os.path.basename(path))
    print("%s %s" % (path, msg))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
