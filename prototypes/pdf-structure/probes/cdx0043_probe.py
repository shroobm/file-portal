"""Fable's independent re-run of MSG-CDX-0043's two controls. No GPU, no pipeline."""
import sys, json, subprocess
sys.path.insert(0, r"C:/Users/Bndit/Projects/file-portal/prototypes/repair-bench")
import bench

HEAD = subprocess.run(["git","-C",r"C:/Users/Bndit/Projects/file-portal","rev-parse","HEAD"],
                      capture_output=True, text=True).stdout.strip()
print(f"HEAD = {HEAD}")
print(f"bench.LEGACY_RUN_CAP = {bench.LEGACY_RUN_CAP}")
print(f"evidence_count signature = {bench.evidence_count.__code__.co_varnames[:5]}")
print()

fails = []
def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}\n         got={got!r}")
    if not ok:
        print(f"         want={want!r}")
        fails.append(label)

# ---- POSITIVE CONTROL: shown=60, runs_total=531, runs_capped_at=100 ----
print("POSITIVE: shown=60, runs_total=531, runs_capped_at=100")
r = bench.evidence_count(60, 531, 100, legacy_cap=bench.LEGACY_RUN_CAP)
print(f"  full record: {json.dumps(r, ensure_ascii=False)}")
check("completeness == partial", r["completeness"], "partial")
check("label == '60 of 531'", r["label"], "60 of 531")
check("unseen == 471", r["unseen"], 471)
check("total == 531", r["total"], 531)
check("complete is False", r["complete"], False)
print()

# ---- NEGATIVE CONTROL: shown=101 against producer cap 100 ----
print("NEGATIVE: shown=101, runs_capped_at=100 (total absent AND total present)")
n1 = bench.evidence_count(101, raw_cap=100, legacy_cap=bench.LEGACY_RUN_CAP)
check("total ABSENT -> malformed", n1["completeness"], "malformed")
check("total ABSENT -> reason names the cap", n1["reason"], "shown count exceeds its producer cap of 100")
n2 = bench.evidence_count(101, 531, 100, legacy_cap=bench.LEGACY_RUN_CAP)
check("total=531 present -> still malformed", n2["completeness"], "malformed")
check("total=531 present -> unseen is None (no invented number)", n2["unseen"], None)
print()

# ---- THE ISOLATING CONTROL: crossing 40 must NOT change the verdict ----
print("ISOLATION: the old 40-row display limit must no longer touch the verdict")
for shown in (39, 40, 41, 60):
    x = bench.evidence_count(shown, 531, 100, legacy_cap=bench.LEGACY_RUN_CAP)
    print(f"  shown={shown:3d} -> {x['completeness']:9s} | {x['label']:12s} | unseen={x['unseen']}")
    check(f"shown={shown} is partial (not malformed)", x["completeness"], "partial")
print()

# ---- NEGATIVE CONTROL ON THIS HARNESS ITSELF (rule 4: watch it fail) ----
print("HARNESS NEGATIVE CONTROL (must report RED, proving check() is not a tautology)")
before = len(fails)
check("[deliberate] positive case mislabelled as complete", r["completeness"], "complete")
harness_ok = len(fails) == before + 1
print(f"  harness detects a genuine mismatch: {'YES' if harness_ok else 'NO -- checks are vacuous'}")
if harness_ok:
    fails.pop()
print()

print("REAL FAILURES:", fails if fails else "none")
print("VERDICT:", "PASS" if not fails and harness_ok else "FINDINGS")
