from backend import network_monitor


def test_latency_is_unavailable_when_broker_tcp_connection_fails(monkeypatch):
    monkeypatch.setattr(network_monitor, "_active_interface", lambda: ("Wi-Fi", "192.168.1.20"))

    def fail_connection(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(network_monitor.socket, "create_connection", fail_connection)
    result = network_monitor.snapshot(mqtt_connected=False)
    assert result["ip_address"] == "192.168.1.20"
    assert result["wifi_connected"] is True
    assert result["latency_ms"] is None
    assert result["packet_loss"] == "N/A"


def test_no_active_network_is_reported_disconnected(monkeypatch):
    monkeypatch.setattr(network_monitor, "_active_interface", lambda: ("", "N/A"))
    monkeypatch.setattr(network_monitor.socket, "create_connection", lambda *args, **kwargs: None)
    result = network_monitor.snapshot(mqtt_connected=False)
    assert result["network_status"] == "DISCONNECTED"
    assert result["wifi_connected"] is False
