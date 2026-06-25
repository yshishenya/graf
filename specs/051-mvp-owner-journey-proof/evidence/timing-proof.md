# 051 Processing Timing Proof

All values are metadata-only.

- candidate_ref: `6adcee6d4e`
- recording_duration_seconds: `31`
- queue_wait_seconds: `unknown`
- workflow_processing_seconds: `8.129`
- provider_processing_seconds: `5.946`
- finalize_to_review_seconds: `381.180`
- target_seconds_per_hour: `180`
- result: `unproven`

## Notes

Current production metadata proves pipeline health on a short 31-second
candidate only. It must not be extrapolated into the one-hour timing target.
Queue/wait duration was not proven separately in this read-only database check.
