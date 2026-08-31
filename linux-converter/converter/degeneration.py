"""Degeneration tripwire -- the calibrated zlib+trigram detector, ported from the Desktop.

Port of ``windows-converter/fidelity_audit.py::degeneration()`` (docs/15 §5; thresholds §9.1;
AND-rule recalibration §9.2). The Desktop lane has carried this detector since 2026-07-20; the
Linux lanes shipped with only the chars-per-page yield probe, so a looping conversion here
could publish to staging unflagged -- the vault's second front door had no degeneration gate.

Report-mode by design: the result is EVIDENCE in manifest.json and a WARNING in the journal;
it never blocks publishing. Enforcement stays an open policy question for Rab, same as the
Desktop's audit lever (docs/19 §9).

Thresholds are the Desktop's calibrated values, deliberately NOT re-derived here: they carry
docs/15 §9.1/§9.2 provenance (real loops: zlib<=0.17 AND trigram>=1674 on Beer; the
table-dense Cybernetics book false-fired the old zlib-OR rule at zlib 0.11/0.15 but its
varied words gave trigram 28/10, so the AND rule clears tables). Two lanes, one detector,
one calibration -- if the Desktop recalibrates, port the numbers, do not fork them.
"""

import re
import zlib
from collections import Counter

# docs/15 §9.1 priors, §9.2 recalibration. A loop is BOTH crushed-compressible AND has an
# extreme repeated word-trigram -- require both (AND). Wide margin either side of the gate:
# table max trigram observed 28 vs loop min observed 1674.
DEGEN_ZLIB_MAX = 0.20
DEGEN_TRIGRAM_MAX = 40
DEGEN_BLOCK_MIN_CHARS = 200
DEGEN_LINE_REPEAT = 20  # longest CONTIGUOUS run of one normalized line beyond this flags


def degeneration(markdown: str) -> dict:
    """Per-paragraph zlib ratio + max repeated trigram (word, or char for space-free/CJK
    blocks), plus a repeated-output-line check. Same output shape as the Desktop audit's
    ``degeneration_detail`` so downstream readers (Bench zones, damage map) need no second
    schema: {flagged, repeated_lines, md_lines, worst[]}.
    """
    flagged = False
    worst = []
    pos = 0
    for para in markdown.split("\n\n"):
        line_no = markdown.count("\n", 0, pos) + 1
        pos += len(para) + 2
        p = para.strip()
        if len(p) < DEGEN_BLOCK_MIN_CHARS:
            continue
        raw = p.encode("utf-8")
        ratio = len(zlib.compress(raw, 6)) / len(raw)
        toks = p.lower().split()
        if len(toks) < 5:  # CJK / space-free block: char n-grams instead of word n-grams
            toks = list(re.sub(r"\s", "", p))
        tri = Counter(" ".join(toks[i : i + 3]) for i in range(len(toks) - 2))
        mx = max(tri.values()) if tri else 0
        # AND, not OR (docs/15 §9.2): dense tables are compressible too (structural |, ---,
        # <br>) but their words vary -> low trigram, so the trigram gate clears them.
        if ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX:
            flagged = True
            worst.append(
                {
                    "line": line_no,
                    "chars": len(p),
                    "zlib": round(ratio, 3),
                    "max_trigram": mx,
                    "excerpt": " ".join(p.split()[:8]),
                }
            )
    # Repeated-line check (docs/15 §9.2): a degeneration loop repeats a line CONTIGUOUSLY
    # (the decoder gets stuck), so measure the longest RUN of consecutive identical non-blank
    # lines -- NOT the total count. Legitimate structure repeats but is DISTRIBUTED (section
    # headings, table rows), giving a run of 1. Blanks and table rows never count toward a run.
    max_run, run, prev = 0, 0, None
    for ln in markdown.splitlines():
        s = ln.strip()
        if not s or s.startswith("|"):
            continue
        run = run + 1 if (s == prev and len(s) > 20) else 1
        prev = s
        max_run = max(max_run, run)
    repeated_lines = max_run if max_run > DEGEN_LINE_REPEAT else 0
    if repeated_lines:
        flagged = True
    worst.sort(key=lambda w: (w["zlib"], -w["max_trigram"]))
    return {
        "flagged": flagged,
        "repeated_lines": repeated_lines,
        "md_lines": markdown.count("\n") + 1,
        # NUM-3 parity (review m6): the true count beside the capped exemplar list,
        # matching the Windows twin in fidelity_audit.degeneration
        "worst": worst[:10],
        "blocks_total": len(worst),
        "worst_capped_at": 10,
    }
