#!/usr/bin/env python3
"""Tripwires for the J32-A normalised analyst-stage comparison (docs/15 §9.4, docs/54-repair-
road/README.md §2, signed: Proposal A). Synthetic, CPU-only, no files, no network -- every case
here is a shape the un-normalised audit_analyst got wrong (an escape/punctuation/spacing
difference counted as loss) or must still catch (a real deletion). Same doctrine as
backend_parity_selftest.py: a guard nobody has watched fire is a proxy with a reputation, so
case (g) VIOLATES the property (disables the ladder) and asserts the alarm fires.

Run with the marker-env interpreter (fidelity_audit imports pymupdf/rapidfuzz):
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe analyst_audit_selftest.py

  (a) escape-only difference                 -> survives (doc_survival 1.0)
  (b) punctuation-only difference             -> survives
  (c) spacing-only difference                 -> survives
  (d) a POISONED window (real 12+-word loss)  -> fails; run >= 25 words -> verdict fail
  (e) a backslash before a LETTER is untouched (\\rm stays \\rm, never unescaped)
  (f) CJK path unchanged (space-free containment still the same rule, no crash)
  (g) negative control: ladder disabled       -> case (a) FAILS (watched)
"""
import text_norm as tn
import fidelity_audit as fa

failed: list[str] = []


def case(name):
    def deco(fn):
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
                                      "space_free": True, "regex_id": "j32a-v1"}, block


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


@case("(e) a backslash before a LETTER is LaTeX and stays (\\rm is never unescaped)")
def _():
    out = tn.unescape("the \\rm command and \\alpha symbol stay, but \\(this\\) does not")
    assert "\\rm" in out and "\\alpha" in out, out
    assert "\\(" not in out and "\\)" not in out, out


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
    # Disabling unescape ALONE proves nothing here: punct_free deletes every backslash
    # regardless of what unescape already did to it (punct_free's [^\w\s] class matches a
    # backslash unconditionally), so punct_free(unescape(x)) == punct_free(x) for any x --
    # the two steps are not independent tripwires, they are one pipeline. The control that
    # actually exercises "the ladder" is disabling BOTH rungs at once (regex_id "none" in
    # the ticket's own words), which is exactly the PRE-J32-A behaviour this ticket replaces:
    # bare prepare_output containment, where Marker's own backslash choices read as loss.
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


print()
if failed:
    print(f"TRIPWIRES DISARMED — {len(failed)} failed of 7: {failed}")
    raise SystemExit(1)
print("ALL TRIPWIRES FIRED — 7/7")
