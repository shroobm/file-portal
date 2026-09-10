"""Seam receipts: mirror copy of `append_receipt` from linux-converter/converter/exporter.py
(the one-file port pattern the Linux lanes already use for sdnotify.py and status.py). Keep
the two copies identical: the byte shape of a line is asserted by the widget's seam test
(windows-widget/src-tauri/src/receipts.rs) and the torn-line healing is SYM-037's fix.

Outcomes this lane writes -- and only these, because the widget's alarm vocabulary keys on
the exporter's (`failed`, `supersede-held`, `bless-invalid`; algedonic.rs):
- `indexed`       one per reconcile run that changed the index: the vault tip, counts, the
                  build levers it ran under (model, model_sha, passage_chars, passage_max_chars,
                  fts_tokenizer, threads) and any lever fallback; `result` pass|fail (fail = a
                  bundle was refused), fixity's check-style shape.
- `index-failed`  the run could not reconcile at all (vault missing, store mismatch, crash).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("file-portal-indexer")

RECEIPTS_NAME = "receipts.jsonl"


def append_receipt(root: Path, outcome: str, **fields) -> None:
    """Append one seam receipt to <root>/receipts.jsonl. Best-effort and never raises:
    telemetry must never cost the operation it reports on. Mirror of the converter's; the
    exporter, the fixity check and the indexer all append to the same file this way."""
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "outcome": outcome,
            **fields,
        }
        receipts_path = root / RECEIPTS_NAME
        # A crash mid-append can leave a torn final line with no newline; appending straight
        # onto it would glue THIS record into the garbage and lose both. Heal the boundary:
        # if the file doesn't end in a newline, start with one (the torn line stays torn --
        # readers already skip unparseable lines -- but this record survives). Observed shape,
        # not hypothetical: S76 took two power cuts mid-run.
        lead = ""
        try:
            with open(receipts_path, "rb") as check:
                check.seek(-1, 2)
                if check.read(1) != b"\n":
                    lead = "\n"
        except OSError:
            pass  # missing or empty file needs no lead
        with open(receipts_path, "a", encoding="utf-8") as fh:
            fh.write(lead + json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        logger.warning("receipt %s could not be written (operation unaffected)", outcome)
