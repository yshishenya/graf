# Research: Review M4A Normalization

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

## Decision: Define the automatic-conversion guarantee precisely

**Decision**: Every accepted source that is valid, contains usable audio, is in
the supported container/codec matrix, and remains within the already accepted
ingest limits must converge automatically to one validated canonical playback
artifact. Neither the user nor a workspace administrator starts retry,
reprocess, or backfill work.

Objectively impossible inputs reach a deterministic terminal state:

- empty or corrupt source;
- no usable audio stream;
- multiple usable audio streams without one unique container-default stream;
- unsupported or encrypted media;
- actual duration, size, or stream count over the documented limit;
- accepted source missing, purged, or digest-mismatched.

Transient infrastructure failures never ask the user to repair the record. A
bounded workflow cycle retries automatically, and the durable reconciler starts
later cycles until the source succeeds or its meeting lifecycle removes it.

**Rationale**: “Any file always works” is not a testable or safe contract. The
guarantee above is complete for every source GRAF explicitly supports and keeps
failure truth honest for impossible inputs.

## Decision: Create durable normalization truth at accepted-source commit

**Decision**: Successful `finalize_upload` upserts a
`PlaybackNormalizationJob` in the same database transaction that marks the
`MediaRevision` accepted and registers its source artifacts. The accepted
transaction commits before either MediaScribe or playback workflows are
started. A post-commit dispatcher performs the fast Temporal start attempt; a
periodic reconciler recovers any job left queued between commit and dispatch.

Normalization is enabled and scheduled independently from
`processing_enabled`. It consumes only accepted `TrackArtifact` rows belonging
to that media revision and never consumes the HTTP upload body, upload parts,
desktop files, or a MediaScribe result.

**Rationale**: The current dispatch is MediaScribe-only and runs before the
caller commits. A direct Temporal start without a durable job leaves a crash
window in which an accepted source can be permanently missed. Durable job first,
external side effect second, and reconciler last closes that window.

**Alternatives considered**:

- Convert inside the upload request: rejected because it makes upload latency,
  browser lifetime, CPU, disk, and failure recovery user-facing.
- Start only a Temporal workflow after finalize: rejected because a crash
  between database commit and workflow start loses work.
- Put playback normalization behind MediaScribe processing: rejected because
  transcript and playback have independent truth and failure modes.

## Decision: Treat uploaded playback as an untrusted candidate

**Decision**: The server accepts both first-party finalize role sets:

```text
manifest + microphone + system
manifest + microphone + system + playback
```

`playback` is an optional derived candidate, not source lineage. Finalize still
checks its uploaded bytes, size, and SHA-256, but persists it with status
`candidate`. It is excluded from the immutable source fingerprint. Only the
normalizer may promote it to canonical `stored` after full byte-level
validation, or supersede it and derive a new artifact from accepted source
roles.

Manual upload remains `manifest + media`; its original `media` artifact never
becomes the playback artifact in place.

**Rationale**: The macOS client already offers `meeting-review.m4a`, but the
server currently accepts only the two exact role sets without playback. Simply
adding the role would trust client-declared codec/rate/channel metadata and make
an unverified file playback-ready.

## Decision: Canonical playback profile v1

The persisted profile identifier is `review_m4a_aac_lc_48k_mono_64k_v1`.

Required properties:

- ISO BMFF M4A container and egress MIME `audio/mp4`;
- exactly one audio stream and no video, subtitle, data, attachment, chapter,
  or fragmented `moof` content;
- AAC-LC, MPEG-4 Audio Object Type 2;
- 48,000 Hz, mono, default disposition;
- target bitrate 64 kbit/s; observed average audio bitrate 56–72 kbit/s for
  byte-for-byte reuse;
- start time within 100 ms of zero;
- `0 < duration <= 14,400` seconds;
- maximum final object size 128 MiB (`134,217,728` bytes);
- `moov` before the first `mdat` for fast-start playback;
- no source/user metadata, chapters, source filename, or private text;
- stored SHA-256/byte length match the complete object;
- full decode with strict error handling succeeds.

Four hours at 64 kbit/s is 115,200,000 bytes. The 128 MiB cap leaves more than
10% plus container overhead while preventing an unbounded output.

The existing Range response remains the playback transport. A request never
transcodes, remuxes, joins, or downloads the whole object into memory.

## Decision: Strict reuse, lossless container repair, then transcode

Validation order:

1. Verify registered byte length and SHA-256 while downloading in bounded
   chunks to a UUID-named private work file.
2. Run bounded `ffprobe` and parse only an allowlisted JSON field set.
3. Parse top-level BMFF boxes with a small stdlib parser to prove box bounds,
   `moov < mdat`, and absence of `moof`.
