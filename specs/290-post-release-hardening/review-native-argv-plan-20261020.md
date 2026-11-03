# F290 T014: независимое ревью плана исправления argv

Дата: 2026-10-20. Reviewer: `review_f290_infra`.
HEAD: `cff973e67fe3e9fa0ffcbb145d04873d6b861cb8`.
Режим: существующий **high-risk-product**, уточнение активного среза FR004.

## Решение до реализации

**PASS плана T014 для одной замены `CommandLine.arguments` на
`ProcessInfo.processInfo.arguments` в существующем async main.** Новых
неустранённых замечаний к этому ограниченному плану нет. Это не PASS ещё
не изменённого кода и не завершение T005: настоящая сборка Apple Swift6.0.3
и три обязательные проверки нового точного PR SHA остаются необходимыми.

Разрешённая область реализации: только
`apps/macos/Shared/Tools/MeetingMuteTruthRuntimeProof/main.swift`, одна строка
получения аргументов перед существующим `RuntimeProofConfiguration`.
План и T014 явно задают эту область, зависимость T014 → T005 и дальнейшее
независимое ревью. `.specify/feature.json` уже содержит дополнительный owned
path; до изменения кода рассогласования указателя и плана нет.

## Подтверждённая причина

Заново прочитаны API run/jobs и сохранённый журнал GitHub run
`39257189895`, attempt1, event pull_request, workflow `macos-pr`, source
`cff973e67fe3e9fa0ffcbb145d04873d6b861cb8`. Run завершился failure.
`Determine native scope` и `Select installed Swift 6.0.3` — success;
`Build and validate native contracts` — failure. Итоговая required job
`macos-pr` также отказала, не скрыв отсутствие успешной сборки.

Журнал указывает одну соответствующую ошибку в main.swift:8:
`reference to static property 'arguments' is not concurrency-safe because
it involves shared mutable state`; stdlib показывает изменяемую static
`CommandLine.arguments: [String]`. Это не отказ выбора toolchain и не
основание менять Swift/SDK, исключать target или смягчать строгую проверку.

SHA256 `hosted-native-failed.log`:
`4d66f166c9a98a9eaf5a54dff79f332dc66a033180ded5c7bd477cf2b21eb7df`.

## Семантика и границы изменения

Полностью прочитаны main.swift, Package.swift и существующий shell caller
`validate-meeting-mute-truth.sh`; проверены все CommandLine/ProcessInfo и
RuntimeProofConfiguration callers в apps/macos. В targets пакета это
единственное такое чтение в async main. Остальные найденные CommandLine —
в отдельных синхронных scripts; их изменение не входит в T014.

Foundation уже импортирован. Публичное `ProcessInfo.processInfo.arguments`
предоставляет массив аргументов текущего процесса; нового parser, зависимости,
actor, Task, unsafe доступа или `@preconcurrency` не требуется. У текущего
RuntimeProofConfiguration один caller; разбор начинается с `index = 1`.
Сохраняются `--default-store`, `--output-root` с отдельным значением,
`--help`/`-h`, ошибки отсутствующего значения/неизвестного параметра и
создание URL существующим способом. Присваивания/мутации CommandLine.arguments
в apps/macos не найдены.

Точное уточнение к словам плана «тот же argv»: не требуется побайтное
равенство **нулевого** элемента. В прочитанной реализации Swift Foundation
6.0.3 `_ProcessInfo.arguments` получает CommandLine.arguments под LockedState
и может заменить argv[0] полным путём программы. Этот элемент parser
игнорирует; аргументы с индекса1 и их разбор сохраняют смысл. Поэтому замена
эквивалентна **для этого инструмента**, без общего утверждения о равенстве
всех массивов или о поведении произвольного потребителя argv[0].

