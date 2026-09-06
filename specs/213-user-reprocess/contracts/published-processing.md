# Contract: effective complete processing result

## Single customer-content selector

`effective_processing_result_query()` is the one authority for customer-visible transcript, diarization and speaker attribution. Latest workflow/job is operational state only.

The selector:

- stays inside workspace, meeting and latest accepted media revision;
- requires explicit `ProcessingWorkflow` lineage;
- applies `complete_processing_result_clause()`;
- orders by attempt ordinal, then result version and deterministic timestamps/ID.

## Automatic publication boundary

The existing result-import transaction locks the meeting and rejects:

- deleting/deleted meetings;
- superseded workflows;
- stale media revisions;
- source fingerprint mismatch.

It stores the parent result and transcript/diarization segments in one transaction. Therefore the shared selector changes from result A to B only after B is a complete committed result. Partial or failed B leaves A selected.

## Customer-facing readers

These consumers must use the shared selector and must not bind customer content to the newest workflow or order imported results independently:

- owner and shared meeting detail;
- browser and embedded desktop cabinet;
- playback/transcript association;
- desktop synchronization review availability;
- transcript exports/downloads and egress checks;
- outcome source selection and generation gates.

Search/indexing or another consumer found during implementation follows the same rule.

## Outcome alignment

Outcome publication remains independent.

- aligned source: normal presentation;
- older source: retain content and show `По предыдущей версии расшифровки`;
- no prior outcome: existing honest pending/unavailable state;
- outcome failure: keep the new transcript and old labelled outcomes.

Combined exports must not silently mix unmatched transcript and outcomes.

## No dual selectors

Do not add local `latest imported`, latest-workflow content binding or outcome-pointer fallback for transcript selection. If no complete result exists, no transcript is published.
