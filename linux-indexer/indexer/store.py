"""The passage store: ONE SQLite file, <root>/index/index.sqlite, holding the bundles, the
passages, a BM25 keyword index (FTS5, in the sqlite build Arch and Ubuntu ship) and the
embeddings (sqlite-vec, a loadable extension, Apache-2.0/MIT). Chosen over a vector-database
package because an operator can open it with `sqlite3`, back it up by copying one file, filter
with a WHERE clause, and get keyword search from the same file -- and because a crash lands
in a transaction, not in two stores that disagree.

The `meta` table is the run record (tip reconciled to, when, result, effective levers, model
identity); `bundles` is one row per vaulted bundle keyed on source_sha256 with the manifest
provenance as JSON; `passages` is the text with its heading and page hint; `passages_fts`
mirrors `passages.text` through triggers; `passages_vec` holds one vector per passage with
the bundle sha as a filterable column. Everything about one bundle changes in one
transaction. Compatibility is checked on open: model, dimension, passage size and tokenizer
must match the run's, or the store REFUSES (report-mode) until `python -m indexer.main
--rebuild` -- the index is never rebuilt behind anyone's back.
"""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import sqlite_vec

DB_NAME = "index.sqlite"
SCHEMA_VERSION = "2"
_CONTRACT_KEYS = ("schema", "model", "dim", "passage_chars", "fts_tokenizer")
_TERM_RE = re.compile(r"\w+", re.UNICODE)
FTS_MAX_TERMS = 32  # lever-waiver: Rab; words of a question reaching BM25; moves on measured recall
_RRF_K = 60  # lever-waiver: Rab; the RRF paper's constant (Cormack 2009), moves on a measured recall number

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bundles (
    id INTEGER PRIMARY KEY,
    sha TEXT NOT NULL UNIQUE,
    note TEXT NOT NULL,
    md_name TEXT NOT NULL,
    source TEXT NOT NULL,
    md_blob TEXT NOT NULL,
    manifest_blob TEXT NOT NULL,
    indexed_tip TEXT NOT NULL,
    passages INTEGER NOT NULL,
    meta TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY,
    sha TEXT NOT NULL REFERENCES bundles(sha) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    heading TEXT NOT NULL,
    page_hint INTEGER,
    text TEXT NOT NULL,
    UNIQUE (sha, idx)
);
CREATE INDEX IF NOT EXISTS passages_by_sha ON passages(sha);
"""
_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts
    USING fts5(text, content='passages', content_rowid='id', tokenize='{tokenizer}');
CREATE TRIGGER IF NOT EXISTS passages_ai AFTER INSERT ON passages BEGIN
    INSERT INTO passages_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS passages_ad AFTER DELETE ON passages BEGIN
    INSERT INTO passages_fts(passages_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
CREATE VIRTUAL TABLE IF NOT EXISTS bundles_fts
    USING fts5(source, md_name, note, content='bundles', content_rowid='id', tokenize='{tokenizer}');
CREATE TRIGGER IF NOT EXISTS bundles_ai AFTER INSERT ON bundles BEGIN
    INSERT INTO bundles_fts(rowid, source, md_name, note) VALUES (new.id, new.source, new.md_name, new.note);
END;
CREATE TRIGGER IF NOT EXISTS bundles_ad AFTER DELETE ON bundles BEGIN
    INSERT INTO bundles_fts(bundles_fts, rowid, source, md_name, note)
        VALUES ('delete', old.id, old.source, old.md_name, old.note);
END;
CREATE TRIGGER IF NOT EXISTS bundles_au AFTER UPDATE ON bundles BEGIN
    INSERT INTO bundles_fts(bundles_fts, rowid, source, md_name, note)
        VALUES ('delete', old.id, old.source, old.md_name, old.note);
    INSERT INTO bundles_fts(rowid, source, md_name, note) VALUES (new.id, new.source, new.md_name, new.note);
END;
"""
_VEC = """
CREATE VIRTUAL TABLE IF NOT EXISTS passages_vec
    USING vec0(id INTEGER PRIMARY KEY, sha TEXT, embedding float[{dim}] distance_metric=cosine);
"""
_TOKENIZERS = {"unicode61": "unicode61 remove_diacritics 2", "trigram": "trigram"}


class StoreMismatch(Exception):
    pass


def fts_query(text: str) -> str | None:
    """A MATCH expression FTS5 cannot choke on: each word quoted, OR-ed (BM25 does the
    ranking); user syntax is never passed through."""
    terms = [t for t in _TERM_RE.findall(text) if len(t) > 1]
    return " OR ".join(f'"{t}"' for t in terms[:FTS_MAX_TERMS]) or None


