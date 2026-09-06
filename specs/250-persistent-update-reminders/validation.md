# Результаты проверки — Feature 250

Дата: 2026-09-06. Ветка: `250-persistent-update-reminders`. Базовый HEAD: `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`. Локальные проверки ниже выполнены до коммита; этот базовый SHA не является SHA реализации. Окончательный SHA и результат GitHub governance-fast фиксируются в PR.

## Требования и исследование

- Spec Kit: specify → clarify (0 обязательных вопросов) → plan → checklist → tasks → analyze → taskstoissues → implement → converge.
- Независимая проверка требований: `sparkle_practices`, checklist 7/7; итог CRITICAL 0, HIGH 0, MEDIUM 0, LOW 0. Рецензент отдельно уточнил исключения из четырехчасового расписания и однократную миграцию интервала.
- GitHub issue canon ensure/validate: PASS, 7 task issues и umbrella #6644. Issues остаются открыты до проверки PR и точного SHA; локальное выполнение не выдается за слитую/выпущенную реализацию.
- FR-001/008: AppUpdateNotice, main-window safeAreaInset, CalendarTrayView/controller и динамический пункт меню. FR-002–004: кэш и reducer/callback tests. FR-005: 14400 в builder/config, совместимость validator с 86400, запуск и migration. FR-006/007/009: единый Sparkle, прежние trust/relaunch/main-frame ограничения и тесты.

## Автоматические проверки

- Исходные AppUpdateControllerTests до изменений: 11 PASS.
- Новые тесты до реализации: ожидаемые ошибки отсутствующего API/нового поведения, затем исправлены реализацией.
- Focused suite: `AppUpdateControllerTests|EmbeddedCabinetUpdateBridgeTests|DesktopCalendarReminderTests|InstallerLifecycleEvidenceTests` — 68 PASS.
- Финальный AppUpdateControllerTests после улучшения доступности: 18 PASS.
- `swift build --package-path apps/macos --product TwoBrainRecApp` — PASS.
- `GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast` — PASS, 133 секунды: 808 macOS tests, 224 governance tests, 66 CI contract tests; ContractValidation PASS; shell syntax, compose config, legacy guard, deployment evidence scan и whitespace PASS.
- Диагностическая запись: `.dev/ci-evidence/ci-fast-6ff8db3ee18d-1f8c3c0f5503.json`. Status `ambiguous` намеренно сохранен из-за незакоммиченных изменений; это не доказательство exact-SHA, merge eligibility или release readiness. Coverage `partial`, next gate `full_before_release`.
- Обычный fast без opt-in остановился на dirty_worktree. Затем preflight обнаружил неполный ignored feature pointer/Legacy Impact; они исправлены до успешного запуска. Ограничения выпуска не отключались.
- Существующие предупреждения Swift о WebKit `@preconcurrency` и предупреждение deprecated initializer Sparkle в синтетическом тесте не скрыты; production не использует deprecated initializer.

## Интерфейс

- ImageRenderer: 12 изображений штатного AppUpdateNotice, 360/900pt × light/dark × available/deferred/failed. Геометрические проверки PASS. Визуально проверены светлый узкий и темный широкий варианты; текст и кнопка не обрезаны.
- Отдельный нативный тестовый процесс с синтетической версией: через CUA подтверждены отображение версии, доступное имя кнопки, один вызов действия по нажатию и по ⇧⌘U. После явного accessibility container macOS видит отдельные `graf.appUpdate.notice` и `graf.appUpdate.open`.
- Изолированный preview находится в ignored `.dev/update-preview/`; рабочие GRAF/GRAF Dev не заменялись. Только синтетические данные, без записи/аккаунта/установки. Тестовый процесс остановлен.
- Реальное нажатие значка строки меню при закрытом главном окне и полный VoiceOver speech walkthrough не заявляются пройденными; структура и подключение меню проверены кодом/сборкой, перед публичным выпуском нужен живой smoke.

## Converge и границы выпуска

Реализация FR-001–009 покрыта существующими и новыми путями, новых обязательных кодовых задач не найдено. Ponytail review: удалены лишние фазовые условия и повторная ветка skip/dismiss; новых зависимостей, таймеров, собственного установщика и API нет. Границы кэша и подписанного источника сохранены.

Публичный appcast прочитан без изменения: HTTP 200; на момент проверки две записи, 2026.09.06.1 и 2026.09.04.1. Это проверка доступности опубликованного списка, не проверка подписи нового кандидата.

На момент локальной проверки коммит/PR и GitHub governance-fast на SHA реализации еще не выполнялись; их итог фиксируется в PR. Перед выпуском остаются: release-full; Developer ID packaging/notarization/stapling/Gatekeeper нового кандидата; живой подписанный переход предыдущая→новая версия, сохранение TCC-разрешений и отсрочка реальной записи; публикация. Для публикации требуется отдельное разрешение; проверки выпуска выполняются на замороженном кандидате. Пользователи получат новую логику только после установки такого выпуска.
