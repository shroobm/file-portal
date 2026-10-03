"""WHAT THIS FILE DOES: holds the dashboard's folder layout (Paths), its user preferences (Settings)
and the default locations. Settings.load() reads ~/.config/file-portal/dashboard.toml (creating it
with defaults if missing); Settings.save() writes it back. Used by main.py, scanner.py and the
widgets.

Filesystem roots and persisted settings for the dashboard.

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

# -- default locations and the list of known categories --
DEFAULT_ROOT = Path.home() / "file-portal"
CONFIG_PATH = Path.home() / ".config" / "file-portal" / "dashboard.toml"

ALL_CATEGORIES = ["photos", "documents", "code", "archive", "misc"]


# -- directory layout --
@dataclass(frozen=True)
class Paths:
    """The file-portal root folder and its sorted/ subfolder (read-only record)."""

    root: Path
    sorted: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        """Build a Paths from a root folder; sorted is root/"sorted". No filesystem access."""
        return cls(root=root, sorted=root / "sorted")


# -- user-adjustable preferences, persisted to dashboard.toml --
@dataclass
class Settings:
    """Window size, refresh interval, category and photo-date filters, and the serve port."""

    window_width: int = 1000
    window_height: int = 700
    refresh_interval_seconds: int = 30
    enabled_categories: list[str] = field(default_factory=lambda: list(ALL_CATEGORIES))
    photo_date_from: str = ""  # "yyyy-mm", empty = no lower bound
    photo_date_to: str = ""  # "yyyy-mm", empty = no upper bound
    serve_port: int = (
        8766  # dashboard.serve's loopback port (S214 E16); the indexer's serve takes 8765
    )

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Settings":
        """Read Settings from the TOML file at path. If the file is missing, create it with defaults.

        Unknown keys in the file are ignored. Side effect: may write the file (via save).
        """
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        with path.open("rb") as f:
            data = tomllib.load(f)
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self, path: Path = CONFIG_PATH) -> None:
        """Write the settings to path as TOML, creating parent folders. Uses tomli_w if installed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if tomli_w is not None:
            path.write_bytes(tomli_w.dumps(asdict(self)).encode("utf-8"))
        else:
            _write_toml_fallback(path, asdict(self))


# -- fallback TOML writer, used when tomli_w is not installed --
def _write_toml_fallback(path: Path, data: dict) -> None:
    """Write a flat dict (bool, number, list of strings, or string values) to path as TOML text."""
    lines = []
    # One "key = value" line per entry; strings get their double quotes escaped.
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
