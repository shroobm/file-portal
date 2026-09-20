# -*- coding: utf-8 -*-
"""bundle_name_selftest.py — the tripwire for clamp_name (S209 E8, SYM-137): a bundle name may never end in a space or a
dot, whatever its length — Windows drops both when it creates the directory, and the ship then copies into a path that does
not exist (WinError 3; the Spring Economic Update, 2026-09-20 19:30Z). Run with the marker-env interpreter (convert_and_ship
imports pymupdf at module level); FP_PIPELINE at a temp dir before import (SYM-010). Cases: a short name with a trailing
space; a short name with a trailing dot; an exactly-80-byte name ending in a space (the SEU's shape); a long name clamped
then rstripped; a clean name untouched; all-spaces → "untitled". Prints `==== bundle_name selftest: N/N ====`."""
import os
import sys
import tempfile

os.environ["FP_PIPELINE"] = tempfile.mkdtemp(prefix="bundle-name-selftest-")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert_and_ship as cas  # noqa: E402

ok = n = 0


def case(name, cond, detail=""):
    global ok, n
    n += 1
    ok += 1 if cond else 0
    print("  [%d] %s %s%s" % (n, "ok " if cond else "RED", name, ("  <- " + repr(detail)[:140]) if (detail and not cond) else ""))


case("a short name with a trailing space loses it", cas.clamp_name("Spring Economic Update 2026 - ") == "Spring Economic Update 2026 -", cas.clamp_name("Spring Economic Update 2026 - "))
case("a short name with a trailing dot loses it", cas.clamp_name("Report to Shareholders.") == "Report to Shareholders", cas.clamp_name("Report to Shareholders."))
seu = "Department of Finance Canada (budget.canada.ca) _ Spring Economic Update 2026 - "
assert len(seu.encode("utf-8")) == 80, len(seu.encode("utf-8"))
case("the SEU's shape — exactly 80 bytes ending in a space — loses the space", cas.clamp_name(seu) == seu.rstrip() and not cas.clamp_name(seu).endswith(" "), cas.clamp_name(seu))
longn = "A very long bundle name that goes on and on and on and on and on and on and on and on and on .  "
out = cas.clamp_name(longn)
case("a long name is clamped to 80 bytes and rstripped", len(out.encode("utf-8")) <= 80 and not out.endswith((" ", ".")), out)
case("a clean name is untouched", cas.clamp_name("Scotiabank _ Report to Shareholders, Q3 2026") == "Scotiabank _ Report to Shareholders, Q3 2026")
case("all spaces → 'untitled', never an empty name", cas.clamp_name("   ") == "untitled", cas.clamp_name("   "))
print("==== bundle_name selftest: %d/%d ====" % (ok, n))
sys.exit(0 if ok == n else 1)
