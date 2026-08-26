#include "lock_fsm.h"

LockFsm::LockFsm(const char* pin, uint8_t pinLength, uint8_t maxAttempts,
                  unsigned long lockoutMs, unsigned long unlockMs,
                  uint8_t lockedAngle, uint8_t unlockedAngle)
    : _pin(pin), _pinLength(pinLength), _maxAttempts(maxAttempts),
      _lockoutMs(lockoutMs), _unlockMs(unlockMs),
      _lockedAngle(lockedAngle), _unlockedAngle(unlockedAngle) {}

EventList LockFsm::pressKey(char key) {
  EventList events;
  if (_state == LockState::Lockout || _state == LockState::Unlocked) return events;

  if (key == '*') {
    _entry = "";
    return events;
  }
  if (key == '#') {
    return submit_();
  }
  if (isDigit(key)) {
    _entry += key;
    if (_entry.length() >= _pinLength) {
      return submit_();
    }
  }
  return events;
}

EventList LockFsm::submit_() {
  EventList events;
  String entry = _entry;
  _entry = "";
  bool correct = (entry == _pin);

  if (_state == LockState::Alarm) {
    // The one deliberate exception: a valid PIN clears an active intrusion
    // alarm AND unlocks in the same motion -- whoever just typed the real
    // PIN is the legitimate owner arriving home to a lock that's currently
    // screaming.
    if (!correct) return events;
    _wrongAttempts = 0;
    _state = LockState::Unlocked;
    _unlockRemainingMs = (long)_unlockMs;
    events.add(EventKind::AlarmClearedByPin);
    events.add(EventKind::UnlockedByPin);
    return events;
  }

  // _state == LockState::Locked
  if (correct) {
    _wrongAttempts = 0;
    _state = LockState::Unlocked;
    _unlockRemainingMs = (long)_unlockMs;
    events.add(EventKind::UnlockedByPin);
    return events;
  }

  _wrongAttempts++;
  int remaining = (int)_maxAttempts - (int)_wrongAttempts;
  String data = "{\"attempts_remaining\":" + String(remaining > 0 ? remaining : 0) + "}";
  events.add(EventKind::WrongPin, data);
  if (remaining <= 0) {
    _state = LockState::Lockout;
    _lockoutRemainingMs = (long)_lockoutMs;
    String lockoutData = "{\"lockout_ms\":" + String(_lockoutMs) + "}";
    events.add(EventKind::LockoutTriggered, lockoutData);
  }
  return events;
}

EventList LockFsm::doorOpened() {
  EventList events;
  if (_state == LockState::Locked) {
    _state = LockState::Alarm;
    events.add(EventKind::Intrusion);
  } else if (_state == LockState::Unlocked) {
    events.add(EventKind::EntryDetected);
  }
  return events;
}

EventList LockFsm::remoteUnlock() {
  EventList events;
  if (_state == LockState::Lockout) {
    events.add(EventKind::RemoteUnlockDeniedLockout);
    return events;
  }
  if (_state == LockState::Locked || _state == LockState::Alarm) {
    _wrongAttempts = 0;
    _state = LockState::Unlocked;
    _unlockRemainingMs = (long)_unlockMs;
    events.add(EventKind::UnlockedRemote);
  }
  return events;  // already UNLOCKED: no-op
}

EventList LockFsm::remoteClearAlarm() {
  EventList events;
  if (_state == LockState::Alarm) {
    _state = LockState::Locked;
    events.add(EventKind::AlarmClearedRemote);
  }
  return events;
}

EventList LockFsm::tick(unsigned long dtMs) {
  EventList events;
  if (_state == LockState::Unlocked) {
    _unlockRemainingMs -= (long)dtMs;
    if (_unlockRemainingMs <= 0) {
      _state = LockState::Locked;
      events.add(EventKind::Relocked);
    }
  } else if (_state == LockState::Lockout) {
    _lockoutRemainingMs -= (long)dtMs;
    if (_lockoutRemainingMs <= 0) {
      _state = LockState::Locked;
      _wrongAttempts = 0;
      events.add(EventKind::LockoutCleared);
    }
  }
  return events;
}

uint8_t LockFsm::boltAngle() const {
  return _state == LockState::Unlocked ? _unlockedAngle : _lockedAngle;
}

uint8_t LockFsm::attemptsRemaining() const {
  int remaining = (int)_maxAttempts - (int)_wrongAttempts;
  return remaining > 0 ? (uint8_t)remaining : 0;
}
