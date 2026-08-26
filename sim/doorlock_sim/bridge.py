"""Optional: puts the simulator on a real MQTT broker, so `webapp/app.py` can
be built, tested, and even hosted before any hardware exists.

Same "offline-by-default, real-optional" shape as the rest of the learning
track: `LockFSM` never needs a network to be correct (see `redteam.py` and
`tests/`), but a door lock's whole point is being controlled remotely, so at
some point something has to actually publish to a broker. `DoorlockBridge` is
that something -- construct it and it drives a real `LockFSM`, publishing
every `Event` to `{prefix}/{device_id}/event` and reacting to commands on
`{prefix}/{device_id}/cmd`, using the exact topic layout
`firmware/keypad_door_lock/main.ino` uses. Point the dashboard at the same
device_id and broker and it can't tell whether it's talking to this bridge or
a real ESP32.

Requires `paho-mqtt` (`pip install "doorlock_sim[mqtt]"`) -- not a core
dependency, so the FSM, keypad, servo, and red-team suite all work with
nothing installed beyond the standard library.
"""

from __future__ import annotations

import time

from .events import Event
from .lock_fsm import LockConfig, LockFSM
from .mqtt_topics import command_topic, event_topic, new_device_id, parse_command, status_topic

DEFAULT_BROKER = "broker.hivemq.com"
DEFAULT_PORT = 1883


class DoorlockBridge:
    def __init__(self, device_id: str | None = None, broker: str = DEFAULT_BROKER,
                 port: int = DEFAULT_PORT, config: LockConfig | None = None):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise ImportError(
                "paho-mqtt is required for live MQTT -- pip install \"doorlock_sim[mqtt]\""
            ) from exc

        self.device_id = device_id or new_device_id()
        self.fsm = LockFSM(config)
        self.broker = broker
        self.port = port
        self._client = mqtt.Client(client_id=f"doorlock-sim-{self.device_id}")
        self._client.will_set(status_topic(self.device_id), payload="offline", retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc) -> None:
        client.subscribe(command_topic(self.device_id))
        client.publish(status_topic(self.device_id), payload="online", retain=True)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            cmd = parse_command(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        events = self.fsm.remote_unlock() if cmd == "unlock" else self.fsm.remote_clear_alarm()
        self._publish_events(events)

    def _publish_events(self, events: list[Event]) -> None:
        for e in events:
            self._client.publish(event_topic(self.device_id), payload=e.to_json())

    def run_forever(self, tick_seconds: float = 1.0) -> None:
        """Connects, then loops forever: advance simulated time, publish
        whatever that produced, sleep, repeat -- while paho's background
        thread handles incoming commands in parallel. Ctrl+C to stop."""
        print(f"device_id={self.device_id} -- point webapp/app.py at this device_id")
        self._client.connect(self.broker, self.port)
        self._client.loop_start()
        try:
            while True:
                time.sleep(tick_seconds)
                self._publish_events(self.fsm.tick(tick_seconds))
        except KeyboardInterrupt:
            pass
        finally:
            self._client.publish(status_topic(self.device_id), payload="offline", retain=True)
            self._client.loop_stop()
            self._client.disconnect()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m doorlock_sim.bridge",
        description="Puts the simulator on a real MQTT broker -- see this module's docstring.",
    )
    parser.add_argument("--device-id", default=None, help="defaults to a random 8-hex-char id")
    parser.add_argument("--broker", default=DEFAULT_BROKER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--pin", default="1234")
    args = parser.parse_args(argv)

    bridge = DoorlockBridge(
        device_id=args.device_id, broker=args.broker, port=args.port,
        config=LockConfig(pin=args.pin),
    )
    bridge.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
