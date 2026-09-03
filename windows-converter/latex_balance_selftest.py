"""Tripwires for SYM-056 — the report-only LaTeX environment balance (signed Rab 2026-09-03).

Run with the marker-env interpreter (fidelity_audit imports pymupdf and rapidfuzz at module
level):
  C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe latex_balance_selftest.py

NO GPU, no marker, no ollama, no real book. Every body here is a synthetic string; the one
PDF (L7) is built in memory by pymupdf in a temp dir and deleted after — CPU only, safe to
run beside a live conversion. Nothing writes into the pipeline roots.

Each tripwire names what breaks if it fires:
  L1  balanced bodies read zero      — a counter that cannot say "nothing is wrong" is noise;
                                       includes Codex's CRLF-split BALANCED negative control
  L2  the SYM-056 shape reads 61     — DECOY: the strict-literal rule reads 60 on this body
                                       and 60 is the falsified semantic claim (MSG-CDX-0014);
                                       61 is the honest count and the test asserts BOTH
  L3  nesting resolves by depth      — DECOY: a first-in-first-out pairer returns the same
                                       count and the WRONG line, and the line is the whole
                                       value of the field (the highlight a human repairs at)
  L4  the honest zero shape          — a body with no \\begin still carries every key; an
                                       absent or null key is a silence the reader must guess
  L5  the arithmetic closes          — begin - end + stray_end == unterminated for every
                                       listed environment, stray closes included
  L6  REPORT-ONLY, structurally      — the verdict is byte-identical with and without the
                                       block, a 61-unterminated body still verdicts "pass",
                                       and compute_verdict's source cannot even name the key
  L7  it rides the real block        — audit_convert carries latex_balance BESIDE tripwires
                                       (never inside them) and the verdict does not move
  L8  fences are NOT skipped         — the declared choice, made falsifiable: an unmatched
                                       open inside a fenced block is counted, because the
                                       shipped SYM-056 specimen was $$\\begin{array}{c*36}$$
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import fidelity_audit as fa  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


# ---------- L1: balanced bodies read zero (with the CRLF negative control) ----------
print("L1 balanced bodies read zero")
BALANCED = (
    "# Chapter\n"
    "$$\\begin{array}{cc} a & b \\end{array}$$\n"
    "text\n"
    "$$\\begin{array}{c} x \\end{array}$$\n"
    "$$\\begin{align} y = 1 \\end{align}$$\n"
    "$$\\begin{array}{c} z \\end{array}$$\n"
)
b1 = fa.latex_balance(BALANCED)
check(b1["unterminated_total"] == 0, "three balanced arrays + one align read 0 unterminated")
check(b1["environments"] == {}, "a balanced environment is never listed")
check(b1["begins_seen"] == 4, "balanced environments still count into the denominator (4)")

# Codex's control, MSG-CDX-0014: a whitespace-split TeX command must still PAIR, or the
# guard inherits the very blind spot that made 60 look like the semantic count.
CRLF_BALANCED = "$$\\begin\r\n{array}{cc} a \\end{array}$$\n"
b1b = fa.latex_balance(CRLF_BALANCED)
check(b1b["unterminated_total"] == 0 and b1b["begins_seen"] == 1,
      "negative control: a CRLF-split \\begin still pairs with its \\end (0 unmatched)")

# ---------- L2: the SYM-056 shape — 61 unmatched, and the 60 the literal rule reports ----------
print("L2 the SYM-056 shape reads 61, not the literal 60")
SYM056 = ["# Ashby-shaped body", ""]                       # first \begin lands on line 3
for _ in range(60):
    SYM056.append("$$\\begin{array}{cccccccccccccccccccccccccccccccccccc}$$")
SYM056_BODY = "\n".join(SYM056) + "\n$$\\begin\r\n{array}{cc}$$\n"
b2 = fa.latex_balance(SYM056_BODY)
literal_delta = SYM056_BODY.count("\\begin{array}") - SYM056_BODY.count("\\end{array}")
print(f"    strict-literal delta reads {literal_delta} · whitespace-aware stack reads "
      f"{b2['unterminated_total']} (first at line {b2['environments']['array']['line']})")
check(b2["unterminated_total"] == 61, "61 unmatched \\begin{array} — the honest count")
check(b2["unterminated_total"] != literal_delta and literal_delta == 60,
      "DECOY: it is NOT 60, the strict-literal delta that MSG-CDX-0014 falsified")
check(b2["environments"]["array"]["line"] == 3,
      "the first unmatched \\begin is reported at its line (3), the human's highlight")
check(b2["environments"]["array"]["begin"] == 61
      and b2["environments"]["array"]["end"] == 0
      and b2["environments"]["array"]["stray_end"] == 0,
      "the per-env record names begin, end and stray_end, not just the delta")
check(b2["begins_seen"] == 61, "docs/34: the denominator (begins seen) rides with it")

# ---------- L3: nesting resolves by depth, not by greedy pairing ----------
print("L3 nesting by depth (the greedy pairer is computed, not assumed)")
NESTED = (
    "$$\\begin{array}{c}\n"        # line 1 — outer, NEVER closed
    "  $$\\begin{array}{c}\n"      # line 2 — inner
    "  \\end{array}$$\n"           # line 3 — closes the INNER one (LIFO)
    "tail\n"
)


def greedy_first_unmatched(text: str, env: str) -> int | None:
    """The wrong implementation this case exists to refute: pair each \\end with the EARLIEST
    open (first-in-first-out) instead of the innermost. Same count, different line."""
    opens: list[int] = []
    ends = 0
    for m in re.finditer(r"\\(begin|end)\s*\{" + env + r"\}", text):
        if m.group(1) == "begin":
            opens.append(text.count("\n", 0, m.start()) + 1)
        else:
            ends += 1
    return opens[ends] if len(opens) > ends else None


b3 = fa.latex_balance(NESTED)
greedy_line = greedy_first_unmatched(NESTED, "array")
print(f"    depth-correct line {b3['environments']['array']['line']} · "
      f"greedy(FIFO) line {greedy_line}")
check(b3["unterminated_total"] == 1, "one environment left open (count agrees either way)")
check(b3["environments"]["array"]["line"] == 1,
      "the OUTER opener (line 1) is the unmatched one — depth, not order")
check(b3["environments"]["array"]["line"] != greedy_line and greedy_line == 2,
      "DECOY: it is NOT line 2, the answer a greedy first-in-first-out pairer produces")

# ---------- L4: the honest zero shape ----------
print("L4 the honest zero shape")
b4 = fa.latex_balance("# A book with no math at all\n\nJust prose, and a $dollar$ sign.\n")
check(b4 == {"checked": True, "environments": {}, "unterminated_total": 0, "begins_seen": 0},
      "no \\begin anywhere -> checked/environments/unterminated_total/begins_seen all present")
check(b4["checked"] is True and b4["unterminated_total"] is not None,
      "never null, never omitted — an unmeasured zero must not read like an absent key")

# ---------- L5: the arithmetic closes, stray closes included ----------
print("L5 begin - end + stray_end == unterminated")
STRAY = (
    "\\end{array}$$\n"             # line 1 — a close with nothing open
    "$$\\begin{align}\n"           # line 2 — open
    "$$\\begin{align}\n"           # line 3 — open
    "\\end{align}$$\n"             # line 4 — closes line 3
)
b5 = fa.latex_balance(STRAY)
for env, d in sorted(b5["environments"].items()):
    print(f"    {env}: begin {d['begin']} end {d['end']} stray_end {d['stray_end']} "
          f"unterminated {d['unterminated']} line {d['line']}")
check(all(d["begin"] - d["end"] + d["stray_end"] == d["unterminated"]
          for d in b5["environments"].values()),
      "every listed environment's four numbers reconcile")
check(b5["environments"]["array"]["stray_end"] == 1
      and b5["environments"]["array"]["line"] is None,
      "a stray \\end is listed with an honest null line — there is no unmatched open to point at")
check(b5["unterminated_total"] == 1 and b5["begins_seen"] == 2,
      "a stray close never inflates the unterminated count")

# ---------- L6: REPORT-ONLY, structurally ----------
print("L6 report-only — the verdict cannot move")
BASE_CONVERT = {"kind": "fidelity", "doc_survival": 1.0, "pages_flagged": [], "runs": [],
                "tripwires": {"degeneration": False}}
with_block = dict(BASE_CONVERT, latex_balance=fa.latex_balance(SYM056_BODY))
v_without = fa.compute_verdict(BASE_CONVERT, None)
v_with = fa.compute_verdict(with_block, None)
print(f"    verdict without the block: {v_without!r} · with 61 unterminated: {v_with!r}")
check(v_with == v_without == "pass",
      "a body with 61 unterminated environments still verdicts pass — report-only, as signed")
an = {"doc_survival": 0.99, "runs": [], "runs_total": 0, "runs_capped_at": 25}
check(fa.compute_verdict(with_block, an) == fa.compute_verdict(BASE_CONVERT, an),
      "and the analyst-stage verdict is identical with and without it")
SRC = (HERE / "fidelity_audit.py").read_text(encoding="utf-8")
verdict_src = SRC[SRC.index("def compute_verdict("):SRC.index("def build_fidelity_block(")]
check("latex_balance" not in verdict_src,
      "compute_verdict's source cannot even name the key — a future wiring breaks this test")
fn_src = SRC[SRC.index("def latex_balance("):SRC.index("# Stage audits")]
check(".write(" not in fn_src and "open(" not in fn_src,
      "the measurement writes nothing — it never touches the markdown or the disk")
check('"latex_balance": latex_balance(markdown),' in SRC,
      "the call site reads the RAW markdown (what ships), not the normalized stream")

# ---------- L7: it rides the real convert block ----------
print("L7 audit_convert carries it beside the tripwires")
TMP = Path(tempfile.mkdtemp(prefix="fp-sym056-selftest-"))
try:
    import pymupdf                                     # CPU only; no marker, no GPU

    doc = pymupdf.open()
    page = doc.new_page()
    for i, line in enumerate([
        "the quick brown fox jumps over the lazy dog again and again",
        "a second line of witness text with enough words to be scored",
        "a third line of witness text so the page clears PAGE_MIN_WORDS",
    ]):
        page.insert_text((72, 90 + 18 * i), line, fontsize=11)
    pdf_path = TMP / "witness.pdf"
    doc.save(str(pdf_path))
    doc.close()

    MD = ("the quick brown fox jumps over the lazy dog again and again\n"
          "a second line of witness text with enough words to be scored\n"
          "a third line of witness text so the page clears PAGE_MIN_WORDS\n"
          "$$\\begin{array}{cc}$$\n"
          "$$\\begin{bmatrix} 1 & 0 \\end{bmatrix}$$\n"
          "$$\\begin{align}\n")
    conv = fa.audit_convert(pdf_path, MD, "clean")
    lb = conv.get("latex_balance")
    print(f"    block latex_balance: {lb}")
    check(lb is not None and lb["unterminated_total"] == 2,
          "the real convert block carries the measurement (2 unterminated here)")
    check("latex_balance" not in conv["tripwires"],
          "it rides BESIDE the tripwires, never inside them — it is not one")
    stripped = {k: v for k, v in conv.items() if k != "latex_balance"}
    check(fa.build_fidelity_block(conv, None)["verdict"]
          == fa.compute_verdict(stripped, None),
          "the fidelity block's verdict is what it would be with the key removed")
    check(sorted(lb["environments"]) == ["align", "array"]
          and lb["begins_seen"] == 3,
          "bmatrix balanced (unlisted, counted); array and align listed as unterminated")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

# ---------- L8: fences are NOT skipped (the declared choice, made falsifiable) ----------
print("L8 fenced and inline math are counted, by decision")
FENCED = ("Example:\n\n```latex\n$$\\begin{array}{c*36}$$\n```\n\n"
          "and inline `\\begin{cases}` too\n")
b8 = fa.latex_balance(FENCED)
check(b8["unterminated_total"] == 2,
      "an unmatched open inside a fence or inline span is COUNTED (docstring names why)")

# ---------- verdict ----------
n_checks = len(re.findall(r"^\s*check\(", Path(__file__).read_text(encoding="utf-8"), re.M))
total = len(FAILURES)
print(f"\n{'RED: ' + str(total) + ' tripwire(s) fired' if FAILURES else 'GREEN'} "
      f"({n_checks - total}/{n_checks})")
if FAILURES:
    print("Failed:")
    for f in FAILURES:
        print(f"  - {f}")
sys.exit(1 if FAILURES else 0)
