# Независимая проверка требований и дизайна F285

Дата: 2026-10-02. Проверяющий: отдельный агент focus_requirements_review.
Область: качество требований и дизайна до генерации tasks.md. Проверка не подтверждает реализацию, GRAF Dev, GitHub-проверки или публикацию. Проверяющий изменяет только requirements.md, ux.md и этот отчёт.

## Доказательства по пунктам

| Чеклист / пункт | Решение и конкретное основание |
| --- | --- |
| requirements CHK001 | Подтверждено: spec.md, User Stories 1–2, FR-001–008 и SC-001–004 описывают наблюдаемые результаты; техническое решение вынесено в plan.md/research.md/contracts/focus.md. |
| requirements CHK002 | Подтверждено: spec.md, US1/US2, Edge Cases, Assumptions; data-model.md исключает изменения API/данных; plan.md, Complexity Tracking ограничивает область. |
| requirements CHK003 | Подтверждено после уточнения: contracts/focus.md явно определяет .meeting-title-input inset shadow 2px одновременно с удалением outline, native editable поле и измеримые ограничения; quickstart.md включает оба случая и обязательную матрицу. |
| requirements CHK004 | Подтверждено: spec.md FR-003–006/008; quickstart.md разделяет автоматические, единственный GRAF Dev, точный SHA, PR и подписанный выпуск; конституция V–VII и product-gates.md сохраняют эти обязательства. |
| ux CHK001 | Подтверждено после уточнения: FR-001/004/005 и contracts/focus.md разделяют контейнеры, действия, web border-bearing поля, borderless редактор названия и NativeSettingsComboBox с единой внутренней 2px линией. |
| ux CHK002 | Подтверждено: spec.md US1.2, FR-002/007, SC-003, Edge Cases; data-model.md запрещает создание navigation request при Start/Stop. |
| ux CHK003 | Подтверждено: spec.md FR-001/003, US1.3; plan.md Phase 1, research.md Контейнеры, data-model.md и contracts/focus.md сохраняют scroll и assistive target только по явному запросу. |
| ux CHK004 | Подтверждено: spec.md FR-005/007 и Edge Cases; plan.md Complexity Tracking, contracts/focus.md Dialog/Notification, research.md Область сохраняют удержание/возврат фокуса, keyboard loop и semantic decorations. |
| ux CHK005 | Подтверждено после уточнения: FR-006 задаёт ≥3:1; contracts/focus.md и quickstart.md требуют light/dark, web high contrast/forced-colors и native Increase Contrast, единый контур без изменения размеров, mouse/Tab и сохранение editing/стрелок/Return/Escape. |
| ux CHK006 | Подтверждено: spec.md FR-007, Assumptions; plan.md Constitution Check; product-gates.md UX Reference Fidelity и PRD §29 разрешают исправление известного дефекта и требуют доступности/независимой реализации без чужих ресурсов. |
| ux CHK007 | Подтверждено: spec.md FR-008/SC-004 и quickstart.md; local-development.md требует единственный Dev и clean SHA; release-and-validation.md и macos-notarization.md разделяют PR и frozen release-full, Developer ID, notarization, stapling, Gatekeeper и публичный appcast. |

## Замечания первого прохода и их разрешение

1. cabinet.css:5976–5992: .meeting-title-input имеет border:0 и собственный outline. Убирать этот outline по общему правилу border-bearing полей можно только с явной видимой заменой без изменения геометрии. Разрешено: contracts/focus.md/research.md требуют inset shadow 2px одновременно с удалением outline; quickstart.md включает редактор названия, mouse/Tab и contrast.
2. plan.md/research.md добавили NativeSettingsComboBox.Control.draw; contracts/focus.md и ручная матрица quickstart пока не называют нативное редактируемое поле, единый внутренний stroke, повышенный контраст и сохранение клавиш выбора. Разрешено: contracts/focus.md добавил отдельную строку NativeSettingsComboBox и абзац о mouse/Tab, обеих темах, Increase Contrast, сохранении bounds и запрете открытия popup от одного focus. quickstart.md добавил отдельный сценарий с editing/стрелками/Return/Escape.
3. Ошибки текущих input представлены aria-invalid и отдельным текстом, явного error-border у input в cabinet.css не найдено. Это не утверждение о дефекте реализации. Требование сохранять семантические рамки остаётся обязательным; рамки статуса, выбора и ошибки вне целевых полей не удалять.

