"""Filesystem roots and persisted settings for the dashboard.

Mirrors the shape of linux-receiver/allocator/config.py: a frozen Paths dataclass for the
file-portal directory layout, plus a separate Settings dataclass for user-adjustable dashboard
preferences (window size, refresh interval, filters) persisted to dashboard.toml.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import tomli_w
except ModuleNotFoundError:  # pragma: no cover - see requirements.txt
    tomli_w = None

DEFAULT_ROOT = Path.home() / "file-portal"
CONFIG_PATH = Path.home() / ".config" / "file-portal" / "dashboard.toml"

ALL_CATEGORIES = ["photos", "documents", "code", "archive", "misc"]


@dataclass(frozen=True)
class Paths:
    root: Path
    sorted: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        return cls(root=root, sorted=root / "sorted")


@dataclass
class Settings:
    window_width: int = 1000
    window_height: int = 700
    refresh_interval_seconds: int = 30
    enabled_categories: list[str] = field(default_factory=lambda: list(ALL_CATEGORIES))
    photo_date_from: str = ""  # "yyyy-mm", empty = no lower bound
    photo_date_to: str = ""  # "yyyy-mm", empty = no upper bound

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        with path.open("rb") as f:
            data = tomllib.load(f)
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if tomli_w is not None:
            path.write_bytes(tomli_w.dumps(asdict(self)).encode("utf-8"))
        else:
            _write_toml_fallback(path, asdict(self))


def _write_toml_fallback(path: Path, data: dict) -> None:
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif isinstance(value, list):
            items = ", ".join(f'"{v}"' for v in value)
            lines.append(f"{key} = [{items}]")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
    path.write_text("\n".join(lines) + "\n")
