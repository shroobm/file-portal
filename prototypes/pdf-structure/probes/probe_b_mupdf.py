"""WHAT THIS FILE DOES: a one-off API inventory (run directly, no arguments). It prints pymupdf's
TEXT_COLLECT_STRUCTURE and PDF_STRUCT_PRESENT constants and lists every name in pymupdf.mupdf that
contains "struct". No files are read or written; stdout only; no callers.
"""
import pymupdf, re
print("TEXT_COLLECT_STRUCTURE =", pymupdf.TEXT_COLLECT_STRUCTURE)
print("PDF_STRUCT_PRESENT =", pymupdf.PDF_STRUCT_PRESENT)
import pymupdf.mupdf as M
pat = re.compile(r'struct', re.I)
hits = sorted(n for n in dir(M) if pat.search(n))
print("mupdf struct-named symbols:", len(hits))
for h in hits: print("  ", h)
