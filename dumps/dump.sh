#!/usr/bin/env bash
# dumps/dump.sh — the ONLY writer of dumps/LEDGER.md (and, since S141, of a ledger's LEDGER.jsonl twin).
#
# Why a script and not a convention: a hand-typed id or digest is a future SYM-039. The id, the
# UTC stamp and the sha256 are all derivable, so none of them is typed. docs/21 §3: nothing
# derivable is written by hand.
#
#   bash dumps/dump.sh <category> "<subject>" <file>              copy the bytes into dumps/<category>/, row + twin
#   <producer> | bash dumps/dump.sh evidence "<subject>" -          the same from stdin
#   bash dumps/dump.sh --ref <category> "<subject>" <file> [--producer <script>] [--source <file>]... [--coverage "<text>"] [--ledger <dir>]
#         S141 (provenance/extend-dump-ledger-not-invent-manifest): record a file IN PLACE — no copy — the row points
#         at it; the JSONL twin row carries what the md row cannot: the path, the producer script and its git blob,
#         each source's bytes + sha256, the coverage sentence, and its own canonical-JSON sha256 (RFC 8785 shape:
#         sorted keys, no whitespace, UTF-8). `--ledger <dir>` writes to another ledger pair (the private receipts'
#         `agent-scripts/journal/LEDGER.md`); the dir must already hold a LEDGER.md (never created silently).
#
# Categories: qa | coordination | evidence | transcripts
#
# Writes the bytes (copy mode) into dumps/<category>/, appends ONE row to LEDGER.md and ONE line to LEDGER.jsonl,
# and prints a pointer+digest line shaped for pasting into relay.md. The md row's SEVEN columns never change shape
# (a reader of D0001–D0005 reads D0099 the same way); the twin is where the columns grow. Trust boundary: this disk
# and the commit of the ledger — a sha proves the bytes did not drift after hashing, not that they were true.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="/c/Users/Bndit/AppData/Roaming/uv/python/cpython-3.12.13-windows-x86_64-none/python.exe"

die() { printf 'dump: %s\n' "$1" >&2; exit 1; }

# --- options (S141) ----------------------------------------------------------------------------
ref=0; producer=""; coverage=""; ledger_dir="$here"; sources=()
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) ref=1; shift ;;
    --producer) [ $# -ge 2 ] || die "--producer needs a path"; producer="$2"; shift 2 ;;
    --source) [ $# -ge 2 ] || die "--source needs a path"; sources+=("$2"); shift 2 ;;
    --coverage) [ $# -ge 2 ] || die "--coverage needs a text"; coverage="$2"; shift 2 ;;
    --ledger) [ $# -ge 2 ] || die "--ledger needs a dir"; ledger_dir="$2"; shift 2 ;;
    --*) die "unknown option $1" ;;
    *) args+=("$1"); shift ;;
  esac
done
set -- "${args[@]+"${args[@]}"}"
[ $# -ge 3 ] || die "usage: dump.sh [--ref] [--producer p] [--source f]... [--coverage t] [--ledger dir] <qa|coordination|evidence|transcripts> \"<subject>\" <file|->"
ledger="$ledger_dir/LEDGER.md"
twin="$ledger_dir/LEDGER.jsonl"

cat_in="$1"; subject="$2"; src="$3"
case "$cat_in" in
  qa|coordination|evidence|transcripts) : ;;
  *) die "unknown category '$cat_in' (qa|coordination|evidence|transcripts)" ;;
esac
[ "$ref" -eq 1 ] || [ -d "$here/$cat_in" ] || die "category dir missing: dumps/$cat_in"
[ "$ref" -eq 0 ] || [ "$src" != "-" ] || die "--ref needs a file, not stdin"

# --- author lane: declared, never guessed -------------------------------------------------
lane="${DUMP_LANE:-}"
[ -n "$lane" ] || die "set DUMP_LANE (e.g. DUMP_LANE=Fable) — a dump with no author is unattributable"

