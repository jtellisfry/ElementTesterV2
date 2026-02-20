"""
=================
Error Messages
=================

Centralized error messages and exception classes for the Element Tester application.

This module provides:
1. All custom exception classes used across the application
2. Standardized error message templates
3. Consistent error handling patterns

Usage:
    from element_tester.system.core.error_messages import (
        ERB08Error, ERROR_RELAY_INIT_FAILED, format_error
    )
    
    raise ERB08Error(format_error(ERROR_RELAY_INIT_FAILED, error=e))
"""

# =================================================================================
# EXCEPTION CLASSES
# =================================================================================

# ---- Relay Driver Errors ----
class ERB08Error(Exception):
    """Base error for the MCC USB-ERB08 relay driver"""
    pass


class PDIS08Error(Exception):
    """Driver-level exception for MCC PDIS08."""
    pass


# ---- Hipot Tester Errors ----
class Hypot3865Error(Exception):
    """Driver-level wrapper error for AR3865 operations."""
    pass


# ---- Meter Driver Errors ----
class Fluke287Error(Exception):
    """Base exception for Fluke 287 driver errors."""
    pass


class Fluke287TimeoutError(Fluke287Error):
    """Raised when communication with Fluke 287 times out."""
    pass


class Fluke287ConnectionError(Fluke287Error):
    """Raised when connection to Fluke 287 fails."""
    pass


class Fluke287CommandError(Fluke287Error):
    """Raised when Fluke 287 returns an error response to a command."""
    pass


class Fluke287ParseError(Fluke287Error):
    """Raised when unable to parse Fluke 287 response."""
    pass


class UT61EError(Exception):
    """Base exception for all UT61E driver errors"""
    pass


class UT61ETimeoutError(UT61EError):
    """Raised when reading times out"""
    pass


class UT61EPacketError(UT61EError):
    """Raised when packet parsing fails"""
    pass


class UT61EAutoError(Exception):
    """Base exception for UT61E auto driver errors"""
    pass


class UT61EAutoTimeoutError(UT61EAutoError):
    """Raised when timeout occurs reading from meter"""
    pass


class UT61EAutoParseError(UT61EAutoError):
    """Raised when packet parsing fails"""
    pass


class UT61EAutoConnectionError(UT61EAutoError):
    """Raised when serial port connection fails"""
    pass


# ---- Measurement Test Errors ----
class MeasurementTimeoutError(RuntimeError):
    """Raised when a meter read operation times out."""
    pass


# =================================================================================
# ERROR MESSAGE TEMPLATES
# =================================================================================

# ---- Import Errors ----
ERROR_IMPORT_AR3865 = "Failed to import AR3865 drivers: {error}"
ERROR_IMPORT_ERB08 = "Failed to import ERB08Driver: {error}"
ERROR_IMPORT_PDIS08 = "Failed to import PDIS08Driver: {error}"
ERROR_IMPORT_HIPOT_TEST = "Failed to import HipotTestSequence: {error}"
ERROR_IMPORT_MEASUREMENT_TEST = "Failed to import MeasurementTestSequence: {error}"
ERROR_IMPORT_CONTINUE_EXIT = "Failed to import ContinueExitDialog: {error}"
ERROR_IMPORT_CONTINUE_RETRY_EXIT = "Failed to import ContinueRetryExitDialog: {error}"
ERROR_IMPORT_TEST_PASSED = "Failed to import TestPassedDialog: {error}"
ERROR_IMPORT_FLUKE287 = "Failed to import Fluke287Driver: {error}"
ERROR_IMPORT_UT61E = "Failed to import UT61EDriver: {error}"
ERROR_IMPORT_MEASUREMENT_PROCS = "Failed to import measurement_test_procedures: {error}"
ERROR_IMPORT_SETTINGS = "Failed to import settings_manager: {error}"

# ---- Driver Initialization Errors ----
ERROR_RELAY_INIT_FAILED = "Failed to initialize ERB08 relay driver: {error}"
ERROR_PDIS_INIT_FAILED = "Failed to initialize PDIS08 relay driver: {error}"
ERROR_HIPOT_INIT_FAILED = "Failed to initialize hipot driver: {error}"
ERROR_HIPOT_CREATE_FAILED = "Failed to create HipotTestSequence: {error}"
ERROR_METER_FLUKE_INIT_FAILED = "Failed to initialize Fluke287 meter driver: {error}"
ERROR_METER_UT61E_INIT_FAILED = "Failed to initialize UT61E meter driver: {error}"
ERROR_MEASUREMENT_CREATE_FAILED = "Failed to create MeasurementTestSequence: {error}"

