# Processing recovery contract

| MediaScribe evidence | GRAF behavior | User projection |
| --- | --- | --- |
| `uploaded`, `queued`, `processing`, `transcribing`, `diarizing`, `summarizing` | Keep same job, schedule next check | Preparing / waiting |
| `409 result_not_ready` | Keep same job, schedule next check | Preparing / waiting |
| `ready` | Fetch and import result | Results according to artifact readiness |
| `ready` + `no_recognizable_speech` | Import terminal no-speech outcome without resubmission | No transcript; playback remains available; new processing attempt is offered |
| `failed` | Persist provider reason and terminalize | Clear error + recovery |
| `429`, `502`, `503`, `504`, timeout | Keep same job, retry with bounded delay | Temporary issue / countdown |
| watchdog deadline without provider failure | Do not claim provider failed; retain manual same-job check | Result not confirmed yet |
| malformed response / missing local artifact | Local terminal or blocked outcome | Actionable GRAF error |

## Manual-upload preparation contract

| GRAF evidence before first provider job | Processing behavior | User projection |
| --- | --- | --- |
| normalization `queued/running/publishing` | Do not create MediaScribe job; durable bounded wait | Подготавливаем запись |
| normalization `retry_wait` | Do not submit; expose `next_attempt_at` | Countdown + «Повторить подготовку» |
| normalization `ready` + exact validated M4A | Stage exact artifact and start one provider operation | Processing starts |
| normalization `terminal` | No provider egress | Clear file/preparation error + upload another file |
| normalization `cancelled` / deletion / supersession | No provider egress | Deleting/deleted/cancelled |
| confirmed `external_job_id` | Skip normalization gate; poll/reconcile same job | Provider state |
| local job row without external id | Re-check exact canonical + immutable request fingerprint; reconcile same idempotency key | Preparation/submission state |

Canonical multipart fields are `Content-Type: audio/mp4` and filename
`manual-media.m4a`. The original manual upload is not a provider source after
this contract applies.

One provider operation does not imply one HTTP attempt. If the POST response is
lost after egress, GRAF may replay the exact same multipart envelope with the
same canonical bytes, SHA, request fingerprint and `Idempotency-Key`. Such
replays MUST resolve to one MediaScribe job. A new key/job is allowed only after
a confirmed terminal provider outcome and an explicit new business attempt.

For `archive_audio=false`, exact canonical bytes are transient provider input,
not playback and not retained storage usage. A revision policy guard applies to
both playback selectors and storage reserve/commit. Journal-first purge deletes
only source/playback media after fencing publication, then reconciles attempts
and artifacts; processing usage remains owned while an attempt is active.

Normalization waiting uses its own durable schedule and does not decrement the
provider watchdog. `retry_wait` follows durable `next_attempt_at`; active states
use a bounded fallback timer. History is bounded through `continue_as_new` only
inside the new `normalization_pending` branch.

Temporal start uses deterministic workflow id plus `REJECT_DUPLICATE`.
`WORKFLOW_STARTED` is committed before the start RPC; running duplicate is
reused, a closed execution is replaced without changing the provider operation,
and ambiguous RPC outcome remains an open intent for maintenance recovery.

Transcript is visible only when the current result has diarization available
with at least one diarization segment. Summary status is independent and may
remain pending while transcript and diarization are ready.

`invalid_audio_payload` with `error_origin=input_audio` is terminal, including
legacy `processed` rows. Terminal projections never schedule frontend polling.
While a meeting detail is non-terminal, its low-frequency status polling is not
dropped merely because the application window is hidden.
