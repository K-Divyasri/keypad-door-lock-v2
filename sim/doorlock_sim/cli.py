"""A terminal front-end for `LockFSM` -- press keys, watch state, no hardware required.

Three ways to run it (from `sim/`, after `pip install -e .`):

    python -m doorlock_sim                interactive: type digits + Enter,
                                           or one of the control words below
    python -m doorlock_sim --demo         a scripted walkthrough of every state
    python -m doorlock_sim --redteam      run the red-team suite, print the table

Interactive control words (typed instead of digits): `open` (simulate the
PIR/door sensor tripping), `unlock` (remote unlock, as if sent from the app
over MQTT), `clear` (remote clear-alarm), `tick N` (advance N seconds of
simulated time), `quit`.
"""

from __future__ import annotations

import argparse
import sys

from .audit import AuditLog
from .lock_fsm import LockConfig, LockFSM
from .redteam import render_report, run_redteam


def _print_events(events) -> None:
    for e in events:
        print(f"  -> {e.kind}" + (f" {e.data}" if e.data else ""))


def run_interactive() -> None:
    fsm = LockFSM()
    log = AuditLog()
    print("Keypad door lock simulator. State:", fsm.state.value)
    print("Type digits (e.g. 1234), or: open | unlock | clear | tick N | quit")
    while True:
        try:
            line = input(f"[{fsm.state.value}] > ").strip()
        except EOFError:
            break
        if not line or line == "quit":
            break
        if line == "open":
            events = fsm.door_opened()
        elif line == "unlock":
            events = fsm.remote_unlock()
        elif line == "clear":
            events = fsm.remote_clear_alarm()
        elif line.startswith("tick"):
            parts = line.split()
            seconds = float(parts[1]) if len(parts) > 1 else 1.0
            events = fsm.tick(seconds)
        else:
            events = fsm.type_pin(line)
        log.record(events)
        _print_events(events)
        print(f"  state={fsm.state.value} bolt_angle={fsm.bolt_angle}")
    print(f"\n{len(log.entries)} events recorded this session.")


def run_demo() -> None:
    """A scripted walkthrough touching every state, printed step by step --
    useful for a README screenshot or a quick sanity check with no typing."""
    fsm = LockFSM(LockConfig(pin="1234", max_attempts=3, lockout_seconds=5, unlock_seconds=5))
    script = [
        ("wrong PIN", lambda: fsm.type_pin("0000")),
        ("wrong PIN", lambda: fsm.type_pin("1111")),
        ("wrong PIN -> lockout", lambda: fsm.type_pin("2222")),
        ("frozen keypad, even the real PIN", lambda: fsm.type_pin("1234")),
        ("lockout expires", lambda: fsm.tick(5.1)),
        ("correct PIN", lambda: fsm.type_pin("1234")),
        ("walking through the door", lambda: fsm.door_opened()),
        ("auto re-lock", lambda: fsm.tick(5.1)),
        ("intruder trips the sensor", lambda: fsm.door_opened()),
        ("owner clears the alarm from the app", lambda: fsm.remote_clear_alarm()),
    ]
    for label, step in script:
        events = step()
        print(f"{label}: state={fsm.state.value}", end="")
        if events:
            print(" ->", ", ".join(e.kind for e in events))
        else:
            print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doorlock_sim", description=__doc__)
    parser.add_argument("--redteam", action="store_true", help="run the red-team suite")
    parser.add_argument("--demo", action="store_true", help="run a scripted walkthrough")
    args = parser.parse_args(argv)

    if args.redteam:
        results = run_redteam()
        print(render_report(results))
        return 0 if all(r.passed for r in results) else 1

    if args.demo:
        run_demo()
        return 0

    run_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
