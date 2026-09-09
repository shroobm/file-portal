#!/usr/bin/env python3
"""coordination/relay_numerations.py — THE RELAY NUMERATIONS (the NR-set), S120, Rab's order 2026-09-09:
"find real another set of numerations that is strictly between your communication and processes utilizing
coordination relay". docs/51 numbers the pipeline; this numbers the BUS — measured from `coordination/relay.md`
(the append-only log) and the two sidecars (`ack-fable.json`, `ack-codex.json`), never from prose.

Every row names its numerator, denominator and conditions (docs/34). A row that cannot be computed from
the files prints UNREAD with the reason, never 0 (SYM-031). Stdlib only; read-only; runtime-neutral
(either lane's interpreter). Exit 0 always — this is a meter, not a gate; gates read it.

    python coordination/relay_numerations.py            # the table
    python coordination/relay_numerations.py --json     # machine-readable
"""
from __future__ import annotations

import io
import json
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RELAY = HERE / "relay.md"
SIDECARS = {"Fable": HERE / "ack-fable.json", "Codex": HERE / "ack-codex.json"}
HEADER = re.compile(r"^## (\d{4}-\d\d-\d\dT\d\d:\d\dZ) · ⟨from: (\w+)⟩ → ⟨to: (\w+)⟩ · ⟨msg: (MSG-[A-Z]{3}-\d{4})⟩\s*$", re.M)
SLOTS = ("RECAP", "FOR RAB", "SUGGESTED PROMPT")
STALE_MIN = 45  # the board's own staleness rule (relay-gate SKILL.md) — a lever the gate already owns


