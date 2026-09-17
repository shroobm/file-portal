"""windows-converter/ladder_lever.py -- the J44 normalisation-ladder lever (SYM-076; S182).

The ONE reader of `ladder.txt` under the pipeline root (roots.json `ladder`). text_norm stays a
pure module (analyst.py must never carry fidelity_audit's dependencies), so the two callers of
the ladder -- fidelity_audit.audit_analyst (the document audit) and analyst.process (the
per-chunk guard) -- import this and pass the id down. Absent, unreadable, empty or unknown reads
`j32a-v2` (today's ladder, byte for byte); only the literal `j32a-v3` (case/whitespace-insensitive)
selects v3. Re-read per audit and per analyst pass, like audit-mode.txt. The ON position is
Rab's word; the manifest's `normalisation.regex_id` names the ladder that RAN, so a flip is
provable from the record, never inferred.
"""
import fp_paths
import text_norm as tn


def read_ladder() -> str:
    try:
        value = fp_paths.root("ladder").read_text(encoding="utf-8").strip().lower()
    except (OSError, KeyError):
        return tn.LADDER_V2
    return value if value in tn.LADDERS else tn.LADDER_V2
