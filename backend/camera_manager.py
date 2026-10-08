"""Local USB webcam and YOLO person detection for the Flask dashboard."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - optional local vision dependency
    cv2 = None
    np = None

from backend.config import CAMERA_INDEX, YOLO_MODEL
from backend.state_store import StateStore

LOGGER = logging.getLogger(__name__)


class CameraManager:
    """Manage a local webcam and expose detection metadata to the dashboard."""

    def __init__(self, state: StateStore | None = None) -> None:
        self.state = state or StateStore()
        self.camera_index = CAMERA_INDEX
        self.camera: Any | None = None
        self.model: Any | None = None
        self._lock = threading.Lock()
        self._last_detection = False
        self._last_count = 0

    def open(self) -> bool:
        if cv2 is None:
            self.state.update_camera(False, False)
            return False
        with self._lock:
            if self.camera is not None and self.camera.isOpened():
                return True
            try:
                self.camera = cv2.VideoCapture(self.camera_index)
            except Exception as exc:  # pragma: no cover - hardware-dependent path
                LOGGER.warning("Could not open webcam at index %s: %s", self.camera_index, exc)
                self.camera = None
                return False

            if self.camera is None or not self.camera.isOpened():
                self.camera = None
                self.state.update_camera(False, False)
                return False

            try:
                from ultralytics import YOLO

                self.model = YOLO(YOLO_MODEL)
            except Exception as exc:  # pragma: no cover - model download may happen on first use
                LOGGER.warning("YOLO model not available for camera detection: %s", exc)
                self.model = None
            return True

    def _read_frame(self) -> tuple[bool, Any | None]:
        if self.camera is None and not self.open():
            return False, None
        if self.camera is None or not self.camera.isOpened():
            self.state.update_camera(False, False)
            return False, None
        with self._lock:
            success, frame = self.camera.read()
        if not success or frame is None:
            self.state.update_camera(False, False)
            return False, None
        return True, frame

    def _detect_people(self, frame: Any) -> tuple[bool, int, Any]:
        if self.model is None:
            return False, 0, frame

        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            results = self.model.predict(source=frame, classes=[0], conf=0.35, device=device, verbose=False)
        except Exception as exc:  # pragma: no cover - model load/runtime dependent
            LOGGER.warning("YOLO detection failed: %s", exc)
            return False, 0, frame

        if not results:
            return False, 0, frame
        boxes = results[0].boxes
        if boxes is None:
            return False, 0, frame

        person_count = len(boxes)
        annotated = results[0].plot()
        return person_count > 0, person_count, annotated

    def snapshot(self) -> dict[str, Any]:
        return {
            "person_detected": bool(self._last_detection),
            "person_count": int(self._last_count),
            "camera_connected": bool(self.camera is not None and self.camera.isOpened()),
        }

    def _placeholder_frame(self, message: str):
        if cv2 is None or np is None:
            from PIL import Image, ImageDraw, ImageFont

            image = Image.new("RGB", (640, 480), color=(9, 13, 12))
            draw = ImageDraw.Draw(image)
            try:
                draw.text((40, 225), message, fill=(79, 214, 133))
            except Exception:
                draw.text((40, 225), message, fill=(79, 214, 133), font=ImageFont.load_default())
            return image

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(image, (0, 0), (640, 480), (9, 13, 12), -1)
        cv2.putText(image, message, (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (79, 214, 133), 2, cv2.LINE_AA)
        return image

    def _encode_frame(self, frame):
        if cv2 is None:
            from PIL import Image

            if not isinstance(frame, Image.Image):
                frame = Image.new("RGB", (640, 480), color=(9, 13, 12))
            return frame.convert("RGB").resize((640, 480)).tobytes(), "JPEG"

        encoded, _ = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not encoded.any():
            fallback = self._placeholder_frame("Camera frame error")
            encoded, _ = cv2.imencode(".jpg", fallback, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        return encoded.tobytes(), "image/jpeg"

    def generate_frames(self):
        while True:
            success, frame = self._read_frame()
            if not success or frame is None:
                frame = self._placeholder_frame("Webcam unavailable")
                self.state.update_camera(False, False)
            else:
                detected, count, frame = self._detect_people(frame)
                self._last_detection = bool(detected)
                self._last_count = int(count)
                self.state.update_camera(detected, True)

            data, content_type = self._encode_frame(frame)
            yield (
                b"--frame\r\n"
                + f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + data + b"\r\n"
            )
            time.sleep(0.1)
