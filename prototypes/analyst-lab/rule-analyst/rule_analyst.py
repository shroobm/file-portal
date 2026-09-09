r"""prototypes/analyst-lab/rule-analyst/rule_analyst.py -- does the analyst's STATED job need an LLM?

prompts/readability.txt asks for exactly four things: fix mid-word hyphenation splits
('unexpect edly' -> 'unexpectedly'), normalize heading levels, keep paragraphs intact, keep the
image placeholders. This module does the first two BY RULE and leaves every other byte alone, then
measures itself against the real DDIA pairs (the held bundle's sidecar = the analyst's input; the
shipped .md = qwen3:8b's output, aligned per chunk by ../decoding/ddia_pairs.py).

Two rules, both reversible and both counted:
  R-HYPHEN  `(\w)-\n(\w)` -> `\1\2`        a hard line-break hyphenation (Marker keeps the hyphen)
  R-SPLIT   `word1 word2` -> `word1word2`  a SPACE split ('unexpect edly') -- ONLY when the join is a
            known word and at least one half is not, where "known" = the document's own vocabulary
            (whitespace-split alphabetic tokens seen >= VOCAB_MIN times in the sidecar) -- a
            self-dictionary; no external wordlist is on the machine. The guard is what keeps
            'data base' -> 'database' from firing on prose that meant two words: it fires only if
            one half is NOT itself a frequent word.
  R-HEADING (measured, not applied by default): the LLM's heading edits are COUNTED so the reader
            can see what "normalize heading levels" meant in practice.

Survival of the rule-based output is ~1.0 BY CONSTRUCTION: R-HYPHEN is a change the ladder's own
_DEHYPHEN already erases, and R-SPLIT moves a space that space_free containment cannot see. The
script PROVES it by scoring with the shipped text_norm.chunk_survival and fidelity_audit.audit_analyst.

Quarantined (prototypes/README.md); read-only against the library.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "decoding"))
import ddia_pairs  # noqa: E402
import analyst  # noqa: E402
import fidelity_audit as fa  # noqa: E402
import text_norm as tn  # noqa: E402

VOCAB_MIN = 3  # lever-waiver: the self-dictionary's frequency floor for a space-split join (S119 R2, quarantined prototype) — a pipeline lever only if J47 graduates this pass; Rab's word then
_HYPHEN_NL = re.compile(r"(\w)-\n(\w)")
_HYPHEN_SP = re.compile(r"(\w)- (\w)")
_WORD = re.compile(r"[A-Za-z]+")
_PAIR = re.compile(r"(?<![\w-])([a-z]{2,})[ ]([a-z]{2,})(?![\w-])")
_HEAD = re.compile(r"(?m)^(#{1,6})\s+(.*)$")


def build_vocab(text: str) -> Counter:
    return Counter(w.lower() for w in _WORD.findall(text))


def dehyphenate(text: str) -> tuple[str, int]:
    out, n = _HYPHEN_NL.subn(r"\1\2", text)
    return out, n


def join_splits(text: str, vocab: Counter, min_count: int = VOCAB_MIN) -> tuple[str, int, list[str]]:
    joined: list[str] = []

    def _fix(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        ab = a + b
        if vocab[ab] >= min_count and (vocab[a] < min_count or vocab[b] < min_count):
            joined.append(f"{a} {b}->{ab}")
            return ab
        return m.group(0)

    out = _PAIR.sub(_fix, text)
    return out, len(joined), joined


def rule_analyst(chunk: str, vocab: Counter) -> tuple[str, dict]:
    out, n_h = dehyphenate(chunk)
    out, n_s, examples = join_splits(out, vocab)
    return out, {"hyphen_joins": n_h, "space_joins": n_s, "examples": examples[:5]}


def heading_lines(text: str) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2).strip()) for m in _HEAD.finditer(text)]


def main() -> None:
    m, sidecar_text, shipped_body = ddia_pairs.load_bundle()
    m, chunks_in, outs, cs = ddia_pairs.pairs()
    vocab = build_vocab(sidecar_text)
    # --- what the INPUT contains ---
    hy_nl = sum(len(_HYPHEN_NL.findall(c)) for c in chunks_in)
    hy_sp = sum(len(_HYPHEN_SP.findall(c)) for c in chunks_in)
    print(f"INPUT (492 chunks, sidecar): hard line-break hyphenations `w-\\nw`: {hy_nl}; `w- w`: {hy_sp}")
    # --- rule-based pass over all 492 ---
    rb_out: list[str] = []
    tot_h = tot_s = 0
    ex_all: list[str] = []
    surv = []
    for c in chunks_in:
        o, st = rule_analyst(c, vocab)
        rb_out.append(o)
        tot_h += st["hyphen_joins"]
        tot_s += st["space_joins"]
        ex_all += st["examples"]
        s = tn.chunk_survival(c, o)
        if s is not None:
            surv.append(s)
    changed = sum(1 for c, o in zip(chunks_in, rb_out) if c != o)
    print(f"RULE-BASED over 492 chunks: hyphen joins {tot_h}, space-split joins {tot_s}, chunks changed {changed}; "
          f"per-chunk survival min {min(surv)} mean {sum(surv)/len(surv):.4f} over {len(surv)} scoreable chunks; "
          f"examples of space joins: {ex_all[:12]}")
    # document-level audit, the real gate function, rule-based body vs sidecar
    rb_body = analyst.unfence("\n\n".join(rb_out), analyst.fence(sidecar_text)[1])
    a_rb = fa.audit_analyst(sidecar_text, rb_body)
    a_llm = fa.audit_analyst(sidecar_text, shipped_body)
    print(f"DOCUMENT audit_analyst: rule-based doc_survival {a_rb['doc_survival']} runs {a_rb['runs_total']} | "
          f"LLM (shipped) {a_llm['doc_survival']} runs {a_llm['runs_total']} | manifest {m['fidelity']['analyst']['doc_survival']}")
    # --- what the LLM actually did on the ALIGNED PASSED chunks ---
    llm_h = llm_h_possible = 0
    llm_s = 0
    llm_s_possible = 0
    head_in = head_out = 0
    head_level_changed = head_removed = head_added = 0
    n_pairs = 0
    other_changes = 0
    for k, o in enumerate(outs):
        i = k + 1
        if o is None or cs[i].get("x"):
            continue
        c = chunks_in[k]
        n_pairs += 1
        # hyphen joins the LLM performed: each input `a-\nb` whose joined `ab` appears in the output
        for mm in _HYPHEN_NL.finditer(c):
            llm_h_possible += 1
            # the joined token: expand to the surrounding word
            s0 = c.rfind(" ", 0, mm.start()) + 1
            e0 = c.find(" ", mm.end())
            tok = c[s0:e0 if e0 > 0 else None].replace("-\n", "")
            if tok and tok in o:
                llm_h += 1
        # space-split joins the LLM performed (same candidate rule as R-SPLIT)
        _, n_rule, exs = join_splits(c, vocab)
        llm_s_possible += n_rule
        for ex in exs:
            ab = ex.split("->")[1]
            if ab in o:
                llm_s += 1
        hi, ho = heading_lines(c), heading_lines(o)
        head_in += len(hi)
        head_out += len(ho)
        ti = {t for _, t in hi}
        to = {t for _, t in ho}
        head_removed += len(ti - to)
        head_added += len(to - ti)
        li = {t: lv for lv, t in hi}
        lo = {t: lv for lv, t in ho}
        head_level_changed += sum(1 for t in ti & to if li[t] != lo[t])
        # everything else: does the output differ from the rule-based output at all, ignoring whitespace?
        rb, _ = rule_analyst(c, vocab)
        if " ".join(o.split()) != " ".join(rb.split()):
            other_changes += 1
    print(f"LLM on {n_pairs} aligned PASSED chunks: hyphen joins performed {llm_h} of {llm_h_possible} possible; "
          f"space-split joins {llm_s} of {llm_s_possible} the rule would make; headings in {head_in} -> out {head_out} "
          f"(level changed {head_level_changed}, removed {head_removed}, added {head_added}); "
          f"chunks whose output differs from the rule-based output beyond whitespace: {other_changes}")
    (HERE / "results.json").write_text(json.dumps({
        "input_hyphen_nl": hy_nl, "input_hyphen_sp": hy_sp,
        "rule_hyphen_joins": tot_h, "rule_space_joins": tot_s, "rule_chunks_changed": changed,
        "rule_chunk_survival_min": min(surv), "rule_chunk_survival_mean": round(sum(surv) / len(surv), 4),
        "rule_doc_survival": a_rb["doc_survival"], "rule_runs": a_rb["runs_total"],
        "llm_doc_survival": a_llm["doc_survival"], "llm_runs": a_llm["runs_total"],
        "llm_pairs_measured": n_pairs, "llm_hyphen_joins": llm_h, "llm_hyphen_possible": llm_h_possible,
        "llm_space_joins": llm_s, "llm_space_possible": llm_s_possible,
        "headings_in": head_in, "headings_out": head_out, "heading_level_changed": head_level_changed,
        "heading_removed": head_removed, "heading_added": head_added,
        "llm_chunks_differing_from_rule_output": other_changes,
        "vocab_min": VOCAB_MIN, "space_join_examples": ex_all[:30],
    }, indent=1), encoding="utf-8")


def selftest() -> None:
    """NEGATIVE CONTROL: the detectors must FIRE on a planted split, or the zero counts above mean
    nothing. Planted: a hard hyphenation and an 'unexpect edly' space split inside real DDIA prose."""
    m, sidecar_text, shipped_body = ddia_pairs.load_bundle()
    vocab = build_vocab(sidecar_text)
    assert vocab["unexpectedly"] >= VOCAB_MIN, vocab["unexpectedly"]
    planted = "The system failed unexpect edly under load, and the data-" + chr(10) + "base was rebuilt."
    out, st = rule_analyst(planted, vocab)
    assert st["hyphen_joins"] == 1, st
    assert st["space_joins"] == 1, st
    assert "unexpectedly" in out and "database" in out, out
    # the guard: two real words stay two words
    out2, st2 = rule_analyst("the data base of record", vocab)
    assert st2["space_joins"] == 0, (st2, out2)
    # survival of the planted repair is 1.0 under the shipped ladder (the audit cannot see the join)
    s = tn.chunk_survival(planted + " " + " ".join(["w"] * 12), out + " " + " ".join(["w"] * 12))
    print("selftest: detectors fire on planted splits; guard holds on 'data base'; survival of the repair", s)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
