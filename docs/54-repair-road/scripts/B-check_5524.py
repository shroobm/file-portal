"""WHAT THIS FILE DOES: a one-off probe script (run directly, no functions). It reads marker_ref.md and held.md
from the current working directory and prints the total line counts, the length of line 5524 in each, and the
first 200 characters of that line in marker_ref.md. Writes nothing. Nothing imports it.
"""
merged = open('marker_ref.md', encoding='utf-8').read()
lines = merged.split('\n')
print('marker_ref total lines', len(lines))
l = lines[5523]
print('line 5524 len', len(l))
print(repr(l[:200]))
print('---held.md line 5524 for comparison---')
held = open('held.md', encoding='utf-8').read().split('\n')
print('held total lines', len(held))
print('held line 5524 len', len(held[5523]))
