# F136/T020: независимый допуск передачи presenter — 21.10.2026

**Предварительный допуск требований и уточнённого плана: PASS.**
Requirements: **16 checked / 0 unchecked**. Auth-navigation:
**20 checked / 0 unchecked**. Блокеров проверяющего: **0**.

Полоса: существующая **high-risk-product**, ветка
`codex/136-auth-navigation-recovery`, HEAD
`0c0cfba5690dead496aaa1bc00cabbe9cc0b6a76`. Рассмотрено уточнение T020/#7689
в plan §«Изоляция настоящего Workspace в XCTest» и актуальная T019/#7688.
Проверяющий меняет только два назначенных checklist и этот отдельный отчёт.
Код, spec/plan/tasks, Git/GitHub, приложения, Dev и данные не изменялись;
сборки и тесты проверяющий не запускал. Другие локальные изменения сохранены.

## Подтверждённая причина аварии XCTest

В прочитанном `trailing-cancellation-red.log` сборка завершается, затем первый
настоящий Workspace-сценарий аварийно останавливается при создании Coordinator.
Стек подтверждает цепочку: `EmbeddedCabinetWebView.makeCoordinator` →
`DesktopNotificationPresenter.shared` → convenience initializer →
`DesktopNotificationRetirement.run` → `UNUserNotificationCenter.current()`.
Исключение: `bundleProxyForCurrentProcess is nil`, завершение по signal 6.
Проверка поведения отмены в этом запуске не завершилась. Строка Swift Testing
про 0 тестов не является успешным результатом XCTest. Этот журнал нельзя
обозначать продуктовым RED навигации или положительной приёмкой.

Причина согласуется с исходниками. Workspace пока не принимает presenter и
не передаёт его EmbeddedCabinetWebView. Embedded уже имеет optional зависимость
и вычисляет `notificationPresenter ?? .shared` при makeCoordinator. Designated
initializer отдельного presenter не вызывает системную очистку; её вызывает
именно обычный convenience initializer. Но designated initializer тоже пишет
метку `beginCalendarRetirement` в переданный preferences store. Поэтому для
теста необходим свой UserDefaults, а не store с `.standard`.

## Допущенное минимальное изменение

1. Добавить в существующий Workspace optional параметр/свойство
   `notificationPresenter`, по умолчанию nil, и передать его в уже существующий
   параметр EmbeddedCabinetWebView. Сохранить обычный production default и
   отложенное вычисление shared. Не менять условие видимости, `.id`,
   навигационный controller, recovery UI или системную очистку уведомлений.
2. Coordinator сохраняет уже переданный presenter и получает authEpoch у него.
   Сейчас notification bridge получает внедрённый экземпляр, а
   synchronizeUserTime читает singleton. Единый экземпляр для bridge и epoch
   устраняет это несоответствие без снятия проверки эпохи авторизации.
3. Настоящий Workspace fixture передаёт свой presenter: отдельные preferences,
   собственная тестовая модель, синтетический contextProvider. Временный
   preferences domain должен очищаться после теста. Нельзя использовать рабочий
   backend, пользовательский preferences store, глобальную подмену singleton
   или общий тестовый флаг. Тест настроек не должен включать реальную запись,
   звук, календарное действие или системную доставку.

Существующий защищённый порядок synchronizeUserTime сохраняется:
согласование cookies → текущие attachment/documentRevision/URL и isActive →
authEpoch того же presenter → refreshContext → повторная актуальность эпохи
и документа → activate. В notification bridge дополнительно остаются точный
адрес страницы настроек, !isLoading, nonce и отзыв соединения при смене эпохи
или auth session. Прямой вызов activate вместо этих проверок не допускается.

Это проводка существующей зависимости в пределах T020. Новая служба,
протокол уведомлений, серверный auth contract или ослабление origin/header
границ не нужны. Все ограничения восстановления завершённого safe currentItem
из прежнего допуска остаются: только accepted provisional cancellation из
loading, та же history item и текущая сессия/привязка; initial/committed,
401/reselection, stale/detach и ресурсные завершения не получают ready.

## Уточнение прежнего заключения о T019

Прежний отчёт `review-trailing-cancellation-preimplementation-20261021.md`
слишком сильно подтвердил причину 4337458144 чтением строк. Он не учёл,
что routePolicy получает путь через Foundation URL.path до точного сравнения.
Его утверждение о доказанном отказе границы для завершающего слеша отзывается
настоящим уточнением; исторический отчёт не переписан.

