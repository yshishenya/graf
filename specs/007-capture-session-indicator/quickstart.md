# Quickstart: Manual Capture Session And Visible Indicator

## 0. Baseline

Start from the current local development build after `006-low-resource-audio`.

Expected baseline:

- `2brain Rec Microphone` and `2brain Rec Speaker` are visible/alive.
- Low-resource route is default-safe when idle.
- Non-recording passthrough works in the selected target.
- No recording, upload, transcription, MediaScribe, Langfuse, or dashboard
  activity is active before pressing Record.

## 1. Automated Validation

```sh
swift test --package-path apps/macos --disable-swift-testing
swift run --package-path apps/macos ContractValidation
sh tests/macos/static/audio-rt-safety-check.sh
```

Expected:

- capture control and prerequisite tests pass;
- diagnostic redaction tests pass;
- realtime safety scan remains accepted.

## 2. Start/Stop Smoke

1. Open 2brain Rec.
2. Confirm route state is valid for non-recording passthrough.
3. Select `2brain Rec Microphone` and `2brain Rec Speaker` in the target app.
4. Press Record.
5. Confirm active recording state appears.
6. Confirm a persistent local visible indicator is present.
7. Confirm Stop is visible, keyboard reachable, and one-action.
8. Press Stop once.
9. Confirm recording transitions to stopping/stopped within 1 second.
10. Confirm non-recording passthrough may continue after stop.

Expected:

- no invisible recording window;
- no external egress;
- metadata-only evidence for start and stop.

## 3. Indicator Fail-Closed Smoke

1. Start recording.
2. Close or background the main window.
3. Confirm another local indicator remains visible.
4. Simulate indicator unavailability where possible.

Expected:

- recording remains visible and stoppable; or
- recording stops/fails closed with evidence.

## 4. Blocked Start Smoke

Run each blocked scenario:

- stale route evidence;
- publication-only route evidence;
- recording policy disabled;
- microphone permission unavailable;
- local storage/buffer reserve unsafe;
- visible indicator unavailable.

Expected:

- recording does not start;
- blocker category and recovery action are shown;
- start-blocked evidence is metadata-only.

## 5. Browser/App Smoke Targets

Run short manual recording smoke for:

- Telemost;
- Chrome;
- Opera;
- Zoom.

Yandex Browser remains skipped/not accepted unless explicitly run.

Expected per target:

- local speech and remote audio route remain usable;
- active recording indicator is visible;
- Stop works in one action;
- no upload, transcription, MediaScribe, Langfuse, or dashboard activity starts;
- evidence records passed or blocked/not accepted metadata-only outcome.

## 6. Evidence Redaction

Generate or inspect diagnostic/evidence bundle.

Expected forbidden content absent:

- raw audio;
- transcript text;
- meeting content;
- credentials;
- tokens;
- signed URLs;
- passwords;
- live secret paths.
