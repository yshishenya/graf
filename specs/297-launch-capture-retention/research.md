# Research: F297 — Capture continuity, retention truth, public copy

## 1. Recording continuity on macOS system audio

**Decision**: Keep one canonical recording across a default output-device change or a short system-audio gap. For a short forward gap, insert bounded silence into the system reference and continue the timeline. For a route change, rebase the new ScreenCaptureKit stream onto the existing output frame timeline and continue with the existing AEC3 processor. If rebasing cannot be trusted, preserve the playable prefix and allow it to be uploaded as an explicitly marked partial recording.

**Rationale**:
- ScreenCaptureKit delivers audio in separate stream callbacks and can stop or change its stream when the default output device changes. Apple's `SCStream`/`SCStreamDelegate` contract requires treating stream termination as an event to handle, not as a reason to discard the user's session.
- Core Audio route changes are normal user actions: AirPods, headphones, dock, display speakers. A recorder that stops on this event is not usable for real meetings.
- WebRTC AEC3 expects a contiguous 10 ms render/capture timeline. Rebuilding the frame counter and inserting a short silence bridge preserves that contract better than passing a discontinuous PTS or dropping the new route.
- The existing `RecordingAudioTimeline` already has a bounded `maximumKnownGapSeconds` and a `recoverableClockDelta` path; extending the same policy is lower risk than inventing a second audio pipeline.

**Alternatives considered**:
- Stop recording and ask the user to start a new one: rejected — loses the meeting and violates the product promise of one recording.
- Buffer the entire call and retry at the end: rejected — unbounded memory, no live recovery.
- Silent AEC reset without frame rebase: rejected — new stream PTS may reset to zero and samples would be trimmed.
- Filling all gaps with silence: rejected — real source loss must remain visible and fail closed above the bound.

**References**:
- Apple, `SCStream` and `SCStreamDelegate` (stream lifecycle and `stream(_:didStopWithError:)`): https://developer.apple.com/documentation/screencapturekit/scstream
- Apple, `AVAudioEngine` configuration change handling: https://developer.apple.com/documentation/avfaudio/avaudioengine
- Apple, Core Audio default output device property: https://developer.apple.com/documentation/coreaudio/audiohardwarepropertydefaultoutputdevice
- WebRTC Audio Processing (AEC3) render/capture 10 ms contract: https://webrtc.googlesource.com/src/+/refs/branch-heads/6613/modules/audio_processing

## 2. Short system-audio gap policy

**Decision**: Close only a **short** forward gap up to `maximumBridgedGapSeconds` (500 ms) for the system reference; the microphone remains fail-closed for missing coverage. A gap within the short bound but beyond the 1 ms clock-recovery window is bridged with zeros, counted in metrics, and logged as a relative event. A gap between 500 ms and `maximumKnownGapSeconds` (15 s) is not masked: it produces a partial result or stops with a preserved prefix. A gap above 15 s still throws `gapExceedsBound`.

**Rationale**: The current code allows the gap through `gapFrames <= maximumKnownGapFrames` but then `hasCoverage` fails and throws `renderReferenceMissing`. That is an internal inconsistency: a bounded gap should either be bridged or rejected explicitly. Bridging only a short system-reference gap matches the physical meaning (brief no incoming system audio) and avoids losing the call. Longer gaps are real lost speech and must remain visible. Microphone silence is not inserted because lost local speech is material.

**Alternatives considered**:
- Always fail on any gap: current behavior; rejected as the cause of the launch blocker.
- Bridge both sources: rejected — hides lost microphone speech.
- Bridge only gaps <= 50 ms and fail otherwise: partially considered; rejected because it would still abort on routine 50–500 ms route/callback transitions. The chosen 500 ms bound is a separate, explicitly named bridge limit, not the 15 s hard bound.

## 3. Route-change rebase

**Decision**: On `.routeChanged`, set a `routeRebasePending` marker for the source, allow the next `routeGeneration`, and on the first real batch compute a per-source offset so its first frame starts at the current `lastInputEndFrame`. The existing AEC3 processor is reused; no new processor is created mid-recording. The event is counted (`continuityRouteChangeCount`) and surfaced as a non-blocking notice, not an error.

**Rationale**:
- Creating a new AEC3 processor mid-recording would reset the echo path and add complexity; reusing it is safer for a short transition.
- Rebase ensures no frame loss and no negative timestamps when SCK restarts with a fresh clock.
- If the new stream never produces valid audio or the gap is too large, the existing fail-closed path remains and the partial-upload fallback applies.

