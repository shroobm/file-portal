"""WHAT THIS FILE DOES: defines the folder layout the allocator works in. Paths holds the
five directories (root, inbox, sorted, logs, quarantine); DEFAULT_ROOT is the starting root.
It only builds paths and creates directories (ensure_exist); it reads nothing. Used by main.py.

Filesystem roots and defaults for the allocator. All paths live under the
receiving user's home directory on purpose -- see docs/06-security-model.md."""

from dataclasses import dataclass
from pathlib import Path


# -- the set of directories the allocator uses --
@dataclass(frozen=True)
class Paths:
    """Immutable bundle of the allocator's directories: root, inbox, sorted, logs, quarantine."""

    root: Path
    inbox: Path
    sorted: Path
    logs: Path
    quarantine: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        """Build a Paths from one root directory; each child is a fixed-name subfolder of it."""
        return cls(
            root=root,
            inbox=root / "inbox",
            sorted=root / "sorted",
            logs=root / "logs",
            quarantine=root / "quarantine",
        )

    def ensure_exist(self) -> None:
        """Create inbox, sorted, logs and quarantine (and parents) on disk if missing."""
        for path in (self.inbox, self.sorted, self.logs, self.quarantine):
            path.mkdir(parents=True, exist_ok=True)


# -- default location --
DEFAULT_ROOT = Path.home() / "file-portal"
