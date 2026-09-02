"""Door A density over the operator's REAL converted corpus (10 distinct anchor works).

Second, differently-shaped method against corpus_probe.py's xref /Type-count (which is a
FLOOR: ISO 32000-2 makes StructElem's /Type optional, so a producer may omit it).

Measures exactly what the proposed lane probe would measure, so the numbers double as the
probe's own cost. Read-only. CPU only. No GPU.
"""
import json
import time
from pathlib import Path

import pymupdf

ANCHOR = Path(r"C:\Users\Bndit\ml\library\anchor")
SEARCH = [Path(r"C:\Users\Bndit\Downloads"), Path(r"C:\Users\Bndit\ml\library"),
          Path(r"C:\Users\Bndit\Documents")]

FL = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE

works = {}
for d in sorted(ANCHOR.iterdir()):
    m = d / "manifest.json"
    if not m.is_file():
        continue
    j = json.loads(m.read_text(encoding="utf-8"))
    src = j.get("source")
    works.setdefault(src, {"lane": j.get("lane"), "reason": j.get("lane_reason"),
                           "pages": j.get("pages")})

index = {}
for root in SEARCH:
    if not root.is_dir():
        continue
    try:
        for p in root.rglob("*.pdf"):
            index.setdefault(p.name, p)
    except OSError:
        pass


def walk(blocks, counts, types, depth, maxdepth):
    for b in blocks:
        if b.get("type") == 2:
            counts[0] += 1
            types.add(b.get("std"))
            maxdepth[0] = max(maxdepth[0], depth + 1)
            walk(b.get("blocks") or [], counts, types, depth + 1, maxdepth)


def door_a(path, sample_pages):
    """(elems, distinct std types, max depth, seconds, pages sampled, chars sampled)"""
    counts = [0]
    types = set()
    maxdepth = [0]
    chars = 0
    t0 = time.perf_counter()
    with pymupdf.open(path) as doc:
        n = doc.page_count
        step = max(1, n // sample_pages)
        idxs = list(range(0, n, step))[:sample_pages]
        for i in idxs:
            d = doc[i].get_text("dict", flags=FL)
            walk(d.get("blocks") or [], counts, types, 0, maxdepth)
            chars += len(doc[i].get_text())
    return counts[0], len(types), maxdepth[0], time.perf_counter() - t0, len(idxs), chars


HEAD = ["work", "lane", "pages", "sampled", "structelem", "std_types", "maxdepth",
        "elem_per_pp", "chars_per_pp", "ms_per_page", "VERDICT"]
print("\t".join(HEAD))
rows = []
for src, w in sorted(works.items()):
    p = index.get(src)
    if p is None:
        print(src[:40] + "\tSOURCE-NOT-FOUND")
        continue
    try:
        e, t, md, sec, sp, ch = door_a(p, 25)
    except Exception as exc:
        print(src[:40] + "\tERR " + type(exc).__name__ + " " + str(exc)[:60])
        continue
    epp = e / sp if sp else 0.0
    cpp = ch / sp if sp else 0.0
    # the density gate the design proposes, stated as code so it is testable
    verdict = "tagged" if (epp >= 5.0 and t >= 6) else (
        "tagged-hollow" if e > 0 else "untagged")
    rows.append((src, w, e, t, md, epp, cpp, 1000 * sec / sp, verdict))
    print("\t".join(str(x) for x in [
        src[:40], w["lane"], w["pages"], sp, e, t, md,
        "%.2f" % epp, "%.0f" % cpp, "%.2f" % (1000 * sec / sp), verdict]))

print()
from collections import Counter
c = Counter(r[8] for r in rows)
print("VERDICT TALLY over", len(rows), "distinct works:", dict(c))
