"""WHAT THIS FILE DOES: a one-off probe script (run directly, no functions). It reads marker_ref.md from the
current working directory, prints where the text 'rm ROC' and the LaTeX begin-array marker first occur (with 200
characters after the latter), and lists the ten longest lines by line number and length. Writes nothing. Nothing
imports it.
"""
merged = open('marker_ref.md', encoding='utf-8').read()
idx = merged.find('rm ROC')
print('idx rm ROC', idx)
idx2 = merged.find(r'\begin{array}{lll}')
print('idx begin array lll', idx2)
if idx2 > 0:
    print(merged[idx2:idx2+200])
# find degenerate long lines in marker ref
lines = merged.split('\n')
lens = sorted(((i+1,len(l)) for i,l in enumerate(lines)), key=lambda x:-x[1])
print('top 10 longest lines in marker ref:')
for ln, ll in lens[:10]:
    print(ln, ll)
