"""Payload contract shared by local vision and backend MQTT ingestion."""
from datetime import datetime, timezone
from typing import Any


def camera_state_payload(detected: bool, connected: bool = True) -> dict[str, Any]:
    """Return a metadata-only MQTT message; camera frames are never transmitted."""
    return {
        "source": "camera",
        "human_camera": bool(detected),
        "camera_connected": bool(connected),
        "device": "laptop-camera",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
