#!/usr/bin/env python3
"""Tripwires for the J32-A normalised analyst-stage comparison (docs/15 §9.4, docs/54-repair-
road/README.md §2, signed: Proposal A). Synthetic, CPU-only, no files, no network -- every case
here is a shape the un-normalised audit_analyst got wrong (an escape/punctuation/spacing
difference counted as loss) or must still catch (a real deletion). Same doctrine as
backend_parity_selftest.py: a guard nobody has watched fire is a proxy with a reputation, so
case (g) and (e') VIOLATE the property (disable/revert the ladder) and assert the alarm fires.

Run with the marker-env interpreter (fidelity_audit imports pymupdf/rapidfuzz):
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe analyst_audit_selftest.py

  (a) escape-only difference                 -> survives (doc_survival 1.0)
  (b) punctuation-only difference             -> survives
  (c) spacing-only difference                 -> survives
  (d) a POISONED window (real 12+-word loss)  -> fails; run >= 25 words -> verdict fail
  (e) a backslash before a LETTER is LaTeX (\\rm vs rm is a real loss, THROUGH audit_analyst,
      R5 v2 -- escape-only case (a) still survives)
  (e') negative control: v1's punct_free restored -> case (e) FALSELY green (watched)
  (f) CJK path unchanged (space-free containment still the same rule, no crash)
  (g) negative control: ladder disabled       -> case (a) FAILS (watched)
  (h) S131: a degenerate block in the REFERENCE is masked -> a body without it reads 1.0,
      no run, and the mask is recorded (docs/15 §12.1, Rab signed 2026-09-12)
  (i) S131: a REAL loss beside the mask still fails (the gate is not blunted)
  (j) negative control: the mask disabled     -> case (h) FAILS the way S130 did (watched)
  (k) S131: a body that KEPT the loop is not rewarded -- the convert gate's degeneration
      tripwire still fails it; the mask only ever removes reference text
  (l) S131: a CRLF reference masks the same block as its LF twin (the fleet's refutation,
      closed in the mask; degeneration() itself is untouched)
"""
import os
import shutil
import tempfile

# J44 (S182): the ladder lever is a file under the pipeline root -- this suite must never read the LIVE tree's
# lever (a `j32a-v3` there would silently run every case under v3). A throwaway root, removed at the end.
_QUARANTINE = tempfile.mkdtemp(prefix="fp-ladder-selftest-")
os.environ["FP_PIPELINE"] = _QUARANTINE

import text_norm as tn  # noqa: E402  (env must be set first)
import fidelity_audit as fa  # noqa: E402
import ladder_lever  # noqa: E402
import fp_paths  # noqa: E402

failed: list[str] = []
ran: list[str] = []


def case(name):
    def deco(fn):
        ran.append(name)
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"  BAD  {name}: {e or 'assertion failed'}")
        return fn
    return deco


def words(n, prefix="alpha"):
    return " ".join(f"{prefix}{i:02d}" for i in range(1, n + 1))


@case("(a) escape-only difference survives (marker's own \\( \\) escapes)")
def _():
    ref = "the committee met in \\(1960-2023\\) to review the annual budget carefully"
    out = "the committee met in (1960-2023) to review the annual budget carefully"
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] == 1.0, block
    assert block["runs_total"] == 0, block
    assert block["normalisation"] == {"unescape": True, "punct_free": True,
                                      "space_free": True, "regex_id": "j32a-v2"}, block


@case("(b) punctuation-only difference survives (a dropped comma)")
def _():
    ref = "the committee, met in the annual budget report today"
    out = "the committee met in the annual budget report today"
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] == 1.0, block


@case("(c) spacing-only difference survives (double spaces / a line break)")
def _():
    ref = "the  committee   met\nin the annual budget report today"
    out = "the committee met in the annual budget report today"
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] == 1.0, block


