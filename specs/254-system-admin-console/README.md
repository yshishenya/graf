# Feature 254 — системная консоль GRAF

Ветка: `codex/254-system-admin-console`. Общая задача: [#6708](https://github.com/yshishenya/graf/issues/6708). Высокий риск: авторизация, глобальный доступ, деньги, удаление, диагностика.

Комплект предназначен для реализации полного запроса: отдельный вход; суперадминистратор и роли; все пользователи/встречи/расшифровки/записи; восстановление и удаление; подписки, индивидуальные права, тарифы и акции; диагностика и продуктовые показатели. Подготовка закоммичена в `e8286572b`; по поручению пользователя начата реализация. Текущее состояние и проверки: [implementation-evidence.md](implementation-evidence.md).

| Документ | Назначение |
|---|---|
| [spec.md](spec.md) | 12 сценариев, 90 требований, 12 измеримых целей, clarify и границы |
| [ui-and-operations.md](ui-and-operations.md) | Экраны, формы, роли, операции, денежные и временные правила |
| [telemetry-and-metrics.md](telemetry-and-metrics.md) | События, 30 показателей, сбор/разрешение/сроки/пределы |
| [plan.md](plan.md) | Архитектура, зависимости, выбранный стек, профиль нагрузки и gates |
| [research.md](research.md) | Решения по текущему коду и причины выбора |
| [research-and-readiness.md](research-and-readiness.md) | Карта существующих функций и исходное продуктовое исследование |
| [data-model.md](data-model.md) | Сущности, ограничения, состояния, версии и транзакции |
| [contracts/api.md](contracts/api.md) | Маршруты, ошибки, preview/commit, разрешённые команды и клиентские события |
| [contracts/security.md](contracts/security.md) | Отдельный origin/login, MFA, RLS, worker authority, аудит и выдача контента |
| [contracts/migration.md](contracts/migration.md) | Миграция старых данных, включение, согласование writers и откат |
| [tasks.md](tasks.md) | 39 задач с путями, зависимостями и покрытием требований |
| [issues.md](issues.md) | Однозначная связь каждой задачи с GitHub |
| [acceptance.md](acceptance.md) | 42 приёмочных сценария и критерии свидетельств |
| [quickstart.md](quickstart.md) | Команды/данные/сценарии проверки будущей реализации |
| [analysis.md](analysis.md) | Находки ревью, исправления и фактические проверки подготовки |

Контрольные списки: [security](checklists/security.md), [billing](checklists/billing.md), [diagnostics](checklists/diagnostics.md), [UX](checklists/ux.md), [infra](checklists/infra.md); авторская проверка specify/clarify — [requirements](checklists/requirements.md).

Проверка целостности комплекта:

```sh
python3 specs/254-system-admin-console/validate_artifacts.py
```

Продолжать реализацию с незаконченной T003, соблюдая зависимости. Не объявлять фичу завершённой после первого среза доступа/встреч: тарифы, подписки, акции и статистика остаются обязательными. Документы и ветка подготовлены локально; GitHub задачи созданы отдельно. Проверенные участки реализации фиксируются отдельными коммитами; push/PR/выпуск ещё не выполнялись.

Подготовка проверена: 27/27 профильных reviewer-пунктов и 14/14 общих; документный validator и project governance проходят. T001–T002 выполнены как основание; T003 в работе, остальные задачи открыты. Первые PostgreSQL-проверки выполнены, полная приёмка фичи ещё предстоит.
