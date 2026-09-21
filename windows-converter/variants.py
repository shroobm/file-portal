"""LANE A — THE VARIANT REGISTRY AND THE WHITELIST (S211).

Rab's word: every final converted bundle must remain in the system; a whitelist names which
variant "pops up", by the verdicts and the lessening of errors, faithful and true — no text
removed, no image lost, no table broken, no looping text.

This module is READ-ONLY toward the pipeline: it reads bundle manifests (manifest.json,
assets/) and maintains its own registry file (a separate JSON document, never the bundle's own
manifest.json). It never deletes a bundle, a variant entry, or the registry's own history — a
supersede only changes which dir a lookup RETURNS, never what the registry KNOWS existed.

Key names below are LITERAL strings (never composed), matching the manifest shapes read from
a real bundle (C:/Users/Bndit/ml/library/anchor/Bank of Canada _ Financial Stability Report _
2026/manifest.json, read-only, grepped 2026-09-21) and fidelity_audit.py's audit_convert /
verdict_with_phase (~773-1020).

stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# The registry lives apart from any one bundle — one file naming every variant of every sha256
# ever converted. The integrator registers a root; this module never touches fp_paths.py.
_DEFAULT_REGISTRY = "C:/Users/Bndit/ml/library/variants.json"


def _registry_path() -> Path:
    """Re-read the env var on every call (not frozen at import) so a caller — or a selftest —
    can point FP_VARIANTS at a temp file without reloading this module. Otherwise the registry is
    the `variants` root of roots.json (S211, resolved through fp_paths — FP_PIPELINE relocates it
    with the tree); the literal default stands only where fp_paths cannot be imported."""
    env = os.environ.get("FP_VARIANTS")
    if env:
        return Path(env)
    try:
        import fp_paths  # the converter's own registry of roots (beside this file)
        return Path(fp_paths.root("variants"))
    except Exception:  # noqa: BLE001 — a caller outside the converter tree keeps the literal
        return Path(_DEFAULT_REGISTRY)


def _load_registry() -> dict:
    path = _registry_path()
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    return json.loads(text)


def _write_registry_atomic(registry: dict) -> None:
    """temp file + os.replace — a reader never sees a half-written registry, and a crash mid-write
    leaves the PREVIOUS registry intact (never a truncated one)."""
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".variants-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(registry, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _infer_root(bundle_path: Path) -> str:
    """"anchor" | "held" from the bundle's own path — the two roots convert_and_ship.py writes
    into (ANCHOR / HELD). A path with no "held" component is an anchor copy by construction."""
    parts = {p.lower() for p in bundle_path.parts}
    return "held" if "held" in parts else "anchor"


def summarize(bundle_dir) -> dict:
    """Read manifest.json (and count assets/) under bundle_dir; return a flat dict of LITERAL
    keys. An absent measure (the manifest's block itself is None/absent — "not measured", per
    fidelity_audit.py's own comments) reads None, never 0. A block that IS present but whose
    number is genuinely zero reads 0, unchanged."""
    bp = Path(bundle_dir)
    manifest = json.loads((bp / "manifest.json").read_text(encoding="utf-8"))

    fid = manifest.get("fidelity") or {}
    convert = fid.get("convert") or {}
    analyst_fid = fid.get("analyst") or {}
    # These four ride BESIDE survival in audit_convert and are explicitly None when blocks was
    # not handed in — grepped verbatim: "None = not measured (no blocks handed in), never 0."
    inventions = convert.get("inventions") or {}
    tables = convert.get("tables") or {}
    figures = convert.get("figures") or {}
    numbers = convert.get("numbers") or {}
    tripwires = convert.get("tripwires") or {}
    extraction = (manifest.get("blocks") or {}).get("extraction") or {}

    assets_dir = bp / "assets"
    assets_count = sum(1 for p in assets_dir.rglob("*") if p.is_file()) if assets_dir.is_dir() else 0

    return {
        "dir": bp.name,
        "root": _infer_root(bp),
        "source_sha256": manifest.get("source_sha256"),
        "fixes": manifest.get("fixes") or [],
        "verdict": fid.get("verdict"),
        "verdict_phase": fid.get("verdict_phase"),
        "converted_at": manifest.get("converted_at"),
        "pages": manifest.get("pages"),
        # No single "words" key exists on the manifest; the closest literal Marker word count is
        # fidelity.convert.inventions.marker_words_total (audit_inventions' own words_total) —
        # None exactly when inventions itself was not measured.
        "words": inventions.get("marker_words_total"),
        "survival_convert": convert.get("doc_survival"),
        "survival_analyst": analyst_fid.get("doc_survival"),
        "pages_flagged": convert.get("pages_flagged"),
        "runs_total": convert.get("runs_total"),
        "inventions_total": inventions.get("invented_total"),
        "words_lost": inventions.get("lost_total"),
        # S211 E3 (Rab's word 23:1xZ — the measures secured): the honest rests beside the old numbers. None on a manifest
        # audited before the keys existed (UNREAD, never 0): rank and faithful fall back / read UNREAD, never a falsified
        # comparison across the two vocabularies.
        "inventions_excl_joined": inventions.get("invented_total_excl_joined"),
        "words_lost_excl_joined": inventions.get("lost_total_excl_joined"),
        "numbers_missing": numbers.get("missing_total"),
        "numbers_missing_in_figures": numbers.get("missing_in_figures_total"),
        "numbers_extra": numbers.get("extra_total"),
        "tables_total": tables.get("tables_total"),
        "rows_lost": tables.get("rows_lost"),
        "rows_lost_population": tables.get("rows_lost_population"),
        "columns_lost": tables.get("columns_lost"),
        "columns_lost_population": tables.get("columns_lost_population"),
        "tables_witnessed_lines": tables.get("tables_witnessed_lines"),
        "figures_total": figures.get("figures_total"),
        "degeneration": tripwires.get("degeneration"),
        "assets": assets_count,
        "extraction_surya": extraction.get("surya"),
        "fixes_effective": _fixes_effective(manifest.get("fixes") or [], manifest.get("fixes_stats")),
    }


_GET_CHARS_FIXES = ("charbox-lift", "offpage-clip")   # the two fixes that live in pdftext's get_chars wrapper (fixes.py)


def _fixes_effective(fixes: list, stats) -> bool | None:
    """Did the job's named get_chars fix actually read the document? S211 E1: Bill C-30's ~160 carried `offpage-clip`
    with every counter at ZERO — pdftext's workers read the pages, the wrapper saw none (CORRECTIONS row 5). None when
    no get_chars fix was named or the record has no counters (UNREAD, never False); False when a get_chars fix is named
    and the wrapper saw no char; True when it saw chars. A reading beside the selection, never a constraint — the
    measures already say what the document became; this says whether the fix was in the room."""
    if not any(f in _GET_CHARS_FIXES for f in fixes):
        return None
    if not isinstance(stats, dict) or stats.get("chars_seen") is None:
        return None
    return bool(stats.get("chars_seen"))


def register(bundle_dir) -> dict:
    """summarize(bundle_dir) and store it under registry[sha]["variants"][dir] (idempotent — the
    same bundle registered twice yields the same stored entry). Tracks registry[sha]["original"]
    as the earliest converted_at seen for this sha (never rewritten to a LATER timestamp).
    registry[sha]["variants"] and ["original"] are never deleted, only added to. Writes
    atomically. Returns the stored entry."""
    bp = Path(bundle_dir)
    entry = summarize(bp)
    # selected_dir() must resolve to an absolute path; "root"+"dir" alone cannot (this module
    # deliberately never imports fp_paths.py), so the caller's own path is carried on the entry.
    entry["path"] = str(bp.resolve()) if bp.exists() else str(bp)

    sha = entry.get("source_sha256")
    if not sha:
        raise ValueError("manifest at %s carries no source_sha256 -- cannot register" % bp)

    registry = _load_registry()
    bucket = registry.setdefault(sha, {})
    variants = bucket.setdefault("variants", {})
    variants[entry["dir"]] = entry

    ts = entry.get("converted_at")
    if ts is not None and (bucket.get("original") is None or ts < bucket["original"]):
        bucket["original"] = ts

    _write_registry_atomic(registry)
    return entry


_ERROR_FIELDS = ("words_lost", "inventions_total", "rows_lost", "columns_lost",
                  "numbers_missing", "numbers_extra")


def _error_sum(entry: dict) -> tuple[int, list[str]]:
    """sum of _ERROR_FIELDS, None treated as 0 -- with the None fields named (for the reason
    sentence), never silently folded into the total."""
    total = 0
    none_fields = []
    for f in _ERROR_FIELDS:
        v = entry.get(f)
        # S211 E3: the honest rest (the count net of the layer's own line-wrap joins) is the error when the manifest
        # carries it; an older manifest's raw count stands in, named in _EXCL_PREFERRED's absence list by the caller.
        ex = _EXCL_PREFERRED.get(f)
        if ex is not None and entry.get(ex) is not None:
            v = entry.get(ex)
        if v is None:
            none_fields.append(f)
        else:
            total += v
    return total, none_fields


# S211 E3: for these two error fields the honest rest is preferred when present (see fidelity_audit.audit_inventions)
_EXCL_PREFERRED = {"words_lost": "words_lost_excl_joined", "inventions_total": "inventions_excl_joined"}


def _verdict_rank(verdict) -> int:
    if verdict == "pass":
        return 3
    if verdict == "flag":
        return 2
    return 1  # anything else (fail, unknown, None, ...)


def rank(entry: dict) -> tuple:
    """verdict rank, then -(errors) (higher rank = fewer errors), then survival_convert, then
    survival_analyst, then converted_at -- every one of these wins ties toward the LARGER value
    under max(). A missing survival sorts as the worst possible (-1.0, below any real 0.0-1.0)."""
    errors, _none_fields = _error_sum(entry)
    sc = entry.get("survival_convert")
    sa = entry.get("survival_analyst")
    return (
        _verdict_rank(entry.get("verdict")),
        -errors,
        sc if sc is not None else -1.0,
        sa if sa is not None else -1.0,
        entry.get("converted_at") or "",
    )


def faithful(candidate: dict, baseline: dict) -> tuple[bool, list[str], list[str]]:
    """(ok, violations, unread). A constraint with None on either side is UNREAD and NAMED --
    never a violation. columns_lost is only checked when BOTH sides witnessed at least one table
    line (tables_witnessed_lines > 0); otherwise it reads "columns unsupported" (UNREAD, not a
    violation) -- the table's geometry witness never ran, so nothing can be claimed about it."""
    violations: list[str] = []
    unread: list[str] = []

    def not_more(name: str) -> None:
        c, b = candidate.get(name), baseline.get(name)
        if c is None or b is None:
            unread.append(name + " unread")
        elif c > b:
            violations.append("%s increased: %s > %s" % (name, c, b))

    def not_less(name: str) -> None:
        c, b = candidate.get(name), baseline.get(name)
        if c is None or b is None:
            unread.append(name + " unread")
        elif c < b:
            violations.append("%s decreased: %s < %s" % (name, c, b))

    def not_more_honest(name: str) -> None:
        """S211 E3: words_lost and inventions_total carry the layer's own line-wrap joins (Bill C-30 ~160c: 574 lost /
        167 invented on the layer path against 479 / 27 on the OCR path, which never joins) -- the raw counts compare
        two vocabularies, not two conversions. The honest rest (`*_excl_joined`) is compared when BOTH sides carry it;
        when either side was audited before the key existed the constraint is UNREAD and NAMED, never a violation
        read off the raw count (rank still orders on each entry's own honest-or-raw error sum)."""
        ex = _EXCL_PREFERRED[name]
        if candidate.get(ex) is not None and baseline.get(ex) is not None:
            not_more(ex)
        else:
            unread.append("%s unread (%s absent on %s; the raw count carries the join artifact)"
                          % (name, ex, "both" if candidate.get(ex) is None and baseline.get(ex) is None
                             else ("candidate" if candidate.get(ex) is None else "baseline")))

    not_more_honest("words_lost")
    not_less("survival_convert")
    not_less("assets")
    not_less("tables_total")
    not_more("rows_lost")

    ctw, btw = candidate.get("tables_witnessed_lines"), baseline.get("tables_witnessed_lines")
    if ctw is not None and btw is not None and ctw > 0 and btw > 0:
        not_more("columns_lost")
    else:
        unread.append("columns unsupported")

    deg = candidate.get("degeneration")
    if deg is True:
        violations.append("degeneration: True")
    elif deg is None:
        unread.append("degeneration unread")

    not_more_honest("inventions_total")

    return (len(violations) == 0, violations, unread)


_TIE_NOTE = "tied on every measured number — the incumbent stays; what no measure sees is not a reason to switch"


def _selection_rank(entry: dict) -> tuple:
    """The four MEASURED fields the tie rule compares -- (verdict rank, -errors, survival_convert,
    survival_analyst) -- rank() with converted_at dropped. S211 Lane C (Rab's word 2026-09-21):
    converted_at is no longer a tie-breaker for SELECTION (a candidate must not unseat the
    incumbent merely for being newer when nothing measured moved); rank() itself is UNCHANGED and
    keeps converted_at as its last element, used only to order the `ordered` variants listing and,
    below, to break a tie between two CHALLENGERS that both beat the baseline (today's rule
    protects the incumbent from a tie, not two new variants from each other)."""
    return rank(entry)[:-1]


def _refusal(entry: dict, violations: list[str], unread: list[str]) -> dict:
    """One refused variant's record — a dict literal that LEAVES a function, so the glass census harvests its keys
    (S211: built inline inside refused.append, `violations` read as a stale signature; the census sees literals a
    function returns, never one hung on a call)."""
    return {
        "dir": entry.get("dir"),
        "violations": violations,
        "unread": unread,
    }


def select(sha: str, reset: bool = False) -> dict:
    """baseline = the current selected entry if any, else the variant whose converted_at equals
    the tracked "original" (falling back to the earliest-dated variant if "original" is absent
    or stale -- e.g. a registry written before this field existed). candidates = every variant
    faithful against that baseline; the baseline itself is ALWAYS a candidate, even if its own
    self-comparison would otherwise read a violation (e.g. its own degeneration is True -- it is
    still the only book anyone has). S211 Lane C: a candidate whose _selection_rank (verdict,
    errors, survival_convert, survival_analyst -- rank() without converted_at) EQUALS the
    baseline's is a TIE -- the baseline stays selected and the candidate is listed under
    ["tied"], never promoted on converted_at alone; a candidate whose _selection_rank is
    STRICTLY greater still wins outright (selected = max of those, by the full rank() including
    converted_at, which only orders a tie between two such challengers). Writes ["selected"],
    ["reason"], ["refused"], ["tied"], ["selected_at"]; never deletes ["variants"] or
    ["original"]. Returns the updated per-sha bucket."""
    registry = _load_registry()
    bucket = registry.get(sha)
    if not bucket or not bucket.get("variants"):
        raise ValueError("no variants registered for sha %r" % (sha,))
    variants = bucket["variants"]

    sel_dir = bucket.get("selected")
    if sel_dir and sel_dir in variants and not reset:
        baseline = variants[sel_dir]
    else:
        # S211 E3 (`reset`): the incumbent is the ORIGINAL — the earliest conversion — never a selection that was itself
        # made on converted_at under the rule Lane C retired (Bill C-288's ~160b: equal numbers, a worse page, chosen as
        # the newest; a sticky baseline would have kept it as "the incumbent"). One re-cut over the shelf, then sticky.
        dated = sorted(variants.values(), key=lambda v: (v.get("converted_at") or "", v.get("dir") or ""))
        original_ts = bucket.get("original")
        matches = [v for v in dated if original_ts is not None and v.get("converted_at") == original_ts]
        baseline = matches[0] if matches else (dated[0] if dated else None)
    if baseline is None:
        raise ValueError("could not determine a baseline for sha %r" % (sha,))

    ordered = sorted(variants.values(), key=lambda v: v.get("dir") or "")
    candidates: list[dict] = []
    refused: list[dict] = []
    for v in ordered:
        if v.get("dir") == baseline.get("dir"):
            candidates.append(v)
            continue
        ok, violations, unread = faithful(v, baseline)
        if ok:
            candidates.append(v)
        else:
            refused.append(_refusal(v, violations, unread))

    # S211 Lane C: a candidate that TIES the baseline on every measured number is not a reason to
    # switch -- the incumbent (baseline) stays selected and the tying candidate is named under
    # `tied`, never silently promoted by converted_at alone. A candidate strictly better than the
    # baseline on the measured rank still wins outright.
    baseline_rank = _selection_rank(baseline)
    tied: list[dict] = []
    better: list[dict] = []
    for c in candidates:
        if c.get("dir") == baseline.get("dir"):
            continue
        c_rank = _selection_rank(c)
        if c_rank == baseline_rank:
            tied.append(c)
        elif c_rank > baseline_rank:
            better.append(c)
        # else: strictly worse than the incumbent on the measured rank -- faithful, but neither
        # selected, tied, nor refused; it simply does not surface here (unchanged from before).

    selected = max(better, key=rank) if better else baseline
    tied_entries = [{"dir": c.get("dir"), "note": _TIE_NOTE} for c in tied]

    errors, none_fields = _error_sum(selected)
    none_note = " [None treated as 0: %s]" % ", ".join(none_fields) if none_fields else ""
    tie_note = ""
    if tied_entries:
        tie_bits = []
        for c in tied:
            fx = c.get("fixes_effective")
            if fx is False:
                tie_bits.append("%r (fixes_effective=False)" % c.get("dir"))
            else:
                tie_bits.append("%r" % c.get("dir"))
        tie_note = " Tied against %s -- the incumbent stays." % ", ".join(tie_bits)
    reason = (
        "selected %r by rank (verdict=%r, errors=%s%s, survival_convert=%s, "
        "survival_analyst=%s) against baseline %r; %d of %d variant(s) refused as unfaithful.%s"
        % (selected.get("dir"), selected.get("verdict"), errors, none_note,
           selected.get("survival_convert"), selected.get("survival_analyst"),
           baseline.get("dir"), len(refused), len(variants), tie_note)
    )

    bucket["selected"] = selected.get("dir")
    bucket["reason"] = reason
    bucket["refused"] = refused
    bucket["tied"] = tied_entries
    bucket["selected_at"] = datetime.now(timezone.utc).isoformat()
    registry[sha] = bucket
    _write_registry_atomic(registry)
    return bucket


def rename_entry(sha: str, old_dir: str, new_path) -> dict | None:
    """S211 (the held park supersedes by RENAME, never by deletion): the entry stored under old_dir
    moves to the renamed bundle's basename with its path updated; if it was the selected one, the
    selection follows it — so the next select() judges the newcomer against the book that was
    current, never against itself. Nothing is deleted; a sha or dir the registry does not know
    returns None. Writes atomically."""
    registry = _load_registry()
    bucket = registry.get(sha)
    if not bucket or old_dir not in (bucket.get("variants") or {}):
        return None
    np = Path(new_path)
    entry = bucket["variants"].pop(old_dir)
    entry["dir"] = np.name
    entry["path"] = str(np.resolve()) if np.exists() else str(np)
    bucket["variants"][np.name] = entry
    if bucket.get("selected") == old_dir:
        bucket["selected"] = np.name
    registry[sha] = bucket
    _write_registry_atomic(registry)
    return entry


def selected_dir(sha: str) -> str | None:
    """The absolute path (anchor or held root) of the currently-selected variant, or None if
    this sha has never been registered or never had select() run."""
    registry = _load_registry()
    bucket = registry.get(sha)
    if not bucket:
        return None
    dirname = bucket.get("selected")
    if not dirname:
        return None
    entry = (bucket.get("variants") or {}).get(dirname)
    if not entry:
        return None
    return entry.get("path")


def _print_show(bucket: dict) -> None:
    """S211 Lane C: the CLI's `show` no longer dumps the raw per-sha JSON blob (still available
    via `list`, or by reading the registry file directly) -- it prints selected / tied / refused
    compactly, the three things a human asking "what happened to this sha" wants first."""
    if not bucket:
        print("(no variants registered for this sha)")
        return
    print("selected: %r" % bucket.get("selected"))
    print("reason: %s" % bucket.get("reason"))
    tied = bucket.get("tied") or []
    print("tied (%d):" % len(tied))
    for t in tied:
        print("  %r -- %s" % (t.get("dir"), t.get("note")))
    refused = bucket.get("refused") or []
    print("refused (%d):" % len(refused))
    for r in refused:
        print("  %r -- violations=%s unread=%s" % (r.get("dir"), r.get("violations"), r.get("unread")))


def _cli(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="variants.py", description="the variant registry and whitelist (Lane A, S211)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_register = sub.add_parser("register", help="summarize + store a bundle_dir under its sha256")
    p_register.add_argument("bundle_dir")

    p_select = sub.add_parser("select", help="pick the whitelisted variant for a sha256")
    p_select.add_argument("sha")
    p_select.add_argument("--reset", action="store_true",
                          help="S211 E3: the incumbent is the ORIGINAL (the earliest conversion), not the current selection")

    p_show = sub.add_parser("show", help="print the registry's current record for a sha256")
    p_show.add_argument("sha")

    sub.add_parser("list", help="print the whole registry")

    args = parser.parse_args(argv)

    if args.command == "register":
        print(json.dumps(register(args.bundle_dir), indent=2))
        return 0
    if args.command == "select":
        print(json.dumps(select(args.sha, reset=bool(getattr(args, "reset", False))), indent=2))
        return 0
    if args.command == "show":
        _print_show(_load_registry().get(args.sha, {}))
        return 0
    if args.command == "list":
        print(json.dumps(_load_registry(), indent=2))
        return 0
    parser.error("unknown command")  # pragma: no cover -- argparse's `required=True` makes this unreachable
    return 2


if __name__ == "__main__":
    sys.exit(_cli())
