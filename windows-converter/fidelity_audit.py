"""windows-converter/fidelity_audit.py — The Survival Audit (docs/15).

Measures how much of a source PDF survives into the Marker markdown (convert stage) and
how much of the Marker markdown survives the qwen formatting pass (analyst stage), using
window-survival containment against an ephemeral pymupdf witness. Deterministic, CPU-only,
report-only. See docs/15 for the design and the CLOSED decisions — do not redesign here.

Public API (imported by convert_and_ship.py, all crash-wrapped by the caller):
  audit_convert(pdf_path, markdown, lane, asset_count=None) -> dict   # the "convert" sub-block
  audit_analyst(marker_markdown, analyst_markdown)          -> dict   # the "analyst" sub-block
  compute_verdict(convert_block, analyst_block)             -> str    # "pass"|"flag"|"fail"
  verdict_with_phase(convert_block, analyst_block)          -> (str, str|None)  # + the phase that decided (S175)
  build_fidelity_block(convert_block, analyst_block=None)   -> dict   # the manifest "fidelity" object

Run standalone (marker-env interpreter):
  python fidelity_audit.py --pdf <src.pdf> --md <out.md> --lane clean|scan
  python fidelity_audit.py --md <analyst.md> --analyst-ref <marker.md>   # stage-2 only
"""

import argparse
import json
import os
import random
import re
import zlib
from collections import Counter
from pathlib import Path

import pymupdf
from rapidfuzz import fuzz

# J32-A (docs/54-repair-road, signed: Proposal A): the pure normalisation core (windows,
# prepare_output, is_cjk, _merge_runs) and the normalisation LADDER (unescape/punct_free/
# space_free/chunk_survival) moved to text_norm.py -- a module with no pymupdf import, so
# analyst.py's per-chunk survival guard (J32-B, analyst.py:299) can import it without
# dragging fidelity_audit's witness-extraction dependencies along. Re-exported here under
# their original names so this module's public surface (`fa.prepare_output`, `fa.make_windows`,
# `fa._merge_runs`, `fa.WINDOW_WORDS`, ...) is BYTE-FOR-BYTE unchanged for audit_convert and
# every existing caller (docs/54's verification scripts import them as `fa.X`).
from text_norm import (  # noqa: F401 -- re-exported, not merely used below
    WINDOW_WORDS, WINDOW_MIN_WORDS, CJK_WINDOW_CHARS, CJK_WINDOW_MIN,
    prepare_output, is_cjk, make_windows, _merge_runs,
    unescape, punct_free, space_free,
    prepare_for,  # J44 (S182): the ladder-aware prepare; v2 == prepare_output byte for byte
    _common, _finalize,  # prepare_witness (witness-side only) still calls these directly
)
import ladder_lever  # J44 (S182): the lever's one reader (roots.json `ladder` -> ladder.txt)
import table_shape  # S209 E11: the source's table geometry inside Marker's table boxes (report-only, beside survival)
import figure_text  # S209 E13: the source's words inside Marker's figure boxes — chart text as text (report-only)

# ---------------------------------------------------------------------------
# Constants. Thresholds calibrated over the vaulted corpus (docs/15 §9.1). Per the
# SIGNED enforcement policy (docs/15 §12, 2026-07-20): degeneration + analyst near-exact
# are the only gates (compute_verdict → "fail"); survival/agreement, page flags, runs,
# and garbage rate stay report-only LOCALIZERS (→ "flag"). Whether a "fail" parks a
# bundle is the separate report<->enforce lever (convert_and_ship, default "report").
# ---------------------------------------------------------------------------
SCHEMA_VERSION = 1

PAGE_MIN_WORDS = 15        # skip image-only / near-blank witness pages
FUZZY_PASS = 90            # rapidfuzz partial_ratio pass threshold
FUZZY_ANCHOR_CAP = 50      # max anchor occurrences probed per missing window
RUN_MIN_WINDOWS = 2        # a reportable omission run is >= this many adjacent misses
REVERSE_SAMPLE_N = 200
REVERSE_SEED = 20260720    # fixed → deterministic

# Degeneration (docs/15 §9.1 priors + §9.2 recalibration). A loop is BOTH crushed-
# compressible AND has an extreme repeated word-trigram; require both (AND). Real loops:
# zlib<=0.17 AND trigram>=1674 (Beer). Dense markdown tables fool zlib (Cybernetics models
# book: zlib 0.11/0.15) but their words vary → low trigram (28/10), so the trigram gate
# clears them. Wide margin either side (table max tri 28 vs loop min 1674).
DEGEN_ZLIB_MAX = 0.20
DEGEN_TRIGRAM_MAX = 40
DEGEN_BLOCK_MIN_CHARS = 200
DEGEN_LINE_REPEAT = 20     # any normalized output line repeated more than this many times

# Per-stage flag/fail priors (docs/15 §6).
CLEAN_PAGE_FLAG = 0.85
CLEAN_DOC_FLAG = 0.97
CLEAN_RUN_WORDS = 50
SCAN_PAGE_FLAG = 0.70
SCAN_GARBAGE_FLAG = 0.20   # 1 - dict_hit prior; garbage-token rate above this flags
ANALYST_DOC_FAIL = 0.995
ANALYST_RUN_WORDS = 25
# SYM-138 (S209 E10): a failed run re-tested as a BAG of words within one span of the output — a reordering (a stacked
# table header the analyst merged into one row, cells moved), not an omission. Report-only: the run is marked, the block
# counts it, the verdict still counts the run — the gate is signed (docs/15 §12) and the rescue waits for his word.
REORDER_SPAN = 4           # the span searched, in multiples of the run's own length (chars) each side of its rarest word
REORDER_ANCHOR_CAP = 50    # occurrences of the rarest word probed
_WORD_CHAR = re.compile(r"\w")  # a bag token must carry a word character (the ladder's lone backslash is structure)
WITNESS_COVERAGE_FLOOR = 0.50  # lever-waiver: Rab's word 2026-09-13 (Desk bf4d5d05, S144 E2); a verdict floor is a rule (docs/15 §12.3), not a lever   # S144: pages_scored / pages_total under this -> the convert gate reads flag, never pass


