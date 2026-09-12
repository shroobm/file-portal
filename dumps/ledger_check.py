# -*- coding: utf-8 -*-
"""ledger_check.py [<ledger dir>] — verify a dump ledger (S141, provenance/extend-dump-ledger-not-invent-manifest):
every LEDGER.md row (seven columns) has a well-formed id/utc/sha; every LEDGER.jsonl twin row recomputes its own
row_sha256 (canonical JSON, sorted keys, no whitespace, over the row without that field) and agrees with its md row on
id/bytes/sha256; for a twin row whose `path` still exists, the bytes and sha256 reproduce (a copy-mode dump whose bytes
were deleted reads `bytes gone — the ledger survives, by design`, not red); an md row without a twin is a pre-S141 row
(said, not red). Read-only. Exit 0 every check agrees · 1 any disagreement · 2 usage / no LEDGER.md."""
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\| (D\d{4}) \| (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) \| ([^|]+) \| ([^|]+) \| (.*) \| (\d+) \| `([0-9a-f]{64})` \|\s*$")


def digest(path):
    h = hashlib.sha256()
    n = 0
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    return n, h.hexdigest()


def main(argv):
    d = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent
    md = d / "LEDGER.md"
    if not md.is_file():
        print("CONFIG: no LEDGER.md at", d)
        return 2
    rows = {}
    bad = 0
    for ln in io.open(md, encoding="utf-8", errors="replace"):
        if not ln.startswith("| D"):
            continue
        m = ROW.match(ln.rstrip("\r\n"))
        if not m:
            print("  md row malformed: %s" % ln.strip()[:80])
            bad += 1
            continue
        rows[m.group(1)] = (int(m.group(6)), m.group(7), m.group(5).strip())
    twins = {}
    jl = d / "LEDGER.jsonl"
    if jl.is_file():
        for ln in io.open(jl, encoding="utf-8", errors="replace"):
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                print("  twin row unparsable: %s" % ln.strip()[:80])
                bad += 1
                continue
            twins[r.get("id")] = r
    for rid, (nbytes, sha, subject) in rows.items():
        t = twins.get(rid)
        if not t:
            print("  %s: md row (no twin — pre-S141) · %d bytes · %s…" % (rid, nbytes, sha[:12]))
            continue
        parts = []
        want = t.get("row_sha256")
        canon = json.dumps({k: v for k, v in t.items() if k != "row_sha256"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        got = hashlib.sha256(canon).hexdigest()
        if got == want:
            parts.append("row_sha256 ✓")
        else:
            parts.append("row_sha256 ✗ (the twin row changed after it was written)")
            bad += 1
        if t.get("bytes") == nbytes and t.get("sha256") == sha:
            parts.append("md == twin ✓")
        else:
            parts.append("md != twin ✗ (bytes %s/%s, sha %s…/%s…)" % (nbytes, t.get("bytes"), sha[:8], str(t.get("sha256"))[:8]))
            bad += 1
        p = t.get("path")
        if p and Path(p).is_file():
            n, s = digest(p)
            if (n, s) == (nbytes, sha):
                parts.append("bytes reproduce ✓")
            else:
                parts.append("bytes at %s do NOT reproduce ✗ (%d bytes now, sha %s…)" % (Path(p).name, n, s[:8]))
                bad += 1
        elif p:
            parts.append("bytes gone (%s) — the ledger survives, by design" % Path(p).name)
        pr = t.get("producer")
        if pr:
            parts.append("producer %s blob %s" % (Path(pr.get("path", "?")).name, str(pr.get("blob", ""))[:8] or "UNREAD"))
        print("  %s: %s · %s" % (rid, " · ".join(parts), subject[:60]))
    for rid in twins:
        if rid not in rows:
            print("  %s: twin row WITHOUT an md row ✗" % rid)
            bad += 1
    print("ledger %s: md rows %d · twin rows %d · disagreements %d" % (d, len(rows), len(twins), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
