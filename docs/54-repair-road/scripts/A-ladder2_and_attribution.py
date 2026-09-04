"""Lane A — second, independent pass at claim (2)/(3): reproduces the BUILDER'S ACTUAL
METHOD for the per-chunk attribution (unescape + space-free ONLY, positional first-5-word
location against the shipped analyst.md, chunk boundaries from analyst.fence/_chunks on the
rebuilt reference) -- but with an OWN unescape regex (not copied from univ4e_chunks.py's
ESC pattern) and reporting what the method silently drops (unlocated failing windows).
Read-only; never touches the journal for output text (journal used only for status lookup,
same role the builder gave it).
"""
import bisect
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
ANALYST_MD = r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md"
JOURNAL_DIR = r"C:/Users/Bndit/ml/library/.analyst-work"
OUT = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/verify-tickets/A/ladder2_result.json"

# OWN unescape regex (different in shape from univ4e_chunks.py's ESC -- that one only strips
# backslash before a fixed whitelist of punctuation; mine strips backslash before ANY single
# character, same as ladder.py's step-1). Kept as its own function so this file does not import
# anything from the builder's scripts, only from the pipeline's own analyst.py/fidelity_audit.py.
def unescape(t: str) -> str:
    return re.sub(r"\\(.)", r"\1", t)


def main():
    files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
    marker = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
    held = open(ANALYST_MD, encoding="utf-8").read()

    fenced, embeds = analyst.fence(marker)
    chunks = analyst._chunks(fenced)
    print("n_chunks:", len(chunks), "(manifest: resumed 641 + generated 316 = 957)")

    journal = {}
    for d in Path(JOURNAL_DIR).iterdir():
        f = d / "chunks.jsonl"
        if f.exists():
            recs = analyst._load_journal(f, chunks)
            print(f"journal {d.name}: {len(recs)} records hash-validate against these chunks")
            journal.update(recs)

    # unescape + space-free only (matches the specific rung the attribution is measured at;
    # NOTE: this SKIPS the punctuation-free rung that sits between them in the ticket's own
    # 3-step ladder text -- flagged as a finding, not silently normalized away here)
    ref = fa.prepare_output(unescape(marker))
    out = fa.prepare_output(unescape(held))
    out_ns = out.replace(" ", "")
    windows = fa.make_windows(ref, False)
    still = [w for w in windows if w.replace(" ", "") not in out_ns]
    print(f"still-failing windows (unescape+space-free, own regex): {len(still)} of {len(windows)}")

    low = fenced.lower()
    starts = [0]
    for c in chunks[:-1]:
        starts.append(starts[-1] + len(c))

    per_chunk = Counter()
    words_chunk = Counter()
    located = 0
    missed = 0
    pos = 0
    for w in still:
        key = " ".join(w.split()[:5])
        k = low.find(key, max(0, pos - 20000))
        if k < 0:
            k = low.find(key)
        if k < 0:
            missed += 1
            continue
        located += 1
        pos = k
        i = bisect.bisect_right(starts, k)
        per_chunk[i] += 1
        words_chunk[i] += len(w.split())

    print(f"windows located: {located} | not located (dropped from attribution): {missed} "
          f"({round(100*missed/len(still),1)}% of still-failing windows)")

    tot = sum(per_chunk.values())
    cum, n80 = 0, 0
    for i, n in per_chunk.most_common():
        cum += n
        n80 += 1
        if cum >= 0.8 * tot:
            break
    print(f"chunks carrying any (located) loss: {len(per_chunk)} of {len(chunks)}; "
          f"{n80} chunks carry >=80% of the LOCATED loss ({tot} windows, not {len(still)})")

    rejected_loss = sum(per_chunk[i] for i, r in journal.items() if r.get("status") == "rejected")
    n_rejected_in_journal = sum(1 for r in journal.values() if r.get("status") == "rejected")
    print(f"journal-known rejected chunks: {n_rejected_in_journal} of {len(journal)} validated "
          f"records; located loss windows falling in a rejected chunk: {rejected_loss}")

    # chunks 23 and 78 explicit
    for i in (23, 78):
        print(f"chunk {i}: located_loss_windows={per_chunk.get(i)} words={words_chunk.get(i)} "
              f"journal_status={journal.get(i, {}).get('status', 'no journal record')}")

    report = {
        "n_chunks": len(chunks),
        "journal_validated_records": len(journal),
        "still_failing_windows_unescape_spacefree": len(still),
        "windows_located": located,
        "windows_not_located": missed,
        "pct_not_located": round(100 * missed / len(still), 1) if still else None,
        "chunks_with_located_loss": len(per_chunk),
        "n_chunks_for_80pct_of_located_loss": n80,
        "total_located_loss_windows": tot,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
