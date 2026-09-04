import glob
import json
import sys

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import analyst  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
JOURNAL = r"C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl"

files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
marker_ref = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
fenced, embeds = analyst.fence(marker_ref)
chunks = analyst._chunks(fenced)
print("n_chunks:", len(chunks))

hashes = {analyst._chunk_hash(c): i for i, c in enumerate(chunks, 1)}

lines = [ln for ln in open(JOURNAL, encoding="utf-8").read().splitlines() if ln.strip()]
recs = [json.loads(ln) for ln in lines]
print("raw journal lines:", len(recs))

matched = 0
mismatched_same_i = 0
matched_diff_i = 0
unmatched_entirely = 0
status_count = {}
for rec in recs:
    i = rec["i"]
    h = rec["hash"]
    status_count[rec.get("status")] = status_count.get(rec.get("status"), 0) + 1
    if 1 <= i <= len(chunks) and analyst._chunk_hash(chunks[i - 1]) == h:
        matched += 1
    elif h in hashes:
        matched_diff_i += 1
    elif 1 <= i <= len(chunks):
        mismatched_same_i += 1
    else:
        unmatched_entirely += 1

print("status_count (raw journal):", status_count)
print("matched (same i, same hash):", matched)
print("hash exists but at different i:", matched_diff_i)
print("i in range but hash differs, hash not found anywhere:", mismatched_same_i)
print("i out of range (>957 or <1):", unmatched_entirely)

# sample: for i=1, compare journal hash vs my chunk[0] hash and length
for i in (1, 2, 641, 646, 647):
    rec = next((r for r in recs if r["i"] == i), None)
    mine_hash = analyst._chunk_hash(chunks[i - 1]) if i <= len(chunks) else None
    print(f"i={i}: journal_hash={rec['hash'] if rec else None} mine_hash={mine_hash} "
          f"journal_text_len={len(rec['text']) if rec else None} "
          f"mine_chunk_len={len(chunks[i-1]) if i <= len(chunks) else None}")
