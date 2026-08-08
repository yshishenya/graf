# Playback Status Contract

**Feature**: `099-review-m4a-normalization`

## Purpose

Define one server-owned playback state for meeting list, review API, web cabinet,
embedded macOS cabinet, and playback route. Playback truth is independent from
transcript/summary processing and never exposes a manual repair control.

The canonical OpenAPI remains
`specs/012-server-ingest-foundation/contracts/openapi.yaml`; implementation must
update it and drift tests for this delta.

## Read projection

Existing meeting list/review responses include:

```json
{
  "playback": {
    "state": "preparing",
    "reason_code": "normalization_running",
    "label": "Аудио готовится автоматически",
    "automatic_recovery": true,
    "can_play": false,
    "action": "disabled"
  }
}
```

Fields:

- `state`: `preparing`, `available`, `unavailable`, `deleting`, or `deleted`;
- `reason_code`: safe stable enum;
- `label`: localized server-owned copy;
- `automatic_recovery`: true only when GRAF continues without user action;
- `can_play`: true only for a validated canonical artifact;
- `action`: `disabled`; the player itself is rendered only when `can_play=true`.

Unknown/new server reason values degrade to the coarse `state` and generic safe
copy. Clients do not infer readiness from `processing_status`.

## Derivation precedence

1. Meeting deletion/deleted state.
2. Viewer access policy; a foreign/inaccessible meeting exposes no content
   existence.
3. `PlaybackNormalizationJob.state` and matching validated canonical
   `TrackArtifact`.
4. Accepted revision without a job -> reconciliation-pending `preparing`.
5. Transcript/summary/MediaScribe state has no effect.

`available` requires all of:

- job state `ready`;
- job canonical artifact pointer is non-null;
- artifact belongs to the same workspace/meeting/revision;
- role `playback`, status `stored`;
- canonical profile/validation/source fingerprint fields match;
- byte length is positive and within the canonical cap.

The read path does not decode or transcode. Full validation was performed before
publication.

## State mapping

| Durable truth | Read state | `automatic_recovery` | User action |
|---|---|---:|---|
| job `queued` | `preparing` | true | none |
| job `running` | `preparing` | true | none |
| job `publishing` | `preparing` | true | none |
| job `retry_wait` | `preparing` | true | none |
| accepted revision, no job | `preparing` | true | none |
| job `ready` + valid canonical artifact | `available` | false | play/seek only |
| job permanent `terminal` | `unavailable` | false | none |
| meeting deleting / job cancelled | `deleting` | false | none |
| meeting deleted / artifacts purged | `deleted` | false | none |

A missing artifact behind a supposedly ready job is not silently reported ready.
It becomes `preparing/canonical_artifact_missing`, emits a safe system incident,
and automatic reconciliation runs if retained accepted source exists.

## Safe reason codes and copy

### Preparing

| Reason | Russian | English |
|---|---|---|
| `normalization_queued` | Аудио готовится автоматически | Audio is being prepared automatically |
| `normalization_running` | Аудио готовится автоматически | Audio is being prepared automatically |
| `normalization_publishing` | Завершаем подготовку аудио | Finishing audio preparation |
| `normalization_retry_wait` | Подготовка занимает больше времени. GRAF продолжит автоматически | Preparation is taking longer. GRAF will continue automatically |
| `reconciliation_pending` | GRAF автоматически восстанавливает подготовку аудио | GRAF is automatically recovering audio preparation |
| `canonical_artifact_missing` | GRAF автоматически восстанавливает аудио | GRAF is automatically recovering the audio |

### Unavailable

