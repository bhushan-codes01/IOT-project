"""Publish reproducible NORMAL, WARNING, or EMERGENCY sensor data over MQTT."""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import paho.mqtt.client as mqtt

from backend.config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_SENSOR


SCENARIOS = {
    "NORMAL": (20.0, 32.0),
    "WARNING": (40.0, 48.0),
    "EMERGENCY": (51.0, 76.0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=SCENARIOS, default="NORMAL", type=str.upper)
    parser.add_argument("--interval", type=float, default=2.0, help="Publish interval in seconds")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fire-monitor-simulator")
    connected = False

    def on_connect(client: mqtt.Client, userdata: object, flags: object, reason_code: object, properties: object) -> None:
        nonlocal connected
        connected = int(reason_code) == 0
        if connected:
            print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        else:
            print(f"MQTT connection rejected: {reason_code}")

    def on_disconnect(client: mqtt.Client, userdata: object, disconnect_flags: object, reason_code: object, properties: object) -> None:
        nonlocal connected
        connected = False
        print(f"MQTT disconnected: {reason_code}; reconnecting automatically")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    try:
        client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=30)
        client.loop_start()
        low, high = SCENARIOS[args.mode]
        print(f"Publishing {args.mode} readings to {MQTT_TOPIC_SENSOR} every {args.interval:g}s. Ctrl+C to stop.")
        while True:
            payload = {
                "temperature": round(random.uniform(low, high), 1),
                "humidity": random.randint(35, 72),
                "human_detected": random.choice((True, False)),
                "device": "SIMULATOR",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if connected:
                info = client.publish(MQTT_TOPIC_SENSOR, json.dumps(payload), qos=1)
                if info.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"{payload['timestamp']} {payload['temperature']}°C {payload['humidity']}% RH presence={payload['human_detected']}")
                else:
                    print("Publish failed; waiting for MQTT reconnection")
            else:
                print(f"MQTT broker not running at {MQTT_BROKER}:{MQTT_PORT}; retrying")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Simulator stopped")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
