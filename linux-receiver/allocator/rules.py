"""Loads config/rules.toml and resolves an incoming file to a destination path.

Rules are re-read on every event (see main.py) so editing rules.toml takes effect without a
service restart -- see docs/05-allocation-rules.md.
"""

import fnmatch
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Rule:
    category: str
    patterns: list[str]
    destination_template: str


@dataclass
class Defaults:
    unmatched_destination: str
    on_collision: str
    max_file_size_mb: int


@dataclass
class RuleSet:
    defaults: Defaults
    rules: list[Rule]

    @classmethod
    def load(cls, path: Path) -> "RuleSet":
        with open(path, "rb") as f:
            data = tomllib.load(f)

        defaults_raw = data.get("defaults", {})
        defaults = Defaults(
            unmatched_destination=defaults_raw.get("unmatched_destination", "sorted/misc"),
            on_collision=defaults_raw.get("on_collision", "rename"),
            max_file_size_mb=defaults_raw.get("max_file_size_mb", 2048),
        )

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
        for rule in self.rules:
            if rule.category != category:
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in rule.patterns):
                return self._expand(rule.destination_template)
        return self._expand(self.defaults.unmatched_destination)

    @staticmethod
    def _expand(template: str) -> str:
        now = datetime.now()
        return template.format(
            yyyy=now.strftime("%Y"), mm=now.strftime("%m"), dd=now.strftime("%d")
        )
