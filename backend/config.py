"""Environment-backed project configuration."""
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_SENSOR = os.getenv("MQTT_TOPIC_SENSOR", "fire/emergency/sensor")
MQTT_TOPIC_ALERT = os.getenv("MQTT_TOPIC_ALERT", "fire/emergency/alert")
MQTT_TOPIC_NETWORK = os.getenv("MQTT_TOPIC_NETWORK", "fire/emergency/network")
TEMPERATURE_THRESHOLD = float(os.getenv("TEMPERATURE_THRESHOLD", "50"))
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolo11n.pt")
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
LOG_DIR = PROJECT_ROOT / "data" / "logs"
