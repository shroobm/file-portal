#!/usr/bin/env python3
"""Tripwires for analyst.process's per-chunk accept-time guards: J32-B (the per-chunk INPUT-
WINDOW survival guard, threshold 0.50, action reject, signed Rab 2026-09-05), SYM-074 (the
`</think>` leak guard) and J34 (the output/input word-ratio INFLATION guard, threshold 1.5,
action reject, signed Rab 2026-09-05 "J34 1.5x reject"). Synthetic, CPU-only, no GPU, no
ollama, no network -- every `_generate`
call is monkeypatched to a scripted stand-in. FP_PIPELINE is pointed at a temp dir BEFORE import
so ANALYST_WORK (the S61 chunk-resume journal dir) and every other fp_paths root land in
quarantine, never the live library (SYM-010's class).

Run with the marker-env interpreter:
    C:\\Users\\Bndit\\ml\\marker-env\\Scripts\\python.exe analyst_selftest.py

  J32-B (a) faithful reflow (hyphen/punctuation only)   -> passed, survival ~= 1.0
  J32-B (b) candidate drops 3 of 5 paragraphs            -> rejected (survival < 0.50)
  J32-B (c) the runaway shape (a short phrase looped)    -> rejected (survival)
  J32-B (d) journal round-trip: reason + survival; an old-shape record still resumes
  J32-B (e) a chunk with 0 windows (short)               -> passed, survival None
  J32-B (f) NEGATIVE CONTROL: threshold monkeypatched to 0.0 -> (b)'s candidate now PASSES
  J32-B (g) the fence still fires first: an IMG-token change is "fence", not "survival"
  SYM-074 (a) a candidate carrying </think> (else identical) -> rejected, reason think_leak
  SYM-074 (b) the plain word "think" in prose             -> passed (not over-broad)
  SYM-074 (c) an opening <think> alone                    -> rejected
  SYM-074 (d) NEGATIVE CONTROL: the think-leak guard removed -> (a)'s candidate now PASSES
  J34 (a) a 2x verbatim duplicate: survival 1.0 (J32-B blind)   -> rejected, reason inflation
  J34 (b) a faithful rewrite at ~1.09x                          -> passed
  J34 (c) NEGATIVE CONTROL: lever monkeypatched to inf -> (a)'s duplicate now PASSES
  J34 (d) survival fires first: a deletion is "survival", never a low ratio
  J34 (e) the lever's edge is strict: 1.4889 passes, 1.5111 rejects
  J34 (f) journal round-trip carries ratio; 0 input words -> ratio None, never a reject
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).parent
QUARANTINE = Path(tempfile.mkdtemp(prefix="fp-analyst-selftest-"))
os.environ["FP_PIPELINE"] = str(QUARANTINE)
sys.path.insert(0, str(HERE))

import analyst  # noqa: E402  (env must be set first -- ANALYST_WORK is frozen at import)
import text_norm as tn  # noqa: E402

analyst.unload = lambda: None  # never touch a real ollama server

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


def words(n, prefix="tok"):
    return " ".join(f"{prefix}{i:02d}" for i in range(1, n + 1))


def scripted(candidates):
    """A _generate stand-in that ignores the prompt and returns the next scripted candidate,
    in call order -- one call per chunk, exactly the shape process() drives it with."""
    calls = {"i": 0}

    def gen(prompt):
        idx = calls["i"]
        calls["i"] += 1
        return candidates[idx]
    return gen


def run(markdown, candidates, module=analyst):
    """Run module.process() with _generate scripted; restores the real _generate after."""
    real_gen = module._generate
    module._generate = scripted(candidates)
    try:
        return module.process(markdown, backend="local")
    finally:
        module._generate = real_gen


# ---------------------------------------------------------------------------
# J32-B
# ---------------------------------------------------------------------------
@case("J32-B (a) faithful reflow (hyphen fix + punctuation only) -> passed, survival ~= 1.0")
def _():
    md = ("The committee met in Septem-\nber to review the annual budget, carefully, "
          "and approved the plan unanimously today for everyone involved in the project")
    candidate = ("The committee met in September to review the annual budget carefully "
                "and approved the plan unanimously today for everyone involved in the project")
    fenced, _ = analyst.fence(md)
    survival = tn.chunk_survival(fenced, candidate)
    assert survival is not None and survival >= 0.95, survival
    out, meta = run(md, [candidate])
    assert meta["chunks_passed"] == 1 and meta["chunks_rejected"] == 0, meta
    assert meta["rejections"] == {"fence": 0, "survival": 0, "think_leak": 0, "inflation": 0}, meta
    assert out.strip() == candidate.strip(), out


B_MD = "\n\n".join([words(15, f"para{p}tok") for p in range(1, 6)])  # 5 distinct paragraphs


@case("J32-B (b) candidate drops 3 of 5 paragraphs -> rejected (survival < 0.50)")
def _():
    paras = B_MD.split("\n\n")
    candidate = "\n\n".join(paras[:2])  # only the first 2 of 5 survive
    out, meta = run(B_MD, [candidate])
    assert meta["chunks_passed"] == 0 and meta["chunks_rejected"] == 1, meta
    assert meta["rejections"] == {"fence": 0, "survival": 1, "think_leak": 0, "inflation": 0}, meta
    assert out.strip() == B_MD.strip(), "the ORIGINAL chunk must ship, not the candidate"


@case("J32-B (c) the runaway shape (a short phrase looped 441x) -> rejected (survival)")
def _():
    md = words(30, "alpha")
    candidate = "{1 - t} " * 441  # SYM-056's shape: shares almost no words with the input
    out, meta = run(md, [candidate])
    assert meta["chunks_rejected"] == 1 and meta["rejections"]["survival"] == 1, meta
    assert out.strip() == md.strip()


@case("J32-B (d) journal round-trip carries reason + survival; an old-shape record still resumes")
def _():
    work = QUARANTINE / "journal-roundtrip"
    work.mkdir(parents=True, exist_ok=True)
    jpath = work / "chunks.jsonl"
    chunk_text = "some chunk text for the hash"
    with open(jpath, "w", encoding="utf-8") as h:
        # new-shape record: reason + survival ride the line
        analyst._append_journal(h, 1, chunk_text, "rejected", chunk_text,
                                reason="survival", survival=0.31)
        # old-shape record (08-30 journal): no reason, no survival key at all
        h.write(json.dumps({"i": 2, "hash": analyst._chunk_hash("second chunk"),
                            "status": "passed", "text": "second chunk"}) + "\n")
    loaded = analyst._load_journal(jpath, [chunk_text, "second chunk"])
    assert loaded[1]["reason"] == "survival" and loaded[1]["survival"] == 0.31, loaded[1]
    assert loaded[2].get("reason") is None and loaded[2].get("survival") is None, loaded[2]
    assert loaded[2]["status"] == "passed", "an old-shape record still resumes"


@case("J32-B (e) a chunk with 0 windows (short) -> passed, survival None")
def _():
    md = "Hi there"  # 2 words -- below WINDOW_MIN_WORDS, make_windows returns []
    fenced, _ = analyst.fence(md)
    assert tn.chunk_survival(fenced, "Hi there indeed") is None
    out, meta = run(md, ["Hi there indeed"])
    assert meta["chunks_passed"] == 1 and meta["chunks_rejected"] == 0, meta


@case("J32-B (f) NEGATIVE CONTROL: threshold -> 0.0 makes (b)'s candidate PASS (watched)")
def _():
    paras = B_MD.split("\n\n")
    candidate = "\n\n".join(paras[:2])
    real_threshold = analyst.ANALYST_CHUNK_SURVIVAL_MIN
    try:
        analyst.ANALYST_CHUNK_SURVIVAL_MIN = 0.0
        out, meta = run(B_MD, [candidate])
        assert meta["chunks_passed"] == 1 and meta["chunks_rejected"] == 0, (
            "the guard did not fire: threshold 0.0 should have let the deletion through", meta)
    finally:
        analyst.ANALYST_CHUNK_SURVIVAL_MIN = real_threshold
    # restored: (b) must reject again
    out2, meta2 = run(B_MD, [candidate])
    assert meta2["chunks_rejected"] == 1


@case('J32-B (g) the fence fires FIRST: an IMG-token change is "fence", not "survival"')
def _():
    md = "![[assets/fig1.png]]\n\n" + words(30, "beta")
    fenced, embeds = analyst.fence(md)
    assert "⟦IMG-0⟧" in fenced
    # candidate drops the token but otherwise reproduces almost all the prose
    candidate = fenced.replace("⟦IMG-0⟧\n\n", "")
    out, meta = run(md, [candidate])
    assert meta["chunks_rejected"] == 1, meta
    assert meta["rejections"] == {"fence": 1, "survival": 0, "think_leak": 0, "inflation": 0}, meta


# ---------------------------------------------------------------------------
# SYM-074
# ---------------------------------------------------------------------------
THINK_MD = words(20, "gamma")


@case("SYM-074 (a) a candidate carrying </think> (else identical) -> rejected, think_leak")
def _():
    candidate = THINK_MD + "\n</think>"
    out, meta = run(THINK_MD, [candidate])
    assert meta["chunks_rejected"] == 1 and meta["rejections"]["think_leak"] == 1, meta
    assert out.strip() == THINK_MD.strip(), "the ORIGINAL chunk must ship"


@case('SYM-074 (b) the plain word "think" in prose -> passed (not over-broad)')
def _():
    md = "I think this analysis is correct and complete for every reader who reviews it"
    candidate = "I think this analysis is correct and complete for every reader who reviews it"
    out, meta = run(md, [candidate])
    assert meta["chunks_passed"] == 1 and meta["rejections"]["think_leak"] == 0, meta


@case("SYM-074 (c) an opening <think> alone -> rejected")
def _():
    candidate = "<think>" + THINK_MD
    out, meta = run(THINK_MD, [candidate])
    assert meta["chunks_rejected"] == 1 and meta["rejections"]["think_leak"] == 1, meta


@case("SYM-074 (d) NEGATIVE CONTROL: the think-leak guard removed -> (a)'s candidate PASSES")
def _():
    # The SAME "blank the guard, watch red, restore" technique convert_and_ship_selftest.py's
    # T17 uses: a literal string patch of the ONE guard line (not the elif/else chain it
    # belongs to), exec'd into a fresh module so the real analyst.py on disk is never touched.
    target = 'if "<think>" in candidate or "</think>" in candidate:'
    src = (HERE / "analyst.py").read_text(encoding="utf-8")
    assert src.count(target) == 1, f"guard line not found exactly once ({src.count(target)})"
    patched_src = src.replace(target, "if False:  # NEGATIVE CONTROL: think-leak guard removed")
    mod = types.ModuleType("analyst_nc_sym074")
    mod.__file__ = str(HERE / "analyst.py")
    sys.modules["analyst_nc_sym074"] = mod
    try:
        exec(compile(patched_src, str(HERE / "analyst.py"), "exec"), mod.__dict__)
        mod.unload = lambda: None
        candidate = THINK_MD + "\n</think>"
        out, meta = run(THINK_MD, [candidate], module=mod)
        assert meta["chunks_passed"] == 1 and meta["chunks_rejected"] == 0, (
            "the guard did not fire: removing the think-leak check should have passed this", meta)
    finally:
        sys.modules.pop("analyst_nc_sym074", None)
    # restored: the real module still rejects (a)'s fixture
    out2, meta2 = run(THINK_MD, [THINK_MD + "\n</think>"])
    assert meta2["chunks_rejected"] == 1 and meta2["rejections"]["think_leak"] == 1


# ---------------------------------------------------------------------------
# J34 -- the inflation guard (signed Rab 2026-09-05, "J34 1.5x reject")
# ---------------------------------------------------------------------------
INF_MD = "\n\n".join([words(15, f"inf{p}tok") for p in range(1, 4)])  # 3 paragraphs, 45 words


@case("J34 (a) a 2x verbatim duplicate -> survival 1.0 (J32-B is blind to it) but REJECTED, inflation")
def _():
    candidate = INF_MD + "\n\n" + INF_MD  # every input window survives; the bulk doubles
    fenced, _ = analyst.fence(INF_MD)
    assert tn.chunk_survival(fenced, candidate) == 1.0, "the constructed case must be invisible to J32-B"
    assert tn.word_ratio(fenced, candidate) == 2.0
    out, meta = run(INF_MD, [candidate])
    assert meta["chunks_passed"] == 0 and meta["chunks_rejected"] == 1, meta
    assert meta["rejections"] == {"fence": 0, "survival": 0, "think_leak": 0, "inflation": 1}, meta
    assert out.strip() == INF_MD.strip(), "the ORIGINAL chunk must ship, not the candidate"


@case("J34 (b) a faithful rewrite at ~1.09x (four words added) -> passed")
def _():
    candidate = INF_MD + " " + words(4, "extra")  # 49 / 45 = 1.0889, under the 1.5 lever
    fenced, _ = analyst.fence(INF_MD)
    r = tn.word_ratio(fenced, candidate)
    assert r is not None and 1.0 < r < analyst.ANALYST_CHUNK_INFLATION_MAX, r
    out, meta = run(INF_MD, [candidate])
    assert meta["chunks_passed"] == 1 and meta["rejections"]["inflation"] == 0, meta
    assert out.strip() == candidate.strip(), out


@case("J34 (c) NEGATIVE CONTROL: lever -> inf makes (a)'s duplicate PASS (watched)")
def _():
    candidate = INF_MD + "\n\n" + INF_MD
    real = analyst.ANALYST_CHUNK_INFLATION_MAX
    try:
        analyst.ANALYST_CHUNK_INFLATION_MAX = float("inf")
        out, meta = run(INF_MD, [candidate])
        assert meta["chunks_passed"] == 1 and meta["chunks_rejected"] == 0, (
            "the guard did not fire: an infinite lever should have let the duplicate through", meta)
    finally:
        analyst.ANALYST_CHUNK_INFLATION_MAX = real
    # restored: (a) must reject again
    out2, meta2 = run(INF_MD, [candidate])
    assert meta2["rejections"]["inflation"] == 1, meta2


@case('J34 (d) survival fires FIRST: a deletion is "survival", never a low ratio')
def _():
    paras = B_MD.split("\n\n")
    candidate = "\n\n".join(paras[:2])  # J32-B (b)'s fixture: 2 of 5 paragraphs, ratio 0.4
    out, meta = run(B_MD, [candidate])
    assert meta["rejections"] == {"fence": 0, "survival": 1, "think_leak": 0, "inflation": 0}, meta


@case("J34 (e) the lever's edge is STRICT: 67 of 45 words (1.4889) passes, 68 (1.5111) rejects")
def _():
    fenced, _ = analyst.fence(INF_MD)
    under = INF_MD + " " + words(22, "pad")   # 67 words
    over = INF_MD + " " + words(23, "pad")    # 68 words
    assert tn.word_ratio(fenced, under) == 1.4889 and tn.word_ratio(fenced, over) == 1.5111
    _, m1 = run(INF_MD, [under])
    _, m2 = run(INF_MD, [over])
    assert m1["chunks_passed"] == 1 and m1["rejections"]["inflation"] == 0, m1
    assert m2["chunks_rejected"] == 1 and m2["rejections"]["inflation"] == 1, m2


@case("J34 (f) journal round-trip: ratio rides beside survival on inflation rejections AND passes; "
      "0 input words -> ratio None (never a reject)")
def _():
    assert tn.word_ratio("", "anything at all") is None
    assert tn.word_ratio("   \n\t ", "anything") is None
    path = QUARANTINE / "journal-j34.jsonl"
    with open(path, "a", encoding="utf-8") as h:
        analyst._append_journal(h, 1, "alpha beta", "rejected", "alpha beta",
                                reason="inflation", survival=1.0, ratio=7.59)
        analyst._append_journal(h, 2, "gamma delta", "passed", "gamma delta ok",
                                survival=1.0, ratio=1.5)
        analyst._append_journal(h, 3, "eps zeta", "rejected", "eps zeta", reason="fence")
    loaded = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            loaded[rec["i"]] = rec
    assert loaded[1]["reason"] == "inflation" and loaded[1]["ratio"] == 7.59, loaded[1]
    assert loaded[2].get("reason") is None and loaded[2]["ratio"] == 1.5, loaded[2]
    assert "ratio" not in loaded[3] and "survival" not in loaded[3], loaded[3]


print()
if failed:
    print(f"TRIPWIRES DISARMED — {len(failed)} failed of 17: {failed}")
    raise SystemExit(1)
print("ALL TRIPWIRES FIRED — 17/17")
