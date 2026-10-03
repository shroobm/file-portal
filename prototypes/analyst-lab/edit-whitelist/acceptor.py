r"""WHAT THIS FILE DOES: the prototype diff-whitelist acceptor. reconcile(input, candidate, rungs, policy) compares an
analyst input chunk with the model's output word by word, keeps only edits that are equivalent under the chosen
whitelist (equivalent/norm) and reverts the rest; label() names each edit's class. run_policy() applies it to all
pairs and audit_with() audits under a patched normaliser; main() runs the controls and the FULL and STRICT policies,
prints the results and writes reconciled_<policy>.md, results_edit_samples.json and results_acceptor.json into the
current directory. Reads the held bundle via common.py/align.py. Imported by promotion_* and reference-repair.

Ask C — the DIFF-WHITELIST ACCEPTOR (quarantined prototype, zero pipeline coupling).

Given (input chunk, candidate) as the analyst sees them (fenced, raw markdown):
  1. whitespace-tokenise both, keep every token's offsets;
  2. word-level opcodes (rapidfuzz Levenshtein.opcodes on the two token lists, exact keys);
  3. for every non-equal opcode decide ACCEPT or REVERT: accept only if the two spans are
     EQUIVALENT under the stated whitelist normalisation N (below); otherwise splice the INPUT's
     span back in place of the candidate's;
  4. emit the reconciled chunk (the candidate's text with every non-whitelisted edit undone).

The whitelist N (applied to BOTH spans, then compared space-free):
  quotes      curly quotes / dashes unified to ASCII (the audit's own _QUOTES map, NFKC)
  escape      markdown backslash-escapes removed (`\_` `\*` `\$` `\(` `\[` `\]` `\#` `\-` ...)
  link        `[text](url)` and Marker's `[[n\]](url)` collapse to their text; the URL SET of the
              two spans must be equal (a link may be re-syntaxed, never re-targeted or dropped)
  markup      heading marks, emphasis `*`, boundary `_`, backticks, blockquote `>`, table pipes
              and separator dashes removed; square brackets removed (citation `[2]` == `2`)
  hyphen      a line-end hyphen glyph mis-mapped to `!` (this PDF's fonts, S119 R1 a_probe3)
              or a real `-` followed by whitespace and a lowercase letter joins the two halves
  ligature    the INPUT's mis-mapped ligature glyphs (`!"#$&'%)` between letters, or before a
              lowercase word start) may be REPLACED by one of ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|
              st|Th|th in the candidate (`Di"cult` -> `Difficult`; `%ere` -> `There`); a
              required replacement, so a dropped quote mark alone is NOT a ligature repair
  reflow      space-free comparison: word boundaries may move (`unexpect edly` -> `unexpectedly`)
Everything else is reverted: word substitutions, deletions, insertions, numeral changes,
punctuation-only edits (`.` -> `,`), case changes. Strict on purpose: the audit is blind to
punctuation and case, so reverting them costs nothing and keeps the text the author's.

Policies (for the report): FULL = the whitelist above; STRICT = FULL minus {ligature, escape,
link} — every edit today's audit (j32a-v2) counts as loss is reverted, which is the ceiling of
"faithful by construction" under the audit AS SHIPPED; ALL = accept everything (must reproduce
the shipped body byte-for-byte and its 0.9718 / 49); NONE = accept nothing (must audit 1.0 / 0).
"""
import collections
import json
import re
import sys
import unicodedata

from rapidfuzz.distance import Levenshtein

from common import analyst, fa, load_bundle, ladder, tn  # noqa: F401
from align import build_pairs

