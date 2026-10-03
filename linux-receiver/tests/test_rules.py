"""WHAT THIS FILE DOES: pytest tests for allocator/rules.py. Writes a sample rules.toml to a
temporary folder, loads it with RuleSet.load and checks resolve(): glob matching, category
matching, first-rule-wins, fallback destination, date tokens and built-in defaults.

Unit tests for allocator/rules.py: glob matching, date tokens, defaults."""

from datetime import datetime
from pathlib import Path

from allocator.rules import RuleSet

# -- test fixture: a sample rules file and a loader --
FULL_RULES = """
[defaults]
unmatched_destination = "sorted/misc"
on_collision = "rename"
max_file_size_mb = 10

[[rule]]
category = "documents"
match = ["*.pdf", "*.txt"]
destination = "sorted/documents"

[[rule]]
category = "photos"
match = ["*.jpg", "*.png"]
destination = "sorted/photos/{yyyy}/{mm}"

[[rule]]
category = "code"
match = ["*.zip"]
destination = "sorted/code/archives"

[[rule]]
category = "code"
match = ["*"]
destination = "sorted/code/inbox"
"""


def load(tmp_path: Path, text: str = FULL_RULES) -> RuleSet:
    """Write text to tmp_path/rules.toml and return the RuleSet loaded from it."""
    rules_path = tmp_path / "rules.toml"
    rules_path.write_text(text)
    return RuleSet.load(rules_path)


# -- resolve() behaviour --
def test_glob_match_routes_to_rule_destination(tmp_path):
    """Files matching a rule's glob in its category go to that rule's destination."""
    rules = load(tmp_path)
    assert rules.resolve("documents", "report.pdf") == "sorted/documents"
    assert rules.resolve("documents", "notes.txt") == "sorted/documents"


def test_category_must_match_not_just_pattern(tmp_path):
    """A matching glob in the wrong category does not count; the default destination is used."""
    rules = load(tmp_path)
    # A .pdf dropped on the photos portal does not match the documents rule.
    assert rules.resolve("photos", "report.pdf") == "sorted/misc"


def test_first_matching_rule_wins(tmp_path):
    """With two rules for one category, the earlier matching one is chosen."""
    rules = load(tmp_path)
    assert rules.resolve("code", "src.zip") == "sorted/code/archives"
    assert rules.resolve("code", "main.py") == "sorted/code/inbox"


def test_unmatched_falls_back_to_default_destination(tmp_path):
    """No matching pattern or an unknown category resolves to sorted/misc."""
    rules = load(tmp_path)
    assert rules.resolve("documents", "movie.mkv") == "sorted/misc"
    assert rules.resolve("nonexistent-category", "anything.bin") == "sorted/misc"


def test_date_tokens_expand_to_current_date(tmp_path):
    """{yyyy} and {mm} in a destination become today's local year and month."""
    rules = load(tmp_path)
    now = datetime.now()
    expected = f"sorted/photos/{now.strftime('%Y')}/{now.strftime('%m')}"
    assert rules.resolve("photos", "pic.jpg") == expected


def test_defaults_applied_when_sections_missing(tmp_path):
    """An empty rules file loads with the built-in defaults and no rules."""
    rules = load(tmp_path, "")
    assert rules.defaults.unmatched_destination == "sorted/misc"
    assert rules.defaults.on_collision == "rename"
    assert rules.defaults.max_file_size_mb == 2048
    assert rules.rules == []
