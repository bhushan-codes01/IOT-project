#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "secrets.h"

#define DHT_PIN 4
#ifndef SENSOR_DHT_TYPE
#define SENSOR_DHT_TYPE DHT11  // Change to DHT22 when using that sensor.
#endif
#define BUZZER_PIN 25
#define RADAR_RX_PIN 16
#define RADAR_TX_PIN 17
#define FIRE_THRESHOLD_C 50.0f
#define SENSOR_TOPIC "fire/emergency/sensor"

DHT dht(DHT_PIN, SENSOR_DHT_TYPE);
HardwareSerial radarSerial(2);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
unsigned long lastPublish = 0;
unsigned long lastReconnectAttempt = 0;
bool buzzerOn = false;

// Replace this adapter body with calls to a verified LD2410C parser/library.
// No LD2410C binary frame parser is implemented or implied by this prototype.
bool readRadarPresence() {
  while (radarSerial.available() > 0) {
    radarSerial.read();  // Avoid UART buffer overflow until a real parser is integrated.
  }
  return false;
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("Connecting to Wi-Fi %s\n", WIFI_SSID);
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

  // LD2410C UART wiring is crossed: sensor TX -> GPIO16 (ESP32 RX),
  // sensor RX -> GPIO17 (ESP32 TX). Baud rate must match sensor configuration.
  radarSerial.begin(256000, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    delay(100);
    return;
  }

  if (!mqttClient.connected() && millis() - lastReconnectAttempt >= 5000) {
    lastReconnectAttempt = millis();
    connectMqtt();
  }
  mqttClient.loop();

  if (millis() - lastPublish < 2000) return;
  lastPublish = millis();

  const float temperature = dht.readTemperature();
  const float humidity = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT read failed; skipping this sensor publication");
    return;
  }

  const bool humanDetected = readRadarPresence();
  const bool emergency = temperature >= FIRE_THRESHOLD_C;
  buzzerOn = emergency;
  digitalWrite(BUZZER_PIN, buzzerOn ? HIGH : LOW);

  char payload[220];
  snprintf(payload, sizeof(payload),
           "{\"temperature\":%.1f,\"humidity\":%.1f,\"human_detected\":%s,\"device\":\"ESP32\",\"timestamp\":%lu}",
           temperature, humidity, humanDetected ? "true" : "false", millis());
  if (mqttClient.connected()) {
    const bool sent = mqttClient.publish(SENSOR_TOPIC, payload);
    Serial.printf("Published=%s %s\n", sent ? "yes" : "no", payload);
  }
}
