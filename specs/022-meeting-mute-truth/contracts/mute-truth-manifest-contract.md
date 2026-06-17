# Contract: Mute-Truth Manifest

## Manifest Extension

`manifest.json` must remain a local artifact manifest and may be extended with
optional fields:

- `privacySegments`
- `meetingMuteTruth`
- `targetMuteCapability`
- `limitationCopyShownAt`

Existing fields such as `schemaVersion`, `sessionId`, `status`,
`transcriptionReadiness`, `tracks`, `scopeApproval`, `permissions`, and
`captureHealth` remain required according to the existing local recording
contract.

## Privacy Segment Fields

Each `privacySegments[]` row contains:

- `segmentId`
- `sessionId`
- `control`: `pause`, `resume`, or `stop`
- `startedAt`
- `endedAt`
- `startMonotonicMs`
- `endMonotonicMs`
- `durationMs`
- `localMicTreatment`: `silenced`, `redacted`, or `ended`
- `initiator`
- `diagnosticSafe`

## Meeting Mute Truth Fields

`meetingMuteTruth` contains:

- `sessionId`
- `decision`: `mute_respecting`, `meeting_mute_unproven`, `unsupported`,
  `degraded`, or `failed`
- `reason`
- `privacySegmentIds`
- `targetEvidenceIds`
- `safeForDiagnostics`
- `decidedAt`

## Target Capability Fields

`targetMuteCapability` contains:

- `targetId`
- `targetDisplayName`
- `targetFamily`
- `productPauseSupported`
- `meetingAppMuteAdapterSupported`
- `firstMatrixStatus`
- `releaseClaim`

## Acceptance Rules

- MVP artifacts must not use `decision=mute_respecting` for third-party
  meeting-app mute because this slice does not implement target adapters.
- Pause intervals require `privacySegments` and silenced/redacted local mic
  samples.
- Unsupported/deferred targets must use `meeting_mute_unproven`,
  `unsupported`, or `degraded`.
- `safeForDiagnostics` must be `true` before any mute-truth evidence is exported
  to diagnostic bundles.
- These fields must not contain raw audio, transcript text, meeting content,
  credentials, tokens, signed URLs, passwords, or live secret paths.
