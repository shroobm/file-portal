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
    omit_analyst=False, words_lost_excl=None, inventions_excl=None,
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
    assert "columns unsupported" in unread, unread


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
        assert [t["dir"] for t in bucket["tied"]] == ["0123456789abcdef"], bucket["tied"]   # the identical copy ties, listed
        assert bucket["refused"] == [], bucket["refused"]


TESTS = [
    test_fixes_effective_reading,
    test_tie_incumbent_stays_selected_newer_listed_tied,
    test_strictly_better_newer_still_wins_despite_tie_logic,
    test_tied_candidate_fixes_effective_false_named_in_reason,
    test_only_variant_is_original_nothing_changes,
    test_two_variants_better_verdict_selected,
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
