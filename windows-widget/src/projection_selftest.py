# -*- coding: utf-8 -*-
"""projection_selftest.py — tripwires over the widget's JS SOURCE for the projection-drift class (SYM-043, docs/40 §3.1:
a working mechanism and its human-facing sentence disagreeing). Born S157 E53 (2026-09-15) with B11's repair and the
B32 U04 fix; stdlib only; reads main.js / room.js / index.html beside this file; runs anywhere (CI's python job can carry
it warn-only). Every case is a SOURCE proxy for a rendered property — said so in its name — and each has a negative
control that plants the drift back into a copy and watches the check go red (docs/32 §5 rule 2).

  1. B11: the assay card's swap note never says "manual" / "supersede pending" while the ⟳ re-convert handler exists
     (the handler IS the supersede author — assay.rs reconvert; the exporter's guard replaces the vaulted note).
  2. U04: the Wall's event line takes the FIRST element of the shift tail (events.rs hands it newest-first), never
     `.slice(-1)[0]`.
  3. J16: the Dock's drop readout and the Room's queue rows carry an age (wait_s, else mtime_ns) or say UNREAD —
     never silently nothing.

Exit 0 only when every case passes and every control fired. Bare run: the suite (it is the tripwire; no --go)."""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = io.open(os.path.join(HERE, "main.js"), encoding="utf-8").read()
ROOM = io.open(os.path.join(HERE, "room.js"), encoding="utf-8").read()

DRIFT = re.compile(r"swap:\s*<b>manual</b>|supersede (flow )?pending", re.I)
HANDLER = re.compile(r'class="ac-remedy"')
WALL_OLDEST = re.compile(r"\(vm\.shift\?\.tail \|\| \[\]\)\.slice\(-1\)\[0\]")
WALL_NEWEST = re.compile(r"\(vm\.shift\?\.tail \|\| \[\]\)\[0\]")


SWAPNOTE = re.compile(r'<span class="ac-swapnote">(.*?)</span>', re.S)


def b11_clean(src: str) -> bool:
    """The RENDERED swap note (the ac-swapnote span's text, not a comment quoting the old words) never carries the
    drift wording wherever the remedy handler exists (a source with neither is not this card)."""
    notes = SWAPNOTE.findall(src)
    return not (HANDLER.search(src) and any(DRIFT.search(n) for n in notes))


def u04_newest(src: str) -> bool:
    return WALL_NEWEST.search(src) is not None and WALL_OLDEST.search(src) is None


def j16_dock_has_age(src: str) -> bool:
    return "oldest ${pfAge(oldest)}" in src and "wait UNREAD" in src


def j16_room_has_age(src: str) -> bool:
    return "sat ${ageText(" in src and "wait UNREAD" in src and "waiting ${etaText(f.wait_s)}" in src


results = []


def case(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("  %s  %s%s" % ("ok " if ok else "RED", name, (" — " + detail) if detail and not ok else ""))


case("B11 main.js: the swap note is not 'manual / supersede pending' while the ⟳ handler exists (source proxy)", b11_clean(MAIN))
case("B11 room.js: the same", b11_clean(ROOM))
case("B11 the note now names the mechanism ('supersedes the vaulted note') in both files",
     "supersedes the vaulted note" in MAIN and "supersedes the vaulted note" in ROOM)
planted = ROOM.replace("swap: <b>automatic</b>", "swap: <b>manual</b>", 1)
case("B11 NEGATIVE CONTROL: the old wording planted back into a copy of room.js reds the check", not b11_clean(planted))
case("B11 NEGATIVE CONTROL: 'supersede pending' planted reds it too", not b11_clean(ROOM.replace("(exporter guard)", "— supersede pending", 1)))
case("B11 control: a source with NO remedy handler is not judged (the card is absent, not drifted)", b11_clean('<span class="ac-swapnote">swap: <b>manual</b> — supersede pending</span>'))

case("U04 room.js: the Wall's event line takes tail[0] (newest-first) and never .slice(-1)[0] (source proxy)", u04_newest(ROOM))
case("U04 NEGATIVE CONTROL: the oldest-of-tail form planted back reds the check",
     not u04_newest(ROOM.replace("(vm.shift?.tail || [])[0]", "(vm.shift?.tail || []).slice(-1)[0]", 1)))

case("J16 main.js: the Dock's drop readout carries the oldest wait or says UNREAD (source proxy)", j16_dock_has_age(MAIN))
case("J16 room.js: a queue row says waiting / sat / UNREAD, never nothing (source proxy)", j16_room_has_age(ROOM))
case("J16 NEGATIVE CONTROL: the Dock readout without its wait note reds the check",
     not j16_dock_has_age(MAIN.replace("oldest ${pfAge(oldest)}", "", 1)))
case("J16 main.js defines pfAge with an hours rung (a three-hour wait is not '180m')",
     re.search(r"function pfAge\(s\) \{\s*return s < 90 \? `\$\{s\}s` : s < 5400 \? `\$\{Math\.round\(s / 60\)\}m` : `\$\{\(s / 3600\)\.toFixed\(1\)\}h`;", MAIN) is not None)

red = [r for r in results if not r[1]]
controls = [r for r in results if "CONTROL" in r[0]]
print("projection selftest: %d/%d · controls %d/%d fired" % (len(results) - len(red), len(results), sum(1 for c in controls if c[1]), len(controls)))
sys.exit(1 if red else 0)
