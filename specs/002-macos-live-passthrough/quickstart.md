# Quickstart: macOS Live Audio Passthrough Validation

This quickstart defines the validation path for the live passthrough feature.

## 0. Preconditions

1. Build the app and proof driver:

   ```sh
   swift build --package-path apps/macos -c release --product TwoBrainRecApp
   make -C apps/macos/AudioDriver proof-plugin-build
   ```

2. Install the current driver bundle from an interactive admin Terminal:

   ```sh
   make -C apps/macos/AudioDriver proof-plugin-install
   ```

3. Confirm macOS system input/output are physical devices, not 2brain Rec
   virtual devices.

4. Launch `/Applications/2brain Rec.app`.

Expected current state before this feature is complete: the app may show both
virtual devices as visible, but it must still show not ready.

## 1. Readiness Check

1. Select or confirm a physical microphone.
2. Select or confirm a physical speaker.
3. Run the app's readiness check.
4. Confirm the check does not start capture or upload audio.
5. Confirm ready is shown only after both live paths pass.

Pass criteria:

- `2brain Rec Microphone` receives physical microphone audio.
- `2brain Rec Speaker` renders to the selected physical speaker.
- Device visibility alone never passes readiness.
- Missing capturability or no valid frames for one 3-second health interval
  fails readiness.
- Natural user silence with valid microphone frames does not fail readiness by
  itself outside the explicit speak-or-tap readiness stimulus.
- Failure states identify microphone, speaker, self-routing, loopback, or device
  change separately.

## 2. Browser Meeting Check

Run one controlled meeting in each target:

- Chrome
- Opera
- Yandex Browser
- Yandex Telemost in browser

For each target:

1. Select `2brain Rec Microphone` as meeting microphone.
2. Select `2brain Rec Speaker` as meeting speaker.
3. Speak locally and play remote audio.
4. Confirm the user can hear and speak normally.
5. Confirm remote audio does not appear in the virtual microphone path.
6. Measure remote speaker leakage against the speaker reference on release-ready
   built-in and wired routes.

Pass criteria: each supported target either passes or remains explicitly
best-effort and not release-ready. Built-in and wired release-ready routes keep
remote speaker leakage in the virtual microphone at least 45 dB below the
speaker reference and not intelligible.

## 3. Capture Evidence Check

1. Start capture only after readiness passes.
2. Record a controlled local/remote audio sample.
3. Verify separate local microphone and remote speaker track evidence.
4. Verify missing expected tracks, no valid frames for one 3-second health
   interval, or repeated empty buffers during expected active stimulus mark the
   session degraded.
5. Verify ordinary local user silence with valid input frames does not mark the
   session degraded solely because speech is absent.

Pass criteria: local and remote evidence exists separately and does not hide
missing-track conditions.

## 4. Long-Run Check

Run a 30-minute pilot call for:

- built-in audio
- wired or USB audio
- Bluetooth headset
- AirPods-class device

Collect:

- alignment drift
- dropped frame count
- route invalidation events
- degraded-state transitions

Pass criteria:

- built-in/wired alignment stays within 100 ms;
- built-in/wired dropped frames stay below 0.1%;
- Bluetooth/AirPods dropped frames stay below 0.5%;
- Bluetooth/AirPods profile remains stable or shows warning/degraded recovery;
- Bluetooth/AirPods local and remote directions deliver valid frames in every
  3-second health interval with no one-sided audio event;
- Bluetooth/AirPods measured latency evidence is recorded for the pilot;
- backend/network outage for 5 minutes does not interrupt live passthrough.

## 5. Recovery Check

During or after readiness:

- disconnect microphone;
- disconnect speaker;
- switch Bluetooth profile;
- change macOS default output;
- restart browser target;
- restart desktop app.

Pass criteria: readiness invalidates within 5 seconds and shows a specific
recovery action before ready can return.

## 6. Diagnostics Check

Generate diagnostics for:

- microphone path failure;
- speaker path failure;
- self-routing rejection;
- loopback rejection;
- device-change invalidation;
- degraded track evidence.

Pass criteria: diagnostics are actionable and contain no raw audio, transcript
text, credentials, tokens, or signed URLs.
