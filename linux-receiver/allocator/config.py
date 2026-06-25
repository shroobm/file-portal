"""Filesystem roots and defaults for the allocator. All paths live under the
receiving user's home directory on purpose -- see docs/06-security-model.md."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path
    inbox: Path
    sorted: Path
    logs: Path
    quarantine: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        return cls(
            root=root,
            inbox=root / "inbox",
            sorted=root / "sorted",
            logs=root / "logs",
            quarantine=root / "inbox" / "quarantine",
        )

    def ensure_exist(self) -> None:
        for path in (self.inbox, self.sorted, self.logs, self.quarantine):
            path.mkdir(parents=True, exist_ok=True)


DEFAULT_ROOT = Path.home() / "file-portal"