# ---------------------------------------------------------------------------
# Windows long-path safety (docs/15 §8 / F5: pre-L15 vault paths reach 349 chars).
# ---------------------------------------------------------------------------
def _longpath(p) -> str:
    p = os.path.abspath(str(p))
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        return "\\\\?\\" + p
    return p


def read_text(path) -> str:
    with open(_longpath(path), "r", encoding="utf-8") as f:
        return f.read()


def prepare_witness(pages_raw: list[str]) -> list[str]:
    """Steps 1-3 per page, then step-5 repeated-line strip across pages, then finalize."""
    pages = [_common(p) for p in pages_raw]
    n = len(pages)
    line_pagecount: Counter = Counter()
    for p in pages:
        for line in {ln.strip() for ln in p.splitlines() if ln.strip()}:
            line_pagecount[line] += 1
    # Only strip when the corpus is big enough for "40% of pages" to mean something.
    threshold = max(2, int(round(0.4 * n)))
    repeated = {ln for ln, c in line_pagecount.items() if n >= 3 and c >= threshold}
    out = []
    for p in pages:
        kept = [ln for ln in p.splitlines() if ln.strip() and ln.strip() not in repeated]
        out.append(_finalize("\n".join(kept)))
    return out


# ---------------------------------------------------------------------------
# Witness extraction (docs/15 §2). Ephemeral: extracted, scored, discarded.
# ---------------------------------------------------------------------------
def extract_witness(pdf_path) -> tuple[list[str], int]:
    """(per-page raw text, unique embedded raster count). Reads bytes via a long-path-safe
    handle and hands a stream to pymupdf so MuPDF never touches the long path itself.
    Images are deduped by xref — get_images repeats an xref on every page it appears on,
    and Marker deliberately drops decorative/inline rasters, so this is an informational
    signal only (never a verdict input)."""
    with open(_longpath(pdf_path), "rb") as f:
        data = f.read()
    pages, xrefs = [], set()
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text())
            for im in page.get_images(full=True):
                xrefs.add(im[0])
    return pages, len(xrefs)


# ---------------------------------------------------------------------------
# Windowing + scoring (docs/15 §4).
# ---------------------------------------------------------------------------
def _build_index(output_final: str) -> tuple[dict, dict]:
    idx: dict[str, list[int]] = {}
    freq: dict[str, int] = {}
    for m in re.finditer(r"\S+", output_final):
        w = m.group(0)
        idx.setdefault(w, []).append(m.start())
        freq[w] = freq.get(w, 0) + 1
    return idx, freq


def _fuzzy_hit(window: str, output_search: str, idx: dict, freq: dict, cjk: bool) -> bool:
    if cjk:
        # Small CJK docs: partial_ratio against the whole (space-free) output is cheap.
        return fuzz.partial_ratio(window, output_search) >= FUZZY_PASS
    anchors = [w for w in window.split() if w in freq]
    if not anchors:
        return False
    rare = min(anchors, key=lambda w: freq[w])
    span = len(window)
    for off in idx[rare][:FUZZY_ANCHOR_CAP]:
        seg = output_search[max(0, off - span): off + span + len(rare)]
        if fuzz.partial_ratio(window, seg) >= FUZZY_PASS:
            return True
    return False


def _reorder(run_text: str, out: str, idx: dict, freq: dict) -> bool:
    """SYM-138: True when every word of a failed run occurs, as a bag (each at least as often as in the run), inside one
    span of the output REORDER_SPAN × the run's length each side of an occurrence of the run's rarest word — the words are
    there in another order (a merged stacked header, moved cells). A word the output lacks anywhere is an omission: False."""
    need: dict[str, int] = {}
    for w in run_text.split():
        # S209 E13 (Desjardins, HELD on three runs): the ladder leaves a lone backslash token where a list breaks after a
        # colon (15 in Marker's text, 6 in the analyst's — a whitelisted markup edit re-renders the list); a token with no
        # word character is structure, not a word, and the bag counts words
        if not _WORD_CHAR.search(w):
            continue
        need[w] = need.get(w, 0) + 1
    if not need or any(freq.get(w, 0) < n for w, n in need.items()):
        return False
    rare = min(need, key=lambda w: freq[w])
    span = REORDER_SPAN * len(run_text)
    for off in idx[rare][:REORDER_ANCHOR_CAP]:
        have: dict[str, int] = {}
        for w in out[max(0, off - span): off + span].split():
            if w in need:
                have[w] = have.get(w, 0) + 1
        if all(have.get(w, 0) >= n for w, n in need.items()):
            return True
    return False


def _score_page(page_text: str, output_search: str, idx: dict, freq: dict,
                cjk: bool, fuzzy: bool):
    """-> (page_score|None, runs, n_windows). None score = page not scored (blank/image).
    output_search is space-free when cjk (windows are too), else the finalized stream."""
    if cjk:
        if len(page_text.replace(" ", "")) < PAGE_MIN_WORDS * 2:
            return None, [], 0
    elif len(page_text.split()) < PAGE_MIN_WORDS:
        return None, [], 0
    windows = make_windows(page_text, cjk)
    if not windows:
        return None, [], 0
    failed = []
    for w in windows:
        hit = w in output_search
        if not hit and fuzzy:
            hit = _fuzzy_hit(w, output_search, idx, freq, cjk)
        failed.append(not hit)
    passed = failed.count(False)
    return passed / len(windows), _merge_runs(windows, failed, page=None), len(windows)


