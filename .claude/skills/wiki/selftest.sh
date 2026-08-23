#!/usr/bin/env bash
# selftest.sh — tripwires for wiki.sh. Every gate is proven BOTH ways:
# a fixture that must PASS and, for each law, a fixture that must FAIL.
# (The 2026-08-22 mapping pass shipped a false byte-level claim from a probe
# nobody had controlled; this file is that lesson, vendored.)
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIKI_SH="$SCRIPT_DIR/wiki.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
fired() { echo "TRIPWIRE T$1 FIRED"; }
t() { # t <name> <expected-exit:0|1> <fixture-dir>
  name="$1"; want="$2"; root="$3"
  WIKI_ROOT="$root" bash "$WIKI_SH" check >/dev/null 2>&1
  got=$?
  if [ "$want" = "0" ] && [ "$got" -eq 0 ]; then echo "  PASS  $name"; PASS=$((PASS+1))
  elif [ "$want" = "1" ] && [ "$got" -ne 0 ]; then echo "  PASS  $name (failed as it must)"; PASS=$((PASS+1))
  else echo "  FAIL  $name (want exit $want, got $got)"; FAIL=$((FAIL+1)); fi
}

good_page() { # good_page <dir> <slug> <title>
  cat > "$1/$2.md" <<EOF
---
title: $3
section: Test
last-verified: 2026-08-23
verified-against: 0000000
sources: []
---

> **Summary.** A valid page.

## Open items
EOF
}

# ---- T1: a valid mini-wiki must pass (positive control for EVERY gate at once)
F1="$TMP/f1"; mkdir -p "$F1"
good_page "$F1" alpha "Alpha"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F1/INDEX.md"
t "valid wiki passes" 0 "$F1"
fired 1

# ---- T2: page missing from INDEX must fail
F2="$TMP/f2"; mkdir -p "$F2"
good_page "$F2" alpha "Alpha"; good_page "$F2" beta "Beta"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F2/INDEX.md"
t "unmapped page fails" 1 "$F2"
fired 2

# ---- T3: dead link in INDEX must fail
F3="$TMP/f3"; mkdir -p "$F3"
good_page "$F3" alpha "Alpha"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n- [Ghost](ghost.md) — missing\n' > "$F3/INDEX.md"
t "dead INDEX link fails" 1 "$F3"
fired 3

# ---- T4: missing frontmatter field must fail
F4="$TMP/f4"; mkdir -p "$F4"
good_page "$F4" alpha "Alpha"
sed -i '/^verified-against:/d' "$F4/alpha.md"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F4/INDEX.md"
t "missing frontmatter fails" 1 "$F4"
fired 4

# ---- T5: page over 200 lines must fail
F5="$TMP/f5"; mkdir -p "$F5"
good_page "$F5" alpha "Alpha"
for i in $(seq 1 200); do echo "filler $i" >> "$F5/alpha.md"; done
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F5/INDEX.md"
t "oversize page fails" 1 "$F5"
fired 5

# ---- T6: INDEX over 120 lines must fail
F6="$TMP/f6"; mkdir -p "$F6"
good_page "$F6" alpha "Alpha"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F6/INDEX.md"
for i in $(seq 1 120); do echo "- filler line $i" >> "$F6/INDEX.md"; done
t "oversize INDEX fails" 1 "$F6"
fired 6

# ---- T7: dead link inside a PAGE must fail
F7="$TMP/f7"; mkdir -p "$F7"
good_page "$F7" alpha "Alpha"
echo "See [nothing](nowhere.md)." >> "$F7/alpha.md"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F7/INDEX.md"
t "dead page link fails" 1 "$F7"
fired 7

# ---- T8: CRLF page measures identically (SYM-029 class) — must PASS
F8="$TMP/f8"; mkdir -p "$F8"
good_page "$F8" alpha "Alpha"
sed -i 's/$/\r/' "$F8/alpha.md"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F8/INDEX.md"
t "CRLF page still passes (line-ending-blind probes)" 0 "$F8"
fired 8

# ---- T9: stale reporting names the lagging page
F9="$TMP/f9"; mkdir -p "$F9"
good_page "$F9" alpha "Alpha"
printf -- '# Index\n\n- [Alpha](alpha.md) — a page\n' > "$F9/INDEX.md"
if WIKI_ROOT="$F9" bash "$WIKI_SH" stale | grep -q "alpha.md"; then
  echo "  PASS  stale names the lagging page"; PASS=$((PASS+1))
else
  echo "  FAIL  stale did not name the lagging page"; FAIL=$((FAIL+1))
fi
fired 9

# ---- T10: link to an existing DIRECTORY must pass (dirs are legitimate targets)
F10="$TMP/f10"; mkdir -p "$F10/subdir"
good_page "$F10" alpha "Alpha"
echo "See [the folder](subdir)." >> "$F10/alpha.md"
printf -- '# Index

- [Alpha](alpha.md) — a page
' > "$F10/INDEX.md"
t "directory link passes" 0 "$F10"
fired 10

# ---- T11: QUOTED verified-against sha is stripped, not mangled (stale must not crash)
F11="$TMP/f11"; mkdir -p "$F11"
good_page "$F11" alpha "Alpha"
sed -i 's/^verified-against: 0000000/verified-against: "0000000"/' "$F11/alpha.md"
printf -- '# Index

- [Alpha](alpha.md) — a page
' > "$F11/INDEX.md"
if WIKI_ROOT="$F11" bash "$WIKI_SH" stale | grep -q 'verified-against 0000000'; then
  echo "  PASS  quoted sha stripped cleanly"; PASS=$((PASS+1))
else
  echo "  FAIL  quoted sha not stripped"; FAIL=$((FAIL+1))
fi
fired 11

echo
TOTAL=$((PASS+FAIL))
if [ "$FAIL" -eq 0 ]; then echo "ALL TRIPWIRES FIRED — $PASS/$TOTAL, exit 0"; exit 0
else echo "TRIPWIRES BROKEN — $FAIL of $TOTAL failed"; exit 1; fi
