"""THE PLANTED-DECOY NEGATIVE CONTROL for a structure-first lane.

Builds four synthetic PDFs by hand (no GPU, no marker, no network) and runs ONE reader
over all four. The reader must be watched FAILING on the controls, or "the lane read the
tree" is an untested claim.

  D1  tagged + sentinel      -- /Figure /Alt carries a token that appears in NO glyph.
                                A reader that read the tree emits it. A reader that fell
                                back to a glyph/layout view CANNOT emit it.
  D2  tree removed           -- byte-identical to D1 except /StructTreeRoot is gone from
                                the catalog. Same reader must report untagged and must NOT
                                emit the sentinel.
  D3  tagged, no sentinel    -- tree present, /Alt absent. Reader must not invent one.
  D4  ROTTEN tree            -- tree present and well-formed, every element /NonStruct,
                                every /K MCID pointing at a marked-content id that does not
                                exist in the content stream. This is the "bad exporter"
                                case: present but garbage.

Repo idiom followed: marker_blocks_selftest.py's decoy pattern -- run the decoy through the
IDENTICAL guard and print what the guard read.
"""
import re
import sys
import tempfile
from pathlib import Path

import pymupdf

SENTINEL = "ZQX-TREE-SENTINEL-7F3A"
GLYPH = "VISIBLE GLYPH TEXT ONLY"


def build(path: Path, *, tagged=True, alt=True, rotten=False):
    content = (
        "/P <</MCID 0>> BDC\n"
        "BT /F1 12 Tf 20 150 Td (" + GLYPH + ") Tj ET\n"
        "EMC\n"
        "/Figure <</MCID 1>> BDC\n"
        "1 0 0 RG 20 40 100 50 re S\n"
        "EMC\n"
    ).encode("latin-1")

    cat = ("<< /Type /Catalog /Pages 2 0 R /MarkInfo << /Marked true >>"
           + (" /StructTreeRoot 6 0 R" if tagged else "") + " >>")
    figure_s = "/NonStruct" if rotten else "/Figure"
    para_s = "/NonStruct" if rotten else "/P"
    mcid_p, mcid_f = (77, 78) if rotten else (0, 1)
    alt_entry = (" /Alt (" + SENTINEL + ")") if (alt and not rotten) else ""

    objs = {
        1: cat,
        2: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> /StructParents 0 >>"),
        4: None,  # stream
        5: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: ("<< /Type /StructTreeRoot /K [7 0 R] /ParentTree 10 0 R "
            "/ParentTreeNextKey 1 >>"),
        7: "<< /Type /StructElem /S /Document /P 6 0 R /K [8 0 R 9 0 R] >>",
        8: ("<< /Type /StructElem /S " + para_s + " /P 7 0 R /Pg 3 0 R /K "
            + str(mcid_p) + " >>"),
        9: ("<< /Type /StructElem /S " + figure_s + " /P 7 0 R /Pg 3 0 R /K "
            + str(mcid_f) + alt_entry + " >>"),
        10: "<< /Nums [0 [8 0 R 9 0 R]] >>",
    }
    if not tagged:
        for k in (6, 7, 8, 9, 10):
            objs.pop(k)

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        if num == 4:
            out += (str(num) + " 0 obj\n<< /Length " + str(len(content))
                    + " >>\nstream\n").encode("latin-1")
            out += content
            out += b"\nendstream\nendobj\n"
        else:
            out += (str(num) + " 0 obj\n" + objs[num] + "\nendobj\n").encode("latin-1")
    maxnum = max(objs)
    xref_at = len(out)
    out += ("xref\n0 " + str(maxnum + 1) + "\n").encode("latin-1")
    out += b"0000000000 65535 f \n"
    for num in range(1, maxnum + 1):
        if num in offsets:
            out += ("%010d 00000 n \n" % offsets[num]).encode("latin-1")
        else:
            out += b"0000000000 65535 f \n"
    out += ("trailer\n<< /Size " + str(maxnum + 1) + " /Root 1 0 R >>\nstartxref\n"
            + str(xref_at) + "\n%%EOF\n").encode("latin-1")
    path.write_bytes(bytes(out))
    return path


# --------------------------------------------------------------------------------
# THE READER UNDER TEST -- one function, run over all four decoys, no special cases.
# Door B (raw xref walk) because Door A drops Figures (mapping.md 1.5).
# --------------------------------------------------------------------------------
_REF = re.compile(r"(\d+) 0 R")
STD_ROLES = {"Document", "Part", "Sect", "Div", "P", "H", "H1", "H2", "H3", "H4", "H5",
             "H6", "L", "LI", "Lbl", "LBody", "Table", "TR", "TH", "TD", "THead", "TBody",
             "TFoot", "Figure", "Formula", "Caption", "Code", "Link", "Span", "Note",
             "FENote", "Reference", "BibEntry", "TOC", "TOCI", "Title", "Quote",
             "BlockQuote", "Artifact", "Form", "Aside", "Em", "Strong"}