# ---------------------------------------------------------------------------
# Tripwires (docs/15 §5).
# ---------------------------------------------------------------------------
# SYM-067 (filed S112, built S114 post-close as J29, signed Rab 2026-09-04): the loop detector
# is TABLE-AWARE. degeneration() used to run on RAW markdown, and a sparse pipe-table grid — a
# single-sentence callout promoted to a 30-row empty table, phantom trailing columns — is BOTH
# crushed-compressible AND an extreme repeated word-trigram ("| | |" hundreds of times): the exact
# signature of a decoder loop, with zero loops in it. It fired the whole `fail` verdict on the
# Damodaran 2025 4e anchor (26 blocks, 0 real). Pipe-table ROWS are blanked before the
# per-paragraph pass (as a whitespace-only line, never an empty one — see _blank_table_rows);
# each row's line terminator is kept, so every `line` in `worst` and
# `md_lines` still address the body as shipped. Measured on the pair that named the symptom
# (docs/53-lead-hunt/scripts/verify_sym067_pair.py, then this function): 2025 4e 26 → 0; the held
# University 4e 25 → 1, and the 1 is a real runaway (line 8776, `{1 - t}` × 441 — SYM-056's
# unterminated array), which MUST stay flagged; the Beer Brain-of-the-Firm anchor (max_trigram
# 2,267) still trips. Declared blind spot, made falsifiable in degeneration_selftest.py D5: a loop
# that emits ONLY table rows is not seen — the repeated-line check never counted `|` rows either
# (docs/15 §9.2). The count of rows blanked rides in the block as `table_rows_stripped` (docs/34:
# a gate that excludes something says how much it excluded).
_TABLE_ROW = re.compile(r"^[ \t]*\|.*\|[ \t]*$")


def _blank_table_rows(markdown: str) -> tuple[str, int]:
    """Replace every markdown pipe-table row with a SINGLE-SPACE line, keeping its terminator, so
    the line count and every newline position are preserved by construction. A space, not an
    empty line: an empty line would manufacture a "\\n\\n" paragraph break where the shipped body
    had none, and a decoder loop interleaved one-to-one with table rows would be split into
    sub-200-char fragments the per-paragraph pass never sees (fleet wf_1e69e60b-b45 lane B,
    2026-09-04; tripwire D11). A whitespace-only line keeps the surrounding prose in ONE
    paragraph exactly as the raw body did, and strip() removes it from the measured text."""
    out, n = [], 0
    for ln in markdown.splitlines(keepends=True):
        body = ln.rstrip("\r\n")
        if _TABLE_ROW.match(body):
            out.append(" " + ln[len(body):])
            n += 1
        else:
            out.append(ln)
    return "".join(out), n


def _degenerate_blocks(markdown: str) -> list[tuple[dict, int]]:
    """The per-paragraph half of degeneration(): every block whose zlib ratio AND repeated
    trigram both cross the priors (docs/15 §9.1–9.2), UNCAPPED, each paired with the 1-based
    line its text ends on (the block spans [block["line"], line_end] on the text as given).
    Shared by degeneration(), which reports the ten worst, and by mask_degenerate_reference()
    (S131), which must mask every one — a cap that hides an eleventh loop from the mask would
    let it back in as loss."""
    found: list[tuple[dict, int]] = []
    pos = 0
    for para in markdown.split("\n\n"):
        # The line of the paragraph's FIRST NON-BLANK character. A blanked table leaves an odd
        # run of newlines that split() hands to the next paragraph as a leading "\n"; counting
        # from `pos` alone would then report the line before the text (off by one).
        lead = len(para) - len(para.lstrip())
        line_no = markdown.count("\n", 0, pos + lead) + 1
        pos += len(para) + 2
        p = para.strip()
        if len(p) < DEGEN_BLOCK_MIN_CHARS:
            continue
        raw = p.encode("utf-8")
        ratio = len(zlib.compress(raw, 6)) / len(raw)
        toks = p.lower().split()
        if len(toks) < 5:                       # CJK / space-free block
            toks = list(re.sub(r"\s", "", p))
        tri = Counter(" ".join(toks[i:i + 3]) for i in range(len(toks) - 2))
        mx = max(tri.values()) if tri else 0
        # AND, not OR (docs/15 §9.2): a loop is BOTH crushed-compressible AND has an extreme
        # repeated word-trigram. Dense tables are compressible too (structural |, ---, <br>)
        # but their words vary → low trigram, so the trigram gate clears them. The old zlib-OR
        # path false-fired on the Cybernetics table-dense book (zlib 0.11/0.15, trigram 28/10).
        if ratio < DEGEN_ZLIB_MAX and mx >= DEGEN_TRIGRAM_MAX:
            found.append(({
                "line": line_no, "chars": len(p), "zlib": round(ratio, 3),
                "max_trigram": mx, "excerpt": " ".join(p.split()[:8]),
            }, line_no + p.count("\n")))
    return found


def mask_degenerate_reference(markdown: str) -> tuple[str, dict]:
    """S131 (Rab signed 2026-09-12): a reference block the audit's OWN degeneration detector
    flags is Marker's disease, not the book, and a body that lacks it is not missing anything.
    The specimen: the Zero to One sidecar carried a 2048-char "# INTERNATIONAL PROPERTY AND
    ROUTE AND ROUTE…" heading Marker looped on (zlib 0.028, trigram 202; the PDF's own text
    holds no "and route" at all), so the body repaired by cutting it read as a 420-word
    omission (survival 0.9848 → fail) while a body that kept it failed on degeneration: no
    repair could pass. This blanks every such block's lines — the same blocks degeneration()
    would find, uncapped, on the same table-blanked text, whose newline positions are
    preserved by construction — BEFORE the near-exact windows are built, and says what it
    masked so the verdict carries its provenance. Blanking glues the block's neighbours in the
    reference stream: a body that KEPT the block loses the windows spanning that seam (a dip
    of a few words, never a run) — and fails on the convert gate's tripwire anyway. The
    repeated-line signal (`repeated_lines`) is NOT masked here: no specimen yet, and a case
    comes before the rule."""
    # CRLF first (fleet wf_c4845e33-681, lane "hostile", 2026-09-12): the paragraph split
    # below is on the literal "\n\n", which a CRLF blank line ("\r\n\r\n") never contains —
    # a CRLF reference would read as ONE paragraph and its loop would go unmasked. The
    # pipeline's sidecars are LF by construction (raw UTF-8 bytes of Marker's body), so this
    # guards the function, not a live path. A reference with nothing to mask is returned
    # byte-identical, CR and all.
    text = markdown.replace("\r\n", "\n")
    blanked, _rows = _blank_table_rows(text)
    blocks = _degenerate_blocks(blanked)
    if not blocks:
        return markdown, {"blocks": [], "words": 0}
    lines = text.split("\n")
    report: list[dict] = []
    words = 0
    for blk, line_end in blocks:
        lo, hi = blk["line"] - 1, min(line_end, len(lines))
        words += sum(len(ln.split()) for ln in lines[lo:hi])
        for i in range(lo, hi):
            lines[i] = ""
        report.append(dict(blk, line_end=line_end))
    return "\n".join(lines), {"blocks": report, "words": words}


