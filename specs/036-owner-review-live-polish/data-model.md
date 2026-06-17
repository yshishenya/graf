# Data Model: Owner Review Live Polish

Feature: `036-owner-review-live-polish`

This slice primarily introduces metadata/view-state concepts. It should reuse
existing persisted tables unless implementation discovers a required
non-content metadata gap.

## OwnerReviewProof

Metadata-safe evidence that an authenticated owner can or cannot access the
production review workspace.

Fields:

- `proof_id`: stable evidence id, for example `feature-036-owner-review-live`.
- `target_origin`: `https://rec.2brain.pro`.
- `run_id`: non-secret smoke/evidence run id.
- `auth_method`: `session_header`, `browser_handoff`, `logged_in_browser`, or
  `blocked`.
- `session_material_committed`: always `false`.
- `list_state`: `ready`, `empty`, `blocked`, or `deferred`.
- `detail_state`: `ready`, `empty`, `blocked`, or `deferred`.
- `governance_state`: `ready`, `blocked`, or `deferred`.
- `failure_code`: optional safe code such as `missing_auth_context`,
  `auth_session_expired`, `empty_owner_workspace`, or `browser_blocked`.
- `cleanup_state`: `not_needed`, `pass`, `blocked`, or `deferred`.
- `evidence_files`: committed metadata-only files.

Validation rules:

- Raw tokens, cookies, bearer values, signed URLs, private account identifiers,
  private meeting titles, and transcript text are forbidden.
- If `auth_method` creates a temporary session, `cleanup_state` must be `pass`
  before closeout or the gap remains open.
- If browser proof is blocked but API proof passes, the final readiness claim
  must state that browser owner UX remains blocked.

## ReviewSurfaceState

User-visible list/detail/governance state for one meeting or workspace.

Fields:

- `surface`: `web_list`, `web_detail`, `desktop_list`, `desktop_detail`,
  `governance`, or `empty`.
- `meeting_state`: `ready`, `partial`, `processing`, `failed`, `deleted`,
  `access_limited`, `empty`, or `blocked`.
- `transcript_state`: `available`, `processing`, `blocked`, or `unavailable`.
- `speaker_state`: `available`, `partial`, `processing`, or `unavailable`.
- `playback_state`: `available`, `blocked`, `unavailable`, or `deferred`.
- `access_state`: existing cabinet access state.
- `deletion_state`: existing lifecycle/deletion state where applicable.
- `primary_action`: product-facing review action or safe blocked action.

Validation rules:

- The UI must not hide blocked or deferred states behind generic empty copy.
- Desktop embedded states must not replace or obscure native capture controls.

## NotesActionTruth

Truth state for generated meeting outcomes.

Fields:

- `summary_state`: `available`, `processing`, `blocked`, `unavailable`, or
  `deferred`.
- `decisions_state`: same state enum.
- `action_items_state`: same state enum.
- `followups_state`: same state enum.
- `source_basis`: `stored_output`, `processing_status`, `transcript_only`,
  `policy_deferral`, or `not_supported`.
- `readiness_impact`: `closes_gap`, `keeps_gap_open`, or `non_blocking`.
- `copy_key`: stable UI copy identifier.

Validation rules:

- `available` requires stored data that can be shown without fabricating
  content.
- `deferred` and `unavailable` keep `mvp_loop_ready` excluded unless the owner
  explicitly accepts a narrower pilot claim in a later feature.
- Private transcript text must not be committed as evidence.

## RuntimePolishEvidence

Metadata-safe comparison of runtime surfaces to the V8 clean-room baseline.

Fields:

- `surface`: `desktop_workspace`, `desktop_active_recording`, `web_list`,
  `web_detail`, `web_governance`, `responsive_web`, or `reference_review`.
- `v8_alignment`: `pass`, `partial`, or `blocked`.
- `native_capture_controls_visible`: boolean where desktop is involved.
- `brand_distance_state`: `pass`, `needs_review`, or `blocked`.
- `private_reference_committed`: always `false`.
- `remaining_gaps`: safe ids.

Validation rules:

- Krisp screenshots, brand assets, copied icons, and copied non-generic copy
  must not be committed.
- Screenshots may be committed only when they are synthetic or metadata-safe.

## LaunchClaimUpdate

Final readiness decision after 036.

Fields:

- `strongest_truthful_claim`: existing readiness claim enum.
- `closed_gaps`: list of gap ids closed by 036.
- `remaining_gaps`: list of gap ids still blocking launch.
- `claim_exclusions`: list of excluded claims and reasons.
- `next_recommended_slice`: product next step.
- `validation_refs`: evidence ids and command results.

Validation rules:

- `mvp_loop_ready` cannot be included while `notes-action-output`,
  `web-owner-live-auth-context`, or equivalent P1 gaps remain open.
- `internal_pilot_candidate` cannot be included without accepted live owner
  journey evidence or a narrower explicitly accepted pilot guardrail.
