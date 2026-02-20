from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
import logging
import time
import json
from datetime import datetime
import sys
import concurrent.futures


# Make sure .../src is on sys.path so `element_tester` is importable
SRC_ROOT = Path(__file__).resolve().parents[3]  # .../Element_Tester/src
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from element_tester.system.ui.testing import MainTestWindow
from element_tester.system.procedures.result_logging import (
    log_test_result,
    start_test_session,
    log_hipot_result,
    log_measurement_result,
    finalize_session,
)
from PyQt6 import QtWidgets  # For QApplication.processEvents()

# Optional hipot driver (still supports simulate mode if missing)
try:
    from element_tester.system.drivers.HYPOT3865.procedures import AR3865Procedures, HipotConfig
    from element_tester.system.drivers.HYPOT3865.driver import AR3865Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import AR3865 drivers: {e}", exc_info=True)
    AR3865Procedures = None
    HipotConfig = None
    AR3865Driver = None

# Optional ERB relay driver (used for measurements)
try:
    from element_tester.system.drivers.MCC_ERB.driver import ERB08Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ERB08Driver: {e}", exc_info=True)
    ERB08Driver = None

# Optional PDIS relay driver (used only for hipot sequences)
try:
    from element_tester.system.drivers.MCC_PDIS.driver import PDIS08Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import PDIS08Driver: {e}", exc_info=True)
    PDIS08Driver = None

# Optional hipot test sequence
try:
    from element_tester.programs.hipot_test.test import HipotTestSequence
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import HipotTestSequence: {e}", exc_info=True)
    HipotTestSequence = None

# Optional measurement test sequence
try:
    from element_tester.programs.measurement_test.test import MeasurementTestSequence
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import MeasurementTestSequence: {e}", exc_info=True)
    MeasurementTestSequence = None

# Continue/Exit dialog widget
try:
    from element_tester.system.widgets.continue_exit import ContinueExitDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ContinueExitDialog: {e}", exc_info=True)
    ContinueExitDialog = None

# Continue/Retry/Exit dialog widget (for hipot test)
try:
    from element_tester.system.widgets.continue_retry_exit import ContinueRetryExitDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import ContinueRetryExitDialog: {e}", exc_info=True)
    ContinueRetryExitDialog = None

# Test Passed dialog widget
try:
    from element_tester.system.widgets.test_passed import TestPassedDialog
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import TestPassedDialog: {e}", exc_info=True)
    TestPassedDialog = None

# Optional meter drivers
try:
    from element_tester.system.drivers.FLUKE287.driver import Fluke287Driver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import Fluke287Driver: {e}", exc_info=True)
    Fluke287Driver = None

try:
    from element_tester.system.drivers.UT61E.driver import UT61EDriver
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import UT61EDriver: {e}", exc_info=True)
    UT61EDriver = None

# Optional measurement procedures
try:
    import element_tester.system.procedures.measurement_test_procedures as meas_procs
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import measurement_test_procedures: {e}", exc_info=True)
    meas_procs = None

# Optional print helper for QC stickers (module-level import)
try:
    import element_tester.system.procedures.print_qc as print_qc
except Exception:
    print_qc = None

# Settings manager for config-based driver selection
try:
    from element_tester.system.procedures.settings_manager import (
        get_relay_driver_from_config,
        get_meter_driver_from_config,
        get_meter_params_from_config,
    )
except Exception as e:
    logging.getLogger("element_tester.runner").error(f"Failed to import settings_manager: {e}", exc_info=True)
    get_relay_driver_from_config = None
    get_meter_driver_from_config = None
    get_meter_params_from_config = None


def should_use_simulate_mode(work_order: str, part_number: str) -> bool:
    """
    Central rule: return True to force simulate/demo mode for a given WO/PN.

    Default rule: WO == "TEST" and PN == "TEST" (case-insensitive).
    Add other tuples to TEST_COMBOS below when you want other shortcuts.
    """
    if not work_order or not part_number:
        return False
    wo = work_order.strip().lower()
    pn = part_number.strip().lower()

    TEST_COMBOS = {
        ("test", "test"),
        ("demo", "demo"),
    }
    return (wo, pn) in TEST_COMBOS


