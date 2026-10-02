# ESP32 Hardware Notes

Firmware: `esp32_fire_monitor/esp32_fire_monitor.ino`. It uses DHT11/DHT22 readings, the LD2410 Arduino library API exposed by `ld2410.h`, an active-high buzzer driver, Wi-Fi, and MQTT. Radar UART is read continuously; sensor JSON is published every two seconds to the existing `fire/emergency/sensor` topic.

## Libraries and configuration

Install ESP32 board support in Arduino IDE 2.x, then install **PubSubClient** by Nick O'Leary, **DHT sensor library** by Adafruit, **Adafruit Unified Sensor**, and **ld2410** by ncmreynolds in Library Manager. The sketch uses the library's `begin`, `read`, `isConnected`, presence, and target measurement APIs. Copy `secrets.example.h` to `secrets.h`; set Wi-Fi credentials, the computer's LAN IPv4 broker address, port, and `FIRE_THRESHOLD_C`. Keep that threshold aligned with `TEMPERATURE_THRESHOLD` in the project `.env`. `secrets.h` is excluded from Git.

## Wiring

Power down before wiring and check the exact breakout/module specifications first.

| Module signal | ESP32 connection |
| --- | --- |
| DHT VCC / GND / DATA | 3.3 V / GND / GPIO 4 |
| DHT DATA pull-up | 4.7-10 kOhm from DATA to 3.3 V if the board lacks one |
| LD2410C TX / RX | GPIO 16 (UART RX) / GPIO 17 (UART TX) |
| LD2410C GND | Common GND |
| LD2410C supply | The selected library documents its common breakout as requiring 5 V or higher; verify the exact module before powering |
| Active-high buzzer driver input | GPIO 25 |
| Buzzer driver supply / GND | Suitable supply through the driver / common GND |

GPIO 25 is an active-high logic output intended for a driver input. Do not connect a high-current buzzer directly to an ESP32 GPIO. A wiring that powers a buzzer from 3.3 V and sinks its negative lead on GPIO 25 is active-low and does not match this firmware logic. The selected library documents the common LD2410 breakout as using 3.3 V UART I/O despite its higher module supply; verify this for your exact board.

## Bring-up

1. Start Mosquitto and ensure it accepts LAN clients; allow the broker port through Windows Firewall as appropriate.
2. Upload the sketch for the selected ESP32 board and open Serial Monitor at 115200 baud.
3. Verify Wi-Fi connects and the printed LD2410C status indicates a connected sensor.
4. Check DHT readings and use a person entering/leaving the sensor's configured detection area to verify real radar presence and target measurements.
5. Subscribe on the computer with `mosquitto_sub -h localhost -p 1883 -t fire/emergency/sensor -v` and confirm the ESP32 JSON arrives about every two seconds.
6. Run the Flask backend and open `http://127.0.0.1:5000`; verify the sensor status, last-seen time, and approximate range band update.
7. Test the buzzer threshold only with a safe, controlled method. Never use an actual fire.
8. Disconnect/reconnect Wi-Fi or stop/restart Mosquitto and verify the firmware reconnects without blocking local sensor sampling or buzzer logic.

The JSON includes temperature, humidity, `presence`, radar connection, moving/stationary distance and energy, local alarm state, system status, and uptime. The backend records its own receive timestamp; ESP32 uptime is not treated as wall-clock time.

## Camera and map limits

No OV2640 capture driver or board-specific camera pin map is implemented. SDA/SCL alone are not enough to capture images, and raw OV2640 GPIO mappings depend on the exact ESP32 camera board. The optional existing YOLO process uses a laptop USB webcam. The dashboard's 2D map uses distance-only near/mid/far zones; the LD2410C does not report left/right bearing, so the marker is illustrative rather than an exact coordinate.

Use an external antenna only when the exact ESP32 board has a compatible antenna connector and switching arrangement. Do not modify antenna hardware based only on the diagram.

This is an educational prototype, not a certified fire alarm or life-safety system. Verify the exact radar library version, module voltage, firmware compile, and hardware behavior before a demonstration.
