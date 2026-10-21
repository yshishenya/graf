# F290 T015: независимое ревью плана двух замыканий Optional.map

Дата: 2026-10-21. Reviewer: `review_f290_infra`.
Режим: существующий **high-risk-product**, FR-004 / SC-001, T015 → T005.
Ветка: `290-post-release-hardening`.
HEAD: `6fa375205449c551a81d7166ecbdc597a77d31b2`.
Проверенная merge-base: `845e6dcff7eb7f8e0e2b884902080ecb96582a3a`.
Уточнения spec/plan/tasks/quickstart пока являются локальными изменениями;
HEAD сам по себе их не идентифицирует, поэтому ниже указаны SHA256.

## Решение до реализации

**PASS ограниченного плана T015. Новых CRITICAL/HIGH замечаний к требованиям,
согласованности и предлагаемым границам изменения — 0.**

Допускаются две замены передачи метода в `Optional.map` на явное синхронное
замыкание в `apps/macos/RecApp/App/TwoBrainRecApp.swift`:

```swift
meetingDetectionTarget.map { isCurrentMeetingDetectionDecision($0) } ?? true
snapshot.recoveryAction.map { recoveryActionText($0) } ?? "Проверьте состояние перед записью"
```

Продуктовый код до этого ревью не изменён. `git diff` рабочего файла пуст;
также нет отличий этого файла между исходным отказавшим `c137a55379d577c818a8510035ea8f03bfefcf46`
и текущим HEAD. Результат разрешает только плановый переход к реализации
после собственного analyze и issue sync основного агента. Это не доказательство
компиляции предлагаемого кода, не принятие T005/T015, не разрешение выпуска,
установки, production или закрытия #6501/#7646.

## Диагностика и граница доказательства

Прямо прочитан сохранённый фрагмент журнала
`apple-swift-603-second-failure.log`, SHA256
`ec39775696a12919092751a3a0ce04096c55eed066ed78713cee4d02b6b74b78`.
В нём `Build and validate native contracts` завершился с exit1: два
`call can throw, but it is not marked with 'try' and the error is not handled`
в TwoBrainRecApp.swift:2022 и :3049, с пояснением про `rethrows` аргумент.
Required job не скрыла отказ успешной проверкой.

