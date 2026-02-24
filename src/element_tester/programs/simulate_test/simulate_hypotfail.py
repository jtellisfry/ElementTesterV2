"""Direct-to-testing simulation for HIPOT fail retry logic.

Behavior:
- Skips scanning and configuration windows.
- Defaults configuration to 208V / 7000W.
- Forces measurement section to PASS with in-range simulated values.
- Forces HIPOT section to FAIL.

Purpose:
- Exercise Continue/Retry/Exit behavior for HIPOT fail handling.

Run from project root (PowerShell):
    & ".venv/Scripts/python.exe" src/element_tester/programs/simulate_test/simulate_hypotfail.py
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer

# Ensure src on path
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.core.test_runner import TestRunner
from element_tester.system.ui.testing import MainTestWindow
from element_tester.system.ui.configuration_ui import ConfigurationWindow


# -----------------------------------------------------------------------------
# Monkey patches for this simulation only
# -----------------------------------------------------------------------------
_original_run_measuring = TestRunner.run_measuring
_original_run_hipot = TestRunner.run_hipot


def _patched_run_measuring(self, ui, work_order, part_number):
    """Force measurement PASS with in-range values for 208V/7000W."""
    self.log.info("MEAS start (FORCED PASS) | WO=%s | PN=%s", work_order, part_number)

    # 208/7000 expected range from configuration mapping
    rmin, rmax = ConfigurationWindow.RESISTANCE_RANGE.get((208, 7000), (9.1, 9.8))

    # In-range simulated values
    left_vals = [9.3, 9.4, 9.5]
    right_vals = [9.3, 9.4, 9.5]
    row_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]

    try:
        ui.append_measurement_log(f"Expected resistance for 208V/7000W: {rmin:.2f} - {rmax:.2f} Ω")
    except Exception:
        pass

    for idx in range(3):
        l_val = left_vals[idx]
        r_val = right_vals[idx]
        l_pass = rmin <= l_val <= rmax
        r_pass = rmin <= r_val <= rmax

        ui.update_measurement("L", idx, f"{row_names[idx]}: {l_val:.2f} Ω", l_pass)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.3)

        ui.update_measurement("R", idx, f"{row_names[idx]}: {r_val:.2f} Ω", r_pass)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.3)

    values = {
        "LP1to6": left_vals[0],
        "LP2to5": left_vals[1],
        "LP3to4": left_vals[2],
        "RP1to6": right_vals[0],
        "RP2to5": right_vals[1],
        "RP3to4": right_vals[2],
    }

    detail = {
        "passed": True,
        "message": "All measurements within limits (simulated)",
        "values": values,
    }
    self.log.info("MEAS end (FORCED PASS)")
    return True, detail["message"], detail


def _patched_run_hipot(self, ui, work_order, part_number, simulate=False, keep_relay_closed=False):
    """Force HIPOT FAIL to drive retry dialog logic."""
    self.log.info("HIPOT start (FORCED FAIL) | WO=%s | PN=%s", work_order, part_number)

    if ui is None:
        return False, "UI not available", {"passed": False, "message": "UI not available", "raw_result": "UI_ERROR"}

    ui.hypot_ready()
    time.sleep(0.2)
    ui.hypot_running()
    QtWidgets.QApplication.processEvents()

    ui.append_hypot_log("Checking Hipot connections...")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.4)

    ui.append_hypot_log("Step 1/5: Reset instrument (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.5)
    ui.append_hypot_log("Step 2/5: Configure relay (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.5)
    ui.append_hypot_log("Step 3/5: Configure hipot test (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.5)
    ui.append_hypot_log("Step 4/5: Execute hipot test (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.8)
    ui.append_hypot_log("Step 5/5: Disable relay (SIM)")
    QtWidgets.QApplication.processEvents()
    time.sleep(0.4)

    passed = False
    msg = "Simulated Hipot FAIL - Current trip detected"

    ui.hypot_result(passed)
    QtWidgets.QApplication.processEvents()
    ui.append_hypot_log(f"Result: FAIL ({msg})")

    detail = {
        "passed": passed,
        "message": msg,
        "raw_result": "FAIL",
    }
    self.log.info("HIPOT end (FORCED FAIL)")
    return passed, msg, detail


TestRunner.run_measuring = _patched_run_measuring
TestRunner.run_hipot = _patched_run_hipot


# -----------------------------------------------------------------------------
# Direct-to-testing app startup
# -----------------------------------------------------------------------------
def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    runner = TestRunner(simulate=True)

    resistance_range = ConfigurationWindow.RESISTANCE_RANGE.get((208, 7000), (9.1, 9.8))
    runner._selected_config = {
        "voltage": 208,
        "wattage": 7000,
        "resistance_range": resistance_range,
    }

    test_window = MainTestWindow()
    test_window.show()

    # No scan screen in this simulator
    setattr(runner, "_return_to_scan_callback", lambda: None)

    print("=== Simulate HIPOT Fail (Direct Testing) ===")
    print("Mode: skip scan + skip config")
    print("Default config: 208V / 7000W")
    print("Measurement: forced PASS (in range)")
    print("HIPOT: forced FAIL")
    print("===========================================")

    QTimer.singleShot(
        400,
        lambda: runner.run_full_sequence(
            ui=test_window,
            work_order="SIM_HIPOTFAIL_WO",
            part_number="SIM_HIPOTFAIL_PN",
        ),
    )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
