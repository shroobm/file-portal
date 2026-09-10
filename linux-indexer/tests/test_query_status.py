"""The read-only surfaces over a store the reconciler built: query in each mode with filters,
returning the documented hit shape or a calm `available: false`; status comparing the index
tip to the vault NOW; the HTTP endpoint's routes on a loopback port. The hash embedder stands
in for the model, so vector-leg ORDER is meaningless here -- what is asserted is shape, the
keyword leg (real FTS5), fusion, filters and the model-free paths."""

import json
import socket
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from indexer import query, serve, status
from indexer.reconcile import reconcile
from indexer.store import fts_query, fuse
from tests.test_reconcile import (
    BODY_B,
    SETTINGS,
    SHA_A,
    SHA_B,
    HashEmbedder,
    commit_all,
    paths,
    vault_bundle,
)

__all__ = ["paths"]  # the fixture is imported for pytest, not re-exported for style


def indexed(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    vault_bundle(
        paths,
        "Inbox/book-b--bb22bb22",
        "Book B",
        SHA_B,
        body=BODY_B,
        manifest={"lane": "scan", "fidelity": {"verdict": "flag"}},
    )
    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 0


HIT_KEYS = [
    "bundle",
    "note",
    "source",
    "source_sha256",
    "heading",
    "page_hint",
    "passage",
    "text",
    "score",
    "matched_by",
]


def test_no_index_is_a_calm_answer_not_an_error(paths):
    doc = query.run(paths.root, SETTINGS, "anything", embedder=HashEmbedder())
    assert doc["available"] is False
    doc = status.run(paths.root)
    assert doc["available"] is False and len(doc["vault_tip"]) == 8


def test_keyword_mode_answers_without_any_model(paths):
    indexed(paths)

    doc = query.run(paths.root, SETTINGS, "Frege assertion", mode="keyword")  # no embedder

    assert doc["available"] is True and doc["mode"] == "keyword"
    assert doc["hits"], "BM25 must find the word"
    assert doc["hits"][0]["bundle"] == "book-b--bb22bb22"
    assert all("keyword" in h["matched_by"] or h["matched_by"] == "title" for h in doc["hits"])
    assert list(doc["hits"][0]) == HIT_KEYS


def test_hybrid_fuses_both_legs_and_names_them(paths):
    indexed(paths)

    doc = query.run(paths.root, SETTINGS, "recursive theorem", top_k=3, embedder=HashEmbedder())

    assert doc["mode"] == "hybrid" and len(doc["tip"]) == 8
    assert doc["levers"]["top_k"] == 3 and doc["levers"]["passage_chars"] == 120
    assert 1 <= len(doc["hits"]) <= 3
    assert all(
        set(h["matched_by"].split("+")) <= {"vector", "keyword", "title"} for h in doc["hits"]
    )
    assert any("keyword" in h["matched_by"] for h in doc["hits"]), "the word is in the index"
    assert doc["hits"] == sorted(doc["hits"], key=lambda h: -h["score"])


def test_filters_narrow_by_bundle_lane_and_verdict(paths):
    indexed(paths)
    embedder = HashEmbedder()

    only_b = query.run(paths.root, SETTINGS, "the", bundle="book-b", embedder=embedder)
    assert {h["bundle"] for h in only_b["hits"]} == {"book-b--bb22bb22"}
    assert only_b["filters"] == {"bundle": "book-b"}
    scan = query.run(paths.root, SETTINGS, "the", lane="scan", embedder=embedder)
    assert {h["bundle"] for h in scan["hits"]} == {"book-b--bb22bb22"}
    unaudited = query.run(paths.root, SETTINGS, "the", verdict="none", embedder=embedder)
    assert {h["bundle"] for h in unaudited["hits"]} == {"book-a--aa11aa11"}
    nothing = query.run(paths.root, SETTINGS, "the", lane="nope", embedder=embedder)
    assert nothing["hits"] == [] and nothing["available"] is True


def test_query_refuses_a_foreign_embedder(paths):
    indexed(paths)
    doc = query.run(paths.root, SETTINGS, "x", embedder=HashEmbedder(name="other"))
    assert doc["available"] is False and "other" in doc["reason"]


def test_fts_query_never_passes_user_syntax_through():
    assert (
        fts_query('requisite "variety" OR NOT (x)') == '"requisite" OR "variety" OR "OR" OR "NOT"'
    )
    assert fts_query("a") is None
    assert fts_query("设计原理 agent") == '"设计原理" OR "agent"'


def test_fusion_prefers_what_both_legs_agree_on():
    fused = fuse({"vector": [(1, 0.1), (2, 0.2)], "keyword": [(2, -3.0), (3, -2.0)]})
    assert [pid for pid, _, _ in fused][0] == 2
    assert dict((pid, by) for pid, _, by in fused) == {
        2: "vector+keyword",
        1: "vector",
        3: "keyword",
    }


def test_status_in_sync_flips_when_the_vault_moves(paths):
    indexed(paths)
    doc = status.run(paths.root)
    assert doc["in_sync"] is True and doc["bundles"] == 2 and doc["passages"] > 0
    assert doc["model"] == "hash-8" and doc["last_result"] == "pass"
    assert doc["levers"]["query_mode"] == "hybrid"

    (paths.root.parent / "vault-work" / "note.md").write_text("a hand note\n")
    commit_all(paths, "hand note")

    assert status.run(paths.root)["in_sync"] is False


def test_serve_routes_on_loopback(paths):
    indexed(paths)
    state = serve._State.__new__(serve._State)
    state.root, state.settings = paths.root, SETTINGS
    state.embedder, state.reranker = HashEmbedder(), None
    state.lock = threading.Lock()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        assert json.load(urllib.request.urlopen(f"{base}/health")) == {"ok": True}
        assert json.load(urllib.request.urlopen(f"{base}/status"))["in_sync"] is True
        got = json.load(urllib.request.urlopen(f"{base}/query?q=Frege&mode=keyword&k=2"))
        assert got["hits"][0]["bundle"] == "book-b--bb22bb22" and len(got["hits"]) <= 2
        req = urllib.request.Request(
            f"{base}/query",
            data=json.dumps({"q": "Frege", "mode": "keyword", "bundle": "book-a"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert json.load(urllib.request.urlopen(req))["hits"] == []
        try:
            urllib.request.urlopen(f"{base}/query?mode=keyword")
        except urllib.error.HTTPError as err:
            assert err.code == 400
        else:
            raise AssertionError("an empty q must be a 400")
    finally:
        server.shutdown()
        server.server_close()


def test_filters_apply_inside_every_leg_not_after_the_fetch(paths):
    # PLANTED starvation: bundle A is long and full of "the"; the unfiltered top-k for "the"
    # belongs to A entirely. A --bundle b filter must still answer from B (Observed on the
    # real vault 2026-09-09: --bundle claude "the" returned nothing under post-filtering).
    long_body = (
        "# A\n\n" + "\n\n".join(f"the {i} the the the filler the" for i in range(300)) + "\n"
    )
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A, body=long_body)
    vault_bundle(paths, "Inbox/book-b--bb22bb22", "Book B", SHA_B, body="# B\n\nthe one line\n")
    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 0

    for mode in ("keyword", "vector", "hybrid"):
        doc = query.run(
            paths.root, SETTINGS, "the", mode=mode, bundle="book-b", embedder=HashEmbedder()
        )
        assert {h["bundle"] for h in doc["hits"]} == {"book-b--bb22bb22"}, mode


def test_title_leg_finds_what_the_body_never_says(paths):
    vault_bundle(
        paths,
        "Inbox/brain-of-the-firm--aa11aa11",
        "BRAIN OF THE FIRM (WITH OCR) ISBN 13 9780471162131",
        SHA_A,
        body="# One\n\nno numbers in this body at all\n",
    )
    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 0

    doc = query.run(paths.root, SETTINGS, "9780471162131", mode="keyword")

    assert doc["hits"] and doc["hits"][0]["matched_by"] == "title"
    assert (
        doc["hits"][0]["passage"] == 0 and doc["hits"][0]["bundle"] == "brain-of-the-firm--aa11aa11"
    )
    assert (
        query.run(paths.root, SETTINGS, "9780471162131", mode="keyword", bundle="nope")["hits"]
        == []
    )


def test_serve_rejects_what_is_not_a_question(paths):
    indexed(paths)
    state = serve._State.__new__(serve._State)
    state.root, state.settings, state.embedder, state.reranker = paths.root, SETTINGS, None, None
    state.lock = threading.Lock()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadingHTTPServer(("127.0.0.1", port), serve._handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    def post(body, **headers):
        req = urllib.request.Request(base + "/query", data=body, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=10).status
        except urllib.error.HTTPError as err:
            return err.code

    try:
        assert post(b"[1, 2]") == 400, "a JSON array is not a question"
        assert post(b"42") == 400
        assert post(b"not json") == 400
        assert post(json.dumps({"q": "x" * 3000, "mode": "keyword"}).encode()) == 400
        assert post(b"{}", **{"Content-Length": str(10**7)}) == 413
        assert post(json.dumps({"q": "Frege", "mode": "keyword"}).encode()) == 200
    finally:
        server.shutdown()
        server.server_close()
