"""WHAT THIS FILE DOES: reads config/rules.toml and decides which folder a file belongs in.
Entry points: RuleSet.load(path) parses the TOML file; RuleSet.resolve(category, filename)
returns the destination folder (relative, with {yyyy}/{mm}/{dd} filled in from local time).
It reads one file and writes nothing. Called by main.py on every file event.

Loads config/rules.toml and resolves an incoming file to a destination path.

Rules are re-read on every event (see main.py) so editing rules.toml takes effect without a
service restart -- see docs/05-allocation-rules.md.
"""

import fnmatch
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# -- data shapes for the parsed rules file --
@dataclass
class Rule:
    """One [[rule]] entry: files in a category matching any glob pattern go to the template folder."""

    category: str
    patterns: list[str]
    destination_template: str


@dataclass
class Defaults:
    """The [defaults] table: fallback folder, collision policy and size limit in MB."""

    unmatched_destination: str
    on_collision: str
    max_file_size_mb: int


@dataclass
class RuleSet:
    """The whole parsed rules file: one Defaults plus an ordered list of Rule entries."""

    defaults: Defaults
    rules: list[Rule]

    # -- loading and matching --
    @classmethod
    def load(cls, path: Path) -> "RuleSet":
        """Parse the TOML file at path into a RuleSet (missing defaults get built-in values)."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        defaults_raw = data.get("defaults", {})
        defaults = Defaults(
            unmatched_destination=defaults_raw.get("unmatched_destination", "sorted/misc"),
            on_collision=defaults_raw.get("on_collision", "rename"),
            max_file_size_mb=defaults_raw.get("max_file_size_mb", 2048),
        )

        # One Rule per [[rule]] table in the file, in file order.
        rules = [
            Rule(
                category=r["category"],
                patterns=r["match"],
                destination_template=r["destination"],
            )
            for r in data.get("rule", [])
        ]

        return cls(defaults=defaults, rules=rules)

    def resolve(self, category: str, filename: str) -> str:
        """Return the relative destination directory (template tokens expanded) for a file."""
        # First rule whose category equals and whose glob matches the filename wins.
        for rule in self.rules:
            if rule.category != category:
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in rule.patterns):
                return self._expand(rule.destination_template)
        return self._expand(self.defaults.unmatched_destination)

    @staticmethod
    def _expand(template: str) -> str:
        """Fill {yyyy}, {mm}, {dd} in a destination template with today's local date."""
        # LOCAL time on purpose: {yyyy}/{mm}/{dd} name the folders a human browses, so they must
        # match the day HE dropped the file, not UTC's. A newer ruff flags this as DTZ005 ("naive
        # datetime"); do NOT satisfy it by passing tz=UTC -- east of Greenwich that silently files
        # evening drops under tomorrow's date. If the rule must be silenced, silence the rule.
        now = datetime.now()  # noqa: DTZ005
        return template.format(
            yyyy=now.strftime("%Y"), mm=now.strftime("%m"), dd=now.strftime("%d")
        )
