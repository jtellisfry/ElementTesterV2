from __future__ import annotations

import logging
import time
from typing import Any


def run_test(drivers: dict[str, Any], config: dict[str, Any], logger: logging.Logger) -> tuple[bool, str]:
    """
    Execute hipot test #1.

    Args:
        drivers: Dict with relay_driver and hipot_driver instances
        config: Dict with file_index, keep_relay_closed, reset_after_test,
                total_test_duration_s, reset_delay_after_result_s
        logger: Active logger

    Returns:
        (passed, raw_result)
    """
    log = logger
    erb_driver = drivers.get("relay_driver")
    hipot_driver = drivers.get("hipot_driver")

    if erb_driver is None:
        raise RuntimeError("relay_driver is required for hypot test")
    if hipot_driver is None:
        raise RuntimeError("hipot_driver is required for hypot test")

    file_index = int(config.get("file_index", 1))
    keep_relay_closed = bool(config.get("keep_relay_closed", False))
    reset_after_test = bool(config.get("reset_after_test", True))
    total_test_duration_s = float(config.get("total_test_duration_s", 5.0))

    relay_closed = False
    test_start_time = time.time()

    try:
        log.info("RELAY(ERB): Ensuring all relays OFF before hipot test")
        try:
            erb_driver.all_off()
            time.sleep(0.1)
        except Exception as e:
            log.warning(f"Failed to turn off all relays at start: {e}")

        log.info("HIPOT: Ensuring instrument is in REMOTE mode and resetting")
        try:
            hipot_driver.reset()
            time.sleep(0.2)
            try:
                idn = hipot_driver.idn()
                log.info(f"HIPOT IDN: {idn}")
            except Exception:
                log.warning("HIPOT: Unable to read IDN; continue if instrument is in remote mode")
        except Exception as e:
            raise Exception(f"Failed to reset hipot instrument: {e}") from e

        try:
            log.info("RELAY(ERB): Closing relay 8 (index 7) to enable hipot path on ERB board")
            erb_driver.set_relay(7, True)
            relay_closed = True
            time.sleep(0.5)
        except Exception as e:
            raise Exception(f"Failed to close ERB relay 8: {e}") from e

        try:
            log.info("RELAY(ERB): Closing relay 7 (index 6) to complete hipot path")
            erb_driver.set_relay(6, True)
            time.sleep(3.0)
        except Exception as e:
            raise Exception(f"Failed to configure ERB relay for hipot: {e}") from e

        log.info("HIPOT: Executing test from configured file index")
        try:
            passed, raw_result, actual_test_start_time = hipot_driver.run_from_file(
                file_index=file_index,
                timeout_s=total_test_duration_s,
            )
            test_start_time = actual_test_start_time
        except Exception as e:
            raise Exception(f"Hipot test execution failed: {e}") from e

        result_str = "PASS ✓" if passed else "FAIL ✗"
        log.info(f"HIPOT: Test complete - {result_str} (raw: {raw_result})")

        if reset_after_test:
            try:
                hipot_driver.reset()
                total_elapsed = time.time() - test_start_time
                log.info(f"HIPOT: Instrument reset at {total_elapsed:.1f}s from test start")
            except Exception as e:
                log.warning(f"Failed to reset instrument after test: {e}")

        if not keep_relay_closed:
            log.info("RELAY: Disabling hipot circuit (opening previously closed relays)")
            try:
                try:
                    erb_driver.set_relay(6, False)
                except Exception:
                    log.debug("Failed to open ERB relay 6 directly; attempting all_off()")
                    try:
                        erb_driver.all_off()
                    except Exception:
                        pass
                try:
                    erb_driver.set_relay(7, False)
                except Exception:
                    pass
                relay_closed = False
                time.sleep(0.1)
            except Exception as e:
                log.error(f"Failed to turn off relays: {e}")
        else:
            log.info("RELAY: Keeping ERB relays 6 and 7 closed (keep_relay_closed=True)")

        return passed, str(raw_result)

    except Exception as e:
        log.error(f"HIPOT: Test sequence failed: {e}", exc_info=True)
        if relay_closed and not keep_relay_closed:
            try:
                log.warning("Emergency relay shutdown due to test failure")
                erb_driver.all_off()
                log.info("RELAY(ERB): All relays turned OFF after error")
            except Exception as relay_err:
                log.critical(f"CRITICAL: Failed to turn off relays after error: {relay_err}")
        raise