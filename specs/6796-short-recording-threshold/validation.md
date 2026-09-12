# Проверка реализации F6796

Lane: high-risk-feature (capture/storage/deletion/UX), полный Spec Kit. Ветка codex/6796-short-recording-threshold, база ad71f2ce4db68d846d7c333213961c5f5f7d5e89. Реализация пока без коммита; CI SHA отсутствует.

## Локальные проверки

- `swift test --package-path apps/macos --filter 'ShortRecording|LocalRecordingWriter|CaptureRecoveryService|DesktopUploadQueueTests'`: PASS, 95 тестов, 0 ошибок. Включена реальная финализация 30 секунд синтетического аудио, 480000 кадров WAV и ненулевые первые кадры.
- `swift build --package-path apps/macos --product TwoBrainRecApp`: PASS; приложение не запускалось.
- `git diff --check`, `validate-changelog-fragments.py`: PASS.

- Требования: requirements 6/6, safety 8/8, независимый analyze PASS; GitHub issue canon PASS (300 задач проверено).
- Порог: 479999/480000/480001 кадров, обе штатные причины, неизвестная частота/кадры, авария, отсутствие новой причины у старого вызова.
- Writer: решение записано вместе с финальным manifest; старый клиент видит blocked. Quit во время Stop отменяет правило до решения; после решения применяется повторяемая очистка.
- Queue: устаревший saving, маркер после перезапуска, отсутствие строки, конфликтные ID/пути/server handoff, symlink escape, повтор после частичной очистки, исторический короткий пакет. Upload client не вызывается для отклонённых пакетов.
- Уведомление: не получает фокус, заменяется, закрывается и исчезает примерно через 6 секунд. Это автоматическая проверка свойств, не ручная приёмка VoiceOver/тем/Spaces.
- Governance: первоначальный отказ из-за локального specify 1.0.6 при lock 1.0.1 устранён запуском проверки с изолированным specify-cli по закреплённому ref 9118ed15a0ba65053469a94c560ea5d233f75884. Глобальная установка и lock не изменены. check_spec_kit_governance.py PASS.

## Оставшиеся этапы

T006 остаётся открытой: разрешённый коммит, PR и governance-fast на его точном SHA, затем ручная проверка через единственный GRAF Dev по quickstart. Производительность штатного Stop на установленной сборке, VoiceOver и видимость поверх других приложений ещё не подтверждены. Merge/публичный выпуск/production deploy не выполнены и не входят в текущую локальную приёмку.

Issues #6943–#6949 остаются открытыми до выполнения соответствующей приёмки. Локальные тесты не заменяют CI и выпуск.

## Согласованность после реализации

speckit-converge: проверены FR-001–FR-009, SC-001–SC-004, обе истории и пять решений плана. Недостающего/противоречащего/необоснованного кода не выявлено; новые задачи не добавлены. Подтверждение пользовательских критериев SC-004 на установленной сборке и итоговые CI/приёмка остаются в существующей T006; полного завершения feature нет.

Независимый code review: Approved, CR1 закрыт; см. code-review.md. T001–T005 завершены локально, T006 pending. Автокоммит hooks выключены; hooks converge отсутствуют.

## Продолжение до PR ready

Пользователь 2026-09-12 разрешил все действия до PR ready. Коммит реализации 8621cded103f4ba0d724aea4282a009b2e307016, PR #6950. GitHub governance-fast PASS: https://github.com/yshishenya/graf/actions/runs/34694733949 ; pr-metadata PASS. Эти результаты относятся к исходному implementation SHA; дополнение стенда требует нового CI.

T007: точный перенос только трёх файлов harness из e964bba55ed594f8bdccf94068d75fd07590c1b5 (F6793). `uv run --project apps/server --extra dev python -m pytest tests/governance/test_graf_local_adapter.py -q`: 43 PASS. Вторая функция/native settings не перенесена. Исходный shared Dev освобождён владельцем F6793; штатная сборка/установка F6796 разрешена, проверка exact SHA/lock не обходилась.