# ---- ERB08 Relay Driver Errors ----
ERROR_ERB08_INIT = "Failed to initialize ERB08: {error}"
ERROR_ERB08_SHUTDOWN = "Failed to shutdown ERB08: {error}"
ERROR_ERB08_SET_RELAY = "Failed to set relay {bit} -> {state}: {error}"
ERROR_ERB08_ALL_OFF = "Failed to set all relays OFF: {error}"
ERROR_ERB08_ALL_ON = "Failed to set all relays ON: {error}"
ERROR_ERB08_APPLY_MAPPING = "Failed to apply mapping: {error}"
ERROR_ERB08_PIN1TO6_CLOSE = "Failed to close Pin1to6: {error}"
ERROR_ERB08_PIN1TO6_OPEN = "Failed to open Pin1to6: {error}"
ERROR_ERB08_PIN2TO5_CLOSE = "Failed to close Pin2to5: {error}"
ERROR_ERB08_PIN2TO5_OPEN = "Failed to open Pin2to5: {error}"
ERROR_ERB08_PIN3TO4_CLOSE = "Failed to close Pin3to4: {error}"
ERROR_ERB08_PIN3TO4_OPEN = "Failed to open Pin3to4: {error}"

# ---- Hipot Test Procedure Errors ----
ERROR_HIPOT_RESET_FAILED = "Failed to reset hipot instrument: {error}"
ERROR_HIPOT_ERB_RELAY8_CLOSE = "Failed to close ERB relay 8: {error}"
ERROR_HIPOT_ERB_RELAY_CONFIG = "Failed to configure ERB relay for hipot: {error}"
ERROR_HIPOT_TEST_EXEC_FAILED = "Hipot test execution failed: {error}"
ERROR_HIPOT_RESET_AFTER_TEST = "Failed to reset instrument after test: {error}"
ERROR_HIPOT_RELAY_OFF_FAILED = "Failed to turn off relays: {error}"
ERROR_HIPOT_RELAY_OFF_CRITICAL = "CRITICAL: Failed to turn off relays after error: {error}"
ERROR_HIPOT_RELAY_CLOSE = "Failed to close relays for hipot: {error}"
ERROR_HIPOT_RELAY_OPEN = "Failed to open relays: {error}"
ERROR_HIPOT_AR3865_INIT = "Failed to initialize AR3865: {error}"
ERROR_HIPOT_AR3865_SHUTDOWN = "Failed to shutdown AR3865: {error}"
ERROR_HIPOT_AR3865_CONFIG = "Failed to apply config: {error}"
ERROR_HIPOT_AR3865_RUN = "Run failed: {error}"
ERROR_HIPOT_AR3865_QUICK_RUN = "Quick run failed: {error}"
ERROR_HIPOT_AR3865_FILE_RUN = "Run from file failed: {error}"

# ---- Measurement Test Procedure Errors ----
ERROR_MEAS_PIN1TO6_CLOSE = "Failed to close Pin1to6: {error}"
ERROR_MEAS_PIN1TO6_OPEN = "Failed to open Pin1to6: {error}"
ERROR_MEAS_PIN2TO5_CLOSE = "Failed to close Pin2to5: {error}"
ERROR_MEAS_PIN2TO5_OPEN = "Failed to open Pin2to5: {error}"
ERROR_MEAS_PIN3TO4_CLOSE = "Failed to close Pin3to4: {error}"
ERROR_MEAS_PIN3TO4_OPEN = "Failed to open Pin3to4: {error}"
ERROR_MEAS_ALL_RELAYS_OPEN = "Failed to open all relays: {error}"
ERROR_MEAS_RELAY_CRITICAL = "CRITICAL: Failed to turn off relays after error: {error}"
ERROR_MEAS_TIMEOUT = "Measurement timed out after {timeout} seconds"
ERROR_MEAS_RELAYS_OPEN = "Failed to open all relays: {error}"
ERROR_MEAS_BUFFER_FLUSH = "Failed to flush initial buffer: {error}"
ERROR_MEAS_RELAY_CLOSE = "Failed to close relays for {config}: {error}"
ERROR_MEAS_BUFFER_FLUSH_CONFIG = "Failed to flush buffer: {error}"

