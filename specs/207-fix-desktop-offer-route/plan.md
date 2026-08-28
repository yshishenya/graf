# Implementation Plan: Safe Desktop Offer Route

**Branch**: `codex/207-fix-desktop-offer-route` | **Date**: 2026-08-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/207-fix-desktop-offer-route/spec.md`

## Summary

Разрешить только канонический same-origin путь `/offer` как browser-owned legal-документ в общей desktop route policy. Переиспользовать существующее внешнее открытие и sanitization, не менять checkout, платежи, серверные маршруты или auth. Закрепить поведение focused XCTest и production installed-app smoke без запуска платежа.

## Technical Context

**Language/Version**: Swift 5.10+ в существующем macOS Swift Package

**Primary Dependencies**: Foundation, AppKit/WebKit и уже встроенная route policy; новых зависимостей нет

**Storage**: N/A; persistent state и миграции не меняются

**Testing**: XCTest через Swift Package Manager, затем repository fast lane

**Risk / Validation Lane**: Significant feature / shared security boundary. Изменяется общий desktop allowlist на legal/payment пути; требуется полный Spec Kit slice, focused negative checks и fast lane перед PR.

**Release Gate**: Во время реализации production не меняется. Для фактического исправления установленного клиента нужен отдельный штатный macOS release: release candidate, full exact-SHA gate, Developer ID, notarization, stapling, Gatekeeper, Sparkle publication и installed-app smoke. Серверный deploy для этого diff не нужен.

**Target Platform**: macOS 14.5+, production bundle `pro.2brain.graf`

**Project Type**: Native macOS desktop application with embedded web cabinet

**Performance Goals**: Решение маршрута остаётся синхронным и визуально мгновенным; внешнее открытие начинается в пределах обычного системного отклика UI.

**Constraints**: Fail closed для неизвестных маршрутов; только HTTPS production origin; query, fragment и пользовательские данные не передаются; открытие оферты не мутирует billing state.

**Scale/Scope**: Один канонический legal route, один общий policy path, один focused regression suite; без новой абстракции.

## Constitution Check

*GATE: PASS before and after design.*

- **Fail-closed trust boundary**: PASS — расширяется только точный `/offer`; неизвестные, внешние и не-HTTPS маршруты остаются заблокированными.
- **Secret and private-data discipline**: PASS — external URL sanitization удаляет query и fragment; evidence не содержит credentials или meeting content.
- **Local capture safety**: PASS — recording controls and local custody remain independent and untouched.
- **No parallel architecture**: PASS — используется существующая `DesktopCabinetRoutePolicy` и системное внешнее открытие.
- **Validation and release truth**: PASS — focused/fast checks отделены от обязательного signed macOS release gate.
- **Minimal change**: PASS — новых зависимостей, серверных endpoint, storage и abstractions нет.

## Validation Plan

1. Focused XCTest для точного `/offer`, sanitized external URL и negative sibling route.
2. Существующий `DesktopCabinetBillingHandoffTests` целиком.
3. `swift build --package-path apps/macos` для compile proof.
4. `infra/scripts/ci-local.sh --fast` перед PR, потому что меняется shared user-facing route policy.
5. Full CI не запускается на каждой итерации. Он обязателен только на release-candidate exact SHA через штатный macOS release/deploy gate.
6. После подписанного выпуска: installed-app smoke `Тариф и оплата → Выбрать тариф → оферту`, проверка внешнего `/offer`, возврата к checkout и отсутствия нового платежа.

## Project Structure

### Documentation (this feature)

```text
specs/207-fix-desktop-offer-route/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── desktop-offer-route.md
├── checklists/
│   ├── requirements.md
│   └── ux-security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Cabinet/
└── DesktopCabinetRoutePolicy.swift

apps/macos/Shared/Tests/
└── DesktopCabinetBillingHandoffTests.swift

CHANGELOG.md
```

**Structure Decision**: Исправление находится в единой общей route policy и уже существующем billing/navigation test suite. Новые modules, services и dependencies не создаются.

## Complexity Tracking

Constitution violations: none.
