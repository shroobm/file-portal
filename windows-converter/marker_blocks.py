"""J24 — the block records that today's convert computes and then throws away (signed 2026-09-01).

A drop-in for `marker_single.exe` on the argv this converter actually sends it, plus one extra
artifact: `<stem>.blocks.json`, one record per block with its ABSOLUTE page, its polygon and its
bbox. It exists because `marker_single --output_format markdown` builds a full block tree for
every page and then discards all of it, and three open items are blocked on exactly that
geometry:

  * SYM-053 — a page "looks covered" because an asset reference exists, but the asset is blank
    paper and a hand-drawn diagram's words are gone. A bbox lets the source region be rendered
    and compared against the markdown. Today nothing in this factory can point at a region.
  * THE UNFILLABLE HIGHLIGHT — the error-structure protocol (docs/29's read-side twin) says
    every surfaced defect carries reason + HIGHLIGHT + solution. The held manifest of
    2026-08-31 carries `run_page: null` on all 25 analyst omission runs; the audit's own note
    calls them "locatable only by their excerpt text". page + bbox is what fills that field.
  * figure_coverage.py currently INFERS what a polygon would MEASURE.

WHY A SIDECAR AND NOT A SECOND MARKER PASS. The 2026-08-31 Damodaran cost 3,834.2 s of GPU
across 7 slices. A second `marker_single --output_format chunks` run would double that, and it
is not even available in one call: `--output_format` is a single-valued `click.Choice`
(marker/config/parser.py), so no CLI invocation can emit two formats. This process therefore
builds the document ONCE — `PdfConverter.build_document()`, which is the whole GPU cost — and
renders that one cached in-memory Document twice: markdown first, then chunks. The chunk render
is pure post-processing over an already-built tree; it touches no model.

WHY A SIDECAR AND NOT AN IMPORT INSIDE convert_and_ship.py. Everything hard-won in `_run_marker`
is subprocess-shaped: the draining reader thread (S48's cp1252 pipe deadlock), the tree-kill
(S48's orphaned python), the kill-early stall signature (S45/S48), the page-scaled outer timeout
(S45). Importing marker into the converter's own process would throw all four away to gain
nothing. This keeps the process boundary exactly where it has always been and only swaps what
runs on the far side of it, so the stall monitor, the retry ladder and the split fallback are
untouched.

ARGV FIDELITY, NOT A REIMPLEMENTATION. The argv is parsed by marker's OWN click command
(`convert_single_cli.make_context`), so every option resolves exactly as `marker_single`
resolves it — including `--strip_existing_ocr` and `--recognition_batch_size`, which do not
appear in `ConfigParser.common_options` at all: `CustomClickPrinter.parse_args` synthesizes them
from the config crawler at parse time. A hand-rolled parser would have silently dropped both,
i.e. silently changed the engine's OCR lane and its VRAM cap while still reporting success —
the expensive kind of wrong.

BLOCKS ARE AN ADDITION AND MAY NEVER COST A BOOK. The markdown is rendered and written FIRST,
by marker's own `save_output`, before the chunk render is attempted at all. Everything after
that point runs under one try/except that prints a named reason and exits 0. A book can lose
its blocks; a book must never fail because of them.

Run exactly as marker_single is run:
  python marker_blocks.py <pdf> --output_dir <dir> --output_format markdown [engine args]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The extra artifact's name, beside marker's own `<stem>.md` / `<stem>_meta.json` in the same
# output dir. Deliberately NOT `<stem>.json`: that is what marker itself writes for the json and
# chunks formats, and a name collision would make "which tool wrote this" unanswerable later.
BLOCKS_SUFFIX = ".blocks.json"

# Bumped when the RECORD SHAPE changes, so a reader can refuse a shape it does not understand
# instead of misreading it. 1 = the shape documented in `normalize_chunk_payload` below.
BLOCKS_SCHEMA = 1

# Marker's chunk renderer inlines every figure as base64 inside the block that owns it
# (renderers/chunk.py `collect_images`). The bundle already carries those exact bytes as FILES
# in assets/, named from the very same block id (renderers/html.py:
# image_name = f"{ref_block_id.to_path()}.{settings.OUTPUT_IMAGE_FORMAT.lower()}", and
# BlockId.to_path() is str(id).replace("/", "_")). So the base64 is a ~1.33x duplicate of
# something already shipped, on a book with hundreds of figures. Stripped to the derived
# FILENAMES, which is the join key a reader actually wants.
DEFAULT_IMAGE_EXT = "jpeg"


def absolute_page_from_block_id(block_id: str) -> int | None:
    """The block's TRUE absolute page number, read out of the block's OWN id string.

    NEVER read `FlatBlockOutput.page` — the field marker ships is wrong, and wrong in a way
    that looks plausible. marker/renderers/chunk.py's `json_to_chunks` computes it as
    `int(block.id.split("/")[-1])` off the *Page pseudo-block*, whose id is
    `/page/<PAGE>/Page/<counter>`; that LAST segment is `PageGroup.incr_block_id`'s per-page
    monotonic counter over every block-creation event on the page
    (marker/schema/groups/page.py), which has nothing to do with a page number. Re-measured
    2026-09-01 on a synthetic 4-page probe: true pages 0,1,2,3 shipped `page` = 8, 8, 10, 26
    — three distinct values for four pages, one of them repeated, none of them a page number.
    (The J24 scouting probe saw 12, 43, 7, 9 on a different 4-page document: same defect, and
    the values are document-shaped, which is exactly what a block counter would be.)

    The correct segment is index [2]. `BlockId.__str__` (marker/schema/blocks/base.py) is
    `/page/<page_id>/<BlockType>/<block_id>`, and `page_id` is ABSOLUTE across slices by
    construction: marker/builders/document.py builds pages as
    `PageGroupClass(page_id=p, ...) for i, p in enumerate(provider.page_range)` — it stores `p`,
    the value from the parsed `--page_range`, not the enumeration index `i`. That is the whole
    reason constraint 2 (merge slices with correct absolute pages) needs NO offset table.

    EVIDENCE, two independently-shaped checks in two runs (J24 probe, re-measured here before
    shipping): (A) the ChunkOutput `page_info` keys come straight from `page.page_id` and read
    2,3 under `--page_range 2-3` — the book's own pages, not re-indexed to 0,1; (B) splitting
    each block's own id at [2] gives the same 2/3, and gives values identical to those the SAME
    two pages produced inside the full unsliced document.

    Returns None — never a guess — when the id is not that shape. A None page is honest; a
    confidently wrong page is the failure this function exists to prevent.
    """
    parts = str(block_id).split("/")
    # "/page/12/SectionHeader/0" -> ["", "page", "12", "SectionHeader", "0"]
    if len(parts) < 3 or parts[1] != "page":
        return None
    try:
        return int(parts[2])
    except (TypeError, ValueError):
        return None


def asset_name_for_image_key(key: str, image_ext: str = DEFAULT_IMAGE_EXT) -> str:
    """The bundle assets/ filename for a chunk block's image key.

    Derived, never retyped (SYM-039's rule): marker names the file `BlockId.to_path()` plus the
    configured image extension, and `to_path()` is `str(id).replace("/", "_")`. So the key
    `/page/2/Picture/1` is the file `_page_2_Picture_1.jpeg` that already sits in assets/ — the
    same name `convert_and_ship.asset_page()` parses the page out of.
    """
    return str(key).replace("/", "_") + "." + image_ext


def normalize_chunk_payload(payload: dict, *, source: str,
                            image_ext: str = DEFAULT_IMAGE_EXT) -> dict:
    """One ChunkOutput dump -> the J24 record shape, with the page correction applied.

    Per block: id, block_type, html, page (CORRECTED, absolute, may be None), page_field_raw
    (marker's shipped-and-broken value, kept so the defect stays visible and so a future marker
    release that fixes it is DETECTABLE rather than silently assumed), polygon, bbox,
    section_hierarchy, image_refs (assets/ filenames; the base64 is dropped, see above).

    `page_info` keys stay exactly as marker dumped them (strings, absolute page ids) — they are
    the independent cross-check on the correction, so they are never re-derived from it.
    """
    blocks_in = payload.get("blocks") or []
    out: list[dict] = []
    unresolved = 0
    pages: set[int] = set()
    disagreements = 0
    for b in blocks_in:
        page = absolute_page_from_block_id(b.get("id", ""))
        if page is None:
            unresolved += 1
        else:
            pages.add(page)
        raw = b.get("page")
        if page is not None and raw is not None and raw != page:
            disagreements += 1
        images = b.get("images") or {}
        out.append({
            "id": b.get("id"),
            "block_type": b.get("block_type"),
            "html": b.get("html"),
            "page": page,
            "page_field_raw": raw,
            "polygon": b.get("polygon"),
            "bbox": b.get("bbox"),
            "section_hierarchy": b.get("section_hierarchy"),
            "image_refs": [asset_name_for_image_key(k, image_ext) for k in images],
        })
    return {
        "schema": BLOCKS_SCHEMA,
        "sources": [source],
        "blocks": out,
        "page_info": payload.get("page_info") or {},
        "blocks_total": len(out),
        "pages_with_blocks": len(pages),
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "page_unresolved": unresolved,
        # How often marker's own `page` field disagreed with the corrected one. Expected to be
        # ~every block on marker-pdf 1.10.2; a sudden 0 means upstream fixed `json_to_chunks`
        # and this correction became a (harmless) no-op — worth knowing, never assumed.
        "page_field_raw_disagreements": disagreements,
        "page_field_note": (
            "page is corrected: read from each block's own id at split('/')[2], because "
            "marker-pdf's FlatBlockOutput.page is the Page pseudo-block's per-page block "
            "counter, not a page number. page_field_raw is what marker shipped."
        ),
    }


def merge_block_records(records: list[dict]) -> dict:
    """Concatenate per-slice records into one.

    A PLAIN concatenation is correct precisely because every `page` is already absolute (see
    `absolute_page_from_block_id`): slices are disjoint page ranges, so there is no offset to
    apply, no renumbering, and no collision. If pages were slice-relative this function would be
    the place the lie became permanent — which is exactly why the correction lives upstream of
    it and carries its evidence with it.
    """
    blocks: list[dict] = []
    page_info: dict = {}
    sources: list[str] = []
    unresolved = 0
    disagreements = 0
    # The per-slice phase timings survive the merge, summed. Without this the "the second render
    # costs no GPU pass" claim would be re-checkable only on a probe — and this factory does not
    # keep a claim it cannot re-measure on the next real book (docs/34). Found by reading the
    # merged file on the J24 acceptance run, where it had silently become null.
    timing: dict | None = None
    for rec in records:
        blocks.extend(rec.get("blocks") or [])
        page_info.update(rec.get("page_info") or {})
        sources.extend(rec.get("sources") or [])
        unresolved += int(rec.get("page_unresolved") or 0)
        disagreements += int(rec.get("page_field_raw_disagreements") or 0)
        t = rec.get("timing_s")
        if isinstance(t, dict):
            timing = timing or {"build_document": 0.0, "markdown_render": 0.0,
                                "chunk_render": 0.0, "pages": 0, "slices_timed": 0}
            for k in ("build_document", "markdown_render", "chunk_render", "pages"):
                timing[k] = round(timing[k] + (t.get(k) or 0), 3)
            timing["slices_timed"] += 1
    pages = {b["page"] for b in blocks if b.get("page") is not None}
    note = records[0].get("page_field_note") if records else None
    return {
        "timing_s": timing,
        "schema": BLOCKS_SCHEMA,
        "sources": sources,
        "blocks": blocks,
        "page_info": page_info,
        "blocks_total": len(blocks),
        "pages_with_blocks": len(pages),
        "page_min": min(pages) if pages else None,
        "page_max": max(pages) if pages else None,
        "page_unresolved": unresolved,
        "page_field_raw_disagreements": disagreements,
        "page_field_note": note,
    }


def merge_block_files(paths, dest: Path, *, slices_total: int) -> dict:
    """Merge every readable per-slice blocks file into `dest`; return the manifest summary.

    `slices_total` is the number of slices the BOOK has, not the number of files handed in, so
    the summary can say `complete: false` out loud when a slice contributed nothing. That case
    is normal and expected: a slice cached by a pre-J24 run has `slice.md` and no blocks, and
    re-converting it to collect blocks would cost hours of GPU for an ADDITION — forbidden by
    constraint 1. A partial record advertising itself as whole would be the SYM-053 disease one
    level up ("it looks covered"), so it says so instead.
    """
    records: list[dict] = []
    unreadable: list[str] = []
    for p in paths:
        name = Path(p).name
        try:
            rec = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            unreadable.append(name + ": " + type(exc).__name__)
            continue
        if isinstance(rec, dict) and rec.get("schema") == BLOCKS_SCHEMA:
            records.append(rec)
        else:
            got = rec.get("schema") if isinstance(rec, dict) else type(rec).__name__
            unreadable.append(name + ": schema " + str(got))
    merged = merge_block_records(records)
    merged["slices_total"] = slices_total
    merged["slices_with_blocks"] = len(records)
    merged["complete"] = (slices_total > 0 and len(records) == slices_total
                          and merged["page_unresolved"] == 0 and not unreadable)
    if unreadable:
        merged["unreadable"] = unreadable
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    return summarize(merged, dest)


def summarize(record: dict, path: Path | None = None) -> dict:
    """The small block that rides in manifest.json — counts and honesty flags, never the blocks
    themselves (the manifest stays readable; blocks.json is the payload)."""
    out = {
        "schema": record.get("schema"),
        "blocks_total": record.get("blocks_total"),
        "pages_with_blocks": record.get("pages_with_blocks"),
        "page_min": record.get("page_min"),
        "page_max": record.get("page_max"),
        "page_unresolved": record.get("page_unresolved"),
        "page_field_raw_disagreements": record.get("page_field_raw_disagreements"),
        "slices_total": record.get("slices_total"),
        "slices_with_blocks": record.get("slices_with_blocks"),
        "complete": record.get("complete"),
        # The whole ticket rests on "the second render is not a second GPU pass". These three
        # seconds, summed over the book's slices, are what lets the next reader CHECK that
        # instead of believing it. numerator = seconds; denominator = this book's slices;
        # conditions = one process per slice, models already resident from the build.
        "timing_s": record.get("timing_s"),
        "file": "blocks.json",
    }
    if record.get("unreadable"):
        out["unreadable"] = record["unreadable"]
    if path is not None:
        try:
            out["bytes"] = path.stat().st_size
        except OSError:
            out["bytes"] = None
    return out


# ---------- the marker_single drop-in ----------

def main(argv: list[str]) -> int:
    # Mirrors marker/scripts/convert_single.py's own preamble, which sets these BEFORE importing
    # anything from marker. Same order here, for the same reason.
    import os

    os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
    os.environ.setdefault("GLOG_minloglevel", "2")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    import time

    from marker.config.parser import ConfigParser
    from marker.logger import configure_logging
    from marker.models import create_model_dict
    from marker.output import save_output
    from marker.scripts.convert_single import convert_single_cli

    configure_logging()

    # marker's OWN parser, so `--strip_existing_ocr`, `--recognition_batch_size` and every other
    # crawler-synthesized option resolve exactly as they do for marker_single (see the module
    # docstring). `fpath` is a click.argument and lands in params beside the options;
    # convert_single_cli pulls it out of its signature, so it is popped here too.
    ctx = convert_single_cli.make_context("marker_single", list(argv))
    kwargs = dict(ctx.params)
    fpath = kwargs.pop("fpath")

    models = create_model_dict()
    config_parser = ConfigParser(kwargs)
    converter_cls = config_parser.get_converter_cls()
    converter = converter_cls(
        config=config_parser.generate_config_dict(),
        artifact_dict=models,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
        llm_service=config_parser.get_llm_service(),
    )
    out_folder = config_parser.get_output_folder(fpath)
    fname_base = config_parser.get_base_filename(fpath)

    # ---- THE ONE GPU PASS. Line-for-line PdfConverter.__call__, with the Document kept. ----
    # The three phases are timed separately and PRINTED, because the whole ticket turns on one
    # claim — that the second render is free of GPU — and this factory does not accept a claim
    # it cannot re-measure on the next book (docs/34: numerator, denominator, conditions).
    t_build = time.perf_counter()
    with converter.filepath_to_str(fpath) as temp_path:
        document = converter.build_document(temp_path)
        converter.page_count = len(document.pages)
        build_s = time.perf_counter() - t_build
        t_md = time.perf_counter()
        rendered = converter.resolve_dependencies(converter.renderer)(document)
        markdown_s = time.perf_counter() - t_md

    # The markdown is written by marker's own save_output, from a render of the same Document
    # the CLI would have rendered, BEFORE any block work is attempted. Constraint 4 (the vault
    # stores this; the fidelity audit scores it) is structural here, not merely tested.
    save_output(rendered, out_folder, fname_base)
    pages_built = len(document.pages)
    print("J24 markdown written: {} ({} pages; build_document {:.2f}s, "
          "markdown render {:.2f}s)".format(
              Path(out_folder) / (fname_base + ".md"), pages_built, build_s, markdown_s),
          flush=True)

    # ---- everything below is the ADDITION, and may never cost the book ----
    try:
        from marker.renderers.chunk import ChunkRenderer
        from marker.renderers.markdown import MarkdownRenderer
        from marker.settings import settings

        if converter.renderer is not MarkdownRenderer:
            # Only the markdown lane is wired for this; any other requested format already
            # writes its own structured output and this would just shadow it.
            print("J24 blocks skipped: renderer is not MarkdownRenderer", flush=True)
            return 0
        t_chunk = time.perf_counter()
        chunk = converter.resolve_dependencies(ChunkRenderer)(document)
        payload = json.loads(chunk.model_dump_json(exclude=["metadata"]))
        chunk_s = time.perf_counter() - t_chunk
        record = normalize_chunk_payload(
            payload, source=fname_base + BLOCKS_SUFFIX,
            image_ext=str(settings.OUTPUT_IMAGE_FORMAT).lower())
        # A single-input record is "complete" in the same vocabulary the merge uses, so a short
        # book and a sliced book produce the same shape and one reader handles both.
        record["slices_total"] = 1
        record["slices_with_blocks"] = 1
        record["complete"] = record["page_unresolved"] == 0
        # The cost of the ADDITION, per run, in the record itself — so the "no second GPU pass"
        # claim is auditable on every real book, not only on the probe that first measured it.
        record["timing_s"] = {"build_document": round(build_s, 3),
                              "markdown_render": round(markdown_s, 3),
                              "chunk_render": round(chunk_s, 3),
                              "pages": pages_built}
        dest = Path(out_folder) / (fname_base + BLOCKS_SUFFIX)
        dest.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        print("J24 blocks written: {} ({} blocks, pages {}-{}, {} bytes, "
              "chunk render {:.2f}s = {:.1f}% of build_document's {:.2f}s)".format(
                  dest.name, record["blocks_total"], record["page_min"], record["page_max"],
                  dest.stat().st_size, chunk_s,
                  (100.0 * chunk_s / build_s) if build_s > 0 else float("nan"), build_s),
              flush=True)
    except Exception as exc:  # noqa: BLE001 — an ADDITION must never fail a conversion
        print("J24 blocks FAILED ({}: {}) — markdown is already written and unaffected".format(
            type(exc).__name__, str(exc)[:200]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
