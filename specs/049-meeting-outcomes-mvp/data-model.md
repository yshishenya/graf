# Data Model: Meeting Outcomes MVP

## Entity: MeetingOutcomeSet

Stored outcome result for one meeting media revision and processing result.

Fields:

- `id`: UUID primary key.
- `workspace_id`: UUID, tenant scope, required.
- `meeting_id`: UUID, required.
- `media_revision_id`: UUID, nullable only for legacy/imported rows.
- `processing_result_id`: UUID, required.
- `status`: `queued`, `generating`, `available`, `partial`, `blocked`,
  `failed`, or `unsafe`.
- `summary_state`: category state.
- `key_points_state`: category state.
- `decisions_state`: category state.
- `action_items_state`: category state.
- `followups_state`: category state.
- `risks_state`: category state.
- `questions_state`: category state.
- `evidence_state`: category state.
- `source_kind`: `stored_output`, `extractive_generator`,
  `mediascribe_summary`, `provider_output`, `not_inferable`, or `blocked`.
- `generator_kind`: `deterministic_extractive`, `mediascribe_summary`,
  `llm_provider`, or `manual_fixture`.
- `generator_version`: stable template/model version string.
- `source_result_hash`: copy of the processing result hash when available.
- `content_hash`: hash over stored category states and item payloads.
- `started_at`: generation start timestamp.
- `generated_at`: successful/partial generation timestamp.
- `latency_ms`: nullable integer.
- `failure_reason`: safe reason code; no provider payload or meeting content.
- `lifecycle_state`: `active`, `deleting`, `deleted`, `retention_expired`,
  or `blocked`.
- `created_at`, `updated_at`: timestamps.

Relationships:

- Belongs to `Meeting`, `MediaRevision`, and `ProcessingResult`.
- Has many `MeetingOutcomeItem`.
- Has many `MeetingOutcomeGenerationAttempt`.

Validation rules:

- Unique active/generated set for
  `(workspace_id, meeting_id, media_revision_id, processing_result_id, generator_version)`.
- `available` or `partial` requires at least one item or at least one category
  state of `not_found`/`not_inferable`.
- `failed`, `blocked`, and `unsafe` require `failure_reason`.
- Category state values are: `available`, `not_found`, `not_inferable`,
  `processing`, `blocked`, `unsafe`, `unavailable`.
- No generated text may be copied to logs or audit metadata.

State transitions:

```text
queued -> generating -> available
queued -> generating -> partial
queued -> generating -> blocked
queued -> generating -> failed
queued -> generating -> unsafe
available -> generating -> available   # supersede after explicit retry/new result
partial -> generating -> available
available|partial|blocked|failed|unsafe -> deleting -> deleted
available|partial -> retention_expired
```

## Entity: MeetingOutcomeItem

User-visible stored item in one category.

Fields:

- `id`: UUID primary key.
- `workspace_id`: UUID, tenant scope, required.
- `meeting_id`: UUID, required.
- `outcome_set_id`: UUID, required.
- `category`: `summary`, `key_points`, `decisions`, `action_items`,
  `followups`, `risks`, `questions`, or `evidence`.
- `sequence`: integer order inside category.
- `state`: `available`, `not_found`, `not_inferable`, `blocked`, or `unsafe`.
- `text`: user-visible outcome text for available items; nullable for
  not-found/not-inferable sentinel rows if needed.
- `owner_text`: nullable, only when inferable from transcript.
- `due_date_text`: nullable, only when inferable from transcript.
- `truth_label`: `supported`, `not_found`, `not_inferable`, `unsafe`, or
  `blocked`.
- `source_refs_json`: list of source evidence references.
- `created_at`: timestamp.

Relationships:

- Belongs to `MeetingOutcomeSet`.

Validation rules:

- Available items require non-empty `text`.
- Factual available items require at least one `source_refs_json` entry unless
  the category is explicitly marked evidence unavailable and not trusted.
- `owner_text` and `due_date_text` must be absent unless source evidence
  supports them.
- Source references store segment IDs/timing/role labels, not raw transcript
  excerpts in diagnostics.

## Value Object: OutcomeSourceReference

Stored as JSON on `MeetingOutcomeItem.source_refs_json`.

Fields:

- `transcript_segment_id`: UUID, optional.
- `sequence`: integer, optional.
- `start_seconds`: decimal/float, optional.
- `end_seconds`: decimal/float, optional.
- `speaker_label`: string, optional.
- `source_role`: `local_mic`, `incoming`, or normalized role.
- `evidence_kind`: `segment`, `timestamp`, `category_state`, or `source_hint`.

Validation rules:

- At least one of `transcript_segment_id`, `sequence`, or timestamp range is
  required for factual available items.
- Do not store full transcript text inside source refs.

## Entity: MeetingOutcomeGenerationAttempt

Durable metadata-only generation attempt.

Fields:

- `id`: UUID primary key.
- `workspace_id`: UUID, tenant scope, required.
- `meeting_id`: UUID, required.
- `media_revision_id`: UUID, nullable only for legacy/imported rows.
- `processing_result_id`: UUID, required.
- `outcome_set_id`: UUID, nullable until the set is created.
- `status`: `queued`, `generating`, `stored`, `partial`, `blocked`,
  `failed_retryable`, `failed_terminal`, or `unsafe`.
- `provider_kind`: `deterministic_extractive`, `mediascribe_summary`,
  `llm_provider`, or `manual_fixture`.
- `generator_version`: stable template/model version string.
- `started_at`, `ended_at`: timestamps.
- `latency_ms`: nullable integer.
- `failure_reason`: safe reason code.
- `metadata_json`: metadata-only payload, such as segment counts and category
  counts. No transcript text, outcome text, prompts, provider responses,
  signed URLs, credentials, private paths, or raw audio.
- `created_at`, `updated_at`: timestamps.

Validation rules:

- Each attempt must reference the processing result it used.
- Successful attempts must link to an outcome set.
- Failure reasons must be from an allowlist.

## Entity: Outcome Review State

Pydantic/API model derived from stored rows for list/detail/web rendering.

Fields:

- `categories`: map from category to category state.
- `items`: ordered items grouped by category.
- `source_basis`: `stored_output`, `processing_status`, `transcript_only`,
  `policy_deferral`, `not_supported`, or `blocked`.
- `readiness_impact`: `closes_gap`, `keeps_gap_open`, or `non_blocking`.
- `provenance`: safe provider/generator/timing metadata.

Rules:

- Denied/unauthenticated/deleted/deleting meetings return no outcome content.
- Existing `NotesActionTruthState` may be extended for compatibility, but the
  review response must include stored category items for available outcomes.
- List rows may show only category states and counts; detail/embedded review
  can show item text and source references after access checks.

## Deletion And Retention Accounting

Outcome rows are controlled meeting content. Deletion service/reporting must
include the controlled artifact class `notes_summary` or a new outcome-specific
artifact class if introduced in implementation. Retention expiry marks outcome
sets/items inactive or purged according to the same meeting lifecycle truth as
transcript-derived artifacts.

## RLS Coverage

Direct workspace-scoped tables:

- `meeting_outcome_sets`
- `meeting_outcome_items`
- `meeting_outcome_generation_attempts`

These must be added to RLS migration policy coverage and to
`RLS_DIRECT_WORKSPACE_TABLES`.
