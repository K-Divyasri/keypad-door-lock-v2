from doorlock_sim.audit import AuditLog
from doorlock_sim.events import Event


def test_record_appends_events():
    log = AuditLog()
    log.record([Event("unlocked_by_pin"), Event("relocked")])
    assert len(log.entries) == 2
    assert log.count("relocked") == 1
    assert log.count("intrusion") == 0


def test_jsonl_round_trip(tmp_path):
    log = AuditLog()
    log.record([Event("wrong_pin", {"attempts_remaining": 2}), Event("lockout_triggered")])
    path = tmp_path / "events.jsonl"
    log.to_jsonl(path)

    loaded = AuditLog.from_jsonl(path)
    assert len(loaded.entries) == 2
    assert loaded.entries[0].kind == "wrong_pin"
    assert loaded.entries[0].data == {"attempts_remaining": 2}


def test_from_jsonl_missing_file_is_empty(tmp_path):
    loaded = AuditLog.from_jsonl(tmp_path / "does_not_exist.jsonl")
    assert loaded.entries == []


def test_render_table_has_a_row_per_event():
    log = AuditLog()
    log.record([Event("unlocked_by_pin"), Event("wrong_pin", {"attempts_remaining": 1})])
    table = log.render_table()
    lines = table.strip().splitlines()
    assert len(lines) == 2 + 2  # header + separator + 2 rows
    assert "attempts_remaining=1" in table
