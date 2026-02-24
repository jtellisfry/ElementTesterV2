from __future__ import annotations

import logging
import time
from typing import Any

from PyQt6 import QtWidgets


def run_test(drivers: dict[str, Any], config: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    relay_driver = drivers.get("relay_driver")
    meter_driver = drivers.get("meter_driver")
    ui = config.get("ui")
    resistance_range = config.get("resistance_range")
    timeout_per_position_s = float(config.get("timeout_per_position_s", 30.0))
    simulate = bool(config.get("simulate", False))
    sim_values = config.get("sim_values") or {}
    log = logger

    if relay_driver is None:
        raise RuntimeError("relay_driver is required")
    if meter_driver is None and not simulate:
        raise RuntimeError("meter_driver is required when simulate=False")

    config_name = "Pin 1 to 6"
    row_idx = 0
    pin_suffix = "1to6"

    timed_out = False
    reading_valid = False
    measured_value = 0.0
    message = ""

    try:
        log.info(f"MEAS: Closing relays for {config_name}")
        relay_driver.close_pin1to6(delay_ms=200.0)
        time.sleep(2.0)

        if not simulate:
            meter_driver.flush_buffer()

        try:
            ui.append_measurement_log(f"Measuring {config_name}...")
        except Exception:
            try:
                ui.append_hypot_log(f"Measuring {config_name}...")
            except Exception:
                pass

        if simulate:
            measured_value = float(sim_values.get("pin1to6", 6.8))
            reading_valid = True
            time.sleep(0.5)
        else:
            start_time = time.time()
            max_attempts = 10
            for attempt in range(max_attempts):
                elapsed = time.time() - start_time
                if elapsed >= timeout_per_position_s:
                    break
                try:
                    reading = meter_driver.read_value(max_retries=3)
                    if reading is not None and reading.value is not None:
                        measured_value = round(float(reading.value), 1)
                        reading_valid = True
                        break
                except Exception as e:
                    log.error(f"MEAS: {config_name} read attempt {attempt + 1} failed: {e}", exc_info=True)
                time.sleep(0.5)

            if not reading_valid:
                timed_out = True

        passed = None
        if reading_valid and resistance_range is not None:
            rmin, rmax = resistance_range
            passed = bool(rmin <= measured_value <= rmax)

        if reading_valid:
            ui.update_measurement("L", row_idx, f"{config_name}: {measured_value:.1f} Ω", passed)
            QtWidgets.QApplication.processEvents()
            ui.update_measurement("R", row_idx, f"{config_name}: {measured_value:.1f} Ω", passed)
            QtWidgets.QApplication.processEvents()
            status_txt = "OK" if passed else "FAIL" if passed is False else "N/A"
            try:
                ui.append_measurement_log(f"Measured {config_name}: {measured_value:.1f} Ω - {status_txt}")
            except Exception:
                pass
            message = f"{config_name}: {measured_value:.1f} Ω"
        else:
            ui.update_measurement("L", row_idx, f"{config_name}: TIMEOUT", False)
            QtWidgets.QApplication.processEvents()
            ui.update_measurement("R", row_idx, f"{config_name}: TIMEOUT", False)
            QtWidgets.QApplication.processEvents()
            message = f"{config_name}: TIMEOUT"

        return {
            "name": config_name,
            "row_index": row_idx,
            "pin_suffix": pin_suffix,
            "value": measured_value,
            "reading_valid": reading_valid,
            "timed_out": timed_out,
            "passed": passed,
            "message": message,
        }
    finally:
        try:
            relay_driver.open_pin1to6(delay_ms=100.0)
        except Exception:
            try:
                relay_driver.all_off()
            except Exception:
                pass
        time.sleep(1.0)
