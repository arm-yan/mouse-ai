"""Serial link to the MouseAI ESP32 firmware.

The ESP32 presents itself to the target machine as a standard BLE mouse.
This module talks to it over USB serial using the line protocol described
in PROTOCOL.md at the repo root.
"""

from __future__ import annotations

import time

import serial
from serial.tools import list_ports

# Common USB-UART bridge chips found on ESP32 dev boards.
_KNOWN_VIDS = {0x10C4, 0x1A86, 0x0403}  # CP210x, CH340, FTDI


class MouseError(Exception):
    pass


def find_port() -> str:
    """Return the COM port of the first likely ESP32 dev board."""
    candidates = [p for p in list_ports.comports() if p.vid in _KNOWN_VIDS]
    if not candidates:
        raise MouseError(
            "No ESP32 serial port found. Is the board plugged in? "
            "Pass port= explicitly if it uses an unusual USB-UART chip."
        )
    return candidates[0].device


class EspMouse:
    def __init__(self, port: str | None = None, baud: int = 115200,
                 timeout: float = 2.0, boot_wait: float = 2.5):
        if port is None:
            port = find_port()
        # Try not to toggle DTR/RTS, which resets the ESP32 on open.
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud
        self.ser.timeout = timeout
        self.ser.dtr = False
        self.ser.rts = False
        self.ser.open()
        # On Windows the open can still pulse the reset line; give the
        # board time to boot, then discard any boot chatter.
        time.sleep(boot_wait)
        self.ser.reset_input_buffer()

    # -- low level ---------------------------------------------------------

    def _cmd(self, line: str) -> str:
        self.ser.write((line + "\n").encode("ascii"))
        while True:
            resp = self.ser.readline().decode("ascii", "replace").strip()
            if not resp:
                raise MouseError(f"Timeout waiting for reply to {line!r}")
            if resp.startswith("OK"):
                return resp
            if resp.startswith("ERR"):
                raise MouseError(f"{line!r} -> {resp}")
            # Ignore boot messages / stray output and keep reading.

    # -- status ------------------------------------------------------------

    def is_connected(self) -> bool:
        """True once the target machine has paired and connected over BLE."""
        return self._cmd("?") == "OK CONNECTED"

    def wait_connected(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_connected():
                return
            time.sleep(0.5)
        raise MouseError("Target machine did not connect over BLE in time")

    # -- actions -----------------------------------------------------------

    def move(self, dx: int, dy: int) -> None:
        """Relative move; large deltas are sent as a burst of HID reports."""
        while dx or dy:
            sx = max(-127, min(127, dx))
            sy = max(-127, min(127, dy))
            self._cmd(f"M {sx} {sy}")
            dx -= sx
            dy -= sy

    def click(self, button: str = "l") -> None:
        self._cmd(f"C {self._btn(button)}")

    def press(self, button: str = "l") -> None:
        self._cmd(f"D {self._btn(button)}")

    def release(self, button: str = "l") -> None:
        self._cmd(f"U {self._btn(button)}")

    def scroll(self, n: int) -> None:
        """Positive scrolls up, negative down."""
        while n:
            step = max(-127, min(127, n))
            self._cmd(f"S {step}")
            n -= step

    def drag(self, dx: int, dy: int, button: str = "l",
             step: int = 15, delay: float = 0.01) -> None:
        """Press, move in small steps so the OS registers a drag, release."""
        self.press(button)
        try:
            while dx or dy:
                sx = max(-step, min(step, dx))
                sy = max(-step, min(step, dy))
                self.move(sx, sy)
                dx -= sx
                dy -= sy
                time.sleep(delay)
        finally:
            self.release(button)

    def close(self) -> None:
        self.ser.close()

    def __enter__(self) -> "EspMouse":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @staticmethod
    def _btn(button: str) -> str:
        b = button[:1].lower()
        if b not in ("l", "r", "m"):
            raise ValueError(f"Unknown button {button!r}; use l, r or m")
        return b
