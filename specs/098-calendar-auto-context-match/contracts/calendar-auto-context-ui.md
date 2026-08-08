# Calendar Auto Context UI Contract

**Feature**: `098-calendar-auto-context-match`

## Purpose

Define one server-owned calendar-context presentation for browser and embedded macOS meeting surfaces. Native macOS remains responsible for capture truth, visible Record/Stop and existing calendar prompts; it does not implement a second meeting-review UI.

## Shared State Language

| Product state | Recording list | Owner review | Owner action |
|---|---|---|---|
| Automatic match | `Из календаря` | `Подобрано автоматически` | `Изменить`, `Убрать контекст` |
| User-selected match | `Выбрано вами` | `Выбрано вами` | `Изменить`, `Убрать контекст` |
| Ambiguous | `Нужно выбрать встречу` | `Несколько встреч подходят по времени. GRAF ничего не выбрал.` | choose one or continue without context |
| No match/calendar | `Без календарного контекста` | normal non-error fallback | choose only when safe candidates exist |
| Private/free-busy skipped | same generic no-context list state | owner only: `Приватное событие пропущено` | no private candidate details |
| Calendar unavailable/stale | same generic no-context list state | owner only: safe availability reason | open Calendar settings, no blocking retry |
| Declined at recording start | same generic no-context list state | `Вы начали запись без календарного контекста` | explicit selection may add context later |
| Cleared by user | same generic no-context list state | `Контекст убран вами` | explicit selection may add context again |

Rules:

- Internal enum/reason names never appear as product copy.
- Private skip reason never appears in recording-list text, JSON accessible label or non-owner review.
- Status uses text plus icon/shape; color alone is insufficient.
- No-context is a normal outcome, not an error banner.

## Recording List Contract

- Add calendar state to the existing row metadata; do not add a new table column or large card.
- Preserve title, recording-time, duration, status and primary action hierarchy.
- Owner ambiguous state uses the existing meeting-title link as the compact
  `Выбрать` action and points it to the meeting-detail context anchor; nested
  anchors are invalid and must not be rendered.
- Non-owner viewers see generic no-context for ambiguous/private/declined/cleared states and receive no action link.
- Row height must support the additional metadata without clipping; use existing design-system spacing and the 64–80 px row target rather than the legacy 46 px override.
- Title source and context state are separate: clearing context can leave a stable calendar-derived title while the context label becomes no-context.

## Meeting Review Contract

### Matched State

Add a compact `Контекст встречи` block in the existing right-side detail panel before access/speaker sections.

Contents:

- provenance: `Подобрано автоматически` or `Выбрано вами`;
- safe match-time event title source when applicable;
- localized event time;
- roster state;
- `Изменить` and `Убрать контекст` for owner only;
- optional recurring previous-meeting pointer.

### Roster

Render roster separately from transcript speakers:

- heading: `Участники из календаря · N`;
- helper copy: `Приглашённые участники, не подтверждённые спикеры`;
- safe display name, participant role and RSVP state;
- no raw email value, meeting access, recipient or speaker implication.

The transcript continues to use `SPEAKER_00`, `SPEAKER_01`, and so on.

### Ambiguous State

- Place the chooser in an attention panel in the main column above transcript/review content; do not squeeze multiple choices into the narrow inspector.
- Copy: `Несколько встреч подходят по времени. GRAF ничего не выбрал.`
- Show a `<fieldset>` with safe radio choices.
- Each choice contains only safe title/generic label, localized start/end time and safe calendar/source label.
- Roster, description, meeting link, passcode and private details are hidden before selection.
- Actions:
  - `Сохранить выбор`;
  - `Продолжить без календаря`.
- After save, collapse to the standard matched detail block.

### No-Context And Skip States

- Generic no-context requires no action when no safe candidates exist.
- Owner-only details may explain `Календарь недоступен`, `Данные календаря устарели`, `Приватное событие пропущено`, `Ручная загрузка не сопоставляется` or `Офлайн-запись не сопоставляется`.
- Safe reason copy never includes a provider error, account identifier, event title or hidden event count.
- Calendar settings link is allowed for connection/stale states but is not required to complete recording review.

## Correction And Clear Contract

### Change Context

- Reuse the ambiguous chooser component and candidate safety rules.
- An explicit new choice becomes `Выбрано вами`.
- If the current title source is calendar, the selected event's safe title may replace it.
- User-confirmed, upload-provided, filename-derived and legacy titles remain unchanged.

### Clear Context

