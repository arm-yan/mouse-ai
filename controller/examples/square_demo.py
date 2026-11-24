"""Smoke test: once the target machine has paired with the ESP32,
the cursor on the target should trace a square.

Run from the controller/ directory:
    python examples/square_demo.py [COM_PORT]
"""

import sys
import time

from mouseai import EspMouse


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else None
    with EspMouse(port=port) as mouse:
        print("Waiting for the target machine to connect over BLE...")
        mouse.wait_connected()
        print("Connected. Tracing a square on the target's screen.")
        for dx, dy in [(200, 0), (0, 200), (-200, 0), (0, -200)]:
            mouse.move(dx, dy)
            time.sleep(0.4)
        print("Done.")


if __name__ == "__main__":
    main()
