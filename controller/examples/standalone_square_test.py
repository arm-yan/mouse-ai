"""Self-contained smoke test — no mouseai package needed, only pyserial.

Copy this single file to the controlling notebook, then:

    pip install pyserial
    python standalone_square_test.py          (auto-detects the port)
    python standalone_square_test.py COM7     (or name it explicitly)

The cursor on the paired target machine should trace a square.
"""

import sys
import time

import serial
from serial.tools import list_ports


def find_port():
    for p in list_ports.comports():
        if p.vid in (0x10C4, 0x1A86, 0x0403):  # CP210x / CH340 / FTDI
            return p.device
    sys.exit("No ESP32 serial port found. Pass it explicitly, e.g.: "
             "python standalone_square_test.py COM7")


def cmd(ser, line):
    ser.write((line + "\n").encode())
    while True:
        resp = ser.readline().decode(errors="replace").strip()
        if not resp:
            sys.exit(f"Timeout waiting for reply to {line!r}")
        if resp.startswith(("OK", "ERR")):
            return resp


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    print(f"Opening {port}...")
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 3
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(2.5)  # board may reset on open
    ser.reset_input_buffer()

    print("Waiting for the target machine's Bluetooth connection...")
    for _ in range(60):
        if cmd(ser, "?") == "OK CONNECTED":
            break
        time.sleep(1)
    else:
        sys.exit("Target never connected over Bluetooth.")

    print("Connected! Tracing a square on the target's screen...")
    for dx, dy in [(120, 0), (0, 120), (-120, 0), (0, -120)]:
        for _ in range(3):  # 3 steps per side so the motion is visible
            cmd(ser, f"M {dx // 3} {dy // 3}")
            time.sleep(0.05)
        time.sleep(0.3)
    print("Done — did the cursor move in a square?")
    ser.close()


if __name__ == "__main__":
    main()
