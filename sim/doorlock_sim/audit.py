"""The lock's permanent record -- every Event, in order, written to disk.

Mirrors the AI-engineer track's `browser_agent/audit.py`: nothing in here
decides anything, it only remembers what `LockFSM` already decided. A door
lock's audit trail exists to answer one question -- "who came and went, and
when" -- which is `projects.txt`'s own framing of what this project needs to
prove.
"""

from __future__ import annotations

from pathlib import Path

from .events import Event


class AuditLog:
    def __init__(self) -> None:
        self.entries: list[Event] = []

    def record(self, events: list[Event]) -> None:
        self.entries.extend(events)

    def count(self, kind: str) -> int:
        return sum(1 for e in self.entries if e.kind == kind)

    def to_jsonl(self, path: str | Path) -> None:
        """One JSON object per line -- the standard shape for log shipping,
        and exactly what the real firmware would append to if it had a flash
        filesystem, or what a cloud function would write per MQTT message."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for e in self.entries:
                f.write(e.to_json() + "\n")

    @staticmethod
    def from_jsonl(path: str | Path) -> "AuditLog":
        log = AuditLog()
        path = Path(path)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                log.entries = [Event.from_json(line) for line in f if line.strip()]
        return log

    def render_table(self) -> str:
        lines = ["| timestamp | event | detail |", "|---|---|---|"]
        for e in self.entries:
            detail = ", ".join(f"{k}={v}" for k, v in e.data.items()) if e.data else "-"
            lines.append(f"| {e.timestamp} | {e.kind} | {detail} |")
        return "\n".join(lines)
