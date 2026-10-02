#define DEVICE_ROLE_SENSOR 1
#define DEVICE_ROLE_CAMERA 2
#include "secrets.h"

#ifndef DEVICE_ROLE
#define DEVICE_ROLE DEVICE_ROLE_SENSOR
#endif

#include <WiFi.h>

#if DEVICE_ROLE == DEVICE_ROLE_SENSOR
#include <PubSubClient.h>
#include <DHT.h>
#include <ld2410.h>
#elif DEVICE_ROLE == DEVICE_ROLE_CAMERA
#include "esp_camera.h"
#include <WebServer.h>
#ifndef CAMERA_MODEL_AI_THINKER
#error "Camera role pin map is AI-Thinker ESP32-CAM only. Confirm board and define CAMERA_MODEL_AI_THINKER in secrets.h."
#endif
#else
#error "Set DEVICE_ROLE to DEVICE_ROLE_SENSOR or DEVICE_ROLE_CAMERA in secrets.h."
#endif

#if DEVICE_ROLE == DEVICE_ROLE_SENSOR

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

  buzzerOn = temperature >= FIRE_THRESHOLD_C;
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

#elif DEVICE_ROLE == DEVICE_ROLE_CAMERA

// AI-Thinker ESP32-CAM + OV2640 pin map. Never use for another board variant.
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

static constexpr uint16_t HTTP_PORT = 80;
static constexpr uint32_t WIFI_RETRY_MS = 10000;
static constexpr uint32_t STREAM_FRAME_DELAY_MS = 120;
static constexpr char STREAM_BOUNDARY[] = "frame";

WebServer cameraServer(HTTP_PORT);
uint32_t lastWiFiAttempt = 0;

void beginCameraWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWiFiAttempt = millis();
  Serial.printf("Connecting to Wi-Fi SSID: %s\n", WIFI_SSID);
}

bool beginCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Reduce resolution and framebuffer count on modules without PSRAM.
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  const esp_err_t result = esp_camera_init(&config);
  if (result != ESP_OK) {
    Serial.printf("OV2640 camera initialization failed: 0x%04x\n", result);
    return false;
  }
  Serial.println("OV2640 initialized in JPEG mode");
  return true;
}

void sendCameraRoot() {
  const String page =
      "<!doctype html><html><head><meta name=\"viewport\" content=\"width=device-width\">"
      "<title>ESP32-CAM</title></head><body><h1>ESP32-CAM</h1>"
      "<p><a href=\"/capture\">JPEG snapshot</a></p>"
      "<p><a href=\"/stream\">MJPEG stream</a></p></body></html>";
  cameraServer.sendHeader("Access-Control-Allow-Origin", "*");
  cameraServer.sendHeader("Cache-Control", "no-store");
  cameraServer.send(200, "text/html; charset=utf-8", page);
}

void sendCameraError(const char* message) {
  cameraServer.sendHeader("Access-Control-Allow-Origin", "*");
  cameraServer.sendHeader("Cache-Control", "no-store");
  cameraServer.send(503, "text/plain; charset=utf-8", message);
}

void sendSnapshot() {
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    Serial.println("Camera capture failed: no framebuffer");
    sendCameraError("Camera capture failed");
    return;
  }

  WiFiClient client = cameraServer.client();
  client.printf(
      "HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n"
      "Cache-Control: no-store\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n",
      static_cast<unsigned int>(frame->len));
  const size_t written = client.write(frame->buf, frame->len);
  esp_camera_fb_return(frame);
  if (written != frame->len) Serial.println("Warning: incomplete JPEG response");
  client.stop();
}

void sendMjpegStream() {
  WiFiClient client = cameraServer.client();
  client.print(
      "HTTP/1.1 200 OK\r\n"
      "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
      "Cache-Control: no-store\r\n"
      "Access-Control-Allow-Origin: *\r\n"
      "Connection: close\r\n\r\n");

  Serial.println("MJPEG client connected; snapshot requests wait until stream closes");
  while (client.connected() && WiFi.status() == WL_CONNECTED) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame == nullptr) {
      delay(50);
      continue;
    }

    client.printf(
        "--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
        STREAM_BOUNDARY,
        static_cast<unsigned int>(frame->len));
    const size_t written = client.write(frame->buf, frame->len);
    client.print("\r\n");
    esp_camera_fb_return(frame);
    if (written == 0) break;
    delay(STREAM_FRAME_DELAY_MS);
    yield();
  }
  client.stop();
  Serial.println("MJPEG client disconnected");
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("AI-Thinker ESP32-CAM OV2640 snapshot server");

  if (!beginCamera()) {
    Serial.println("Check the confirmed AI-Thinker board, OV2640 connector, and PSRAM setting.");
    while (true) delay(1000);
  }

  beginCameraWiFi();
  cameraServer.on("/", HTTP_GET, sendCameraRoot);
  cameraServer.on("/capture", HTTP_GET, sendSnapshot);
  cameraServer.on("/stream", HTTP_GET, sendMjpegStream);
  cameraServer.onNotFound([]() { cameraServer.send(404, "text/plain", "Not found"); });
  cameraServer.begin();
  Serial.printf("Camera HTTP server listening on port %u\n", HTTP_PORT);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWiFiAttempt >= WIFI_RETRY_MS) beginCameraWiFi();
  } else {
    cameraServer.handleClient();
  }
  delay(2);
}

#endif