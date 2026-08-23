# Contract: Windows native desktop boundary

Дата: 2026-08-23

Контракт сохраняет границу Feature 058/057/177 для нового Windows host. Он не
создаёт новый серверный API и не разрешает удалённой странице владеть capture.

## 1. Ownership

| Capability | Windows native | Server WebView |
|---|---:|---:|
| Record/Pause/Resume/Stop | owner | no authority |
| capture readiness/permissions | owner | bounded read-only state |
| render loopback/microphone/AEC/timeline | owner | none |
| active indicator/tray/Stop | owner | cannot hide |
| local package/manifest/integrity | owner | no file path/access |
| upload queue/retry/reconcile | owner through existing GRAF API | auth page can recover session |
| meeting list/detail/review | no duplicate | owner |
| settings page/account/workspace | only native-only settings | owner when route is allowed |
| deletion report and server lifecycle | no business decision | owner; local purge remains native |
| MediaScribe/MinIO credentials | never | server only |

## 2. Readiness gate

`Record` can enter `starting` only when every condition is true:

- current workspace recording policy allows capture;
- microphone privacy state is granted and selected/default capture endpoint is
  available;
- render endpoint is available for shared loopback;
- endpoint formats can be normalized to 48 kHz mono;
- AEC3 static processor is created with the pinned configuration;
- local recording directory can be created and written atomically;
- WebView may be unavailable; it is not a capture prerequisite;
- native indicator and one-action Stop have been installed before the first audio
  batch is accepted.

If any condition is false, no normal recording starts. UI shows the safe reason
and recovery action. A missing WebView runtime or network is not converted into a
fake audio permission error.

## 3. Session transitions

```text
idle -> checking_readiness -> ready -> starting -> recording
recording <-> paused
recording/paused -> degraded -> stopping
recording/paused/starting -> stopping
stopping -> finalizing -> saved_local -> queued -> uploaded
finalizing -> failed|blocked
```

Rules:

- one `WindowsDesktopSession` can be active at a time;
- `Stop` is idempotent while `starting`, `recording`, `paused`, `degraded` or
  `stopping`; repeated clicks do not create a second finalizer;
- `Pause` is a privacy pause: keep the system reference and PTS timeline alive,
  feed a timestamped zero microphone contribution through the same AEC3 path,
  and preserve a bounded privacy segment in the manifest; do not switch to raw
  mic or invent silence by wall clock;
- `Resume` restores mic samples only after the same endpoint/timeline gates are
  valid;
- a route/clock/device discontinuity ends the trusted normal segment. The first
  version may finalize a proven cleaned prefix as degraded, but may not silently
  splice a new endpoint into the old normal package.

## 4. Capture source contract

Both sources publish `RecordingAudioBatch` values with:

- `source` (`system_render` or `microphone`);
- actual source format and normalized format;
- device/QPC-derived presentation timestamp;
- opaque clock domain and route generation;
- finite sample count and discontinuity marker.

Callbacks must only drain WASAPI packets and enqueue into a bounded queue. They
must not perform file I/O, WebView calls, UI work, allocations that can grow
without bound or blocking waits. The worker/timeline owns normalization,
alignment and AEC3.

The system source is the global mix from the selected/default render endpoint.
The microphone source is the selected/default physical capture endpoint. The
contract does not claim process isolation, and protected render content may be
unavailable.

## 5. Timeline and artifact contract

`RecordingAudioTimeline` is the only alignment owner:

1. compare clock domains and route generations;
2. reject invalid/backward timestamps and gaps above the approved bound;
3. normalize both sources to 48 kHz mono float;
4. emit 480-sample pairs;
5. call AEC3 render/reference first, microphone second;
6. mix cleaned microphone with unchanged system reference;
7. send contiguous canonical chunks to the writer.

Normal output is exactly:

- `meeting-transcription.wav`: PCM signed 16-bit little-endian, 16 kHz, mono;
- `meeting-review.m4a`: AAC-LC, 48 kHz, mono;
- `manifest.json`: existing v5-compatible schema with optional Windows health
  metadata.

The writer validates byte count, hash, decodable format, frame count and duration
before changing the package to normal/saved. No normal package is created from
an unprocessed raw microphone path.

## 6. Failure and degraded policy

| Failure | Native result | Normal package? |
|---|---|---:|
| microphone denied/missing | block start; show recovery | no |
| render endpoint missing | block start; show recovery | no |
| format normalization unavailable | block start or degraded prefix | no |
| AEC3 creation/process error | block or finalize cleaned prefix | no |
| endpoint invalidated/service stopped | end trusted segment; Stop remains | no |
| timestamp/gap/clock failure | end trusted segment; bounded reason | no |
| queue overflow | end trusted segment; record count | no |
| protected render content | explicit limited/degraded state | only if all required gates still pass |
| disk full/finalization failure | preserve verified prefix and ledger | no |
| WebView/network unavailable | native capture/local custody continues | yes, if audio gates pass |

Failures contain only stable reason codes, counters, durations and safe recovery
actions. Raw input is never used as a hidden fallback.

## 7. Local custody and upload

The Windows writer finalizes local package before any network call. The queue:

- uses the existing `desktop-upload-queue.v2` ledger and item identity;
- writes atomically and quarantines malformed documents;
- runs on launch, activation, auth change, network recovery, wake, scheduled
  retry and local finalization;
- reconciles server truth before upload/finalize/review/purge;
- resumes accepted ranges and does not create duplicate meeting/upload sessions;
- exposes owner/action policy, not raw transport controls, to the user;
- acknowledges local purge only after deletion, tombstone or cryptographic
  unrecoverability is verified.

The client talks only to the existing GRAF desktop upload API. No audio request
goes from Windows directly to MediaScribe, MinIO or an upstream provider.

## 8. Indicator and accessibility

The shell must expose a persistent native recording strip with status, source
scope copy and Stop. When the main window is hidden/minimized, the tray item
continues to show recording state and Stop. It must support keyboard focus,
accessible name/description, high contrast and 200% DPI. Color alone cannot
convey active/degraded/paused state.

The indicator state is derived from the native session, not from WebView DOM or a
web message. A navigation failure cannot remove it.

## 9. Evidence and logging

Allowed fields include:

- app/build/OS/architecture;
- state and safe reason code;
- source class (`render_loopback`, `microphone`), format class, route generation;
- bounded counters, byte counts, durations and retry class;
- redacted device fingerprint.

Forbidden fields include raw audio, transcript text, signed URLs, authorization
headers, cookies, passwords, local absolute paths, process command lines and
private meeting identifiers.

