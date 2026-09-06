# F243: результаты исправлений и границы приёмки

Дата: 2026-09-06. Lane: `high-risk-feature`.
Ветка: `codex/243-cabinet-audit-remediation`; исходная база:
`41bf51c7da86212503d971bce09e44640c087f4e` — НЕ SHA исправлений.
Implementation SHA: `6db3eb4cb1f0f2efb0f660d83164533da9289a8a`.
Создан [draft PR #6581](https://github.com/yshishenya/graf/pull/6581).
[GitHub governance-fast](https://github.com/yshishenya/graf/actions/runs/33994631990)
на implementation SHA: **PASS, 7m0s**. Последующий коммит меняет только этот
отчёт и task markers, не исходники. Его окончательный SHA и отдельный run
подтверждаются в [validation comment PR](https://github.com/yshishenya/graf/pull/6581#issuecomment-5555093596).
Все данные синтетические; production, реальные записи и учётные записи не использовались.

## Результат

Собственная реализация F243 проверена в пределах таблицы ниже. Полная F243
**не принята**: открыт зависимый draft PR, а не готовность к merge/release.
Незакоммиченные изменения соседних задач не копировались и не учитываются как PASS.

| Требование | Реализация и доказательство | Статус |
|---|---|---|
| FR-001, FR-010 | Настоящий WKUIDelegate/NSAlert: доверенная главная страница, однократный ответ, Return/Escape отменяют, явная кнопка продолжает; смена страницы, закрытие окна, detach и смерть веб-процесса отменяют запрос | PASS в 50 Swift tests |
| FR-002, FR-010 | Точные settings/shared/audio/legal routes; desktop hint в full/summary/unavailable и повторной загрузке фрагментов; ссылки архива учитывают поверхность | PASS Swift + 39 DB tests + Node regression |
| FR-003 | Общая палитра, контраст и все состояния списка/диалогов — F240 | BLOCKED: T008/T014 |
| FR-004 | Сохранение темы и неизменность locale/timezone — F242 | BLOCKED: T006 частично, T008/T015 |
| FR-005 | Нативный Popover API, hover/focus/клавиатура, перенос длинных подписей, ограничение области меню и подсказок, короткие окна/масштаб | PASS: 438 проверок Chrome и 438 WebKit |
| FR-006 | Принятие итогов сначала открывает вкладку итогов, затем фокусирует существующий раздел с tabindex=-1 | PASS executable Node + template tests; настоящий серверный accept/reload в браузере не запускался |
| FR-007 | Русские роли/статусы с прежними кодами; точные ограничения календаря, локали и пространства; Итоги/Расшифровка в видимых подписях | PASS production renderers и export tests |
| FR-008 | Удалены только 19 макросов и 20 точных CSS-токенов без производителей; сохранены действующие смешанные группы, маскирование аналитики и все 46 production templates | PASS consumer scan + 321 scoped/39 DB tests |
| FR-009 | Предупреждающая рамка отключения календаря использует danger-border с достаточной специфичностью | PASS computed style Chrome/WebKit в light/dark |
| FR-010 | Серверные auth/tenant/grant guards не удалены; view-only не получает права скачивания; capture/Record/Stop не изменены | PASS границы затронутых потоков; не полный аудит продукта |

## Воспроизводимые проверки

### Сервер и исполняемый JavaScript

Из `apps/server`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -B -m pytest \
  -p no:cacheprovider -p pytest_asyncio.plugin -p tests.fixtures.cabinet_exports \
  --noconftest --capture=sys \
  tests/unit/test_cabinet_template_components.py \
  tests/unit/test_cabinet_template_sections.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_cabinet_audit_presentation.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/unit/test_transcript_exports.py \
  tests/contract/test_cabinet_static_assets_contract.py -q --tb=short
```

Итог: **321 passed**, последний запуск 3.36 s. Node-проверки выполняются из
существующего pytest contract suite: положение подсказок/подменю, порядок
активации вкладки и фокуса, desktop hint при обновлении фрагмента и отсутствие
повторных обработчиков после HTMX. Проверяются настоящие функции cabinet.js.

Из корня, отдельный временный PostgreSQL, автоматически удалённый после тестов:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_shared_with_me.py \
  tests/integration/test_recording_share_public_link.py \
  tests/contract/test_cabinet_no_secret_content_egress.py
```

Итог: **39 passed**, 145.91 s. Проверены full/summary/unavailable с/без desktop
hint, разрешённое скачивание синтетического retained audio и отказы. Для full
view-only прежний ответ `409 artifact_unavailable` сохраняется; summary и
unavailable не получают аудио. Это не тест серверного сохранения темы F242.

### macOS

```sh
swift test --package-path apps/macos --filter \
  'EmbeddedCabinetJavaScriptConfirmTests|DesktopCabinetRoutePolicyTests|DesktopCabinetNavigationRequestPolicyTests|DesktopCabinetNavigationResponsePolicyTests|DesktopMeetingShellWebViewBoundaryTests'
```

Итог: **50 passed**, 0 failures, 7.883 s после сборки. Шесть новых тестов
подтверждений включают реальный WKWebView с локальной HTTP-страницей на loopback,
нативные кнопки, Return/Escape и отсутствие защищаемого действия после отмены.
Современная сигнатура delegate содержит `@MainActor @Sendable`: тест настоящего
JavaScript выявил бы необязательный delegate, который лишь «почти совпадает».
Существующие предупреждения Swift и рекомендация async API в тесте не ошибки.
Установленное приложение и публичный подписанный бинарник не менялись.

### Браузер

Из `apps/server` запускается тестовый сервер только на loopback:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B -m uvicorn \
  tests.fixtures.cabinet_audit_ui_harness:app \
  --host 127.0.0.1 --port 56643 --no-access-log
```

На открытой странице этого сервера выполнить функцию из
[`browser-checks.js`](browser-checks.js) через Playwright `run-code` для Chrome
и WebKit. Использован установленный WebKit build 2336; отсутствующий default
build 2358 не выдаётся за проверенный. Функция возвращает `{checks, failures}`.

Итог: **Chrome 438/438, WebKit 438/438**, failures=[].
Системная тема light/dark × выбранная system/light/dark × ширины 375/550/768/1200,
высота 812; отдельно 550×400/375×400 и CSS zoom 200%. Проверены подсказки
account/calendar, границы подменю, перенос каждой подписи, Escape, hover→текст,
клик снаружи, no-JS Enter/Space/Escape и рамка calendar disconnect.
Эта матрица доказывает геометрию F243, **не общий контраст F240**.
CSS zoom 200% не подменяет отдельную проверку системного увеличения/VoiceOver.

Снимки синтетических страниц проверены визуально при 375/550 px. Обнаруженное
обрезание длинного пункта меню (scrollWidth 294 при clientWidth 220) устранено
общим white-space:normal; в runner добавлена проверка ширины текста.
Первый дополнительный browser run был прерван кликом теста по ссылке навигации;
тест кликает по неинтерактивному заголовку, оба полных повторных запуска прошли.

## Удаление неиспользуемого кода

Удалены макросы sections: meeting_row, playback_controls, detail_side_panel,
confirmation_dialog, status_banner, empty_state, unavailable_state, auth_form.
Удалены макросы primitives: button, icon_button, input, select, chip, tab, loader,
text, status_label, analytics_private_attrs, provider_private_attrs.

Удалены CSS-токены: workspace, brand-mark, avatar, workspace-title, nav-count,
detail-layout, playback-terminal-state, right-panel, governance, brand-logo--auth,
auth-brand-wordmark, calendar-empty, calendar-connect-link, settings-handoff-card,
settings-choice-row--toggle, billing-cycle-choice, calendar-count,
calendar-disconnect, calendar-provider-mark, sidebar-profile-menu__identity.
Одноимённый машинный recovery-код `workspace` и маршрут settings/workspace
сохранены: это не производители CSS-класса. Действующий calendar-disconnect__body,
provider-logo, cabinet-banner, panel headings, sidebar profile и auth/nav сохранены.
В deletion report удалён вызов неопределённого импорта старого privacy-макроса;
стандартные маскирующие атрибуты записаны явно, покрытие реального списка усилено.

Legacy Impact: `remove`; новых aliases/fallbacks/dependencies нет.
`legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0` для этого изменения.
Остальное наследие продукта не объявляется удалённым.

## Ревью и convergence

Независимый review требований: requirements 10/10, security 5/5, UX 6/6 PASS.
Implementation не менял reviewer-owned markers.
Проверка correctness и Ponytail основным агентом: новых блокирующих ошибок нет;
переиспользованы NSAlert, route policy, Popover API и существующие handlers.
Отдельное заключительное ревью кода выявило P2: штатные фрагменты вкладок
общей встречи запрещали native reload. Ошибка воспроизведена двумя failed
assertions. В рамках T005 разрешены только `#outcomes`/`#recording` для detail;
audio download и неизвестные фрагменты остаются закрытыми. Повторные 50 Swift
tests PASS. Независимый reviewer повторно проверил staged guard и четыре
ожидания: APPROVED для commit/draft PR; P2 закрыт, новых блокеров нет.
Это не доказательство сквозного native reload в установленном приложении.

Converge: `tasks_appended`, не `converged`. Проверены 10 FR, 10 acceptance
scenarios, 4 SC, 6 решений плана и 7 принципов конституции. Три findings:
2 partial + 1 missing; CRITICAL 0, HIGH 2, MEDIUM 1. Phase7 добавлена только
в конец tasks.md: T014/T015/T016 отслеживаются вместе с T008 в #6575.
Смысл spec.md/plan.md не переписывался для объявления готовности.

Состояние зависимостей на проверку:

- F240: PR #6560, SHA `8eb1bb8078140d51ae910197a613ce0999a98ed9` до последних
  исправлений тем; незакоммиченный diff владельца не интегрирован.
- F242: владелец подтвердил отсутствие implementation commit/PR. База
  `41bf51c7da86212503d971bce09e44640c087f4e` не evidence исправления.
- F244: владелец подтвердил отсутствие implementation commit/PR; ещё нужны
  реализация upload/rail/accessibility и совместная проверка.

T003/T004/T005/T007/T009/T010/T011 выполнены. T006 частично (overlays готовы,
сохранение темы — F242); T008/T012 и T014–T016 остаются открытыми.
T013 выполнена: fragment/commit/push/PR и exact-SHA governance-fast есть.
Выполнение T013 на draft-checkpoint не закрывает T012 и совместную приёмку.
Issues #6573, #6576, #6577 закрыты после подробных русских closure comments
с implementation SHA и успешным run. #6567/#6574/#6575/#6578 остаются открытыми.

## Гигиена и следующие ограничения

- `node --check .../cabinet.js`, scoped `ruff check --no-cache`,
  `git diff --check`: PASS; два новых Python-файла отформатированы Ruff.
- `python3 scripts/check_spec_kit_governance.py`: PASS.
- Issue canon ensure: PASS без изменений root governance;
  validate: PASS, 300 проверенных Spec Kit issues.
- Полный CI, локальный повтор `ci-local.sh --fast`, release-full, CD dry-run,
  merge, публикация, notarization/Sparkle, установка и production smoke:
  **NOT RUN**. Для PR запускается authoritative GitHub governance-fast;
  локальные выборочные тесты не равны полному CI и не разрешают релиз.
- Настоящее изменение профиля/удаление аккаунта/отключение календаря production
  не выполнялись. Нативные механизмы и права проверены синтетически.
- Не проверены объединённые list/search/upload/dialog contrast состояния,
  persistence темы и совместные accessibility изменения до финальных SHA
  F240/F242/F244. Не помечать весь аудит закрытым и не снимать draft до приёмки.

## Совместная приёмка общего выпуска — 2026-09-06

Lane: high-risk-product; последующий выпуск — Release / deploy. Исходные
частичные результаты выше сохранены как история. Эта проверка относится к
объединённым F238/F240/F242/F243/F244, integration source
`50defae4301cc3fa6388862c5234ca3a2b6b11ee`; финальные SHA отдельных PR и
обязательный governance-fast связываются в их описаниях после rebase.

Проверены production renderers/assets на синтетическом loopback стенде:

- 1620 сочетаний 27 состояний × 6 тем × 2 поверхности × 5 ширин
  320/390/768/1024/1440: HTTP 200, заголовок, отсутствие горизонтального
  выхода страницы. Список ready/empty/filtered, detail ready/processing/partial/
  failed/unavailable, настройки, тариф, shared ready/empty/summary/blocked,
  вход/код/регистрация/ошибка/успех. Календарь покрыт отдельным runner F243.
- По 438 Chrome/WebKit: подсказки, profile submenu, zoom200%, короткие окна,
  Escape/hover/no-JS, warning border. По 42: один профильный DOM, смена ширины,
  темы, формы и возврат фокуса. По 10: кнопки плеера не перекрываются.
- Численный контраст видимого текста и placeholder: Chrome3042 и WebKit3048,
  нарушений0. Шесть сочетаний явной/системной темы, список, поиск, detail,
  тариф, профиль и upload. Порог4.5:1 для обычного текста,3:1 для крупного.
- По 639 Chrome/WebKit: upload accessible name, файл/ошибка/нет сессии,
  Tab/Shift+Tab, scroll, Escape/reopen; narrow rail, сохранение предпочтения,
  фокус в заменённом main, hit-test поиска и нижние действия панели.
- По 63 Chrome/WebKit: auth/referral active/unavailable/invalid, ширины и темы,
  неперекрывающийся legal footer и динамический light→dark→light без reload.
  Явная тема остаётся выбранной, system следует ОС. Снимок регистрации390
  проверен после завершения анимации: поле и кнопка видны, legal ниже формы.

Найдены и устранены четыре интеграционных дефекта: потеря мобильного профиля,
перекрытие «Спикеры» и перемотки, отрицательный отступ legal footer и два
устаревших тестовых ожидания после удаления мёртвых компонентов F243.
Проверки не ослаблены: billing тест теперь рендерит обе реальные ссылки,
theme проверяет используемый selector. Theme-only POST дополнительно проверен
через настоящую сессию и свежую DB session: locale/timezone сохраняются.

Нативная проверка: сборка GRAF Dev PASS; реальный WKWebView на loopback,
ручные Record/Stop доступны. Настройки открываются через профиль; NSAlert
для выхода с других устройств отменяется Return и возвращает фокус.
После включения F244 повторно проверены доступное имя «Загрузить файл»,
Tab по контролам, Escape и возврат на «Загрузить запись» в собранном приложении.
24 focused XCTest (WKWebView/confirmation/routes/zoom) ранее PASS; добавленный
F238 имеет собственные17 XCTest и exact-head GitHub evidence. Проигрывание
синтетического WAV не считается доказательством Range или capture.

Correctness/Ponytail review: общий focus helper и все8 callers просмотрены;
cycleAll включён только для upload, cancel использует существующее закрытие.
Динамический main сохраняет recovery replaceWith. F242 trial_confirmation
сохранён при удалении старых macros F243. Mobile profile переносит существующий
DOM, не создаёт дубли форм. Новых зависимостей и производственных маршрутов нет.

Границы: это применимая матрица Spec Kit, не сертификат WCAG. VoiceOver в этой
среде не запустился; реальные имена/landmarks/focus проверены через macOS AX.
Синтетические страницы не доказывают успешные изменения production данных;
эти операции проверяются DB integration suites. Full CI, notarization и
production smoke выполняются отдельно для окончательного release candidate.
Review-owned checklist markers не менялись.

Совместный quickstart **396 passed**, 552.02s, контейнер удалён.
T006/T008/T012/T014–T016 выполнены; converge: converged.
PR остаётся зависимым до merge F240/F244 и exact-head governance-fast.

Дополнительная совместная проверка shared-with-me/public-link/export/auth:
**123 passed**, 414.59s, изолированный контейнер удалён. Включены права
полного и ограниченного доступа, отзыв доступа, пакет экспорта и auth contracts.

## Исправление релизной проверки Swift6.0.3

Full CI33999768481 на0b840a3550315497bcc7981e1d457996bb7d6b69 остановил
macOS-компонент сигналом5 при начале
`testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction`. До этого пять
проверок trust/lifecycle/buttons выполнялись без assertion failures. На локальном
Swift6.3.3 исходная проверка проходила; это различие окружений, не успешный Full CI.

Локальный NWListener и NWConnection теста вызывали closures из MainActor класса
на global queue. Теперь оба используют main queue, соответствующую изоляции
теста. Это единственные два изменения Swift; тест, HTTP/WKFrameInfo, реальный
JavaScript confirm, Return/Escape и protectedAction assertions сохранены.
Новых helpers/dependencies/таймаутов/skip нет. В других тестах NWListener отсутствует.

`swift test --package-path apps/macos --filter EmbeddedCabinetJavaScriptConfirmTests`:
6 PASS,7.842s на Swift6.3.3. Решающая проверка выполняется отдельным
`macos-diagnostic` на закреплённом Swift6.0.3. Старый кандидат непригоден для
публикации; после исправления требуется новый exact-SHA Full CI.

Диагностика34000042467 наece415187bce6564dc8c3d50f4a619e68da80bae
также завершилась сигналом5 в том же тесте. Гипотеза о сетевой очереди не
подтвердилась; две замены отменены. Добавлены временные stage markers и
диагностический вывод только exception/termination/stack symbols из crash report.
Процессные аргументы, пути, окружение и содержимое памяти не выводятся.

### Причина аварийного завершения macOS 14

- Диагностика 34000555379: `EXC_BREAKPOINT` в `URLRequest._unconditionallyBridgeFromObjectiveC`, вызванном `Coordinator.webView(_:decidePolicyFor:decisionHandler:)` во время загрузки HTTP-документа, до confirm.
- `WKFrameInfo.request` может отсутствовать до появления документа вопреки nonnull-объявлению SDK. Все чтения URL фрейма сведены к существующему Objective-C getter через KVC с optional `NSURLRequest`; отсутствующий адрес остаётся nil, проверки доверенного адреса не ослаблены.
- Временные маркеры удалены. Сетевые очереди исходные. Реальный регрессионный тест сохраняет HTTP, WKFrameInfo, JS confirm и Return/Escape. Требуется повторная диагностика Swift 6.0.3.
- Локальный regression run: 39 XCTest PASS, 8.031s (`EmbeddedCabinet|DesktopMeetingShellWebViewBoundary`); обновлено устаревшее source assertion на тот же guard с optional адресом. Governance и whitespace PASS.
- Ponytail review: временная диагностика workflow удалена после получения стека; один getter для восьми потребителей, без новых зависимостей.

- Диагностика 34000870450 устранила crash и выполнила 801 XCTest, но реальный confirm не вызывал delegate: Swift 6.0.3 предупреждал `nearly matches optional requirement` из-за новых `@MainActor @Sendable` аннотаций completionHandler. Применён существующий в этом файле шаблон typealias для старого/нового Swift, как у navigation и file picker. Обход или исключение теста не используется.
- Серверный Full CI 33999768481: 3900 PASS, 5 FAIL, 36 skipped. Причины: старые подписи календаря, запрет нового focus target итогов, удалённый неиспользуемый privacy macro, старое CSS-ожидание 46px. Проверка аналитики теперь использует реально отрисованный body с четырьмя masking attributes и разрешённым autocapture; runtime evidence проверяет действующие вкладки >=44px вместо наличия произвольного 46px в файле. Это актуализация проверок принятого F240/F243, не изменение производственного server-кода.

- Итоговые focused проверки: 63 server tests PASS в изолированной PostgreSQL, 68.73s; контейнер удалён. 39 macOS tests PASS, 7.964s. Новая диагностика старого Swift и authoritative Full CI остаются обязательными.
