"""Laptop USB camera + YOLO person detector; publishes detection state only."""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import paho.mqtt.client as mqtt
from ultralytics import YOLO

from backend.config import CAMERA_INDEX, MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_SENSOR, YOLO_MODEL


class HumanDetector:
    def __init__(self, model_path: str = YOLO_MODEL, camera_index: int = CAMERA_INDEX, confidence: float = 0.35) -> None:
        self.model = YOLO(model_path)
        try:
            import torch
            self.device = 0 if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"
        self.camera_index = camera_index
        self.confidence = confidence

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            classes=[0],
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )
        detected = bool(results and results[0].boxes is not None and len(results[0].boxes) > 0)
        if results:
            frame = results[0].plot()
        return detected, frame

    def run(self, on_detection: Callable[[bool, bool], None] | None = None) -> None:
        camera = cv2.VideoCapture(self.camera_index)
        if not camera.isOpened():
            camera.release()
            if on_detection:
                on_detection(False, False)
            raise RuntimeError(f"Could not open webcam at camera index {self.camera_index}")

        last_sent: tuple[bool, bool] | None = None
        last_publish = 0.0
        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fire-monitor-camera")
        try:
            publisher.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=30)
            publisher.loop_start()
        except (OSError, ValueError) as error:
            print(f"Camera detections will stay local; MQTT unavailable: {error}")
            publisher = None

        print(f"Camera open. YOLO device: {'CUDA' if self.device == 0 else 'CPU'}. Press Q to quit.")
        try:
            while True:
                success, frame = camera.read()
                if not success:
                    if on_detection:
                        on_detection(False, False)
                    break
                detected, annotated = self.detect(frame)
                if on_detection:
                    on_detection(detected, True)
                now = time.monotonic()
                state = (detected, True)
                if publisher and (state != last_sent or now - last_publish >= 2):
                    payload = {
                        "source": "camera",
                        "human_camera": detected,
                        "camera_connected": True,
                        "device": "laptop-camera",
                        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    publisher.publish(MQTT_TOPIC_SENSOR, __import__("json").dumps(payload), qos=1)
                    last_sent, last_publish = state, now
                cv2.imshow("AIoT Human Detection - Q to quit", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()
            if publisher:
                publisher.loop_stop()
                publisher.disconnect()


def main() -> None:
    try:
        HumanDetector().run()
    except (RuntimeError, OSError) as error:
        print(f"Camera detector stopped: {error}")
        raise SystemExit(1) from error
    except Exception as error:
        print(f"YOLO detector could not start: {error}")
        print("Check that requirements are installed and the YOLO model can be downloaded on first run.")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
