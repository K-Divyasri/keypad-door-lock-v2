"""A web dashboard for the keypad door lock, built with Streamlit.

    streamlit run app.py

Three tabs:

- **Try the simulator** -- drives a real `LockFSM` entirely in this process,
  no hardware and no broker required. This is the tab a visitor with no ESP32
  sees when you host this app -- same "offline-by-default" idea as the rest of
  this learning track: the core logic is provable without any real device.
- **Live device** -- connects to a real MQTT broker (the same one the
  firmware or `doorlock_sim.bridge.DoorlockBridge` publishes to) and shows
  whatever device is running under the `device_id` you type in, live. Works
  identically whether that device is a real ESP32 or the bridge simulator --
  the wire format is the contract.
- **Red-team report** -- runs the documented security-scenario suite against
  the FSM and shows the pass/fail table.
"""

from __future__ import annotations

import os
import sys
import threading
import time

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))

from doorlock_sim.lock_fsm import LockConfig, LockFSM, LockState  # noqa: E402
from doorlock_sim.mqtt_topics import (  # noqa: E402
    build_command,
    command_topic,
    event_topic,
    status_topic,
)
from doorlock_sim.redteam import render_report, run_redteam  # noqa: E402

st.set_page_config(page_title="Keypad Door Lock Dashboard", page_icon="🔐")
st.title("🔐 Keypad Door Lock Dashboard")
st.caption(
    "PIN entry, servo bolt, PIR intrusion alarm, lockout, and WiFi/MQTT remote "
    "unlock -- physical build of the 'Ladder C' spec, with a Python simulator "
    "twin standing in for the real ESP32."
)

tab_sim, tab_live, tab_redteam = st.tabs(["Try the simulator", "Live device", "Red-team report"])

# ---- Try the simulator -------------------------------------------------------

with tab_sim:
    st.write("No hardware needed -- this drives a real `LockFSM` right here in the browser tab.")

    if "fsm" not in st.session_state:
        st.session_state.fsm = LockFSM(LockConfig(pin="1234"))
        st.session_state.log = []

    fsm: LockFSM = st.session_state.fsm

    def _do(events_fn) -> None:
        events = events_fn()
        st.session_state.log = st.session_state.log + [
            {"kind": e.kind, "data": e.data} for e in events
        ]

    st.subheader(f"State: {fsm.state.value}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Bolt angle", f"{fsm.bolt_angle}°")
    c2.metric("Attempts left", fsm.attempts_remaining)
    c3.metric("Events logged", len(st.session_state.log))

    st.write("**Keypad** (default PIN is `1234`)")
    rows = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
    for row in rows:
        cols = st.columns(3)
        for col, key in zip(cols, row):
            if col.button(key, key=f"key_{key}", width="stretch"):
                _do(lambda k=key: fsm.press_key(k))

    st.write("**Sensors and remote commands**")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("🚪 Door/PIR trip"):
        _do(fsm.door_opened)
    if b2.button("📱 Remote unlock"):
        _do(fsm.remote_unlock)
    if b3.button("📱 Clear alarm"):
        _do(fsm.remote_clear_alarm)
    if b4.button("⏱️ Advance 5s"):
        _do(lambda: fsm.tick(5.0))

    if st.button("Reset lock"):
        st.session_state.fsm = LockFSM(LockConfig(pin="1234"))
        st.session_state.log = []
        st.rerun()

    if st.session_state.log:
        st.write("**Event log**")
        st.dataframe(pd.DataFrame(st.session_state.log), width="stretch", hide_index=True)

# ---- Live device --------------------------------------------------------------

with tab_live:
    st.write(
        "Point this at a real device's `device_id` -- either the ESP32 firmware "
        "or `python -m doorlock_sim.bridge` -- to watch its actual event stream "
        "and send it real commands."
    )

    try:
        import paho.mqtt.client as mqtt
        mqtt_available = True
    except ImportError:
        mqtt_available = False
        st.info("Install `paho-mqtt` to enable this tab: `pip install paho-mqtt`.")

    if mqtt_available:
        broker = st.text_input("Broker", value="broker.hivemq.com")
        device_id = st.text_input("Device ID", value="")

        if "live_events" not in st.session_state:
            st.session_state.live_events = []
            st.session_state.live_status = "unknown"
            st.session_state.live_client = None
            st.session_state.live_device = None

        def _connect(broker: str, device_id: str) -> None:
            def on_message(client, userdata, msg) -> None:
                if msg.topic == status_topic(device_id):
                    st.session_state.live_status = msg.payload.decode("utf-8")
                else:
                    st.session_state.live_events.append(msg.payload.decode("utf-8"))

            client = mqtt.Client()
            client.on_message = on_message
            client.connect(broker, 1883)
            client.subscribe(event_topic(device_id))
            client.subscribe(status_topic(device_id))
            threading.Thread(target=client.loop_forever, daemon=True).start()
            st.session_state.live_client = client
            st.session_state.live_device = device_id

        if device_id and st.session_state.live_device != device_id:
            if st.session_state.live_client:
                st.session_state.live_client.disconnect()
            st.session_state.live_events = []
            _connect(broker, device_id)
            st.success(f"Subscribed to doorlock/{device_id}/#")

        if st.session_state.live_device:
            st.metric("Device status", st.session_state.live_status)
            lc1, lc2 = st.columns(2)
            if lc1.button("📱 Send: unlock"):
                st.session_state.live_client.publish(
                    command_topic(st.session_state.live_device), build_command("unlock")
                )
            if lc2.button("📱 Send: clear_alarm"):
                st.session_state.live_client.publish(
                    command_topic(st.session_state.live_device), build_command("clear_alarm")
                )
            st.write(f"**{len(st.session_state.live_events)} events received**")
            for raw in reversed(st.session_state.live_events[-25:]):
                st.code(raw, language="json")
            time.sleep(1)
            st.rerun()

# ---- Red-team report ------------------------------------------------------------

with tab_redteam:
    st.write("Every documented security edge case, run straight against the FSM.")
    results = run_redteam()
    passed = sum(1 for r in results if r.passed)
    st.metric("Handled as expected", f"{passed}/{len(results)}", f"{passed / len(results):.0%}")
    rows = [
        {"id": r.scenario.id, "category": r.scenario.category,
         "result": "PASS" if r.passed else "FAIL", "note": r.scenario.note}
        for r in results
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    with st.expander("Raw report"):
        st.code(render_report(results), language="markdown")
