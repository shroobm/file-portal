"""WHAT THIS FILE DOES: a one-off reader (run directly, no arguments). It loads the converter's ledger file
(conversion-ledger.jsonl in the ml library folder, path hard-coded), prints the row count and the first
row's keys, then one line per row: lane, pages, cost_s, s_per_page, peak_mib and the source name.
Read-only; stdout only; no callers.
"""
import json
from pathlib import Path

# one JSON object per non-blank line
p = Path(r"C:\Users\Bndit\ml\library\conversion-ledger.jsonl")
rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
print("ledger rows:", len(rows))
if rows:
    print("keys:", sorted(rows[0].keys()))
for r in rows:
    src = str(r.get("source", ""))[:44]
    print(" | ".join(str(r.get(k)) for k in
                     ("lane", "pages", "cost_s", "s_per_page", "peak_mib")) + " | " + src)
