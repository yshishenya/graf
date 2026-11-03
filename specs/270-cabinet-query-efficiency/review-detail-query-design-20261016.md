# Независимая проверка требований полной детали F270

Дата: 2026-10-16. Ветка: `codex/270-cabinet-query-efficiency`, исходный HEAD
`5395cfd5e45f3cd4aa3fbdee91fdbc2973256dae`. Область: требования и проектирование
T032/T033, часть T025 и #7142. Полоса — `high-risk-product`.

Результат первой проверки: **FAIL** по F01. После исправления требований
и повторного чтения результат **PASS: 13/13 нового списка, 41/41 reviewer-owned**.
Неподтверждённых требований и открытых HIGH/CRITICAL замечаний нет.
Это проверка качества требований до кода. Новые продуктовые изменения,
исполнение тестов, GitHub, коммиты, слияние и выпуск не выполнялись.

## Замечания

### F01 — HIGH, устранено: путь к бюджету опубликованных итогов

`plan.md`, раздел «Полная деталь», пункт6, рассчитывает ровно25 SQL для простой
готовой детали. При этом `spec.md`, уточнение полной детали, и `quickstart.md`,
сценарий7, требуют тот же потолок для опубликованных итогов. В расчёте нет
отдельного чтения `MeetingOutcomeItem` (`outcomes/service.py:795`) и названий
шаблонов (`cabinet/queries.py:1555`, личный default также :1576). Эти чтения
не входят в перечисленные в пункте4 одиночные связи; items — коллекция и
не могут молча перемножать строки остальных связей.

Нельзя считать доказанным архитектурный путь к25, оставляя ровно25 на
базовый сценарий и дополнительные обязательные чтения без назначения в плане.
Нужно определить опубликованные проверочные варианты (встроенный/личный шаблон,
пункты итогов), назначить их чтения в ограниченные запросы/отдельные коллекции
и дать непротиворечивый предварительный расчёт. Фактическое число затем обязан
подтвердить полный HTTP-предохранитель. Увеличивать потолок нельзя.

### F02 — устранено в ходе проверки: отсутствующий selected slot и default

Первоначальная формулировка «отсутствующий слот не подменяется другим шаблоном»
конфликтовала с `get_cabinet_meeting_review`:1536–1554: при отсутствии selected
outcome он явно запрашивает default. Текущие `spec.md`:228–232,
`plan.md`:254–259 и `data-model.md` различают честный None отдельного resolver
и сохранённый переход отображения selected→default. CHK007 подтверждён.

### F03 — рекомендация выполнена: различающиеся порядки выбора результатов

После уточнения план и quickstart7 прямо закрепляют ситуацию, где imported_at
и result_version дают разных победителей. `_latest_result` (`queries.py`:2205)
выбирает attempt→imported_at→result_version; `effective_processing_result_query`
(`processing/results.py`:48) — attempt→result_version→imported_at. Хвост
created_at/id и NULLS LAST также сохраняется. Это не новый продуктовый выбор.

## Поэлементное сопоставление detail-query.md

| Пункт | Результат | Точное доказательство требований |
|---|---|---|
| CHK001 | PASS | spec уточнение полной детали:84×30%=25, все SQL полного HTTP; plan п.1; quickstart7: обе страницы и служебные обращения |
| CHK002 | PASS | baseline `seed_cabinet_meetings`,84→68 и рост5→50; quickstart7 built-in/custom summary с items; plan п.3/4/6:один bounded SQL,24+1=25; F01 устранено |
| CHK003 | PASS | spec FR-006/011, уточнение:API/partial/all9 callers; quickstart7: serialized MeetingReviewResponse прежнего/нового пути плюс прежние контракты |
| CHK004 | PASS | tasks T025–027 остаются открыты; plan завершение:full suite/SC-005/exact-SHA checks/release-full отдельны; quickstart3/5/7 |
| CHK005 | PASS | spec FR-003/012 и уточнение матрицы; quickstart7 строки Доступ/Удаление; recipient proof сохраняется |
| CHK006 | PASS | spec уточнение:workspace/viewer/meeting/revision/template/source-result; plan п.2:не читать/не заполнять membership/grants read-through в detail scope |
| CHK007 | PASS | spec уточнение:три независимых выбора ревизии; plan п.3–4/default playback slot, accepted fallback без immutable; selected→default уточнён; F02 |
| CHK008 | PASS | plan п.3:include_non_publishable/allow_legacy_read_only/processing_result_id; п.4:разные порядки; п.5:presence только exact workspace/meeting/result |
| CHK009 | PASS | plan п.4–5:populate_existing, повторные Meeting/decide_meeting_access календаря; spec FR-011; quickstart7 сохраняет старые security assertions |
| CHK010 | PASS | spec FR-008, уточнение; quickstart7 Данные/Версия/Удаление:missing,foreign lineage,deleting/deleted и отзыв между вызовами |
| CHK011 | PASS | spec уточнение; plan п.2:новый локальный prefetch после auth, восстановление прежнего, исключение и вложенный вызов; quickstart7 Срок жизни |
| CHK012 | PASS | plan п.3–4:outer join/LATERAL, максимум1 строка на источник, отдельные коллекции, прежние условия; schema unchanged |
| CHK013 | PASS | plan ожидаемые файлы/ограничения; spec Assumptions/Legacy Impact; tasks T032/T033 оба связаны с#7142, T025–027 открыты |