@case("(d) a POISONED window (a real deletion) fails, and a run >= 25 words fails the verdict")
def _():
    ref = words(60)
    tok = ref.split()
    # drop windows 1, 2 and 3 (0-based, 12 words each) -- 36 real words gone, so the run is
    # BOTH long enough to trip ANALYST_RUN_WORDS on its own AND drags doc_survival to 0.4,
    # so the assertion below is not accidentally passing on the wrong half of the OR.
    out = " ".join(tok[0:12] + tok[48:60])
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] < 0.995, block
    assert block["runs_total"] >= 1 and any(r["words"] >= 25 for r in block["runs"]), block
    verdict = fa.compute_verdict(
        {"tripwires": {"degeneration": False}, "kind": "fidelity", "doc_survival": 1.0,
         "runs": [], "pages_flagged": []}, block)
    assert verdict == "fail", verdict


@case("(e) a backslash before a LETTER is LaTeX and stays -- THROUGH fa.audit_analyst (R5): "
      "'\\rm' vs 'rm' is a real content loss, the escape-only case still survives")
def _():
    # v1 (before R5): punct_free's [^\w\s] deleted every backslash unconditionally, so
    # unescape()'s letter-vs-punctuation distinction never reached a comparison -- \rm and rm
    # compared identical, the exact outcome the ticket rejected. This asserts through the real
    # audit path, not tn.unescape() in isolation, so a regression here is caught where it
    # actually matters.
    ref = "the committee used the \\rm command to typeset the annual budget report carefully"
    out = "the committee used the rm command to typeset the annual budget report carefully"
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] < 1.0, block
    # the escape-only case (a) is untouched by this fix -- \(1960-2023\) still survives as
    # (1960-2023), because unescape (not punct_free) is the one function allowed to drop that
    # backslash, and it does so BEFORE punctuation exactly as before.
    ref2 = "the committee met in \\(1960-2023\\) to review the annual budget carefully"
    out2 = "the committee met in (1960-2023) to review the annual budget carefully"
    block2 = fa.audit_analyst(ref2, out2)
    assert block2["doc_survival"] == 1.0, block2


@case("(e') NEGATIVE CONTROL: restore v1's punct_free ([^\\w\\s], backslash NOT excluded) -> "
      "case (e) goes falsely green")
def _():
    import re as _re
    _v1_punct = _re.compile(r"[^\w\s]", _re.UNICODE)

    def _v1_punct_free(t):
        return tn._WS.sub(" ", _v1_punct.sub("", t)).strip()

    real_punct_free = fa.punct_free
    try:
        fa.punct_free = _v1_punct_free
        ref = "the committee used the \\rm command to typeset the annual budget report carefully"
        out = "the committee used the rm command to typeset the annual budget report carefully"
        block = fa.audit_analyst(ref, out)
        assert block["doc_survival"] == 1.0, (
            "the guard did not fire: restoring v1's punct_free should have made \\rm vs rm "
            "read as agreement again", block)
    finally:
        fa.punct_free = real_punct_free
    # restored: case (e) must fail (doc_survival < 1.0) again
    ref = "the committee used the \\rm command to typeset the annual budget report carefully"
    out = "the committee used the rm command to typeset the annual budget report carefully"
    assert fa.audit_analyst(ref, out)["doc_survival"] < 1.0


@case("(f) the CJK path is unchanged: space-free containment, ladder applied, no crash")
def _():
    ref = "这是一个测试用的中文段落用来验证窗口切分与空格无关的匹配规则是否正常工作的情况"
    out = "这是一个测试用的中文段落，用来验证窗口切分与空格无关的匹配规则是否正常工作的情况。"
    assert tn.is_cjk(ref), "fixture must classify as CJK for this case to test anything"
    block = fa.audit_analyst(ref, out)
    assert block["doc_survival"] == 1.0, block
    # a real CJK deletion still fails -- the unification did not blunt the gate
    out_poisoned = ref[:10] + ref[34:]
    block2 = fa.audit_analyst(ref, out_poisoned)
    assert block2["doc_survival"] < 1.0, block2


