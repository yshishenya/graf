# F211/T109 — независимая проверка требований confirm

Дата: 2026-10-31. Ветка `codex/211-macos-runner-migration`.
Основа: `9b3edf7351b1421bac821db04b061a71891057c8`.
Полоса: `active Spec Kit slice`, качество требований FR064/SC026 перед кодом,
с сохранением высокорисковых границ подтверждения действия и доверия WebKit.

**Итог: SCOPED PASS требований. P1: 0; P2: 0; CRITICAL: 0; HIGH: 0.**
Это не приёмка реализации или нового SDK-прохождения. Полный независимый
analyze и дальнейшие проверки, перечисленные ниже, остаются обязательными.

## Область чтения и владение

Прочитаны целые новые дополнения FR064 в spec, A14/T109 в plan/quickstart,
T109 и зависимость T106 в tasks; окружающие FR059–063/SC026 и A14.
Конституция и весь runner-image checklist прочитаны непосредственно.
Повторно прочитаны AGENTS, guidance index и применимые Spec Kit risk/checklist
правила; применён навык code-reviewer. Указатель `.specify/feature.json`
совпадает с F211, указанными веткой/основой и T105–T109.

Прочитан весь `EmbeddedCabinetJavaScriptConfirmTests.swift` с шестью тестами
и подготовкой. В реальном WebView исходнике прочитаны объявления alias,
Coordinator/его состояние, весь confirm request/cancel/finish, trust predicate,
и места отмены при detach/смене навигации/ошибке/закрытии/завершении процесса.
Поиск consumers выполнен по репозиторию, а не только одному файлу.
Остальные 3000+ строк WebView и весь исторический массив F211 не выдаются
за новую полную приёмку; это проверка конкретного дополнения и его зависимостей.
Предыдущие CHK001–007 сохранены как уже принятые требования; их формулировки
и отметки побайтно не меняются, все пункты перечитаны.

Разрешены только этот новый отчёт и отметка/примечание runner-image checklist.
Код, spec/plan/tasks/quickstart, конституция, Git/GitHub, приложение и БД
reviewer не изменяет. Общие продуктовые требования не принимаются заново.

## Доказанный исходный отказ

