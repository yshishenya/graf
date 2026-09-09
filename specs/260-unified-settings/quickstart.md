# Validation: F260

## Интерактивный макет
Из корня репозитория:
```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory specs/260-unified-settings
```
Открыть http://127.0.0.1:8766/prototype.html. Макет изолирован: синтетические значения только в памяти страницы; нет запросов к GRAF, macOS или провайдерам. Изменения не сохраняются после перезагрузки. Отдельная панель над макетом задаёт сценарий проверки, она не часть продукта.

Проверить: Назад → Настройки; все семь разделов; правило Zoom; массовый выбор и mixed; возврат в раздел; уведомления off/offset; system denied; saving failure; отсутствие сервера; светлая/тёмная тема; узкое окно и Tab/Escape. Регрессионная проверка логики макета: `node specs/260-unified-settings/prototype-check.cjs`.

## После продуктовой реализации
```sh
swift test --package-path apps/macos --filter 'EmbeddedCabinetRecordingSettingsBridgeTests|EmbeddedCabinetNotificationSettingsBridgeTests|DesktopNotificationControlTests|DesktopLocalNotificationDeliveryTests|DesktopCabinetRoutePolicyTests|AppControlAccessibilityTests'
```
Существующий изолированный server runner: `apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_settings_ui_contract.py tests/integration/test_settings_ia_flow.py tests/unit/test_settings_view_models.py tests/unit/test_settings_outcomes.py -q -o addopts=''` из принятого каталога по инструкции runner.

Добавить security matrix: origin/port/scheme/encoded path/query/fragment/iframe/loading/old nonce/extra keys/bad types/offset; owner A→B→A; async permission после logout; подтверждённый snapshot; no-JS CSRF/version conflict; неизвестный/пустой target list; перезапуск и отсутствие сброса настроек.

Визуальная матрица продукта: 820×600, 1024×768, 1440×900, responsive 320/390/768 px, 200%, обе темы, длинные имена, keyboard/VoiceOver/forced-colors/reduced-motion. Никакого наложения/горизонтальной прокрутки; имя/правило доступны для всего допустимого реестра.

## Native / closeout
Прочитать docs/agent-guidance/local-development.md. Только `/Applications/GRAF Dev.app` через harness status → build → promote → status → smoke; чистый авторизованный commit и точный SHA. Не запускать новую копию/swift run и не менять подпись/TCC. Проверить все точки входа, резерв без кабинета, возврат, реальное разрешение macOS и безопасную синтетическую запись. Отдельно фиксировать browser, WebKit и GRAF Dev.

До closeout: reviewer checklists, analyze, canonical issue sync; после реализации — Ponytail review, convergence, required fast/governance-fast точного SHA. Full CI и выпуск — отдельный release gate. На этапе проекта продуктовые тесты и CI не доказываются проверками макета.

## Автоматизация визуальной проверки
Макет: `playwright-cli -s=f260-prototype open http://127.0.0.1:8766/prototype.html`, затем `run-code --filename=specs/260-unified-settings/prototype-visual-check.js` в той же сессии.
Production templates: из apps/server запустить `PYTHONPATH=src:. .venv/bin/python -m uvicorn tests.fixtures.settings_visual_ui_harness:app --host 127.0.0.1 --port 8767`; открыть страницу через Playwright CLI и выполнить `run-code --filename=specs/260-unified-settings/visual-check.js`. Снимки в output/playwright игнорируются git. Native bridge в этом визуальном сценарии синтетический; проверка реального WebKit находится в Swift-тестах.
