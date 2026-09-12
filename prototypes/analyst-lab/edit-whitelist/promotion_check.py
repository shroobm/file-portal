# -*- coding: utf-8 -*-
"""promotion_check.py — S140: the promoted `windows-converter/edit_whitelist.py` against this prototype's `acceptor.py`
over the real 492 DDIA pairs (held fc1f068c3a8eeb63). Acceptance: (1) the two CONTROLS hold for the promoted module
(accept-all == the shipped body byte-for-byte; accept-none == the sidecar's ladder words); (2) FULL under both
reconcilers: the audit under the shipped ladder and under v3c, the accepted/reverted totals by class — the promoted
module aligns on normalised keys and judges hunks, so it is expected to ACCEPT MORE whitelisted repairs (hyphen, reflow,
ligature) and REVERT FEWER neighbours than the prototype; a lower survival under the SHIPPED ladder is possible (the
shipped ladder counts ligature/escape repairs as loss) while v3c must not fall. (3) no non-whitelisted edit accepted: the
reverted classes of the prototype (deletion/substitution/numeral/insertion/punctuation) must not appear among the
promoted module's ACCEPTED classes. Read-only; stdout only. Run with the converter's interpreter from this directory."""
import collections
import sys

import acceptor as proto
from common import analyst, fa, load_bundle, ladder, tn  # noqa: F401
from align import build_pairs

sys.path.insert(0, "C:/Users/Bndit/Projects/file-portal/windows-converter")
import edit_whitelist as ew  # noqa: E402

_V3 = proto._V3
_LIG_BLIND = proto._LIG_BLIND
_CITE = __import__("re").compile(r"\[\[([^\]\n]*)\]\]\(([^)\n]*)\)")
_real_prepare = tn.prepare_output


def _v3c(markdown: str) -> str:
    return _LIG_BLIND.sub("", _real_prepare(_CITE.sub(r"\1", _V3.sub("", markdown))))


def run(pairs, embeds, fn, rungs, policy):
    recon, counts = [], collections.Counter()
    for p in pairs:
        text, log = fn(p["input"], p["output"], rungs, policy)
        recon.append(p["prefix"] + text)
        for lab, acc, _, _ in log:
            counts[(lab, "accepted" if acc else "reverted")] += 1
    return analyst.unfence("".join(recon), embeds), counts


def split(counts):
    acc, rev = collections.Counter(), collections.Counter()
    for (lab, st), n in counts.items():
        (acc if st == "accepted" else rev)[lab] += n
    return acc, rev


b = load_bundle()
pairs, stats = build_pairs(b)
_, embeds = analyst.fence(b["shipped_body"])
print("pairs:", len(pairs), "| alignment:", {k: v for k, v in stats.items() if k != "rejected_mismatch"}, flush=True)

body_all, _ = run(pairs, embeds, ew.reconcile, ew.FULL, "all")
print("(1) control accept-ALL  == shipped body byte-for-byte:", body_all == b["shipped_body"], flush=True)
body_none, _ = run(pairs, embeds, ew.reconcile, set(), "none")
print("(1) control accept-NONE ladder words == sidecar:", ladder(body_none).split() == ladder(b["sidecar_text"]).split(), flush=True)

for name, fn, rungs in (("PROTOTYPE", proto.reconcile, proto.FULL), ("PROMOTED ", ew.reconcile, ew.FULL)):
    body, counts = run(pairs, embeds, fn, rungs, "whitelist")
    a = fa.audit_analyst(b["sidecar_text"], body)
    a3 = proto.audit_with(_v3c, b["sidecar_text"], body)
    acc, rev = split(counts)
    print("(2) %s FULL: shipped ladder %s/%s · v3c %s/%s · accepted %d %s · reverted %d %s" % (
        name, a["doc_survival"], a["runs_total"], a3["doc_survival"], a3["runs_total"],
        sum(acc.values()), dict(acc.most_common()), sum(rev.values()), dict(rev.most_common())), flush=True)
    if name.startswith("PROMOTED"):
        bad = {k: v for k, v in acc.items() if k in ("deletion", "substitution", "numeral", "insertion", "punctuation/case")}
        print("(3) non-whitelisted classes among the PROMOTED module's ACCEPTED edits:", bad or "none", flush=True)
a0 = fa.audit_analyst(b["sidecar_text"], b["shipped_body"])
print("    shipped (as held): %s/%s  (S119: 0.9718/49)" % (a0["doc_survival"], a0["runs_total"]), flush=True)
