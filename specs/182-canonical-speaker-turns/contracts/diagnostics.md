# Contract: Attribution Diagnostics

## Allowed fields

- `mediascribe_job_id`
- `result_version`, `provider_result_version`
- `provider_build_version`, `provider_model_version`, `alignment_version`
- `raw_turn_count`, `accepted_turn_count`
- `multi_label_conflict_count`
- `unknown_tiny_count`
- `duplicate_text_count`
- `text_conservation_status`
- `source_result_hash`
- `attribution_result_state`
- `defect_origin`
- bounded `reason_codes`

Unavailable version fields are omitted. UUIDs and hashes are strings. Counts
are non-negative integers. Status and reason values come from fixed enums.

## Forbidden fields

No audio, transcript or turn text, provider JSON, object key, URL, signed URL,
credential, header, prompt, meeting title, participant name, or raw provider
payload may enter the diagnostic object, logs, audit evidence, or fixtures.

## Defect ownership

- `provider`: the received attributed rows violate the documented contract.
- `graf`: GRAF cannot construct or project its deterministic canonical model.

Multi-label ASR overlap is a count, not by itself a provider defect.
