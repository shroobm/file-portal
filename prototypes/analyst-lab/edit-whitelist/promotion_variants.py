# -*- coding: utf-8 -*-
"""promotion_variants.py — S140: the promoted module over the 492 DDIA pairs under three rung sets — FULL, FULL minus
hyphen, STRICT — the audit under the shipped ladder and v3c, accepted/reverted totals. The hyphen rung fires for the
first time in the promoted module (669 joins on DDIA) and the audit's ladder counts every join as loss; this measures
what the wired default costs either way so Rab can pick the slot. Read-only; stdout only."""
import collections
import sys

import acceptor as proto
from common import analyst, fa, load_bundle, ladder, tn  # noqa: F401
from align import build_pairs

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import edit_whitelist as ew  # noqa: E402

_CITE = __import__("re").compile(r"\[\[([^\]\n]*)\]\]\(([^)\n]*)\)")
_real_prepare = tn.prepare_output


def _v3c(markdown: str) -> str:
    return proto._LIG_BLIND.sub("", _real_prepare(_CITE.sub(r"\1", proto._V3.sub("", markdown))))


b = load_bundle()
pairs, _ = build_pairs(b)
_, embeds = analyst.fence(b["shipped_body"])
for name, rungs in (("FULL", ew.FULL), ("FULL-hyphen", ew.FULL - {"hyphen"}), ("STRICT", ew.STRICT), ("STRICT-hyphen", ew.STRICT - {"hyphen"})):
    recon, counts = [], collections.Counter()
    for p in pairs:
        text, log = ew.reconcile(p["input"], p["output"], rungs, "whitelist")
        recon.append(p["prefix"] + text)
        for lab, acc, _, _ in log:
            counts[(lab, "accepted" if acc else "reverted")] += 1
    body = analyst.unfence("".join(recon), embeds)
    a = fa.audit_analyst(b["sidecar_text"], body)
    a3 = proto.audit_with(_v3c, b["sidecar_text"], body)
    acc = sum(n for (l, s), n in counts.items() if s == "accepted")
    rev = sum(n for (l, s), n in counts.items() if s == "reverted")
    hy = counts[("hyphen", "accepted")]
    print("%-14s shipped ladder %s/%s · v3c %s/%s · accepted %d (hyphen %d) · reverted %d" % (
        name, a["doc_survival"], a["runs_total"], a3["doc_survival"], a3["runs_total"], acc, hy, rev), flush=True)
