"""Filesystem roots and levers for the indexer. Mirrors linux-converter/converter/config.py --
all paths live under the receiving user's home directory on purpose (see docs/06-security-model.md).

The index is DERIVED data: everything under <root>/index can be deleted and rebuilt from the
vault in minutes (docs/11 Phase 3: "fully reversible, must not gate anything"). It therefore
lives beside the vault, never inside it -- the vault holds notes, not machine records
(linux-converter/converter/exporter.py, the receipts decision).
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path
    index: Path
    models: Path
    logs: Path
    vault_bare: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        return cls(
            root=root,
            # index.sqlite (passages, embeddings, keyword index, run record) lives here.
            index=root / "index",
            # Embedding/reranker model files, fetched once from Hugging Face by fastembed and
            # kept here so they survive reboots (fastembed's own default is /tmp) and so the
            # whole station's footprint is under ~/file-portal (docs/06 framing).
            models=root / "index" / "models",
            logs=root / "logs",
            # Read-only from here. Deliberately NOT in ensure_exist: the indexer never
            # initializes or repairs the vault -- exactly one side does, and that was manual
            # (Decision #4). A missing vault is a loud failure, not a bootstrap.
            vault_bare=root / "vault.git",
        )

    def ensure_exist(self) -> None:
        for path in (self.index, self.models, self.logs):
            path.mkdir(parents=True, exist_ok=True)


DEFAULT_ROOT = Path.home() / "file-portal"

# Signed defaults and admissible ranges (docs/18 modularity gate): key -> (default, low, high).
# A lever value that is missing, unparseable or out of range falls back to the default and is
# NAMED in Settings.fallbacks so the run can report it -- never silently ignored. The ranges
# are documented beside each key in config/indexer.toml; keep the two in step.
_INT_LEVERS = {
    "passage_chars": (800, 200, 2000),
    "passage_max_chars": (1200, 200, 4000),
    "threads": (4, 1, 12),
    "top_k": (5, 1, 50),
    "serve_port": (8765, 1024, 65535),
}
# String levers: key -> (default, menu or None for any non-empty string).
_STR_LEVERS = {
    "model": ("sentence-transformers/all-MiniLM-L6-v2", None),
    "query_mode": ("hybrid", ("hybrid", "vector", "keyword")),
    "rerank": ("off", None),
    "fts_tokenizer": ("unicode61", ("unicode61", "trigram")),
}


@dataclass(frozen=True)
class Settings:
    passage_chars: int
    passage_max_chars: int
    threads: int
    top_k: int
    serve_port: int
    model: str
    query_mode: str
    rerank: str
    fts_tokenizer: str
    fallbacks: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            with open(path, "rb") as f:
                raw = tomllib.load(f).get("index", {})
        except OSError:
            raw = {}
        values: dict = {}
        fallbacks = []
        for key, (default, low, high) in _INT_LEVERS.items():
            value = raw.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                fallbacks.append(f"{key}={value!r}->{default}")
                value = default
            values[key] = value
        for key, (default, menu) in _STR_LEVERS.items():
            value = raw.get(key, default)
            if (
                not isinstance(value, str)
                or not value.strip()
                or (menu is not None and value not in menu)
            ):
                fallbacks.append(f"{key}={value!r}->{default}")
                value = default
            values[key] = value.strip()
        if values["passage_max_chars"] < values["passage_chars"]:
            fallbacks.append(
                f"passage_max_chars={values['passage_max_chars']}->{values['passage_chars']}"
            )
            values["passage_max_chars"] = values["passage_chars"]
        return cls(**values, fallbacks=tuple(fallbacks))

    def effective(self) -> dict:
        """The values a run actually used -- printed, never the defaults (docs/18 step 3)."""
        return {key: getattr(self, key) for key in (*_INT_LEVERS, *_STR_LEVERS)}


def lever_range(key: str) -> tuple[int, int]:
    """The admissible range of an integer lever, for CLI overrides to honour the same bounds."""
    _, low, high = _INT_LEVERS[key]
    return low, high


def lever_menu(key: str) -> tuple[str, ...]:
    return tuple(_STR_LEVERS[key][1] or ())
