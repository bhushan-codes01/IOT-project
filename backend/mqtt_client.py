"""MQTT transport. A missing broker leaves the web app running offline."""
import json
import logging
import math
import time
from typing import Any, Callable

import paho.mqtt.client as mqtt

from backend.config import (
    LOG_DIR,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC_ALERT,
    MQTT_TOPIC_NETWORK,
    MQTT_TOPIC_SENSOR,
    TEMPERATURE_THRESHOLD,
)
from backend.fire_detection import assess_fire_risk
from backend.utils import log_event, utc_timestamp

LOGGER = logging.getLogger(__name__)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def _optional_nonnegative_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a non-negative number") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a non-negative finite number")
    return int(number)


class MQTTService:
    def __init__(self, state_store: Any) -> None:
        self.state_store = state_store
        self.connected = False
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fire-monitor-backend")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        try:
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=30)
            self.client.loop_start()
        except (OSError, ValueError) as error:
            LOGGER.warning("MQTT broker unavailable at %s:%s: %s", MQTT_BROKER, MQTT_PORT, error)
            self.state_store.update({"mqtt_connected": False})

    def stop(self) -> None:
        self.client.loop_stop()
        try:
            self.client.disconnect()
        except (OSError, ValueError):
            pass

    def publish(self, topic: str, payload: dict[str, Any]) -> bool:
        if not self.connected:
            return False
        try:
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except (OSError, ValueError, TypeError):
            LOGGER.exception("Could not publish MQTT message to %s", topic)
            return False

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        self.connected = int(reason_code) == 0
        self.state_store.update({"mqtt_connected": self.connected})
        if self.connected:
            client.subscribe([(MQTT_TOPIC_SENSOR, 1), (MQTT_TOPIC_NETWORK, 1)])
            LOGGER.info("Connected to MQTT broker %s:%s", MQTT_BROKER, MQTT_PORT)
        else:
            LOGGER.warning("MQTT connection rejected: %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any) -> None:
        self.connected = False
        self.state_store.update({"mqtt_connected": False})
        LOGGER.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("MQTT payload must be a JSON object")
            if message.topic == MQTT_TOPIC_SENSOR:
                self._apply_sensor(payload)
            elif message.topic == MQTT_TOPIC_NETWORK:
                self.state_store.update({"device_network": payload, "timestamp": payload.get("timestamp", utc_timestamp())})
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            LOGGER.warning("Ignoring invalid MQTT message on %s: %s", message.topic, error)

    def _apply_sensor(self, payload: dict[str, Any]) -> None:
        if payload.get("source") == "camera" or "human_camera" in payload:
            self.state_store.update_camera(
                bool(payload.get("human_camera", payload.get("human_detected", False))),
                bool(payload.get("camera_connected", True)),
            )
            return

        temperature = float(payload.get("temperature", 0))
        humidity = float(payload.get("humidity", 0))
        if not math.isfinite(temperature) or not math.isfinite(humidity):
            raise ValueError("temperature and humidity must be finite numbers")
        human_detected = _as_bool(payload.get(
            "presence", payload.get("human_detected", payload.get("human_radar", False))
        ))
        moving_distance = _optional_nonnegative_int(payload.get("moving_distance"), "moving_distance")
        stationary_distance = _optional_nonnegative_int(payload.get("stationary_distance"), "stationary_distance")
        moving_energy = _optional_nonnegative_int(payload.get("moving_energy"), "moving_energy")
        stationary_energy = _optional_nonnegative_int(payload.get("stationary_energy"), "stationary_energy")
        human_distance = next(
            (distance for distance in (moving_distance, stationary_distance) if distance),
            None,
        )
        assessment = assess_fire_risk(temperature, TEMPERATURE_THRESHOLD)
        timestamp = utc_timestamp()
        device = str(payload.get("device") or "UNKNOWN")
        previous = self.state_store.snapshot()
        values = {
            "temperature": temperature,
            "humidity": humidity,
            "human_radar": human_detected,
            "radar_connected": _as_bool(payload["radar_connected"]) if "radar_connected" in payload else None,
            "human_distance_cm": human_distance,
            "moving_distance_cm": moving_distance,
            "stationary_distance_cm": stationary_distance,
            "moving_energy": moving_energy,
            "stationary_energy": stationary_energy,
            "fire_status": assessment.fire_status,
            "fire_level": assessment.level.value,
            "buzzer": assessment.fire_status,
            "mqtt_connected": self.connected,
            "timestamp": timestamp,
            "sensor_received_at": time.time(),
            "sensor_device": device,
            "message": assessment.message,
        }
        self.state_store.update(values)
        log_event(LOG_DIR, {**values, "event": "sensor_update"})

        if assessment.fire_status and not previous["fire_status"]:
            alert = {
                "fire": True,
                "temperature": temperature,
                "human_detected": human_detected,
                "message": "Prototype temperature rule reached its configured threshold",
                "timestamp": timestamp,
            }
            self.publish(MQTT_TOPIC_ALERT, alert)
