# Processing recovery contract

| MediaScribe evidence | GRAF behavior | User projection |
| --- | --- | --- |
| `uploaded`, `queued`, `processing`, `transcribing`, `diarizing`, `summarizing` | Keep same job, schedule next check | Preparing / waiting |
| `409 result_not_ready` | Keep same job, schedule next check | Preparing / waiting |
| `ready` | Fetch and import result | Results according to artifact readiness |
| `failed` | Persist provider reason and terminalize | Clear error + recovery |
| `429`, `502`, `503`, `504`, timeout | Keep same job, retry with bounded delay | Temporary issue / countdown |
| watchdog deadline without provider failure | Do not claim provider failed; retain manual same-job check | Result not confirmed yet |
| malformed response / missing local artifact | Local terminal or blocked outcome | Actionable GRAF error |

Transcript is visible only when the current result has diarization available
with at least one diarization segment. Summary status is independent and may
remain pending while transcript and diarization are ready.
