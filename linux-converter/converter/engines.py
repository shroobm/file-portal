"""Conversion engines: the text-layer probe and the PyMuPDF4LLM / Pandoc calls.

Dispatch is first-match over extension patterns, the same shape as the allocator's
rules.py -- one routing idiom in the repo, not two.
"""

# pymupdf.layout MUST be imported before pymupdf4llm: pymupdf4llm decides at import time
# whether layout mode -- and with it the OCR parameters (use_ocr/force_ocr/ocr_dpi) -- is
# active. If layout arrives second, auto-OCR silently never fires on image-only pages.
# (pymupdf4llm 1.28.0 hard-depends on pymupdf_layout and sets _use_layout itself, but the
# ordering is kept as insurance against older or partially-installed environments.)
import pymupdf.layout  # noqa: F401  (import order is load-bearing -- see comment above)
import pymupdf4llm
from pymupdf4llm.helpers.document_layout import OCRMode

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from converter.config import Settings


@dataclass(frozen=True)
class Engine:
    name: str
    patterns: list[str]


# First match wins, same as RuleSet.resolve in linux-receiver/allocator/rules.py.
ENGINES = [
    Engine(name="pymupdf4llm", patterns=["*.pdf", "*.epub"]),
    Engine(name="pandoc", patterns=["*.docx"]),
]


def resolve_engine(filename: str) -> Engine | None:
    for engine in ENGINES:
        if any(fnmatch.fnmatch(filename.lower(), pattern) for pattern in engine.patterns):
            return engine
    return None


def probe_chars_per_page(path: Path) -> float:
    """Average extractable text characters per page -- the pre-flight text-layer test.

    A born-digital PDF probes in the thousands; a pure scan probes at or near zero. Raises
    (pymupdf.FileDataError etc.) on files that cannot be opened at all -- callers quarantine.
    """
    with pymupdf.open(path) as doc:
        page_count = doc.page_count or 1
        total = sum(len(page.get_text()) for page in doc)
    return total / page_count


def chars_per_page_of_markdown(markdown: str, page_count: int) -> float:
    """Post-conversion yield check for the terminal Scan lane."""
    return len(markdown) / max(page_count, 1)


def page_count(path: Path) -> int:
    with pymupdf.open(path) as doc:
        return doc.page_count or 1


def run_pymupdf(src: Path, assets_dir: Path, lane: str, settings: Settings) -> str:
    """Convert a .pdf/.epub to markdown, writing images into assets_dir.

    Lane flags, mapped onto pymupdf4llm 1.28 layout-mode reality (verified against
    document_layout.make_ocr_decision, 2026-07-10): OCR is need-based and automatic in every
    mode -- image-only pages get OCR'd even on the Clean lane, and no flag forces OCR over a
    genuine non-OCR text layer. What the modes actually control is prior OCR spans:

    - Clean = SELECT_KEEP_OLD: trust existing text (including previous OCR), auto-OCR only
      pages that need it.
    - Scan = FORCE_DROP_OLD + ocr_dpi: discard prior OCR text and redo it at our resolution,
      and raise if no OCR engine is available. This -- not the plan doc's force_ocr=True,
      which maps to FORCE_KEEP_OLD and would KEEP a bad prior OCR layer -- is the honest
      1.28 spelling of "force OCR".

    Image links in the returned markdown carry whatever path pymupdf4llm was given --
    bundle.rewrite_image_links normalizes them afterwards.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {
        "write_images": True,
        "image_path": str(assets_dir),
        "dpi": settings.image_dpi,
    }
    if lane == "scan":
        kwargs.update(
            use_ocr=OCRMode.FORCE_DROP_OLD,
            ocr_dpi=settings.ocr_dpi,
            ocr_language=settings.ocr_language,
        )
    else:
        kwargs["use_ocr"] = OCRMode.SELECT_KEEP_OLD
    return pymupdf4llm.to_markdown(str(src), **kwargs)


def run_pandoc(src: Path, assets_dir: Path) -> str:
    """Convert a .docx to markdown via Pandoc, extracting embedded media into assets_dir.

    gfm output rather than pandoc-native markdown: Obsidian reads gfm, and it avoids pandoc's
    attribute syntax leaking into the vault. --extract-media nests files under a media/
    subfolder; they are flattened into assets_dir so every bundle has one assets layout.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "pandoc",
            "-f",
            "docx",
            "-t",
            "gfm",
            "--extract-media",
            str(assets_dir),
            str(src),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc exited {result.returncode}: {result.stderr.strip()[:500]}")

    media = assets_dir / "media"
    if media.is_dir():
        for item in media.iterdir():
            item.rename(assets_dir / item.name)
        media.rmdir()
    return result.stdout
