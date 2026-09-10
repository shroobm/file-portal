"""Reconcile tests against a REAL bare vault on a temp root, same doctrine as the converter's
test_exporter: the vault pair is built by the fixture with real git, bundles are committed and
pushed the way the exporter ships them (Inbox/<slug>--<sha8>/{<name>.md, manifest.json,
assets/}), and assertions read what the code provably wrote -- the SQLite store on disk (the
way bare_has/bare_show read the bare repo) and receipts.jsonl.

The model is replaced by a deterministic hash embedder: reconcile logic (identity, staleness,
supersede, filing, removal, refusal, the store as the only record) is what is under test here.
Embedding quality against the real vault was measured in docs/11 Phase 3 and re-measured
2026-09-09; it is not something a fixture can stand in for (SYM-001), so nothing here claims
it. No network, no ~/file-portal, no model files."""

import hashlib
import json
import shutil
import subprocess

import pytest

from indexer.config import Paths, Settings
from indexer.reconcile import reconcile
from indexer.store import Store

SHA_A = "aa11" * 16
SHA_B = "bb22" * 16
IDENT = ["-c", "user.name=test", "-c", "user.email=test@test.invalid"]
# Small passages so a few paragraphs make several of them.
SETTINGS = Settings(
    passage_chars=120,
    passage_max_chars=200,
    threads=1,
    top_k=5,
    serve_port=8765,
    model="hash-8",
    query_mode="hybrid",
    rerank="off",
    fts_tokenizer="unicode61",
)

BODY_A = (
    "# Chapter One\n\nThe viable system model describes regulation. It has five systems.\n\n"
    "![[assets/_page_3_Figure_0.jpeg]]\n\n## Recursion\n\nEvery viable system contains and is "
    "contained in a viable system. This is the recursive theorem.\n\nA second paragraph on "
    "recursion that pads the section out a little further for the packer.\n"
)
BODY_B = (
    "# Judgement\n\nFrege distinguished the thought from its assertion. Judging is advancing "
    "from a thought to its truth value.\n\nTruth is not a property in the ordinary sense.\n"
)


class HashEmbedder:
    """Deterministic, model-free vectors: sha256 of the text, eight bytes, unit-normalised.
    Counts its calls so a test can prove the model was NOT consulted."""

    dim = 8

    def __init__(self, name="hash-8"):
        self.name = name
        self.calls = 0

    def _vec(self, text):
        raw = hashlib.sha256(text.encode("utf-8")).digest()[: self.dim]
        vec = [(b - 128) / 128 for b in raw]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def embed_passages(self, texts):
        self.calls += 1
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)

    def identity(self):
        return {"name": self.name, "dim": self.dim, "runtime": "test", "model_sha256": "0" * 64}


def git(repo, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        text=True,
    )
    if check:
        assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


@pytest.fixture
def paths(tmp_path):
    p = Paths.from_root(tmp_path / "file-portal")
    p.ensure_exist()
    # Wire the vault pair the way Decision #4 did manually: bare repo + working clone,
    # seeded before any content. The indexer only ever reads the bare side.
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(p.vault_bare)],
        check=True,
        capture_output=True,
    )
    work = work_of(p)
    subprocess.run(["git", "clone", str(p.vault_bare), str(work)], check=True, capture_output=True)
    (work / ".gitattributes").write_text("* text=auto eol=lf\n")
    git(work, "add", ".gitattributes")
    git(work, *IDENT, "commit", "-m", "chore: seed")
    git(work, "push", "-u", "origin", "main")
    return p


def work_of(paths):
    return paths.root.parent / "vault-work"


def commit_all(paths, message):
    work = work_of(paths)
    git(work, "add", "-A")
    git(work, *IDENT, "commit", "-m", message)
    git(work, "push", "origin", "main")


