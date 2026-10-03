#!/usr/bin/env python3
"""observability/label_gate.py — the gate under a comment-only edit (S218 E8, Rab's word on the Desk, 2026-10-03: a swarm
labels the code "but the comments must not break the code"). A labelling lane may add comments, docstrings and blank
lines and NOTHING else. This gate makes that mechanical for Python:

  * the syntax tree with every docstring removed must be IDENTICAL before and after (a comment never reaches the tree;
    a docstring is the first statement of a module/class/function body and is stripped before the compare — so adding or
    rewording one passes, and any other change, one token, fails);
  * both sides must compile (py_compile), so a comment that swallowed a line or broke a string is caught by the compiler
    as well as by the tree;
  * the line count may only grow (a labelling lane deletes nothing);
  * every CODE LINE must be verbatim and in order (added S218 E8 after wave 1: docstring lines and comment-only lines
    aside, trailing comments cut — whitespace inside a code line counts, and a comment dropped into a data string is a
    changed code line); a tree is whitespace-blind, and 55 glued `name =value` lines passed the first three checks.

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
import tokenize


def _docstring_lines(tree: ast.AST) -> set[int]:
    """Line numbers covered by module/class/function docstrings (the only text a lane may rewrite)."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.update(range(body[0].lineno, body[0].end_lineno + 1))
    return out


def _code_lines(src: str) -> list[str]:
    """The file's CODE lines, verbatim and in order: every physical line that is not blank, not comment-only and not inside a
    docstring, with its trailing comment cut off and the right side stripped. Two files with equal code lines differ only in
    comments, docstrings and blank lines — whitespace INSIDE a code line counts (wave 1 glued `name =value` on 43 lines and the
    tree could not see it), and a comment dropped into a data string is a changed code line too."""
    lines = src.splitlines()
    doc = _docstring_lines(ast.parse(src))
    comment_at: dict[int, int] = {}
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == tokenize.COMMENT:
                comment_at[t.start[0]] = t.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    out = []
    for i, line in enumerate(lines, 1):
        if i in doc:
            continue
        if i in comment_at:
            line = line[:comment_at[i]]
        if not line.strip():
            continue
        out.append(line.rstrip())
    return out


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                # a module may be empty once its docstring is gone (an `__init__.py` that gained one); a def/class
                # body may not, so the placeholder keeps both sides comparable (a docstring-only def strips to `pass`)
                node.body = body[1:] if isinstance(node, ast.Module) else (body[1:] or [ast.Pass()])
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
    # (the no-shrink rule of wave 1 is gone since Rab's word of 2026-10-03 20:39Z - "anything that is not an accurate
    # description can be deleted and changed": a stale docstring line may go; the tree and the verbatim code lines
    # below still prove that no CODE went with it)
    sa, sb = _skeleton(before), _skeleton(after)
    if sa != sb:
        return 1, "TREE CHANGED beyond comments/docstrings at: %s" % _first_diff(sa, sb)
    ca, cb = _code_lines(before), _code_lines(after)
    if ca != cb:
        k = next((i for i, (x, y) in enumerate(zip(ca, cb)) if x != y), min(len(ca), len(cb)))
        x = ca[k] if k < len(ca) else "<end>"
        y = cb[k] if k < len(cb) else "<end>"
        return 1, "CODE LINE CHANGED (whitespace counts; #%d of %d/%d): %r -> %r" % (k + 1, len(ca), len(cb), x.strip()[:70], y.strip()[:70])
    return 0, "OK comment/docstring-only (%d -> %d lines, %d code lines verbatim)" % (before.count("\n") + 1, after.count("\n") + 1, len(ca))


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
        ("an EMPTY module gains a docstring (the __init__.py case)", "\"\"\"The package.\"\"\"\n", 0),
        ("a docstring-only def gains a comment", base.replace("    def m(self):\n        return 1\n", "    def m(self):\n        \"\"\"One.\"\"\"\n        # the one\n        return 1\n"), 0),
        ("MUTANT a statement added", base.replace("    y = x + 1\n", "    y = x + 1\n    y += 1\n"), 1),
        ("MUTANT a constant changed", base.replace("x + 1", "x + 2"), 1),
        ("MUTANT a name changed", base.replace("def f(x)", "def f(z)"), 1),
        ("MUTANT a line deleted", base.replace("    y = x + 1\n    return y\n", "    return x + 1\n"), 1),
        ("MUTANT a comment that swallowed a line", base.replace("    y = x + 1\n", "    # y = x + 1\n"), 1),
        ("MUTANT a broken docstring", base.replace("def f(x):\n", "def f(x):\n    \"\"\"Add one.\n"), 3),
        ("MUTANT an import added", base.replace("import os\n", "import os\nimport sys\n"), 1),
        ("MUTANT a return value changed", base.replace("return 1", "return 2"), 1),
        ("MUTANT whitespace glued inside a code line (`y =x`)", base.replace("    y = x + 1\n", "    y =x + 1\n"), 1),
        ("MUTANT a code line's spacing changed (`x+1`)", base.replace("x + 1", "x+1"), 1),
        ("a trailing comment added to a code line", base.replace("    y = x + 1\n", "    y = x + 1  # add one\n"), 0),
        ("a trailing comment re-aligned", base.replace("    return y\n", "    return y   # out\n"), 0),
        ("MUTANT a comment dropped inside a data string",
         "DATA = \"\"\"line one\nline two\n\"\"\"\n".replace("line two\n", "line two\n# a comment in data\n"), 1),
    ]
    bad = 0
    for name, after, want in cases:
        before = "" if name.startswith("an EMPTY module") else ("DATA = \"\"\"line one\nline two\n\"\"\"\n" if "data string" in name else base)
        code, msg = gate(before, after, "selftest")
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
