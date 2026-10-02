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


def test_status_exposes_configured_camera_endpoints(monkeypatch):
    from backend import app as backend_app

    monkeypatch.setattr(backend_app, "CAMERA_BASE_URL", "http://192.168.1.50")
    monkeypatch.setattr(backend_app, "CAMERA_REFRESH_SECONDS", 5)

    result = backend_app.create_app(StateStore()).test_client().get("/api/status").get_json()

    assert result["camera_base_url"] == "http://192.168.1.50"
    assert result["camera_capture_url"] == "http://192.168.1.50/capture"
    assert result["camera_stream_url"] == "http://192.168.1.50/stream"
    assert result["camera_refresh_seconds"] == 5


def test_dashboard_renders_camera_controls_and_distance_map():
    response = create_app(StateStore()).test_client().get("/")

    assert response.status_code == 200
    assert b"camera-image" in response.data
    assert b"Capture Image" in response.data
    assert b"Refresh Image" in response.data
    assert b"Start Live Stream" in response.data
    assert b"radar-map" in response.data
