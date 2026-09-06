#!/usr/bin/env python3
"""Tripwires for the parity harness's judgment functions — offline, no GPU, no servers.

Every case here is a pathology this instrument actually produced in S80–S82, banked so it
cannot return unnoticed. The muster's selftest.sh guards the session open; this guards the
instrument — same doctrine (docs/32 §5, SKILL.md Phase 4): a guard nobody has watched fire is
a proxy with a reputation, so each case VIOLATES the property and asserts the alarm fires.

Run it whenever backend_parity.py changes, and before any record run is trusted:

    python backend_parity_selftest.py
"""
import backend_parity as bp

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


@case("the unit trap: the same numeral in ollama-ns and llama.cpp-ms differs by 10^6")
def _():
    o = bp._phases_ollama({"eval_count": 3, "eval_duration": 82_501_000})
    llamacpp = bp._phases_llamacpp({"timings": {"predicted_n": 3, "predicted_ms": 82_501_000.0}})
    assert abs(o["decode_s"] - 0.082501) < 1e-9, o["decode_s"]
    assert abs(llamacpp["decode_s"] / o["decode_s"] - 1e6) < 1e-3, "the 10^6 boundary moved"


@case("S81: ollama's unseeable cache is None and prints UNREAD, never 0")
def _():
    assert bp._phases_ollama({})["cached_tok"] is None
    assert bp.fmt_rate(None) == bp.UNREAD


@case("S81 §10.2: a mostly-cached prompt yields NO prefill rate; the program prefix is tolerated")
def _():
    cached = {"prefill_tok": 1, "prefill_s": 0.0134, "cached_tok": 524}
    assert bp.prefill_rate(cached) is None, "prompt_n=1 with 524 cached must be withheld"
    prefix = {"prefill_tok": 700, "prefill_s": 0.15, "cached_tok": 90}   # ~11 % shared program
    assert bp.prefill_rate(prefix) is not None


@case("docs/34 rule 6: a rate with no duration is None, not 0.0")
def _():
    assert bp.rate(100, None) is None
    assert bp.rate(None, 1.0) is None
    assert bp.rate(100, 0) is None


@case("docs/34 rule 3: summarise switches min-max -> p95 at n=20; empty renders UNREAD")
def _():
    small = bp.summarise([1.0] * 5, "x")
    assert "min" in small and "p95" not in small
    assert "p95" in bp.summarise([float(i) for i in range(25)], "x")
    assert bp.UNREAD in bp.summarise([None, None], "x")


@case("S81 §10.1 banked: the 37,729 tok/s warmup artefact is withheld by the arm's own median")
def _():
    rows = [{"chunk": i, "prefill_tps": v}
            for i, v in enumerate([4465.4, 4869.0, 4570.8, 37729.3])]
    out = bp.censor_prefill_outliers(rows)
    assert len(out) == 1 and out[0]["chunk"] == 3, "the guard did not fire on the artefact"
    assert rows[3]["prefill_tps"] is None and rows[3].get("prefill_suspect")
    assert rows[0]["prefill_tps"] is not None, "a legitimate reading was withheld"


@case("S82 §10.4 closed: a bad warmup can no longer veto legitimate prefills")
def _():
    rows = [{"chunk": 88, "prefill_tps": 3093.0}, {"chunk": 176, "prefill_tps": 3285.0}]
    assert bp.censor_prefill_outliers(rows) == [], "n<3 has no reference; nothing may be withheld"
    assert rows[0]["prefill_tps"] and rows[1]["prefill_tps"]


@case("S81 §10.5: the incumbent sets the bar - no worse, not perfect")
def _():
    assert bp.gate_verdict(1000, 1000, 0, 0, 1, 1), "matching the incumbent's failure must pass"
    assert not bp.gate_verdict(1000, 1000, 0, 0, 2, 1), "worse than the incumbent must fail"
    assert not bp.gate_verdict(3430, 1000, 0, 0, 0, 1), "the thinking arm's +243% must fail"


@case("SYM-035: +18.1% order drift withholds the ratios; 3% does not")
def _():
    drift, admissible = bp.order_drift_verdict(74.8, 88.3)
    assert not admissible and abs(drift - 0.1805) < 0.01
    _, admissible2 = bp.order_drift_verdict(100.0, 103.0)
    assert admissible2


print()
if failed:
    print(f"TRIPWIRES DISARMED - {len(failed)} failed of 9: {failed}")
    raise SystemExit(1)
print("ALL TRIPWIRES FIRED - 9/9")
