# F260 — Результаты проверки

Дата: 2026-09-09. Lane: **High-risk product / reference-fidelity UX**, полный Spec Kit.
PR: https://github.com/yshishenya/graf/pull/6900.

## Матрица

| Проверка | Результат | Граница доказательства |
|---|---|---|
| Требования / независимый review | PASS: checklist 9/9, CRITICAL 0 / HIGH 0 после исправления auth race | Заключение в requirements-review.md |
| Макет | PASS: 42 сочетания ширины/раздела, 8 состояний, Node model | Синтетические значения |
| Swift / настоящий WKWebView | PASS: 100/100 на d5aba78c1 | Production templates + cabinet.js, оба моста, auth race, сохранение/фокус, маршруты, доставка, доступность и 20 capture regressions |
| Сервер / изолированный PostgreSQL | PASS: 81/81 | Маршруты, модели, права, операции и notification preferences |
| Shell / settings после исправления CI | PASS: 126/126 | Default renderer, единственная навигация, размеры и contract regressions |
| Production templates / Playwright | PASS: 36 сочетаний account/recording/notifications × 6 ширин × 2 темы | Реестр 79, поиск, bulk скрытых строк, ошибка, auth clear, keyboard, forced-colors, reduced-motion, 200%, no-JS/CSRF; четыре пары контраста >=4.5:1 |
| GRAF Dev | PASS: harness 13/13 и установленная матрица на 113abd487180241b322f2716aa35e2eabb007abc | Подробности ниже; финальный повтор exact SHA публикуется в PR |
| JavaScript / Ruff / changelog / whitespace | PASS | Синтаксис, lint сервера, fragment и git diff --check |
| Spec Kit governance | PASS | Закреплённый CLI v1.0.1/ref 9118ed15a0ba65053469a94c560ea5d233f75884; глобальный CLI и lock не менялись |
| Issue canon F260 | PASS 16/16 | Посторонняя #6852 не изменялась |
| Required GitHub governance-fast | PASS на d5aba78c1f5e2f8dbb693d3ec03c153ac5e547c1, run 34389811229; pr-metadata run 34389811157 PASS | Окончательный exact-SHA check обязателен в PR перед ready; старый PASS его не заменяет |
| Full CI / merge / deploy / release | НЕ ВЫПОЛНЕНО | Full CI выполняется для отдельного замороженного release candidate; PR не выпускает продукт |

## Итоговая идентичность

Последняя строка PR содержит полный source SHA. После документационного коммита required governance-fast, pr-metadata и повтор harness build/promote/status/smoke должны совпасть с ним; результаты добавляются в PR и machine-local harness receipts без нового коммита, который снова изменил бы SHA. До их PASS PR остаётся draft. Issues закрываются после merge, с явной связью tasks и evidence.

## Исправления, проверенные повторно

- Независимый reviewer обнаружил повторную активацию устаревшего документа после смены аккаунта. refreshContext возвращает подтверждённое поколение, а отложенная активация проверяет поколение до и после await. WKWebView-регрессия воспроизводит задержанный ответ и смену владельца.
- Первый GitHub run 34384977227 выявил четыре shell assertions. Исправлены default renderer и устаревшие ожидания; повтор 126/126 PASS и последующие GitHub runs PASS.
- Контраст белого текста на фиолетовом фоне тёмной темы был 3.06:1. Текст активного элемента #202125 теперь даёт 5.26:1; четыре пары проверяются в каждой теме. Это документированное отличие ради доступности.
- Сохранение подтверждения при повторном read проверено настоящим WKWebView после save/refresh.

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

## Установленная приёмка F260 — 113abd487180241b322f2716aa35e2eabb007abc

Harness build/promote PASS13/13, единственный /Applications/GRAF Dev.app, pro.2brain.graf.dev; подпись и разрешения сохранены. Native UI проверен через CUA screenshot/AX и системную клавиатуру, без исполнения JavaScript в приложении.

- Cmd+, открыл account в основном окне. Контекст «Автоопределение встреч» открыл recording в том же окне. Боковая навигация открывает notifications; в широком виде видны группы/имена, в узком есть раскрываемая панель. Существующая правая панель записи сохраняет своё раскрытое/свёрнутое состояние, ручные controls доступны.
- Окна1040×680/820×600: имена приложений и select читаемы. ПоискZoom даётZoom иZoom Phone. Клавиатурой Zoom: ask→never→ask; native store подтверждает запись. Все79 исходных правил после проверки семантически совпадают с начальным файлом (78ask,1always).
- Notifications: реальный статус macOS authorized, все4 локальных поля и2 серверных. Sound:on→off→on; фокус остаётся на переключателе. Повторный вход и резерв показывают восстановленные значения. Тестовая команда доступна; фактическая доставка баннера не заявляется.
- Масштаб установленного кабинета200% подтверждён workspaceZoom=2; строки/select переходят вертикально, текст и контроли не обрезаны, горизонтальная прокрутка не нужна. Возвращены100% и1040×680.
- VoiceOver включался и отключался штатным Cmd+F5, NSWorkspace.isVoiceOverEnabled подтверждалtrue. Имена, роли и значения native/WebKit доступны через AX; клавиатурный проход сохраняет доступ к системной кнопке. Озвученный текст автоматически прочитать не удалось (VoiceOver scripting−1728), аудиовывод не записывался; это ограничение доказательства, не подтверждение полной проверки произношения.
- Отказ кабинета воспроизведён остановкой толькоDevAPI; Cmd+, открыл единственное graf-settings-window с записью и уведомлениями. ПоискZoom и прежние правила доступны, local notifications сохраняют исходные значения. После запуска того жеAPI «Все настройки GRAF» открывает account и закрывает резерв. Данные/тома/TCC/подпись не менялись.
- CaptureIndicatorTests/CaptureSessionSafetyTests/CaptureControlV5Tests:20/20PASS на кандидате; вместе с80 профильными и проверкой звука приrecording:true покрывают неизменённую семантику. Новая реальная аудиозапись не выполнялась: reviewer подтвердил, что изменённые пути не затрагивают аудиотракт, и принял соответствующее уточнение quickstart. Сквозной новый захват/артефакт не подтверждён.

Во время приёмки выявлено слишком быстро исчезающее подтверждение локального сохранения при повторном чтении. JS теперь сохраняет presenter.message и приread; настоящая WKWebView-регрессия проверяет «Сохранено на этом Mac» послеsave/refresh. Повтор 100 Swift/WebKit-тестов и 36 браузерных сочетаний прошёл на d5aba78c1f5e2f8dbb693d3ec03c153ac5e547c1. Финальная установка и CI привязываются к последнему SHA в PR.

## Исправление по автоматическому review — 2026-09-10

P2 в discussion_r3971976053: тест создавал graf.local.test.<UUID>, а willPresent/openResponse распознавали только прежний exact ID. Оба пути теперь используют общий predicate: legacy ID или префикс с валидным UUID. Регрессия проверяет сформированный request, banner/list/sound, открытие настроек, тишину при active capture, неверные ID и dismiss. Все101 Swift/WebKit/capture-тестов PASS после правки. Независимый review принят, CRITICAL0/HIGH0. Новый commit требует повторных exact-SHA CI и установленного Dev; окончательное evidence публикуется в PR #6900. Предыдущее заключение о готовности f9200a95d заменяется этим уточнением; отсутствие прежнего системного баннера не считалось PASS.