# --- next id: derived from the ledger, at write time (SYM-045: re-read the counter NOW) ----
[ -f "$ledger" ] || die "LEDGER.md missing at $ledger_dir — refusing to create it silently"
last=$(grep -oE '^\| D[0-9]{4} ' "$ledger" 2>/dev/null | grep -oE '[0-9]{4}' | sort -n | tail -1)
[ -n "${last:-}" ] || last=0
id=$(printf 'D%04d' $((10#$last + 1)))

ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
day=$(date -u '+%Y%m%d')

if [ "$ref" -eq 1 ]; then
  # --- IN PLACE: the row points at the file where it lives; nothing is copied ------------------
  [ -f "$src" ] || die "no such file: $src"
  [ -s "$src" ] || die "refusing to record an EMPTY file"
  dest="$src"
  bytes=$(wc -c < "$src" | tr -d ' ')
  sha=$(sha256sum "$src" | cut -d' ' -f1 | tr -d '\\')   # coreutils prefixes a backslash when the path carries one
  shown="$src"
else
  # --- slug the subject for a filename ------------------------------------------------------
  slug=$(printf '%s' "$subject" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//; s/-$//' | cut -c1-60)
  [ -n "$slug" ] || slug="untitled"
  ext="md"
  if [ "$src" != "-" ]; then
    [ -f "$src" ] || die "no such file: $src"
    case "$src" in *.*) ext="${src##*.}" ;; esac
  fi
  name="${id}-${day}-${slug}.${ext}"
  dest="$here/$cat_in/$name"
  part="$here/$cat_in/.part-${name}"
  # --- ATOMIC: write .part- then rename. A reader never sees a torn file. -------------------
  if [ "$src" = "-" ]; then
    cat > "$part" || die "could not write $part"
  else
    cp "$src" "$part" || die "could not copy $src"
  fi
  [ -s "$part" ] || { rm -f "$part"; die "refusing to record an EMPTY dump — nothing was captured"; }
  bytes=$(wc -c < "$part" | tr -d ' ')
  sha=$(sha256sum "$part" | cut -d' ' -f1 | tr -d '\\')
  mv -f "$part" "$dest" || die "rename failed"
  shown="dumps/$cat_in/$name"
fi

# --- ledger row: APPENDED, never rewritten; SEVEN columns, always -----------------------------
printf '| %s | %s | %s | %s | %s | %s | `%s` |\r\n' \
  "$id" "$ts" "$lane" "$cat_in" "$subject" "$bytes" "$sha" >> "$ledger"

# --- the JSONL twin (S141): the same row plus what the md cannot hold; canonical, self-hashed ---
"$PY" - "$twin" "$id" "$ts" "$lane" "$cat_in" "$subject" "$bytes" "$sha" "$dest" "$producer" "$coverage" "${sources[@]+"${sources[@]}"}" <<'PYEOF' || die "twin row not written"
import hashlib, io, json, os, subprocess, sys
twin, id_, ts, lane, cat, subject, nbytes, sha, path, producer, coverage, *sources = sys.argv[1:]
def blob(p):
    try:
        return subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(p)), "hash-object", p], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""
def digest(p):
    h = hashlib.sha256(); n = 0
    with io.open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk); n += len(chunk)
    return n, h.hexdigest()
row = {"id": id_, "utc": ts, "lane": lane, "category": cat, "subject": subject, "bytes": int(nbytes), "sha256": sha,
       "path": path.replace("\\", "/"), "stamp": "fp.receipt/0.1", "canonicalization": "RFC 8785 (sorted keys, no whitespace, UTF-8; row_sha256 over the row without itself)"}
if producer:
    row["producer"] = {"path": producer.replace("\\", "/"), "blob": blob(producer) or "UNREAD"}
if sources:
    row["sources"] = []
    for s in sources:
        if os.path.isfile(s):
            n, d = digest(s); row["sources"].append({"path": s.replace("\\", "/"), "bytes": n, "sha256": d})
        else:
            row["sources"].append({"path": s.replace("\\", "/"), "UNREAD": "not a file at write time"})
if coverage:
    row["coverage"] = coverage
canon = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
row["row_sha256"] = hashlib.sha256(canon).hexdigest()
with io.open(twin, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
PYEOF

# --- the pointer, shaped for the bus ------------------------------------------------------
printf '\n'
printf 'DUMPED  %s  %s bytes%s\n' "$id" "$bytes" "$([ "$ref" -eq 1 ] && printf ' (in place)')"
printf '  path    %s\n' "$shown"
printf '  sha256  %s\n' "$sha"
printf '  ledger  row appended to %s (+ the JSONL twin)\n' "$ledger"
printf '\n'
printf 'For relay.md — pointer + digest, bytes never cross the bus:\n'
printf '  **DUMP %s** · `%s` · `sha256:%s` · %s bytes · ⟨%s⟩ %s\n' \
  "$id" "$shown" "$sha" "$bytes" "$lane" "$ts"
