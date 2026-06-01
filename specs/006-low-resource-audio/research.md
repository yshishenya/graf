# Research: Low-Resource Reliable macOS Audio

**Feature**: `006-low-resource-audio`
**Date**: 2026-06-01

## Clean-Room Krisp Observation

### Sources Checked

- Installed app bundle: `/Users/yshishenya/Applications/krisp.app`
- Installed HAL driver: `/Library/Audio/Plug-Ins/HAL/KrispAudio.driver`
- Launch agent: `/Users/yshishenya/Library/LaunchAgents/krisp.plist`
- Local logs: `/Users/yshishenya/Library/Application Support/krisp/logs/`
- Local app configuration: `/Users/yshishenya/Library/Application Support/krisp/userConfigs.json`
- Public Krisp help:
  - `https://help.krisp.ai/hc/en-us/articles/4402174576402-How-Krisp-Microphone-and-Krisp-Speaker-work`
  - `https://help.krisp.ai/hc/en-us/articles/11092650435996-Why-I-can-t-use-Virtual-Devices-with-Krisp`
  - `https://help.krisp.ai/hc/en-us/articles/5414924899612-Set-up-Krisp-audio-devices-as-system-default`
  - `https://help.krisp.ai/hc/en-us/articles/15519990852380-Set-and-control-system-default-devices-Krisp-Call-Center-AI`

Public Krisp help was rechecked on 2026-06-01. The public behavior-level guidance still supports three conclusions: Krisp microphone/speaker are virtual devices, Krisp sits between physical devices and communication apps, and Krisp warns users to choose genuine physical devices inside Krisp rather than chaining virtual devices.

### Installed Component Model

Krisp installs a native Core Audio HAL driver and a separate Electron application:

- `KrispAudio.driver` is loaded by `coreaudiod` as `Core Audio Driver (KrispAudio.driver)`.
- `krisp.app` is launched for the user through a LaunchAgent with `--hidden`.
- The driver bundle declares `ai.krisp.krispMac.audioDriver`.
- The application bundle declares `ai.krisp.krispMac`.
- The application has audio input entitlement and usage strings for microphone and audio capture.

This supports a split architecture:

- Driver: virtual device publication, client stream tracking, device visibility, route IO.
- App/native modules: physical device selection, stream graph, processing, recording/transcription decisions, permissions, UI.

### Driver-Level Signals

Strings and logs from the installed driver show three device concepts:

- `krisp microphone`
- `krisp speaker`
- `krisp app io`

The driver also exposes evidence of:

- audio client tracking;
- `StartIO` / `StopIO`;
- `BeginIOOperation` / `EndIOOperation`;
- app process watching;
- per-client process ID / bundle ID properties;
- hide/show behavior when the Krisp app is gone;
- stream labels `to krisp` and `from krisp`.

Important inference: the driver is not just a passive device-name stub. It tracks client IO and distinguishes the Krisp app client from other audio clients. However, recording/transcription ownership appears above the driver, not inside the HAL publication layer.

### App/Native Module Signals

The unpacked native modules include:

- `kr-audio-dm.node`: Core Audio device manager, stream tracker, default device watcher, working physical device selection, volume mapping.
- `kr-media-sp.node`: media stream graph, processors, ASR, file/stream recorders, AEC, noise cancellation, diarization, ScreenCaptureKit dependencies.
- `kr-native-utils.node`: utility/native integration, driver version reading, AudioUnit/CoreAudio helpers.

Local logs show the app selecting physical working devices:

- microphone working device: built-in physical microphone;
- speaker working device: built-in physical speaker;
- virtual devices marked as `isKrisp=true`;
- volume mapping between physical devices and Krisp devices;
- stream graph creation for microphone outbound and speaker inbound flows.

This supports the model:

```text
Communication app/browser
  -> Krisp virtual speaker / microphone
  -> Krisp driver app-IO boundary
  -> Krisp app native stream graph
  -> physical speaker / microphone
```

### Recording And Transcription Boundary

Krisp logs and bundle strings show processors such as:

- `FILE_REC`
- `STREAM_REC`
- `RTC_ASR`
- ASR / transcript / recording upload features

These are found in the app/native media service layer, not as the primary HAL driver responsibility. Public app configuration also separates meeting recording, transcript, ASR, note taking, local ASR, remote ASR, and audio device settings.

Decision for 2brain Rec: the driver must not own recording or transcription. The driver should publish and route audio; app software should subscribe to audio only after an explicit application-level recording trigger.

### Device Visibility Behavior

Observed state on 2026-06-01:

- `KrispAudio.driver` was loaded by `coreaudiod`.
- When the Krisp app was not fully active, `system_profiler SPAudioDataType` did not show `krisp microphone` or `krisp speaker`.
- Historic logs show normal sessions where Krisp devices were added and visible.
- Driver strings include app watcher and "app is gone, hide devices" behavior.

Inference: Krisp can keep the HAL driver installed and loaded while controlling user-visible virtual devices based on app state/health. This is different from a driver that always publishes visible devices regardless of app readiness.

For 2brain Rec, default behavior should remain simpler for MVP: keep virtual devices visible when installed and fail closed. If we later hide devices when the app is unavailable, it needs its own acceptance gates because stale browser selections and user trust become harder.

### Default Device Behavior

Public Krisp docs support two setup modes:

- Select Krisp devices inside the communication app/browser.
- In some configurations, set Krisp audio devices as system defaults so apps with active streams use Krisp.

Krisp docs also warn not to select virtual devices as the physical devices inside Krisp itself. Local logs align with this: the app chooses real physical devices as working devices and treats virtual devices separately.

Decision for 2brain Rec:

- 2brain Rec app must select real physical input/output as working devices.
- 2brain Rec virtual devices may be selected by browser/meeting apps or as system defaults.
- 2brain Rec must avoid chaining its own virtual devices back into itself.

