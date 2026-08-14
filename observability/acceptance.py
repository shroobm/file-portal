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
    print("\n  [2] the documented limit — §5.1 is weaker than §7.2 wants")
    check(
        "pages_scored reads glass (referenced as a denominator, never displayed)",
        verdicts.get("pages_scored") == {"glass"},
    )

    print("\n  [3] dispositions.json is a record of judgment")
    cfg = json.loads((HERE / "dispositions.json").read_text(encoding="utf-8"))
    for sig, entry in cfg.get("dispositions", {}).items():
        check(f"{sig}: disposition is one of the five", entry.get("disposition") in VALID)
        check(f"{sig}: silence is signed with a reason", bool(entry.get("reason", "").strip()))
    check("no stale signatures (a key that is gone)", data["stale"] == [])

    print("\n  [4] the guard fires on a planted glitch")
    check("negative test: a planted unreferenced key is reported", _planted_glitch_is_caught())

    # §5.4's mode is the one that PREVENTS the class rather than finding it late, so it needs
    # its own proof that the filter is applied at all — a `--since` that silently ignored its
    # argument would report a clean scope forever and look exactly like success.
    print("\n  [5] §5.4 same-commit scoping actually filters")
    since_head = _census(["--since", "HEAD"])
    scoped = sum(len(lane["rows"]) for lane in since_head["lanes"].values())
    total = sum(len(lane["rows"]) for lane in data["lanes"].values())
    check(f"--since HEAD scopes to 0 keys (full census has {total})", scoped == 0 and total > 0)

    failed = [n for n, ok in results if not ok]
    print(f"\n{'PASS' if not failed else 'FAIL'} — {len(results) - len(failed)}/{len(results)} checks")
    for n in failed:
        print(f"  failed: {n}")
    print(f"\ncensus: {len(data['glitches'])} unsigned glitch(es) across {len(data['lanes'])} lanes")
    return 1 if failed else 0


def _census(extra: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(DETECTOR), "--json", *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    return json.loads(proc.stdout)


def _planted_glitch_is_caught() -> bool:
    """A guard nobody has watched fire is not a guard (SYM-001). Plant a producer whose key no
    renderer can possibly name, in a throwaway lane, and require the detector to report it."""
    import tempfile

    with tempfile.TemporaryDirectory(dir=str(ROOT)) as td:
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
                    "producers": [f"{d.name}/producer.py"],
                    "renderers": [f"{d.name}/renderer.html"],
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