# -- regexes and constants for the whitelist rungs (tokens, quotes, escapes, links, hyphens, ligatures, markup) --
_WS_TOKEN = re.compile(r"\S+")
_QUOTES = tn._QUOTES
_ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|<>~\"'])")
_LINK = re.compile(r"\[(\[?[^\]\n]*\]?)\]\(([^)\n]*)\)")
_HYPHEN_JOIN = re.compile(r"(?<=[A-Za-z])[!\-\u00ad]\s+(?=[a-z])")
_GARBLE_IN = re.compile(r"(?<=[A-Za-z])[!\"#$&'%)](?=[a-z])")
_GARBLE_START = re.compile(r"(?<![A-Za-z])[!\"#$&'%](?=[a-z]{2,})")
LIG_ALT = "(?:ffi|ffl|ff|fi|fl|ft|fk|fj|fb|fh|st|Th|th)"
_MARKUP = re.compile(r"(?m)^\s{0,3}#{1,6}\s*|`|\*|(?<!\w)_|_(?!\w)|^\s*>\s?|\||^\s*:?-{3,}:?\s*$")
_BRACKETS = re.compile(r"[\[\]]")
_WS = re.compile(r"\s+")
_DIGIT = re.compile(r"\d")


# -- equivalence test: normalise both spans under the rungs and compare --
def _urls(text: str, rungs: set[str]) -> collections.Counter:
    """Count the link targets (urls) found in text, removing markdown escapes first when the escape rung is on.
    Returns a Counter of url strings."""
    # escapes come off BEFORE the link regex: Marker writes a citation as `[[2\]](#page-490-0)`
    # and the escaped bracket hides the link from a naive regex (S119 R1, first acceptor run)
    if "escape" in rungs:
        text = _ESC.sub(r"\1", text)
    return collections.Counter(u for _, u in _LINK.findall(text))


def norm(text: str, rungs: set[str]) -> str:
    """Normalise text with NFKC and quote unification, then each enabled rung (escape, link, markup, hyphen), and
    remove all whitespace. Pure function; returns the space-free string."""
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    if "escape" in rungs:
        t = _ESC.sub(r"\1", t)
    if "link" in rungs:
        t = _LINK.sub(r"\1", t)
    if "markup" in rungs:
        t = _MARKUP.sub(" ", t)
        t = _BRACKETS.sub("", t)
    if "hyphen" in rungs:
        t = _HYPHEN_JOIN.sub("", t)
    return _WS.sub("", t)


def equivalent(a: str, b: str, rungs: set[str]) -> bool:
    """True when spans a and b are equal after normalisation under rungs, with equal link-target sets when the link
    rung is on, or when the ligature rung can turn every garbled glyph in a into a ligature that yields b."""
    if "link" in rungs and _urls(a, rungs) != _urls(b, rungs):
        return False
    na, nb = norm(a, rungs), norm(b, rungs)
    if na == nb:
        return True
    if "ligature" in rungs and (_GARBLE_IN.search(na) or _GARBLE_START.search(na)) and len(na) <= 600:
        # rebuild na as a regex where every garble char becomes the ligature alternation
        pat = ""
        for j, ch in enumerate(na):
            left = na[j - 1] if j else ""
            right = na[j + 1:j + 3]
            if ch in "!\"#$&'%)" and (
                (left.isalpha() and right[:1].islower()) or
                (not left.isalpha() and len(right) == 2 and right.islower() and right.isalpha())):
                pat += LIG_ALT
            else:
                pat += re.escape(ch)
        return re.fullmatch(pat, nb) is not None
    return False


# -- policies (rung sets) and the edit labeller --
FULL = {"escape", "link", "markup", "hyphen", "ligature"}
STRICT = {"markup", "hyphen"}


