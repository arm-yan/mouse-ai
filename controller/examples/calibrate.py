"""One-time calibration: click the four corners of the target monitor as
seen by the camera. Saves the mapping to screen_map.json.

    python examples/calibrate.py [camera_index]

Click order: top-left, top-right, bottom-right, bottom-left.
Press R to restart, Q to quit without saving.
"""

import sys

import cv2
import numpy as np

from mouseai.vision import ScreenMapper

ORDER = ["top-left", "top-right", "bottom-right", "bottom-left"]


def main() -> None:
    cam_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cam = cv2.VideoCapture(cam_index)
    if not cam.isOpened():
        sys.exit(f"Could not open camera {cam_index}")

    points: list[tuple[int, int]] = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)

    while True:
        ok, frame = cam.read()
        if not ok:
            continue
        for i, p in enumerate(points):
            cv2.circle(frame, p, 6, (0, 255, 0), -1)
            cv2.putText(frame, ORDER[i], (p[0] + 8, p[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        if len(points) < 4:
            msg = f"Click the {ORDER[len(points)]} corner of the monitor"
        else:
            cv2.polylines(frame, [np.array(points)], True, (0, 255, 0), 2)
            msg = "Press S to save, R to restart"
        cv2.putText(frame, msg, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 200, 255), 2)
        cv2.imshow("calibrate", frame)

        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            points.clear()
        if key == ord("s") and len(points) == 4:
            ScreenMapper(np.array(points)).save("screen_map.json")
            print("Saved screen_map.json")
            break

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
