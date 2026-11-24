"""Camera-side helpers: map the camera's view of the target monitor to
screen coordinates, locate the cursor, and servo it to a target.

Requires the vision extra:  pip install -e .[vision]

Coordinate convention: "screen coords" are fractions in [0, 1] x [0, 1],
(0, 0) = top-left of the monitor, (1, 1) = bottom-right. Fractions are
used because the camera never knows the target's pixel resolution, and
the servo loop doesn't need it.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np

from .link import EspMouse


class ScreenMapper:
    """Perspective mapping between camera pixels and screen fractions.

    Calibrate once by giving the four corners of the monitor as seen in
    the camera frame, in order: top-left, top-right, bottom-right,
    bottom-left (see examples/calibrate.py).
    """

    def __init__(self, corners: np.ndarray):
        corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)
        unit = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
        self.cam_to_screen = cv2.getPerspectiveTransform(corners, unit)
        self.screen_to_cam = cv2.getPerspectiveTransform(unit, corners)
        self.corners = corners

    def to_screen(self, xy_cam) -> tuple[float, float]:
        pt = np.array([[xy_cam]], dtype=np.float32)
        out = cv2.perspectiveTransform(pt, self.cam_to_screen)[0, 0]
        return float(out[0]), float(out[1])

    def to_camera(self, xy_screen) -> tuple[float, float]:
        pt = np.array([[xy_screen]], dtype=np.float32)
        out = cv2.perspectiveTransform(pt, self.screen_to_cam)[0, 0]
        return float(out[0]), float(out[1])

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"corners": self.corners.tolist()}))

    @classmethod
    def load(cls, path: str | Path) -> "ScreenMapper":
        data = json.loads(Path(path).read_text())
        return cls(np.array(data["corners"]))


class CursorFinder:
    """Locate the cursor by motion: jiggle the mouse and difference frames.

    The cursor is the only thing on screen guaranteed to move when we move
    the mouse, which makes frame differencing far more robust than
    template matching across themes, cursor shapes and screen content.
    """

    def __init__(self, camera: "cv2.VideoCapture", mouse: EspMouse,
                 jiggle: int = 12, settle: float = 0.08):
        self.cam = camera
        self.mouse = mouse
        self.jiggle = jiggle
        self.settle = settle

    def _grab_gray(self) -> np.ndarray:
        # Drain the driver's buffer so we get a current frame.
        for _ in range(2):
            self.cam.grab()
        ok, frame = self.cam.read()
        if not ok:
            raise RuntimeError("Camera read failed")
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def find(self, retries: int = 3) -> tuple[float, float] | None:
        """Return the cursor position in camera pixels, or None."""
        for _ in range(retries):
            before = self._grab_gray()
            self.mouse.move(self.jiggle, 0)
            time.sleep(self.settle)
            mid = self._grab_gray()
            self.mouse.move(-self.jiggle, 0)
            time.sleep(self.settle)

            diff = cv2.absdiff(before, mid)
            diff = cv2.GaussianBlur(diff, (5, 5), 0)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            moments = cv2.moments(thresh)
            if moments["m00"] > 10:  # enough changed pixels
                cx = moments["m10"] / moments["m00"]
                cy = moments["m01"] / moments["m00"]
                return cx, cy
        return None


class VisualServo:
    """Closed-loop 'go to (x, y)' built from relative mouse moves.

    The gain (mouse counts per screen fraction) is estimated on the fly
    from each observed move, which absorbs OS pointer acceleration and
    camera perspective without explicit calibration.
    """

    def __init__(self, mouse: EspMouse, finder: CursorFinder,
                 mapper: ScreenMapper, tolerance: float = 0.01,
                 initial_gain: float = 1500.0, max_step: int = 300):
        self.mouse = mouse
        self.finder = finder
        self.mapper = mapper
        self.tolerance = tolerance
        self.gain = initial_gain  # counts per full screen width
        self.max_step = max_step

    def locate(self) -> tuple[float, float] | None:
        cam_xy = self.finder.find()
        if cam_xy is None:
            return None
        return self.mapper.to_screen(cam_xy)

    def goto(self, tx: float, ty: float, max_iters: int = 25) -> bool:
        """Drive the cursor to screen fraction (tx, ty). True on success."""
        for _ in range(max_iters):
            pos = self.locate()
            if pos is None:
                continue
            ex, ey = tx - pos[0], ty - pos[1]
            if abs(ex) < self.tolerance and abs(ey) < self.tolerance:
                return True

            # Proportional step, damped to 70% to avoid overshoot.
            dx = int(np.clip(ex * self.gain * 0.7, -self.max_step, self.max_step))
            dy = int(np.clip(ey * self.gain * 0.7, -self.max_step, self.max_step))
            if dx == 0 and dy == 0:
                dx = 1 if ex > 0 else -1
            self.mouse.move(dx, dy)
            time.sleep(0.1)

            # Update gain from what that move actually did.
            new = self.locate()
            if new is not None and dx != 0:
                moved = new[0] - pos[0]
                if abs(moved) > 0.003:
                    observed = abs(dx / moved)
                    self.gain = 0.7 * self.gain + 0.3 * float(
                        np.clip(observed, 200, 20000))
        return False
