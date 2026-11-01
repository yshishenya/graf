# Проверка F140/T077/O15 — 02.11.2026

Полоса: active Spec Kit slice/high-risk-product. Ветка codex/140-observation-storage,
HEAD/base 4c7924ea69ac6c0968d563988b884a0ecc75ba21. Только S1–S6 storage projection
в исходной T077/#4932; полный FR-089/O6 и T070 остаются открытыми.

## Результат профильных проверок

12 уникальных окончательных PASS, 0 FAIL/ERROR/SKIP: 3 новых unit,
6 новых PostgreSQL/CLI и 3 затронутых прежних PostgreSQL/CLI.
Unit 0.04с; первоначальный PG 47.29с, correction1 15.29с, correction2 9.01с.
Последующие исходы заменяют те же nodeids; числа запусков не складываются.
Два прежних предупреждения pytest/Starlette, новых SAWarning нет.

Запуск: owned apps/server/.venv/bin/python, PYTHONPATH=src:.; package __file__
проверен в owned src. PostgreSQL17, полные Alembic миграции, ENABLE/FORCE RLS,
restricted maintenance. Точные nodeids, frozen11 input hashes и все XML/log
hashes находятся во внешнем metadata-only manifest
f140-t077-storage-implementation-validation-20261102.json.

Проверены существующие источники: Free/Trial/paid cutoff; applied bonus;
действующий storage grant; base purchase_schema2; legacy catalog; historical
capacity cache; истёкший journal. Независимая ожидаемая сумма13 пространств —
156750000000 байтов. Used/reserved — реальные canonical artifacts и активные
резервы: 888/90, после позднего commit989/140; старый RR снимок прежний.
Проверены missing subscription отдельно от NULL/unknown plan, nonfinite даты,
expiry==as_of, malformed/NULL reservation, sorted groups/приоритеты/null totals,
полная граница500/501 и общий timeout штатного wrapper.

CLI из нового процесса/разные report_date, разрешённые группы без private
sentinels, HTTP запрещён, no-write fingerprints новых источников совпадают.
Truthy неподдерживаемые snapshots/schema/helper exception дают безопасный
report_unavailable/exit1; falsy обеих snapshot границ сохраняет прежний fallback.
Роли, SET ROLE, неверный контекст и mutation denied; READ ONLY до hooks сохранён.

## История, исправления и очистка

Причинный RED: unit3 FAIL до collector; PG1 FAIL на прежнем sourceNone.
Initial PG:6PASS/3FAIL — дополнительные синтетические personal workspaces
нарушали настоящий unique personal-owner. Исправлены только данные fixture:
corporate поддерживает разные пространства одного владельца, схема прежняя.
Correction1:1PASS/2FAIL — grant40G не совпал с произвольной catalog row и NULL
synthetic VALUES PostgreSQL вывел как text. Fixture теперь выбирает настоящий
40G month/version2 с его amount_minor и явно задаёт NULL::timestamptz.
Correction2:2PASS. Constraints/RLS/продуктовая логика не ослаблялись.
Ruff изменил только организацию imports/удалил неиспользуемый select.
Успешные unit3/initialPG6/correction1PG1 не повторялись.

Все собственные одноразовые контейнеры удалены fixture finally; полные sets
после каждого запуска равны своим baseline. Чужой старый bootstrap и другие
проекты сохранены. Перед контейнерами147GiB свободно; рабочих данных нет.
Ruff/diff/process/governance/context/fragments PASS.
87/87 полных task lines и20/20 прежних checklist побайтно прежние:
266 checked/58 unchecked; новый storage reviewer-owned checklist10/0 отдельно.

## Границы и следующие ворота

Всегда partial/database_inventory, reconciliation_gaps=null. Capacity с
historical cache не финансовая сверка, used не MinIO, expired-active не
доказательство очистки/работы заданий. Все сроки O6 сохранены. Существующие
helpers/writers/схема/права/CLI/guard/cleanup/лимиты прежние. Новых служб,
зависимостей, тревог/записи, Full/CD/Dev/выпуска/реальных платежей нет.
Независимое code review — APPROVE, новых замечаний нет; отдельная scoped
converge:6 требований/7 решений плана/7 принципов,0 новых пробелов.
Полный фактический отчёт review-storage-projection-code-20261102.md прочитан
основным исполнителем; SHA-256 a74f9143a679d5f46eab5e8df63b60a8018011558a2d5e7c1a15ae659f39db85.
11 frozen inputs и12 XML/log hashes совпали с проверенными. Полный O6 HIGH
partial остаётся в T077. Exact-SHA/base PR checks — следующий отдельный допуск;
commit/PR/merge ещё не заявлены. Это не закрытие #4932.