- Start-time `Продолжить без календаря` persists `declined_by_user`; it is not labeled as a later clear.
- Inline confirmation copy: `Контекст и список приглашённых исчезнут. Название записи останется прежним.`
- On confirmation, roster, event relationship, candidate choices and recurring pointer disappear.
- State becomes `Контекст убран вами` in owner detail and generic no-context in list.
- Automatic matching must not reattach context after clear.
- A later explicit owner selection can add context again.

## Recurring Context Contract

Minimum privacy-safe surface:

- Review block label: `В серии`.
- Link: `Предыдущая встреча · {локальная дата}`.
- Readiness text: `Итоги готовы`, `Транскрипт готов`, `Обрабатывается` or omitted.
- Accessible label names the previous meeting, date and readiness.

Rules:

- Show only when the previous recording is matched to the same series, in the same workspace and independently authorized for the viewer.
- Deleted, inaccessible or cross-space previous meetings produce no block and no disabled placeholder.
- Do not show summary/transcript excerpts in the calendar block.
- The existing server-owned `Ближайшие` list section may reuse the same pointer for pre-meeting continuity when a current authorized upcoming occurrence exists.
- Native macOS prompts do not show roster or previous-meeting content.

## macOS Prompt Semantics

- Ordinary manual Record uses `automatic` resolve intent.
- A single-event record prompt also uses `automatic`; it must not pass the event as `manual_selection`.
- An overlap choice uses `user_selected` and the selected event ID.
- `Начать запись без календаря` uses explicit `user_declined`.
- Resolve starts only after local capture starts and never delays visible capture state.
- If resolve fails, capture continues and the queue contains no attempt ID, so later upload is safely treated as offline/unknown.
- Recovered/scanned queue items never fabricate an attempt ID.
- Native Record/Stop, active recording indicator and one-action Stop remain unchanged.

## Settings Boundary

Feature 063 may let users opt private/free-busy or all-day events into preview/prompts. Calendar settings must explain:

`Эти фильтры управляют подсказками и списком ближайших встреч. Приватные события и события на весь день не используются для автоматического контекста записи.`

Changing prompt categories never weakens 098 auto-match eligibility.

## Accessibility Contract

- Chooser uses `<fieldset>` and `<legend>Выберите встречу</legend>` with native radio controls.
- Candidate label includes localized time and source; helper copy is connected through `aria-describedby`.
- Opening the chooser moves focus to its heading.
- Saving/clearing returns focus to the `Контекст встречи` heading.
- Async result copy uses `aria-live="polite"` without repeating sensitive detail.
- Keyboard users can open, choose, save, decline, change and clear without pointer input.
- Focus indicators use existing cabinet tokens and remain visible in high-contrast mode.
- Private reason is excluded from list accessible labels.
- Status is never color-only.
- Controls use minimum existing target sizes and do not put long Russian explanations inside buttons.

## Localization Contract

Required Russian/English message pairs:

| Russian | English |
|---|---|
| Из календаря | From calendar |
| Выбрано вами | Selected by you |
| Нужно выбрать встречу | Choose a meeting |
| Без календарного контекста | No calendar context |
| Приватное событие пропущено | Private event skipped |
| Вы начали запись без календарного контекста | You started recording without calendar context |
| Контекст убран вами | Context removed by you |
| Предыдущая встреча | Previous meeting |
| Участники из календаря | Calendar invitees |

- Times use the recording/user display timezone and locale-aware formatter.
- Do not hardcode UTC in the new surface.
- Provider, matcher and reason-code identifiers are not user-facing copy.

## Visual Reuse Contract

Reuse existing GRAF primitives and calendar patterns:

- meeting row metadata and status chip;
- `.panel`, `.state-row`, `.chip`;
- calendar preview rows and conflict actions;
- existing cabinet focus, spacing, radius, border and typography tokens;
- current meeting detail main/inspector layout.

Do not add a new design system, copied reference-product layout, handcrafted icon set, native duplicate review or new frontend framework.

## Embedded macOS Parity

- Browser and embedded macOS load the same server meeting list/detail context model.
- New actions remain on allowed meeting-detail/HTMX routes or update the native route policy explicitly.
- The same meeting cannot show matched in browser and unmatched in embedded review after refresh.
- Native pre-upload/local custody state may show `Проверяем календарь` only while an attempt is unresolved; it must not claim a match before server truth exists.

## Forbidden UI Side Effects

The calendar-context UI must not:

- start hidden or automatic capture;
- hide or disable manual Stop;
- grant attendee access or create share controls;
- create recipients or delivery controls;
- label invitees as speakers;
- expose private titles, attendee emails, descriptions, links or passcodes;
- present provider downtime as a recording failure;
- copy UI, copy, assets or proprietary flows from reference products.
