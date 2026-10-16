# Анализ восстановления совместимости F096

Scope: T109 / issue7472, действующие FR030–034a исходного draft. Требования интеграции записаны в integration-recovery-plan-2026-10-16.md. Source/base и два конфликтующих пути подтверждены git merge-tree без изменения рабочего дерева. Independent checklist — отдельный gate до применения кода.

| Обязательство | Реализация/проверка |
|---|---|
| Одна вершина схемы без потери ни одной ветки | Новый no-op merge0105, parents0102_explicit_analytics_consent и0104_summary_share_scope_cascade; прежние revisions сохранены |
| Совместимость данных и согласия | Disposable PostgreSQL upgrade с обеих вершин и старой0037; null/no-default/no-backfill, sharing schema |
| FR030/031 consent/user identity | Прежние explicit integration/UI и unit tests, auth switch, revoke/stale/CSRF |
| FR032/033 delivery/dedupe/no-content | Прежние synthetic provider tests, реальный ingestion остаётся незакрытым условием T109 |
| FR034/034a неизменные операционные границы | Default-off и waiver только прежнего draft; no production keys/flags/purge; не считать tests runtime approvals |
| Release/governance | Независимый review/converge; новый commit только после validation+approval; старые CI не применимы к новой базе |

Новых продуктовых требований/провайдеров/разрешений нет. CRITICAL/HIGH requirement ambiguities: 0 внутри локальной интеграции; readiness/runtime proofs остаются pending. Реализацию не начинать до независимого requirement PASS. Исторические полные CI, юридические и operational receipts не переаттестуются. Отдельный новый issue не создаётся: integration/test obligation принадлежит существующему T109, source tasks/PR уже связывают её с issue7472.