def degeneration(markdown: str, strip_table_rows: bool = True) -> dict:
    """Per-paragraph zlib ratio + max repeated trigram (word, or char for CJK blocks),
    plus a repeated-output-line check. Priors from docs/15 §9.1. Table rows are blanked
    first (SYM-067, above); `strip_table_rows=False` is the pre-J29 behaviour, kept only so
    the selftest can prove the gate does work."""
    table_rows_stripped = 0
    if strip_table_rows:
        markdown, table_rows_stripped = _blank_table_rows(markdown)
    worst = [blk for blk, _end in _degenerate_blocks(markdown)]
    flagged = bool(worst)
    # Repeated-line check (docs/15 §9.2): a degeneration loop repeats a line CONTIGUOUSLY
    # (the decoder gets stuck), so measure the longest RUN of consecutive identical non-blank
    # lines — NOT the total count. Legitimate structure repeats but is DISTRIBUTED: section
    # headings (Cybernetics: "#### a. goal of model" once per model) and table rows recur
    # throughout the doc, giving a run of 1. Blanks and table rows never count toward a run.
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
    # md_lines: the widget's damage-map denominator — places each worst-block band at
    # line/md_lines along a book-length track (docs/15 §13).
    # NUM-3: the exemplar list stays capped at 10; the TRUE flagged-block count survives it
    return {"flagged": flagged, "repeated_lines": repeated_lines,
            "md_lines": markdown.count("\n") + 1, "worst": worst[:10],
            "blocks_total": len(worst), "worst_capped_at": 10,
            "table_rows_stripped": table_rows_stripped}


def garbage_rate(output_final: str):
    """Reference-free OCR-junk signal (docs/15 §5, QuPipe-style): fraction of alpha
    tokens (len>=4) with no vowel. Zero-dependency stand-in for dict-hit (wordfreq absent)."""
    toks = re.findall(r"[a-z]{4,}", output_final)
    if not toks:
        return None
    novowel = sum(1 for t in toks if not re.search(r"[aeiou]", t))
    return round(novowel / len(toks), 3)


def reverse_sample(output_final: str, witness_search: str, cjk: bool) -> float | None:
    """Anti-hallucination: sampled OUTPUT windows sought in the witness (docs/15 §5).
    witness_search must be space-free when cjk (output windows are too)."""
    windows = make_windows(output_final, cjk)
    if not windows:
        return None
    rng = random.Random(REVERSE_SEED)
    sample = windows if len(windows) <= REVERSE_SAMPLE_N else rng.sample(windows, REVERSE_SAMPLE_N)
    hit = sum(1 for w in sample if w in witness_search)
    return round(hit / len(sample), 3)


# ---------------------------------------------------------------------------
# LaTeX environment balance - REPORT-ONLY (SYM-056, signed Rab 2026-09-03).
#
# S109 shipped a book carrying 61 unmatched `\begin{array}` opens: the audit scores CONTENT
# and never STRUCTURE, so all 28 affected chunks read `status: passed` while three of them
# ate 49.9 % of the analyst lane on a shape that has no valid completion. Nothing anywhere
# in the pipeline measures environment balance. This counts it and does nothing else: it is
# NOT a tripwire, compute_verdict never reads it, it never touches the markdown, and it can
# never move a verdict - the report-only signature Rab gave it on 2026-09-03.
#
# docs/34: numerator = `\begin` tokens left unmatched; denominator = `\begin` tokens seen;
# conditions = the Marker body exactly as audited, whole (see the fence note below).
#
# WHITESPACE-AWARE BY CONSTRUCTION, and that is the corrected half of SYM-056: the strict
# literal rule `count("\begin{array}")` reads 60 on the Ashby body, but one opener is written
# `\begin` + CRLF + `{array}`, which the literal rule misses while still counting its closer.
# The cross-vendor correction (Codex lane, MSG-CDX-0014, 2026-08-27) measured 127 opens /
# 66 closes / 0 stray closes / 61 unmatched with a whitespace-aware stack, and left a standing
# note: any guard's test must include whitespace-separated TeX commands or it inherits the
# same blind spot. The `\s*` below is that requirement, not decoration.
#
# FENCES AND INLINE CODE ARE NOT SKIPPED - a deliberate choice, written down because the
# opposite is defensible. Two reasons. (1) Marker emits math inside fenced and inline spans
# too, and the shipped SYM-056 specimen is `$$\begin{array}{c*36}$$`, so a fence-skipping
# counter would under-report the very defect this exists to measure. (2) Skipping fences means
# PARSING them, and a single unterminated fence would swallow the rest of the body and hide
# every real unmatched open - the same class of blind spot as the strict-literal rule, bought
# for nothing. A fenced example of BALANCED LaTeX costs nothing: balanced environments are
# never listed, only counted into the denominator.
# ---------------------------------------------------------------------------
_LATEX_ENV = re.compile(r"\\(begin|end)\s*\{([A-Za-z][A-Za-z0-9*]{0,31})\}")


