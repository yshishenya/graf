# Validation: F275

Lane: high-risk-feature. Production deployment не входит.

1. В apps/server: uv sync --frozen --extra dev. Тестовая Postgres — существующий local fixture, не production.
2. Ruff и pytest: MediaScribe contract/request mapping/submit/happy path/worker restart; ingest/finalize; manual upload normalization; reprocessing; deletion/retention. После shared-fixture изменений выполнить server regression и записать точную выборку.
3. swift test --package-path apps/macos: DesktopUpload, CanonicalRecordingManifest, RecordingDeletion; полная suite и ContractValidation по доступности. Приложение запускается только как /Applications/GRAF Dev.app через dev-harness; swift run запрещён.
4. Synthetic create_test_artifact: валидные WAV/M4A/v5 manifest; upload MockTransport без живого провайдера; seed выбирает правильный media artifact.
5. rg по submit_dual_track, dual_track, dual-track, mic_file, incoming_file, initial_recording и именам двух файлов. Классифицировать migrations/read/delete/fingerprint/negative tests; доступных producers/senders нет.
6. Независимый review, speckit-converge, git diff --check; PR governance-fast/macos-pr/pr-metadata на точном SHA; release-full только в отдельном выпуске.

## Evidence

### Дополнительные замечания перед выпуском — 2026-09-24

После прежнего PASS автоматическое ревью PR выявило два дополнительных
сценария. Независимый рецензент подтвердил оба: workflow без ревизии и без
известного внешнего ID не получал причину неподдерживаемого источника;
историческое доказательство финализации ошибочно давало этапу `ready`.
В рамках T003/T007 добавлена остановка до новых запросов и резервирования,
с сохранением исключения для известного ID; этап готовности теперь `degraded`
с явным пробелом актуального подтверждения. Требования и границы не меняются.

Регрессии сначала воспроизвели дефекты: 5 failed, 47 passed. После исправления
расширенный набор — **81 passed**, 10 warnings, 41.76 s, exit 0:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned -q \
  tests/integration/test_retired_processing_source.py \
  tests/unit/test_single_source_retirement.py \
  tests/unit/test_mvp_loop_readiness_matrix.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/contract/test_mvp_loop_readiness_contract.py \
  tests/unit/test_mvp_launch_proof_readiness.py \
  tests/unit/test_mvp_owner_journey_readiness.py
