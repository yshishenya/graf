# F248: реализация и проверки

Дата: 2026-09-06. Ветка: `codex/248-trustworthy-account-sessions`.
Исходный HEAD: `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`.
Lane: high-risk-feature (авторизация, жизненный цикл сеансов, интерфейс).
Итоговый SHA и обязательный GitHub governance-fast фиксируются в PR. Это отчёт об изменениях, а не разрешение на релиз.

## Причины и исправления

1. WKWebView не передавал устойчивый признак GRAF при отправке HTML-форм. Общие регистрации `browser-email` / `browser-login` смешивали независимые входы. Production WKWebView теперь задаёт `applicationNameForUserAgent` до создания; сервер создаёт отдельную `login:<uuid>` регистрацию. Полный User-Agent не сохраняется; ограниченная подпись клиента не участвует в выдаче прав.
2. Название провайдера и статус записи не доказывали тип клиента и действующий доступ. Новый список использует срок, состояние сеанса и согласованную trusted binding; текущий сеанс первый. Неизвестные старые клиенты не переклассифицируются. Законный unbound bootstrap отличим от повреждённой привязки и не получает tenant-доступ.
3. Principal-only API не всегда учитывали отзыв устройства. Общий resolver проверяет owner/workspace/device/binding после правильной смены RLS-контекста. Общий отзыв завершает direct и binding-only сеансы, блокирует bindings и не оживляет терминальные записи.
4. Внешний переход к оплате мог делить токен с приложением. Теперь он создаёт независимый браузерный сеанс со сроком не позже исходного; callback заново проверяет источник, устройство, членство и одноразовый state.
5. Раздел объединён в «Устройства и сеансы». Действующие входы, раскрываемые сведения и история отделены; названы область рабочего пространства и смысл последней связи. Single/bulk действие имеет серверное подтверждение, отмену, защиту текущего сеанса и честный результат ошибки.

## Независимое ревью

Рецензент `references` проверил correctness/security/UX и отдельно Ponytail. Найдены и устранены:

- P1: предварительный `RegisteredDevice FOR UPDATE` в массовом отзыве создавал цикл с обновителем активности. Конкурентный тест на двух транзакциях получил настоящий `DeadlockDetectedError` до исправления. Удалены преждевременные блокировки устройств и несортированная блокировка сеансов; общий helper первым блокирует сеансы в стабильном порядке. Итоговый набор account: 107 passed.
- P2: общий PrincipalDependency обновлял last_seen при выходе. Два теста настоящих POST `/logout` и `/desktop/meetings` воспроизвели ошибку; activity пропускает только эти операции. Проверяются сохранение трёх временных полей и фактический revoke: 2 failed до исправления → 11 passed после в целевом наборе.

Повторное заключение рецензента: APPROVED; новых блокеров нет. Ponytail: новых зависимостей и лишних уровней нет, проверки границ сохранены.

## Проверки

Команды выполняются из корня, кроме явно указанного перехода. PostgreSQL создаётся скриптом в отдельном контейнере и удаляется после проверки; используются только синтетические данные.

```sh
GRAF_TEST_WORKERS=2 apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_account_lifecycle.py tests/contract/test_account_routes.py tests/contract/test_settings_ui_contract.py tests/unit/test_settings_view_models.py
```
Результат: **107 passed**, 30.18 s pytest / 34 s phase. Включены single/bulk, browser/desktop, no-JS server confirmation, отсутствие CSRF, повтор, защита текущего, неизвестная цель, действительность токена до/после отзыва, конкурентные транзакции, состояния и часовой пояс.

```sh
GRAF_TEST_WORKERS=2 apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_auth_session_clients.py tests/unit/test_workspace_onboarding.py tests/contract/test_auth_contracts.py tests/integration/test_web_owner_session_context.py tests/integration/test_rls_stale_session_device_context.py
```
Результат финального повторного прогона: **177 passed**, 172.61 s pytest / 177 s phase. Все исходные три отказа устранены; новые client/revoke/expiry/handoff/logout проверки и затронутые существующие сценарии прошли вместе.

```sh
GRAF_TEST_WORKERS=2 apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_rls_postgres_policies.py -k 'session_client or billing_handoff or email_login or workspace_switch'
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
```
RLS: **2 passed**, 2.90 s / 7 s phase в финальном повторе новых client/activity/revoke и независимого billing callback; ранее ещё проверены email и workspace переходы под ролью приложения (общая группа 4 passed). Swift: **47 passed**. Новый тест использует production EmbeddedCabinetWebView внутри NSHostingView и живой loopback HTTP-сервер: GET → form POST → 303 → GET, во всех запросах WebKit и GRAFDesktop marker. До фикса этот тест дал три ожидаемые ошибки отсутствующего marker.

Ruff по всем изменённым Python файлам: PASS. `git diff --check`: PASS. `python3 scripts/check_spec_kit_governance.py`: PASS; повтор перед PR. Changelog fragment и описание PR проходят штатные валидаторы.

## Интерфейс

Playwright CLI, Chromium и WebKit, реальные production templates/viewmodels/static assets с синтетическим аккаунтом на loopback origin:

- 375 / 768 / 1280 px: горизонтального переполнения нет, текущий сеанс первый.
- «Подробнее» открывается клавишей Enter; фокус видим. История раскрывается.
- Отдельный Chromium context с JavaScript disabled: форма открывает подтверждение с `confirm=1` и ссылкой «Отмена».
- Ошибка отзыва отображается через `role=alert`, без успешного результата.
- Визуально проверены мобильный и широкий списки; снимки содержат только синтетический профиль.

Preview сервер используется только для проверки отображения и навигации: он не доказывает изменение БД. Настоящие CSRF/confirmation/revoke и независимость токенов доказаны PostgreSQL route tests; production WKWebView transport — Swift тестом. Внешние OAuth провайдеры и установленная публичная сборка с приватным аккаунтом не использовались.

## Convergence и границы

FR-001–012, SC-001–004, три пользовательских сценария, решения plan о моделях/сроках/RLS/UI/зависимостях и применимые принципы конституции проверены. Реализация согласована с требованиями; незакрытый этап T009 — создание PR и обязательная проверка GitHub на точном SHA. Дополнительные задачи реализации не требуются.

Legacy Impact: untouched; нового legacy path нет. БД, зависимости, секреты, сбор контента/геолокации, capture и локальное удаление не меняются. Публичный релиз, full CI, notarization/stapling/Sparkle и deployment не запускались и остаются отдельными релизными этапами. Для появления новой классификации у пользователя требуются обновлённые сервер/macOS клиент и новый вход; старые сведения остаются честно неопределёнными.
