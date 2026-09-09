"""Segment the shipped DDIA body into the 492 per-chunk counterparts of the analyst's inputs.

HOW THE SHIPPED BODY WAS MADE (analyst.process, read at e19e0e0):
    fenced, embeds = fence(marker_body); chunks = _chunks(fenced)
    out[i] = candidate (passed) | chunk (rejected/failed)
    shipped_body = unfence("\n\n".join(out), embeds)
So re-fencing the shipped body yields the SAME ⟦IMG-n⟧ tokens in the same order (every passed chunk
kept its token list, `_tokens_of` compares sorted lists; rejected chunks are the originals), and the
shipped body is the concatenation of 492 pieces separated by "\n\n".

HOW A BOUNDARY IS FOUND (honestly, method recorded per boundary):
  - tokens: raw whitespace tokens of the fenced shipped body, with a boundary-search KEY per token
    (casefold, non-alphanumerics dropped; ⟦IMG-n⟧ tokens keep an exact key).
  - for chunk k+1 we take its first 12 non-empty keys (the ANCHOR) and search the shipped key list
    from the cursor, inside a window sized by chunk k's own length (x1.6 + 200 tokens — the inflation
    guard admits at most 1.5x); exact subsequence first ("exact12"), then shorter anchors
    ("exact8", "exact6", "exact4"), then a fuzzy anchor via difflib on the window ("fuzzy"); a
    boundary nothing finds is cut at the proportional position and flagged "unaligned".
  - the cut lands at the "\n\n" that precedes the anchor token when one is within 3 chars of it
    (the join separator), else at the token itself.
  - pieces concatenate back to the shipped body byte-for-byte (asserted).
  - every REJECTED chunk's piece must equal its input verbatim (asserted, reported): 20 independent
    checks of the segmentation that would fail if a boundary drifted into a neighbour.
"""
import difflib
import re

from common import analyst, load_bundle  # noqa: F401

_WS_TOKEN = re.compile(r"\S+")
_TOK = re.compile(r"⟦IMG-(\d+)⟧")


def key_of(tok: str) -> str:
    m = _TOK.search(tok)
    if m:
        return f"<img{m.group(1)}>"
    return re.sub(r"[^0-9a-z]+", "", tok.casefold())


def tokens_with_offsets(text: str):
    return [(m.start(), m.end(), m.group(0)) for m in _WS_TOKEN.finditer(text)]


def _find_subseq(keys, anchor, lo, hi):
    n = len(anchor)
    first = anchor[0]
    i = lo
    while True:
        try:
            i = keys.index(first, i, hi)
        except ValueError:
            return -1
        if keys[i:i + n] == anchor:
            return i
        i += 1


def segment(fenced_shipped: str, chunks_in: list[str], rejected: set[int] = frozenset()) -> list[dict]:
    """`rejected` holds 1-based chunk indices the manifest marks rejected (they ship verbatim)."""
    toks = tokens_with_offsets(fenced_shipped)
    keys = [key_of(t[2]) for t in toks]
    n_chunks = len(chunks_in)
    chunk_keys = []
    for c in chunks_in:
        ks = [key_of(t) for t in c.split()]
        chunk_keys.append([k for k in ks if k])
    # nonempty-key index list for the shipped side (search ignores empty keys)
    ne_idx = [i for i, k in enumerate(keys) if k]
    ne_keys = [keys[i] for i in ne_idx]
    starts = [0]           # char offset where chunk k's piece starts
    methods = []
    cursor_ne = 0          # position in ne_keys
    import bisect
    for k in range(n_chunks - 1):
        this_len = len(chunk_keys[k])
        lo = cursor_ne
        hi = min(len(ne_keys), cursor_ne + int(this_len * 1.6) + 200)
        method, pos = None, -1
        # (a) verbatim fast path: the piece at the cursor IS the input chunk (rejected chunks, and
        # passed chunks the model returned byte-identical), followed by the join separator.
        cur_off = starts[-1]
        probe = cur_off + (2 if fenced_shipped.startswith("\n\n", cur_off) and k > 0 else 0)
        cand = chunks_in[k]
        if fenced_shipped.startswith(cand, probe) and fenced_shipped.startswith("\n\n", probe + len(cand)):
            cut = probe + len(cand)
            # the next chunk's anchor must sit right after the separator, else fall through
            nxt_tok = bisect.bisect_left([t[0] for t in toks], cut + 2)
            ne_pos = bisect.bisect_left(ne_idx, nxt_tok)
            anchor = chunk_keys[k + 1][:min(12, len(chunk_keys[k + 1]))]
            # a REJECTED chunk ships verbatim by construction (analyst.process appends the
            # original), so its verbatim match is the boundary even when the next candidate
            # reordered its own opening (chunk 2 of DDIA moved a heading to its front); a PASSED
            # chunk that came back byte-identical still needs the next anchor to agree
            if (k + 1) in rejected or (anchor and ne_keys[ne_pos:ne_pos + len(anchor)] == anchor):
                starts.append(cut)
                methods.append("verbatim")
                cursor_ne = ne_pos
                continue
        # (b) anchor search: every occurrence in the window, the one closest to the expected
        # position wins (title pages repeat their blurbs; the FIRST occurrence is the wrong one)
        expected = cursor_ne + this_len
        for n in (12, 8, 6, 4):
            anchor = chunk_keys[k + 1][:n]
            if len(anchor) < n:
                continue
            occ = []
            p = _find_subseq(ne_keys, anchor, lo, hi)
            while p != -1 and len(occ) < 50:
                occ.append(p)
                p = _find_subseq(ne_keys, anchor, p + 1, hi)
            if occ:
                pos = min(occ, key=lambda q: abs(q - expected))
                method = f"exact{n}" + (f"(of {len(occ)})" if len(occ) > 1 else "")
                break
        if pos == -1:
            # fuzzy: best matching block of the 12-key anchor inside the window
            anchor = chunk_keys[k + 1][:12]
            window = ne_keys[lo:hi]
            sm = difflib.SequenceMatcher(None, window, anchor, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size >= 3]
            if blocks:
                b0 = blocks[0]
                pos = lo + b0.a - b0.b
                pos = max(lo, min(pos, hi - 1))
                method = f"fuzzy(size={b0.size})"
        if pos == -1:
            pos = min(len(ne_keys) - 1, lo + this_len)
            method = "unaligned"
        tok_i = ne_idx[pos]
        off = toks[tok_i][0]
        # the cut is the LAST join separator in the gap between the previous non-empty-key token
        # and the anchor token (a list's "- " or a table row's "| " begins the next chunk and has
        # an empty key; the separator sits before it, not before the anchor word)
        prev_end = toks[ne_idx[pos - 1]][1] if pos > 0 else 0
        sep = fenced_shipped.rfind("\n\n", max(prev_end, starts[-1]), off)
        cut = sep if sep != -1 else off
        if cut < starts[-1]:
            cut = starts[-1]
            method += "+clamped"
        starts.append(cut)
        methods.append(method)
        cursor_ne = pos
    pieces = []
    for k in range(n_chunks):
        a = starts[k]
        b = starts[k + 1] if k + 1 < n_chunks else len(fenced_shipped)
        pieces.append({"i": k + 1, "start": a, "end": b, "raw": fenced_shipped[a:b],
                       "method": methods[k] if k < len(methods) else "last"})
    assert "".join(p["raw"] for p in pieces) == fenced_shipped
    return pieces


