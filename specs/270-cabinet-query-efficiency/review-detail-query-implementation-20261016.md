# Независимое ревью реализации полной детали F270

Дата:2026-10-16. Ветка:`codex/270-cabinet-query-efficiency`.
Базовый HEAD:`5395cfd5e45f3cd4aa3fbdee91fdbc2973256dae`.
Область:T032/T033, часть T025/#7142. Полоса:`high-risk-product`.

**Итог: PASS локального среза T032/T033 на указанном ниже снимке6файлов.**
Открытых замечаний к прочитанному коду нет; R01 исправлено и проверено.
Независимо исполнен весь окончательный новый suite:37PASS. Это не полная
приёмка F270, не T026 и не разрешение на коммит/слияние/выпуск. Отметки
качества требований13/13+20/20+8/8 остаются отдельными от исполнения кода.

## Найденная и исправленная ошибка R01

HIGH: `cache_access=False` первоначально обходил карты membership/grants,
но `_share_grant_recipient_is_valid` продолжал использовать и заполнять
`viewer_verified_emails`. После одного решения доступа последующий календарный
переход мог повторно использовать уже отозванное подтверждение адреса.

Независимая исполняемая проверка с синтетическим AsyncSession-заменителем:
первый вызов с подтверждённым адресом=True; затем источник адресов очищается;
второй вызов на первоначальном коде=True, число чтений1. После исправления
обоих read/write условий на `prefetch.cache_access` та же проверка подтверждает
`(True, False, 2, {})`: прежний положительный ответ больше не кэшируется,
два чтения и пустая карта. Реальная PostgreSQL-проверка
`test_detail_recipient_identity_is_read_again_after_revocation` затем включена
в окончательный независимо исполненный37случайный suite и прошла.

## Чтение реализации

| Поверхность | Результат чтения |
|---|---|
| `_meeting_review_read_scope` | Сохраняет прежний CabinetReadPrefetch, очищает его перед первоначальной auth, восстанавливает через finally; nested вызов создаёт собственный scope |
| `_prefetch_meeting_review_reads` | Один SELECT с ограниченными lateral источниками; каждый≤1строки; отдельные latest/effective алиасы и разные порядки |
| Access | membership/grants обходят карты при cache_access=False; после R01 verified emails тоже читаются заново; recipient_proof/share_actor_proof прежние |
| Calendar | Повторные Meeting и decide_meeting_access не удалены; переиспользуется только точно workspace/viewer/meeting-fenced calendar link |
| Outcome | default/selected раздельны; outcome_candidates сохраняют сырые fenced строки и передают include_non_publishable/allow_legacy_read_only/processing_result_id в прежний pure validator |
| Playback | default pinned outcome определяет revision; invalid pinned resolution даёт None; fallback accepted не требует immutable, как прежде; canonical pure validator остаётся |
| Presence | Только реально загруженные transcript/diarization того же result ID; effective ID может отличаться и сохраняет отдельный путь |
| Контракты | Схема, RLS, публичные сигнатуры, stream/download/write пути не изменены |

Проверены все9потребителей общего чтения: APIcabinet; browser detail,
shared detail, share fragment; embedded detail, share fragment; speaker rename;
title conflict response; calendar context HTMX response. Изменён общий путь;
отдельные правила разрешения операций этих маршрутов не удалены.

## Независимое исполнение

Команда через существующий `run_local_postgres_tests.sh --focused`,
`UV_NO_SYNC=1`, существующее окружение, `GRAF_TEST_WORKERS=1`:

- `tests/integration/test_transcript_export_egress.py::test_export_capability_never_pairs_an_accepted_summary_with_a_newer_result`;
- `tests/contract/test_summary_template_ui_contract.py::test_meeting_detail_renders_the_selected_summary_slot_after_reload`;
- `tests/integration/test_cabinet_meeting_detail.py::test_098_authorized_recurring_pointer_reuses_context_block_with_web_embedded_parity`;
- `tests/integration/test_cabinet_meeting_detail.py::test_098_deleted_recurring_predecessor_has_no_block_or_disabled_placeholder`;
- `tests/integration/test_meeting_summary_slots.py::test_complete_and_grandfathered_bindings_keep_type_specific_current_reads`.

Результат:**5PASS/11.76s**, runner duration16s,
collection digest:`83ccd8875a16c182fa45d79926e832c09c497f7178560519c854d3ebecef1e84`.
`postgres_test_cleanup=isolated_container_removed`. Одна прежняя
PytestAssertRewriteWarning; пропусков и падений нет.

