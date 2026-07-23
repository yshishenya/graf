# Data Model: Восстановление автозаписи встреч

Feature 124 reuses existing entities. No new persisted table, file format or
service is introduced.

## MeetingDetectionSettings

Existing local settings document persisted by
`MeetingDetectionSettingsStore`.

| Field | Meaning | Feature 124 rule |
|---|---|---|
| `detectionMode` | `detectOnly` or `detectAndAsk` | Auto-record and prompt require `detectAndAsk`; detect-only never starts. |
| `targetScopedAutoRecordEnabled` | Compatibility/global guard for target rules | True exactly when at least one target permission is enabled. |
| `autoRecordTargetIds` | Set of canonical target IDs | Exact-target, reversible permissions; no bundle or display-name substitution. |
| `uploadMode`, `unknownIdentityUploadAllowed` | Existing candidate/telemetry controls | Unchanged by this feature. |

Validation:

- The store retains existing values on load/save and writes atomically.
- Settings UI only adds/removes IDs from the current verified native target list.
- Removing a registry target does not rewrite its ID to another target.
- The policy guard blocks all target rules when `detectionMode != .detectAndAsk`.

## MeetingTargetRegistryDocument

Existing canonical registry cache resolved by `MeetingTargetRegistryStore`.

Feature 124 settings projection:

```text
registry.targets
  where platform == macos
    and targetFamily == nativeApp
    and mode == promptEnabled
  sorted by displayName.localizedCaseInsensitiveCompare
```

The registry validator remains responsible for schema, identity, evidence and
unsafe-target rejection. Browser, Windows, manual-only, diagnostic-only,
verify-required and unknown entries are not auto-record rows.

## MeetingDetectionPolicyAction

Runtime decision derived from a stable detector decision, local settings and
capture prerequisites.

```text
suppress(reason)
detectOnly(targetID?)
prompt(targetID)
autoRecord(targetID)
```

Transitions:

1. Suppressed or unknown candidate → `suppress`/`detectOnly`.
2. Known target with detection disabled → `detectOnly`.
3. Known prompt-capable target with failed prerequisite → `suppress`.
4. Known target with saved exact-target permission → `autoRecord`.
5. Known target without saved permission → `prompt`.

The `autoRecord` action is not a capture command. It is an eligibility output
that the native app sends through the same capture start path as a prompt Start.

## MacOSMeetingActivityDetectorOutput

Existing detector output expanded with the restored action:

| Output | Consumer behavior |
|---|---|
| `promptEligible(targetID, bundleID)` | Present the floating prompt with timer and checkbox. |
| `autoRecordEligible(targetID, bundleID)` | Start exact target through `startManualRecording(meetingDetectionTarget:)`. |
| `candidateObserved` | Keep metadata-only telemetry behavior. |
| `suppressed` | Keep status/suppression behavior. |
| `ended` | Dismiss matching prompt and stop matching detector recording as already implemented. |

The detector emits at most one eligible output per stable bundle episode using
the existing debounce/emitted-bundle state.

## MeetingDetectionPrompt

Transient in-memory entity shown in the native floating `NSPanel`.

Fields remain `targetID`, `bundleID`, `displayName`, capture mode/source copy,
workspace policy state and detector reason. The view adds/restores:

- exact eight-second countdown state;
- `autoRecordOptIn` checkbox;
- cancellable automatic-start task;
- immediate primary action and dismiss action;
- single-resolution guard so Start/expiry/dismiss cannot race.

The prompt is never persisted or restored after app restart.

## CaptureSession

Existing local recording lifecycle. A detector-assisted session carries
`meetingDetectionTarget` evidence, remains locally visible and exposes the
existing one-action Stop. It must not create a second session when an active
capture already exists.

## Relationships

```text
MeetingTargetRegistryDocument
        │ exact target identity
        ▼
MeetingDetectionSettings ──► MeetingDetectionPolicyAction
        │                         │
        │                         ├── prompt ──► MeetingDetectionPrompt
        │                         │                 │ timer/opt-in
        │                         │                 ▼
        └─────────────────────────┴──────► CaptureSession
```
