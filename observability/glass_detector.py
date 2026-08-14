#!/usr/bin/env python3
"""The glass detector — docs/29 §5.1, made mechanical.

    For every dict a producer returns or persists, walk its keys and confirm each is
    referenced by at least one renderer.

The S77 lanes performed exactly this check by hand with `grep`, which is why it is
automatable, and found ~83 fields that were computed correctly, written to disk, and read by
nobody. This script is that hand-grep, run every time instead of once.

A key that no renderer references is not automatically a defect — docs/29 §5.3 step 4 is
"does it already have a home, anywhere, live or archival?". So the detector never decides. It
partitions:

    GLASS-BY-REFERENCE  a renderer names it        -> silent, nothing to do
    SIGNED SILENCE      dispositions.json names it -> silent, the reason is on the record
    GLITCH              neither                    -> reported, and fatal under --enforce

That third case is docs/29's definition of a glitch: a real terminus whose step-4 answer is
*nowhere*. The point of the dispositions file is that silence must be **signed, never
defaulted** (§4) — the cost of ignoring a producer's key stops being zero.

Usage
-----
    python observability/glass_detector.py                # census, always exit 0
    python observability/glass_detector.py --enforce      # exit 1 on any unsigned glitch
    python observability/glass_detector.py --lane bench   # one lane
    python observability/glass_detector.py --since HEAD~1 # §5.4: only keys added since REF
    python observability/glass_detector.py --json         # machine-readable

Whether this runs in CI, in the closeout ritual, or both is docs/29 §8 decision 3 and is
UNSIGNED. Until Rab signs it, the default is report-only.

Honest limits (read these before trusting a clean run):
  * A key whose name is a common word ("name", "id", "kind", "size") will almost always find
    an incidental match in a renderer and be scored GLASS. The detector is a FLOOR: what it
    reports is real, what it passes is not proven. Distinctive names are checked well;
    generic ones are not checkable this way at all.
  * Reference means "the renderer's text contains this identifier", not "this value reaches a
    human". A key named in dead code counts as referenced.
  * Only string-literal keys are seen. Computed keys (f-strings, ** merges from elsewhere) are
    invisible; `{**r, "anchor_line": at}` contributes `anchor_line` but not r's own keys.
No stdlib-only static check can fix these. They are the reason §5.4's same-commit timing rule
is the part that actually prevents the class, and this script is only the net underneath it.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "dispositions.json"

VALID_DISPOSITIONS = {"GLASS", "EVIDENCE", "REPORT", "INTERNAL", "DEAD"}

# Keys this short are never distinctive enough for a word-boundary search to mean anything.
MIN_KEY_LEN = 3


# --------------------------------------------------------------------------------------------
# producers — extracting the keys of every dict that is returned or persisted
# --------------------------------------------------------------------------------------------


class _PyProducer(ast.NodeVisitor):
    """Collect string keys of dicts that leave the function: returned directly, returned via a
    local, appended to a list that is returned, or handed to json.dump/dumps.

    Deliberately NOT "every dict literal in the file" — that would drown the census in config
    tables and lookup maps, and a census nobody reads is the very failure this detects.
    """

    def __init__(self) -> None:
        self.found: list[tuple[str, int, str]] = []  # (key, lineno, context)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._scan_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._scan_function(node)
        self.generic_visit(node)

    def _scan_function(self, fn: ast.AST) -> None:
        name = getattr(fn, "name", "?")

        # 1. names that are returned, and dicts returned literally.
        #    Walk the whole return expression rather than matching its top-level shape: the two
        #    biggest producers in this repo return TUPLES holding the payload
        #    (`return md, assets, wall, peak, chunking, stats` — convert_and_ship.py; `return
        #    unfence(...), meta` — analyst.py). A `Return(Name)`/`Return(Dict)` test misses both,
        #    and with them `seams` and `chunks_resumed`: docs/29 §7.3 and §7.5, two of the ten
        #    findings this detector exists to reproduce.
        returned_names: set[str] = set()
        escaping: list[ast.Dict] = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Return) and n.value is not None:
                for sub in ast.walk(n.value):
                    if isinstance(sub, ast.Dict):
                        escaping.append(sub)
                    elif isinstance(sub, ast.Name):
                        returned_names.add(sub.id)

        # 2. dicts assigned to, or appended to, something that is returned
        #    (two passes: a returned dict's values can name more locals, e.g. {"runs": runs})
        for _ in range(2):
            for d in list(escaping):
                for v in d.values:
                    if isinstance(v, ast.Name):
                        returned_names.add(v.id)
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
                    for t in n.targets:
                        if isinstance(t, ast.Name) and t.id in returned_names:
                            escaping.append(n.value)
                if (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr in {"append", "insert"}
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id in returned_names
                ):
                    for a in n.args:
                        if isinstance(a, ast.Dict):
                            escaping.append(a)

        # 3. dicts that are persisted rather than returned
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if n.func.attr in {"dump", "dumps"}:
                    for a in n.args:
                        if isinstance(a, ast.Dict):
                            escaping.append(a)

        seen: set[int] = set()
        for d in escaping:
            if id(d) in seen:
                continue
            seen.add(id(d))
            self._harvest(d, name)

    def _harvest(self, d: ast.Dict, ctx: str) -> None:
        """Keys of this dict and of every dict nested in its values — a nested dict that rides
        out inside a returned payload escapes just as surely as the top level."""
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                self.found.append((k.value, k.lineno, ctx))
            for sub in ast.walk(v) if v is not None else []:
                if isinstance(sub, ast.Dict) and sub is not d:
                    self._harvest(sub, ctx)


def keys_from_python(path: Path) -> list[tuple[str, int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  ! could not parse {path}: {e}", file=sys.stderr)
        return []
    p = _PyProducer()
    p.visit(tree)
    return p.found


_JSON_BANG = re.compile(r"json!\s*\(")
_RS_KEY = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:')
_SERDE_RENAME = re.compile(r'#\[serde\s*\(\s*rename\s*=\s*"([^"]+)"')
_RS_FIELD = re.compile(r"^\s*pub\s+([a-z_][a-z0-9_]*)\s*:", re.M)


def keys_from_rust(path: Path) -> list[tuple[str, int, str]]:
    """Rust producers speak two dialects: `json!({...})` literals and `#[derive(Serialize)]`
    structs. Both cross the same wire to the same JS."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[str, int, str]] = []

    # json!( ... ) — brace-matched so a nested payload is captured whole
    for m in _JSON_BANG.finditer(text):
        i, depth, start = m.end(), 0, m.end()
        while i < len(text):
            c = text[i]
            if c in "({[":
                depth += 1
            elif c in ")}]":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        block = text[start:i]
        line0 = text.count("\n", 0, start) + 1
        for km in _RS_KEY.finditer(block):
            out.append((km.group(1), line0 + block.count("\n", 0, km.start()), "json!"))

    # serde structs — take every `pub field:` in a Serialize-deriving struct, plus renames
    for sm in re.finditer(
        r"#\[derive\([^)]*Serialize[^)]*\)\][\s\S]{0,400}?struct\s+(\w+)\s*\{([\s\S]*?)\n\}",
        text,
    ):
        sname, body = sm.group(1), sm.group(2)
        line0 = text.count("\n", 0, sm.start(2)) + 1
        for fm in _RS_FIELD.finditer(body):
            out.append((fm.group(1), line0 + body.count("\n", 0, fm.start()), f"struct {sname}"))
        for rm in _SERDE_RENAME.finditer(body):
            out.append((rm.group(1), line0, f"struct {sname}"))
    return out


