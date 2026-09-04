"""Charge each analyst-stage loss to the chunk that produced it. Re-chunk the rebuilt Marker text with
the analyst's own fence + _chunks, map every still-failing window (after unescape + space-free) to its
chunk, and read the chunk's journal status where the journal has it. Read-only."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa  # noqa: E402
import analyst  # noqa: E402

SP = Path(__file__).parent
HELD = Path("C:/Users/Bndit/ml/library/held/14c66834bdfeaa2e")
marker = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((SP / "univ4e-marker").glob("slice-*.md")))
held = next(HELD.glob("*.md")).read_text(encoding="utf-8")
ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|<>~])")
un = lambda t: ESC.sub(r"\1", t)  # noqa: E731

fenced, embeds = analyst.fence(marker)
chunks = analyst._chunks(fenced)
print("chunks re-cut from the rebuilt Marker text:", len(chunks), "| manifest: resumed 641 + generated 316 = 957")
journal = {}
jp = Path("C:/Users/Bndit/ml/library/.analyst-work")
for d in jp.iterdir():
    f = d / "chunks.jsonl"
    if f.exists():
        recs = analyst._load_journal(f, chunks)
        print(f"journal {d.name}: {len(recs)} records validate against these chunks (hash match)")
        journal.update(recs)

# still-failing windows after unescape + space-free
ref = fa.prepare_output(un(marker))
out_ns = fa.prepare_output(un(held)).replace(" ", "")
windows = fa.make_windows(ref, False)
still = [w for w in windows if w.replace(" ", "") not in out_ns]
print("still-failing windows:", len(still), "of", len(windows))

# map each window to a chunk: locate its first 5 words in the lowercased fenced text
low = fenced.lower()
starts = [0]
for c in chunks[:-1]:
    starts.append(starts[-1] + len(c))
import bisect
per_chunk = Counter()
words_chunk = Counter()
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
    pos = k
    i = bisect.bisect_right(starts, k)  # 1-based chunk index
    per_chunk[i] += 1
    words_chunk[i] += len(w.split())
print("windows located:", sum(per_chunk.values()), "| not located:", missed)
tot = sum(per_chunk.values())
cum, n80 = 0, 0
for i, n in per_chunk.most_common():
    cum += n
    n80 += 1
    if cum >= 0.8 * tot:
        break
print(f"chunks carrying any loss: {len(per_chunk)} of {len(chunks)}; {n80} chunks carry 80% of it")
print("\ntop chunks by lost windows:")
for i, n in per_chunk.most_common(15):
    st = journal.get(i, {}).get("status", "no journal rec")
    head = re.sub(r"\s+", " ", chunks[i - 1][:90])
    print(f"  chunk {i:4d}  windows {n:4d}  words {words_chunk[i]:5d}  journal {st:14s}  | {head}")
rej = sum(1 for r in journal.values() if r.get("status") == "rejected")
print(f"\njournal: {len(journal)} validated records, {rej} rejected; loss in rejected chunks: "
      f"{sum(per_chunk[i] for i, r in journal.items() if r.get('status') == 'rejected')} windows")
json.dump({"chunks": len(chunks), "still": len(still), "per_chunk": dict(per_chunk), "words": dict(words_chunk),
           "journal_records": len(journal)}, open(SP / "univ4e_chunks.json", "w", encoding="utf-8"), indent=1)
