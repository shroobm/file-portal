#!/usr/bin/env python3
"""observability/line_gate.py — the gate under a comment-only edit for Rust, JavaScript and PowerShell (S218 E8 wave 3).
A labelling lane in these languages may add WHOLE comment lines and blank lines, and nothing else. The gate: remove every
line that is entirely a comment (Rust/JS: `//`, `///`, `//!`, and block-comment lines `/* … */` that start and end on
comment lines; PowerShell: `#` lines and `<# … #>` block lines) and every blank line, then the remaining lines of the
two files must be IDENTICAL, verbatim and in order (whitespace counts; a trailing comment added to a code line is a
changed code line here — the brief forbids it). Nothing is parsed: a string that happens to hold `//` is not a comment
line because the LINE does not start with it; a block comment opened in the middle of a code line is part of that line.

    python observability/line_gate.py <path> [--base <git ref>]     # the working file against <ref>:<path> (default HEAD)
    python observability/line_gate.py <path> --against <other>      # two files on disk
    python observability/line_gate.py --selftest

Exit 0 comment/blank-only · 1 a code line changed, appeared or vanished · 2 usage or unreadable. Read-only; stdlib.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys

KINDS = {".rs": "c", ".js": "c", ".mjs": "c", ".ts": "c", ".ps1": "ps", ".psm1": "ps"}


def code_lines(src: str, kind: str) -> list[str]:
    out = []
    in_block = False
    for raw in src.splitlines():
        s = raw.strip()
        if in_block:
            if (kind == "c" and s.endswith("*/")) or (kind == "ps" and s.endswith("#>")):
                in_block = False
            continue
        if not s:
            continue
        if kind == "c":
            if s.startswith("//"):
                continue
            if s.startswith("/*"):
                if s.endswith("*/") and s.count("*/") == 1:
                    continue
                in_block = True
                continue
        else:
            if s.startswith("#") and not s.startswith("#>"):
                if s.startswith("<#") and not s.endswith("#>"):
                    in_block = True
                continue
            if s.startswith("<#"):
                if not s.endswith("#>"):
                    in_block = True
                continue
        out.append(raw.rstrip())
    return out


def gate(before: str, after: str, kind: str) -> tuple[int, str]:
    a, b = code_lines(before, kind), code_lines(after, kind)
    if a == b:
        return 0, "OK comment/blank-only (%d -> %d lines, %d code lines verbatim)" % (before.count("\n") + 1, after.count("\n") + 1, len(a))
    k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    x = a[k] if k < len(a) else "<end>"
    y = b[k] if k < len(b) else "<end>"
    return 1, "CODE LINE CHANGED (#%d of %d/%d): %r -> %r" % (k + 1, len(a), len(b), x.strip()[:70], y.strip()[:70])


def _read(p: str) -> str:
    return io.open(p, encoding="utf-8", errors="replace").read()


def _git_show(ref: str, path: str) -> str | None:
    top = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(path)), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        return None
    root = top.stdout.strip()
    rel = os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")
    r = subprocess.run(["git", "-C", root, "show", "%s:%s" % (ref, rel)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def selftest() -> int:
    rs = "use std::fs;\n\nfn f(x: i32) -> i32 {\n    let y = x + 1; // add\n    y\n}\n"
    js = "const a = 1;\nfunction f(x) {\n  return x + 1;\n}\n"
    ps = "param([string]$Name)\n$x = 1\nWrite-Output $x\n"
    cases = [
        ("rs: a doc comment line added", rs.replace("fn f(", "/// Adds one.\nfn f("), rs, "c", 0),
        ("rs: a section comment and a blank line", rs.replace("use std::fs;\n", "use std::fs;\n\n// -- the helper --\n"), rs, "c", 0),
        ("rs: a block comment on its own lines", rs.replace("fn f(", "/*\n * adds one\n */\nfn f("), rs, "c", 0),
        ("rs: unchanged", rs, rs, "c", 0),
        ("rs MUTANT: a space glued in a code line", rs.replace("let y = x + 1;", "let y =x + 1;"), rs, "c", 1),
        ("rs MUTANT: a trailing comment added to a code line", rs.replace("    y\n", "    y // return\n"), rs, "c", 1),
        ("rs MUTANT: a code line deleted", rs.replace("    let y = x + 1; // add\n", ""), rs, "c", 1),
        ("rs MUTANT: a statement added", rs.replace("    y\n", "    let z = 2;\n    y\n"), rs, "c", 1),
        ("rs MUTANT: a comment opened mid-line swallowing code", rs.replace("    let y = x + 1; // add\n    y\n", "    let y = x + 1; /* add\n    y */\n"), rs, "c", 1),
        ("js: a comment line added", js.replace("function f(", "// adds one\nfunction f("), js, "c", 0),
        ("js MUTANT: a string with // changed", js.replace("const a = 1;", "const a = '//x';"), js, "c", 1),
        ("ps: a comment line and a block comment", ps.replace("$x = 1\n", "# the count\n$x = 1\n<#\n a block\n#>\n"), ps, "ps", 0),
        ("ps MUTANT: a space glued", ps.replace("$x = 1", "$x =1"), ps, "ps", 1),
        ("ps MUTANT: a trailing comment", ps.replace("$x = 1\n", "$x = 1 # one\n"), ps, "ps", 1),
    ]
    bad = 0
    for name, after, before, kind, want in cases:
        code, msg = gate(before, after, kind)
        ok = code == want
        bad += not ok
        print("%s %s -> %d (want %d) %s" % ("PASS" if ok else "FAIL", name, code, want, msg[:80]))
    print("════ line_gate selftest: %d/%d ════" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    kind = KINDS.get(os.path.splitext(path)[1].lower())
    if not kind:
        print("UNREAD: %s is not a Rust/JS/PowerShell file" % path)
        return 2
    after = _read(path)
    if "--against" in argv:
        before = _read(argv[argv.index("--against") + 1])
    else:
        ref = argv[argv.index("--base") + 1] if "--base" in argv else "HEAD"
        before = _git_show(ref, path)
        if before is None:
            print("UNREAD: %s not in %s" % (path, ref))
            return 2
    code, msg = gate(before, after, kind)
    print("%s %s" % (path, msg))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
