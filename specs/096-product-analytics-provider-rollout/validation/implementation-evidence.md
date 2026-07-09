# Implementation Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `planning_created`

This file records what has been completed for the planning pass and defines how
future implementation evidence must be added. It is safe to commit because it
contains no live secrets, counter IDs, project keys, payloads, screenshots,
visitor/account identifiers, meeting content, transcripts, audio, signed URLs,
local paths, cookies, or private provider exports.

## Planning Pass Evidence

| Item | Status | Evidence |
| --- | --- | --- |
| Risk lane | complete | High-risk Spec Kit provider/infrastructure rollout selected. |
| Baseline | complete | 096 starts after merged/deployed 094 scaffold and reuses 093 public analytics baseline. |
| Specify | complete | `spec.md` created for 096. |
| Clarify | complete | Clarifications recorded for PostHog first-party scope, Yandex counter reuse, hosting/domain posture, PostHog autocapture everywhere, and two Yandex offline conversions. |
| Plan | complete | `plan.md`, `research.md`, `data-model.md`, contracts, quickstart, and validation templates created. |
| Checklist | complete | `checklists/provider-rollout.md` reviewed against 096 artifacts. All 52 requirement-quality checks are complete after adding explicit same-server PostHog resource-threshold requirements. |
| Tasks | complete | `tasks.md` generated with 90 dependency-ordered tasks across setup, foundation, four user stories, and final validation. |
| Analyze | complete | `$speckit-analyze` found no critical blockers and identified RBAC/audit, lifecycle, deploy-dry-run, and placeholder consistency remediation. |
| Analyze remediation | complete | Planning artifacts and tasks were tightened so RBAC/audit access model, provider retention/deletion lifecycle truth, PostHog deploy dry-run handoff, and concrete script/doc paths are explicit before implementation. |
| Repeat analyze remediation | complete | Secret inventory owner/rotation coverage and stale plan wording were tightened before `$speckit-taskstoissues`. |
| Agent context | complete with local tool caveat | Official agent-context helper was attempted, but the local Python environment lacked `PyYAML`; the managed `AGENTS.md` Spec Kit plan pointer was updated manually to the 096 plan path. |
| Implementation | not started | No provider deploy, live secret wiring, dashboard setup, or provider smoke execution in this pass. |
| Production deploy | not started | `cd-remote.sh --execute` not run in this pass. |
| Paid campaign launch | blocked | Campaign launch remains outside 096 readiness. |

## Official Documentation Reviewed

Planning research reviewed official provider documentation for:

- self-hosted PostHog operations and operator responsibility;
- self-hosted PostHog environment configuration;
- self-hosted PostHog session replay storage;
- Yandex Metrica OAuth authorization;
- Yandex Metrica quick start and required scopes;
- Yandex Metrica offline conversion upload.

See [research.md](../research.md) for decisions and source links.

## Required Future Evidence

Implementation tasks must append metadata-only evidence for:

- PostHog Docker Compose/service readiness;
- analytics domain/TLS readiness;
- PostHog secret-file wiring;
- PostHog backup/restore proof;
- PostHog resource limit and retention proof;
- PostHog RBAC/access model and audit expectation proof;
- provider retention/deletion lifecycle proof for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboard/report aggregates;
- separate PostHog stack deploy dry-run handoff proof;
- PostHog server-mediated delivery smoke;
- PostHog web-direct delivery smoke;
- PostHog desktop-direct delivery smoke;
- PostHog autocapture page inventory proof;
- PostHog replay disabled proof;
- Yandex counter reuse proof without live counter ID;
- Yandex `/` and `/download` baseline proof;
- Yandex blocked-page rendering proof;
- Yandex offline conversion OAuth secret-file proof;
- Yandex offline live upload smoke for exactly two conversion names;
- duplicate-protection proof;
- dashboard readiness proof;
- rollback proof;
- no-secret/evidence scan;
- local CI and deploy dry-run result.

## Required Validation Commands

Later implementation must record command names and pass/fail summaries for:

```sh
rg -n "\[NEEDS CLARIFICATION\]|NEEDS CLARIFICATION:" specs/096-product-analytics-provider-rollout
git diff --check
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

The later implementation may add focused pytest, SwiftPM, browser/page, Docker,
and provider smoke commands while completing the generated tasks.

## Evidence Safety Rules

Allowed evidence:

- command names;
- pass/fail status;
- redacted environment labels;
- event names;
- conversion names;
- page-class states;
- dashboard/report names;
- retention days;
- backup/restore status;
- rollback status;
- blocker names.

Forbidden evidence:

- live PostHog project keys or internal secrets;
- live Yandex counter IDs or OAuth tokens;
- cookies, ClientIDs, Yclids, visitor IDs, or user IDs;
- emails, names, account identifiers, or private local paths;
- signed URLs;
- raw request/response payloads;
- Yandex CSV rows;
- PostHog event/autocapture/replay exports;
- screenshots with visitor/account/meeting data;
- raw audio, transcript text, meeting content, or meeting filenames.

## Current Blockers Before Implementation

Implementation must still complete:

- `$speckit-taskstoissues`;
- implementation and validation tasks;
- explicit production deploy approval for any `--execute` step.

Known planning blockers closed before `$speckit-taskstoissues`:

- RBAC/audit access model is now explicit in tasks, contracts, data model, smoke, and dashboard evidence.
- Provider retention/deletion lifecycle truth is now explicit for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboards.
- Separate PostHog stack deploy dry-run handoff is now explicit for `infra/scripts/cd-remote.sh` and validation evidence.
- Placeholder-style script/doc structure in the plan has been replaced with concrete paths.
