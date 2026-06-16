# Data Model: MVP Loop Readiness

Date: 2026-06-16

## MvpLoopStage

Represents one required step in the owner value loop.

Fields:

- `id`: stable slug, for example `local-recording`, `upload`, `processing`,
  `meeting-list`, `meeting-detail`, `desktop-embedding`, `access-egress`,
  `retention-deletion`, `production-smoke`.
- `label`: reader-facing stage name.
- `owner_surface`: `macos_native`, `desktop_embedded_web`, `web_cabinet`,
  `server_backend`, `production_infra`, or `docs_status`.
- `required_for_claims`: list of readiness claims that depend on the stage.
- `status`: `ready`, `degraded`, `blocked`, `not_accepted`, or `out_of_scope`.
- `evidence_strength`: `live`, `production_smoke`, `local_runtime`,
  `synthetic`, `docs_only`, `missing`, or `blocked`.
- `evidence_ids`: list of `ReadinessEvidence.id` values.
- `launch_gap_ids`: list of `LaunchGap.id` values when status is not fully
  ready for the target claim.
- `notes`: short metadata-only explanation.

Validation rules:

- `ready` stages must have at least one evidence record.
- `ready` plus `synthetic` evidence is allowed only for partial readiness
  claims, not for `mvp_loop_ready`.
- `blocked` and `not_accepted` stages must reference at least one launch gap.
- A stage that touches capture must preserve native authority and visible stop
  truth.

## ReadinessEvidence

Represents proof that can be reviewed without exposing private content.

Fields:

- `id`: stable slug.
- `type`: `command`, `screenshot`, `document`, `endpoint`, `github`, `runtime`,
  `production_smoke`, or `reference_review`.
- `source`: path, URL, command label, PR/issue reference, or endpoint label.
- `captured_at`: ISO-like timestamp or date.
- `scope`: what the evidence proves.
- `strength`: same vocabulary as `MvpLoopStage.evidence_strength`.
- `safe_to_commit`: boolean.
- `forbidden_content_scan`: `pass`, `blocked`, `not_applicable`, or `pending`.
- `limitations`: list of bounded caveats.

Validation rules:

- Evidence with `safe_to_commit=false` cannot be referenced from committed
  reports except as an uncommitted/private observation with no content.
- Screenshots must be scanned or explicitly marked blocked.
- Production evidence must identify the deployed commit or state why it cannot.
- Evidence must not contain raw audio, transcript text from private meetings,
  credentials, tokens, signed URLs, passwords, private emails, live local paths,
  or Krisp private captures.

## LaunchGap

Represents a launch blocker or intentionally deferred item.

Fields:

- `id`: stable slug.
- `severity`: `P0`, `P1`, `P2`, or `P3`.
- `affected_journey`: loop stage or user story impacted.
- `current_evidence`: metadata-only summary.
- `missing_evidence`: what must be proven or implemented.
- `recommended_next_action`: next slice, validation action, or deferral.
- `owner_area`: `desktop`, `web`, `server`, `infra`, `security`, `ux`,
  `product`, or `ops`.
- `deferred`: boolean.
- `deferral_guardrail`: required when `deferred=true`.

Validation rules:

- P0/P1 gaps must have a recommended next action.
- Deferred gaps must include a guardrail explaining why they do not block the
  current MVP claim.
- Gaps cannot be closed by weaker evidence than the missing evidence describes.

## ReferenceComparison

Represents clean-room comparison against final mockups and Krisp IA/category
reference.

Fields:

- `id`: stable slug.
- `surface`: `desktop_home`, `desktop_detail`, `web_list`, `web_detail`,
  `settings`, `governance`, or `other`.
- `allowed_lessons`: category-level observations used.
- `forbidden_similarity_checks`: copied visuals, exact copy, icons, colors,
  assets, private content, proprietary behavior.
- `result`: `pass`, `needs_polish`, or `blocked`.
- `evidence_ids`: evidence records supporting the comparison.

Validation rules:

- A comparison cannot pass if it relies on committed private Krisp screenshots.
- A comparison cannot pass if it copies Krisp exact product copy or visual
  expression.
- Results must distinguish IA alignment from visual/pixel similarity.

## ReadinessClaim

Represents the bounded conclusion of the readiness pass.

Fields:

- `claim`: `infra_smoke_ready`, `desktop_loop_verified`,
  `web_review_verified`, `policy_lifecycle_verified`,
  `internal_pilot_candidate`, `pilot_blocked`, or `mvp_loop_ready`.
- `status`: `proven`, `partial`, or `blocked`.
- `required_stage_ids`: list of stages required for the claim.
- `supporting_evidence_ids`: evidence records supporting the claim.
- `blocking_gap_ids`: gaps preventing the claim.
- `exclusions`: claims explicitly not made.

Validation rules:

- `mvp_loop_ready` requires no P0/P1 gaps, live or production evidence for all
  P1 stages, passing forbidden-content scans, and explicit production claim
  boundaries.
- `internal_pilot_candidate` may allow P2/P3 gaps but not P0/P1 gaps.
- `infra_smoke_ready` alone does not imply pilot or rollout readiness.
