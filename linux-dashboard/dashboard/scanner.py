"""WHAT THIS FILE DOES: scan(paths, settings) reads the sorted/ folder tree (read-only, no writes)
and returns, per enabled category, a newest-first list of Entry records (path, category, mtime,
and for photos a yyyy-mm label). Callers are the dashboard UI code (not shown in this file).

Walks ~/file-portal/sorted/ into an in-memory model the UI can render.

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

# -- pattern for a valid "yyyy-mm" date-filter string --
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


# -- the record produced for each file found --
@dataclass(frozen=True)
class Entry:
    """One sorted file: its path, its category, its modified time, and (photos only) yyyy-mm."""

    path: Path
    category: str
    mtime: float
    year_month: str | None = None  # "yyyy-mm", photos only


# -- public entry point --
def scan(paths: Paths, settings: Settings) -> dict[str, list[Entry]]:
    """Returns {category: [Entry, ...]} for every category enabled in settings."""
    result: dict[str, list[Entry]] = {}
    # Photos use the date-bucketed scan; every other category uses the flat recursive scan.
    # A missing category folder yields an empty list.
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


# -- per-category scanners (read-only filesystem walks) --
def _scan_flat(category_root: Path, category: str) -> list[Entry]:
    """List every file under category_root (recursive) as an Entry, newest first. Reads file stats."""
    entries = []
    for file_path in category_root.rglob("*"):
        if file_path.is_file():
            entries.append(
                Entry(path=file_path, category=category, mtime=file_path.stat().st_mtime)
            )
    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries


def _scan_photos(category_root: Path, settings: Settings) -> list[Entry]:
    """List photos in <root>/<yyyy>/<mm>/ folders within the optional date range, newest first.

    Inputs: the photos folder and settings (photo_date_from / photo_date_to). Reads file stats.
    """
    # A bound is used only if it looks like yyyy-mm; anything else means no bound.
    date_from = (
        settings.photo_date_from if _YEAR_MONTH_RE.match(settings.photo_date_from or "") else None
    )
    date_to = settings.photo_date_to if _YEAR_MONTH_RE.match(settings.photo_date_to or "") else None

    entries = []
    # Walk four-digit year folders, then two-digit month folders; skip months outside the range
    # (yyyy-mm strings compare correctly as text).
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
