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
import text_norm as tn
import fidelity_audit as fa

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


print()
if failed:
    print(f"TRIPWIRES DISARMED — {len(failed)} failed of {len(ran)}: {failed}")
    raise SystemExit(1)
print(f"ALL TRIPWIRES FIRED — {len(ran)}/{len(ran)}")
