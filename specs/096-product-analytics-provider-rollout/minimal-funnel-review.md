# Независимый review требований минимальной воронки

Дата: 2026-10-03. Reviewer: отдельный агент header_review. Область: append-only срез FR-030–034 и T105–109, не исторический broad capture/provider rollout.

## Вердикт

PASS requirements-quality: 8 пунктов подтверждены, 0 неподтвержденных; блокеров качества требований не выявлено. Реализация, ingestion, конфигурация проекта и production readiness этим review не подтверждаются.

## Доказательства

- CHK001: новый раздел spec явно заменяет исторический широкий сбор в данном выпуске. Согласованы pseudonymous IDs/noIP/no-content/no-autocapture/replay/direct desktop; политика и главная неизменны.
- CHK002–003: FR-030 отделяет собственное согласие аутентифицированного пользователя от operator approval, auth и cookies; unknown/stale/revoked закрывают отправку. План шаг1 не позволяет выводить consent из клиентского payload/workspace; legal соответствие остается отдельным блокером.
- CHK004: FR-031 требует server-bound pseudonym(user_id), отказывает чужим claims и сбрасывает desktop контекст при выходе/смене principal; T106 и quickstart предусматривают пользователей A/B.
- CHK005: FR-032 отличает HTTP receipt от ingestion, сохраняет возможность повтора после provider error/readiness blocked и требует устойчивую идемпотентность. FR-033/quickstart требуют одну активацию на синтетическом ingestion.
- CHK006: новый согласованный режим, FR-033/034 и acceptance запрещают IP, PII/content/secrets/free fields и разрешают только существующий каталог; GeoIP/IP enrichment явно выключается. План ограничивает routes и не разрешает новый broad/direct сбор. При implementation review проверить также provider-specific IP fields/enrichment и фактические transport routes: одного отсутствия пользовательского IP в прикладном JSON недостаточно для runtime proof.
- CHK007: FR-034 отличает 365-day supported configuration от TTL/purge и требует оценить удаления; существующие runtime/access/backup/restore/legal proofs не объявляются выполненными.
- CHK008: acceptance сохраняет production flags off; plan шаг5, T109 и quickstart требуют isolated synthetic checks и точные PR CI. Production enablement, credentials/grants, history purge, payments и изменения policy/UI не разрешены.

## Независимые operational blockers

Legal сопоставление существующих notices, supported management session/access, актуальные backup/restore/access proofs, безопасная secret wiring и настоящий ingestion/readback остаются открытыми. Настройка retention не применяется этим review. Псевдонимные идентификаторы связуемы с аккаунтом и не являются необратимо анонимными.

## Повторное чтение

minimal-funnel.md: 8 [x], 0 [ ]. Проверен каждый пункт с текущими artifacts. Исторические checklist не изменены и не переаттестованы. Отмеченные требования не означают завершение T105–109 или успешную runtime доставку.

Reviewer изменил только minimal-funnel.md и этот отчет; код, spec, plan, tasks, commits, GitHub и production не изменял. Не создавались synthetic production events и runtime proofs не фабриковались.

Дополнительно прочитан уточненный plan: nullable authenticated user consent record, tenant RLS, default-off endpoint, проверка записи при каждом событии и недоступность acceptance до реального legal gate. Это усиливает CHK002–004; synthetic fixture approval не является production approval, а user-action UI путь остается непроверенным. Вердикт требований не изменился.