@case("(g) NEGATIVE CONTROL: the WHOLE ladder disabled (regex_id 'none') -> case (a) now FAILS")
def _():
    # PRE-R5 this comment read "disabling unescape ALONE proves nothing": punct_free's old
    # [^\w\s] regex deleted every backslash regardless of what unescape already did to it, so
    # punct_free(unescape(x)) == punct_free(x) for any x and the two steps were one pipeline,
    # not two independent tripwires (docs/15 SS9.4's residual finding). R5 excluded the
    # backslash from punct_free's deletion set, so that is NO LONGER TRUE -- disabling unescape
    # alone now breaks case (a) too (Observed: doc_survival 0.0, not 1.0). This control still
    # disables BOTH rungs at once (regex_id "none" in the ticket's own words) because that
    # remains the exact PRE-J32-A behaviour this ticket replaces: bare prepare_output
    # containment, where Marker's own backslash choices read as loss regardless of which single
    # rung a narrower control might have exercised.
    real_unescape, real_punct_free = fa.unescape, fa.punct_free
    try:
        fa.unescape = lambda t: t
        fa.punct_free = lambda t: t
        ref = "the committee met in \\(1960-2023\\) to review the annual budget carefully"
        out = "the committee met in (1960-2023) to review the annual budget carefully"
        block = fa.audit_analyst(ref, out)
        assert block["doc_survival"] < 1.0, (
            "the guard did not fire: disabling the ladder should have broken case (a)", block)
    finally:
        fa.unescape, fa.punct_free = real_unescape, real_punct_free
    # restored: case (a) must pass again
    ref = "the committee met in \\(1960-2023\\) to review the annual budget carefully"
    out = "the committee met in (1960-2023) to review the annual budget carefully"
    assert fa.audit_analyst(ref, out)["doc_survival"] == 1.0


# S131 fixtures: Marker's loop, as the Zero to One sidecar carried it -- a heading that repeats
# a trigram hundreds of times (zlib << DEGEN_ZLIB_MAX, trigram >> DEGEN_TRIGRAM_MAX).
LOOP = "# INTERNATIONAL PROPERTY " + "AND ROUTE " * 200
PARA_A = words(40, "alpha")
PARA_B = words(40, "beta")
REF_WITH_LOOP = PARA_A + "\n\n" + LOOP + "\n\n" + PARA_B
CONVERT_OK = {"tripwires": {"degeneration": False}, "kind": "fidelity", "doc_survival": 1.0,
              "runs": [], "pages_flagged": []}


@case("(h) S131: a degenerate block in the REFERENCE is masked -- a body without it reads 1.0, "
      "no run, and reference_masked names the block")
def _():
    assert fa.degeneration(REF_WITH_LOOP)["flagged"], "fixture must trip the detector on its own"
    block = fa.audit_analyst(REF_WITH_LOOP, PARA_A + "\n\n" + PARA_B)
    assert block["doc_survival"] == 1.0, block
    assert block["runs_total"] == 0, block
    rm = block["reference_masked"]
    assert len(rm["blocks"]) == 1, rm
    assert rm["blocks"][0]["line"] == 3 and rm["blocks"][0]["line_end"] == 3, rm
    assert rm["blocks"][0]["chars"] == len(LOOP.strip()), rm   # chars of the STRIPPED block
    assert rm["words"] == len(LOOP.split()), rm
    assert fa.compute_verdict(CONVERT_OK, block) == "pass", block


@case("(m) S144 audit/verdict-weighs-denominator: a convert block whose witness scored 1 page of 465 "
      "reads flag, never pass; a block covering 400 of 465 passes; a block with no page counts (pre-S144) "
      "is unchanged")
def _():
    # Rab's word (Desk bf4d5d05); born of S142 E1 F5 — Valentine's scan read `1.0 over 1 page` as a pass-shaped
    # number. A witness that saw under half the book localises nothing; the verdict weighs its denominator.
    thin = dict(CONVERT_OK, pages_scored=1, pages_total=465)
    assert fa.compute_verdict(thin, None) == "flag", thin
    wide = dict(CONVERT_OK, pages_scored=400, pages_total=465)
    assert fa.compute_verdict(wide, None) == "pass", wide
    edge = dict(CONVERT_OK, pages_scored=233, pages_total=465)   # 0.501: at the floor, not under it
    assert fa.compute_verdict(edge, None) == "pass", edge
    assert fa.compute_verdict(dict(CONVERT_OK), None) == "pass"   # no counts: the old blocks' verdicts stand
    # the negative control: a thin witness never LIFTS a fail — degeneration still fails first
    degen = dict(thin, tripwires={"degeneration": True})
    assert fa.compute_verdict(degen, None) == "fail", degen


