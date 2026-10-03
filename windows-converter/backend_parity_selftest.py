#!/usr/bin/env python3
"""WHAT THIS FILE DOES: selftest for backend_parity.py's judgment functions (unit conversion of ollama vs llama.cpp
timings, prefill-rate censoring, summarise, gate_verdict, order_drift_verdict). Each case is a small function
registered by the @case decorator and run immediately at import; assertion failures are collected and printed. Exit 0
when all nine fired, 1 otherwise. It makes no network, GPU, server or file calls.

Tripwires for the parity harness's judgment functions — offline, no GPU, no servers.

Every case here is a pathology this instrument actually produced in S80–S82, banked so it
cannot return unnoticed. The muster's selftest.sh guards the session open; this guards the
instrument — same doctrine (docs/32 §5, SKILL.md Phase 4): a guard nobody has watched fire is
a proxy with a reputation, so each case VIOLATES the property and asserts the alarm fires.

Run it whenever backend_parity.py changes, and before any record run is trusted:

    python backend_parity_selftest.py
"""
import backend_parity as bp

# -- test harness: the failed list and the @case decorator --
failed: list[str] = []


def case(name):
    """Decorator factory: returns a decorator that runs the test function at once, printing ok/BAD for name and
    adding name to the failed list when an AssertionError is raised."""
    def deco(fn):
        """Run fn now, report the result, and return fn unchanged."""
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"  BAD  {name}: {e or 'assertion failed'}")
        return fn
    return deco


# -- the cases (one decorated function each) --
@case("the unit trap: the same numeral in ollama-ns and llama.cpp-ms differs by 10^6")
def _():
    """The same decode number read through the ollama and llama.cpp parsers differs by a factor of a million."""
    o = bp._phases_ollama({"eval_count": 3, "eval_duration": 82_501_000})
    llamacpp = bp._phases_llamacpp({"timings": {"predicted_n": 3, "predicted_ms": 82_501_000.0}})
    assert abs(o["decode_s"] - 0.082501) < 1e-9, o["decode_s"]
    assert abs(llamacpp["decode_s"] / o["decode_s"] - 1e6) < 1e-3, "the 10^6 boundary moved"


@case("S81: ollama's unseeable cache is None and prints UNREAD, never 0")
def _():
    """A cache count ollama does not report is None and formats as UNREAD."""
    assert bp._phases_ollama({})["cached_tok"] is None
    assert bp.fmt_rate(None) == bp.UNREAD


@case("S81 §10.2: a mostly-cached prompt yields NO prefill rate; the program prefix is tolerated")
def _():
    """A mostly-cached prompt gives no prefill rate; a small shared program prefix still does."""
    cached = {"prefill_tok": 1, "prefill_s": 0.0134, "cached_tok": 524}
    assert bp.prefill_rate(cached) is None, "prompt_n=1 with 524 cached must be withheld"
    prefix = {"prefill_tok": 700, "prefill_s": 0.15, "cached_tok": 90}   # ~11 % shared program
    assert bp.prefill_rate(prefix) is not None


@case("docs/34 rule 6: a rate with no duration is None, not 0.0")
def _():
    """bp.rate returns None whenever the count or the duration is missing or zero."""
    assert bp.rate(100, None) is None
    assert bp.rate(None, 1.0) is None
    assert bp.rate(100, 0) is None


@case("docs/34 rule 3: summarise switches min-max -> p95 at n=20; empty renders UNREAD")
def _():
    """summarise shows min-max for small samples, p95 for 25 samples, and UNREAD for an empty one."""
    small = bp.summarise([1.0] * 5, "x")
    assert "min" in small and "p95" not in small
    assert "p95" in bp.summarise([float(i) for i in range(25)], "x")
    assert bp.UNREAD in bp.summarise([None, None], "x")


@case("S81 §10.1 banked: the 37,729 tok/s warmup artefact is withheld by the arm's own median")
def _():
    """censor_prefill_outliers withholds the one huge warmup reading and keeps the legitimate ones."""
    rows = [{"chunk": i, "prefill_tps": v}
            for i, v in enumerate([4465.4, 4869.0, 4570.8, 37729.3])]
    out = bp.censor_prefill_outliers(rows)
    assert len(out) == 1 and out[0]["chunk"] == 3, "the guard did not fire on the artefact"
    assert rows[3]["prefill_tps"] is None and rows[3].get("prefill_suspect")
    assert rows[0]["prefill_tps"] is not None, "a legitimate reading was withheld"


@case("S82 §10.4 closed: a bad warmup can no longer veto legitimate prefills")
def _():
    """With fewer than three readings there is no reference median, so nothing is withheld."""
    rows = [{"chunk": 88, "prefill_tps": 3093.0}, {"chunk": 176, "prefill_tps": 3285.0}]
    assert bp.censor_prefill_outliers(rows) == [], "n<3 has no reference; nothing may be withheld"
    assert rows[0]["prefill_tps"] and rows[1]["prefill_tps"]


@case("S81 §10.5: the incumbent sets the bar - no worse, not perfect")
def _():
    """gate_verdict passes an arm that matches the incumbent's failures and fails one that is worse."""
    assert bp.gate_verdict(1000, 1000, 0, 0, 1, 1), "matching the incumbent's failure must pass"
    assert not bp.gate_verdict(1000, 1000, 0, 0, 2, 1), "worse than the incumbent must fail"
    assert not bp.gate_verdict(3430, 1000, 0, 0, 0, 1), "the thinking arm's +243% must fail"


@case("SYM-035: +18.1% order drift withholds the ratios; 3% does not")
def _():
    """order_drift_verdict marks an 18 percent drift inadmissible and a 3 percent drift admissible."""
    drift, admissible = bp.order_drift_verdict(74.8, 88.3)
    assert not admissible and abs(drift - 0.1805) < 0.01
    _, admissible2 = bp.order_drift_verdict(100.0, 103.0)
    assert admissible2


# -- the verdict and exit code --
print()
if failed:
    print(f"TRIPWIRES DISARMED - {len(failed)} failed of 9: {failed}")
    raise SystemExit(1)
print("ALL TRIPWIRES FIRED - 9/9")
