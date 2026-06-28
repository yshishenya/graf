# Handoff Spec: Calendar Settings UI

## Overview

The screen lets a user manage read-only calendar integrations for 2brain Rec. It is a working settings screen, not a landing page. The main job is to make calendar access understandable and safe: connect a source, choose calendars, see sync health, control meeting prompts, and disconnect without changing recording behavior.

Primary path: `Настройки -> Интеграции -> Календари`.

Primary surfaces:

- Web cabinet.
- Embedded cabinet inside the macOS app.

## Layout

### Desktop Web Cabinet

- Use the existing cabinet shell: left navigation, main content column, dark work surface.
- Content width follows current cabinet pattern: main content maxes near the existing `980px` cards/lists where possible.
- Header order:
  1. Breadcrumb/location cue: `Настройки / Интеграции / Календари`.
  2. Page title: `Календари`.
  3. Subtitle: `Подключите календарь, выберите нужные календари и настройте подсказки перед встречами.`
- First content block is the read-only boundary.
- Source cards appear before provider catalog when at least one source exists.
- Provider catalog remains visible after source cards so users can add another source.
- Prompt behavior and sync details sit below source/calendar selection, not above connection status.
- Destructive disconnect area is last.

### Embedded macOS Cabinet

- Reuse the same server-rendered content.
- Keep native active-recording indicator and one-action Stop outside the embedded content.
- Embedded width may be tighter; avoid horizontal scrolling and long multi-column rows.
- Provider authorization can leave the embedded view only for provider-controlled auth, then must return to the calendar settings result state.

### Responsive Behavior

| Breakpoint | Behavior |
| --- | --- |
| `>980px` | Sidebar visible; source cards can use two-column internal metadata/action layout. |
| `541-980px` | Sidebar hidden per existing cabinet CSS; stack header actions and source card actions. |
| `<=540px` | Single column; every action is full-width or wraps cleanly; source metadata appears as short stacked rows. |

## Design Tokens Used

Use existing cabinet tokens from `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

| Token | Value | Usage |
| --- | --- | --- |
| `--bg` | `#191a1c` | Page background. |
| `--panel` | `#202224` | Sidebar/shell panels. |
| `--surface` | `#242629` | Cards, banners, source blocks. |
| `--surface-2` | `#26282c` | Inputs/buttons. |
| `--surface-3` | `#2f3237` | Selected/hover states. |
| `--line` | `#30343a` | Borders and dividers. |
| `--line-soft` | `rgba(255,255,255,.07)` | Low-emphasis dividers. |
| `--text` | `#e8eaee` | Primary text. |
| `--muted` | `#a8adb5` | Secondary text and helper copy. |
| `--subtle` | `#7c828b` | Disabled/low-confidence metadata. |
| `--accent` | `#8c73ff` | Selected states, focus-adjacent emphasis. |
| `--blue` | `#2f91ff` | Primary action. |
| `--green` | `#2fc9a6` | Connected/success states. |
| `--amber` | `#f0a742` | Stale/warning states. |
| `--red` | `#ff6b6b` | Error/destructive states. |

Typography:

- Use existing system stack: `-apple-system`, `BlinkMacSystemFont`, `SF Pro Text`, `Segoe UI`, `system-ui`, `ui-sans-serif`, `sans-serif`.
- Body baseline: `13px`, line-height `1.38`, letter spacing `0`.
- Page title follows existing `h1`: `24px`, line-height `1.15`, weight `700`.
- Compact section headings follow existing pattern: `12px`, weight `700`, muted color.

Radii and spacing:

- Cards, dialogs, buttons, inputs: `7-8px` radius.
- Avoid nested cards. Use cards only for source rows/cards, dialogs, and repeated provider/calendar items.
- Use `8px`, `12px`, `14px`, `16px`, `18px`, `22px`, `28px` spacing steps already present in cabinet CSS.

## Components

| Component | Variant | Props / Content | Notes |
| --- | --- | --- | --- |
| Read-only boundary banner | `cabinet-banner` info | title, short body, safe bullet list | First block. No secrets, no provider payloads. |
| Source card | repeated card/row | provider, account label, state, selected count, sync health, actions | Main status object. Must fit long provider/account labels. |
| Provider item | repeated row/button | provider label, method label, availability/admin note | Not a marketing tile grid. Dense settings list. |
| Calendar picker row | checkbox row | calendar name, source, safe visibility state, selected | Label and checkbox share one hit target. |
| Sync status | status label + details | current state, last successful sync, latest attempt category | `role=status` for async updates. |
| Upcoming preview item | compact list row | safe title state, time, source, conflict/duplicate state | Never show private body, attendee dumps, passcodes, full signed links. |
| Prompt setting | checkbox/switch-like binary control | one-minute prompt, at-start prompt, event categories | Use real checkbox or existing binary primitive; label explains effect. |
| Conflict chooser | inline panel or dialog | overlapping events, choose event, continue without context | Appears only during ambiguous interval. |
| Disconnect confirmation | destructive dialog | consequence copy, cancel, disconnect | No immediate destructive action. |

