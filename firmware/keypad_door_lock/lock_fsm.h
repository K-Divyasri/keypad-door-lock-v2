#pragma once

#include <Arduino.h>
#include "events.h"

// The lock's brain: a four-state machine, and every failure case named up
// front. This is the C++ twin of sim/doorlock_sim/lock_fsm.py -- same four
// states, same transitions, same event names. See
// ../../knowledge/05_the_lock_state_machine.md for the reasoning behind
// every decision baked into this file.

// A single emitted event, queued for the caller to publish/log/display. The
// FSM never touches MQTT, Serial, or the display directly -- same
// separation as the Python twin: the FSM decides WHAT happened, main .ino
// decides what to DO about it.
struct FsmEvent {
  EventKind kind;
  String data;  // a JSON fragment, "{}" if there's no extra data
};

// At most 2 events come out of any single call (a wrong PIN that also
// triggers a lockout is the only case that produces two).
const uint8_t MAX_EVENTS_PER_CALL = 4;

struct EventList {
  FsmEvent items[MAX_EVENTS_PER_CALL];
  uint8_t count = 0;
  void add(EventKind kind, const String& data = "{}") {
    if (count < MAX_EVENTS_PER_CALL) items[count++] = {kind, data};
  }
};

enum class LockState { Locked, Unlocked, Lockout, Alarm };

class LockFsm {
 public:
  LockFsm(const char* pin, uint8_t pinLength, uint8_t maxAttempts,
          unsigned long lockoutMs, unsigned long unlockMs,
          uint8_t lockedAngle, uint8_t unlockedAngle);

  // ---- the keypad ----------------------------------------------------------
  // '0'-'9' accumulate into the entry buffer; '*' clears it; '#' forces an
  // early submit. Completely frozen during LOCKOUT and ignored while
  // UNLOCKED (already open).
  EventList pressKey(char key);

  // ---- the PIR sensor --------------------------------------------------------
  // A trip is only an intrusion if it happens while LOCKED. A trip while
  // UNLOCKED is just the person who entered a correct PIN walking through.
  EventList doorOpened();

  // ---- the remote commands (from the app, over MQTT) --------------------------
  // Denied outright during LOCKOUT -- a brute-force lockout must not be
  // remotely bypassable. Otherwise behaves like a correct PIN.
  EventList remoteUnlock();

  // Deliberately a DIFFERENT command from unlock. Returns to LOCKED, not
  // UNLOCKED -- acknowledging an alert from the app isn't the same as being
  // physically present to walk through the door.
  EventList remoteClearAlarm();

  // ---- time ------------------------------------------------------------------
  // Advance by dtMs milliseconds -- call this once per loop() with the
  // elapsed time since the last call.
  EventList tick(unsigned long dtMs);

  // ---- what the outside world can observe -------------------------------------
  LockState state() const { return _state; }
  uint8_t boltAngle() const;
  uint8_t attemptsRemaining() const;

 private:
  EventList submit_();

  String _pin;
  uint8_t _pinLength;
  uint8_t _maxAttempts;
  unsigned long _lockoutMs;
  unsigned long _unlockMs;
  uint8_t _lockedAngle;
  uint8_t _unlockedAngle;

  LockState _state = LockState::Locked;
  String _entry;
  uint8_t _wrongAttempts = 0;
  long _unlockRemainingMs = 0;
  long _lockoutRemainingMs = 0;
};
