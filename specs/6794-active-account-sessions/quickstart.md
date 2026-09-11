# Validation
## Focused tests
Из apps/server с существующим uv:
```sh
uv run --extra dev pytest tests/contract/test_account_routes.py tests/unit/test_settings_view_models.py -q
# Из корня репозитория:
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/unit/test_auth_session_clients.py
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_account_lifecycle.py -k session
```
Для интеграционных тестов использовать только отдельную локальную тестовую БД, по существующему tests/conftest.py; не production.
## Сценарии
- Смешанные текущий/другой active и expired/revoked/replaced/blocked: видны только первые, нет истории/счётчика и метаданных остальных.
- Два одинаковых имени не объединены, unknown active виден; единственный текущий и недоступность имеют разные состояния.
- Одиночное и массовое подтверждения: CSRF, confirm=1, отмена, текущий защищён, после успеха другой отсутствует.
- Браузерные синтетические веб и embedded страницы: 390/1280 px, светлая/тёмная темы, details клавиатурой, формы без JavaScript, нет переполнения.
## Release boundary
Локальные тесты не доказывают deployed или установленное приложение. PR требует governance-fast exact SHA; release-full и выпуск — после согласования. Коммит не выполнять автоматически.

## Повторная проверка компактного варианта T005
Проверить обе формы кабинета, темы, 390/1280 px и 200%: единый список, общий счётчик, 64–72 px при обычном тексте на широком экране, цели действий ≥44 px, переносы без переполнения. Раскрыть native details мышью и клавиатурой. Первый POST сохраняет доступ и показывает подтверждение под целью; cancel/Escape скрывают панель и возвращают фокус к исходной кнопке. Повторный вход в подтверждение и confirm=1 завершают доступ; список/счётчик обновлены. Повторить одиночный и массовый путь без JS: cancel href к исходной кнопке. Для исчезнувшей цели/массовой кнопки подтверждение под списком, отмена к focusable #account-sessions-title. Проверить ошибки/reauth, пустоту, current-only и недоступность. Серверную авторизацию подтверждает integration test, синтетический браузер — только взаимодействие и отображение.