## Область и чтение

Прочитаны spec.md, plan.md, research.md, data-model.md, contracts/focus.md, quickstart.md, оба checklist; конституция, guidance README/spec-kit-flow/product-gates/local-development/release-and-validation/macos-notarization/codex-worktrees; соответствующие PRD §29 и current-product-status, существующие CSS/NativeSettingsComboBox/desktop source. Ветка, feature.json и check-prerequisites.sh подтверждают F285. tasks.md отсутствует: результат относится только к предшествующей генерации задач проверке качества требований; после генерации tasks требуется отдельное повторное чтение и сверка.

Первый проход: requirements 3 checked / 1 unchecked; ux 5 checked / 2 unchecked; всего 8 checked / 3 unchecked. После уточнения основным агентом повторно полностью прочитаны spec.md, plan.md, research.md, data-model.md, contracts/focus.md, quickstart.md и оба checklist. Все три замечания качества требований получили конкретное подтверждение выше.

Окончательно для предшествующего задачам этапа: requirements 4 checked / 0 unchecked; ux 7 checked / 0 unchecked; всего 11 checked / 0 unchecked. Чеклисты перечитаны после правки. Результат: PASS качества требований и дизайна. tasks.md всё ещё отсутствует: после его генерации необходимо отдельное чтение и сверка. Реализация, GRAF Dev, GitHub-проверки и релиз не подтверждены этим PASS.

## Повторная сверка после генерации tasks.md

Полностью прочитаны tasks.md (T001–T009), обновлённый plan.md, contracts/focus.md, quickstart.md, feature.json и оба чеклиста. Область owned_paths включает три целевых файла реализации, два Swift-набора, браузерный сценарий, pytest-вход, фрагмент изменений и документы F285; risk_lane согласован с high-risk-ux.

| Требования | Задачи и доказательство согласованности |
| --- | --- |
| FR-001/002/003, US1 | T002 перед T003 требует воспроизводимого отказа, сохраняет раскрытие/scroll/идентификаторы, assistive focus и дочерние действия. T009 включает остановку и Tab/notification navigation в единственном Dev. |
| FR-004, native editable | T004 перед T006 требует реальную геометрию/контур, editing/keyboard/AX; T006 сохраняет currentEditor/keyWindow и repaint lifecycle. quickstart включает обе темы и Increase Contrast. |
| FR-004/005/006, web fields | T005 перед T007 требует computed styles, ≥3:1, размеры, click/Tab, code, borderless title, интерактивные non-field controls и forced colors. pytest-вход включает сценарий в существующий запуск CI; quickstart требует отдельного Chromium/WebKit без засчитывания пустого/пропущенного результата. |
| FR-005/007, ограничения | T003/T006/T007 ограничены конкретными файлами и запрещают потерю действий, semantic/error/selection рамок и глобальное отключение outline. Modal/notification проверки остаются обязательными по quickstart; новые данные/API/зависимости не вводятся. |
| FR-008, SC-004, выпуск | T001 требует analyze/issue sync до кода; T008 требует независимого просмотра, локальной валидации/converge, evidence/changelog и отдельного одобрения коммита; T009 требует Dev на clean SHA, PR checks, merge, frozen release-full, CD dry-run/execute, Developer ID/notarization/stapling/Gatekeeper и публичных артефактов. Источник, сервер, публичные байты и установленная версия отделяются. |

Противоречий требований между задачами и проверенным дизайном не найдено. HTML combobox в браузерной задаче проверяет web-поверхность; подтверждение нативного поля принадлежит T004/T006 и GRAF Dev, не браузерному результату. T004/T005 используют разные файлы; порядок tests-before-code сохранён в зависимостях.

После повторного чтения чеклистов: requirements 4 checked / 0 unchecked; ux 7 checked / 0 unchecked; всего 11 checked / 0 unchecked. Независимые требования/дизайн/tasks gate: PASS. Это не выдаёт ещё не выполненные analyze/issue sync/реализацию/Dev/PR/release за завершённые.

## Независимое чтение реализации и проверок