def read_tree(path):
    """-> dict: what a structure-first lane would ground itself on."""
    rec = {"tagged": False, "elems": 0, "roles": {}, "alts": [], "mcids": 0,
           "mcids_resolvable": 0, "nonstruct": 0}
    with pymupdf.open(path) as doc:
        cat = doc.pdf_catalog()
        v = doc.xref_get_key(cat, "StructTreeRoot")
        # THE ('null','null') TRAP (mapping.md 1.1): absent keys return a TRUTHY tuple.
        if not v or v[0] == "null":
            return rec
        rec["tagged"] = True
        m = _REF.search(v[1])
        if not m:
            return rec
        # collect the marked-content ids that actually EXIST in the page content streams
        live_mcids = set()
        for page in doc:
            for cs in page.get_contents():
                for mm in re.finditer(rb"/MCID\s+(\d+)", doc.xref_stream(cs)):
                    live_mcids.add(int(mm.group(1)))
        seen, stack = set(), [int(m.group(1))]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            s = doc.xref_get_key(x, "S")
            if s and s[0] != "null":
                role = s[1].lstrip("/")
                rec["elems"] += 1
                rec["roles"][role] = rec["roles"].get(role, 0) + 1
                if role == "NonStruct":
                    rec["nonstruct"] += 1
            a = doc.xref_get_key(x, "Alt")
            if a and a[0] != "null":
                rec["alts"].append(a[1].strip("()"))
            k = doc.xref_get_key(x, "K")
            if k and k[0] != "null":
                for r in _REF.findall(k[1]):
                    stack.append(int(r))
                # MCID leaves: /K <int> or /K [ <int> ... ]. Strip every indirect
                # reference FIRST, or "8 0 R" donates three spurious integers.
                leaves = _REF.sub(" ", k[1])
                for num in re.findall(r"\b(\d+)\b", leaves):
                    rec["mcids"] += 1
                    if int(num) in live_mcids:
                        rec["mcids_resolvable"] += 1
    return rec


# THE GATE the design proposes -- stated as code so the decoys can be run through it.
def gate(rec, pages):
    if not rec["tagged"]:
        return "untagged"
    if rec["elems"] == 0:
        return "tagged-hollow"
    named = sum(n for r, n in rec["roles"].items() if r in STD_ROLES and r != "NonStruct")
    if named == 0 or rec["nonstruct"] / max(1, rec["elems"]) > 0.5:
        return "tagged-rotten(roles)"
    if rec["mcids"] and rec["mcids_resolvable"] / rec["mcids"] < 0.9:
        return "tagged-rotten(mcid)"
    return "tagged"


tmp = Path(tempfile.mkdtemp(prefix="fp-decoy-"))
cases = [
    ("D1 tagged+sentinel", dict(tagged=True, alt=True, rotten=False), True, "tagged"),
    ("D2 tree REMOVED", dict(tagged=False, alt=True, rotten=False), False, "untagged"),
    ("D3 tagged, no /Alt", dict(tagged=True, alt=False, rotten=False), False, "tagged"),
    ("D4 ROTTEN tree", dict(tagged=True, alt=True, rotten=True), False,
     "tagged-rotten(roles)"),
]

FAIL = []
print("case\t\t\tglyph_has_sentinel\ttree_has_sentinel\telems\troles\t\t\tgate\texpected")
for name, kw, want_sentinel, want_gate in cases:
    p = build(tmp / (name.split()[0] + ".pdf"), **kw)
    with pymupdf.open(p) as d:
        glyphs = "".join(pg.get_text() for pg in d)
        pages = d.page_count
    rec = read_tree(p)
    g = gate(rec, pages)
    tree_sent = any(SENTINEL in a for a in rec["alts"])
    glyph_sent = SENTINEL in glyphs
    print("\t".join([name.ljust(20), str(glyph_sent).ljust(8), str(tree_sent).ljust(8),
                     str(rec["elems"]), str(rec["roles"])[:34].ljust(34), g, want_gate]))
    if glyph_sent:
        FAIL.append(name + ": sentinel leaked into the GLYPH stream -- decoy is invalid")
    if tree_sent != want_sentinel:
        FAIL.append(name + ": tree sentinel " + str(tree_sent) + ", wanted "
                    + str(want_sentinel))
    if g != want_gate:
        FAIL.append(name + ": gate said " + g + ", wanted " + want_gate)

print()
print("D1 mcids:", read_tree(tmp / "D1.pdf")["mcids"], "resolvable:",
      read_tree(tmp / "D1.pdf")["mcids_resolvable"])
print("D4 mcids:", read_tree(tmp / "D4.pdf")["mcids"], "resolvable:",
      read_tree(tmp / "D4.pdf")["mcids_resolvable"])
print()
print("RED: " + "; ".join(FAIL) if FAIL else "GREEN: 4/4 decoys behaved as specified")
print("files kept at:", tmp)
sys.exit(1 if FAIL else 0)
