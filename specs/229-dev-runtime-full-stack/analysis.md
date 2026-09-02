# Specification Analysis Report

Дата: 2026-09-01
Feature: 229 / issue #6276
Lane: `high-risk-feature`

## Findings and remediation

| ID | Category | Severity | Status | Evidence |
|---|---|---:|---|---|
| C1 | Boundary | CRITICAL | Resolved | Dev Compose no longer consumes the server `.env.example`; provider endpoints and credential-file variables are explicit deny-by-default values. |
| C2 | Ordering | CRITICAL | Resolved | `start-dev-runtime.sh` runs Compose config/infra, migration preflight, then migration, then API/workers. |
| C3 | Rollback | HIGH | Resolved | Live rollback requires checkout `HEAD == target.source_sha`; app/runtime are restored only through the owned staged path. |
| C4 | Legacy | HIGH | Resolved | Active adapter points only to `docker-compose.dev.yml`/`start-dev-runtime.sh`; old local path is documented as non-active exception. |
| H1 | Ownership | HIGH | Resolved | `.specify/feature.json` lists every F229 implementation, test, fixture and documentation path. |
| H2 | Identity | HIGH | Resolved | Compose build args and service labels carry the requested 40-character SHA; smoke inspects running container labels. |
| H3 | Smoke coverage | HIGH | Resolved | Smoke has named API, frontend, auth, database, storage, migration, Temporal, processing-worker, media-worker, app-identity and exact-SHA checks. |
| H4 | Evidence | HIGH | Resolved | Fixture smoke is marked `authoritative=false`; only live smoke can produce an authoritative promotion result. |
| H5 | Promotion | HIGH | Resolved | F229 metadata-only promotion rejects `health.result != pass`; live promotion supplies checks from the adapter. |
| H6 | Contract | MEDIUM | Resolved | Dev project, ports, origins, service names and bounded readiness intervals are explicit in Compose/startup/docs. |
| H7 | App continuity | HIGH | Resolved | Installer accepts exactly `/Applications/GRAF Dev.app` and compares bundle ID, designated requirement, signer and entitlements before replacement. |
| H8 | Retirement | HIGH | Resolved | Legacy exception has ISO expiry `2026-10-31` and points to Feature 228 issue #6238/T000. |
| H9 | Dependency | HIGH | Resolved | F227 PR #6275 merged as `0f3becdc9970c0a86fc8aa273ef1bc26eca0b5a0`; the presentation-lifecycle follow-up is based on current master `18f35e0d7c3ada16a7c13c6bf1dc1a5247cdab2f`. |

## Requirement coverage

All fourteen functional requirements and all seven buildable success criteria have
at least one task and an evidence path. The explicit mapping is maintained in
`plan.md` under “Requirement and success-criteria traceability”.

| Metric | Result |
|---|---:|
| Functional requirements | 14 |
| Buildable success criteria | 7 |
| Planned tasks | 40 |
| Requirements with task coverage | 100% |
| Critical findings remaining | 0 |
| High findings remaining | 0 |
| Reviewer checklist markers changed | 0 |

## Constitution alignment

No constitution MUST is intentionally weakened. Capture semantics are untouched;
provider credentials remain server-side and disabled by default; Dev data and
origins are isolated; promotion is lock-protected and fail-closed; public
notarization/release rules are out of scope; Spec Kit high-risk gates remain
required. The retained `start-local.sh` path is a bounded exception with an
owner, expiry, removal trigger and linked retirement task.

## Gate and next actions

The dependency gate is resolved. T038 exact-SHA GitHub fast validation and T039
clean-state live smoke remain open after the lifecycle follow-up. Reviewer-owned
infra, requirements and security checklist items also remain open; their
markers are intentionally unchecked and require a separate reviewer.

No `taskstoissues` or production operation is performed in this implementation
turn; existing issue links remain the external tracker source of truth.