# ---- Fluke 287 Driver Errors ----
ERROR_FLUKE287_INIT = "Initialization failed: {error}"
ERROR_FLUKE287_NOT_INIT = "Fluke 287 not initialized"
ERROR_FLUKE287_READ_FAILED = "Failed to read after {attempts} attempts: {error}"
ERROR_FLUKE287_NO_READINGS = "No successful readings obtained"
ERROR_FLUKE287_BUFFER_FLUSH = "Buffer flush failed: {error}"
ERROR_FLUKE287_NOT_CONNECTED = "Fluke 287 not connected"
ERROR_FLUKE287_NO_RESPONSE = "No response from Fluke 287"
ERROR_FLUKE287_IDENTIFY = "Failed to get identification: {error}"
ERROR_FLUKE287_CONFIG_RES = "Failed to configure resistance: {error}"
ERROR_FLUKE287_CONFIG_VDC = "Failed to configure DC voltage: {error}"
ERROR_FLUKE287_MEASURE_RES = "Failed to measure resistance: {error}"
ERROR_FLUKE287_READ_VALUE = "Failed to read current value: {error}"
ERROR_FLUKE287_FETCH_MEAS = "Failed to fetch last measurement: {error}"
ERROR_FLUKE287_CHECK_ERROR = "Failed to check errors: {error}"
ERROR_FLUKE287_RESET = "Failed to reset instrument: {error}"
ERROR_FLUKE287_CLEAR_STATUS = "Failed to clear status: {error}"
ERROR_FLUKE287_PARSE = "Failed to parse measurement '{response}': {error}"
ERROR_FLUKE287_OPEN = "Failed to open Fluke 287 on {port}: {error}"
ERROR_FLUKE287_WRITE = "Failed to write to Fluke 287: {error}"
ERROR_FLUKE287_READ = "Failed to read from Fluke 287: {error}"
ERROR_FLUKE287_FLUSH_INPUT = "Failed to flush input buffer: {error}"

# ---- UT61E Driver Errors ----
ERROR_UT61E_INIT = "Failed to initialize UT61E: {error}"
ERROR_UT61E_TIMEOUT = "Timeout reading from UT61E: {error}"
ERROR_UT61E_READ = "Failed to read from UT61E: {error}"
ERROR_UT61E_RESISTANCE = "Failed to read resistance: {error}"
ERROR_UT61E_MULTIPLE = "Failed to read multiple samples: {error}"
ERROR_UT61E_FLUSH = "Failed to flush buffer: {error}"
ERROR_UT61E_PARSE_INVALID = "Invalid format: '{text}' (parts: {parts})"

# ---- UT61E Auto Driver Errors ----
ERROR_UT61E_AUTO_INIT = "Failed to initialize UT61E Auto: {error}"
ERROR_UT61E_AUTO_TIMEOUT = "Timeout reading from UT61E Auto: {error}"
ERROR_UT61E_AUTO_READ = "Failed to read from UT61E Auto: {error}"
ERROR_UT61E_AUTO_RESISTANCE = "Failed to read resistance: {error}"
ERROR_UT61E_AUTO_AVERAGED = "Failed to read averaged value: {error}"
ERROR_UT61E_AUTO_STABLE = "Reading did not stabilize: {error}"
ERROR_UT61E_AUTO_WAIT_STABLE = "Failed waiting for stable reading: {error}"
ERROR_UT61E_AUTO_READ_TIMEOUT = "Failed to read after {attempts} attempts: {error}"
ERROR_UT61E_AUTO_NO_SAMPLES = "No valid samples obtained for averaging"
ERROR_UT61E_AUTO_PARSE = "Parse error: {error}"

# ---- Test Runner Errors ----
ERROR_CONFIG_RELAY_READ = "Failed to read relay driver from config, using default ERB08: {error}"
ERROR_CONFIG_METER_READ = "Failed to read meter driver from config, using default FLUKE287: {error}"
ERROR_RELAY_RESET = "Failed to open relays during reset: {error}"
ERROR_HIPOT_RESET = "Failed to reset hipot during cleanup: {error}"


