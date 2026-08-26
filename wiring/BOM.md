# Bill of materials

Everything here is generic and available from any of the usual hobbyist
electronics sellers (Amazon, AliExpress, Adafruit, SparkFun, a local
electronics shop) -- search by the part name, there's no single "correct"
listing to link to. Total cost matches the ~$30 estimate in
`hardware/projects.txt`.

| Part | Notes | Approx. price |
|---|---|---|
| ESP32 dev board | Any 30-pin ESP32-WROOM-32 dev board (the ones with 2 rows of pins that fit a breadboard). Confirm which of its GPIOs are "safe" general-purpose pins before wiring -- some ESP32 boards use certain pins for flash/boot and misbehave if you use them. | ~$8 |
| 4x4 matrix membrane keypad | The flexible flat kind with a ribbon connector, or a hard-button 4x4 keypad module -- either works, wiring is identical (8 pins: 4 rows + 4 columns). | ~$2 |
| SG90 micro servo | The tiny blue hobby servo. This is the bolt actuator. | ~$3 |
| PIR motion sensor (HC-SR501 or similar) | 3 pins: VCC, GND, OUT. Has two onboard potentiometers for sensitivity and pulse-hold time -- turn hold time to its minimum for this project so it doesn't stay "tripped" for tens of seconds. | ~$2 |
| SSD1306 OLED, 128x64, I2C | 4 pins: VCC, GND, SCL, SDA. Confirm it's the I2C variant (4 pins), not SPI (7 pins). | ~$4 |
| Active buzzer module, or a bare piezo buzzer | Active buzzer modules are simpler (just apply voltage); a bare piezo needs `tone()`, which the firmware already uses either way. | ~$1 |
| Breadboard, 830-point (full size) | Smaller boards work but get cramped once the keypad ribbon and OLED are both in place. | ~$3 |
| Jumper wires | A mix of male-male and male-female (female for the keypad ribbon connector if it doesn't end in pins). | ~$3 |
| Resistors, 220Ω x3 | One per status LED, if your LEDs don't come on a pre-wired module. | ~$1 |
| Micro-USB or USB-C cable | Whatever your specific ESP32 board uses -- this is both power and the programming connection. | (often already owned) |
| A separate 5V/1A+ USB power source (phone charger + cable, or a powered USB hub) | Recommended, not strictly required -- see `WIRING.md`'s power notes for why the servo can brown out a board powered only through a laptop's USB port. | ~$5 (often already owned) |

**Total: roughly $25-32**, depending on what you already have lying around.

## What you do NOT need

- No soldering iron is required if everything above is breadboard-friendly
  (it usually is). Soldering header pins onto a bare keypad ribbon is the one
  place you might need one -- see `ASSEMBLY.md`.
- No logic analyzer or oscilloscope for this project (that's project #5 on
  the hardware list, the custom PCB smart plug). A multimeter is enough here.
