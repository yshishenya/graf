# MediaScribe Result Contract

## Ready With Transcript

Input:

```json
{
  "job": {"id": "job-id", "status": "ready"},
  "transcript_status": "available",
  "transcript_reason": null,
  "transcript": [
    {"start": 0.0, "end": 1.2, "text": "example", "source_role": "mic"}
  ],
  "downloads": {}
}
```

GRAF behavior:

- Store `processing_results.transcript_status="available"`.
- Store transcript rows from `transcript`.
- Set `segment_count` to the number of transcript rows.
- Allow outcome generation.
- Keep transcript downloads based on stored transcript availability, not on MediaScribe `downloads.transcript`.

## Ready Without Transcript

Input:

```json
{
  "job": {"id": "job-id", "status": "ready"},
  "transcript_status": "unavailable",
  "transcript_reason": "no_recognizable_speech",
  "transcript": [],
  "downloads": {}
}
```

GRAF behavior:

- Store `processing_results.transcript_status="unavailable"`.
- Store `segment_count=0`.
- Store `failure_reason="no_recognizable_speech"` and `failure_source="input_audio"`.
- Store blocked meeting outcomes with the same reason/source.
- Do not run summary generation.
- Show `MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена.`
- Record a `processed_no_transcript` diagnostic event.

## Failed Input Audio

Input:

```json
{
  "id": "job-id",
  "status": "failed",
  "error_code": "invalid_audio_payload",
  "error_origin": "input_audio"
}
```

GRAF behavior:

- Treat as an input-audio problem, not a MediaScribe service outage.
- Store unavailable processing result with `failure_reason="invalid_audio_payload"` and `failure_source="input_audio"`.
- Block meeting outcomes with the same reason/source.
- Show `Файл записи не является декодируемым аудио или поврежден.`
- Record an `input_audio_problem` diagnostic event.

## Failed MediaScribe Service Problem

Input:

```json
{
  "id": "job-id",
  "status": "failed",
  "error_code": "worker_failed",
  "error_origin": "mediascribe"
}
```

GRAF behavior:

- Treat as a MediaScribe service problem.
- Preserve existing retry/alert behavior.
- Record a `mediascribe_service_problem` diagnostic event with safe metadata.

## Forbidden Behavior

- Do not use `downloads.transcript` as the main transcript availability signal.
- Do not call a MediaScribe transcript download endpoint for unavailable transcripts.
- Do not expose external MediaScribe job IDs, raw audio, raw transcript text, signed URLs, object keys, or credentials in normal product UI.