def latex_balance(markdown: str) -> dict:
    """Per-environment `\\begin{X}` / `\\end{X}` balance. Report-only; feeds no verdict.

    Returns, ALWAYS with every key present (an absent key is a silence the reader would have
    to guess at - SYM-057's lesson is that an unmeasurable result must never look like a
    clean one):

        {"checked": True,
         "environments": {env: {"begin": n, "end": m, "unterminated": u,
                                "stray_end": s, "line": first-unmatched-begin | None}},
         "unterminated_total": u_total,      # numerator (docs/34)
         "begins_seen": n_total}             # denominator (docs/34)

    Only UNBALANCED environments are listed; a balanced one still counts into begins_seen. A
    body with no `\\begin` at all reports the honest zero shape - never {} alone, never null.

    Nesting resolves by DEPTH, not by pairing greedily: an `\\end` closes the INNERMOST open
    environment of that name (LIFO), so with an inner pair closing cleanly the reported `line`
    is the OUTER opener. A first-in-first-out pairer returns the same count and the wrong
    line, and the line is the whole value of the field - the highlight a human repairs at
    (error-structure protocol: reason = the env plus its counts, highlight = the line; the
    solution comment belongs to the Repair Bench, which does not read this yet).
    """
    stacks: dict[str, list[int]] = {}          # env -> line numbers of still-open begins
    counts: dict[str, list[int]] = {}          # env -> [begins, ends, stray_ends]
    for m in _LATEX_ENV.finditer(markdown):
        kind, env = m.group(1), m.group(2)
        c = counts.setdefault(env, [0, 0, 0])
        if kind == "begin":
            c[0] += 1
            # Same line convention as degeneration(): 1-based within the body as audited,
            # so `line` and degeneration_detail's `line` share one denominator (md_lines).
            stacks.setdefault(env, []).append(markdown.count("\n", 0, m.start()) + 1)
        else:
            c[1] += 1
            stack = stacks.setdefault(env, [])
            if stack:
                stack.pop()                    # LIFO: close the innermost, never the first
            else:
                c[2] += 1                      # a close with nothing open (Codex: stray close)
    envs: dict[str, dict] = {}
    unterminated_total = 0
    begins_seen = 0
    for env in sorted(counts):
        begins, ends, strays = counts[env]
        begins_seen += begins
        left = stacks.get(env, [])
        unterminated_total += len(left)
        if not left and not strays:
            continue                           # balanced: counted, not listed
        envs[env] = {
            "begin": begins,
            "end": ends,
            "unterminated": len(left),
            "stray_end": strays,               # begin - end + stray_end == unterminated
            "line": left[0] if left else None,
        }
    return {"checked": True, "environments": envs,
            "unterminated_total": unterminated_total, "begins_seen": begins_seen}