## Все действующие списки

Прочитаны полностью `checklists/requirements.md`, `security.md`,
`tenant-context.md`, `detail-query.md`. Исторические отметки исходных списков
не являются новой приёмкой реализации. `requirements.md` — исходная проверка
specify, не отдельный reviewer-owned runtime gate. Её16отметок сохранены.

- `detail-query.md`:13 checked /0 unchecked.
- `security.md`:20 checked /0 unchecked. FR-003/004/008/009/011/012,
  сохранённые ограничения списка, полный SC-005 и уточнение детали сохраняют
  основания20пунктов. Исторические R12/R18 остаются открыты по прежнему отчёту.
- `tenant-context.md`:8 checked /0 unchecked. FR-014/SC-007 и весь раздел
  контекста не изменены новой частью; план запрещает менять tenant_context/RLS.
- `requirements.md`:16 checked /0 unchecked, исходные отметки specify сохранены.
- Всего reviewer-owned:41 checked /0 unchecked; с requirements:57/0.

## Прочитанные источники и границы

`AGENTS.md`, `docs/agent-guidance/README.md`, `spec-kit-flow.md`,
`product-gates.md`, `release-and-validation.md`, конституция7.1.0;
продуктовые ограничения PRD §36 и F270/status update; активные
`.specify/feature.json`, spec/plan/tasks/quickstart/research/data-model.
В коде прочитаны get_cabinet_meeting_review и его latest helpers,
CabinetReadPrefetch, current_outcome_set, effective result, transcript visibility,
artifact/playback projection, calendar context response и processing-source/items.

Это чтение подтверждает реализуемость ограниченных SQL-связей и необходимость
сохранения разных выборов, но не заменяет красный/зелёный предохранитель,
сравнение полных ответов, runtime security matrix и независимое ревью кода.
Изменены только этот отчёт и reviewer-owned checklists: detail-query.md,
security.md, tenant-context.md. Код, spec/plan/tasks и состояние GitHub не менялись.

## SHA-256 снимка требований при первой проверке

- `spec.md`: `ebe5e06e5a97d9902e9a072d57c0652c341091866512b7a54fb6e6aa05aeafc4`
- `plan.md`: `6796d61819d17a9e6476c682e53f36567f5a1e394ce9c44aa79c4c82b5bf6289`
- `tasks.md`: `535fe566a60e0c9065c8150f9740df7294fc49fd1ff279fc3fff6d9b67629a72`
- `quickstart.md`: `efbff4e1db82ba535484c31fc9702e19d6a6c726c16781da181b7891ad168ebc`
- `research.md`: `a386505d878ebdd90bfa01f6976d9254fb2cf555856d37964389e18d92fb5c37`
- `data-model.md`: `b9aa792e85069d5df7f141f756efe69bfd2c527e226a2f9815913e06b5b93e0c`

## Повторная проверка после устранения замечаний

F01 устранён документально до кода. План п.3 включает только default/selected
слоты с не более одной строкой каждого, их outcome/result и custom template
name в тот же совместный SQL, что и прочие одиночные связи. Пункт6 сохраняет
отдельную коллекцию load_outcome_items:24→25 для опубликованного варианта.
При необходимости singleton attempt также входит в совместный SQL.
Quickstart7 явно требует built-in и custom summary с именем и items на обеих
полных HTTP-страницах. Число25 остаётся требованием, не измеренным результатом.

F02 устранён разделением resolver None и UI fallback; F03 — обязательной
парой результатов с конфликтующим imported_at/result_version. Дополнительная
обязательная изоляция access read-through явно записана в plan п.2: карты
членства/выдач не используются и не заполняются в detail scope; list scope
сохраняется. Пустого словаря было бы недостаточно, поскольку текущий
active_workspace_membership сам заполняет карту; план этот случай учитывает.

Все четыре checklists перечитаны после правок. Статистика повторно посчитана
по буквальным checkbox-строкам:13/0,20/0,8/0,16/0. Исторические обязательства
реализации security R12/R18 не закрывались.

План технически допускает bounded LATERAL/outer join и разные алиасы строк,
не требует кэша решений доступа и не меняет RLS. Не установлена практическая
скорость такого SQL и фактическое число запросов: это предмет RED/GREEN T032,
совпадения ответов T033 и последующего независимого review. Перед кодом всё
ещё нужны analyze и task-to-issue sync; этот PASS их не заменяет.

