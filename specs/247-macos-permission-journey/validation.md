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
