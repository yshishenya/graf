# Quickstart: macOS Virtual Audio Driver MVP Validation

This quickstart defines the validation path for the feature before implementation
is accepted. It is not an end-user setup guide.

## 0. Phase 0 Runtime Proof Gate

Before US1 driver implementation, run and record the proof gate.

1. Build and run the current scaffold check:

   ```sh
   make -C apps/macos/AudioDriver proof-scaffold-run
   ```

2. Record the runtime proof result in:

   ```text
   apps/macos/AudioDriver/RuntimeProofReport.md
   ```

3. The report must include OS version, CPU architecture, command used, whether
   both virtual devices are visible to macOS, self-routing rejection status,
   passthrough/mirror status, continuity signal status, permissions/signing
   assumptions, limitations, and the Core Audio path decision.

Pass criteria: the scaffold command passes and the runtime report contains an
observed Apple Silicon result. A one-machine runtime result unlocks architecture
work only; it is not release-candidate matrix coverage.

The local foundation validation command is:

```sh
sh apps/macos/Scripts/validate-foundation.sh
```

The US1 readiness gate is:

```sh
sh apps/macos/Scripts/validate-us1-gate.sh
```

It must fail until the runtime report status is `ACCEPTED`.

## 1. Fresh Install

1. Start on Apple Silicon macOS 14.5 or latest stable macOS at RC time.
2. Confirm no previous 2brain Rec virtual devices are present.
3. Run the interactive signed/notarized installer.
4. Grant required permissions.
5. Confirm both devices appear in macOS audio settings:
   - `2brain Rec Microphone`
   - `2brain Rec Speaker`
6. If restart is required, confirm the installer and app say so explicitly.

Pass criteria: both virtual devices are available or the required restart/manual
step is clearly reported.

## 2. Route Verification

1. Select a physical microphone and physical output.
2. Run synthetic microphone route verification.
3. Run synthetic speaker route verification.
4. Attempt self-routing by selecting a 2brain Rec virtual device as its own
   physical source/output.
5. Confirm self-routing is blocked or clearly rejected.

Pass criteria: the app shows `ready` only after valid mic and speaker paths pass;
self-routing never produces a ready state.

## 3. Browser Meeting Validation

Run the approved browser meeting scenario for:

- Chrome
- Opera
- Yandex Browser
- Yandex Telemost in browser after QA

For each target:

1. Select `2brain Rec Microphone` as meeting microphone.
2. Select `2brain Rec Speaker` as meeting speaker.
3. Start a meeting with remote audio.
4. Start capture manually.
5. Confirm local mic and remote speaker tracks are separate.
6. Confirm remote audio is absent from the virtual microphone path.

Pass criteria: each officially supported target passes or remains best-effort and
is not marketed as supported.

## 4. Long-Run Audio Integrity

Run 60-minute calls for:

- wired audio
- USB audio
- Bluetooth headset
- AirPods-class device

Collect:

- track alignment drift
- dropped frame rate
- passthrough status
- continuity/dropout markers
- user-visible degraded state when applicable

Pass criteria: wired calls stay within 100 ms alignment and below 0.1% dropped
frames; Bluetooth and AirPods-class calls stay usable and below 0.5% dropped
frames.

## 5. Failure Recovery

During or around capture, test:

- microphone permission denied before onboarding
- microphone permission revoked after onboarding
- physical microphone disconnect
- physical output disconnect
- Bluetooth profile switch
- browser target restart
- desktop app restart
- 5-minute server/network outage
- local disk/buffer warning and critical thresholds

Pass criteria: failures are distinguished, visible, and recoverable; passthrough
continues when backend/network fails; capture degrades or stops before silent
loss.

## 6. Visible Control

1. Start audio-recording mode.
2. Start transcript-only mode.
3. Observe capture state without opening the full desktop app.
4. Stop capture in one interaction from the visible local surface.

Pass criteria: active capture is always locally visible and one-action stop is
available.

## 7. Installer Recovery

Run:

- update while no call is active
- attempted update while call is active
- repair
- rollback
- uninstall
- reinstall after uninstall

Pass criteria: active-call update is deferred or explicitly delayed; uninstall
removes app-managed artifacts where OS permits; previous physical input/output
restoration is attempted and truthfully reported.

## 8. Diagnostics Redaction

Generate diagnostic bundles for:

- install failure
- route failure
- permission failure
- physical device failure
- network/server outage during capture
- buffer pressure
- uninstall partial failure

Pass criteria: bundles contain actionable manifest data and no raw audio,
transcript text, credentials, tokens, or signed URLs by default.
