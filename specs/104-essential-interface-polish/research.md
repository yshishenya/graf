# Research: Essential Interface Polish

## Evidence Boundary

The audit compared the current installed GRAF main window with the supplied Krisp reference in these states: ordinary meeting list, selected rows, search, filter, sort, compact native rail, and expanded native controls. Current GRAF runtime screenshots were inspected together with the server templates/CSS/JavaScript and SwiftUI/AppKit shell. Screenshots remain outside the repository because they contain private meeting metadata; this artifact records only generalized findings and synthetic wording.

The reference is used as clean-room evidence for hierarchy and progressive disclosure, not as a visual source to copy. Current official guidance was checked against Apple’s 2026 [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars), [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars), [Search fields](https://developer.apple.com/design/human-interface-guidelines/search-fields), [Designing for macOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos/), and [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility/) guidance, plus W3C [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum), and the [menu-button pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/).

## Decision 1: Content-first, original GRAF shell

**Decision**: Keep a three-zone shell: a restrained server-owned navigation sidebar, flexible meeting content, and a compact native capture rail. Use the current GRAF dark tokens and system typography; reduce competing cards, borders, and persistent tool clusters. The main screen’s hierarchy is `Мои встречи` → search/context controls → meeting list, with local recording always visually separate. Remove the unconditional empty calendar region because the current route has no authoritative upcoming-event projection.

**Rationale**: The current screen spends too much width and attention on a large wordmark, disabled navigation, duplicated controls, and idle diagnostics. The reference demonstrates the general value of a flat navigation hierarchy and calm content density, while Apple recommends deliberate toolbar contents and comfortable density on resizable Mac windows.

**Alternatives considered**:

- Copy the reference’s gradient banner, right-side product controls, and list composition — rejected by the GRAF clean-room/brand-distance gate.
- Replace the server cabinet with a full native meeting list — rejected because it breaks the established server/native ownership boundary and expands scope.
- Keep every current element and only change colors — rejected because the central usability problem is information architecture, not decoration.

## Decision 2: Only working navigation and one search surface

**Decision**: The sidebar shows the compact GRAF wordmark, `Мои встречи`, `Настройки`, and `Выйти`. Remove disabled `Поиск`, `Общие`, `Действия`, `Активность`, disabled `Пригласить`, the hard-coded trial/plan label, and the duplicate footer `GRAF`. Search remains in the content toolbar as the single searchable location.

**Rationale**: Disabled future destinations advertise capability that does not exist and increase scan cost. Apple recommends a single clearly identified search location and using sidebars for actual peer destinations. The current main-window navigation model has no authoritative billing/plan projection, so presenting `Пробный период 7 дней` would be false account context rather than useful status.

**Alternatives considered**:

- Keep disabled items to preview the roadmap — rejected because roadmap communication is not a user task.
- Implement the missing destinations — rejected as new product functionality outside feature 104.
- Add a Krisp-like command palette — rejected because one responsive search field already exists and a second search model would duplicate it.

## Decision 3: Progressive disclosure for list tools

**Decision**: Keep a single search field visible. Put status/access filters in one semantic disclosure and sorting in a separate semantic disclosure; show active-filter state/count and a clear reset. Preserve automatic HTMX refresh on input/change. Remove the redundant submit icon and disabled saved-filter button. Keep `Загрузить` as the only visible secondary content action.

**Rationale**: The current eight-column control bar is denser than the content it controls. Filtering and sorting are important but intermittent. Native/semantic disclosure preserves keyboard and assistive-technology behavior without a component dependency.

**Alternatives considered**:

- Keep three visible selects — rejected for routine visual noise and poor fit in the minimum window.
- Hide all controls behind one unlabeled icon — rejected because filter and sort have different mental models and active state would be unclear.
- Add saved filters — rejected because the visible action is currently disabled and no saved-filter contract exists.

## Decision 4: Contextual selection and destruction

**Decision**: Row selection remains available on hover and keyboard focus; after the first selection, all selection affordances and the bulk toolbar become visible. The toolbar contains count, select-all/clear semantics, and delete only. The unavailable bulk download placeholder is removed. Per-row delete remains hover/focus contextual and keeps bounded confirmation.

**Rationale**: Always-visible checkboxes make reading feel like administration. Selection is a mode, so its controls should appear with intent. Destructive operations retain the product’s deletion-truth boundary.

**Alternatives considered**:

- Remove multi-selection entirely — rejected because validated bulk deletion is useful.
- Always show all destructive actions — rejected because it overemphasizes a rare and risky task.
- Add an overflow menu to every row — rejected because the only current row action is delete and the existing hover/focus action is simpler.

## Decision 5: Human meeting titles, durations, and states

**Decision**: Presentation rules convert known capture-generated titles into `Запись <date/time>` only when a trustworthy local date/time exists. Generated upload IDs become `Загруженная запись`; empty/unsafe titles become `Запись без названия`; without trustworthy time, the separate date remains `Без даты`. File-like titles lose only the final media extension and repeated separator noise. Persisted titles remain unchanged. Durations use Russian units. Completed rows show a result (`Готово` or `Готово с замечаниями`) without a 100% meter; active upload/processing alone shows progress. Recoverable failure uses `Нужна помощь`; local-only custody uses `Сохранено на Mac`.

**Rationale**: Raw capture labels, identifiers, English duration abbreviations, and `100%` after completion expose implementation rather than meaning. The list should answer “what is this?” and “is it ready?” without making the user interpret the pipeline.

**Alternatives considered**:

- Rewrite stored database titles — rejected because this feature is presentation-only and must not mutate user data.
- Show all backend states verbatim for transparency — rejected because raw state is not useful transparency; detail/support paths retain accurate underlying truth.
- Collapse every non-ready result into `Готово` — rejected because partial/degraded truth remains important.

## Decision 6: Compact action-first native capture surface

**Decision**: The compact rail owns the direct capture action: `Начать запись` when idle and `Стоп` while capture is active, with accessible labels/tooltips. The titlebar recording HUD remains the persistent active indicator and one-action Stop. Expanding the inspector is manual or triggered only by an actionable problem; recording start itself never shifts the meeting workspace. Expanded content is headed `Запись` and shows status/action, permission or recovery blocker, concise auto-detection mode, exceptional local-custody action, and meters only during active recording. Microphone choice moves behind a secondary `Параметры записи` disclosure or existing settings path.

**Rationale**: The current rail communicates state but requires expansion before idle start, while the expanded inspector repeats headings and exposes secondary/detail information. A direct rail action makes the important task available without making a 336-point panel permanent. Keeping the titlebar HUD prevents server content or window layout from hiding Stop.

**Alternatives considered**:

- Keep the expanded panel open by default — rejected because it permanently removes meeting-list width and recreates the current density problem.
- Auto-expand whenever recording starts — rejected because it causes a surprising layout shift during a time-sensitive action.
- Move capture into the WebView — rejected by the native-authority constitution gate.

## Decision 7: Diagnostics remain, debug presentation goes

**Decision**: Remove ordinary rendering of telemetry counters, registry versions/sources, Apple/WebRTC processing internals, local paths, generic report/copy-report actions, idle meters, the unconditional trust card, and the diagnostics disclosure. Keep metadata collection, redaction, diagnostic bundle logic, and support submission services. Show `Связаться с поддержкой` only from a real actionable failure, after the user understands impact and recovery.

**Rationale**: “No debug information” is a presentation requirement, not authorization to weaken observability. Normal UI needs outcome and next action; support metadata belongs behind an intentional failure path.

**Alternatives considered**:

- Delete diagnostic services — rejected because it would weaken product and privacy gates.
- Keep diagnostics collapsed — rejected because even a collapsed engineering concept is noise in the main user workspace.
- Send reports automatically — rejected because support contact is an explicit user action and must remain metadata-safe.

## Decision 8: Density, sizing, responsiveness, and accessibility

**Decision**:

- Keep the native capture rail at 52 pt; reduce the expanded inspector from 336 to about 304–312 pt.
- Reduce the server sidebar from 184 to about 168–176 CSS px and the oversized wordmark card to a compact unbordered header.
- Use 32–36 px controls, 44–48 px meeting rows, an 8/12/16/24 spacing rhythm, 8 px component radii, and a 2 px visible focus ring.
- Use a restrained selected-row tint derived from the existing `#8c73ff` accent instead of the saturated purple block.
- Keep primary text at or above 13–14 px and supporting text at or above 12 px on this dense desktop surface; never encode state by color alone.
- At the supported `1040×680` minimum, keep the content usable without horizontal scrolling. Collapse server navigation to an approximately 64 px rail and toolbar labels to accessible icon controls when needed; title, duration, status, date, upload, and the 48–52 pt native capture rail remain visible.

**Rationale**: Apple’s current macOS accessibility guidance gives 28×28 pt as the default control size and 20×20 pt as the minimum; WCAG 2.2 requires at least 24×24 CSS px or sufficient spacing for pointer targets. WCAG text contrast remains at least 4.5:1 for normal text, and visible keyboard focus must not be obscured. The proposed sizes exceed the minimum while preserving desktop density.

**Alternatives considered**:

- Increase all controls to mobile-sized 44 px — rejected because it wastes Mac screen space and reduces information utility.
- Preserve the current 720 px rail breakpoint unchanged — rejected because native inspector width changes can push the embedded viewport across it and create an inconsistent shell.
- Add a complete light theme — rejected as a separate product-wide theme project; feature 104 validates the supported dark theme and increased-contrast behavior.

## Decision 9: Minimal implementation form

**Decision**: Change existing templates, CSS, JavaScript state classes, SwiftUI views, and presentation helpers in place. Add no UI framework, icon package, new API, persistence model, or command-palette subsystem. Remove code only when its sole purpose is a removed visible element; preserve shared support/diagnostic internals.

**Rationale**: The existing stack already supports the desired behavior. A small evidence-driven diff is easier to validate across capture, accessibility, and server/native boundaries.

**Alternatives considered**:

- Rewrite the cabinet in React — rejected as unnecessary architecture and dependency expansion.
- Introduce a cross-platform design-system package — rejected because there are only two existing owners and no shared runtime rendering layer.
- Broadly delete every now-hidden status field — rejected because some feed diagnostics, tests, or recovery outside the main screen.

## Decision 10: Pre-build visual target

**Decision**: Use Stitch project `8185028688921991455`, selected screen
`e3c3421bd78e4320845d072c6a7193cc`, as the visual source of truth recorded in
[visual-target.md](./visual-target.md). The target was chosen after one base
screen, three layout variants, and focused edits that removed rail noise, fixed
minimum-window clipping, and restored exact accessible names after responsive
label collapse.

**Rationale**: A high-risk pixel-polish slice needs a concrete hierarchy and
responsive geometry before product code changes. The selected target was
rendered at `1280×760` and `1040×680`; the first minimum-width attempt exposed
off-screen date/upload/capture controls and was rejected before implementation.

**Boundary**: Stitch HTML uses design-time tooling and is not production code.
Implementation reuses current GRAF assets, icon macros, CSS, Jinja, JavaScript,
SwiftUI, and AppKit without importing CDN/runtime dependencies from the mock.

## Element-by-element Inventory

| Surface | Current element | Decision | Target state and reason |
|---|---|---|---|
| macOS chrome | Standard traffic-light controls | Keep | System-owned window controls remain untouched and visible. |
| macOS chrome | Window title `GRAF` | Keep | Stable product/window orientation without duplicate in-content labeling. |
| Sidebar | Large bordered GRAF wordmark card | Simplify | Compact unbordered wordmark; brand is orientation, not the primary task. |
| Sidebar | Disabled `Пригласить` | Remove | No result exists; a disabled roadmap control is not useful. |
| Sidebar | Disabled `Поиск` | Remove | Search has one primary location in the content toolbar. |
| Sidebar | `Мои встречи` | Keep | Main working destination. |
| Sidebar | Disabled `Общие` | Remove | Future destination with no supported path. |
| Sidebar | Disabled `Действия` and count | Remove | Count suggests actionable content that cannot be opened. |
| Sidebar | Disabled `Активность` | Remove | Future destination with no supported path. |
| Sidebar | `Настройки` | Keep | Real route for calendar/capture configuration. |
| Sidebar footer | `Выйти` | Keep | Required session action; keep low emphasis. |
| Sidebar footer | Purple trial card | Remove | Hard-coded account state has no authoritative plan source in the current projection. |
| Sidebar footer | Duplicate `GRAF` text | Remove | Brand already appears in the header/window. |
| Main header | `Мои встречи` | Keep and strengthen | Single page heading. |
| Main header | Persistent sort label beside title | Remove | Selected sort belongs to its control, not the heading. |
| Main toolbar | Search field | Keep and clarify | Single responsive search, descriptive placeholder, immediate results. |
| Main toolbar | Status select | Move | Inside labeled filter disclosure with active state. |
| Main toolbar | Access select | Move | Inside labeled filter disclosure with active state. |
| Main toolbar | Sort icon plus select | Simplify | One labeled sort disclosure showing current choice. |
| Main toolbar | Submit/filter icon | Remove | HTMX already applies changes; a second apply action is redundant. |
| Main toolbar | Disabled saved/bookmark | Remove | No saved-filter behavior exists. |
| Main toolbar | `Загрузить` | Keep | Useful secondary meeting-ingest action. |
| Empty list | `Установите GRAF` / app-download step inside the installed app | Remove | The user is already in the macOS app; reuse the persistent upload and native recording actions instead of asking for installation again. |
| Empty list | Duplicate upload, calendar connection, and multi-step onboarding actions | Remove | They compete with existing controls and invent an unrelated path; keep one concise first-value explanation. |
| Calendar | Large always-present empty card | Remove | The current meeting-list route has no authoritative upcoming-event projection; calendar settings remain reachable through `Настройки`. |
| List header | `Записи встреч` | Simplify | Use `Встречи` or omit when the page heading and list relationship are obvious. |
| List header | Decorative filter/sort icons | Remove | Duplicate toolbar controls and are not interactive. |
| Selection | Always-visible row checkboxes | Move/contextualize | Reveal on hover/focus or active selection; remain keyboard accessible. |
| Selection | Select-all and count | Keep contextually | Show only after selection intent. |
| Selection | Disabled bulk download | Remove | No working result; upload/download scope is unchanged. |
| Selection | Bulk delete | Keep contextually | Valid owner task with confirmation. |
| Meeting row | Media/source icon | Keep, de-emphasize | Helps distinguish recording/upload without dominating title. |
| Meeting row | Raw capture/generated title | Simplify | Human fallback title; persisted data unchanged. |
| Meeting row | Duration in English abbreviations | Simplify | Russian compact units. |
| Meeting row | Completed `100%` label and meter | Remove | Completion is a result, not active progress. |
| Meeting row | Degraded upload wording | Simplify | `Готово с замечаниями`; detailed truth remains in meeting/recovery view. |
| Meeting row | Date | Keep | Primary scan metadata. |
| Meeting row | Hover/focus delete | Keep | Contextual, discoverable, and confirmed. |
| Native rail | Inspector chevron | Keep and clarify | Accessible expand/collapse label and stable hit target. |
| Native rail | Passive capture-status icon | Merge with action | Direct Start/Stop control plus status label/help. |
| Native rail | Custody icon/count | Keep only when useful | Show count only for action-required local items; otherwise no badge. |
| Native rail | Settings icon | Move | Recording parameters remain behind intentional inspector/settings disclosure; the ordinary rail keeps only capture truth/action and disclosure. |
| Native panel | `Управление` + `Локальное управление` | Merge | One heading: `Запись`. Ownership is communicated by the native rail, not repeated copy. |
| Native panel | Idle `Запись не идет` | Rewrite | `Готово к записи`; positive readiness plus `Начать запись`. |
| Native panel | Meeting detection plus telemetry counter | Simplify | `Автоопределение: спрашивать/выключено`; telemetry stays internal. |
| Native panel | Microphone selector always visible | Move | Secondary recording parameters/settings; surface only recovery when invalid. |
| Native panel | Generic upload/custody error card | Contextualize | Show only an affected local item or owner action with clear recovery. |
| Native panel | `Отправить отчет` / `Скопировать отчет` | Remove from ordinary UI | Support action appears only after a real failure; no raw report exposure. |
| Native panel | Idle recording meters | Remove from idle | Meters answer a question only while recording. |
| Native panel | Permanent `Доверие записи` card | Merge/contextualize | During capture, concise truth accompanies the recording state; idle does not need a card. |
| Native panel | `Локальная сохранность` disclosure | Contextualize | Show `Сохранено на Mac` only when a local item requires awareness/action. |
| Native panel | `Диагностика` disclosure | Remove from ordinary UI | Diagnostics remain metadata-only internal/support infrastructure. |
| Titlebar HUD | Active indicator, elapsed time, Pause/Resume/Stop | Keep | Persistent native recording truth and one-action Stop across every WebView state. |

## Research Result

All technical and product unknowns required for planning are resolved. No unresolved question remains. The chosen and responsive-tested visual target is an original GRAF composition that borrows only general progressive-disclosure and hierarchy lessons from the supplied reference.

## Implementation Deletion And Boundary Proof — 2026-07-13

The implemented diff removed only presentation clusters whose behavior was
either unavailable, duplicated, or engineering-facing:

- server sidebar placeholders, invite/trial/plan presentation, duplicate
  footer branding, unconditional calendar space, saved/download placeholders,
  redundant submit/decorative controls, and always-visible selection chrome;
- native duplicate headings, auto-expanding recording inspector, permanent
  trust/diagnostics cards, idle meters, raw telemetry/registry/Apple/WebRTC
  presentation, local paths, generic report/copy-report actions, and an unused
  location accessibility helper;
- CSS/DOM/state branches serving the removed elements, including permanently
  reserved selection columns and inactive toolbar layouts.

The preserved alternatives and safety boundaries are explicit:

- real `Мои встречи`, `Настройки`, logout, search, filter, sort, upload,
  meeting links, contextual selection/delete, and bounded confirmation remain;
- native capture authority, permission recovery, direct Start/Stop, titlebar
  Pause/Resume/Stop, local custody truth, and support-eligible recovery remain;
- diagnostic models, redaction, audit/evidence collection, and metadata-only
  support submission remain internal and are not exposed as a normal user
  surface;
- stored meeting titles and backend states are not rewritten; human wording is
  presentation-only.

No package, schema, API route, storage entity, background service, capture-thread
work, or periodic task was added. Search retains the existing `150ms` HTMX
debounce and existing list replacement. The deletion request uses the existing
endpoint and user action, now checks HTTP failure and retries only failed rows;
it does not add a background request. Existing upload polling is paused while a
list interaction or modal is active, rather than duplicated or accelerated.
