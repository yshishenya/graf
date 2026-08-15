# Implementation Plan: Встроенные тарифы и оплата

**Branch**: `codex/149-settings-auth-handoff` | **Date**: 2026-08-15 | **Spec**: [spec.md](spec.md)

## Summary

Переклассифицировать существующие billing document routes как embedded, убрать desktop billing handoff в системный браузер и добавить узкую allowlist-проверку YooKassa checkout navigation. Серверные auth, CSRF и billing ownership contracts не ослабляются.

## Technical Context

**Language/Version**: Swift 6/macOS WebKit; Python 3.11/FastAPI

**Primary Dependencies**: WKWebView, existing `DesktopCabinetRoutePolicy`, existing YooKassa allowlist

**Storage**: Existing PostgreSQL billing/session records; no schema change

**Testing**: XCTest focused route/navigation tests; focused pytest billing/auth tests; `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: high-risk-feature — auth boundary and user-visible payment UX

**Release Gate**: cd dry-run first; production execute only after explicit approval and full release gate

**Target Platform**: notarized macOS app and existing FastAPI server

**Project Type**: desktop app + web service

**Performance Goals**: no additional network round trip for ordinary billing navigation

**Constraints**: no secrets/tokens in URLs; no new dependency; preserve browser-owned sibling routes

## Constitution Check

- PASS: auth/session, CSRF, tenant, payment-provider allowlist and secret boundaries remain fail-closed.
- PASS: no capture, deletion, storage, or observability contract changes.
- PASS: clean-room UX remains the existing GRAF shell.

## Validation Plan

1. Run Spec Kit requirements/security/UX checklist and analyze pass.
2. Run focused macOS route/navigation tests and billing trust-boundary tests.
3. Run `infra/scripts/ci-local.sh --fast`.
4. For release, run full CI through the approved CD gate, notarization, Sparkle and production smoke; GitHub Actions remain disabled.

## Project Structure

```text
specs/149-embedded-billing/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/embedded-billing.md
├── checklists/requirements.md
├── checklists/security.md
├── checklists/ux.md
└── tasks.md

apps/macos/RecApp/Sources/Cabinet/
├── DesktopCabinetRoutePolicy.swift
├── DesktopCabinetNavigationRequestPolicy.swift
└── EmbeddedCabinetWebView.swift
apps/macos/Shared/Tests/
└── DesktopCabinetRoutePolicyTests.swift
```

**Structure Decision**: Reuse the existing client route/navigation policy and server billing contracts; no new service or abstraction.

## Complexity Tracking

No constitution violations and no new dependencies.
