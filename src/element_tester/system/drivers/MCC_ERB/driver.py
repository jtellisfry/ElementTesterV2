# driver.py
from __future__ import annotations
from typing import Optional, Iterable
import logging

from .procedures import ERB08Procedures, RelayMapping
from .errors import ERB08Error
from element_tester.system.core.error_messages import (
    ERROR_ERB08_INIT,
    ERROR_ERB08_SHUTDOWN,
    ERROR_ERB08_SET_RELAY,
    ERROR_ERB08_ALL_OFF,
    ERROR_ERB08_ALL_ON,
    ERROR_ERB08_APPLY_MAPPING,
    ERROR_ERB08_PIN1TO6_CLOSE,
    ERROR_ERB08_PIN1TO6_OPEN,
    ERROR_ERB08_PIN2TO5_CLOSE,
    ERROR_ERB08_PIN2TO5_OPEN,
    ERROR_ERB08_PIN3TO4_CLOSE,
    ERROR_ERB08_PIN3TO4_OPEN,
    INFO_RELAY_PIN1TO6_CLOSED,
    INFO_RELAY_PIN1TO6_OPENED,
    INFO_RELAY_PIN2TO5_CLOSED,
    INFO_RELAY_PIN2TO5_OPENED,
    INFO_RELAY_PIN3TO4_CLOSED,
    INFO_RELAY_PIN3TO4_OPENED,
    format_error,
    format_info,
)


class ERB08Driver:
    """
    Hypot-style façade for the MCC ERB08 driver.

    Wraps Procedures so the rest of the system can talk to a single
    object, similar to your Hypot instrument driver.
    """

    def __init__(
        self,
        board_num: int = 0,
        port_low: object = 12,
        port_high: object = 13,
        simulate: bool = False,
        active_high: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.log = logger or logging.getLogger("element_tester.driver.mcc_erb08")
        self.proc = ERB08Procedures(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
            logger=self.log,
        )

    # ---- Lifecycle ----
    def initialize(self) -> None:
        try:
            self.proc.ProcInitializeRelays()
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_INIT, error=e)) from e

    def shutdown(self) -> None:
        try:
            self.proc.ProcShutdownRelays()
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_SHUTDOWN, error=e)) from e

    # ---- Simple control wrappers ----
    def set_relay(self, bit: int, on: bool) -> None:
        try:
            self.proc.ProcSetBit(bit, on)
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_SET_RELAY, bit=bit, state=on, error=e)) from e

    def all_off(self) -> None:
        try:
            self.proc.ProcAllOff()
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_ALL_OFF, error=e)) from e

    def all_on(self) -> None:
        try:
            self.proc.ProcAllOn()
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_ALL_ON, error=e)) from e

    def apply_mapping(
        self,
        bits_on: Iterable[int],
        bits_off: Iterable[int],
    ) -> None:
        try:
            mapping = RelayMapping(
                bits_on=list(bits_on),
                bits_off=list(bits_off),
            )
            self.proc.ProcApplyMapping(mapping)
        except Exception as e:
            raise ERB08Error(format_error(ERROR_ERB08_APPLY_MAPPING, error=e)) from e

    def self_test_walk(self, delay_ms: float = 100.0) -> None:
        try:
            self.proc.ProcSelfTestWalk(delay_ms=delay_ms)
        except Exception as e:
            raise ERB08Error("Self-test walk failed: {0}".format(e)) from e

    # ---- Pin-specific measurement functions ----
    def close_pin1to6(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 1 and pin 6.
        
        Relay mapping:
        - Relay 4: Meter position
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(0.1)
            self.set_relay(4, True)  # Meter position (relay 5, bit 4)
            time.sleep(3)  # Brief settling delay
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN1TO6_CLOSED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN1TO6_CLOSE, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN1TO6_CLOSE, error=e)) from e

    def open_pin1to6(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 1 to pin 6 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN1TO6_OPENED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN1TO6_OPEN, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN1TO6_OPEN, error=e)) from e

    def close_pin2to5(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 2 and pin 5.
        
        Relay mapping:
        - Relay 0: Pin 2
        - Relay 4: Meter position
        - Relay 1: Pin 5
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(0.05)
            self.set_relay(0, True)  # Pin 2
            self.set_relay(4, True)  # Meter position
            self.set_relay(1, True)  # Pin 5
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN2TO5_CLOSED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN2TO5_CLOSE, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN2TO5_CLOSE, error=e)) from e

    def open_pin2to5(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 2 to pin 5 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN2TO5_OPENED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN2TO5_OPEN, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN2TO5_OPEN, error=e)) from e

    def close_pin3to4(self, delay_ms: float = 200.0) -> None:
        """
        Close relays to measure resistance between pin 3 and pin 4.
        
        Relay mapping:
        - Relay 2: Pin 3
        - Relay 4: Meter position
        - Relay 3: Pin 4
        
        Args:
            delay_ms: Settling delay after relay closure in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(0.05)
            self.set_relay(2, True)  # Pin 3
            # self.set_relay(4, True)  # Meter position
            self.set_relay(3, True)  # Pin 4
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN3TO4_CLOSED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN3TO4_CLOSE, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN3TO4_CLOSE, error=e)) from e

    def open_pin3to4(self, delay_ms: float = 100.0) -> None:
        """
        Open relays after pin 3 to pin 4 measurement.
        
        Args:
            delay_ms: Delay after opening relays in milliseconds
        """
        try:
            import time
            self.all_off()
            time.sleep(delay_ms / 1000.0)
            self.log.info(format_info(INFO_RELAY_PIN3TO4_OPENED, delay=delay_ms))
        except Exception as e:
            self.log.error(format_error(ERROR_ERB08_PIN3TO4_OPEN, error=e))
            raise ERB08Error(format_error(ERROR_ERB08_PIN3TO4_OPEN, error=e)) from e