### SHA-256 окончательного снимка требований

- `spec.md`: `ebe5e06e5a97d9902e9a072d57c0652c341091866512b7a54fb6e6aa05aeafc4`
- `plan.md`: `6796d61819d17a9e6476c682e53f36567f5a1e394ce9c44aa79c4c82b5bf6289`
- `tasks.md`: `535fe566a60e0c9065c8150f9740df7294fc49fd1ff279fc3fff6d9b67629a72`
- `quickstart.md`: `efbff4e1db82ba535484c31fc9702e19d6a6c726c16781da181b7891ad168ebc`
- `research.md`: `a386505d878ebdd90bfa01f6976d9254fb2cf555856d37964389e18d92fb5c37`
- `data-model.md`: `b9aa792e85069d5df7f141f756efe69bfd2c527e226a2f9815913e06b5b93e0c`
- `checklists/detail-query.md`: `ab14f05da5b5103d68f4d37de266f2f884d161f1ce280e18543a990f89bce5be`
- `checklists/security.md`: `c3520569221c13a1e5029d22cc7fe5fe4624b8e3d8c51dac0abbd7087f8681f7`
- `checklists/tenant-context.md`: `e5e980b74f7c14a9eb78dfde46fd17104c78712b0114208f4b5d09e6648ab5df`
- `checklists/requirements.md`: `8258e18573ac7977981ef1dcdeb34bb86181896e5d14253a7f1774c4aa9abc16`

## Повторная поэлементная сверка прежних reviewer-owned списков

Все следующие пункты PASS качества требований; runtime-отметки не меняются.

| security | Подтверждающие артефакты |
|---|---|
| CHK001 | spec2026-10-16:recipient/source workspace и параллельные сессии; полная деталь:exact workspace/viewer/meeting |
| CHK002 | FR-003; plan Summary и полная деталь п.2:тот же decide_meeting_access |
| CHK003 | FR-003; tasks T011; detail п.2 запрещает membership read-through вместо свежей проверки |
| CHK004 | FR-003/012; plan shared-часть:ambiguous fallback; quickstart7:revoked/expired/ambiguous |
| CHK005 | spec shared clarification:recipient_scope.user_id/source_db; detail recipient_proof и scope one-call |
| CHK006 | FR-003/012; US2/AC2; quickstart4:summary-only не получает аудио/текст |
| CHK007 | FR-012; quickstart4:404 summary-only/unavailable audio,409 full без download permission |
| CHK008 | FR-012; quickstart4:revoked исчезает; quickstart7:отзыв между вызовами |
| CHK009 | product-gates Audio Artifacts And Diagnostics; constitutionIII; Evidence Safety:metadata-only |
| CHK010 | FR-004; Edge Cases mixed/deletion; quickstart7:deleting/deleted |
| CHK011 | FR-004/009; plan Constraints; detail не меняет decision/deletion helper |
| CHK012 | FR-011/SC-004; quickstart7 запрещает ослаблять прежние security assertions |
| CHK013 | FR-008 и Edge Cases; quickstart7 Данные:missing revision/result/slot; политика и календарь в FR-008 |
| CHK014 | Edge Cases empty workspace; shared clarification:skip empty group |
| CHK015 | spec shared clarification:0/1≤своего baseline; plan shared single path |
| CHK016 | FR-006/010; quickstart1/shared section:owner web/embedded/shared5→50 и negative probe |
| CHK017 | FR-010; research5:before_cursor_execute,без зависимости от времени |
| CHK018 | SC-005; plan full-suite clarification2214→1881,9s,7583s не wall time; без baseline OPEN |
| CHK019 | plan Complexity Tracking и detail:≤25обязательно,T025/T026/T027 OPEN |
| CHK020 | spec shared clarification:shared50,owner max100,последние50grants и UUID tie-break; plan Scale/Scope |

| tenant-context | Подтверждающие артефакты |
|---|---|
| CHK001 | FR-014; spec context clarification:все пары ключ/значение,конструкторы и операции прежние |
| CHK002 | FR-014; spec context clarification:transaction-local,after_begin,rehydrate,commit/rollback |
| CHK003 | spec context clarification:замена внутри транзакции,физическое соединение,параллельные сессии |
| CHK004 | SC-007:1SQL/pass,2initial passes,0empty; plan context:noPostgreSQL unchanged |
| CHK005 | FR-003/004/011/012/014; plan context запрещает удалять auth/data guards; detail context/RLS вне scope |
| CHK006 | spec context clarification:SQL failure прежний exception/rollback,нет защищённого чтения после failure |
| CHK007 | quickstart6:current_setting/strictRLS/worker/auth/read boundaries и unchanged assertions |
| CHK008 | spec context+detail завершение; tasks T025–027; SC-003/005 остаются обязательными и открытыми |
