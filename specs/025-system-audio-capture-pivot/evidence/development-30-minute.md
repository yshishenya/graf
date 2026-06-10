# Development 30-Minute Validation

Feature: `025-system-audio-capture-pivot`

This evidence file is metadata-only. Do not paste raw audio, transcripts,
meeting content, credentials, tokens, signed URLs, or personal contact details.

| Run | Duration | Scope | mic.wav | incoming.wav | Alignment | CPU Gate | Responsiveness | Stop/Quit Release | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260610-112827-761CE2A6-1D90-4028-9BF8-8C1EF7352D6B | 30 minutes | passed | passed | passed | passed | passed | passed | passed | passed | scope=display device=/Applications/2brain Rec.app artifact=20260610-112827-761CE2A6-1D90-4028-9BF8-8C1EF7352D6B cpu=stop-gate-passed-in-manifest micDuration=7543.114s incomingDuration=7543.100s durationDifferenceSeconds=0.014 responsiveness=manual-stop-completed release=manifest-captureHealth-stop-passed actualDurationMinutes=125.72 mostlySilent=true |

Blocked, failed, degraded, and not-tested rows are not acceptance.

Accepted rows must include metadata-only traceability tokens in Notes:
`scope=`, `device=`, `artifact=`, `cpu=`, `micDuration=`,
`incomingDuration=`, `durationDifferenceSeconds=`, `responsiveness=`, and
`release=`.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T174858Z`
- Timestamp: `2026-06-08T17:48:58Z`
- Commit: `967c381`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T012803Z`
- Timestamp: `2026-06-09T01:28:03Z`
- Commit: `6395360`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T042611Z`
- Timestamp: `2026-06-09T04:26:11Z`
- Commit: `36f5516`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T042937Z`
- Timestamp: `2026-06-09T04:29:37Z`
- Commit: `36f5516`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T052528Z`
- Timestamp: `2026-06-09T05:25:28Z`
- Commit: `62616bb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T090022Z`
- Timestamp: `2026-06-09T09:00:22Z`
- Commit: `e01db77`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.

## 2026-06-10 30-Minute Development Acceptance

- Decision: accepted for T074 / issue #310.
- Accepted artifact directory: `20260610-112827-761CE2A6-1D90-4028-9BF8-8C1EF7352D6B`
- Actual duration: `7543.100` to `7543.114` seconds (`125.72` minutes), which exceeds the 30-minute requirement.
- Manifest status: `saved`
- Failure reason: `none`
- Transcription readiness: `ready`
- Track evidence: `mic.wav` and `incoming.wav` saved as WAV PCM, `local_mic` source `microphone`, `remote_speaker` source `systemAudio`.
- Alignment: `durationDifferenceSeconds=0.014`
- Capture health: stop phase, `gateStatus=passed`, `halProbeObserved=false`, dropped/protected/silent frame counts `0`.
- Note: the user reported the recording was mostly silent; the manifest still reports both tracks saved, no silent-input degradation, and validator accepted the artifact metadata.

## Metadata Validator Run

- Run ID: `20260610T133653Z`
- Timestamp: `2026-06-10T13:36:53Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--duration-minutes 30`
- Validator result: `blocked`
- Reason: Real sustained recording run is still required before acceptance.
- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.
