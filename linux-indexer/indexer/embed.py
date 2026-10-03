"""WHAT THIS FILE DOES: turns text into number vectors (FastEmbedder, used to index passages and to
embed a question) and re-scores candidate passages against a question (Reranker). Both load their
model lazily through the fastembed library from files kept under <root>/index/models. Also defines
the Embedder interface that tests replace with a fake. Called by reconcile.py and query.py.

Embedding and reranking backends over fastembed (Apache-2.0): ONNX Runtime, no torch, a
catalogue of models selectable by name -- the `model` lever in config/indexer.toml.

Why a lever and not the one model docs/11 measured: the vault already holds a Chinese book
(Observed 2026-09-09: bojieli, a 200-byte CJK source name) and all-MiniLM-L6-v2 is
English-only with a 256-token window. Measured here 2026-09-09 (batch 32, 4 threads, 1,244 real
passages): all-MiniLM-L6-v2 56 passages/s at 420 MiB, 7/7 probes; the multilingual sibling
paraphrase-multilingual-MiniLM-L12-v2 5 passages/s at 980 MiB, 6/7. The default stays the
fast July model; the multilingual one is one lever flip away, and anything in
`TextEmbedding.list_supported_models()` is admissible. The store records the model and
refuses a mismatch until `--rebuild`. NOTE: fastembed's MiniLM is a different ONNX export
from the one docs/11 measured through torch -- cosine floor 0.58 against it on 64 passages
(Observed) -- so July's vectors and today's are not interchangeable, only the model name is.

Model files are fetched once from Hugging Face into <root>/index/models (fastembed's own
default is /tmp, which does not survive a reboot); after that the loader is told
local_files_only so nothing here touches the network again. Every *.onnx file of the chosen
model is hashed into the identity the store and every receipt carry (docs/34 §5).

Query-vs-passage prefixes (e5, bge, nomic need them) are fastembed's `query_embed` /
`passage_embed` responsibility, which is why both are exposed rather than one `embed`.
"""

import hashlib
from functools import cached_property
from pathlib import Path
from typing import Protocol


# -- constant: how many passages are embedded per call --
# fastembed's own default batch of 256, padded to the model's window, blew one process to
# 9.9 GiB here (Observed 2026-09-09).
EMBED_BATCH = 32  # lever-waiver: Rab; the per-call embed batch, moves on a measured RSS number


# -- the embedder interface and its error --
class Embedder(Protocol):
    """What the rest of the indexer needs from an embedder: a model name, a vector size and the
    three methods below (FastEmbedder is the real one; tests supply a fake)."""

    name: str
    dim: int

    # embed_passages: list of passage texts in, one vector per text out (interface only, no body)
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    # embed_query: one question text in, one vector out (interface only, no body)
    def embed_query(self, text: str) -> list[float]: ...

    # identity: a dict describing the model and runtime, stored with the index (interface only)
    def identity(self) -> dict: ...


class UnknownModel(ValueError):
    """Raised when the requested model name is not in fastembed's catalogue."""

    pass


# -- model catalogue and file lookup --
def catalogue() -> dict[str, dict]:
    """fastembed's list of supported embedding models, keyed by model name (imports fastembed)."""
    from fastembed import TextEmbedding

    return {m["model"]: m for m in TextEmbedding.list_supported_models()}


def _model_files(cache_dir: Path, model: str) -> list[Path]:
    """Every *.onnx under the cache that belongs to this model (fastembed lays models out
    HF-hub style, models--org--name/snapshots/<rev>/...)."""
    tag = model.split("/")[-1]
    return sorted(p for p in cache_dir.rglob("*.onnx") if tag in str(p.relative_to(cache_dir)))


# -- the real embedder (fastembed / ONNX Runtime) --
class FastEmbedder:
    """Embeds text with a fastembed model; the model loads on first use."""

    def __init__(self, model: str, threads: int, cache_dir: Path):
        """Look the model up in the catalogue (raises UnknownModel if absent) and record its name,
        vector size, thread count and cache folder. Loads no model yet."""
        entry = catalogue().get(model)
        if entry is None:
            raise UnknownModel(
                f"{model!r} is not in fastembed's catalogue; pick one of "
                f"{', '.join(sorted(catalogue()))}"
            )
        self.name = model
        self.dim = int(entry["dim"])
        self.threads = threads
        self.cache_dir = cache_dir

    @cached_property
    def _backend(self):
        """The loaded fastembed TextEmbedding, built once. Uses local files only when the model's
        .onnx files are already in the cache; otherwise fastembed downloads them (network)."""
        from fastembed import TextEmbedding

        offline = bool(_model_files(self.cache_dir, self.name))
        return TextEmbedding(
            self.name,
            cache_dir=str(self.cache_dir),
            threads=self.threads,
            providers=["CPUExecutionProvider"],
            local_files_only=offline,
        )

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embed passage texts (in batches of EMBED_BATCH); returns one list of floats per text."""
        if not texts:
            return []
        return [
            [float(x) for x in v]
            for v in self._backend.passage_embed(texts, batch_size=EMBED_BATCH)
        ]

    def embed_query(self, text: str) -> list[float]:
        """Embed one question; returns a single list of floats."""
        return [float(x) for x in next(iter(self._backend.query_embed(text)))]

    @cached_property
    def _model_sha256(self) -> str:
        """SHA-256 over the names and bytes of the model's .onnx files (read from disk once)."""
        digest = hashlib.sha256()
        for path in _model_files(self.cache_dir, self.name):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def identity(self) -> dict:
        """A dict naming the model, vector size, library versions, model-file hash and thread
        count; stored in the index and in receipts. Loads the model if not yet loaded."""
        import fastembed
        import onnxruntime as ort

        _ = self._backend  # ensure the files exist before hashing them
        return {
            "name": self.name,
            "dim": self.dim,
            "runtime": f"fastembed {fastembed.__version__} / onnxruntime {ort.__version__}",
            "model_sha256": self._model_sha256,
            "model_files": [p.name for p in _model_files(self.cache_dir, self.name)],
            "threads": self.threads,
        }


# -- the optional reranker --
class Reranker:
    """Cross-encoder over (query, passage) pairs; the `rerank` lever names the model or `off`.
    Report-only in the sense of docs/15 §6: it reorders what the retrievers returned and
    attaches its score; it never drops a hit."""

    def __init__(self, model: str, threads: int, cache_dir: Path):
        """Record the reranker model name, thread count and cache folder; loads nothing yet."""
        self.name = model
        self.threads = threads
        self.cache_dir = cache_dir

    @cached_property
    def _backend(self):
        """The loaded fastembed cross-encoder, built once; local files only when already cached."""
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        offline = bool(_model_files(self.cache_dir, self.name))
        return TextCrossEncoder(
            self.name,
            cache_dir=str(self.cache_dir),
            threads=self.threads,
            providers=["CPUExecutionProvider"],
            local_files_only=offline,
        )

    def scores(self, query: str, texts: list[str]) -> list[float]:
        """Score each text against the question; returns one float per text, in the same order."""
        if not texts:
            return []
        return [float(s) for s in self._backend.rerank(query, texts)]
