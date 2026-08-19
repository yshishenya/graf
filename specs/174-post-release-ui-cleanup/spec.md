# Feature Specification: Пострелизная очистка интерфейса

**Feature Branch**: `codex/174-post-release-ui-cleanup`

**Created**: 2026-08-19

**Status**: Draft

**Input**: После принятого релиза устранить подтверждённые хвосты ревью: не терять профиль в узком embedded-окне, убрать конфликтующие поколения responsive-правил, удалить больше не используемую внутреннюю навигацию настроек и мёртвый tooltip-контракт, упростить native inspector и заменить хрупкие проверки исходного текста поведенческими regression checks — без изменения принятого пользовательского поведения.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Доступный профиль при любом поддерживаемом размере (Priority: P1)

Пользователь узкого окна GRAF видит тот же компактный sidebar, что и в более широком окне: профиль остаётся доступным, все элементы лежат на одной оси и ничего не перекрывается.

**Why this priority**: Исчезнувший профиль блокирует выход и переход к настройкам в реальном поддерживаемом состоянии окна.

**Independent Test**: Открыть embedded-кабинет на каждом граничном размере, проверить видимость и геометрию toggle, navigation и profile, открыть меню профиля и дважды переключить sidebar в одной точке.

**Acceptance Scenarios**:

1. **Given** embedded-окно шириной 720 px или меньше, **When** кабинет загрузился и sidebar компактный, **Then** профиль видим как цель 40×40 px, доступен мышью и клавиатурой и не перекрывает соседние элементы.
2. **Given** любое состояние sidebar на ширинах 640, 720, 980, 981, 1120, 1121 и 1280 px, **When** пользователь переключает sidebar, **Then** rail имеет принятую ширину 64 или 176 px, контент не переполняет окно по горизонтали, а toggle остаётся в верхнем слоте.
3. **Given** sidebar раскрыт или свёрнут, **When** пользователь дважды активирует toggle, не перемещая указатель, **Then** второе действие возвращает исходное состояние.

---

### User Story 2 - Настройки с одной навигацией и одной колонкой (Priority: P1)

Пользователь открывает любую страницу настроек и видит только основную навигацию кабинета, а содержимое начинается сразу после стандартного отступа без скрытой внутренней колонки.

**Why this priority**: Старый fallback больше не имеет production-потребителя, но сохраняет дублирующий контракт, стили и тесты, которые могут снова разъехать компоновку.

**Independent Test**: Открыть overview, обычную форму, календарный fragment и billing в web и embedded режиме; на каждой поверхности должен быть один navigation landmark, одна активная ссылка и одна колонка содержимого.

**Acceptance Scenarios**:

1. **Given** авторизованный пользователь открывает любую страницу настроек, **When** страница или частичный календарный fragment загружены, **Then** присутствует ровно одна основная навигация и нет скрытого дубликата внутреннего меню.
2. **Given** широкое или узкое окно, **When** пользователь переходит между разделами настроек, **Then** формы, маршруты, активные состояния, CSRF/auth/role boundaries и HTMX fragment boundaries остаются неизменными.

---

### User Story 3 - Стабильный native inspector без лишних контрактов (Priority: P2)

Пользователь macOS видит закреплённый сверху inspector toggle в том же месте и с теми же accessibility-свойствами, а внутреннее упрощение не меняет размер или поведение панели.

**Why this priority**: Неиспользуемый layout-wrapper и дублирующие source-string проверки усложняют безопасные изменения и закрепляют случайную структуру вместо результата.

**Independent Test**: Собрать и открыть native shell, проверить верхний toggle в раскрытом и свёрнутом состоянии, затем выполнить один смысловой accessibility/layout contract test.

**Acceptance Scenarios**:

1. **Given** native inspector открыт или закрыт, **When** пользователь переключает его, **Then** toggle остаётся закреплённым сверху в той же позиции, панель сохраняет принятые размеры и не перекрывает native или web controls.
2. **Given** keyboard или VoiceOver navigation, **When** focus достигает toggle, **Then** доступное имя, подсказка и действие остаются однозначными.

### Edge Cases

