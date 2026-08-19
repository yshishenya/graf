# Research: Пострелизная очистка интерфейса

## Decision 1: один финальный владелец sidebar state

**Decision**: Сохранить поздний JS-ready state layer как полный owner compact/expanded geometry и удалить из старых `≤980/≤720/≤1120` блоков только дублирующие или конфликтующие state properties. Breakpoint-блоки оставляют реальные layout differences.

**Rationale**: Три поколения правил сейчас сходятся только благодаря order и specificity. Узкий embedded профиль получает `display:none` из старого блока, а поздний owner восстанавливает opacity/visibility, но не display. Удаление конфликта исправляет root cause и уменьшает каскад.

**Alternatives considered**:

- Добавить ещё один `display:flex !important`: отвергнуто как четвёртый owner и маскировка причины.
- Откатить весь sidebar к старому дизайну: отвергнуто, потому что ломает принятые Features 168–173.
- Переписать responsive state в JavaScript: отвергнуто; существующих class/data state достаточно.

## Decision 2: удалить inner settings navigation полностью

**Decision**: Удалить imports/calls из 21 page template и двух HTMX fragments, затем удалить macro и все `.settings-navigation*` styles/tests. Settings page и calendar layout становятся single-column напрямую. Outer shell продолжает получать `settings_navigation` для единственной основной навигации.

**Rationale**: Все production routes используют `_page_shell(..., active_nav="settings")`; fragments уже передают `legacy_hidden=True`. Единственные видимые fallback consumers — synthetic tests. Сохранение macro больше не защищает реальный путь и оставляет второй IA contract.

**Alternatives considered**:

- Оставить guard `legacy_hidden`: отвергнуто после user approval и полного caller trace.
- Удалить весь `settings_navigation` view model: отвергнуто, потому что outer cabinet sidebar его использует.
- Менять каждый route: отвергнуто; route truth уже корректна.

## Decision 3: tooltip остаётся на существующей доступной поверхности

**Decision**: Удалить только неиспользуемый `data-tooltip` из button и JS update. Сохранить `data-rail-tooltip`, CSS pseudo-element, `aria-label`, `title`, focus и hover behavior.

**Rationale**: В коде нет consumer для `data-tooltip`; второй атрибут создаёт ложный контракт без пользовательской пользы.

**Alternatives considered**:

- Добавить consumer: отвергнуто как дублирование уже работающего tooltip.
- Удалить visible tooltip: отвергнуто, это принятое пользовательское требование.

## Decision 4: убрать только unused GeometryReader

**Decision**: Заменить `GeometryReader { _ in VStack... }` на тот же `VStack` с существующим outer infinite frame/background. Сохранить `HStack + Spacer` в header, чтобы hit region кнопки не расширился. Один test остаётся semantic layout contract; второй проверяет только accessibility help/hint.

**Rationale**: Geometry proxy не читается, а parent уже предлагает full height. Два теста сейчас дублируют source layout и один требует сам unused wrapper.

**Alternatives considered**:

- Ввести отдельный layout type: отвергнуто как лишняя abstraction.
- Заменить header на overlay/alignment без проверки: отвергнуто из-за риска расширить hit region.
- Удалить все source contracts: отвергнуто; один узкий контракт полезен для top-placement и accessibility.

## Decision 5: rendered evidence без новой test dependency

**Decision**: Удалить широкие CSS substring expectations, оставить точные semantic/exact-defect guards в pytest и выполнить небольшую computed-style matrix через существующий in-app Browser. Результаты записать metadata-only в quickstart.

**Rationale**: В репозитории нет browser-test dependency; добавлять Playwright ради одной CSS-регрессии не нужно. Live Browser уже доступен в принятом процессе и измеряет финальный cascade, который source-string test пропустил.

**Alternatives considered**:

- Собственный CSS parser/cascade emulator: отвергнуто как сложнее браузера и менее достоверно.
- Новая Playwright dependency/config: отвергнуто как избыточное для одного shared-shell contract.
- Только static test: отвергнуто, потому что именно он пропустил `0×0` defect.
