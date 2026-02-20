# =================
# ERB08 Errors
# =================
#
# Re-export error classes from centralized error_messages module.
# This file exists for backwards compatibility.

from element_tester.system.core.error_messages import ERB08Error

__all__ = ['ERB08Error']