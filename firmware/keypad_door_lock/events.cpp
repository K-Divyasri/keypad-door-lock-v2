#include "events.h"
#include <time.h>

const char* eventKindName(EventKind kind) {
  switch (kind) {
    case EventKind::UnlockedByPin: return "unlocked_by_pin";
    case EventKind::WrongPin: return "wrong_pin";
    case EventKind::LockoutTriggered: return "lockout_triggered";
    case EventKind::LockoutCleared: return "lockout_cleared";
    case EventKind::Relocked: return "relocked";
    case EventKind::Intrusion: return "intrusion";
    case EventKind::UnlockedRemote: return "unlocked_remote";
    case EventKind::RemoteUnlockDeniedLockout: return "remote_unlock_denied_lockout";
    case EventKind::AlarmClearedRemote: return "alarm_cleared_remote";
    case EventKind::AlarmClearedByPin: return "alarm_cleared_by_pin";
    case EventKind::EntryDetected: return "entry_detected";
  }
  return "unknown";
}

static String isoTimestampNow() {
  // Populated by configTime() in setup() once WiFi is up -- the ESP32 has no
  // battery-backed real-time clock of its own, so "now" only means anything
  // after it's asked an NTP server. Before that sync completes this reads as
  // the 1970 epoch, which only matters for the first second or two after
  // boot. See knowledge/07_wifi_mqtt_and_remote_unlock.md.
  time_t now;
  time(&now);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buf);
}

String buildEventJson(EventKind kind, const String& dataJson) {
  String out = "{\"kind\":\"";
  out += eventKindName(kind);
  out += "\",\"data\":";
  out += dataJson;
  out += ",\"timestamp\":\"";
  out += isoTimestampNow();
  out += "\"}";
  return out;
}