class TestRunner:
    """
    Orchestrates the high-level test sequence and logs results.

    - Normal flow: Hipot -> Measuring
    - Special flow: if WO == 'test' and PN == 'test' -> demo-only visual run
    """

    def __init__( 
        self,
        simulate: bool = False,
        hipot_resource: str = "serial://COM6",
        hipot_baud: int = 38400,
        relay_board_num: int = 0,
        relay_port_low: int = 12,
        relay_port_high: int = 13,
        logger: Optional[logging.Logger] = None,
        results_dir: Path | None = None,
    ):
        self.log = logger or logging.getLogger("element_tester.runner")
        self.simulate = simulate
        # store default connection params so run_full_sequence can create drivers
        self.hipot_resource = hipot_resource
        self.hipot_baud = hipot_baud
        self.relay_board_num = relay_board_num
        self.relay_port_low = relay_port_low
        self.relay_port_high = relay_port_high

        if results_dir is None:
            # Absolute path to ensure consistent logging regardless of working directory
            self.results_dir = Path(r"C:\Files\ElementTester\ElementTesterV2\data\results")
        else:
            self.results_dir = results_dir

        # Initialize drivers
        self.hipot_driver = None
        self.relay_driver = None
        self.hipot_test_seq = None
        self.meter_driver = None
        self.measurement_test_seq = None
        
        self.log.info(f"TestRunner.__init__ | simulate={simulate} | ERB08Driver={ERB08Driver is not None} | PDIS08Driver={PDIS08Driver is not None} | AR3865Driver={AR3865Driver is not None} | HipotTestSequence={HipotTestSequence is not None} | Fluke287Driver={Fluke287Driver is not None} | UT61EDriver={UT61EDriver is not None} | MeasurementTestSequence={MeasurementTestSequence is not None}")
        
        if not simulate:
            # Initialize relay driver based on config file
            relay_choice = "MCC_ERB"  # Default
            if get_relay_driver_from_config is not None:
                try:
                    relay_choice = get_relay_driver_from_config()
                    self.log.info(f"Config file relay driver choice: {relay_choice}")
                except Exception as e:
                    self.log.warning(f"Failed to read relay driver from config, using default MCC_ERB: {e}")
            else:
                self.log.warning("SettingsManager not available, using default MCC_ERB")
            
            # Initialize the selected relay driver
            if relay_choice == "MCC_PDIS" and PDIS08Driver is not None:
                try:
                    self.relay_driver = PDIS08Driver(
                        board_num=1,
                        port_low=1,
                        port_high=None,
                        simulate=simulate,
                        logger=self.log
                    )
                    self.relay_driver.initialize()
                    self.log.info("✓ Relay (MCC_PDIS) driver initialized")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize MCC_PDIS relay driver: {e}", exc_info=True)
                    self.relay_driver = None  # Clear the partially-initialized driver
            elif relay_choice == "MCC_ERB" and ERB08Driver is not None:
                try:
                    self.relay_driver = ERB08Driver(
                        board_num=relay_board_num,
                        port_low=relay_port_low,
                        port_high=relay_port_high,
                        simulate=simulate
                    )
                    self.relay_driver.initialize()
                    self.log.info("✓ Relay (MCC_ERB) driver initialized")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize MCC_ERB relay driver: {e}", exc_info=True)
                    self.relay_driver = None  # Clear the partially-initialized driver
            else:
                if relay_choice == "MCC_PDIS":
                    self.log.error("✗ PDIS08Driver not available (import failed)")
                else:
                    self.log.error("✗ ERB08Driver not available (import failed)")
            
            # Initialize hipot driver
            if AR3865Driver is not None:
                try:
                    self.hipot_driver = AR3865Driver(
                        resource=hipot_resource,
                        simulate=simulate
                    )
                    self.hipot_driver.initialize()
                    idn = self.hipot_driver.idn()
                    self.log.info(f"✓ Hipot driver initialized: {idn}")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize hipot driver: {e}", exc_info=True)
                    self.hipot_driver = None  # Clear the partially-initialized driver
            else:
                self.log.error("✗ AR3865Driver not available (import failed)")
            
            # Create hipot test sequence if both drivers available
            # For hipot test sequence use the PDIS relay driver if available,
            # otherwise fall back to the ERB relay driver.
            # Create HipotTestSequence using the ERB relay driver only.
            if self.relay_driver and self.hipot_driver and HipotTestSequence:
                try:
                    self.hipot_test_seq = HipotTestSequence(
                        relay_driver=self.relay_driver,
                        hipot_driver=self.hipot_driver,
                        logger=self.log
                    )
                    self.log.info("✓ HipotTestSequence initialized - REAL HARDWARE MODE ACTIVE (PDIS logic removed)")
                except Exception as e:
                    self.log.error(f"✗ Failed to create HipotTestSequence: {e}", exc_info=True)
            else:
                self.log.error(f"✗ Cannot create HipotTestSequence - relay={self.relay_driver is not None}, hipot={self.hipot_driver is not None}, seq_class={HipotTestSequence is not None}")
            
            # Initialize meter driver based on config file
            meter_choice = "FLUKE287"  # Default
            meter_params = None
            if get_meter_driver_from_config is not None and get_meter_params_from_config is not None:
                try:
                    meter_choice = get_meter_driver_from_config()
                    meter_params = get_meter_params_from_config()
                    self.log.info(f"Config file meter driver choice: {meter_choice}")
                except Exception as e:
                    self.log.warning(f"Failed to read meter driver from config, using default FLUKE287: {e}")
            else:
                self.log.warning("SettingsManager not available, using default FLUKE287")
            
            # Initialize the selected meter driver
            if meter_choice == "FLUKE287" and Fluke287Driver is not None:
                try:
                    port = meter_params.fluke_port if meter_params else "COM11"
                    timeout = meter_params.fluke_timeout if meter_params else 2.0
                    self.meter_driver = Fluke287Driver(
                        port=port,
                        timeout=timeout,
                        simulate=simulate,
                        logger=self.log
                    )
                    self.meter_driver.initialize()
                    self.log.info(f"✓ Meter driver initialized (Fluke 287 on {port})")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize Fluke287 meter driver: {e}", exc_info=True)
            elif meter_choice == "UT61E" and UT61EDriver is not None:
                try:
                    vendor_id = meter_params.ut61e_vendor_id if meter_params else 0x1a86
                    product_id = meter_params.ut61e_product_id if meter_params else 0xe429
                    serial_number = meter_params.ut61e_serial_number if meter_params else None
                    self.meter_driver = UT61EDriver(
                        vendor_id=vendor_id,
                        product_id=product_id,
                        serial_number=serial_number,
                        simulate=simulate,
                        logger=self.log
                    )
                    self.meter_driver.initialize()
                    self.log.info(f"✓ Meter driver initialized (UT61E VID={hex(vendor_id)} PID={hex(product_id)})")
                except Exception as e:
                    self.log.error(f"✗ Failed to initialize UT61E meter driver: {e}", exc_info=True)
            else:
                if meter_choice == "FLUKE287":
                    self.log.error("✗ Fluke287Driver not available (import failed)")
                else:
                    self.log.error("✗ UT61EDriver not available (import failed)")
            
            # Create measurement test sequence if both drivers available
            if self.relay_driver and self.meter_driver and MeasurementTestSequence:
                try:
                    self.measurement_test_seq = MeasurementTestSequence(
                        relay_driver=self.relay_driver,
                        meter_driver=self.meter_driver,
                        logger=self.log,
                        simulate=simulate
                    )
                    self.log.info("✓ MeasurementTestSequence initialized - REAL HARDWARE MODE ACTIVE")
                except Exception as e:
                    self.log.error(f"✗ Failed to create MeasurementTestSequence: {e}", exc_info=True)
            else:
                self.log.error(f"✗ Cannot create MeasurementTestSequence - relay={self.relay_driver is not None}, meter={self.meter_driver is not None}, seq_class={MeasurementTestSequence is not None}")
        else:
            self.log.info("TestRunner using SIMULATE mode (simulate=True in __init__)")

    def _reset_hardware(self) -> None:
        """
        Reset all hardware to safe state after test completion.
        Opens all relays and resets hipot instrument.
        """
        # Open all relays
        if self.relay_driver:
            try:
                self.log.info("Resetting hardware: Opening all relays")
                self.relay_driver.all_off()
            except Exception as e:
                self.log.error(f"Failed to open relays during reset: {e}", exc_info=True)
        
        # Reset hipot instrument (if available and has reset method)
        if self.hipot_driver:
            try:
                self.log.info("Resetting hardware: Resetting hipot instrument")
                # Most hipot instruments don't need explicit reset, but we can ensure relays are open
                if self.hipot_test_seq and hasattr(self.hipot_test_seq, 'open_relay'):
                    self.hipot_test_seq.open_relay()
            except Exception as e:
                self.log.error(f"Failed to reset hipot during cleanup: {e}", exc_info=True)
        
        self.log.info("Hardware reset complete")

    def _select_hypot_file_index(self, work_order: str, part_number: str) -> int:
        """
        Decide which instrument test file to use.

        Current rule: Always return 1 when WO/PN have any input.
        We'll add if/else mapping later per your logic.
        """
        # Inspect the operator-selected configuration when available.
        # If the operator selected 440V or 480V use FL 2 on the hipot instrument.
        try:
            cfg = getattr(self, "_selected_config", None)
            if cfg and isinstance(cfg, dict):
                voltage = cfg.get("voltage")
                if voltage is not None:
                    try:
                        v = int(voltage)
                        if v in (440, 480):
                            return 2
                    except Exception:
                        pass
        except Exception:
            pass
        return 1

    # --------------- PUBLIC ENTRY ---------------
    def run_full_sequence(
        self,
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str]:
        """
        Top-level: decides which branch to run, logs results.
        """

        wo = work_order.strip()
        pn = part_number.strip()

        # Ensure a configuration has been selected. Some callers may not show
        # the configuration dialog before calling `run_full_sequence()`; in
        # that case open the dialog here so the full flow (scanning ->
        # configuration -> testing) is preserved.
        if not getattr(self, "_selected_config", None):
            try:
                from element_tester.system.ui.configuration_ui import ConfigurationWindow
                cfg = ConfigurationWindow.get_configuration(None, wo, pn)
                if cfg is None:
                    # Operator cancelled configuration
                    return False, "Operator cancelled configuration"
                # cfg is (voltage, wattage, (rmin, rmax)) or (v, w)
                v = int(cfg[0])
                w = int(cfg[1])
                selected = {"voltage": v, "wattage": w}
                if len(cfg) > 2 and isinstance(cfg[2], (list, tuple)) and len(cfg[2]) == 2:
                    selected["resistance_range"] = (float(cfg[2][0]), float(cfg[2][1]))
                else:
                    selected["resistance_range"] = (0.0, 0.0)
                self._selected_config = selected  # type: ignore[attr-defined]
            except Exception:
                # If configuration dialog can't be shown, proceed without it
                pass

        # Decide simulate/demo mode for THIS RUN ONLY
        # Only use simulate if explicitly requested via WO/PN (TEST TEST) or __init__ flag
        simulate_for_run = should_use_simulate_mode(wo, pn) or self.simulate
        
        self.log.info("Test mode for run: %s (WO=%s PN=%s)", 
                     "SIMULATE" if simulate_for_run else "HARDWARE", wo, pn)

        # Log the mode we're using for this run
        if simulate_for_run:
            self.log.debug("Running in SIMULATE mode for this test")
        else:
            self.log.debug("Running in HARDWARE mode for this test")

        # Start a new test session for logging (creates new ET_ELOV####.txt file)
        cfg = getattr(self, "_selected_config", None)
        start_test_session(
            results_dir=self.results_dir,
            work_order=wo,
            part_number=pn,
            configuration=cfg,
        )

        # CASE 1: Special demo mode: WO == "test" and PN == "test"
        if wo.lower() == "test" and pn.lower() == "test":
            self.log.info("Entering DEMO test sequence (WO=TEST, PN=TEST)")
            ok, msg, hypot_info, meas_info = self._run_demo_sequence(ui, wo, pn)
        else:
            # CASE 2: Normal real/simulated test
            ok, msg, hypot_info, meas_info = self._run_normal_sequence(ui, wo, pn, simulate_for_run)

        # Finalize the test session log file with overall result
        mode = "demo" if wo.lower() == "test" and pn.lower() == "test" else "normal"
        finalize_session(
            overall_pass=ok,
            final_message=f"Mode: {mode} | {msg}",
        )

        return ok, msg

    # --------------- INTERNAL SEQUENCES ---------------
    def _run_normal_sequence(
        self,
        ui: MainTestWindow,
        wo: str,
        pn: str,
        simulate_for_run: bool = False,
    ) -> Tuple[bool, str, dict, dict]:
        # Prompt operator readiness before starting with Continue/Exit dialog
        ui.hypot_ready()
        QtWidgets.QApplication.processEvents()  # Force UI update
        
        if ContinueExitDialog:
            if not ContinueExitDialog.show_prompt(
                parent=ui,
                title="Ready to Test",
                message="Ready to begin testing?\n\nPress CONTINUE to start or EXIT to cancel."
            ):
                # Operator chose to exit - reset hardware and return to scanning
                self._reset_hardware()
                if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                    self._return_to_scan_callback()
                if hasattr(ui, 'close'):
                    ui.close()
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}
        else:
            # Fallback if widget not available
            if not ui.confirm_ready_to_test():
                msg = "Operator cancelled before starting tests"
                return False, msg, {"passed": False, "message": msg}, {}

        # Initialize hipot_detail for error handling (hipot test should run here)
        hip_detail = {"passed": False, "message": "Hipot test not run", "raw_result": None}
        hip_ok = False
        hip_msg = "Hipot test not run"

        # Measurement test with unlimited retry logic ---------------------------------------------
        meas_ok = False
        meas_msg = ""
        meas_detail = {}
        attempt = 0
        
        while True:  # Unlimited retries until pass or operator exits
            if attempt > 0:
                self.log.info(f"MEASUREMENT retry attempt {attempt + 1}")
                # Clear previous measurement values on retry
                ui.update_measurement("L", 0, "Pin 1 to 6: ---", None)
                ui.update_measurement("L", 1, "Pin 2 to 5: ---", None)
                ui.update_measurement("L", 2, "Pin 3 to 4: ---", None)
                ui.update_measurement("R", 0, "Pin 1 to 6: ---", None)
                ui.update_measurement("R", 1, "Pin 2 to 5: ---", None)
                ui.update_measurement("R", 2, "Pin 3 to 4: ---", None)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"--- Retry Attempt {attempt + 1} ---")
                except Exception:
                    ui.append_hypot_log(f"--- Measurement Retry Attempt {attempt + 1} ---")
                QtWidgets.QApplication.processEvents()
            
            meas_ok, meas_msg, meas_detail = self.run_measuring(ui, wo, pn)
            
            # Log this measurement attempt to the session file
            log_measurement_result(
                passed=meas_ok,
                message=meas_msg,
                values=meas_detail.get("values") if meas_detail else None,
            )
            
            if meas_ok:
                break  # Success, exit retry loop and complete
            else:
                # Test failed - ask operator if they want to retry using Continue/Exit dialog
                if ContinueExitDialog:
                    if not ContinueExitDialog.show_prompt(
                        parent=ui,
                        title="Measurement Test Failed",
                        message=f"Test failed: {meas_msg}\n\nPress CONTINUE to retry or EXIT to cancel."
                    ):
                        # Operator chose to exit - reset hardware and return to scanning
                        self._reset_hardware()
                        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                            self._return_to_scan_callback()
                        if hasattr(ui, 'close'):
                            ui.close()
                        
                        return False, f"Measuring failed: {meas_msg} (operator cancelled)", hip_detail, meas_detail
                else:
                    # Fallback if widget not available
                    if not ui.confirm_retry_test("Measurement", meas_msg):
                        return False, f"Measuring failed: {meas_msg} (operator cancelled)", hip_detail, meas_detail
                # If continue, loop will retry
            
            attempt += 1


        # Hipot test with unlimited retry logic ---------------------------------------------
        hip_ok = False
        hip_msg = ""
        hip_detail = {}
        attempt = 0
        
        while True:  # Unlimited retries until pass or operator exits
            if attempt > 0:
                self.log.info(f"HIPOT retry attempt {attempt + 1}")
                ui.append_hypot_log(f"--- Retry Attempt {attempt + 1} ---")
                QtWidgets.QApplication.processEvents()
            
            # Always keep relay closed during retries (only open when operator exits)
            hip_ok, hip_msg, hip_detail = self.run_hipot(ui, wo, pn, simulate_for_run, keep_relay_closed=True)
            
            # Log this hipot attempt to the session file
            log_hipot_result(
                passed=hip_ok,
                message=hip_msg,
                raw_result=hip_detail.get("raw_result") if hip_detail else None,
            )
            
            # Always show the Continue/Retry/Exit dialog after every test attempt
            # (regardless of pass/fail) - operator controls what happens next
            if ContinueRetryExitDialog:
                if hip_ok:
                    dialog_title = "Hipot Test Passed"
                    dialog_message = f"Hipot test passed!\n\nPress CONTINUE to proceed to measurements, RETRY to re-test, or EXIT to cancel."
                else:
                    dialog_title = "Hipot Test Failed"
                    dialog_message = f"Test failed: {hip_msg}\n\nPress CONTINUE to re-test (passes on success), RETRY to re-test (returns to this dialog), or EXIT to cancel."
                
                result = ContinueRetryExitDialog.show_prompt(
                    parent=ui,
                    title=dialog_title,
                    message=dialog_message
                )
                
                if result == ContinueRetryExitDialog.RETRY:
                    # Operator chose to retry - run test again and return to this dialog
                    # regardless of pass or fail
                    self.log.info(f"Hipot test - operator pressed RETRY - re-running test")
                    attempt += 1
                    continue  # Loop will retry and show dialog again
                elif result == ContinueRetryExitDialog.CONTINUE:
                    if hip_ok:
                        # Test passed and operator chose to continue - proceed to measurements
                        self.log.info(f"Hipot test passed, operator pressed CONTINUE - proceeding to measurements")
                        break  # Exit loop and continue to measurements
                    else:
                        # Test failed and operator chose to continue - retry, and if it passes, proceed
                        self.log.info(f"Hipot test failed, operator pressed CONTINUE - will retry and proceed if passes")
                        attempt += 1
                        # Re-run the hipot test
                        if attempt > 0:
                            ui.append_hypot_log(f"--- Retry Attempt {attempt + 1} (Continue mode) ---")
                            QtWidgets.QApplication.processEvents()
                        hip_ok, hip_msg, hip_detail = self.run_hipot(ui, wo, pn, simulate_for_run, keep_relay_closed=True)
                        log_hipot_result(
                            passed=hip_ok,
                            message=hip_msg,
                            raw_result=hip_detail.get("raw_result") if hip_detail else None,
                        )
                        if hip_ok:
                            # Test passed - proceed to measurements
                            self.log.info(f"Hipot test passed on CONTINUE retry - proceeding to measurements")
                            break
                        else:
                            # Test failed again - show dialog again
                            self.log.info(f"Hipot test failed on CONTINUE retry - showing dialog again")
                            continue
                else:  # EXIT
                    # Operator chose to exit - reset hardware and return to scanning
                    self._reset_hardware()
                    if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
                        self._return_to_scan_callback()
                    if hasattr(ui, 'close'):
                        ui.close()
                    
                    return False, f"Hipot failed: {hip_msg} (operator cancelled)", hip_detail, {}
            else:
                # Fallback if widget not available - use old behavior
                if hip_ok:
                    break  # Success, exit retry loop and continue to measurements
                if not ui.confirm_retry_test("Hipot", hip_msg):
                    if self.hipot_test_seq:
                        try:
                            self.hipot_test_seq.open_relay()
                        except Exception:
                            pass
                    return False, f"Hipot failed: {hip_msg} (operator cancelled)", hip_detail, {}
                attempt += 1  # Only increment for fallback path

        
        # Both tests passed - show success dialog. Schedule QC printing from the
        # dialog so the sticker is printed ~1s after the dialog is shown.
        if TestPassedDialog:
            try:
                TestPassedDialog.show_passed(parent=ui, work_order=wo, part_number=pn)
            except TypeError:
                # Fallback if older signature present
                TestPassedDialog.show_passed(parent=ui)

        # QC printing is scheduled from the TestPassedDialog to occur
        # ~1 second after the dialog is shown. No additional action needed here.

        # Reset all hardware after successful test
        self._reset_hardware()

        # IMPORTANT: Show scan window BEFORE closing test window
        # This ensures there's always a visible window, preventing Qt event loop exit
        if hasattr(self, '_return_to_scan_callback') and self._return_to_scan_callback:
            self._return_to_scan_callback()
        
        # Now close test window (scan window is already visible)
        if hasattr(ui, 'close'):
            ui.close()
        
        return True, "Hipot + Measuring completed successfully", hip_detail, meas_detail

    def _run_demo_sequence(
        self,
        ui: MainTestWindow,
        wo: str,
        pn: str,
    ) -> Tuple[bool, str, dict, dict]:
        """
        Demo-only visual run with preset values.
        No real hardware activity; just drives the UI.
        """
        # Hypot demo
        ui.hypot_ready()
        ui.append_hypot_log("DEMO: Hypot Ready...")
        time.sleep(1.0)

        ui.hypot_running()
        ui.append_hypot_log("DEMO: Configuring test parameters...")
        time.sleep(1.2)
        ui.append_hypot_log("DEMO: Starting high voltage test...")
        time.sleep(1.5)
        ui.append_hypot_log("DEMO: Monitoring for breakdown...")
        time.sleep(1.0)
        ui.append_hypot_log("DEMO: Ramping down voltage...")
        time.sleep(0.8)

        demo_hipot_pass = True
        ui.hypot_result(demo_hipot_pass)
        ui.append_hypot_log("DEMO: Hipot PASS (simulated).")
        time.sleep(0.5)

        hipot_info = {
            "passed": demo_hipot_pass,
            "message": "Demo Hypot PASS",
            "raw_result": "PASS (demo)",
        }

        # Measuring demo – using your LP/RP style
        demo_meas = {
            "LP1to6": 6,
            "LP2to5": 7,
            "LP3to4": 6,
            "RP1to6": 6,
            "RP2to5": 7,
            "RP3to4": 6,
        }

        # Left - update UI immediately for each measurement
        ui.update_measurement("L", 0, f"Pin 1 to 6: {demo_meas['LP1to6']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("L", 1, f"Pin 1 to 6: {demo_meas['LP2to5']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("L", 2, f"Pin 1 to 6: {demo_meas['LP3to4']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)

        # Right - update UI immediately for each measurement
        ui.update_measurement("R", 0, f"Pin 1 to 6: {demo_meas['RP1to6']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("R", 1, f"Pin 1 to 6: {demo_meas['RP2to5']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.6)
        ui.update_measurement("R", 2, f"Pin 1 to 6: {demo_meas['RP3to4']}", True)
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.4)

        meas_info = {
            "passed": True,
            "message": "Demo measuring PASS",
            "values": demo_meas,
        }

        msg = (
            "DEMO sequence complete. This did not exercise real hardware.\n"
            "WORK ORDER = TEST, PART = TEST."
        )
        return True, msg, hipot_info, meas_info

    # --------------- HIPOT ----------------
    def run_hipot(
        self,
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
        simulate: bool = False,
        keep_relay_closed: bool = False,
    ) -> Tuple[bool, str, dict]:
        """
        Run the Hipot portion of the test and update the UI.
        Uses HipotTestSequence which handles relay closure + hipot test.
        Returns (passed, message, detail_dict).
        """
        self.log.info(f"HIPOT start | WO={work_order} | PN={part_number}")
        # Defensive checks: ensure UI is present and implements required methods
        if ui is None:
            self.log.error("HIPOT start failed: ui is None")
            return False, "UI not available", {"passed": False}

        try:
            ui.hypot_ready()
        except Exception as e:
            self.log.error(f"HIPOT: ui.hypot_ready() failed: {e}", exc_info=True)
            return False, f"UI error: {e}", {"passed": False}
        time.sleep(0.2)

        ui.hypot_running()
        QtWidgets.QApplication.processEvents()  # Force UI update
        ui.append_hypot_log("Checking Hipot connections...")
        QtWidgets.QApplication.processEvents()  # Force UI update
        time.sleep(0.5)

        if simulate:
            # Simulated behavior
            ui.append_hypot_log("Step 1/5: Reset instrument (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 2/5: Configure relay (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 3/5: Configure hipot test (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            ui.append_hypot_log("Step 4/5: Execute hipot test (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(1.5)
            ui.append_hypot_log("Step 5/5: Disable relay (SIM)")
            QtWidgets.QApplication.processEvents()
            time.sleep(0.8)
            passed = True
            msg = "Simulated Hipot PASS"
        elif self.hipot_test_seq is None:
            # Hardware not available - show error
            error_msg = "Hipot hardware not available!\n\n"
            if self.hipot_driver is None:
                error_msg += "• Hipot driver (AR3865) failed to initialize\n"
            if self.relay_driver is None:
                error_msg += "• Relay driver failed to initialize\n"
            error_msg += "\nCheck hardware connections and driver availability."
            
            ui.append_hypot_log("ERROR: Hardware not available")
            QtWidgets.QApplication.processEvents()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(ui, "Hardware Not Available", error_msg)
            
            passed = False
            msg = "Hipot hardware not available"
        else:
            # Real hardware test using HipotTestSequence
            try:
                ui.append_hypot_log("Step 1/5: Reset instrument")
                QtWidgets.QApplication.processEvents()
                # Run the full hipot test sequence (handles relay + hipot)
                # Default: 1500V, 5mA trip, 1s ramp, 1s dwell, 0.5s fall
                ui.append_hypot_log("Step 2/5: Configure relay (closing relay 8)")
                QtWidgets.QApplication.processEvents()
                ui.append_hypot_log("Step 3/5: Configure hipot test")
                QtWidgets.QApplication.processEvents()
                ui.append_hypot_log("Step 4/5: Execute hipot test")
                QtWidgets.QApplication.processEvents()
                
                # TIMING CONFIGURATION FOR RESET
                HIPOT_TEST_DURATION = 4.0  # Expected test duration in seconds
                RESET_DELAY_AFTER_RESULT = 3.0  # Delay after result for operator awareness

                # Determine which FL to run based on operator configuration
                file_index = self._select_hypot_file_index(work_order, part_number)
                passed, msg = self.hipot_test_seq.run_test(
                    keep_relay_closed=keep_relay_closed,
                    reset_after_test=True,
                    total_test_duration_s=HIPOT_TEST_DURATION,
                    reset_delay_after_result_s=RESET_DELAY_AFTER_RESULT,
                    file_index=file_index
                )
                
                ui.append_hypot_log("Step 5/5: Disable relay (all relays OFF)")
                QtWidgets.QApplication.processEvents()
                
            except Exception as e:
                passed = False
                msg = f"Exception: {e}"
                ui.append_hypot_log(f"ERROR: {e}")
                self.log.error(f"Hipot test failed with exception: {e}", exc_info=True)

        ui.hypot_result(passed)
        QtWidgets.QApplication.processEvents()
        self.log.info(f"HIPOT result | pass={passed} | msg={msg}")
        ui.append_hypot_log(f"Result: {'PASS' if passed else 'FAIL'} ({msg})")
        QtWidgets.QApplication.processEvents()

        detail = {
            "passed": passed,
            "message": msg,
            "raw_result": msg,  # Include raw result for logging
        }
        return passed, msg, detail

    # --------------- MEASURING ----------------
    def run_measuring(
        self,
        ui: MainTestWindow,
        work_order: str,
        part_number: str,
    ) -> Tuple[bool, str, dict]:
        """
        Run the measuring portion using real meter readings.
        Measures resistance for Pin 1to6, Pin 2to5, and Pin 3to4.
        """
        self.log.info(f"MEAS start | WO={work_order} | PN={part_number}")

        # Check if we have measurement test sequence
        use_real_measurement = (self.measurement_test_seq is not None and not self.simulate)
        
        if self.simulate:
            # Explicitly in simulate mode
            use_real_measurement = False
        elif self.measurement_test_seq is None:
            # Hardware not available - show error
            error_msg = "Measurement hardware not available!\n\n"
            if self.meter_driver is None:
                error_msg += "• Meter driver failed to initialize\n"
            if self.relay_driver is None:
                error_msg += "• Relay driver failed to initialize\n"
            error_msg += "\nCheck hardware connections and driver availability."
            
            try:
                ui.append_measurement_log("ERROR: Hardware not available")
            except Exception:
                ui.append_hypot_log("ERROR: Measurement hardware not available")
            QtWidgets.QApplication.processEvents()
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(ui, "Hardware Not Available", error_msg)
            
            detail = {
                "passed": False,
                "message": "Measurement hardware not available",
                "values": {},
            }
            return False, "Measurement hardware not available", detail
        
        if use_real_measurement:
            self.log.info("MEAS: Using REAL HARDWARE via MeasurementTestSequence")
            
            # Get resistance range from configuration
            resistance_range = None
            cfg = getattr(self, "_selected_config", None)
            if cfg and isinstance(cfg, dict):
                rr = cfg.get("resistance_range")
                if isinstance(rr, (list, tuple)) and len(rr) == 2:
                    try:
                        resistance_range = (float(rr[0]), float(rr[1]))
                    except Exception:
                        pass
            
            # If no range from config, try to get from ConfigurationWindow mapping
            if resistance_range is None or resistance_range == (0.0, 0.0):
                try:
                    from element_tester.system.ui.configuration_ui import ConfigurationWindow
                    key = None
                    if cfg and isinstance(cfg, dict) and cfg.get("voltage") and cfg.get("wattage"):
                        key = (int(cfg.get("voltage")), int(cfg.get("wattage")))
                    # Fallback to (208, 7000) if not set
                    if key is None or key not in ConfigurationWindow.RESISTANCE_RANGE:
                        key = (208, 7000)
                    if key in ConfigurationWindow.RESISTANCE_RANGE:
                        resistance_range = ConfigurationWindow.RESISTANCE_RANGE[key]
                        # Log the expected resistance
                        try:
                            ui.append_measurement_log(f"Expected resistance for {key[0]}V/{key[1]}W: {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω")
                        except Exception:
                            ui.append_hypot_log(f"Expected resistance for {key[0]}V/{key[1]}W: {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω")
                except Exception as e:
                    self.log.warning(f"Could not get resistance range from configuration: {e}")
            
            # Run measurement test sequence
            try:
                passed, msg, detail = self.measurement_test_seq.run_test(
                    ui=ui,
                    resistance_range=resistance_range,
                    timeout_per_position_s=30.0  # Increased from 10s for Fluke 287 stability
                )
                return passed, msg, detail
            except Exception as e:
                self.log.error(f"MEAS: Measurement test sequence failed: {e}", exc_info=True)
                # Return failure
                detail = {
                    "passed": False,
                    "message": f"Measurement test exception: {e}",
                    "values": {},
                }
                return False, str(e), detail
        else:
            # Simulated readings (only when simulate mode explicitly enabled)
            self.log.info("MEAS: Using simulated values (simulate mode)")
            left_vals = [6.0, 7.0, 6.0]
            right_vals = [6.0, 7.0, 6.0]
            
            # Determine expected resistance range from selected configuration
            cfg = getattr(self, "_selected_config", None)
            rmin = rmax = None
            if cfg and isinstance(cfg, dict):
                rr = cfg.get("resistance_range")
                if isinstance(rr, (list, tuple)) and len(rr) == 2:
                    try:
                        rmin = float(rr[0])
                        rmax = float(rr[1])
                    except Exception:
                        rmin = rmax = None

            # If no range from config, try ConfigurationWindow.RESISTANCE_RANGE
            if rmin is None or rmax is None:
                try:
                    from element_tester.system.ui.configuration_ui import ConfigurationWindow
                    key = None
                    if cfg and isinstance(cfg, dict) and cfg.get("voltage") and cfg.get("wattage"):
                        key = (int(cfg.get("voltage")), int(cfg.get("wattage")))
                    # Fallback to (208, 7000)
                    if key is None or key not in ConfigurationWindow.RESISTANCE_RANGE:
                        key = (208, 7000)
                    if key in ConfigurationWindow.RESISTANCE_RANGE:
                        rmin, rmax = ConfigurationWindow.RESISTANCE_RANGE[key]
                        # Log expected resistance
                        try:
                            ui.append_measurement_log(f"Expected resistance for {key[0]}V/{key[1]}W: {rmin:.1f} - {rmax:.1f} Ω")
                        except Exception:
                            ui.append_hypot_log(f"Expected resistance for {key[0]}V/{key[1]}W: {rmin:.1f} - {rmax:.1f} Ω")
                except Exception:
                    pass

            # Update UI with simulated measurements
            row_names = ["Pin 1 to 6", "Pin 2 to 5", "Pin 3 to 4"]
            for idx in range(3):
                # Left measurement
                l_val = float(left_vals[idx])
                l_pass = None
                if rmin is not None and rmax is not None:
                    l_pass = (rmin <= l_val <= rmax)
                ui.update_measurement("L", idx, f"{row_names[idx]}: {l_val:.2f} Ω", l_pass)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"Measured {row_names[idx]} LEFT: {l_val:.2f} Ω - {'OK' if l_pass else 'FAIL' if l_pass is False else 'N/A'}")
                except Exception:
                    ui.append_hypot_log(f"Measured row {idx+1} LEFT: {l_val:.2f} Ω")
                time.sleep(0.6)

                # Right measurement
                r_val = float(right_vals[idx])
                r_pass = None
                if rmin is not None and rmax is not None:
                    r_pass = (rmin <= r_val <= rmax)
                ui.update_measurement("R", idx, f"{row_names[idx]}: {r_val:.2f} Ω", r_pass)
                QtWidgets.QApplication.processEvents()
                try:
                    ui.append_measurement_log(f"Measured {row_names[idx]} RIGHT: {r_val:.2f} Ω - {'OK' if r_pass else 'FAIL' if r_pass is False else 'N/A'}")
                except Exception:
                    ui.append_hypot_log(f"Measured row {idx+1} RIGHT: {r_val:.2f} Ω")
                time.sleep(0.6)

            # Store values
            values = {}
            for idx in range(3):
                values[f"LP{idx+1}to6"] = left_vals[idx]
                values[f"RP{idx+1}to6"] = right_vals[idx]

            # Decide overall pass
            if rmin is not None and rmax is not None:
                all_ok = True
                for val in left_vals + right_vals:
                    if val == 0.0 or not (rmin <= val <= rmax):
                        all_ok = False
                        break
                passed = all_ok
                msg = "All measurements within limits" if passed else "Some measurements out of range"
            else:
                passed = True
                msg = "Measurements recorded (no range configured)"

            detail = {
                "passed": passed,
                "message": msg,
                "values": values,
            }

            self.log.info(f"MEAS result | pass={passed} | msg={msg}")
            return passed, msg, detail

if __name__ == "__main__":
    import sys
    import argparse
    from PyQt6 import QtWidgets
    from element_tester.system.ui.scanning import ScanWindow

    parser = argparse.ArgumentParser(description="Run Element Tester UI")
    parser.add_argument("--simulate", action="store_true", help="Run in simulate mode (no hardware)")
    args, unknown = parser.parse_known_args()

    app = QtWidgets.QApplication(sys.argv)

    # Force dark mode for the application - this affects child processes like Notepad
    # Set Windows app to prefer dark mode via registry
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            # AppsUseLightTheme: 0 = Dark, 1 = Light
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception:
            pass
    except Exception:
        pass

    # Apply dark palette to PyQt6 application
    from PyQt6.QtGui import QPalette, QColor
    from PyQt6.QtCore import Qt
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(dark_palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")

    # Default to hardware mode; enable simulate only when --simulate provided.
    runner = TestRunner(simulate=bool(args.simulate))

    # Keep persistent references to prevent GC closing windows
    class _WindowHolder:
        main: Optional[MainTestWindow] = None
        scan: Optional[ScanWindow] = None
    window_refs = _WindowHolder()

    def show_scan_window():
        """Show or create the scanning window."""
        if window_refs.scan is None:
            scan = ScanWindow()
            scan.scanCompleted.connect(on_scan_completed)
            window_refs.scan = scan
        window_refs.scan.show()
        window_refs.scan.raise_()
        window_refs.scan.activateWindow()

    def on_scan_completed(wo: str, pn: str):
        # Hide scanning window and show configuration dialog first
        if window_refs.scan:
            window_refs.scan.hide()

        # Show configuration UI to choose voltage/wattage
        try:
            from element_tester.system.ui.configuration_ui import ConfigurationWindow
        except Exception:
            ConfigurationWindow = None

        selected: dict | None = None
        if ConfigurationWindow is not None:
            cfg = ConfigurationWindow.get_configuration(None, wo, pn)
            if cfg is None:
                # User cancelled configuration - return to scanning with cleared fields
                show_scan_window()
                return
            if cfg is not None:
                # cfg may be (voltage, wattage) or (voltage, wattage, (rmin, rmax))
                v = int(cfg[0])
                w = int(cfg[1])
                selected: dict = {"voltage": v, "wattage": w}
                if len(cfg) > 2 and isinstance(cfg[2], (list, tuple)) and len(cfg[2]) == 2:
                    try:
                        rmin = float(cfg[2][0])
                        rmax = float(cfg[2][1])
                        selected["resistance_range"] = (rmin, rmax)
                    except Exception:
                        selected["resistance_range"] = (0.0, 0.0)

        # Store selected config on runner for later use
        runner._selected_config = selected  # type: ignore[attr-defined]

        # Now create and show main testing window
        main = MainTestWindow()
        main.show()
        # Persist reference so the window isn't garbage collected
        window_refs.main = main
        # Also store on runner for easy access elsewhere if needed
        runner._main_window = main  # type: ignore[attr-defined]

        # Optionally show the chosen settings in the hypot log
        if selected:
            # Write selected config and resistance range into the measurement log
            try:
                main.append_measurement_log(f"Selected config: {selected['voltage']}V, {selected['wattage']}W")
            except Exception:
                main.append_hypot_log(f"Selected config: {selected['voltage']}V, {selected['wattage']}W")

            # Also show resistance range if provided by the configuration dialog
            rr = selected.get("resistance_range")
            if rr is not None and isinstance(rr, (list, tuple)) and len(rr) == 2:
                rmin, rmax = rr
                if rmin == 0.0 and rmax == 0.0:
                    try:
                        main.append_measurement_log(f"Resistance range: not configured for {selected['voltage']} V / {selected['wattage']} W")
                    except Exception:
                        main.append_hypot_log(f"Resistance range: not configured for {selected['voltage']} V / {selected['wattage']} W")
                else:
                    try:
                        main.append_measurement_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")
                    except Exception:
                        main.append_hypot_log(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")

        # Set return-to-scan callback on runner
        runner._return_to_scan_callback = show_scan_window  # type: ignore[attr-defined]

        # Start the run (simulate decision already made in run_full_sequence)
        runner.run_full_sequence(main, wo, pn)

    # Show initial scan window
    show_scan_window()
    sys.exit(app.exec())
