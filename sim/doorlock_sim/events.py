"""The event shape shared by the firmware, the simulator, and the dashboard.

Every meaningful thing the lock does becomes one `Event`, serialized to the exact
same JSON shape whether it comes from the real ESP32 (see
`firmware/keypad_door_lock/events.cpp`) or from `LockFSM` here. That's what lets
`webapp/app.py` display real device events and simulator events with the same
code path -- the wire format is the contract, not the language on either end.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# Every event kind the lock can ever emit. Keep this list in sync with
# firmware/keypad_door_lock/events.h's EventKind comment block by hand -- there's
# no shared build step between C++ and Python here, so a mismatch is a real risk
# worth a code-review checklist item, not just a comment.
EVENT_KINDS = (
    "unlocked_by_pin",
    "wrong_pin",
    "lockout_triggered",
    "lockout_cleared",
    "relocked",
    "intrusion",
    "unlocked_remote",
    "remote_unlock_denied_lockout",
    "alarm_cleared_remote",
    "alarm_cleared_by_pin",
    "entry_detected",
)


@dataclass
class Event:
    kind: str
    data: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"'{self.kind}' is not a known event kind; must be one of {EVENT_KINDS}")
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_json(raw: str) -> "Event":
        d = json.loads(raw)
        return Event(kind=d["kind"], data=d.get("data", {}), timestamp=d.get("timestamp", ""))
