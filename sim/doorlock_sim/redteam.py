"""A documented list of security edge cases fired straight at `LockFSM`, PASS/FAIL either way.

Same idea as the AI-engineer track's red-team suites: don't just claim the
lock handles brute force, remote-bypass attempts, and the alarm/unlock
distinction correctly -- write down every case, run it against the real state
machine, and commit the actual table. Every scenario below builds a fresh
`LockFSM`, drives it through a script of key presses / sensor trips / remote
commands, and asserts on the resulting events and end state -- so the whole
suite runs in milliseconds, no hardware, no MQTT broker, no serial port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .lock_fsm import LockConfig, LockFSM, LockState


@dataclass
class Scenario:
    id: str
    category: str
    note: str
    check: Callable[[], tuple[bool, str]]


def _kinds(events) -> list[str]:
    return [e.kind for e in events]


def _brute_force_lockout() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(pin="1234", max_attempts=3))
    events = []
    for _ in range(3):
        events += fsm.type_pin("0000")
    ok = fsm.state == LockState.LOCKOUT and "lockout_triggered" in _kinds(events)
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _lockout_not_remotely_bypassable() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(max_attempts=1))
    fsm.type_pin("0000")  # -> LOCKOUT after one wrong try
    events = fsm.remote_unlock()
    ok = fsm.state == LockState.LOCKOUT and _kinds(events) == ["remote_unlock_denied_lockout"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _keypad_frozen_during_lockout() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(max_attempts=1))
    fsm.type_pin("0000")
    events = fsm.type_pin("1234")  # even the real PIN -- frozen is frozen
    ok = fsm.state == LockState.LOCKOUT and events == []
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _intrusion_while_locked() -> tuple[bool, str]:
    fsm = LockFSM()
    events = fsm.door_opened()
    ok = fsm.state == LockState.ALARM and _kinds(events) == ["intrusion"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _entry_benign_while_unlocked() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.type_pin("1234")
    events = fsm.door_opened()
    ok = fsm.state == LockState.UNLOCKED and _kinds(events) == ["entry_detected"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _wrong_pin_during_alarm_does_nothing() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.door_opened()  # -> ALARM
    events = fsm.type_pin("0000")
    ok = fsm.state == LockState.ALARM and events == []
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _correct_pin_clears_alarm_and_unlocks() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.door_opened()  # -> ALARM
    events = fsm.type_pin("1234")
    ok = (fsm.state == LockState.UNLOCKED and fsm.alarm_reason is None
          and _kinds(events) == ["alarm_cleared_by_pin", "unlocked_by_pin"])
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _remote_clear_alarm_returns_locked_not_unlocked() -> tuple[bool, str]:
    fsm = LockFSM()
    fsm.door_opened()  # -> ALARM
    events = fsm.remote_clear_alarm()
    ok = fsm.state == LockState.LOCKED and _kinds(events) == ["alarm_cleared_remote"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _remote_unlock_from_locked_works() -> tuple[bool, str]:
    fsm = LockFSM()
    events = fsm.remote_unlock()
    ok = fsm.state == LockState.UNLOCKED and _kinds(events) == ["unlocked_remote"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _auto_relock_after_timeout() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(unlock_seconds=5.0))
    fsm.remote_unlock()
    events = fsm.tick(5.1)
    ok = fsm.state == LockState.LOCKED and _kinds(events) == ["relocked"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _lockout_auto_clears_after_timeout() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(max_attempts=1, lockout_seconds=30.0))
    fsm.type_pin("0000")
    events = fsm.tick(30.1)
    ok = (fsm.state == LockState.LOCKED and fsm.attempts_remaining == 1
          and _kinds(events) == ["lockout_cleared"])
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


def _star_clears_entry_buffer() -> tuple[bool, str]:
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.type_pin("999")   # 3 wrong digits, buffer not yet full (pin_length=4)
    fsm.press_key("*")    # wipe it before it becomes a wrong-PIN submit
    events = fsm.type_pin("1234")
    ok = fsm.state == LockState.UNLOCKED and _kinds(events) == ["unlocked_by_pin"]
    return ok, f"state={fsm.state.value}, events={_kinds(events)}"


SCENARIOS: list[Scenario] = [
    Scenario("brute_force_lockout", "lockout",
             "three wrong PINs must trigger a lockout", _brute_force_lockout),
    Scenario("lockout_not_remotely_bypassable", "lockout",
             "a lockout must not be liftable from the app", _lockout_not_remotely_bypassable),
    Scenario("keypad_frozen_during_lockout", "lockout",
             "even the correct PIN does nothing during a lockout", _keypad_frozen_during_lockout),
    Scenario("intrusion_while_locked", "alarm",
             "a door/motion trip while LOCKED is an intrusion", _intrusion_while_locked),
    Scenario("entry_benign_while_unlocked", "alarm",
             "a door/motion trip while UNLOCKED is benign entry, not an alarm", _entry_benign_while_unlocked),
    Scenario("wrong_pin_during_alarm_does_nothing", "alarm",
             "a wrong PIN must not silently clear an active alarm", _wrong_pin_during_alarm_does_nothing),
    Scenario("correct_pin_clears_alarm_and_unlocks", "alarm",
             "the one deliberate exception: a correct PIN clears the alarm and unlocks in one motion",
             _correct_pin_clears_alarm_and_unlocks),
    Scenario("remote_clear_alarm_returns_locked_not_unlocked", "alarm",
             "acknowledging an alarm from the app must not open the door",
             _remote_clear_alarm_returns_locked_not_unlocked),
    Scenario("remote_unlock_from_locked_works", "remote",
             "an ordinary remote unlock must still work", _remote_unlock_from_locked_works),
    Scenario("auto_relock_after_timeout", "timing",
             "an unlocked door must re-lock itself after the timeout", _auto_relock_after_timeout),
    Scenario("lockout_auto_clears_after_timeout", "timing",
             "a lockout must expire and reset the wrong-attempt counter", _lockout_auto_clears_after_timeout),
    Scenario("star_clears_entry_buffer", "keypad",
             "'*' must clear a partial entry instead of it becoming a wrong PIN", _star_clears_entry_buffer),
]


@dataclass
class ScenarioResult:
    scenario: Scenario
    passed: bool
    detail: str


def run_redteam() -> list[ScenarioResult]:
    results = []
    for s in SCENARIOS:
        passed, detail = s.check()
        results.append(ScenarioResult(s, passed, detail))
    return results


def summarize(results: list[ScenarioResult]) -> dict:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    return {"passed": passed, "total": total, "pass_rate": passed / total if total else 0.0}


def render_report(results: list[ScenarioResult]) -> str:
    s = summarize(results)
    lines = [
        "# Red-team report -- keypad door lock state machine",
        "",
        f"**{s['passed']}/{s['total']} handled as expected ({s['pass_rate']:.0%})**",
        "",
        "| id | category | result | note | detail |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"| {r.scenario.id} | {r.scenario.category} | {mark} | {r.scenario.note} | {r.detail} |")
    return "\n".join(lines) + "\n"
