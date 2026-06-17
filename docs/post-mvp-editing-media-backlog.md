# Post-MVP Editing And Media Backlog

Date: 2026-06-18

This backlog captures product-improvement work that is intentionally outside
the `042-recording-sync-transcription-loop` MVP. The MVP must prove recording,
offline-safe upload, server transcription, and transcript display first. Editing,
reprocessing, and full video review should build on that loop later without
creating duplicate meeting entities.

Number allocation lives in `docs/feature-registry.md`. At the time this backlog
was written, `043-app-zoom-shortcuts` already existed in git history, so the
first free reserved product-improvement number here is `044`.

## Design Rule For Future Work

- Keep one logical `Meeting` for one real meeting.
- Treat accepted media as immutable.
- Represent local trim, replace, reprocess, and future video as new
  `MediaRevision` records under the same meeting.
- Tie upload sessions, processing runs, transcript revisions, lifecycle truth,
  and deletion accounting to the relevant media revision.
- Do not mutate accepted audio/video files in place.
- Do not duplicate meetings to represent edits, retries, or reprocessing.

## Reserved Feature Candidates

### 044-local-media-trim-revisions

**Status**: Reserved backlog, post-MVP product improvement.

**Goal**: Let the owner trim or edit local audio/video media on device before it
is accepted for upload, creating a new media revision under the same meeting.

**Scope Notes**:

- Local-only trim/edit UI and validation.
- Edit decision list or equivalent metadata-safe revision record.
- Superseded revision lifecycle, retention, and deletion truth.
- No server-side destructive mutation of accepted media.
- No transcript editing unless a later spec explicitly includes it.

### 045-online-transcript-edit-sync

**Status**: Reserved backlog, post-MVP product improvement.

**Goal**: Let authorized users edit transcript text and speaker labels online
without losing server/client consistency.

**Scope Notes**:

- Transcript revision identity.
- Optimistic locking or equivalent expected-version checks.
- Segment-level edit operations and conflict states.
- Audit and rollback/revert truth.
- No audio/video media trimming in this slice.

### 046-video-capture-package-foundation

**Status**: Reserved backlog, post-MVP product improvement.

**Goal**: Add video-capable capture package support without changing the
audio-first `042` MVP promise.

**Scope Notes**:

- Future screen video and/or camera video tracks.
- Shared timeline with microphone/system audio.
- Larger-file upload/retry limits and metadata-safe diagnostics.
- Video track lifecycle, retention, deletion, and storage accounting.
- Transcript still derives from approved audio/media processing boundaries.

### 047-media-reprocess-replace-flow

**Status**: Reserved backlog, post-MVP product improvement.

**Goal**: Support explicit owner-controlled replace, reprocess, and restore
flows after a media revision has already been accepted or processed.

**Scope Notes**:

- New media revision creation from explicit replace/reprocess action.
- Processing result invalidation and new processing run truth.
- Review UI warnings when transcript/notes belong to an older revision.
- Revert/restore metadata and lifecycle accounting.
- No silent overwrite of accepted media or transcript results.

## Relationship To 042

Feature `042` should not implement the features above. It should only keep the
identity and lifecycle model compatible with them: one meeting, immutable
accepted media, revision-ready upload/processing/transcript truth, and visible
conflict states when local and server truth disagree.
