"""Selftest for variants.py (LANE A, S211). stdlib only. NEVER touches the real library --
every registry and every bundle_dir lives under a fresh tempfile.TemporaryDirectory(), and
FP_VARIANTS is redirected there for the duration of each test.

Run: python variants_selftest.py
Prints "N/N ok" and exits non-zero on any failure (GROUND: a check that could not run is
UNREAD, never "passes" -- a raised exception inside a test counts as a FAIL, not a skip).
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import variants  # noqa: E402


# ---------- fixtures ----------

def _manifest(
    sha="deadbeef00000000000000000000000000000000000000000000000000000000",
    verdict="pass", phase=None, converted_at="2026-01-01T00:00:00+00:00", pages=10,
    survival_convert=0.95, survival_analyst=0.99, pages_flagged=None, runs_total=0,
    inventions_total=0, words_lost=0, marker_words_total=1000,
    numbers_missing=0, numbers_extra=0,
    tables_total=1, rows_lost=0, columns_lost=0, tables_witnessed_lines=10,
    figures_total=1, degeneration=False, surya=0, fixes=None,
    omit_inventions=False, omit_tables=False, omit_figures=False, omit_numbers=False,
    omit_analyst=False, words_lost_excl=None, inventions_excl=None, kind=None,
) -> dict:
    convert: dict = {
        "doc_survival": survival_convert,
        "pages_flagged": pages_flagged if pages_flagged is not None else [],
        "runs_total": runs_total,
        "tripwires": {"degeneration": degeneration},
    }
    if not omit_inventions:
        convert["inventions"] = {
            "invented_total": inventions_total, "lost_total": words_lost,
            "marker_words_total": marker_words_total,
        }
        # S211 E3: the honest rests (fidelity_audit's *_excl_joined) only when a case asks for them — an older
        # manifest carries neither, and the registry must read that as UNREAD, never 0
        if words_lost_excl is not None:
            convert["inventions"]["lost_total_excl_joined"] = words_lost_excl
        if inventions_excl is not None:
            convert["inventions"]["invented_total_excl_joined"] = inventions_excl
    if not omit_tables:
        convert["tables"] = {
            "tables_total": tables_total, "rows_lost": rows_lost,
            "columns_lost": columns_lost, "tables_witnessed_lines": tables_witnessed_lines,
        }
    if not omit_figures:
        convert["figures"] = {"figures_total": figures_total}
    if not omit_numbers:
        convert["numbers"] = {"missing_total": numbers_missing, "extra_total": numbers_extra}

    if kind is not None:
        convert["kind"] = kind
    fidelity: dict = {"verdict": verdict, "verdict_phase": phase, "convert": convert}
    if not omit_analyst:
        fidelity["analyst"] = {"doc_survival": survival_analyst}

    m = {
        "source_sha256": sha,
        "converted_at": converted_at,
        "pages": pages,
        "fidelity": fidelity,
        "blocks": {"extraction": {"surya": surya}},
    }
    if fixes is not None:
        m["fixes"] = fixes
    return m


def _make_bundle(library_dir: Path, root_kind: str, name: str, n_assets: int = 2, **kw) -> Path:
    bundle_dir = library_dir / root_kind / name
    (bundle_dir / "assets").mkdir(parents=True, exist_ok=True)
    for i in range(n_assets):
        (bundle_dir / "assets" / ("a%d.jpeg" % i)).write_bytes(b"x")
    manifest = _manifest(**kw)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return bundle_dir


@contextlib.contextmanager
def _isolated():
    """A fresh temp dir for both the registry file (FP_VARIANTS) and every bundle_dir this test
    creates -- HARD RULE 3: never write under C:/Users/Bndit/ml/library."""
    with tempfile.TemporaryDirectory(prefix="fp-variants-selftest-") as td:
        tdp = Path(td)
        old = os.environ.get("FP_VARIANTS")
        os.environ["FP_VARIANTS"] = str(tdp / "variants.json")
        try:
            yield tdp
        finally:
            if old is None:
                os.environ.pop("FP_VARIANTS", None)
            else:
                os.environ["FP_VARIANTS"] = old


# ---------- tests ----------

def test_two_variants_better_verdict_selected():
    with _isolated() as td:
        sha = "sha-verdict-0001"
        a = _make_bundle(td, "anchor", "A-flag", sha=sha, verdict="flag",
                          converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-pass", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-pass", bucket


def test_equal_verdict_fewer_errors_selected():
    with _isolated() as td:
        sha = "sha-errors-0002"
        a = _make_bundle(td, "anchor", "A-more-errors", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00", words_lost=5)
        b = _make_bundle(td, "anchor", "B-fewer-errors", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00", words_lost=2)
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-fewer-errors", bucket


def test_asset_loss_refused():
    with _isolated() as td:
        sha = "sha-assets-0003"
        base = _make_bundle(td, "anchor", "A-baseline", sha=sha, verdict="flag",
                             converted_at="2026-01-01T00:00:00+00:00", n_assets=3)
        loses_asset = _make_bundle(td, "anchor", "B-loses-asset", sha=sha, verdict="pass",
                                    converted_at="2026-01-02T00:00:00+00:00", n_assets=2)
        variants.register(base)
        variants.register(loses_asset)
        bucket = variants.select(sha)
        refused_dirs = [r["dir"] for r in bucket["refused"]]
        assert "B-loses-asset" in refused_dirs, bucket
        assert bucket["selected"] != "B-loses-asset", bucket
        entry = [r for r in bucket["refused"] if r["dir"] == "B-loses-asset"][0]
        assert any("assets" in v for v in entry["violations"]), entry


def test_rows_lost_rose_refused():
    with _isolated() as td:
        sha = "sha-rows-0004"
        base = _make_bundle(td, "anchor", "A-baseline", sha=sha, verdict="flag",
                             converted_at="2026-01-01T00:00:00+00:00", rows_lost=0)
        worse = _make_bundle(td, "anchor", "B-rows-lost", sha=sha, verdict="pass",
                              converted_at="2026-01-02T00:00:00+00:00", rows_lost=3)
        variants.register(base)
        variants.register(worse)
        bucket = variants.select(sha)
        refused_dirs = [r["dir"] for r in bucket["refused"]]
        assert "B-rows-lost" in refused_dirs, bucket
        entry = [r for r in bucket["refused"] if r["dir"] == "B-rows-lost"][0]
        assert any("rows_lost" in v for v in entry["violations"]), entry


def test_degeneration_true_refused():
    with _isolated() as td:
        sha = "sha-degen-0005"
        base = _make_bundle(td, "anchor", "A-baseline", sha=sha, verdict="flag",
                             converted_at="2026-01-01T00:00:00+00:00", degeneration=False)
        degenerate = _make_bundle(td, "anchor", "B-degenerate", sha=sha, verdict="pass",
                                   converted_at="2026-01-02T00:00:00+00:00", degeneration=True)
        variants.register(base)
        variants.register(degenerate)
        bucket = variants.select(sha)
        refused_dirs = [r["dir"] for r in bucket["refused"]]
        assert "B-degenerate" in refused_dirs, bucket
        entry = [r for r in bucket["refused"] if r["dir"] == "B-degenerate"][0]
        assert any("degeneration" in v for v in entry["violations"]), entry


def test_columns_unsupported_reads_unread_not_violation():
    # Neither side witnessed a table line (tables_witnessed_lines=0) -- columns_lost must never
    # be judged; it reads "columns unsupported" in `unread`, and faithful() must still say ok.
    cand = {
        "words_lost": 0, "survival_convert": 0.9, "assets": 2, "tables_total": 1,
        "rows_lost": 0, "tables_witnessed_lines": 0, "columns_lost": 99,
        "degeneration": False, "inventions_total": 0,
    }
    base = {
        "words_lost": 0, "survival_convert": 0.9, "assets": 2, "tables_total": 1,
        "rows_lost": 0, "tables_witnessed_lines": 0, "columns_lost": 0,
        "degeneration": False, "inventions_total": 0,
    }
    ok, violations, unread = variants.faithful(cand, base)
    assert ok is True, (ok, violations, unread)
    assert not any("columns_lost" in v for v in violations), violations
    assert any(u.startswith("columns unsupported") for u in unread), unread


def test_register_idempotent():
    with _isolated() as td:
        sha = "sha-idem-0007"
        b = _make_bundle(td, "anchor", "A-only", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00")
        e1 = variants.register(b)
        e2 = variants.register(b)
        assert e1 == e2, (e1, e2)
        registry = variants._load_registry()
        assert list(registry[sha]["variants"].keys()) == ["A-only"], registry[sha]["variants"]


def test_original_never_deleted_after_supersede():
    with _isolated() as td:
        sha = "sha-supersede-0008"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="flag",
                          converted_at="2026-01-01T00:00:00+00:00")
        variants.register(a)
        variants.select(sha)
        b = _make_bundle(td, "anchor", "B-better", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00")
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-better", bucket
        assert "A-original" in bucket["variants"], bucket["variants"]
        assert bucket["original"] == "2026-01-01T00:00:00+00:00", bucket["original"]


def test_negative_control_faithful_better_candidate_is_selected():
    # Proves refusal is not blanket: a strictly-better, fully-faithful candidate DOES win, and
    # the refused list stays empty for it.
    with _isolated() as td:
        sha = "sha-negctrl-0009"
        base = _make_bundle(td, "anchor", "A-baseline", sha=sha, verdict="flag",
                             converted_at="2026-01-01T00:00:00+00:00",
                             words_lost=4, rows_lost=1, n_assets=2)
        better = _make_bundle(td, "anchor", "B-better", sha=sha, verdict="pass",
                               converted_at="2026-01-02T00:00:00+00:00",
                               words_lost=1, rows_lost=0, n_assets=2)
        variants.register(base)
        variants.register(better)
        ok, violations, unread = variants.faithful(
            variants.summarize(better), variants.summarize(base))
        assert ok is True, (violations, unread)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-better", bucket
        assert bucket["refused"] == [], bucket["refused"]


def test_absent_measure_reads_none():
    with _isolated() as td:
        b = _make_bundle(td, "anchor", "C-partial", sha="sha-absent-0010",
                          converted_at="2026-01-01T00:00:00+00:00",
                          omit_tables=True, omit_analyst=True)
        entry = variants.summarize(b)
        assert entry["tables_total"] is None, entry
        assert entry["rows_lost"] is None, entry
        assert entry["columns_lost"] is None, entry
        assert entry["tables_witnessed_lines"] is None, entry
        assert entry["survival_analyst"] is None, entry
        # a genuinely-measured zero elsewhere on the SAME entry must stay 0, not be swept to None
        assert entry["inventions_total"] == 0, entry


def test_fixes_effective_reading():
    """S211 E1 (CORRECTIONS row 5): a variant whose get_chars fix never saw a char says so — a reading beside the
    selection, never a constraint; UNREAD (None) when no counters or no get_chars fix."""
    with _isolated() as td:
        b = _make_bundle(td, "anchor", "C-fx", sha="sha-fixes-0011", converted_at="2026-01-01T00:00:00+00:00")
        mp = b / "manifest.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["fixes"] = ["offpage-clip"]
        m["fixes_stats"] = {"chars_seen": 0, "chars_dropped": 0, "chars_lifted": 0}
        mp.write_text(json.dumps(m), encoding="utf-8")
        assert variants.summarize(b)["fixes_effective"] is False, variants.summarize(b)   # the wrapper saw no char
        m["fixes_stats"] = {"chars_seen": 7173, "chars_dropped": 3363, "chars_lifted": 0}
        mp.write_text(json.dumps(m), encoding="utf-8")
        assert variants.summarize(b)["fixes_effective"] is True, variants.summarize(b)    # it read the document
        m["fixes_stats"] = None
        mp.write_text(json.dumps(m), encoding="utf-8")
        assert variants.summarize(b)["fixes_effective"] is None, variants.summarize(b)    # no counters: UNREAD
        m["fixes"] = ["overlap-fraction-gate"]
        m["fixes_stats"] = {"chars_seen": 0, "chars_dropped": 0, "chars_lifted": 0}
        mp.write_text(json.dumps(m), encoding="utf-8")
        assert variants.summarize(b)["fixes_effective"] is None, variants.summarize(b)    # NEGATIVE CONTROL: not a get_chars fix
        m["fixes"] = []
        mp.write_text(json.dumps(m), encoding="utf-8")
        assert variants.summarize(b)["fixes_effective"] is None, variants.summarize(b)    # a stock run


def test_tie_incumbent_stays_selected_newer_listed_tied():
    """S211 Lane C (Rab's word 2026-09-21): a candidate that TIES the baseline on every measured
    number (verdict, errors, survival_convert, survival_analyst) must not unseat it merely for
    being newer -- the incumbent stays selected, the newer is named under `tied`.

    NEGATIVE CONTROL, proven directly: rank() is unchanged -- it still ends in converted_at --
    so rank(a) and rank(b) below are equal in every slot but the last, and rank(b) > rank(a)
    purely because B is dated later. Before this change, select() did `max(candidates,
    key=rank)`, so this asserted-true old-rank comparison IS what would have selected B: this
    test would FAIL against the pre-Lane-C select() (it would find bucket["selected"] ==
    "B-newer-tie", not "A-original"). Against the new code it passes."""
    with _isolated() as td:
        sha = "sha-tie-0012"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-newer-tie", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)

        old_rank_a = variants.rank(variants.summarize(a))
        old_rank_b = variants.rank(variants.summarize(b))
        assert old_rank_a[:-1] == old_rank_b[:-1], (old_rank_a, old_rank_b)  # tied on the 4 measures
        assert old_rank_b > old_rank_a, (old_rank_a, old_rank_b)  # OLD rule: B wins on converted_at alone

        bucket = variants.select(sha)
        assert bucket["selected"] == "A-original", bucket
        tied_dirs = [t["dir"] for t in bucket["tied"]]
        assert tied_dirs == ["B-newer-tie"], bucket["tied"]
        assert bucket["tied"][0]["note"] == variants._TIE_NOTE, bucket["tied"]
        assert "B-newer-tie" in bucket["reason"], bucket["reason"]


def test_strictly_better_newer_still_wins_despite_tie_logic():
    """Proves the tie rule does nothing where it must not: a candidate with strictly fewer
    errors than the baseline still wins outright (its _selection_rank is greater, not equal),
    and nothing is listed under `tied`. Same shape as test_equal_verdict_fewer_errors_selected,
    asserted again here explicitly against the new `tied` key so a future edit to the tie path
    cannot silently start swallowing a real win."""
    with _isolated() as td:
        sha = "sha-tie-better-0013"
        a = _make_bundle(td, "anchor", "A-baseline", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00", words_lost=3)
        b = _make_bundle(td, "anchor", "B-fewer-errors", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00", words_lost=0)
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-fewer-errors", bucket
        assert bucket["tied"] == [], bucket["tied"]


def test_tied_candidate_fixes_effective_false_named_in_reason():
    """A tied candidate is not a refusal (S211 E1: fixes_effective is a reading beside the
    selection, never a constraint) -- but when it IS the tied candidate, the reason sentence
    names its fixes_effective False, per Rab's word: a measure must never assert a number (or a
    silence) it cannot support, and here the tie's own explanation should say what else is known
    about the candidate it declined to promote."""
    with _isolated() as td:
        sha = "sha-tie-fx-0014"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-tied-fx", sha=sha, verdict="pass",
                          converted_at="2026-01-02T00:00:00+00:00")
        bp = b / "manifest.json"
        m = json.loads(bp.read_text(encoding="utf-8"))
        m["fixes"] = ["offpage-clip"]
        m["fixes_stats"] = {"chars_seen": 0, "chars_dropped": 0, "chars_lifted": 0}
        bp.write_text(json.dumps(m), encoding="utf-8")
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-original", bucket
        tied_dirs = [t["dir"] for t in bucket["tied"]]
        assert tied_dirs == ["B-tied-fx"], bucket["tied"]
        assert "B-tied-fx" in bucket["reason"] and "fixes_effective=False" in bucket["reason"], bucket["reason"]


def test_only_variant_is_original_nothing_changes():
    """When the only variant registered IS the baseline/original, select() must behave exactly
    as before Lane C: it is selected, and `tied` is empty (there is nothing to tie against)."""
    with _isolated() as td:
        sha = "sha-tie-solo-0015"
        a = _make_bundle(td, "anchor", "A-only", sha=sha, verdict="pass",
                          converted_at="2026-01-01T00:00:00+00:00")
        variants.register(a)
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-only", bucket
        assert bucket["tied"] == [], bucket["tied"]


def test_honest_rest_compared_when_both_carry_it():
    """S211 E3 (Rab's word 23:1xZ; Bill C-30 ~160c refused on 574 > 479 lost / 167 > 27 invented, the layer path's
    own line-wrap joins): when BOTH sides carry lost_total_excl_joined / invented_total_excl_joined, faithful compares
    the honest rests and rank sums them. NEGATIVE CONTROL: the raw counts alone (the old comparison) read a violation
    -- asserted directly -- while the honest rests read none, so the candidate is selected."""
    with _isolated() as td:
        sha = "sha-honest-0001"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="flag",
                          converted_at="2026-01-01T00:00:00+00:00",
                          words_lost=479, inventions_total=27, words_lost_excl=300, inventions_excl=20)
        b = _make_bundle(td, "anchor", "B-fixed", sha=sha, verdict="flag",
                          converted_at="2026-01-02T00:00:00+00:00", survival_convert=0.97,
                          words_lost=574, inventions_total=167, words_lost_excl=200, inventions_excl=10)
        variants.register(a)
        variants.register(b)
        sa, sb = variants.summarize(a), variants.summarize(b)
        assert sb["words_lost"] > sa["words_lost"] and sb["inventions_total"] > sa["inventions_total"], (sa, sb)  # raw: worse
        ok, violations, unread = variants.faithful(sb, sa)
        assert ok and violations == [], (violations, unread)
        assert not any("words_lost" in u or "inventions_total" in u for u in unread), unread
        assert variants._error_sum(sb)[0] == 200 + 10, variants._error_sum(sb)
        assert variants._error_sum(sa)[0] == 300 + 20, variants._error_sum(sa)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-fixed", bucket


def test_honest_rest_absent_on_one_side_reads_unread_never_violation():
    """S211 E3: an older manifest (audited before the keys existed) carries no honest rest -- the raw comparison
    across the two vocabularies would be a falsified refusal, so faithful reads the constraint UNREAD and NAMES the
    side lacking it; rank still orders on each entry's own honest-or-raw sum, so a strictly worse candidate is not
    promoted (NEGATIVE CONTROL: with the raw comparison the candidate would be refused; here it is neither refused
    nor selected -- the incumbent stays)."""
    with _isolated() as td:
        sha = "sha-honest-0002"
        a = _make_bundle(td, "anchor", "A-original-old", sha=sha, verdict="flag",
                          converted_at="2026-01-01T00:00:00+00:00", words_lost=479, inventions_total=27)
        b = _make_bundle(td, "anchor", "B-fixed-new", sha=sha, verdict="flag",
                          converted_at="2026-01-02T00:00:00+00:00",
                          words_lost=574, inventions_total=167, words_lost_excl=550, inventions_excl=150)
        variants.register(a)
        variants.register(b)
        sa, sb = variants.summarize(a), variants.summarize(b)
        assert sa["words_lost_excl_joined"] is None and sb["words_lost_excl_joined"] == 550, (sa, sb)
        ok, violations, unread = variants.faithful(sb, sa)
        assert ok and violations == [], (violations, unread)
        assert any(u.startswith("words_lost unread") and "baseline" in u for u in unread), unread
        assert any(u.startswith("inventions_total unread") and "baseline" in u for u in unread), unread
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-original-old", bucket   # 550+150 > 479+27: strictly worse, never promoted
        assert bucket["refused"] == [] and bucket["tied"] == [], bucket


def test_select_reset_reinstates_the_original_over_a_sticky_newest():
    """S211 E3: a selection made under the retired rule (the newest on a tie -- Bill C-288's ~160b) is sticky, so the
    tie rule alone would keep the wrong incumbent. select(sha, reset=True) takes the ORIGINAL (the earliest
    conversion) as the baseline: the tied newer variant is listed under `tied`, the original selected. NEGATIVE
    CONTROL: the same call without reset keeps the sticky newest."""
    with _isolated() as td:
        sha = "sha-reset-0003"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="pass", converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-newer-tie", sha=sha, verdict="pass", converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)
        reg = variants._load_registry()
        reg[sha]["selected"] = "B-newer-tie"        # the retired rule's pick, sticky
        variants._write_registry_atomic(reg)
        sticky = variants.select(sha)
        assert sticky["selected"] == "B-newer-tie", sticky   # without reset the sticky pick stays
        assert [t["dir"] for t in sticky["tied"]] == ["A-original"], sticky["tied"]
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "A-original", bucket
        assert [t["dir"] for t in bucket["tied"]] == ["B-newer-tie"], bucket["tied"]
        again = variants.select(sha)                   # sticky from here on
        assert again["selected"] == "A-original", again


def test_reset_prefers_the_shipped_copy_among_equal_originals():
    """S211 E3: one conversion in BOTH roots (S209's held park kept a copy beside the shipped one — RBC Q3, CIFE,
    TD Q3: identical converted_at and numbers). The incumbent among equals is the SHIPPED copy (root anchor), never
    the parked one by the accident of its sha-name sorting first. NEGATIVE CONTROL: the plain (converted_at, dir)
    order — the old key — puts the digit-named held copy first, asserted directly."""
    with _isolated() as td:
        sha = "sha-copies-0004"
        held = _make_bundle(td, "held", "0123456789abcdef", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00")
        anchor = _make_bundle(td, "anchor", "Some Bank _ Q3 Report", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00")
        variants.register(held)
        variants.register(anchor)
        sh, sa = variants.summarize(held), variants.summarize(anchor)
        assert sh["root"] == "held" and sa["root"] == "anchor", (sh["root"], sa["root"])
        assert sorted([sh, sa], key=lambda v: (v["converted_at"], v["dir"]))[0]["dir"] == "0123456789abcdef"  # the old order
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "Some Bank _ Q3 Report", bucket
        # S211 E6: the identical copy is ONE conversion parked twice, so it is folded before the ranking and named
        # under `same_conversion` — it is not a tie, because nothing was weighed (this line asserted the old
        # behaviour; the case's own subject, that the SHIPPED copy is the incumbent, is unchanged above)
        assert bucket["tied"] == [], bucket["tied"]
        assert [e["dir"] for e in bucket["same_conversion"]] == ["0123456789abcdef"], bucket["same_conversion"]
        assert bucket["refused"] == [], bucket["refused"]


def test_anchor_first_among_equal_challengers():
    """S211 E3 (Investment Valuation: two identical challengers — an anchor copy and its held park — beat the original
    on survival 0.9334 over 0.9333, and the held one won because its digit-named dir sorts first): among challengers
    equal on the full rank the SHIPPED copy is selected. NEGATIVE CONTROL: the plain max by rank() over the dir-ordered
    candidates returns the held one — asserted directly."""
    with _isolated() as td:
        sha = "sha-challengers-0007"
        o = _make_bundle(td, "anchor", "Some Book", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00", survival_convert=0.9333)
        h = _make_bundle(td, "held", "0123456789abcdef", sha=sha, verdict="fail", converted_at="2026-01-02T00:00:00+00:00", survival_convert=0.9334)
        a = _make_bundle(td, "anchor", "Some Book (1)", sha=sha, verdict="fail", converted_at="2026-01-02T00:00:00+00:00", survival_convert=0.9334)
        for b in (o, h, a):
            variants.register(b)
        sh, sa = variants.summarize(h), variants.summarize(a)
        assert variants.rank(sh) == variants.rank(sa)
        assert max([sh, sa], key=variants.rank)["dir"] == "0123456789abcdef"     # the old pick: first maximal in dir order
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "Some Book (1)", bucket


def test_unmeasured_field_excluded_never_read_as_zero():
    """S211 E3 (the accounting on Waterloo's Kamalzadeh thesis): a candidate whose numbers measure never ran (None)
    must not read as "0 missing figures" against a baseline with 5 measured. The field is EXCLUDED from the
    comparison and NAMED under bucket["excluded_fields"]; on the rest they tie, so the incumbent stays. NEGATIVE
    CONTROL: the old rank tuple (None summed as 0) reads the candidate as better -- asserted directly."""
    with _isolated() as td:
        sha = "sha-excl-0005"
        a = _make_bundle(td, "anchor", "A-measured", sha=sha, verdict="flag", converted_at="2026-01-01T00:00:00+00:00", numbers_missing=5)
        b = _make_bundle(td, "anchor", "B-unmeasured", sha=sha, verdict="flag", converted_at="2026-01-02T00:00:00+00:00", omit_numbers=True)
        variants.register(a)
        variants.register(b)
        sa, sb = variants.summarize(a), variants.summarize(b)
        assert sb["numbers_missing"] is None and sa["numbers_missing"] == 5, (sa, sb)
        assert variants._selection_rank(sb) > variants._selection_rank(sa), "the old rule: None as 0 wins"   # the negative control
        verdict, excluded = variants._compare(sb, sa)
        assert verdict == "tie" and "numbers_missing" in excluded and "numbers_extra" in excluded, (verdict, excluded)
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-measured", bucket
        assert [t["dir"] for t in bucket["tied"]] == ["B-unmeasured"], bucket["tied"]
        assert bucket["excluded_fields"] == {"B-unmeasured": ["numbers_missing", "numbers_extra"]}, bucket["excluded_fields"]
        assert "Excluded from the comparison" in bucket["reason"], bucket["reason"]


def test_degeneration_on_both_sides_is_not_a_refusal():
    """S211 E3 (the accounting on Desjardins AR / the AI Index / Ashby / RBC Q3): one conversion in both roots, both
    carrying degeneration True -- the registry selected the anchor copy and REFUSED the identical held copy for the
    very flag the incumbent carries. Now: True on both sides is UNREAD-named, not a violation; the copy ties. NEGATIVE
    CONTROL: the regression case (baseline False, candidate True) is still refused -- test_degeneration_true_refused
    above; and a candidate False against a baseline True is an improvement, selected."""
    with _isolated() as td:
        sha = "sha-degen-both-0006"
        a = _make_bundle(td, "anchor", "Some Report", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00", degeneration=True)
        h = _make_bundle(td, "held", "0123456789abcdef", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00", degeneration=True)
        c = _make_bundle(td, "anchor", "Some Report _160", sha=sha, verdict="fail", converted_at="2026-01-03T00:00:00+00:00", degeneration=False)
        variants.register(a)
        variants.register(h)
        ok, violations, unread = variants.faithful(variants.summarize(h), variants.summarize(a))
        assert ok and violations == [] and any("both sides" in u for u in unread), (violations, unread)
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "Some Report" and bucket["tied"] == [] and bucket["refused"] == [], bucket
        assert [e["dir"] for e in bucket["same_conversion"]] == ["0123456789abcdef"], bucket["same_conversion"]
        variants.register(c)
        ok2, v2, _u2 = variants.faithful(variants.summarize(c), variants.summarize(a))
        assert ok2 and v2 == [], (ok2, v2)
        bucket = variants.select(sha)
        # his word "no looping text": clearing the loops the incumbent carries is a lessening of errors -- the variant wins
        assert bucket["selected"] == "Some Report _160", bucket
        assert variants._compare(variants.summarize(c), variants.summarize(a)) == ("better", []), variants._compare(variants.summarize(c), variants.summarize(a))


def test_analyst_confounded_candidate_is_named_not_silent():
    """S211 E3 (McGill-1 ~148, SYM-163): a candidate whose convert survival beats the incumbent's but whose verdict is
    fail AT THE ANALYST PHASE loses on the verdict alone -- the incumbent stays, and the candidate is NAMED under
    bucket["analyst_confounded"] with the note (the convert fix worked; the analyst's own pass failed it). NEGATIVE
    CONTROL: the same candidate failed at the CONVERT phase is not listed (its loss is the convert stage's own)."""
    with _isolated() as td:
        sha = "sha-analyst-0008"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="flag", phase="convert", converted_at="2026-01-01T00:00:00+00:00", survival_convert=0.8169)
        b = _make_bundle(td, "anchor", "B-repaired _148", sha=sha, verdict="fail", phase="analyst", converted_at="2026-01-02T00:00:00+00:00", survival_convert=0.8496)
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-original", bucket
        assert [x["dir"] for x in bucket["analyst_confounded"]] == ["B-repaired _148"], bucket["analyst_confounded"]
        assert "ANALYST phase" in bucket["analyst_confounded"][0]["note"] and "SYM-163" in bucket["analyst_confounded"][0]["note"]
        assert bucket["tied"] == [] and bucket["refused"] == []
    with _isolated() as td:
        sha = "sha-analyst-0009"
        a = _make_bundle(td, "anchor", "A-original", sha=sha, verdict="flag", phase="convert", converted_at="2026-01-01T00:00:00+00:00", survival_convert=0.8169)
        c = _make_bundle(td, "anchor", "C-worse-at-convert", sha=sha, verdict="fail", phase="convert", converted_at="2026-01-02T00:00:00+00:00", survival_convert=0.8496)
        variants.register(a)
        variants.register(c)
        bucket = variants.select(sha)
        assert bucket["selected"] == "A-original" and bucket["analyst_confounded"] == [], bucket


def test_scan_lane_agreement_counts_read_none_not_errors():
    """S211 E3 (the accounting's mechanism reading — Stanford Research, Shannon & Weaver): on the scan lane the convert
    audit's witness is the PDF's own untrusted OCR layer (kind "agreement"; fidelity_audit's meaning: "disagreement, not
    invention") — the registry summed those counts as errors. Now the word and figure counts read None (UNREAD), the kind
    carried, and _compare EXCLUDES them by name. NEGATIVE CONTROL: the same manifest with kind "fidelity" keeps its numbers."""
    with _isolated() as td:
        sha = "sha-scan-0010"
        s = _make_bundle(td, "anchor", "Scan-Doc", sha=sha, verdict="flag", kind="agreement", words_lost=4403, inventions_total=2332, numbers_missing=706)
        f = _make_bundle(td, "anchor", "Layer-Doc", sha="sha-layer-0011", verdict="flag", kind="fidelity", words_lost=4403, inventions_total=2332, numbers_missing=706)
        ss, sf = variants.summarize(s), variants.summarize(f)
        assert ss["witness_kind"] == "agreement" and ss["words_lost"] is None and ss["inventions_total"] is None and ss["numbers_missing"] is None, ss
        assert sf["witness_kind"] == "fidelity" and sf["words_lost"] == 4403 and sf["numbers_missing"] == 706, sf
        assert variants._error_sum(ss)[0] == 0 and "words_lost" in variants._error_sum(ss)[1], variants._error_sum(ss)
        verdict, excluded = variants._compare(ss, dict(ss, dir="other"))
        assert verdict == "tie" and "words_lost" in excluded and "numbers_missing" in excluded, (verdict, excluded)


def test_rows_columns_compare_only_over_the_same_population():
    """S211 E3 (RBC Q3 ~155, read on p.72): the variant was refused on columns_lost 1 > 0 with its lines witness over 5
    tables against the original's 3 — p.72's table was among the five and not the three, and BOTH renderings show the
    same two columns: a measured 1 against an unmeasured 0. Populations that differ read UNREAD and NAMED, never a
    violation; the rest of the comparison decides (verdict flag over fail: selected). NEGATIVE CONTROL: equal populations
    with a real increase are still refused."""
    with _isolated() as td:
        sha = "sha-pop-0012"
        o = _make_bundle(td, "anchor", "Q3 Report", sha=sha, verdict="fail", converted_at="2026-01-01T00:00:00+00:00", degeneration=True,
                          columns_lost=0, rows_lost=0, tables_witnessed_lines=3)
        v = _make_bundle(td, "anchor", "Q3 Report _155", sha=sha, verdict="flag", converted_at="2026-01-02T00:00:00+00:00", degeneration=False,
                          columns_lost=1, rows_lost=0, tables_witnessed_lines=5)
        for b in (o, v):
            variants.register(b)
        # the fixture's manifest carries no *_population keys — the populations come from tables_witnessed_lines in summarize?
        so, sv = variants.summarize(o), variants.summarize(v)
        so["columns_lost_population"], so["rows_lost_population"] = 3, 3
        sv["columns_lost_population"], sv["rows_lost_population"] = 5, 5
        ok, violations, unread = variants.faithful(sv, so)
        assert ok and violations == [], (violations, unread)
        assert any(u.startswith("columns incomparable (populations differ: 5 vs 3)") for u in unread), unread
        # the negative control: the same increase over EQUAL populations is a violation
        sv2 = dict(sv, columns_lost_population=3, rows_lost_population=3)
        ok2, v2, _ = variants.faithful(sv2, so)
        assert not ok2 and any("columns_lost increased: 1 > 0" in x for x in v2), (ok2, v2)


def test_analyst_decided_named_when_the_analyst_phase_alone_decides():
    """S211 E5, read live on TD Q3 ~r2 (a PLAIN re-send, no lever): every convert-stage number tied with the
    incumbent (survival 0.9147, inventions 5, lost 464, missing 24) and the analyst's own pass differed (0.9994 ->
    1.0, verdict fail -> flag at the ANALYST phase), which selected it. A better verdict is his signed criterion, so
    the selection stands — but the bucket and the reason must SAY that a sampled rewrite decided it (SYM-163's other
    face; the loss case is `analyst_confounded`)."""
    with _isolated() as td:
        sha = "sha-analyst-decided-0026"
        a = _make_bundle(td, "anchor", "A-orig", sha=sha, verdict="fail", phase="analyst",
                          survival_convert=0.9147, survival_analyst=0.9994, words_lost=464, inventions_total=5,
                          numbers_missing=24, converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-r2", sha=sha, verdict="flag", phase="convert",
                          survival_convert=0.9147, survival_analyst=1.0, words_lost=464, inventions_total=5,
                          numbers_missing=24, converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha)
        assert bucket["selected"] == "B-r2", bucket
        named = bucket.get("analyst_decided") or []
        assert len(named) == 1 and named[0]["dir"] == "B-r2", bucket
        assert "THE ANALYST PHASE DECIDED THIS" in bucket["reason"], bucket["reason"]


def test_analyst_decided_not_named_when_a_convert_number_moved_or_the_phase_is_convert():
    """The negative controls on the same shape: (a) the same analyst-phase win with ONE convert-stage number moved is
    the LEVER's win, not the lottery's — not named; (b) two convert-phase bundles differing only in verdict are not
    named either (no analyst phase in it)."""
    with _isolated() as td:
        sha = "sha-analyst-decided-neg-a"
        a = _make_bundle(td, "anchor", "A-orig", sha=sha, verdict="fail", phase="analyst",
                          survival_convert=0.9147, survival_analyst=0.9994, words_lost=464, inventions_total=5,
                          converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-155", sha=sha, verdict="flag", phase="convert",
                          survival_convert=0.9147, survival_analyst=1.0, words_lost=464, inventions_total=1,
                          converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)
        lever = variants.select(sha)
        assert lever["selected"] == "B-155", lever
        assert not (lever.get("analyst_decided") or []), lever
    with _isolated() as td:
        sha = "sha-analyst-decided-neg-b"
        a = _make_bundle(td, "anchor", "A-fail", sha=sha, verdict="fail", phase="convert",
                          survival_convert=0.90, survival_analyst=1.0, converted_at="2026-01-01T00:00:00+00:00")
        b = _make_bundle(td, "anchor", "B-flag", sha=sha, verdict="flag", phase="convert",
                          survival_convert=0.90, survival_analyst=1.0, converted_at="2026-01-02T00:00:00+00:00")
        variants.register(a)
        variants.register(b)
        conv = variants.select(sha)
        assert conv["selected"] == "B-flag", conv
        assert not (conv.get("analyst_decided") or []), conv


def test_one_conversion_parked_twice_is_folded_not_tied():
    """S211 E6, read over the whole live registry: of 30 tie entries, 8 were a bundle tied against ITS OWN COPY —
    the same converted_at and the same marker-body sha256, one conversion standing in anchor/ and in S209's park
    under held/<sha16>. It cannot change which bundle is selected (the copy is identical) but it inflates the
    variant and tie counts a reader sees, and invites the belief that an alternative was weighed. The copies are
    folded to the SHIPPED one before the ranking and named under `same_conversion`; nothing is deleted."""
    with _isolated() as td:
        sha = "sha-selftie-0028"
        a = _make_bundle(td, "anchor", "Some Bank _ AR", sha=sha, verdict="flag",
                          converted_at="2026-02-01T00:00:00+00:00", words_lost=12)
        h = _make_bundle(td, "held", "fedcba9876543210", sha=sha, verdict="flag",
                          converted_at="2026-02-01T00:00:00+00:00", words_lost=12)
        variants.register(a)
        variants.register(h)
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "Some Bank _ AR", bucket
        assert bucket["tied"] == [], bucket["tied"]
        folded = bucket["same_conversion"]
        assert [e["dir"] for e in folded] == ["fedcba9876543210"], folded
        assert folded[0]["folded_into"] == "Some Bank _ AR" and "SAME conversion" in folded[0]["note"], folded
        # and nothing was deleted: both rows are still in `variants`
        assert set(bucket["variants"]) == {"Some Bank _ AR", "fedcba9876543210"}, sorted(bucket["variants"])


def test_a_second_conversion_of_the_same_body_still_ties():
    """THE NEGATIVE CONTROL for the fold, and the case that keeps it from swallowing real evidence: two runs of the
    same document at DIFFERENT times, agreeing on every measured number, are two readings — not one parked twice —
    and must still be listed under `tied` (this is TD Q3's live shape: byte-identical body, two conversions a day
    apart)."""
    with _isolated() as td:
        sha = "sha-two-runs-0029"
        a = _make_bundle(td, "anchor", "Some Bank _ Q3", sha=sha, verdict="flag",
                          converted_at="2026-02-01T00:00:00+00:00", words_lost=12)
        b = _make_bundle(td, "anchor", "Some Bank _ Q3 _r2", sha=sha, verdict="flag",
                          converted_at="2026-02-02T00:00:00+00:00", words_lost=12)
        variants.register(a)
        variants.register(b)
        bucket = variants.select(sha, reset=True)
        assert bucket["selected"] == "Some Bank _ Q3", bucket
        assert [t["dir"] for t in bucket["tied"]] == ["Some Bank _ Q3 _r2"], bucket["tied"]
        assert bucket["same_conversion"] == [], bucket["same_conversion"]


def test_the_counted_apart_keys_cannot_move_the_ranking():
    """S211 E8: the registry now reads `numbers_missing_in_citations`, `numbers_missing_in_furniture` and
    `numbers_extra_on_blank_layer` so a reader of the register can see where this sitting's fallen counts went
    (missing 1,716 -> 1,660, extra 2,218 -> 969 across the shelf). They are a READING, and the promise is that they
    cannot move which bundle is selected. Asserted twice, because either half can rot alone: STRUCTURALLY, none of
    the three is among the six fields the error sum reads; BEHAVIOURALLY, the sum is identical for an entry carrying
    large values in all three and one carrying none."""
    for f in ("numbers_missing_in_citations", "numbers_missing_in_furniture", "numbers_extra_on_blank_layer"):
        assert f not in variants._ERROR_FIELDS, (f, variants._ERROR_FIELDS)
    base = {"words_lost": 100, "inventions_total": 20, "rows_lost": 1, "columns_lost": 2,
            "numbers_missing": 5, "numbers_extra": 7}
    loud = dict(base, numbers_missing_in_citations=900, numbers_missing_in_furniture=900,
                numbers_extra_on_blank_layer=900)
    assert variants._error_sum(base)[0] == variants._error_sum(loud)[0] == 135, (
        variants._error_sum(base), variants._error_sum(loud))
    # and the None fields named by the sum are the same on both sides — the reading adds no unmeasured field either
    assert variants._error_sum(base)[1] == variants._error_sum(loud)[1], (variants._error_sum(base), variants._error_sum(loud))


TESTS = [
    test_fixes_effective_reading,
    test_tie_incumbent_stays_selected_newer_listed_tied,
    test_strictly_better_newer_still_wins_despite_tie_logic,
    test_tied_candidate_fixes_effective_false_named_in_reason,
    test_only_variant_is_original_nothing_changes,
    test_two_variants_better_verdict_selected,
    test_analyst_decided_named_when_the_analyst_phase_alone_decides,
    test_analyst_decided_not_named_when_a_convert_number_moved_or_the_phase_is_convert,
    test_one_conversion_parked_twice_is_folded_not_tied,
    test_a_second_conversion_of_the_same_body_still_ties,
    test_the_counted_apart_keys_cannot_move_the_ranking,
    test_equal_verdict_fewer_errors_selected,
    test_asset_loss_refused,
    test_rows_lost_rose_refused,
    test_degeneration_true_refused,
    test_columns_unsupported_reads_unread_not_violation,
    test_register_idempotent,
    test_original_never_deleted_after_supersede,
    test_negative_control_faithful_better_candidate_is_selected,
    test_absent_measure_reads_none,
    test_honest_rest_compared_when_both_carry_it,
    test_honest_rest_absent_on_one_side_reads_unread_never_violation,
    test_select_reset_reinstates_the_original_over_a_sticky_newest,
    test_reset_prefers_the_shipped_copy_among_equal_originals,
    test_anchor_first_among_equal_challengers,
    test_unmeasured_field_excluded_never_read_as_zero,
    test_degeneration_on_both_sides_is_not_a_refusal,
    test_analyst_confounded_candidate_is_named_not_silent,
    test_scan_lane_agreement_counts_read_none_not_errors,
    test_rows_columns_compare_only_over_the_same_population,
]


def main() -> int:
    passed = 0
    failed = []
    for t in TESTS:
        try:
            t()
        except Exception:  # noqa: BLE001 -- a failing test must be counted, not raised past main()
            failed.append((t.__name__, traceback.format_exc()))
        else:
            passed += 1

    for name, tb in failed:
        print("FAIL: %s" % name)
        print(tb)

    total = len(TESTS)
    print("%d/%d ok" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
