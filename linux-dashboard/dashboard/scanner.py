"""Walks ~/file-portal/sorted/ into an in-memory model the UI can render.

Layout assumptions come from linux-receiver/config/rules.toml (see docs/05-allocation-rules.md):
- "photos" is the only category with date-token destinations: sorted/photos/{yyyy}/{mm}/...
- every other category (documents, code, archive, misc) is a flat-ish tree directly under
  sorted/<category>/...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from dashboard.config import Paths, Settings

_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class Entry:
    path: Path
    category: str
    mtime: float
    year_month: str | None = None  # "yyyy-mm", photos only


def scan(paths: Paths, settings: Settings) -> dict[str, list[Entry]]:
    """Returns {category: [Entry, ...]} for every category enabled in settings."""
    result: dict[str, list[Entry]] = {}
    for category in settings.enabled_categories:
        category_root = paths.sorted / category
        if not category_root.is_dir():
            result[category] = []
            continue
        if category == "photos":
            result[category] = _scan_photos(category_root, settings)
        else:
            result[category] = _scan_flat(category_root, category)
    return result


def _scan_flat(category_root: Path, category: str) -> list[Entry]:
    entries = []
    for file_path in category_root.rglob("*"):
        if file_path.is_file():
            entries.append(
                Entry(path=file_path, category=category, mtime=file_path.stat().st_mtime)
            )
    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries


def _scan_photos(category_root: Path, settings: Settings) -> list[Entry]:
    date_from = (
        settings.photo_date_from if _YEAR_MONTH_RE.match(settings.photo_date_from or "") else None
    )
    date_to = settings.photo_date_to if _YEAR_MONTH_RE.match(settings.photo_date_to or "") else None

    entries = []
    for year_dir in sorted(category_root.glob("[0-9][0-9][0-9][0-9]")):
        if not year_dir.is_dir():
            continue
        for month_dir in sorted(year_dir.glob("[0-9][0-9]")):
            if not month_dir.is_dir():
                continue
            year_month = f"{year_dir.name}-{month_dir.name}"
            if date_from and year_month < date_from:
                continue
            if date_to and year_month > date_to:
                continue
            for file_path in month_dir.iterdir():
                if file_path.is_file():
                    entries.append(
                        Entry(
                            path=file_path,
                            category="photos",
                            mtime=file_path.stat().st_mtime,
                            year_month=year_month,
                        )
                    )
    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries
