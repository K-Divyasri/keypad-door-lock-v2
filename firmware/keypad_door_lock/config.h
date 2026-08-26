#pragma once

// Pin assignments and timing constants for the keypad door lock. See
// ../../wiring/WIRING.md for the full pin-by-pin table, the bill of
// materials, and what to check with a multimeter before powering this up.

// ---- 4x4 matrix keypad -----------------------------------------------------
// 4 row pins, 4 column pins -- see knowledge/02_the_keypad_matrix_scan.md for
// why 8 GPIOs read 16 buttons instead of wiring one pin per key.
const uint8_t KEYPAD_ROW_PINS[4] = {13, 12, 14, 27};
const uint8_t KEYPAD_COL_PINS[4] = {26, 25, 33, 32};

// ---- SG90 servo -------------------------------------------------------------
// Any PWM-capable GPIO works; 18 is free on most ESP32 dev boards.
const uint8_t SERVO_PIN = 18;

// ---- PIR motion sensor ------------------------------------------------------
// Reads HIGH while motion is seen, LOW otherwise.
const uint8_t PIR_PIN = 4;

// ---- Piezo buzzer -----------------------------------------------------------
// Driven with tone()/noTone() -- a steady low tone during LOCKOUT, an
// urgent high tone during ALARM.
const uint8_t BUZZER_PIN = 5;

// ---- Status LEDs -------------------------------------------------------------
const uint8_t LED_LOCKED_PIN = 15;    // solid while LOCKED
const uint8_t LED_UNLOCKED_PIN = 2;   // solid while UNLOCKED (many boards
                                       // already have an LED wired to 2)
const uint8_t LED_ALARM_PIN = 19;     // flashing while ALARM or LOCKOUT

// ---- I2C OLED (SSD1306, 128x64) ----------------------------------------------
// 21/22 are the ESP32's default I2C pins (SDA/SCL) -- no extra wiring config
// needed beyond connecting the display to them.
const uint8_t OLED_SDA_PIN = 21;
const uint8_t OLED_SCL_PIN = 22;
const uint8_t OLED_ADDRESS = 0x3C;
const uint8_t OLED_WIDTH = 128;
const uint8_t OLED_HEIGHT = 64;

// ---- Lock behaviour ----------------------------------------------------------
// Same defaults as doorlock_sim.LockConfig -- change one, change the other,
// or the simulator stops being a faithful twin of the real firmware.
const char LOCK_PIN[] = "1234";
const uint8_t PIN_LENGTH = 4;
const uint8_t MAX_ATTEMPTS = 3;
const unsigned long LOCKOUT_MS = 30000;
const unsigned long UNLOCK_MS = 5000;
const uint8_t SERVO_LOCKED_ANGLE = 0;
const uint8_t SERVO_UNLOCKED_ANGLE = 90;

// ---- MQTT ----------------------------------------------------------------------
const char MQTT_BROKER[] = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;
