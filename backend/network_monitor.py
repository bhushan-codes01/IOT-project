"""Network-interface status and measured TCP connection latency."""
import socket
import time
from typing import Any

import psutil

from backend.config import MQTT_BROKER, MQTT_PORT


def _active_interface() -> tuple[str, str]:
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for name, interface_stats in stats.items():
        if not interface_stats.isup or name.lower() in {"loopback pseudo-interface 1", "lo"}:
            continue
        entries = addresses.get(name, [])
        ipv4 = next((entry.address for entry in entries if entry.family == socket.AF_INET), None)
        if ipv4 and not ipv4.startswith("127."):
            return name, ipv4
    return "", "N/A"


def snapshot(mqtt_connected: bool | None = None, timeout: float = 0.7) -> dict[str, Any]:
    interface, ip_address = _active_interface()
    wifi_connected = bool(interface and any(
        token in interface.lower() for token in ("wi-fi", "wifi", "wlan", "wireless")
    ))
    if not interface:
        wifi_connected = False

    latency_ms = None
    if interface:
        try:
            started = time.perf_counter()
            with socket.create_connection((MQTT_BROKER, MQTT_PORT), timeout=timeout):
                latency_ms = round((time.perf_counter() - started) * 1000, 1)
        except (OSError, socket.gaierror):
            pass

    return {
        "ip_address": ip_address,
        "wifi_connected": wifi_connected,
        "mqtt_connected": bool(mqtt_connected),
        "latency_ms": latency_ms,
        "packet_loss": "N/A",
        "network_status": "CONNECTED" if interface else "DISCONNECTED",
        "connection_status": "CONNECTED" if interface else "DISCONNECTED",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
