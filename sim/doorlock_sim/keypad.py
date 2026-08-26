"""Simulates a 4x4 matrix keypad the exact way the firmware scans one.

A matrix keypad doesn't wire every button to its own pin -- 16 buttons share
just 8 (4 rows + 4 columns). The scan trick: drive one row LOW at a time, read
all four columns, and whichever column reads LOW tells you which button on
that row is pressed. `MatrixKeypad.scan()` below does exactly that against a
simulated grid, so learning this file is learning what the Arduino `Keypad`
library is doing for you every `loop()` iteration -- see
`knowledge/02_the_keypad_matrix_scan.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The layout etched onto the keypad -- same 4x4 grid whether it's simulated
# here or wired for real in firmware/keypad_door_lock/config.h.
KEYS = (
    ("1", "2", "3", "A"),
    ("4", "5", "6", "B"),
    ("7", "8", "9", "C"),
    ("*", "0", "#", "D"),
)


@dataclass
class MatrixKeypad:
    """A stand-in for the real keypad hardware. Call `press(row, col)` /
    `release()` to simulate a finger, and `scan()` to read whatever the scan
    algorithm currently sees -- including debounce, so a bouncing contact (or
    a test that calls scan() every millisecond) doesn't register ten presses
    for one touch.
    """

    debounce_ticks: int = 3
    _pressed_rc: tuple[int, int] | None = field(default=None, init=False)
    _stable_ticks: int = field(default=0, init=False)
    _last_reported: str | None = field(default=None, init=False)

    def press(self, row: int, col: int) -> None:
        """Simulates a finger landing on physical position (row, col)."""
        if not (0 <= row < 4 and 0 <= col < 4):
            raise ValueError(f"({row}, {col}) is outside the 4x4 grid")
        self._pressed_rc = (row, col)

    def press_key(self, key: str) -> None:
        """Same as press(), but by the character printed on the button."""
        for r, row in enumerate(KEYS):
            for c, k in enumerate(row):
                if k == key:
                    self.press(r, c)
                    return
        raise ValueError(f"'{key}' is not on the keypad")

    def release(self) -> None:
        self._pressed_rc = None

    def scan(self) -> str | None:
        """One pass of the row-drive / column-read algorithm. Returns the key
        character the instant a press becomes debounced-stable, then returns
        None for that same held-down key until it's released and pressed
        again -- exactly like the real library, so holding a key down doesn't
        spam '5' into the entry buffer sixty times a second."""
        if self._pressed_rc is None:
            self._stable_ticks = 0
            self._last_reported = None
            return None

        self._stable_ticks += 1
        row, col = self._pressed_rc
        key = KEYS[row][col]

        if self._stable_ticks >= self.debounce_ticks and self._last_reported != key:
            self._last_reported = key
            return key
        return None