Прочитаны текущий git diff целевых Swift/CSS-файлов, новые browser/pytest файлы, связанные CaptureControlView/TwoBrainRecApp и lifecycle NativeSettingsComboBox. Повторно прочитаны обновлённые договор, research, задачи и оба чеклиста. Проверка кода выполнена read-only; изменён только этот отчёт.

Существенных ошибок в рассмотренном diff не найдено. Shell убирает только две лишние keyboard цели: @AccessibilityFocusState и accessibilityFocused сохраняют binding, scrollTo, идентификаторы и явный navigation request. Реальный CaptureControlView уже имеет accessibilityElement(children:.contain) и доступное имя, поэтому модификатор применяется к существующей доступной группе. Команды управления и audio/data/permissions не изменены.

NativeSettingsComboBox.swift:125–133 сохраняет currentEditor/keyWindow guard; stroke 2px строится по inset bounds 1px с радиусом 4px и покрывает существующую границу без изменения размера. Существующие invalidate paths в Field.becomeFirstResponder, controlTextDidBeginEditing/controlTextDidEndEditing и close сохранены. Никакие editing/selection/keyboard/AX обработчики не изменены.

cabinet.css:6385–6403 применяет единый контур только к редактируемым полям и исключает checkbox/radio/range/file/button/submit/reset/image/hidden/color. Borderless title использует отдельную ширину внутреннего контура 2px. Select сохраняет native appearance, размеры и стрелку: внутренний outline 2px offset -2px решает отсутствие inset shadow в WebKit. Forced colors сохраняет Highlight outline без shadow; offset -2px покрывает нативную границу, даже когда UA перекрашивает transparent border. Общие :focus-visible действий и semantic border вне целевых полей остаются.

### Подтверждённые доказательства и границы

- Прочитан /tmp/graf-f285-swift-before.log: до исправления 2 регрессионных проверки получили 33 failed assertions. Это конкретно подтверждает воспроизводимость статического Shell-контракта и нативного рисования, не заменяет живую проверку приложения.
- Прочитан актуальный /tmp/graf-f285-swift-after.log: выбранные 75 Swift checks прошли с 0 failures; финальный новый testActiveContourStaysInsideUnchangedBoundsInEveryAppearance прошёл. Он проверяет реальный stroke bitmap, 2px внутри bounds, ≥3:1, четыре NSAppearance и исчезновение после blur при явном draw. Существующие проверки keyboard/editing/AX сохранены.
- git diff --check прошёл при независимом чтении.
- Browser script действительно проверяет mouse/keyboard активный элемент, computed contour, geometry, light/dark, contrast more и ≥3:1 с основными соседними поверхностями; borderless title, web combobox, code и native HTML select имеют явные сценарии. Non-field controls сохраняют 2px outline; после mouse button нет клавиатурной рамки. Chromium forced-colors проверяет отдельный Highlight contour; WebKit uses Option+Tab для all-control navigation при системном ограничении обычного Tab.
- Скрипт не засчитывает неизвестный engine или ошибку browser запуска; pytest entrypoint выполняет реальный Node subprocess с check=True и timeout. Финальные browser/pytest результаты на момент записи ещё не прочитаны из отдельного validation evidence; сообщение основного агента о PASS WebKit не подменяет проверенный отчёт/вывод.
- Shell regression — source-contract test, а не подтверждение фактического VoiceOver focus. Native bitmap не доказывает composite CALayer layout установленного приложения и переключение активных окон. Browser synthetic fixture не подтверждает embedded WKWebView. Эти границы должны остаться явными в T009/validation.md.
- Существующий local-recording browser scenario проверяет Enter и Escape restore после удаления; полная ручная матрица удержания Tab, notification navigation и stop/start остаётся в T009.

Итоги reread: requirements 4 checked / 0 unchecked, ux 7 checked / 0 unchecked, всего 11 checked / 0 unchecked; требования/дизайн/tasks gate остаётся PASS. Предварительный code review: значимых code findings нет; финальные результаты локальных проверок требуется дописать отдельно. Dev, PR exact SHA, release-full, прод и публичные/установленные артефакты этим review не подтверждены.

## Финальная сверка после layer/forced-colors и T010

Лично перечитаны актуальный diff NativeSettingsComboBox/Shell/CSS/Swift tests/local-recording fixture, новая T010, user-time.js и финальные журналы.

