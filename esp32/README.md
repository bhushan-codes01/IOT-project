# ESP32 Firmware

All ESP32 firmware is in the single source file `esp32_fire_monitor/esp32_fire_monitor.ino`. It has two compile-time roles selected in the local `esp32_fire_monitor/secrets.h`:

- `DEVICE_ROLE_SENSOR` (default): original ESP32 DevKit firmware for DHT11/DHT22, LD2410C radar, active-high buzzer, Wi-Fi, and MQTT.
- `DEVICE_ROLE_CAMERA`: separate AI-Thinker ESP32-CAM + OV2640 firmware for HTTP JPEG snapshots and optional MJPEG streaming.

The roles are alternatives: compile and upload the same `.ino` once for each physical board, changing `DEVICE_ROLE` in `secrets.h` before each build. The sensor role remains the default and preserves its existing MQTT JSON fields/topic. The camera role does not publish images through MQTT.

## Libraries

Install Arduino IDE 2.x and Espressif ESP32 board support. For the sensor role install:

- PubSubClient by Nick O'Leary
- DHT sensor library by Adafruit
- Adafruit Unified Sensor
- `ld2410` by ncmreynolds

The camera role uses `esp_camera.h` and `WebServer.h` from the ESP32 Arduino board package; it does not require another Arduino library.

## Shared `secrets.h`

Copy `esp32_fire_monitor/secrets.example.h` to `esp32_fire_monitor/secrets.h`. This file is ignored by Git. Set the Wi-Fi credentials for the board being programmed. For sensor mode also set `MQTT_HOST` to the PC's reachable LAN IPv4 address (not `localhost`), `MQTT_PORT`, and `FIRE_THRESHOLD_C` aligned with `.env`'s `TEMPERATURE_THRESHOLD`.

Sensor role (default):

```cpp
#define DEVICE_ROLE DEVICE_ROLE_SENSOR
```

Camera role is selected only after checking the physical camera board:

```cpp
#define DEVICE_ROLE DEVICE_ROLE_CAMERA
#define CAMERA_MODEL_AI_THINKER
```

The checked-in example defaults to sensor mode and leaves the camera-model define commented out. The compile-time guard intentionally rejects camera mode without that confirmation. If your camera board is not specifically AI-Thinker ESP32-CAM with OV2640, do not enable this define or use its pin map; identify the exact variant first.

## Sensor-role wiring

Power down while wiring. Confirm exact module voltage and logic requirements.

| Signal | Main ESP32 DevKit |
| --- | --- |
| DHT VCC / GND / DATA | 3.3 V / GND / GPIO 4 |
| DHT pull-up | 10 kΩ DATA-to-3.3 V if not present on module |
| LD2410C TX / RX | GPIO 16 (UART2 RX) / GPIO 17 (UART2 TX), crossed |
| LD2410C supply / GND | Module-specified supply / common GND; common breakouts often require 5 V with 3.3 V UART logic, but check exact board |
| Buzzer driver input | GPIO 25, active-high |
| Buzzer driver return | Common GND; use a transistor/MOSFET driver, not a high-current direct GPIO load |

UART2 runs at 256000 baud. The sensor role publishes every two seconds to `fire/emergency/sensor` with temperature, humidity, `presence`, radar connectivity, moving/stationary distance and energy, alarm/status, device, and uptime fields.

## Camera-role wiring: AI-Thinker board only

The OV2640 module is attached to the ESP32-CAM PCB. Do not connect its camera bus to GPIO 21/22 on the main ESP32 DevKit. For flashing, use a USB-to-TTL adapter with 3.3 V UART logic and a separate stable 5 V supply for the camera board:

| USB-to-TTL / boot wiring | AI-Thinker ESP32-CAM |
| --- | --- |
| Adapter TX | U0R / GPIO 3 (RX) |
| Adapter RX | U0T / GPIO 1 (TX) |
| GND | GND |
| Stable regulated 5 V | 5V pin; avoid powering from adapter 3.3 V |
| Flash-mode jumper | GPIO 0 to GND only during upload; remove to run |

The camera signals wired internally on this specific board are: PWDN=32, XCLK=0, SCCB SDA/SCL=26/27, D0-D7=5/18/19/21/36/39/34/35, VSYNC=25, HREF=23, PCLK=22. These pins are not generic ESP32-CAM assignments.

## Flash the single sketch

### Main sensor board

1. Select `DEVICE_ROLE_SENSOR` in local `secrets.h`.
2. Select the ESP32 DevKit board and its COM port in Arduino IDE.
3. Upload the shared `esp32_fire_monitor.ino` and open Serial Monitor at 115200 baud.
4. Check Wi-Fi, LD2410C, DHT readings, and MQTT publications.

### Optional camera board

1. Confirm the board marking/model says AI-Thinker ESP32-CAM with OV2640. If unknown or different, stop and provide the exact model before compiling.
2. Select `DEVICE_ROLE_CAMERA` and uncomment `CAMERA_MODEL_AI_THINKER` in the same local `secrets.h`.
3. Select **AI Thinker ESP32-CAM** in Arduino IDE. Enable PSRAM if that option is available.
4. Connect USB-to-TTL TX/RX crossed, GND, stable 5 V, and GPIO0-to-GND for flashing. Never apply 5 V UART logic.
5. Upload the same `esp32_fire_monitor.ino`. If upload waits to connect, reset the board after upload starts.
6. Remove the GPIO0-GND jumper and reset/power-cycle. Open Serial Monitor at 115200 baud; record its IP.
7. Check `http://CAMERA_IP/capture` for a JPEG and `http://CAMERA_IP/stream` for MJPEG.
8. Set `CAMERA_BASE_URL=http://CAMERA_IP` in the project `.env`, restart Flask, then use Capture Image / Refresh Image / Start Live Stream on the dashboard.

The MJPEG route uses synchronous `WebServer` and occupies the camera's request loop while streaming, so use one viewer and stop the stream before requesting snapshots. Camera HTTP routes have no authentication; keep them on a trusted LAN and do not port-forward them.

This remains an educational prototype, not a certified fire alarm or life-safety system. Hardware compile and image capture must be verified on the exact physical boards.