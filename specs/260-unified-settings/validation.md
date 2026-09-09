# F260 — Проверка реализации

Дата: 2026-09-09. Ветка `codex/260-unified-settings`. Lane: **High-risk product / reference-fidelity UX**. PR #6900. Первая проверка GitHub на `40c13ba96b5fb9af85e3cbfa253f7373a063a16a` выявила устаревшие ожидания shell-тестов и лишнюю account-навигацию в default renderer. Они исправлены; новый SHA требует повторного CI/Dev.

## Результаты

| Проверка | Результат | Границы доказательства |
|---|---|---|
| Требования и принятие макета | PASS, независимый reviewer 9/9; владелец «Подтверждаю, реализовать» | Принятие требований, отдельно от продукта |
| Макет, Node | PASS, 79 имён, правила/patch/валидация/ошибки | Модель, без внешних действий |
| Макет, Playwright | PASS: 42 сочетания ширины/раздела, 8 состояний; сохранение, ошибка, возврат и восстановление | `prototype-visual-check.js`, синтетические значения |
| Swift | PASS: 80 тестов | Два моста настроек, маршруты, controls, доставка уведомлений и accessibility regression |
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

## Исправления после проверки кандидата

Независимый reviewer обнаружил гонку повторной активации моста после смены аккаунта. refreshContext теперь возвращает только подтверждённое поколение; отложенная активация проверяет поколение до подготовки и после неё. WKWebView-регрессия задерживает ответ, меняет аккаунт без навигации, отклоняет прежнее продолжение и отдельно проверяет первое успешное подключение. 80 профильных Swift-тестов PASS; повтор 5 notification bridge тестов с подтверждённым новым владельцем PASS.

GitHub run 34384977227: FAIL в четырёх shell assertions, не PASS. Renderer по умолчанию теперь показывает account с одной навигацией; мёртвый overview template удалён. Тест ширины ограничен sidebar, не запрещает размер нового select. Ожидания реестра разделов и отдельного sessionStorage ключа настроек обновлены. Повтор shell/settings: 126 PASS. Полная повторная проверка GitHub потребуется на новом SHA.

На `7336027b2244a3335469535a5e9e2db47bb496bf` required governance-fast PASS: https://github.com/yshishenya/graf/actions/runs/34385808940 (4m27s); pr-metadata PASS: https://github.com/yshishenya/graf/actions/runs/34385808961. Harness build PASS, установка ещё не выполнялась. Эти результаты не относятся автоматически к следующим коммитам.

Дополнительная проверка контраста выявила белый текст на новом светло-фиолетовом фоне (3.06:1). В тёмных настройках текст активного элемента теперь #202125, фон наведения #a18cff; текст/основной акцент 5.26:1. В production-template матрицу добавлены четыре пары цветов в обеих темах с порогом 4.5:1. Повтор 36 сочетаний с contrast, search/bulk/error/keyboard/200%/no-JS PASS. Это собственное исправление доступности, обязательное отличие от цветовых пропорций референса.
