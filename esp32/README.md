# ESP32 firmware

The ESP32 sensor firmware is implemented in `esp32/esp32_fire_monitor/esp32_fire_monitor.ino` and is designed for the actual project hardware only:

- ESP32 DevKit
- DHT11 temperature and humidity sensor
- HLK-LD2410C radar sensor
- Active buzzer

The firmware does not include any camera module or camera-library support.

## Wiring

### DHT11
- VCC -> ESP32 3.3V
- DATA -> GPIO 4
- GND -> GND
- Add a 10k pull-up to 3.3V if needed

### LD2410C
- TX -> GPIO 16 (UART2 RX)
- RX -> GPIO 17 (UART2 TX)
- GND -> GND
- VCC -> module-specified supply
- Baud rate -> 256000

### Active buzzer
- + -> GPIO 25
- - -> GND
- Use a transistor or MOSFET driver if a direct GPIO connection is not safe.

## MQTT settings

Create a local `esp32/secrets.h` file before compiling, with values such as:

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

The board publishes to `fire/emergency/sensor` as JSON with fields including temperature, humidity, presence, radar connectivity, moving/stationary distances, energies, alarm, status, device, and uptime.

## Upload

1. Open the Arduino IDE.
2. Select the ESP32 board and port.
3. Compile and upload `esp32_fire_monitor.ino`.
4. Confirm Wi-Fi connection and MQTT publishing to the Mosquitto broker.

## Notes

- Use the PC LAN IP of the Mosquitto broker for `MQTT_HOST`.
- Never use `localhost` or `127.0.0.1` in the ESP32 firmware.
- The webcam remains connected to the laptop USB port and is not part of the ESP32 firmware.