@case("(i) S131: a REAL loss beside the mask still fails -- the whole of PARA_B gone reads as a "
      "run >= 25 words and the verdict is fail")
def _():
    block = fa.audit_analyst(REF_WITH_LOOP, PARA_A)
    assert block["doc_survival"] < 0.995, block
    assert any(r["words"] >= 25 for r in block["runs"]), block
    assert "beta01" in block["runs"][0]["excerpt"], block   # the run is the real loss, not the loop
    assert block["reference_masked"]["words"] == len(LOOP.split()), block
    assert fa.compute_verdict(CONVERT_OK, block) == "fail"


@case("(j) NEGATIVE CONTROL: the mask disabled -> case (h)'s body FAILS the way S130 did "
      "(the loop counted as a run of hundreds of words)")
def _():
    real_mask = fa.mask_degenerate_reference
    try:
        fa.mask_degenerate_reference = lambda t: (t, {"blocks": [], "words": 0})
        block = fa.audit_analyst(REF_WITH_LOOP, PARA_A + "\n\n" + PARA_B)
        assert block["doc_survival"] < 0.995, (
            "the guard did not fire: with the mask off the loop should read as loss", block)
        assert any(r["words"] >= 25 for r in block["runs"]), block
        assert fa.compute_verdict(CONVERT_OK, block) == "fail"
    finally:
        fa.mask_degenerate_reference = real_mask
    # restored: case (h) must pass again
    assert fa.audit_analyst(REF_WITH_LOOP, PARA_A + "\n\n" + PARA_B)["doc_survival"] == 1.0


@case("(k) S131: a body that KEPT the loop is not rewarded -- the mask glues the loop's "
      "neighbours in the reference, so the body's extra block costs it the seam windows "
      "(a dip, never a run), and the convert gate's degeneration tripwire still fails it")
def _():
    body = PARA_A + "\n\n" + LOOP + "\n\n" + PARA_B
    block = fa.audit_analyst(REF_WITH_LOOP, body)
    clean = fa.audit_analyst(REF_WITH_LOOP, PARA_A + "\n\n" + PARA_B)
    assert block["doc_survival"] <= clean["doc_survival"] == 1.0, (block, clean)
    assert block["runs_total"] == 0, block          # the seam never manufactures a run
    conv = {"tripwires": {"degeneration": fa.degeneration(body)["flagged"]}, "kind": "fidelity",
            "doc_survival": 1.0, "runs": [], "pages_flagged": []}
    assert conv["tripwires"]["degeneration"] is True, conv
    assert fa.compute_verdict(conv, block) == "fail"
    # and a reference with no degenerate block is left byte-identical, nothing masked
    clean_ref = PARA_A + "\n\n" + PARA_B
    assert fa.mask_degenerate_reference(clean_ref) == (clean_ref, {"blocks": [], "words": 0})


@case("(l) S131: a CRLF reference masks the same block as its LF twin -- same block report, "
      "same words, and the clean body reads 1.0 either way")
def _():
    crlf_ref = REF_WITH_LOOP.replace("\n", "\r\n")
    _lf_text, lf_report = fa.mask_degenerate_reference(REF_WITH_LOOP)
    crlf_text, crlf_report = fa.mask_degenerate_reference(crlf_ref)
    assert crlf_report == lf_report and len(crlf_report["blocks"]) == 1, (crlf_report, lf_report)
    assert "AND ROUTE" not in crlf_text, "the loop survived the CRLF mask"
    assert fa.audit_analyst(crlf_ref, PARA_A + "\n\n" + PARA_B)["doc_survival"] == 1.0
    # a CRLF reference with nothing to mask comes back byte-identical, CR and all
    clean_crlf = (PARA_A + "\n\n" + PARA_B).replace("\n", "\r\n")
    assert fa.mask_degenerate_reference(clean_crlf) == (clean_crlf, {"blocks": [], "words": 0})


