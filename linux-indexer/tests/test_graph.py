"""The Library graph (S214 E24): centroids from the stored vectors, edges by cosine with a floor and
a per-book k, terms by tf-idf, the cache keyed by the tip and the levers. A store with four small
books and hand-made vectors; a NEGATIVE control (two orthogonal books are not joined); no model."""

import json

from indexer import graph
from indexer.passages import Passage
from indexer.store import Store

DIM = 4


def _store(tmp_path):
    s = Store(tmp_path)
    s.open(
        model="test-model",
        dim=DIM,
        passage_chars=800,
        fts_tokenizer="unicode61",
        indexer_version="t",
    )
    return s


def _passage(i, text):
    return Passage(index=i, heading="h", page_hint=None, text=text)


def _book(store, sha, md_name, texts, vecs, meta=None):
    common = {
        "note": f"Inbox/{md_name}",
        "md_name": md_name + ".md",
        "source": md_name + ".pdf",
        "md_blob": "\n".join(texts),
        "manifest_blob": "{}",
        "indexed_tip": "abc12345",
        **(meta or {}),
    }
    store.replace_bundle(sha, common, [_passage(i, t) for i, t in enumerate(texts)], vecs)


def _seed(store):
    # two books on the same subject (parallel vectors), one on another (orthogonal), one without vectors
    _book(
        store,
        "a" * 16,
        "Parallel Algorithms",
        ["parallel processors mesh mesh mesh", "processors mesh routing routing"],
        [[1, 0, 0, 0], [1, 0.1, 0, 0]],
        {"lane": "scan", "verdict": "flag", "doc_survival": 0.9, "pages": 10},
    )
    _book(
        store,
        "b" * 16,
        "Scalable Multiprocessors",
        ["multiprocessors parallel mesh mesh", "processors processors cache"],
        [[0.9, 0.2, 0, 0], [1, 0, 0.1, 0]],
        {"lane": "scan", "verdict": "pass", "doc_survival": 0.99},
    )
    _book(
        store,
        "c" * 16,
        "Polyhedral Functions",
        ["simplicial polyhedral polyhedral minimizing", "polyhedral functions functions"],
        [[0, 0, 1, 0], [0, 0, 1, 0.05]],
        {"lane": "clean", "verdict": "flag", "doc_survival": 0.52},
    )
    _book(store, "d" * 16, "No Vectors Yet", ["an empty empty book"], [], {"lane": "clean"})
    store.set_meta(tip="deadbeef")


def test_centroids_edges_and_terms(tmp_path):
    s = _store(tmp_path)
    _seed(s)
    cents = graph.centroids(s)
    assert set(cents) == {"a" * 16, "b" * 16, "c" * 16}, "a book without vectors has no centroid"
    for v in cents.values():
        assert abs(sum(x * x for x in v) - 1.0) < 1e-6, "centroids are unit length"
    edges = graph.edges_from(cents, edge_k=4, min_sim=0.30)
    pairs = {(e["a"], e["b"]) for e in edges}
    assert ("a" * 16, "b" * 16) in pairs, "the two parallel books are joined"
    assert ("a" * 16, "c" * 16) not in pairs and ("b" * 16, "c" * 16) not in pairs, (
        "NEGATIVE: orthogonal books are not joined"
    )
    per_book, shared = graph.terms_from(s, top_terms=5, max_terms=10)
    assert per_book["a" * 16][0]["term"] == "mesh", per_book["a" * 16]
    assert any(t["term"] == "mesh" and len(t["books"]) == 2 for t in shared), shared
    assert all(len(t["books"]) >= 2 for t in shared), (
        "a shared term is carried by at least two books"
    )
    assert "polyhedral" not in {t["term"] for t in shared}, "a term of one book alone is not shared"


def test_build_lists_every_book_and_the_levers(tmp_path):
    s = _store(tmp_path)
    _seed(s)
    doc = graph.build(s)
    assert (
        doc["tip"] == "deadbeef"
        and doc["counts"]["nodes"] == 4
        and doc["counts"]["with_vectors"] == 3
    )
    by = {n["sha"]: n for n in doc["nodes"]}
    assert by["d" * 16]["vectors"] is False and by["d" * 16]["title"] == "No Vectors Yet"
    assert (
        by["a" * 16]["lane"] == "scan"
        and by["a" * 16]["survival"] == 0.9
        and by["a" * 16]["pages"] == 10
    )
    assert doc["levers"] == {
        "edge_k": graph.EDGE_K,
        "min_sim": graph.MIN_SIM,
        "top_terms": graph.TOP_TERMS,
        "max_terms": graph.MAX_TERMS,
    }
    assert doc["edges"] and all(0 < e["w"] <= 1.0001 for e in doc["edges"])
    json.dumps(doc)  # the document is plain JSON


def test_graph_route_serves_the_document(tmp_path):
    """The ROUTE, not just the module (S214 E24: the first deploy 502'd on a path the module never
    exercised): a store under the root's own index dir, the endpoint on a loopback port, /graph
    gated by the token like every route, and the document it returns."""
    import json as _json
    import socket
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    from indexer import serve
    from indexer.config import Paths, Settings

    paths = Paths.from_root(tmp_path)
    paths.index.mkdir(parents=True, exist_ok=True)
    s = _store(paths.index)
    _seed(s)
    s.close()
    (tmp_path / serve.TOKEN_FILE).write_text("s3cret\n", encoding="utf-8")
    state = serve._State.__new__(serve._State)
    state.root = tmp_path
    state.settings = Settings.load(tmp_path / "missing.toml")
    state.lock = threading.Lock()
    state.embedder = None
    state.reranker = None
    state.token = serve.read_token(tmp_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/graph")
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("NEGATIVE: /graph without the token must be refused")
        except urllib.error.HTTPError as e:
            assert e.code == 403
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/graph", headers={"X-FP-Token": "s3cret"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            doc = _json.load(r)
        assert doc["available"] is True and doc["tip"] == "deadbeef" and doc["counts"]["nodes"] == 4
        assert (paths.index / graph.GRAPH_FILE).is_file(), (
            "the route cached the graph beside the index"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            again = _json.load(r)
        assert again["cached"] is True
    finally:
        server.shutdown()


def test_cache_follows_the_tip_and_the_levers(tmp_path):
    s = _store(tmp_path)
    _seed(s)
    first = graph.cached(tmp_path, s)
    assert first["cached"] is False and (tmp_path / graph.GRAPH_FILE).is_file()
    second = graph.cached(tmp_path, s)
    assert second["cached"] is True and second["computed_at"] == first["computed_at"]
    other = graph.cached(tmp_path, s, edge_k=1)
    assert other["cached"] is False and other["levers"]["edge_k"] == 1, "a different lever rebuilds"
    s.set_meta(tip="feedface")
    third = graph.cached(tmp_path, s)
    assert third["cached"] is False and third["tip"] == "feedface", "a new tip rebuilds"
