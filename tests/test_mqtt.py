from backend.mqtt_client import MQTTService
from backend.state_store import StateStore


def test_mqtt_service_starts_disconnected_without_broker(monkeypatch):
    state = StateStore()
    service = MQTTService(state)

    def fail_connection(*args, **kwargs):
        raise OSError("broker unavailable")

    monkeypatch.setattr(service.client, "connect_async", fail_connection)
    service.start()
    assert service.connected is False
    assert state.snapshot()["mqtt_connected"] is False


def test_publish_returns_false_when_not_connected():
    service = MQTTService(StateStore())
    assert service.publish("fire/emergency/alert", {"fire": True}) is False


def test_sensor_payload_accepts_presence_and_radar_range(monkeypatch):
    from backend import mqtt_client

    monkeypatch.setattr(mqtt_client, "log_event", lambda *args, **kwargs: None)
    state = StateStore()
    service = MQTTService(state)

    service._apply_sensor({
        "temperature": 42.0,
        "humidity": 55,
        "presence": True,
        "radar_connected": True,
        "moving_distance": 245,
        "stationary_distance": 0,
        "moving_energy": 71,
        "device": "ESP32",
    })

    values = state.snapshot()
    assert values["human_radar"] is True
    assert values["radar_connected"] is True
    assert values["human_distance_cm"] == 245
    assert values["moving_distance_cm"] == 245
    assert values["moving_energy"] == 71
    assert values["sensor_device"] == "ESP32"
    assert values["fire_level"] == "WARNING"


def test_string_false_presence_is_not_treated_as_detected(monkeypatch):
    from backend import mqtt_client

    monkeypatch.setattr(mqtt_client, "log_event", lambda *args, **kwargs: None)
    state = StateStore()
    MQTTService(state)._apply_sensor({"temperature": 25, "humidity": 50, "presence": "false"})

    assert state.snapshot()["human_radar"] is False


def test_zero_radar_distance_is_reported_as_unavailable(monkeypatch):
    from backend import mqtt_client

    monkeypatch.setattr(mqtt_client, "log_event", lambda *args, **kwargs: None)
    state = StateStore()
    MQTTService(state)._apply_sensor({
        "temperature": 25,
        "humidity": 50,
        "presence": True,
        "moving_distance": 0,
        "stationary_distance": 0,
    })

    assert state.snapshot()["human_distance_cm"] is None
