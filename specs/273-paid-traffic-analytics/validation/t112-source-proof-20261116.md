# T112 — происхождение результата и краткое подтверждение, 16.11.2026

Ветка `codex/f273-result-visibility-20261116`, исходная точка этого шага
`f8c560c0e8afc5c425b7767613519f33ab3e673c`, полоса `high-risk-product`
существующей F273/T112. Это следующий шаг принятого проекта, не полный T112.

## До кода

Входные SHA-256 конституции, PRD, текущего статуса, product-gates,
spec/plan/tasks/research/data-model/quickstart и обоих контрактов совпали с
проектом. Затронутые разделы и зависимости прочитаны; незатронутая история
повторно использована по прямому разрешению владельца для F273.
Четыре reviewer-owned checklist сохраняют124 подтверждённых вопроса/0 открытых:
16/0,27/0,52/0,29/0. Принятые analyze и mapping T112→открытая #7698
сохраняются; требования и их отметки в этом шаге не менялись.

Область: новый внутренний `cabinet/result_visibility.py`, unit/DB contract
проверки и собственный фрагмент F273. Поиск вызывающих путей после изменения
находит только новый модуль и его тесты. Будущие callers — общий detail render
и защищённый POST обеих поверхностей; в этом шаге они ещё не подключены.
Нет новых зависимостей, настроек, таблиц, миграций или получателей.

## Что реализовано

`load_result_view_source()` читает одну согласованную цепочку существующих
Meeting/MediaRevision/UploadSession/ProcessingWorkflow/ProcessingResult с тремя
совпадающими сохранёнными audit-событиями. Проверяет точного владельца,
workspace/meeting/revision/result, новое создание/приём после переданного
начала, серверные времена, завершение загрузки, immutable source fingerprint
и deletion fences. Для готовности используется существующий
`complete_processing_result_clause()`, без второго определения готовности.
Штатный `status=imported` не считается миграцией. Исторический dual source
исключён. Неполная/противоречивая цепочка не достраивается.

NULL revision в обычных session_created/finalized разрешён только вместе с
совпадающей upload session. Отдельный media_revision_upload_session_created
требует точной revision. Finalized audit может предшествовать присвоению
finalized_at, как в настоящем ingest; требование обратного порядка не вводится.
Чтение использует populate_existing, поэтому старый ORM object после изменения
в другой сессии не становится доказательством. Это не замена locks T113.

Полная цепочка manual_upload даёт capture=false; для desktop-derived источника
свойство остаётся неизвестным. Время старого разговора не исключает новую
загрузку. Этот факт не определяет внешний статус аккаунта, действующий доступ
или фактический показ. Значение started_at должен дать только принятый T113;
параметр функции не создаёт разрешение или новую дату начала периода.

Краткое подтверждение — HMAC-SHA256 существующим переданным CSRF secret с
отдельным signing domain f273-result-view-v1. Оно связывает owner/workspace,
auth session/device, meeting/revision/source, result/version, deletion epoch,
тип/digest блока и outcome set. Срок10 минут, ограничение1536bytes, состояния
valid/expired/invalid. Нет неизвестных полей, подмены подписи или привязки;
полезная нагрузка сравнивается с точным ожидаемым каноническим представлением.
Expired не принимает событие и не обновляется автоматически. Текст, заголовок,
URL и auth credential в подтверждение не включаются. Код ничего не сохраняет,
не журналирует и не передаёт получателям.

## Причинные проверки

- Перед стендом проверено место:171687584KiB доступно, выше требуемого запаса80GB.
- Начальный DB RED:34 failed/1 warning — новый модуль ещё отсутствовал;
  реальные синтетические строки и audit были сохранены в PostgreSQL.
- Начальный unit RED:12 прежних passed/22 новых setup errors — тот же
  отсутствующий модуль. Это проверка отсутствия реализации, не поведенческий
  RED старого производственного trigger, которого по-прежнему нет.
- После первого кода34 unit и34 DB прошли. Дополнительный поведенческий RED
  на неполной обработке дал4 failed: недоступные transcript/diarization и
  нулевые segment counts ошибочно проходили. Подключён общий критерий продукта.
- Итоговый общий профиль:137 passed/1 warning,90.60s; runner95s, EXIT0,
  без skips. Содержит34 unit,38 DB source cases и существующие ingress/ledger/
  delivery проверки. Коллекция137,
  digest `f68fcea6adaf990e39725ea9400c259d941f1286028dcaed1f39bfa79d59af9a`.
- DB cases включают настоящее изменение deletion_epoch в другой сессии после
  первого чтения; старый source отвергается. В каждой source-проверке число
  ProductActivationMilestone остаётся0. Это не конкурентный POST/admission тест.
- Runner сообщил isolated_container_removed после каждого запуска.
  Только синтетические данные и фиктивные получатели существующих тестов.
- Ruff трёх Python-файлов и git diff --check: PASS.
- Warning: уже импортированный fixture-модуль PostgreSQL, как в предыдущем
  профиле; не пропуск и не ошибка нового кода.

Итоговая команда из корня:

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
/opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_result_visibility.py tests/contract/test_result_visibility.py \
  tests/contract/test_activation_milestone_ingress.py \
  tests/contract/test_activation_milestone_ledger.py \
  tests/contract/test_activation_milestone_delivery.py -q --tb=short
```

Результат взят из завершившегося процесса исполнителя, session61404;
это сводка наблюдённого вывода, не сохранённый полный stdout и не независимый
повтор тестов reviewer. Локальная проверка не является exact-SHA GitHub gate.

| Код/тест | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/cabinet/result_visibility.py | aed1b4172995ce5619d9c9506a537db074679a51ac1e8a2135c3034f81b11d88 |
| apps/server/tests/unit/test_result_visibility.py | eea528f87f2ed95dd92c5b3eba55cc71a02c518c7e6951467d323883df5d36bc |
| apps/server/tests/contract/test_result_visibility.py | 27bd0f0876bc2fbc43a50165abd354d57629309aebce350fb2d35e3643f321ff |

## Что ещё обязательно

Не реализованы общий render/projection/digest конкретных непустых блоков,
передача proof в DOM, browser/native visibility, защищённый POST и атомарная
пара через настоящую общую T113 admission с request/lock/statement budgets.
Нельзя подставить произвольный started_at, доверенный client flag или записать
вехи напрямую из этого модуля. Настоящие recovery/readiness/access/session/
resource/legal guards и trigger_unverified в обычном client ingest сохраняются.
Сейчас нет новых INSERT, provider calls или рабочего writer.

Независимое [ревью этого шага](t112-source-proof-review-20261116.md) завершено:
PASS в пределах source/proof, P1/P2=0. Три входных хеша совпали с проверенными;
тесты reviewer независимо не повторял. Ещё нужны полная оставшаяся реализация, причинная
browser/Swift/concurrency/failure матрица, converge и точные PR/release gates.
Это не RLS-приёмка нового endpoint, не полный end-to-end, не приёмка restore,
не рабочее local_only и не T0. T112/T113/#7698, измерение и коммерческие AC
остаются открытыми. Контент/вёрстка и рабочие службы не менялись.
