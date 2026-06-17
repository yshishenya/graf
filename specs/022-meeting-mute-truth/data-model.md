# Data Model: Meeting-App Mute Truth

## ProductPrivacyControlState

Represents the local privacy state owned by 2brain Rec.

Values:

- `capturing`: local microphone samples may be written normally.
- `paused`: local microphone samples must be silenced/redacted before storage.
- `resuming`: transition from paused to capturing is in progress.
- `stopping`: recording stop is in progress; Stop remains the stronger privacy
  control.
- `stopped`: recording has ended.

Validation rules:

- `paused` requires visible local capture state and one-action Stop.
- `paused` must not be conflated with third-party meeting-app mute, hardware
  mute, macOS input mute, or route failure.
- `paused -> capturing` and `capturing -> paused` transitions must record
  metadata-only evidence.

## ProductPrivacySegment

Represents one local interval controlled by `2brain Pause` or `2brain Stop`.

Fields:

- `segmentId`: Stable local segment ID.
- `sessionId`: Local recording session ID.
- `control`: `pause`, `resume`, `stop`.
- `startedAt`: Wall-clock timestamp.
- `endedAt`: Wall-clock timestamp or null while active.
- `startMonotonicMs`: Monotonic start timestamp.
- `endMonotonicMs`: Monotonic end timestamp or null while active.
- `durationMs`: Duration after finalization.
- `localMicTreatment`: `silenced`, `redacted`, `ended`.
- `initiator`: `user`, `system_fail_closed`, `validation`.
- `diagnosticSafe`: Always `true`.

Validation rules:

- A finalized pause segment must have `durationMs >= 0`.
- `localMicTreatment=silenced` or `redacted` is required for pause segments.
- Segment evidence must not contain raw audio, transcript text, meeting content,
  credentials, tokens, signed URLs, passwords, or live secret paths.

## MeetingMuteTruthEvidence

Metadata-only evidence describing whether third-party meeting-app mute truth is
known for the recording target.

Fields:

- `evidenceId`: Stable local evidence ID.
- `sessionId`: Local recording session ID.
- `targetId`: Stable target key such as `zoom_native`, `chrome_telemost`,
  `opera_telemost`, `yandex_browser`, or `unknown`.
- `targetDisplayName`: User-facing target label.
- `source`: `product_pause`, `target_adapter`, `unsupported`, `unknown`,
  `stale`, `contradicted`.
- `status`: `accepted`, `meeting_mute_unproven`, `unsupported`, `deferred`,
  `degraded`.
- `freshness`: `fresh`, `stale`, `unavailable`.
- `limitationCopyShown`: Boolean.
- `recordedAt`: Wall-clock timestamp.
- `adapterId`: Optional future adapter identifier; null in MVP.
- `diagnosticSafe`: Always `true`.

Validation rules:

- MVP evidence must use `source=product_pause`, `unsupported`, or `unknown`
  unless a future spec adds a target adapter.
- `status=accepted` for meeting-app mute requires `source=target_adapter` and
  `freshness=fresh`; this is out of scope for this feature.
- Unsupported or unknown targets must not produce a mute-respecting acceptance
  claim.

## TargetMuteCapability

Records the first QA target matrix for mute-truth claims.

Fields:

- `targetId`
- `targetDisplayName`
- `targetFamily`: `native_app`, `browser_meeting`, `unknown`.
- `productPauseSupported`: Boolean.
- `meetingAppMuteAdapterSupported`: Boolean.
- `firstMatrixStatus`: `pause_validated`, `unsupported`, `deferred`.
- `releaseClaim`: Human-readable local claim allowed for this target.

Validation rules:

- Zoom native, Chrome/Telemost, and Opera/Telemost require
  `productPauseSupported=true` and `meetingAppMuteAdapterSupported=false`.
- Yandex Browser and unknown targets require `firstMatrixStatus=unsupported` or
  `deferred`.
- A target cannot claim meeting-app-mute-respecting support unless
  `meetingAppMuteAdapterSupported=true`.

## MuteTruthDecision

Final per-recording local decision for mute-truth claims.

Fields:

- `sessionId`
- `decision`: `mute_respecting`, `meeting_mute_unproven`, `unsupported`,
  `degraded`, `failed`.
- `reason`: `product_pause_segments_present`, `unsupported_target`,
  `adapter_missing`, `stale_evidence`, `contradicted_evidence`,
  `diagnostic_redaction_failed`.
- `privacySegments`: List of `ProductPrivacySegment` references.
- `targetEvidence`: List of `MeetingMuteTruthEvidence` references.
- `safeForDiagnostics`: Boolean.
- `decidedAt`: Wall-clock timestamp.

Validation rules:

- MVP recordings without target adapter evidence must not use
  `decision=mute_respecting` for third-party meeting-app mute.
- A recording with one or more pause segments may be accepted only for
  product-owned pause truth, not for third-party meeting-app mute.
- `safeForDiagnostics=false` blocks evidence export until redaction passes.

## LocalRecordingManifest Extension

Extend `LocalRecordingManifest` with optional fields:

- `privacySegments`: `[ProductPrivacySegment]`
- `meetingMuteTruth`: `MuteTruthDecision`
- `targetMuteCapability`: `TargetMuteCapability`
- `limitationCopyShownAt`: Optional timestamp.

Validation rules:

- `status=saved` may still be used for a valid local recording, but
  `meetingMuteTruth.decision` controls whether the artifact may be described as
  meeting-app-mute-respecting.
- If `privacySegments` contains pause intervals, local microphone audio for
  those intervals must be silenced/redacted.
- If `targetMuteCapability.firstMatrixStatus` is `unsupported` or `deferred`,
  the artifact must carry `meeting_mute_unproven`, `unsupported`, or `degraded`
  mute-truth status.
