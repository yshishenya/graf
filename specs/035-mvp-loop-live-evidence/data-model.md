# Data Model: MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

## LiveEvidencePack

Represents the complete metadata-safe evidence bundle for the slice.

- `feature`: fixed value `035-mvp-loop-live-evidence`.
- `generatedAt`: ISO timestamp.
- `desktopRuntimePath`: accepted desktop app path, expected
  `/Applications/2brain Rec.app`.
- `validationRuns`: list of command/manual validation records.
- `screenshots`: metadata-safe screenshot records.
- `readinessReport`: generated JSON/Markdown report reference.
- `launchGapRegister`: generated gap register reference.
- `cleanRoomReference`: reference comparison note reference.
- `forbiddenContentScan`: scan result and match summary.
- `strongestClaim`: one bounded claim value.

## ValidationRun

Evidence for a command or manual walkthrough.

- `id`: stable identifier.
- `surface`: `desktop`, `web`, `server`, `infra`, `policy`, `reference`, or
  `tracker`.
- `commandOrAction`: command text or manual flow label.
- `result`: `pass`, `fail`, `blocked`, or `not_applicable`.
- `evidencePath`: repository path to metadata-safe evidence.
- `notes`: short explanation of limitations.

## MvpLoopStage

Existing readiness stage reused from the server readiness model.

- `id`: stable stage id.
- `ownerSurface`: product surface owner.
- `status`: `ready`, `degraded`, `blocked`, or `deferred`.
- `evidenceStrength`: `live`, `local_runtime`, `synthetic`, `docs_only`,
  `missing`, or `not_applicable`.
- `evidenceIds`: evidence references.
- `launchGapIds`: blocker references.
- `claimImpact`: claims affected by this stage.

## LaunchGap

Remaining launch blocker or deferred risk.

- `id`: stable gap id.
- `severity`: `P0`, `P1`, `P2`, or `P3`.
- `affectedJourney`: journey blocked by the gap.
- `currentEvidence`: what is currently known.
- `missingEvidence`: what would close or downgrade the gap.
- `recommendedNextAction`: next concrete action.
- `ownerArea`: accountable area.

## ReadinessClaim

The strongest claim allowed by current evidence.

- `value`: `infra_smoke_ready`, `pilot_blocked`, `mvp_loop_ready`,
  `internal_pilot_candidate`, `user_rollout_ready`, or `production_ready`.
- `allowedClaims`: bounded claims currently allowed.
- `excludedClaims`: claims explicitly excluded.
- `blockerCount`: P0/P1 blocker count.
- `rationale`: one-paragraph explanation.

## CleanRoomReferenceNote

Reference comparison record.

- `surfaces`: desktop/web surfaces compared.
- `allowedLessons`: generic product lessons.
- `intentionalDifferences`: how 2brain remains original.
- `forbiddenSimilarityChecks`: checks for copied expression.
- `privateReferencePolicy`: statement about screenshots/account data.
- `result`: `pass`, `needs_polish`, or `blocked`.
