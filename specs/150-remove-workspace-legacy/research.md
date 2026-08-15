# Research: Remove Workspace Legacy

## Clean cut instead of migration compatibility

**Decision**: Не переносить pre-097 memberships/data. Удалить report-only CLI и legacy fixtures; перед production cleanup выполнить backup и одноразовый read-only zero-data inventory.

**Rationale**: Публичного запуска и реальных данных нет. Две tenancy-модели создают риск неверного active workspace, billing owner и data placement без пользовательской ценности.

**Alternatives considered**: UI-only hiding оставляет опасный API/session path; автоматический mover не нужен без данных; постоянный report после clean cut становится мёртвым operational surface.

## Keep internal auth anchor, remove customer behavior

**Decision**: Сохранить configured login workspace для provider policy, callback state и RLS, но исключить его из callback target selection, customer tenant validation, list/activation и self-serve billing.

**Rationale**: Полное удаление anchor требует новой organization/global auth-policy модели. Configured server-owned ID уже достаточен как discriminator; новый DB subtype не уменьшает риск или diff.

**Alternatives considered**: organization-level auth schema — отдельная architecture slice; полагаться только на cleanup — недостаточно без runtime fail-closed guard; новый `auth_bootstrap` workspace kind — лишняя migration при наличии server-owned ID.

## Preserve legitimate corporate access

**Decision**: Internal ID исключается до membership resolution. Valid non-internal corporate membership остаётся доступным после explicit enrollment; pending invitation/domain/provider claim membership не создают.

**Rationale**: Удаляется ошибочная bootstrap compatibility без поломки B2B contract Feature 097.

## Canonical naming

**Decision**: Personal name — `Моё пространство`, subtitle — `Личное · Владелец`; corporate — реальное имя и `Рабочее пространство · <роль>`.

**Rationale**: Raw `Personal` и generic `Команда` не являются достоверными customer names.

## Concurrency

**Decision**: Existing unique personal-owner index остаётся source of truth; concurrent creation handles the uniqueness race and re-reads the winning personal workspace.

**Rationale**: Двойной callback должен быть идемпотентным outcome, а не 500. Новая locking abstraction не нужна.

## External pattern check

- WorkOS models organization access through membership and session revocation: <https://workos.com/docs/authkit/users-organizations>
- Slack does not expose a system/default anchor as an optional user workspace: <https://slack.com/help/articles/220266727-Join-or-leave-workspaces-in-an-Enterprise-organization>
- Notion switcher contains real accessible workspaces and removes left workspaces: <https://www.notion.com/help/create-delete-and-switch-workspaces>

The selected boundary follows these patterns: internal auth state is not a selectable tenant; customer access requires membership.
