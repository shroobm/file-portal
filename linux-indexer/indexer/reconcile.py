"""Reconcile the passage store to the vault's main tip -- the Index station's one operation.

Design (docs/11 Phase 3 passed 2026-07-19; built 2026-09-09 on Rab's go, OPEN-TASKS D7):

- SEPARATE CONSUMER. The exporter copies bytes and never reads them (Decision #5), so this is
  its own package and unit, fired by vault.git/hooks/post-update and a daily timer. The index
  gates nothing: no export, verdict or vault write ever waits on it.
- IDEMPOTENT, WHOLE-TREE. Every run lists every bundle at ONE commit and compares each to the
  store by its .md and manifest.json blob shas; nothing depends on a remembered "last tip", so
  a hand history rewrite cannot desynchronise it. Unchanged -> nothing. Body changed (a
  supersede rewrites the SAME path in place) -> that bundle's passages are replaced. Manifest
  changed only (a bless) -> the bundle row is rewritten without the model. Gone -> removed.
  Identity is the manifest's source_sha256 -- the exporter's own key, stable across supersede,
  rename and Desktop filing.
- REPORT-MODE. A bundle that breaks the contract (not exactly one .md, unreadable manifest, a
  sha vaulted twice) is refused and logged; the run still finishes the others and exits 1 so
  the unit shows red. Nothing is repaired or guessed (the exporter's "refusing to guess"). The
  index is rebuilt only on an explicit --rebuild.
- ONE WRITER AT A TIME. The hook and the timer can coincide; a file lock makes the second run
  wait for the first (blocking, so a push that lands mid-run is still picked up by the run
  that follows), and SQLite makes every bundle's change a transaction.
- ONE RECEIPT PER RUN THAT CHANGED SOMETHING, never per passage and none when the index already
  matched: the widget tails the last 60 receipt lines (receipts.rs) and MUSTER counts them.
  `bundle`/`note` ride on the receipt when exactly one bundle changed -- the steady-state
  shape (one export -> one push -> one hook -> one bundle) and what the widget's fallback
  phrase renders.
"""

import fcntl
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from indexer.config import Paths, Settings
from indexer.embed import Embedder, FastEmbedder, UnknownModel
from indexer.passages import split_passages, strip_frontmatter
from indexer.receipts import append_receipt
from indexer.store import Store, StoreMismatch
from indexer.vault import Vault, VaultError

logger = logging.getLogger("file-portal-indexer")

INDEXER_VERSION = "0.1.0"
LOCK_NAME = ".reconcile.lock"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def manifest_metadata(manifest: dict) -> dict:
    """Flatten the manifest keys worth carrying on every bundle (docs/15 §7 shapes as found at
    HEAD 2026-09-09). Scalars only, and absent stays absent: a manifest without `fidelity` is
    not a pass (exporter.py)."""
    fidelity = manifest.get("fidelity") or {}
    final = (fidelity.get("final") or {}).get("convert") or {}
    convert = fidelity.get("convert") or {}
    supersede = manifest.get("supersede") or {}
    blessed = manifest.get("blessed") or {}
    candidates = {
        "source": manifest.get("source"),
        "lane": manifest.get("lane"),
        "lane_reason": manifest.get("lane_reason"),
        "engine": manifest.get("engine"),
        "pages": manifest.get("pages"),
        "converter_version": manifest.get("converter_version"),
        "converted_at": manifest.get("converted_at"),
        "verdict": fidelity.get("verdict"),
        # D-1 (docs/15 §16): after a re-audit `final` bears the verdict; `convert` is history.
        "doc_survival": final.get("doc_survival", convert.get("doc_survival")),
        "blessed_by": blessed.get("by"),
        "supersede_reason": supersede.get("reason"),
        "supersede_from_verdict": supersede.get("from_verdict"),
    }
    return {k: v for k, v in candidates.items() if isinstance(v, (str, int, float, bool))}


def _fail(root: Path, tip: str | None, error: str) -> None:
    logger.error("INDEX-FAIL %s", error)
    fields = {"tip": tip[:8]} if tip else {}
    append_receipt(root, "index-failed", **fields, error=error[:200])


