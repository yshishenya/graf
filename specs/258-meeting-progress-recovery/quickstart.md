# Проверка F258

## Условия

Только synthetic данные. Installed QA в `/Applications/GRAF Dev.app` через harness; status и владелец стенда перед promote. Фиксировать exact SHA и PASS/FAIL/SKIPPED отдельно. Production и частную встречу не менять.

## Автоматические проверки

1. `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_processing_status_contract.py tests/contract/test_summary_template_ui_contract.py tests/contract/test_playback_status_contract.py tests/integration/test_meeting_summary_slots.py -q`
2. Node поведенческие проверки pending→available/partial, >5min, transient→online, hidden→visible, stale response, selected format, title/player preservation; точные новые файлы/команды в evidence после реализации.
3. `swift test --package-path apps/macos/Shared --filter DesktopNotificationControlTests`; дополнительно queue/model/web boundary tests, затем весь пакет в fast gate.
4. Настоящая media role: только нужные workflow metadata своей scope, без DML/чужих строк.
5. `git diff --check`, focused lint, GitHub governance-fast exact PR SHA. Local fast только diagnostic/fallback; Full CI на отдельном будущем release candidate.

## Сценарная приёмка

- US1: page/list до ingest; audio ready при пустом slot; transcript ready при queued/generating/blocked/failed/accepted/partial summary без reload. No archive и повреждённый файл различаются.
- Web/WKWebView: выбранный формат, refresh >5min/40 polls, offline→online, sleep/возврат, title draft, играющий player; GET не создаёт генерацию.
- US2: ask/always/never, failed start, confirmed start/Stop, закрытое окно/WKWebView отсутствует, denied/allowed/Focus; настоящий banner отдельно от center.add.
- US3: две записи, чужой primary, >5 групп, retention expiry, failure→recovery→failure, retry без дубля, visible related/unrelated; unknown owner/logout/scope не раскрывают запись.
- Клавиатура/фокус, 200%, темы, постоянный Stop, тихие notifications при capture. Audio pipeline не меняется: lifecycle tests обязательны; extended hardware performance отдельно и явно не PASS.

## Результат

После focused проверок авторизованный commit, Dev build/promote/status/smoke, исправления и новый exact SHA/PR. Установленный production GRAF и сервер не меняются. Пропущенные аппаратные сценарии остаются открытыми.
