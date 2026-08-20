# Implementation Plan: Стабильное подключение email в приложении

**Branch**: `codex/176-fix-email-link-route` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/176-fix-email-link-route/spec.md`

## Summary

После отправки embedded-формы подключения email WebKit должен сохранить
полученный экран ввода кода, не превращая исходный POST URL в новый GET.
Исправление расширяет существующий request-identity predicate: mutating request
не становится SwiftUI-owned route, direct-response email endpoints остаются
WebKit-owned, а SwiftUI не запускает повторный GET к уже активному или pending
URL. Другой route по-прежнему может заменить текущую загрузку. Серверный
auth-контракт, доставка, CSRF, rate limit, одноразовые коды и account merge не
меняются.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Swift 6 package with macOS AppKit/SwiftUI integration

**Primary Dependencies**: SwiftUI, WebKit, Foundation; no new dependency

**Storage**: N/A; no model, schema, cookie or migration change

**Testing**: XCTest through Swift Package Manager; existing focused server
contract tests as unchanged-contract evidence

**Risk / Validation Lane**: `high-risk-feature` — authenticated account linking
inside an embedded WebView and a production-visible regression

**Release Gate**: focused tests and `ci-local.sh --fast` before PR; production
hotfix requires release preparation, `cd-remote.sh --dry-run`, signed/notarized
macOS artifact checks and the repository release/deploy gate

**Target Platform**: macOS desktop app with server-rendered embedded settings

**Project Type**: desktop app plus unchanged FastAPI HTML contract

**Performance Goals**: no extra request or visible delay; code form remains
available within 5 seconds of the successful server response

**Constraints**: preserve same-origin headers, session cookies, CSRF, rate
limits, one-time code semantics and provider/account merge behavior; never log
email, code, token, state nonce or private account identifiers

**Scale/Scope**: one shared route-tracking predicate, its two existing call
phases and focused regression coverage; no auth redesign

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Spec-driven delivery**: PASS — Feature 176 uses mandatory clarification,
  security/UX checklists, tasks, analyze and issue sync before implementation.
- **Auth/privacy boundary**: PASS — only desktop navigation ownership changes;
  server auth, session, CSRF, rate limit and account-link rules stay intact.
- **Secret/evidence discipline**: PASS — synthetic routes and metadata only;
  no email, code, token, nonce or account data in committed evidence.
- **User-visible recovery**: PASS — existing code, resend, error and back
  screens remain server-owned and accessible inside the app.
- **Release integrity**: PASS — a public macOS hotfix must remain Developer ID
  signed, notarized, stapled, Gatekeeper-accepted and Sparkle-valid.
- **Post-design re-check**: PASS — no schema, dependency, egress, entitlement
  or constitution exception was added.

## Validation Plan

1. Add a focused XCTest that fails when a POST settings form is eligible to
   become a SwiftUI-owned GET route and proves stable GET/redirect behavior.
2. Run `DesktopCabinetWorkspaceTests` and adjacent route/header policy tests.
3. Run focused account route tests to prove the server remains POST-only and
   embedded form actions remain correct.
4. Run `infra/scripts/ci-local.sh --fast` once after implementation and review.
5. Perform metadata-safe local app smoke without recording real email, codes,
   tokens, cookies, meeting content or private account identifiers.
6. Before production, run the release dry-run and mandatory signed/notarized
   macOS release checks; execute deployment only at the release boundary.

## Project Structure

### Documentation (this feature)

```text
specs/176-fix-email-link-route/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── embedded-navigation.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
├── RecApp/Sources/Cabinet/DesktopCabinetNavigationResponsePolicy.swift
├── Shared/Tests/DesktopCabinetConfigurationTests.swift
└── Shared/Tests/DesktopCabinetWorkspaceTests.swift

apps/server/
├── src/twobrain_rec_server/cabinet/auth_rendering.py
├── src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
├── src/twobrain_rec_server/cabinet/templates/cabinet/auth/email_code.html
├── src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py
├── src/twobrain_rec_server/cabinet/web_routes/settings.py
├── tests/contract/test_account_routes.py
├── tests/contract/test_cabinet_static_assets_contract.py
└── tests/integration/test_web_owner_session_context.py
```

**Structure Decision**: Reuse the existing WebView route-identity owner and its
existing test module. Server rendering disables only the problematic embedded
entry animation; the existing auth flow preserves CSRF for every retry form.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations or justified complexity exceptions.
