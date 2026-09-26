# ESP32 Hardware Notes

The firmware is in `esp32_fire_monitor/esp32_fire_monitor.ino`. Copy `secrets.example.h` to `secrets.h` in that same directory and enter local Wi-Fi and broker settings there. `secrets.h` is excluded from Git. The ESP32 and PC must be routable to the same MQTT broker; for remote ESP32 clients, Mosquitto must listen on the PC's LAN interface and Windows Firewall must allow the chosen port.

This prototype reads the DHT sensor, drives a buzzer at the configured temperature threshold, and publishes JSON every two seconds. The LD2410C UART is initialized but its binary protocol is intentionally not guessed or falsely parsed. `readRadarPresence()` is the integration point for a verified HLK-LD2410C parser/library; until that adapter is installed, firmware reports radar presence as false. See the root README's wiring and limitations sections.
