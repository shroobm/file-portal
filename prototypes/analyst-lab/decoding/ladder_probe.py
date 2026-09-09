"""prototypes/analyst-lab/decoding/ladder_probe.py -- the DOCUMENT audit (fidelity_audit.audit_analyst,
the real gate function) on sidecar vs shipped DDIA body under successive in-memory ladders, so the
audit's own share of the residual is a doc_survival number:
  v2   as shipped (j32a-v2)
  v3   + unescape incl. `_` BEFORE the markdown strip (J44 rung 1, S118 ladder_v3_probe)
  v3b  + ligature-blind `ffi|ffl|fi|fl|ff` on both sides (J44 rung 2, S118 ladder_v3b_probe)
  v3c  + cite-anchor rung: strip Marker's `(#page-N-K)` link targets on both sides (NEW, this lane --
        the model canonicalises `[\\[2\\]](#page-49-0)` to `[[2](#page-49-0)]` and the ladder's link
        strip cannot see through the escaped brackets, so the anchor text survives on the input side only)
fidelity_audit binds prepare_output BY NAME at import, so both bindings are patched (S118's note).
In-memory only; read-only against the library. Extends the S118 scratchpad probes (copied shape).
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ddia_pairs  # noqa: E402
import fidelity_audit as fa  # noqa: E402
import text_norm as tn  # noqa: E402

m, sidecar_text, shipped_body = ddia_pairs.load_bundle()
real_prepare = tn.prepare_output
V3 = re.compile(r"\\(?=[^\w\s]|_)")
LIG = re.compile(r"ffi|ffl|fi|fl|ff")
CITE = re.compile(r"\(#page-[\d-]+\)")


def prepare_v3(md: str) -> str:
    return real_prepare(V3.sub("", md))


def prepare_v3b(md: str) -> str:
    return LIG.sub("", real_prepare(V3.sub("", md)))


def prepare_v3c(md: str) -> str:
    return LIG.sub("", real_prepare(V3.sub("", CITE.sub("", md))))


def audit_with(fn):
    tn.prepare_output = fn
    fa.prepare_output = fn
    try:
        return fa.audit_analyst(sidecar_text, shipped_body)
    finally:
        tn.prepare_output = real_prepare
        fa.prepare_output = real_prepare


if __name__ == "__main__":
    rows = []
    for name, fn in (("v2 as shipped", real_prepare), ("v3 escape-first", prepare_v3),
                     ("v3b + ligature-blind", prepare_v3b), ("v3c + cite-anchor", prepare_v3c)):
        r = audit_with(fn)
        rows.append((name, r["doc_survival"], r["runs_total"]))
        print(f"{name:22s} doc_survival {r['doc_survival']}  runs_total {r['runs_total']}  "
              f"{'CLEARS 0.995' if r['doc_survival'] >= 0.995 else 'gate not cleared'}")
    print(f"manifest says {m['fidelity']['analyst']['doc_survival']} / {m['fidelity']['analyst']['runs_total']}")
    # negative control for the cite rung: it must NOT rescue a real deletion
    a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [\\[2\\]](#page-49-0) nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    b_repair = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [[2](#page-49-0)] nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    b_delete = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [[2](#page-49-0)]"
    for label, fn in (("v2", real_prepare), ("v3c", prepare_v3c)):
        tn.prepare_output = fn; fa.prepare_output = fn
        try:
            print(f"  control {label}: repaired cite -> {fa.audit_analyst(a, b_repair)['doc_survival']}, "
                  f"deleted tail -> {fa.audit_analyst(a, b_delete)['doc_survival']}")
        finally:
            tn.prepare_output = real_prepare; fa.prepare_output = real_prepare
