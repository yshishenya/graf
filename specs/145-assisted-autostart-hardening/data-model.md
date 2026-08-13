# Data Model: Assisted Auto-Start Hardening

## AssistedAutoStartPolicySnapshot

Получается только из authenticated target registry response.

| Field | Type | Rules |
|---|---|---|
| `policyRef` | string | opaque, stable for workspace+policy version |
| `acknowledgementSubjectRef` | string | opaque, stable for user+workspace+policy version |
| `deviceRef` | string | opaque, stable for device+workspace+policy version |
| `policyVersion` | string | non-empty safe version code |
| `acknowledgementVersion` | string | exact version required from user |
| `enabled` | bool | must be `true` for assisted start |
| `issuedAt` | datetime | server-generated; policy is inactive before this time |
| `expiresAt` | datetime | required; policy is inactive at and after this time |
| `noticeMode` | enum | `internal_no_participant_notice` in this slice |

Missing policy is a valid registry state and means assisted start denied.

## AssistedAutoStartAcknowledgement

Stored atomically inside existing `MeetingDetectionSettings`.

| Field | Type | Rules |
|---|---|---|
| `policyRef` | string | exact match with current snapshot |
| `subjectRef` | string | exact match with current authenticated subject reference |
| `deviceRef` | string | exact match with current authenticated device reference |
| `acknowledgementVersion` | string | exact match with current snapshot |
| `acceptedAt` | datetime | written only after explicit user action inside the policy validity window |

Deleting the object is revocation. Existing `autoRecordTargetIds` remain intact.
Decode failure or write failure does not grant authorization.

## DetectorAssistedStartDecision

Ephemeral value created once at the trigger boundary.

| Field | Type | Rules |
|---|---|---|
| `targetID` | string | current verified registry target |
| `bundleID` | string | current native bundle ID |
| `displayName` | string | UI only; not uploaded as policy evidence |
| `reason` | enum | `prompt_button`, `prompt_timeout`, `saved_target_policy` |
| `policy` | snapshot | current non-expired policy |
| `acknowledgement` | acknowledgement | exact current match |

## CountdownDecision

Pure single-resolution state.

- Initial: `pending(deadline)`.
- `prompt_button` before deadline resolves once as button.
- `skip`, disappearance, target end, setting disablement or competing recording
  resolves once as cancelled.
- timeout resolves once only at `now >= deadline`.
- Any later event is ignored.

## Capture evidence additions

The existing `CaptureSession.triggerEvidence` receives safe code values only:

- `meetingDetectionStartReason`
- `meetingDetectionAutoStart`
- `meetingDetectionPolicyRef`
- `meetingDetectionPolicyVersion`
- `meetingDetectionPolicyExpiresAt`
- `meetingDetectionAcknowledgementVersion`
- `meetingDetectionAcknowledgementSubjectRef`
- `meetingDetectionDeviceRef`
- `meetingDetectionAcknowledgementState`
- `meetingDetectionNoticeMode`
- existing target/bundle, permission, route, indicator and Stop evidence

No raw audio, transcript, title, URL, credential or participant data is added.

## State transitions

```text
policy absent/expired/disabled ───────────────> detected only / blocked
policy active + acknowledgement absent ──────> detected only / settings action
policy active + acknowledgement exact ───────> prompt countdown or saved-target path
pending countdown + Start ───────────────────> prompt_button decision
pending countdown + 8.000 s ─────────────────> prompt_timeout decision
saved target + all current gates ────────────> saved_target_policy decision
any decision + failed re-check ──────────────> blocked evidence
any decision + all current gates ────────────> one active capture session
```
