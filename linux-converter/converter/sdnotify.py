"""systemd notify/watchdog helper -- stdlib only, no python-systemd dependency.

Duplicated in linux-receiver/allocator/sdnotify.py and linux-converter/converter/sdnotify.py
(the same one-file port pattern as status.py); keep the copies identical.

The unit runs Type=notify + WatchdogSec (see systemd/*.service): systemd hands us
$NOTIFY_SOCKET and $WATCHDOG_USEC, we send READY=1 once the watches are armed and then
WATCHDOG=1 heartbeats from the main loop. Outside systemd (dev foreground, tests) both
env vars are absent and everything here is a silent no-op.
"""

import os
import socket


def sd_notify(state: str) -> None:
    """Best-effort datagram to $NOTIFY_SOCKET; silently a no-op outside systemd.

    Failures are swallowed by design: liveness reporting must never kill the service it
    reports on (the same rule status.py and the exporter's _receipt follow).
    """
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):  # abstract-namespace socket
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(addr)
            sock.sendall(state.encode())
    except OSError:
        pass


def watchdog_armed() -> bool:
    """True when systemd armed a watchdog for this process ($WATCHDOG_USEC present)."""
    usec = os.environ.get("WATCHDOG_USEC", "")
    return usec.isdigit() and int(usec) > 0
