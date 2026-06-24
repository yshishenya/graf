# Contract: Processing Result Delivery

## Purpose

Define how an accepted upload becomes a transcription/diarization result visible
in web and desktop review.

## Trigger

After a server finalizes an upload as an accepted media revision:

1. If processing is enabled and dependencies are configured, the server starts
   or reuses processing for that accepted media revision without operator
   action.
2. If processing is disabled or dependencies are unavailable, upload remains
   successful and processing status becomes a visible blocked or not-submitted
   state with a safe reason.
3. Finalization must not wait for transcription or polling to finish.

## Idempotency

For one accepted media revision:

- repeated pickup reuses any open workflow;
- repeated worker start does not create duplicate external submissions when a
  job is already submitted or ready;
- repeated import of the same result version and source hash does not duplicate
  transcript or diarization rows;
- retryable failures preserve the same meeting and media revision identity.

## Status Visibility

Product surfaces must distinguish:

- upload accepted;
- processing not submitted;
- processing starting;
- workflow started;
- submitted to transcription dependency;
- polling;
- importing;
- processed/ready;
- partial result;
- retryable failure;
- blocked dependency;
- blocked package;
- terminal failure.

Upload success must remain visible even when transcription is blocked or failed.

## Result Visibility

When processing imports transcript and diarization:

- web review shows transcript availability, diarization availability,
  source/provenance labels, and review status for the accepted media revision;
- desktop embedded review shows the same state as web review for the same
  meeting and media revision;
- status-only endpoints may expose availability booleans and safe reason codes
  but must not expose transcript text.

## Failure And Deletion

- Deleted or unauthorized meetings must not expose transcript results.
- Dependency failures must expose safe reason codes, not provider payloads.
- A terminal processing failure must not imply that local recording or server
  upload failed.
- Reprocessing or derived cleanup is outside this feature unless a later spec
  creates a new accepted media revision.

## Evidence Rules

Validation evidence may include counts, statuses, timing, workflow/job presence,
hash equality, and content availability booleans. It must not include raw audio,
transcript text, private meeting content, credentials, signed URLs, secret
paths, or private local paths.
