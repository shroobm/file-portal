"""Lane A — independent normalisation ladder (claim 2), own regexes, not the builder's script.

Steps, cumulative:
  0 baseline   = fa.prepare_output on both sides (this reproduces claim 1: 0.9402 / 404 runs)
  1 unescape   = strip a backslash before any single character (re.sub(r'\\(.)', r'\1', .))
                 applied AFTER prepare_output on both ref and out (backslashes survive
                 prepare_output's _strip_markdown, which only strips * _ ~ `)
  2 +punct-free = additionally drop every non-alphanumeric, non-space character (own regex,
                 [^\w\s], applied to both sides after unescape) -- collapses whitespace after
  3 +space-free = additionally, for the CONTAINMENT CHECK ONLY (not for window construction --
                 windows stay the same word-split 12-word windows as step 2, so "words" stays
                 a meaningful unit and run lengths stay comparable), strip ALL whitespace from
                 both the window and the output search stream before testing containment.

At every step: doc_survival, failed count, runs_total (via fa._merge_runs, RUN_MIN_WINDOWS=2),
max run (in words).
"""
import glob
import json
import re
import sys

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
ANALYST_MD = r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md"
OUT = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/A/ladder_result.json"

_WS = re.compile(r"\s+")


def unescape(t: str) -> str:
    return re.sub(r"\\(.)", r"\1", t)


def punct_free(t: str) -> str:
    t = re.sub(r"[^\w\s]", "", t, flags=re.UNICODE)
    return _WS.sub(" ", t).strip()


def score(ref_text: str, out_text: str, space_free: bool):
    """ref_text/out_text already normalized per-step. Windows built from ref_text
    (word split, 12-word non-overlapping, min 6 for tail -- same constants as fa)."""
    words = ref_text.split()
    windows = []
    for i in range(0, len(words), fa.WINDOW_WORDS):
        chunk = words[i:i + fa.WINDOW_WORDS]
        if len(chunk) >= fa.WINDOW_MIN_WORDS:
            windows.append(" ".join(chunk))
    if space_free:
        search = out_text.replace(" ", "")
        failed = [w.replace(" ", "") not in search for w in windows]
    else:
        search = out_text
        failed = [w not in search for w in windows]
    n_ok = failed.count(False)
    doc_survival = round(n_ok / len(windows), 4)
    runs = fa._merge_runs(windows, failed, page=None)
    max_run = max((r["words"] for r in runs), default=0)
    return {
        "windows_total": len(windows),
        "failed": failed.count(True),
        "doc_survival": doc_survival,
        "runs_total": len(runs),
        "max_run_words": max_run,
    }


def main():
    files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
    assert len(files) == 7
    marker_ref_raw = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
    analyst_raw = open(ANALYST_MD, encoding="utf-8").read()

    # step 0: baseline (fa.prepare_output on both)
    ref0 = fa.prepare_output(marker_ref_raw)
    out0 = fa.prepare_output(analyst_raw)
    s0 = score(ref0, out0, space_free=False)

    # step 1: +unescape
    ref1 = unescape(ref0)
    out1 = unescape(out0)
    s1 = score(ref1, out1, space_free=False)

    # step 2: +punctuation-free
    ref2 = punct_free(ref1)
    out2 = punct_free(out1)
    s2 = score(ref2, out2, space_free=False)

    # step 3: +space-free (containment only; windows still from ref2's word split)
    s3 = score(ref2, out2, space_free=True)

    report = {
        "0_baseline": s0,
        "1_unescape": s1,
        "2_punct_free": s2,
        "3_space_free": s3,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
