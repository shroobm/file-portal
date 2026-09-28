"""The Library graph (S214 E24; Rab, 2026-09-27 22:14Z: "all obsidian vault books and up to date ones
that get sent to the vault in the future show up as a network cell graph in library"; 2026-09-28
17:52Z: "all three" readings).

The vault's notes do not link one another, so the edges are derived from what the index already
holds: one vector per passage. A book's CENTROID is the mean of its passage vectors; two books are
joined when their centroids' cosine is high enough (each book keeps its top-k neighbours). The
third reading hangs books off TERMS: each book's top words by tf-idf over its own passages, and a
term is a shared node when at least two books carry it.

One JSON, rebuilt when the index's tip changes and cached beside the index (graph.json); /graph
serves it (token-gated like every route but /health). Every number names its rule: the levers are
in the document, and a book with no vectors is listed as a node without edges, never dropped.
"""

from __future__ import annotations

import json
import math
import re
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from indexer.store import Store

GRAPH_FILE = "graph.json"
EDGE_K = 4  # lever-waiver: Rab; neighbours kept per book, moves on how the graph reads
MIN_SIM = 0.30  # lever-waiver: Rab; the cosine under which two books are not joined
TOP_TERMS = 12  # lever-waiver: Rab; terms kept per book
MAX_TERMS = 80  # lever-waiver: Rab; shared terms kept in the third reading
_WORD = re.compile(r"[a-z][a-z'-]{2,}")
_STOP = frozenset(
    """a about above after again against all also although am an and any are as at be because been
    before being below between both but by can cannot could did do does doing done down during each
    either few for from further had has have having he her here hers herself him himself his how i if
    in into is it its itself just let me more most my myself no nor not now of off on once only or
    other our ours ourselves out over own same she should so some such than that the their theirs them
    themselves then there these they this those through to too under until up upon us very was we were
    what when where which while who whom why will with within without would you your yours yourself
    yourselves one two three first second new used using use uses may might must shall via per et al
    fig figure figures table tables page pages chapter section eq equation equations ie eg vol pp""".split()
)


