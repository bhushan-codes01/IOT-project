#pragma once

// Default role preserves the original DHT/radar/buzzer/MQTT firmware.
// Change to DEVICE_ROLE_CAMERA only for the separate AI-Thinker ESP32-CAM board.
#define DEVICE_ROLE DEVICE_ROLE_SENSOR

#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_HOST "192.168.1.10"  // Set to the PC's LAN IPv4 address, not localhost.
#define MQTT_PORT 1883
#define FIRE_THRESHOLD_C 50.0f  // Keep aligned with TEMPERATURE_THRESHOLD in .env.

// In CAMERA role, uncomment only after confirming AI-Thinker ESP32-CAM + OV2640.
// #define CAMERA_MODEL_AI_THINKER
