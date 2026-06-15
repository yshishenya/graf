# Desktop Embedded Cabinet Entry

## Purpose

Define the safe server-rendered cabinet subset allowed inside the macOS app.

## Allowed Desktop Routes

- `/desktop/meetings`
- `/desktop/meetings/:id`
- `/desktop/meetings/:id/speakers`
- `/desktop/upload`
- `/desktop/processing/:id`
- `/desktop/account`
- `/desktop/workspace-policy`
- `/desktop/settings/basic`
- `/desktop/deletion/:id`

## Desktop Sidebar

Visible:

- `Встречи`
- `Обзор`
- `Настройки`
- `Помощь`

Not separate sidebar destinations:

- Upload appears as `Загрузить медиа` in the meeting workspace header, empty
  state, row action, or upload sheet.
- Processing appears as row/detail status inside `Встречи`, not as a global
  destination.
- Speaker assignment appears from a meeting review row or detail action.
- Account, policy, storage, language, and notifications live inside
  `Настройки`.
- Share, export, delete, admin, security, billing, and full access governance
  hand off to the browser.

Footer:

- Compact sync/session text: `Синхронизировано`, `Нет связи`,
  `Вход требуется`, or `Правила устарели`.
- `Открыть полный веб-кабинет`.

Hidden or handoff:

- Admin
- Billing
- Team/users
- Global action items
- Contacts management
- Activity center
- Sharing/public links
- Downloads/export management
- Integrations
- Developer/API
- Detailed audit
- Help/legal

## Loading And Failure States

- `Загружаем кабинет`: skeleton rows only, capture strip remains real.
- `Войдите снова`: account prompt with recording and sync truth.
- `Нет связи`: local recording and queue remain visible when prior policy
  allows it.
- `Откроется в браузере`: handoff banner with `Открыть в браузере` and
  `Остаться здесь`.
- `Запись недоступна`: explain the workspace rule and show the next account or
  browser action.

## Boundary Rules

- Embedded product UI cannot own `Записать`, `Остановить`, permission state,
  local queue truth, local diagnostics, or active recording indicator.
- During active recording, every embedded route preserves the native strip.
- Browser-only links never load hidden admin UI inside desktop.
- Speaker assignment is an allowlisted embedded route. The macOS app hosts the
  server-rendered speaker panel, keeps the platform capture strip visible, and
  does not duplicate speaker/diarization business logic in app code.
- Embedded speaker assignment keeps the browser lane model: one horizontal
  track per speaker, speaker-specific segments, talk-time percentage, and
  compact fixed-width action buttons.

## Acceptance Evidence

Covered by Figma `V8 00 - Карта MVP-потока и границы`,
`V8 03 - Рабочее пространство встреч`, `V8 08 - Дорожки назначения спикеров`,
`V8 09 - Настройки записи и темы`, and `design/validation-evidence.md`.
