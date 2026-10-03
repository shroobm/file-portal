"""WHAT THIS FILE DOES: a one-off check script (run directly; run() is its one helper). It reads marker_ref.md,
held.md and repaired.md from the current working directory and prints fidelity_audit.audit_analyst results for
three pairings: original Marker vs original held, original Marker vs repaired held, and Marker with line 8796
deleted vs repaired held. Writes nothing. Nothing imports it.
"""
import sys, json
sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import fidelity_audit as fa

# -- inputs --
marker_orig = open("marker_ref.md", encoding="utf-8").read()
held_orig = open("held.md", encoding="utf-8").read()
held_repaired = open("repaired.md", encoding="utf-8").read()

# -- one audit_analyst run, printed --
def run(label, ref, out):
    """Run audit_analyst(ref, out), print label with doc_survival, runs_total and the longest run in words.

    Returns the audit block dict. Side effect: prints one line.
    """
    b = fa.audit_analyst(ref, out)
    print(label, "doc_survival=", b["doc_survival"], "runs_total=", b["runs_total"],
          "max_run_words=", max((r["words"] for r in b["runs"]), default=0))
    return b

run("(a) historical: marker_orig -> held_orig", marker_orig, held_orig)
run("(b) marker_orig -> held_repaired(deleted)", marker_orig, held_repaired)

# (c) repair the marker reference too: delete its own runaway paragraph at line 8796 (1-idx)
mlines = marker_orig.split("\n")
print("marker line 8796 len before:", len(mlines[8795]))
del mlines[8795]
marker_repaired = "\n".join(mlines)
run("(c) marker_repaired -> held_repaired(deleted, matched)", marker_repaired, held_repaired)
