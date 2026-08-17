"""Tests for the ported degeneration tripwire (converter/degeneration.py).

The cases mirror the calibration evidence in docs/15 §9.1/§9.2: a real loop trips BOTH gates,
a dense table trips only zlib (and must be cleared by the trigram AND-gate), a stuck decoder
repeats a line CONTIGUOUSLY while legitimate structure repeats DISTRIBUTED.
"""

from converter.degeneration import (
    DEGEN_BLOCK_MIN_CHARS,
    DEGEN_LINE_REPEAT,
    degeneration,
)

# A paragraph of normal prose, long enough to be scanned (> DEGEN_BLOCK_MIN_CHARS).
PROSE = (
    "The viable system model describes the organization of autonomous units within a larger "
    "whole, each unit itself organized recursively on the same principles, so that regulation "
    "and autonomy are balanced at every level of the enterprise rather than concentrated at "
    "the top of a command hierarchy."
)


def test_clean_prose_not_flagged():
    result = degeneration(PROSE + "\n\n" + PROSE.replace("viable", "living"))
    assert result["flagged"] is False
    assert result["worst"] == []
    assert result["repeated_lines"] == 0


def test_loop_paragraph_flagged():
    # The SYM-003 shape: one phrase repeated until the block is both crushed-compressible
    # and trigram-extreme (docs/15: Beer's loop hit zlib<=0.17, trigram>=1674).
    loop = " ".join(["the control of the control of"] * 80)
    assert len(loop) >= DEGEN_BLOCK_MIN_CHARS
    result = degeneration(loop)
    assert result["flagged"] is True
    assert len(result["worst"]) == 1
    w = result["worst"][0]
    assert w["zlib"] < 0.20
    assert w["max_trigram"] >= 40
    assert w["line"] == 1
    assert w["excerpt"].startswith("the control of")


def test_table_dense_block_not_flagged():
    # The Cybernetics false-positive (docs/15 §9.2): structural | and --- crush zlib, but
    # varied words keep the trigram low -- the AND rule must clear it.
    rows = [
        f"| model {i} | goal of system {i} | outcome {i * 7} | note {i * 13} |" for i in range(40)
    ]
    table = "| a | b | c | d |\n|---|---|---|---|\n" + "\n".join(rows)
    result = degeneration(table)
    assert result["flagged"] is False
    assert result["worst"] == []


def test_contiguous_repeated_lines_flagged():
    # A stuck decoder emits the same line back-to-back; runs beyond DEGEN_LINE_REPEAT flag.
    line = "the purpose of a system is what it does"
    assert len(line) > 20
    body = "\n".join([line] * (DEGEN_LINE_REPEAT + 5))
    result = degeneration(body)
    assert result["flagged"] is True
    assert result["repeated_lines"] == DEGEN_LINE_REPEAT + 5


def test_distributed_repeats_not_flagged():
    # Legitimate structure (a recurring heading) is distributed, giving runs of 1.
    section = "#### a. goal of model with a name long enough\n\n" + PROSE + "\n\n"
    result = degeneration(section * 30)
    assert result["repeated_lines"] == 0
    assert result["flagged"] is False


def test_table_rows_never_count_toward_runs():
    row = "| identical row content that is quite long here |"
    body = "\n".join([row] * (DEGEN_LINE_REPEAT + 10))
    assert degeneration(body)["repeated_lines"] == 0


def test_cjk_loop_flagged_via_char_ngrams():
    # Space-free block: word split yields <5 tokens, so the char-trigram path must catch it.
    loop = "制御の制御の" * 60
    assert len(loop) >= DEGEN_BLOCK_MIN_CHARS
    result = degeneration(loop)
    assert result["flagged"] is True


def test_short_blocks_ignored():
    short_loop = " ".join(["loop loop loop"] * 3)
    assert len(short_loop) < DEGEN_BLOCK_MIN_CHARS
    assert degeneration(short_loop)["flagged"] is False


def test_md_lines_counts_lines():
    assert degeneration("a\nb\nc")["md_lines"] == 3


def test_worst_sorted_by_zlib_then_trigram():
    heavy = " ".join(["alpha beta gamma"] * 100)
    lighter = " ".join(["one two three four five six"] * 40)
    result = degeneration(heavy + "\n\n" + lighter)
    zlibs = [w["zlib"] for w in result["worst"]]
    assert zlibs == sorted(zlibs)
