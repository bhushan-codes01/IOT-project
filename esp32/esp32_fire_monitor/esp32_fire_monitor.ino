#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ld2410.h>
#include "secrets.h"

#define DHT_PIN 4
#ifndef SENSOR_DHT_TYPE
#define SENSOR_DHT_TYPE DHT11  // Change to DHT22 when using that sensor.
#endif
#ifndef FIRE_THRESHOLD_C
#define FIRE_THRESHOLD_C 50.0f
#endif
#define BUZZER_PIN 25
#define RADAR_RX_PIN 16
#define RADAR_TX_PIN 17
#define SENSOR_TOPIC "fire/emergency/sensor"

DHT dht(DHT_PIN, SENSOR_DHT_TYPE);
HardwareSerial radarSerial(2);
ld2410 radar;
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
unsigned long lastSensorRead = 0;
unsigned long lastReconnectAttempt = 0;
unsigned long lastWiFiAttempt = 0;
bool buzzerOn = false;
bool humanDetected = false;
bool radarConnected = false;
float temperature = NAN;
float humidity = NAN;
uint16_t movingDistance = 0;
uint16_t stationaryDistance = 0;
uint8_t movingEnergy = 0;
uint8_t stationaryEnergy = 0;

const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long RECONNECT_INTERVAL = 5000;

const char* getSystemStatus() {
  if (temperature >= FIRE_THRESHOLD_C) return "EMERGENCY";
  if (temperature >= FIRE_THRESHOLD_C * 0.8f) return "WARNING";
  return "NORMAL";
}

void updateRadarState() {
  radarConnected = radar.isConnected();
  humanDetected = radarConnected && radar.presenceDetected();
  movingDistance = 0;
  stationaryDistance = 0;
  movingEnergy = 0;
  stationaryEnergy = 0;

  if (!humanDetected) return;
  if (radar.movingTargetDetected()) {
    movingDistance = radar.movingTargetDistance();
    movingEnergy = radar.movingTargetEnergy();
  }
  if (radar.stationaryTargetDetected()) {
    stationaryDistance = radar.stationaryTargetDistance();
    stationaryEnergy = radar.stationaryTargetEnergy();
  }
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastWiFiAttempt < RECONNECT_INTERVAL) return;
  lastWiFiAttempt = millis();
  Serial.printf("Connecting to Wi-Fi %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool connectMqtt() {
  if (mqttClient.connected()) return true;
  const String clientId = "esp32-fire-monitor-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("Connected to MQTT broker");
    return true;
  }
  Serial.printf("MQTT connection failed, state=%d\n", mqttClient.state());
  return false;
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  dht.begin();

  // LD2410C TX -> GPIO16 (RX), RX -> GPIO17 (TX); default UART is 256000 baud.
  radarSerial.begin(256000, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);
  if (radar.begin(radarSerial)) {
    Serial.println("LD2410C connected");
  } else {
    Serial.println("LD2410C not detected; check power, UART wiring, and baud rate");
  }

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setBufferSize(384);
  connectWiFi();
}

void loop() {
  radar.read();
  connectWiFi();

  if (WiFi.status() != WL_CONNECTED) {
    if (mqttClient.connected()) mqttClient.disconnect();
  } else if (!mqttClient.connected() && millis() - lastReconnectAttempt >= RECONNECT_INTERVAL) {
    lastReconnectAttempt = millis();
    connectMqtt();
  }
  mqttClient.loop();

  const unsigned long now = millis();
  if (now - lastSensorRead < SENSOR_INTERVAL) return;
  lastSensorRead = now;

  const float newTemperature = dht.readTemperature();
  const float newHumidity = dht.readHumidity();
  if (isnan(newTemperature) || isnan(newHumidity)) {
    Serial.println("DHT read failed; skipping this sensor publication");
    buzzerOn = false;
    digitalWrite(BUZZER_PIN, LOW);
    return;
  }

  temperature = newTemperature;
  humidity = newHumidity;
  updateRadarState();

  const bool emergency = temperature >= FIRE_THRESHOLD_C;
  buzzerOn = emergency;
  digitalWrite(BUZZER_PIN, buzzerOn ? HIGH : LOW);

  char payload[320];
  snprintf(payload, sizeof(payload),
           "{\"temperature\":%.1f,\"humidity\":%.1f,\"presence\":%s,\"radar_connected\":%s,\"moving_distance\":%u,\"stationary_distance\":%u,\"moving_energy\":%u,\"stationary_energy\":%u,\"alarm\":%s,\"status\":\"%s\",\"device\":\"ESP32\",\"uptime_ms\":%lu}",
           temperature, humidity, humanDetected ? "true" : "false",
           radarConnected ? "true" : "false", movingDistance, stationaryDistance,
           movingEnergy, stationaryEnergy, buzzerOn ? "true" : "false",
           getSystemStatus(), now);
  if (mqttClient.connected()) {
    const bool sent = mqttClient.publish(SENSOR_TOPIC, payload);
    Serial.printf("Published=%s %s\n", sent ? "yes" : "no", payload);
  }
}
