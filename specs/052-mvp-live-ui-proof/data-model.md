# Data Model: MVP Live Owner Journey And UI Proof

052 does not introduce a new product database model by default. It uses
metadata-only evidence records and existing product state.

## Owner Journey Candidate

- **candidate_ref**: redacted stable reference for one current recording.
- **recording_state**: `pass`, `fail`, `blocked`, or `unproven`.
- **upload_state**: `pass`, `fail`, `blocked`, or `unproven`.
- **finalization_state**: `pass`, `fail`, `blocked`, or `unproven`.
- **processing_state**: `pass`, `fail`, `blocked`, or `unproven`.
- **review_state**: `pass`, `fail`, `blocked`, or `unproven`.
- **transcript_state**: `available`, `partial`, `blocked`, `failed`,
  `missing`, or `unknown`.
- **diarization_state**: `available`, `partial`, `blocked`, `failed`,
  `missing`, or `unknown`.
- **playback_state**: `available`, `blocked`, `failed`, `missing`, or
  `unknown`.
- **speaker_timeline_state**: `available`, `blocked`, `failed`, `missing`, or
  `unknown`.
- **outcome_state**: `available`, `partial`, `blocked`, `failed`, `missing`, or
  `unknown`.
- **claim_impact**: `can_raise`, `keep_pilot_blocked`, or `out_of_scope`.

## Launch Gate

- **gate_id**: canonical gate name.
- **status**: `pass`, `fail`, `blocked`, `unproven`, or `out_of_scope`.
- **evidence_ref**: metadata-only reference to the proof artifact.
- **reason**: short non-private explanation.
- **next_action**: smallest next step when not passing.
- **claim_impact**: readiness claim allowed or blocked by this gate.

## Review Surface Observation

- **surface**: `web_desktop`, `web_compact`, `macos_embedded`, or
  `macos_native`.
- **meeting_state**: `ready`, `processing`, `blocked`, `auth_required`,
  `server_unavailable`, or `unknown`.
- **playback_visible**: boolean or `unknown`.
- **seek_visible**: boolean or `unknown`.
- **speaker_lanes_visible**: boolean or `unknown`.
- **outcomes_visible**: boolean or `unknown`.
- **native_truth_visible**: boolean or `unknown`.
- **critical_findings**: count only; no private content.

## Reference Observation

- **reference_surface**: `krisp_web` or `krisp_app`.
- **interaction_pattern**: metadata-only note of approved observable reference fidelity.
- **applies_to_2brain**: `yes`, `no`, or `later`.
- **deviation_reason**: accessibility, localization, privacy, security, known defect, or none.
- **asset_provenance**: GRAF-owned, licensed, or unverified; no extracted/private assets.

## Validation Rules

- No evidence entity may include raw audio, transcript text, private notes,
  private titles, account identifiers, cookies, tokens, signed URLs, object
  keys, or private local paths.
- `internal_pilot_candidate` requires every P1 Launch Gate to be `pass`.
- A short timing candidate cannot set the timing gate to `pass`.
- Local fixture evidence can support UI/runtime quality but cannot by itself
  pass production owner journey gates.

## T020 API Metadata Observation

- **proof_scope**: fixed `owner_review_api_metadata`.
- **owner_journey_status**: fixed `unproven`; no full P1 pass inferred.
- **owner_review.status / overall_status**: pass, blocked or fail, according to
  the owner contract's ordered response/type/access/state/category rules.
- **reason**: fixed bounded code, never a server-provided private string.
- **candidate_ref**: fixed redacted runtime-input reference.
- **candidate binding**: response meeting UUID equals the requested UUID after
  normalization; IDs are validated in memory and never emitted.
- **counts**: transcript segments, speaker lanes, lane intervals, seek targets,
  eight category item counts. Missing/malformed is not coerced to zero.

This is transient evidence metadata, not a database migration. Detailed source
paths, enum/type rules, aggregate and exit codes are defined once in
`contracts/owner-journey-proof-contract.md`.
