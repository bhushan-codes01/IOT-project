"""Flask dashboard API and application entry point."""
import argparse
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, render_template

from backend import network_monitor
from backend.config import FLASK_HOST, FLASK_PORT, LOG_DIR, MQTT_BROKER, MQTT_PORT, TEMPERATURE_THRESHOLD
from backend.fire_detection import assess_fire_risk
from backend.mqtt_client import MQTTService
from backend.state_store import StateStore
from backend.utils import utc_timestamp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(state_store: StateStore | None = None) -> Flask:
    state = state_store or StateStore()
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "dashboard" / "templates"),
        static_folder=str(PROJECT_ROOT / "dashboard" / "static"),
        static_url_path="/static",
    )
    app.extensions["state_store"] = state

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/status")
    def status() -> Any:
        values = state.snapshot()
        received_at = float(values.get("sensor_received_at") or 0)
        sensor_connected = received_at > 0 and time.time() - received_at <= 10
        esp32_connected = sensor_connected and values.get("sensor_device") == "ESP32"
        return jsonify({
            "temperature": values["temperature"],
            "humidity": values["humidity"],
            "human_radar": values["human_radar"],
            "radar_connected": values["radar_connected"],
            "human_distance_cm": values["human_distance_cm"],
            "moving_distance_cm": values["moving_distance_cm"],
            "stationary_distance_cm": values["stationary_distance_cm"],
            "moving_energy": values["moving_energy"],
            "stationary_energy": values["stationary_energy"],
            "human_camera": values["human_camera"],
            "camera_connected": values["camera_connected"],
            "fire_status": values["fire_status"],
            "fire_level": values["fire_level"],
            "buzzer": values["buzzer"],
            "mqtt_connected": values["mqtt_connected"],
            "wifi_connected": values["wifi_connected"],
            "ip_address": values["ip_address"],
            "network_status": values["network_status"],
            "latency_ms": values["latency_ms"],
            "packet_loss": values["packet_loss"],
            "timestamp": values["timestamp"],
            "last_seen": values["timestamp"],
            "sensor_connected": sensor_connected,
            "esp32_connected": esp32_connected,
            "sensor_device": values["sensor_device"],
            "message": values["message"],
            "demo_mode": values.get("demo_mode", False),
        })

    @app.get("/api/network")
    def network() -> Any:
        values = state.snapshot()
        result = network_monitor.snapshot(values["mqtt_connected"])
        return jsonify(result)

    @app.get("/api/logs")
    def logs() -> Any:
        log_file = LOG_DIR / "events.jsonl"
        if not log_file.exists():
            return jsonify([])
        try:
            lines = log_file.read_text(encoding="utf-8").splitlines()[-100:]
            return jsonify([json.loads(line) for line in reversed(lines)])
        except (OSError, json.JSONDecodeError):
            app.logger.exception("Could not read event log")
            return jsonify([]), 500

    return app


def _start_network_updates(state: StateStore, mqtt_service: MQTTService) -> None:
    def update_loop() -> None:
        while True:
            values = network_monitor.snapshot(mqtt_service.connected)
            state.update({**values, "timestamp": state.snapshot()["timestamp"] or utc_timestamp()})
            time.sleep(5)

    threading.Thread(target=update_loop, name="network-monitor", daemon=True).start()


def _start_demo_updates(state: StateStore) -> None:
    def update_loop() -> None:
        scenarios = (
            (TEMPERATURE_THRESHOLD * 1.08, 68),
            (TEMPERATURE_THRESHOLD * 0.9, 56),
            (TEMPERATURE_THRESHOLD * 0.5, 42),
        )
        index = 0
        while True:
            temperature, humidity = scenarios[index % len(scenarios)]
            assessment = assess_fire_risk(temperature, TEMPERATURE_THRESHOLD)
            state.update({
                "temperature": round(temperature, 1),
                "humidity": humidity,
                "human_radar": True,
                "human_camera": True,
                "camera_connected": True,
                "fire_status": assessment.fire_status,
                "fire_level": assessment.level.value,
                "buzzer": assessment.fire_status,
                "mqtt_connected": False,
                "timestamp": utc_timestamp(),
                "sensor_received_at": time.time(),
                "sensor_device": "DEMO",
                "message": "SIMULATED DEMO DATA - not connected to sensors",
                "demo_mode": True,
            })
            index += 1
            time.sleep(8)

    threading.Thread(target=update_loop, name="sensor-demo", daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AIoT fire-monitor dashboard.")
    parser.add_argument("--demo", action="store_true", help="cycle simulated sensor readings without MQTT hardware")
    args = parser.parse_args()

    state = StateStore()
    mqtt_service = MQTTService(state)
    if args.demo:
        _start_demo_updates(state)
        print("Demo mode: simulated radar, camera, temperature, and humidity readings")
    else:
        mqtt_service.start()
        print(f"MQTT broker: {MQTT_BROKER}:{MQTT_PORT} (install/start Mosquitto separately)")
    _start_network_updates(state, mqtt_service)
    print(f"Dashboard: http://{FLASK_HOST}:{FLASK_PORT}")
    create_app(state).run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
