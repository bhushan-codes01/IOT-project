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

from backend.config import CAMERA_EXPOSURE, CAMERA_INDEX, YOLO_MODEL
from backend.state_store import StateStore

LOGGER = logging.getLogger(__name__)


class CameraManager:
    """Manage a local webcam with asynchronous YOLO detection, MJPG streaming, and shutter/exposure control."""

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
        self._capture_thread: threading.Thread | None = None
        self._yolo_thread: threading.Thread | None = None
        self._pending_raw_frame: Any | None = None
        self._yolo_busy = False
        self._current_exposure: float | None = float(CAMERA_EXPOSURE) if CAMERA_EXPOSURE else -6.0

    def open(self) -> bool:
        if cv2 is None:
            self.state.update_camera(False, False)
            return False
        with self._lock:
            if self.camera is not None and self.camera.isOpened():
                return True
            try:
                # Use DirectShow on Windows for low latency
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

            # Force hardware MJPG codec to eliminate USB transfer bottlenecks and slow shutter
            try:
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            except Exception:
                pass

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            # Apply shutter speed / exposure if configured
            if self._current_exposure is not None:
                self._apply_exposure(self._current_exposure)

            try:
                from ultralytics import YOLO

                self.model = YOLO(YOLO_MODEL)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("YOLO model not available for camera detection: %s", exc)
                self.model = None

            self.state.update_camera(False, True)
            self._start_workers()
            return True

    def _apply_exposure(self, exposure_val: float) -> bool:
        """Apply exposure value (e.g. -6 = 1/64s, -7 = 1/128s fast shutter)."""
        if self.camera is None or not self.camera.isOpened():
            return False
        try:
            # On DirectShow: exposure is log2 seconds (-6 = 1/64s, -7 = 1/128s)
            self.camera.set(cv2.CAP_PROP_EXPOSURE, float(exposure_val))
            self._current_exposure = float(exposure_val)
            LOGGER.info("Camera exposure set to %s", self._current_exposure)
            return True
        except Exception as exc:
            LOGGER.warning("Failed to set camera exposure: %s", exc)
            return False

    def set_exposure(self, exposure_val: float | None) -> bool:
        with self._lock:
            if exposure_val is None:
                if self.camera is not None and self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                self._current_exposure = None
                return True
            return self._apply_exposure(exposure_val)

    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            actual_exp = None
            if self.camera is not None and self.camera.isOpened():
                try:
                    actual_exp = float(self.camera.get(cv2.CAP_PROP_EXPOSURE))
                except Exception:
                    actual_exp = self._current_exposure
            return {
                "exposure": actual_exp if actual_exp is not None else self._current_exposure,
                "camera_index": self.camera_index,
                "fps": 30,
            }

    def _start_workers(self) -> None:
        if self._running:
            return
        self._running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, name="camera-capture", daemon=True)
        self._capture_thread.start()
        self._yolo_thread = threading.Thread(target=self._yolo_loop, name="camera-yolo", daemon=True)
        self._yolo_thread.start()

    def _capture_loop(self) -> None:
        """Continuously grab frames at full hardware 30 FPS without blocking on YOLO."""
        while self._running:
            if self.camera is None or not self.camera.isOpened():
                time.sleep(0.05)
                continue

            # Direct hardware capture - blocks until next frame is ready from camera
            success, frame = self.camera.read()

            if not success or frame is None:
                self.state.update_camera(False, False)
                time.sleep(0.02)
                continue

            # Pass latest frame to async YOLO worker if ready
            with self._lock:
                self._pending_raw_frame = frame

            # Render bounding boxes onto frame and encode JPEG
            display_frame = self._draw_detections(frame)
            data, content_type = self._encode_frame(display_frame)

            with self._lock:
                self._frame_count += 1
                self._latest_frame_jpeg = data
                self._latest_content_type = content_type

    def _yolo_loop(self) -> None:
        """Asynchronous YOLO inference worker that never stalls the camera capture stream."""
        while self._running:
            frame_to_process = None
            with self._lock:
                if self._pending_raw_frame is not None:
                    frame_to_process = self._pending_raw_frame
                    self._pending_raw_frame = None

            if frame_to_process is None or self.model is None:
                time.sleep(0.01)
                continue

            self._run_yolo_detection(frame_to_process)
            time.sleep(0.02)

    def _run_yolo_detection(self, frame: Any) -> None:
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            results = self.model.predict(source=frame, classes=[0], conf=0.35, imgsz=320, device=device, verbose=False)
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                count = len(boxes)
                cached = []
                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cached.append((int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]), conf))
                with self._lock:
                    self._cached_boxes = cached
                    self._last_count = count
                    self._last_detection = count > 0
                self.state.update_camera(self._last_detection, True)
            else:
                with self._lock:
                    self._cached_boxes = []
                    self._last_count = 0
                    self._last_detection = False
                self.state.update_camera(False, True)
        except Exception as exc:
            LOGGER.debug("YOLO detection error: %s", exc)

    def _draw_detections(self, frame: Any) -> Any:
        with self._lock:
            boxes = list(self._cached_boxes)
        if cv2 is None or not boxes:
            return frame
        display = frame.copy()
        for x1, y1, x2, y2, conf in boxes:
            cv2.rectangle(display, (x1, y1), (x2, y2), (79, 214, 133), 2)
            label = f"Person {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(display, (x1, max(0, y1 - 20)), (x1 + w, y1), (79, 214, 133), -1)
            cv2.putText(display, label, (x1, max(14, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (9, 13, 12), 1, cv2.LINE_AA)
        return display

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "person_detected": bool(self._last_detection),
                "person_count": int(self._last_count),
                "camera_connected": bool(self.camera is not None and self.camera.isOpened()),
                "exposure": self._current_exposure,
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

        success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not success or buffer is None or len(buffer) == 0:
            fallback = self._placeholder_frame("Camera frame error")
            success, buffer = cv2.imencode(".jpg", fallback, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
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
        """Yield frames smoothly and immediately from the background capture worker."""
        if not self.open():
            placeholder = self._placeholder_frame("Webcam unavailable")
            data, content_type = self._encode_frame(placeholder)
            yield (
                b"--frame\r\n"
                + f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + data + b"\r\n"
            )
            return

        last_id = -1
        while self._running:
            with self._lock:
                current_id = self._frame_count
                data = self._latest_frame_jpeg
                content_type = self._latest_content_type

            if data is not None and current_id != last_id:
                last_id = current_id
                yield (
                    b"--frame\r\n"
                    + f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + data + b"\r\n"
                )
            time.sleep(0.01)
