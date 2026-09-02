"""Walk the structure tree pymupdf 1.28.0 exposes via TEXT_COLLECT_STRUCTURE.

Prints, for ONE page: every StructElem node as raw/std tag, its bbox, and the
glyph text beneath it. Then whole-document element-type counts.
"""
import sys, collections
import pymupdf

P = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Bndit/Downloads/Well-Tagged-PDF-WTPDF-1.0.pdf"
PAGE = int(sys.argv[2]) if len(sys.argv) > 2 else 10
FLAGS = pymupdf.TEXTFLAGS_DICT | pymupdf.TEXT_COLLECT_STRUCTURE

doc = pymupdf.open(P)
print("FILE:", P)
print("pages:", doc.page_count, "markinfo:", doc.markinfo)


def block_text(b):
    out = []
    for l in b.get("lines", []):
        out.append("".join(s["text"] for s in l.get("spans", [])))
    return " ".join(out)


def union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def walk(blocks, depth, sink, path=()):
    """Yield (depth, kind, raw, std, index, bbox, text). Returns union bbox."""
    ub = None
    for b in blocks:
        t = b.get("type")
        if t == 2:  # FZ_STEXT_BLOCK_STRUCT
            raw = b.get("raw")
            std = b.get("std")
            idx = b.get("index")
            rec = {"depth": depth, "kind": "STRUCT", "raw": raw, "std": std,
                   "index": idx, "bbox": None, "text": "", "path": path + (raw,)}
            sink.append(rec)
            child_bbox = walk(b.get("blocks", []), depth + 1, sink, path + (raw,))
            rec["bbox"] = child_bbox
            # collect text of everything under it
            rec["text"] = " ".join(r["text"] for r in sink[sink.index(rec) + 1:]
                                   if r["kind"] == "TEXT" and r["depth"] > depth)
            ub = union(ub, child_bbox)
        elif t == 0:  # text
            bb = tuple(b.get("bbox"))
            sink.append({"depth": depth, "kind": "TEXT", "raw": None, "std": None,
                         "index": b.get("number"), "bbox": bb,
                         "text": block_text(b), "path": path})
            ub = union(ub, bb)
        elif t == 1:  # image
            bb = tuple(b.get("bbox"))
            sink.append({"depth": depth, "kind": "IMAGE", "raw": None, "std": None,
                         "index": b.get("number"), "bbox": bb,
                         "text": "", "path": path})
            ub = union(ub, bb)
        else:
            sink.append({"depth": depth, "kind": "TYPE%s" % t, "raw": None,
                         "std": None, "index": None, "bbox": None, "text": "",
                         "path": path})
    return ub


page = doc[PAGE]
d = page.get_text("dict", flags=FLAGS)
sink = []
walk(d["blocks"], 0, sink)
print()
print("=== PAGE %d STRUCTURE WALK (%d nodes) ===" % (PAGE, len(sink)))
for r in sink:
    ind = "  " * r["depth"]
    if r["kind"] == "STRUCT":
        bb = r["bbox"]
        bbs = "None" if bb is None else "(%.1f %.1f %.1f %.1f)" % bb
        print("%s<%s> std=%s idx=%s bbox=%s" % (ind, r["raw"], r["std"], r["index"], bbs))
    else:
        bb = r["bbox"]
        bbs = "None" if bb is None else "(%.1f %.1f %.1f %.1f)" % bb
        txt = r["text"][:90].replace(chr(10), " ")
        print("%s[%s] bbox=%s %r" % (ind, r["kind"], bbs, txt))

# whole-document tally
print()
print("=== WHOLE-DOC ELEMENT TALLY ===")
raw_ct = collections.Counter()
std_ct = collections.Counter()
maxdepth = 0
struct_pages = 0
for pno in range(doc.page_count):
    s = []
    dd = doc[pno].get_text("dict", flags=FLAGS)
    walk(dd["blocks"], 0, s)
    if any(r["kind"] == "STRUCT" for r in s):
        struct_pages += 1
    for r in s:
        if r["kind"] == "STRUCT":
            raw_ct[r["raw"]] += 1
            std_ct[r["std"]] += 1
            maxdepth = max(maxdepth, r["depth"])
print("pages with >=1 StructElem: %d / %d" % (struct_pages, doc.page_count))
print("max nesting depth observed:", maxdepth)
print("total StructElem instances:", sum(raw_ct.values()))
print("distinct raw tags:", len(raw_ct))
for k, v in raw_ct.most_common():
    print("   raw %-16s %5d" % (k, v))
print("distinct std tags:", len(std_ct))
for k, v in std_ct.most_common():
    print("   std %-16s %5d" % (str(k), v))
