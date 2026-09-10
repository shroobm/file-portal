"""Status CLI: is the index in step with the vault? One JSON document, no model load, exit 0.
`in_sync` is true only when the last run reconciled to the vault's CURRENT tip and refused
nothing; anything else is false or null (docs/18: liveness is proven, never remembered --
the tip comparison is made now, against the bare repo, not read back from memory)."""

import argparse
import json
import sys
from pathlib import Path

from indexer.config import DEFAULT_ROOT, Paths
from indexer.store import Store
from indexer.vault import Vault


def run(root: Path) -> dict:
    paths = Paths.from_root(root)
    vault = Vault(paths.vault_bare)
    vault_tip = vault.tip() if vault.exists() else None
    store = Store(paths.index)
    if not store.exists():
        return {
            "available": False,
            "reason": f"no index at {paths.index}",
            "vault_tip": vault_tip[:8] if vault_tip else None,
        }
    store.open_readonly()
    try:
        meta = store.meta()
        passages = store.count()
    finally:
        store.close()
    index_tip = meta.get("tip")
    identity = json.loads(meta["model_identity"]) if "model_identity" in meta else {}
    return {
        "available": True,
        "index": str(store.db_path),
        "index_tip": index_tip[:8] if index_tip else None,
        "vault_tip": vault_tip[:8] if vault_tip else None,
        "in_sync": bool(
            index_tip and vault_tip and index_tip == vault_tip and meta.get("result") == "pass"
        ),
        "last_result": meta.get("result"),
        "reconciled_at": meta.get("reconciled_at"),
        "bundles": int(meta["bundles"]) if "bundles" in meta else None,
        "passages": passages,
        "model": meta.get("model"),
        "model_sha": str(identity.get("model_sha256", ""))[:16] or None,
        "levers": json.loads(meta["levers"]) if "levers" in meta else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="File Portal index status (JSON on stdout)")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    print(json.dumps(run(parser.parse_args().root), ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
