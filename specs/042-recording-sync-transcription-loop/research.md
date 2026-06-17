# Phase 0 Research: Recording Sync And Transcription Loop

Date: 2026-06-18

## Decision: Keep server-mediated resumable upload with server-authoritative truth

**Decision**: Reuse the existing 2brain Rec upload API instead of adopting a
full tus server in `042`. Align the behavior with tus-style best practices:
server accepted offsets/ranges are authoritative, every part carries checksum
truth, and reconnect resumes from server state instead of local guesses.

**Rationale**: The repo already has server-mediated upload sessions,
`accepted_bytes_by_track`, missing ranges, checksums, MinIO writes, and desktop
queue retries. Full tus adoption would add protocol surface and migration cost
without changing the core MVP need. The tus protocol still provides the right
benchmark: offset agreement, checksum verification, termination/expiry, and
explicit upload resource state.

**Alternatives considered**:

- Full tus server/client adoption: rejected for `042` because it duplicates
  accepted server-mediated API work and would broaden integration risk.
- Direct-to-MinIO upload: rejected because it violates the existing desktop
  no-secret/no-signed-storage-boundary and needs separate security review.
- Restart full upload after reconnect: rejected because it wastes bandwidth and
  makes large offline recordings fragile.

**Sources**:

- tus resumable upload protocol: <https://tus.io/protocols/resumable-upload>
- IETF draft on `Upload-Offset` agreement:
  <https://www.ietf.org/archive/id/draft-tus-httpbis-resumable-uploads-protocol-00.html>
- tus-js-client serious reference implementation:
  <https://github.com/tus/tus-js-client>
- Uppy tus docs:
  <https://uppy.io/docs/tus/>

## Decision: Use local-first durable queue, not optimistic-only UI state

**Decision**: The desktop app must persist upload state locally first and
reconcile from server state on reconnect, app launch, queue view, and retry.
Visible states must distinguish queued, uploading, retrying, uploaded, blocked,
failed, local-only, deleted/denied, and conflict.

**Rationale**: Offline recording only helps if the local package and queue
survive network loss, app restart, and partial server acceptance. Optimistic UI
without durable local state creates false success or hidden rollback. A local
queue with server reconciliation is compatible with the existing JSON queue and
can later move to SQLite/CoreData if volume demands it.

**Alternatives considered**:

- Server-only state: rejected because recordings must exist before network.
- Local-only state after upload: rejected because desktop would drift from
  deletion/access/processing truth.
- Silent last-writer-wins sync: rejected because audio/transcript lifecycle
  conflicts are privacy-sensitive and must be visible.

**Sources**:

- Apple URLSession robust resumable transfer guidance:
  <https://developer.apple.com/videos/play/wwdc2023/10006/>
- Apple URLSession uploads and downloads documentation:
  <https://developer.apple.com/documentation/foundation/urlsession>
- Local-first/offline-first design tradeoffs:
  <https://evilmartians.com/chronicles/cool-front-end-arts-of-local-first-storage-sync-and-conflicts>
- Nextcloud Desktop sync client as serious desktop sync reference:
  <https://github.com/nextcloud/desktop>

## Decision: Add explicit `MediaRevision` in 042, but no editing runtime

**Decision**: Introduce a server `MediaRevision` and local
`localMediaRevisionId` for the initial accepted recording. Bind upload sessions,
track artifacts, processing jobs, MediaScribe jobs, processing results,
transcripts, lifecycle, and deletion accounting to the revision. Keep one
logical `Meeting` row for the real meeting.

**Rationale**: The current meeting-only model is enough for one upload, but it
blocks future trim, video, replace, restore, and reprocess without duplicating
meetings or mutating accepted media. Adding the identity boundary now keeps the
MVP simple while avoiding a later data migration that would have to reinterpret
uploaded transcript history.

**Alternatives considered**:

- Store edits as new meetings: rejected because it breaks user mental model and
  duplicates review/deletion/access state.
- Mutate accepted track artifacts in place: rejected because it breaks
  auditability and processing provenance.
- Delay revision model until editing feature: rejected because `042` is the
  first loop that creates the long-lived meeting/transcript relationship.

**Sources**:

- Krisp upload/transcribe and meeting workspace pattern:
  <https://help.krisp.ai/hc/en-us/articles/16411029727260-Upload-and-transcribe-audio-video-files-with-Krisp>
- Krisp meeting dashboard/help pattern:
  <https://help.krisp.ai/hc/en-us/articles/10291109632412-Meetings-page-in-account-dashboard>
- Krisp recording FAQ:
  <https://help.krisp.ai/hc/en-us/articles/12216182124956-FAQ-about-Krisp-Recording-feature>

## Decision: Key processing idempotency by accepted media revision

**Decision**: Processing workflow identity should include the accepted
`media_revision_id`, e.g. `processing/<media_revision_id>`, and imports should
reuse existing successful results for the same revision.

**Rationale**: Temporal can retry workflows and activities, but external side
effects still need application-level idempotency. If future revisions are
processed, meeting-only workflow uniqueness would either block reprocessing or
overwrite result meaning. Revision-keyed processing keeps retries safe and
future edits explicit.

**Alternatives considered**:

- Keep workflow identity as `processing/<meeting_id>`: rejected because it
  prevents multiple explicit revisions later.
- Generate a new workflow for every retry: rejected because it can duplicate
  MediaScribe submissions.
- Let MediaScribe dedupe implicitly: rejected because desktop/server truth must
  not depend on opaque third-party behavior.

**Sources**:

- Temporal activity idempotency documentation:
  <https://docs.temporal.io/activity-definition>
- Temporal durable execution idempotency article:
  <https://temporal.io/blog/idempotency-and-durable-execution>
- Temporal queues/workflows reliability article:
  <https://temporal.io/blog/reliable-data-processing-queues-workflows>

## Decision: Reuse server-owned cabinet UI for web and desktop display

**Decision**: Keep the transcript/review UI server-owned and embedded in the
desktop shell through the existing `/desktop/meetings` routes. Add revision and
sync provenance to API/view models instead of building a separate native
transcript UI in `042`.

**Rationale**: The repo already has a web cabinet and desktop embedding
boundary. Building a second native transcript UI would duplicate access,
governance, deletion, and no-secret policy. Desktop-native ownership remains
capture, local queue truth, visible controls, and retry actions.

**Alternatives considered**:

- Native-only transcript display: rejected because it duplicates web review and
  risks inconsistent access/deletion truth.
- Web-only with no desktop link: rejected because `042` requires display in the
  installed desktop app.
- Editing-oriented review UI: rejected because editing is reserved for
  post-MVP features `044`-`047`.

**Sources**:

- Existing 2brain Rec feature `016-meeting-dashboard-review`
- Existing 2brain Rec feature `033-desktop-cabinet-embedding`
- Krisp meeting review/share pattern:
  <https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp>
