import re, json, sys

with open("table5_raw.txt", encoding="utf-8") as f:
    raw_lines = [l.rstrip("\n") for l in f]

NOISE_EXACT = {
    "Structure Type", "Children", "Parents", "Occ.",
    "Table 5 (continued)",
    "Table 5 — Parent-child relationships between the PDF 1.7 elements and PDF 2.0 elements",
    "© ISO 2023 – All rights reserved\t",
    "© ISO 2023 – All rights reserved",
    "ISO/TS 32005:2023(E)",
    "Sold by the PDF Association to Rabiullah Lotfullah  20978 | September 2, 2026 |",
    "Single user only, copying and networking prohibited.",
    "﻿",
    "c",  # stray OCR artifact observed twice mid-sequence (lines ~3794, ~4929 of table5_raw.txt)
}

OCC_SET = {"0..n", "1..n", "0..1", "1", "∅*", "‡", "[a]", "[b]"}

tokens = []
token_src_line = []  # 1-based line number in table5_raw.txt, for traceability
dropped_digit_lines = []

for i, l in enumerate(raw_lines, start=1):
    s = l.strip()
    if s == "":
        continue
    if re.match(r"^-{5,} PAGE \d+ -{5,}$", s):
        continue
    if s in NOISE_EXACT:
        continue
    if re.match(r"^\d+$", s) and s != "1":
        dropped_digit_lines.append((i, s))
        continue
    tokens.append(s)
    token_src_line.append(i)

print(f"Total data tokens after noise filtering: {len(tokens)}", file=sys.stderr)
print(f"Dropped bare page-number digit lines: {len(dropped_digit_lines)}", file=sys.stderr)

rows = []
pos = 0
n_tok = len(tokens)
errors = []

while pos < n_tok:
    header = tokens[pos]
    header_line = token_src_line[pos]
    if header in OCC_SET:
        errors.append((pos, token_src_line[pos], f"Expected row header (type name), got OCC token {header!r}"))
        pos += 1
        continue
    pos += 1

    children_occ = []
    while pos < n_tok and tokens[pos] in OCC_SET:
        children_occ.append(tokens[pos])
        pos += 1
    n = len(children_occ)
    children_types = tokens[pos:pos+n]
    child_lines = token_src_line[pos:pos+n]
    pos += n

    parents_occ = []
    while pos < n_tok and tokens[pos] in OCC_SET:
        parents_occ.append(tokens[pos])
        pos += 1
    m = len(parents_occ)
    parents_types = tokens[pos:pos+m]
    parent_lines = token_src_line[pos:pos+m]
    pos += m

    rows.append({
        "header": header,
        "header_line": header_line,
        "children": list(zip(children_types, children_occ, child_lines)),
        "parents": list(zip(parents_types, parents_occ, parent_lines)),
    })

print(f"Parsed {len(rows)} row-blocks", file=sys.stderr)
print(f"Parse errors: {len(errors)}", file=sys.stderr)
for e in errors:
    print("  ERROR:", e, file=sys.stderr)

# Sanity: list row headers in order with line numbers and counts
for r in rows:
    print(f"L{r['header_line']:5d}  {r['header']:16s} children={len(r['children']):3d} parents={len(r['parents']):3d}")

with open("table5_parsed.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
