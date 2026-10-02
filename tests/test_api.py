import time

from backend.app import create_app
from backend.state_store import StateStore


def test_status_exposes_live_esp32_and_radar_measurements():
    state = StateStore()
    state.update({
        "temperature": 42.0,
        "humidity": 55,
        "human_radar": True,
        "radar_connected": True,
        "human_distance_cm": 245,
        "moving_distance_cm": 245,
        "moving_energy": 71,
        "sensor_received_at": time.time(),
        "sensor_device": "ESP32",
        "timestamp": "2026-10-02T12:00:00+00:00",
    })

    response = create_app(state).test_client().get("/api/status")
    result = response.get_json()

    assert response.status_code == 200
    assert result["sensor_connected"] is True
    assert result["esp32_connected"] is True
    assert result["radar_connected"] is True
    assert result["human_distance_cm"] == 245
    assert result["moving_energy"] == 71
    assert result["last_seen"] == "2026-10-02T12:00:00+00:00"


def test_status_marks_old_sensor_data_disconnected():
    state = StateStore()
    state.update({"sensor_received_at": time.time() - 11, "sensor_device": "ESP32"})

    result = create_app(state).test_client().get("/api/status").get_json()

    assert result["sensor_connected"] is False
    assert result["esp32_connected"] is False
