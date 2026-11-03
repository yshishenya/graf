# F136: итоговое независимое ревью среза и T018

Дата: 2026-10-18. Reviewer: `review_f290_infra`.
Ветка: `codex/136-auth-navigation-recovery`.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Режим проверки: **high-risk-product** — авторизация, сессия и native navigation.

## Решение

**Code review: Approved, подтверждённых замечаний к текущему diff нет.**
Проверен весь текущий source/test diff F136, включая T005/T006/T010,
постоянный настоящий WebKit overlap test и T018; прочитан owned changelog.
Это решение относится к перечисленным ниже SHA256 незакоммиченных файлов,
а не к базовому HEAD как к коммиту исправления.

Текущий полный повтор автоматических проверок **PASS**: 1245 различных
тестов, 1243 PASS, 2 SKIP, 0 FAIL. Исходный полный запуск имел реальный FAIL
одного notification focus test; он сохранён и описан ниже. Это не доказательство
устранения причины нестабильности фокуса и не основание скрыть исходный сбой.

Приёмка всей F136, OAuth, установленного GRAF Dev, PR на точном SHA и выпуска
этим ревью не подтверждается. Текущие convergence, validation и tasks
дополнительно перечитаны после оформления основным исполнителем. T005/T006/
T010/T018 отмечены как локально реализованные, соответствующие issues явно
остаются OPEN до принятого PR; T017, OAuth и ручная приёмка остаются открытыми.
Reviewer эти файлы не меняет.

## Проверенный код и тесты

- Обычные GET/POST, результат формы, 303, серверная ошибка и отмена не создают
  новую границу сессии. Pending boundary очищается при неуспешном завершении;
  завершённая отмена перестаёт оставлять экран в loading.
- Успешный переход между корневым auth document и защищённым документом
  подготавливает границу в контроллере. Coordinator сначала сохраняет конечные
  route, request identity и cabinet state, затем публикует boundary для SwiftUI.
  Немедленная защита при 401/выборе пространства сохранена; защищённые команды
  и Home недоступны для истёкшей сессии.
- Проверены pending URL, active WKNavigation, redirect confirmation и отклонение
  устаревшего завершения. Замена прежнего classifier по navigationType согласована
  с настоящими 303/307 и JS navigation; эти действия не различаются надёжно
  только по типу action.
- В T018 общий safe-history predicate повторно использует safe-document predicate.
  Вложенные `/login/...` и `/sign-up/...` исключены из истории и обоих вариантов
  SwiftUI identity. Корневые страницы, trailing slash и query остаются доступными;
  POST не становится safe history. Живая route policy остаётся прежней и допускает
  текущие auth actions в WebKit. URL helper не хранит содержимое запросов.
- Новые tests используют настоящий Coordinator, NSHostingView, SwiftUI `.id`,
  WebKit и локальный HTTP listener с синтетическими данными. Проверяются число
  запросов, идентичность WebView, число boundaries, сохранение видимого результата
  и запрет истории прежней сессии. Новый root-only matrix проверяет все три
  потребителя политики, положительные корневые и отрицательные вложенные адреса.
- Changelog перечисляет T005/T006/T010/T017/T018 и сохраняет ограничения OAuth,
  ручной приёмки и выпуска. Серверные контракты, cookies и права не менялись.

Прежний P2 по вручную заданному callback order остаётся **снятым как
неподтверждённый достижимый сбой**, а не исправленным новым кодом.
Основание: `review-native-overlap-disposition-20261018.md`.
Настоящий overlap test подтверждает замену ожидающей формы новой без remount.
`old_response_send=written` означает запись ответа в соединение; получение
позднего redirect WebKit не доказано. Произвольный порядок вручную вызванных
callbacks не подменяет настоящую последовательность WebKit.

## Текущие автоматические результаты

Журналы находятся вне репозитория:
`/Users/yshishenya/Documents/Codex/2026-10-18/f136-native-navigation-order/`.
Reviewer самостоятельно прочитал журналы и пересчитал started/distinct/
passed/failed/skipped; числа не взяты только из итогового сообщения исполнителя.

| Запуск | Различных | PASS | SKIP | FAIL | Результат |
|---|---:|---:|---:|---:|---|
| t018-red.log | 1 | 0 | 0 | 1 | Исходная реализация: 32 assertion failures нового root-only test |
| t018-focused-green.log | 83 | 83 | 0 | 0 | Текущие workspace/route tests, 2.150s |
| t018-full-swift.log | 1245 | 1241 | 3 | 1 | Исходный полный запуск, 104.069s |
| t018-focus-recheck.log | 1 | 1 | 0 | 0 | Тот же упавший test отдельно, 0.512s |
| t018-full-recheck.log | 1245 | 1243 | 2 | 0 | Полный повтор без изменения source/tests, 100.129s |

В первом полном запуске упал
`DesktopNotificationAccessibilityTests.testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus`:
6 assertions в одном тесте, первая — отклонённый запрос фокуса,
`active=true, running=false, policy=0, canKey=false`. Этот test и notification
код отсутствуют в F136 diff. Отдельный повтор и полный повтор на неизменном
коде прошли; в полном повторе test выполнился за 0.302s. Этого достаточно
для регистрации непостоянного результата, но недостаточно для установленной
причины. Ни ошибку продукта, ни исключительно внешнюю причину этим не объявляем.

