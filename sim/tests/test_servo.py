import pytest

from doorlock_sim.servo import (
    PERIOD_US,
    Servo,
    ServoConfig,
    angle_to_pulse_us,
    pulse_us_to_duty_fraction,
)


def test_min_angle_gives_min_pulse():
    assert angle_to_pulse_us(0) == 500


def test_max_angle_gives_max_pulse():
    assert angle_to_pulse_us(180) == 2400


def test_midpoint_is_halfway_between():
    assert angle_to_pulse_us(90) == pytest.approx(1450, abs=1)


def test_out_of_range_angle_rejected():
    with pytest.raises(ValueError):
        angle_to_pulse_us(200)


def test_duty_fraction_is_pulse_over_period():
    assert pulse_us_to_duty_fraction(PERIOD_US) == 1.0
    assert pulse_us_to_duty_fraction(0) == 0.0


def test_servo_starts_at_min_angle():
    s = Servo()
    assert s.angle == 0
    assert s.pulse_us == 500


def test_servo_write_moves_it():
    s = Servo()
    s.write(90)
    assert s.angle == 90
    assert s.pulse_us == angle_to_pulse_us(90)


def test_servo_respects_custom_config():
    cfg = ServoConfig(min_angle=0, max_angle=90, min_pulse_us=1000, max_pulse_us=2000)
    s = Servo(config=cfg)
    s.write(90)
    assert s.pulse_us == 2000
