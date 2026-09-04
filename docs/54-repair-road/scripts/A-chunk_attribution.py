"""Lane A — per-chunk attribution (claim 3) + qualitative diff for chunks 23, 78 (claim re
rewordings). Uses the REAL analyst.fence / analyst._chunks / analyst._chunk_hash /
analyst._load_journal (pipeline's own code) against the independently rebuilt Marker
reference, cross-checked against C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl.
Read-only: never calls analyst.process() / _generate / ollama.
"""
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
JOURNAL = r"C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl"
OUT = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/A/chunk_attribution_result.json"


def main():
    files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
    assert len(files) == 7
    marker_ref = "\n\n".join(open(f, encoding="utf-8").read() for f in files)

    fenced, embeds = analyst.fence(marker_ref)
    chunks = analyst._chunks(fenced)
    print("n_chunks (fence+_chunks on rebuilt reference):", len(chunks))

    done = analyst._load_journal(Path(JOURNAL), chunks)
    print("journal entries matched by hash:", len(done))
    print("chunks NOT in journal (never completed / hash mismatch):", len(chunks) - len(done))

    statuses = {}
    for i, rec in done.items():
        statuses[rec.get("status")] = statuses.get(rec.get("status"), 0) + 1
    print("status breakdown of matched journal entries:", statuses)

    # Per-chunk window-failure attribution: treat each chunk's INPUT (fenced) text as its
    # own tiny "book" and its journal OUTPUT text as the "analyst" side, run the same
    # audit_analyst window logic chunk-local (never against the whole doc — this is the
    # attribution step, distinct from claim 1's whole-document mirror).
    per_chunk = []
    total_failed = 0
    total_windows = 0
    for i in range(1, len(chunks) + 1):
        chunk_in = chunks[i - 1]
        rec = done.get(i)
        if rec is None:
            per_chunk.append({"i": i, "status": "missing_from_journal", "failed": None,
                               "windows": None})
            continue
        status = rec.get("status")
        chunk_out = rec.get("text", chunk_in)
        result = fa.audit_analyst(chunk_in, chunk_out)
        # audit_analyst returns doc_survival=1.0, runs_total=0 with empty windows when the
        # chunk has < WINDOW_MIN_WORDS words after prep; treat that as 0/0.
        ref_prepped = fa.prepare_output(chunk_in)
        cjk = fa.is_cjk(ref_prepped[:4000])
        windows = fa.make_windows(ref_prepped, cjk)
        n_windows = len(windows)
        n_failed = n_windows - round(result["doc_survival"] * n_windows) if n_windows else 0
        # exact count instead of derived-from-rounded doc_survival:
        out_prepped = fa.prepare_output(chunk_out)
        out_search = out_prepped.replace(" ", "") if cjk else out_prepped
        n_failed_exact = sum(1 for w in windows if w not in out_search)
        per_chunk.append({"i": i, "status": status, "failed": n_failed_exact,
                           "windows": n_windows})
        total_failed += n_failed_exact
        total_windows += n_windows

    chunks_with_loss = [c for c in per_chunk if c.get("failed")]
    chunks_with_loss_sorted = sorted(chunks_with_loss, key=lambda c: -c["failed"])

    # top-80%-of-loss count
    cum = 0
    n_for_80 = None
    for idx, c in enumerate(chunks_with_loss_sorted, 1):
        cum += c["failed"]
        if n_for_80 is None and total_failed and cum / total_failed >= 0.80:
            n_for_80 = idx
            break

    rejected_chunk_failed = sum(c["failed"] for c in per_chunk if c["status"] == "rejected")

    # front matter mention counts (figure N.N / table N.N) on marker ref vs analyst output
    analyst_md = open(
        r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md",
        encoding="utf-8").read()
    import re
    fig_marker = len(re.findall(r"figure\s+\d+\.\d+", marker_ref, re.IGNORECASE))
    fig_analyst = len(re.findall(r"figure\s+\d+\.\d+", analyst_md, re.IGNORECASE))
    tab_marker = len(re.findall(r"table\s+\d+\.\d+", marker_ref, re.IGNORECASE))
    tab_analyst = len(re.findall(r"table\s+\d+\.\d+", analyst_md, re.IGNORECASE))

    report = {
        "n_chunks_rebuilt": len(chunks),
        "n_journal_matched": len(done),
        "status_breakdown": statuses,
        "sum_per_chunk_failed_windows": total_failed,
        "sum_per_chunk_windows": total_windows,
        "n_chunks_with_any_loss": len(chunks_with_loss),
        "n_chunks_needed_for_80pct_of_loss": n_for_80,
        "top20_chunks_by_loss": chunks_with_loss_sorted[:20],
        "rejected_chunks_count": statuses.get("rejected", 0),
        "rejected_chunks_total_failed_windows": rejected_chunk_failed,
        "figure_mentions_marker": fig_marker,
        "figure_mentions_analyst": fig_analyst,
        "table_mentions_marker": tab_marker,
        "table_mentions_analyst": tab_analyst,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "top20_chunks_by_loss"}, indent=2))
    print("top20:")
    print(json.dumps(report["top20_chunks_by_loss"], indent=2))


if __name__ == "__main__":
    main()
