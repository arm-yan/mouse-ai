"""End-to-end test of the camera loop: steer the cursor to the center of
the target monitor, then to each corner region.

Prerequisites:
  - firmware flashed, target machine paired with "Nazar"
  - pip install -e .[vision]
  - examples/calibrate.py has saved screen_map.json

    python examples/goto_demo.py [camera_index]
"""

import sys

import cv2

from mouseai import EspMouse
from mouseai.vision import CursorFinder, ScreenMapper, VisualServo

TARGETS = [(0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]


def main() -> None:
    cam_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cam = cv2.VideoCapture(cam_index)
    if not cam.isOpened():
        sys.exit(f"Could not open camera {cam_index}")

    mapper = ScreenMapper.load("screen_map.json")
    with EspMouse() as mouse:
        print("Waiting for the target machine's BLE connection...")
        mouse.wait_connected()
        servo = VisualServo(mouse, CursorFinder(cam, mouse), mapper)
        for tx, ty in TARGETS:
            ok = servo.goto(tx, ty)
            print(f"goto({tx}, {ty}): {'reached' if ok else 'FAILED'}  "
                  f"gain={servo.gain:.0f}")

    cam.release()


if __name__ == "__main__":
    main()
