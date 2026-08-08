# Processing, Lifecycle and Rollback Contract

## Server Validation

Validation binds source kind, exact role set and descriptor shape at both upload session creation and finalization. A role set alone is insufficient.

| Source kind | Role set | Authoritative ASR input |
| --- | --- | --- |
| `initial_recording` (historic) | `manifest,microphone,system` or plus `playback` | historic microphone + system dual input |
| `initial_mixed_recording` (v5) | exactly `manifest,media,playback` | one `media` WAV |
| `manual_upload` | exactly `manifest,media` | one manual `media` input |

For v5, validation rejects an incorrect codec, rate, channel count, byte count, digest, duration, role or immutable revision identity. Accepted packages cannot later change source kind or authoritative digest.

## MediaScribe Egress

```text
desktop package → GRAF object storage → server staging of media WAV only
                → POST /v1/audio/transcriptions (one file, *.wav, audio/wav)
```

- Desktop never contacts MediaScribe or stores its credentials.
- Internal `wav-pcm-s16le` maps explicitly to HTTP `audio/wav` and a `.wav` multipart name.
- `meeting-review.m4a`, microphone and system roles are absent from a v5 ASR request.
- One accepted revision owns one external job. If a POST outcome is unknown, record a safe blocked state and do not retry with a second job.
- Poll/import stays revision-bound and idempotent; result timestamps and speaker boundaries come from the one ASR result rather than a two-result merge.

## Bounded Operational Outcomes

- Every MediaScribe HTTP request uses the existing explicit 30-second request timeout. A connection failure conclusively before request delivery may use the established retry lifecycle; any timeout or malformed/ambiguous response after delivery might have occurred is an unknown submission outcome and blocks automatic resubmission.
- Staging is limited to the existing accepted-audio size policy and available temporary capacity. Missing object, size/digest mismatch or invalid WAV yields a source-input block; unavailable temporary storage yields the existing bounded retryable storage state.
- Polling, result parsing and playback normalization preserve their existing finite workflow/deadline policy. Malformed provider data, unavailable provider and deletion/lifecycle conflicts remain typed, content-safe statuses; none may create an unbounded loop or publish a false result.

## Playback and Deletion

The existing playback-normalization pipeline validates/reuses the v5 `playback` candidate. It must select the `media` artifact—not historic mic/system tracks—when it needs the revision's authoritative source fingerprint.

When a meeting is deleted or reaches its accepted retention outcome, existing revision-bound deletion handles all v5 artifacts: canonical WAV, playback candidate/canonical derivative, temporary upload parts, processing job/state, transcript/diarization and local purge task. Evidence states only what GRAF controls; external-provider deletion remains independently truthful.

## Control Period and Rollback

1. Keep the pre-v5 rollback procedure and candidate baseline reference documented; do not install or rehearse it before v5 has a quality failure.
2. Make server support additive: historic dual and v5 readers/validators are available before v5 desktop capture is installed.
3. Validate v5 on controlled synthetic and installed-app recordings. No personal meeting data is used as test evidence.
4. If the v5 quality gate fails, verify and return only future recording to the selected pre-v5 desktop baseline. Do not alter accepted v5 revisions, create a dual fallback, replace their transcript or make a second external job.
5. Keep server v5 reader/processing support until every accepted v5 revision is processed or terminal/deleted under its lifecycle. Do not roll the server below that compatibility point.
6. After v5 acceptance and historic dual drain/explicit retirement, remove active dual capture/upload/submission/merge/echo code. Preserve only bounded historical reader/display support until retention expires.

No live user-facing switch exists. Rollback is a contingency operator decision and requires the separate release/deploy approval gate; it is not a current v5 closeout gate while the new path passes.