# ---------------------------------------------------------------------------
# Stage audits (docs/15 §4/§6/§7).
# ---------------------------------------------------------------------------
def audit_inventions(pages_raw: list[str], blocks: list[dict], kind: str = "fidelity") -> dict:
    """S209 B35 (2026-09-20) — THE AUDIT'S BLIND SIDE, report-only. Survival counts what the output LOST against the
    witness; a re-OCR'd clean page can also INVENT words the layer never had (RBC Q3, Marker's own re-OCR of a born-digital
    report: `TLAC loverage satio`, `last guarter` — 0.25 % of ten pages' words; CIBC, not re-OCR'd, 0 on the same measure).
    Per page from blocks.json (every block page-labelled; the markdown itself carries no page marks): the words Marker's
    blocks carry that the witness page does not, over the page's word count; the witness's words the blocks lack ride
    beside them (the losses, survival's own view). Words = runs of 3+ letters, lower-cased; entities unescaped first
    (`&amp;` is not a word). On the scan lane the witness is the embedded OCR layer, so the number is DISAGREEMENT, not
    invention — `meaning` says which. No verdict reads this key (compute_verdict cannot see it); the threshold is Rab's."""
    from html import unescape
    word_re = re.compile(r"[^\W\d_]{3,}")
    math_re = re.compile(r"(?is)<math[^>]*>.*?</math>")
    cmd_re = re.compile(r"\\[A-Za-z]+")
    by_page: dict[int, list[str]] = {}
    latex_commands = 0
    for b in blocks or []:
        p = b.get("page")
        if p is None:
            continue
        html = b.get("html", "") or ""
        # S209 E12 (Waterloo, a PhD thesis): Marker writes equations as LaTeX inside <math> elements — `\hat`, `\boldsymbol`,
        # `\bmatrix`, `\frac` — words the layer never had and never should (it has the glyphs). 1,810 of 32,843 Marker words
        # read "invented" on 147 pages, every worst page an equation page. The equations come out before the words are
        # counted, and the commands are counted apart as `latex_commands`: the equation is not an invention and not a word.
        for m in math_re.findall(html):
            latex_commands += len(cmd_re.findall(m))
        text = re.sub(r"<[^>]+>", " ", unescape(math_re.sub(" ", html)))
        by_page.setdefault(int(p) + 1, []).extend(w.lower() for w in word_re.findall(text))
    pages: dict[int, dict] = {}
    inv_total = words_total = lost_total = wit_total = measured = 0
    blank_pages = blank_marker_words = 0
    for pnum, raw in enumerate(pages_raw, start=1):
        mw = by_page.get(pnum)
        if not mw:
            continue
        # the layer breaks words at line ends ("amalga-\nmation"); Marker joins them — joined first, so a rejoined word is
        # neither an invention nor a loss (C-31's first run read 1.16 % invented, most of it the layer's own hyphenation)
        lw = [w.lower() for w in word_re.findall(re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", raw or ""))]
        if len(lw) < PAGE_MIN_WORDS:
            # a near-blank witness page (a chart baked into an image) cannot judge inventions: Marker's words there are
            # its OCR of the picture — text the layer never had, a gain if right — not garble (the SEU's p.73: 74 of 77
            # "invented"). Counted apart, never in the ratio, exactly as survival skips such pages.
            blank_pages += 1
            blank_marker_words += len(mw)
            continue
        measured += 1
        ls, ms = set(lw), set(mw)
        invented = [w for w in mw if w not in ls]
        lost = [w for w in lw if w not in ms]
        inv_total += len(invented)
        words_total += len(mw)
        lost_total += len(lost)
        wit_total += len(lw)
        if invented:
            spec = sorted(set(invented), key=lambda w: (-invented.count(w), w))[:6]
            pages[pnum] = {"marker": len(mw), "witness": len(lw), "invented": len(invented), "lost": len(lost), "specimens": spec}
    worst = sorted(pages.items(), key=lambda kv: -kv[1]["invented"] / max(1, kv[1]["marker"]))[:10]
    return {
        "meaning": ("words in Marker's blocks absent from the source's text layer" if kind == "fidelity"
                    else "words in Marker's blocks absent from the embedded OCR layer (disagreement, not invention)"),
        "pages_measured": measured,
        "invented_total": inv_total,
        "marker_words_total": words_total,
        "invented_ratio": round(inv_total / words_total, 5) if words_total else None,
        "lost_total": lost_total,
        "witness_words_total": wit_total,
        "pages_with_inventions": len(pages),
        "pages_witness_blank": blank_pages,            # witness under PAGE_MIN_WORDS: OCR of pictures, not judged
        "blank_marker_words": blank_marker_words,
        "latex_commands": latex_commands,              # S209 E12: equations' commands, counted apart, never inventions
        "worst": [dict(page=p, **v) for p, v in worst],
    }


def audit_convert(pdf_path, markdown: str, lane: str, asset_count: int | None = None, blocks: list | None = None) -> dict:
    kind = "agreement" if lane == "scan" else "fidelity"
    witness_label = "embedded-ocr" if lane == "scan" else "pymupdf"
    pages_raw, embedded_images = extract_witness(pdf_path)
    witness_pages = prepare_witness(pages_raw)
    cjk = is_cjk(" ".join(witness_pages[:8]))
    output_final = prepare_output(markdown)
    # CJK has no word boundaries: match space-free on both sides (windows are space-free too).
    output_search = output_final.replace(" ", "") if cjk else output_final
    idx, freq = _build_index(output_final) if not cjk else ({}, {})

    page_flag = SCAN_PAGE_FLAG if lane == "scan" else CLEAN_PAGE_FLAG
    scored, runs, pages_flagged, surviving = 0, [], [], 0
    weighted_sum, total_windows = 0.0, 0
    for pnum, page in enumerate(witness_pages, start=1):
        score, page_runs, nwin = _score_page(page, output_search, idx, freq, cjk, fuzzy=True)
        if score is None:
            continue
        scored += 1
        weighted_sum += score * nwin
        total_windows += nwin
        if score > 0:
            surviving += 1
        if score < page_flag:
            pages_flagged.append(pnum)
        for r in page_runs:
            r["page"] = pnum
            runs.append(r)
    doc_survival = round(weighted_sum / total_windows, 4) if total_windows else 1.0

    degen = degeneration(markdown)
    block = {
        "witness": witness_label,
        "kind": kind,
        "doc_survival": doc_survival,
        "pages_scored": scored,
        # S144 (audit/verdict-weighs-denominator, Rab's word 2026-09-13): the denominator rides beside the numerator, so a
        # witness that saw 1 page of 465 (Valentine's scan, S142 E1 F5) can no longer print a pass-shaped 1.0 — the
        # verdict reads pages_scored / pages_total (compute_verdict). Blocks written before this key stay as they were.
        "pages_total": len(pages_raw),
        "pages_flagged": pages_flagged,
        # NUM-3 (signed 2026-08-31, SYM-066's repair at the source): the shown list stays
        # capped for payload size, but the TRUE count and the cap ride beside it — "25" can
        # never again masquerade as the count (the night of 2026-08-30 it hid 634).
        "runs": sorted(runs, key=lambda r: -r["words"])[:25],
        "runs_total": len(runs),
        "runs_capped_at": 25,
        "tripwires": {
            "degeneration": degen["flagged"],
            "degeneration_detail": degen,
            "page_coverage": {"with_text": scored, "surviving": surviving},
            "asset_delta": (asset_count - embedded_images) if asset_count is not None else None,
            "embedded_images": embedded_images,
            "reverse_sample": reverse_sample(
                output_final,
                ("".join(witness_pages).replace(" ", "") if cjk else " ".join(witness_pages)),
                cjk),
            "dict_hit": None,                       # wordfreq absent; garbage_rate below
            "garbage_rate": garbage_rate(output_final) if lane == "scan" else None,
        },
        # SYM-056, REPORT-ONLY (signed Rab 2026-09-03): structural balance riding BESIDE the
        # content tripwires and deliberately not among them - compute_verdict cannot see this
        # key and must not. Measured on the RAW markdown, which is what ships; prepare_output
        # would strip the very structure in question.
        "latex_balance": latex_balance(markdown),
        # S209 B35, REPORT-ONLY: the words Marker's blocks carry that the layer does not (inventions; disagreement on the
        # scan lane), per page from blocks.json — riding BESIDE survival, unseen by compute_verdict; None = not measured
        # (no blocks handed in), never 0.
        "inventions": audit_inventions(pages_raw, blocks, kind) if blocks is not None else None,
        # S209 E11, REPORT-ONLY: the bank tables' SHAPE — the source's own table geometry (pymupdf find_tables inside each
        # Marker table box) against Marker's rows and width: columns_lost / rows_lost where the witness's cells agree and its
        # shape is credible, tables_disagree / tables_unread for the rest, the scan lane unread with its reason. Beside
        # survival, unseen by compute_verdict; None = not measured (no blocks handed in), never 0.
        "tables": table_shape.table_shape(pdf_path, blocks, lane) if blocks is not None else None,
        # S209 E13, REPORT-ONLY: CHART TEXT AS TEXT — the words the source's layer carries inside each Marker figure box
        # (a chart's legend, axis labels, data labels) against the words Marker shipped for the figure; a silent figure has
        # layer words and no shipped words (the AI Index: 10,551 layer words inside 479 figures, 680 shipped, 67 silent).
        # Beside survival, unseen by compute_verdict; None = not measured (no blocks handed in); the scan lane unread.
        "figures": figure_text.figure_text(pdf_path, blocks, lane) if blocks is not None else None,
    }
    return block



# J32-A (docs/54-repair-road/README.md §2, signed: Proposal A). The near-exact analyst-stage
# comparison was counting Marker's OWN backslash escapes, punctuation and spacing choices as
# LOSS: qwen3:8b routinely rewrites `\(1960-2023\)` to `(1960-2023)`, or moves a comma, and
# prepare_output alone has no way to tell that from a real drop — measured at ~3.7x over-count
# in windows on the anchor corpus, ~7x on the held University 4e run (docs/54 §2). The ladder
# (text_norm.unescape -> punct_free, applied to BOTH sides before windowing) narrows agreement,
# it can never manufacture it: the same transform runs on ref and out alike, so a real 12-word
# deletion still fails and a run of real omissions still accumulates. `regex_id` names the
# EXACT regex pair this ran with (text_norm._UNESCAPE / _PUNCT) so a future change to either
# is provable as a version bump, not a silent drift in what "near-exact" means.
#
# v2 (verifier GO_AMENDED, 2026-09-05): text_norm._PUNCT changed (`[^\w\s]` -> `[^\w\s\\]`, R5)
# to stop deleting a backslash unconditionally -- see text_norm.py's v2 note. A regex change
# bumps this id per the ticket's own rule.
#
# J44 (S182): the id is the LADDER that ran -- `j32a-v2` (this pair, unchanged) or `j32a-v3`
# (text_norm.prepare_for's escape-first + cite-anchor rungs) -- read from the lever per call
# when the caller does not name one. _REGEX_ID stays as v2's name for readers that import it.
_REGEX_ID = "j32a-v2"


def audit_analyst(marker_markdown: str, analyst_markdown: str, ladder: str | None = None) -> dict:
    """Near-exact containment: the Marker doc IS the reference (docs/15 §6/§9.4). No fuzzy.
    S131 (docs/15 §12.1): blocks of the reference that degeneration() flags are masked first.
    Both sides run the J32-A normalisation ladder (unescape -> punct_free) before windowing;
    containment is tested SPACE-FREE on both the window and the output stream — the CJK path
    was already space-free, this unifies the word path onto the same rule rather than keeping
    two containment tests that happen to agree."""
    # S131: Marker's own degenerate blocks come out of the reference first (see
    # mask_degenerate_reference); `reference_masked` says what left, so a verdict that leaned
    # on the mask can be read as such.
    masked_ref, reference_masked = mask_degenerate_reference(marker_markdown)
    if ladder is None:
        ladder = ladder_lever.read_ladder()  # J44 (S182): the lever, re-read per audit; absent = v2
    ref = punct_free(unescape(prepare_for(masked_ref, ladder)))
    out = punct_free(unescape(prepare_for(analyst_markdown, ladder)))
    normalisation = {"unescape": True, "punct_free": True, "space_free": True,
                     "regex_id": ladder}
    cjk = is_cjk(ref[:4000])
    windows = make_windows(ref, cjk)
    if not windows:
        # SYM-057 (S175, his word 8ca8279b — the restart window): a comparison that never happened is UNREAD, never a
        # flawless 1.0 — the two were byte-identical in every shipped manifest. windows_total 0 says why; compute_verdict
        # and convert_and_ship's fallback branch read None as "not measured" (neither fail nor flag — the verdict's
        # signals are docs/15 §12's two, and an unmeasured stage adds none; a flag for it would be a gate change, his).
        return {"doc_survival": None, "windows_total": 0, "runs": [], "runs_total": 0, "runs_capped_at": 25,
                "normalisation": normalisation, "reference_masked": reference_masked}
    out_flat = space_free(out)
    failed = [space_free(w) not in out_flat for w in windows]
    doc = round(failed.count(False) / len(windows), 4)
    runs = [r for r in _merge_runs(windows, failed, page=None)]
    # SYM-138 (S209 E10; TD Q3 2026 HELD at 0.9994): the analyst merged a STACKED table header — two rows Marker wrote for
    # one header because the source's columns are narrow — into one row, a better table with every word kept, and the
    # windows over the two raw rows read as a 36-word omission that FAILED the document. Each run is re-tested as a bag
    # of words within one span of the output (_reorder): a reordering is marked `reorder` and counted (runs_reorder,
    # words_reorder) — REPORT-ONLY: the verdict still counts the run; the gate is signed (docs/15 §12) and the rescue
    # waits for his word. The CJK path is not re-tested (None: unread, never a negative). The runs walk `failed` left to
    # right exactly as _merge_runs does, so the flags pair with the runs by position.
    if not cjk:
        r_idx, r_freq = _build_index(out)
        flags, i = [], 0
        while i < len(windows):
            if failed[i]:
                j = i
                while j < len(windows) and failed[j]:
                    j += 1
                if j - i >= RUN_MIN_WINDOWS:
                    flags.append(_reorder(" ".join(windows[i:j]), out, r_idx, r_freq))
                i = j
            else:
                i += 1
        assert len(flags) == len(runs), (len(flags), len(runs))
        for r, f in zip(runs, flags):
            r["reorder"] = f
    else:
        for r in runs:
            r["reorder"] = None
    runs_reorder = sum(1 for r in runs if r["reorder"] is True)
    words_reorder = sum(r["words"] for r in runs if r["reorder"] is True)
    # NUM-3, both phases (review M2: repairing only the convert phase left the analyst event
    # ASSERTING that 25 is the total — strictly worse than the bare capped count)
    return {"doc_survival": doc, "windows_total": len(windows),  # SYM-057: the denominator travels with the ratio
            "runs": sorted(runs, key=lambda r: -r["words"])[:25],
            "runs_total": len(runs), "runs_capped_at": 25, "normalisation": normalisation,
            "runs_reorder": runs_reorder, "words_reorder": words_reorder,  # SYM-138: report-only, beside the runs
            "reference_masked": reference_masked}


def compute_verdict(convert_block: dict, analyst_block: dict | None) -> str:
    """The verdict string (every caller's contract); the phase that decided it is verdict_with_phase()'s second value."""
    return verdict_with_phase(convert_block, analyst_block)[0]


def verdict_with_phase(convert_block: dict, analyst_block: dict | None) -> tuple:
    """Verdict per the SIGNED enforcement policy (docs/15 §12, signed 2026-07-20), WITH THE PHASE THAT DECIDED IT.

    S175 (SYM-059/061's converter half; S161 E4's design): the Dock cannot name the deciding phase honestly from its side —
    the thresholds live here — so the writer carries it: ("fail", "analyst") when the analyst near-exact gate fired,
    ("fail", "convert") on degeneration, ("flag", "convert") for every localiser (they all read the convert block, the
    witness-coverage floor included), ("pass", None). The verdict logic below is UNCHANGED — only the tuple is new.

    Two signals — and only two — reach "fail":
      * degeneration — OCR/LLM repetition-loop corruption. Unambiguous and witness-free,
        so it gates on EITHER lane (calibrated zero-FP on the vaulted corpus; the
        Brain-of-the-Firm true positive is the labeled specimen it must catch).
      * analyst near-exact loss — the Marker doc IS a perfect reference, so a drop below
        ANALYST_DOC_FAIL or any run >= ANALYST_RUN_WORDS is a rewrite, not reflow.

    Every OTHER signal (low survival/agreement, page flags, omission runs, garbage rate)
    only LOCALIZES a suspect zone → at most "flag", never "fail" — acceptable books
    measured 0.76-0.96 survival (legitimate reflow), so gating on them would false-fail
    good work and erode the terracotta signal. The verdict is ALWAYS computed; whether a
    "fail" actually parks a bundle is the separate report<->enforce lever
    (convert_and_ship.audit_mode(), default "report")."""
    # Analyst stage first: a perfect reference earns the ruthless near-exact gate.
    if analyst_block is not None:
        a_runs = analyst_block.get("runs", [])
        a_doc = analyst_block.get("doc_survival", 1.0)  # SYM-057: None = not measured (no windows) — it fails nothing
        if ((a_doc is not None and a_doc < ANALYST_DOC_FAIL)
                or any(r["words"] >= ANALYST_RUN_WORDS for r in a_runs)):
            return "fail", "analyst"

    tw = convert_block.get("tripwires", {})
    # Degeneration is corruption regardless of witness quality → fail on either lane.
    if tw.get("degeneration"):
        return "fail", "convert"

    # Remaining signals are report-only LOCALIZERS → "flag" at most (docs/15 §12).
    doc = convert_block.get("doc_survival", 1.0)
    runs = convert_block.get("runs", [])
    if convert_block.get("kind") == "agreement":       # scan lane (agreement witness)
        gr = tw.get("garbage_rate")
        if (convert_block.get("pages_flagged")
                or (gr is not None and gr > SCAN_GARBAGE_FLAG)):
            return "flag", "convert"
    else:                                              # clean lane
        if (doc < CLEAN_DOC_FLAG or convert_block.get("pages_flagged")
                or any(r["words"] >= CLEAN_RUN_WORDS for r in runs)):
            return "flag", "convert"
    # S144 (audit/verdict-weighs-denominator; Rab's word, Desk bf4d5d05 2026-09-13; docs/15 §12.3): a witness that scored
    # under WITNESS_COVERAGE_FLOOR of the book's pages localises nothing — its survival is a number over the pages it saw,
    # not over the book — so the verdict is at most `flag` (a localiser, never a fail: §12's two fail signals stand above).
    # Both counts must exist (audit_convert writes pages_total from S144 on); a block without them keeps its old verdict.
    pages_total = convert_block.get("pages_total")
    pages_scored = convert_block.get("pages_scored")
    if pages_total and pages_scored is not None and pages_scored / pages_total < WITNESS_COVERAGE_FLOOR:
        return "flag", "convert"
    return "pass", None


def fail_phases(convert_block: dict, analyst_block: dict | None) -> list:
    """S188 E6: EVERY phase whose FAIL signal fired, in pipeline order — `["convert"]` on degeneration, `["analyst"]` on the
    near-exact gate, `["convert", "analyst"]` on both, `[]` on a pass or a flag (a flag is a localiser, not a fail).
    `verdict_with_phase` names ONE deciding phase in the signed order (the analyst gate first), so a book whose convert
    phase degenerated AND whose analyst audit fell under the gate read `analyst` alone (Automate the Boring Stuff, S187:
    the loop a bench reader looks for first is the convert phase's). The verdict and the deciding phase are unchanged;
    this is the attribution beside them. The same two signals as the verdict — nothing new fails here."""
    phases = []
    if (convert_block.get("tripwires") or {}).get("degeneration"):
        phases.append("convert")
    if analyst_block is not None:
        a_doc = analyst_block.get("doc_survival", 1.0)
        if ((a_doc is not None and a_doc < ANALYST_DOC_FAIL)
                or any(r["words"] >= ANALYST_RUN_WORDS for r in analyst_block.get("runs", []))):
            phases.append("analyst")
    return phases


def build_fidelity_block(convert_block: dict, analyst_block: dict | None = None) -> dict:
    block = {"version": SCHEMA_VERSION, "convert": convert_block}
    if analyst_block is not None:
        block["analyst"] = analyst_block
    block["verdict"], block["verdict_phase"] = verdict_with_phase(convert_block, analyst_block)  # S175: the phase beside it
    block["verdict_phases"] = fail_phases(convert_block, analyst_block)  # S188 E6: every failing phase, in order
    return block


# ---------------------------------------------------------------------------
# CLI (standalone use / spot checks; the watcher calls the functions directly).
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Survival Audit (docs/15), report-only.")
    ap.add_argument("--pdf", type=Path)
    ap.add_argument("--md", type=Path, required=True)
    ap.add_argument("--lane", choices=["clean", "scan"], default="clean")
    ap.add_argument("--asset-count", type=int)
    ap.add_argument("--analyst-ref", type=Path,
                    help="Marker md to treat --md as the analyst output of (stage 2)")
    args = ap.parse_args()

    md_text = read_text(args.md)
    convert_block = None
    if args.pdf:
        convert_block = audit_convert(args.pdf, md_text, args.lane, args.asset_count)
    analyst_block = None
    if args.analyst_ref:
        analyst_block = audit_analyst(read_text(args.analyst_ref), md_text)
    if convert_block is None and analyst_block is None:
        ap.error("give --pdf (convert stage) and/or --analyst-ref (analyst stage)")
    if convert_block is None:                          # stage-2-only convenience
        convert_block = {"kind": "fidelity", "doc_survival": 1.0, "tripwires": {},
                         "pages_flagged": [], "runs": []}
    print(json.dumps(build_fidelity_block(convert_block, analyst_block), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
