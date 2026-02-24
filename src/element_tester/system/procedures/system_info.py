"""System information helpers for test procedures."""

from __future__ import annotations

import os
import socket


def get_computer_name() -> str:
    """
    Return the current computer name.

    Priority:
    1. Windows COMPUTERNAME environment variable
    2. socket.gethostname()
    3. "UNKNOWN_COMPUTER"
    """
    name = os.environ.get("COMPUTERNAME", "").strip()
    if name:
        return name

    try:
        host = socket.gethostname().strip()
        if host:
            return host
    except Exception:
        pass

    return "UNKNOWN_COMPUTER"
