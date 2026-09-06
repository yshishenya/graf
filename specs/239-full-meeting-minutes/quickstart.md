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

## 5. Закрытая проверка всех встреч

Запуск выполняется только в разрешённом приватном контуре. Пользователь
разрешил оценить все осмысленные встречи доступной базы в рамках Feature 239;
это не разрешение на отправку вне согласованного gateway. Позднейшим указанием
разрешены отдельный технический выпуск снятия model lock и итоговый выпуск
протоколов после полной приёмки; оба проходят release-gates.

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
   Langfuse EU без label. Модель и параметры каждой стадии берутся из exact
   Langfuse config, без runtime override. Пользователь разрешил сравнение
   моделей, включая Gemini, через существующий gateway; назначение данных
   и retention остаются в разрешённом оператором контуре. Обычный worker не
   получает ключ мутации label. Если действующий hook ещё запрещает запрос,
   фиксируется блокировка — не используется другой ключ/прямой endpoint.
   Полные тексты уходят только в этот существующий разрешённый AI-контур.
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
   незавершённые, ambiguous и quality-fail строки блокируют общий PASS.

В Git сохраняется только безопасный итог:

- число найденных встреч;
- число пригодных и исключённых;
- количества по типам;
- количества pass/fail по критериям FR-029;
- причины исключений и классы общих ошибок без текста, имён и цитат.

Для каждой пригодной встречи Codex сначала составляет независимый перечень существенных тем, аргументов,
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
После последней общей правки весь corpus генерируется повторно и каждая полная
расшифровка с новым результатом перечитывается по всем критериям FR-029.
Перед финальным отчётом инвентаризация повторяется; новые пригодные встречи
включаются, изменённые source hashes пересчитываются. Дата среза фиксируется.

Gate считается пройденным только при SC-001..SC-013. Частичный corpus-run или
автоматический judge без полного прочтения не считается приёмкой.

## 6. Closeout

После удаления model lock прогнать тесты всех вызывающих путей, включая
optimizer, CLI sync, root/export/load, publication/replay и retained observer.
Поиск runtime/config/tests не должен находить старый descriptor, callback,
`require_route_binding` и `X-GRAF-*`. Исторические release evidence не
переписываются. Безопасный будущий порядок активации указан в contracts;
локальный diff не считается снятием ограничения в production. Предварительный
технический PR/релиз снимает ограничение до T043 и основного PR; до успешного
согласованного переключения реальная генерация через старый hook заблокирована.

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

После `speckit-converge` зафиксировать exact HEAD, обновить PR metadata и
дождаться `governance-fast` на том же SHA. Проверка PR сама по себе не разрешает
deploy или продвижение Langfuse production label: эти действия выполняются
только в разрешённых T058/T059 с отдельными release gates. T058 сохраняет
действующий outcome contract; T059 выпускает новые протоколы только после
полной приёмки T043–T048.
