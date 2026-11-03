# F290 T015: независимое итоговое ревью двух замыканий Optional.map

Дата: 2026-10-21. Reviewer: `review_f290_infra`.
Режим: существующий **high-risk-product**, FR-004 / SC-001, T015 → T005.
Ветка: `290-post-release-hardening`.
HEAD: `6fa375205449c551a81d7166ecbdc597a77d31b2`.
Проверенная merge-base: `845e6dcff7eb7f8e0e2b884902080ecb96582a3a`.

## Решение

**APPROVE локального изменения T015. Замечаний к двум заменам — 0.**

Рабочие байты App совпадают с согласованным планом. Проверены содержимое
diff, сигнатуры и все места вызова, прежние проверки свежести и текст,
реальная выборка XCTest и окончательные validation.md/F290.yaml.
Локальные журналы подтверждают сборку самого executable target и выбранные
58 XCTest. Они не подтверждают результат нового Apple Swift6.0.3 в GitHub.
T005/T014/T015 остаются открытыми до настоящей hosted приёмки.

Это ревью локальных незакоммиченных байтов: приведённый HEAD сам по себе
не идентифицирует новый App. Проверенная SHA256 App:
`812664a5503fe9aba977f4287e9a3a14eebae0dc2a80474a3aca8e4d6b13649d`.
До T015: `796887841384370e22c67a857c83f90db1efa37494db1a21038f605d684b6b0a`.

## Проверенный diff и поведение

В `apps/macos/RecApp/App/TwoBrainRecApp.swift` изменены ровно две строки:

```swift
sourceAppIsCurrent: meetingDetectionTarget.map { isCurrentMeetingDetectionDecision($0) } ?? true,
let action = snapshot.recoveryAction.map { recoveryActionText($0) } ?? "Проверьте состояние перед записью"
```

Оба метода не объявлены `throws`. Замыкания синхронные, не создают Task,
не вводят `await`, не меняют обработку ошибок и выполняются в прежней
области `@MainActor` типа ContentView. Аннотации actor, strict concurrency,
Package.swift, Swift/SDK и workflow не менялись в T015. Новых try/try?,
nonisolated/unchecked, helpers, зависимостей или обходных параметров нет.

У первого Optional nil сохраняет true без вызова метода; some вызывает
тот же метод один раз. Возвращённый false остаётся false. У recoveryAction
сохранены прежние nil fallback, таблица известных действий и default для
неизвестной строки. Пользовательский текст не изменён.

Заново просмотрены четыре места вызова isCurrentMeetingDetectionDecision:
1900 до запуска, 2022 в map, 2095 после systemAudioCaptureService.start,
2120 после localRecordingWriter.startAsync. Последняя проверка остаётся
перед markCapturing/acceptStart без новой точки приостановки. Внутри метода
сохраняются сравнение текущего решения, authEpoch/presentationEpoch и отказ
при pendingStopBundleID того же приложения. Единственный вызов
recoveryActionText остаётся в recordingBlockerText:3049; последний
используется при отказе предварительных условий в startManualRecording:2044.

Прочитанный MeetingDetectionAppModule.allowsPendingStart по-прежнему
возвращает `decisionIsCurrent && pendingStopBundleID != bundleID`.
Проверка не заменена константой и не перенесена через await.

## Проверки и пределы доказательств

Ревьюер не запускал сборки, тесты или typecheck повторно. Он прочитал
сохранённые журналы и подсчитал уникальные успешные XCTest по их полным
идентификаторам. Прочитанные исходники проверок совпадают с плановым ревью.

| Источник | Подтверждённый результат |
|---|---|
| native-map-build.log | Компиляция TwoBrainRecApp.swift, emission, linking и Applying TwoBrainRecApp; `Build of product 'TwoBrainRecApp' complete! (24.03s)`. В журнале нет `error:`, предупреждения присутствуют. |
| native-map-focused.log | 58 разных успешных XCTest: CaptureControlTests 49, DesktopNotificationAppIntegrationTests 6, MeetingDetectionRecordingLifecycleTests 3; 0 failures, нет skipped; Selected tests завершён за 2.465s. |
| workflow-tests-rebased.log | 300 passed за 73.70s; FAIL/ERROR/SKIP в итоговой сводке нет. Этот набор обновляет прежние 275 и не суммируется с ними. |
| native-map-process.log | agent-context, changelog-fragments, legacy-impact и development-process: OK. |

