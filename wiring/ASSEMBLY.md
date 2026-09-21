# Assembly -- build it one rung at a time

Don't wire everything at once and hope. Bring each piece up on its own,
confirm it with a tiny throwaway sketch and the serial monitor, *then* move
to the next piece. If something breaks later, you'll know it's the new
piece, not a mystery buried in six simultaneous changes. This is the same
discipline `wiring/WIRING.md`'s multimeter checks are for -- catching a
problem at the smallest possible diff.

Each rung below: what to wire, a minimal test sketch, and what "working"
looks like. The full combined firmware is
`firmware/keypad_door_lock/keypad_door_lock.ino` -- you don't type these test
sketches into that project; paste each into a new, throwaway Arduino sketch,
confirm it works, then move on. Delete each throwaway sketch once you've
moved on to the next rung.

## Rung 0 -- bare board

Wire nothing. Plug the ESP32 into USB, open the Arduino IDE (or
`arduino-cli`), select the right board (`esp32:esp32:esp32` for a generic
30-pin dev board -- see `hosting/HOSTING_GUIDE.md` if you're not sure which
one) and the right serial port, and upload the classic blink sketch:

```cpp
void setup() { pinMode(2, OUTPUT); }
void loop() { digitalWrite(2, HIGH); delay(500); digitalWrite(2, LOW); delay(500); }
```

**Working looks like:** the onboard LED (usually on GPIO 2) blinks. This
confirms the board, cable, drivers, and toolchain all work before a single
external component is involved -- if this doesn't work, nothing past this
point will either, and the fix is driver/cable/board related, not logic.

## Rung 1 -- keypad

Wire the 8 keypad pins per `WIRING.md`'s table. Install the `Keypad` library,
then:

```cpp
#include <Keypad.h>
char keys[4][4] = {{'1','2','3','A'},{'4','5','6','B'},{'7','8','9','C'},{'*','0','#','D'}};
uint8_t rowPins[4] = {13, 12, 14, 27};
uint8_t colPins[4] = {26, 25, 33, 32};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, 4, 4);

void setup() { Serial.begin(115200); }
void loop() {
  char k = keypad.getKey();
  if (k) Serial.println(k);
}
```

**Working looks like:** pressing each of the 16 keys prints the matching
character. If a key prints the *wrong* character, see WIRING.md's note on
row/column order -- swap the two relevant wires and retest.

## Rung 2 -- OLED display

Wire the 4 OLED pins. Install `Adafruit SSD1306` and `Adafruit GFX Library`,
then:

```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Wire.begin(21, 22);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { Serial.begin(115200); Serial.println("OLED init failed"); return; }
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("HELLO");
  display.display();
}
void loop() {}
```

**Working looks like:** "HELLO" appears on the screen. If nothing shows up,
the most common cause is a wrong I2C address -- try `0x3D` instead of
`0x3C`, or run an I2C scanner sketch (search "ESP32 I2C scanner", a standard
5-minute Arduino example) to find whatever address your specific board
actually answers to.

## Rung 3 -- servo bolt

Wire the servo (its own 5V supply, shared GND -- see WIRING.md's power
notes). Install `ESP32Servo`, then:

```cpp
#include <ESP32Servo.h>
Servo bolt;
void setup() { bolt.attach(18); }
void loop() {
  bolt.write(0);   delay(1000);   // locked position
  bolt.write(90);  delay(1000);   // unlocked position
}
```

**Working looks like:** the servo horn sweeps back and forth between the two
angles once a second. If it jitters or doesn't move at all, that's almost
always the power problem WIRING.md describes, not a code problem -- check
grounds and the 5V supply first.

## Rung 4 -- PIR, buzzer, LEDs

Wire the PIR sensor, buzzer, and 3 LEDs. This one reuses
`hardware/07-motion-alarm`'s exact wiring pattern -- if you've built that
project already, this rung is nothing new.

```cpp
#define PIR_PIN 4
#define BUZZER_PIN 5
void setup() { pinMode(PIR_PIN, INPUT); pinMode(BUZZER_PIN, OUTPUT); Serial.begin(115200); }
void loop() {
  if (digitalRead(PIR_PIN) == HIGH) {
    Serial.println("motion!");
    tone(BUZZER_PIN, 2000); delay(200); noTone(BUZZER_PIN);
  }
}
```

**Working looks like:** waving a hand in front of the PIR prints "motion!"
and beeps. Most PIR modules have a "hold time" potentiometer -- turn it to
its minimum so the sensor doesn't stay latched HIGH for 10+ seconds after
one trigger, which would make the real lock's intrusion detection feel
broken (it isn't, it's just waiting out the sensor's own hold timer).

## Rung 5 -- WiFi and MQTT

No new wiring -- this rung is purely about the network stack.
Copy `firmware/keypad_door_lock/secrets.h.example` to `secrets.h`
(gitignored) and fill in your WiFi credentials and a unique `DEVICE_ID`.

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi connected");
  mqtt.setServer("broker.hivemq.com", 1883);
}
void loop() {
  if (!mqtt.connected()) {
    String topic = String("doorlock/") + DEVICE_ID + "/event";
    if (mqtt.connect(DEVICE_ID)) {
      mqtt.publish(topic.c_str(), "{\"kind\":\"test\"}");
      Serial.println("published a test event to " + topic);
    }
  }
  mqtt.loop();
  delay(2000);
}
```

**Working looks like:** open [HiveMQ's free public web client](http://www.hivemq.com/demos/websocket-client/),
connect to `broker.hivemq.com`, subscribe to `doorlock/<your DEVICE_ID>/#`,
and watch your test event arrive. This confirms the whole network path --
WiFi, DNS, TCP, MQTT handshake, publish -- works before it's buried inside
the full state machine, where a network problem and a logic problem would
otherwise look identical from the serial monitor.

## Rung 6 -- the whole thing

Now flash the real `firmware/keypad_door_lock/keypad_door_lock.ino`. Every
piece above has already been individually proven, so if something's wrong
now, it's almost certainly in how the pieces are combined (a pin reused for
two purposes, a shared resource like I2C misconfigured) rather than in any
one piece itself.

Walk through the same script `doorlock_sim`'s demo runs
(`python -m doorlock_sim --demo` in `sim/`, after
installing it -- see that folder's README) against the real hardware: wrong
PIN three times and confirm LOCKOUT, wait it out, enter the right PIN and
confirm the bolt turns, trip the PIR while LOCKED and confirm ALARM, and
send a `clear_alarm` command from `webapp/app.py`'s "Live device" tab and
confirm it returns to LOCKED without opening the bolt. If the real device and
the simulator ever disagree on what happens next, that's a real bug in one
of the two -- and worth writing down, the same way this project's AI-track
sibling documented its own Playwright/asyncio bug as a knowledge file instead
of quietly fixing it and moving on.
