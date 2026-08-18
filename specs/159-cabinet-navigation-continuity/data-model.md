# Data Model: непрерывная навигация кабинета

Новых persistent entities, migrations и API contracts не требуется. Срез меняет
только server-owned presentation projections и shared shell behavior.

## Presentation entities

### Cabinet shell surface

| Поле | Значение | Инвариант |
|---|---|---|
| `embedded` | browser или embedded mode | Приходит из явного route/shell contract; User-Agent не используется. |
| `active_nav` | текущий product route | Не меняется при toggle и не получает новый redirect. |
| `shell_mode` | `cabinet` или `settings` | Определяет содержимое одной primary rail. |
| `return_href` | canonical meetings path | `/meetings` или `/desktop/meetings` в зависимости от surface. |

### Cabinet navigation item

Существующий `CabinetNavigationItem`: безопасные `id`, `label`, `href` и `icon`.
`aria-current` выставляется только для текущего item.

### Settings category view

Существующий `SettingsCategoryView`: `id`, `label`, `description`, `scope_label`,
`href`, `group_label`, `icon`. Новая rail не меняет category ids, route suffixes,
scope или authorization.

### Safe profile projection

Существующий `AccountSettingsSurface.profile` / `AccountProfileView`.
Разрешённые отображаемые поля:

- `display_name`, включая fallback «Без имени»;
- verified `primary_email`, если он доступен текущей сессии.

Запрещённые поля: provider subject, internal user/account IDs, tokens, session
secrets, credentials и meeting content.

### Auth entry intent

Существующий login/signup/invitation/provider/email-code intent с bounded
same-origin return path. Новая сущность или состояние не создаётся.

## State transitions

### Sidebar toggle

`expanded ↔ collapsed` через один control. Каждое состояние имеет truthful
`aria-expanded`, action label/title и icon. Повторная activation идемпотентна.

### Profile menu

`closed → open → closed` по trigger, Escape или outside click. При закрытии focus
возвращается на исходную profile button, если она ещё подключена к DOM.

### Settings rail

`cabinet → settings(category) → cabinet`. Selected category определяется
текущим route, а не клиентским persistent state.

## Validation rules

- У каждого shell surface максимум один shared sidebar toggle, один profile menu
  initializer и один web download CTA.
- Embedded surface имеет ноль sidebar download CTA.
- Partial updates не создают дублирующие controls/listeners.
- Rendered output не содержит запрещённых safe-profile fields.
