# F247 — результат локальной проверки

Дата: 2026-09-06. Lane: high-risk-product. Ветка: `codex/247-macos-permission-journey`. База: `107e7e692b896863f70ba632a101469d6f80e29a`. Проверены незакоммиченные изменения; это не доказательство для merge/release SHA.

## Пройдено

- Регрессионная проверка до исправления: unknown/denied/stale→granted давали ложный restart, 3 ожидаемых падения.
- `swift test --package-path apps/macos --filter 'SystemAudioPermissionUXTests|AppControlAccessibilityTests|SystemAudioCaptureServiceTests|MeetingDetection'`: 119 tests, 0 failures.
- Синтетические previews через `GRAF_PERMISSION_PREVIEW_DIR`: initial, system-audio, denied/settings, restricted, stale/recovery, ready — светлая и темная темы. Дополнительно настоящий NSHostingView/NSScrollView при 520×380 pt: прокрутка до подсказки и кнопки «Позже», обе темы. 16 изображений (включая верх/низ прокрутки). После добавления scroll assertion отдельный render test прошел.
- `swift build --package-path apps/macos`: passed.
- `python3 scripts/check_spec_kit_governance.py`: OK, bootstrap integrity + GRAF invariants.
- `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py`: OK, 300 open Spec Kit issues checked.
- `git diff --check`: passed.

## Проверенные свойства

ОС остается источником прав; история только выбирает CTA. Следующий missing шаг; нет запросов в общем start. Refresh не открывает/закрывает sheet. SCShareableContent доступен только после granted preflight, callback ограничен 8 секундами и завершается один раз. После callback проверяется отзыв. Request/probe не пересекаются. Settings не ставят recovery flag. Успешная functional проверка снимает stale. Runtime error не объявляется отказом в правах автоматически. Restart учитывает protected work и busy, при отсутствии relaunch delegate показывает инструкцию без внезапного завершения.
При входе в настройку старый ask закрывается без skip, outcome retryable; queued и новые detector starts закрыты общим guard. После закрытия действуют прежние правила, включая Всегда для текущей встречи и полный 8-секундный ask. UI об этом сообщает.
Дополнительная помощь покрывает unknown с историей: приложение отсутствует в списке → явный повторный системный запрос; доступ включён, но не действует → повторная проверка / необязательный защищенный перезапуск.

## Code review / Ponytail

Проверены все измененные вызовы start, refresh, Settings, restart, detector decisions; нет изменений протоколов, аудиозахвата или правил автозаписи. Убраны лишние observe/restart transition, async-обертка Settings, повторяющаяся кнопка настройки рядом с основной CTA. Новых зависимостей нет. Малый completion с NSLock необходим для callback, который может не прийти; structured task group здесь не гарантировала бы выход.

## Convergence

$speckit-converge: buildable требования FR-001–010 покрыты; новых отсутствующих частей реализации не обнаружено. tasks.md не расширен дублирующими задачами. Существующая T005 остается открытой из-за оставшегося validation gate. Реализация локально готова к review, выпуск не разрешен этим документом.

## Непройденные / отложенные проверки

`infra/scripts/ci-local.sh --fast` завершился до стадий: `ci_evidence_status=ambiguous`, `reason=dirty_worktree`. Контроль не обходился; временный commit не создавался. Для exact-SHA CI нужен отдельный разрешенный commit, затем GitHub governance-fast / предусмотренный локальный fallback. Full CI, PR, commit, push, merge, notarization и публикация не выполнялись.
Реальная выдача/отзыв TCC, чистая установка, MDM, физически отсутствующий микрофон и VoiceOver не проверялись на пользовательском Mac. Unit/source assertions и синтетические native snapshots не доказывают эти сценарии. Acceptance matrix в quickstart.md остается обязательной перед выпуском. Существующая установленная GRAF не заменялась; пользовательские разрешения не менялись.

## Продолжение реализации и подготовка PR

Пользователь явно разрешил commit и PR после представленной локальной проверки. Штатный диагностический режим `GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast` позволил выполнить проверки без приписывания незакоммиченным изменениям статуса exact-SHA evidence. Исправлены метаданные owned_paths в локальном feature pointer и обязательный Legacy Impact в spec.

Расширенная диагностика: 224 governance tests passed; 796 macOS XCTest tests, 1 skipped, 0 failures; Swift build passed. Найден и исправлен устаревший ContractValidation, требовавший прежних permission prompts после preparing и безусловного restart. После исправления `swift run --package-path apps/macos ContractValidation`: PASS. Задача T006 и issue #6612 отражают это дополнение; продуктовые требования не менялись.

Собрана отдельная `apps/macos/.build/permission-journey/GRAF Local.app`; `codesign --verify --deep --strict` passed. Это локальная сборка с адресом кабинета http://127.0.0.1:8081, не публичный релиз. Существующая установленная GRAF не заменялась. После коммита требуется authoritative GitHub governance-fast; T005/T006 остаются открыты до его результата.

## Итоговый CI и convergence

GitHub `governance-fast`: SUCCESS, implementation SHA `6e457dfe34f1c82270204b61579c1bcd19f74fe1`, длительность job 1m1s. Run: https://github.com/yshishenya/graf/actions/runs/34017555088. PR: https://github.com/yshishenya/graf/pull/6613.

T005/T006 завершены. После исправления старого тестового контракта обязательных нереализованных требований не осталось; T001–T006 отмечены выполненными. Локальная подпись приложения и штатная сборка проверены. Слияние и публикация не выполнялись. Результат CodeRabbit означает skipped/manual review required, а не пройденный автоматический code review. Перед выпуском по-прежнему необходима реальная TCC/MDM/VoiceOver приемка на тестовом Mac.

