# Feature Specification: Боковая навигация настроек

**Feature Branch**: `codex/135-settings-sidebar`

**Created**: 2026-07-27

**Status**: Implemented locally; PR and production rollout pending

**Input**: User description: "Показывать разделы настроек в боковом меню, как в референсе Krisp"

## User Scenarios & Testing

### User Story 1 - Сразу видеть все разделы настроек (Priority: P1)

Пользователь открывает настройки и видит постоянное боковое меню со всеми
доступными разделами, сгруппированными по смыслу. Он понимает, где находится,
и может перейти в нужный раздел без поиска по карточкам или горизонтальной
прокрутки. Страница `/settings` остаётся короткой точкой входа, а не вторым
списком навигации.

**Why this priority**: Видимость структуры — основной пользовательский запрос и
самый короткий путь к исправлению текущего неудобства.

**Independent Test**: Открыть обзор и каждую существующую страницу настроек в
browser и embedded desktop режимах; все разделы должны быть видны в боковом
меню, а текущий раздел — однозначно выделен.

**Acceptance Scenarios**:

1. **Given** пользователь открыл `/settings`, **When** страница загрузилась,
   **Then** боковое меню показывает «Запись», «Итоги», «Календари»,
   «Пространство» и «Аккаунт и безопасность» ровно по одному разу, а
   «Настройки» остаётся заголовком текущей landing-страницы.
2. **Given** пользователь находится в категории, **When** он смотрит на меню,
   **Then** текущая категория имеет selected-состояние и `aria-current`, а
   остальные пункты остаются доступными ссылками.
3. **Given** пользователь выбирает пункт меню, **When** открывается категория,
   **Then** URL, заголовок страницы и selected-состояние меню соответствуют
   одной и той же категории.

### User Story 2 - Понимать границы и сохранять существующее поведение (Priority: P1)

Пользователь видит знакомые scope-обозначения в содержимом категории и может
продолжать пользоваться существующими настройками, не меняя их смысл,
permissions, CSRF-защиту и обработку ошибок.

**Why this priority**: Перестройка IA не должна скрыть область действия
настройки или сломать уже работающие mutation-флоу.

**Independent Test**: Открыть категории «Итоги», «Календари», «Пространство» и
«Аккаунт и безопасность», выполнить существующие focused contract tests и
проверить, что ссылки возврата и состояния ошибок остаются на корректной
категории.

**Acceptance Scenarios**:

1. **Given** категория имеет scope («На этом Mac», «В этом пространстве» или
   «Личная настройка»), **When** пользователь открывает страницу,
   **Then** scope остаётся виден в основном содержимом до изменения настройки.
2. **Given** форма категории вернула success/error/conflict состояние,
   **When** страница отображается снова, **Then** боковое меню сохраняет
   выбранную категорию, а введённые значения и безопасная copy остаются
   доступными по существующим контрактам.
3. **Given** пользователь открывает recording category, **When** он читает
   страницу, **Then** веб остаётся честным handoff к native macOS capture settings
   и не получает новый глобальный переключатель записи.

### User Story 3 - Пользоваться меню с клавиатуры и на узком экране (Priority: P2)

Пользователь может пройти все пункты меню клавиатурой, увидеть focus-state и
достичь каждого раздела на узком viewport без обрезанного или скрытого пункта.

**Why this priority**: Боковой rail ценен только если он остаётся рабочим в
embedded webview, небольшом окне и при keyboard navigation.

**Independent Test**: Проверить страницу при desktop viewport и на ширине
около 320px, затем пройти navigation links клавиатурой и проверить focus,
selected state и отсутствие горизонтального клиппинга.

**Acceptance Scenarios**:

1. **Given** desktop viewport достаточной ширины, **When** пользователь открывает
   settings page, **Then** rail находится слева, content — справа, а меню не
   вытесняет основной контент за пределы окна.
2. **Given** узкий viewport, **When** пользователь открывает settings page,
   **Then** пункты остаются доступными в компактном вертикальном меню перед
   содержимым и не требуют скрытой горизонтальной прокрутки.
