# Evidence Rules for Feature 106

Feature 106 is a high-risk capture, storage, processing and installed-app
change. Evidence proves behavior without retaining user content.

## Allowed Evidence

- command name, exit status, test count and non-secret warning class;
- source revision, tag name, package schema and artifact hash;
- artifact member count/name class, format/rate/channel result, duration,
  marker-lag metric, gap/drop count and lifecycle status;
- upload-progress state transitions, one-job count, deletion state and
  rollback pass/fail/deferred verdict.

## Never Record

- audio bytes, decoded samples, waveform screenshots or spoken marker text;
- transcript, diarization text, meeting title, device name, local path,
  credential, signed URL, provider payload or private identifier;
- a claim that a release, deployment, install or physical-device check ran
  without its separate approval and recorded metadata-only result.

## Receipt Template

Use this shape for a new safe receipt. Omit unknown fields; never replace them
with invented values.

```text
date:
baseline_ref: optional contingency reference
baseline_sha:
candidate_sha:
schema: local-recording-manifest.v5
scope: synthetic | installed-app
checks: command/status/count only
package: member-class/format/duration/hash-count only
timeline: pass|fail|open, lag-ms only
route_and_volume: pass|fail|open, delta-db only
upload_and_processing: pass|fail|open, job-count/status only
deletion: pass|fail|open
rollback: pass|fail|deferred|open
limitations:
```

The user-confirmed, still-in-progress parallel `v2026.07.16.7` work is not an
interchangeable rollback baseline. While v5 passes its quality gates, rollback
is recorded as `deferred`; if a quality failure triggers it, rollback changes
only the next controlled capture. It never
rewrites an accepted v5 revision or introduces a hidden dual-provider retry.
