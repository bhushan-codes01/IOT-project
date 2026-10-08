<div align="center">

# AIoT Fire Monitor

**AIoT-Based Environmental Mapping and Human Detection for Fire Emergencies**

</div>

## Overview

This project monitors environmental conditions using an ESP32, DHT11, HLK-LD2410C mmWave radar, and a Windows PC-hosted USB webcam. The ESP32 publishes sensor telemetry over MQTT to a Mosquitto broker running on the same LAN as the PC. The Python backend aggregates sensor data, exposes a Flask dashboard, and integrates human detection from the local USB webcam using OpenCV + Ultralytics YOLO.

The actual hardware used by this project is limited to:

- ESP32 development board
- DHT11 temperature and humidity sensor
- HLK-LD2410C 24GHz mmWave radar sensor
- Active buzzer
- Breadboard and jumper wires
- USB webcam connected to the Windows PC

This project does not use any external camera board or dedicated camera module on the ESP32.

## Architecture

```text
DHT11
  |
LD2410C
  |
Buzzer
  |
  v
ESP32 -> Wi-Fi -> Mosquitto MQTT broker on Windows PC -> Flask backend -> Dashboard + 2D map

USB webcam -> OpenCV -> YOLO person detection -> Flask dashboard
```

The sensor pipeline and the webcam pipeline are separate inputs that are merged in the Flask backend dashboard.

## Hardware wiring

### DHT11
- VCC -> ESP32 3.3V
- DATA -> ESP32 GPIO 4
- GND -> ESP32 GND
- If there is no onboard pull-up, add 10k from DATA to 3.3V

### LD2410C
- TX -> ESP32 GPIO 16 (UART2 RX)
- RX -> ESP32 GPIO 17 (UART2 TX)
- GND -> ESP32 GND
- VCC -> use the module's exact supply rating and verify before wiring
- UART baud rate: 256000
- Hardware serial: `HardwareSerial(2)`

### Active buzzer
- + -> ESP32 GPIO 25
- - -> GND
- If the buzzer requires more current than the GPIO can safely provide, use a transistor or MOSFET driver.

### PC webcam
- USB webcam -> Windows PC USB port
- Not connected to the ESP32

## MQTT configuration

Use Mosquitto on the Windows PC and configure the ESP32 to connect to the PC LAN IP, not `localhost` or `127.0.0.1`.

Topics:
- `fire/emergency/sensor`
- `fire/emergency/alert`
- `fire/emergency/network`

Default MQTT values:
- Host: `localhost` for PC-side tools
- Port: `1883`
- ESP32 host: set to the LAN IP of the PC running Mosquitto

## ESP32 secrets

Use the checked-in example file and copy it into a local `esp32/secrets.h` file before compiling:

```cpp
#ifndef SECRETS_H
#define SECRETS_H

#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define FIRE_THRESHOLD_C 50.0f

#endif
```

Do not commit real Wi-Fi or MQTT configuration values.

## Mosquitto on Windows

Install Mosquitto and run:

```powershell
mosquitto -v
```

Broker default:
- `localhost:1883`

Test commands:

```powershell
mosquitto_sub -h localhost -p 1883 -t "fire/emergency/sensor"
mosquitto_pub -h localhost -p 1883 -t "fire/emergency/sensor" -m "{\"temperature\":52.0,\"humidity\":40.0,\"presence\":true,\"alarm\":true,\"status\":\"EMERGENCY\"}"
```

If the ESP32 cannot reach the broker, ensure the PC firewall allows inbound TCP port 1883 and both devices are on the same local network.

## Python backend

The backend subscribes to MQTT, stores the latest sensor state, and serves the dashboard. It also exposes the local USB webcam stream via Flask and runs YOLO person detection on the PC.

Core endpoints:
- `GET /`
- `GET /api/sensor`
- `GET /api/status`
- `GET /api/camera`
- `GET /video_feed`

## Webcam and YOLO

Use a local USB webcam connected to the PC and capture it with OpenCV.

Configuration values:
- `CAMERA_INDEX=0`
- `YOLO_MODEL=yolo11n.pt`

The main requirement is HUMAN detection only, using the person class from YOLO. The webcam remains local to the Windows PC and is not sent over MQTT.

## Dependencies

The Python environment uses the packages in `requirements.txt`, including:

- Flask
- paho-mqtt
- opencv-python
- ultralytics
- numpy
- Pillow
- python-dotenv
- psutil
- requests
- pytest

The first YOLO run may download `yolo11n.pt` and its runtime weights.

## Project layout

```text
backend/
  app.py
  config.py
  mqtt_client.py
  state_store.py
  fire_detection.py
  network_monitor.py
  camera_manager.py

dashboard/
  templates/index.html
  static/js/dashboard.js
  static/css/style.css

esp32/
  esp32_fire_monitor/esp32_fire_monitor.ino
  secrets.h

ai/
  human_detector.py
```

## Notes

- This is an educational prototype and not a certified safety system.
- The LD2410C reports range information, not exact X-Y coordinates, so the dashboard uses a 2D range-zone map instead of inventing target positions.
- Do not add any separate camera module or external camera code paths to this project.