| Reason | Russian | English |
|---|---|---|
| `empty_source` | В исходном файле нет данных | The source file is empty |
| `no_audio` | В файле нет пригодной аудиодорожки | The file has no usable audio track |
| `ambiguous_audio_tracks` | В файле несколько равноправных аудиодорожек | The file has multiple equally valid audio tracks |
| `unsupported_media` | Формат или кодек файла не поддерживается | The file format or codec is not supported |
| `encrypted_media` | Защищённый файл нельзя подготовить для воспроизведения | Protected media cannot be prepared for playback |
| `corrupt_source` | Файл повреждён и не может быть воспроизведён | The file is corrupt and cannot be played |
| `limit_exceeded` | Файл превышает допустимые параметры | The file exceeds supported limits |
| `source_missing` | Исходный файл больше не хранится в GRAF | The source file is no longer retained by GRAF |
| `source_mismatch` | Целостность исходного файла не подтверждена | Source file integrity could not be confirmed |

Terminal copy describes the result and does not instruct the user to retry,
re-upload, contact an administrator, or run a technical operation. Product
follow-up actions, if ever introduced, require a separate feature decision.

## Independent status composition

Required combinations:

| Playback | Transcript | Review behavior |
|---|---|---|
| preparing | processing | show both independently |
| preparing | ready | transcript visible; player replaced by preparing state |
| preparing | failed | playback still recovers automatically |
| available | processing | player works; transcript remains processing |
| available | failed | player works; transcript failure remains truthful |
| unavailable | ready | transcript visible; playback terminal reason visible |
| available | ready | complete review |

No state in one column implies or overwrites the other.

## Cabinet rendering

- Meeting list uses a compact status token with existing GRAF styles.
- Review page reserves the player region and renders the corresponding state;
  no dead `<audio>` element is created while unavailable/preparing.
- `preparing` includes a live but non-noisy status announcement; frequent poll
  updates must not repeatedly interrupt screen readers.
- `unavailable` copy is associated with the audio region and remains keyboard
  reachable as ordinary text, not a disabled mystery control.
- No button/link/menu item says retry, reprocess, repair, backfill, convert, or
  contact administrator.
- Browser and embedded macOS routes render the same server fragment/read model.
- Refresh, two tabs, reconnect, and app restart read the same durable state.
- Light/dark, narrow/wide window, reduced motion, keyboard focus, localization,
  and loading/error states reuse existing cabinet primitives.

## Polling/reconnect behavior

- Existing list/review refresh polling may observe status changes; starting a
  second job is forbidden.
- Client disconnect does not cancel server work.
- Client refresh does not start work; it only reads current durable truth.
- Temporary API/read failure uses ordinary page recovery copy and must not be
  transformed into a normalization terminal reason.
- Multiple tabs never obtain distinct record, source, job, or canonical IDs.

## Playback endpoint

Existing authorized playback route behavior remains:

- only `available` returns media;
- response media type `audio/mp4`;
- `Content-Disposition: inline; filename="meeting-review.m4a"`;
- `Accept-Ranges: bytes`;
- valid single-range requests return `206` with correct `Content-Range`;
- invalid/unsatisfiable ranges use existing safe behavior;
- body streams in bounded chunks from the stored canonical object;
- no source object, candidate, attempt, or temporary object is streamed;
- no on-demand probe/remux/transcode/mix;
- authorization and deletion state are rechecked before egress.

## Mutation boundary

Feature 099 adds no user/admin mutation endpoint for playback preparation.

Forbidden API/UI operations:

- retry normalization;
- reprocess playback;
- start backfill;
- select an audio track;
- replace or edit source media;
- force-ready or bypass validation.

Read-only operational/admin metrics may expose aggregate backlog, oldest safe
age, state/reason counts, and backfill progress. They never expose filenames,
object keys, media metadata dumps, or content.

## Privacy/access rules

- A foreign workspace/user receives ordinary not-found/access-denied behavior
  with no normalization existence signal.
- Shared viewers receive only the meeting playback state already authorized by
  meeting access; owner-only operational reasons are not expanded.
- Diagnostics and responses never contain original filename, local path, object
  key/URL, FFmpeg output, tags, transcript/summary, or credentials.
- Terminal source categories are coarse enough to explain the result without
  exposing private container metadata.
