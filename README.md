<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rounded&height=170&color=0:071009,100:16351D&text=AIoT%20Fire%20Monitor&fontColor=74F08A&fontSize=42&fontAlignY=48&desc=Environmental%20Telemetry%20%7C%20Radar%20Presence%20%7C%202D%20Range%20Map&descAlignY=72&descSize=15" alt="AIoT Fire Monitor project banner">

# AIoT-Based 3D Environmental Mapping & Human Detection for Fire Emergencies

**A Windows-first college project for environmental telemetry, mmWave presence detection, and fire-emergency monitoring.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-REST%20API-black?logo=flask)](https://flask.palletsprojects.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Paho%20%2F%20Mosquitto-660066)](https://mqtt.org/)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?logo=espressif&logoColor=white)](https://www.espressif.com/)
[![YOLO](https://img.shields.io/badge/Detection-YOLO-8A2BE2)](https://docs.ultralytics.com/)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![Arduino](https://img.shields.io/badge/Firmware-Arduino%20IDE-00979D?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![Windows](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows11&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> [!CAUTION]
> **Educational prototype only. This is not a certified fire alarm or life-safety system.** Temperature alone does not establish that a fire exists. Never depend on this project for emergency response or replace certified alarms and safety procedures.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture and Data Flow](#architecture-and-data-flow)
- [Hardware Requirements and Wiring](#hardware-requirements-and-wiring)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Run the Application](#run-the-application)
- [ESP32 Firmware Setup](#esp32-firmware-setup)
- [API Endpoints](#api-endpoints)
- [Fire Decision Logic](#fire-decision-logic)
- [MQTT Topics and Payload](#mqtt-topics-and-payload)
- [2D Environmental Map](#2d-environmental-map)
- [Hardware Demonstration Checklist](#hardware-demonstration-checklist)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Acknowledgements](#acknowledgements)

## Overview

This Windows-first college-project prototype brings together ESP32 sensor telemetry, MQTT messaging, a Python/Flask dashboard, an optional ESP32-CAM OV2640 for JPEG visual monitoring, optional laptop USB webcam person detection with YOLO, and host network measurements. The software can also be demonstrated without hardware by publishing reproducible sensor-simulator scenarios.

The project name refers to environmental mapping, but **the current visualization is 2D**. It is a range-zone display, not 3D mapping, a measured floor plan, or a certified detection system.

```text
DHT11/DHT22 +-------+
                    +--> ESP32 -- Wi-Fi/TCP/MQTT --> Mosquitto --> Python backend
HLK-LD2410C +-------+                                      |          +-- fire rule + JSONL logs
                                                           |          +-- host network monitoring
ESP32-CAM / OV2640 -- HTTP JPEG snapshot or MJPEG stream --> Flask dashboard
USB webcam --> OpenCV --> YOLO --> detection flag ----------+          +-- Flask API + dashboard
Simulator --------------------- MQTT sensor topic ---------------------+

ESP32 buzzer output <-- local temperature decision
```

The ESP32-CAM is a separate board because the main ESP32 DevKit is already assigned to DHT, radar, and buzzer. It serves real JPEG images directly over HTTP and does not publish images to MQTT. The optional laptop YOLO process remains a separate detection feature and publishes metadata only.

## Features

- [x] 🌡️ DHT11/DHT22 temperature and humidity telemetry.
- [x] 📡 LD2410C UART presence parsing, with moving/stationary target range and energy when reported by the library.
- [x] 🔔 ESP32 active-high buzzer control through a suitable transistor/driver.
- [x] 📶 ESP32 Wi-Fi and MQTT reconnect behavior; browser/API remains available when the broker is offline.
- [x] 📨 MQTT simulator with NORMAL, WARNING, and EMERGENCY scenarios.
- [x] 📷 Separate ESP32-CAM OV2640 JPEG snapshot endpoint and optional MJPEG stream (AI-Thinker pin map gated on explicit board confirmation).
- [x] 🧍 Optional laptop USB webcam person detection with OpenCV and Ultralytics YOLO (`yolo11n.pt`).
- [x] 🖥️ Flask REST API and responsive live dashboard with sensor, alert, broker, and network state.
- [x] 🗺️ 2D near/mid/far radar range-zone visualization.
- [x] 📝 Rotating JSONL event history and automated tests.
- [x] 🧪 Software-only demonstration before hardware is connected.

## Hardware Requirements and Wiring

Disconnect power before wiring. Check each breakout board's datasheet for supply voltage, logic levels, and current. Grounds must be common. Do not drive a high-current buzzer directly from an ESP32 GPIO.

| Component / signal | ESP32 connection | Notes |
| --- | --- | --- |
| DHT11/DHT22 VCC | 3.3 V | Confirm the sensor breakout supports 3.3 V. |
| DHT11/DHT22 DATA | GPIO 4 | Add a 10 kΩ pull-up from DATA to 3.3 V if the module does not include one. |
| DHT11/DHT22 GND | GND | Common ground. |
| LD2410C TX | GPIO 16 / UART2 RX | Cross the UART data lines. |
| LD2410C RX | GPIO 17 / UART2 TX | Default UART rate is 256000 baud. |
| LD2410C GND | GND | Common ground. |
| LD2410C VCC | Module-specified supply | The selected `ld2410` library documents a common breakout requiring 5 V or higher with 3.3 V UART I/O. Verify the exact module before connecting power. |
| Active buzzer driver input | GPIO 25 | Firmware logic is active-high. Use a transistor/MOSFET driver suitable for the buzzer. |
| Buzzer/driver ground | Common GND | Power the buzzer through the driver, not directly from an ESP32 GPIO. |
| ESP32 power | 5 V USB to board VIN/USB | Use the board's documented power input. |
| OV2640 camera | Onboard connector of the separate ESP32-CAM | The AI-Thinker sketch uses that board's internal pin map; do not connect the camera bus to GPIO21/22 on the main sensor ESP32. Confirm the exact camera-board model before enabling its pin map. |
| External antenna | Compatible board antenna connector only | Applicable only to the exact ESP32 board with a compatible connector and antenna-selection hardware. Do not modify antenna hardware blindly. |
| Laptop camera | USB webcam on the PC | Used by the optional YOLO process; separate from the ESP32 OV2640. |

## Software Requirements

### PC

- Windows 10/11
- Python 3.12, 64-bit recommended
- Mosquitto MQTT broker, installed separately
- Arduino IDE 2.x and Espressif ESP32 board support for firmware upload
- USB webcam for optional YOLO detection

Python packages are pinned or constrained in [`requirements.txt`](requirements.txt): Flask, Paho MQTT, OpenCV, Ultralytics, NumPy, Pillow, python-dotenv, psutil, requests, and pytest. The first YOLO run may download `yolo11n.pt` and its PyTorch runtime; allow network access and disk space.

### Arduino libraries

- PubSubClient by Nick O'Leary
- DHT sensor library by Adafruit
- Adafruit Unified Sensor
- `ld2410` by ncmreynolds

## Installation

### Automatic Windows setup

From the project root, run:

```powershell
setup.bat
```

If your terminal does not accept that path, run `setup.bat` from File Explorer or PowerShell. The script creates `venv`, installs `requirements.txt`, creates runtime folders, and copies `.env.example` to `.env` if needed. It does not install Mosquitto or administrator-level software.

### Manual setup

```powershell
cd AIoT-Fire-Emergency-System
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, either enable script activation according to your organization's policy or run the venv interpreter directly:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe backend\app.py
```

### Install and start Mosquitto

Install Mosquitto separately from [mosquitto.org](https://mosquitto.org/). Start the broker in its own terminal:

```powershell
mosquitto -v
```

The default local configuration commonly listens on localhost. For an ESP32 on Wi-Fi, configure Mosquitto to accept LAN clients, set the ESP32 broker host to the PC's reachable LAN IPv4 address, and allow TCP 1883 through Windows Firewall as required. Do not set the ESP32 broker host to `localhost`; that refers to the ESP32 itself. Port 1883 is unencrypted and should remain on a trusted local network for this prototype.

## Configuration

### `.env` settings

Copy `.env.example` to `.env`. These are the current configuration keys:

| Variable | Example/default | Purpose |
| --- | --- | --- |
| `WIFI_SSID` | `YOUR_WIFI_NAME` | Reference for the local wireless network; ESP32 credentials are placed in ignored `secrets.h`. |
| `WIFI_PASSWORD` | `YOUR_WIFI_PASSWORD` | Reference only; keep real credentials out of tracked files. |
| `MQTT_BROKER` | `localhost` | Broker host from the PC/backend perspective. Set the PC LAN address in `.env` when that is how the ESP32 reaches Mosquitto. |
| `MQTT_PORT` | `1883` | Broker TCP port. |
| `MQTT_TOPIC_SENSOR` | `fire/emergency/sensor` | Sensor and camera metadata topic. |
| `MQTT_TOPIC_ALERT` | `fire/emergency/alert` | Backend rising-edge emergency alert topic. |
| `MQTT_TOPIC_NETWORK` | `fire/emergency/network` | Optional network telemetry topic. |
| `TEMPERATURE_THRESHOLD` | `50` | Backend emergency threshold in °C. |
| `CAMERA_INDEX` | `0` | Laptop USB webcam index for YOLO. |
| `YOLO_MODEL` | `yolo11n.pt` | Ultralytics model name/path. |
| `CAMERA_BASE_URL` | empty | Base HTTP URL of ESP32-CAM, e.g. `http://192.168.1.50`; Flask derives `/capture` and `/stream`. |
| `CAMERA_REFRESH_SECONDS` | `5` | Automatic snapshot refresh interval, clamped to at least 2 seconds. |
| `FLASK_HOST` | `127.0.0.1` | Flask bind address. |
| `FLASK_PORT` | `5000` | Flask port. |

For consistent alarms, set `FIRE_THRESHOLD_C` in ESP32 `secrets.h` equal to `TEMPERATURE_THRESHOLD` in `.env`.

### Shared ESP32 `secrets.h`

Copy the example header in the firmware folder and edit the local copy:

```powershell
Copy-Item esp32\esp32_fire_monitor\secrets.example.h esp32\esp32_fire_monitor\secrets.h
```

Set `WIFI_SSID` and `WIFI_PASSWORD` for either board. For `DEVICE_ROLE_SENSOR`, also set `MQTT_HOST` to the PC's reachable LAN IPv4 address, `MQTT_PORT`, and `FIRE_THRESHOLD_C` aligned with `.env`. The default role is `DEVICE_ROLE_SENSOR`; select `DEVICE_ROLE_CAMERA` only for the separate camera board. **Only uncomment `CAMERA_MODEL_AI_THINKER` after confirming that the physical camera board is AI-Thinker ESP32-CAM with OV2640.** `secrets.h` is ignored by Git. Do not commit credentials.

## Run the Application

Open separate terminals from the project root. Start the broker before publishers. The normal dashboard starts without simulated readings; use the simulator in its own terminal for software-only mode.

**Terminal 1: Mosquitto**

```powershell
mosquitto -v
```

**Terminal 2: Flask dashboard and backend**

```powershell
venv\Scripts\Activate.ps1
python backend\app.py
```

Open **http://127.0.0.1:5000**. To run the built-in rotating demo instead of live MQTT ingestion, start `python backend\app.py --demo` (do not use demo mode for hardware readings).

**Terminal 3: Sensor simulator (software-only mode)**

```powershell
venv\Scripts\Activate.ps1
python simulator\sensor_simulator.py
```

Other scenarios:

```powershell
python simulator\sensor_simulator.py --mode WARNING --interval 2
python simulator\sensor_simulator.py --mode EMERGENCY --interval 2
```

**Terminal 4: Optional YOLO USB webcam detector**

```powershell
venv\Scripts\Activate.ps1
python ai\human_detector.py
```

The webcam window displays local detection boxes. Press `Q` to exit. Only detection state and camera connectivity metadata are published; frames are not sent.

The ESP32-CAM is a separate microcontroller/HTTP service, not another Python terminal. Flash and power it as described in [ESP32-CAM Setup](#esp32-cam-setup). Put its printed IP in `CAMERA_BASE_URL` in `.env`, restart Flask, then use Capture Image, Refresh Image, or Start Live Stream on the dashboard. Use a DHCP reservation or static lease if the camera IP must stay fixed.

## ESP32 Firmware Setup

1. Install Arduino IDE 2.x and Espressif ESP32 board support through Boards Manager.
2. Install PubSubClient, Adafruit DHT sensor library, Adafruit Unified Sensor, and `ld2410` by ncmreynolds through Library Manager.
3. Copy `esp32\esp32_fire_monitor\secrets.example.h` to `secrets.h` in the same folder and configure Wi-Fi, broker LAN IP, port, and threshold.
4. Open `esp32\esp32_fire_monitor\esp32_fire_monitor.ino`; choose the ESP32 DevKit board and serial port.
5. Upload the sketch. Set `SENSOR_DHT_TYPE` to `DHT22` if using a DHT22.
6. Open Serial Monitor at **115200 baud**. Check the Wi-Fi and LD2410C messages and sensor readings.
7. Confirm JSON appears about every two seconds on `fire/emergency/sensor`.

The LD2410C parser is driven by `radar.read()` on UART2 at 256000 baud. The library's `begin()` performs a bounded sensor handshake. If the radar is missing, check supply, common ground, crossed UART pins, and the module's UART configuration. The firmware's local buzzer rule is temperature-based; presence is reported separately.

## ESP32-CAM Setup

This is a second board but it uses the same single `.ino` source with another compile-time role. The camera role uses `esp_camera.h`, JPEG capture, `GET /capture`, and optional `GET /stream` for the **AI-Thinker ESP32-CAM with OV2640 only**. The model is deliberately compile-gated. Do not select camera role or enable its board macro until you have checked the board name printed on the module/package. If yours is another variant or a raw OV2640 module, identify the exact board/module model before using a pin map.

### AI-Thinker camera board wiring

The OV2640 is normally fitted and connected to the AI-Thinker ESP32-CAM PCB. Do not connect its camera flex/header to the main ESP32 DevKit. For flashing, use a USB-to-TTL adapter:

| USB-to-TTL / control | ESP32-CAM connection | Notes |
| --- | --- | --- |
| Adapter TX | U0R / GPIO3 | UART crossed: adapter TX to board RX. Use 3.3 V UART logic. |
| Adapter RX | U0T / GPIO1 | UART crossed: adapter RX to board TX. |
| GND | GND | Common ground. |
| Stable regulated 5 V supply | 5V pin | Use a supply with sufficient current for Wi-Fi and camera peaks; do not power from the adapter's 3.3 V pin. |
| Boot strap for flashing | GPIO0 to GND | Connect only while uploading; remove GPIO0-GND and reset/power-cycle to run. |
| OV2640 | On-board camera connector | Use the board's latch/connector as designed; no extra SDA/SCL wiring. |

Never feed 5 V into UART GPIO pins. Power down before wiring. GPIO0 must be disconnected from GND for normal operation. The camera IP and main ESP32 sensor device may be on the same Wi-Fi but are independent network devices.

### Flash and configure

1. Confirm the board is specifically an AI-Thinker ESP32-CAM with OV2640. If not, stop and identify the model first.
2. In Arduino IDE 2.x install Espressif ESP32 board support. Select **AI Thinker ESP32-CAM**, enable PSRAM if that menu is available, and choose the USB serial port for the USB-to-TTL adapter.
3. In the same shared `esp32_fire_monitor/secrets.h` used for the sensor role, enter Wi-Fi details, set `DEVICE_ROLE` to `DEVICE_ROLE_CAMERA`, and uncomment `CAMERA_MODEL_AI_THINKER` only after confirming the model.
4. Wire 5 V, GND, crossed U0R/U0T, and GPIO0-GND for upload; press/reset the board if needed, then upload the shared `esp32_fire_monitor.ino`.
5. Remove the GPIO0-GND jumper and reset/power-cycle. Open Serial Monitor at 115200 baud and note the camera's DHCP IP address.
6. Verify the camera directly by opening `http://CAMERA_IP/capture` in a browser; it should return a JPEG. `http://CAMERA_IP/stream` serves optional MJPEG. The synchronous stream holds the camera web-server loop while a viewer is connected; use one viewer at a time and stop the stream before requesting a snapshot.
7. Set `CAMERA_BASE_URL=http://CAMERA_IP` in `.env`, restart Flask, and use the dashboard camera controls. The dashboard shows image load/error state, not a fabricated camera-connected flag.

Camera `/capture` and `/stream` are unauthenticated plain HTTP endpoints for a trusted LAN demonstration only. Do not expose them to the public internet.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/status` | Latest sensor state, radar measurements, assessment, broker state, and sensor freshness. |
| `GET` | `/api/network` | Host network interface/IP, MQTT connectivity, TCP connect latency, and packet-loss status (`N/A` when unmeasured). |
| `GET` | `/api/logs` | Up to 100 most recent JSONL events, latest first. |

`/api/status` also returns `camera_base_url`, `camera_capture_url`, `camera_stream_url`, and `camera_refresh_seconds`, derived from the single `CAMERA_BASE_URL` setting.

## Fire Decision Logic

With threshold `T` configured by `TEMPERATURE_THRESHOLD` in `.env`:

| State | Rule | Prototype behavior |
| --- | --- | --- |
| `NORMAL` | Temperature is below 80% of threshold. | No temperature warning. |
| `WARNING` | Temperature is at least 80% of threshold and below threshold. | Dashboard warning; buzzer remains off. |
| `EMERGENCY` | Temperature is at or above the configured threshold. | Emergency state and buzzer activation. |

The backend warning/emergency thresholds use `TEMPERATURE_THRESHOLD`; align the ESP32 `FIRE_THRESHOLD_C` with it. Human presence is contextual and does not independently establish fire or activate the temperature-based alarm. This demonstration rule is not scientifically validated or certified.

## MQTT Topics and Payload

| Topic | Direction | Purpose |
| --- | --- | --- |
| `fire/emergency/sensor` | ESP32/simulator/camera → backend | Sensor readings and metadata-only camera detections. |
| `fire/emergency/network` | Device → backend | Optional device network information. |
| `fire/emergency/alert` | Backend → subscribers | Rising-edge emergency notification. |

The main ESP32 sends `presence`, while the simulator's legacy field is `human_detected`; the backend accepts both. Laptop YOLO sends camera detection metadata on the sensor topic. ESP32-CAM JPEG images are served directly over HTTP and are **not** sent over MQTT. A representative sensor message is:

```json
{
  "temperature": 32.4,
  "humidity": 64.0,
  "presence": true,
  "radar_connected": true,
  "moving_distance": 245,
  "stationary_distance": 0,
  "moving_energy": 71,
  "stationary_energy": 0,
  "alarm": false,
  "status": "NORMAL",
  "device": "ESP32",
  "uptime_ms": 123456
}
```

The firmware uptime is not a wall-clock timestamp. The backend assigns receive time for dashboard freshness and event logs. The simulator and camera publisher include their own ISO timestamps.

To inspect traffic locally:

```powershell
mosquitto_sub -h localhost -p 1883 -t "fire/emergency/#" -v
```

## 2D Environmental Map

The dashboard maps the LD2410C's measured range to illustrative **near**, **mid**, and **far** bands. The current display uses near below 150 cm, mid from 150 to 399 cm, and far at 400 cm or farther. These are visualization bands, not calibrated room zones.

The LD2410C reports distance but not target bearing. The dashboard therefore draws a circular range ring around the fixed radar point; it does not place a person at an invented X/Y coordinate. The ring display scale tops out at 600 cm; farther reported ranges are labeled with their measurement while the visible radius is clamped. It is a 2D view only: there is no 3D reconstruction, depth sensing, or LiDAR.

## Hardware Demonstration Checklist

1. Verify wiring with power disconnected; confirm DHT DATA on GPIO 4, radar TX/RX on GPIO 16/17, and buzzer driver input on GPIO 25.
2. Confirm module supply requirements from the actual DHT, LD2410C, buzzer driver, and ESP32 board documentation.
3. Confirm the buzzer uses a suitable transistor/MOSFET driver and common ground; do not load an ESP32 GPIO directly with a high-current buzzer.
4. Copy/configure ignored `secrets.h`; use the PC's reachable LAN address for `MQTT_HOST`, never `localhost` on the ESP32.
5. Start Mosquitto and confirm it accepts the intended local/LAN clients.
6. Upload the firmware and open Serial Monitor at 115200 baud.
7. Confirm the ESP32 boots and associates with Wi-Fi.
8. Confirm the LD2410C handshake reports connected; verify UART2 is 256000 baud and TX/RX are crossed.
9. Check DHT11/DHT22 temperature and humidity are plausible and refresh regularly.
10. Move into and out of the radar field of view; verify `presence` changes from the physical sensor.
11. Check moving/stationary distance and energy when those targets are reported by the radar.
12. Verify the local buzzer threshold with a safe, controlled test method; never use an actual fire.
13. Subscribe to `fire/emergency/sensor` and confirm ESP32 JSON arrives about every two seconds.
14. Start the normal Flask app and confirm `/api/status` shows fresh ESP32 telemetry.
15. Open the dashboard and verify status, connectivity, map range band, and event history update.
16. Interrupt Wi-Fi or restart Mosquitto, then confirm reconnect and that stale device status clears before returning online.

For the separate camera board, additionally verify `/capture` returns a JPEG, dashboard Capture/Refresh updates the picture, the optional stream connects, and the snapshot control works again after stopping the stream. Test with a harmless scene; no fire is required.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `mosquitto` command not found | Mosquitto is not installed or not on PATH. | Install it separately and reopen PowerShell; check its install folder/PATH. |
| MQTT remains disconnected | Broker stopped, wrong host/port, or backend `.env` mismatch. | Start `mosquitto -v`; verify `MQTT_BROKER` and `MQTT_PORT`, then test TCP port 1883. |
| ESP32 cannot connect to MQTT | ESP32 configured with `localhost`, broker only listens on loopback, firewall blocks access, or Wi-Fi client isolation. | Put the PC LAN IPv4 in `secrets.h`; configure broker LAN listening/firewall and check router isolation. |
| Dashboard shows no sensor data | No publisher is sending to the configured topic. | Check broker, serial output, topic subscription, and `MQTT_TOPIC_SENSOR`; run the simulator to isolate hardware. |
| DHT read fails | Wrong data pin/type, missing pull-up, power/ground issue. | Check GPIO 4, DHT11 vs DHT22 setting, wiring, supply, and DATA pull-up. |
| LD2410C stays disconnected or reports no presence | Supply/logic mismatch, UART crossed incorrectly, baud/configuration mismatch, or target outside detection area. | Verify exact module voltage, common ground, TX→GPIO16, RX→GPIO17, 256000 baud, compatible library, and sensor configuration. |
| Buzzer does not sound | Wrong polarity/active level, threshold mismatch, or driver wiring issue. | Check active-high GPIO 25 driver, its supply/common ground, and `FIRE_THRESHOLD_C` alignment with `.env`. |
| Webcam/YOLO does not start | Camera busy/permission denied, wrong index, or first-run model/download issue. | Close other webcam apps, check OS permissions and `CAMERA_INDEX`, confirm network/disk access, and retry on CPU. |
| ESP32-CAM image does not load | Camera IP missing/wrong, camera not on same LAN, wrong board pin map, or camera server failed. | Read its IP from Serial Monitor; check `http://CAMERA_IP/capture` directly, `CAMERA_BASE_URL`, board identity, power, and Wi-Fi. |
| ESP32-CAM uploads but does not boot | GPIO0 is still tied to GND, weak 5 V supply, or wrong board selected. | Remove GPIO0-GND after flashing, reset, use a stable 5 V supply, and verify the exact board selection. |
| MJPEG stream prevents snapshots | The simple synchronous WebServer stream handles one camera client at a time. | Stop the stream in the dashboard before requesting a snapshot; power-cycle the camera if the browser disconnect did not release it. |

For Windows network checks, see [`network/network_testing.md`](network/network_testing.md).

## Limitations

- Educational prototype only; no certification, calibrated fire detection, or emergency-response guarantee.
- Temperature-only thresholds are simple demonstration rules and do not prove fire.
- The current visual map is 2D and range-zone-based; it has no 3D/depth/LiDAR sensing or radar bearing.
- ESP32-CAM firmware is currently AI-Thinker-specific and compile-gated; other camera variants need their confirmed pin mapping. Its basic synchronous MJPEG handler serves one viewer at a time.
- Camera endpoints are unauthenticated HTTP on the trusted local network; they are not hardened for internet exposure.
- The optional YOLO detector uses a laptop USB webcam and publishes metadata rather than video.
- MQTT port 1883 is unencrypted in the documented local setup; authentication/TLS and deployment hardening are not implemented.
- Sensor history is bounded rotating JSONL, not a database. Network latency is TCP connect time, not MQTT round-trip time; packet loss is not measured.
- Hardware/library compatibility and sensor behavior must be validated on the exact ESP32 board and sensor modules.

## Testing

Run the test suite from the project root with the project environment activated:

```powershell
venv\Scripts\Activate.ps1
python -m pytest
```

Tests cover fire-rule boundaries, MQTT offline and payload behavior, API sensor freshness, and network status/latency failure cases. Unit tests do not require a live broker, webcam, or physical ESP32. Use the simulator for an end-to-end software demonstration.

## Project Structure

```text
AIoT-Fire-Emergency-System/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── fire_detection.py
│   ├── human_detection.py
│   ├── mqtt_client.py
│   ├── network_monitor.py
│   ├── state_store.py
│   └── utils.py
├── dashboard/
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/dashboard.js
│   └── templates/index.html
├── ai/
│   ├── human_detector.py
│   └── models/
├── esp32/
│   ├── esp32_fire_monitor/
│   │   ├── esp32_fire_monitor.ino
│   │   └── secrets.example.h
│   └── README.md
├── simulator/sensor_simulator.py
├── network/
│   ├── mqtt_topics.md
│   └── network_testing.md
├── data/logs/
├── tests/
│   ├── test_api.py
│   ├── test_fire_detection.py
│   ├── test_mqtt.py
│   └── test_network.py
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.bat
├── LICENSE
└── README.md
```

## Contributing

Contributions are welcome, especially reproducible fixes, hardware compatibility notes, and tests.

1. Fork the repository and create a focused feature branch.
2. Keep changes aligned with the existing Flask, MQTT, and dashboard structure; avoid committing `.env`, `secrets.h`, model weights, or runtime logs.
3. Run `python -m pytest` and validate any touched frontend code.
4. Describe hardware-dependent assumptions and test results clearly in your pull request.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for the full text.

## Author

**Bhushan Wanere**

[![GitHub](https://img.shields.io/badge/GitHub-bhushan--codes01-181717?logo=github)](https://github.com/bhushan-codes01)

## Acknowledgements

- Espressif and Arduino communities for ESP32 tooling and documentation.
- Adafruit for the DHT sensor library and sensor integration resources.
- Nick O'Leary for PubSubClient and ncmreynolds for the LD2410 Arduino library.
- Eclipse Mosquitto and the Paho project for MQTT broker/client implementations.
- Ultralytics and OpenCV for the optional local webcam detection pipeline.
- Flask and the Python open-source community for the backend and testing ecosystem.