# Data model: permission and termination lifecycle

## InstallArtifact

| Field | Meaning | Invariant |
| --- | --- | --- |
| `bundleIdentifier` | macOS application identity | Always `pro.2brain.graf` |
| `applicationName` | Installed bundle name | Always `GRAF.app` |
| `appSignature` | Embedded app signing identity | Must pass strict code-sign verification before install |
| `packageSignature` | Product package trust | May be absent in the no-account local channel; docs must say so |
| `privacyDescriptions` | Microphone and Screen/System Audio explanations | Both required before packaging |
| `trustChannel` | Local/self-signed or public Developer ID | Local channel must not be described as notarized |

## CapturePermissionState

Each permission is observed independently as one of:

`unknown` → `granted` or `denied`/`restricted`.

The app may request only the normal API transition from `unknown`. A denied or
restricted state is recoverable only through the system's own settings or policy
change. Recording readiness is the conjunction:

```text
microphone == granted && systemAudio == granted
```

No UI action may manufacture `granted` without a fresh platform read.

## PermissionOnboardingState

```text
status: (microphone, systemAudio)
presented: Bool
requestInProgress: Bool
restartRequired: Bool
```

Transitions:

- app launch → read both statuses; present if not ready;
- normal microphone action → request only when platform state is `unknown`;
- denied/restricted microphone action → open Microphone settings;
- system-audio settings action → mark `restartRequired`; open Screen & System
  Audio Recording settings;
- app becomes active → read both statuses again; keep the sheet if restart is
  required or either status is not granted;
- explicit restart → clear presentation state, then invoke normal `NSApp`
  termination; a new process starts with `restartRequired == false`.

## TerminationRequest

```text
replyPending: Bool
modalStateCleared: Bool
captureCleanup: pending | finished | timed_out
replyDeadline: 10 seconds
```

Only one request may own the pending reply. The reply is sent after cleanup or
the existing 10-second timeout. Modal dismissal is best-effort and must not
disable the safety gate for active capture/finalization.

## Evidence record

Validation records only bundle identity, signature metadata, permission state,
process exit timing, and test names. It must not contain audio, transcript text,
credentials, raw TCC database contents, or private meeting content.
