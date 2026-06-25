# Data Model: MVP Owner Journey Proof

This feature does not require new production database tables by default. The
model below defines metadata-only evidence records, readiness reports, and
validation outputs used by tests, probes, docs, and release evidence.

## MVP Owner Journey Evidence Pack

- `feature`: fixed value `051-mvp-owner-journey-proof`
- `created_at`: ISO timestamp
- `release_tag`: product release tag under validation
- `deployed_sha`: production commit SHA under validation
- `installed_app_version`: installed app version or build identity
- `production_candidate`: redacted Production Candidate summary
- `owner_journey_gates`: list of Owner Journey Gate records
- `outcome_proof`: Stored Outcome Proof record
- `timing_evidence`: Processing Timing Evidence record
- `interface_findings`: list of Interface Audit Finding records
- `launch_gaps`: list of Launch Gap records
- `final_claim`: one of `pilot_blocked`, `internal_pilot_candidate`
- `forbidden_content_scan`: pass/fail status and command summary

## Production Candidate

- `candidate_ref`: redacted stable reference safe for local notes
- `recording_duration_seconds`: integer or `unknown`
- `upload_status`: safe status string
- `media_revision_status`: safe status string
- `track_role_count`: integer
- `stored_track_count`: integer
- `workflow_status`: safe status string
- `mediascribe_status`: safe status string
- `result_status`: safe status string
- `transcript_status`: `available`, `missing`, `processing`, `failed`, or `unknown`
- `diarization_status`: `available`, `missing`, `processing`, `failed`, or `unknown`
- `playback_status`: `available`, `blocked`, `processing`, `failed`, or `unknown`
- `review_route_status`: `available`, `auth_required`, `server_unavailable`, `blocked`, or `unknown`

## Owner Journey Gate

- `id`: stable gate id, for example `fresh-record-stop-upload`
- `surface`: `macos_native`, `server_backend`, `web_cabinet`,
  `desktop_embedded_web`, `production_infra`, `docs_status`, or `security`
- `status`: `pass`, `fail`, `blocked`, or `unproven`
- `evidence`: metadata-only evidence reference
- `claim_impact`: affected readiness claims
- `next_action`: required when status is not `pass`

## Stored Outcome Proof

- `candidate_ref`: redacted production candidate reference
- `outcome_set_status`: `available`, `missing`, `processing`, `blocked`,
  `failed`, or `unknown`
- `outcome_item_count`: integer
- `category_states`: map of outcome category to state
- `source_basis`: `stored_output`, `processing`, `not_found`,
  `not_inferable`, `blocked`, `failed`, or `unknown`
- `privacy_check`: pass/fail status confirming no private outcome text is
  committed

## Processing Timing Evidence

- `candidate_ref`: redacted production candidate reference
- `recording_duration_seconds`: integer or `unknown`
- `queue_wait_seconds`: number or `unknown`
- `workflow_processing_seconds`: number or `unknown`
- `provider_processing_seconds`: number or `unknown`
- `finalize_to_review_seconds`: number or `unknown`
- `target_seconds_per_hour`: fixed value `180`
- `target_result`: `pass`, `fail`, or `unproven`
- `notes`: metadata-only explanation of what was measured and what was not

## Interface Audit Finding

- `id`: stable finding id
- `surface`: `web_desktop`, `web_mobile`, `embedded_desktop`,
  `embedded_mobile`, or `native_macos`
- `severity`: `P0`, `P1`, `P2`, or `P3`
- `user_visible_problem`: short non-private description
- `evidence`: screenshot path outside git, DOM metric, test name, or command
  result
- `fix_status`: `open`, `fixed`, `deferred`, or `not_reproducible`
- `claim_impact`: readiness claim blocked or unaffected

## Launch Gap

- `id`: stable gap id
- `severity`: `P0`, `P1`, `P2`, or `P3`
- `journey`: owner journey or product area
- `missing_evidence`: what is still not proven
- `next_action`: smallest next step
- `claim_impact`: claim blocked by this gap

## State Rules

- `internal_pilot_candidate` is allowed only when every P1 Owner Journey Gate is
  `pass`, Stored Outcome Proof is `available` or truthfully complete for all
  categories, Processing Timing Evidence passes or is explicitly accepted as a
  non-P1 limitation, every P1 Interface Audit Finding is `fixed` or
  `not_reproducible`, and no P1 Launch Gap remains.
- `pilot_blocked` is required when any P1 gate is `fail`, `blocked`, or
  `unproven`.
- `production_ready` and broad `user_rollout_ready` are not allowed 051 final
  claims.
