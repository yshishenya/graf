# Implementation Plan: Единый ввод одноразового кода

**Branch**: `190-otp-code-input` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

## Summary

Заменить единичный прямоугольный email-code input общим server-rendered OTP
компонентом из шести слотов. Слоты будут одинаковыми в web и embedded macOS,
а vanilla JS сохранит существующий hidden `code`, автозаполнение, вставку,
клавиатурную навигацию и однократный submit.

## Technical Context

- **Language**: Python/Jinja templates, vanilla JavaScript, CSS; Swift только владеет WebView shell.
- **Dependencies**: Existing FastAPI/Jinja cabinet, `cabinet.js`, `cabinet.css`; no new dependency.
- **Storage**: N/A; existing auth state and server parameter `code` remain unchanged.
- **Testing**: pytest contract/integration tests and a Node DOM behavior harness; Swift route/workspace tests as applicable.
- **Risk / Validation Lane**: high-risk-feature — auth confirmation UX and a shared web/desktop surface.
- **Release Gate**: no deploy; focused checks plus `infra/scripts/ci-local.sh --fast`.
- **Target Platform**: Browser cabinet and macOS embedded cabinet WebView.
- **Scope**: One shared code template, one shared CSS/JS implementation, five flow contexts, two surfaces.

## Constitution Check

- Capture, storage, deletion, and provider verification are not changed.
- Auth/user-facing UX keeps shared web/desktop parity, keyboard accessibility, and existing server validation.
- No client secret/token state is introduced; digits are copied only into the existing form field at submit time.
- Public release/deploy is out of scope; local implementation and validation only.

## Validation Plan

1. Contract rendering tests for login, signup, invitation, browser link, and desktop link contexts.
2. Static CSS/JS checks plus a Node DOM harness for digit input, paste, filtering, navigation, incomplete submit, and one-shot submit.
3. Integration checks for browser email-code start/verify and embedded desktop code route actions.
4. `infra/scripts/ci-local.sh --fast` before closeout. No deploy gate applies.

## Project Structure

```text
specs/190-otp-code-input/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/otp-code-entry.md
├── checklists/security.md
├── checklists/ux.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/
├── auth_rendering.py
├── static/cabinet/cabinet.css
├── static/cabinet/cabinet.js
└── templates/cabinet/auth/email_code.html

apps/server/tests/
├── contract/test_account_merge_contract.py
├── contract/test_account_routes.py
├── contract/test_cabinet_static_assets_contract.py
└── integration/test_web_owner_session_context.py

apps/macos/
├── RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
└── Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

**Structure Decision**: The server owns auth HTML/CSS/JS. macOS only loads the
desktop route in its embedded WebView, so there is no second native OTP
implementation to change.

## Complexity Tracking

| Decision | Why it is needed | Simpler alternative rejected |
|---|---|---|
| Six visible inputs plus one hidden existing field | Meets the one-digit-per-cell UX while preserving the backend contract | Changing the backend to accept six parameters would expand auth scope |
