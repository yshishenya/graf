# Quickstart: Feature 231

Все evidence должны быть metadata-only или synthetic; не сохранять аудио, transcript, private paths или signed URLs в git.

## 1. Focused checks

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'RecordingEchoProcessorTests|RecordingAudioTimelineTests|DesktopUploadQueueTests|DesktopMeetingShellWebViewBoundaryTests'
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

Expected: finite overshoot clamps without failure; NaN/size and injected AEC failures remain terminal; UTF-8, local open/delete policy, duration, category migration and no-grafting assertions pass.

## 2. Local row UX

1. Build and launch the existing dev-channel app entrypoint.
2. Open embedded `/desktop/meetings` with a synthetic local row containing Cyrillic title/status.
3. Verify normal audio icon, readable text, actual saved duration and `Сохранено X из Y` for a partial prefix.
4. Activate title/row with pointer, Tab + Enter and VoiceOver; verify native playback opens without exposing the path in DOM.
5. Exercise cancel and confirm delete; verify only confirm removes the item and it stays absent after rescan.

## 3. Handoff

1. Observe one uploadable item through queued → uploading → uploaded.
2. Before the server list contains its meeting ID, verify local row remains.
3. Refresh after server row appears; verify exactly one normal server row remains, carries no local ID, and opens its authorized detail route.

## 4. Fresh capture

1. Run a dev-channel capture with finite loud peaks and stop normally.
2. Verify no `echo_processing_failed`, upload proceeds and server meeting opens.
3. Inject NaN or a processor failure in tests; verify prompt stop, exact failure code, local-only cleaned prefix and no raw-mic artifact.

## 5. Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Full CI, signing, notarization, installed production app replacement, release and deploy are outside this local feature gate.