- /tmp/graf-f285-swift-after.log: финальный запуск 2026-10-02 22:40 завершён 75 tests, 0 failures. Новый тест проверяет не только stroke bitmap/contrast/blur, но и совпадение непрозрачного CALayer.borderColor с focusRing во всех четырёх появлениях. /tmp/graf-f285-layer-before.log подтверждает 4 отказа этой дополнительной проверки до синхронизации layer color.
- /tmp/graf-f285-webkit.log и /tmp/graf-f285-chromium.log: оба содержат завершённый PASS contour/keyboard/geometry/themes/contrast. /tmp/graf-f285-delete-focus.log: завершённый PASS. Эти доказательства лично прочитаны и дополняют ограничения прежнего прохода.
- Native draw теперь вызывает updateColors перед stroke. updateColors сохраняет controlBackgroundColor, устанавливает focusRing для active currentEditor/keyWindow и separatorColor иначе. Field.becomeFirstResponder, begin/end editing и coordinator.close по-прежнему помечают Control для перерисовки; appearance callback обновляет цвета. Geometry и editing contracts не изменены.
- T010 ограничена двумя строками тестовой страницы: graf-time-preferred задаёт действительно существующий приоритет пользовательского часового пояса. user-time.js:6–7 выбирает preferred, иначе пояс устройства; graf-timezone:61 относится к серверному/первичному контексту, поэтому смена только его не могла принудительно переключить пояс. Исправление fixture соответствует production-контракту без изменения production JS, входит в append-only convergence и имеет ownership #7452. Результаты baseline failure, исправленного полного local-recording PASS и 102 pytest PASS пока известны из сообщения основного агента; до записи validation.md/отдельного вывода не объявлены лично прочитанными журналами.

### Замечание по порядку модификаторов доступности

В прочитанной версии custodyDetailRow accessibilityFocused расположен перед accessibilityElement(children:.combine/.contain) и label. Это не доказанный runtime дефект: source-contract тест не раскрывает построение AX группы. Основному агенту рекомендовано минимально поставить binding после окончательного grouping/label, чтобы цель явного перехода была прикреплена к итоговой доступной группе. captureControls уже получает доступную группу из CaptureControlView и этого дополнительного локального grouping не имеет. Фактический переход VoiceOver в обоих случаях обязателен в T009.

Итоги перечитанных checklist неизменны: requirements 4 checked / 0 unchecked; ux 7 checked / 0 unchecked; всего 11 checked / 0 unchecked. Качество требований/дизайна/tasks PASS. Значимых ошибок в конечном проверенном производственном diff не установлено; замечание порядка AX передано для устранения неоднозначности. Live Dev/PR/release/production/published/installed evidence остаётся pending T009. Проверяющий изменил только checklist-review.md.


## Итоговое независимое review перед коммитом — 2026-10-02

Повторно прочитаны конечный производственный diff Shell/NativeSettingsComboBox/CSS и две строки исправленной local-recording fixture, полный validation.md и оба reviewer-owned чеклиста. Независимо вычислены SHA-256 всех восьми файлов из validation.md: 8 совпадений, 0 расхождений. Это связывает локальные доказательства с содержимым файлов до коммита; GitHub exact-SHA и выпуск требуют отдельных проверок.

Рекомендация по порядку модификаторов доступности выполнена: в custodyDetailRow accessibilityFocused теперь стоит после accessibilityElement и accessibilityLabel. Лично прочитан /tmp/graf-f285-shell-final.log: финальный запуск AppControlAccessibilityTests от 2026-10-02 22:43:14 завершён 25 tests, 0 failures. Прежнее замечание по неоднозначности привязки к доступной группе закрыто по исходному коду. Фактический переход VoiceOver этим результатом не подтверждён.

Ранее лично прочитанные журналы 75 Swift tests, Chromium, WebKit и meeting-delete-focus остаются действующими для совпавших файлов; затронутая перестановкой Shell часть проверена повторно 25 тестами. Результаты 102 pytest, полного исправленного local-recording-focus, Ruff, governance/bootstrap doctor, changelog и issue canon теперь записаны основным агентом в validation.md. Они учтены как предоставленный отчёт о валидации, без утверждения, что проверяющий лично прочитал отсутствующие отдельные журналы. Чужие задачи, validation.md и tracker проверяющий не изменял.

