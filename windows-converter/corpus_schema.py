"""The portal schema's live half — docs/35 describes the tree, this reads it.

The division of labour is docs/33 §2.1's, signed: docs/35 (curated prose, in the chat corpus,
citable) explains what every folder and file IS; this module reports what is IN them right now,
as DATA that the surface renders verbatim. The model never sees this output and never speaks
it — an assistant that restated a live listing would be a projection-law violation wearing a
helpful face.

Stdlib only. Read-only. Bounded output — a listing is a glance, not a dump.
"""
from __future__ import annotations

from pathlib import Path

CAP = 40  # names per folder; past this a listing stops being a glance


def _names(root: Path, sub: str, pattern: str = "*") -> list[str] | None:
    """Sorted entry names, dotfiles excluded, capped. None = UNREAD (the folder could not be
    listed), never [] — absence of a reading is not a reading of absence (SYM-031)."""
    try:
        names = sorted(p.name for p in (root / sub).glob(pattern)
                       if not p.name.startswith("."))
    except OSError:
        return None
    return names[:CAP]


def _read(root: Path, name: str) -> str | None:
    try:
        return (root / name).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def tree_snapshot(pipe: Path) -> dict:
    """One glance at the pipeline root, keyed the way docs/35 §2–§3 name things."""
    return {
        "anchor": _names(pipe, "anchor"),
        "held": _names(pipe, "held"),
        "pending": _names(pipe, "pending"),
        "drop": _names(pipe, "drop", "*.pdf"),
        "drop_done": _names(pipe, "drop/done", "*.pdf"),
        "drop_failed": _names(pipe, "drop/failed", "*.pdf"),
        "levers": {
            "analyst_mode": _read(pipe, "analyst-mode.txt"),
            "audit_mode": _read(pipe, "audit-mode.txt"),
            "chunk_batch": _read(pipe, "chunk-batch.txt"),
        },
        "markers": {
            "gpu_lock": _read(pipe, ".gpu-lock"),        # a busy SIGNAL, not a lock (SYM-032)
            "chat_hold": (pipe / "chat-hold.json").is_file(),
        },
    }
