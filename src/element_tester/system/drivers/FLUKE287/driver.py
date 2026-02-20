from __future__ import annotations

from typing import Optional
import logging
from dataclasses import dataclass

from .procedures import read_resistance_measurement
from .transport import SerialTransport
from .commands import read_qm


@dataclass
class MeterReading:
    """Compatible meter reading object for measurement tests."""
    value: Optional[float]
    unit: str
    mode: str = "resistance"
    is_overload: bool = False
    is_negative: bool = False
    flags: dict = None
    
    def __post_init__(self):
        if self.flags is None:
            self.flags = {}


class Fluke287Driver:
    """User-facing driver interface for the Fluke 287 meter."""

    def __init__(
        self, 
        port: str, 
        timeout: float = 2.0,
        simulate: bool = False,
        logger: Optional[logging.Logger] = None,
        **serial_kwargs
    ) -> None:
        """
        Initialize Fluke 287 driver.
        
        Args:
            port: Serial port (e.g., "COM11")
            timeout: Serial timeout in seconds
            simulate: If True, simulate readings without hardware
            logger: Optional logger instance
            **serial_kwargs: Additional serial port parameters
        """
        self.log = logger or logging.getLogger("element_tester.driver.fluke287")
        self.port = port
        self.timeout = timeout
        self.simulate = simulate
        self._transport = SerialTransport(port=port, timeout=timeout, **serial_kwargs)

    def initialize(self) -> None:
        """Initialize connection to meter (alias for connect)."""
        try:
            self.connect()
            self.log.info(f"Fluke 287 initialized on {self.port}")
            
            # Test communication with a quick read
            if not self.simulate:
                try:
                    test_reading = self.read_value(max_retries=1)
                    if test_reading:
                        self.log.info(f"Fluke 287 communication test OK: {test_reading.value} {test_reading.unit}")
                    else:
                        self.log.warning(f"Fluke 287 on {self.port} - No response during communication test")
                except Exception as e:
                    self.log.warning(f"Fluke 287 on {self.port} - Communication test failed: {e}")
        except Exception as e:
            self.log.error(f"Failed to initialize Fluke 287 on {self.port}: {e}", exc_info=True)
            raise

    def shutdown(self) -> None:
        """Close connection to meter (alias for disconnect)."""
        self.disconnect()
        self.log.info(f"Fluke 287 shutdown on {self.port}")

    def connect(self) -> None:
        self._transport.open()

    def disconnect(self) -> None:
        self._transport.close()

    def read_resistance(self, average_count: int = 1) -> float:
        """
        Read resistance value.
        
        Args:
            average_count: Number of samples to average (default 1)
            
        Returns:
            Resistance in Ohms
        """
        if self.simulate:
            self.log.debug("Simulating resistance reading")
            return 6.5  # Simulated value
        
        if average_count == 1:
            return read_resistance_measurement(self._transport)
        else:
            # Take multiple readings and average
            readings = []
            for _ in range(average_count):
                readings.append(read_resistance_measurement(self._transport))
            return sum(readings) / len(readings)

    def read_value(self, max_retries: int = 3) -> Optional[MeterReading]:
        """
        Read current displayed value as MeterReading (compatible with measurement test).
        
        Args:
            max_retries: Number of retry attempts on error
            
        Returns:
            MeterReading object with value and unit, or None on failure
        """
        if self.simulate:
            self.log.debug("Simulating meter reading")
            return MeterReading(
                value=6.5,
                unit="Ohm",
                mode="resistance"
            )
        
        for attempt in range(max_retries):
            try:
                # Use the existing QM command to read value
                measurement = read_qm(self._transport)
                
                # Convert to MeterReading format
                return MeterReading(
                    value=measurement.value,
                    unit=measurement.unit,
                    mode="measurement",
                    is_overload=False,
                    is_negative=(measurement.value < 0 if measurement.value is not None else False)
                )
            except Exception as e:
                self.log.debug(f"Read attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    self.log.error(f"Failed to read value after {max_retries} attempts: {e}")
                    return None
                import time
                time.sleep(0.2)  # Brief delay before retry
        
        return None

    def flush_buffer(self) -> None:
        """
        Clear any buffered serial data.
        
        This is critical after relay switching to discard stale readings
        from previous configurations. Call after closing relays and before
        taking measurements.
        """
        try:
            if hasattr(self._transport, 'flush_input'):
                self._transport.flush_input()
            elif hasattr(self._transport, 'reset_input_buffer'):
                self._transport.reset_input_buffer()
            self.log.debug("Flushed serial buffer")
        except Exception as e:
            self.log.warning(f"Failed to flush buffer: {e}")

    def __enter__(self) -> "Fluke287Driver":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fluke 287 meter driver")
    parser.add_argument("port", help="Serial port to connect to (e.g. COM3 or /dev/ttyUSB0)")
    args = parser.parse_args()

    with Fluke287Driver(port=args.port) as driver:
        resistance = driver.read_resistance()
        print(f"Resistance: {resistance} ohms")