# ---------------------------------------------------------------- J44 (S182): ladder v3 behind a lever, OFF
SYM076_REF = "the planner rewrites the call to within\\_recursive before the optimiser sees the subquery plan at all here"
SYM076_OUT = "the planner rewrites the call to within_recursive before the optimiser sees the subquery plan at all here"


@case("(m) J44 rung 1: the SYM-076 specimen -- `within\\_recursive` vs `within_recursive` reads 0.0 under v2 "
      "(the defect reproduced) and 1.0 under v3 (the escape set gains the underscore)")
def _():
    assert fa.audit_analyst(SYM076_REF, SYM076_OUT, ladder="j32a-v2")["doc_survival"] == 0.0
    v3 = fa.audit_analyst(SYM076_REF, SYM076_OUT, ladder="j32a-v3")
    assert v3["doc_survival"] == 1.0 and v3["normalisation"]["regex_id"] == "j32a-v3", v3


@case("(n) J44 keeps R5 under v3: `\\rm` vs `rm` is STILL a real loss (1 of 2 windows) under both ladders -- the underscore is the only "
      "addition to the escape set")
def _():
    ref = "the macro expands to \\rm before the layout pass and the renderer then reads it back as text"
    out = "the macro expands to rm before the layout pass and the renderer then reads it back as text"
    v3, v2 = fa.audit_analyst(ref, out, ladder="j32a-v3"), fa.audit_analyst(ref, out, ladder="j32a-v2")
    # 18 words = two windows (12 + a kept 6); the first carries `\\rm` and fails under BOTH ladders: 1 of 2 survives
    assert v3["doc_survival"] == v2["doc_survival"] == 0.5 and v3["windows_total"] == 2, (v3, v2)


CITE_REF = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [\\[2\\]](#page-49-0) "
            "nu xi omicron pi rho sigma tau upsilon phi chi psi omega")
CITE_OUT = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [2](#page-49-0) "
            "nu xi omicron pi rho sigma tau upsilon phi chi psi omega")


@case("(o) J44 rung 3: Marker's `[\\[n\\]](#page-N-K)` vs the model's `[n](#page-N-K)` -- a failed window under v2, "
      "1.0 under v3; and a DELETED tail under v3 still fails (the rung rescues no deletion)")
