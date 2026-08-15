#!/usr/bin/env python3
"""Acceptance harness for the glass detector — docs/29 §5.1.

The detector's only real claim is that it reproduces mechanically what the S77 lanes found by
hand. So the harness IS that claim, pinned: docs/29 §7's ranked findings become an answer key
the detector must agree with, row for row. Four were fixed by S76/S77 and must now read
`glass`; five are open and must read `GLITCH`. A detector that stops finding the open ones has
regressed; one that starts flagging the fixed ones has gone blind to a repair.

Deliberately END-TO-END against the REAL trees, never fixtures. A fixture would share the
extractor's assumptions about what a producer looks like, and two checks that share an
assumption are one check (SYM-001) — which is exactly how `seams` and `chunks_resumed` slipped
past the first version of the detector: it tested `Return(Name)` and `Return(Dict)` while both
producers return a TUPLE holding the payload. The answer key caught that; a fixture would not.

House style follows `prototypes/repair-bench/acceptance.py`. Stdlib only — no pytest on this
machine, and a check you cannot run is not a check.

    python observability/acceptance.py     # exit 0 = pass
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DETECTOR = HERE / "glass_detector.py"
VALID = {"GLASS", "EVIDENCE", "REPORT", "INTERNAL", "DEAD"}

# docs/29 §7, ranked by what a human would want most. (key, expected verdict, why)
ANSWER_KEY = [
    ("vault_recommendation", "glass", "§7.1 — fixed S77; the rescore button now shows its answer"),
    ("coverage", "glass", "§7.1 — fixed S77"),
    ("outcome_reason", "glass", "§7.4 — the five-outcome triage, wired S77"),
    ("runs", "glass", "SYM-026 — omission runs, wired S76 as amber ◍ chips"),
    ("seams", "GLITCH", "§7.3 — recorded FOR the Bench (docs/18 §5.2); the Bench never reads it"),
    ("chunks_resumed", "GLITCH", "§7.5 — the power-cut recovery, silenced on two channels"),
    ("recent_audits", "GLITCH", "§7.6 — a ready-made 'last 6 books' digest, rendered nowhere"),
    ("reverse_sample", "GLITCH", "§7.8 — the promised precision tripwire, read by nothing"),
    ("dict_hit", "GLITCH", "a signed threshold (docs/15) whose input is hardcoded None"),
]

results: list[tuple[str, bool]] = []


def check(name: str, cond: bool) -> None:
    results.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name, flush=True)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    print("──────── GLASS DETECTOR ACCEPTANCE · docs/29 §5.1 ────────\n")

    proc = subprocess.run(
        [sys.executable, str(DETECTOR), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        print(f"  FAIL  detector exited {proc.returncode}\n{proc.stderr}")
        return 1
    data = json.loads(proc.stdout)

    verdicts: dict[str, set[str]] = {}
    for lane in data["lanes"].values():
        for row in lane["rows"]:
            verdicts.setdefault(row["key"], set()).add(row["verdict"])

    print("  [1] reproduces the S77 hand census (docs/29 §7)")
    for key, expected, why in ANSWER_KEY:
        seen = verdicts.get(key)
        if seen is None:
            check(f"{key}: EXTRACTED at all — {why}", False)
            continue
        check(f"{key}: {expected} ({', '.join(sorted(seen))}) — {why}", expected in seen)

    # §7.2 is the law's own gap, pinned rather than papered over. `main.js` and `room.js` both
    # name `st.pages_scored` — as the DENOMINATOR positioning run marks, never as a number a
    # human reads. So it satisfies §5.1 ("referenced by a renderer") while §7.2's complaint
    # ("never printed") still stands. The detector is a FLOOR: what it reports is real, what it
    # passes is not proven. If this flips, re-read the assumption — that is the point of it.
    # DISCLOSURE, not a scored check. The S78 version asserted `== {"glass"}` — an equality on
    # a BLINDNESS. If someone deleted the run-mark rendering (making pages_scored a genuine,
    # actionable glitch) the detector would correctly report GLITCH and the suite would go RED
    # for the detector becoming more correct. A test whose green depends on a gap staying open
    # is not a test. docs/31 §2.
    print("\n  [2] disclosure — §5.1 is weaker than docs/29 §7.2 wants (not scored)")
    ps = verdicts.get("pages_scored")
    if ps == {"glass"}:
        print("       pages_scored: glass — referenced by main.js/room.js as the DENOMINATOR")
        print("       positioning run marks, never displayed. §5.1 satisfied, §7.2 still open.")
    else:
        print(f"       pages_scored: {sorted(ps) if ps else 'ABSENT'} — CHANGED since S78.")
        print("       Go read docs/29 §7.2; the last reference may have been removed.")

    # The answer key is a SELECTION and saying so is part of being honest about it: §7 holds
    # ~16 field-level findings and ANSWER_KEY scores 9. Of the 8 omitted, SEVEN are cases the
    # detector gets WRONG (docs/31 §1.9) — they are omitted because the detector has no notion
    # of producer SITE, which is docs/29 §8 semantic work Rab has not signed. Printing them
    # every run keeps the omission visible instead of letting silence do the hiding, which is
    # the whole subject of docs/29.
    print("\n  [2b] disclosure — §7 findings NOT in the answer key (detector gets these wrong)")
    for k, why in [
        ("note", "§7.9 — receipts 'where did my book land'"),
        ("sha", "§7.9 — absent from the census entirely; exporter.py is in no lane"),
        ("model", "§7.10 — cleared by the transcribe-proposal render, not the persisted record"),
        ("gates", "§7.10 — same"),
        ("secs", "§7.10 — same"),
        ("cycle", "§7.10 — same"),
        ("rect", "§7.10 — same"),
    ]:
        seen = verdicts.get(k)
        print(f"       {k:8} {(', '.join(sorted(seen)) if seen else 'not extracted'):10} {why}")

    print("\n  [3] dispositions.json is a record of judgment")
    cfg = json.loads((HERE / "dispositions.json").read_text(encoding="utf-8"))
    for sig, entry in cfg.get("dispositions", {}).items():
        check(f"{sig}: disposition is one of the five", entry.get("disposition") in VALID)
        check(f"{sig}: silence is signed with a reason", bool(entry.get("reason", "").strip()))
    check("no stale signatures (a key that is gone)", data["stale"] == [])

    print("\n  [4] the guard fires on a planted glitch")
    check("negative test: a planted unreferenced key is reported", _planted_glitch_is_caught())

    # §5.4's mode is the one that PREVENTS the class rather than finding it late, so it needs
    # proof the filter is applied at all — a `--since` that silently ignored its argument would
    # report a clean scope forever and look exactly like success.
    #
    # The S78 version wrote that comment and then tested `--since HEAD`: an EMPTY DIFF. It could
    # not distinguish a working filter from a no-op, and — because the crash only fires on
    # non-ASCII bytes in a real diff — it was the one input that could not reach the bug that
    # made the whole signed mode exit 1. It reported PASS 13/13 over a broken feature.
    # docs/31 §1.2. Every check below therefore runs against a REAL, NON-EMPTY diff.
    print("\n  [5] §5.4 same-commit scoping, against a real diff")
    keyed, nonascii = _exercising_ref()
    total = sum(len(lane["rows"]) for lane in data["lanes"].values())

    # The crash regression (docs/31 §1.1) needs a diff with NON-ASCII bytes in it — that is the
    # whole bug: git's output decoded as cp1252. Asserting on the EXIT CODE, not on a count:
    # the S78 version asserted `scoped_rows >= 0`, a sum of len()s, which is a tautology — the
    # regression test for the headline bug could not fail. And a real crash never reached it,
    # because _census raises on empty stdout and the harness tracebacks instead of printing FAIL.
    if nonascii is None:
        print("       SKIP — no ref in the last 40 commits has a non-ASCII diff")
    else:
        check(
            f"--since {nonascii[:7]} survives a NON-ASCII diff (the cp1252 crash: exit 1)",
            _rc(["--since", nonascii]) == 0,
        )

    if keyed is None:
        print("       SKIP — no ref in the last 40 commits introduces an extractable key")
    else:
        scoped = _census(["--since", keyed])
        scoped_rows = sum(len(lane["rows"]) for lane in scoped["lanes"].values())
        check(f"--since {keyed[:7]} finds keys ({scoped_rows}) — the filter is not a no-op",
              scoped_rows > 0)
        check(f"--since {keyed[:7]} is narrower than the full census ({total})",
              scoped_rows < total)
        check("--since did not silently fall back", scoped.get("since_fell_back") is False)

    print("\n  [6] the guards fire when stepped on (tripwires)")
    bad = _census(["--since", "zz-no-such-ref-zz"])
    check("a bad --since ref is MARKED as a fallback, not passed off as scoped",
          bad.get("since_fell_back") is True)
    check("a typo'd --lane name exits 2, never a silent 0", _rc(["--lane", "zz-nope", "--enforce"]) == 2)
    check("a producer glob matching nothing is fatal under --enforce", _empty_glob_is_caught())
    check("a stale signature is caught in the SIGNED (--since) mode", _stale_caught_under_since())

    failed = [n for n, ok in results if not ok]
    print(f"\n{'PASS' if not failed else 'FAIL'} — {len(results) - len(failed)}/{len(results)} checks")
    for n in failed:
        print(f"  failed: {n}")
    print(
        f"\ncensus: {data['glitch_count']} unsigned glitch(es) at {len(data['glitches'])} site(s) "
        f"across {len(data['lanes'])} lanes"
    )
    return 1 if failed else 0


def _census(extra: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(DETECTOR), "--json", *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    if not proc.stdout:
        raise RuntimeError(f"detector produced no output for {extra}:\n{proc.stderr}")
    return json.loads(proc.stdout)


def _rc(extra: list[str]) -> int:
    return subprocess.run(
        [sys.executable, str(DETECTOR), *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    ).returncode


def _diff_since(ref: str) -> str | None:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "-U0", ref, "--", "*.py", "*.rs"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return out.stdout if out.returncode == 0 else None


def _exercising_ref() -> tuple[str | None, str | None]:
    """Two refs, each chosen for the PROPERTY it must exercise — never for a proxy.

    S78: the first version of this picked a ref by `len(diff) > 500` and called it "guaranteed
    non-empty AND contains non-ASCII". Byte length is neither. `ed20c02` added 171 lines with no
    dict-key literal in them, sailed past the 500-byte gate, and turned the suite RED two commits
    after it was written — not because the detector regressed, but because of the incidental
    content of an unrelated commit. A guard that stands in for the property it asserts will
    eventually assert something else.

    Returns (ref whose diff yields >=1 extracted key, ref whose diff contains non-ASCII).
    They are usually the same ref and need not be. Either may be None on a shallow history —
    the caller reports that as a skip, never as a pass.
    """
    keyed = nonascii = None
    for n in range(1, 40):
        ref = f"HEAD~{n}"
        diff = _diff_since(ref)
        if diff is None:
            break
        if keyed is None:
            found = _census(["--since", ref])
            if sum(len(ln["rows"]) for ln in found["lanes"].values()) > 0:
                keyed = ref
        if nonascii is None and any(ord(c) > 127 for c in diff):
            nonascii = ref
        if keyed and nonascii:
            break
    return keyed, nonascii


def _tmp_cfg(mutate) -> str:
    """A copy of the real config with one thing broken, written to the system temp dir (NOT the
    repo — S78 put TemporaryDirectory(dir=ROOT) here and an interrupted run leaked an untracked
    dir into git status, on a machine that has had two power cuts mid-run)."""
    import tempfile

    cfg = json.loads((HERE / "dispositions.json").read_text(encoding="utf-8"))
    mutate(cfg)
    fd, path = tempfile.mkstemp(suffix=".json", prefix="glassdet-")
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


def _empty_glob_is_caught() -> bool:
    def break_it(cfg):
        cfg["lanes"] = [
            {
                "name": "bench",
                "producers": ["prototypes/repair-bench/RENAMED_AWAY.py"],
                "renderers": ["prototypes/repair-bench/bench.html"],
            }
        ]

    p = _tmp_cfg(break_it)
    try:
        return _rc(["--config", p, "--enforce"]) == 1
    finally:
        Path(p).unlink(missing_ok=True)


def _stale_caught_under_since() -> bool:
    def plant(cfg):
        cfg["dispositions"] = {
            "bench:zz_key_that_no_longer_exists": {
                "disposition": "DEAD",
                "reason": "planted by the acceptance harness",
            }
        }

    p = _tmp_cfg(plant)
    try:
        ref, _ = _exercising_ref()
        if ref is None:
            return False
        rc = _rc(["--config", p, "--enforce", "--since", ref])
        seen = _census(["--config", p, "--since", ref]).get("stale") or []
        return rc == 1 and "bench:zz_key_that_no_longer_exists" in seen
    finally:
        Path(p).unlink(missing_ok=True)


def _planted_glitch_is_caught() -> bool:
    """A guard nobody has watched fire is not a guard (SYM-001). Plant a producer whose key no
    renderer can possibly name, in a throwaway lane, and require the detector to report it."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "producer.py").write_text(
            'def state():\n    return {"zz_planted_glitch_never_rendered": 1, "shared": 2}\n',
            encoding="utf-8",
        )
        (d / "renderer.html").write_text("<p>shared</p>\n", encoding="utf-8")
        cfg = {
            "lanes": [
                {
                    "name": "planted",
                    "producers": [str(d / "producer.py")],
                    "renderers": [str(d / "renderer.html")],
                }
            ],
            "dispositions": {},
        }
        cfgp = d / "cfg.json"
        cfgp.write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(DETECTOR), "--config", str(cfgp), "--enforce", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
        )
        if proc.returncode != 1:  # --enforce must make an unsigned glitch fatal
            return False
        out = json.loads(proc.stdout)
        keys = {k for _, k, _, _, _ in out["glitches"]}
        # the planted key is caught, and the rendered one is NOT falsely accused
        return keys == {"zz_planted_glitch_never_rendered"}


if __name__ == "__main__":
    sys.exit(main())
