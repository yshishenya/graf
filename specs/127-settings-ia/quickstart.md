# Quickstart: проверка settings IA

## Prerequisites

- Repository checkout with Python dependencies installed via `uv`.
- Test environment variables required by the existing server fixtures.
- For the browser smoke, a seeded authenticated cabinet session.

## Focused validation

From repository root:

```sh
cd apps/server
PYTHONPATH=src uv run pytest \
  tests/unit/test_cabinet_navigation_model.py \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_provider_link_settings_contract.py \
  tests/contract/test_calendar_settings_contract.py
```

Expected result: all focused settings contracts pass and no HTML assertion
contains provider subjects, candidate contact data or credentials.

## Manual scenario A: discoverability

1. Open `/meetings` as an authenticated user.
2. Choose «Настройки» in the global navigation.
3. Confirm `/settings` opens the overview.
4. Open «Итоги», «Интеграции → Календари», «Аккаунт и безопасность» and
   «Пространство и команда» from the inner navigation.
5. Confirm «Уведомления» is visible in the same settings navigation and opens
   its own page without relying on the account sub-navigation.
6. Repeat steps 2–5 in `/desktop/meetings` and confirm the embedded paths remain
   under `/desktop/`.
7. In the installed GRAF macOS client select the web cabinet's «Настройки»
   link and confirm the overview opens inside the webview; the native gear in
   the recording rail must remain the separate «Автозапись» handoff.

### Manual scenario D: browser-owned billing handoff

1. From the embedded desktop cabinet select «Тариф и оплата».
2. Confirm the system opens the browser-owned billing route without copying
   headers, cookies or tokens into the URL.
3. If the browser has no validated session, confirm it opens the normal login
   page with `/billing` as the safe return path; it must not show raw JSON 401.
4. Repeat with `/settings`, `/account`, `/referrals` and their supported
   desktop aliases. API paths must continue returning problem JSON to API
   clients.

## Manual scenario B: scope and safe empty states

1. Use a member workspace and an owner workspace.
2. Confirm scope labels and disabled owner-only controls explain the reason.
3. Use a user with no calendar source, no actionable invitation and no
   additional provider; confirm each category has an intentional empty state.

## Manual scenario C: mutations and recovery

1. Change calendar preferences and attempt to reload/leave before saving;
   confirm the dirty state is communicated.
2. Force a safe calendar/provider failure; confirm the form retains non-secret
   values and shows a retry path without echoing credentials.
3. Revoke a non-current device after confirmation; confirm the result is
   announced and the device state is no longer presented as active.

## Accessibility scenario

Keyboard-only review of overview, every category, provider dialog and device
confirmation: Tab order is logical, focus is visible, Escape closes dialogs,
focus returns to the opener, and all statuses/errors are announced.

## Repository gate

After focused checks pass, run:

```sh
infra/scripts/ci-local.sh
```

The original server-only feature had no deploy gate. The corrective macOS
rollout follows the repository release guidance and requires explicit approval;
hardware capture acceptance is not required because the implementation does
not change capture behavior.
