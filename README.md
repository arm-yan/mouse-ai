# MouseAI

An ESP32 that the target machine sees as a **standard Bluetooth mouse**,
driven by an AI running on a separate notebook that watches the target's
monitor through a camera.

```
AI notebook ──USB serial──► ESP32 ──BLE HID──► target machine
     ▲                                              │
     └────────────── camera watches monitor ────────┘
```

The target machine needs no software, drivers, or configuration beyond
pairing a Bluetooth mouse once. The feedback loop is closed through the
camera: the AI sees the cursor, nudges it with relative moves, and looks
again (visual servoing).

## Layout

- [firmware/](firmware/) — PlatformIO project for the ESP32 (BLE HID mouse + serial command port)
- [controller/](controller/) — Python package `mouseai` used on the AI notebook
- [PROTOCOL.md](PROTOCOL.md) — the serial protocol between the two

## Setup

### 1. Flash the firmware

Install [PlatformIO Core](https://platformio.org/install/cli) (or the VS Code
extension), plug the ESP32 into the notebook, then:

```
cd firmware
pio run -t upload
```

If the upload can't find the port, pass it explicitly:
`pio run -t upload --upload-port COM5`. Some boards need the BOOT button
held during the "Connecting..." phase.

### 2. Pair the target machine

On the target machine, open Bluetooth settings and pair with **Nazar**.
It appears and behaves like an ordinary Bluetooth mouse. Pairing is needed
once; afterwards it reconnects automatically whenever the ESP32 is powered.

### 3. Install the controller library on the AI notebook

```
cd controller
pip install -e .          # add [vision] for the camera loop: pip install -e .[vision]
```

On **Ubuntu/Linux** additionally:

- No USB driver needed — the CP210x driver ships with the kernel; the board
  appears as `/dev/ttyUSB0` (auto-detected by the library).
- Give yourself permission to open serial ports (once, then log out/in):

  ```
  sudo usermod -aG dialout $USER
  ```

### 4. Smoke test

With the ESP32 plugged in and the target paired:

```
cd controller
python examples/square_demo.py
```

The cursor on the target machine should trace a square.

## Using the library

```python
from mouseai import EspMouse

with EspMouse() as mouse:          # auto-detects the COM port
    mouse.wait_connected()         # until the target is connected over BLE
    mouse.move(300, -50)           # relative, chunked into HID reports
    mouse.click("l")               # l / r / m
    mouse.drag(120, 0)             # press, move smoothly, release
    mouse.scroll(-3)               # negative = down
```

## Notes and gotchas

- **Opening the serial port may reset the ESP32** (DTR line). `EspMouse`
  waits ~2.5 s after opening for the board to boot; the BLE link to the
  target then re-establishes itself within a few seconds. Keep the port
  open for the whole session rather than reopening per command.
- **Moves are relative.** There is no "go to pixel (x, y)" — that is by
  design, so the device stays a plain standard mouse. Absolute targeting
  is done in the camera loop: estimate where the cursor is, move a
  fraction of the error, re-observe, repeat.
- **One host at a time.** The BLE HID connection is bonded to the machine
  that paired. To move it to a different target, unpair there and pair on
  the new one.

## Next step: the vision loop

The planned `mouseai[vision]` extra (OpenCV) will add:

1. **Screen homography** — detect the monitor's quadrilateral in the camera
   frame (or use four clicked corner points once) and map camera pixels to
   screen-relative coordinates.
2. **Cursor localisation** — find the pointer in the rectified frame
   (template matching, or frame-differencing while jiggling the mouse,
   which makes the cursor the only thing moving).
3. **Servo controller** — `goto(x_frac, y_frac)`: move a proportional step
   toward the target, re-detect, stop within tolerance. This also
   self-calibrates the mouse-counts-per-screen-fraction gain, absorbing
   OS pointer acceleration.
