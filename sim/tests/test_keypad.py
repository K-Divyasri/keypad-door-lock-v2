import pytest

from doorlock_sim.keypad import KEYS, MatrixKeypad


def test_layout_is_4x4():
    assert len(KEYS) == 4
    assert all(len(row) == 4 for row in KEYS)


def test_press_key_by_row_col():
    kp = MatrixKeypad(debounce_ticks=1)
    kp.press(0, 0)
    assert kp.scan() == "1"


def test_press_key_by_character():
    kp = MatrixKeypad(debounce_ticks=1)
    kp.press_key("5")
    assert kp.scan() == "5"


def test_unknown_character_rejected():
    kp = MatrixKeypad()
    with pytest.raises(ValueError):
        kp.press_key("Z")


def test_out_of_range_position_rejected():
    kp = MatrixKeypad()
    with pytest.raises(ValueError):
        kp.press(4, 0)


def test_debounce_requires_stable_ticks():
    kp = MatrixKeypad(debounce_ticks=3)
    kp.press_key("7")
    assert kp.scan() is None  # tick 1
    assert kp.scan() is None  # tick 2
    assert kp.scan() == "7"   # tick 3 -- now stable


def test_held_key_does_not_repeat():
    kp = MatrixKeypad(debounce_ticks=1)
    kp.press_key("9")
    assert kp.scan() == "9"
    assert kp.scan() is None  # still held -- no repeat fire
    assert kp.scan() is None


def test_release_and_repress_fires_again():
    kp = MatrixKeypad(debounce_ticks=1)
    kp.press_key("9")
    assert kp.scan() == "9"
    kp.release()
    assert kp.scan() is None
    kp.press_key("9")
    assert kp.scan() == "9"


def test_no_press_returns_none():
    kp = MatrixKeypad()
    assert kp.scan() is None
