"""
Read Resistance Test Script
============================

Simple test script to read resistance values from the Fluke 287 meter.
Useful for verifying meter communication and seeing actual readings.

Usage:
    python read_resistance.py
    python read_resistance.py --port COM11
    python read_resistance.py --continuous
"""
import sys
import time
import argparse
from pathlib import Path

# Add src/ to path
SRC_ROOT = Path(__file__).resolve().parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from element_tester.system.drivers.FLUKE287.driver import Fluke287Driver


def read_once(driver: Fluke287Driver):
    """Read a single resistance value."""
    print("Reading meter value...")
    try:
        # Try read_value() first (returns MeterReading)
        reading = driver.read_value(max_retries=3)
        if reading:
            print(f"✓ Value: {reading.value} {reading.unit}")
            print(f"  Mode: {reading.mode}")
            print(f"  Overload: {reading.is_overload}")
            print(f"  Negative: {reading.is_negative}")
            return reading.value
        else:
            print("✗ No reading received (None returned)")
            return None
    except Exception as e:
        print(f"✗ Error reading value: {e}")
        import traceback
        traceback.print_exc()
        return None


def read_resistance(driver: Fluke287Driver):
    """Read resistance specifically."""
    print("Reading resistance...")
    try:
        resistance = driver.read_resistance(average_count=1)
        print(f"✓ Resistance: {resistance} Ω")
        return resistance
    except Exception as e:
        print(f"✗ Error reading resistance: {e}")
        import traceback
        traceback.print_exc()
        return None


def read_continuous(driver: Fluke287Driver, interval: float = 1.0):
    """Continuously read values."""
    print(f"Reading continuously (every {interval}s). Press Ctrl+C to stop...")
    print("-" * 60)
    
    count = 0
    try:
        while True:
            count += 1
            print(f"\n[{count}] ", end="")
            
            # Read using read_value
            reading = driver.read_value(max_retries=2)
            if reading and reading.value is not None:
                print(f"{reading.value:.3f} {reading.unit}", end="")
                if reading.is_overload:
                    print(" [OVERLOAD]", end="")
                if reading.is_negative:
                    print(" [NEGATIVE]", end="")
            else:
                print("NO READING", end="")
            
            print()  # Newline
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\n✗ Error during continuous reading: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Test Fluke 287 resistance reading")
    parser.add_argument(
        "--port",
        type=str,
        default="COM11",
        help="Serial port for Fluke 287 (default: COM11)"
    )
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="Read continuously until Ctrl+C"
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=1.0,
        help="Interval between readings in continuous mode (default: 1.0s)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use simulated values (no hardware)"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Fluke 287 Resistance Reading Test")
    print("=" * 60)
    print(f"Port: {args.port}")
    print(f"Mode: {'SIMULATE' if args.simulate else 'HARDWARE'}")
    print()
    
    # Create driver
    print("Initializing Fluke 287 driver...")
    try:
        driver = Fluke287Driver(
            port=args.port,
            timeout=2.0,
            simulate=args.simulate
        )
        driver.initialize()
        print("✓ Driver initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize driver: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    try:
        if args.continuous:
            # Continuous reading mode
            read_continuous(driver, interval=args.interval)
        else:
            # Single reading mode
            print("-" * 60)
            print("Test 1: Read value (MeterReading)")
            print("-" * 60)
            value1 = read_once(driver)
            
            print()
            print("-" * 60)
            print("Test 2: Read resistance (float)")
            print("-" * 60)
            value2 = read_resistance(driver)
            
            print()
            print("-" * 60)
            print("Summary")
            print("-" * 60)
            print(f"read_value():      {value1}")
            print(f"read_resistance(): {value2}")
            
            if value1 is not None and value2 is not None:
                print("\n✓ Both methods working!")
            else:
                print("\n✗ One or more methods failed")
                return 1
    
    finally:
        # Clean up
        print()
        print("Shutting down driver...")
        try:
            driver.shutdown()
            print("✓ Driver shutdown complete")
        except Exception as e:
            print(f"✗ Error during shutdown: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
