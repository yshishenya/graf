# Quickstart: Полноценные итоги встреч

## 1. Предварительная проверка

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
speckit-bootstrap . --doctor --frozen
```

Ожидается active feature `239-full-meeting-minutes` и отсутствие незакрытых
Spec Kit gate.

## 2. Схема и prompt

Каждый блок команд запускается из корня checkout, не вслед за `cd` предыдущего
блока. Окружение соответствует CI: Python >=3.13, `uv --extra dev`, PYTHONPATH
указывает на текущую ветку. Integration/RLS выполняются из отдельного
PostgreSQL runner ниже, никогда не против production DSN.

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest tests/unit/test_outcome_prompts.py tests/unit/test_meeting_outcomes_generator.py -q
PYTHONPATH=src uv run --extra dev pytest tests/unit/test_prompt_bundle.py tests/unit/test_prompt_optimization.py -q
PYTHONPATH=src uv run --extra dev pytest tests/unit/test_litellm_gateway.py -q
```

Проверить nested schema, exact refs, multi-segment statements, decision/action
границы, отдельные owner/due refs, prompt injection и root-bundle binding.
Для config 5 проверить разные модели/параметры из exact Langfuse versions,
отсутствие defaults, сохранность настроек при sync текста и отказ до записи
при неизвестных/отсутствующих настройках. Root v3/export v2 не требуют route
descriptor или специальных заголовков. После export/load HTTP request,
attempt metadata и generator hash сохраняют настройки точно. Подмена/пропуск
параметра даже с пересчитанным request hash запрещают публикацию; workflow
replay не повторяет inference. Nullable actual provenance сверяется с raw
response; честно сообщённая другая модель не отклоняется по старому allowlist.

## 3. Хранение и lifecycle

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_meeting_outcomes_migrations.py tests/integration/test_meeting_outcomes_generation.py tests/integration/test_outcome_generation_workflow.py tests/unit/test_trusted_outcome_publication_boundary.py tests/integration/test_meeting_outcomes_deletion.py tests/contract/test_rls_access_outcomes.py
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_meeting_protocol_generation.py tests/integration/test_meeting_protocol_generation_fences.py
```

Ожидается один protocol document, отдельная logical call каждой стадии, immutable acceptance,
fail-closed stale/deletion и отсутствие active flat fallback.

## 4. Интерфейс, share и export

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/unit/test_meeting_outcomes_view_models.py tests/integration/test_cabinet_meeting_outcomes.py tests/unit/test_transcript_exports.py tests/integration/test_transcript_export_egress.py tests/integration/test_recording_share_public_link.py tests/contract/test_cabinet_playback_contract.py
```

Проверить полную иерархию, таймкод рядом с тезисом, seek/focus, task table,
empty states, нормальную пунктуацию и accepted-only parity.

