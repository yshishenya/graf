# Validation: F275

Lane: high-risk-feature. Production deployment не входит.

1. В apps/server: uv sync --frozen --extra dev. Тестовая Postgres — существующий local fixture, не production.
2. Ruff и pytest: MediaScribe contract/request mapping/submit/happy path/worker restart; ingest/finalize; manual upload normalization; reprocessing; deletion/retention. После shared-fixture изменений выполнить server regression и записать точную выборку.
3. swift test --package-path apps/macos: DesktopUpload, CanonicalRecordingManifest, RecordingDeletion; полная suite и ContractValidation по доступности. Приложение запускается только как /Applications/GRAF Dev.app через dev-harness; swift run запрещён.
4. Synthetic create_test_artifact: валидные WAV/M4A/v5 manifest; upload MockTransport без живого провайдера; seed выбирает правильный media artifact.
5. rg по submit_dual_track, dual_track, dual-track, mic_file, incoming_file, initial_recording и именам двух файлов. Классифицировать migrations/read/delete/fingerprint/negative tests; доступных producers/senders нет.
6. Независимый review, speckit-converge, git diff --check; PR governance-fast/macos-pr/pr-metadata на точном SHA; release-full только в отдельном выпуске.

## Evidence

Промежуточные результаты (2026-09-24); итоговая проверка реализации ещё идёт.
Недоступное доказательство не считается PASS.

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
