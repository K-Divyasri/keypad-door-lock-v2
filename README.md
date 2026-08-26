# Keypad Door Lock v2

A PIN-entry door lock built around an ESP32: a 4x4 matrix keypad, an SG90 servo bolt, a PIR motion sensor, an OLED status display, and WiFi/MQTT for remote unlock and a live event log.

The security logic is a four-state machine (`LOCKED` / `UNLOCKED` / `LOCKOUT` / `ALARM`), implemented twice: once as real C++ firmware for the ESP32, and once as a pure Python package, `doorlock_sim`, with 42 passing unit tests and a 12-scenario red-team suite (currently 12/12). Keeping both in sync means the logic can be learned, tested, and demoed with no hardware at all, while the firmware itself has also been compiled and verified against the real ESP32 toolchain (`arduino-cli compile`, 76% flash used).

## What's real here, and what needs a bench

The lock logic and its test suite, and the firmware's compilation against the ESP32 toolchain, are both verified and repeatable from this repo alone. What still needs a physical board: whether a real keypad, servo, and PIR sensor behave the way `wiring/WIRING.md` and `wiring/ASSEMBLY.md` expect once wired up. Those two documents exist specifically to bring the hardware up one piece at a time rather than all at once.

## Try the simulator (no hardware required)

```powershell
cd sim
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m doorlock_sim --demo
```

```
wrong PIN: state=LOCKED -> wrong_pin
wrong PIN: state=LOCKED -> wrong_pin
wrong PIN -> lockout: state=LOCKOUT -> wrong_pin, lockout_triggered
frozen keypad, even the real PIN: state=LOCKOUT
lockout expires: state=LOCKED -> lockout_cleared
correct PIN: state=UNLOCKED -> unlocked_by_pin
walking through the door: state=UNLOCKED -> entry_detected
auto re-lock: state=LOCKED -> relocked
intruder trips the sensor: state=ALARM -> intrusion
owner clears the alarm from the app: state=LOCKED -> alarm_cleared_remote
```

Run the red-team suite, 12 documented security scenarios fired straight at the state machine (brute-force lockout, a lockout that can't be remotely bypassed, a frozen keypad during lockout, intrusion vs. benign entry, an alarm a wrong PIN can't silently clear, a remote alarm-clear that does not unlock, timed auto-relock and auto-lockout-clear, and more):

```powershell
python -m doorlock_sim --redteam
pytest
```

The committed result is in `sim/REDTEAM_REPORT.md`: 12/12 handled as expected.

## Build and flash the firmware

```powershell
cd firmware/keypad_door_lock
cp secrets.h.example secrets.h  # fill in your WiFi/MQTT details
# open keypad_door_lock.ino in the Arduino IDE, or:
arduino-cli compile --fqbn esp32:esp32:esp32 .
arduino-cli upload -p <PORT> --fqbn esp32:esp32:esp32 .
```

`secrets.h` is git-ignored on purpose; `secrets.h.example` is the committed template.

## Try the dashboard

```powershell
cd webapp
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

A "Try the simulator" tab needs no hardware, a "Live device" tab talks to a real board once one is wired up, and a "Red-team report" tab shows the current suite results.

## Build the physical lock

`wiring/BOM.md`, `wiring/WIRING.md`, and `wiring/ASSEMBLY.md`, in that order: parts list, pin table, and a staged bring-up sequence that brings each piece up on its own before combining them. The full parts list runs to roughly $30.

## Repo layout

```
keypad-door-lock-v2/
├── firmware/keypad_door_lock/   real C++ firmware for the ESP32
├── sim/doorlock_sim/            the tested Python twin of the lock logic
├── webapp/                      Streamlit dashboard (simulator, live device, red-team report)
├── wiring/                      BOM, wiring table, staged assembly guide
└── hosting/                     CI workflow and hosting guide for the dashboard
```

## Hosting

See `hosting/HOSTING_GUIDE.md`. A GitHub Actions workflow re-runs the simulator's tests, the red-team suite, and a firmware compile check on every push, and the Streamlit dashboard can be deployed to Streamlit Community Cloud or a Hugging Face Space.
