"""Bundle assembly: frontmatter, Obsidian link rewrite, manifest, atomic publish.

A bundle is a folder -- <name>/<name>.md + assets/ + manifest.json -- never a bare file. It is
assembled in a dot-prefixed temp directory and published by atomic rename, so a partial bundle
can never appear in anchor or staging. Same .part- invariant as the Windows transfer (W1) and
the allocator, extended one hop.
"""

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Inline image links, e.g. ![](x.png) or ![alt](/abs/path/x.png "title"). External URLs are
# left alone; everything else is rewritten to an Obsidian embed pointing into assets/.
_IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def rewrite_image_links(markdown: str) -> str:
    """Rewrite inline image links to Obsidian embeds: ![](…/img.png) -> ![[assets/img.png]].

    pymupdf4llm and pandoc both emit the (absolute) extraction path they were given; only the
    basename is meaningful once the bundle is assembled, and keeping the assets/ prefix keeps
    the embed resolvable as a plain relative path too.
    """

    def _replace(match: re.Match) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "data:")):
            return match.group(0)
        return f"![[assets/{Path(target).name}]]"

    return _IMAGE_LINK.sub(_replace, markdown)


def render_frontmatter(
    engine: str,
    lane: str,
    lane_reason: str,
    chars_per_page_detected: float | None,
    ocr: bool,
    ocr_dpi: int | None,
    converted_at: datetime,
    source_sha256: str,
) -> str:
    """YAML frontmatter stamped on every output -- OCR text is probabilistic, extracted text
    is not, and the vault must be able to tell them apart (Open Decision #3, 2026-07-09)."""
    lines = [
        "---",
        "conversion:",
        f"  engine: {engine}",
        f"  lane: {lane}",
        f"  lane_reason: {lane_reason}",
        "  chars_per_page_detected: "
        + ("~" if chars_per_page_detected is None else f"{chars_per_page_detected:.1f}"),
        f"  ocr: {'true' if ocr else 'false'}",
    ]
    if ocr_dpi is not None:
        lines.append(f"  ocr_dpi: {ocr_dpi}")
    lines += [
        f"  converted_at: {converted_at.isoformat(timespec='seconds')}",
        f"  source_sha256: {source_sha256}",
        "---",
        "",
    ]
    return "\n".join(lines)


def clamp_name(name: str, max_bytes: int = 80) -> str:
    """Clamp a bundle name to a filename byte budget.

    The binding constraint is Windows MAX_PATH on the consuming end (L15): the note travels
    to the vault as Inbox/<slug60>--<sha8>/<name>.md, and at 80 bytes that worst case is
    exactly 160 bytes vault-relative — inside the 260-char full-path limit with margin for
    the vault prefix. ext4's 255-byte component limit (the original 200-byte rationale, L13)
    holds a fortiori. Clamps on utf-8 bytes without splitting a codepoint.
    """
    if len(name.encode("utf-8")) <= max_bytes:
        return name
    clamped = name.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return clamped.rstrip(" .") or "untitled"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_path(dest: Path) -> Path:
    """Never overwrite an existing file or bundle of the same name -- append a " (n)" suffix,
    the allocator's default collision policy. Works for files ("a (1).pdf") and bundle
    directories ("a (1)") alike."""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    n = 1
    while True:
        candidate = dest.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def assemble(
    tmp_dir: Path,
    bundle_name: str,
    markdown: str,
    frontmatter: str,
    manifest: dict,
) -> None:
    """Write markdown (frontmatter + rewritten links) and manifest.json into the temp bundle.
    The engines already wrote assets/ into tmp_dir before this is called."""
    md_path = tmp_dir / f"{bundle_name}.md"
    md_path.write_text(frontmatter + rewrite_image_links(markdown), encoding="utf-8")
    (tmp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def publish(tmp_dir: Path, bundle_name: str, anchor: Path, staging: Path) -> tuple[Path, Path]:
    """Atomically publish the assembled temp bundle to anchor and staging.

    Staging gets a copy (built next to its destination, then renamed in); anchor gets the temp
    directory itself renamed in. Both renames are same-filesystem and atomic, so neither
    destination can ever hold a partial bundle.
    """
    anchor_dest = unique_path(anchor / bundle_name)
    staging_dest = unique_path(staging / bundle_name)

    # Distinct from the assembly temp dir (.part-<name>), which may itself live in staging.
    staging_tmp = staging / f".part-{bundle_name}.staging-copy"
    if staging_tmp.exists():
        shutil.rmtree(staging_tmp)
    shutil.copytree(tmp_dir, staging_tmp)
    os.rename(staging_tmp, staging_dest)
    os.rename(tmp_dir, anchor_dest)
    return anchor_dest, staging_dest


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
