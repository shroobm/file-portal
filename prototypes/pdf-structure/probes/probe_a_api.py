"""WHAT THIS FILE DOES: a one-off API inventory (run directly, no arguments). It prints the installed
pymupdf version and every module-level, Document, Page, TextPage, Story and Xml name that matches
struct / tag / mark / mcid / logic / role, then whether six xref methods exist on Document. No files
are read or written; stdout only; no callers.
"""
import pymupdf, re
print("pymupdf", pymupdf.__version__)
# names in the pymupdf module that mention structure-related words
names = dir(pymupdf)
pat = re.compile(r'struct|tag|mark|mcid|logic|role', re.I)
print("MODULE-LEVEL matches:", sorted(n for n in names if pat.search(n)))
print()
for cls in ("Document","Page","TextPage","Story","Xml"):
    if hasattr(pymupdf, cls):
        m = sorted(n for n in dir(getattr(pymupdf, cls)) if pat.search(n))
        print(f"{cls}: {m}")
print()
# xref-level primitives we will need
for n in ("xref_object","xref_get_key","xref_get_keys","pdf_catalog","xref_length","xref_stream_raw","xref_stream"):
    print(n, hasattr(pymupdf.Document, n))
