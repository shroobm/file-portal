"""Entry point: watches pipeline/convert-inbox and pipeline/convert-scan-inbox and converts
arrivals into markdown bundles (anchor + staging).

Lane topology (Open Decision #3, resolved 2026-07-09): a missing text layer is a detectable
precondition, not a failure. Clean-lane .pdf/.epub files are probed first; a sub-threshold text
layer reroutes the file into convert-scan-inbox as a normal `allocated` hop. The Scan lane is
terminal: sub-threshold OCR output quarantines the file with a `rejected` event. Clean may
route to Scan; Scan may route to nothing -- no cycle is possible by construction.

Event model: the allocator hop is a rename whose SOURCE is outside this service's watch
(inbox/ -> pipeline/), and inotify reports an unpaired IN_MOVED_TO as a plain `created` event
-- not `moved`, and never `close_write` (verified empirically 2026-07-10; the allocator's
own on_moved/on_closed-only model does not transfer to this topology). So all three event
types are handled: on_moved (the probe reroute, a rename within the watch), on_closed (a cp
or scp written in place), and on_created with a size-stability wait (the allocator hop; also
the first event of an in-progress cp). A cp fires created AND closed, but events dispatch on
a single watchdog thread and success consumes the source file, so the second event sees a
missing file and returns. Runs as a systemd --user service -- see
systemd/file-portal-converter.service.
"""

import argparse
import logging
import shutil
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from converter import bundle, engines, exporter
from converter.config import DEFAULT_ROOT, Paths, Settings
from converter.status import StatusWriter

logger = logging.getLogger("file-portal-converter")

VERSION = "0.1.0"

LANE_BY_INBOX = {"convert-inbox": "clean", "convert-scan-inbox": "scan"}
CATEGORY_BY_LANE = {"clean": "convert", "scan": "convert-scan"}