Реальный PostgreSQL/RLS, из корня:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_meeting_outcomes_migrations.py tests/integration/test_meeting_outcomes_deletion.py tests/integration/test_meeting_summary_slots.py tests/integration/test_rls_meeting_content_policies.py tests/integration/test_rls_worker_context.py tests/integration/test_rls_application_boundaries.py
```

Browser matrix на synthetic local стенде: 1280×720 и 390×844; owner candidate,
accepted full viewer, summary-only, pinned share; Tab/Enter/Space, видимый фокус,
объявление перехода, exact segment и аудио seek при наличии аудио. Отдельно
source deep-link после login, отсутствие transcript/audio прав, старая ревизия,
удаление и переименование спикера. Переполнение по горизонтали — 0; таблица
остаётся читаемой. Для XLSX/JSON/TXT/MD проверяются все разрешённые scopes и
include_evidence=false на каждой вложенной ветке. HTML assertions не заменяют
проверку действий в браузере; частные production screenshots не создаются.

## 5. Закрытая проверка выбранных встреч

Запуск выполняется только в разрешённом приватном контуре. Пользователь
разрешил оценить все осмысленные встречи доступной базы в рамках Feature 239;
это не разрешение на отправку вне согласованного gateway. Последнее указание
владельца ограничивает задачу готовым проверенным PR. Merge, release, deploy,
production labels здесь запрещены; общий выпуск выполняется отдельной задачей.
Уточнение владельца от 2026-09-07 сокращает обязательную приёмку: три разные
реальные встречи, одна длительностью ≥3600 секунд, и семь controls. Выборка
закрепляется до первого egress; полный inventory сохраняется отдельно.
Полный режим доступен для дополнительной проверки, но не задерживает этот PR.
Дополнительным прямым указанием от 2026-09-06 владелец разрешил удалить только
специальный ограничитель ГРАФ в production LiteLLM. Ключи, маршруты и общие
guardrails не меняются. Прежние ответные метаданные для старого ГРАФ могут
сохраниться до общего выпуска, но не должны блокировать запросы или модели.

Границы выполнения:

1. Источник — production GRAF через read-only соединение. Инвентаризация
   перечисляет все встречи без LIMIT выборки. Для каждой выбирается текущая
   принятая source revision через существующий latest_processing_result_query,
   а не только максимальный result_version (номер может повторяться между jobs).
2. Отдельная база и отдельная очередь Temporal для оценки на инфраструктуре
   владельца; worker не имеет production write DSN, не слушает production
   очередь и не публикует accepted slots. Не копируются пользователи, пароли,
   токены, аудио, подписанные ссылки и чужие таблицы. Для ledger достаточно
   служебных workspace identity и непрозрачных meeting/candidate correlations.
3. Точный numeric candidate root/children создаются в разрешённом private
   Langfuse EU. Только корневой комплект MAY получить `dev`: перед всем прогоном
   эта метка однократно разрешается в exact numeric root и фиксируется вместе
   с run id. Перезапуск читает закреплённую версию, не текущую `dev`. Без неё
   разрешён прямой выбор exact numeric root. Дочерние метки не читаются,
   production и его сохранённый комплект не используются как запасной тестовый
   путь. Модель и параметры каждой стадии берутся из exact
   Langfuse config, без runtime override. Пользователь разрешил сравнение
   моделей, включая Gemini, через существующий gateway; назначение данных
   и retention остаются в разрешённом оператором контуре. Обычный worker не
   получает ключ мутации label. Если действующий hook ещё запрещает запрос,
   фиксируется блокировка — не используется другой ключ/прямой endpoint.
   Полные тексты уходят только в этот существующий разрешённый AI-контур.
   До первого вызова сохраняется immutable run-owned snapshot полного root
   export/Activation и EvaluationAuthority, без Qualification/production-журнала.
   Проверить запуск до существования любой операторской строки и отказ при
   подмене этого снимка. Qualification получает отчёт только прямым вызовом
   finalize_run: повторная инвентаризация, все reviews/output/call bindings,
   фиксированные controls из contracts и privacy PASS. Чужой/изменённый JSON
   отчёта с пересчитанным хешем не разрешает root. Финальный metadata-only
   отчёт сохраняется в операторской строке после очистки временных заметок.
4. Evaluation Generation Call и Temporal сохраняют полный transcript,
   request/response/result; private Langfuse observations используют evaluation
   environment, не public trace. Эти observability copies сохраняются по
   действующей политике оператора и не удаляются при удалении встречи.
5. Рабочие заметки содержательной проверки живут только в закрытом каталоге
   владельца с правами 0700/0600, вне checkout и без публичных URL. Каждая
   заметка связана с run id, meeting id, source hash, root hash, output hash,
   reviewer и всеми критериями FR-029. В ordinary stdout/logs идут только
   counts, hashes, machine codes — не тексты или цитаты.
6. Перед чтением, перед egress и перед учётом PASS повторно проверяются доступ,
   source/deletion epoch. Удалённый или отозванный источник прекращает обработку
   и инвалидирует оценку; рабочая копия и заметки удаляются. После завершения
   PR рабочие заметки/временные входы удаляются; retained ledger/observability
   остаются по указанной политике. Без этих границ запуск запрещён.
7. Начать с concurrency=1. Временная ошибка не исключает встречу из корпуса;
   незавершённые, ambiguous и существенные quality-fail строки выбранного
   объёма блокируют PASS. Стилистика и повторы сами по себе не блокируют.
8. Сквозной прогон создаёт попытку обычным HTTP `summaries/{template_key}/ensure`
   с синтетической сессией и CSRF после копирования только источника в отдельную
   базу. До запуска выделенного worker попытка получает evaluation/source binding.
   Затем штатные dispatch, Temporal, три стадии, ledger и GET состояния кандидата работают
   без подмены модели или проверки. Отдельно проверяются 403 без CSRF, 202 при
   создании, 200 и `private, no-store` при чтении состояния, неизменность accepted slot.
   Это не проверка принятого результата, браузера или экспорта: они проходят
   отдельно на синтетических данных; evaluation-only запрет публикации не снимается.
9. Время HTTP ожидания по умолчанию — 900 секунд на модельный вызов. Бюджет
   generation activity рассчитывается как три таких ожидания плюс 120 секунд
   на проверки/хранение и записывается в результат resolve activity. На выпуске
   проверить фактическую transport config: явное значение окружения перекрывает
   default. Это не модельный параметр и не часть запроса в LiteLLM. После
   неопределённого завершения не повторять тот же вызов; новый сравнительный
   опыт имеет новую candidate/run identity и не считается восстановленным ответом.

В Git сохраняется только безопасный итог:

- число найденных встреч;
- число пригодных и исключённых;
- scope `representative`, размер выбранной выборки и число непроверенных;
- количества по типам;
- количества pass/fail по критериям FR-029;
- причины исключений и классы общих ошибок без текста, имён и цитат.

Для каждой выбранной встречи Codex сначала составляет независимый перечень существенных тем, аргументов,
решений, обязательств и поздних поправок только по transcript, затем сравнивает
с output. В приватной строке оценки обязательны все поля FR-029 с pass/fail,
пропусками/ошибками и source references; пустая либо неполная оценка не PASS.
Partial/degraded source с осмысленным содержанием включается с описанием
границ достоверности; нельзя признать пропущенную часть «не обсуждалась».
Codex проверяет все refs и заполняет приватную рабочую оценку. Смысловая пригодность
определяется чтением, не минимальным числом символов: хотя бы один предметный
обмен, аргумент, факт, решение или обязательство; короткая встреча не
исключается автоматически. Дубликаты встреч не исключаются по сходству текста.
Неразборчивая речь, пустой/отсутствующий transcript и удаление/отзыв доступа
фиксируются отдельно; технический сбой генерации не является непригодностью.
После последней общей правки весь выбранный объём генерируется повторно и каждая полная
расшифровка с новым результатом перечитывается по всем критериям FR-029.
Перед финальным отчётом инвентаризация повторяется; новые пригодные встречи
учитываются как непроверенные; изменение выбранного источника блокирует
приёмку, а не разрешает молча заменить его. Дата среза фиксируется.

Gate считается пройденным только при SC-001..SC-013 для закреплённого объёма.
Незаконченная выборка или автоматический judge без полного прочтения не
считается приёмкой. Завершённая выборка не доказывает качество всего корпуса.

### Трёхстадийный регрессионный срез

В существующих generation/fences/eval-workflow/publication тестах проверить
полную цепочку extraction → synthesis → verification. Точные разные модели
и параметры приходят из Langfuse; весь transcript есть во всех трёх calls и
Temporal History, extraction только в запросе синтеза, draft только в verifier.
Отсутствующая/подменённая/повторная стадия, неверные refs, изменённый predecessor
даже с новыми локальными hashes блокируют публикацию. Replay completed calls
не повторяет inference; ambiguous каждой стадии останавливает последующие.
Повторить source/access/deletion гонки и retained observations для всех стадий.

Синтетические содержательные сценарии: отдельное поручение в последней реплике,
принятая задача со сроком в разговорно смягчённой форме (задача и срок остаются
подтверждёнными), настоящее условное обязательство, поздний выбор,
отмена и переназначение. Они проверяются реальными модельными ответами в новом
root, а не только утверждениями о тексте prompt. Сначала контрольная и другая
содержательная встреча через HTTP; после стабилизации выборка по FR-028.
Старые root19–22 не считаются доказательством качества нового pipeline.

Отдельная отрицательная пара к разговорному согласию: догадка о чужом сроке
или прямой отказ не становится обещанием. После уточнения владельца прежняя
диагностическая оценка оговорки сама по себе не является ошибкой. Остальные
пропуски/неподтверждённые утверждения не прощаются и старый FAIL не превращается
в PASS без нового полного чтения и генерации.

## 6. Closeout

После удаления model lock прогнать тесты всех вызывающих путей, включая
optimizer, CLI sync, root/export/load, publication/replay и retained observer.
Поиск runtime/config/tests не должен находить старый descriptor, callback,
`require_route_binding` и `X-GRAF-*`. Исторические release evidence не
переписываются. Безопасный будущий порядок активации указан в contracts;
локальный diff не считается снятием ограничения в production. Разрешённое
удаление pre-call ограничителя LiteLLM проверяется реальными синтетическими
запросами разных моделей тем же ключом без специального заголовка. Проверить
также старый клиент и неизменность ключей, маршрутов и общих guardrails.
Любой оставшийся отказ фиксируется отдельно; предварительный deploy ГРАФ
и подмена реальных проверок mock по-прежнему запрещены.

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

После `speckit-converge` зафиксировать exact HEAD, обновить PR metadata и
дождаться `governance-fast` на том же SHA. Проверка PR сама по себе не разрешает
deploy или продвижение Langfuse production label. T058 учитывает техническую
зависимость без выпуска; T059 передаёт инструкцию активации в отдельную задачу
общего выпуска. Эта задача заканчивается PR после полной приёмки T043–T048,
без merge. Непройденный корпус явно блокирует статус «готово».
