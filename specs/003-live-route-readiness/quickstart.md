# Quickstart: macOS Live Route Readiness

## Prerequisites

- Apple Silicon macOS 14.5+.
- Local package from `apps/macos/Installer/Scripts/build-local-installer.sh`.
- Physical microphone and physical output available.
- 2brain Rec app installed from the current branch.

## Validation Flow

1. Build and install the local package.

   ```sh
   TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
   sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
   sudo killall coreaudiod || true
   ```

2. Launch 2brain Rec and confirm publication.

   ```sh
   open -a "2brain Rec"
   make -C apps/macos/AudioDriver proof-runtime-probe-run
   ```

3. Select a physical microphone and physical output in the app.

4. Run readiness check.

   Expected:

   - publication-only state does not show ready;
   - microphone path evidence passes only with valid physical input frames;
   - speaker path evidence passes only with the selected physical output route;
   - self-routing fails;
   - app remains non-recording.

5. Validate fail-closed behavior.

   ```sh
   pkill -TERM -x "2brain Rec" || true
   sleep 7
   make -C apps/macos/AudioDriver proof-runtime-probe-run || true
   open -a "2brain Rec"
   sleep 8
   make -C apps/macos/AudioDriver proof-runtime-probe-run
   ```

   Expected:

   - after kill: public devices hidden or unavailable;
   - after relaunch: devices return only after app heartbeat and route recovery.

6. Run latency and leakage validation.

   Expected:

   - built-in/wired added latency `<= 30 ms`;
   - remote-to-mic leakage `<= -45 dB` and not intelligible.

7. Run browser target matrix.

   Required targets:

   - Chrome
   - Opera
   - Yandex Browser
   - Yandex Telemost-in-browser

   Each target must record pass or blocked/not accepted evidence.

8. Confirm diagnostics redaction.

   Diagnostics must include route state and recovery action, but no raw audio,
   transcript text, credentials, tokens, or signed URLs.