def label(a: str, b: str) -> str:
    """A class name for the report: the cheapest rung set that makes the spans equivalent, or
    the content class of a non-whitelisted edit."""
    if not a.strip():
        return "insertion"
    if not b.strip():
        return "deletion"
    if equivalent(a, b, set()):
        return "reflow"
    # try each single rung (then two combined) in turn; the first that makes the spans equivalent names the edit
    for name, rungs in (("hyphen", {"hyphen"}), ("escape", {"escape"}), ("link", {"link"}),
                        ("markup", {"markup"}), ("ligature", {"ligature"}),
                        ("markup+link", {"markup", "link"}), ("markup+escape", {"markup", "escape"})):
        if equivalent(a, b, rungs):
            return name
    if equivalent(a, b, FULL):
        return "mixed-whitelist"
    pa = re.sub(r"[^\w\s]", "", a).casefold().split()
    pb = re.sub(r"[^\w\s]", "", b).casefold().split()
    if "".join(pa) == "".join(pb):
        return "punctuation/case"
    da = [w for w in a.split() if _DIGIT.search(w)]
    db = [w for w in b.split() if _DIGIT.search(w)]
    if da != db and len(a.split()) == len(b.split()):
        return "numeral"
    return "substitution"


# -- the reconciler: splice accepted edits and reverted originals into one text --
def reconcile(inp: str, cand: str, rungs: set[str], policy: str = "whitelist") -> tuple[str, list]:
    """Returns (reconciled text, edit log [(label, accepted, a_span, b_span)])."""
    # tokenise both texts, remembering each token's character offsets
    ta = [(m.start(), m.end()) for m in _WS_TOKEN.finditer(inp)]
    tb = [(m.start(), m.end()) for m in _WS_TOKEN.finditer(cand)]
    wa = [inp[s:e] for s, e in ta]
    wb = [cand[s:e] for s, e in tb]
    if wa == wb and policy != "all":
        # token-identical: whitespace/paragraphing is the only difference; keep the candidate
        return cand, []
    # walk the word-level opcodes: equal runs are copied from the candidate; each other edit is accepted or reverted
    ops = Levenshtein.opcodes(wa, wb)
    out = []
    log = []
    prev_end_b = 0       # candidate offset after the last emitted candidate segment
    prev_end_a = 0
    first = True
    for op in ops:
        tag, s0, s1, d0, d1 = op.tag, op.src_start, op.src_end, op.dest_start, op.dest_end
        if tag == "equal":
            seg = cand[tb[d0][0]:tb[d1 - 1][1]]
            gap = cand[prev_end_b:tb[d0][0]] if not first else cand[:tb[d0][0]]
            out.append(gap + seg)
            prev_end_b = tb[d1 - 1][1]
            prev_end_a = ta[s1 - 1][1]
            first = False
            continue
        # a non-equal edit: decide accept (keep candidate span) or revert (restore the input span)
        a_span = inp[ta[s0][0]:ta[s1 - 1][1]] if s1 > s0 else ""
        b_span = cand[tb[d0][0]:tb[d1 - 1][1]] if d1 > d0 else ""
        if policy == "all":
            accept = True
        elif policy == "none":
            accept = False
        else:
            accept = equivalent(a_span, b_span, rungs) if (a_span or b_span) else True
        log.append((label(a_span, b_span), accept, a_span, b_span))
        if accept:
            if d1 > d0:
                gap = cand[prev_end_b:tb[d0][0]] if not first else cand[:tb[d0][0]]
                out.append(gap + b_span)
                prev_end_b = tb[d1 - 1][1]
            # an accepted pure deletion emits nothing
        else:
            if s1 > s0:
                # the input's own preceding whitespace (a reverted deletion keeps its paragraphing)
                gap = inp[prev_end_a:ta[s0][0]] if not first else inp[:ta[s0][0]]
                if d1 > d0 and not first:
                    gap = cand[prev_end_b:tb[d0][0]] or gap
                out.append(gap + a_span)
            # a reverted pure insertion emits nothing
            if d1 > d0:
                prev_end_b = tb[d1 - 1][1]
        if s1 > s0:
            prev_end_a = ta[s1 - 1][1]
        first = False
    # whatever follows the last emitted segment (trailing whitespace) goes on the end
    tail = cand[prev_end_b:] if tb else inp[prev_end_a:]
    out.append(tail)
    return "".join(out), log


