# Contract: App Recording Status

## Purpose

Ensure AEC3 candidate, problem, rollback, and fallback-relevant states are
visible in the macOS app without leaking private content or creating noisy
technical UI.

## Required Status States

| State | Meaning | User Action |
|---|---|---|
| `notEvaluated` | No AEC3 evidence is active for the recording | None |
| `evaluatingAEC3` | Candidate evidence is being evaluated for the built-in route | Continue recording; Stop remains available |
| `usingOriginalMicTruth` | Original microphone truth is authoritative | None or review status |
| `candidateBlocked` | AEC3 is blocked by route, quality, stability, dependency, or diagnostics | Continue with current limitations or review status |
| `promotedBuiltinRoute` | Built-in Mac mic/speakers passed all gates and the promoted candidate is active | Continue recording; Stop remains available |
| `rolledBackToOriginal` | A previously promoted candidate became unsafe and original mic truth is restored | Continue recording or review status |
| `fallbackRelevant` | Evidence points to `040` fallback decision or user guidance | Review status or use a safer route |
| `requiresUserAttention` | User can improve the route, for example by choosing headphones or retrying a check | Take the shown action |

## Copy Rules

- Copy must be calm, short, and route-scoped.
- Copy must say whether the app is using original microphone truth or an
  accepted promoted candidate when that distinction matters.
- Copy must not claim clean speakerphone recording outside built-in Mac
  microphone plus built-in Mac speakers.
- Copy must not expose raw audio, transcript text, meeting content,
  participant names, credentials, signed URLs, object keys, private local paths,
  or unnecessary implementation details.
- Stop must remain visible and available while recording is active.
- Normal evaluation, original-microphone-truth, blocked, rollback, and
  fallback-relevant states belong in the recording status surface, not as
  repeated modal alerts or noisy toast loops.
- Interruptive attention states are allowed only when the user can take a clear
  immediate action, such as choosing headphones, retrying a check, or stopping
  recording.

## Consistency Rules

- App status must match manifest/package truth.
- Rollback state must be visible after rollback and must remove the
  clean-recording claim.
- Blocked or unproven states must not contain the words `clean`, `чист`,
  `cleaned`, `speakerphone_clean`, or equivalent claim language.
- Status priority must be deterministic when multiple states apply: active
  capture and Stop availability first, then rollback, promoted built-in route,
  blocked/problem, fallback relevance, evaluation, and original microphone
  truth.
- Stale, missing, or contradictory app status blocks immediate promotion.
