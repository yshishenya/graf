# Contract: Automatic Recording Runtime

## 1. Source contract

- AudioHAL parser emits only `.audioHAL` events.
- Control Center microphone attribution diffs emit only `.sensorIndicator` events.
- Repeated transitions are idempotent per `(bundleID, source)`.
- A bundle is active while at least one source is active.
- End grace and auto-stop begin only when all sources are inactive.

## 2. Eligibility and authorization contract

- Unknown, browser/manual-only, diagnostic-only, suppressed and media-playback
  signals never become prompt/auto-start targets.
- Before showing an automatic-start countdown, the app requires current target,
  capture readiness, authenticated current workspace policy and exact device-local
  acknowledgement.
- Immediately before button, timeout or saved-target capture, the app reevaluates
  all current gates through the existing start decision.
- Manual Record and Stop keep their existing policy boundary and do not acquire an
  assisted-auto-start acknowledgement requirement.

## 3. Trigger delivery contract

- A detector output is an offer, not proof that it was handled.
- Consumer acceptance closes the continuous candidate against duplicates.
- Skip and manual Stop are terminal for that continuous candidate.
- Transition/readiness/auth/cache/competing-prompt failures may be classified
  retryable and offered again after at least 2 seconds while still active.
- Terminal policy/eligibility/user failures are not retried before the end boundary.
- At most one recording and one auto-stop outcome are attached to a candidate.

## 4. Observer contract

- One supervisor owns at most one `/usr/bin/log` child.
- Startup/restart/wake resets stale detector state and applies a filtered current
  snapshot before consuming live events.
- Snapshot history is sensor-attribution-only, bounded to two hours and a hard
  3.5-second runtime deadline; only its final complete attribution set is
  published atomically.
- A missing, redacted, truncated, failed or timed-out snapshot produces no
  candidate and proceeds fail-closed to live observation.
- Unexpected live completion is recorded and retried after 1 second.
- Deliberate stop/termination cancels pending retry and does not respawn.
- Wake requests a new generation; it cannot leave the prior completed task as the
  sole observer reference.

## 5. Auth contract

- For the configured same-origin auth cookie, WebKit is authoritative on every
  navigation completion sync.
- Replacement removes old native same-scope values before inserting current ones.
- Absence in WebKit removes native same-scope values.
- Native selection is deterministic and ignores empty, expired, scheme/domain/path
  incompatible cookies.
- No general browser `Cookie` header is forwarded and no value is logged.
- Successful reconciliation permits the existing registry refresh to replace a
  stale cache; failure remains fail closed for assisted start.

## 6. Diagnostic contract

Allowed: event name, source enum, bundle ID, active/inactive, candidate phase,
stable blocker/result code, retryability, observer generation/phase and timestamp.

Forbidden: raw system log line, raw audio, transcript, meeting title/content,
cookie/token/credential/password value, signed URL and live secret path.

Every synthetic scenario must allow reconstruction of:

```text
source transition -> candidate decision -> consumer result
                  -> start reason/capture result -> all-source end/stop result
```
