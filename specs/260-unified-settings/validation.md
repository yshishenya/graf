# F260 — Проверка реализации

Дата: 2026-09-09. Ветка `codex/260-unified-settings`. Lane: **High-risk product / reference-fidelity UX**. База рабочего дерева: `bc41c10bf7a561c04c8a51d2a034dd6d75a36aad`. Изменения не закоммичены; эта база не является SHA проверенного кандидата F260.

## Результаты

| Проверка | Результат | Границы доказательства |
|---|---|---|
| Требования и принятие макета | PASS, независимый reviewer 9/9; владелец «Подтверждаю, реализовать» | Принятие требований, отдельно от продукта |
| Макет, Node | PASS, 79 имён, правила/patch/валидация/ошибки | Модель, без внешних действий |
| Макет, Playwright | PASS: 42 сочетания ширины/раздела, 8 состояний; сохранение, ошибка, возврат и восстановление | `prototype-visual-check.js`, синтетические значения |
| Swift | PASS: 79 тестов | Два моста настроек, маршруты, controls, доставка уведомлений и accessibility regression |
| Настоящий WebKit | PASS внутри Swift suite | Production template + cabinet.js: запись, поиск, bulk для скрытых строк, подтверждённые значения, обновление native store, фокус, уведомления и смена аккаунта |
| Сервер с изолированным PostgreSQL | PASS: 81 тест | Страницы/маршруты/модели/права/существующие операции, предпочтения и notification navigation; контейнер удалён runner |
| Production templates, Playwright | PASS: 36 сочетаний: account/recording/notifications × 320/390/768/820/1024/1440 × light/dark | Синтетический мост, никаких настоящих настроек macOS; полный реестр 79, поиск Zoom, bulk, ошибка, disconnect, keyboard, forced-colors, reduced-motion, 200%, no-JS button/CSRF |
| JavaScript syntax | PASS | `node --check` текущего cabinet.js |
| Spec Kit governance | PASS с закреплённым specify-cli v1.0.1/ref 9118ed15a0ba65053469a94c560ea5d233f75884 | Изолированная временная среда; глобальный v1.0.4 и project lock не изменены |
| Changelog / whitespace | PASS | validate-changelog-fragments.py; git diff --check |
| Issue canon F260 | PASS 16/16 по прямому чтению | Общий validator ранее FAIL на посторонней #6852; чужая issue не изменена |
| Установленный GRAF Dev | НЕ ВЫПОЛНЕНО | Нужны авторизованный commit, согласование общего стенда и harness |
| Required governance-fast exact SHA | НЕ ВЫПОЛНЕНО | Нет коммита/PR; локальные проверки не заменяют GitHub check |
| Full CI / merge / deploy / release | НЕ ВЫПОЛНЕНО | Не входят в выполненную локальную реализацию |

## Воспроизведение

```sh
swift test --package-path apps/macos --filter 'EmbeddedCabinetRecordingSettingsBridgeTests|EmbeddedCabinetNotificationSettingsBridgeTests|DesktopNotificationControlTests|DesktopLocalNotificationDeliveryTests|DesktopCabinetRoutePolicyTests|AppControlAccessibilityTests'
apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_settings_ui_contract.py tests/integration/test_settings_ia_flow.py tests/unit/test_settings_view_models.py tests/unit/test_settings_outcomes.py tests/unit/test_notification_preferences.py tests/contract/test_notification_navigation.py -q -o addopts=''
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
node specs/260-unified-settings/prototype-check.cjs
python3 scripts/validate-changelog-fragments.py
git diff --check
```

Веб-стенд использует существующий `tests.fixtures.settings_visual_ui_harness:app`, порт 8767. Макет — локальный http.server на 8766. Сценарии запускаются через `playwright-cli -s=<session> run-code --filename=specs/260-unified-settings/visual-check.js` и `prototype-visual-check.js`; сначала открыть локальный URL командой `open`. Снимки создаются в игнорируемом `output/playwright/`; они содержат только демонстрационный профиль и реестр приложений. API уведомлений в production-template сценарии подменяется синтетическим ответом, macOS bridge — моделью; настоящий WebKit/Swift проверены отдельно.

Для governance использована временная среда uv с установкой `git+https://github.com/github/spec-kit.git@9118ed15a0ba65053469a94c560ea5d233f75884`, добавленная первой в PATH только для команды проверки. Удалён созданный Python файл bytecode и пустой `__pycache__` в расширении issue-canon: они меняли hash дерева. Проверки целостности не отключались; tracked-файлы расширений/lock не менялись.

## Оставшиеся проверки

T014/T015: полная VoiceOver-проверка, ручные входы меню/Cmd+,/контекст, загрузка/отказ/восстановление кабинета в установленном приложении, фактические настройки macOS, проверка сигнала записи и системных ограничений. Результат Chromium или тестового WKWebView не считается этой приёмкой.

Read-only harness status: единственный GRAF Dev активен на `450ef2fbe14524efb5341f3d7d1704c1325388ab` (другая feature `6791`). Состояние стенда не менялось. Перед переключением требуется повторный status и согласование занятости; результат прежнего smoke не относится к F260.

T016: GitHub governance-fast на новом точном SHA, PR/closeout и согласование issue evidence. Все 16 issues остаются открытыми; локально выполненные задачи не выдаются за merged/released acceptance.