def _decode(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _norm(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def centroids(store: Store) -> dict[str, list[float]]:
    """Mean passage vector per book, unit length; a book without vectors is absent here."""
    sums: dict[str, list[float]] = {}
    counts: Counter = Counter()
    for row in store.db.execute("SELECT sha, embedding FROM passages_vec"):
        vec = _decode(row["embedding"])
        acc = sums.get(row["sha"])
        if acc is None:
            sums[row["sha"]] = list(vec)
        else:
            for i, x in enumerate(vec):
                acc[i] += x
        counts[row["sha"]] += 1
    return {sha: _norm([x / counts[sha] for x in acc]) for sha, acc in sums.items()}


def edges_from(
    cents: dict[str, list[float]], edge_k: int = EDGE_K, min_sim: float = MIN_SIM
) -> list[dict]:
    """Undirected edges: each book's top-k neighbours by cosine at or above min_sim, deduplicated."""
    shas = sorted(cents)
    kept: dict[tuple[str, str], float] = {}
    for a in shas:
        sims = []
        for b in shas:
            if a == b:
                continue
            s = sum(x * y for x, y in zip(cents[a], cents[b]))
            if s >= min_sim:
                sims.append((s, b))
        sims.sort(reverse=True)
        for s, b in sims[:edge_k]:
            key = (a, b) if a < b else (b, a)
            kept[key] = max(kept.get(key, 0.0), s)
    return [
        {"a": a, "b": b, "w": round(w, 4)}
        for (a, b), w in sorted(kept.items(), key=lambda kv: -kv[1])
    ]


def terms_from(
    store: Store, top_terms: int = TOP_TERMS, max_terms: int = MAX_TERMS
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Per book: its top words by tf-idf over its passages (tf = share of the book's words, idf over
    books). Shared: a term carried by at least two books, with those books, the strongest first."""
    tf: dict[str, Counter] = {}
    total: Counter = Counter()
    for row in store.db.execute("SELECT sha, text FROM passages"):
        words = [
            w for w in _WORD.findall(row["text"].lower()) if w not in _STOP and not w.endswith("'s")
        ]
        if not words:
            continue
        tf.setdefault(row["sha"], Counter()).update(words)
        total[row["sha"]] += len(words)
    n_books = max(1, len(tf))
    df: Counter = Counter()
    for counts in tf.values():
        df.update(counts.keys())
    per_book: dict[str, list[dict]] = {}
    shared: dict[str, dict] = {}
    for sha, counts in tf.items():
        scored = []
        for term, c in counts.items():
            if c < 2:
                continue
            idf = math.log((1 + n_books) / (1 + df[term])) + 1.0
            scored.append((c / total[sha] * idf, term, c))
        scored.sort(reverse=True)
        per_book[sha] = [
            {"term": t, "score": round(s, 5), "count": c} for s, t, c in scored[:top_terms]
        ]
        for s, t, _c in scored[:top_terms]:
            entry = shared.setdefault(t, {"term": t, "books": [], "weight": 0.0})
            entry["books"].append(sha)
            entry["weight"] += s
    shared_terms = [e for e in shared.values() if len(e["books"]) >= 2]
    shared_terms.sort(key=lambda e: (-len(e["books"]), -e["weight"]))
    for e in shared_terms:
        e["weight"] = round(e["weight"], 5)
    return per_book, shared_terms[:max_terms]


def build(
    store: Store,
    edge_k: int = EDGE_K,
    min_sim: float = MIN_SIM,
    top_terms: int = TOP_TERMS,
    max_terms: int = MAX_TERMS,
) -> dict:
    """The whole graph from an open store: nodes (every indexed book), edges, terms, the levers, the tip."""
    meta = store.meta()
    cents = centroids(store)
    per_book, shared = terms_from(store, top_terms, max_terms)
    nodes = []
    for row in store.db.execute(
        "SELECT sha, note, md_name, source, indexed_tip, passages, meta FROM bundles ORDER BY note"
    ):
        extra = json.loads(row["meta"] or "{}")
        title = (row["md_name"] or row["source"] or row["sha"]).rsplit("/", 1)[-1]
        title = re.sub(r"\.(md|pdf)$", "", title, flags=re.I)
        nodes.append(
            {
                "sha": row["sha"],
                "title": title,
                "note": row["note"],
                "source": row["source"],
                "lane": extra.get("lane"),
                "verdict": extra.get("verdict"),
                "survival": extra.get("doc_survival"),
                "pages": extra.get("pages"),
                "converted_at": extra.get("converted_at"),
                "indexed_tip": row["indexed_tip"],
                "passages": row["passages"],
                "vectors": row["sha"] in cents,
                "terms": per_book.get(row["sha"], []),
            }
        )
    edges = edges_from(cents, edge_k, min_sim)
    return {
        "tip": meta.get("tip"),
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": meta.get("model"),
        "levers": {
            "edge_k": edge_k,
            "min_sim": min_sim,
            "top_terms": top_terms,
            "max_terms": max_terms,
        },
        "counts": {
            "nodes": len(nodes),
            "with_vectors": len(cents),
            "edges": len(edges),
            "terms": len(shared),
        },
        "nodes": nodes,
        "edges": edges,
        "terms": shared,
    }


def cached(index_dir: Path, store: Store, **levers) -> dict:
    """The graph for the store's current tip: read from graph.json when it was built from that tip
    with these levers, else rebuilt and written. A missing tip (an index never reconciled) still
    builds, uncached."""
    path = index_dir / GRAPH_FILE
    tip = store.meta().get("tip")
    wanted = {
        "edge_k": EDGE_K,
        "min_sim": MIN_SIM,
        "top_terms": TOP_TERMS,
        "max_terms": MAX_TERMS,
        **levers,
    }
    if tip and path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("tip") == tip and doc.get("levers") == wanted:
                doc["cached"] = True
                return doc
        except (OSError, ValueError):
            pass
    doc = build(store, **wanted)
    doc["cached"] = False
    if tip:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    return doc
