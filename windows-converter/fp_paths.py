"""fp_paths - the ONE resolver for pipeline filesystem roots (S108 Lane E, value-map bet 1).

Every path the desktop converter lane touches under the pipeline tree is named once in
roots.json (beside this file) and resolved here. FP_PIPELINE relocates the whole tree -
the mechanism the deferral-gate tripwire already used through events.py and
watch_and_convert.py; this module unifies it so no file can miss the override and point
a test run at the live library (SYM-010's class: a missed literal IS the data-loss path).

Contract:
  - root(name)        -> absolute Path for a named root from roots.json
  - pipeline_root()   -> the tree's base (FP_PIPELINE env, else roots.json default_root)
  - known_roots()     -> every registered name
  - the env var is read at CALL time; modules that want import-time freeze semantics
    (the existing behavior of every consumer) assign module-level constants as before.

A missing or malformed roots.json raises loudly. A wrong path silently pointed at the
live library is the hazard; a crash is the safe direction (docs/19).

Selftest (THE SCRATCH-ROOT TRIPWIRE, gates Lane E's commit):
  python fp_paths.py
sets FP_PIPELINE to a fresh temp dir, imports each owned module (import only - never a
main or a watch loop), asserts every registered root and every consumer path constant
resolves UNDER the temp dir, then censuses the owned sources for any remaining
ml\\library literal (count must be 0).
"""

import json
import os
from pathlib import Path

_REGISTRY_FILE = Path(__file__).with_name("roots.json")
_registry: dict | None = None


def _load() -> dict:
    global _registry
    if _registry is None:
        with open(_REGISTRY_FILE, encoding="utf-8") as f:
            _registry = json.load(f)
    return _registry


def pipeline_root() -> Path:
    """The base of the pipeline tree: FP_PIPELINE env if set, else the registry default."""
    reg = _load()
    return Path(os.environ.get(reg["root_env"], reg["default_root"]))


def root(name: str) -> Path:
    """Absolute Path for the named root. Unknown names raise - never guess a path."""
    reg = _load()
    try:
        rel = reg["roots"][name]["path"]
    except KeyError:
        raise KeyError(
            f"unknown pipeline root {name!r} - not in {_REGISTRY_FILE.name} "
            f"(known: {', '.join(sorted(reg['roots']))})"
        ) from None
    base = pipeline_root()
    return base if rel == "." else base.joinpath(*rel.split("/"))


def known_roots() -> list[str]:
    return list(_load()["roots"].keys())


# ---------- THE SCRATCH-ROOT TRIPWIRE (selftest mode) ----------
#
# Owned modules and the path constants each one derives from this resolver. Import only -
# never invoke a main, a watch loop, or a conversion. Nothing here touches the live root:
# FP_PIPELINE is pointed at a throwaway temp dir before any owned module is imported,
# and resolution never creates directories.
_OWNED = {
    "events": ["EVENTS_FILE"],
    "watch_and_convert": ["BASE", "DROP_DIR", "DONE_DIR", "FAILED_DIR",
                          "MODE_FILE", "LOCK_FILE", "HOLD_FILE", "LOG_FILE",
                          "INTAKE_STATE_FILE"],
    "analyst": ["ANALYST_PROGRESS", "ANALYST_WORK", "EVENTS_FILE", "RULES_FILE"],
    "backend_parity": ["PIPE_ROOT", "GPU_LOCK", "DEFAULT_BOOK"],
    "convert_and_ship": ["ANCHOR", "PENDING", "HELD", "AUDIT_MODE_FILE", "PROGRESS_FILE",
                         "ESTIMATE_FILE", "CHUNK_BATCH_FILE", "CHUNK_WORK", "LEDGER_FILE"],
}


def _selftest() -> int:
    import importlib
    import re
    import tempfile

    failures = 0
    with tempfile.TemporaryDirectory(prefix="fp-paths-selftest-") as tmp:
        scratch = Path(tmp).resolve()
        os.environ["FP_PIPELINE"] = str(scratch)
        print(f"scratch root: {scratch}")

        def under(p: Path) -> bool:
            return Path(p).resolve().is_relative_to(scratch)

        # 1. every registered root resolves under the scratch root
        bad = [n for n in known_roots() if not under(root(n))]
        for n in bad:
            print(f"FAIL root {n!r} escapes scratch: {root(n)}")
        failures += len(bad)
        print(f"roots-under-scratch: {len(known_roots()) - len(bad)}/{len(known_roots())} "
              f"{'PASS' if not bad else 'FAIL'}")

        # 2. import each owned module; its resolver-fed constants sit under scratch
        for mod_name, attrs in _OWNED.items():
            try:
                mod = importlib.import_module(mod_name)
            except Exception as exc:  # noqa: BLE001 - a dep gap must be NAMED, not hidden
                print(f"FAIL import {mod_name}: {type(exc).__name__}: {exc}")
                failures += 1
                continue
            bad_attrs = [a for a in attrs if not under(getattr(mod, a))]
            for a in bad_attrs:
                print(f"FAIL {mod_name}.{a} escapes scratch: {getattr(mod, a)}")
            failures += len(bad_attrs)
            print(f"import {mod_name}: {len(attrs) - len(bad_attrs)}/{len(attrs)} "
                  f"constants under scratch {'PASS' if not bad_attrs else 'FAIL'}")

    # 3. zero-literal census of the owned sources (roots.json is the ONE sanctioned home)
    literal = re.compile(r"ml[\\/]+library", re.IGNORECASE)
    here = Path(__file__).parent
    total = 0
    for fname in [f"{m}.py" for m in _OWNED] + ["fp_paths.py"]:
        hits = [i for i, line in enumerate(
            (here / fname).read_text(encoding="utf-8").splitlines(), 1)
            if literal.search(line)]
        # this file's own docstring/regex mention the pattern in prose - count only
        # sources OTHER than the census machinery itself for the gate, but print both.
        if fname == "fp_paths.py":
            print(f"census {fname}: {len(hits)} prose mention(s) (census machinery, not a path)")
            continue
        total += len(hits)
        print(f"census {fname}: {len(hits)} literal(s)" + (f" at lines {hits}" if hits else ""))
    print(f"owned-file literal census: {total} (must be 0) {'PASS' if total == 0 else 'FAIL'}")
    failures += total

    print("SELFTEST " + ("PASS" if failures == 0 else f"FAIL ({failures})"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
