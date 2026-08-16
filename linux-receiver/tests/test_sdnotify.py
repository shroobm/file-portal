"""Tests for the sd_notify helper -- a real AF_UNIX datagram socket stands in for systemd.

Mirror copy in linux-converter/tests/test_sdnotify.py (the helper is duplicated by design;
so is its test). AF_UNIX socket paths are capped ~108 bytes, so the socket binds under a
short mkdtemp rather than pytest's deeply nested tmp_path.
"""

import socket
import tempfile
from pathlib import Path

import pytest

from allocator.sdnotify import sd_notify, watchdog_armed


@pytest.fixture
def notify_socket(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="sdn-") as tmp:
        path = Path(tmp) / "notify.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(path))
            server.settimeout(2)
            monkeypatch.setenv("NOTIFY_SOCKET", str(path))
            yield server


def test_sends_state_to_notify_socket(notify_socket):
    sd_notify("READY=1")
    assert notify_socket.recv(64) == b"READY=1"


def test_noop_without_notify_socket(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    sd_notify("WATCHDOG=1")  # must simply not raise


def test_noop_on_dead_socket_path(monkeypatch):
    monkeypatch.setenv("NOTIFY_SOCKET", "/nonexistent/notify.sock")
    sd_notify("WATCHDOG=1")  # connection failure is swallowed by design


def test_watchdog_armed_reads_usec(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "90000000")
    assert watchdog_armed() is True
    monkeypatch.setenv("WATCHDOG_USEC", "0")
    assert watchdog_armed() is False
    monkeypatch.setenv("WATCHDOG_USEC", "junk")
    assert watchdog_armed() is False
    monkeypatch.delenv("WATCHDOG_USEC")
    assert watchdog_armed() is False
