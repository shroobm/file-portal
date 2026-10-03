"""WHAT THIS FILE DOES: a one-off check script (run directly; unescape() is its one helper). It rebuilds the
Marker reference from slice files, prints which of the first 15 analyst chunks look like front matter, finds the
windows still failing after unescape + space-free, charges each to a chunk by position, and prints how much of
the located loss falls in chunks 1-15. Reads the slice dir and the held .md; writes nothing. Run by hand; nothing
imports it.

Check claim (6): "the losses concentrate in the front matter's list of figures."
Front matter (title page / TOC / list of figures & tables) sits in the first few chunks of a
957-chunk book. If losses concentrated there, the top-loss chunks would cluster at low chunk
indices. Reuses the ladder2 positional attribution (own unescape+space-free regex).
"""
import bisect
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

SLICE_DIR = Path(r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker")
ANALYST_MD = Path(r"C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e/Investment Valuation, University Edition _ Tools and -- Aswath Damodaran -- Four.md")


# -- helper and inputs --
def unescape(t):
    """Remove a backslash before any single character in t. Returns the new str (pure)."""
    return re.sub(r"\\(.)", r"\1", t)


marker = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(SLICE_DIR.glob("slice-*.md")))
held = ANALYST_MD.read_text(encoding="utf-8")

fenced, embeds = analyst.fence(marker)
chunks = analyst._chunks(fenced)

# where is the "list of figures" / "list of tables" front matter, chunk-index-wise?
low_chunks_text = [c.lower() for c in chunks[:15]]
for idx, c in enumerate(low_chunks_text, 1):
    if "list of figures" in c or "list of tables" in c or "contents" in c:
        print(f"chunk {idx} contains front-matter marker (contents/list of figures/tables); "
              f"first 120 chars: {re.sub(chr(10), ' ', chunks[idx-1][:120])!r}")

ref = fa.prepare_output(unescape(marker))
out = fa.prepare_output(unescape(held))
out_ns = out.replace(" ", "")
windows = fa.make_windows(ref, False)
still = [w for w in windows if w.replace(" ", "") not in out_ns]

low = fenced.lower()
starts = [0]
for c in chunks[:-1]:
    starts.append(starts[-1] + len(c))

# locate each failing window by its first 5 words (searching forward from the last hit, then from 0)
# and count it against the chunk that contains that position
per_chunk = Counter()
pos = 0
for w in still:
    key = " ".join(w.split()[:5])
    k = low.find(key, max(0, pos - 20000))
    if k < 0:
        k = low.find(key)
    if k < 0:
        continue
    pos = k
    i = bisect.bisect_right(starts, k)
    per_chunk[i] += 1

tot = sum(per_chunk.values())
front = sum(n for i, n in per_chunk.items() if i <= 15)
print(f"total located loss windows: {tot}")
print(f"loss windows in chunks 1-15 (front matter zone): {front} "
      f"({round(100*front/tot,1)}% of located loss)")
print(f"chunks 1-15 individual loss counts: {[per_chunk.get(i,0) for i in range(1,16)]}")
print(f"median chunk index of a loss window (by count): "
      f"{sorted((i for i,n in per_chunk.items() for _ in range(n)))[len(still)//2] if per_chunk else None}")
top10 = per_chunk.most_common(10)
print("top10 loss chunks by index:", top10)
