# Feature Specification: Понятный toggle боковой панели

**Feature Branch**: `codex/161-graf-ux-regressions`

**Created**: 2026-08-18

**Status**: Ready for implementation

**Input**: Регрессия после Feature 159: двойная стрелка не объясняет действие
при наведении, а пользователю трудно понять, что одна кнопка управляет
сворачиванием и разворачиванием боковой панели.

## User Scenarios & Testing

### User Story 1 - Понимать действие toggle (Priority: P1)

Пользователь видит одну кнопку в верхней части боковой панели и по подписи,
иконке и короткому tooltip понимает, что произойдёт при следующем нажатии.

**Why this priority**: Боковая панель используется на каждой защищённой
странице; непонятный control делает основную навигацию случайной.

**Independent Test**: В synthetic browser и embedded shell вывести collapsed и
expanded состояния, навести указатель и перевести фокус на toggle. Проверить
один control, truthful label, visible tooltip, icon state, `aria-expanded` и
последовательные активации мышью/клавиатурой.

**Acceptance Scenarios**:

1. **Given** панель свернута, **When** пользователь наводит указатель или
   переводит фокус на toggle, **Then** рядом с кнопкой появляется подсказка
   «Показать боковую панель», а accessible name и icon описывают то же действие.
2. **Given** панель развернута, **When** пользователь наводит указатель или
   переводит фокус на toggle, **Then** подсказка меняется на «Скрыть боковую
   панель», не закрывает кнопку или навигацию и не зависит только от hover.
3. **Given** пользователь активирует toggle мышью, Enter или Space, **When**
   состояние меняется, **Then** фокус остаётся на том же control, `aria-expanded`
   и подсказка обновляются, а текущий маршрут не меняется.
4. **Given** пользователь активировал раскрытие, **When** он повторно нажимает
   ту же кнопку без перемещения указателя, **Then** панель снова сворачивается,
   а hit target остаётся в верхней части rail.

### Edge Cases

- Tooltip не должен обрезаться краем rail, native/web chrome или узким viewport.
- Tooltip не должен перехватывать pointer events, перекрывать focus ring или
  создавать горизонтальную прокрутку.
- Повторная HTMX/partial initialization не создаёт второй toggle или второй
  обработчик.
- Dark/light theme, keyboard-only и reduced-motion сохраняют тот же смысл.
- Embedded shell использует тот же accessible contract, что и browser shell.

## Clarifications

### Session 2026-08-18

- Критических неоднозначностей не обнаружено: state persistence и responsive
  default state остаются отдельным successor-срезом Feature 165.

## Requirements

### Functional Requirements

- **FR-001**: Каждый full cabinet shell MUST содержать ровно один focusable
  sidebar toggle в стабильной верхней позиции expanded и collapsed states.
- **FR-002**: Toggle MUST иметь `aria-controls`, truthful `aria-expanded`,
  accessible name, matching icon and a visible tooltip for hover и focus.
- **FR-003**: Tooltip MUST сообщать следующее действие простым русским текстом
  и оставаться доступным при keyboard focus, даже если hover недоступен.
- **FR-004**: Toggle MUST работать через pointer, Enter и Space, сохранять
  focus, active route и stable hit target после каждой активации.
- **FR-005**: Tooltip MUST быть визуально читаемым в dark/light themes,
  reduced-motion, narrow viewport и embedded shell без overflow или clipping.
- **FR-006**: Shared JS initialization MUST be idempotent after partial updates
  and MUST NOT add analytics, storage, router or new dependency.
- **FR-007**: Existing navigation, settings, logout, download visibility,
  auth, CSRF, tenant and native recording boundaries MUST NOT change.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic browser/embedded matrix finds exactly one toggle per
  shell and matching label, tooltip, icon and `aria-expanded` in both states.
- **SC-002**: Keyboard and pointer activation pass two consecutive state changes
  with focus remaining on the toggle in 100% of tested cases.
- **SC-003**: Tooltip is visible on both hover and focus in wide and narrow
  renders, without horizontal overflow or focus-ring occlusion.
- **SC-004**: Existing shared-shell and static-asset contracts remain green;
  no route or auth behavior changes are observed.

## Assumptions

- Feature 159 remains the owner of shared shell markup and current rail state
  mechanics; this slice improves the affordance without redesigning navigation.
- Feature 165 owns the default expanded/collapsed decision by viewport.
- A native CSS tooltip affordance plus existing dynamic label is sufficient;
  no onboarding or persistent help system is required.

## Out of Scope

- Responsive default sidebar state and persistence between sessions.
- Profile menu, settings IA, search spacing, download CTA or login copy.
- Native capture controls, macOS permissions, updater and production release.
- Copying Krisp or any proprietary visual/interaction design.

