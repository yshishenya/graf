# Feature Specification: Адаптивное стартовое состояние боковой панели

**Feature Branch**: `codex/161-graf-ux-regressions`

**Created**: 2026-08-18

**Status**: Ready for planning

**Input**: Регрессия из задачи 14: боковая панель при загрузке всегда
свёрнута, хотя в широком окне раньше открывалась автоматически; в узком окне
она должна оставаться свёрнутой.

## User Scenarios & Testing

### User Story 1 - Получать правильное состояние панели при открытии (Priority: P1)

Пользователь открывает GRAF в браузере или embedded macOS shell и сразу видит
боковую панель в состоянии, соответствующем ширине рабочей области: на широком
экране навигация раскрыта, на узком — компактна. Пользователь может изменить
это состояние существующим toggle, не теряя выбор при изменении размера окна в
течение текущего открытия страницы.

**Why this priority**: Боковая панель — основной способ навигации. Неверное
стартовое состояние создаёт ощущение сломанного интерфейса и скрывает подписи
разделов в обычном desktop-сценарии.

**Independent Test**: В synthetic browser и embedded shell инициализировать
один cabinet shell на ширинах 1280, 981, 980, 1121, 1120 и 720 px. Проверить
expanded/collapsed state, действие toggle, `aria-expanded`, отсутствие
горизонтального overflow и сохранение ручного выбора после resize.

**Acceptance Scenarios**:

1. **Given** standalone browser shell шириной 981 px или больше, **When**
   страница инициализируется без заранее заданного состояния, **Then** rail
   раскрыт, видны подписи навигации и toggle сообщает «Скрыть боковую панель».
2. **Given** standalone browser shell шириной 980 px или меньше, **When**
   страница инициализируется без заранее заданного состояния, **Then** rail
   свёрнут до компактной ширины, а toggle сообщает «Показать боковую панель».
3. **Given** embedded shell шириной 1121 px или больше, **When** страница
   инициализируется без заранее заданного состояния, **Then** rail раскрыт;
   при ширине 1120 px или меньше **Then** rail свёрнут до compact rail и
   остаётся доступен через видимый toggle.
4. **Given** пользователь вручную раскрыл или свернул rail, **When** ширина
   окна меняется, **Then** текущее ручное состояние не перезаписывается
   автоматикой до следующей полной инициализации страницы.
5. **Given** shell получил явный класс `is-rail-pinned`, **When** выполняется
   инициализация, **Then** этот явный expanded state имеет приоритет над
   breakpoint default.
6. **Given** пользователь использует клавиатуру, **When** он активирует toggle
   после responsive initialization, **Then** `aria-expanded`, accessible label,
   icon и фактическая ширина rail меняются согласованно, а focus остаётся на
   toggle.

### Edge Cases

- Граничные значения 980/981 px для browser и 1120/1121 px для embedded не
  должны давать промежуточное или неопределённое состояние.
- Embedded shell на ширине 721–1120 px использует compact rail, потому что
  существующий CSS задаёт его как безопасное default-состояние для узкого
  embedded окна; toggle остаётся видимым.
- Partial/HTMX initialization не должна добавлять второй обработчик или
  сбрасывать уже выбранное состояние.
- Поведение не должно добавлять сохранение между сессиями, новый маршрут,
  аналитику или горизонтальную прокрутку.
- Dark/light theme, reduced-motion и keyboard focus сохраняют тот же смысл
  состояния и доступный focus ring.

## Clarifications

### Session 2026-08-18

- Критических неоднозначностей не обнаружено: границы следуют действующим CSS
  breakpoints, а состояние между сессиями остаётся вне scope.

## Requirements

### Functional Requirements

- **FR-001**: Cabinet shell MUST choose its initial rail state from the
  existing responsive breakpoints when no explicit state is present: standalone
  browser expanded at `min-width: 981px`, embedded expanded at
  `min-width: 1121px`.
- **FR-002**: At standalone widths up to 980 px and embedded widths up to 1120
  px, the initial rail state MUST be collapsed and the existing toggle MUST
  remain the available expansion control.
- **FR-003**: An explicit `is-rail-pinned` state MUST take precedence over the
  responsive default during initialization.
- **FR-004**: Responsive initialization MUST run once per shell and MUST NOT
  install a resize listener or overwrite a state changed by the user during the
  current page lifetime.
- **FR-005**: The existing toggle MUST keep its current pointer, keyboard,
  focus, `aria-expanded`, accessible label and icon contract after the default
  state is selected.
- **FR-006**: Browser and embedded shells MUST share the same initialization
  path; the feature MUST NOT add persistence, routing, analytics, dependencies
  or changes to auth, capture, playback and meeting content behavior.

### Key Entities

- **Cabinet shell**: Existing page-level navigation surface with a
  `desktop-embedded` mode marker and one sidebar toggle.
- **Rail state**: Ephemeral `expanded`/`collapsed` presentation state for one
  page lifetime; it is not persisted.
- **Responsive default**: The width-derived initial state used only when the
  shell has no explicit pinned state.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All six boundary widths in the browser/embedded matrix produce
  the expected initial state in 100% of synthetic runs.
- **SC-002**: Wide standalone and embedded renders expose navigation labels on
  first paint/initialization; narrow renders expose a usable compact toggle,
  with no horizontal overflow in 100% of checked states.
- **SC-003**: After two consecutive pointer or keyboard toggles, focus,
  accessible label, `aria-expanded`, icon and rail state remain synchronized in
  100% of tested shells.
- **SC-004**: A manual state survives every tested resize event within the same
  page lifetime, and no new persistence or resize listener is introduced.
- **SC-005**: Existing shared-shell, auth, meeting, playback and embedded
  routing regression contracts remain green.

## Assumptions

- The current CSS breakpoints are the source of truth: 981 px for standalone
  expanded behavior and 1121 px for embedded expanded behavior (the CSS
  compact rule is `max-width: 1120px`).
- The server-rendered shell does not currently encode a user preference; the
  absence of `is-rail-pinned` means that the responsive default may be chosen.
- The existing JS idempotency guard remains the owner of partial-update safety.
- A full production deploy is not part of this isolated slice; the later
  release train owns deployment and release approval.

## Out of Scope

- Persisting sidebar state between page loads or devices.
- Redesigning the sidebar toggle, profile menu, settings IA, download CTA or
  search field.
- Changing meeting content, playback, summary generation, auth, capture,
  permissions, macOS packaging or production deployment.
