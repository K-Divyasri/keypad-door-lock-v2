# Publishing the Keypad Door Lock v2 project

This project has three things worth shipping separately:

1. The **source** on GitHub, with CI proving the simulator's tests and
   red-team suite still pass, and the real firmware still compiles, on
   every push -- the part that matters most in an interview, because it's
   evidence, not a claim.
2. The **dashboard** (`webapp/app.py`) running somewhere public, so anyone
   can try the simulator tab live with nothing installed.
3. The **real firmware**, flashed onto an actual ESP32 -- this one isn't
   "hosted" anywhere; see the note at the bottom of this guide.

Do them in that order. A repo with green CI and a working simulator is
worth having even before you've soldered anything.

Everything below assumes you're working from
the repo root -- the folder containing `firmware/`,
`sim/`, `webapp/`, `wiring/`, and this `hosting/` folder.
That whole folder is what becomes the GitHub repo.

---

## Step 1 -- Get it on GitHub

If you've never used Git before, the "Step 0" section of
`ai/01-data-detective/hosting/HOSTING_GUIDE.md` (on the AI-engineer track)
walks through installing Git, making a GitHub account, and telling Git who
you are. From here on this guide assumes `git --version` already works.

### 1a. Check what must never be committed

Open `.gitignore` and confirm it has at least:

```
firmware/keypad_door_lock/secrets.h
webapp/.env
**/.venv/
**/__pycache__/
**/*.egg-info/
**/.pytest_cache/
```

The line that matters most is `secrets.h`. If you ever flashed the real
firmware, you put your real WiFi password into
`firmware/keypad_door_lock/secrets.h`. That file is
gitignored on purpose -- the repo ships `secrets.h.example` instead
(variable names, no real values), and that's the one meant to be
committed. **If a real `secrets.h` ever shows up in `git status`, stop and
fix your `.gitignore` before committing anything.**

### 1b. Init, commit, push

From the repo root:

```powershell
git init
git add .
git commit -m "Keypad door lock v2: firmware, simulator, notebooks, labs, docs"
```

Then check the single most important thing before you push anything
anywhere:

```powershell
git status
```

You want `nothing to commit, working tree clean`, and you must **not** see
a real `secrets.h` listed. If it shows up, stop and fix it now.

