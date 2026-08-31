#!/usr/bin/env python3
"""Hermetic negative controls for A4's source-generated schema registry."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

import schema_registry as sr


ROOT = Path(__file__).resolve().parents[1]
passed = failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    print(("  ok  " if condition else "  FAIL"), name)
    passed += int(condition)
    failed += int(not condition)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scratch_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="fp-a4-schema-"))
    for relative in sorted(set(sr.WRITER_SOURCES + sr.CONSUMER_SOURCES)):
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    registry = root / sr.REGISTRY_REL
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(sr.registry_bytes(root))
    return root


def mutate(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor count for {relative}: {text.count(old)}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def rejects(root: Path) -> bool:
    try:
        sr.check_registry(root)
    except sr.RegistryError:
        return True
    return False


tracked = [ROOT / relative for relative in sorted(set(sr.WRITER_SOURCES + sr.CONSUMER_SOURCES))]
before = {path: digest(path) for path in tracked}

# Positive controls: byte determinism and the real checked-in projection.
check("deterministic generation is byte-identical", sr.registry_bytes(ROOT) == sr.registry_bytes(ROOT))
try:
    sr.check_registry(ROOT)
    current_ok = True
except sr.RegistryError:
    current_ok = False
check("checked-in schemas.json is current", current_ok)
shapes = sr.build_registry(ROOT)["contracts"]["events.jsonl"]["variants"]
check(
    "event variants preserve required intersection and optional union",
    "held" in shapes["gate/resolved"]["optional_keys"]
    and "batch" in shapes["convert/slice"]["optional_keys"]
    and "degeneration" in shapes["audit/scored"]["optional_keys"]
    and "promised_eta_s" in shapes["convert/converted"]["optional_keys"],
)

# 1. A real writer grows a key but schemas.json is stale.
case = scratch_repo()
mutate(case, "windows-converter/convert_and_ship.py", '"peak_vram_mib": peak_mib or None,',
       '"peak_vram_mib": peak_mib or None,\n            "zz_writer_probe": 1,')
check("negative: undeclared writer key trips byte drift", rejects(case))
shutil.rmtree(case)

# 2. A consumer asks convert progress for a key no writer declares.
case = scratch_repo()
mutate(case, "windows-widget/src-tauri/src/line.rs", '"convert_split_side": cp_field("split_side"),',
       '"convert_split_side": cp_field("split_side"),\n        "zz": cp_field("zz_consumer_probe"),')
check("negative: unregistered consumer key fails parity", rejects(case))
shutil.rmtree(case)

# 3. Nested paths are parent-sensitive, not a global key union.
case = scratch_repo()
mutate(case, "windows-converter/coverage_rescore.py", "inventory['conditions']['interpretation']",
       "inventory['conditions']['candidate_status']")
check("negative: valid key under wrong parent fails", rejects(case))
shutil.rmtree(case)

# The historical specimen: this path exists only below p1_page_coverage, never at report root.
contract_set = sr.build_registry(ROOT)["contracts"]
contract_set["coverage_rescore.stdout"]["consumer_paths"].append("sym050_doubled_offset")
try:
    sr._assert_parity(contract_set)
    historical_wrong_path_rejected = False
except sr.RegistryError:
    historical_wrong_path_rejected = True
check("negative: historical root-level sym050 path fails", historical_wrong_path_rejected)

# 4. Unknown dynamic fields fail closed instead of disappearing from the registry.
case = scratch_repo()
mutate(case, "windows-converter/watch_and_convert.py", 'emit("intake", "detected", source=pdf.name, analyst_mode=mode)',
       'emit("intake", "detected", source=pdf.name, analyst_mode=mode, **mystery_fields)')
check("negative: unresolved event spread fails closed", rejects(case))
shutil.rmtree(case)

# 5. Per-event schemas catch a key that exists in the stream but not this variant.
case = scratch_repo()
mutate(case, "windows-widget/src/event-vocab.js",
       '"convert/probe": `${icon("⚙")}probing ${s(e.source)} — ${e.pages}pp ${e.lane || ""}`.trim(),',
       '"convert/probe": `${icon("⚙")}probing ${s(e.source)} — ${e.pages}pp ${e.wall_s}`.trim(),')
check("negative: cross-event guessed key fails variant parity", rejects(case))
shutil.rmtree(case)

# 6. Even whitespace drift in the checked-in projection is visible.
case = scratch_repo()
registry = case / sr.REGISTRY_REL
registry.write_bytes(registry.read_bytes() + b"\n")
check("negative: stale registry bytes fail", rejects(case))
shutil.rmtree(case)

# 7. A selector that vanished cannot leave a forever-green contract.
case = scratch_repo()
(case / "windows-widget/src-tauri/src/events.rs").unlink()
check("negative: missing consumer source fails UNREAD", rejects(case))
shutil.rmtree(case)

# 8. Event aliases are contract variables, not hardcoded to the spelling `ev`.
case = scratch_repo()
mutate(case, "windows-widget/src-tauri/src/room.rs", '"name": e["bundle"].as_str()',
       '"name": e["zz_unknown"].as_str()')
check("negative: aliased Rust event consumer key fails parity", rejects(case))
shutil.rmtree(case)

# 9. A branch-local object assembled before the return still belongs to the writer contract.
case = scratch_repo()
mutate(case, "windows-converter/figure_coverage.py", 'sym050 = {"detected": False}',
       'sym050 = {"detected": False, "zz_nested_writer": True}')
check("negative: nested local writer key trips byte drift", rejects(case))
shutil.rmtree(case)

# 10. Rust match-arm readers remain variant-scoped even when the guessed key exists elsewhere.
case = scratch_repo()
mutate(case, "windows-widget/src-tauri/src/events.rs", 'ev["chunks_rejected"]', 'ev["wall_s"]')
check("negative: Rust match-arm cross-event key fails variant parity", rejects(case))
shutil.rmtree(case)

# 11. A selected event assigned through find/ok_or keeps its exact variant contract.
case = scratch_repo()
mutate(case, "windows-widget/src-tauri/src/line.rs", 'shipped["bundle"]', 'shipped["zz_unknown"]')
check("negative: find/ok_or event alias key fails parity", rejects(case))
shutil.rmtree(case)

# 12. Literal dict.update growth is writer output; an unresolved update fails closed.
case = scratch_repo()
mutate(case, "windows-converter/figure_coverage.py", 'sym050 = {"detected": False}',
       'sym050 = {"detected": False}\n        sym050.update({"zz_update_writer": 1})')
check("negative: nested literal update key trips byte drift", rejects(case))
shutil.rmtree(case)

case = scratch_repo()
mutate(case, "windows-converter/figure_coverage.py", 'sym050 = {"detected": False}',
       'sym050 = {"detected": False}\n        sym050.update(mystery_fields)')
check("negative: unresolved nested update fails closed", rejects(case))
shutil.rmtree(case)

after = {path: digest(path) for path in tracked}
check("source-only test leaves production writers and consumers byte-identical", before == after)

print("-" * 58)
print(f"{'ALL TRIPWIRES FIRED' if not failed else 'RED'} — {passed}/{passed + failed}")
raise SystemExit(1 if failed else 0)
