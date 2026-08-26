# Wiring

Pin numbers below match `firmware/keypad_door_lock/config.h` exactly -- if you
wire it differently, change the constants there rather than relying on
memory. GPIO numbers are the ESP32's internal GPIO number (the number
silkscreened next to each pin on most dev boards, sometimes written `Dx` or
`GPIOx` depending on the board).

## Power notes -- read this before wiring anything

An SG90 servo can pull 500mA+ for a brief moment when it starts moving
(the "stall current"). A laptop's USB port, or a cheap USB cable, often can't
supply that on top of what the ESP32 and WiFi radio already draw -- the
symptom is the board randomly resetting or the WiFi dropping the instant the
servo moves. Two ways to avoid this:

1. **Easiest:** power the whole breadboard from a phone charger (5V/1A or
   better) instead of a laptop USB port, using a USB cable cut to bare wires
   or a USB breakout, feeding the breadboard's 5V rail directly.
2. **Also fine:** keep the ESP32 on its own USB cable (for programming and a
   stable 3.3V for logic) and give the servo's 5V and GND their own separate
   supply -- **as long as both supplies share a common GND**. A servo with no
   shared ground with the ESP32 will move erratically or not at all, because
   the PWM signal has no reference voltage to compare against.

Either way: **wire GND everywhere before you wire anything else.** Every
component's GND pin needs to reach the same breadboard rail as the ESP32's
GND.

## Pin table

| Component | Pin | ESP32 GPIO | Notes |
|---|---|---|---|
| Keypad | Row 1 | 13 | |
| Keypad | Row 2 | 12 | |
| Keypad | Row 3 | 14 | |
| Keypad | Row 4 | 27 | |
| Keypad | Col 1 | 26 | |
| Keypad | Col 2 | 25 | |
| Keypad | Col 3 | 33 | |
| Keypad | Col 4 | 32 | Row/col order matters -- see below. |
| SG90 servo | Signal (orange/yellow) | 18 | Must be a PWM-capable pin (most ESP32 GPIOs are). |
| SG90 servo | VCC (red) | 5V rail | Not the ESP32's 3.3V pin -- see power notes above. |
| SG90 servo | GND (brown/black) | GND rail | |
| PIR sensor | OUT | 4 | Digital HIGH while motion is seen. |
| PIR sensor | VCC | 5V rail | Most PIR modules want 5V, not 3.3V -- check yours. |
| PIR sensor | GND | GND rail | |
| Buzzer | + | 5 | |
| Buzzer | - | GND rail | |
| LED (LOCKED, e.g. green) | anode, through a 220Ω resistor | 15 | |
| LED (UNLOCKED, e.g. blue) | anode, through a 220Ω resistor | 2 | |
| LED (ALARM, e.g. red) | anode, through a 220Ω resistor | 19 | |
| All 3 LED cathodes | -- | GND rail | |
| OLED (SSD1306) | SDA | 21 | ESP32's default I2C SDA pin. |
| OLED (SSD1306) | SCL | 22 | ESP32's default I2C SCL pin. |
| OLED (SSD1306) | VCC | 3.3V rail | Most SSD1306 breakout boards want 3.3V, not 5V -- check the silkscreen on yours; some are 5V-tolerant. |
| OLED (SSD1306) | GND | GND rail | |

### Why row/column order matters for the keypad

The `Keypad` library doesn't know which physical wire is "row 1" -- it trusts
the order of the pin array you give it. If your keypad's ribbon cable pins
aren't labeled, you'll need to figure out the mapping once: wire it up
following any order, upload the firmware, and press keys while watching the
serial monitor. If pressing "1" reports "A" instead, your rows or columns are
swapped or reversed -- swap the corresponding two wires (not the whole
row/column arrays) and try again. This is normal and doesn't mean anything
is broken; see `knowledge/02_the_keypad_matrix_scan.md` for why the mapping
can come out scrambled on the first try.

## Multimeter checks before first power-on

Do these with the board **unpowered**, multimeter in continuity/beep mode:

1. **No shorts across the rails.** Touch one probe to the breadboard's + rail
   and the other to its - (GND) rail. It should NOT beep. If it does, a
   component is bridging power to ground somewhere -- find it before
   powering on.
2. **Every GND wire actually reaches the same rail.** Pick a component's GND
   pin and beep it against the ESP32's GND pin. If it doesn't beep, that
   component has no ground reference and will misbehave in ways that look
   like a software bug but aren't.
3. **Resistors are in the LED legs, not bypassed.** An LED wired directly to
   5V/3.3V with no resistor draws far more current than it's rated for and
   will burn out (sometimes instantly, sometimes after a few minutes) --
   cheap insurance to check before power-on.

With the board powered (multimeter in DC voltage mode):

4. Measure across the servo's VCC and GND pins -- should read close to 5V.
   If it reads closer to 3.3V, you've accidentally wired it to the wrong
   rail.
5. Measure the OLED's VCC pin against GND -- should match whatever your
   specific OLED board wants (check its silkscreen).

None of this replaces `labs/`'s software-only exercises, but it catches the
class of bug that no amount of firmware debugging will ever find, because
the problem is upstream of any code running at all.
