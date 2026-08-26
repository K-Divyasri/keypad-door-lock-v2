"""SG90 servo math: turning an angle into the PWM signal that actually moves it.

A hobby servo doesn't take "go to 90 degrees" over a wire -- it takes a 50Hz
square wave whose HIGH pulse width (roughly 500-2400 microseconds) tells the
servo's own internal electronics what angle to hold. `ESP32Servo::write(angle)`
in the firmware does this conversion for you; this file spells it out so you
know what's actually happening on the wire, and so the simulator can report a
bolt angle without ever touching real hardware. See
`knowledge/03_pwm_and_the_servo_bolt.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PWM_FREQUENCY_HZ = 50
PERIOD_US = 1_000_000 // PWM_FREQUENCY_HZ  # 20,000 microseconds


@dataclass
class ServoConfig:
    min_angle: int = 0
    max_angle: int = 180
    min_pulse_us: int = 500
    max_pulse_us: int = 2400


def angle_to_pulse_us(angle: int, config: ServoConfig | None = None) -> int:
    """Linear map from an angle in the servo's range to a pulse width in
    microseconds -- the same formula `ESP32Servo::write()` uses internally."""
    config = config or ServoConfig()
    if not (config.min_angle <= angle <= config.max_angle):
        raise ValueError(f"{angle} is outside [{config.min_angle}, {config.max_angle}]")
    span_angle = config.max_angle - config.min_angle
    span_pulse = config.max_pulse_us - config.min_pulse_us
    fraction = (angle - config.min_angle) / span_angle
    return round(config.min_pulse_us + fraction * span_pulse)


def pulse_us_to_duty_fraction(pulse_us: int) -> float:
    """What fraction of each 20ms period the signal spends HIGH -- what the
    ESP32's `ledc` PWM peripheral actually needs to produce that pulse width
    at 50Hz."""
    return pulse_us / PERIOD_US


@dataclass
class Servo:
    """A simulated SG90. Doesn't move anything -- just tracks the angle it was
    last told to hold, and reports the pulse width / duty cycle that would
    produce it, so a notebook can print real numbers without a breadboard."""

    config: ServoConfig = field(default_factory=ServoConfig)
    angle: int = field(init=False)

    def __post_init__(self) -> None:
        self.angle = self.config.min_angle

    def write(self, angle: int) -> None:
        angle_to_pulse_us(angle, self.config)  # raises if out of range
        self.angle = angle

    @property
    def pulse_us(self) -> int:
        return angle_to_pulse_us(self.angle, self.config)

    @property
    def duty_fraction(self) -> float:
        return pulse_us_to_duty_fraction(self.pulse_us)
