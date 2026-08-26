"""doorlock_sim -- a pure-Python twin of the keypad door lock firmware.

Everything the ESP32 firmware in `firmware/keypad_door_lock/` does --
scanning the keypad, running the PIN/lockout/alarm state machine, moving the
servo, publishing events over MQTT -- has a matching module here, so
notebooks, tests, and labs can run the same logic with no breadboard. See
`knowledge/00_START_HERE.md` for the map.
"""

from .events import EVENT_KINDS, Event
from .keypad import KEYS, MatrixKeypad
from .lock_fsm import LockConfig, LockFSM, LockState
from .servo import Servo, ServoConfig, angle_to_pulse_us

__all__ = [
    "Event",
    "EVENT_KINDS",
    "MatrixKeypad",
    "KEYS",
    "LockConfig",
    "LockFSM",
    "LockState",
    "Servo",
    "ServoConfig",
    "angle_to_pulse_us",
]
