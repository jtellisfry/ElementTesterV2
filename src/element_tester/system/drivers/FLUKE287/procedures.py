from __future__ import annotations

from .commands import read_qm


def read_resistance_measurement(transport) -> float:
    measurement = read_qm(transport)
    unit_norm = measurement.unit.strip().lower()
    if "ohm" not in unit_norm:
        raise ValueError(f"Meter is not in resistance mode (unit={measurement.unit})")
    return measurement.value