Источник: [run41222159260](https://github.com/yshishenya/graf/actions/runs/41222159260).
Прочитан точный excerpt `/tmp/f211-confirm-mismatch-excerpt.txt`;
в полном `/tmp/f211-native-attempt4.log` проверены source checkout,
предупреждения compiler, ошибки конкретного теста и итог XCTest.
Журнал связан с `9b3edf7351b1421bac821db04b061a71891057c8`.

- Compiler показывает optional WKUIDelegate callback requirement с
  `@escaping @Sendable (Bool) -> Void`; candidate имеет дополнительную
  изоляцию **самого замыкания** `@MainActor @Sendable (Bool) -> Void`.
  `@MainActor` метода/Coordinator и атрибут callback — разные части типа.
- Предупреждение `nearly matches optional requirement` означает, что одной
  успешной сборки недостаточно. Проверка настоящего Objective-C selector
  `webView:runJavaScriptConfirmPanelWithMessage:initiatedByFrame:completionHandler:`
  в тесте дала false; затем отсутствует настоящий NSAlert.
- Тестовое сообщение фиксирует завершённые navigation/WebKit loading=false;
  перенос ожидания или обход guard не исправляет неправильное объявление.
- SDK note прямо содержит стандартный async requirement
  `webView(_:runJavaScriptConfirmPanelWithMessage:initiatedByFrame:) async -> Bool`.
  Его использование не требует нового callback-adapter, условной SDK ветви
  или добавления второго делегата.
- Исходный результат: 1296 tests, 9 прежних skipped, 4 failures
  (1 unexpected). Это один отказ; дубли строк общего итога не суммируются.
  Он сохранён и не объявляется новым PASS.

Прежняя широкая совместимость T107 не доказывает регистрацию этого optional
метода. FR064 явно уточняет найденное продуктовое исключение, оставляя
остальные четыре alias и их methods без расширения объёма работ.

## Проверка CHK008 по требованиям

| Часть | Фактическое основание | Решение |
| --- | --- | --- |
| Причина и область | FR064 называет точные run/SHA, nearly-matches/selector=false и один метод/alias; T109 владеет существующим WebView файлом | PASS |
| Стандартный протокол | В исходном SDK note есть нужный async requirement; план использует его, сохраняет MainActor и стандартный withCheckedContinuation | PASS требований; компиляция ещё обязательна |
| Consumers | Код содержит ровно объявление alias на строке 14 и использование в заменяемом методе на строке 2107; других рабочих consumers по поиску нет | PASS |
| Trust guards | Сохраняются main frame, same-origin, отсутствие credential URL, разрешённый route, attached navigation, isActive, отсутствие terminated/loading, видимое окно и свободный sheet | PASS |
| Однократность | Существующий UUID/pending guard, очистка pending/наблюдателей перед ответом и игнорирование старого id не меняются; continuation возобновляется только тем же callback | PASS |
| Lifecycle | Отмена при навигации/ошибке/detach/window close/process termination остаётся; отказ guard сразу возвращает false | PASS |
| Настоящий UX | Тот же NSAlert; Return/Cancel/Escape=false, явный Continue=true, прежние кнопки и монитор клавиатуры | PASS |
| Приёмка | Сохранены все шесть confirm tests, настоящий selector/JavaScript/NSAlert, full XCTest/ContractValidation, новый pinned native и exact-SHA validator до T106 | PASS требований |

FR064, A14/T109 plan, T109 task и quickstart задают одну и ту же границу:
меняется объявление optional method и удаляется ставший ненужным alias.
В существующий request передаются те же webView/message/frame URL/main-frame;
новая Task, другой поток, свой диалог или изменение guard/таймаутов не разрешены.
Продолжение должно получить единственный ответ существующего request:
при immediate refusal — false, при отложенном завершении — подтверждённый Bool.
Новый код с continuation пока не существует и этим выводом не принят.

## Сохраняемые шесть проверок

1. `testConfirmationTrustBoundary`: разрешённые routes, чужой origin,
   credential URL, служебные/неизвестные/file/about URL и subframe.
2. `testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction`: настоящий
   loopback HTTP документ, настоящий selector, didFinish/loading/sheet readiness,
   JavaScript confirm, настоящий NSAlert, Return и Escape, результат false,
   невыполнение защищённого действия. Этот тест нельзя заменить прямым request.
3. `testNativeButtonsCancelByDefaultAndContinueExplicitly`: настоящий click,
   cancel по умолчанию и явное продолжение, false/true.
4. `testDuplicateAndLateCompletionCannotResolveNewRequest`: duplicate request,
   late UUID, отмена и отсутствие повторного callback.
5. `testUnavailableWindowsAndSubframesCancel`: занятый sheet, скрытое/отсутствующее
   окно, subframe — немедленный false без pending.
6. `testLifecycleCancelsExactlyOnceAndProcessExitRejectsOldDocument`: navigation,
   detach, close, process, позднее подтверждение и повтор старого документа.

Существующая матрица покрывает изменяемую границу без новой тестовой службы.
Тот факт, что тесты существуют, не объявляется их прохождением. Число 1296
и прежние девять допустимых пропусков не дают права добавлять новые skips
или обходить исходные сценарии. Окончательная приёмка обязана показать
настоящую регистрацию метода на закреплённой среде, а не только локальный SDK.

## Конституционные границы и дальнейшие ворота

Решение сохраняет видимое подтверждение и явный отказ по умолчанию,
однократность, доверенный источник и жизненный цикл (конституция II/VI/VII).
Продуктовые данные, capture, consent, storage, egress, подпись и доступ
не меняются. Нет оснований для нового расширения архитектуры или полномочий.

Следующие обязательные условия: отдельный scoped analyze → минимальный код
→ focused шесть confirm cases → полный XCTest/ContractValidation в локальной
поддерживаемой среде → независимое implementation review/converge → новый
настоящий native на Swift6.0.3/SDK15.2 и все exact-SHA/base checks общего validator.
Нужны отсутствие nearly-matches для этого метода, true существующего selector,
настоящий alert и прежние ответы/ограничения. Старое доказательство не заменяет
новый точный SHA, а локальный результат не заменяет pinned SDK.

T109, T108, T106 и #7834 остаются незавершёнными; общая F211 и внешние
установленные/выпускные условия не принимаются. GRAF Dev, release-full,
публикация и production reviewer не запускает.

## Итог checklist и действия reviewer

Все восемь пунктов reread: **8 отмечено / 0 не отмечено**.
CHK001–007 и прежняя история сохранены; изменена только CHK008 и добавлено
примечание. Открытых P1/P2, CRITICAL/HIGH к качеству этого дополнения нет.
Тесты, сборки, приложение, БД, CI и сеть не запускались. Лично выполнены
read-only чтения/search/diff/status/HEAD, вычисление hashes и `git diff --check`.
Контрольные суммы ниже фиксируют прочитанные байты и не доказывают исправление.

## SHA256 источников

| Путь | SHA256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `specs/211-optimize-ci-cd/spec.md` | `79dc194215121e2298f7383ac2533e168abac6d88f1cf9feca982cc38da67d0d` |
| `specs/211-optimize-ci-cd/plan.md` | `75f3a225908cf9196d814a987ec3cecae8390f312d81517ebbf8a766d3807725` |
| `specs/211-optimize-ci-cd/tasks.md` | `eea9be4f7077df62d75fd2abb05f0a35a646383bc329fe763a71259fbc573d03` |
| `specs/211-optimize-ci-cd/quickstart.md` | `280b5746004b6aadd4cb462057ae47b4c203649894a5c3d09eb8689959ad4923` |
| `specs/211-optimize-ci-cd/checklists/runner-image.md` | `47859126f192e155da8d4c2ff87ccb726a78b9f59dd1bec7dd77af1507771e90` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `3bc5278f9f42c2a90b7b68957ae65ae2ba0ebcfb640c66d6b31c6f1e56e2788f` |
| `apps/macos/Shared/Tests/EmbeddedCabinetJavaScriptConfirmTests.swift` | `2e6e3043b5228f7590bb8ac45a44568dcaa40d3f16313c3737072735b50b338e` |
| `/tmp/f211-confirm-mismatch-excerpt.txt` | `74c84f5badd26398ae86b5c9af973873996208dde5a13bfb3049d831f3fad02b` |
| `/tmp/f211-native-attempt4.log` | `5f55af55b9467d3f37655b3fafba3dae5357158440f20e2f50fc050d28494d6d` |
