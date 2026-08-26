from doorlock_sim.lock_fsm import LockConfig, LockFSM, LockState


def test_starts_locked():
    fsm = LockFSM()
    assert fsm.state == LockState.LOCKED
    assert fsm.bolt_angle == fsm.config.locked_angle


def test_correct_pin_unlocks():
    fsm = LockFSM(LockConfig(pin="1234"))
    events = fsm.type_pin("1234")
    assert fsm.state == LockState.UNLOCKED
    assert fsm.bolt_angle == fsm.config.unlocked_angle
    assert [e.kind for e in events] == ["unlocked_by_pin"]


def test_wrong_pin_counts_down_attempts():
    fsm = LockFSM(LockConfig(pin="1234", max_attempts=3))
    events = fsm.type_pin("0000")
    assert fsm.state == LockState.LOCKED
    assert events[0].data["attempts_remaining"] == 2
    assert fsm.attempts_remaining == 2


def test_star_clears_partial_entry():
    fsm = LockFSM(LockConfig(pin="1234", pin_length=4))
    fsm.press_key("9")
    fsm.press_key("9")
    fsm.press_key("*")
    events = fsm.type_pin("1234")
    assert fsm.state == LockState.UNLOCKED
    assert [e.kind for e in events] == ["unlocked_by_pin"]


def test_hash_forces_early_submit():
    fsm = LockFSM(LockConfig(pin="12", pin_length=4))
    fsm.press_key("1")
    fsm.press_key("2")
    events = fsm.press_key("#")
    assert fsm.state == LockState.UNLOCKED
    assert [e.kind for e in events] == ["unlocked_by_pin"]


def test_correct_pin_after_lockout_expires():
    fsm = LockFSM(LockConfig(pin="1234", max_attempts=1, lockout_seconds=10))
    fsm.type_pin("0000")
    assert fsm.state == LockState.LOCKOUT
    fsm.tick(10.0)
    assert fsm.state == LockState.LOCKED
    events = fsm.type_pin("1234")
    assert fsm.state == LockState.UNLOCKED
    assert [e.kind for e in events] == ["unlocked_by_pin"]


def test_unlocked_relocks_after_timeout():
    fsm = LockFSM(LockConfig(pin="1234", unlock_seconds=3))
    fsm.type_pin("1234")
    assert fsm.tick(1.0) == []
    events = fsm.tick(2.5)
    assert fsm.state == LockState.LOCKED
    assert [e.kind for e in events] == ["relocked"]


def test_door_opened_while_unlocked_does_not_relock_or_alarm():
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.type_pin("1234")
    events = fsm.door_opened()
    assert fsm.state == LockState.UNLOCKED
    assert [e.kind for e in events] == ["entry_detected"]


def test_door_opened_while_lockout_or_alarm_is_a_no_op():
    fsm = LockFSM(LockConfig(pin="1234", max_attempts=1))
    fsm.type_pin("0000")
    assert fsm.state == LockState.LOCKOUT
    assert fsm.door_opened() == []

    fsm2 = LockFSM()
    fsm2.door_opened()  # -> ALARM
    assert fsm2.state == LockState.ALARM
    assert fsm2.door_opened() == []


def test_remote_unlock_already_unlocked_is_a_no_op():
    fsm = LockFSM(LockConfig(pin="1234"))
    fsm.type_pin("1234")
    assert fsm.remote_unlock() == []


def test_remote_clear_alarm_only_valid_during_alarm():
    fsm = LockFSM()
    assert fsm.remote_clear_alarm() == []  # LOCKED, nothing to clear yet
    fsm.door_opened()  # -> ALARM
    events = fsm.remote_clear_alarm()
    assert fsm.state == LockState.LOCKED
    assert fsm.alarm_reason is None
    assert [e.kind for e in events] == ["alarm_cleared_remote"]