4. Fully decode the selected audio stream to a null sink using strict errors.
5. Recheck duration, size, profile, and complete digest.

Outcomes:

- A first-party playback candidate that fully passes is promoted without audio
  re-encoding.
- A fully compliant manual-upload M4A is copied byte-for-byte into a separate
  immutable playback object; the accepted source object remains separate.
- An otherwise compliant AAC-LC M4A whose only mismatch is container layout is
  losslessly remuxed with explicit stream copy and `+faststart`. It is not
  treated as byte-for-byte reuse.
- Any audio-profile mismatch or other supported source is decoded and encoded
  to profile v1.
- Every remuxed or encoded output passes the complete gate again before it can
  be published.

**Rationale**: `ffprobe` alone does not prove that the tail of a file decodes.
Lossless remux repairs a non-fast-start container without needless generation
loss; all other mismatches require real normalization.

## Verified local baseline from `test-rec`

Only safe metadata was inspected; no audio or transcript content was emitted.

- The canonical test alias is AAC-LC, 48 kHz, mono, default stream, 64,648
  bit/s audio, 4,453.333 seconds, start time 44 ms, and fully decodes.
- Its `moov` follows `mdat`, so the current AVFoundation artifact needs the
  lossless fast-start-remux branch rather than byte-for-byte promotion.
- The accepted microphone/system test aliases are PCM S16LE, 16 kHz, mono and
  differ slightly in duration. The server fallback must preserve alignment and
  use the longer logical timeline.

This baseline is evidence for the branch design, not proof of the future Linux
runtime. The media-enabled container must repeat the capability and decode
checks.

## Decision: Supported input matrix and explicit audio-stream selection

The v1 matrix is byte-detected and requires both an allowed demuxer family and
an allowed audio codec family:

| Container family | Supported audio codec families |
|---|---|
| WAV/RF64/W64 | PCM integer/float, A-law, mu-law |
| MP3 | MPEG Audio Layer III |
| raw AAC/ADTS | AAC-LC/HE-AAC |
| FLAC | FLAC |
| Ogg | Vorbis, Opus, FLAC |
| M4A/MP4/MOV/M4V | AAC-LC/HE-AAC, ALAC, MP3, PCM |
| WebM | Opus, Vorbis |
| Matroska/MKV | Opus, Vorbis, AAC, MP3, FLAC, PCM |

Encrypted/DRM media, playlists, remote references, executable attachments, and
all other container/codec combinations are unsupported. Extension and MIME are
hints only. The cabinet `accept` list must advertise this exact matrix rather
than unrestricted `audio/*,video/*`; server validation remains authoritative
because drag/drop and API clients can bypass browser hints.

Limits:

- no more than 16 total streams;
- no more than 8 audio streams;
- actual source duration at most 14,400 seconds;
- existing ingest byte limits remain authoritative: 1 GiB manual file, 2.5 GiB
  per track, 5 GiB first-party package.

Selection for a single uploaded media container:

1. Keep only decodable, supported audio streams with usable configuration.
2. If one remains, use it.
3. If multiple remain, use only the one stream whose container disposition is
   uniquely `default`.
4. Otherwise finish as `ambiguous_audio_tracks`.
5. Invoke FFmpeg with an explicit global stream index (`-map 0:<index>`); never
   let automatic stream selection choose the most channels or the first stream.
6. A decode failure of the selected stream is terminal for that source and does
   not silently fall through to another stream.

## Decision: Mirror the existing first-party dual-source mix

The multiple-stream rule above applies to audio streams inside one uploaded
media container. It does not remove the already defined first-party review mix
from two explicit accepted source roles.

When a first-party playback candidate cannot be promoted/remuxed, the server
derives playback from exactly one accepted `microphone` artifact plus exactly
one accepted `system` artifact from the same revision. It mirrors the native
writer's product rule:

```text
mixed_sample = clamp((microphone_sample + system_sample) * 0.5, -1, 1)
timeline = longest input; a missing tail is silence
```

Both streams start at zero, preserve silence alignment, are resampled to the
48 kHz playback profile, and produce one mono output. The current source WAVs
are 16 kHz; resampling meets the playback container contract but is recorded as
`dual_source_16k_fallback` and never claimed as fidelity improvement. Source
WAVs remain unchanged for transcription and custody.

Mixing arbitrary streams inside one manual file, choosing the first stream, or
substituting one missing first-party role is forbidden.

## Decision: Isolate FFmpeg in a dedicated non-root media worker

Use the Debian Bookworm `ffmpeg` package, which includes `ffmpeg` and `ffprobe`,
inside a new media-enabled Docker target. API, migration, and MediaScribe worker
targets remain free of FFmpeg. The release build pins the base-image digest and
Debian snapshot/package version and records safe version/build capability
evidence.

