# Desktop Account Status

## Purpose

Show enough account, workspace, sync, and policy truth for safe recording and
upload without embedding full admin/billing UI.

## Layout

- Route: `/desktop/account`.
- Header: account avatar, display name, workspace, compact sync state.
- Status summary row:
  - `Вы вошли`
  - `Войдите снова`
  - `Сессия истекла`
  - `Нет связи`
  - `Правила устарели`
  - `Рабочее пространство заблокировало запись`
- Policy summary:
  - Recording allowed or blocked.
  - Upload allowed, queued, or blocked.
  - Retention summary.
  - Deletion boundary summary.
- Device/session:
  - Registered device state.
  - Last sync.
  - Local queue count.

## Actions

- `Войти`.
- `Повторить синхронизацию`.
- `Обновить правила`.
- `Открыть аккаунт в вебе`.
- `Выйти`.

No alternate offline auth path. Offline/local buffering is a degraded
continuation state after a trusted session and policy are already known, not an
onboarding mode.

## Browser Handoff Only

- Change email.
- Enable or manage 2FA.
- Delete account.
- Support access.
- Workspace admin.
- Billing.
- Team/users.
- SSO/session duration policy.
- Integrations.

## Required States

- `Вы вошли`.
- `Войдите снова`, recording blocked until policy is known.
- `Сессия истекла`.
- `Нет связи`.
- `Правила устарели`.
- `Рабочее пространство заблокировало запись`.

## Forbidden

- Auth copy cannot imply local recordings were deleted.
- Offline copy cannot imply the app can bypass workspace policy.
- Account actions cannot hide active recording.
- No billing/payment data in desktop.

## Acceptance Evidence

Covered by Figma `V8 02 - Первый запуск и разрешения macOS`,
`V8 09 - Настройки записи и темы`, `V8 12 - Поделиться, экспорт, удаление`,
`V8 14 - Правила интерфейса и QA`, and `design/validation-evidence.md`.