Независимо прочитан `trailing-slash-red.log`: оба настоящих WebKit сценария
прошли на исходном продукте, **2 PASS / 0 FAIL**, до правки navigation logic.
Сообщённая исполнителем отдельная Swift-проба различает URL.path и
URLComponents.path; проверяющий сам её не запускал. Исходники подтверждают
использование url.path в routePolicy. Поэтому runtime-дефект T019 этим
исследованием не воспроизведён; первоначальный PASS не может стать RED.

Согласование через `.authLogin/.authSignup` и существующий
`isSafeHistoryDocument` допустимо как устранение дублирующего сравнения:
корневой auth допускается тем же общим правилом, вложенные start/verify,
provider/callback и опасные POST остаются исключены. Сохранить обе регрессии
логично: они проверяют два разных корня, стоимость мала и смена границы
важна. Одно объяснение в обсуждении также допустимо, если исполнитель решит
не менять сравнение; оно не доказывает T020 и не заменяет остальные проверки.
Текущие plan/tasks честно фиксируют именно исходный PASS и ограничение вывода.

## Повторная проверка каждого пункта requirements

| Пункт в порядке checklist | Основание текущего PASS |
|---|---|
| 1: нет деталей реализации в спецификации | Spec описывает пользовательские результаты; presenter остаётся в plan. |
| 2: пользовательская ценность | US1–3: вход, безопасная навигация, отсутствие повторов формы. |
| 3: понятный язык | Spec объясняет стабильную страницу, одноразовый переход и границу сессии. |
| 4: обязательные секции | Clarifications, US/AC, Edge Cases, FR, SC, Assumptions заполнены. |
| 5: нет NEEDS CLARIFICATION | Нет неразрешённых маркеров; scope и исключения заданы. |
| 6: однозначность и проверяемость | FR-001–009 и текущие plan/quickstart задают события и запреты. |
| 7: измеримые критерии | SC-001: 10 секунд; SC-002: один запрос; SC-003/004: исходы навигации. |
| 8: независимость SC от реализации | SC оценивают результат пользователя и отсутствие повтора, не выбранный presenter. |
| 9: сценарии приёмки | US1–3 и дополнительная матрица initial/committed/отмена/сессия. |
| 10: крайние случаи | Edge Cases плюс plan: 401/reselection/stale/detach, ошибки и отмена. |
| 11: границы | OAuth/ручная T016 и выпуск отдельно; DI не меняет продуктовый scope. |
| 12: зависимости | Existing server routes, тестовые данные и отдельная ручная приёмка явны. |
| 13: критерии FR | FR сопоставлены с US/AC/SC и задачами текущего среза. |
| 14: основные потоки | Вход, история и формы представлены раздельно. |
| 15: измеримые исходы | Требования определяют SC; текущая реализация и её приёмка не заявлены. |
| 16: детали не проникли в spec | Новое техническое решение ограничено plan/tasks. |

## Повторная проверка каждого пункта auth-navigation

| Пункт | Основание текущего PASS |
|---|---|
| CHK001 | Key Entities, FR-002/003, data-model: stable/transient различены. |
| CHK002 | US1/3 и OAuth continuation: sign-in и provider-link разделены. |
| CHK003 | FR-004 и session transition table: вход/выход/истечение/reselection. |
| CHK004 | Assumptions и FR-007: серверные методы, providers и session storage вне изменений. |
| CHK005 | FR-001/003/007 запрещают повтор и подмену POST на GET. |
| CHK006 | FR-002–005 и contract invariant 3: общие правила всех поверхностей. |
| CHK007 | FR-004, plan и contract: route/identity до успешной границы; 401 сразу. |
| CHK008 | FR-006: нормальные встречи/настройки сохраняются; отмена не означает новую сессию. |
| CHK009 | SC-001/002, US1 AC и отдельные OAuth задачи. |
| CHK010 | US2 AC и SC-003/004: обычная и transient history, Reload/Back/Forward. |
| CHK011 | Edge Cases, FR-008, initial/committed cancellation matrix. |
| CHK012 | FR-007 и product-gates: нет секретов и содержимого в evidence; isolated defaults. |
| CHK013 | FR-009 сохраняет доступные имена и состояние нативных кнопок. |
| CHK014 | Assumptions, FR-007 и plan исключают server workaround. |
| CHK015 | Quickstart: разрешённые тестовые данные и единственный GRAF Dev, metadata-only. |
| CHK016 | T019/020/T017 отделены от открытых T004/T011/T012/T016. |
| CHK017 | FR-001/006: ordinary POST success/error/cancel без повтора; T020 видимость отдельно. |
| CHK018 | FR-004, plan: current identity/session guards и немедленный отказ 401/reselection. |
| CHK019 | Исходный T019 PASS, crash до T020, будущий RED/GREEN и ручная приёмка разделены. |
| CHK020 | Общий root-only safe predicate; вложенные auth действия не становятся документами истории. |

