"""Thread-safe latest state shared by MQTT callbacks and Flask routes."""
from threading import RLock
from typing import Any

from backend.utils import utc_timestamp


class StateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state: dict[str, Any] = {
            "temperature": 0,
            "humidity": 0,
            "human_radar": False,
            "human_camera": False,
            "camera_connected": False,
            "fire_status": False,
            "fire_level": "NORMAL",
            "buzzer": False,
            "mqtt_connected": False,
            "wifi_connected": False,
            "ip_address": "N/A",
            "network_status": "DISCONNECTED",
            "latency_ms": None,
            "packet_loss": "N/A",
            "timestamp": "",
            "message": "Waiting for sensor data",
        }

    def update(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._state.update(values)
            return dict(self._state)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def update_camera(self, detected: bool, connected: bool) -> None:
        self.update({
            "human_camera": bool(detected),
            "camera_connected": bool(connected),
            "timestamp": utc_timestamp(),
        })
