"""
Measurement Test Sequence
=========================

High-level measurement test orchestration class that combines relay control
and meter reading to measure resistance at different pin combinations.

This class encapsulates all the logic for:
- Opening/closing relays for each measurement position
- Reading meter values with retry logic
- Handling timeouts and errors
- Updating UI with results

Usage:
    from element_tester.programs.measurement_test.test import MeasurementTestSequence
    
    seq = MeasurementTestSequence(relay_driver, meter_driver, logger)
    passed, msg, detail = seq.run_test(ui, resistance_range=(5.0, 8.0))
"""
from __future__ import annotations
import logging
import time
import threading
from typing import Optional, Tuple, Any
from pathlib import Path
import sys

# Add src/ to path
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.drivers.MCC_ERB.driver import ERB08Driver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class MeasurementTestSequence:
    """
    Orchestrates resistance measurement tests using relay switching and meter reading.
    
    This class handles the complete measurement workflow:
    1. Configure relays for each pin position
    2. Wait for settling time
    3. Read meter value with timeout handling
    4. Update UI with results
    5. Move to next position
    """
    
    def __init__(
        self,
        relay_driver: ERB08Driver,
        meter_driver: Any,  # Fluke287Driver or UT61EDriver
        logger: Optional[logging.Logger] = None,
        simulate: bool = False
    ):
        """
        Initialize measurement test sequence.
        
        Args:
            relay_driver: ERB08 relay board driver for switching configurations
            meter_driver: Meter driver (must implement read_value() and flush_buffer())
            logger: Optional logger instance
            simulate: Force simulation mode (uses controllable test values)
        """
        self.relay_driver = relay_driver
        self.meter_driver = meter_driver
        self.log = logger or logging.getLogger("measurement_test_sequence")
        self.simulate = simulate
        
        # Simulated resistance values (can be overridden for testing)
        self.sim_values = {
            "pin1to6": 6.8,  # Ohms
            "pin2to5": 7.2,  # Ohms
            "pin3to4": 6.5,  # Ohms
        }
    
    def set_simulated_values(self, pin1to6: float, pin2to5: float, pin3to4: float):
        """
        Set simulated resistance values for testing pass/fail scenarios.
        
        Args:
            pin1to6: Resistance in ohms for pin 1 to 6 measurement
            pin2to5: Resistance in ohms for pin 2 to 5 measurement
            pin3to4: Resistance in ohms for pin 3 to 4 measurement
        """
        self.sim_values = {
            "pin1to6": pin1to6,
            "pin2to5": pin2to5,
            "pin3to4": pin3to4,
        }
        self.log.info(f"Simulated values set: 1to6={pin1to6}Ω, 2to5={pin2to5}Ω, 3to4={pin3to4}Ω")
    
    def run_test(
        self,
        ui: Any,  # MainTestWindow
        resistance_range: Optional[Tuple[float, float]] = None,
        timeout_per_position_s: float = 10.0
    ) -> Tuple[bool, str, dict]:
        """
        Execute complete measurement test sequence for all pin positions.
        
        Args:
            ui: MainTestWindow instance for updating display
            resistance_range: Optional (min, max) resistance in ohms for pass/fail
            timeout_per_position_s: Maximum time to wait for each position reading
        
        Returns:
            Tuple of (passed, message, detail_dict) where detail_dict contains:
                - 'passed': bool
                - 'message': str
                - 'values': dict with LP1to6, LP2to5, LP3to4, RP1to6, RP2to5, RP3to4
        """
        self.log.info("MEAS: Starting measurement test sequence")
        
        # Log the resistance range being used for pass/fail
        if resistance_range is not None:
            self.log.info(f"MEAS: Using resistance range {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω for pass/fail")
            try:
                ui.append_measurement_log(f"Expected resistance: {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω")
            except Exception:
                try:
                    ui.append_hypot_log(f"Expected resistance: {resistance_range[0]:.1f} - {resistance_range[1]:.1f} Ω")
                except:
                    pass
        else:
            self.log.info("MEAS: No resistance range configured - all readings will be recorded as pass")
        
        left_vals = []
        right_vals = []
        timeout_occurred = False
        
        # Test meter communication before starting measurements
        if not self.simulate:
            self.log.info("MEAS: Testing meter communication...")
            try:
                # Use a simple direct read with error handling
                self.log.info(f"MEAS: Calling read_value() on meter driver (type: {type(self.meter_driver).__name__})...")
                test_read = self.meter_driver.read_value(max_retries=2)
                
                if test_read is None:
                    self.log.warning(f"MEAS: Meter test returned None")
                elif test_read.value is None:
                    self.log.warning(f"MEAS: Meter test returned reading with None value")
                else:
                    self.log.info(f"MEAS: Meter communication OK - read {test_read.value} {test_read.unit}")
                    try:
                        ui.append_measurement_log(f"Meter test: {test_read.value} {test_read.unit}")
                    except:
                        pass
            except AttributeError as e:
                self.log.error(f"MEAS: Meter driver missing read_value() method: {e}", exc_info=True)
                try:
                    ui.append_measurement_log(f"ERROR: Meter driver incompatible - missing read_value()")
                except:
                    pass
            except Exception as e:
                self.log.warning(f"MEAS: Meter communication test failed: {e}", exc_info=True)
                try:
                    ui.append_measurement_log(f"WARNING: Meter test failed - {str(e)}")
                except:
                    pass
        
        # Ensure all relays are open before starting measurements
        self.log.info("MEAS: Opening all relays before starting measurements")
        try:
            self.relay_driver.all_off()
            time.sleep(0.2)  # Brief settling delay
            self.log.info("MEAS: All relays opened successfully")
            try:
                from PyQt6 import QtWidgets
                QtWidgets.QApplication.processEvents()  # Keep UI responsive
            except:
                pass
        except Exception as e:
            self.log.error(f"MEAS: Failed to open all relays: {e}", exc_info=True)
        
        # Flush meter buffer before starting any measurements
        self.log.info("MEAS: Flushing meter buffer before starting measurements")
        try:
            self.meter_driver.flush_buffer()
            self.log.info("MEAS: Initial buffer flush complete")
            try:
                from PyQt6 import QtWidgets
                QtWidgets.QApplication.processEvents()  # Keep UI responsive
            except:
                pass
        except Exception as e:
            self.log.error(f"MEAS: Failed to flush initial buffer: {e}", exc_info=True)
        
        # Define measurement configurations - using driver methods directly
        configurations = [
            ("Pin 1 to 6", self.relay_driver.close_pin1to6, self.relay_driver.open_pin1to6, 0, "pin1to6"),
            ("Pin 2 to 5", self.relay_driver.close_pin2to5, self.relay_driver.open_pin2to5, 1, "pin2to5"),
            ("Pin 3 to 4", self.relay_driver.close_pin3to4, self.relay_driver.open_pin3to4, 2, "pin3to4"),
        ]
        
        self.log.info(f"MEAS: Starting measurement loop for {len(configurations)} positions...")
        
        # Process each measurement position
        for idx, (config_name, close_func, open_func, row_idx, sim_key) in enumerate(configurations):
            self.log.info(f"MEAS: ===== Position {idx + 1}/{len(configurations)}: {config_name} =====")
            try:
                # Close relays for this position
                self.log.info(f"MEAS: Closing relays for {config_name}")
                try:
                    close_func(delay_ms=200.0)
                    self.log.info(f"MEAS: Relays closed successfully for {config_name}")
                except Exception as e:
                    self.log.error(f"MEAS: Failed to close relays for {config_name}: {e}", exc_info=True)
                    raise
                
                # Wait for relay to settle before reading
                self.log.info(f"MEAS: Waiting 2 seconds for relay to settle...")
                time.sleep(2.0)
                try:
                    from PyQt6 import QtWidgets
                    QtWidgets.QApplication.processEvents()
                except:
                    pass
                
                # Flush buffer after relay switching
                self.log.info(f"MEAS: Flushing meter buffer for {config_name}")
                try:
                    self.meter_driver.flush_buffer()
                    self.log.info(f"MEAS: Buffer flushed successfully")
                    try:
                        from PyQt6 import QtWidgets
                        QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    except:
                        pass
                except Exception as e:
                    self.log.error(f"MEAS: Failed to flush buffer: {e}", exc_info=True)
                    raise
                
                # Read meter value with timeout
                self.log.info(f"MEAS: Reading {config_name} (timeout: {timeout_per_position_s}s, max 10 attempts)...")
                try:
                    ui.append_measurement_log(f"Measuring {config_name}...")
                except Exception:
                    try:
                        ui.append_hypot_log(f"Measuring {config_name}...")
                    except:
                        pass
                
                try:
                    from PyQt6 import QtWidgets
                    QtWidgets.QApplication.processEvents()  # Keep UI responsive
                except:
                    pass
                
                # Check if we're in simulate mode
                if self.simulate:
                    # Use simulated value for this pin configuration
                    avg = self.sim_values.get(sim_key, 6.8)
                    left_vals.append(avg)
                    right_vals.append(avg)
                    self.log.info(f"MEAS: {config_name} = {avg:.1f} Ω (SIMULATED)")
                    
                    # Simulate some delay
                    time.sleep(0.5)
                    
                    reading_valid = True
                else:
                    # Real hardware reading with multiple retries
                    self.log.info(f"MEAS: {config_name} - Starting real hardware reading loop")
                    reading = None
                    reading_valid = False
                    start_time = time.time()
                    
                    # Try up to 10 times to get a valid reading
                    max_attempts = 10
                    for attempt in range(max_attempts):
                        elapsed = time.time() - start_time
                        if elapsed >= timeout_per_position_s:
                            self.log.warning(f"MEAS: {config_name} - Overall timeout after {elapsed:.1f}s")
                            break
                        
                        try:
                            self.log.info(f"MEAS: {config_name} read attempt {attempt + 1}/{max_attempts} (elapsed: {elapsed:.1f}s)")
                            
                            # Call read_value with retries
                            reading = self.meter_driver.read_value(max_retries=3)
                            self.log.info(f"MEAS: {config_name} read_value() returned: {reading}")
                            
                            if reading is not None and reading.value is not None:
                                reading_valid = True
                                avg = round(reading.value, 1)
                                left_vals.append(avg)
                                right_vals.append(avg)
                                self.log.info(f"MEAS: {config_name} = {avg:.1f} Ω (SUCCESS on attempt {attempt + 1})")
                                try:
                                    ui.append_measurement_log(f"{config_name}: {avg:.1f} Ω")
                                except:
                                    pass
                                break  # Success!
                            else:
                                self.log.warning(f"MEAS: {config_name} - No valid reading on attempt {attempt + 1} (reading={reading})")
                        except Exception as e:
                            self.log.error(f"MEAS: {config_name} - Read attempt {attempt + 1} exception: {e}", exc_info=True)
                            try:
                                ui.append_measurement_log(f"Read error: {str(e)[:50]}")
                            except:
                                pass
                        
                        # Keep UI responsive and wait before retry
                        try:
                            from PyQt6 import QtWidgets
                            QtWidgets.QApplication.processEvents()
                        except:
                            pass
                        time.sleep(0.5)  # Wait before retry
                    
                    if not reading_valid:
                        self.log.error(f"MEAS: {config_name} - Failed to get valid reading after {max_attempts} attempts")
                
                # Process reading (common for both simulate and real)
                # Process reading (common for both simulate and real)
                if reading_valid:
                    # Get the averaged value (already set in left_vals/right_vals)
                    avg = left_vals[-1]
                    
                    # Determine pass/fail based on resistance range
                    l_pass = None
                    r_pass = None
                    if resistance_range is not None:
                        rmin, rmax = resistance_range
                        l_pass = (rmin <= avg <= rmax)
                        r_pass = (rmin <= avg <= rmax)
                    
                    # Update LEFT
                    ui.update_measurement("L", row_idx, f"{config_name}: {avg:.1f} Ω", l_pass)
                    try:
                        from PyQt6 import QtWidgets
                        QtWidgets.QApplication.processEvents()
                    except:
                        pass
                    try:
                        ui.append_measurement_log(f"Measured {config_name} LEFT: {avg:.1f} Ω - {'OK' if l_pass else 'FAIL' if l_pass is False else 'N/A'}")
                    except Exception:
                        ui.append_hypot_log(f"Measured {config_name} LEFT: {avg:.1f} Ω")
                    
                    # Update RIGHT
                    ui.update_measurement("R", row_idx, f"{config_name}: {avg:.1f} Ω", r_pass)
                    try:
                        from PyQt6 import QtWidgets
                        QtWidgets.QApplication.processEvents()
                    except:
                        pass
                    try:
                        ui.append_measurement_log(f"Measured {config_name} RIGHT: {avg:.1f} Ω - {'OK' if r_pass else 'FAIL' if r_pass is False else 'N/A'}")
                    except Exception:
                        ui.append_hypot_log(f"Measured {config_name} RIGHT: {avg:.1f} Ω")
                else:
                    # Timeout or invalid reading
                    left_vals.append(0.0)
                    right_vals.append(0.0)
                    timeout_occurred = True
                    elapsed = time.time() - start_time
                    self.log.warning(f"MEAS: {config_name} - TIMEOUT after {elapsed:.1f}s")
                    ui.update_measurement("L", row_idx, f"{config_name}: TIMEOUT", False)
                    ui.update_measurement("R", row_idx, f"{config_name}: TIMEOUT", False)
                    try:
                        from PyQt6 import QtWidgets
                        QtWidgets.QApplication.processEvents()
                    except:
                        pass
                
                # Open relays
                self.log.info(f"MEAS: Opening relays for {config_name}")
                try:
                    open_func(delay_ms=100.0)
                    self.log.info(f"MEAS: Relays opened successfully")
                except Exception as e:
                    self.log.error(f"MEAS: Failed to open relays: {e}", exc_info=True)
                
                # Buffer delay before next measurement
                self.log.info(f"MEAS: Waiting 1 second before next measurement...")
                time.sleep(1.0)
                try:
                    from PyQt6 import QtWidgets
                    QtWidgets.QApplication.processEvents()
                except:
                    pass
                
            except Exception as e:
                self.log.error(f"MEAS: CRITICAL ERROR measuring {config_name}: {e}", exc_info=True)
                left_vals.append(0.0)
                right_vals.append(0.0)
                
                # Show error to user
                try:
                    ui.append_measurement_log(f"ERROR measuring {config_name}: {str(e)}")
                except Exception:
                    try:
                        ui.append_hypot_log(f"MEAS ERROR {config_name}: {str(e)}")
                    except:
                        pass
                
                # Try to open relays on error
                try:
                    self.log.info(f"MEAS: Emergency relay open after error")
                    open_func(delay_ms=100.0)
                except Exception:
                    pass
        
        # Build results dictionary with correct pin names
        # Pin 1 to 6, Pin 2 to 5, Pin 3 to 4
        pin_suffixes = ["1to6", "2to5", "3to4"]
        values = {}
        for idx in range(len(left_vals)):
            if idx < len(pin_suffixes):
                suffix = pin_suffixes[idx]
                values[f"LP{suffix}"] = left_vals[idx]
                values[f"RP{suffix}"] = right_vals[idx]
            else:
                # Fallback for unexpected extra values
                values[f"LP{idx+1}"] = left_vals[idx]
                values[f"RP{idx+1}"] = right_vals[idx]
        
        # Log final values for debugging
        self.log.info(f"MEAS: Final values: left={left_vals}, right={right_vals}, range={resistance_range}")
        
        # Determine overall pass/fail
        if timeout_occurred:
            passed = False
            msg = "Problem with the UT61xP measurement application. Call (318-272-3118)"
        elif len(left_vals) == 0 or len(right_vals) == 0:
            # No measurements were taken at all
            passed = False
            msg = "No measurements were completed - check hardware and connections"
            self.log.error("MEAS: No measurements completed!")
        elif resistance_range is not None:
            rmin, rmax = resistance_range
            all_ok = True
            failed_measurements = []
            for idx, val in enumerate(left_vals + right_vals):
                side = "L" if idx < 3 else "R"
                pin = (idx % 3) + 1
                if val == 0.0:
                    all_ok = False
                    failed_measurements.append(f"{side}P{pin} (failed/timeout)")
                elif not (rmin <= val <= rmax):
                    all_ok = False
                    failed_measurements.append(f"{side}P{pin} ({val:.1f}Ω out of {rmin}-{rmax}Ω)")
            
            passed = all_ok
            if passed:
                msg = "All measurements within limits"
            else:
                msg = f"Failed: {', '.join(failed_measurements)}"
                self.log.warning(f"MEAS: Failed measurements: {failed_measurements}")
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


