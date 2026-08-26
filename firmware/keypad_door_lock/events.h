#pragma once

#include <Arduino.h>

// Every event kind the lock can ever emit. Keep this in sync BY HAND with
// sim/doorlock_sim/events.py's EVENT_KINDS tuple -- there's no shared build
// step between C++ and Python here, so a mismatch is a real risk worth a
// code-review checklist item, not just a comment.
enum class EventKind {
  UnlockedByPin,
  WrongPin,
  LockoutTriggered,
  LockoutCleared,
  Relocked,
  Intrusion,
  UnlockedRemote,
  RemoteUnlockDeniedLockout,
  AlarmClearedRemote,
  AlarmClearedByPin,
  EntryDetected,
};

const char* eventKindName(EventKind kind);

// Builds the exact JSON shape events.py's Event.to_json() produces:
// {"kind": "...", "data": {...}, "timestamp": "..."}. `dataJson` must
// already be valid JSON -- "{}" for no data, or a hand-built fragment like
// "{\"attempts_remaining\":2}". Built with plain string concatenation
// rather than ArduinoJson: the shape is small and fixed, so a JSON library
// buys nothing here. Parsing the *incoming* MQTT command in main .ino is a
// different story -- that payload is untrusted, and that's where
// ArduinoJson actually earns its keep.
String buildEventJson(EventKind kind, const String& dataJson = "{}");
