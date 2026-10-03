"""WHAT THIS FILE DOES: loads the held DDIA bundle and rebuilds the (input chunk, shipped output) pairs the analyst
produced. Entry points: load_bundle() -> (manifest, sidecar text, shipped body); pairs() -> (manifest, input chunks,
aligned outputs, per-chunk score map); align(); sidecar_hash_check(). Reads the library read-only; the __main__ block
prints alignment checks to stdout. Imported by ladder_probe, analyze_results, edit_taxonomy and others in this folder.

prototypes/analyst-lab/decoding/ddia_pairs.py -- rebuild the analyst's INPUT chunks exactly as
analyst.process() does and align each chunk's shipped OUTPUT from the held DDIA bundle.

Read-only against the library. Quarantined (prototypes/README.md): nothing in the pipeline imports
this. The ONLY coupling is `sys.path` to windows-converter so the SAME fence/_chunks/ladder code
scores the pairs -- a re-implementation would measure the neighbour of the shipped thing.

Alignment rule: process() ships `unfence("\n\n".join(out), embeds)`, chunk order preserved, rejected
chunks verbatim. So chunk k's output is the shipped span between the located head of chunk k and
the located head of chunk k+1. A head is located by the first 6 whitespace-split words of the
NEXT chunk (heading markers stripped), searched forward from the current position on both the raw
and the ladder-normalised streams. The proof of alignment is not the locate step but the re-derivation:
text_norm.chunk_survival(input, aligned_output) must equal the manifest's `s` to the 4th digit on
every passed chunk it is asked about. Chunks where it does not are reported, not smoothed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

# -- setup: locate windows-converter, set the quarantine pipeline folder, import the shipped analyst code --
# S157 E50 (J44 re-measured): this bound the S119 fleet's WORKTREE (`.claude/worktrees/wf_cd7e80f0-d5a-2/…`), which no
# longer exists — the probe that sized J44's rungs could not run again (a script carrying its birthplace, S154's class).
# The repo's own windows-converter, found from this file; FP_WC overrides for a worktree run.
WC = os.environ.get("FP_WC") or str(pathlib.Path(__file__).resolve().parents[3] / "windows-converter")
sys.path.insert(0, WC)
os.environ.setdefault("FP_PIPELINE", os.path.join(os.environ.get("TEMP", r"C:\Temp"), "r2-quarantine"))
import analyst  # noqa: E402
import text_norm as tn  # noqa: E402

# -- constants: the held bundle location and the regex that strips leading heading markers --
LIB = pathlib.Path(r"C:\Users\Bndit\ml\library")
HELD = LIB / "held" / "fc1f068c3a8eeb63"
_HEAD_STRIP = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")


# -- bundle loading --
def load_bundle():
    """Read the held bundle's manifest, Marker sidecar text and shipped markdown body (frontmatter removed).
    Returns (manifest dict, sidecar text, shipped body). Read-only."""
    m = json.loads((HELD / "manifest.json").read_text(encoding="utf-8"))
    sidecar = next(HELD.glob("*.marker.txt"))
    sidecar_text = sidecar.read_text(encoding="utf-8")
    shipped_md = next(p for p in HELD.glob("*.md")).read_text(encoding="utf-8")
    parts = shipped_md.split("---\n", 2)
    shipped_body = parts[2] if len(parts) == 3 else shipped_md
    return m, sidecar_text, shipped_body


def sidecar_hash_check(m: dict, sidecar_text: str) -> dict:
    """Return the manifest's marker_body entry plus SHA-256 digests (raw and CRLF-normalised) and byte length of the
    sidecar text, so a caller can see whether the sidecar matches what the manifest recorded."""
    mb = m.get("marker_body") or {}
    raw = sidecar_text.encode("utf-8")
    return {
        "manifest.marker_body": mb,
        "sha256_of_sidecar_bytes": hashlib.sha256(raw).hexdigest(),
        "sha256_of_sidecar_crlf_normalised": hashlib.sha256(sidecar_text.replace("\r\n", "\n").encode("utf-8")).hexdigest(),
        "bytes": len(raw),
    }


# -- alignment of input chunks to the shipped output --
def _head_key(chunk: str, n: int = 6) -> str:
    """Return the first n whitespace-split words of the chunk, heading markers stripped, joined by single spaces
    (the search key used to find where a chunk starts in the output)."""
    return " ".join(_HEAD_STRIP.sub("", chunk).split()[:n])


def align(chunks_in: list[str], fenced_out: str) -> list[str | None]:
    """Return per-chunk output spans (fenced), None where the next head could not be located."""
    outs: list[str | None] = []
    pos = 0
    n = len(chunks_in)
    norm_out = fenced_out
    # for each chunk, find where the NEXT chunk's head starts in the output; the span between is this chunk's output
    for k in range(n):
        if k + 1 < n:
            key = _head_key(chunks_in[k + 1])
            nxt = norm_out.find(key, pos) if key else -1
            if nxt < 0:
                # second shape: 4 words
                key4 = _head_key(chunks_in[k + 1], 4)
                nxt = norm_out.find(key4, pos) if key4 else -1
            if nxt < 0:
                outs.append(None)
                # try to resync: search the head of k+2 and skip
                continue
            # back up to the start of that paragraph (the preceding blank line) so heading markers ride along
            para_start = norm_out.rfind("\n\n", pos, nxt)
            end = para_start if para_start >= 0 else nxt
            outs.append(norm_out[pos:end].strip("\n"))
            pos = end
        else:
            outs.append(norm_out[pos:].strip("\n"))
    return outs


# -- pair builder --
def pairs():
    """Rebuild the analyst's input chunks from the sidecar and align the shipped output to them. Returns
    (manifest, input chunks, aligned outputs with None for unlocated, {chunk index: manifest score row})."""
    m, sidecar_text, shipped_body = load_bundle()
    fenced_in, embeds = analyst.fence(sidecar_text)
    chunks_in = analyst._chunks(fenced_in)
    fenced_out, _ = analyst.fence(shipped_body)
    outs = align(chunks_in, fenced_out)
    cs = {r["i"]: r for r in m["analyst"]["chunk_scores"]}
    return m, chunks_in, outs, cs


# -- main: print the sidecar hash check, alignment counts and the survival re-derivation against the manifest --
if __name__ == "__main__":
    m, sidecar_text, shipped_body = load_bundle()
    print("sidecar hash check:", json.dumps(sidecar_hash_check(m, sidecar_text), indent=1))
    m, chunks_in, outs, cs = pairs()
    print(f"chunks rebuilt: {len(chunks_in)}  (manifest chunk_scores rows: {len(cs)})")
    print(f"program prefix chars: {len(analyst.load_program('readability'))}")
    unaligned = [k + 1 for k, o in enumerate(outs) if o is None]
    print(f"aligned outputs: {len(outs) - len(unaligned)} of {len(outs)}; unaligned chunk ids: {unaligned[:40]}{'...' if len(unaligned) > 40 else ''}")
    exact = mism = 0
    mism_rows = []
    # re-derive each aligned chunk's survival and compare with the manifest's score to the 4th digit
    for k, o in enumerate(outs):
        i = k + 1
        r = cs[i]
        if o is None or r.get("s") is None:
            continue
        s = tn.chunk_survival(chunks_in[k], o)
        if s is not None and abs(s - r["s"]) < 5e-5:
            exact += 1
        else:
            mism += 1
            if len(mism_rows) < 15:
                mism_rows.append((i, r.get("s"), s, r.get("x")))
    print(f"per-chunk survival re-derived == manifest s (4 dp): {exact}; mismatched: {mism}; first mismatches (i, manifest_s, mine, x): {mism_rows}")
    # rejected chunks must ship verbatim: out == in
    verb = sum(1 for k, o in enumerate(outs) if o is not None and cs[k + 1].get("x") and o == chunks_in[k])
    rej = sum(1 for r in cs.values() if r.get("x"))
    print(f"rejected chunks whose aligned output is byte-identical to input: {verb} of {rej}")
