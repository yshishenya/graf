# Production E2E Proof Plan

**Feature context**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Purpose

This runbook defines the metadata-safe proof required before claiming that the
MVP recording-to-result loop works outside local tests and fixtures.

The proof target is:

```text
controlled recording -> upload/finalize -> processing workflow ->
MediaScribe result import -> transcript/diarization available ->
web cabinet review -> desktop embedded review
```

## Approval Boundary

Do not run production mutations without explicit owner approval.

Approval-gated actions include:

- committing, pushing, opening, merging, or releasing the 045 branch;
- replacing the installed macOS app;
- running `infra/scripts/cd-remote.sh --execute`;
- uploading a production test recording;
- starting production processing jobs;
- deleting or modifying production records created during proof.

The non-mutating deploy preflight is:

```sh
infra/scripts/cd-remote.sh --dry-run
```

Current preflight status:

- `infra/scripts/cd-remote.sh --dry-run`: passed locally on 2026-06-24 and
  reported branch `045-transcription-results-pipeline`, remote host
  `2brain.dev`, remote path `/opt/projects/2brain-rec`, local CI required, and
  the production gate sequence. This does not deploy and does not prove
  production runtime behavior.
- Latest post-web-runtime recheck on 2026-06-24: `infra/scripts/cd-remote.sh
  --dry-run` still passed with `deploy_result=dry_run`, and a 045 include-set
  patch generated from 36 tracked paths plus 25 untracked include paths passed
  `git apply --check` in a detached temporary worktree at `origin/master`
  `a89cf91`. The temporary worktree was removed after the check. This reduces
  PR/deploy-preflight risk, but it still does not deploy, does not prove
  production runtime behavior, and does not replace the approval-gated
  production e2e proof below.

Previous production e2e evidence for earlier processing slices, such as
`015-mediascribe-processing-pipeline`, is not sufficient for this proof. The
production run below must execute against the intended 045 commit because this
feature changes upload eligibility, finalize-triggered processing dispatch,
desktop/web review state, and metadata-safe evidence boundaries.

## Required Preconditions

1. The 045 implementation is merged into the intended release branch.
2. The production deploy target is known and matches the intended git remote.
3. Local CI and focused 045 validation have passed after any merge/rebase.
4. Production deploy execute has passed with pinned commit evidence.
5. A controlled, non-sensitive test recording is available.
6. Evidence capture is configured to store only metadata, booleans, safe reason
   codes, IDs already allowed by policy, timings, and command/test results.

## Test Recording Policy

Use only controlled non-sensitive audio. Do not use a private meeting or private
customer recording.

Allowed evidence:

- synthetic or owner-approved test recording label;
- duration bucket or exact duration when non-sensitive;
- safe media revision id;
- safe meeting/upload identifiers if already allowed by project policy;
- processing state and safe reason code;
- transcript availability boolean;
- diarization availability boolean;
- speaker/provenance availability boolean;
- start/end timestamps for processing duration;
- UI route/status observed.

Forbidden evidence:

- raw audio or video;
- transcript text;
- private meeting title, participant names, or customer account text;
- provider raw payloads;
- signed URLs or object keys;
- credentials, API keys, tokens, passwords, secret paths;
- screenshots containing private account, meeting, or transcript content.

## Production Proof Steps

### 1. Deploy Gate

Run and record metadata-only output:

```sh
infra/scripts/cd-remote.sh --dry-run
```

After owner approval and release readiness:

```sh
infra/scripts/cd-remote.sh --execute
```

Required evidence:

- branch/ref and pinned SHA;
- backup reference created by the deploy script;
- restore rehearsal passed;
- compose config secret scan passed;
- runtime secret env scan passed;
- production smoke passed;
- `/api/v1/health/live` passed;
- `/api/v1/health/ready` passed.

### 2. Controlled Upload And Finalize

Using the approved desktop app or an approved metadata-safe upload harness,
upload the controlled recording package and finalize it.

Required evidence:

