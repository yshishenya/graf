# Implementation Plan: Desktop Billing Actions

**Branch**: `codex/208-desktop-billing-actions` | **Date**: 2026-08-28 | **Spec**: [spec.md](spec.md)

## Summary

Расширить существующий точный billing allowlist в общей macOS route policy всеми user-visible POST-действиями, которые уже рендерит сервер. Не менять серверные handlers и платёжную семантику. Закрепить полный перечень одним focused XCTest и negative sibling cases.

## Technical Context

**Language/Version**: Swift 5.10+

**Primary Dependencies**: Foundation и существующая desktop route policy; новых зависимостей нет

**Storage**: N/A; данные, миграции и production-конфигурация не меняются

**Testing**: XCTest через Swift Package Manager, Swift build, repository fast lane

**Risk / Validation Lane**: High-risk product area / shared billing navigation boundary. Используется полный Spec Kit slice, обязательные clarify/checklist/analyze, focused negative checks и repository gate перед PR.

**Release Gate**: Реализация и PR не меняют production. Для установленного клиента нужен отдельный exact-SHA macOS release с full CI, Developer ID, notarization, stapling, Gatekeeper, Sparkle publication и installed-app smoke. Параллельный release/deploy запрещён.

**Target Platform**: macOS 14.5+, production bundle `pro.2brain.graf`

**Project Type**: Native macOS application with embedded server-rendered cabinet

**Performance Goals**: Синхронная классификация маршрута без пользовательски заметной задержки

**Constraints**: Exact allowlist; неизвестные siblings fail closed; POST body не переписывается и не повторяется; YooKassa остаётся test-shop; новая оплата при focused QA не создаётся

**Scale/Scope**: Один helper, один существующий test suite, документация slice; без серверного diff

## Constitution Check

*GATE: PASS before and after design.*

- **Billing trust boundary**: PASS — разрешаются только уже существующие user-visible actions; server-side auth, CSRF, tenant, idempotency и launch gates остаются authoritative.
- **Secret discipline**: PASS — test paths содержат только синтетический safe number; credentials, provider IDs и payment payloads не фиксируются.
- **No production mutation**: PASS — миграции, runtime config и YooKassa shop не меняются; focused QA не создаёт платёж.
- **Fail-closed desktop policy**: PASS — unknown siblings остаются blocked.
- **No parallel architecture**: PASS — переиспользуется `DesktopCabinetRoutePolicy.isBillingRoute`.
- **Release truth**: PASS — code validation отделена от подписанного exact-SHA release gate.
- **Minimal change**: PASS — один shared policy helper и один regression suite.

## Design

1. Канонический перечень берётся из текущих форм и POST handlers billing UI.
2. `isBillingRoute` сохраняет существующие GET-маршруты и добавляет exact static action paths.
3. Status actions разрешаются только по схеме `billing/checkout/status/<safe-number>/<refresh|continue>`.
4. Request policy не перезагружает POST и не добавляет headers повторной загрузкой; server получает исходный form request.
5. Negative cases доказывают, что произвольные вложенные действия не разрешены.

## Validation Plan

1. RED/GREEN: `swift test --package-path apps/macos --filter DesktopCabinetBillingHandoffTests`.
2. Sibling policy: `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests`.
3. Compile: `swift build --package-path apps/macos`.
4. Before PR: `infra/scripts/ci-local.sh --fast`.
5. Before release/deploy: synchronize with latest master, verify deploy lock and active release worktrees, then full exact-SHA gate.
6. Installed-app smoke uses preview only first; payment start is exercised only with explicit test-payment authorization and no duplicate charge.

## Project Structure

```text
specs/208-desktop-billing-actions/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── desktop-billing-routes.md
├── checklists/
│   ├── requirements.md
│   └── billing-security.md
└── tasks.md

apps/macos/RecApp/Sources/Cabinet/
└── DesktopCabinetRoutePolicy.swift

apps/macos/Shared/Tests/
└── DesktopCabinetBillingHandoffTests.swift
```

## Complexity Tracking

Constitution violations: none.