def _():
    assert fa.audit_analyst(CITE_REF, CITE_OUT, ladder="j32a-v2")["doc_survival"] < 1.0
    assert fa.audit_analyst(CITE_REF, CITE_OUT, ladder="j32a-v3")["doc_survival"] == 1.0
    deleted = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu [2](#page-49-0)"
    assert fa.audit_analyst(CITE_REF, deleted, ladder="j32a-v3")["doc_survival"] == 0.5


@case("(o') negative control: v3's rungs disabled (prepare_for reverted to prepare_output) -> (m) and (o) FAIL under "
      "the v3 id -- the rungs, not the id, are what passes them (watched)")
def _():
    saved = fa.prepare_for
    fa.prepare_for = lambda md, ladder="j32a-v2": tn.prepare_output(md)
    try:
        assert fa.audit_analyst(SYM076_REF, SYM076_OUT, ladder="j32a-v3")["doc_survival"] == 0.0
        assert fa.audit_analyst(CITE_REF, CITE_OUT, ladder="j32a-v3")["doc_survival"] < 1.0
    finally:
        fa.prepare_for = saved


@case("(p) J44 the lever: absent -> v2; garbage -> v2; `J32A-V3` (case, whitespace) -> v3; audit_analyst with no "
      "ladder named READS the file; chunk_survival takes the same id; an unknown id given by hand RAISES")
def _():
    lever = fp_paths.root("ladder")
    lever.unlink(missing_ok=True)
    assert ladder_lever.read_ladder() == "j32a-v2"
    lever.write_text("j32a-v9\n", encoding="utf-8")
    assert ladder_lever.read_ladder() == "j32a-v2"
    lever.write_text("  J32A-V3 \n", encoding="utf-8")
    assert ladder_lever.read_ladder() == "j32a-v3"
    block = fa.audit_analyst(SYM076_REF, SYM076_OUT)
    assert block["doc_survival"] == 1.0 and block["normalisation"]["regex_id"] == "j32a-v3", block
    assert tn.chunk_survival(SYM076_REF, SYM076_OUT, ladder="j32a-v3") == 1.0
    assert tn.chunk_survival(SYM076_REF, SYM076_OUT) == 0.0  # the pure function's default is v2, always
    lever.unlink()
    block = fa.audit_analyst(SYM076_REF, SYM076_OUT)
    assert block["doc_survival"] == 0.0 and block["normalisation"]["regex_id"] == "j32a-v2", block
    try:
        tn.prepare_for("x", "j32a-v9")
        raise AssertionError("an unknown ladder id must raise in the pure function")
    except ValueError:
        pass


@case("(q) POSITIVE CONTROL: under v2 -- the default, the lever absent -- every shape the suite knows is BYTE-IDENTICAL "
      "to prepare_output, chunk_survival and audit_analyst read what they read before J44 (the shipped numbers do not move)")
def _():
    shapes = [
        "the committee met in \\(1960-2023\\) to review the annual budget carefully",
        "a heading\n\n# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nsee [the paper](http://x/y) and ![img](a.png) plus `code` and *em*",
        SYM076_REF, CITE_REF, "漢字の文章は空白なしで続きます。これは十分に長い文である。",
        "the macro expands to \\rm before the layout pass",
    ]
    for s in shapes:
        assert tn.prepare_for(s, "j32a-v2") == tn.prepare_output(s) == tn.prepare_for(s), s
    for a, b in ((SYM076_REF, SYM076_OUT), (CITE_REF, CITE_OUT), (shapes[0], shapes[0].replace("\\", ""))):
        assert tn.chunk_survival(a, b) == tn.chunk_survival(a, b, ladder="j32a-v2")
        blk = fa.audit_analyst(a, b)
        assert blk == fa.audit_analyst(a, b, ladder="j32a-v2") and blk["normalisation"]["regex_id"] == "j32a-v2"


shutil.rmtree(_QUARANTINE, ignore_errors=True)

@case("(v) SYM-138: a stacked table header the analyst merged into one row reads as a REORDER (report-only), a deleted one as an omission")
def _():
    pre, post = words(24, "pre"), words(24, "post")
    raw = ("| | Less than | 1 to 3 | | 3 to 6 | 6 months | Up to 1 | Over 1 to | Over |\n"
           "| | 1 month | months | | months | to 1 year | year | 2 years | 2 years |")
    merged = "| | Less than 1 month | 1 to 3 months | | 3 to 6 months | 6 months to 1 year | Up to 1 year | Over 1 to 2 years | Over 2 years | Total | Total |"
    ref = pre + "\n" + raw + "\n" + post
    block = fa.audit_analyst(ref, pre + "\n" + merged + "\n" + post)
    assert block["runs_total"] == 1, block
    run = block["runs"][0]
    assert run["reorder"] is True and run["words"] >= 24, block
    assert block["runs_reorder"] == 1 and block["words_reorder"] == run["words"], block
    assert block["doc_survival"] < 1.0, block          # report-only: the run still counts against the number
    ctl = fa.audit_analyst(ref, pre + "\n" + post)      # the control: the two rows DELETED — an omission, never a reorder
    assert ctl["runs_total"] == 1 and ctl["runs"][0]["reorder"] is False and ctl["runs_reorder"] == 0 and ctl["words_reorder"] == 0, ctl
    clean = fa.audit_analyst(ref, ref)
    assert clean["runs_reorder"] == 0 and clean["words_reorder"] == 0 and clean["runs"] == [], clean


print()
if failed:
    print(f"TRIPWIRES DISARMED — {len(failed)} failed of {len(ran)}: {failed}")
    raise SystemExit(1)
print(f"ALL TRIPWIRES FIRED — {len(ran)}/{len(ran)}")
