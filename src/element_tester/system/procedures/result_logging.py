"""
Result logging module for Element Tester.

This module handles logging test results to session-based log files.
Each test session (when user enters work order and part number) creates a new file.

Files are stored with naming convention:
- ET_ELOV0001.txt, ET_ELOV0002.txt, etc.

MULTI-TESTER COORDINATION:
The sequence number is determined by checking the REMOTE location (L drive) first.
This remote location is shared by all testers and contains results from ALL testers,
ensuring unique sequence numbers even when multiple testers run simultaneously.

Each tester writes results to TWO locations:
1. LOCAL: data/results/ (only this tester's results)
2. REMOTE: L:\Test Engineering\...\data (ALL testers' results - AUTHORITATIVE)

The remote location serves as the single source of truth for sequence numbering,
preventing collisions across multiple testers in the facility.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import logging
import re

from .system_info import get_computer_name

log = logging.getLogger("element_tester.result_logging")

# Remote/network log location - PRIMARY source for sequence numbering.
# This location is shared across all testers to ensure unique, coordinated numbering.
# Each tester writes to both this remote location AND its local data/results/ folder.
# Sequence numbers are determined by checking this remote location FIRST.
REMOTE_LOG_PATH = Path(r"L:\Test Engineering\Tester Information\ElementTesterV2(Python)\ElementTesterV2\data")

# Additional mirror log locations (network/share/local backups).
# Add/remove entries as needed. Failures on any mirror path are non-fatal.
MIRROR_LOG_PATHS: tuple[Path, ...] = (
    REMOTE_LOG_PATH,
)

# Module-level session state
_current_session: "TestSession | None" = None


class TestSession:
    """
    Manages a single test session log file.
    
    A session starts when the user enters a work order and part number,
    and logs all test attempts (including retries) to a single file.
    
    Writes to the primary results_dir and any configured mirror locations.
    """
    
    def __init__(self, results_dir: Path, work_order: str, part_number: str, configuration: dict | None = None):
        self.results_dir = results_dir
        self.work_order = work_order
        self.part_number = part_number
        self.configuration = configuration
        self.start_time = datetime.now()
        
        # Get next sequence number (coordinated via remote L drive location)
        self.sequence_num = _get_next_sequence_number(results_dir)
        self.filename = f"ET_ELOV{self.sequence_num:04d}.txt"
        
        # Set up target file paths: local + remote
        self.filepath = results_dir / self.filename  # Local tester location
        self._target_filepaths = [self.filepath]
        self._target_filepaths.extend([mirror_path / self.filename for mirror_path in MIRROR_LOG_PATHS])
        
        # Track attempts
        self.hipot_attempts: list[dict] = []
        self.measurement_attempts: list[dict] = []
        self.final_result: str | None = None
        
        # Write session header
        self._write_header()
        
        log.info(f"Started new test session: {self.filename} (writing to {len(self._target_filepaths)} locations)")
    
    def _write_header(self) -> None:
        """Write the session header to all configured target locations."""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        header_lines = []
        header_lines.append("=" * 70 + "\n")
        header_lines.append("ELEMENT TESTER - TEST SESSION LOG\n")
        header_lines.append("=" * 70 + "\n")
        header_lines.append(f"Session ID:    {self.filename.replace('.txt', '')}\n")
        header_lines.append(f"Start Time:    {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        header_lines.append(f"Computer:      {get_computer_name()}\n")
        header_lines.append(f"Work Order:    {self.work_order}\n")
        header_lines.append(f"Part Number:   {self.part_number}\n")
        if self.configuration:
            header_lines.append(f"Configuration: {self.configuration}\n")
        header_lines.append("-" * 70 + "\n\n")
        
        header_content = "".join(header_lines)
        
        self._write_to_targets(header_content, mode="w")
    
    def _write_to_targets(self, content: str, mode: str = "a") -> int:
        """
        Write content to all configured target locations.
        
        Any individual target may fail without stopping the test flow.
        If remote location is unavailable, continues with local-only mode.
        
        Args:
            content: Text content to write
            mode: File mode ('w' for write/overwrite, 'a' for append)

        Returns:
            Number of target files successfully written.
        """
        success_count = 0
        remote_success = False
        local_success = False
        
        for target_path in self._target_filepaths:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with target_path.open(mode, encoding="utf-8") as f:
                    f.write(content)
                success_count += 1
                
                # Track whether local or remote writes succeeded
                if target_path == self.filepath:
                    local_success = True
                else:
                    remote_success = True
                    
            except Exception as e:
                log.warning(f"Could not write to log target {target_path}: {e}")

        if success_count == 0:
            log.error("Failed to write log content to all configured targets (local AND remote)")
        elif not remote_success and local_success:
            log.debug("Remote location unavailable - logging to local only")
            
        return success_count
    
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
        
        self._write_to_targets(content)
        
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
        
        self._write_to_targets(content)
        
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
        
        self._write_to_targets(content)
        
        log.info(f"Finalized session {self.filename}: {self.final_result}")


def _get_next_sequence_number(results_dir: Path) -> int:
    """
    Get the next sequence number for log files.
    
    PRIORITY: Checks REMOTE_LOG_PATH first (L drive) as the authoritative source.
    This ensures all testers coordinate and avoid collisions, since the remote
    location contains results from ALL testers across the facility.
    
    FALLBACK: If remote location is unavailable, uses local results directory only.
    When remote becomes available again, automatically resumes with remote numbering.
    
    Returns the next available sequence number that doesn't exist in ANY location.
    """
    results_dir.mkdir(parents=True, exist_ok=True)

    # Find all existing ET_ELOV*.txt files across all configured locations
    pattern = re.compile(r"ET_ELOV(\d{4})\.txt$")
    max_num = 0
    remote_available = False

    # PRIORITY 1: Check remote/network location first (L drive)
    # This is the primary source of truth shared by all testers
    for directory in MIRROR_LOG_PATHS:
        try:
            log.debug(f"Checking remote location for sequence numbers: {directory}")
            if directory.exists():
                for file in directory.glob("ET_ELOV*.txt"):
                    match = pattern.match(file.name)
                    if match:
                        num = int(match.group(1))
                        max_num = max(max_num, num)
                remote_available = True
                log.info(f"Remote location accessible - max sequence: {max_num}")
            else:
                log.warning(f"Remote location not accessible: {directory}")
        except Exception as e:
            # Unavailable/missing remote paths are logged but not fatal
            log.warning(f"Could not access remote log location {directory}: {e}")
            continue

    # PRIORITY 2: Check local results directory
    # If remote unavailable, this becomes the primary source
    # If remote available, this is checked for safety
    try:
        log.debug(f"Checking local location for sequence numbers: {results_dir}")
        for file in results_dir.glob("ET_ELOV*.txt"):
            match = pattern.match(file.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
        log.debug(f"After local check, max sequence: {max_num}")
    except Exception as e:
        log.warning(f"Could not access local results directory {results_dir}: {e}")

    if not remote_available:
        log.warning("Remote location unavailable - using local numbering only. Will sync when reconnected.")

    candidate = max_num + 1

    # Extra safety: ensure candidate doesn't already exist in any accessible target.
    # Check remote location first (if available), then local.
    while True:
        filename = f"ET_ELOV{candidate:04d}.txt"
        in_use = False
        
        # Check remote location(s) first (if accessible)
        for directory in MIRROR_LOG_PATHS:
            try:
                if directory.exists() and (directory / filename).exists():
                    in_use = True
                    break
            except Exception:
                continue
        
        # Check local location
        if not in_use:
            try:
                if (results_dir / filename).exists():
                    in_use = True
            except Exception:
                pass

        if not in_use:
            log.info(f"Next sequence number determined: {candidate} (remote {'available' if remote_available else 'UNAVAILABLE - using local only'})")
            return candidate
        candidate += 1


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
