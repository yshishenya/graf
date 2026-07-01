# Data Model: Deep Architecture Audit

Feature 072 does not add application data tables or runtime models. This file
defines the audit records used by the documentation artifacts and roadmap.

## Architecture Surface

Represents a product area under audit.

- `id`: Stable short identifier, for example `server.cabinet`.
- `name`: Human-readable surface name.
- `paths`: Exact repository paths included in the surface.
- `owner_boundary`: Capture, auth, privacy, deletion, processing, cabinet,
  support, infra, release, or docs.
- `runtime_role`: What the surface does at runtime.
- `evidence`: Links to files, commands, or docs used to support the assessment.

## Dependency Graph

Represents static dependency evidence for one ecosystem.

- `graph_id`: `python-server`, `swift-macos`, `shell-infra`, or
  `docker-runtime`.
- `scope`: Paths inspected.
- `nodes`: Packages, modules, targets, scripts, services, or containers.
- `edges`: Import, target dependency, script call, service dependency, or
  runtime command relationship.
- `interpretation`: What the graph says about boundaries or risk.
- `limitations`: Known static-analysis blind spots.

## Runtime Flow

Represents an end-to-end behavior path.

- `flow_id`: Stable identifier, for example `capture-to-upload`.
- `start_event`: User, system, worker, or deploy event that starts the flow.
- `steps`: Ordered repository-backed steps.
- `state_transitions`: Local files, queue items, DB rows, object storage, worker
  state, or cabinet state touched by the flow.
- `trust_boundaries`: Native desktop, server API, background worker,
  third-party service, storage, admin, or deploy boundary.
- `validation_needed`: Checks required before refactoring the flow.

## Architecture Finding

Represents one actionable architecture observation.

- `finding_id`: Stable identifier, for example `F-072-001`.
- `title`: Short name.
- `classification`: One of `delete now`, `split soon`, `keep intentionally`,
  or `risky / needs spec`.
- `paths`: Exact paths involved.
- `evidence`: Caller/runtime/control-boundary evidence.
- `risk`: What could break if changed casually.
- `recommended_next_step`: Future PR, focused validation, or separate Spec Kit
  slice.
- `pre_refactor_checks`: Checks required before changing the code.

## Refactor Batch

Represents a safe future PR unit.

- `batch_id`: Stable identifier, for example `RB-072-01`.
- `goal`: Plain-language outcome.
- `included_findings`: Finding IDs addressed by the batch.
- `excluded_scope`: Explicit boundaries not touched.
- `validation`: Focused checks and repository gates required before merge.
- `release_policy`: Whether local CI, dry-run, execute deploy, or no deploy is
  appropriate.

## Boundary Gate

Represents a non-negotiable product safety boundary.

- `boundary_id`: Capture, auth-session-device, privacy, deletion-retention,
  MediaScribe, Langfuse, MinIO-Postgres-Temporal, desktop-WebView-cabinet, or
  deploy.
- `current_contract`: What must remain true.
- `evidence_sources`: Docs and code paths supporting the contract.
- `risk_signals`: What indicates a refactor must become a separate spec.
- `required_checks`: Validation before changing code in that boundary.

