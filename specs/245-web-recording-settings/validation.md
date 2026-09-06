# Validation — Feature 245

Дата: 2026-09-06. Ветка: codex/245-web-recording-settings.
Base SHA: a553e3dae122084d977e2b6e52bac99354a10df5; изменения пока без commit.
Lane: high-risk-feature. Scope: только локальные правила автозаписи в общих настройках.

## Design gates

- Specify → clarify → plan → checklist → tasks → analyze выполнены.
- Clarify использует уже согласованные границы; дополнительных вопросов нет.
- Независимый проверяющий requirements: settings_contract_research,
  checklists/security-ux.md 8/8; встроенный requirements.md 5/5.
- Analyze: 10 FR, 5 задач, 100% покрытия, critical/high 0.
- GitHub task owners: #6591–6595; umbrella #6590. Issue canon PASS.
- Перед резервированием исправлено отсутствие feature:245 label; собственный
  bootstrap issue приведён к canon. Другие issues не изменялись.

## Automated evidence

- Red: новый XCTest выявил отсутствие update/bridge; pytest выявил отсутствие формы.
- Swift test: 78 passed в группах EmbeddedCabinetRecordingSettingsBridgeTests,
  MeetingDetectionPolicyTests, DesktopCabinetRoutePolicyTests,
  DesktopMeetingShellWebViewBoundaryTests.
- Новые 5 XCTest: patch между экземплярами store сохраняет соседние поля,
  bulk/unknown target, испорченный файл, запрет записи на диск,
  frame/origin/route/nonce/version/body rejection, реальный WebKit и форма.
- WebKit проверяет полный путь JS → native → временный файл, изменение по
  native notification, фокус и отзыв доступа после invalidate.
- pytest settings UI + cabinet static assets: 93 passed.
- Первоначальный запуск 6 integration checks без БД остановился на setup;
  повтор через run_local_postgres_tests.sh --focused: 6 passed, временный
  PostgreSQL-контейнер удалён. Продуктовая БД не использовалась.
- node --check, ruff touched Python test, git diff --check и
  check_spec_kit_governance.py: PASS.
- Swift build проверяет также TwoBrainRecApp. Сохраняются предупреждения
  @preconcurrency на совместимом WebKit callback boundary; ошибок сборки нет.

## Rendered UI evidence

Browser skill/plugin отсутствует, использован существующий Playwright CLI.
Loopback preview: /desktop/settings/recording и /settings/recording.
Настоящие шаблон/CSS/cabinet.js, синтетический native simulator только для
визуальной проверки; нативное применение отдельно доказано XCTest/WebKit.

- 1280×720 и 390×844: экран не пуст, название страницы верное,
  элементы не перекрываются, ошибок/предупреждений консоли 0.
- Отдельное правило → подтверждение; bulk → все четыре синтетические цели.
- Ошибка сохранения → старое подтверждённое значение и кнопка повтора.
- Timeout → сообщение о неподтверждённом результате, повторное чтение работает.
- Пустой реестр → сообщение и недоступный bulk.
- Нет handler (старый клиент) → элементы скрыты, ссылка локальной формы доступна.
- Обычный браузер → объяснение без локальных контролов.
- Скриншоты и временный runner вне git; приватные настройки не читались/не менялись.

## Review and convergence

Проверка корректности: trust boundary, все writers, подтверждение результата,
повторное чтение, lifecycle и fallback проверены. Исправлены сохранение фокуса,
порядок обновлённого списка и флаг повторного открытия уже выбранной страницы.
Ponytail review: stdlib/WebKit, прежний store, стандартные select;
новых зависимостей и универсального RPC нет. Удалён повторный invalidate.
Converge: обязательных незакрытых требований локальной реализации не обнаружено.

## Delivery boundary

Код не установлен поверх GRAF/GRAF Dev; реальные записи/настройки не менялись.
Клики меню/⌘,/шестерёнок в подписанной установленной версии и live capture
остаются проверкой выпуска; текущая проверка покрывает код/сборку и WebKit.
Commit, push, PR, governance-fast на точном PR SHA, release-full, notarization,
публикация клиента и сервера не выполнялись. GitHub issues остаются открытыми
до review/PR evidence; локальные результаты не представлены как release proof.
