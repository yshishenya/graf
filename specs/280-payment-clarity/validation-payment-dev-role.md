# F280 T034 — защищенная роль фонового обработчика в Dev

Дата: 2026-10-03. Task T034 / issue #7482 добавлены и синхронизированы root до изменения кода. Исполнитель владеет только Dev Compose, новым вспомогательным сценарием, двумя новыми адресными тестовыми файлами и этим отчетом. Режим significant/high-risk-product внутри FR-038/T030/T032; исходный guard, queue/workflow/activity history и production файлы не менялись. Root сохраняет владельца tasks/plan/contract/changelog. Требуется независимый source review `return_design` до closeout; автор этим отчетом не объявляет свой код независимо проверенным.

## Причина и изменение

Documented Dev `rec-maintenance` наследовал URL владельца БД `twobrain_rec`. Новый фактический guard правильно отклоняет такой superuser и останавливает весь maintenance service еще до календаря/уведомлений. Обход в development отключил бы защиту; вместо него настройка стенда исправлена.

- `infra/docker-compose.dev.yml`: rec-maintenance переопределяет URL точной защищенной ролью twobrain_rec_maintenance и ждет `rec-db-runtime-bootstrap` service_completed_successfully.
- Новый one-shot bootstrap использует тот же уже закрепляемый migration image; ждет завершения миграций и healthy PostgreSQL. Новой версии образа/компонента harness не добавлено. Прежние зависимости API/MinIO сохранены.
- `apps/server/scripts/bootstrap_dev_database_roles.py` требует TWOBRAIN_ENV=development, получает только синтетические пароли local stack, создает ограниченные600 временные файлы и вызывает неизмененный canonical `_bootstrap` из `bootstrap_runtime_database_roles.py`. Тем самым создаются/проверяются обычные app/maintenance/media роли с прежними ограниченными grants, membership guards и row_security. Файлы удаляются и переменные *_FILE восстанавливаются и при ошибке. Никакого development exemption, superuser/BYPASSRLS или копии SQL grants нет. CLI ошибки печатают только static fail, без пароля/URL/SQL traceback.

## Причинный RED до изменения Compose/helper

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_dev_maintenance_database_role.py
```

`graf-f280-payment-dev-role-red.log`:1FAILED/1PASSED,8.44s pytest/12s phase, isolated_container_removed. Тест берет username из прежнего actual Dev Compose, подключается им к отдельному мигрированному PostgreSQL и вызывает настоящий `verify_billing_maintenance_database`; отказ BillingMaintenanceDatabaseError «requires a protected maintenance database role». Контроль реального прежнего superuser тоже успешно подтверждает отказ. Это RED продукта/конфигурации, не missing import или недоступный Docker.

## Окончательный GREEN

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_dev_maintenance_database_role.py tests/contract/test_dev_maintenance_database_role.py
```

`graf-f280-payment-dev-role-complete-green.log`: **8PASSED**,8.21s pytest/12s phase,2 existing warnings, isolated_container_removed. Тесты используют свои отдельные PostgreSQL17 containers и настоящие миграции; installed GRAF Dev/его БД не запускаются и не читаются.

Покрытие: Compose resolved anchors/роль/порядок запуска/image/restart; отказ helper вне development до bootstrap; canonical helper delegation; временные600 files/cleanup и env restore при успехе и exception; настоящий login session_user=current_user=twobrain_rec_maintenance, row_security=on, rolsuper=false, rolbypassrls=false; startup billing guard PASS; повторный вызов bootstrap с тем же результатом; действующий rec_maintenance_allowed и реальный SELECT для календаря, уведомлений, удаления, генерации результатов и восстановления обработки; прежний superuser снова отклоняется.

Промежуточные прогоны не выдаются за GREEN: `payment-dev-role-green.log`2FAIL/6PASS от неверного размещения YAML блока; `payment-dev-role-final-green.log`1FAIL/7PASS от typo ключа теста rolsuper. Оба исправлены до окончательного8PASS. Итоговый git diff Dev Compose содержит только25 вставок, прежние зависимости API возвращены полностью. В отчет не копируются DSN/пароли даже отдельных одноразовых тестовых контейнеров.

## Дополнительные адресные проверки

- Настоящий `docker compose -f infra/docker-compose.dev.yml config --format json`, только parse без запуска: PASS. Разобранные значения подтвердили bootstrap deps={rec-migrate,rec-postgres}, maintenance→bootstrap completed, существующий migration image, прежние API storage deps. Metadata `graf-f280-payment-dev-role-compose.log`.
- `apps/server/.venv/bin/python -m pytest tests/governance/test_dev_harness.py -q`: **23PASS**,0.52s; metadata `graf-f280-payment-dev-role-harness-green.log`. Fixture harness, не реальная установка/переключение GRAF Dev.
- `uv run --directory apps/server --extra dev ruff check scripts/bootstrap_dev_database_roles.py tests/contract/test_dev_maintenance_database_role.py tests/integration/test_dev_maintenance_database_role.py`: PASS.
- py_compile нового helper и scoped git diff --check: PASS.

## Привязка к исходникам SHA256

| Файл | SHA256 |
|---|---|
| infra/docker-compose.dev.yml | 50c7f48f281927c28f08af36ce4b1e717e60fa4ad67c5fbe98103390b1ad0945 |
| apps/server/scripts/bootstrap_dev_database_roles.py | e1dca251cb64acf9368217d9de51bd494798f236b88a8711f5fc3e4fe0929f8e |
| apps/server/tests/contract/test_dev_maintenance_database_role.py | f8732ecb2e211276646c80ff42444d21bf2fe53863576c352fcfc902d5e3fbbc |
| apps/server/tests/integration/test_dev_maintenance_database_role.py | 5df39bb2ea1cf2df22ac76efa2e795edb4c1e4bc04f2949f99c6831072056e43 |

## Границы

Коммит не создан. Production и установленный GRAF Dev не менялись; подготовленные live probe scripts не изменялись этим заданием. Изменение Compose меняет runtime-definition digest: дальнейшее настоящее обновление установленного Dev должно пройти существующий штатный dev-harness cutover, не обход совместимости. Полный Docker Dev startup и promotion здесь не выполнялись и не объявляются проверенными. Exact-SHA CI/Full/CD, независимый review, release и postdeploy observation — отдельные gates root. Финансовая приемка F278/T011/T012, реальный чек/банк/возврат/recurring/конверсия этим Dev исправлением не закрываются.
