# Data Model: MVP Launch Proof

This feature does not require new production database tables. The model below
defines evidence and readiness records used in tests, docs, and validation
harnesses.

## MVP Readiness Evidence Pack

- `feature`: fixed value `050-mvp-launch-proof`
- `created_at`: ISO timestamp
- `release_tag`: current product release tag under validation
- `deployed_sha`: production commit SHA under validation
- `installed_app_version`: installed app version or build identity
- `owner_journey_gates`: list of Owner Journey Gate records
- `interface_findings`: list of Interface Audit Finding records
- `launch_gaps`: list of Launch Gap records
- `final_claim`: one of `pilot_blocked`, `internal_pilot_candidate`
- `forbidden_content_scan`: pass/fail status and command summary

## Owner Journey Gate

- `id`: stable gate id, for example `record-stop-upload`
- `surface`: `macos_native`, `server_backend`, `web_cabinet`,
  `desktop_embedded_web`, `production_infra`, or `docs_status`
- `status`: `pass`, `fail`, `blocked`, or `unproven`
- `evidence`: metadata-only evidence reference
- `claim_impact`: affected readiness claims
- `next_action`: required when status is not `pass`

## Interface Audit Finding

- `id`: stable finding id
- `surface`: web, embedded macOS, native macOS, or mobile-width web
- `severity`: P0, P1, P2, or P3
- `user_visible_problem`: short non-private description
- `evidence`: screenshot path outside git, DOM metric, test name, or command
  result
- `fix_status`: `open`, `fixed`, `deferred`, or `not_reproducible`
- `claim_impact`: readiness claim blocked or unaffected

## Launch Gap

- `id`: stable gap id
- `severity`: P0, P1, P2, or P3
- `journey`: owner journey or product area
- `missing_evidence`: what is still not proven
- `next_action`: smallest next step
- `claim_impact`: claim blocked by this gap

## State Rules

- `internal_pilot_candidate` is allowed only when every P1 Owner Journey Gate
  is `pass`, every P1 Interface Audit Finding is `fixed` or
  `not_reproducible`, and no P1 Launch Gap remains.
- `pilot_blocked` is required when any P1 gate is `fail`, `blocked`, or
  `unproven`.
- `production_ready` is not an allowed 050 final claim.
