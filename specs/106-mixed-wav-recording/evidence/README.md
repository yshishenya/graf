# Evidence Rules for Feature 106

Feature 106 is a high-risk capture, storage, processing and installed-app
change. Evidence proves behavior without retaining user content.

## Allowed Evidence

- command name, exit status, test count and non-secret warning class;
- source revision, tag name, package schema and artifact hash;
- artifact member count/name class, format/rate/channel result, duration,
  marker-lag metric, gap/drop count and lifecycle status;
- upload-progress state transitions, one-job count, deletion state and
  rollback pass/fail verdict.

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
baseline_ref: v2026.07.17.6
baseline_sha: 4be444e82ec449a3bb5312920fb0cd6008072c56
candidate_sha:
schema: local-recording-manifest.v5
scope: synthetic | installed-app
checks: command/status/count only
package: member-class/format/duration/hash-count only
timeline: pass|fail|open, lag-ms only
route_and_volume: pass|fail|open, delta-db only
upload_and_processing: pass|fail|open, job-count/status only
deletion: pass|fail|open
rollback: pass|fail|open
limitations:
```

`v2026.07.17.7` is parallel work and is not an interchangeable rollback
baseline. A rollback changes only the next controlled capture; it never
rewrites an accepted v5 revision or introduces a hidden dual-provider retry.