def reconcile(
    root: Path,
    settings: Settings,
    embedder: Embedder | None = None,
    rebuild: bool = False,
) -> int:
    paths = Paths.from_root(root)
    paths.ensure_exist()
    for note in settings.fallbacks:
        logger.warning("LEVER-FALLBACK %s (signed default applied)", note)
    vault = Vault(paths.vault_bare)
    if not vault.exists():
        _fail(paths.root, None, "vault bare repo missing")
        return 2
    with open(paths.index / LOCK_NAME, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # blocking: a coinciding run waits, never skips
        return _reconcile_locked(paths, vault, settings, embedder, rebuild)


def _reconcile_locked(paths, vault, settings, embedder, rebuild) -> int:
    tip = vault.tip()
    if tip is None:
        _fail(paths.root, None, "branch tip unresolvable")
        return 1

    store = Store(paths.index)
    if rebuild:
        for suffix in ("", "-wal", "-shm"):
            Path(str(store.db_path) + suffix).unlink(missing_ok=True)
        logger.info("INDEX-REBUILD %s emptied on request", store.db_path)
    try:
        embedder = embedder or FastEmbedder(settings.model, settings.threads, paths.models)
        store.open(
            embedder.name,
            embedder.dim,
            settings.passage_chars,
            settings.fts_tokenizer,
            INDEXER_VERSION,
        )
        identity = embedder.identity()
        bundles = vault.bundles(tip)
    except (StoreMismatch, VaultError, UnknownModel) as exc:
        _fail(paths.root, tip, str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 -- report-mode: the receipt is the record
        logger.exception("INDEX-FAIL")
        _fail(paths.root, tip, f"{type(exc).__name__}: {exc}")
        return 1

    known = store.all_bundles()
    counts = {"added": 0, "replaced": 0, "updated": 0, "removed": 0, "refused": 0, "unchanged": 0}
    changed: list[str] = []
    refused_shas: set[str] = set()
    live: set[str] = set()
    embed_s = 0.0

    parsed = []
    for bundle in bundles:
        try:
            manifest = json.loads(vault.blob(bundle.manifest_blob).decode("utf-8"))
            sha = manifest.get("source_sha256")
            if not isinstance(sha, str) or not _SHA256_RE.match(sha):
                raise ValueError("manifest has no 64-hex source_sha256")
        except (VaultError, ValueError, UnicodeDecodeError) as exc:
            counts["refused"] += 1
            logger.error("INDEX-REFUSE %s: %s", bundle.note, exc)
            continue
        parsed.append((bundle, manifest, sha))
    duplicated = {sha for sha, n in Counter(sha for _, _, sha in parsed).items() if n > 1}

    for bundle, manifest, sha in parsed:
        if sha in duplicated:
            counts["refused"] += 1
            refused_shas.add(sha)
            logger.error("INDEX-REFUSE %s: source_sha256 vaulted more than once", bundle.note)
            continue
        if bundle.md_blob is None:
            counts["refused"] += 1
            refused_shas.add(sha)
            logger.error(
                "INDEX-REFUSE %s: expected exactly one .md, found %s", bundle.note, bundle.md_names
            )
            continue
        common = {
            **manifest_metadata(manifest),
            "source_sha256": sha,
            "note": bundle.note,
            "md_name": bundle.md_name,
            "md_blob": bundle.md_blob,
            "manifest_blob": bundle.manifest_blob,
            "indexed_tip": tip[:8],
        }
        try:
            current = store.bundle_state(sha)
            same_body = current is not None and current.get("md_blob") == bundle.md_blob
            if (
                same_body
                and current.get("manifest_blob") == bundle.manifest_blob
                and current.get("note") == bundle.note
            ):
                counts["unchanged"] += 1
            elif same_body:
                n = store.rewrite_metadata(sha, common)
                counts["updated"] += 1
                changed.append(bundle.note)
                logger.info("INDEX-UPDATE %s metadata rewritten (%d passages kept)", bundle.note, n)
            else:
                body = vault.blob(bundle.md_blob).decode("utf-8", errors="replace")
                passages = split_passages(
                    strip_frontmatter(body), settings.passage_chars, settings.passage_max_chars
                )
                started = time.monotonic()
                embeddings = embedder.embed_passages([p.text for p in passages])
                embed_s += time.monotonic() - started
                store.replace_bundle(sha, common, passages, embeddings)
                counts["replaced" if current else "added"] += 1
                changed.append(bundle.note)
                logger.info("INDEXED %s -> %d passages", bundle.note, len(passages))
        except Exception:  # noqa: BLE001 -- one bad bundle must not cost the others
            counts["refused"] += 1
            refused_shas.add(sha)
            logger.exception("INDEX-REFUSE %s", bundle.note)
            continue
        live.add(sha)

    for sha, entry in known.items():
        if sha in live or sha in refused_shas:
            continue
        try:
            n = store.remove_bundle(sha)
        except Exception:  # noqa: BLE001
            counts["refused"] += 1
            logger.exception("INDEX-REFUSE removal of %s", sha[:16])
            continue
        counts["removed"] += 1
        changed.append(entry["note"])
        logger.info("INDEX-REMOVED %s (%d passages)", entry["note"], n)

    total = store.count()
    result = "fail" if counts["refused"] else "pass"
    store.set_meta(
        tip=tip,
        reconciled_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        result=result,
        passages=str(total),
        bundles=str(len(live) + len(refused_shas & set(known))),
        model_identity=identity,
        levers=settings.effective(),
        lever_fallbacks=list(settings.fallbacks),
    )
    store.close()

    if not any(counts[k] for k in ("added", "replaced", "updated", "removed", "refused")):
        logger.info(
            "INDEX-SKIP tip %s already indexed (%d bundles, %d passages)", tip[:8], len(live), total
        )
        return 0

    fields: dict = {"result": result, "tip": tip[:8]}
    if len(changed) == 1:
        fields["bundle"] = changed[0].rsplit("/", 1)[-1]
        fields["note"] = changed[0]
    fields.update(bundles=len(live), **counts, passages=total)
    if embed_s:
        fields["embed_s"] = round(embed_s, 1)
    fields.update(
        model=embedder.name,
        model_sha=str(identity.get("model_sha256", ""))[:16],
        passage_chars=settings.passage_chars,
        passage_max_chars=settings.passage_max_chars,
        fts_tokenizer=settings.fts_tokenizer,
        threads=settings.threads,
    )
    if settings.fallbacks:
        fields["lever_fallbacks"] = ", ".join(settings.fallbacks)
    append_receipt(paths.root, "indexed", **fields)
    return 1 if counts["refused"] else 0