## T007 — исправление после сообщения пользователя

Уточнение: прежний вывод о покрытии US3 был неполным — внешний Quit из System Settings не проверялся при открытом sheet. Исправлено: обычная страница вместо sheet, сохранение явно открытого процесса настройки в AppStorage до Позже/Готово, подсказка о системном перезапуске. Закрытие приложения сохраняет намерение; новый процесс проверяет права заново. Скрытый кабинет недоступен для ввода/VoiceOver, его нативные кнопки заголовка учитывают isEnabled. Новых разрешений/зависимостей нет.

Проверка окончательного кода локально:
- 119 профильных XCTest, 1 optional preview skipped, 0 failures; отдельный preview test прошёл без пропусков (16 светлых/тёмных снимков, реальная прокрутка при 380 pt).
- Swift build / отдельный GRAF Local.app, ContractValidation и Spec Kit governance прошли.
- `test-permission-restart.py`: настоящая отдельная копия приложения, стандартный Quit Apple Event; два запуска, `modal=false`, `sheets=0`, штатная очистка `cleanup_finished`, exit=0, 0,62 / 0,39 секунды. Запуск второй копии процесса сохранил страницу настройки без передачи launch overrides. Резервный 10-секундный таймаут не использован.
- Нативный интерфейс отдельной локальной копии проверен через CUA: Готово → основная страница → Cmd+Q → запуск без настройки; Подготовить запись → Позже → Cmd+Q → запуск без настройки; повторный вход и Escape работают. После последней правки кнопки Home/Back/Reload исчезают из интерфейса/дерева доступности на время настройки и возвращаются после выхода.
- Ponytail review: переиспользованы основной NSWindow, AppStorage и existing isEnabled; отдельный контроллер окон/служба восстановления не понадобились. Проверены все три пути выхода: внешний Quit, собственный restart, явное завершение настройки.

Реальный TCC grant и кнопка «Завершить и открыть снова» в System Settings на установленном Developer ID приложении пока не проверены. Нативный Apple Event тест проверяет доставку внешнего Quit/очистку/новый запуск, но не подменяет эту приёмку. Подписанная публичная сборка, MDM, полноценная VoiceOver-приёмка и release-full остаются отдельными release gates. Установленный GRAF и пользовательские права не менялись.

T007 реализована, issue #6625, PR #6613. Обязательный governance-fast должен подтвердить новый точный PR SHA; прежний CI не является доказательством этой правки.

## T008 — пользовательский язык, иерархия и возврат

Свежие снимки исходного SwiftUI показали перегруз: две большие карточки, служебная сводка, несколько действий и длинная помощь одновременно. Реализован один текущий шаг с объяснением пользы, компактный прогресс, контекстные инструкции, одна главная кнопка и постоянно доступный выход. Busy request и passive checking различаются; restricted предлагает выйти и обратиться к администратору. Восстановление сохранено под «Не получается?».

Проверено локально на окончательном коде:
- 119 профильных XCTest, 0 skipped, 0 failures (preview включён). 20 нативных снимков через NSHostingView: initial, system audio, denied/settings, compact top/bottom, restricted, recovery, ready, waiting, checking в обеих темах. При 380 pt footer остаётся вне прокрутки.
- Swift build, GRAF Local.app, ContractValidation и Spec Kit governance: PASS.
- Quit Apple Event proof: два запуска настоящей отдельной копии, modal=false/sheets=0, cleanup_finished, exit=0 за 0,49 / 0,23 секунды; незавершённая настройка восстанавливается.
- CUA на отдельной копии: первый шаг, раскрытие помощи, переход в System Settings, сохранение первичного запроса после раннего перехода в настройки, явный запрос микрофона и понятное ожидание, Настроить позже → Подготовить запись → возврат к тому же ожидающему запросу без второго запроса, Cmd+Q → cleanup_finished. Найденную блокировку повторного входа исправили: busy блокирует действие записи, но не вход в настройку.
- CUA запретил доступ к защищённому UserNotificationCenter. Системный allow/deny не выполнялся; разрешения тестовой копии не выдавались. Escape во время системного запроса не подтвердил выход (системный диалог может перехватывать клавиатуру); кнопка Настроить позже и Cmd+Q проверены. Доступность внутри GRAF подтверждена деревом и действиями, но полной VoiceOver приёмки нет.

Ponytail/code review: сохранены существующие callbacks, SF Symbols, цвета/кнопки, AppStorage и lifecycle. Новый isChecking только различает два существующих вида ожидания. Главный маршрут зависит от статуса/истории, а не от раскрытой подсказки: открытие помощи не лишает пользователя первичного запроса. Без новых зависимостей и изменений аудиосервисов.

T008 / #6627 реализована; обязательный governance-fast должен пройти на новом точном SHA PR #6613. Публичный выпуск, настоящее TCC allow/deny/Settings restart, MDM и VoiceOver остаются отдельными gates.

Финальный визуальный проход T008: стандартный secondary в светлом снимке дал RGB 128 на белом фоне (около 3,95:1). Пояснения получили адаптивный primary с непрозрачностью 0,75; повторный native render проверяет усиленный контраст. Это локальное улучшение текста, не утверждение о полной доступности всего приложения.
Повторный рендер: основной цвет пояснения RGB 93 на 255 в светлой теме (6.58:1) и RGB 173 на 31 в тёмной (7.34:1); 119 тестов, включая все native previews, прошли повторно.
