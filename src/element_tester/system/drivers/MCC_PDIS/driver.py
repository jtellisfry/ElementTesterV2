from __future__ import annotations
from typing import Optional, List, Iterable
import logging

from .procedures import PDIS08Procedures, RelayMapping


class PDIS08Driver:
    """High-level driver facade for PDIS08 relay board."""

    def __init__(
        self,
        board_num: int = 1,
        port_low=1,
        port_high=None,
        simulate: bool = False,
        active_high: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.log = logger or logging.getLogger("element_tester.relay.mcc_pdis.driver")
        self.procs = PDIS08Procedures(
            board_num=board_num,
            port_low=port_low,
            port_high=port_high,
            simulate=simulate,
            active_high=active_high,
            logger=self.log,
        )

    def initialize(self) -> None:
        self.procs.ProcInitializeRelays()

    def shutdown(self) -> None:
        self.procs.ProcShutdownRelays()

    def set_relay(self, channel: int, on: bool) -> None:
        self.procs.ProcSetBit(channel, on)

    def all_off(self) -> None:
        self.procs.ProcAllOff()

    def all_on(self) -> None:
        self.procs.ProcAllOn()

    def apply_mapping(
        self,
        bits_on: Iterable[int],
        bits_off: Iterable[int],
    ) -> None:
        """Apply a relay mapping directly (compatible with ERB08Driver interface)."""
        mapping = RelayMapping(
            bits_on=list(bits_on),
            bits_off=list(bits_off),
        )
        self.procs.ProcApplyMapping(mapping)

    def add_named_mapping(self, name: str, bits_on: List[int], bits_off: List[int]) -> None:
        self.procs.add_named_mapping(name, bits_on, bits_off)

    def apply_named_mapping(self, name: str) -> None:
        self.procs.ProcApplyNamedMapping(name)

    def self_test_walk(self, delay_ms: float = 100.0) -> None:
        self.procs.ProcSelfTestWalk(delay_ms)

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
            self.log.info("RELAY: Pin1to6 closed with {0}ms settling delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to close Pin1to6: {0}".format(e))
            raise Exception("Failed to close Pin1to6: {0}".format(e)) from e

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
            self.log.info("RELAY: Pin1to6 opened with {0}ms delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to open Pin1to6: {0}".format(e))
            raise Exception("Failed to open Pin1to6: {0}".format(e)) from e

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
            self.log.info("RELAY: Pin2to5 closed with {0}ms settling delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to close Pin2to5: {0}".format(e))
            raise Exception("Failed to close Pin2to5: {0}".format(e)) from e

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
            self.log.info("RELAY: Pin2to5 opened with {0}ms delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to open Pin2to5: {0}".format(e))
            raise Exception("Failed to open Pin2to5: {0}".format(e)) from e

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
            #self.set_relay(4, True)  # Meter position
            self.set_relay(3, True)  # Pin 4
            time.sleep(delay_ms / 1000.0)
            self.log.info("RELAY: Pin3to4 closed with {0}ms settling delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to close Pin3to4: {0}".format(e))
            raise Exception("Failed to close Pin3to4: {0}".format(e)) from e

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
            self.log.info("RELAY: Pin3to4 opened with {0}ms delay".format(delay_ms))
        except Exception as e:
            self.log.error("Failed to open Pin3to4: {0}".format(e))
            raise Exception("Failed to open Pin3to4: {0}".format(e)) from e
