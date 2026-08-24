# Data Model: Навигация кабинета

Новых постоянных данных нет. Описанные сущности — in-memory projection
существующего WebKit history и опубликованного состояния контроллера.

## History candidate

| Поле | Источник | Ограничение |
|---|---|---|
| `url` | `WKBackForwardListItem.url` | Должен быть разрешён route policy и отличаться от текущего URL. |
| `direction` | back list или forward list | Определяет порядок выбора и допустимый переход. |
| `safety` | existing safe/unsafe URL ledgers + route policy | auth, external, artifact и недоверенные записи не открываются. |

## Navigation state

| Поле | Значение |
|---|---|
| `canGoBack` | Есть безопасный отличный back candidate либо разрешён fallback meeting list. |
| `canGoForward` | Есть безопасный отличный forward candidate. |
| `canReload` | Текущий документ безопасен и контроллер не загружает другой документ. |
| `canGoHome` | Текущий URL не является fallback, а fallback — безопасный meeting list. |
| `isLoading` | Контроллер выполняет переход, reload или synthetic home load. |

## Invariants

- Любой выбранный candidate должен пройти существующую
  `EmbeddedCabinetNavigationPolicy`.
- Дубликат URL текущего документа не является пользовательским переходом.
- Session expiration продолжает запрещать возврат в protected cabinet routes.
- State buttons are a projection: they do not create a second navigation policy.
