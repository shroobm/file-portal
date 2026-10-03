"""WHAT THIS FILE DOES: holds the converter's configuration. Paths.from_root builds every directory
the service uses under one root and Paths.ensure_exist creates them; Settings.load reads the
[conversion] table of a TOML file (defaults if the file is missing); DEFAULT_ROOT is ~/file-portal.
Used by the converter service, engines.py, fixity.py and others. Writes only directories.

Filesystem roots and tuning for the converter service. Mirrors linux-receiver/allocator/config.py --
all paths live under the receiving user's home directory on purpose (see docs/06-security-model.md).
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


# -- directory layout --
@dataclass(frozen=True)
class Paths:
    """The set of directories the converter uses, all derived from one root."""

    root: Path
    pipeline: Path
    convert_inbox: Path
    convert_scan_inbox: Path
    quarantine: Path
    anchor: Path
    staging: Path
    logs: Path
    vault_work: Path
    vault_bare: Path

    @classmethod
    def from_root(cls, root: Path) -> "Paths":
        """Build a Paths with every directory placed under root. Pure: creates nothing."""
        return cls(
            root=root,
            pipeline=root / "pipeline",
            convert_inbox=root / "pipeline" / "convert-inbox",
            convert_scan_inbox=root / "pipeline" / "convert-scan-inbox",
            # Shared with the allocator: one quarantine, outside every watched tree (the L1 fix).
            quarantine=root / "quarantine",
            # Anchor holds the immutable as-converted snapshot; staging is the transient export
            # queue Part 4 ships to the vault and then deletes.
            anchor=root / "library" / "anchor",
            staging=root / "library" / "staging",
            logs=root / "logs",
            # The Part 4 vault pair (Decision #4). Deliberately NOT in ensure_exist: the
            # exporter never initializes a repo -- exactly one side does, and that was manual.
            vault_work=root / "vault-work",
            vault_bare=root / "vault.git",
        )

    def ensure_exist(self) -> None:
        """Create the working directories (not the vault pair) if missing. Touches the disk."""
        for path in (
            self.convert_inbox,
            self.convert_scan_inbox,
            self.quarantine,
            self.anchor,
            self.staging,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)


# -- tuning settings --
@dataclass(frozen=True)
class Settings:
    """Conversion tuning values: text-yield floor, OCR resolution and language, image resolution."""

    min_chars_per_page: int
    ocr_dpi: int
    ocr_language: str
    image_dpi: int

    @classmethod
    def load(cls, path: Path) -> "Settings":
        """Read the [conversion] table of the TOML file at path; use defaults for anything absent.

        A missing or unreadable file is not an error. Returns a Settings.
        """
        # an unreadable file means "all defaults"
        try:
            with open(path, "rb") as f:
                raw = tomllib.load(f).get("conversion", {})
        except OSError:
            raw = {}
        return cls(
            min_chars_per_page=raw.get("min_chars_per_page", 100),
            ocr_dpi=raw.get("ocr_dpi", 300),
            ocr_language=raw.get("ocr_language", "eng"),
            image_dpi=raw.get("image_dpi", 150),
        )


# -- default location --
DEFAULT_ROOT = Path.home() / "file-portal"
