"""
Result logging module for Element Tester.

This module handles logging test results to session-based log files.
Each test session (when user enters work order and part number) creates a new file.

Files are stored in data/results/ with naming convention:
- ET_ELOV0001.txt, ET_ELOV0002.txt, etc.

The sequence number persists across application restarts via a tracking file.

Additionally, logs are written to a secondary network location:
- I:\\AssemblyTester\\ElementTester\\TestLog
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import logging
import re

log = logging.getLogger("element_tester.result_logging")

# Secondary log location (network share for backup/archival)
SECONDARY_LOG_PATH = Path(r"I:\AssemblyTester\ElementTester\TestLog")

# Module-level session state
_current_session: "TestSession | None" = None


class TestSession:
    """
    Manages a single test session log file.
    
    A session starts when the user enters a work order and part number,
    and logs all test attempts (including retries) to a single file.
    
    Writes to both the primary results_dir and a secondary network location.
    """
    
    def __init__(self, results_dir: Path, work_order: str, part_number: str, configuration: dict | None = None):
        self.results_dir = results_dir
        self.work_order = work_order
        self.part_number = part_number
        self.configuration = configuration
        self.start_time = datetime.now()
        
        # Get next sequence number and create file
        self.sequence_num = _get_next_sequence_number(results_dir)
        self.filename = f"ET_ELOV{self.sequence_num:04d}.txt"
        self.filepath = results_dir / self.filename
        
        # Secondary log path (network location)
        self.secondary_filepath = SECONDARY_LOG_PATH / self.filename
        
        # Track attempts
        self.hipot_attempts: list[dict] = []
        self.measurement_attempts: list[dict] = []
        self.final_result: str | None = None
        
        # Write session header
        self._write_header()
        
        log.info(f"Started new test session: {self.filename}")
    
    def _write_header(self) -> None:
        """Write the session header to the log file (both primary and secondary)."""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        header_lines = []
        header_lines.append("=" * 70 + "\n")
        header_lines.append("ELEMENT TESTER - TEST SESSION LOG\n")
        header_lines.append("=" * 70 + "\n")
        header_lines.append(f"Session ID:    {self.filename.replace('.txt', '')}\n")
        header_lines.append(f"Start Time:    {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        header_lines.append(f"Work Order:    {self.work_order}\n")
        header_lines.append(f"Part Number:   {self.part_number}\n")
        if self.configuration:
            header_lines.append(f"Configuration: {self.configuration}\n")
        header_lines.append("-" * 70 + "\n\n")
        
        header_content = "".join(header_lines)
        
        # Write to primary location
        with self.filepath.open("w", encoding="utf-8") as f:
            f.write(header_content)
        
        # Write to secondary location (network)
        self._write_to_secondary(header_content, mode="w")
    
    def _write_to_secondary(self, content: str, mode: str = "a") -> None:
        """
        Write content to the secondary log location (network share).
        
        Silently fails if the network location is unavailable to avoid
        disrupting the primary logging flow.
        
        Args:
            content: Text content to write
            mode: File mode ('w' for write/overwrite, 'a' for append)
        """
        try:
            SECONDARY_LOG_PATH.mkdir(parents=True, exist_ok=True)
            with self.secondary_filepath.open(mode, encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            log.warning(f"Could not write to secondary log location: {e}")
    
    def log_hipot_attempt(self, passed: bool, message: str, raw_result: str | None = None) -> None:
        """
        Log a hipot test attempt (pass or fail).
        
        Args:
            passed: True if the hipot test passed
            message: Result message
            raw_result: Raw result string from the instrument (optional)
        """
        attempt_num = len(self.hipot_attempts) + 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        attempt_data = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "passed": passed,
            "message": message,
            "raw_result": raw_result,
        }
        self.hipot_attempts.append(attempt_data)
        
        # Build content for logging
        lines = []
        lines.append(f"[{timestamp}] HIPOT TEST - Attempt #{attempt_num}\n")
        lines.append(f"    Result: {'PASS' if passed else 'FAIL'}\n")
        lines.append(f"    Message: {message}\n")
        if raw_result:
            lines.append(f"    Raw: {raw_result}\n")
        lines.append("\n")
        content = "".join(lines)
        
        # Write to primary location
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(content)
        
        # Write to secondary location (network)
        self._write_to_secondary(content)
        
        log.info(f"Logged hipot attempt #{attempt_num}: {'PASS' if passed else 'FAIL'}")
    
    def log_measurement_attempt(
        self,
        passed: bool,
        message: str,
        values: dict | None = None,
    ) -> None:
        """
        Log a measurement test attempt with pin values.
        
        Args:
            passed: True if all measurements passed
            message: Result message
            values: Dictionary with measurement values:
                    LP1to6, LP2to5, LP3to4, RP1to6, RP2to5, RP3to4
        """
        attempt_num = len(self.measurement_attempts) + 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        attempt_data = {
            "attempt": attempt_num,
            "timestamp": timestamp,
            "passed": passed,
            "message": message,
            "values": values or {},
        }
        self.measurement_attempts.append(attempt_data)
        
        # Build content for logging
        lines = []
        lines.append(f"[{timestamp}] MEASUREMENT TEST - Attempt #{attempt_num}\n")
        lines.append(f"    Result: {'PASS' if passed else 'FAIL'}\n")
        lines.append(f"    Message: {message}\n")
        if values:
            lines.append("    Pin Readings:\n")
            lines.append(f"        Pin 1 to 6 (L): {values.get('LP1to6', '---')}\n")
            lines.append(f"        Pin 2 to 5 (L): {values.get('LP2to5', '---')}\n")
            lines.append(f"        Pin 3 to 4 (L): {values.get('LP3to4', '---')}\n")
            lines.append(f"        Pin 1 to 6 (R): {values.get('RP1to6', '---')}\n")
            lines.append(f"        Pin 2 to 5 (R): {values.get('RP2to5', '---')}\n")
            lines.append(f"        Pin 3 to 4 (R): {values.get('RP3to4', '---')}\n")
        lines.append("\n")
        content = "".join(lines)
        
        # Write to primary location
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(content)
        
        # Write to secondary location (network)
        self._write_to_secondary(content)
        
        log.info(f"Logged measurement attempt #{attempt_num}: {'PASS' if passed else 'FAIL'}")
    
    def finalize(self, overall_pass: bool, final_message: str = "") -> None:
        """
        Finalize the test session with the overall result.
        
        Args:
            overall_pass: True if the entire test session passed
            final_message: Optional final message/notes
        """
        end_time = datetime.now()
        duration = end_time - self.start_time
        self.final_result = "PASS" if overall_pass else "FAIL"
        
        # Build content for logging
        lines = []
        lines.append("-" * 70 + "\n")
        lines.append("SESSION SUMMARY\n")
        lines.append("-" * 70 + "\n")
        lines.append(f"End Time:      {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Duration:      {duration.total_seconds():.1f} seconds\n")
        lines.append(f"Hipot Attempts:       {len(self.hipot_attempts)}\n")
        lines.append(f"Measurement Attempts: {len(self.measurement_attempts)}\n")
        lines.append(f"\nFINAL RESULT: {self.final_result}\n")
        if final_message:
            lines.append(f"Notes: {final_message}\n")
        lines.append("=" * 70 + "\n")
        content = "".join(lines)
        
        # Write to primary location
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(content)
        
        # Write to secondary location (network)
        self._write_to_secondary(content)
        
        log.info(f"Finalized session {self.filename}: {self.final_result}")


def _get_next_sequence_number(results_dir: Path) -> int:
    """
    Get the next sequence number for log files.
    
    Scans existing ET_ELOV*.txt files to find the highest number,
    then returns that + 1.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all existing ET_ELOV*.txt files
    pattern = re.compile(r"ET_ELOV(\d{4})\.txt$")
    max_num = 0
    
    for file in results_dir.glob("ET_ELOV*.txt"):
        match = pattern.match(file.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return max_num + 1


def start_test_session(
    results_dir: Path,
    work_order: str,
    part_number: str,
    configuration: dict | None = None,
) -> TestSession:
    """
    Start a new test session when user enters work order and part number.
    
    Creates a new log file with incrementing sequence number.
    
    Args:
        results_dir: Path to results directory (usually data/results/)
        work_order: Work order number entered by user
        part_number: Part number entered by user
        configuration: Optional configuration dict
    
    Returns:
        TestSession object for logging test attempts
    """
    global _current_session
    
    # If there's an existing session that wasn't finalized, finalize it as incomplete
    if _current_session is not None and _current_session.final_result is None:
        _current_session.finalize(False, "Session ended without completion (new session started)")
    
    _current_session = TestSession(results_dir, work_order, part_number, configuration)
    return _current_session


def get_current_session() -> TestSession | None:
    """Get the current active test session, if any."""
    return _current_session


def log_hipot_result(passed: bool, message: str, raw_result: str | None = None) -> None:
    """
    Log a hipot test result to the current session.
    
    Args:
        passed: True if the hipot test passed
        message: Result message
        raw_result: Raw result string from the instrument
    """
    if _current_session is None:
        log.warning("No active test session - hipot result not logged to session file")
        return
    
    _current_session.log_hipot_attempt(passed, message, raw_result)


def log_measurement_result(passed: bool, message: str, values: dict | None = None) -> None:
    """
    Log a measurement test result to the current session.
    
    Args:
        passed: True if measurements passed
        message: Result message
        values: Dictionary with pin measurement values
    """
    if _current_session is None:
        log.warning("No active test session - measurement result not logged to session file")
        return
    
    _current_session.log_measurement_attempt(passed, message, values)


def finalize_session(overall_pass: bool, final_message: str = "") -> None:
    """
    Finalize the current test session.
    
    Args:
        overall_pass: True if the entire test passed
        final_message: Optional notes/message
    """
    global _current_session
    
    if _current_session is None:
        log.warning("No active test session to finalize")
        return
    
    _current_session.finalize(overall_pass, final_message)
    _current_session = None


# Legacy function for backwards compatibility with existing test_runner._log_result
def log_test_result(
    results_dir: Path,
    work_order: str,
    part_number: str,
    hypot_info: dict,
    meas_info: dict,
    overall_pass: bool,
    mode: str = "normal",
    configuration: dict | None = None,
) -> None:
    """
    Legacy function - now finalizes the current session.
    
    This is called at the end of a test sequence to record the final result.
    Individual hipot and measurement attempts should be logged via
    log_hipot_result() and log_measurement_result() as they occur.
    """
    global _current_session
    
    # If no session exists, create one for backwards compatibility
    if _current_session is None:
        _current_session = TestSession(results_dir, work_order, part_number, configuration)
        
        # Log the final results as single attempts
        if hypot_info:
            _current_session.log_hipot_attempt(
                passed=hypot_info.get("passed", False),
                message=hypot_info.get("message", ""),
                raw_result=hypot_info.get("raw_result"),
            )
        
        if meas_info:
            _current_session.log_measurement_attempt(
                passed=meas_info.get("passed", False),
                message=meas_info.get("message", ""),
                values=meas_info.get("values"),
            )
    
    # Finalize the session
    final_msg = f"Mode: {mode}"
    _current_session.finalize(overall_pass, final_msg)
    _current_session = None
    
    log.info(f"Logged final test result: WO={work_order}, PN={part_number}, PASS={overall_pass}")
