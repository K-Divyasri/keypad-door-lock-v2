import pytest

from doorlock_sim.mqtt_topics import (
    build_command,
    command_topic,
    event_topic,
    new_device_id,
    parse_command,
    status_topic,
)


def test_device_id_is_unique_enough():
    ids = {new_device_id() for _ in range(100)}
    assert len(ids) == 100  # no collisions in 100 draws


def test_topics_are_namespaced_under_device_id():
    dev = "abc123"
    assert event_topic(dev) == "doorlock/abc123/event"
    assert command_topic(dev) == "doorlock/abc123/cmd"
    assert status_topic(dev) == "doorlock/abc123/status"


def test_build_and_parse_command_round_trip():
    payload = build_command("unlock")
    assert parse_command(payload) == "unlock"


def test_unknown_command_rejected_both_ways():
    with pytest.raises(ValueError):
        build_command("reboot")
    with pytest.raises(ValueError):
        parse_command('{"cmd": "reboot"}')