План связывает этот журнал с [run39586205761](https://github.com/yshishenya/graf/actions/runs/39586205761)
на `c137a55379d577c818a8510035ea8f03bfefcf46`. Повторного API-запроса run/jobs
в этом плановом ревью не было; приведённый фрагмент сам по себе не является
новым подтверждением всех предыдущих этапов или результата argv. Причина
планируемой правки подтверждена двумя реальными диагностиками и текущими
сигнатурами методов без `throws`; устранение диагностик проверяет будущая
настоящая сборка Apple Swift6.0.3. Называть её уже успешной нельзя.

## Все места вызова и изоляция

`ContentView` помечен `@MainActor` на уровне типа (строки155–156).
`startManualRecording` и `isCurrentMeetingDetectionDecision` дополнительно
помечены `@MainActor`. `recordingBlockerText` и `recoveryActionText` —
закрытые методы того же типа; отсутствие повторной аннотации не снимает
изоляцию типа. `Optional.map` вызывает переданное синхронное замыкание
непосредственно, без нового Task, ухода в другой actor или точки `await`.

Проверены все найденные места вызова обоих методов во всём apps/macos:

- `isCurrentMeetingDetectionDecision`: прямой вызов перед началом (1900),
  единственная передача в map (2022), повторная проверка после
  `systemAudioCaptureService.start` (2095) и после `localRecordingWriter.startAsync`
  непосредственно перед markCapturing/acceptStart (2120). Все принадлежат
  одному `startManualRecording`. Три прямых вызова менять не требуется.
- `recoveryActionText`: единственный вызов через map (3049) из
  `recordingBlockerText`; последняя вызывается при отказе допуска записи
  (2044), также в `startManualRecording`.
- `evaluatedMeetingDetectionRecordingPrerequisite`: два вызова (1610,2020).
  Параметр sourceAppIsCurrent по-прежнему превращается в eligible/ineligible;
  другая проверка предварительных условий не меняется.

Метод свежести заново строит решение по настройке приложения, актуальной
активности, registry target/mode и доступности уведомления, затем сравнивает
его с сохранённым решением, включая authEpoch/presentationEpoch. Прочитанный
`MeetingDetectionAppModule.allowsPendingStart` дополнительно сохраняет отказ
при pendingStopBundleID того же приложения. Подмена проверки константой
или перенос её через `await` в план не входят.

Для nil первого Optional тело не вызывается и сохраняется true; для some
вызывается тот же метод один раз. Его false остаётся false, а не заменяется
значением `??`. Для recoveryAction сохраняются и nil fallback, и прежняя
таблица строк для известного/неизвестного непустого значения. Порядок
вычислений, число вызовов, ошибки и пользовательский текст не меняются.
Новые try/try?, async/Task, nonisolated, unchecked, compiler flags или
изменения SDK/Swift в допустимый diff не входят.

## Согласованность spec, plan, tasks и проверки

Все11 FR и4 SC повторно сопоставлены с планом и задачами как требования,
а не как исполненные результаты. FR-004/SC-001 непосредственно покрывают
T015 → T005. FR-003/009/010/011 задают сохранность доказательств, метаданных,
порядка review/analyze/sync/validation и отсутствие обходов. FR-001 и
SC-004 сохраняют полный объём #6501; FR-005–008/SC-002–003 остаются US2/US3.
Противоречий, требующих нового продуктового решения или изменения
конституции, не обнаружено. Дополнительный App owned path и source_sha
присутствуют в проверенном `.specify/feature.json`; paths-only prerequisite
возвращает ту же F290 и ту же рабочую копию.

T015 пока открыта, имеет точный путь и исходную issue #6501. Внешний ownership
T014/T015 должен синхронизировать основной агент после analyze и до кода;
настоящее GitHub-состояние reviewer не менял и не объявляет проверенным.
Историческая исходная база c6c5441… в вводных документах не выдаётся за
новую основу PR; текущие HEAD/merge-base зафиксированы отдельно выше.

План и quickstart требуют адресных lifecycle/capture проверок и настоящей
сборки App. Важно при исполнении: файл `CaptureControlV5Tests.swift`
объявляет класс **CaptureControlTests**, поэтому фильтр по несуществующему
CaptureControlV5Tests не даёт нужной проверки. Есть три теста в
MeetingDetectionRecordingLifecycleTests; не считать нулевую выборку PASS.
Полезно включить уже существующий DesktopNotificationAppIntegrationTests:
он отдельно контролирует свежесть решения после последнего await перед
markCapturing/acceptStart. Эти source checks дополняют настоящую сборку,
но не импортируют executable target и не доказывают совместимость compiler.

Критерии после реализации:

1. Проверить diff только двух выражений и сохранность всех вызовов/сигнатур,
   fallback, actor, Package.swift и compiler/SDK gates; повторное независимое ревью.
2. До сборки выполнить дисковую проверку. Диагностика в отдельном временном
   scratch-path с очисткой, без установки или запуска приложения; не создавать
   второе GRAF-приложение и не менять существующий GRAF Dev.
3. Выполнить существующие адресные lifecycle/capture тесты с непустой
   выборкой и сборку `TwoBrainRecApp`; записать compiler identity и предел
   локального Swift6.3.3. Не выдавать локальный результат за Apple6.0.3.
4. На новом точном PR SHA/основе нужны настоящий AppleSwift6.0.3,
   build, все XCTest и ContractValidation, затем governance-fast,
   macos-pr, pr-metadata и общий validate-pr-checks.py. Исходный отказ
   сохраняется, новое падение не обходится и не становится PASS.
5. Сохранить отдельными US2/US3, T005, итоговую сходимость/closeout,
   поддержку runner после macos14 retirement и выпуск/production gates.

## Повторная проверка обоих списков

| Пункт infra | Основание сохранения отметки качества требований |
|---|---|
| CHK001 | FR-001/SC-004, три US и T005–T013 сохраняют все исходные результаты и границу F238/Windows. |
| CHK002 | FR-002/research сохраняют точные commits Node24; T015 не меняет actions. |
| CHK003 | FR-003, SC-001 и T005 требуют точные SHA/base/run/attempt и прежние required checks; обходов для T015 нет. |
| CHK004 | FR-004/research/plan различают semantic6.0.3, Apple compiler build и SDK; T015 сохраняет изоляцию кэша и compiler gates. |
| CHK005 | US1/quickstart и прочитанный selector macos-pr прекращаются до GITHUB_PATH при ошибке; T015 не меняет selector. |
| CHK006 | plan/quickstart явно различают локальный Swift6.3.3 и настоящий Apple6.0.3; новый hosted результат обязателен. |
| CHK007 | Edge cases/plan ограничивают macos14 сроком2026-11-02; другого image T015 не обещает. |
| CHK008 | FR-005, T006/T007 и US2 quickstart сохраняют index/untracked и проверку чужой работы до переноса. |
| CHK009 | FR-006/T008/quickstart сохраняют failure/concurrency/restore матрицу и отдельное согласие на удаление. |
| CHK010 | FR-007/data-model сохраняют четыре результата и normalization_cleanup_result → cleanup_result. |
| CHK011 | FR-008/T009–T011 сохраняют синтетику, запрет считать пишущий inventory чтением и отдельные права production. |
| CHK012 | FR-009 ограничивает evidence метаданными; source diff и синтетическая compiler диагностика не требуют пользовательских данных. |
| CHK013 | FR-010/011, T015 и plan задают review/analyze/sync до кода, validation/review до commit и обязательные проверки до merge; новых путей/зависимостей нет. |

| Пункт requirements по порядку | Основание сохранения отметки |
|---|---|
| 1 | Полные три исходных результата #6501 и отдельная F238 сохранены. |
| 2 | Три US имеют независимую проверку; T015 ограничена native частью US1. |
| 3 | FR/SC определяют конкретные ошибки, источник/основу и обязательный новый настоящий CI. |
| 4 | Текущие spec/plan/FR-010 разграничивают общее разрешение commit/PR/merge после проверки и отдельные release/production/delete gates. Старые слова «отдельные права» не требуют повторного согласия на уже разрешённое действие. |
| 5 | У T015 нет неоднозначного продуктового решения; неизвестные серверные факты остаются T006/T009–T011. |
| 6 | SC-001/004 и открытые T005/T015/T012/T013 сохраняют пределы технической и общей готовности. |

Повторно перечитано после дополнения примечаний: infra — **13 checked /
0 unchecked**, requirements — **6 checked / 0 unchecked**, всего **19/0**.
Эти отметки относятся к качеству требований, не к приёмке реализации.

## Источники и SHA256

Обязательные документы перечитаны полностью после сжатия контекста, до
изменения списков. В затронутых поддеревьях apps/macos и specs/290 более
близких AGENTS.md/AGENTS.override.md не найдено. Исторические ссылки не
использованы как новая приёмка продукта или разрешение серверных действий.

| Источник | SHA256 |
|---|---|
| AGENTS.md | `4bdbcd97dbb86b560cc5cf5294684d7adfbe85a1a39716765145072aa840ae77` |
| .specify/feature.json | `e0c8945b90a89e044a9c35efb16d5dbb6b8a6caad68f6ff71e9ffca81c927177` |
| .specify/memory/constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| docs/prd-voice-layer-final.md | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| docs/current-product-status.md | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| docs/agent-guidance/README.md | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| docs/agent-guidance/document-reading.md | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| docs/agent-guidance/spec-kit-flow.md | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| docs/agent-guidance/development-process.md | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| docs/agent-guidance/product-gates.md | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| docs/agent-guidance/release-and-validation.md | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| spec.md | `f30b3e407e7d900ff8517a0dc022ee04a41fee57ae9c236e2587ee3c0fa485e5` |
| plan.md | `732d18600f90e96e49f244ad9c2805aa441bfdc5b4be3b3c78ea8ab0f04faf65` |
| tasks.md | `c9a0295dba44bfc44522ca75b0d3f3a60f4e0abc89a9c40c4b594f7f38133592` |
| quickstart.md | `68d4901326079596135d32127c83c52da0abf3395cdab39196112a4a004b521b` |
| research.md | `a6bec8f55ff23b876fe93e74a9b6ce8ee5f33b2d4bcf9669e70add8fab7179ed` |
| data-model.md | `ea2ad0764fef4e57c9324459a5e2bf1726d3ddd3e678dddcac08580f797e8468` |
| apps/macos/RecApp/App/TwoBrainRecApp.swift | `796887841384370e22c67a857c83f90db1efa37494db1a21038f605d684b6b0a` |
| apps/macos/Package.swift | `00be33a568134c2addbd2d14a722c4fbb9accf54b915862293373e8cb753eca7` |
| .github/workflows/macos-pr.yml | `5aa2a59ec9d8e5036305e271818ebd0dbb70a587d2c56900f3b6060af228d942` |
| MeetingDetectionRecordingLifecycleTests.swift | `b1647b1d68d79d2efbbfc195192e0ce80c15d06055ea4c7b3632bd7ee80a4c3c` |
| CaptureControlV5Tests.swift | `90ae086a0524f8639828e3b721f082c9b17dd46f92802e80a39a4d4bea69ac9e` |
| DesktopNotificationAppIntegrationTests.swift | `1e4db5acc5fb57d640a3b8a164b90cb85fe8ba420f8d6ccd02a3e90f32f9d43d` |
| MeetingDetectionAppModule.swift | `95f27d00b49c6f1e9ca28725d21e33f378e260d9438c46ad7a1ffc7bb9cf4998` |

Проверяющий изменил только два reviewer-owned списка и этот отчёт.
Код/spec/plan/tasks/pointer, Git/GitHub-состояние, приложения и данные не менял.
Сборки, тесты, typecheck, Dev/production и выпуск не запускал.