Прочитанный upstream:
[Swift Foundation 6.0.3 ProcessInfo.swift](https://github.com/swiftlang/swift-foundation/blob/swift-6.0.3-RELEASE/Sources/FoundationEssentials/ProcessInfo/ProcessInfo.swift),
SHA256 `041c728bc529f03f3047020c00e77a717dc46d033a19a32988ed23c029a361a5`.
Там `_ProcessInfo: Sendable`, singleton static let и защищённое чтение state.
Это обоснование выбранного стандартного API, а не доказательство конкретных
аннотаций установленного Apple SDK или успешной компиляции на hosted image.
Последнее должен подтвердить предусмотренный настоящий build.

Остальная синтетическая запись/пауза/возобновление/остановка, validation
manifest, capture paths продукта, actor isolation и Swift6 language mode
не меняются. Не запускать runtime-proof ради проверки argv и не создавать
приложение вне единственного GRAF Dev; T014 достаточно адресной проверки
входа/типов и настоящей сборки пакета в CI. Локальный Swift6.3.3 может дать
лишь диагностическую проверку, он не заменяет Apple Swift6.0.3.

## Применимые списки требований

Шесть пунктов requirements перечитаны: исходные три результата/разделение
срезов сохранены; отказ сборки измерим и остаётся отказом; права и этапы принятия
разделены; отсутствие новой продуктовой неоднозначности объяснено выше;
исходные критерии и границы readiness не меняются. **6 checked / 0 unchecked**.

| Пункт infra | Применимость и основание сохранения отметки |
|---|---|
| CHK001 | Контекст: T014 не подменяет stash и четыре post-deploy результата или принадлежность F238/F290. |
| CHK002 | Контекст: Actions pins/runtime не меняются. |
| CHK003 | Прямо: ошибка остаётся failure; новая строка требует собственного exact SHA/base/run/attempt и всех трёх обязательных checks. |
| CHK004 | Прямо: сохраняются Swift6.0.3, Apple build, SDK и отдельный cache namespace. Исправляется несовместимое обращение в исходнике. |
| CHK005 | Контекст: selector уже прошёл; прежние fail-closed условия до GITHUB_PATH сохраняются. |
| CHK006 | Прямо: local typecheck не Apple6.0.3; будущие build/tests/ContractValidation и общий validator остаются T005. |
| CHK007 | Контекст: macos14 retirement и отдельная миграция image не отменены. |
| CHK008 | Контекст: stash, index/untracked и работа другого владельца не затрагиваются. |
| CHK009 | Контекст: backup/retention/restore и права удаления не меняются. |
| CHK010 | Контекст: четыре US3 результата и cleanup mapping не затрагиваются. |
| CHK011 | Контекст: T014 не разрешает synthetic production запись или inventory write. |
| CHK012 | Прямо: в отчёт входят исходный диагностический текст, source/run и digests; содержимое встреч/credentials не требуется. |
| CHK013 | Прямо: до кода есть ограниченный plan/T014/owned path и независимое review; после кода — повторное review/validation, без нового сервиса или обхода строгой проверки. |

Infra перечитан: **13 checked / 0 unchecked**. Новых отметок исполнения
hosted/production не добавлено; прежние отметки качества требований сохранены.

## Что требуется после правки

Повторно проверить, что diff кода состоит из одной заявленной замены,
RuntimeProofConfiguration/синтетика/Package.swift/параметры compiler не
менялись. Выполнить предусмотренную адресную диагностическую проверку и
настоящую hosted build/XCTest/ContractValidation нового source. Отказ
следующего compiler этапа сохранять как отказ, не обходить проверку.
Три текущие PR-проверки должны пройти общий `validate-pr-checks.py`.
После переноса на свежий master сохранить F263 и заново проверить результат
совмещения; прежние proof нового SHA не покрывают. T005, US2/US3, #6501/#7646
этим предварительным решением не закрываются.

Код до реализации не менялся; SHA256 main.swift:
`be555098afe92b2e0ec829462874593cb44ca4c4c6f6312d3be2b3e26720edd0`.
Проверяющий менял только оба reviewer-owned checklist и этот новый отчёт;
код/spec/plan/tasks/pointer, Git/GitHub state, приложение, сервер и данные
не менял. Тесты, приложение и сборки reviewer не запускал.
