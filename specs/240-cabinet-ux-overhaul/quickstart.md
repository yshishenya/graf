# Quickstart: повторная проверка интерфейса F240

Команды запускаются из корня репозитория. Нужны `uv`, Node.js и Docker для
изолированной тестовой PostgreSQL. Настоящие аккаунты, записи и секреты не нужны.

## Проверки контрактов и сценариев

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_cabinet_frontend_foundation_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_theme_contract.py \
  tests/contract/test_cabinet_shell_response_contract.py \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_billing_ui.py \
  tests/contract/test_graf_ux_ui_contract.py \
  tests/contract/test_cabinet_playback_contract.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_billing_accessibility.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_settings_ia_flow.py
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Скрипт сам поднимает и удаляет свой контейнер. Не подставляйте рабочую БД.
Статические тесты контраста не заменяют вычисленные браузером стили.

## Синтетический браузерный стенд

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev uvicorn \
  tests.fixtures.calendar_visual_ui_harness:app --host 127.0.0.1 --port 8765
```

Открывайте только `http://127.0.0.1:8765`:

- `/meetings?mode=populated&theme=light` — список, выбор, фильтры, профиль,
  загрузка, предупреждение удаления; отменяйте удаление.
- `/meetings/synthetic-theme?theme=light` — расшифровка, плеер, имя спикера,
  «Поделиться». В последнем окне ввод `а` и «Найти» дают локальную ошибку
  без изменения доступа.
- `/desktop/meetings/synthetic-theme?theme=light` — встроенная разметка,
  не настоящее нативное WKWebView.
- `/login?error=email_connected_relogin_required` — тема ОС, сообщение успеха,
  поле почты. Ничего не отправляйте.
- `/login/email/code?error=email_code_wrong` — ошибка кода; введите только одну
  синтетическую цифру для проверки перехода фокуса, не завершайте вход.

Повторите `theme=light`, `dark`, `system` при обеих темах ОС. Сверяйте реальный
`innerWidth` с выбранными 320/390/768/1024/1440 CSS px; проверяйте содержимое,
открытые меню/окна, выбранные строки, фокус и `prefers-reduced-motion`.
После изменения CSS перезапустите стенд: версия статического файла вычисляется
при импорте. Старый URL из кэша не является доказательством нового CSS.

Сохраняйте только синтетические снимки и измерения. Для обычного текста нужен
контраст 4,5:1, для значимых графических элементов — 3:1. Не считайте скрытый
элемент или ноль найденных элементов успешной проверкой.

Тестовый WAV содержит тишину; стенд не реализует Range-запросы и серверные
операции входа, общего доступа или изменения данных. Поэтому он проверяет
оформление и локальные взаимодействия, но не заменяет приёмку этих операций.

## Перед обновлением PR

Используйте текущие правила `docs/agent-guidance/release-and-validation.md`:
после проверок получите явное подтверждение коммита, обновите SHA в описании
существующего PR и дождитесь `governance-fast` именно на этом SHA.
Локальный `infra/scripts/ci-local.sh --fast` — ручная диагностика, не замена
GitHub-проверке. Полный CI и deployment относятся к отдельному релизу.

Полная матрица из [контракта](contracts/ui-surface-contract.md) остаётся
обязательной перед merge. Свежий [отчёт](light-theme-qa.md) явно ограничивает
объём текущего прохода; старые отметки задач не подменяют новые доказательства.