Имя класса CaptureControlTests подтверждено файлом
CaptureControlV5Tests.swift. Нулевая выборка не засчитана: в журнале
есть 49 разных успешных методов этого класса. Заключительное сообщение
Swift Testing о 0 тестах относится к другому пустому runner и не отменяет
исполненные 58 XCTest. Повторные сводки Selected tests не удваивают число.

Package.swift выделяет TwoBrainRecApp в executable target `RecApp/App`,
исключённый из AppCore. Lifecycle и notification source-integration проверки
дополняют реальные capture tests, но сами по себе не доказывают компиляцию
App или реальные разрешения устройств. Поэтому отдельно проверен журнал
настоящей сборки TwoBrainRecApp.

Validation указывает локальный AppleSwift6.3.3/arm64-apple-macosx26.0;
это метаданные исполнителя. Ревьюер не воспроизводил выбор compiler и не
выдаёт локальный журнал за квитанцию exact-SHA hosted выполнения. Заявленные
исполнителем дополнительные actionlint/workflow/governance результаты не
запускались ревьюером; process log подтверждает только перечисленные в нём
проверки. Установка, запуск GRAF Dev, ручная запись и работа production
в это ревью не входят. Исполнитель сообщил очистку собственного scratch
после завершения проверки; ревьюер сборочные каталоги не изменял.

Сохранённый apple-swift-603-second-failure.log прямо содержит прежние две
ошибки `call can throw`/`rethrows` на строках2022/3049 и exit1. План связывает
его с run39586205761/source c137a55379d577c818a8510035ea8f03bfefcf46;
повторного API-запроса run/jobs в этом ревью нет. Исходный отказ сохраняется.
Новый точный PR SHA/checked base должен получить настоящие AppleSwift6.0.3
build, все XCTest, ContractValidation, governance-fast, macos-pr и pr-metadata
с успешным общим validate-pr-checks.py. Локальный PASS этого не заменяет.

## Требования, полномочия и остаток

Текущие spec/plan/tasks/quickstart и окончательные validation/fragment
согласованы: T015 ограничена совместимостью FR004/SC001; T005/T014/T015
остаются открытыми. По validation и сообщению основного агента analyze
CRITICAL0/HIGH0/MEDIUM0 и синхронизация T014/T015 с #6501 выполнены до кода.
Внешнее GitHub-состояние ревьюер заново не запрашивал и не менял.

Полномочия пользователя на проверенную работу с Git действуют. В requirements
устаревший пункт о раздельных согласиях заменён на определённые полномочия
Git и отдельные границы выпуска, production и удаления сохранённой работы;
объяснительный абзац со старой трактовкой также заменён. Новое согласие
на уже разрешённые действия этот список не требует. Ревьюер не выполняет Git
операции, слияние, выпуск или изменение production.

Повторно проверены все 19 пунктов как качество требований:

| Пункты | Основания сохранения отметок |
|---|---|
| requirements 1–3 | FR001/SC004 и три независимых US сохранены; FR/SC определяют измеримые результаты и честные отказы; первый CI-срез ограничен. |
| requirements 4 | FR010/plan/tasks задают полномочия Git после проверки и отдельные границы выпуска/production/удаления; формулировка исправлена. |
| requirements 5–6 | T015 не требует нового продуктового решения; неизвестные серверные факты исследуются в T006/T009–T011; SC001/004 и открытые задачи не скрывают остаток. |
| CHK001–002 | FR001/SC004 сохраняют три результата #6501 и F238; FR002/research задают точные Node24 commits, которые T015 не меняет. |
| CHK003–005 | FR003/004, T005, plan/quickstart сохраняют SHA/base/run/attempt, AppleSwift6.0.3/SDK/cache границы и отказ selector до GITHUB_PATH. |
| CHK006–007 | План явно разделяет локальную диагностику, hosted, merge и release; ограничение macos14/2026-11-02 сохранено. |
| CHK008–009 | FR005/006, T006–T008 и US2 quickstart сохраняют index/untracked/чужую работу, failure/concurrency/restore и отдельное согласие на удаление. |
| CHK010–011 | FR007/008, data-model и T009–T011 задают четыре разных результата, cleanup_result mapping, синтетику, пишущий inventory и отдельные production действия. |
| CHK012–013 | FR009–011 ограничивают evidence метаданными, сохраняют review/analyze/sync/validation/closeout порядок; новых служб, обходов и зависимостей нет. |