class Store:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.db_path = index_dir / DB_NAME
        self.db: sqlite3.Connection | None = None

    def exists(self) -> bool:
        return self.db_path.is_file()

    # --- lifecycle ---

    def _connect(self, readonly: bool) -> sqlite3.Connection:
        if readonly:
            db = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        else:
            db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        db.execute("PRAGMA busy_timeout = 30000")
        db.execute("PRAGMA foreign_keys = ON")
        if not readonly:
            db.execute("PRAGMA journal_mode = WAL")
        return db

    def open(
        self,
        model: str,
        dim: int,
        passage_chars: int,
        fts_tokenizer: str,
        indexer_version: str,
    ) -> None:
        """Create or open for writing; refuse a store built under a different contract."""
        wanted = {
            "schema": SCHEMA_VERSION,
            "model": model,
            "dim": str(dim),
            "passage_chars": str(passage_chars),
            "fts_tokenizer": fts_tokenizer,
        }
        self.db = self._connect(readonly=False)
        with self.db:
            self.db.executescript(_SCHEMA)
            have = self.meta()
            if not have:
                self.db.executescript(_FTS.format(tokenizer=_TOKENIZERS[fts_tokenizer]))
                self.db.executescript(_VEC.format(dim=int(dim)))
                self.set_meta(
                    **wanted,
                    indexer_version=indexer_version,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
                return
        for key in _CONTRACT_KEYS:
            if have.get(key) != wanted[key]:
                self.close()
                raise StoreMismatch(
                    f"index was built with {key}={have.get(key)!r}, this run wants "
                    f"{wanted[key]!r}; rerun with --rebuild to re-embed from the vault"
                )

    def open_readonly(self) -> None:
        self.db = self._connect(readonly=True)

    def close(self) -> None:
        if self.db is not None:
            self.db.close()
            self.db = None

    # --- the run record ---

    def meta(self) -> dict:
        return {r["key"]: r["value"] for r in self.db.execute("SELECT key, value FROM meta")}

    def set_meta(self, **values) -> None:
        with self.db:
            self.db.executemany(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [(k, v if isinstance(v, str) else json.dumps(v)) for k, v in values.items()],
            )

    # --- per-bundle truth ---

    def bundle_state(self, sha: str) -> dict | None:
        row = self.db.execute("SELECT * FROM bundles WHERE sha = ?", (sha,)).fetchone()
        if row is None:
            return None
        state = dict(row)
        state.pop("id")
        state.update(json.loads(state.pop("meta")))
        return state

    def all_bundles(self) -> dict[str, dict]:
        return {
            r["sha"]: {
                "note": r["note"],
                "md_blob": r["md_blob"],
                "manifest_blob": r["manifest_blob"],
                "passages": r["passages"],
            }
            for r in self.db.execute(
                "SELECT sha, note, md_blob, manifest_blob, passages FROM bundles"
            )
        }

    def passage_ids(self, sha: str) -> list[int]:
        return [r["id"] for r in self.db.execute("SELECT id FROM passages WHERE sha = ?", (sha,))]

    def _delete_bundle_rows(self, sha: str) -> int:
        ids = self.passage_ids(sha)
        self.db.executemany("DELETE FROM passages_vec WHERE id = ?", [(i,) for i in ids])
        self.db.execute("DELETE FROM passages WHERE sha = ?", (sha,))
        self.db.execute("DELETE FROM bundles WHERE sha = ?", (sha,))
        return len(ids)

    def remove_bundle(self, sha: str) -> int:
        with self.db:
            return self._delete_bundle_rows(sha)

    def replace_bundle(self, sha: str, common: dict, passages, embeddings) -> None:
        """One transaction: the old rows go, the bundle row and every passage (text, keyword
        index via trigger, vector) come in."""
        columns = {
            k: common.get(k, "")
            for k in ("note", "md_name", "source", "md_blob", "manifest_blob", "indexed_tip")
        }
        extra = {k: v for k, v in common.items() if k not in columns and k != "source_sha256"}
        with self.db:
            self._delete_bundle_rows(sha)
            self.db.execute(
                "INSERT INTO bundles(sha, note, md_name, source, md_blob, manifest_blob, "
                "indexed_tip, passages, meta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sha, *columns.values(), len(passages), json.dumps(extra, ensure_ascii=False)),
            )
            base = self.db.execute("SELECT COALESCE(MAX(id), 0) FROM passages").fetchone()[0]
            self.db.executemany(
                "INSERT INTO passages(id, sha, idx, heading, page_hint, text) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (base + 1 + p.index, sha, p.index, p.heading, p.page_hint, p.text)
                    for p in passages
                ],
            )
            self.db.executemany(
                "INSERT INTO passages_vec(id, sha, embedding) VALUES (?, ?, ?)",
                [
                    (base + 1 + p.index, sha, sqlite_vec.serialize_float32(vec))
                    for p, vec in zip(passages, embeddings)
                ],
            )

    def rewrite_metadata(self, sha: str, common: dict) -> int:
        """A manifest changed but the body did not: the bundle row is rewritten and every
        passage keeps its text and vector. Exact -- a withdrawn key is gone, not merged over."""
        columns = {
            k: common.get(k, "")
            for k in ("note", "md_name", "source", "manifest_blob", "indexed_tip")
        }
        extra = {
            k: v
            for k, v in common.items()
            if k not in columns and k not in ("source_sha256", "md_blob")
        }
        with self.db:
            self.db.execute(
                "UPDATE bundles SET note = ?, md_name = ?, source = ?, manifest_blob = ?, "
                "indexed_tip = ?, meta = ? WHERE sha = ?",
                (*columns.values(), json.dumps(extra, ensure_ascii=False), sha),
            )
            return self.db.execute("SELECT passages FROM bundles WHERE sha = ?", (sha,)).fetchone()[
                0
            ]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM passages").fetchone()[0]

    # --- search legs; each returns [(passage id, raw score)] best first. A sha filter is applied
    # INSIDE the SQL (sqlite-vec accepts IN on a metadata column), never after the fetch: a
    # filtered query for a common word must not starve because the unfiltered top-k belonged
    # to other bundles (Observed 2026-09-09 on the real vault: --bundle claude "the" -> nothing).

    @staticmethod
    def _sha_clause(column: str, shas: set[str] | None) -> tuple[str, list]:
        if shas is None:
            return "", []
        marks = ",".join("?" * len(shas))
        return f" AND {column} IN ({marks})", sorted(shas)

    def search_vector(self, embedding: list[float], k: int, shas: set[str] | None = None) -> list:
        if k <= 0 or shas == set():
            return []
        clause, params = self._sha_clause("sha", shas)
        rows = self.db.execute(
            "SELECT id, distance FROM passages_vec WHERE embedding MATCH ? AND k = ?"
            + clause
            + " ORDER BY distance",
            (sqlite_vec.serialize_float32(embedding), k, *params),
        ).fetchall()
        return [(r["id"], r["distance"]) for r in rows]

    def search_keyword(self, text: str, k: int, shas: set[str] | None = None) -> list:
        match = fts_query(text)
        if match is None or k <= 0 or shas == set():
            return []
        clause, params = self._sha_clause("p.sha", shas)
        rows = self.db.execute(
            "SELECT f.rowid AS id, bm25(passages_fts) AS score "
            "FROM passages_fts f JOIN passages p ON p.id = f.rowid "
            "WHERE passages_fts MATCH ?" + clause + " ORDER BY score LIMIT ?",
            (match, *params, k),
        ).fetchall()
        return [(r["id"], r["score"]) for r in rows]

    def search_titles(self, text: str, k: int, shas: set[str] | None = None) -> list:
        """The keyword leg over what the body never says about itself: the source filename, the
        note's filename and its vault path (an ISBN or a title lives there, Observed 2026-09-09:
        Brain of the Firm's ISBN is in its filename and nowhere in its text). A matching bundle
        answers with its first passage."""
        match = fts_query(text)
        if match is None or k <= 0 or shas == set():
            return []
        clause, params = self._sha_clause("b.sha", shas)
        rows = self.db.execute(
            "SELECT p.id AS id, bm25(bundles_fts) AS score "
            "FROM bundles_fts f JOIN bundles b ON b.id = f.rowid "
            "JOIN passages p ON p.sha = b.sha AND p.idx = 0 "
            "WHERE bundles_fts MATCH ?" + clause + " ORDER BY score LIMIT ?",
            (match, *params, k),
        ).fetchall()
        return [(r["id"], r["score"]) for r in rows]

    def shas_where(
        self, bundle: str | None, lane: str | None, verdict: str | None
    ) -> set[str] | None:
        """Bundle-level filters resolve to a sha set once (the bundles table is small)."""
        if bundle is None and lane is None and verdict is None:
            return None
        allowed: set[str] = set()
        for row in self.db.execute("SELECT sha, note, meta FROM bundles"):
            meta = json.loads(row["meta"])
            if bundle is not None and bundle not in row["note"]:
                continue
            if lane is not None and meta.get("lane") != lane:
                continue
            if verdict is not None and meta.get("verdict", "none") != verdict:
                continue
            allowed.add(row["sha"])
        return allowed

    def fetch(self, ids: list[int]) -> dict[int, dict]:
        if not ids:
            return {}
        marks = ",".join("?" * len(ids))
        out = {}
        for r in self.db.execute(
            f"SELECT p.id, p.sha, p.idx, p.heading, p.page_hint, p.text, b.note, b.meta "
            f"FROM passages p JOIN bundles b ON b.sha = p.sha WHERE p.id IN ({marks})",
            ids,
        ):
            meta = json.loads(r["meta"])
            out[r["id"]] = {
                "bundle": r["note"].rsplit("/", 1)[-1],
                "note": r["note"],
                "source": meta.get("source"),
                "source_sha256": r["sha"],
                "heading": r["heading"],
                "page_hint": r["page_hint"],
                "passage": r["idx"],
                "text": r["text"],
            }
        return out


def fuse(legs: dict[str, list]) -> list[tuple[int, float, str]]:
    """Reciprocal rank fusion across legs -> [(id, score, matched_by)] best first."""
    scores: dict[int, float] = {}
    seen: dict[int, list[str]] = {}
    for name, ranked in legs.items():
        for rank, (pid, _raw) in enumerate(ranked):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (_RRF_K + rank + 1)
            seen.setdefault(pid, []).append(name)
    return sorted(
        ((pid, score, "+".join(seen[pid])) for pid, score in scores.items()),
        key=lambda t: -t[1],
    )
