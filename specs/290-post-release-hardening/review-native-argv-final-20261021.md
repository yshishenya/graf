# F290 T014: независимое итоговое ревью локальной правки argv

Дата: 2026-10-21. Reviewer: `review_f290_infra`.
HEAD: `cff973e67fe3e9fa0ffcbb145d04873d6b861cb8`; правка пока в рабочей копии.
Режим: существующий **high-risk-product**, FR004, T014 → T005.

**APPROVE локальной правки T014. Findings: 0.** Реализация соответствует
принятому плану одной строки. Это не завершение настоящей hosted приёмки
T014/T005 и не подтверждение готовности всей F290.

## Проверка исходника

Полностью перечитаны main.swift и предварительное независимое ревью
`review-native-argv-plan-20261020.md`; повторно прочитаны уточнение plan,
T014 и оба списка требований. Текущий указатель F290 содержит дополнительный
owned path, исходный SHA согласован с HEAD. Применён прежний `code-reviewer`.

Побайтовая проверка подтвердила: текущий main.swift получается из HEAD
**ровно одной** заменой
`RuntimeProofConfiguration(arguments: CommandLine.arguments)` на
`RuntimeProofConfiguration(arguments: ProcessInfo.processInfo.arguments)`.
Иных отличий этого файла нет. Вызов расположен в том же месте до создания
store и первого await. Foundation был импортирован до правки.

`RuntimeProofConfiguration`, enum ошибок и весь остальной файл побайтно
неизменны. Parser по-прежнему начинает с индекса1: нормализация argv[0]
Foundation не влияет на разбор. Сохраняются --default-store, --output-root
с отдельным значением, --help/-h, ошибки неизвестного параметра и отсутствия
пути. Нет новых изменений actor isolation, unsafe API, конкурентных задач
или подмены аргументов.

Package.swift, существующий shell caller `validate-meeting-mute-truth.sh`
и все три native workflows побайтно равны HEAD. Версия Swift/SDK, выбор
toolchain, строгий режим, обязательные targets/build/tests/ContractValidation
не ослаблены. Синтетическая запись/пауза/возобновление/остановка и проверки
manifest сохранены точным сравнением всего исходного файла. Runtime-proof
и приложение reviewer не запускал.

| Источник | SHA256 |
|---|---|
| main.swift до правки | `be555098afe92b2e0ec829462874593cb44ca4c4c6f6312d3be2b3e26720edd0` |
| main.swift после правки | `311b0a42403f101b34fa1cd0df95b79280cbbd155aa151e58f55da55855c3902` |
| Package.swift, неизменён | `00be33a568134c2addbd2d14a722c4fbb9accf54b915862293373e8cb753eca7` |
| validate-meeting-mute-truth.sh, неизменён | `44962a537579edad9863cdf1707575fa6068ca007cfa3b8f8bd2eb1cc1d08e87` |

## Локальная диагностическая проверка

Прочитан завершённый протокол основного агента:
`/Users/yshishenya/Documents/Codex/2026-10-19/f290-current-preflight/native-argv-typecheck.log`.
Журнал содержит Apple Swift6.3.3, target arm64-apple-macosx26.0, команду
`swiftc -swift-version 6 -strict-concurrency=complete -parse-as-library -typecheck`
малого временного аргументного входа и терминальный **result: 0**.
SHA256 журнала:
`3149401e18adb0b3368df6060b3cedaedaf99091c944cdc147c62be41df6a685`.

Это завершённая локальная диагностика выбранного API под строгим режимом,
не сборка всего пакета, не выполнение parser/runtime-proof и не компиляция
на Apple Swift6.0.3. Протокол не содержит полного временного исходника или
его digest, поэтому reviewer не заявляет независимую побайтовую сверку этого
извлечения. Достаточность итоговой совместимости докажет предусмотренный
настоящий hosted build нового SHA. Reviewer проверку не повторял.

## Списки требований и границы приёмки

После добавления reviewer notes оба списка перечитаны:
**requirements 6 checked / 0 unchecked; infra 13 checked / 0 unchecked**.
Отметки качества требований сохранены, новых отметок исполнения не добавлено.
Все основания 19 пунктов предварительного отчёта остаются применимы:
CHK003 сохраняет точные SHA/base/run/attempt и required jobs; CHK004/006 —
Swift6.0.3/SDK и отличие локальной диагностики от hosted; CHK012 — безопасные
метаданные; CHK013 — план/owned path/review до кода и validation после.
Остальные пункты сохраняют контекст CI, stash и US3 без расширения объёма.

Следующий обязательный результат — настоящие build/XCTest/ContractValidation
и три текущих PR checks по новому source/base, принятые общим
`validate-pr-checks.py`. Исходный run39257189895 остаётся failure, а успешный
локальный typecheck его не заменяет. T014 включает настоящий native CI,
поэтому полный T014/T005 пока не объявлен PASS. При дальнейшем rebase нужны
сохранность F263 и проверка фактического совмещения. US2/US3, SE01/SE02,
#6501/#7646 этим отчётом не закрываются.

Reviewer изменил только два reviewer-owned checklist и этот новый отдельный
отчёт. Код, plan/tasks, прежний отчёт, Git/GitHub, приложения, сервер,
Docker, stash и данные не менял; тесты/сборки не запускал.
`git diff --check` пройден; это проверка оформления, не hosted приёмка.
