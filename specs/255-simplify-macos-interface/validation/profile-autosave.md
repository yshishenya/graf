# F255 T025: автосохранение темы в профиле

Дата: 2026-09-07. Lane: active Spec Kit slice / high-risk UX. Исправление сокращает путь выбора темы и не меняет состав или порядок меню.

## Причина

В установленном GRAF Dev выбор «Светлая» в профиле выполнял обычный POST на `/desktop/settings/account/preferences`. Серверный redirect вёл на «Аккаунт и безопасность», поэтому пользователь покидал текущий экран и терял контекст списка встреч. Это не было нужно для сохранения одной темы.

## Решение

- Форма меню профиля содержит только тему, CSRF и безопасный локальный `return_to` для обычного HTML-пути.
- `cabinet.js` перехватывает только форму с `data-account-preferences-auto-save`, отправляет её через `fetch` с текущими cookie/CSRF и оставляет текущий документ на месте.
- После успешного ответа меню закрывается; при ошибке preview и radio выбор возвращаются к последней сохранённой теме, элементы снова доступны.
- Обычная форма страницы аккаунта и её no-JS redirect не изменены.
- Сервер повторно проверяет `return_to` через `safe_first_party_path`, отбрасывает `/login`/`/logout` и сохраняет прежний fallback аккаунта.

## Проверки

- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_cabinet_audit_fixes.py apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/contract/test_settings_ui_contract.py` — 145 PASS.
- `swift test --package-path apps/macos --parallel --num-workers 1 --filter CabinetSidebarRuntimeTests` — PASS; новый сценарий подтверждает `/meetings`, `return_to` и `fetch` без навигации.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` — PASS.
- `git diff --check` — PASS.

## Ограничения

Свежая установленная общая сборка GRAF Dev принадлежит интеграции F249; T025 нужно подтвердить в её следующем кандидате. Полная матрица macOS, VoiceOver и release/full CI этим изменением не закрываются.
