// Keypad Door Lock v2 -- PIN entry, servo bolt, PIR intrusion alarm, lockout,
// WiFi/MQTT remote unlock, cloud event log. Physical build of the "Ladder C"
// spec from hardware/projects.txt. See ../../knowledge/00_START_HERE.md for
// the full write-up and ../../wiring/WIRING.md before connecting anything.
//
// Libraries needed (Arduino Library Manager -- exact names/authors):
//   Keypad             by Mark Stanley, Alexander Brevig
//   ESP32Servo         by Kevin Harrington, John K. Bennett
//   Adafruit SSD1306 + Adafruit GFX Library    by Adafruit
//   PubSubClient       by Nick O'Leary
//   ArduinoJson        by Benoit Blanchon (only used to parse incoming MQTT
//                       commands -- see events.h for why the outgoing side
//                       doesn't use it)
//
// Board: any ESP32 dev board, via the esp32 core
// (https://github.com/espressif/arduino-esp32) added through Boards Manager.

#include <Keypad.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "secrets.h"
#include "lock_fsm.h"
#include "events.h"

char keys[4][4] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'},
};
uint8_t rowPins[4] = {KEYPAD_ROW_PINS[0], KEYPAD_ROW_PINS[1], KEYPAD_ROW_PINS[2], KEYPAD_ROW_PINS[3]};
uint8_t colPins[4] = {KEYPAD_COL_PINS[0], KEYPAD_COL_PINS[1], KEYPAD_COL_PINS[2], KEYPAD_COL_PINS[3]};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, 4, 4);

Servo bolt;
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

LockFsm lock(LOCK_PIN, PIN_LENGTH, MAX_ATTEMPTS, LOCKOUT_MS, UNLOCK_MS,
             SERVO_LOCKED_ANGLE, SERVO_UNLOCKED_ANGLE);

String eventTopic, commandTopic, statusTopic;
unsigned long lastTickMs = 0;
unsigned long lastAlarmBlinkMs = 0;
bool alarmBlinkOn = false;

void handleEvents(EventList events);
void updateLeds();
void updateAlarmSound();
void updateDisplay();
void connectWifi();
void connectMqtt();
void onMqttMessage(char* topic, byte* payload, unsigned int length);

void setup() {
  Serial.begin(115200);

  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_LOCKED_PIN, OUTPUT);
  pinMode(LED_UNLOCKED_PIN, OUTPUT);
  pinMode(LED_ALARM_PIN, OUTPUT);

  bolt.attach(SERVO_PIN);
  bolt.write(SERVO_LOCKED_ANGLE);

  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println("OLED not found -- check wiring/WIRING.md");
  }

  eventTopic = String("doorlock/") + DEVICE_ID + "/event";
  commandTopic = String("doorlock/") + DEVICE_ID + "/cmd";
  statusTopic = String("doorlock/") + DEVICE_ID + "/status";

  connectWifi();
  configTime(0, 0, "pool.ntp.org");  // real wall-clock time for event timestamps
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  connectMqtt();

  lastTickMs = millis();
  Serial.println("Ready. State: LOCKED");
  updateDisplay();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  char key = keypad.getKey();
  if (key) {
    handleEvents(lock.pressKey(key));
  }

  if (digitalRead(PIR_PIN) == HIGH) {
    handleEvents(lock.doorOpened());
  }

  unsigned long now = millis();
  handleEvents(lock.tick(now - lastTickMs));
  lastTickMs = now;

  bolt.write(lock.boltAngle());
  updateLeds();
  updateAlarmSound();
  updateDisplay();
}

void handleEvents(EventList events) {
  for (uint8_t i = 0; i < events.count; i++) {
    FsmEvent e = events.items[i];
    Serial.println(String("event: ") + eventKindName(e.kind));
    String json = buildEventJson(e.kind, e.data);
    mqtt.publish(eventTopic.c_str(), json.c_str());
  }
}

void updateLeds() {
  LockState s = lock.state();
  digitalWrite(LED_LOCKED_PIN, s == LockState::Locked ? HIGH : LOW);
  digitalWrite(LED_UNLOCKED_PIN, s == LockState::Unlocked ? HIGH : LOW);

  bool alarmActive = (s == LockState::Alarm || s == LockState::Lockout);
  if (alarmActive) {
    if (millis() - lastAlarmBlinkMs > 300) {
      alarmBlinkOn = !alarmBlinkOn;
      lastAlarmBlinkMs = millis();
    }
    digitalWrite(LED_ALARM_PIN, alarmBlinkOn ? HIGH : LOW);
  } else {
    digitalWrite(LED_ALARM_PIN, LOW);
  }
}

void updateAlarmSound() {
  if (lock.state() == LockState::Alarm) {
    tone(BUZZER_PIN, 2000);
  } else if (lock.state() == LockState::Lockout) {
    tone(BUZZER_PIN, 500);
  } else {
    noTone(BUZZER_PIN);
  }
}

void updateDisplay() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 0);
  switch (lock.state()) {
    case LockState::Locked:    display.println("LOCKED"); break;
    case LockState::Unlocked:  display.println("UNLOCKED"); break;
    case LockState::Lockout:   display.println("LOCKOUT"); break;
    case LockState::Alarm:     display.println("** ALARM **"); break;
  }

  display.setTextSize(1);
  display.setCursor(0, 40);
  display.print("attempts left: ");
  display.println(lock.attemptsRemaining());
  display.display();
}

void connectWifi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected. IP: " + WiFi.localIP().toString());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    String clientId = String("doorlock-") + DEVICE_ID;
    // Last-Will-and-Testament: if this device drops off the network without
    // a clean disconnect, the broker publishes "offline" on our behalf --
    // that's how the dashboard tells "disconnected" apart from "connected
    // but quiet".
    if (mqtt.connect(clientId.c_str(), statusTopic.c_str(), 0, true, "offline")) {
      Serial.println(" connected.");
      mqtt.subscribe(commandTopic.c_str());
      mqtt.publish(statusTopic.c_str(), "online", true);
    } else {
      Serial.println(" failed, rc=" + String(mqtt.state()) + ", retrying in 5s");
      delay(5000);
    }
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  // Untrusted input from a shared public broker -- this is exactly the
  // boundary where a real JSON parser earns its keep instead of hand-rolled
  // string matching.
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.println("Bad command payload, ignoring.");
    return;
  }
  const char* cmd = doc["cmd"];
  if (cmd == nullptr) return;

  if (strcmp(cmd, "unlock") == 0) {
    handleEvents(lock.remoteUnlock());
  } else if (strcmp(cmd, "clear_alarm") == 0) {
    handleEvents(lock.remoteClearAlarm());
  } else {
    Serial.println(String("Unknown command '") + cmd + "', ignoring.");
  }
}
