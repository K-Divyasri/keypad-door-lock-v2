"""The MQTT topic layout the firmware, the simulator, and the dashboard all
agree on -- and the one real gotcha with using a public broker.

Public brokers like HiveMQ's (`broker.hivemq.com:1883`) are free and need no
account, which is perfect for a portfolio project -- and also mean everyone
else building a door-lock tutorial this month is publishing to the exact same
broker. If two devices both publish to `doorlock/event`, your dashboard shows
a stranger's lock. The fix is namespacing every topic under a `device_id`
that's actually unique -- see `new_device_id()` below -- not a clever protocol
trick, just "don't collide with strangers." See
`knowledge/07_wifi_mqtt_and_remote_unlock.md`.
"""

from __future__ import annotations

import json
import secrets

TOPIC_PREFIX = "doorlock"

# The only two commands the lock will ever accept over MQTT. Deliberately not
# a generic "run this" channel -- a narrow, closed command vocabulary is part
# of the security design, not an accident.
COMMANDS = ("unlock", "clear_alarm")


def new_device_id() -> str:
    """8 random hex characters -- good enough entropy that two people running
    this project the same week won't collide on a shared public broker."""
    return secrets.token_hex(4)


def event_topic(device_id: str) -> str:
    """Device -> cloud: every Event the lock produces gets published here."""
    return f"{TOPIC_PREFIX}/{device_id}/event"


def command_topic(device_id: str) -> str:
    """Cloud -> device: the dashboard publishes remote commands here, and the
    firmware/simulator subscribes."""
    return f"{TOPIC_PREFIX}/{device_id}/cmd"


def status_topic(device_id: str) -> str:
    """Retained "online"/"offline", set as an MQTT Last Will and Testament --
    so the dashboard can tell "device is disconnected" apart from "device is
    connected but quiet"."""
    return f"{TOPIC_PREFIX}/{device_id}/status"


def build_command(cmd: str) -> str:
    if cmd not in COMMANDS:
        raise ValueError(f"'{cmd}' is not a known command; must be one of {COMMANDS}")
    return json.dumps({"cmd": cmd})


def parse_command(payload: str) -> str:
    d = json.loads(payload)
    cmd = d.get("cmd")
    if cmd not in COMMANDS:
        raise ValueError(f"'{cmd}' is not a known command; must be one of {COMMANDS}")
    return cmd
