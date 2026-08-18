# Data Model: Контекстная ссылка на приложение на экране входа

Постоянные сущности и схема данных отсутствуют.

## Ephemeral presentation context

- `safe_next`: уже нормализованный same-origin целевой путь login flow.
- `embedded`: вычисляемый флаг поверхности; `true` только для `safe_next`,
  начинающегося с `/desktop/`.
- `show_download_cta`: вычисляемый inverse presentation decision для login
  template; не сохраняется и не передаётся в auth/session state.

## Invariants

- `safe_next` не может быть внешним URL или protocol-relative URL.
- `embedded=true` не меняет пользователя, workspace, session, provider или
  redirect authorization.
- `/download` остаётся публичным GET-маршрутом и не получает новый контракт.