Пункты подтверждают качество требований и плана, не выполненность продукта.
Оба checklist после записи повторно прочитаны целиком; итог 16/0 и20/0.

## Следующие обязательные доказательства

Основной исполнитель проверяет актуальность analyze и issue sync, включая
файл Workspace в T020/локальном указателе владения. Затем сначала только
проводка зависимости и изоляция fixture, после неё настоящий T020 RED на
неизменённом navigation logic. Для T019 сохранить исходный 2/2 PASS.
После исправления T020 нужны настоящие Workspace/DOM/history проверки после
SwiftUI reconciliation, initial/committed отрицательные случаи, повторная
активация recording и notification settings с тем же presenter и отзывом
устаревшей эпохи/документа. Отдельно сохранить прежние 401/reselection,
stale/detach, resource/синтетические terminal и повторы адресов.

Далее quickstart, convergence, независимое итоговое ревью и новые
governance-fast/macos-pr/pr-metadata на точном SHA/основе через общий validator.
T017, OAuth T004/T011/T012, ручная T016 и вся F136 остаются открытыми.
Выпуск, развёртывание, установка и live-состояние GitHub этим допуском не
подтверждены. Legacy Impact: untouched; новых путей совместимости нет.

## Прочитанные документы и контрольные суммы

После сжатия контекста полностью перечитаны AGENTS, guidance index,
document-reading, development-process, codex-worktrees, spec-kit-flow,
конституция, PRD, current-product-status, product-gates, release-and-validation,
активные spec/plan/tasks/quickstart/research/data-model/contract/validation,
оба checklist. Исходники прочитаны в применимых местах. Применён code-reviewer;
checkout/preflight не выполнялись из-за узкого назначения без запуска тестов.

| Документ | SHA256 |
|---|---|
| AGENTS.md | `4bdbcd97dbb86b560cc5cf5294684d7adfbe85a1a39716765145072aa840ae77` |
| guidance README | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| document-reading | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| development-process | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| codex-worktrees | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| spec-kit-flow | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| release-and-validation | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| spec | `6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668` |
| plan с DI и T019 ограничением | `ea68c95e6eea751b193f934ff038572af573dee15fbc0ce29423d6809c242e3b` |
| tasks с Workspace в T020 | `6f45332b2d11ae58af45cd930f309c12a2319868d196289f490be87af4ea039b` |
| quickstart | `9167952e3e862622cc9154dfc272bcc9344be6343a25e8ed86a28f6c7ee3eb19` |
| research | `e49a028936a317a75e21afc6b4f554b04bab19f8175bb0635f3eb377fb2603a8` |
| data-model | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| contract | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
| validation | `e26b894edb95cec2810d70b833885fc707252eb8256bae5fb0d23507c43d7186` |
| Workspace.swift | `c62897a32cd0bc2b7b020697a7f91bf51ab0cc693ec9c59beb4a1113747ab70e` |
| EmbeddedCabinetWebView.swift | `8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078` |
| NotificationSettingsBridge.swift | `90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca` |
| DesktopNotificationPresenter.swift | `01c6c4bf5dac1fb2e05f6132249fccb66a1472eeb3a64ccb6ad95576386d632a` |
| DesktopNotificationRetirement.swift | `fc2a3cfbefdccc630a490b2a73623a7d16a556dacba27c549da680b9789f5073` |
| WorkspaceTests.swift до DI | `586a58f60d796dabf2e4aaa41cffa7f7496dab8927bc20c9b48d6d2c0181eddb` |
| trailing-cancellation-red.log | `cc91c9e23cfab5143291ef7811a6c103af6c7c58d05b97596deb2ef1e060db10` |
| trailing-slash-red.log | `52e2787a34dc439ea51373ac8b247f3dc812f8e5f743ce2f17d9f6cce021c571` |
