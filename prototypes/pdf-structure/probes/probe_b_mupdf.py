import pymupdf, re
print("TEXT_COLLECT_STRUCTURE =", pymupdf.TEXT_COLLECT_STRUCTURE)
print("PDF_STRUCT_PRESENT =", pymupdf.PDF_STRUCT_PRESENT)
import pymupdf.mupdf as M
pat = re.compile(r'struct', re.I)
hits = sorted(n for n in dir(M) if pat.search(n))
print("mupdf struct-named symbols:", len(hits))
for h in hits: print("  ", h)