Блокирующих замечаний по конечному рассмотренному коду и качеству требований/дизайна нет. T008 может использовать этот отчёт как независимую проверку реализации. Документированное одобрение пользователем коммита после локальных проверок учтено; этот reviewer не запрашивает повторного разрешения и не выполняет Git/release действий.

До завершения T009 остаются pending: единственный GRAF Dev на чистом SHA исправления, ручные Stop/start/Tab/notification/поля/диалоги, фактический VoiceOver и встроенный WKWebView; GitHub проверки на точном SHA и актуальной основе; merge, frozen release-full, CD dry-run/execute; Developer ID/notarization/stapling/Gatekeeper/Sparkle, опубликованные ZIP/PKG/appcast и фактически установленная версия. Открытость этих этапов не означает пробела требований и не превращает локальный PASS в runtime/release/production PASS.

После записи отчёт и оба чеклиста перечитаны. Итоги: requirements 4 checked / 0 unchecked; ux 7 checked / 0 unchecked; всего 11 checked / 0 unchecked. Итоговая независимая проверка рассмотренного кода: PASS без блокирующих замечаний в доступной области. Проверяющий изменил только checklist-review.md.


## Независимая сверка исправлений первого CI — T011

2026-10-02: прочитан текущий diff NativeSettingsComboBoxTests.swift, spec.md и append-only T011 (ownership #7452). Рабочий diff содержит только эти три файла до записи настоящего отчёта; производственные Shell/NativeSettingsComboBox/CSS не менялись.

В luminance удалена сложная связка zip/reduce, вместо неё введена linearize с явными входом и результатом CGFloat и три отдельных взвешенных компонента. Ветвление на 0.04045, деление на 12.92, добавка 0.055, делитель 1.055, степень 2.4 и коэффициенты 0.2126/0.7152/0.0722 сохранены. Суммирование имеет прежний порядок red→green→blue; assertions, порог контраста 3 и перечень проверяемых appearance не изменены. Ослабления проверки не обнаружено.

Legacy Impact содержит единственную Classification: untouched и нулевые legacy_new/unowned_legacy/expired_exceptions. Это соответствует ограниченному исправлению контура/лишних Tab stops без изменения старых API, форматов данных или совместимости. Проверяющий отдельно выполнил python3 scripts/validate-legacy-impact.py --feature specs/285-refine-focus-indicators/spec.md: legacy-impact: OK. T011 сохраняет связь с исходным неуспешным CI на 00dc275bf9bfcdea1dfacbb31c2754fdbfb13a36 и требует повторной независимой проверки.

Лично прочитаны предоставленные журналы повторного запуска:

- /tmp/graf-f285-swift-ci-fix.log: NativeSettingsComboBoxTests завершён 2026-10-02 23:10:53, 28 tests / 0 failures; XCTest выполнен, отдельный завершающий Swift Testing вывод 0 tests не подменяет этот результат.
- /tmp/graf-f285-pytest-final.log: 102 passed, 1 существующий PytestAssertRewriteWarning, 7.49s.
- /tmp/graf-f285-local-recording-final.log: полный local recording focus сценарий stable keyed nodes/changed controls/checkbox handoff/time context/safe removal PASS.

Повторная SHA-256 сверка таблицы validation.md подтверждает неизменность остальных семи файлов, включая все три производственных файла. Единственный новый хеш NativeSettingsComboBoxTests.swift: 51420bb9378b0809c420cb82b0979c370ae1154a9ef610384c7245742be2b8b8. В прочитанном validation.md пока указан прежний хеш; основному агенту требуется дополнить доказательства T011 и обновить эту строку перед новым checkpoint/коммитом. Проверяющий validation.md не изменял. Прежняя запись 8 совпадений описывает исторический проход до T011.

Код и требования T011: PASS, блокирующих замечаний по реализации нет. Локальные результаты не доказывают успешный повторный GitHub CI на новом SHA; он остаётся отдельным обязательным этапом. Ручная матрица единственного GRAF Dev, фактический VoiceOver/WKWebView и выпуск/прод по-прежнему pending T009.

После записи отчёт и оба reviewer-owned чеклиста перечитаны: requirements 4 checked / 0 unchecked; ux 7 checked / 0 unchecked; всего 11 checked / 0 unchecked. Проверяющий изменил только checklist-review.md, не менял код, spec/tasks/validation, Git/GitHub, приложение или выпуск.