3. **Given** пользователь использует клавиатуру, **When** фокус переходит по
   пунктам меню, **Then** focus indicator виден, порядок соответствует меню, а
   Enter открывает выбранную ссылку.

## Edge Cases

- Категория отсутствует в текущем route map или не разрешена в embedded режиме:
  меню не должно показывать битую ссылку; существующая безопасная fallback
  логика сохраняется.
- Очень длинный заголовок или scope-label не должен расширять rail и ломать
  основной контент; текст переносится или обрезается предсказуемо с доступным
  полным названием.
- Страница возвращается после mutation с query-string результатом: selected
  category определяется из canonical route, а не сбрасывается в «Обзор».
- Пользователь без нужной роли не должен получить новый пункт или действие,
  которого нет в существующем permissions-контракте.

## Requirements

### Functional Requirements

- **FR-001**: System MUST render a semantic settings side navigation for the
  browser and embedded desktop settings surfaces.
- **FR-002**: The side navigation MUST expose each actionable category from
  the existing canonical settings route map exactly once: recording, summaries,
  calendar, workspace and account. The overview route remains available as the
  direct `/settings` entry point but is not repeated as a navigation item.
- **FR-003**: The side navigation MUST group categories with concise visible
  group labels («Встречи», «Рабочее пространство», «Аккаунт») while keeping the
  existing Russian category names and routes.
- **FR-004**: The active category MUST be derived from the canonical route and
  represented by both a visible selected state and `aria-current="page"`; the
  overview landing page has no selected category.
- **FR-005**: Existing category scope labels, mutation forms, CSRF protection,
  authorization checks, result states and safe account presentation MUST remain
  unchanged in meaning and reachable from the side navigation.
- **FR-006**: The side navigation MUST preserve browser/embedded route parity
  and MUST NOT add arbitrary redirects, new settings persistence or new backend
  contracts.
- **FR-007**: The layout MUST provide a visible keyboard focus state and a
  minimum 44px interactive target for every navigation link.
- **FR-008**: At a viewport width of 640px or less, all settings categories MUST
  remain reachable without horizontal-only navigation or clipped labels.
- **FR-009**: The recording category MUST continue to describe native macOS
  capture settings as a handoff and MUST NOT move capture policy into web.
- **FR-010**: The UI MUST NOT expose provider subjects, device secrets, raw
  credentials or other account-sensitive fields through navigation or templates.

### Out of Scope

- Adding new settings categories, settings persistence, backend mutation routes
  or permissions.
- Redesigning the contents of category pages beyond the layout space needed for
  the sidebar.
- Changing native macOS recording, meeting detection or audio-routing behavior.
- Mixing `/admin` navigation into the user settings rail.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a desktop settings viewport of at least 1024px width, 100% of
  the five actionable categories are visible in the side navigation without
  horizontal scrolling.
- **SC-002**: From any settings category, a user reaches any other canonical
  category with one navigation activation and no intermediate overview screen.
- **SC-003**: In browser and embedded render checks, 100% of actionable category
  links have matching route, heading and active-state evidence; the overview
  entry point has a matching heading and no false active link.
- **SC-004**: At a 320px-wide viewport, 100% of canonical categories remain
  reachable and no settings navigation text is clipped out of the viewport.
- **SC-005**: Existing settings contract and focused integration tests remain
  green, including CSRF, safe-account-output, return-path and recording-handoff
  assertions.
- **SC-006**: No new settings data model, mutation endpoint or capture-policy
  behavior is introduced by this slice.

## Assumptions

- The existing route map is the source of truth for the sidebar; the slice does
  not invent sections for settings that do not yet exist.
- Group labels are presentation-only and do not change authorization or scope.
- Desktop and embedded web surfaces share the same server-rendered navigation
  contract; only the base path differs.
- The supplied Krisp screenshots are a structural reference for grouped left
  navigation, selected state and dark density, not a request to copy branding,
  icons or product copy.
- The current GRAF design tokens, typography and native capture boundaries remain
  the visual and product baseline.

## Dependencies

- Existing settings route map, category view model and server-rendered templates.
- Existing browser/embedded page shell and settings CSS tokens.
- Existing settings contract, accessibility and mutation tests.
