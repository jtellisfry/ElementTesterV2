from __future__ import annotations

from dataclasses import dataclass


QM_COMMAND = "QM"


@dataclass(frozen=True)
class Measurement:
    ack: str
    value: float
    unit: str
    state: str
    attribute: str


def parse_qm_response(response: bytes) -> Measurement:
    if not response:
        raise ValueError("No response from meter")

    response_string = response.decode("utf-8")
    response_split = response_string.split("\r")
    if len(response_split) != 3:
        raise ValueError("Unexpected response format (CR count)")

    ack = response_split[0]
    measurement_split = response_split[1].split(",")
    if len(measurement_split) != 4:
        raise ValueError("Unexpected response format (fields)")

    value_str, unit, state, attribute = measurement_split
    try:
        value = float(value_str)
    except ValueError as exc:
        raise ValueError("Invalid numeric value in response") from exc

    return Measurement(
        ack=ack,
        value=value,
        unit=unit,
        state=state,
        attribute=attribute,
    )


def read_qm(transport) -> Measurement:
    response = transport.send_command(QM_COMMAND)
    return parse_qm_response(response)