Оба списка полностью перечитаны после правки: requirements **6 checked /
0 unchecked**, infra **13 checked / 0 unchecked**, всего **19/0**. Это не
подтверждает исполнение US2/US3 или приёмку всей F290. Существующие
T006–T013 и #6501/#7646 остаются открытыми. Миграция после macos14 retirement,
Full нового frozen candidate, выпуск/production и installed acceptance
сохраняют собственные условия. Новых обязательных кодовых задач для двух
замен не обнаружено; существующие остатки не дублируются.

## Контрольные суммы

Журналы находятся во внешнем каталоге
`/Users/yshishenya/Documents/Codex/2026-10-21/f290-pr-closeout/`.

| Источник | SHA256 |
|---|---|
| native-map-build.log | `153b29c9e91808452f462dd2940d8bbddf7584cd4427074f37d813f0a24f75f3` |
| native-map-focused.log | `6630896681c2ac5b6f8d2999a51b16143f2b08f7314513a41fcd7cda33a61f7e` |
| native-map-process.log | `dd9ca59b66450faffecadb9fb16f318ebbcdc027bf6279ccc7b558fb02f4ebeb` |
| workflow-tests-rebased.log | `26c82146e438bf050eb4748b2ab5fbf0a93637944b0ceefade2a43991e78619d` |
| apple-swift-603-second-failure.log | `ec39775696a12919092751a3a0ce04096c55eed066ed78713cee4d02b6b74b78` |
| spec.md | `f30b3e407e7d900ff8517a0dc022ee04a41fee57ae9c236e2587ee3c0fa485e5` |
| plan.md | `732d18600f90e96e49f244ad9c2805aa441bfdc5b4be3b3c78ea8ab0f04faf65` |
| tasks.md | `c9a0295dba44bfc44522ca75b0d3f3a60f4e0abc89a9c40c4b594f7f38133592` |
| quickstart.md | `c5a8b562fdbd9a901d1cc772d4ef341c89568c0c99fe24619d114cd8727870fe` |
| validation.md | `d3116ade32d3722141dcacb4513935ed2ed6a9567ab7a93943e112bce1a99322` |
| changes/unreleased/F290.yaml | `f56b1480ca559399220d7a60a95cba40eb93ae84be3e641838d67adfb00a7349` |
| apps/macos/Package.swift | `00be33a568134c2addbd2d14a722c4fbb9accf54b915862293373e8cb753eca7` |
| .github/workflows/macos-pr.yml | `5aa2a59ec9d8e5036305e271818ebd0dbb70a587d2c56900f3b6060af228d942` |
| CaptureControlV5Tests.swift | `90ae086a0524f8639828e3b721f082c9b17dd46f92802e80a39a4d4bea69ac9e` |
| MeetingDetectionRecordingLifecycleTests.swift | `b1647b1d68d79d2efbbfc195192e0ce80c15d06055ea4c7b3632bd7ee80a4c3c` |
| DesktopNotificationAppIntegrationTests.swift | `1e4db5acc5fb57d640a3b8a164b90cb85fe8ba420f8d6ccd02a3e90f32f9d43d` |
| MeetingDetectionAppModule.swift | `95f27d00b49c6f1e9ca28725d21e33f378e260d9438c46ad7a1ffc7bb9cf4998` |

Reviewer изменил только requirements.md, infra.md и этот новый отчёт.
Код, spec/plan/tasks, pointer, validation, fragment, Git/GitHub, приложение,
данные, release и deploy не изменялись reviewer. Проверка оформления —
git diff --check; повторные тесты для этих документальных изменений не нужны.