```

Ruff и diff-check проходят. Прежние полные результаты ниже относятся только
к прежнему code SHA и не присваиваются этому исправлению: обязательные PR
проверки и полная проверка кандидата выпуска должны пройти на новых SHA.

Дополнительно новые pickup-сценарии проверяют освобождение существующего
резервирования по ключу встречи при отсутствующей ревизии. Та же команда
для `tests/integration/test_retired_processing_source.py -k revisionless`:
**3 passed**, 10 warnings, 10.33 s, exit 0. Runtime correction зафиксирована
в `b1b3ccdb2a0641e4f6bd4748eac386f7e394e8a8`, полные исходники и тесты —
`f431e8076d0bd5381dcfcdff97ca3a1bc9d25449`.
Повторный converge: 8 FR, 4 SC, 8 сценариев приёмки, 4 граничных случая,
6 решений плана и 7 принципов конституции; новых реализационных пробелов 0.
`tasks.md` не изменялся. Отсутствующее живое доказательство финализации честно
обозначено в readiness и не заменяется синтетическими проверками.

Соседняя pickup/restart-регрессия выявила неверную классификацию нового draft
без ревизии: 1 failed, 42 passed. Вызов retirement в pickup ограничен
существующим источником, исторической обработкой или принятым состоянием
встречи; отказ по недопустимому состоянию не делает новый draft историческим
даже при повторном обращении. Остальные пути retirement не ослаблены.
Совместный набор выше плюс `test_processing_pickup.py`,
`test_processing_pickup_blockers.py`, `test_processing_worker_restart.py`:
**124 passed**, 10 warnings, 40.91 s, exit 0. Collection digest
`8e6c9e762770c49da4e9fad22d52b09bce4dd315161addc18944fcdb090b0e2a`.
Это адресная регрессия текущего кода, не полный выпускной CI.

Результаты на 2026-09-24. Локальная проверка завершена; обязательные проверки
GitHub для итогового коммита проверяются отдельно. Недоступное доказательство
не считается PASS.

### Итоговый полный серверный прогон

Code SHA: `ee9533b28166d142fd1186d24ad303b2e89cc7be`. После фиксации исходники
и тесты не менялись. Из корня рабочей копии:

```sh
GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh --full -q
```

PASS, exit 0: **5511 passed, 1 skipped**, collection 5512;
digest `00bca9ba64c85df116a80006a6a4201976c5befeacf0cf42103e4fa2529b2ee7`.
Этапы: strict 69 passed / 37 s; performance 2 passed / 15 s; parallel
5440 passed, 1 skipped / 537 s (pytest 532.63 s). Изолированный контейнер
PostgreSQL штатно удалён. Предупреждения зависимостей и существующего порядка
FK не являются ошибками. Необязательная проверка разрешённой пользователем
реальной записи пропущена: `GRAF_TEST_REC_DIR` не задан. Синтетические проверки
настоящего декодирования FFmpeg выполнены; пропуск не выдаётся за успешный тест.

Ниже сохранены результаты отдельных этапов; они пересекаются с полным набором.

### Независимая проверка и PR

Окончательная независимая проверка кода — PASS, C1/C2 закрыты, открытых находок
нет; отчёт — `implementation-review.md`. После code SHA изменяются только
материалы F275, а не исходники/тесты.

PR: https://github.com/yshishenya/graf/pull/7267. Первый `governance-fast`
остановился на отсутствующем формальном разделе Legacy Impact; раздел добавлен
без изменения требований, `check-development-process.py` теперь PASS.
Первое описание PR также дополнено F012: там хранится действующий OpenAPI.
`pr-metadata` и `macos-pr` на code SHA прошли. Проверки итогового PR SHA должны
пройти заново; до этого слияние запрещено. Их актуальные результаты и проверка
`scripts/validate-pr-checks.py` фиксируются в PR, без подмены старым SHA.
Отметка T008 означает завершённую реализацию, локальные испытания и независимую
проверку; она не заменяет отдельный запрет слияния до актуальных GitHub gates.

- T001: независимый review требований и задач — 12/12, замечания R1/R2 закрыты
  рецензентом в review-report.md; analyze — 0 critical/high, все 8 FR покрыты.
- T002: Ruff, helper contracts (роли/размеры/SHA/WAV), `git diff --check` — PASS;
  `test_media_revision_state_machine.py` — 3 passed.
- `check_spec_kit_governance.py`, `validate-changelog-fragments.py` — PASS.
- Точное сравнение `create_app(Settings()).openapi()` с активным YAML — PASS.
- Промежуточный server fast: 2074 pure и 150 DB проверок прошли; браузерная
  проверка не стартовала без локальной зависимости. Выполнены `npm ci` в
  `apps/server/tests/browser` и `npx playwright install chromium`; нужен повтор.
  Более раннее ожидание старого schema head обновлено до новой миграции.
- Первый диагностический полный server run на изменявшемся рабочем дереве:
  strict 69 passed; performance 2 passed; parallel 5419 passed, 14 failed,
  1 skipped. Он не считается PASS. Исправлены старые ожидания ролей в общих
  тестовых данных, текст сообщения, объявление revision двух новых миграций,
  ссылки на переименованный тест и ожидаемые поля single-source запроса.
  Часть ошибок совпала с изменением схемы/OpenAPI во время запуска.
- Повторная выборка copy convention, retention/deletion, OpenAPI, ingest
  contract и PostgreSQL migrations: 102 passed, 10 warnings, 33.71 s, exit 0.
  Команда: `bash apps/server/scripts/run_local_postgres_tests.sh --focused --partitioned -q tests/contract/test_copy_convention_contract.py tests/contract/test_retention_deletion_contract.py tests/contract/test_openapi_contract_drift.py tests/contract/test_ingest_openapi_contract.py tests/integration/test_postgres_migrations.py`.
  Collection digest: `fff07edeed6125ee73359e6a56a4106664d37b09ce8ae6926058619e19200c5b`.
- T003: расширенная выборка 339 passed, включая historical known-ID
  poll/import/delete; часовой single-source сценарий — отдельный 1 passed.
- Финальный `test_retired_processing_source.py`: 30 passed. C1 проверяет
  невозобновляемый известный ID без источника (3 случая), C2 — освобождение
  существующего резервирования 60 секунд с повторным чтением PostgreSQL.
- T004: ingest/recording_sync выборка 161 passed; ограниченная схема и admission
  19 passed. Пересекающиеся проверки не суммируются.
- `speckit-converge`: 8 FR, 4 SC, 8 acceptance scenarios, 4 edge cases,
  6 решений плана и 7 принципов конституции проверены. Реализационных пробелов
  missing/partial/contradicts/unrequested — 0; задач не добавлено. Окончательные
  validation/review/PR gates остаются в T008, это не разрешение на выпуск.
- Исправления playback route — 17 passed; media-tools/copy/missing retained
  source — 9 passed; audit persistence — 3 passed. Эти выборки пересекаются
  с общей регрессией и не суммируются как уникальные тесты.

### T005: macOS

Из корня рабочей копии:

```sh
swift test --package-path apps/macos -j 4 --disable-swift-testing
swift build --package-path apps/macos -j 4 --product ContractValidation
apps/macos/.build/arm64-apple-macosx/debug/ContractValidation
```

Полный XCTest: 1052 теста, 2 пропуска необязательных снимков интерфейса,
0 ошибок, 122.571 s, exit 0. ContractValidation: PASS, build/run exit 0.
Целевая выборка очереди и загрузки: 237 passed. Проверочная утилита не является
приложением; `swift run` и отдельные копии GRAF не использовались.

### T006: пакет и служебные сценарии

Из apps/server:

```sh
bash scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_smoke_outcome_seed.py \
  tests/unit/test_smoke_package.py \
  tests/integration/test_upload_helper_contract.py \
  tests/integration/test_production_smoke_boundary.py \
  tests/integration/test_rls_smoke_cleanup_context.py \
  tests/unit/test_smoke_cleanup.py \
  tests/unit/test_smoke_identity_seed.py \
  tests/contract/test_smoke_evidence_contract.py