- Сохранённое состояние sidebar ещё не применилось после загрузки страницы.
- Профиль не содержит имени и показывает email/fallback без расширения compact rail.
- Download/update action отсутствует или присутствует перед профилем.
- Настройки загружаются полной страницей или HTMX fragment-ответом.
- Embedded page zoom увеличивает эффективную ширину интерфейса до узкого breakpoint.
- Native inspector получает минимальную высоту окна и длинное локализованное доступное имя.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Compact embedded sidebar MUST сохранять видимый и интерактивный profile action размером 40×40 px на всех поддерживаемых ширинах, включая 720 px и меньше.
- **FR-002**: Toggle, navigation actions, optional update/download action и profile action в compact state MUST использовать одну визуальную ось с допуском не более 1 px и MUST NOT перекрывать друг друга или main content.
- **FR-003**: Sidebar MUST сохранять принятые ширины 64 px в compact state и 176 px в expanded state, текущую responsive default-state semantics и возможность двойного переключения без перемещения указателя.
- **FR-004**: Responsive sidebar behavior MUST иметь один непротиворечивый владелец состояния; breakpoint-specific rules MAY задавать только реально отличающиеся свойства и MUST NOT скрывать доступные действия поздним каскадом.
- **FR-005**: Все production settings surfaces MUST использовать только outer cabinet navigation; внутренняя legacy settings navigation и её зарезервированная колонка MUST быть удалены.
- **FR-006**: Удаление legacy settings navigation MUST сохранить существующие routes, forms, active states, CSRF/auth/role boundaries, calendar/provider HTMX fragments и billing/referral flows.
- **FR-007**: Feature 173 fallback requirement MUST быть явно помечено как superseded этим срезом, чтобы historical contract не противоречил production truth.
- **FR-008**: Неиспользуемый tooltip data contract MUST быть удалён, при этом видимый rail tooltip, `aria-label`, `title`, hover, focus и keyboard behavior MUST сохраниться.
- **FR-009**: Native inspector MUST сохранить верхнее расположение toggle, принятую геометрию, accessibility semantics и отсутствие перекрытий после удаления неиспользуемого layout-wrapper.
- **FR-010**: Regression checks MUST измерять отрисованное или вычисленное поведение responsive sidebar и MUST NOT считать наличие отдельных деклараций достаточным доказательством видимости и геометрии.
- **FR-011**: Проверки native inspector MUST закреплять пользовательский accessibility/layout результат без дублирования одной и той же случайной структуры исходного кода.
- **FR-012**: Изменение MUST NOT добавлять новую runtime dependency, состояние, breakpoint, навигационную систему или пользовательскую настройку.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: На ширинах 640, 720, 980, 981, 1120, 1121 и 1280 px профиль имеет ненулевую видимую область, compact actions — цели 40×40 px, а horizontal overflow равен нулю.
- **SC-002**: На 100% проверенных settings overview/form/calendar/billing поверхностей существует ровно один navigation landmark и одна активная settings-ссылка.
- **SC-003**: Два последовательных действия по одной экранной координате возвращают web sidebar и native inspector в исходное состояние без перекрытий.
- **SC-004**: Существующие focused server, JavaScript и macOS проверки проходят; один новый поведенческий regression check падает на известном состоянии, где profile action имеет область 0×0.
- **SC-005**: Итоговый diff уменьшает количество legacy navigation/tooltip/layout кода и не добавляет зависимости или новый responsive state owner.
- **SC-006**: Feature quickstart и единичный repository fast gate проходят перед closeout; полный release gate не запускается в рамках этого нерелизного среза.

## Assumptions

- Принятый визуальный baseline Feature 172 сохраняется: compact rail 64 px, expanded sidebar 176 px, controls 40×40 px и допуск центров 1 px.
- Feature 174 supersedes только fallback-часть Feature 173; его основной single-column settings contract остаётся действующим.
- Все production settings routes уже находятся внутри outer cabinet shell; новых standalone settings consumers не создаётся.
- Видимый rail tooltip, доступные имена и browser `title` достаточны; отдельный `data-tooltip` consumer не существует и не вводится.
- Состояние данных, auth, capture, recording, billing и deployment не меняется.

## Out of Scope

- Редизайн sidebar, profile menu, settings IA, native inspector или размеров control.
- Изменение responsive breakpoint values, persistence или default expanded/collapsed behavior.
- Изменение capture, recording, permissions, auth, billing, backend data или release packaging.
- Production deployment, новый CalVer-релиз и публичная macOS-публикация.