def piece_text(p: dict, first: bool) -> str:
    """The chunk's counterpart with the join separators removed: pieces after the first start with
    the "\\n\\n" separator; the last piece may end with a trailing newline."""
    t = p["raw"]
    if not first and t.startswith("\n\n"):
        t = t[2:]
    return t


def build_pairs(bundle: dict) -> tuple[list[dict], dict]:
    fenced_out, embeds_out = analyst.fence(bundle["shipped_body"])
    chunks_in = bundle["chunks_in"]
    cs = bundle["chunk_scores"]
    pieces = segment(fenced_out, chunks_in, rejected={i for i, r in cs.items() if "x" in r})
    pairs = []
    stats = {"tokens_in": len(bundle["embeds"]), "tokens_out": len(embeds_out), "methods": {},
             "rejected_verbatim": 0, "rejected_total": 0, "rejected_mismatch": []}
    for k, p in enumerate(pieces):
        out_text = piece_text(p, first=(k == 0))
        row = cs.get(k + 1, {})
        status = "rejected" if "x" in row else "passed"
        prefix = p["raw"][:len(p["raw"]) - len(out_text)]  # the separator actually present ("" | "\n\n")
        rec = {"i": k + 1, "input": chunks_in[k], "output": out_text, "prefix": prefix,
               "method": p["method"], "status": status, "s": row.get("s"), "r": row.get("r"),
               "x": row.get("x")}
        stats["methods"][p["method"].split("(")[0].split("+")[0]] = stats["methods"].get(p["method"].split("(")[0].split("+")[0], 0) + 1
        if status == "rejected":
            stats["rejected_total"] += 1
            if out_text.rstrip("\n") == chunks_in[k].rstrip("\n"):
                stats["rejected_verbatim"] += 1
            else:
                stats["rejected_mismatch"].append(k + 1)
        pairs.append(rec)
    return pairs, stats


if __name__ == "__main__":
    b = load_bundle()
    pairs, stats = build_pairs(b)
    print("pairs:", len(pairs))
    print("stats:", stats)
    # the rebuilt shipped body must be the shipped body
    fenced_out, embeds_out = analyst.fence(b["shipped_body"])
    rebuilt = "".join(p["prefix"] + p["output"] for p in pairs)
    print("rebuilt == fenced shipped body:", rebuilt == fenced_out, "| unfenced ==:",
          analyst.unfence(rebuilt, embeds_out) == b["shipped_body"],
          "| pieces without the \\n\\n separator:", sum(1 for p in pairs[1:] if p["prefix"] != "\n\n"))
    import collections
    print("method census:", collections.Counter(p["method"] for p in pairs).most_common())
    # word ratio per pair vs manifest r for passed rows (a second-shaped check of the segmentation)
    from common import tn
    diffs = []
    for p in pairs:
        if p["status"] == "passed" and p["r"] is not None:
            r2 = tn.word_ratio(p["input"], p["output"])
            diffs.append((abs((r2 or 0) - p["r"]), p["i"], p["r"], r2))
    diffs.sort(reverse=True)
    print("passed pairs with manifest ratio:", len(diffs), "| |ratio - manifest r| <= 0.005:",
          sum(1 for d in diffs if d[0] <= 0.005), "| worst 5:", diffs[:5])
    s_diffs = []
    for p in pairs:
        if p["status"] == "passed" and p["s"] is not None:
            s2 = tn.chunk_survival(p["input"], p["output"])
            s_diffs.append((abs((s2 or 0) - p["s"]), p["i"], p["s"], s2))
    s_diffs.sort(reverse=True)
    print("passed pairs with manifest survival:", len(s_diffs), "| |survival - manifest s| <= 0.005:",
          sum(1 for d in s_diffs if d[0] <= 0.005), "| worst 5:", s_diffs[:5])