Это доказывает реальные browser/source ссылки с invalid/foreign отказами,
selected-slot UI, авторизованный/deleted recurring pointer и прежние
binding flags. Последний тест не включает detail-предвыборку, поэтому сам
по себе не подтверждает новую outcome_candidates ветку.

## Остаток первой проверки и его итог

- PASS: окончательный новый budget suite с published built-in/custom≤25,
  history5→50,scope/nested/exception,result-order конфликтом и постоянной R01.
- PASS: outcome_candidates при активной detail-предвыборке:available/failed/
  candidate/legacy; на каждом состоянии36комбинаций template/include/legacy/source
  сопоставлены с одиночным resolver, включая неверный processing_result_id.
- PASS: два вызова общего чтения в одной сессии после revoke/deleting дают
  прежний отказ,None; scope после обоих вызовов отсутствует.
- PASS: ложная API/source строка удалена. Добавлен прямой helper parity с
  source_result_id+selected custom template и полным model_dump. Реальный
  browser/source с invalid/foreign случаями независимо проверен старым тестом выше.
- PASS:6/6 hashes до/после независимого37случайного прогона совпали.
  Отчёт полного серверного прогона пока отсутствует: это отдельная T026.

T026/full suite/SC-005, точный SHA PR, разрешение коммита/слияния, выпуск и
приёмка установленного приложения остаются отдельными воротами. В этой проверке
агент менял только этот отчёт; никаких продуктовых/test/spec/plan/tasks/GitHub
изменений не делал.

## Окончательный независимый прогон

Исполнен существующим runner на реальной PostgreSQL:

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
  bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_cabinet_meeting_detail_query_budget.py -q -s
```

**37PASS/108.98s**, runner113s,collection37,
collection digest:`ba4e07216b859b64e08356cd2a9a86fb50f8cdd70682451128437dca35d8ecdd`.
`postgres_test_result=pass`, `postgres_test_cleanup=isolated_container_removed`.
Одна прежняя PytestAssertRewriteWarning; пропусков/падений нет. Отрицательные
пробы намеренно достигают26SQL и подтверждают AssertionError предохранителя.
Оба полных HTTP-экрана и published built-in/custom прошли≤25;5→50истории
на обоих экранах не увеличивает число SQL,содержимое не обрезается.

Прочитан основной журнал `F270-detail-budget-matrix-second.log`:62PASS/123.53s;
в нём фактически записаны24SQL обычной детали,25SQL опубликованных built-in/
custom итогов,24/24history и26обеих отрицательных проб. Это отдельный журнал
основного агента; он не подменяет независимый37случайный прогон. Ранний
185случайный regression начал импорт до финальных правокR01/canonical:
его нельзя представлять как проверку всех окончательных байтов.

Независимых разных исполненных случаев37+5=42; повтор одного и того же
случая в другом журнале к этому числу не добавляется. Для первых5не был
заморожен отдельный6файловый снимок,поэтому exact-bytes доказательство ниже
относится именно к37случаям окончательного нового suite.

### SHA-256 снимка до и после независимого окончательного прогона

- `apps/server/src/twobrain_rec_server/cabinet/queries.py`: `9a84866cee19d5fbaee1d7d9390e3fc7f26ad22945db20c60177aabb4396b605`
- `apps/server/src/twobrain_rec_server/cabinet/read_prefetch.py`: `b39afa3b2e1cac3b231c7621bd9d931b6d35beeae9ea0b5d4bf361a716404fda`
- `apps/server/src/twobrain_rec_server/cabinet/egress.py`: `f0afefd6633ef92bdba3eb3f80ef9a17ca3d40a263082eb1367bfbdda4ae7bcc`
- `apps/server/src/twobrain_rec_server/cabinet/access.py`: `12c96ecbbada2d3bb027f29b711a038fdf1e0f4cad050c7c2184b089d0f3afb4`
- `apps/server/src/twobrain_rec_server/calendar/service.py`: `5c81afc11964c63314c1dcdafd381c594ed6f8081141117afb63ffd033c8fb84`
- `apps/server/tests/integration/test_cabinet_meeting_detail_query_budget.py`: `730ab32ab05154542ce231d8f76c182f46ab8aec11ac981cd5dca1281aa0e9a3`

Перед окончательным ответом все4чеклиста перечитаны и посчитаны:
13/0 detail-query,20/0 security,8/0 tenant-context,16/0 requirements.
Reviewer-owned всего41/0,с историческим requirements57/0. Runtime-пункты
исторического security отчёта не переписаны. Полный SC-004/SC-005 остаётся
неподтверждённым до T026; PASS этого отчёта относится к локальному исправлению.
