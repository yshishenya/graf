# Desktop Home Ready

## Purpose

Default macOS first screen for a signed-in owner. It must show capture
readiness and a real meeting library, not diagnostics. Offline/local buffering
is a degraded state of the signed-in product, not a primary "continue locally"
auth path.

## Frame And Density

- Target: `1080 x 760`.
- Minimum: `960 x 680`.
- Titlebar/toolbar: `52 px`.
- Native capture strip: `84 px`, pinned below toolbar.
- Embedded cabinet fills remaining height.
- Left embedded sidebar: `216 px`.
- Main content padding: `24 px`.
- Meeting row height: `60 px`.

## Toolbar

Left:

- App mark and `2brain Rec`.
- Workspace chip: short workspace name.
- Compact sync/policy chip: `Синхронизировано`, `Нет сети`,
  `Вход требуется`, `Политика устарела`, or `Запись недоступна`.

Right:

- Refresh/sync icon button.
- Account avatar/menu.
- `Открыть веб-кабинет` icon button.

No toolbar item may start or stop recording. Capture controls stay in the
native strip.

## Native Capture Strip

Left group:

- Status dot and label: `Готово к записи`, `Нет сети`, or
  `Нужно разрешение`.
- Source line: `Звук системы + микрофон`.
- Policy line: `Ручной старт` or `Будем спрашивать перед встречей`.

Center group:

- Two meters with labels `Микрофон` and `Система`.
- When idle, meters show muted baseline and copy `Проверим при старте записи`.
- Permission summary uses compact icons, not diagnostic prose.

Right group:

- Primary `Начать запись` button, `40 px` high, minimum `128 px` wide.
- Secondary `Загрузить медиа` button that opens an embedded/web upload sheet.
- Overflow button for `Настройки`, `Диагностика`, `Журнал`.

## Embedded Cabinet Home

Sidebar items visible in desktop:

- `Встречи`
- `Обзор`
- `Настройки`

Upload, processing, speaker assignment, share/export/delete, account security,
and admin are not separate desktop sidebar destinations. They appear as
meeting-row states, sheets, embedded review routes, or browser handoffs.

Footer:

- Compact workspace/sync state.
- `Открыть полный веб-кабинет`.

Main header:

- Title: `Встречи`.
- Search field: `Поиск по встречам, тексту, людям`.
- Status tabs: `Все`, `Нужна проверка`, `В работе`, `Только на этом Mac`,
  `Ошибка`.
- Primary action: `Загрузить медиа`.

List rows require:

- Source icon: desktop recording, uploaded media, imported recording.
- Title.
- Date/time.
- Duration if known.
- Status chip with icon and label.
- Progress line if processing.
- Primary row action: `Открыть`, `Смотреть статус`, `Повторить`, or
  `Загрузить`.
- When transcript is ready, a secondary `Speakers` action may open the embedded
  server-owned speaker assignment route inside the desktop app.
- Overflow row menu for safe secondary actions.

## Required States

- User signed in and ready: `Готово к записи`.
- User signed out: `Войдите снова`, no primary local bypass.
- Sync unavailable: `Нет связи`, local buffer can continue only if prior
  policy permits it.
- Stale policy: `Правила устарели`, recording blocked until refresh.
- No meetings: `Встреч пока нет`.
- Recent meetings with mixed statuses.
- Embedded cabinet loading.
- Embedded cabinet unavailable.

## Empty State

Visible when no meetings exist:

- Title: `Встреч пока нет`.
- Body: `Запишите разговор на этом Mac или загрузите медиафайл. Транскрипт
  появится после обработки.`
- Primary: `Записать`.
- Secondary: `Загрузить медиа`.
- Tertiary: `Открыть веб-кабинет`.

No fake rows or sample transcript content.

## Forbidden

- No driver diagnostics in the first viewport.
- No web-rendered `Остановить`.
- No hidden or silent recording.
- No claim that upload or transcription has happened before the state exists.

## Acceptance Evidence

Covered by Figma `V8 03 - Рабочее пространство встреч`,
`V8 04 - Подсказка найденной встречи`, `V8 06 - Загрузка и обработка в списке`,
`V8 08 - Дорожки назначения спикеров`, and `design/validation-evidence.md`.
