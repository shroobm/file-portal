import re, glob
from collections import Counter

files = sorted(glob.glob(r"C:/Users/Bndit/AppData/Local/Temp/claude/C--Users-Bndit-Projects-file-portal/3567c0ef-5c0b-42cf-8101-4bb783f0ee67/scratchpad/univ4e-marker/slice-*.md"))
parts = [open(f, encoding="utf-8").read() for f in files]
marker_ref = "\n\n".join(parts)

c = Counter(re.findall(r"\\(.)", marker_ref))
print("backslash-escaped char counts in marker ref:")
for ch, n in c.most_common(30):
    print(repr(ch), n)

# sample a few contexts for the most common one
top = c.most_common(1)[0][0]
idx = 0
found = 0
for m in re.finditer(re.escape("\\" + top), marker_ref):
    print(repr(marker_ref[max(0, m.start()-30):m.start()+30]))
    found += 1
    if found >= 8:
        break
