# Red-team report -- keypad door lock state machine

**12/12 handled as expected (100%)**

| id | category | result | note | detail |
|---|---|---|---|---|
| brute_force_lockout | lockout | PASS | three wrong PINs must trigger a lockout | state=LOCKOUT, events=['wrong_pin', 'wrong_pin', 'wrong_pin', 'lockout_triggered'] |
| lockout_not_remotely_bypassable | lockout | PASS | a lockout must not be liftable from the app | state=LOCKOUT, events=['remote_unlock_denied_lockout'] |
| keypad_frozen_during_lockout | lockout | PASS | even the correct PIN does nothing during a lockout | state=LOCKOUT, events=[] |
| intrusion_while_locked | alarm | PASS | a door/motion trip while LOCKED is an intrusion | state=ALARM, events=['intrusion'] |
| entry_benign_while_unlocked | alarm | PASS | a door/motion trip while UNLOCKED is benign entry, not an alarm | state=UNLOCKED, events=['entry_detected'] |
| wrong_pin_during_alarm_does_nothing | alarm | PASS | a wrong PIN must not silently clear an active alarm | state=ALARM, events=[] |
| correct_pin_clears_alarm_and_unlocks | alarm | PASS | the one deliberate exception: a correct PIN clears the alarm and unlocks in one motion | state=UNLOCKED, events=['alarm_cleared_by_pin', 'unlocked_by_pin'] |
| remote_clear_alarm_returns_locked_not_unlocked | alarm | PASS | acknowledging an alarm from the app must not open the door | state=LOCKED, events=['alarm_cleared_remote'] |
| remote_unlock_from_locked_works | remote | PASS | an ordinary remote unlock must still work | state=UNLOCKED, events=['unlocked_remote'] |
| auto_relock_after_timeout | timing | PASS | an unlocked door must re-lock itself after the timeout | state=LOCKED, events=['relocked'] |
| lockout_auto_clears_after_timeout | timing | PASS | a lockout must expire and reset the wrong-attempt counter | state=LOCKED, events=['lockout_cleared'] |
| star_clears_entry_buffer | keypad | PASS | '*' must clear a partial entry instead of it becoming a wrong PIN | state=UNLOCKED, events=['unlocked_by_pin'] |

