# Network Testing Guide (Windows)

## Check the local network

Open PowerShell or Command Prompt:

```powershell
ipconfig
ping 127.0.0.1
ping <MQTT_BROKER_IP>
```

A successful ping tests ICMP reachability only; some networks block ICMP. It does not prove that MQTT is available.

## Start and test Mosquitto

Install Mosquitto separately from the official Mosquitto download page. The installer may offer to register a Windows service; administrator access is not required to run the broker manually from a normal terminal.

```powershell
mosquitto -v
```

In a second terminal, subscribe and publish a probe:

```powershell
mosquitto_sub -h localhost -p 1883 -t fire/emergency/# -v
mosquitto_pub -h localhost -p 1883 -t fire/emergency/sensor -m '{"temperature":42,"humidity":55,"human_detected":true,"device":"test","timestamp":"2026-01-01T00:00:00Z"}'
```

If the commands are not found, add the Mosquitto installation directory to PATH or use the executable's full path. For remote ESP32 use, configure Mosquitto to listen on the PC's LAN interface and firewall appropriately; the default loopback-only/local configuration may not accept remote clients.

## Check TCP port connectivity and measured latency

```powershell
Test-NetConnection localhost -Port 1883
Test-NetConnection <MQTT_BROKER_IP> -Port 1883
```

The dashboard latency is the elapsed time of a TCP connection attempt to the broker. This is not an MQTT application round-trip time. A failed connection appears as `N/A`.

## Inspect packet flow with Wireshark

1. Install Wireshark separately and select the active Wi-Fi/Ethernet interface.
2. Start a capture, then use display filter `tcp.port == 1883`.
3. Start the simulator or publish a probe and inspect TCP setup plus MQTT packets.
4. Plain MQTT on 1883 is not encrypted. Do not transmit real Wi-Fi credentials or sensitive data in packet captures; prefer a TLS broker on port 8883 for deployed systems.

Packet loss is not calculated by this app. Use a controlled network test tool if packet-loss measurement is needed, and record the method and test endpoint.
