# Quickstart: проверка фичи 268

Все команды — из корня репозитория. Реальные аккаунты, записи и секреты не
используются; на стенде только синтетические данные.

## 1. Статические и focused-проверки

```sh
cd apps/server
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/contract/test_cabinet_theme_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_frontend_foundation_contract.py \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_billing_ui.py \
  tests/contract/test_billing_accessibility.py \
  tests/contract/test_graf_ux_ui_contract.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_cabinet_shell_response_contract.py \
  tests/contract/test_notifications_ui_contract.py \
  tests/unit/test_cabinet_web_shell.py
cd ../..
python3 scripts/check_spec_kit_governance.py
```

## 2. Браузерный стенд (кабинет)

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev uvicorn \
  tests.fixtures.calendar_visual_ui_harness:app --host 127.0.0.1 --port 8765
PYTHONPATH=src uv run --extra dev uvicorn \
  tests.fixtures.settings_visual_ui_harness:app --host 127.0.0.1 --port 8766
```

Проверить и сохранить замеры/скриншоты:

1. `/meetings?mode=populated&theme=dark|light` и `/desktop/meetings?...`:
   скелетон виден в светлой теме; подписи навигации не обрезаны (замер
   `scrollWidth <= clientWidth`); фон/акцент/границы совпадают с токенами.
2. `/meetings/synthetic-theme?theme=light`: вкладки объявляются как вкладки;
   цвета спикеров различимы и контрастны; фокус единообразен.
3. `/settings/...` и `/settings/integrations/calendar?theme=light`: статус
   автосохранения зелёный при успехе и красный при ошибке; бейджи состояний
   оформлены одинаково; панель настроек без обрезки «Тариф и оплата».
4. Билдинг/рефералы недоступны на стенде: проверяются контрактными тестами и
   синтетическим рендерингом (см. п. 1).
5. Проверить 320/390/768/1024/1440, отсутствие горизонтального переполнения,
   тёмную и светлую тему, `prefers-reduced-motion`, консоль без ошибок.

## 3. macOS

```sh
swift build --package-path apps/macos
bash apps/macos/Scripts/run-swift-tests.sh
```

Проверить контрактные тесты подсказок, статусов автозаписи, обновлений, трея,
онбординга и локализации (обновлённые ожидания текстов).

## 4. Единственное Dev-приложение

```sh
infra/scripts/dev-harness.sh status --json
# build → promote → status → smoke по infra/dev/README.md
```

Ручная проверка в `/Applications/GRAF Dev.app`: один индикатор обновления;
полоса только в фазе действия; статус автозаписи честный; трей и онбординг
соответствуют контракту; цвета совпадают с кабинетом в светлой и тёмной теме.

## 5. Итоговые артефакты

- `specs/268-ui-consistency-unification/validation.md` — что выполнено, чем
  проверено, какие границы остались.
- `changes/unreleased/268-ui-consistency-unification.md` — фрагмент changelog.
