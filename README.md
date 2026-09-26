# AIoT-Based Environmental Monitoring and Human Detection for Fire Emergencies

A Windows-first college-project prototype combining ESP32 environmental telemetry, MQTT, a Python/Flask dashboard, laptop webcam person detection with YOLO, and host network measurements. It works in software-only mode with a sensor simulator before any hardware is connected. It does not use Raspberry Pi or an LLM.

> **Safety:** This is an educational prototype, not a certified fire alarm or life-safety system. Temperature alone does not prove a fire. Do not rely on this software for emergency response or replace certified alarms.

## Features

- Flask dashboard with REST endpoints for state, network health, and recent JSONL events.
- MQTT sensor ingest and alert publishing; the web app stays available when Mosquitto is down.
- Repeatable NORMAL, WARNING, and EMERGENCY simulator scenarios.
- YOLO person detection from a local USB webcam, with automatic CPU fallback and metadata-only MQTT publishing.
- Network interface/IP status and measured TCP connection time to the MQTT broker. Packet loss is honestly reported as `N/A`.
- ESP32 firmware for DHT11/DHT22, buzzer, Wi-Fi, and MQTT; LD2410C UART integration point is explicit and not represented as a completed parser.

## Architecture and data flow

```text
DHT11/DHT22 ─┐
             ├─> ESP32 ── Wi-Fi/TCP/MQTT ──> Mosquitto ──> Python backend
HLK-LD2410C ─┘                                      │          ├─ fire rule + logs
                                                    │          ├─ network monitoring
USB camera ──> OpenCV ──> YOLO ── detection flag ──┘          └─ Flask dashboard
Simulator ─────────────────── MQTT sensor topic ────────────────┘
```

Only detection metadata is sent by the camera process; no image or video stream is exposed. The backend subscribes to `fire/emergency/sensor` and `fire/emergency/network`, then publishes a rising-edge emergency message to `fire/emergency/alert`.

## Project structure

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
│   ├── templates/index.html
│   └── static/{css/style.css,js/dashboard.js}
├── ai/
│   ├── human_detector.py
│   └── models/
├── esp32/
│   ├── esp32_fire_monitor/esp32_fire_monitor.ino
│   ├── esp32_fire_monitor/secrets.example.h
│   └── README.md
├── simulator/sensor_simulator.py
├── network/{mqtt_topics.md,network_testing.md}
├── data/logs/
├── tests/{test_mqtt.py,test_fire_detection.py,test_network.py}
├── requirements.txt
├── .env.example
├── .gitignore
├── setup.bat
└── README.md
```

## Requirements

- Windows 10/11 and Python 3.12 (recommended; Python 3.10+ may work with compatible wheels).
- Mosquitto MQTT broker, installed separately.
- For vision: a laptop/PC USB webcam. A GPU is optional; CPU inference is supported.
- For hardware: ESP32 DevKit, DHT11 or DHT22, HLK-LD2410C radar, and a suitable buzzer/driver.
- Arduino IDE 2.x for the ESP32 firmware.

Python dependencies are declared in `requirements.txt`: Flask, Paho MQTT, OpenCV, Ultralytics, NumPy, Pillow, python-dotenv, psutil, requests, and pytest. Ultralytics may install PyTorch as a dependency; its first model run downloads the configured small model (`yolo11n.pt`). Allow disk space and network access for that one-time setup.

## Installation

### Automatic Windows setup

From the project folder, run `setup.bat`. It creates `venv`, upgrades pip, installs requirements, creates runtime folders, and copies `.env.example` to `.env` if needed. It does not install Mosquitto or any administrator-level software.

### Manual setup

```powershell
cd AIoT-Fire-Emergency-System
py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` for local settings. Do not put real credentials in source control. The Flask app defaults to `127.0.0.1`; to use the dashboard from another device, configure an appropriate host and secure the network first.

## Start Mosquitto

Install Mosquitto separately from the official Mosquitto download site. The project does not silently install it. Open one terminal:

```powershell
mosquitto -v
```

This default local setup usually listens on localhost. To connect an ESP32 on Wi-Fi, configure the broker to listen on the PC's LAN interface, allow TCP port 1883 through Windows Firewall as appropriate, and set `MQTT_BROKER` to the PC's LAN IP in `.env` and `MQTT_HOST` in ESP32 `secrets.h`. Never use `localhost` as the broker address on the ESP32: it would mean the ESP32 itself. Port 1883 is unencrypted; keep testing local or configure authenticated TLS for deployment.

If Mosquitto is absent or stopped, Flask still starts and shows MQTT disconnected. The simulator retries and reports the broker as unavailable.

## Start the dashboard and simulator

Terminal 1 (dashboard):

```powershell
cd AIoT-Fire-Emergency-System
venv\Scripts\activate
python backend/app.py
```

Open `http://127.0.0.1:5000`. API endpoints: `GET /api/status`, `GET /api/network`, and `GET /api/logs`.

Terminal 2 (simulated sensors):

```powershell
cd AIoT-Fire-Emergency-System
venv\Scripts\activate
python simulator/sensor_simulator.py
```

Try `python simulator/sensor_simulator.py --mode WARNING` or `--mode EMERGENCY`; use `--interval 2`. Start the broker before the simulator for live data.

## YOLO webcam detector

With the dashboard and broker running, open another terminal:

```powershell
cd AIoT-Fire-Emergency-System
venv\Scripts\activate
python ai/human_detector.py
```