- upload accepted;
- finalization accepted;
- integrity gates passed;
- quality/readiness warnings, if present, are diagnostic-only;
- unsafe conditions still block if deliberately tested separately;
- desktop did not call MediaScribe directly and did not hold MediaScribe
  credentials.

### 3. Processing Start Or Reuse

Observe processing state after accepted finalization.

Required evidence:

- exactly one processing workflow was started or an existing one was reused;
- no duplicate MediaScribe job was created for the same accepted media revision;
- dependency-blocked state, if it occurs, preserves upload success;
- status payload remains metadata-only.

### 4. MediaScribe Result Import

Wait for the approved processing job to complete or fail.

Required evidence for success:

- workflow status reaches `processed` or equivalent ready state;
- MediaScribe job reaches the safe ready/imported state;
- transcript availability is true;
- diarization availability is true or a truthful partial reason is shown;
- accepted media revision identity matches the imported result;
- processing duration is recorded.

Required evidence for failure:

- failure/blocker reason is safe and actionable;
- upload success remains visible separately from processing failure;
- no raw provider payload is exposed in status, logs, diagnostics, or evidence.

### 5. Web Cabinet Review

Open the production web cabinet under a real owner session.

Required evidence:

- owner-auth session can access the meeting;
- unauthenticated access is rejected;
- transcript availability state is visible;
- diarization/provenance availability state is visible;
- ready, partial, failed, or blocked state is truthful;
- no transcript text or private meeting content is copied into evidence.

### 6. Desktop Embedded Review

Open the same processed meeting from the desktop app.

Required evidence:

- desktop sync sees the same accepted media revision;
- desktop review link resolves to the owner-auth review surface;
- desktop embedded state matches the web cabinet state;
- auth/missing-auth states remain safe;
- no MediaScribe secret or provider payload reaches the desktop.

### 7. Privacy And Cleanup Check

After the run, inspect only metadata-safe logs/status surfaces.

Required evidence:

- no raw audio, transcript text, signed URL, provider payload, credential, token,
  or private local path appears in status, diagnostics, test evidence, or logs
  collected for the proof;
- any test data cleanup action is recorded by safe identifier and result;
- deletion/access state remains authoritative if cleanup is performed.

## One-Hour Budget Check

The MVP target is processing an hour of audio in no more than 3 minutes of
product-observed processing time.

The existing one-hour benchmark proves product-owned orchestration with fake
dependencies. Production proof needs a separate long-recording run only when
the provider/network path is approved for measurement.

Required long-run evidence:

- controlled non-sensitive one-hour recording;
- upload/finalize timing;
- processing start time;
- result import time;
- total product-observed processing duration;
- whether provider/network latency, object storage throughput, or product
  orchestration dominated the run.

## Halt Criteria

Stop the production proof and keep the MVP gap open if any of these occur:

- branch/ref does not match the intended release commit;
- deploy script blocks on dirty worktree, SHA mismatch, backup, restore,
  compose config, secret scan, runtime scan, smoke, or health;
- upload/finalize accepts an unsafe package that should be blocked;
- accepted finalize creates duplicate processing attempts;
- desktop directly calls MediaScribe or contains MediaScribe credentials;
- transcript text, raw audio, signed URLs, credentials, or private meeting
  content appear in status, diagnostics, logs, screenshots, or evidence;
- web and desktop review disagree on result readiness for the same accepted
  media revision;
- owner-auth access fails or unauthorized access succeeds.

## Acceptance For Closing The Production MVP Gap

The production upload-to-transcript-to-review gap can be marked proven only
when one approved run shows:

1. production runs the intended 045 commit;
2. deploy smoke and health are green;
3. controlled recording upload/finalize is accepted;
4. processing starts or reuses exactly one workflow/job;
5. MediaScribe result is imported or a truthful partial/failure state is shown;
6. transcript availability and diarization/provenance availability are visible;
7. web cabinet and desktop embedded review agree;
8. auth, deletion/access, privacy, and content boundaries hold;
9. evidence remains metadata-only.