Дополнительный focus SKIP первого полного запуска —
`DesktopNotificationPromptLifecycleTests.testKeyFocusHoldAndHoverOverlapResumeOnlyAfterBothEnd`:
среда не подтвердила фокус обычного AppKit-окна. Во втором полном запуске
он прошёл за 0.242s. Остались только два необязательных image-export SKIP:

- `DesktopNotificationCardTests.testCardSurfacesCanBeCapturedForReferenceComparison` —
  не задан `GRAF_CARD_SNAPSHOT_DIR`, экспорт не запрошен.
- `SystemAudioPermissionUXTests.testRenderSyntheticPermissionStates` —
  не задан `GRAF_PERMISSION_PREVIEW_DIR`.

Также прочитаны текущие журналы: `spec-kit-governance: OK`,
`changelog-fragments: OK`, `ContractValidation: PASS`. `git diff --check` PASS.
Reviewer новых оконных тестов не запускал и не конкурировал с исполнителем
за системный фокус. Старый зелёный набор 1244 до T018 не подменяет новый 1245.
Обновлённый `t018-validation-receipt.json` прочитан; его source/test/fragment
и все пять log SHA256 совпали с независимо вычисленными reviewer значениями.

`convergence-20261018.md` сверяет 9 FR, 4 SC, сценарии и края требований;
нового неучтённого пробела текущего среза не найдено. Вся F136 не объявлена
завершённой: продолжение OAuth, ручная приёмка и принятие имеют прежних
владельцев. Снятый synthetic finding не переименован в исправленный.

## Требования и оставшиеся этапы

Оба reviewer-owned checklist снова перечитаны полностью и пересчитаны:
requirements — **16 checked / 0 unchecked**;
auth-navigation — **20 checked / 0 unchecked**;
всего — **36 checked / 0 unchecked**. Хеши не изменились со времени допуска
T018; обоснования требований находятся в
`checklist-review-before-t018-20261018.md`. Отметки относятся к требованиям,
не означают завершения OAuth или ручной приёмки. Checklist в этом проходе
не менялись.

T004/#4731, T011/#4738, T012/#4739 и T016/#4743 остаются открытыми.
Реальные OAuth/provider-link, сквозная ручная матрица в единственном
`/Applications/GRAF Dev.app`, установка, выпуск и production не аттестованы.
T017 включает дальнейшие gates; Approved code review не завершает их молча.
До коммита требуется разрешение пользователя после проверки по AGENTS.md;
до слияния — актуальные обязательные проверки PR на его точном коммите и базе.

Reviewer создал только этот собственный отчёт. Код, tests, specs, plan, tasks,
GitHub, коммиты, releases и чужие изменения не менялись.

## SHA256 проверенного состояния

| Файл | SHA256 |
|---|---|
| apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift | `c1d60d7951d3a8ac40ddff8453b0ab48ed44eff34eac0e69a30bbf6ac73eaf1b` |
| apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift | `32888dc19731c9d53ca28415b45698c81456ef2df87e0af6bd2ee42d8a14c839` |
| changes/unreleased/F136.yaml | `5157ebc1ca2e3eb3cdf77daceb0ab9c4e2814326112362bda8d9c1529d5f169f` |
| checklists/requirements.md | `3f770ca061291eeab1d834cd1b9e9e9519b530c592fb5bb80830bb8e12660ea0` |
| checklists/auth-navigation.md | `5d5bd9ca041e99d3d02d2d6df48c382d95ccfba8c3db088bdaa82ff9c69334b6` |
| tasks.md | `853c0806cd20407c949292c3bd33697b86517585ecc311f4b09eb6928e72e359` |
| validation.md | `a2a24a0af7973a545c532cdf069ad8cf30b639641256f9a003ad51a1e7e9e4c1` |
| convergence-20261018.md | `20f37347ef1921fc030602f9cf50c410fa0aeceb012a9a8b94db85a4e1a9f45d` |
| t018-validation-receipt.json | `d694cf5a67f9dc1c37708f414b4110253fbacbb90eae27636d7fc498f07402a2` |
| t018-red.log | `23bef1aef9ed9b8b66b3afd7545aac5f6eb6115e894264af5d7abdaa50e8cf1a` |
| t018-focused-green.log | `4fec2be974b17fd4632efa71c0e20aea3bdbf7db95c14f434d24fe6ec7c062a4` |
| t018-full-swift.log | `e838e4a4b6269aa964ce97185b0a1145c907115a6539d2a6a258ac8e1e97ab9a` |
| t018-focus-recheck.log | `fc56d0d3ff5851f7a3960d5f71525d2bed81fe7efbaa9971438e1bdf1fca5d11` |
| t018-full-recheck.log | `b9d027826e131be814d48c64782d3eb8ed1cec4790e04fbc87145e10c8551c87` |
| t018-governance.log | `59cfeb588ee423427af9f09c0dfe4d3d2b36bbfcca7bbb8b49ba0f0b1ce6bceb` |
| t018-changelog.log | `59aed550d1f8a68e1f37c0dd400db59c03d429b3af8d478fd8577c281aad06b8` |
| t018-native-contracts.log | `17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87` |
