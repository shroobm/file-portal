"""Query: hybrid retrieval over the store -- a vector leg (the model), a keyword leg (FTS5 BM25
over passage text) and a title leg (BM25 over each bundle's source filename, note name and
vault path -- where an ISBN or a title lives when the body never says it), fused by reciprocal
rank, optionally re-ordered by a cross-encoder. Modes are a lever (`query_mode`): `keyword`
answers without loading any model (keyword + title legs), `vector` is docs/11's pure semantic
search, `hybrid` is all three. Filters narrow to a bundle (substring of its vault path), a
lane, or a verdict (`none` for bundles that carry no fidelity block); they apply inside the
SQL of every leg.

The CLI prints exactly one JSON document on stdout and exits 0 -- the shape the widget already
consumes (status.rs) and the dashboard can subprocess. Callable over the channel the Desktop
already uses, as one fixed literal with the question on stdin:

    tailscale ssh rab@archlinux '~/file-portal-src/linux-indexer/.venv/bin/python -m indexer.query'

No path arguments, no sockets, nothing written (docs/06; docs/14: read-only by construction).
No LLM in the loop (docs/41 P-4: the search path is deterministic; an LLM may adjudicate,
never search). A missing index is a calm `{"available": false, ...}` answer, not an error; a
real failure exits 1 with one line on stderr. The answer carries the index tip and the
effective levers so its currency and conditions are checkable; `page_hint` is a hint or null,
never a promise.
"""

import argparse
import json
import sys
from pathlib import Path

from indexer.config import DEFAULT_ROOT, Paths, Settings, lever_menu, lever_range
from indexer.embed import Embedder, FastEmbedder, Reranker
from indexer.store import Store, fuse

_LEG_FACTOR = 4  # lever-waiver: Rab; candidates per leg as a multiple of top_k, moves on a measured recall number


def run(
    root: Path,
    settings: Settings,
    text: str,
    top_k: int | None = None,
    mode: str | None = None,
    bundle: str | None = None,
    lane: str | None = None,
    verdict: str | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
) -> dict:
    paths = Paths.from_root(root)
    store = Store(paths.index)
    if not store.exists():
        return {"available": False, "reason": f"no index at {paths.index}"}
    n = settings.top_k if top_k is None else top_k
    mode = mode or settings.query_mode
    store.open_readonly()
    try:
        meta = store.meta()
        shas = store.shas_where(bundle, lane, verdict)
        legs: dict[str, list] = {}
        leg_k = max(n * _LEG_FACTOR, n)
        if mode in ("vector", "hybrid"):
            embedder = embedder or FastEmbedder(meta["model"], settings.threads, paths.models)
            if embedder.name != meta.get("model"):
                return {
                    "available": False,
                    "reason": f"index built with {meta.get('model')!r}, query embedder is "
                    f"{embedder.name!r}",
                }
            legs["vector"] = store.search_vector(embedder.embed_query(text), leg_k, shas)
        if mode in ("keyword", "hybrid"):
            legs["keyword"] = store.search_keyword(text, leg_k, shas)
            legs["title"] = store.search_titles(text, leg_k, shas)
        fused = fuse(legs)
        rows = store.fetch([pid for pid, _, _ in fused[: max(n * _LEG_FACTOR, n)]])
        hits = []
        for pid, score, matched_by in fused:
            if pid not in rows:
                continue
            hits.append({**rows[pid], "score": round(score, 5), "matched_by": matched_by})
        rerank_model = settings.rerank if reranker is None else reranker.name
        if rerank_model != "off" and hits:
            reranker = reranker or Reranker(settings.rerank, settings.threads, paths.models)
            scores = reranker.scores(text, [h["text"] for h in hits])
            for hit, s in zip(hits, scores):
                hit["rerank_score"] = round(s, 4)
            hits.sort(key=lambda h: -h["rerank_score"])
        hits = hits[:n]
        tip = meta.get("tip")
        return {
            "available": True,
            "query": text,
            "mode": mode,
            "filters": {
                k: v for k, v in (("bundle", bundle), ("lane", lane), ("verdict", verdict)) if v
            },
            "tip": tip[:8] if tip else None,
            "reconciled_at": meta.get("reconciled_at"),
            "model": meta.get("model"),
            "rerank": rerank_model,
            "levers": {**settings.effective(), "top_k": n, "query_mode": mode},
            "hits": hits,
        }
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="File Portal index query (JSON on stdout)")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "indexer.toml",
    )
    parser.add_argument("--top-k", type=int, default=None, help="passages to return")
    parser.add_argument("--mode", choices=lever_menu("query_mode"), default=None)
    parser.add_argument("--bundle", default=None, help="substring of the bundle's vault path")
    parser.add_argument("--lane", default=None, help="clean | scan")
    parser.add_argument("--verdict", default=None, help="pass | flag | fail | none")
    parser.add_argument("--query", default=None, help="question text (default: stdin)")
    args = parser.parse_args()
    text = (args.query if args.query is not None else sys.stdin.read(65536)).strip()
    if not text:
        print("query text required (--query or stdin)", file=sys.stderr)
        sys.exit(1)
    low, high = lever_range("top_k")
    if args.top_k is not None and not low <= args.top_k <= high:
        print(f"--top-k must be within {low}..{high}", file=sys.stderr)
        sys.exit(1)
    try:
        doc = run(
            args.root,
            Settings.load(args.config),
            text,
            top_k=args.top_k,
            mode=args.mode,
            bundle=args.bundle,
            lane=args.lane,
            verdict=args.verdict,
        )
    except Exception as exc:  # noqa: BLE001 -- one line on stderr is the contract
        print(f"query failed: {type(exc).__name__}: {exc}"[:300], file=sys.stderr)
        sys.exit(1)
    print(json.dumps(doc, ensure_ascii=False))


if __name__ == "__main__":
    main()
