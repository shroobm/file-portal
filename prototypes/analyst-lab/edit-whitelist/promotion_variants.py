# -*- coding: utf-8 -*-
"""WHAT THIS FILE DOES: a run-once script (no functions to call). It rebuilds the 492 DDIA pairs, reconciles each under
four rung sets (FULL, FULL minus hyphen, STRICT, STRICT minus hyphen) with the promoted windows-converter
edit_whitelist module, and prints the audit survival (shipped ladder and v3c) plus accepted/reverted totals.
Reads the held bundle via common.py; writes nothing but stdout. Run directly from this folder.

promotion_variants.py — S140: the promoted module over the 492 DDIA pairs under three rung sets — FULL, FULL minus
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

# -- the v3c normaliser: cite-anchor rung ([[n]](target) reduced to its text) plus the v3 and ligature rungs --
_CITE = __import__("re").compile(r"\[\[([^\]\n]*)\]\]\(([^)\n]*)\)")
_real_prepare = tn.prepare_output


def _v3c(markdown: str) -> str:
    """Normalise markdown the v3c way: unwrap [[x]](y) cites, apply the prototype's escape rung, the shipped
    prepare_output, then drop ligature letters. Pure function; returns the normalised string."""
    return proto._LIG_BLIND.sub("", _real_prepare(_CITE.sub(r"\1", proto._V3.sub("", markdown))))


# -- main run: build pairs, reconcile under each rung set, audit, print one summary line per rung set --
b = load_bundle()
pairs, _ = build_pairs(b)
_, embeds = analyst.fence(b["shipped_body"])
for name, rungs in (("FULL", ew.FULL), ("FULL-hyphen", ew.FULL - {"hyphen"}), ("STRICT", ew.STRICT), ("STRICT-hyphen", ew.STRICT - {"hyphen"})):
    recon, counts = [], collections.Counter()
    # reconcile every chunk pair; tally each logged edit by (class label, accepted/reverted)
    for p in pairs:
        text, log = ew.reconcile(p["input"], p["output"], rungs, "whitelist")
        recon.append(p["prefix"] + text)
        for lab, acc, _, _ in log:
            counts[(lab, "accepted" if acc else "reverted")] += 1
    # rebuild the document body and audit it under the shipped ladder and under v3c
    body = analyst.unfence("".join(recon), embeds)
    a = fa.audit_analyst(b["sidecar_text"], body)
    a3 = proto.audit_with(_v3c, b["sidecar_text"], body)
    acc = sum(n for (l, s), n in counts.items() if s == "accepted")
    rev = sum(n for (l, s), n in counts.items() if s == "reverted")
    hy = counts[("hyphen", "accepted")]
    print("%-14s shipped ladder %s/%s · v3c %s/%s · accepted %d (hyphen %d) · reverted %d" % (
        name, a["doc_survival"], a["runs_total"], a3["doc_survival"], a3["runs_total"], acc, hy, rev), flush=True)