```

101 passed, 2 warnings, pytest 25.14 s; exit 0. Collection digest:
`33d7a2e8464471476546e82d870ca6c38776fda8af3350c15b0d705df815aafb`.
Ruff, formatting check, `bash -n`, `git diff --check` — PASS. Проверено реальное
декодирование синтетического AAC, приём пакета действующим локальным API,
повреждение/усечение/дубли/ссылки/размеры и cleanup. Production-контейнеры и
живой MediaScribe в этой проверке не использовались.

## Восстановление установленного Dev (не доказательство F275)

По прямому указанию пользователя восстановлен `/Applications/GRAF Dev.app`
через `dev-harness promote --live` неизменного active manifest
`dev-3cae818cf57a` из чистой копии точного SHA
`3cae818cf57ad24ab4b58c5bafd2d0cb8b1df600`. Все 13 штатных smoke checks — PASS;
установка и запуск успешны. Подпись, bundle ID, данные и разрешения сохранены.

Первая попытка безопасно остановилась из-за различного представления времени
старта управляющего процесса после смены часового пояса. Сверены точная команда
и абсолютное время `started_at`; повтор с исходным UTC+5 прошёл. Проверки
владения процессом и runtime metadata не подменялись. Эта установленная версия
предшествует F275 и не служит доказательством работы нового кода.

## Установка F275 в единственный GRAF Dev

Код зафиксирован в `ee9533b28166d142fd1186d24ad303b2e89cc7be`.
Из чистой рабочей копии выполнены `dev-harness.sh build --sha <этот SHA>
--feature-id 275 --live` и `promote --manifest <manifest этого SHA>
--previous-checkout <чистая копия прежнего SHA> --live` с исходным UTC+5.
Это штатный переход Dev с 0097 на 0099; пользовательские данные не сбрасывались.

Установлен и запущен `/Applications/GRAF Dev.app`, активный manifest
`dev-ee9533b28166`, migration head `0099_single_source_revision`.
Все 13 настоящих проверок штатного механизма — PASS: подпись/идентичность,
представление приложения, точный SHA, API, кабинет, вход, БД, хранилище,
миграции, Temporal и оба обработчика. Повторный `status --json` подтверждает
`active` и `app.installed=true`. В интерфейсе видны «GRAF Dev», «Готово к записи»
и «Микрофон и системный звук готовы»; запись без участия пользователя не начиналась.

MediaScribe в базовом локальном стенде не настроен. Эти результаты подтверждают
установку и работу компонентов, но не живую расшифровку внешним провайдером.
Отправка/получение результата проверены изолированными автоматическими тестами
с синтетическими данными. Рабочий сервер не обновлялся.
