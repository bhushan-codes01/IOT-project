"""Flask dashboard API and application entry point."""
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
from backend.config import FLASK_HOST, FLASK_PORT, LOG_DIR, MQTT_BROKER, MQTT_PORT
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
        return jsonify({
            "temperature": values["temperature"],
            "humidity": values["humidity"],
            "human_radar": values["human_radar"],
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
            "message": values["message"],
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


def main() -> None:
    state = StateStore()
    mqtt_service = MQTTService(state)
    mqtt_service.start()
    _start_network_updates(state, mqtt_service)
    print(f"Dashboard: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"MQTT broker: {MQTT_BROKER}:{MQTT_PORT} (install/start Mosquitto separately)")
    create_app(state).run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