**Alternatives considered**:
- Start a second meeting: rejected — user loses one-meeting continuity.
- Create a new AEC processor per segment and concatenate: deferred — possible future improvement, not needed for the first fix.
- Ignore route generation changes entirely: rejected — could splice unrelated streams with wrong clocks.

## 4. Partial recording fallback

**Decision**: If continuity fails after a playable prefix exists, map the specific continuity errors (`routeGenerationChanged`, `renderReferenceMissing`) to the existing upload-safe `timelineMisaligned` failure and mark the manifest/UI as a partial recording. Do not use this path for AEC failure, invalid samples, format change, or missing required source.

**Rationale**: The user gets the recorded part and a transcript of it instead of a dead local file. The distinction preserves fail-closed behavior for corrupt or untrustworthy audio.

**Alternatives considered**:
- Keep `captureFailed` and block upload: current behavior; rejected as the blocker.
- Upload everything including unverified frames: rejected — violates integrity.

## 5. Retention scheduler

**Decision**: Add a maintenance-loop reconciler that runs `run_retention_scan` for every active workspace once per 24 hours after an operator explicitly enables it. The scheduler is opt-in (`TWOBRAIN_RETENTION_SCHEDULER_ENABLED=false` by default); the operator first runs a per-workspace dry-run and verifies a fresh backup, then enables it. Use `MaintenanceTenantContext` with a new `retention_scan` operation; process bounded batches (100 per workspace); commit per workspace; log only counts and safe reasons.

**Rationale**: The scan already implements deletion fences, policy snapshots, processing/deleting/policy-blocked skips, local purge reconciliation and audit. Reusing it avoids a second deletion path. A daily cadence matches the 365-day policy and is cheap. Destructive deletion is opt-in so a first deployment cannot delete unseen data before backup verification. Legal hold is not implemented in the current server and is explicitly out of F297.

**Alternatives considered**:
- Temporal schedule: more moving parts; the maintenance worker already owns reconcilers.
- Run on each request: unpredictable and destructive; rejected.
- Only admin endpoint: current behavior; rejected as the cause of the policy mismatch.

## 6. Backup retention / prune

**Decision**: Add `infra/scripts/prune-rec-backups.sh` with dry-run by default, `--execute`, `--older-than-days` (default 30), `--backup-root` default `/opt/projects/2brain-rec/backups` from `TWOBRAIN_BACKUP_ROOT`, and strict checks: only directories whose name matches `YYYYMMDDTHHMMSSZ`, complete GRAF backup contract (`postgres.dump`, `schema.sql`, `inventory.jsonl`, `checksums.sha256`, `minio-objects/`), no symlinks, no `.`/`..`, no path outside root, never the newest overall or newest verified backup. Exit codes: `0` success/no candidates, `2` invalid root/arguments, `3` partial deletion failure. Add `infra/systemd/graf-rec-backup-prune.{service,timer}` daily; operator stops the timer to disable. Document production enablement and rollback from the newest backup.

**Rationale**: The privacy policy promises 30-day backup expiry; a host script with dry-run and strict path checks is the smallest safe mechanism. It does not require database access or a new service inside the API container.

**Alternatives considered**:
- Delete from the API container: rejected — backups are host files and the container has no mount.
- Keep backups forever: rejected — policy mismatch.
- Auto-delete without dry-run: rejected — too risky.

## 7. Offer and auto-renewal copy

**Decision**: Keep `recurring_consent` checked by default in checkout. Change the offer to say that auto-renewal is pre-checked, can be unchecked before payment, and does not prevent a one-time payment. Replace “unlimited duration” with the real 4-hour limit in the offer and landing.

**Rationale**: The owner explicitly wants auto-renewal checked by default. The truthful fix is to align the offer, not to change the product behavior. The 4-hour cap is a hard server limit (`le=14_400`), so “unlimited” is false.

**Alternatives considered**:
- Remove `checked`: rejected by owner decision.
- Raise the cap: not in this feature; requires storage/processing capacity evidence.
- Keep “unlimited” and ignore the cap: rejected — false advertising.

## 8. Referral 500

**Decision**: Make `cabinet/auth/analytics.html` tolerate an absent `public_analytics` with a safe default, and pass the real public analytics context from the referral route. Add a regression test that renders the referral page without analytics context.

**Rationale**: The live 500 is caused by `StrictUndefined` on `public_analytics` when `_referral_landing_html` renders `base.html`. The template default fixes the class of bug; passing context keeps analytics working where available.

**Alternatives considered**:
- Only add `public_analytics` at the referral route: fixes one caller, leaves the same trap for future auth pages.
- Disable StrictUndefined: rejected — hides template errors.
