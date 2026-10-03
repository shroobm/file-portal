"""WHAT THIS FILE DOES: pytest tests for allocator/sdnotify.py. A fixture opens a real unix
datagram socket and points NOTIFY_SOCKET at it, so the tests check what sd_notify sends, that it
stays silent without systemd, and how watchdog_armed reads WATCHDOG_USEC. Uses a temp directory.

Tests for the sd_notify helper -- a real AF_UNIX datagram socket stands in for systemd.

Mirror copy in linux-converter/tests/test_sdnotify.py (the helper is duplicated by design;
so is its test). AF_UNIX socket paths are capped ~108 bytes, so the socket binds under a
short mkdtemp rather than pytest's deeply nested tmp_path.
"""

import socket
import tempfile
from pathlib import Path

import pytest

from allocator.sdnotify import sd_notify, watchdog_armed


# -- fixture: a fake systemd notify socket --
@pytest.fixture
def notify_socket(monkeypatch):
    """Bind a unix datagram server in a short temp dir, set NOTIFY_SOCKET to it, and yield the server."""
    with tempfile.TemporaryDirectory(prefix="sdn-") as tmp:
        path = Path(tmp) / "notify.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(path))
            server.settimeout(2)
            monkeypatch.setenv("NOTIFY_SOCKET", str(path))
            yield server


# -- sd_notify and watchdog_armed behaviour --
def test_sends_state_to_notify_socket(notify_socket):
    """sd_notify('READY=1') arrives at the socket as exactly those bytes."""
    sd_notify("READY=1")
    assert notify_socket.recv(64) == b"READY=1"


def test_noop_without_notify_socket(monkeypatch):
    """With NOTIFY_SOCKET unset, sd_notify returns quietly."""
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    sd_notify("WATCHDOG=1")  # must simply not raise


def test_noop_on_dead_socket_path(monkeypatch):
    """With NOTIFY_SOCKET pointing at a path that does not exist, sd_notify swallows the error."""
    monkeypatch.setenv("NOTIFY_SOCKET", "/nonexistent/notify.sock")
    sd_notify("WATCHDOG=1")  # connection failure is swallowed by design


def test_watchdog_armed_reads_usec(monkeypatch):
    """watchdog_armed is True only for a positive number in WATCHDOG_USEC (not 0, junk or unset)."""
    monkeypatch.setenv("WATCHDOG_USEC", "90000000")
    assert watchdog_armed() is True
    monkeypatch.setenv("WATCHDOG_USEC", "0")
    assert watchdog_armed() is False
    monkeypatch.setenv("WATCHDOG_USEC", "junk")
    assert watchdog_armed() is False
    monkeypatch.delenv("WATCHDOG_USEC")
    assert watchdog_armed() is False