def keys_from(path: Path) -> list[tuple[str, int, str]]:
    if path.suffix == ".py":
        return keys_from_python(path)
    if path.suffix == ".rs":
        return keys_from_rust(path)
    return []


# --------------------------------------------------------------------------------------------
# renderers — does anything name this key?
# --------------------------------------------------------------------------------------------


def renderer_text(paths: list[Path]) -> str:
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths if p.is_file())


def referenced(key: str, blob: str, cache: dict[str, bool]) -> bool:
    if key in cache:
        return cache[key]
    hit = re.search(r"\b" + re.escape(key) + r"\b", blob) is not None
    cache[key] = hit
    return hit


# --------------------------------------------------------------------------------------------
# the timing rule (§5.4) — restrict the census to keys this change actually introduced
# --------------------------------------------------------------------------------------------


def added_keys_since(ref: str) -> set[str] | None:
    """String literals appearing on ADDED lines since `ref`. Line numbers shift under a diff,
    so this matches on the key text rather than pretending to track position."""
    try:
        diff = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "-U0", ref, "--", "*.py", "*.rs"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"! --since {ref} failed ({e}); falling back to the full census", file=sys.stderr)
        return None
    keys: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            keys.update(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', line))
    return keys


# --------------------------------------------------------------------------------------------


def main() -> int:
    # Windows consoles default to cp1252 and this report is full of box-drawing and §.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):  # already-wrapped or non-reconfigurable stream
            pass

    ap = argparse.ArgumentParser(description="docs/29 §5.1 — the glass detector")
    ap.add_argument("--enforce", action="store_true", help="exit 1 on any unsigned glitch")
    ap.add_argument("--lane", action="append", help="restrict to lane(s) by name")
    ap.add_argument("--since", metavar="REF", help="§5.4: only keys added since REF")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--config", default=str(CONFIG))
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    signed: dict[str, dict] = cfg.get("dispositions", {})

    for k, v in signed.items():
        d = v.get("disposition")
        if d not in VALID_DISPOSITIONS:
            print(f"! dispositions.json: {k} has invalid disposition {d!r}", file=sys.stderr)
            return 2
        if not v.get("reason"):
            print(f"! dispositions.json: {k} has no reason — silence must be signed", file=sys.stderr)
            return 2

    only_added = added_keys_since(args.since) if args.since else None

    report: dict[str, dict] = {}
    glitches: list[tuple[str, str, int, str, str]] = []
    used_signatures: set[str] = set()

    for lane in cfg["lanes"]:
        if args.lane and lane["name"] not in args.lane:
            continue
        producers = [p for g in lane["producers"] for p in sorted(ROOT.glob(g))]
        renderers = [p for g in lane["renderers"] for p in sorted(ROOT.glob(g))]
        blob = renderer_text(renderers)
        cache: dict[str, bool] = {}

        lane_rows: list[dict] = []
        for prod in producers:
            for key, lineno, ctx in keys_from(prod):
                if len(key) < MIN_KEY_LEN:
                    continue
                if only_added is not None and key not in only_added:
                    continue
                sig = f"{lane['name']}:{key}"
                if referenced(key, blob, cache):
                    verdict = "glass"
                elif sig in signed:
                    verdict = signed[sig]["disposition"].lower()
                    used_signatures.add(sig)
                else:
                    verdict = "GLITCH"
                    glitches.append(
                        (lane["name"], key, lineno, str(prod.relative_to(ROOT)), ctx)
                    )
                lane_rows.append(
                    {
                        "key": key,
                        "producer": str(prod.relative_to(ROOT)),
                        "line": lineno,
                        "context": ctx,
                        "verdict": verdict,
                    }
                )
        report[lane["name"]] = {
            "producers": [str(p.relative_to(ROOT)) for p in producers],
            "renderers": [str(p.relative_to(ROOT)) for p in renderers],
            "rows": lane_rows,
        }

    stale = sorted(set(signed) - used_signatures) if not (args.lane or args.since) else []

    if args.json:
        print(json.dumps({"lanes": report, "glitches": glitches, "stale": stale}, indent=2))
    else:
        _print_census(report, glitches, stale, args)

    if args.enforce and (glitches or stale):
        return 1
    return 0


def _print_census(report, glitches, stale, args) -> None:
    print("──────── GLASS DETECTOR · docs/29 §5.1 ────────")
    if args.since:
        print(f"    scope: keys added since {args.since} (§5.4 same-commit rule)")
    for name, lane in report.items():
        counts: dict[str, int] = {}
        for r in lane["rows"]:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        tally = " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "no keys"
        print(f"\n  [{name}] {len(lane['rows'])} keys — {tally}")
        print(f"      producers: {', '.join(lane['producers']) or '(none matched)'}")
        print(f"      renderers: {', '.join(lane['renderers']) or '(none matched)'}")

    if glitches:
        print(f"\n  ✗ {len(glitches)} UNSIGNED GLITCH(ES) — computed, stored, reaching nobody:")
        for lane, key, lineno, prod, ctx in glitches:
            print(f"      {lane}:{key}\n          {prod}:{lineno}  ({ctx})")
        print(
            "\n    Each needs a docs/29 §5.2 disposition. Walk §5.3 in order — the sharpest\n"
            "    question is step 4, 'does this already have a home anywhere, live or\n"
            "    archival?'. If the answer is nowhere and a human would act on it, wire it.\n"
            "    Otherwise record it in observability/dispositions.json WITH ITS REASON."
        )
    else:
        print("\n  ✓ no unsigned glitches")

    if stale:
        print(f"\n  ! {len(stale)} stale signature(s) — the key is gone, the disposition remains:")
        for s in stale:
            print(f"      {s}")

    print(
        "\n  Reads as clean is not the same as is clean: generic key names always find an\n"
        "  incidental match. See this file's docstring for the limits."
    )


if __name__ == "__main__":
    sys.exit(main())
