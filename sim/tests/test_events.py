import pytest

from doorlock_sim.events import EVENT_KINDS, Event


def test_valid_kind_gets_a_timestamp():
    e = Event("unlocked_by_pin")
    assert e.kind == "unlocked_by_pin"
    assert e.timestamp  # auto-filled


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        Event("not_a_real_event")


def test_round_trips_through_json():
    e = Event("wrong_pin", {"attempts_remaining": 2})
    e2 = Event.from_json(e.to_json())
    assert e2.kind == e.kind
    assert e2.data == e.data
    assert e2.timestamp == e.timestamp


def test_every_declared_kind_is_constructible():
    for kind in EVENT_KINDS:
        Event(kind)  # must not raise
