"""Qualitative proof for chunks 23 and 78: diff the journal's recorded OUTPUT ('text' field,
what the run assembled) against the INPUT chunk (from analyst.fence + analyst._chunks on the
rebuilt reference), word by word, via difflib. Only meaningful where the journal record's hash
validates against this rebuilt chunk (analyst._load_journal does this check already)."""
import difflib
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/windows-converter")
import analyst  # noqa: E402

SLICE_DIR = r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker"
JOURNAL = r"C:/Users/Bndit/ml/library/.analyst-work/d58db211c41b0e17/chunks.jsonl"

files = sorted(glob.glob(SLICE_DIR + "/slice-*.md"))
marker_ref = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
fenced, embeds = analyst.fence(marker_ref)
chunks = analyst._chunks(fenced)
done = analyst._load_journal(Path(JOURNAL), chunks)

for idx in (23, 78):
    rec = done.get(idx)
    print(f"\n===== chunk {idx} =====")
    if rec is None:
        print("NOT in journal (hash mismatch or absent) -- cannot diff; input length was",
              len(chunks[idx - 1]))
        continue
    chunk_in = chunks[idx - 1]
    chunk_out = rec["text"]
    print(f"journal status: {rec.get('status')}  input_chars={len(chunk_in)} output_chars={len(chunk_out)}")
    win = chunk_in.split()
    wout = chunk_out.split()
    sm = difflib.SequenceMatcher(None, win, wout, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    print(f"word-level diff ops (non-equal): {len(ops)}")
    shown = 0
    for tag, i1, i2, j1, j2 in ops:
        if shown >= 6:
            break
        a = " ".join(win[max(0, i1 - 4):i2 + 4])
        b = " ".join(wout[max(0, j1 - 4):j2 + 4])
        print(f"  [{tag}] IN:  ...{a}...")
        print(f"        OUT: ...{b}...")
        shown += 1