def utc(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def load_sidecar(lane: str):
    p = SIDECARS[lane]
    if not p.exists():
        return None, f"{p.name} absent"
    try:
        return json.loads(p.read_text(encoding="utf-8")), "ok"
    except (OSError, ValueError) as e:
        return None, f"{p.name} unreadable: {e}"


def entries():
    """Every header in relay.md with its body; entries whose header is not in the canonical form are
    counted separately (they exist: the pre-gate era) and are not silently dropped."""
    text = io.open(RELAY, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    heads = list(HEADER.finditer(text))
    out = []
    for k, m in enumerate(heads):
        body = text[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        out.append({"utc": m.group(1), "from": m.group(2), "to": m.group(3), "id": m.group(4),
                    "words": len(body.split()),
                    "slots": tuple(s for s in SLOTS if f"**{s}" in body)})
    # The card (open.sh [2b]) counts `^## 20` — dated headers. Legacy = dated but not canonical
    # (the 2026-08-24 `⟨to: Fable, and the record⟩` six, and the pre-gate headers without ⟨msg:⟩).
    dated = len(re.findall(r"^## 20", text, re.M))
    return out, dated - len(heads)


def eol_census(path: Path):
    b = path.read_bytes()
    crlf = b.count(b"\r\n")
    return crlf, b.count(b"\n") - crlf


def pct(n, d):
    return f"{n}/{d} = {100.0 * n / d:.1f} %" if d else f"{n}/0 UNREAD (empty denominator)"


def minutes(a, b):
    return (b - a).total_seconds() / 60.0


def main(argv):
    as_json = "--json" in argv
    now = datetime.now(timezone.utc)
    rows = []

    def row(nid, name, value, numden, tag):
        rows.append({"id": nid, "name": name, "value": value, "numerator_denominator_conditions": numden, "tag": tag})

    ents, noncanon = entries()
    by_lane = {ln: [e for e in ents if e["from"] == ln] for ln in SIDECARS}
    row("NR-01", "relay entries", f"{len(ents) + noncanon} dated headers (the card's count) = {len(ents)} canonical + {noncanon} legacy",
        "dated `## 20…` headers in relay.md, as open.sh [2b] counts them; canonical = `## <UTC> · ⟨from⟩ → ⟨to⟩ · ⟨msg⟩`; per lane (canonical) " + ", ".join(f"{ln} {len(v)}" for ln, v in by_lane.items()),
        "Observed")
    crlf, lf = eol_census(RELAY)
    row("NR-15", "line-ending purity — relay.md", f"CRLF {crlf} · bare-LF {lf} · {100.0 * lf / (crlf + lf):.1f} % bare-LF" if crlf + lf else "UNREAD (empty)",
        "bare-LF lines / all lines; the repo's markdown is CRLF (SYM-029) and core.autocrlf rewrites at `git add`, so every bare-LF line is a future +N/−N diff (S116 F8) — gate.py appends body bytes verbatim",
        "Observed")

    sc = {ln: load_sidecar(ln) for ln in SIDECARS}
    for ln, (d, st) in sc.items():
        if d is None:
            row("NR-00", f"sidecar {ln}", f"UNREAD — {st}", "the file must parse before any NR row below can be trusted", "UNREAD")
    both = all(d is not None for d, _ in sc.values())

    # NR-02 gated share: headers with a matching `sent` record
    if both:
        for ln in SIDECARS:
            sent_ids = {s["id"] for s in sc[ln][0].get("sent", [])}
            heads = [e["id"] for e in by_lane[ln]]
            gated = [i for i in heads if i in sent_ids]
            ungated = [i for i in heads if i not in sent_ids]
            row("NR-02", f"gated appends — {ln}", pct(len(gated), len(heads)) + (f"; ungated: {ungated}" if ungated else ""),
                "headers from this lane whose id has a `sent` record in its own sidecar / all its canonical headers (a header without one was appended outside `gate.py post`)",
                "Observed")
            noack = [s["id"] for s in sc[ln][0].get("sent", []) if not s.get("requires_ack")]
            row("NR-03", f"no-ack notices — {ln}", pct(len(noack), len(sc[ln][0].get("sent", []))),
                "sent records with requires_ack false / all sent records (notices never appear in the peer's `inbox`; only a header diff sees them)",
                "Observed")

    # NR-04/05 ack latency and debt, per direction
    if both:
        for ln in SIDECARS:
            peer = "Codex" if ln == "Fable" else "Fable"
            sent = [s for s in sc[ln][0].get("sent", []) if s.get("requires_ack") and s.get("to") == peer]
            conf = {c["id"]: c for c in sc[peer][0].get("confirmed", [])}
            lat = []
            debt = []
            for s in sent:
                t0 = utc(s.get("utc"))
                c = conf.get(s["id"])
                if c and t0 and utc(c.get("confirmed_utc")):
                    lat.append((s["id"], minutes(t0, utc(c["confirmed_utc"]))))
                elif t0:
                    debt.append((s["id"], minutes(t0, now)))
            if lat:
                vals = sorted(m for _, m in lat)
                med = statistics.median(vals)
                p90 = vals[min(len(vals) - 1, int(round(0.9 * (len(vals) - 1))))]
                worst = max(lat, key=lambda x: x[1])
                row("NR-04", f"ack latency {ln}→{peer}", f"median {med:.0f} min · p90 {p90:.0f} min · max {worst[1]:.0f} min ({worst[0]}) · n {len(vals)}",
                    "for each ack-required message this lane sent to the peer AND the peer confirmed: peer's confirmed_utc − sender's utc, minutes (minute-granular stamps); n = confirmed ack-required messages",
                    "Observed")
            else:
                row("NR-04", f"ack latency {ln}→{peer}", "UNREAD — no confirmed ack-required message in this direction", "as above", "UNREAD")
            if debt:
                oldest = max(debt, key=lambda x: x[1])
                row("NR-05", f"ack debt {ln}→{peer}", f"{len(debt)} unconfirmed · oldest {oldest[0]} at {oldest[1] / 60:.1f} h",
                    "ack-required messages sent to the peer with no confirmation in the peer's sidecar; age = now − sender's utc (this is `inbox` from the sender's side)",
                    "Observed")
            else:
                row("NR-05", f"ack debt {ln}→{peer}", "0", "as above", "Observed")

    # NR-06 form conformance (the bus standard's three slots), NR-07 entry length, per lane
    for ln, v in by_lane.items():
        ok = [e for e in v if len(e["slots"]) == 3]
        row("NR-06", f"form conformance — {ln}", pct(len(ok), len(v)) + f"; last 10: {sum(1 for e in v[-10:] if len(e['slots']) == 3)}/10",
            "entries carrying all of **RECAP / **FOR RAB / **SUGGESTED PROMPT / all canonical entries from this lane (coordination/selftest.sh T2's rule)",
            "Observed")
        words = sorted(e["words"] for e in v) or [0]
        last = [e["words"] for e in v[-10:]] or [0]
        row("NR-07", f"entry length — {ln}", f"median {statistics.median(words):.0f} words · p90 {words[min(len(words) - 1, int(round(0.9 * (len(words) - 1))))]:.0f} · last 10 median {statistics.median(last):.0f}",
            "whitespace-split words per entry body (header excluded); the succinctness meter Rab asked for",
            "Observed")

    # NR-08 restatement length, NR-09 beat age, NR-10 escalations/disagreements, NR-11 state, per lane
    if both:
        for ln in SIDECARS:
            d = sc[ln][0]
            rl = sorted(len((c.get("restatement") or "").split()) for c in d.get("confirmed", [])) or [0]
            row("NR-08", f"restatement length — {ln}", f"median {statistics.median(rl):.0f} words · min {rl[0]} · n {len(rl)}",
                "words in each confirmation's restatement written by this lane (law 3: <10 chars refused)", "Observed")
            b = d.get("beat") or {}
            bt = utc(b.get("utc"))
            if bt:
                age = minutes(bt, now)
                row("NR-09", f"beat age — {ln}", f"{age:.0f} min{' *** STALE ***' if age > STALE_MIN else ''} (gate {b.get('gate_rev', '?')})",
                    f"now − beat.utc; the sidecar keeps ONLY the latest beat, so beat CADENCE over time is UNREAD until beats are logged (stale rule {STALE_MIN} min)",
                    "Observed")
            else:
                row("NR-09", f"beat age — {ln}", "UNREAD — no beat", "as above", "UNREAD")
            esc = d.get("escalations", [])
            open_esc = [e for e in esc if e.get("state") == "open"]
            row("NR-10", f"escalations — {ln}", f"{len(esc)} total · {len(open_esc)} open · disagreements {len(d.get('disagreements', []))}",
                "rows in the sidecar's escalations[] (open = state 'open'); an open one is FULL STOP for both lanes", "Observed")
            row("NR-11", f"state — {ln}", f"{d.get('state')} · ticket {d.get('current_ticket')} · occupant {d.get('occupant') or 'UNDECLARED'} · sent {len(d.get('sent', []))} · confirmed {len(d.get('confirmed', []))}",
                "the sidecar's own fields (a state says busy/idle; the beat says on what)", "Observed")

    # NR-12 peer bytes unstaged in the shared checkout
    try:
        st = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "coordination", "sessions"],
                            capture_output=True, text=True, timeout=30).stdout.splitlines()
        peer_files = [line[3:] for line in st if "ack-codex.json" in line or "codex" in line.lower()]
        # relay.md is one file with two writers: attribute its uncommitted hunk by the headers it adds
        hunk = subprocess.run(["git", "-C", str(REPO), "diff", "-U0", "--", "coordination/relay.md"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
        added = [m.group(1) for m in re.finditer(r"^\+## .*⟨from: (\w+)⟩", hunk, re.M)]
        relay_note = ("; relay.md uncommitted headers by writer: " + ", ".join(f"{w} {added.count(w)}" for w in sorted(set(added)))) if added else ""
        row("NR-12", "peer-owned bytes unstaged in the shared checkout", (f"{len(peer_files)}: {peer_files}" if peer_files else "0") + relay_note,
            "git status entries under coordination/ and sessions/ whose path names the peer lane, plus relay.md's uncommitted `+## ` headers counted per writer; a lane's close must not absorb the peer's (MSG-CDX-0048)",
            "Observed")
    except (OSError, subprocess.SubprocessError) as e:
        row("NR-12", "peer-owned bytes unstaged", f"UNREAD — git status failed: {e}", "as above", "UNREAD")

    # NR-13/14: the watcher's signals and the handler's turnaround need a signal log the watcher does not yet write
    log = HERE / "private" / "relay-watch.log"
    if log.exists():
        lines = [line for line in io.open(log, encoding="utf-8") if line.strip()]
        sig = [line for line in lines if not line.startswith("WATCH ARMED")]
        row("NR-13", "watcher signals logged", f"{len(sig)} signal lines · {sum(1 for line in lines if line.startswith('WATCH ARMED'))} arms",
            "lines in coordination/private/relay-watch.log (one per signal; FALSE-POSITIVE lines are those the session marked so)", "Observed")
    else:
        row("NR-13", "watcher signals logged", "UNREAD — the watcher writes no log yet (relay-watch.sh prints to the Monitor only)",
            "needs relay-watch.sh to append each signal line with its UTC to coordination/private/relay-watch.log", "UNREAD")
    row("NR-14", "handler turnaround (signal → confirmation)", "UNREAD — needs NR-13's log to pair a signal's UTC with the confirmation's confirmed_utc",
        "confirmed_utc − signal utc per handled signal", "UNREAD")

    if as_json:
        print(json.dumps({"measured_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "rows": rows}, indent=1, ensure_ascii=False))
    else:
        print(f"RELAY NUMERATIONS (NR-set) · measured {now.strftime('%Y-%m-%dT%H:%MZ')} · relay.md + ack-*.json · read-only")
        for r in rows:
            print(f"  {r['id']:6s} {r['name']:44s} {r['value']}")
            print(f"         [{r['tag']}] {r['numerator_denominator_conditions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