### Clean-Room Takeaways For 2brain Rec

- Use a native HAL driver for virtual microphone and speaker.
- Keep audio routing separate from recording/transcription.
- Maintain an app-level audio service that chooses physical working devices, tracks default-device changes, and owns route recovery.
- Track audio clients and active streams explicitly rather than guessing from silence.
- Use app/driver boundary metadata to distinguish 2brain Rec's own app client from browser/meeting clients.
- Start route processing when a client stream needs it; do not require a manual readiness check.
- Do not mute or block an actively selected virtual speaker route merely to save resources.
- Keep diagnostics metadata-only and never store raw audio or transcript content for routing validation.
- Avoid virtual-device chaining and aggregate-device dependence as a primary path.

## Current 2brain Rec Baseline Compared To Krisp Model

### What Already Matches The Target Model

- 2brain Rec has a native HAL virtual microphone and speaker rather than a browser-only or no-driver fallback.
- The driver exposes virtual devices and keeps driver-side IO fail-closed when the app bridge is unavailable.
- The driver tracks explicit client IO through `StartIO` / `StopIO` style running-state evidence; this is the right foundation for low-resource activation because natural silence is not treated as idle.
- Shared-memory audio handoff exists between the HAL driver and app-side bridge.
- The app-side bridge, not the driver, currently owns physical microphone capture and physical speaker playback.
- The existing product behavior keeps recording/transcription out of the driver; no current acceptance evidence requires the driver to create recordings, transcripts, uploads, MediaScribe jobs, or Langfuse traces.
- Self-routing protection exists in app/shared code and should become a hard release gate rather than a best-effort helper.

### Gaps Against The Required 006 Behavior

- App-side physical Core Audio setup can still be reached through synchronous startup paths. This is high risk because previous validation produced `coreaudiod` CPU spikes, distortion, silence, and hangs in Zoom, Telemost, browser audio settings, and System Settings.
- Core Audio enumeration, physical AudioUnit binding, and route startup are not yet proven bounded to the accepted 3-second timeout across all no-hang surfaces.
- Driver realtime safety is not fully proven: current HAL paths include trace/file-output helpers around `StartIO` / `StopIO` and heartbeat freshness checks from IO flow. Planning must audit and remove or isolate any wall-clock, file IO, logging, allocation, lock wait, or blocking IPC from callback-sensitive paths.
- The app-health/public-device policy is inconsistent across artifacts: older planning accepted hiding public devices when app heartbeat is stale, while 006 selects visible fail-closed devices as the MVP default.
- The current driver/app handoff is shared memory plus heartbeat. That may be sufficient, but planning must explicitly decide whether a hidden app-IO device, a stronger app-client identity signal, or the existing shared-memory protocol is the accepted long-term boundary.
- Active-stream detection is moving in the right direction through explicit running-state evidence, but app-side polling/enumeration of Core Audio state must itself be bounded and must not run concurrently with physical setup in a way that can deadlock common audio clients.
- Physical working-device selection must reject 2brain Rec virtual devices and treat other virtual, aggregate, or multi-output devices as unsupported unless a validation gate explicitly accepts them.
- The current UI and diagnostics must show separate planes for publication, client IO/running, app bridge heartbeat/readiness, physical working device validity, and recording trigger state. Device visibility alone is not enough evidence for live-route readiness.

### Required Planning Decisions

1. **Public device policy**: Default to visible fail-closed virtual devices for MVP. Do not hide devices on stale app heartbeat unless a later explicit feature accepts the stale-selection UX cost.
2. **Startup isolation**: Move or guard any physical Core Audio setup so UI, validation commands, browsers, meeting apps, and System Settings cannot be blocked by route startup.
3. **Realtime callback boundary**: Keep HAL IO callbacks limited to realtime-safe ring-buffer reads/writes, zero/drop fail-closed behavior, and atomic state updates.
4. **Route truth model**: Store and display separate metadata for publication, client IO activity, app bridge heartbeat/readiness, physical working-device validity, and recording trigger state.
5. **Fallback**: Preserve a switch back to the accepted 005 app-launch passthrough lifecycle without reinstalling the driver.
6. **Clean-room implementation**: Use Krisp only as behavior-level validation of architecture principles. Do not copy code, UI, identifiers, protocols, assets, or private implementation details.

### Why A Full Refactor May Be Needed

The risky part is not simply "idle release". The risky part is where physical Core Audio setup happens and how failures propagate. If route startup can synchronously touch Core Audio from app/UI paths or coordinate poorly with `coreaudiod`, then low-resource activation may save idle CPU while making real calls less reliable. The implementation plan should therefore treat startup isolation, bounded route orchestration, and realtime-safe driver IO as foundational work before optimizing any smaller resource counters.

The likely refactor boundary is:

- Driver: publish virtual devices, track explicit client IO state, perform realtime-safe shared-buffer handoff, fail closed on stale app bridge.
- App route engine: decide when a stream needs physical routing, orchestrate bounded startup, choose valid physical devices, recover from restarts, and expose route truth.
- Future recording layer: subscribe only after an explicit application trigger and visible capture state; never require the driver to become a recorder.

### Open Questions For Planning

- Whether 2brain Rec needs a hidden app-IO device analogous to Krisp's `krisp app io`, or whether shared ring buffers plus explicit app client metadata are sufficient.
- Whether virtual devices should ever hide when the app exits, or remain visible and fail closed for MVP reliability.
- How to implement bounded app/driver handoff so Core Audio callbacks stay realtime-safe and never wait on app process health, IPC, locks, logs, or allocation.
- How to detect active browser/meeting streams without relying on natural audio energy, because silence is a valid active-stream state.
