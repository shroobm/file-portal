# -*- coding: utf-8 -*-
"""latex_structure.py — SYM-056's structural check on converter markdown (S168 E3): every `\\begin{X}` balanced against its
`\\end{X}` per environment name (the strict-literal delta the Codex lane's MSG-CDX-0014 asked for), the nesting walked (a
`\\end{X}` that closes nothing, or closes the wrong environment, is named with its line), and runaway column specs flagged
(an `array`/`tabular` spec wider than MAX_SPEC_COLS — the S109 specimen was 36 `c`s). Read-only, stdlib, no engine.

    from latex_structure import check
    r = check(markdown)   # {"begin", "end", "delta": {env: begin-end}, "unterminated", "unopened", "misordered": [...],
                          #  "runaway": [(line, env, spec)], "valid": bool}
    python latex_structure.py <file.md> ...   # one line per file, exit 0 when every file is valid, 1 otherwise, 2 usage

The converter's guard-to-be: SYM-056's cell names it ("a structural validator on converter output, before the analyst ever
sees it"); wiring it into convert_and_ship.py is the restart window's act, not this file's. MAX_SPEC_COLS is a lever
(Rab's); the check reports, it never edits.
"""
import re
import sys
from collections import Counter

MAX_SPEC_COLS = 20  # lever: the widest honest column spec seen on the shelf is far below the S109 runaway (36)
# Whitespace-aware on purpose: the Codex lane's MSG-CDX-0014 found one Ashby opener written as `\begin` + CRLF + `{array}` that a
# strict-literal `\begin{array}` misses while its closer is counted (60 literal vs 61 semantic). `begin_literal` keeps the strict
# count beside the semantic one so both readings stay on the record.
_BEGIN = re.compile(r"\\begin\s*\{([A-Za-z*]+)\}(?:\{([^}\n]*)\})?")
_END = re.compile(r"\\end\s*\{([A-Za-z*]+)\}")
_BEGIN_LITERAL = re.compile(r"\\begin\{([A-Za-z*]+)\}")
_SPEC_ENVS = {"array", "tabular", "tabularx", "matrix"}
_TOKENS = re.compile(r"\\(begin|end)\s*\{([A-Za-z*]+)\}(?:\{([^}\n]*)\})?")


def _spec_width(spec: str) -> int:
    """Column letters in a spec: `c`, `l`, `r`, `p{…}`; a `*{n}{c}` repeat counts n."""
    rep = re.search(r"\*\{?(\d+)\}?", spec)
    if rep:
        return int(rep.group(1))
    return len(re.sub(r"p\{[^}]*\}", "p", spec).replace("|", "").replace("@{}", "").strip())


def check(md: str) -> dict:
    begins = Counter(m.group(1) for m in _BEGIN.finditer(md))
    ends = Counter(m.group(1) for m in _END.finditer(md))
    envs = sorted(set(begins) | set(ends))
    delta = {e: begins[e] - ends[e] for e in envs if begins[e] != ends[e]}
    stack, misordered, unopened = [], [], 0
    runaway = []
    line_of = lambda pos: md.count("\n", 0, pos) + 1  # noqa: E731
    for m in _TOKENS.finditer(md):
        kind, env, spec = m.group(1), m.group(2), m.group(3)
        if kind == "begin":
            stack.append((env, line_of(m.start())))
            if env in _SPEC_ENVS and spec is not None and _spec_width(spec) > MAX_SPEC_COLS:
                runaway.append((line_of(m.start()), env, spec[:60]))
        else:
            if not stack:
                unopened += 1
                misordered.append((line_of(m.start()), "end{%s} closes nothing" % env))
            elif stack[-1][0] != env:
                misordered.append((line_of(m.start()), "end{%s} closes begin{%s} from line %d" % (env, stack[-1][0], stack[-1][1])))
                stack.pop()
            else:
                stack.pop()
    unterminated = sum(v for v in delta.values() if v > 0)
    return {
        "begin": sum(begins.values()),
        "begin_literal": len(_BEGIN_LITERAL.findall(md)),
        "end": sum(ends.values()),
        "delta": delta,
        "unterminated": unterminated,
        "unopened": unopened,
        "misordered": misordered,
        "runaway": runaway,
        "valid": not delta and not misordered and not runaway,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: latex_structure.py <file.md> ...")
        return 2
    red = 0
    for path in argv[1:]:
        try:
            md = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print("%s: UNREAD (%s)" % (path, e))
            red = 1
            continue
        r = check(md)
        red = red or (0 if r["valid"] else 1)
        print("%s: begin=%d (literal %d) end=%d delta=%s unterminated=%d unopened=%d misordered=%d runaway=%d %s" % (
            path, r["begin"], r["begin_literal"], r["end"], r["delta"] or "{}", r["unterminated"], r["unopened"], len(r["misordered"]),
            len(r["runaway"]), "valid" if r["valid"] else "INVALID"))
    return red


if __name__ == "__main__":
    sys.exit(main(sys.argv))
