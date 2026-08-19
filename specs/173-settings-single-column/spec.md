# Feature Specification: Одна колонка настроек без legacy gutter

**Feature Branch**: `codex/173-settings-single-column`

**Created**: 2026-08-19

**Status**: Implemented and validated

**Input**: Настройки уже используют общую левую навигацию кабинета, но скрытая
legacy-навигация продолжает резервировать пустую колонку и смещает содержимое
вправо. Нужно завершить миграцию к одной основной боковой панели.

## User Scenarios & Testing

### User Story 1 - Видеть настройки рядом с единственной навигацией (Priority: P1)

Пользователь открывает любой раздел настроек и видит одну основную левую
навигацию, а заголовок, формы и карточки начинаются в нормальной рабочей области
сразу после неё без пустого места от второго скрытого меню.

**Why this priority**: Пустая колонка визуально выглядит как сломанная
компоновка, уменьшает полезную ширину форм и противоречит выбранной модели одной
основной навигации.

**Independent Test**: Открыть обзор настроек, обычный подраздел, календарь и
billing surface на широком и узком окне; на каждой странице должна быть одна
доступная навигация и ни одной пустой legacy-колонки перед содержимым.

**Acceptance Scenarios**:

1. **Given** пользователь открыл настройки на широком окне, **When** страница
   стабильно загружена, **Then** видна одна основная боковая навигация, а
   содержимое начинается в первой колонке рабочей области без второго gutter.
2. **Given** пользователь переходит между обзором, записью, итогами, календарём,
   аккаунтом и оплатой, **When** меняется активный раздел, **Then** существующие
   маршруты, формы и active state остаются рабочими, а компоновка не возвращает
   скрытую колонку.
3. **Given** окно узкое или sidebar свёрнут, **When** настройки перераскладываются,
   **Then** содержимое не создаёт горизонтальный overflow и не перекрывается с
   navigation, focus ring или native chrome.
4. **Given** страница обновляется полностью или частично, **When** shell повторно
   инициализируется, **Then** в accessibility tree остаётся ровно одна основная
   навигация настроек без скрытого дубля.

### Edge Cases

- Settings overview, обычные server-backed формы, calendar fragment, provider
  link flow и billing pages используют разные content wrappers, но один layout
  contract.
- Режим без outer settings navigation сохраняет существующую standalone
  навигацию; исправление не удаляет поддерживаемый fallback вслепую.
- Длинные заголовки, validation errors и billing banners не должны расширять
  страницу по горизонтали.
- Удаление скрытого дубля не должно менять tab order, accessible names или
  canonical return-to-meetings action внешнего sidebar.

## Requirements

### Functional Requirements

- **FR-001**: Settings mode MUST показывать ровно одну основную навигацию и MUST
  NOT создавать скрытый дубликат внутреннего settings menu.
- **FR-002**: Settings overview, settings forms, calendar и billing content MUST
  занимать первую и единственную колонку рабочей области, когда outer sidebar
  уже владеет навигацией.
- **FR-003**: Между outer sidebar и settings content MUST оставаться только
  существующий стандартный main padding; legacy navigation width и gap MUST NOT
  резервироваться.
- **FR-004**: Существующие settings routes, active states, forms, CSRF/auth/role
  gates, billing actions и native recording handoff MUST остаться без изменения.
- **FR-005**: Поддерживаемая standalone-компоновка без outer settings mode MUST
  сохранить внутреннюю navigation, если такой surface ещё вызывается.
- **FR-006**: Wide, narrow, standalone web и embedded macOS settings surfaces
  MUST сохранять readable content, predictable focus order и отсутствие
  horizontal overflow.
- **FR-007**: Исправление MUST NOT добавлять JavaScript state, localStorage,
  router, breakpoint, dependency или вторую layout abstraction.

## Success Criteria

### Measurable Outcomes

- **SC-001**: В 100% проверенных settings-mode страниц содержимое находится в
  первой grid-column рабочей области, а скрытая legacy navigation отсутствует.
- **SC-002**: На viewport 1280 px исчезает измеренный legacy offset 252 px
  (220 px column + 32 px gap); content начинается после стандартного main
  padding, а не после пустого menu slot.
- **SC-003**: В матрице overview/form/calendar/billing × wide/narrow не возникает
  horizontal overflow, overlap или второго navigation landmark.
- **SC-004**: Все существующие focused settings, shell, auth/CSRF и billing
  contracts проходят без изменения server-side поведения.

## Assumptions

- Feature 159 остаётся владельцем IA: outer cabinet sidebar меняет содержимое
  на settings navigation и предоставляет явное действие «К встречам».
- `settings_mode` является существующим достоверным признаком того, что outer
  sidebar уже владеет settings navigation.
- Визуальные стили карточек, форм, typography и ширина content 780 px не
  редизайнятся; меняется только ошибочно сохранённая двухколоночная оболочка.

## Out of Scope

- Новый дизайн карточек и форм, изменение списка разделов или маршрутов.
- Изменение auth, billing, permissions, capture или desktop navigation logic.
- Новый responsive breakpoint, persistence или SPA/router architecture.
