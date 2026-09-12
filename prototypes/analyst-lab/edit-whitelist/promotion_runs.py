# -*- coding: utf-8 -*-
"""promotion_runs.py — S140: the windows that FAIL the audit under the promoted module's STRICT policy, each mapped to
its CHUNK (the chunk whose input holds the window's first six words, space-free), with every accepted edit of that
chunk under the prototype's reconciler AND the promoted one side by side — the cause is read off the difference.
Read-only; stdout only."""
import sys

import acceptor as proto
from common import analyst, fa, load_bundle, ladder, tn  # noqa: F401
from align import build_pairs

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import edit_whitelist as ew  # noqa: E402

b = load_bundle()
pairs, _ = build_pairs(b)
_, embeds = analyst.fence(b["shipped_body"])
recon, per_chunk = [], {}
for p in pairs:
    text, log = ew.reconcile(p["input"], p["output"], ew.STRICT, "whitelist")
    _, log_p = proto.reconcile(p["input"], p["output"], proto.STRICT, "whitelist")
    recon.append(p["prefix"] + text)
    per_chunk[p["i"]] = (p, [(lab, a_, b_) for lab, acc, a_, b_ in log if acc], [(lab, a_, b_) for lab, acc, a_, b_ in log_p if acc], text)
body = analyst.unfence("".join(recon), embeds)
a = fa.audit_analyst(b["sidecar_text"], body)
print("promoted STRICT:", a["doc_survival"], a["runs_total"], "runs")
ref = ladder(b["sidecar_text"])
outl = tn.space_free(ladder(body))
wins = tn.make_windows(ref, tn.is_cjk(ref[:4000]))
still = [w for w in wins if tn.space_free(w) not in outl]
print("failing windows:", len(still))
shown = set()
for w in still:
    probe = tn.space_free("".join(w.split()[:6]))
    owner = None
    for i, (p, acc_n, acc_p, text) in per_chunk.items():
        if probe in tn.space_free(ladder(p["input"])):
            owner = i
            break
    if owner is None or owner in shown:
        continue
    shown.add(owner)
    p, acc_n, acc_p, text = per_chunk[owner]
    print("\nCHUNK %s — window: %s" % (owner, w[:90].replace("\n", " ")))
    print("   promoted accepted (%d): %s" % (len(acc_n), [(lab, a_[:50], b_[:50]) for lab, a_, b_ in acc_n[:6]]))
    print("   prototype accepted (%d): %s" % (len(acc_p), [(lab, a_[:50], b_[:50]) for lab, a_, b_ in acc_p[:6]]))
    # is the window's text present in the promoted text of THIS chunk, space-free?
    print("   window in promoted chunk text:", tn.space_free(w) in tn.space_free(ladder(text)),
          "| in input:", tn.space_free(w) in tn.space_free(ladder(p["input"])))
    if len(shown) >= 6:
        break
