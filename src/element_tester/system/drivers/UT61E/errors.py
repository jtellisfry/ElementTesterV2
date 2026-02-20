"""
UT61E-specific exceptions

Re-export error classes from centralized error_messages module.
This file exists for backwards compatibility.
"""

from element_tester.system.core.error_messages import (
    UT61EError,
    UT61ETimeoutError,
    UT61EPacketError,
)

__all__ = [
    'UT61EError',
    'UT61ETimeoutError',
    'UT61EPacketError',
]
