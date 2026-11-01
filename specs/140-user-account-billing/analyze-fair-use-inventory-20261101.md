# Scoped analyze F140/T077 O12 — 01.11.2026

High-risk-product/active Spec Kit slice, owner repository-audit.
Проверены новые F1–F6; полная F140 повторно не принимается.
Штатные prerequisites --json --require-tasks --include-tasks: PASS;
spec существует отдельно. Before/after_analyze hooks отключены.

| Требование | Задача | План и проверка |
| --- | --- | --- |
| F1 источник/inventory/count строк | T077/#4932 | FairUseReviewRecord, без фильтра дня/магазина |
| F2 пять state/unknown/confirmed | T077/#4932 | CASE и сортировка; confirmed не снятое ограничение |
| F3 pending/четыре buckets/границы | T077/#4932 | NULL/isfinite до numeric epoch; 86400секунд, ±1мкс |
| F4 partial/reason/null/error | T077/#4932 | Приоритеты, пустота и отказ схемы; срок не доказанный SLA |
| F5 один SQL/приватность/no-write | T077/#4932 | Только state/starts_at/review_by, READ ONLY RR/guard/лимиты |
| F6 порядок и реальная приёмка | T077/#4932 | RED/PG/CLI/constraints/RLS/privacy/снимки/review/converge/exact gates |

6 требований,1 исходная задача,100% покрытия. Новых ambiguity/duplication/
CRITICAL/HIGH/MEDIUM/LOW=0; новых несвязанных задач0. Конституционные
I–VII сохранены: нет capture/денежных/правовых/egress/deletion mutations,
metadata-only и независимый процесс обязательны. Исходные FR107/FR089,
operations/security/deletion/F278FR041 зависимости сохранены. Обратный порядок
и >24ч проверяются защитно без ослабления положительной схемы; infinity
безопасно отделяется до арифметики. Не обнаружено конфликта с планом/моделью.

Полный O6/FR089 остаётся HIGH partial исходной T077, все87 исходных полных
task lines и58 старых checklist gaps прежние. Исторический пропуск чтения
до PR7884 не исправлен; весь O8 не PASS. Реализация разрешена только после
проверяемого независимого checklist PASS и подтверждения прежней #4932.

## Входы анализа

- `specs/140-user-account-billing/spec.md` SHA256 `2bb46cd0c1a56229b805020826b5c394896ad40570e49442e37058b9974c07c1`
- `specs/140-user-account-billing/contracts/operator-observation.md` SHA256 `d2677f946881c4aac82a96932cfde02d1418e230ce835b177f76f9db5a80563b`
- `specs/140-user-account-billing/plan.md` SHA256 `541b831f259b4df9c995f2920f7539afda709c6d1ce6546a38b47affb0eb2947`
- `specs/140-user-account-billing/tasks.md` SHA256 `f37b52d4ddf7f8a36b56f50ca410172a7af19154bc02c13d38373a3f4cc5318c`
- `specs/140-user-account-billing/quickstart.md` SHA256 `345236fe985477df29e569eb115e5265b126829bd040cc7f60543461476cd434`
- `specs/140-user-account-billing/research.md` SHA256 `d32added43f00e206e658932dd93574196682ed1e9e58f4b1bcf9e94d2a85183`
- `specs/140-user-account-billing/data-model.md` SHA256 `b8aa76ae308f33b29d3a58aa5f3c399aa062bedaf54f14e21edea1776d4e2d18`
