# Visual Target: Essential Interface Polish

## Source Of Truth

The pre-build visual target is the selected synthetic Stitch screen from project
`8185028688921991455`, screen `e3c3421bd78e4320845d072c6a7193cc`.
It was selected after one base screen, three layout variants, and focused edits
for control reduction, minimum-window behavior, and accessibility semantics.

The Stitch HTML and screenshots are local design evidence outside git. They
contain synthetic meeting names only. The exported HTML is a visual checkpoint,
not production code: feature 104 adapts the target through the existing Jinja,
CSS, JavaScript, SwiftUI, AppKit, and icon surfaces without adding the prototype's
CDN or design-time dependencies.

## Selection Rationale

- The meeting list, not navigation or recording diagnostics, owns the visual
  center.
- Search has one obvious location; filter and sort remain secondary; upload is
  the only persistent content action.
- Rows use alignment and separators instead of card stacking.
- Completed work reads as a result, while progress is reserved for an active
  operation.
- The native rail exposes direct recording and intentional disclosure without
  occupying meeting-list width.
- The composition is original GRAF work. It uses no Krisp copy, assets, icons,
  gradient banner, right-side feature stack, or proprietary interaction.

## Geometry And Responsive Target

| Surface | `1280x760` target | `1040x680` target |
|---|---|---|
| macOS chrome | Standard traffic-light controls and `GRAF` window title | Same; system-owned controls never collapse |
| Server navigation | 168-176 px, compact wordmark, labeled working destinations | Approximately 64 px icon rail with accessible labels/tooltips |
| Meeting workspace | Flexible column with 40 px outer gutter | Flexible column with 24 px outer gutter; no horizontal scroll |
| Toolbar | Search, labeled `Фильтры`, labeled `Сортировка`, `Загрузить` | Flexible search plus icon-only controls retaining exact accessible names |
| Meeting rows | 44-48 px, thin separators, aligned title/duration/status/date | Same columns remain visible; only a long title may truncate |
| Native capture rail | 52 pt, ready indicator, direct Record/Stop, disclosure | 48-52 pt and fully visible; Record/Stop is never clipped |

The default surface contains no plan or trial label, disabled/future
navigation, invite placeholder, duplicate brand footer, empty calendar card,
saved-filter placeholder, permanent bulk toolbar, idle meters, telemetry,
diagnostic disclosure, or report actions.

## State Evidence Matrix

All evidence uses synthetic or redacted content and the same viewport before and
after. `1280x760` and `1040x680` are required for every state where window layout
is relevant.

| State | Owner | Required visible truth / action | Required evidence |
|---|---|---|---|
| Session or sign-in required | Server region | Human sign-in/session message and one recovery action; native capture authority follows existing policy | Screenshot plus accessibility tree |
| Permission required | Native | Affected capability, `Нужно разрешение`, and one settings/recovery action | Screenshot plus accessibility tree |
| Idle / ready | Native + server | `Готово к записи`, direct `Начать запись`, ordinary meeting list | Both target viewports |
| Meeting detected | Native | Human meeting-detected prompt and the existing ask/start choice; no candidate telemetry | Screenshot plus accessibility tree |
| Active recording | Native | Persistent indicator, elapsed truth when available, and one-action `Стоп` | Both target viewports plus action count |
| Paused | Native | `Запись на паузе`, `Продолжить`, and still-visible `Стоп` | Screenshot plus accessibility tree |
| Stopping / finalizing | Native | `Сохраняем запись...`; no premature ready state or duplicate command | Screenshot plus accessibility tree |
| Saved locally | Native | `Сохранено на Mac` and only the applicable recovery/next step | Screenshot plus accessibility tree |
| Upload active | Server list / native custody | `Отправляем` and measured progress only when a real total exists | Row screenshot plus presentation fixture |
| Processing | Server list | `Обрабатывается` and measured progress only while active | Row screenshot plus presentation fixture |
| Ready result | Server list | `Готово` or `Готово с замечаниями`; no terminal `100%` meter | Row screenshot plus presentation fixture |
| Empty list | Server list | Concise guidance that reuses toolbar upload and native recording; no duplicate CTA, app-download/install, calendar, onboarding, or roadmap placeholder in the installed app | Both target viewports |
| Selection | Server list | Selection affordances and delete-only contextual toolbar after intent | Both target viewports plus keyboard focus |
| Search / filter / sort | Server list | Active refinement, current sort, results, and one-action reset | Both target viewports plus keyboard focus |
| Cabinet offline / unavailable | Server region + native | Human retry/sign-in state; native capture controls remain truthful and available per policy | Screenshot plus local-control proof |
| Actionable degraded failure | Relevant owner | Impact, one recovery action, local-custody truth, and contextual support only when eligible | Screenshot plus accessibility tree |

## Accessibility Target

The selected prototype was inspected at `1040x680`. Its ordinary accessibility
tree retains `Поиск встреч`, `Фильтры`, `Сортировка`, `Загрузить запись`,
`Готово к записи`, `Начать запись`, and `Открыть управление записью` after
visible toolbar/sidebar labels collapse, while exposing zero checkbox/delete
nodes before row intent. Hover and keyboard focus on a row reveal the exact
row-specific selection and deletion names; the meeting title remains a separate
`Открыть встречу …` link. The readiness status uses a check symbol plus its exact
name instead of color alone. The result link and contextual row controls retain
at least 32×32 CSS px hit areas, the rail disclosure retains 40×40 CSS px, and
the processing pulse stops under Reduce Motion. Production implementation must
use native semantic controls and match or improve this contract.

## Implementation Boundary

The target specifies hierarchy, density, geometry, state visibility, wording,
and responsive intent. It does not authorize new routes, a new component
framework, persistence changes, a calendar event projection, billing/account
copy, or replacement of native capture authority.