## Content Specs

Required Russian copy principles:

- Plain language, not provider jargon.
- Active voice.
- Error messages include the next action.
- Do not say "calendar is broken"; say what the user can do.
- Do not mention raw scopes, tokens, payloads, passcodes, or private event text.

Suggested core copy:

- Boundary title: `Что делает 2brain Rec с календарем`
- Boundary body: `Мы читаем выбранные будущие события, чтобы показать встречи и подсказать запись. Мы не меняем события, не отправляем письма, не рассылаем саммари и не выдаем доступ участникам.`
- Zero selected: `Источник подключен, но календари не выбраны. Встречи из него не появятся, пока вы не выберете календари.`
- Stale sync: `Данные могут быть устаревшими. Последняя успешная синхронизация: {time}.`
- Latest failed: `Последняя синхронизация не прошла. Можно повторить или переподключить источник.`
- Conflict: `Сейчас пересекаются несколько встреч. Выберите, к какой встрече относится запись, или продолжите без календарного контекста.`
- Disconnect: `Будущая синхронизация остановится. Доступ, которым управляет 2brain Rec, будет удален или отозван. Уже сохраненный контекст встречи живет по правилам хранения записей.`

Character handling:

- Provider name: allow wrapping.
- Account label: truncate middle or end; never show raw tokens.
- Calendar name: one line on desktop with title tooltip; wraps on mobile if needed.
- Error body: max 2 short sentences plus action.
- Status labels: 1-3 words in Russian where possible.

## States And Interactions

| Element | State | Behavior |
| --- | --- | --- |
| Settings nav item | selected | Visible active state; route opens working screen. |
| Provider connect | loading | Button disabled, spinner, status text announced politely. |
| Credential form | error | Inline error near field; focus first invalid field on submit. |
| Source card | connected | Green/normal state, selected count, last sync. |
| Source card | needs action | Amber/error state, reconnect action. |
| Source card | stale | Amber status, last successful sync, manual sync. |
| Source card | disabled | Muted state, no contribution to upcoming preview. |
| Manual sync | running | Do not start duplicate sync; say sync is already running. |
| Calendar selection | unsaved change | Save/cancel controls visible; warn before leaving if needed. |
| Empty source list | empty | Read-only boundary plus provider choices. |
| Preview | stale affected | Show confidence warning near preview. |
| Disconnect | destructive | Confirmation dialog required. |

Motion:

- Keep motion minimal.
- Use existing `opacity`/`transform` patterns only.
- Honor `prefers-reduced-motion`.
- No decorative animation.

## Accessibility Notes

- Keyboard order follows visible order: nav, title/actions, boundary, source cards, provider list, selection, prompt settings, sync details, disconnect.
- Icon-only buttons need `aria-label`.
- Async sync/connect updates use `role=status` or polite live region.
- Provider list and calendar list must be reachable by keyboard.
- Calendar checkboxes must have visible labels and one hit target.
- Conflict chooser needs heading, focus management, Escape/cancel, and explicit "continue without context".
- Destructive confirmation must trap focus while open and return focus to the triggering disconnect button.
- Do not rely on color alone: all success/warning/error states need text labels.
- Dates/times should be locale-aware; avoid hardcoded English date formats.

## Edge Cases

- No connected sources.
- Source connected with zero selected calendars.
- Source has no readable calendars.
- Provider requires admin action.
- Provider auth cancelled or denied.
- Credentials expired/revoked.
- Sync running, stale, failed, partially successful, disabled.
- Multiple sources with the same account label.
- Duplicate calendar names inside one source.
- Duplicate event by stable provider event ID or same meeting link.
- Partial overlap, such as 12:00-13:00 and 12:30-13:30.
- Private/free-busy event.
- Long Russian provider/calendar names.
- Embedded cabinet offline/auth unavailable while native recording remains active.

## Design QA Gate

Before implementation handoff is considered visually ready, capture:

- Source visual target: Figma frame, screenshot, or approved prototype.
- Rendered implementation: web cabinet and embedded macOS screenshot at matching state.
- Viewports: desktop `>980px`, tablet `541-980px`, mobile `<=540px`, and embedded macOS.
- States: empty, connected zero calendars, selection open, stale sync, error, overlap conflict, disconnect confirmation.

Current QA status: blocked until a source visual target and rendered implementation exist.
