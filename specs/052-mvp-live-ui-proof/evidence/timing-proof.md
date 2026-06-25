# 052 Processing Timing Proof

All values are metadata-only.

- candidate_ref: `synthetic_non_sensitive_3600s`
- recording_duration_seconds: `3600`
- queue_wait_seconds: `2`
- workflow_processing_seconds: `36`
- provider_processing_seconds: `28`
- finalize_to_review_seconds: `37`
- target_seconds_per_hour: `180`
- result: `pass`

## Notes

The production-safe synthetic one-hour candidate contained no private meeting
content and was processed on the production stack deployed from
`db1eca18f08d26f6816b2bd88067709d0e57e590`.

Measured metadata:

- upload_seconds: `3`
- workflow_start_to_imported_seconds: `36`
- mediascribe_submit_to_ready_seconds: `28`
- created_to_imported_seconds: `37`
- transcript_segments: `210`
- diarization_segments: `210`
- outcome_sets: `1`
- outcome_items: `5`

This proves the three-minute-per-hour processing target for a non-sensitive
synthetic hour candidate. It does not prove the fresh installed-app owner
journey, real meeting variability, or speakerphone echo/noise quality.
