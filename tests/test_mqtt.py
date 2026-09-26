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
