"""windows-converter/fidelity_audit.py — The Survival Audit (docs/15).

Measures how much of a source PDF survives into the Marker markdown (convert stage) and
how much of the Marker markdown survives the qwen formatting pass (analyst stage), using
window-survival containment against an ephemeral pymupdf witness. Deterministic, CPU-only,
report-only. See docs/15 for the design and the CLOSED decisions — do not redesign here.

Public API (imported by convert_and_ship.py, all crash-wrapped by the caller):
  audit_convert(pdf_path, markdown, lane, asset_count=None) -> dict   # the "convert" sub-block
  audit_analyst(marker_markdown, analyst_markdown)          -> dict   # the "analyst" sub-block
  compute_verdict(convert_block, analyst_block)             -> str    # "pass"|"flag"|"fail"
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
import unicodedata
import zlib
from collections import Counter
from pathlib import Path

import pymupdf
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Constants. Thresholds calibrated over the vaulted corpus (docs/15 §9.1). Per the
# SIGNED enforcement policy (docs/15 §12, 2026-07-20): degeneration + analyst near-exact
# are the only gates (compute_verdict → "fail"); survival/agreement, page flags, runs,
# and garbage rate stay report-only LOCALIZERS (→ "flag"). Whether a "fail" parks a
# bundle is the separate report<->enforce lever (convert_and_ship, default "report").
# ---------------------------------------------------------------------------
SCHEMA_VERSION = 1

WINDOW_WORDS = 12          # non-overlapping window size (word path)
WINDOW_MIN_WORDS = 6       # keep a short final window if at least this many words
CJK_WINDOW_CHARS = 24      # char-n-gram window for CJK (no word boundaries)
CJK_WINDOW_MIN = 12
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

_CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ가-힯]")
_QUOTES = str.maketrans({
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "–": "-", "—": "-", "‐": "-", "‑": "-", "«": '"', "»": '"',
})
_DEHYPHEN = re.compile(r"(\w)-\n(\w)")
_WS = re.compile(r"\s+")


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


# ---------------------------------------------------------------------------
# Normalization (docs/15 §3). Steps 1-3 common; step 4 output-only markdown strip;
# step 5 witness-only repeated-line strip (cross-page, handled in prepare_witness);
# steps 6-7 casefold + whitespace collapse in _finalize.
# ---------------------------------------------------------------------------
def _common(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_QUOTES)
    text = _DEHYPHEN.sub(r"\1\2", text)
    return text


def _finalize(text: str) -> str:
    return _WS.sub(" ", text.casefold()).strip()


def _strip_markdown(t: str) -> str:
    t = re.sub(r"!\[\[[^\]]*\]\]", " ", t)                 # ![[assets/img]] embeds
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)            # ![alt](url) images
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)              # [[wikilink]] -> inner
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)         # [text](url) -> text
    t = re.sub(r"<[^>\n]+>", " ", t)                       # html tags
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", " ", t)           # headings
    t = re.sub(r"(?m)^\s*>\s?", " ", t)                    # blockquote markers
    t = re.sub(r"(?m)^\s*`{3,}.*$", " ", t)                # fenced-code marker lines
    t = re.sub(r"(?m)^\s*\|?[\s:|-]{3,}\|?\s*$", " ", t)   # table separator rows
    t = t.replace("|", " ")                                # table pipes
    t = re.sub(r"[*_~`]", "", t)                           # emphasis / inline-code markers
    return t


def prepare_output(markdown: str) -> str:
    return _finalize(_strip_markdown(_common(markdown)))


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
def is_cjk(text: str) -> bool:
    sample = re.sub(r"\s", "", text)[:4000]
    if not sample:
        return False
    return len(_CJK.findall(sample)) / len(sample) > 0.3


def make_windows(text: str, cjk: bool) -> list[str]:
    if cjk:
        s = text.replace(" ", "")
        out = [s[i:i + CJK_WINDOW_CHARS] for i in range(0, len(s), CJK_WINDOW_CHARS)]
        return [w for w in out if len(w) >= CJK_WINDOW_MIN]
    words = text.split()
    out = []
    for i in range(0, len(words), WINDOW_WORDS):
        chunk = words[i:i + WINDOW_WORDS]
        if len(chunk) >= WINDOW_MIN_WORDS:
            out.append(" ".join(chunk))
    return out


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


def _merge_runs(windows: list[str], failed: list[bool], page) -> list[dict]:
    runs, i = [], 0
    while i < len(windows):
        if failed[i]:
            j = i
            while j < len(windows) and failed[j]:
                j += 1
            if j - i >= RUN_MIN_WINDOWS:
                span = windows[i:j]
                words = sum(len(w.split()) for w in span)
                runs.append({
                    "page": page,
                    "words": words,
                    "excerpt": " ".join(span[0].split()[:10]),
                })
            i = j
        else:
            i += 1
    return runs


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


def degeneration(markdown: str, strip_table_rows: bool = True) -> dict:
    """Per-paragraph zlib ratio + max repeated trigram (word, or char for CJK blocks),
    plus a repeated-output-line check. Priors from docs/15 §9.1. Table rows are blanked
    first (SYM-067, above); `strip_table_rows=False` is the pre-J29 behaviour, kept only so
    the selftest can prove the gate does work."""
    table_rows_stripped = 0
    if strip_table_rows:
        markdown, table_rows_stripped = _blank_table_rows(markdown)
    flagged = False
    worst = []
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
            flagged = True
            worst.append({
                "line": line_no, "chars": len(p), "zlib": round(ratio, 3),
                "max_trigram": mx, "excerpt": " ".join(p.split()[:8]),
            })
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
def audit_convert(pdf_path, markdown: str, lane: str, asset_count: int | None = None) -> dict:
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
    }
    return block


def audit_analyst(marker_markdown: str, analyst_markdown: str) -> dict:
    """Near-exact containment: the Marker doc IS the reference (docs/15 §6). No fuzzy."""
    ref = prepare_output(marker_markdown)
    out = prepare_output(analyst_markdown)
    cjk = is_cjk(ref[:4000])
    out_search = out.replace(" ", "") if cjk else out
    windows = make_windows(ref, cjk)
    if not windows:
        return {"doc_survival": 1.0, "runs": [], "runs_total": 0, "runs_capped_at": 25}
    failed = [w not in out_search for w in windows]
    doc = round(failed.count(False) / len(windows), 4)
    runs = [r for r in _merge_runs(windows, failed, page=None)]
    # NUM-3, both phases (review M2: repairing only the convert phase left the analyst event
    # ASSERTING that 25 is the total — strictly worse than the bare capped count)
    return {"doc_survival": doc, "runs": sorted(runs, key=lambda r: -r["words"])[:25],
            "runs_total": len(runs), "runs_capped_at": 25}


def compute_verdict(convert_block: dict, analyst_block: dict | None) -> str:
    """Verdict per the SIGNED enforcement policy (docs/15 §12, signed 2026-07-20).

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
        if (analyst_block.get("doc_survival", 1.0) < ANALYST_DOC_FAIL
                or any(r["words"] >= ANALYST_RUN_WORDS for r in a_runs)):
            return "fail"

    tw = convert_block.get("tripwires", {})
    # Degeneration is corruption regardless of witness quality → fail on either lane.
    if tw.get("degeneration"):
        return "fail"

    # Remaining signals are report-only LOCALIZERS → "flag" at most (docs/15 §12).
    doc = convert_block.get("doc_survival", 1.0)
    runs = convert_block.get("runs", [])
    if convert_block.get("kind") == "agreement":       # scan lane (agreement witness)
        gr = tw.get("garbage_rate")
        if (convert_block.get("pages_flagged")
                or (gr is not None and gr > SCAN_GARBAGE_FLAG)):
            return "flag"
    else:                                              # clean lane
        if (doc < CLEAN_DOC_FLAG or convert_block.get("pages_flagged")
                or any(r["words"] >= CLEAN_RUN_WORDS for r in runs)):
            return "flag"
    return "pass"


def build_fidelity_block(convert_block: dict, analyst_block: dict | None = None) -> dict:
    block = {"version": SCHEMA_VERSION, "convert": convert_block}
    if analyst_block is not None:
        block["analyst"] = analyst_block
    block["verdict"] = compute_verdict(convert_block, analyst_block)
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
