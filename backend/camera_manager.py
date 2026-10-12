"""Local USB webcam and YOLO person detection for the Flask dashboard."""
from __future__ import annotations

import logging
import platform
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
    """Manage a local webcam with background thread capture and optimized YOLO detection."""

    def __init__(self, state: StateStore | None = None) -> None:
        self.state = state or StateStore()
        self.camera_index = CAMERA_INDEX
        self.camera: Any | None = None
        self.model: Any | None = None
        self._lock = threading.Lock()
        self._last_detection = False
        self._last_count = 0
        self._latest_frame_jpeg: bytes | None = None
        self._latest_content_type = "image/jpeg"
        self._cached_boxes: list[tuple[int, int, int, int, float]] = []
        self._frame_count = 0
        self._running = False
        self._worker_thread: threading.Thread | None = None

    def open(self) -> bool:
        if cv2 is None:
            self.state.update_camera(False, False)
            return False
        with self._lock:
            if self.camera is not None and self.camera.isOpened():
                return True
            try:
                # Use DirectShow on Windows to prevent MSMF startup delay, buffer lag, and shuttering
                if platform.system() == "Windows":
                    self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                else:
                    self.camera = cv2.VideoCapture(self.camera_index)

                if not self.camera.isOpened():
                    self.camera = cv2.VideoCapture(self.camera_index)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Could not open webcam at index %s: %s", self.camera_index, exc)
                self.camera = None
                return False

            if self.camera is None or not self.camera.isOpened():
                self.camera = None
                self.state.update_camera(False, False)
                return False

            # Set hardware properties for smooth, low-latency streaming
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            try:
                from ultralytics import YOLO

                self.model = YOLO(YOLO_MODEL)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("YOLO model not available for camera detection: %s", exc)
                self.model = None

            self.state.update_camera(False, True)
            self._start_worker()
            return True

    def _start_worker(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._capture_loop, name="camera-worker", daemon=True)
        self._worker_thread.start()

    def _capture_loop(self) -> None:
        """Background thread continuously grabbing frames and running YOLO smoothly."""
        while self._running:
            if self.camera is None or not self.camera.isOpened():
                time.sleep(0.05)
                continue

            with self._lock:
                success, frame = self.camera.read()

            if not success or frame is None:
                self.state.update_camera(False, False)
                time.sleep(0.04)
                continue

            self._frame_count += 1
            # Run YOLO inference every 3rd frame (or if cache is empty) to keep stream at 25-30 FPS without CPU stutter
            if self.model is not None and (self._frame_count % 3 == 0 or not self._cached_boxes):
                self._run_yolo_detection(frame)

            # Draw smooth bounding boxes onto the frame
            display_frame = self._draw_detections(frame)

            data, content_type = self._encode_frame(display_frame)
            with self._lock:
                self._latest_frame_jpeg = data
                self._latest_content_type = content_type

            # Frame pacing: ~25-30 FPS
            time.sleep(0.033)

    def _run_yolo_detection(self, frame: Any) -> None:
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            # imgsz=320 gives ~3x faster inference on CPU while preserving person detection accuracy
            results = self.model.predict(source=frame, classes=[0], conf=0.35, imgsz=320, device=device, verbose=False)
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                count = len(boxes)
                cached = []
                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cached.append((int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]), conf))
                self._cached_boxes = cached
                self._last_count = count
                self._last_detection = count > 0
                self.state.update_camera(self._last_detection, True)
            else:
                self._cached_boxes = []
                self._last_count = 0
                self._last_detection = False
                self.state.update_camera(False, True)
        except Exception as exc:
            LOGGER.debug("YOLO detection error: %s", exc)

    def _draw_detections(self, frame: Any) -> Any:
        if cv2 is None or not self._cached_boxes:
            return frame
        display = frame.copy()
        for x1, y1, x2, y2, conf in self._cached_boxes:
            cv2.rectangle(display, (x1, y1), (x2, y2), (79, 214, 133), 2)
            label = f"Person {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(display, (x1, max(0, y1 - 20)), (x1 + w, y1), (79, 214, 133), -1)
            cv2.putText(display, label, (x1, max(14, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (9, 13, 12), 1, cv2.LINE_AA)
        return display

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
            return frame.convert("RGB").resize((640, 480)).tobytes(), "image/jpeg"

        success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not success or buffer is None or len(buffer) == 0:
            fallback = self._placeholder_frame("Camera frame error")
            success, buffer = cv2.imencode(".jpg", fallback, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        return buffer.tobytes(), "image/jpeg"

    def get_snapshot_jpeg(self) -> tuple[bytes, str]:
        """Return a single JPEG frame without initiating an ongoing stream."""
        if not self.open():
            placeholder = self._placeholder_frame("Webcam unavailable")
            return self._encode_frame(placeholder)
        with self._lock:
            data = self._latest_frame_jpeg
            content_type = self._latest_content_type
        if data is None:
            placeholder = self._placeholder_frame("Camera ready")
            return self._encode_frame(placeholder)
        return data, content_type

    def generate_frames(self):
        """Yield frames smoothly from the single background capture worker."""
        if not self.open():
            placeholder = self._placeholder_frame("Webcam unavailable")
            data, content_type = self._encode_frame(placeholder)
            yield (
                b"--frame\r\n"
                + f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + data + b"\r\n"
            )
            return

        while True:
            with self._lock:
                data = self._latest_frame_jpeg
                content_type = self._latest_content_type

            if data is None:
                placeholder = self._placeholder_frame("Initializing stream...")
                data, content_type = self._encode_frame(placeholder)

            yield (
                b"--frame\r\n"
                + f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + data + b"\r\n"
            )
            time.sleep(0.04)
