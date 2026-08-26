"""The lock's brain: a four-state machine, and every failure case named up front.

`projects.txt`'s own framing of this project is the design spec: "Security logic
is all about the failure cases. What happens on the third wrong PIN? What if
someone opens the door without a valid code? How long does the bolt stay open?
Can the alarm be cleared, and by whom?" This file answers every one of those
questions in code, and the answers are deliberate design decisions -- see
`knowledge/05_the_lock_state_machine.md` for the reasoning behind each one.

This is the Python twin of `firmware/keypad_door_lock/lock_fsm.cpp`. Same four
states, same transitions, same event names -- so learning this file is learning
the real firmware's logic, just without a breadboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .events import Event


class LockState(str, Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    LOCKOUT = "LOCKOUT"
    ALARM = "ALARM"


@dataclass
class LockConfig:
    pin: str = "1234"
    pin_length: int = 4
    max_attempts: int = 3
    lockout_seconds: float = 30.0
    unlock_seconds: float = 5.0
    locked_angle: int = 0
    unlocked_angle: int = 90


class LockFSM:
    """Call `press_key`, `door_opened`, `remote_unlock`, `remote_clear_alarm`, and
    `tick` to drive it. Every one of those returns the list of `Event`s it caused
    -- possibly empty -- which is the entire audit trail of this lock's life."""

    def __init__(self, config: LockConfig | None = None):
        self.config = config or LockConfig()
        self.state = LockState.LOCKED
        self.alarm_reason: str | None = None
        self._entry = ""
        self._wrong_attempts = 0
        self._unlock_remaining = 0.0
        self._lockout_remaining = 0.0

    # ---- the keypad ------------------------------------------------------ #

    def press_key(self, key: str) -> list[Event]:
        """'0'-'9' accumulate into the entry buffer; '*' clears it; '#' forces
        an early submit. The keypad is completely frozen during LOCKOUT --
        not just ignored input, no reaction of any kind -- and typing does
        nothing while UNLOCKED (already open) either."""
        if self.state in (LockState.LOCKOUT, LockState.UNLOCKED):
            return []

        if key == "*":
            self._entry = ""
            return []

        if key == "#":
            return self._submit()

        if key.isdigit():
            self._entry += key
            if len(self._entry) >= self.config.pin_length:
                return self._submit()
        return []

    def type_pin(self, digits: str) -> list[Event]:
        """Convenience for tests and notebooks: press a whole string of keys."""
        events: list[Event] = []
        for ch in digits:
            events += self.press_key(ch)
        return events

    def _submit(self) -> list[Event]:
        entry, self._entry = self._entry, ""
        correct = entry == self.config.pin

        if self.state == LockState.ALARM:
            # The one deliberate exception: a valid PIN clears an active
            # intrusion alarm AND unlocks in the same motion, on the theory
            # that whoever just typed the real PIN is the legitimate owner
            # arriving home to a lock that's currently screaming.
            if not correct:
                return []
            self.alarm_reason = None
            self._wrong_attempts = 0
            self.state = LockState.UNLOCKED
            self._unlock_remaining = self.config.unlock_seconds
            return [Event("alarm_cleared_by_pin"), Event("unlocked_by_pin")]

        # state == LOCKED
        if correct:
            self._wrong_attempts = 0
            self.state = LockState.UNLOCKED
            self._unlock_remaining = self.config.unlock_seconds
            return [Event("unlocked_by_pin")]

        self._wrong_attempts += 1
        remaining = self.config.max_attempts - self._wrong_attempts
        events = [Event("wrong_pin", {"attempts_remaining": max(remaining, 0)})]
        if remaining <= 0:
            self.state = LockState.LOCKOUT
            self._lockout_remaining = self.config.lockout_seconds
            events.append(Event("lockout_triggered", {"lockout_seconds": self.config.lockout_seconds}))
        return events

    # ---- the PIR sensor ---------------------------------------------------#

    def door_opened(self) -> list[Event]:
        """A door/motion trip is only an intrusion if it happens while LOCKED
        -- nobody was supposed to be opening the door. A trip while UNLOCKED
        is just the person who just entered a correct PIN walking through,
        logged as ordinary entry, not an alarm."""
        if self.state == LockState.LOCKED:
            self.state = LockState.ALARM
            self.alarm_reason = "intrusion"
            return [Event("intrusion")]
        if self.state == LockState.UNLOCKED:
            return [Event("entry_detected")]
        return []

    # ---- the remote commands (from the app, over MQTT) --------------------#

    def remote_unlock(self) -> list[Event]:
        """Denied outright during LOCKOUT -- see
        knowledge/05_the_lock_state_machine.md for why a brute-force lockout
        must not be remotely bypassable. Otherwise behaves like a correct PIN:
        unlocks from LOCKED, and clears+unlocks from ALARM."""
        if self.state == LockState.LOCKOUT:
            return [Event("remote_unlock_denied_lockout")]
        if self.state in (LockState.LOCKED, LockState.ALARM):
            self.alarm_reason = None
            self._wrong_attempts = 0
            self.state = LockState.UNLOCKED
            self._unlock_remaining = self.config.unlock_seconds
            return [Event("unlocked_remote")]
        return []  # already UNLOCKED

    def remote_clear_alarm(self) -> list[Event]:
        """Deliberately a DIFFERENT command from unlock. Clearing an alarm
        remotely returns the lock to LOCKED, not UNLOCKED -- acknowledging an
        alert from your phone isn't the same as being physically present to
        walk through the door."""
        if self.state == LockState.ALARM:
            self.alarm_reason = None
            self.state = LockState.LOCKED
            return [Event("alarm_cleared_remote")]
        return []

    # ---- time -------------------------------------------------------------#

    def tick(self, dt_seconds: float) -> list[Event]:
        """Advance simulated time by `dt_seconds`. The real firmware calls the
        equivalent of this every loop() iteration using millis(); tests and
        notebooks call it with whatever dt they like, so a 30-second lockout
        is one line to test, not a real 30-second wait."""
        if self.state == LockState.UNLOCKED:
            self._unlock_remaining -= dt_seconds
            if self._unlock_remaining <= 0:
                self.state = LockState.LOCKED
                return [Event("relocked")]
        elif self.state == LockState.LOCKOUT:
            self._lockout_remaining -= dt_seconds
            if self._lockout_remaining <= 0:
                self.state = LockState.LOCKED
                self._wrong_attempts = 0
                return [Event("lockout_cleared")]
        return []

    # ---- what the outside world can observe -------------------------------#

    @property
    def bolt_angle(self) -> int:
        """What angle the servo should be at right now. Only UNLOCKED opens
        the bolt -- ALARM and LOCKOUT both keep it firmly shut."""
        return self.config.unlocked_angle if self.state == LockState.UNLOCKED else self.config.locked_angle

    @property
    def attempts_remaining(self) -> int:
        return max(self.config.max_attempts - self._wrong_attempts, 0)
