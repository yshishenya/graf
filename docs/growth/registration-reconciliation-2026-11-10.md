# Сверка новых аккаунтов за 2–8 ноября 2026 UTC

`public_signup_completed` охватывает только форму регистрации по коду. В
`v2026.11.10.4` карточка «Активные пользователи» в `/admin/metrics` тоже не
подходит: это текущие активные участники одной корпоративной рабочей области;
даты фильтруют дневные показатели использования, а не дату создания аккаунта.

Ниже разовый запрос для штатной роли с полной видимостью обеих таблиц.
Он не запрашивает имена, адреса, идентификаторы или строки пользователей.
Перед исполнением оператор подтверждает рабочую БД и область видимости роли.
`excluded_ids` и `external_ids` — UUID-массивы из разрешённой операторской
классификации, которую не нужно прикладывать к отчёту. Если такой классификации
нет, оставить оба пустыми: новые аккаунты будут в группе с неизвестным
статусом, даже если для них есть метка кампании. Реальные списки подставляются
только через разрешённый закрытый сеанс оператора, где параметры не попадут
в командную строку или журналы клиента и сервера. Если такой путь не
подтверждён, исполнить без списков и сохранить статус как неизвестный.

Запрос объединяет известные слияния и относит аккаунт к дате самой ранней
записи в его цепочке. Исключение любой записи цепочки имеет приоритет над
подтверждением внешнего статуса. Источник признаётся связанным, только если
на оставшемся аккаунте к концу периода записан непустой `source` с признаком
`linked`; слабая, отсутствующая или слишком поздняя запись остаётся неизвестной.
Это сверка по сохранившимся записям и известным слияниям: она не восстанавливает
стёртые записи и не объединяет аккаунты по предполагаемому общему владельцу.

```sql
\set ON_ERROR_STOP on
\if :{?excluded_ids}
\else
    \set excluded_ids '{}'
\endif
\if :{?external_ids}
\else
    \set external_ids '{}'
\endif

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL row_security = on;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SELECT has_table_privilege('public.user_identities', 'SELECT')
   AND has_table_privilege('public.client_acquisition_attributes', 'SELECT')
   AND NOT row_security_active('public.user_identities')
   AND NOT row_security_active('public.client_acquisition_attributes') AS full_read
\gset
\if :full_read
WITH RECURSIVE lineage(account_id, member_id, created_at) AS (
    SELECT id, id, created_at
    FROM public.user_identities
    WHERE merged_into_user_id IS NULL
      AND created_at >= TIMESTAMPTZ '2026-11-02 00:00:00+00'
    UNION ALL
    SELECT l.account_id, u.id, u.created_at
    FROM lineage l
    JOIN public.user_identities u ON u.merged_into_user_id = l.member_id
), cohort AS (
    SELECT account_id,
           CASE
               WHEN bool_or(member_id = ANY (:'excluded_ids'::uuid[])) THEN 'excluded'
               WHEN bool_or(member_id = ANY (:'external_ids'::uuid[])) THEN 'external_verified'
               ELSE 'status_unknown'
           END AS account_class
    FROM lineage
    GROUP BY account_id
    HAVING min(created_at) >= TIMESTAMPTZ '2026-11-02 00:00:00+00'
       AND min(created_at) <  TIMESTAMPTZ '2026-11-09 00:00:00+00'
)
SELECT account_class, count(c.account_id) AS accounts,
       count(a.account_id) AS source_linked,
       count(c.account_id) - count(a.account_id) AS source_unknown
FROM (VALUES ('excluded'), ('external_verified'), ('status_unknown')) AS classes(account_class)
LEFT JOIN cohort c USING (account_class)
LEFT JOIN public.client_acquisition_attributes a ON a.account_id = c.account_id
   AND a.attribution_confidence = 'linked'
   AND nullif(btrim(a.source), '') IS NOT NULL
   AND a.captured_at < TIMESTAMPTZ '2026-11-09 00:00:00+00'
GROUP BY account_class
ORDER BY account_class;
\else
    \echo unavailable: role does not have full table visibility
\endif
ROLLBACK;
```

При `unavailable`, ошибке или неполном периоде числа в отчёт
не переносятся. При успешной сверке `external_verified` — подтверждённая
часть; ненулевая `status_unknown` оставляет итоговое число внешних регистраций
неизвестным. Метка источника сама по себе не делает аккаунт внешним.

Проверено на временной PostgreSQL 14.13 с учебными строками и ограниченной
ролью: границы окна одинаковы при UTC и Europe/Istanbul, слияния по обе
стороны границы не искажают когорту, исключение имеет приоритет, пустая
когорта даёт нули, ограничение видимости или отсутствие `SELECT` даёт
`unavailable` без чисел. На рабочей БД запрос не исполнялся.