The detector opens camera index `0`, draws boxes, and exits on `Q`. Set `CAMERA_INDEX` or `YOLO_MODEL` in `.env` if needed. YOLO downloads the lightweight model on first run. It selects CUDA only when available and otherwise runs on CPU. Its MQTT messages contain only detection state and camera connectivity. Close other apps using the webcam if it cannot open.

## ESP32 connection

1. Install Arduino IDE 2.x and the Espressif ESP32 board support using the Boards Manager.
2. Install **PubSubClient** by Nick O'Leary and **DHT sensor library** by Adafruit (including Adafruit Unified Sensor) through Library Manager.
3. Copy `esp32/esp32_fire_monitor/secrets.example.h` to `secrets.h` in that directory. Set Wi-Fi SSID/password, the PC's reachable LAN IPv4 address, and broker port. `secrets.h` is ignored by Git.
4. Open `esp32_fire_monitor.ino`, select the ESP32 DevKit board and serial port, then compile/upload. Change `SENSOR_DHT_TYPE` from `DHT11` to `DHT22` if needed.
5. Monitor serial at 115200 baud. Firmware publishes every two seconds to `fire/emergency/sensor`. The threshold in this starter firmware is `50°C`; keep it aligned with `TEMPERATURE_THRESHOLD` in `.env`.

Do not connect the ESP32 broker host to `localhost`; use the PC's LAN IP. Routers may isolate Wi-Fi clients, so confirm reachability and firewall rules if the board cannot connect.

## Hardware wiring

Disconnect power while wiring. Check the exact breakout-board voltage/current specifications and ESP32 pin tolerance before connecting. Do not drive a high-current buzzer directly from a GPIO; use an appropriate transistor/driver and common ground.

| Module | Connection |
| --- | --- |
| DHT11/DHT22 VCC | 3.3V (check breakout requirements) |
| DHT GND | ESP32 GND |
| DHT DATA | GPIO 4; add pull-up if the module does not include one |
| Buzzer driver input | GPIO 25 |
| Buzzer/driver ground | ESP32 common GND |
| LD2410C TX | ESP32 RX GPIO 16 (crossed) |
| LD2410C RX | ESP32 TX GPIO 17 (crossed) |
| LD2410C GND | ESP32 GND |
| LD2410C power | Use the module's specified supply; verify logic levels before wiring UART |

The firmware initializes UART2 at 256000 baud, RX=16/TX=17. It deliberately does not implement a guessed LD2410C parser: `readRadarPresence()` drains incoming bytes and returns false. Integrate a verified LD2410 library/parser there before treating radar readings as real. Until then, simulated radar and camera presence still exercise the software path. Confirm your specific LD2410C board's voltage and UART configuration from its datasheet before applying power.

## Fire decision rule

`NORMAL` is below 80% of the configured temperature threshold, `WARNING` is at or above 80% but below threshold, and `EMERGENCY` is at or above threshold. Only the emergency level sets backend `fire_status` and buzzer state. Human presence is contextual and does not independently establish a fire. This is a configurable demonstration rule, not a scientifically validated or certified detector. The ESP32 starter buzzer rule uses its firmware constant; update both settings consistently.

## Computer Networks component

See `network/mqtt_topics.md` for IoT, Wi-Fi, IP, client/server, MQTT broker, publisher/subscriber, TCP/IP, port 1883, latency and packet transmission. See `network/network_testing.md` for Windows `ping`, `Test-NetConnection`, MQTT CLI and Wireshark tests. Dashboard latency is a measured TCP connect time to the broker, not application round-trip latency. Packet loss is shown as `N/A`; interface byte counters are host-level totals, not MQTT packet counts.

## Logs and tests

Sensor events are JSONL in `data/logs/events.jsonl`, rotated at 1 MB with three backups. The log route exposes only the latest 100 entries.

```powershell
venv\Scripts\activate
python -m pytest
```

Tests cover fire-rule boundaries, MQTT offline behavior, and network status/latency failure cases; they do not require a live broker, camera, or ESP32.

## Troubleshooting

- **MQTT disconnected:** Run `mosquitto -v`, confirm host/port in `.env`, then test with `Test-NetConnection localhost -Port 1883`.
- **ESP32 cannot reach broker:** Use the PC LAN IPv4 in `secrets.h`; configure Mosquitto for LAN access and check Windows Firewall/client isolation.
- **Dashboard receives no sensor values:** Ensure broker is running and simulator prints a successful connection; subscribe to `fire/emergency/#` with `mosquitto_sub`.
- **Webcam unavailable:** Check `CAMERA_INDEX`, OS camera permissions, and whether another app has locked it.
- **YOLO model download/inference fails:** Confirm internet access for the first model download, available disk space, then retry on CPU. GPU is optional.
- **DHT read failed:** Check GPIO 4, power, ground, pull-up, and selected DHT model type.
- **Radar always reports absent:** This is expected until a verified parser adapter replaces the documented stub.
- **No dependency wheel:** Use Python 3.12 64-bit and rerun `python -m pip install -r requirements.txt` inside the venv.

## Limitations and future improvements

This is a prototype for coursework and controlled demonstrations only. It lacks certified fire sensing, authenticated/encrypted broker configuration, reliable LD2410C parsing, persistent database storage, camera privacy controls beyond local processing, and deployment hardening. The laptop webcam must run on the same broker network. Network latency sampling is TCP connection setup time and packet loss remains unmeasured. There is no LiDAR/depth sensor, so the system does not provide 3D environmental mapping. Future work can add verified radar parsing, multi-sensor calibrated alarm logic, authenticated TLS MQTT, role-based dashboard access, database retention, and optional depth/LiDAR hardware.