Create an empty repo on github.com (name it something like
`keypad-door-lock-v2`, public, and **don't** tick "Add a README" or "Add
.gitignore" -- you already have both). Then:

```powershell
git branch -M main
git remote add origin https://github.com/YOURNAME/keypad-door-lock-v2.git
git push -u origin main
```

Refresh the repo page. You should see `firmware/`, `sim/`, `webapp/`,
`wiring/`, `hosting/`, this project's `README.md`, and
`.gitignore`.

---

## Step 2 -- Add CI as a ship gate

The workflow at `hosting/github_actions/ci.yml` runs two independent jobs
on every push and pull request, since there's no way to flash real
hardware inside a CI runner:

- **`sim-tests`** -- installs `doorlock_sim`, runs the full 42-test pytest
  suite, then runs the 12-scenario red-team suite standalone as the ship
  gate (`python -m doorlock_sim --redteam` exits `1` if any scenario stops
  behaving as documented).
- **`firmware-compile`** -- installs `arduino-cli`, the ESP32 core, and
  every library the firmware needs, then compiles the real
  `keypad_door_lock.ino` against the real `esp32:esp32:esp32` target. This
  can't prove the firmware behaves correctly on a real board, but it does
  prove it still *builds* -- which catches the class of regression ("I
  renamed a function and forgot to update one call site") that would
  otherwise only surface the next time someone tries to flash a board.

Concretely: without the `sim-tests` job, "a lockout can't be bypassed
remotely" is true today and could quietly stop being true after someone
edits `lock_fsm.py` to fix an unrelated bug and accidentally removes the
`LOCKOUT` check in `remote_unlock()`. Nobody would notice until a real
attack (or a curious code reviewer) found the gap. With this job, that same
edit makes the very next push go red, with a table showing exactly which
scenario, `lockout_not_remotely_bypassable`, started failing.

### Install it

```powershell
mkdir .github\workflows
copy hosting\github_actions\ci.yml .github\workflows\ci.yml
git add .github\workflows\ci.yml
git commit -m "Add CI: sim tests + red-team suite, and a firmware compile check"
git push
```

Go to the repo's **Actions** tab and watch both jobs run. The
`firmware-compile` job takes noticeably longer than `sim-tests` the first
time (installing the ESP32 core is a real, if one-time-per-run, download) --
that's expected, same as Playwright's Chromium install adds time to the
AI-engineer track's browser-automation project.

To *see* the gate work, try breaking something on purpose in a scratch
branch -- comment out the `LockState.LOCKOUT` check at the top of
`remote_unlock()` in `sim/doorlock_sim/lock_fsm.py`, push, and watch the
red-team step go red with
`lockout_not_remotely_bypassable ... FAIL` in the log. Then revert it.

---

## Step 3 -- Deploy the dashboard

Unlike the AI-engineer track's browser-automation project (which needs a
real headless Chromium and therefore a Docker-based host), `webapp/app.py`
needs nothing heavier than Python plus two optional pure-Python libraries
-- so a plain Streamlit-native host works fine. Two good, free options:

### Option A -- Streamlit Community Cloud (simplest)

1. Push your repo to GitHub (Step 1, above) if you haven't already.
2. Go to [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
   and sign in with GitHub.
3. Click **New app**, pick your repo and the `main` branch, and set the
   main file path to `webapp/app.py`.
4. Deploy. Streamlit Cloud installs
   `webapp/requirements.txt` automatically and starts
   the app.

The "Try the simulator" and "Red-team report" tabs work immediately with
zero configuration. The "Live device" tab works too, the moment a visitor
(or you) types in a `device_id` that something is actually publishing to.

### Option B -- Hugging Face Spaces, Streamlit SDK

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space),
   give it a name, pick **Streamlit** as the SDK, choose **Public**.
2. Push your whole project folder's contents into the Space's Git repo
   (Spaces are themselves Git repos, same as the AI-engineer track's
   Docker Space deploy, just with the Streamlit SDK instead of Docker this
   time -- no `Dockerfile` needed).
3. Add this to the Space's `README.md` YAML front matter (Spaces reads
   this to know where your app lives, since it isn't at the repo root
   here):

   ```yaml
   ---
   title: Keypad Door Lock v2
   emoji: 🔐
   sdk: streamlit
   sdk_version: "1.58.0"
   app_file: webapp/app.py
   pinned: false
   ---
   ```

4. Commit and push. Hugging Face installs
   `webapp/requirements.txt` and starts the app at
   `app_file`.

Either option needs zero secrets -- the simulator tab and red-team tab need
nothing at all, and the live-device tab only ever talks to the public
`broker.hivemq.com` broker with no credentials required.

---

## Step 4 -- A note on the firmware: there's no "hosting" a physical lock

Unlike the dashboard, the real firmware in
`firmware/keypad_door_lock/` doesn't get deployed to a
server -- it gets **flashed** onto your specific, physical ESP32 board,
following `01_setup_and_parts.md`'s Arduino toolchain setup and
`wiring/ASSEMBLY.md`'s rung-by-rung bring-up order. What
CI proves is narrower and still valuable: the firmware *compiles* against
the real toolchain on every push. Proving it *works* on your specific board
is bench work only you can do -- which is exactly why this project put so
much effort into the wiring docs, the multimeter checklist
(`knowledge/09_bench_debugging_with_a_multimeter.md`), and a Python
simulator faithful enough that the logic side was fully de-risked before a
single wire needed to go in.

If you want to go further later: **OTA (over-the-air) firmware updates**
are a real, common next step for ESP32 projects (the `ArduinoOTA` library,
or a more involved scheme like `esp32FOTA` pulling a new binary over
HTTPS) -- worth knowing the term exists, out of scope for this project as
built.
