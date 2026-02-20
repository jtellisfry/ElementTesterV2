from __future__ import annotations

from typing import Optional

import serial


class SerialTransport:
    """Low-level serial transport for the Fluke 287 meter."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        bytesize: int = serial.EIGHTBITS,
        parity: str = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        xonxoff: bool = True,
        rtscts: bool = False,
        dsrdtr: bool = False,
        timeout: float = 0.1,
    ) -> None:
        self._ser = serial.Serial()
        self._ser.port = port
        self._ser.baudrate = baudrate
        self._ser.bytesize = bytesize
        self._ser.parity = parity
        self._ser.stopbits = stopbits
        self._ser.xonxoff = xonxoff
        self._ser.rtscts = rtscts
        self._ser.dsrdtr = dsrdtr
        self._ser.timeout = timeout

    @property
    def is_open(self) -> bool:
        return self._ser.is_open

    def open(self) -> None:
        if not self._ser.is_open:
            self._ser.open()

    def close(self) -> None:
        if self._ser.is_open:
            self._ser.close()

    def flush_input(self) -> None:
        """Clear input buffer (wrapper for serial flushInput)."""
        if self._ser.is_open:
            self._ser.flushInput()

    def send_command(self, command: str) -> bytes:
        """Send an ASCII command and read until two CR terminators or timeout."""
        self._ser.flushInput()
        self._ser.flushOutput()
        self._ser.write((command + "\r").encode("utf-8"))

        response = b""
        second_eol = False
        while True:
            c = self._ser.read(1)
            if c:
                response += c
                if c == b"\r":
                    if second_eol:
                        break
                    second_eol = True
            else:
                break
        return response