class ConvertHandler(FileSystemEventHandler):
    def __init__(self, paths: Paths, settings_path: Path, status: StatusWriter):
        self.paths = paths
        self.settings_path = settings_path
        self.status = status

    def on_moved(self, event):
        # A rename within the watched tree: the probe reroute into convert-scan-inbox.
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def on_closed(self, event):
        # inotify IN_CLOSE_WRITE: completion signal for transports that write in place (a
        # manual cp, scp). Usually a no-op after on_created already consumed the file.
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_created(self, event):
        # The allocator hop arrives HERE: a rename from outside the watch is an unpaired
        # IN_MOVED_TO, which inotify/watchdog surface as `created` (see module docstring).
        # The stability wait costs one 0.5s poll for an already-complete rename and protects
        # against converting a cp that is still writing.
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        self._wait_until_stable(file_path)
        self._handle(file_path)

    def _handle(self, file_path: Path):
        # A single bad file must not kill the observer thread and stop the service.
        try:
            self._convert(file_path)
        except Exception:
            logger.exception("failed to convert %s", file_path)

    def _convert(self, file_path: Path):
        if not file_path.exists():
            return
        # Dot-prefixed files are in-progress temp files (the transfer's .part-* pattern).
        if file_path.name.startswith("."):
            return
        lane = LANE_BY_INBOX.get(file_path.parent.name)
        if lane is None:
            # Not one of the two watched inboxes (e.g. a stray file directly in pipeline/).
            return

        # Settings re-read on every event, same contract as the allocator's rules.toml.
        settings = Settings.load(self.settings_path)
        category = CATEGORY_BY_LANE[lane]

        engine = engines.resolve_engine(file_path.name)
        if engine is None:
            self._quarantine(file_path, category, "no conversion engine for this extension")
            return

        chars_detected: float | None = None
        pages = 1
        if engine.name == "pymupdf4llm":
            try:
                chars_detected = engines.probe_chars_per_page(file_path)
                pages = engines.page_count(file_path)
            except Exception as exc:
                self._quarantine(file_path, category, f"unreadable by pymupdf: {exc}")
                return
            logger.info(
                "PROBE %s chars_per_page=%.1f threshold=%d lane=%s",
                file_path.name,
                chars_detected,
                settings.min_chars_per_page,
                lane,
            )
            if lane == "clean" and chars_detected < settings.min_chars_per_page:
                self._reroute_to_scan(file_path, category, chars_detected, settings)
                return
            if lane == "clean":
                lane_reason = "text_layer_present"
            elif chars_detected < settings.min_chars_per_page:
                lane_reason = "no_text_layer"
            else:
                # Dropped on the force-scan inbox despite a real text layer: a user override
                # (e.g. the embedded text layer is garbled), not a detection.
                lane_reason = "user_forced_scan"
        else:
            # .docx is born-digital by definition -- no probe, always Clean, never OCR.
            lane_reason = "text_layer_present"

        bundle_name = file_path.stem
        # Assemble in a dot-prefixed temp dir under staging (unwatched), publish by rename.
        tmp_dir = self.paths.staging / f".part-{bundle_name}"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        assets_dir = tmp_dir / "assets"

        source_sha = bundle.sha256_of(file_path)
        logger.info("CONVERTING %s engine=%s lane=%s", file_path.name, engine.name, lane)
        try:
            if engine.name == "pymupdf4llm":
                markdown = engines.run_pymupdf(file_path, assets_dir, lane, settings)
            else:
                markdown = engines.run_pandoc(file_path, assets_dir)
        except Exception as exc:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            self._quarantine(file_path, category, f"conversion failed: {exc}")
            return

        if lane == "scan":
            # The Scan lane is terminal: below-threshold OCR yield goes to quarantine, never
            # back into an inbox. One hop, no retry counter, no cycle possible.
            ocr_yield = engines.chars_per_page_of_markdown(markdown, pages)
            logger.info(
                "OCR-YIELD %s chars_per_page=%.1f threshold=%d",
                file_path.name,
                ocr_yield,
                settings.min_chars_per_page,
            )
            if ocr_yield < settings.min_chars_per_page:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                self._quarantine(
                    file_path,
                    category,
                    f"ocr yield {ocr_yield:.1f} chars/page below threshold "
                    f"({settings.min_chars_per_page})",
                )
                return

        converted_at = bundle.utcnow()
        ocr = lane == "scan"
        frontmatter = bundle.render_frontmatter(
            engine=engine.name,
            lane=lane,
            lane_reason=lane_reason,
            chars_per_page_detected=chars_detected,
            ocr=ocr,
            ocr_dpi=settings.ocr_dpi if ocr else None,
            converted_at=converted_at,
            source_sha256=source_sha,
        )
        manifest = {
            "source": file_path.name,
            "source_sha256": source_sha,
            "engine": engine.name,
            "lane": lane,
            "lane_reason": lane_reason,
            "chars_per_page_detected": chars_detected,
            "pages": pages,
            "converter_version": VERSION,
            "pymupdf4llm_version": engines.pymupdf4llm.__version__,
            "converted_at": converted_at.isoformat(timespec="seconds"),
        }
        bundle.assemble(tmp_dir, bundle_name, markdown, frontmatter, manifest)
        anchor_dest, staging_dest = bundle.publish(
            tmp_dir, bundle_name, self.paths.anchor, self.paths.staging
        )
        file_path.unlink()
        logger.info(
            "CONVERTED %s -> %s (staging copy %s)",
            file_path.name,
            anchor_dest.relative_to(self.paths.root),
            staging_dest.relative_to(self.paths.root),
        )

    def _reroute_to_scan(self, file_path: Path, category: str, chars: float, settings: Settings):
        # A normal path, not an error path: emits `allocated` (green tile), never `rejected`.
        # The rename lands in convert-scan-inbox, where this same handler picks it up as Scan.
        dest = bundle.unique_path(self.paths.convert_scan_inbox / file_path.name)
        file_path.rename(dest)
        logger.info(
            "REROUTED %s -> %s (chars_per_page %.1f < %d)",
            file_path.name,
            dest.relative_to(self.paths.root),
            chars,
            settings.min_chars_per_page,
        )
        self.status.record(
            "allocated",
            file_path.name,
            category,
            dest=str(dest.relative_to(self.paths.root)),
        )

    def _quarantine(self, file_path: Path, category: str, reason: str):
        dest = bundle.unique_path(self.paths.quarantine / file_path.name)
        shutil.move(str(file_path), str(dest))
        logger.warning("REJECTED %s (%s) -> %s", file_path, reason, dest)
        self.status.record("rejected", file_path.name, category, reason=reason)

    @staticmethod
    def _wait_until_stable(file_path: Path, interval: float = 0.5, timeout: float = 60.0):
        """Block until file_path's size is unchanged across one polling interval.

        Returns early if the file disappears; gives up after `timeout` seconds and lets
        _convert see whatever is there.
        """
        deadline = time.monotonic() + timeout
        last_size = -1
        while time.monotonic() < deadline:
            try:
                size = file_path.stat().st_size
            except OSError:
                return
            if size == last_size:
                return
            last_size = size
            time.sleep(interval)


def run(root: Path, settings_path: Path):
    paths = Paths.from_root(root)
    paths.ensure_exist()

    logging.basicConfig(
        filename=paths.logs / "converter.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    status = StatusWriter(paths.logs / "status.json")
    observer = Observer()
    handler = ConvertHandler(paths, settings_path, status)
    # One watch on pipeline/ covers both inboxes; _convert derives the lane from the parent
    # directory, the same way the allocator derives the category.
    observer.schedule(handler, str(paths.pipeline), recursive=True)
    # L11: same process, second watch. Staging only ever receives whole bundles (atomic
    # rename), so non-recursive top-level directory events are the complete signal.
    vault_exporter = exporter.Exporter(paths)
    observer.schedule(exporter.ExportHandler(vault_exporter), str(paths.staging), recursive=False)
    observer.start()
    logger.info("watching %s (lanes: %s)", paths.pipeline, ", ".join(LANE_BY_INBOX))
    logger.info("watching %s (exporting to %s)", paths.staging, paths.vault_bare)
    # Sweep AFTER the watch starts so nothing lands unseen in the gap; export() is
    # idempotent and lock-serialized, so a bundle caught by both is a harmless no-op.
    vault_exporter.sweep()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="File Portal converter service")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "converter.toml",
    )
    args = parser.parse_args()
    run(args.root, args.config)


if __name__ == "__main__":
    main()