# =================================================================================
# INFORMATIONAL MESSAGES
# =================================================================================

# ---- Relay Messages ----
INFO_RELAY_PIN1TO6_CLOSED = "RELAY: Pin1to6 closed with {delay}ms settling delay"
INFO_RELAY_PIN1TO6_OPENED = "RELAY: Pin1to6 opened with {delay}ms delay"
INFO_RELAY_PIN2TO5_CLOSED = "RELAY: Pin2to5 closed with {delay}ms settling delay"
INFO_RELAY_PIN2TO5_OPENED = "RELAY: Pin2to5 opened with {delay}ms delay"
INFO_RELAY_PIN3TO4_CLOSED = "RELAY: Pin3to4 closed with {delay}ms settling delay"
INFO_RELAY_PIN3TO4_OPENED = "RELAY: Pin3to4 opened with {delay}ms delay"
INFO_RELAY_ALL_OPENED = "RELAY: All relays opened"
INFO_RELAY_ERB_RELAY8_CLOSED = "RELAY: ERB relay 8 closed for hipot circuit"

# ---- Hipot Messages ----
INFO_HIPOT_REMOTE_MODE = "HIPOT: Ensuring instrument is in REMOTE mode and resetting"
INFO_HIPOT_IDN = "HIPOT IDN: {idn}"
INFO_HIPOT_IDN_WARN = "HIPOT: Unable to read IDN; continue if instrument is in remote mode"
INFO_HIPOT_ERB_CLOSE_R7 = "RELAY(ERB): Closing relay 7 (index 6) to complete hipot path"
INFO_HIPOT_ERB_RELAY8 = "RELAY(ERB): Closing relay 8 to enable hipot path on ERB board"
INFO_HIPOT_EXECUTE = "HIPOT: Executing test from file 1 (FL 1) against relays 0-5"
INFO_HIPOT_RESULT = "HIPOT: Test complete - {result} (raw: {raw})"
INFO_HIPOT_RESET = "HIPOT: Instrument reset at {elapsed:.1f}s from test start"
INFO_HIPOT_RELAY_DISABLE = "RELAY: Disabling hipot circuit (opening previously closed relays)"
INFO_HIPOT_RELAY_KEEP = "RELAY: Keeping ERB relays 6 and 7 closed (keep_relay_closed=True)"
INFO_HIPOT_SEQ_FAILED = "HIPOT: Test sequence failed: {error}"
INFO_HIPOT_EMERGENCY_SHUTDOWN = "Emergency relay shutdown due to test failure"
INFO_HIPOT_ERB_OPENING_R6 = "Failed to open ERB relay 6 directly; attempting all_off()"

# ---- Measurement Messages ----
INFO_MEAS_TIMEOUT_LOG = "Measurement read timed out after {timeout} seconds"

# ---- Simulation Messages ----
SIM_OPEN_FLUKE287 = "SIM: Open Fluke 287 on {port} @ {baud} baud"
SIM_CLOSE_FLUKE287 = "SIM: Close Fluke 287"
SIM_TX = "SIM: TX -> {command}"
SIM_RX = "SIM: RX <- {response}"


# =================================================================================
# HELPER FUNCTIONS
# =================================================================================

def format_error(template: str, **kwargs) -> str:
    """
    Format an error message template with provided keyword arguments.
    
    Args:
        template: Error message template with {placeholders}
        **kwargs: Values to substitute into placeholders
        
    Returns:
        Formatted error message string
        
    Example:
        format_error(ERROR_ERB08_SET_RELAY, bit=3, state=True, error="timeout")
        # Returns: "Failed to set relay 3 -> True: timeout"
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"{template} (Missing placeholder: {e})"


def format_info(template: str, **kwargs) -> str:
    """
    Format an informational message template with provided keyword arguments.
    
    Args:
        template: Info message template with {placeholders}
        **kwargs: Values to substitute into placeholders
        
    Returns:
        Formatted info message string
        
    Example:
        format_info(INFO_RELAY_PIN1TO6_CLOSED, delay=200)
        # Returns: "RELAY: Pin1to6 closed with 200ms settling delay"
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"{template} (Missing placeholder: {e})"