# -- drivers: apply the reconciler to every pair, and audit under a patched normaliser --
def run_policy(pairs, embeds, policy, rungs, tag):
    """Reconcile every pair under policy/rungs and rebuild the document body. The tag argument is not used inside
    the function. Returns (unfenced body text, Counter keyed by (label, 'accepted'/'reverted'))."""
    recon = []
    counts = collections.Counter()
    for p in pairs:
        text, log = reconcile(p["input"], p["output"], rungs, policy)
        recon.append(p["prefix"] + text)
        for lab, acc, a, b in log:
            counts[(lab, "accepted" if acc else "reverted")] += 1
    fenced = "".join(recon)
    body = analyst.unfence(fenced, embeds)
    return body, counts


def audit_with(prepare, sidecar, body):
    """Run fidelity_audit.audit_analyst(sidecar, body) with prepare patched in as prepare_output (both bindings),
    restoring the originals afterwards. Returns the audit dict."""
    real = tn.prepare_output
    tn.prepare_output = prepare
    fa.prepare_output = prepare
    try:
        return fa.audit_analyst(sidecar, body)
    finally:
        tn.prepare_output = real
        fa.prepare_output = real


# -- ladder-variant regexes (escape-first, ligature-blind) used by the audits below and by promotion_* scripts --
_V3 = re.compile(r"\\(?=[^\w\s]|_)")
_LIG_BLIND = re.compile(r"ffi|ffl|fi|fl|ff")


