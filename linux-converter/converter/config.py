"""Filesystem roots for the converter service. Mirrors linux-receiver/allocator/config.py --
all paths live under the receiving user's home directory on purpose (see docs/06-security-model.md).
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path
    convert_inbox: Path
    logs: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        return cls(
            root=root,
            convert_inbox=root / "pipeline" / "convert-inbox",
            logs=root / "logs",
        )

    def ensure_exist(self) -> None:
        for path in (self.convert_inbox, self.logs):
            path.mkdir(parents=True, exist_ok=True)


DEFAULT_ROOT = Path.home() / "file-portal"