The new `rec-media-worker`:

- uses task queue `twobrain-rec-playback-normalization`;
- runs as the existing unprivileged `twobrain` user;
- has 1 CPU, 1 GiB RAM, and `max_concurrent_activities=1`;
- has a private disk-backed work volume, never tmpfs;
- invokes subprocesses with an argv array and no shell;
- uses `-nostdin`, explicit `-map`, `-protocol_whitelist file`, an explicit
  demuxer allowlist, one codec/filter thread, and no remote protocols;
- caps probe stdout at 256 KiB and stderr at 1 MiB;
- never persists or logs raw FFmpeg stderr, local paths, original filenames,
  object keys, tags, chapters, or media content;
- terminates the whole process group on cancellation or timeout;
- uses private `0700` attempt directories and `0600` files named only by UUID;
- cleans every work directory in `finally` and reaps orphan UUID directories on
  startup.

FFmpeg official documentation confirms that explicit `-map` disables automatic
stream selection, protocols are otherwise allowed by default, `aac_low` is the
AAC-LC profile, and `+faststart` moves `moov` to the beginning:

- [FFmpeg CLI](https://ffmpeg.org/ffmpeg.html)
- [FFprobe](https://ffmpeg.org/ffprobe.html)
- [Protocols](https://ffmpeg.org/ffmpeg-protocols.html)
- [Codecs](https://ffmpeg.org/ffmpeg-codecs.html)
- [Formats](https://ffmpeg.org/ffmpeg-formats.html)
- [Debian Bookworm ffmpeg package](https://packages.debian.org/bookworm/ffmpeg)

## Decision: Exact resource, timeout, and backfill budgets

Resource defaults:

- worker concurrency: 1;
- work-volume configured budget: 6 GiB;
- required free bytes before a job:
  `sum(selected accepted source bytes) + 128 MiB output + 256 MiB reserve`;
- MinIO download chunk: existing 4 MiB path;
- probe timeout: 60 seconds;
- activity start-to-close timeout: 6 hours;
- workflow execution timeout: 12 hours;
- activity heartbeat interval: 30 seconds;
- reconciler interval: 60 seconds;
- workspace scan page: 50;
- per-workspace inventory page: 100;
- dispatch batch: 25;
- active media jobs per worker: 1.

Six GiB covers the existing 5 GiB maximum first-party package plus output and
reserve. The worker validates free space before download and again before
conversion. Insufficient capacity is retryable and never starts partial work.

FFmpeg output uses `-fs 134217728` and a duration guard only as defense in
depth. Because FFmpeg may slightly exceed `-fs` and `-t` can silently truncate,
stat/full-decode/profile validation remains authoritative. An output at the
duration boundary is never published unless the complete source was proved to
end within 14,400 seconds.

The 6-hour activity default must be benchmarked with production-equivalent 1
CPU/1 GiB synthetic near-limit inputs before release. A timeout remains
retryable and does not become user work.

## Decision: Bounded retry cycles with automatic long-term recovery

One Temporal execution uses at most four attempts:

- initial interval: 30 seconds;
- backoff coefficient: 2;
- maximum interval: 15 minutes.

Retryable classes:

- MinIO/network or temporary database failure;
- worker crash/cancellation;
- unavailable temp capacity;
- FFmpeg/ffprobe process spawn or runtime dependency temporarily unavailable;
- output upload/publish transaction interruption;
- timeout or lease expiry.

After four attempts, the job remains `retry_wait`, emits one metadata-only
operational incident, and is picked up automatically after 15 minutes, 1 hour,
6 hours, 24 hours, then once per day while the accepted source remains. Each
cycle is bounded, but transient failure never becomes a terminal state or a
manual retry requirement.

Permanent source failures are not retried blindly. An implementation defect
such as a generated output failing the canonical gate is treated as a retryable
system failure plus operational incident, not falsely blamed on the source.

## Decision: Immutable attempt objects and atomic database visibility

The workflow ID is deterministic:

```text
playback-normalization/<media-revision-uuid>/v1
```

Idempotency layers:

1. one job per `(workspace_id, media_revision_id, profile_version)`;
2. deterministic workflow identity and due-time pickup;
3. one active `stored` playback artifact per media revision enforced by a
   PostgreSQL/SQLite partial unique index;
4. one immutable UUID object key per attempt;
5. row lock on job and meeting before publication.

The attempt row registers its object key before upload. After local validation,
the complete object is uploaded to that unique key. A database transaction then
locks the meeting/job, rechecks source fingerprint and deletion state, and
either publishes one `TrackArtifact` plus the job pointer or marks the attempt
for cleanup. The object is invisible to playback until the transaction commits.

There is no overwrite of a shared deterministic object key and no claim of a
cross-system MinIO/PostgreSQL transaction. An uploaded object left by a database
failure remains registered and is cleaned by retry, deletion, or orphan
reconciliation.

## Decision: Keep playback status independent from transcript status

`Meeting.processing_status` and `ProcessingResult` remain transcript/summary
truth. Playback projection reads the normalization job plus its one validated
canonical artifact.

Projection:

- `queued`, `running`, `publishing`, `retry_wait` -> `preparing`, with copy that
  GRAF continues automatically;
- `ready` plus canonical artifact -> `available`;
- permanent source failure -> `unavailable` with a safe reason;
- `cancelled` or meeting deletion -> `deleted`/`deleting`;
- missing job on an accepted revision -> `preparing` while reconciler repairs
  the gap, never a retry button.

The existing route streams only the stored artifact and preserves byte ranges.
It never gates audio on imported transcript state. List, review, browser, and
embedded macOS cabinet use the same server read model. No user/admin retry,
reprocess, or backfill mutation endpoint is added.

## Decision: Inventory-first automatic legacy backfill

At media-worker start, and then every 60 seconds, a reconciler uses narrowly
allowlisted maintenance operations only to enumerate bounded workspace/job
candidates. It immediately switches to the target meeting's tenant worker
context for all content reads and mutations.

For each workspace/profile version:

1. Create or resume one `PlaybackBackfillRun`.
2. Inventory accepted media revisions by stable `(created_at, id)` keyset pages
   of 100.
3. Persist one job/action row for every evaluated revision, including
   `preserve_valid`, `validate_candidate`, `normalize_source`, and terminal
   missing-source plans.
4. Commit the complete inventory and counts.
5. Only after `inventory_complete`, dispatch mutation batches of at most 25.
6. Prioritize new finalize jobs, then due retries, then legacy backfill.
7. Resume from the persisted cursor after restart and never recreate a ready
   artifact unnecessarily.

Alembic creates schema and portable constraints only. It never downloads media,
runs FFmpeg, or mutates object storage. There is no backfill button or required
operator command. Admin visibility is read-only backlog/age/count evidence.

## Decision: Lifecycle, deletion, RLS, and diagnostics

- Canonical playback remains a `TrackArtifact` and participates in ordinary
  meeting retention/deletion.
- Normalization attempts are separate from upload temporary objects because
  they belong to a different lifecycle.
- Publisher and deletion both lock the meeting. Deletion sets the job
  `cancelled`, deletes registered unpublished attempt objects, then purges
  playback/source objects. A losing worker cleans its output and cannot publish
  after deletion begins.
- Whole-meeting retention deletion wins the race rather than waiting for
  normalization. Feature 099 does not add source-only retention policy.
- Deletion reports distinguish canonical playback and normalization temporary
  objects from generic upload temp.
- New tables are workspace-scoped, force RLS, appear in the validation
  inventory, and are covered on PostgreSQL as well as SQLite.
- Normalization audit reuses `IngestAuditEvent` through a strict event/metadata
  allowlist. Allowed metadata is limited to state/reason/profile, attempt counts,
  byte/duration buckets, stream counts, timestamps, and booleans. Raw filenames,
  object keys, tags, stderr, audio, transcript, summary, URLs, and credentials
  are forbidden.
- Repeated transient-cycle exhaustion and impossible legacy source loss create
  metadata-only operational incidents through the existing support-incident
  surface; they do not create user work or expose content.

## Rejected alternatives

- In-process PyAV: adds a native Python dependency and puts untrusted media in
  the API process.
- One shared MediaScribe/FFmpeg worker: backfill CPU/disk work could starve the
  transcript pipeline and blur status truth.
- Trust MIME, extension, or client codec metadata: none proves decodability or
  complete file integrity.
- Automatic FFmpeg stream selection: FFmpeg may choose the most channels or
  lowest index rather than the unique product-intended track.
- On-demand conversion during playback: creates unbounded request latency and
  broken retry UX.
- Backfill inside Alembic: long-running media/object work is not a safe schema
  migration.
- Shared source/playback object key: breaks independent validation,
  replacement, retention, and deletion truth.
- Manual retry/reprocess/backfill controls: directly contradicts the accepted
  product requirement.

## Validation boundary

The standalone Codex Security scan for feature 097 remains deferred and
untouched. Feature 099 still requires its ordinary authorization, RLS,
untrusted-media isolation, redaction, deletion-race, and dependency/version
acceptance tests because those are product requirements. Passing them must not
be represented as completion of the deferred repository security scan.