def main():
    """
    Standalone test execution.
    Run with: python test.py [--simulate]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Measurement Test Sequence")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no hardware required)"
    )
    parser.add_argument(
        "--port",
        type=str,
        default="COM7",
        help="Meter serial port (default: COM7)"
    )
    args = parser.parse_args()
    
    logger = logging.getLogger("measurement_test")
    logger.info("Initializing drivers...")
    
    # Initialize relay driver
    relay_drv = ERB08Driver(
        board_num=0,
        port_low=12,
        port_high=13,
        simulate=args.simulate
    )
    
    # Initialize meter driver (try Fluke287 first, fallback to UT61E)
    meter_drv = None
    try:
        from element_tester.system.drivers.FLUKE287.driver import Fluke287Driver
        meter_drv = Fluke287Driver(
            port=args.port,
            timeout=2.0,
            simulate=args.simulate,
            logger=logger
        )
        meter_drv.initialize()
        logger.info("✓ Fluke 287 meter initialized")
    except Exception as e:
        logger.warning(f"Fluke 287 not available: {e}")
        try:
            from element_tester.system.drivers.UT61E.driver import UT61EDriver
            meter_drv = UT61EDriver(
                vendor_id=0x1a86,
                product_id=0xe429,
                simulate=args.simulate,
                timeout_ms=2000,
                logger=logger
            )
            meter_drv.initialize()
            logger.info("✓ UT61E meter initialized")
        except Exception as e2:
            logger.error(f"No meter driver available: {e2}")
            sys.exit(1)
    
    # Create test sequence
    seq = MeasurementTestSequence(relay_drv, meter_drv, logger)
    
    # Create a simple mock UI for standalone testing
    class MockUI:
        def update_measurement(self, side, idx, text, passed):
            status = "✓" if passed else "✗" if passed is False else "?"
            logger.info(f"  [{side}{idx}] {status} {text}")
        
        def append_measurement_log(self, msg):
            logger.info(f"  LOG: {msg}")
        
        def append_hypot_log(self, msg):
            logger.info(f"  LOG: {msg}")
    
    mock_ui = MockUI()
    
    # Run test
    logger.info("=" * 60)
    logger.info("Starting measurement test sequence")
    logger.info("=" * 60)
    
    resistance_range = (5.0, 8.0)  # Example range
    passed, msg, detail = seq.run_test(mock_ui, resistance_range=resistance_range)
    
    logger.info("=" * 60)
    if passed:
        logger.info("✓ MEASUREMENT TEST PASSED")
    else:
        logger.info(f"✗ MEASUREMENT TEST FAILED: {msg}")
    logger.info(f"Results: {detail['values']}")
    logger.info("=" * 60)
    
    # Cleanup
    try:
        relay_drv.shutdown()
        meter_drv.shutdown()
    except:
        pass


if __name__ == "__main__":
    main()
