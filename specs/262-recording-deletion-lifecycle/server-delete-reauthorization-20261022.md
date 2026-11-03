# F262 T006/#6881: повторное серверное удаление и текущие права

Дата: 2026-10-22. Основа: `9b12f0b1f34a8dc0b294d8e500f9a7a14f9fe4a8`.
Ветка: `codex/262-server-delete-reauthorization`.
Дорожка: действующий срез Spec Kit, удаление и авторизация.

## Результат

Серверная реализация T006 из слитого PR #6911 повторно проверена по исходным
критериям. Усилен существующий PostgreSQL integration-тест: управляющий,
отличающийся от создателя записи, повторяет удаление после смены сессии и
создания нового приложения/соединения с БД. Проверяются JSON, обычная HTML-форма
и HTMX, оба адреса кабинета, доступ к отчёту до и после отзыва роли.
Рабочий код не меняется: текущий общий resolver уже проверяет актуальные права.

Повтор возвращает прежние request_id/epoch и не создаёт новых request/report/audit;
обычная форма сохраняет 303, HTMX — пустой HTML 202 с Vary. После отзыва прав обе
действующие сессии получают 404 для удалённой и существующей встречи и отчёта,
без раскрытия прежнего подтверждения и без изменения данных.

## Проверки

В существующем изолированном PostgreSQL окружении выполнены два непересекающихся
набора, **39 разных проверок PASS, 0 FAIL, 0 SKIP**:

1. `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_recording_deletion_scope_acceptance.py tests/integration/test_cabinet_hx_delete_feedback.py tests/integration/test_cabinet_csrf.py` — 23 PASS.
2. `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_deletion_lifecycle_blocks_access.py tests/integration/test_recording_workflow_deletion_races.py tests/contract/test_retention_deletion_contract.py tests/contract/test_deletion_no_secret_leakage.py tests/unit/test_deletion_report_view_models.py` — 16 PASS.

Журналы внешнего аудита: `f262-t006-web-reauthorization-corrected-20261022.log`
и `f262-t006-contract-content-20261022.log`. Оба запуска подтвердили штатное удаление
своего временного контейнера. Синтетические данные; пользовательские записи не затронуты.
Проверки охватывают конкурирующее удаление, отмену origin, блокировку чтения,
повтор после рестарта, текущие права, типизированный ответ и ограниченность отчёта.

Manager-тест использует настоящий X-Auth-Session, а не браузерную cookie-сессию;
CSRF отдельно проверяется существующим набором `test_cabinet_csrf.py` и настоящей
формой владельца. Перезапуск TestClient/engine — проверка серверного состояния,
не запуск установленного GRAF.

## Сходимость и границы

FR-002/004/008/009/019, T006 и применимые серверные части S01/S05/S06/S28/S49
сопоставлены с исходниками и профильными проверками. Неизвестное состояние и
отказ в доступе не выдаются за удаление; принятый результат не отменяется
устаревшим повтором. Другой обязательной runtime-правки для T006 не найдено.

Установленная матрица всей F262, локальная физическая очистка, T018, T021,
новый выпуск и production отдельно не принимаются. Для слияния нужны независимое
ревью и три обязательные GitHub проверки точного SHA/основы. Закрытие #6881
возможно только после merge, подробного комментария и `--verify-live` проверки.
Истёкший артефакт старого PR #6911 новым локальным запуском не восстанавливается.

Legacy Impact: `untouched`; новые alias/fallback/flag/dependency не добавлены.
Форматы и правила доступа не изменены; legacy_new=0, unowned_legacy=0,
expired_exceptions=0.
