# Feature Specification: Надёжный email-вход в macOS WebView

**Feature Branch**: `134-email-login-webview`
**Created**: 2026-08-06
**Status**: Ready for implementation
**Tracking**: [GitHub #4734](https://github.com/yshishenya/crisp/issues/4734)

## User Stories

### User Story 1 - Войти по email и подтвердить код (Priority: P1)

Как пользователь GRAF, я хочу ввести email, получить код и завершить вход во
встроенном окне приложения, чтобы открыть встречи.

**Acceptance Scenarios**:

1. **Given** открыта форма `/login`, **When** пользователь отправляет email,
   **Then** страница с кодом остаётся видимой и приложение не запускает повторный
   `GET` для endpoint отправки кода.
2. **Given** отображается форма кода, **When** введён действительный код,
   **Then** сессия сохраняется и открываются встречи.
3. **Given** код неверен или истёк, **When** сервер возвращает ошибку,
   **Then** форма остаётся доступной для повторного ввода.

### User Story 2 - Не изменить вход через Яндекс (Priority: P1)

Вход через Яндекс продолжает проходить provider и callback routes без повторного
запуска OAuth continuation.

## Requirements

- **FR-001**: WebView MUST treat `/login/email/start`, `/login/email/verify`,
  `/sign-up/email/start` и `/sign-up/email/verify` as transient form-response
  routes, not as SwiftUI-owned GET routes.
- **FR-002**: WebView MUST preserve the current auth document and cookies until
  the next server navigation.
- **FR-003**: Existing session, redirect, same-origin allowlist and Yandex OAuth
  behavior MUST remain unchanged.
- **NFR-001**: Diagnostics MUST remain metadata-only and exclude email addresses,
  codes, cookies, tokens, meeting content and audio.

## Success Criteria

- **SC-001**: Focused macOS tests pass for all four email form endpoints.
- **SC-002**: Email login completes without `GET /login/email/start` or
  `GET /sign-up/email/start` replay.
- **SC-003**: Existing Yandex OAuth and meeting-shell tests remain green.

## Out of Scope

Server auth policy, email delivery, session schema, capture, virtual audio
driver, production deployment mechanics and credentials.
