"""WHAT THIS FILE DOES: reports what is currently inside the pipeline root's folders and lever files. The one
entry point is tree_snapshot(pipe), which returns a dict of capped folder listings (anchor, held, pending, drop,
drop/done, drop/failed), the text of three lever files, and two marker readings. It only reads the disk (no
writes) and a failed read comes back as None. Callers are not named in this file (purpose of the callers not
evident from the code); the docstring below says the surface renders the result as data.

The portal schema's live half — docs/35 describes the tree, this reads it.

The division of labour is docs/33 §2.1's, signed: docs/35 (curated prose, in the chat corpus,
citable) explains what every folder and file IS; this module reports what is IN them right now,
as DATA that the surface renders verbatim. The model never sees this output and never speaks
it — an assistant that restated a live listing would be a projection-law violation wearing a
helpful face.

Stdlib only. Read-only. Bounded output — a listing is a glance, not a dump.
"""
from __future__ import annotations

from pathlib import Path

# -- constants --
CAP = 40  # names per folder; past this a listing stops being a glance


# -- small readers: list a folder, read a lever file --
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
    """Return the stripped UTF-8 text of root/name, or None if the file cannot be read. Read-only."""
    try:
        return (root / name).read_text(encoding="utf-8").strip()
    except OSError:
        return None


# -- the public snapshot --
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
