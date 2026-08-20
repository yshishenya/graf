# Implementation Plan: Подключение email без тупиков

**Branch**: `codex/178-account-linking-journey` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/178-account-linking-journey/spec.md`

## Summary

Убрать системную блокировку двух полноценных профилей: перед переносом владельца
перевести личное пространство исходного профиля в отдельный `linked`-тип,
сохранив его ID, содержимое и membership. Затем переиспользовать существующую
proof-bound merge transaction, расширить bounded preview реальными способами
входа и заменить технический экран на согласованную IA «сейчас → после» с
конкретными действиями для настоящих блокировок.

## Technical Context

**Language/Version**: Python 3.13, Jinja2 templates, CSS; Swift tests and existing macOS route policy

**Primary Dependencies**: FastAPI, SQLAlchemy 2 async, PostgreSQL forced RLS, Jinja2

**Storage**: PostgreSQL; существующие `AccountMergeIntent`, `AccountMergeJournal`, `Workspace`, `WorkspaceMembership`

**Testing**: pytest 9, contract/unit tests, disposable PostgreSQL app-role/RLS checks, in-app Browser, macOS Computer Use

**Risk / Validation Lane**: `high-risk-feature` — auth, identity ownership, RLS, user data and cross-surface UX

**Release Gate**: focused checks during implementation; `infra/scripts/ci-local.sh --fast` before PR; full CI and `infra/scripts/cd-remote.sh --dry-run` only for approved production release

**Target Platform**: Linux-hosted web service plus browser and embedded macOS WebView

**Project Type**: server-rendered web application embedded in the native macOS app

**Performance Goals**: preview and confirm add only bounded indexed reads for two users; no content scan beyond existing meeting/artifact counts

**Constraints**: fail closed; one-use proof/CSRF/nonce/idempotency unchanged; stable workspace and meeting IDs; metadata-only audit; no real production account data in tests

**Scale/Scope**: one account-linking transaction, two user roots, bounded provider/workspace summaries, existing web/desktop route pair

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Spec-driven delivery**: PASS — feature 178 has specify/clarify/plan and will run security plus UX/accessibility checklists, tasks and analyze before code.
- **Auth and privacy boundary**: PASS — existing proof-bound intent, fresh preflight, row locks, CSRF, idempotency, forced RLS and metadata-only audit remain authoritative.
- **Data lifecycle**: PASS — no workspace, meeting, file, audit or source-user row is deleted; stable IDs and deletion blockers remain intact.
- **Original UI and brand distance**: PASS — selected visual is an original GRAF mock and implementation reuses current tokens/components; visual QA is a release gate.
- **Public macOS integrity**: PASS — no native binary behavior or signing surface changes; embedded route parity is validated through the existing app.
- **Production gate**: PASS — deployment is deferred until focused evidence, fast CI, PR review and the release dry-run all pass.

Post-design re-check: the `linked` workspace kind is deliberately neither
personal nor corporate. It avoids duplicate personal-only billing/trial/referral
privileges and does not expose corporate invitation/admin behavior. Existing RLS
request access still requires the survivor's active membership.

## Validation Plan

1. Unit/contract checks for policy, provider projection, wording, routes,
   responsive semantics and actionable blocker mappings.
2. PostgreSQL integration cases for two personal workspaces, transformation to
   `linked`, stable IDs/content, rollback, stale preview, replay, concurrent
   confirmation, forced RLS and session/device revocation.
3. Existing email, Yandex ID and VK login/provider-link regression subset.
4. Browser flow at wide and 390px widths, keyboard/focus/console inspection.
5. Embedded macOS flow through the installed local app, including allowed route
   navigation and post-confirm login handoff.
6. Correctness, security/privacy, UX/accessibility and Ponytail review passes.
7. One `ci-local.sh --fast` closeout before PR; full CI only at release gate.

## Project Structure

### Documentation (this feature)

```text
specs/178-account-linking-journey/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/account-linking.md
├── checklists/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── auth/account_merge.py
├── auth/provider_links.py
├── auth/workspace_onboarding.py
├── api/auth.py
├── cabinet/rendering.py
├── cabinet/web_routes/account_merge.py
├── cabinet/web_routes/auth_email_flow.py
├── cabinet/templates/cabinet/pages/account_merge_content.html
├── cabinet/static/cabinet/cabinet.css
├── db/models/identity.py
├── db/models/federated_auth.py
└── db/migrations/versions/0074_linked_workspace_and_merge_proofs.py

apps/server/tests/
├── unit/test_account_merge_policy.py
├── unit/test_workspace_onboarding.py
├── contract/test_account_merge_contract.py
├── contract/test_account_routes.py
└── integration/test_account_merge.py

apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift
apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift
```

**Structure Decision**: сохранить существующий server-rendered путь и общий
template для web/macOS; не добавлять SPA, wizard, клиентское состояние или новую
support-систему.

## Complexity Tracking

Нарушений конституции и оправдываемых исключений нет.