def vault_bundle(paths, note, name, sha, body=BODY_A, manifest=None, commit=True):
    """Lay a bundle down in the working clone the way the exporter publishes it, then push."""
    bundle = work_of(paths) / note
    (bundle / "assets").mkdir(parents=True, exist_ok=True)
    (bundle / f"{name}.md").write_text(
        f"---\nconversion:\n  engine: marker\n  lane: clean\n  source_sha256: {sha}\n---\n{body}"
    )
    (bundle / "assets" / "page-1.png").write_bytes(b"\x89PNG fake")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {"source": f"{name}.pdf", "source_sha256": sha, "lane": "clean", **(manifest or {})}
        )
    )
    if commit:
        commit_all(paths, f"ingest: {note}")
    return bundle


def open_store(paths):
    store = Store(paths.index)
    store.open_readonly()
    return store


def passage_rows(store, sha):
    return [
        dict(r)
        for r in store.db.execute(
            "SELECT id, idx, heading, page_hint, text FROM passages WHERE sha = ? ORDER BY idx",
            (sha,),
        )
    ]


def read_receipts(paths):
    out = []
    try:
        lines = (paths.root / "receipts.jsonl").read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue  # a deliberately torn seed line in one test
    return out


# --- first contact, idempotence ---


def test_first_run_indexes_every_bundle_and_writes_one_receipt(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    vault_bundle(paths, "Inbox/book-b--bb22bb22", "Book B", SHA_B, body=BODY_B)
    embedder = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0

    store = open_store(paths)
    rows = passage_rows(store, SHA_A)
    assert len(rows) > 1, "BODY_A must split into several passages at these levers"
    assert [r["idx"] for r in rows] == list(range(len(rows)))
    assert store.db.execute("SELECT COUNT(*) FROM passages_vec").fetchone()[0] == store.count()
    state = store.bundle_state(SHA_A)
    assert state["note"] == "Inbox/book-a--aa11aa11"
    assert state["md_name"] == "Book A.md"
    assert state["lane"] == "clean"
    assert "verdict" not in state, "absent fidelity must stay absent, never become a pass"
    meta = store.meta()
    assert meta["model"] == "hash-8" and meta["dim"] == "8" and meta["result"] == "pass"
    assert len(meta["tip"]) == 40
    (record,) = read_receipts(paths)
    assert record["outcome"] == "indexed"
    assert record["result"] == "pass"
    assert len(record["tip"]) == 8
    assert record["added"] == 2 and record["bundles"] == 2
    assert record["passages"] == store.count()
    assert "bundle" not in record, "two bundles changed: no single bundle to name"
    assert record["model"] == "hash-8" and record["passage_chars"] == SETTINGS.passage_chars


def test_second_run_is_quiet_and_never_consults_the_model(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 0
    again = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=again) == 0

    assert again.calls == 0
    assert len(read_receipts(paths)) == 1, "an unchanged tip must not re-file its receipt"


def test_page_hint_and_heading_ride_on_the_passage(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    reconcile(paths.root, SETTINGS, embedder=HashEmbedder())

    rows = passage_rows(open_store(paths), SHA_A)
    by_heading = {r["heading"]: r for r in rows}
    assert "Chapter One" in by_heading and "Recursion" in by_heading
    assert by_heading["Recursion"]["page_hint"] == 4, "_page_3_ is 0-based: the hint is page 4"
    assert by_heading["Chapter One"]["page_hint"] is None, "no figure before it: null, not 0"
    assert not any("![[" in r["text"] for r in rows), "embeds are stripped from the text"


# --- the vault moves: supersede, bless, filing, deletion ---


def test_supersede_replaces_that_bundle_in_place(paths):
    bundle = vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    vault_bundle(paths, "Inbox/book-b--bb22bb22", "Book B", SHA_B, body=BODY_B)
    reconcile(paths.root, SETTINGS, embedder=HashEmbedder())
    before_a = passage_rows(open_store(paths), SHA_A)
    before_b = passage_rows(open_store(paths), SHA_B)
    # A supersede keeps the path and the .md filename; only the bytes change (docs/15 §14.3).
    (bundle / "Book A.md").write_text(
        f"---\nconversion:\n  source_sha256: {SHA_A}\n---\n# Remedied\n\nA wholly new body.\n"
    )
    commit_all(paths, "supersede: book-a--aa11aa11 (reaudit, fail→pass)")
    embedder = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0

    store = open_store(paths)
    after_a = passage_rows(store, SHA_A)
    assert [r["text"] for r in after_a] == ["# Remedied\n\nA wholly new body."]
    assert {r["id"] for r in after_a}.isdisjoint({r["id"] for r in before_a}), "old rows gone"
    assert passage_rows(store, SHA_B) == before_b, "the untouched bundle is untouched"
    assert store.db.execute("SELECT COUNT(*) FROM passages_vec").fetchone()[0] == store.count()
    record = read_receipts(paths)[-1]
    assert record["replaced"] == 1 and record["unchanged"] == 1 and record["added"] == 0
    assert record["bundle"] == "book-a--aa11aa11", "exactly one bundle changed: it is named"
    assert record["note"] == "Inbox/book-a--aa11aa11"


def test_manifest_only_change_rewrites_metadata_without_the_model(paths):
    bundle = vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    reconcile(paths.root, SETTINGS, embedder=HashEmbedder())
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["blessed"] = {"by": "rab", "ts": 1, "reason": "figure-heavy", "from_verdict": "flag"}
    manifest["fidelity"] = {"verdict": "flag", "convert": {"doc_survival": 0.93}}
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    commit_all(paths, "bless")
    embedder = HashEmbedder()
    before = passage_rows(open_store(paths), SHA_A)

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0

    assert embedder.calls == 0, "same body: the model must not run"
    store = open_store(paths)
    assert passage_rows(store, SHA_A) == before, "passages and their ids survive a bless"
    state = store.bundle_state(SHA_A)
    assert state["blessed_by"] == "rab" and state["verdict"] == "flag"
    assert state["doc_survival"] == 0.93
    assert read_receipts(paths)[-1]["updated"] == 1

    # PLANTED withdrawal: a stale key must be gone, not merged over.
    del manifest["blessed"]
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    commit_all(paths, "unbless")
    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0
    assert "blessed_by" not in open_store(paths).bundle_state(SHA_A)


def test_desktop_filing_keeps_identity_and_adds_no_duplicates(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    embedder = HashEmbedder()
    reconcile(paths.root, SETTINGS, embedder=embedder)
    before = passage_rows(open_store(paths), SHA_A)
    work = work_of(paths)
    (work / "Filed").mkdir()
    git(work, "mv", "Inbox/book-a--aa11aa11", "Filed/book-a--aa11aa11")
    commit_all(paths, "file: book-a")
    embedder = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0

    assert embedder.calls == 0
    store = open_store(paths)
    assert passage_rows(store, SHA_A) == before, "same sha, same passages, no duplicates"
    assert store.bundle_state(SHA_A)["note"] == "Filed/book-a--aa11aa11"
    assert store.count() == len(before)


def test_deleted_bundle_passages_are_removed(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    vault_bundle(paths, "Inbox/book-b--bb22bb22", "Book B", SHA_B, body=BODY_B)
    reconcile(paths.root, SETTINGS, embedder=HashEmbedder())
    git(work_of(paths), "rm", "-r", "-q", "Inbox/book-b--bb22bb22")
    commit_all(paths, "chore: remove book-b")
    embedder = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 0

    store = open_store(paths)
    assert passage_rows(store, SHA_B) == []
    assert store.bundle_state(SHA_B) is None
    assert passage_rows(store, SHA_A), "the surviving bundle survives"
    assert store.db.execute("SELECT COUNT(*) FROM passages_vec").fetchone()[0] == store.count()
    assert store.search_keyword("Frege", 5) == [], "the keyword index forgets it too"
    record = read_receipts(paths)[-1]
    assert record["removed"] == 1 and record["bundles"] == 1
    assert record["bundle"] == "book-b--bb22bb22"


# --- refusing to guess ---


def test_two_bodies_are_refused_and_the_rest_still_index(paths):
    bundle = vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A, commit=False)
    (bundle / "Book A (copy).md").write_text("# a second body\n")
    good = vault_bundle(paths, "Inbox/book-b--bb22bb22", "Book B", SHA_B, body=BODY_B, commit=False)
    # A generated report beside the body is NOT a second body (repair-bench's REPAIRS.md).
    (good / "REPAIRS.md").write_text("# repairs\n")
    commit_all(paths, "ingest both")
    embedder = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=embedder) == 1

    store = open_store(paths)
    assert store.bundle_state(SHA_A) is None
    assert passage_rows(store, SHA_B), "REPAIRS.md must not disqualify a well-formed bundle"
    record = read_receipts(paths)[-1]
    assert record["result"] == "fail"
    assert record["refused"] == 1 and record["added"] == 1


def test_a_sha_vaulted_twice_refuses_both_copies(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A, commit=False)
    vault_bundle(paths, "Inbox/book-a-again--aa11aa11", "Book A again", SHA_A)

    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 1

    record = read_receipts(paths)[-1]
    assert record["refused"] == 2 and record["bundles"] == 0
    assert open_store(paths).bundle_state(SHA_A) is None


def test_missing_vault_fails_loudly(paths):
    shutil.rmtree(paths.vault_bare)

    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 2

    (record,) = read_receipts(paths)
    assert record["outcome"] == "index-failed"
    assert "missing" in record["error"]


def test_model_mismatch_is_refused_until_an_explicit_rebuild(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    assert reconcile(paths.root, SETTINGS, embedder=HashEmbedder()) == 0
    other = HashEmbedder(name="hash-8-other")

    assert reconcile(paths.root, SETTINGS, embedder=other) == 1

    record = read_receipts(paths)[-1]
    assert record["outcome"] == "index-failed"
    assert "rebuild" in record["error"]
    assert other.calls == 0, "a refused run must not embed"
    assert open_store(paths).meta()["model"] == "hash-8", "a refused run changes nothing"

    assert reconcile(paths.root, SETTINGS, embedder=other, rebuild=True) == 0
    record = read_receipts(paths)[-1]
    assert record["outcome"] == "indexed" and record["added"] == 1
    assert record["model"] == "hash-8-other"
    assert open_store(paths).meta()["model"] == "hash-8-other"


def test_the_store_is_the_only_record(paths):
    # NEGATIVE CONTROL: no state file exists to lie; delete the store and the next run
    # re-adds everything from the vault, because there is nothing else to trust.
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    reconcile(paths.root, SETTINGS, embedder=HashEmbedder())
    store = Store(paths.index)
    assert not any(p.suffix == ".json" for p in paths.index.iterdir()), "no side state files"
    store.db_path.unlink()
    again = HashEmbedder()

    assert reconcile(paths.root, SETTINGS, embedder=again) == 0

    assert again.calls == 1
    assert read_receipts(paths)[-1]["added"] == 1


def test_lever_fallbacks_are_named_in_the_receipt(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    settings = Settings(**{**SETTINGS.__dict__, "fallbacks": ("threads='x'->4",)})

    assert reconcile(paths.root, settings, embedder=HashEmbedder()) == 0

    assert read_receipts(paths)[-1]["lever_fallbacks"] == "threads='x'->4"
    assert json.loads(open_store(paths).meta()["lever_fallbacks"]) == ["threads='x'->4"]


def test_unknown_model_name_is_a_receipt_not_a_traceback(paths):
    vault_bundle(paths, "Inbox/book-a--aa11aa11", "Book A", SHA_A)
    settings = Settings(**{**SETTINGS.__dict__, "model": "nobody/no-such-model"})

    assert reconcile(paths.root, settings) == 1  # No embedder injected: the real lookup runs

    record = read_receipts(paths)[-1]
    assert record["outcome"] == "index-failed" and "catalogue" in record["error"]
