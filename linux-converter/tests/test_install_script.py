"""S157 E51 (B32 U03): scripts/install.sh must install the vault-fixity service AND timer beside the converter service.

Codex's 2026-08-27 completion audit found the units shipped in systemd/ with placeholders and a comment promising that
install.sh substituted them, while install.sh installed only the converter — a fresh machine had no weekly fixity check.
This is the tripwire for the repair: the script must name both units, template the service the way it templates the
converter's (no placeholder survives the sed), copy the timer, and enable the TIMER (the service is its oneshot).
The negative control edits a copy of the script to drop the timer line and expects the same checks to fail.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.sh"
SERVICE = ROOT / "systemd" / "file-portal-vault-fixity.service"
TIMER = ROOT / "systemd" / "file-portal-vault-fixity.timer"


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def _enables_timer(script: str) -> bool:
    return (
        re.search(
            r"^systemctl --user enable --now file-portal-vault-fixity\.timer\s*$", script, re.M
        )
        is not None
    )


def test_units_exist_and_the_service_carries_the_placeholders_the_script_substitutes():
    assert SERVICE.is_file() and TIMER.is_file()
    svc = _text(SERVICE)
    assert "__WORKDIR__" in svc and "__EXEC_PATH__" in svc
    assert "__" not in _text(TIMER), "the timer carries no placeholder and is copied as is"


def test_install_script_installs_and_enables_the_fixity_timer():
    script = _text(INSTALL)
    assert "file-portal-vault-fixity.service" in script
    assert "file-portal-vault-fixity.timer" in script
    assert _enables_timer(script)
    # the service is templated with the SAME two substitutions as the converter unit
    m = re.search(
        r'sed "s\|__WORKDIR__\|\$\(pwd\)\|; s\|__EXEC_PATH__\|\$\(pwd\)/\.venv/bin/python\|" \\\n\s+"\$FIXITY_SRC" > "\$FIXITY_DST"',
        script,
    )
    assert m, "the fixity service must be templated like the converter service"


def test_the_templating_leaves_no_placeholder(tmp_path: Path):
    sed = shutil.which("sed")
    if not sed:
        import pytest

        pytest.skip("no sed on PATH — the templating cannot be exercised here (UNREAD, not a pass)")
    out = subprocess.run(
        [
            sed,
            "s|__WORKDIR__|/home/x/file-portal/linux-converter|; s|__EXEC_PATH__|/home/x/file-portal/linux-converter/.venv/bin/python|",
            str(SERVICE),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "__WORKDIR__" not in out and "__EXEC_PATH__" not in out
    assert (
        "ExecStart=/home/x/file-portal/linux-converter/.venv/bin/python -m converter.fixity"
        in out.replace("\r", "")
    )


def test_negative_control_a_script_without_the_timer_line_fails_the_check(tmp_path: Path):
    script = _text(INSTALL)
    stripped = "\n".join(
        ln for ln in script.split("\n") if "file-portal-vault-fixity.timer" not in ln
    )
    assert not _enables_timer(stripped)
    assert "file-portal-vault-fixity.timer" not in stripped
