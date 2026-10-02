# MQTT Topics and Network Concepts

## Topic contract

| Topic | Direction | Purpose |
| --- | --- | --- |
| `fire/emergency/sensor` | ESP32/simulator/camera to backend | Sensor readings or camera detection metadata |
| `fire/emergency/alert` | Backend to subscribers | Rising-edge prototype emergency alert |
| `fire/emergency/network` | Device to backend | Optional device network diagnostics |

ESP32 sensor JSON on `fire/emergency/sensor` carries `temperature`, `humidity`, `presence`, `radar_connected`, `moving_distance`, `stationary_distance`, `moving_energy`, `stationary_energy`, `alarm`, `status`, `device`, and `uptime_ms`. The backend also accepts the simulator's legacy `human_detected` field. ESP32 uptime is not wall-clock time; the backend assigns the receive timestamp used by the dashboard and JSONL event log. Camera messages carry `source: camera`, `human_camera`, `camera_connected`, and an ISO timestamp. Camera frames are not sent. MQTT QoS 1 is used for backend publications; the simulator also publishes at QoS 1.

## Computer Networks concepts

1. **IoT device:** ESP32 reads local sensors and sends their measurements.
2. **Wi-Fi:** A wireless LAN link gives the ESP32 and PC network access; both must be able to reach the broker.
3. **IP address:** A network-layer address identifying a host/interface, shown by the backend when available.
4. **Client-server communication:** ESP32, simulator, backend, and camera process are MQTT clients; Mosquitto is the message server (broker).
5. **MQTT:** A lightweight publish/subscribe messaging protocol suited to small telemetry messages.
6. **MQTT broker:** Mosquitto accepts client connections, routes topic publications to subscribers, and manages subscriptions.
7. **Publisher:** A process that sends a message to a topic, such as the ESP32 publishing sensor values.
8. **Subscriber:** A process that subscribes to a topic, such as the backend subscribing to sensor data.
9. **TCP/IP:** MQTT runs over TCP/IP here, providing reliable, ordered transport between client and broker.
10. **Port 1883:** The conventional unencrypted MQTT TCP port. Keep this prototype broker on a trusted local network; use TLS/authentication before exposing a broker.
11. **Network latency:** The app times a TCP connection attempt to the configured MQTT host and port. It is a connection-time sample, not a continuous round-trip MQTT measurement; it shows `N/A` if the connection fails.
12. **Packet transmission:** Interface byte counters from `psutil` describe bytes sent/received by the host; they are not application-specific MQTT packet counts.
13. **Wireless communication:** Wi-Fi uses radio between the ESP32 and access point; signal quality, interference, and distance can affect delivery delay or availability.

The dashboard never invents packet-loss values; loss is shown as `N/A` because this prototype does not measure it reliably.