# -- entry point --
def main():
    """Run the shipped baseline, the accept-all and accept-none controls, then the FULL and STRICT policies under
    three ladders; print the results, write reconciled_<policy>.md plus two JSON files in the current directory."""
    b = load_bundle()
    pairs, stats = build_pairs(b)
    fenced_out, embeds_out = analyst.fence(b["shipped_body"])
    assert embeds_out == b["embeds"], "embed lists differ — the fence numbering would not line up"
    sidecar = b["sidecar_text"]
    results = {}
    print("alignment:", {k: v for k, v in stats.items() if k != "rejected_mismatch"}, "mismatch:", stats["rejected_mismatch"])

    base = fa.audit_analyst(sidecar, b["shipped_body"])
    print(f"\nSHIPPED (as held):        doc_survival {base['doc_survival']}  runs {base['runs_total']}")
    results["shipped"] = (base["doc_survival"], base["runs_total"])

    # negative controls
    body_all, c_all = run_policy(pairs, embeds_out, "all", FULL, "all")
    a_all = fa.audit_analyst(sidecar, body_all)
    print(f"CONTROL accept-ALL:       doc_survival {a_all['doc_survival']}  runs {a_all['runs_total']}  "
          f"| body == shipped byte-for-byte: {body_all == b['shipped_body']}")
    results["control_all"] = (a_all["doc_survival"], a_all["runs_total"], body_all == b["shipped_body"])
    body_none, c_none = run_policy(pairs, embeds_out, "none", set(), "none")
    a_none = fa.audit_analyst(sidecar, body_none)
    same_words = ladder(body_none).split() == ladder(sidecar).split()
    print(f"CONTROL accept-NONE:      doc_survival {a_none['doc_survival']}  runs {a_none['runs_total']}  "
          f"| ladder words == sidecar: {same_words}")
    results["control_none"] = (a_none["doc_survival"], a_none["runs_total"], same_words)

    # the two alternative ladders defined as local functions: v3b (escape-first plus ligature-blind), v3c (plus cites)
    real_prepare = tn.prepare_output
    def _v3b(markdown: str) -> str:
        """Ladder v3b: strip escaping backslashes, apply the shipped prepare_output, drop ligature letter groups."""
        return _LIG_BLIND.sub("", real_prepare(_V3.sub("", markdown)))
    _CITE = re.compile(r"\[\[([^\]\n]*)\]\]\(([^)\n]*)\)")   # Marker's `[[n]](url)` once unescaped
    def _v3c(markdown: str) -> str:
        """Ladder v3c: v3b plus the [[n]](url) citation form collapsed to its text."""
        # v3b + the citation-link form collapsed to its text (the class B's classifier calls link-syntax)
        return _LIG_BLIND.sub("", real_prepare(_CITE.sub(r"\1", _V3.sub("", markdown))))

    # run each policy: reconcile, audit under three ladders, print class counts, write the reconciled body to disk
    sample_log = {}
    for name, rungs in (("FULL", FULL), ("STRICT", STRICT)):
        body, counts = run_policy(pairs, embeds_out, "whitelist", rungs, name)
        a = fa.audit_analyst(sidecar, body)
        a3 = audit_with(_v3b, sidecar, body)
        a3c = audit_with(_v3c, sidecar, body)
        print(f"\nPOLICY {name:6s} rungs={sorted(rungs)}")
        print(f"   under the SHIPPED ladder (j32a-v2): doc_survival {a['doc_survival']}  runs {a['runs_total']}"
              f"  {'CLEARS 0.995' if a['doc_survival'] >= 0.995 else 'below the 0.995 gate'}")
        print(f"   under ladder v3b (escape-first + ligature-blind, both bindings patched): "
              f"doc_survival {a3['doc_survival']}  runs {a3['runs_total']}")
        print(f"   under ladder v3c (v3b + `[[n]](url)` citation collapsed): "
              f"doc_survival {a3c['doc_survival']}  runs {a3c['runs_total']}")
        acc = collections.Counter(); rev = collections.Counter()
        for (lab, st), n in counts.items():
            (acc if st == "accepted" else rev)[lab] += n
        print("   accepted by class:", acc.most_common())
        print("   reverted by class:", rev.most_common())
        print("   totals: accepted", sum(acc.values()), "reverted", sum(rev.values()),
              "(numerator: non-equal word-level opcodes over the 492 aligned pairs)")
        results[name] = {"v2": (a["doc_survival"], a["runs_total"]), "v3b": (a3["doc_survival"], a3["runs_total"]),
                         "v3c": (a3c["doc_survival"], a3c["runs_total"]),
                         "accepted": dict(acc), "reverted": dict(rev)}
        # the windows that still fail under this policy and the shipped ladder (for the record)
        ref = ladder(sidecar); outl = tn.space_free(ladder(body))
        wins = tn.make_windows(ref, tn.is_cjk(ref[:4000]))
        still = [w for w in wins if tn.space_free(w) not in outl]
        results[name]["still_failing_windows"] = len(still)
        if len(still) <= 12:
            for w in still:
                print("     still failing:", w[:100])
        # a sample of the edit log per class (first 3 of each)
        seen = collections.defaultdict(list)
        # re-run the reconciler to collect up to three edit samples per (class, accepted/reverted)
        for p in pairs:
            _, log = reconcile(p["input"], p["output"], rungs, "whitelist")
            for lab, acc_, a_, b_ in log:
                key = (lab, "accepted" if acc_ else "reverted")
                if len(seen[key]) < 3:
                    seen[key].append({"chunk": p["i"], "in": a_[:120], "out": b_[:120]})
        sample_log[name] = {f"{k[0]}/{k[1]}": v for k, v in seen.items()}
        out_path = f"reconciled_{name}.md"
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        print("   reconciled body written (untracked, .gitignore'd):", out_path, len(body), "chars")
        # the largest runs still open
        for r in sorted(a.get("runs") or [], key=lambda r: -(r.get("words") or 0))[:5]:
            print("     open run:", r.get("words"), "|", (r.get("excerpt") or "")[:90])
    json.dump(sample_log, open("results_edit_samples.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    # what the whole shipped body scores under v3b alone (no acceptor) — the S118 number, re-measured
    a3s = audit_with(_v3b, sidecar, b["shipped_body"])
    print(f"\nSHIPPED under ladder v3b (no acceptor): doc_survival {a3s['doc_survival']}  runs {a3s['runs_total']}")
    results["shipped_v3b"] = (a3s["doc_survival"], a3s["runs_total"])
    json.dump(results, open("results_acceptor.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
