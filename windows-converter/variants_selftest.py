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
    omit_analyst=False,
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


TESTS = [
    test_fixes_effective_reading,
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
