# F136: независимое ревью требований перед реализацией

Дата:2026-10-17. Reviewer:`review_f290_infra`.
Ветка:`codex/136-auth-navigation-recovery`.
HEAD:`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Risk/validation lane:**high-risk-product**, auth/session/native navigation.

## Результат

**PASS требований:35 checked/0 unchecked.** Проверен заново каждый пункт
обоих checklist; архивные x сами по себе основанием не являлись.
Блокирующих недостатков качества требований не найдено. Это не подтверждение
реализации, входа через провайдера или ручной приёмки. Перед кодом основной
агент отдельно подтверждает актуальный analyze и issue-sync gates.

## Артефакты и границы

Прочитаны активные spec, plan, tasks, research, data-model, contract
cabinet-navigation-lifecycle, quickstart и оба checklist. Проверены текущая
ветка, .specify/feature.json и вывод check-prerequisites --json --paths-only:
все указывают F136; канонический BRANCH136 в prerequisites не заменяет
фактическую ветку codex/136 выше.

Применены AGENTS, guidance README/codex-worktrees/spec-kit-flow/product-gates/
release-and-validation; constitution7.1.0, особенно III/VI/VII; продуктовые
границы PRD §4.y и текущий merged status F013/F047. Сервер владеет auth и
кабинетом, native Record/Stop остаётся независимым; текущий срез не меняет
серверные маршруты, способы входа, session storage, доступы и UI-assets.

T005/T006/T010/T017 — текущий срез. T004/T011/T012 OAuth continuation и T016
manual smoke остаются открытыми. Исторические T013–T015 и старые числа
тестов не принимаются за текущую проверку. Фрагмент F136.yaml и текущий
validation принадлежат T017; архивная задача про root CHANGELOG не разрешает
новое изменение root-файла. Продуктовый код reviewer не менял и не запускал.

## Specification quality:16 пунктов

У встроенного checklist нет ID; R01–R16 ниже соответствуют точному порядку
его пунктов сверху вниз, каждый пункт имеет отдельное основание.

| Пункт | Решение | Текущее основание |
|---|---|---|
| R01 No implementation details | checked | Spec описывает действия пользователя и наблюдаемую безопасность; языки, framework, классы и конкретный алгоритм находятся в plan/research. GET/POST/401 задают границы поведения существующего сервера. |
| R02 User value/business needs | checked | US1 убирает повтор входа/белый экран; US2 делает навигацию безопасной; US3 исключает повтор настроек и потерю сессии. |
| R03 Non-technical stakeholders | checked | Given/When/Then и объяснения приоритета используют понятные пользовательские результаты; технические названия ограничены точными границами. |
| R04 Mandatory sections | checked | Есть user scenarios/testing, requirements, key entities и measurable success criteria. |
| R05 No clarification markers | checked | NEEDS CLARIFICATION отсутствует; новая Session2026-10-17 явно уточняет ordinary POST, immediate fail-closed, текущий срез и ограничения. |
| R06 Testable/unambiguous requirements | checked | FR001–009 задают запрет повтора, allowed history, session boundary, жесты, normal navigation, secrets, recovery и accessibility; текущая приёмка конкретизирует200/error/cancel. |
| R07 Measurable success criteria | checked | SC001: не более10s белого экрана после окончания сетевого ответа; SC002: ровно один исходный action в контролируемой отправке; SC003/004: наблюдаемые history/navigation результаты. |
| R08 Technology-agnostic outcomes | checked | SC измеряют результат входа, число действий и безопасную навигацию без привязки к SwiftUI/WKWebView алгоритму. |
| R09 Acceptance scenarios | checked | Каждый US содержит независимую проверку и Given/When/Then; текущий срез добавляет error/cancel, ordering,401/reselection и stale callback. |
| R10 Edge cases | checked | Отмена, закрытие/restart, rate limiting, server error, session expiry во время формы/callback, query-параметры и normal pages перечислены. |
| R11 Bounded scope | checked | Assumptions и Session исключают server auth/storage/access policy changes; текущий срез отделён от OAuth/manual и production. |
| R12 Dependencies/assumptions | checked | Существующие providers/routes, разрешённые синтетические данные, безопасный server error и отдельный тестовый аккаунт для T016 описаны в spec/plan/quickstart. |
| R13 FR acceptance criteria | checked | FR001/007→SC002; FR002–005→US2/SC003; FR006→US2/US3/SC004; FR008→US1.3/edge cases; FR009→native controls assertions в plan и T010. |
| R14 Primary flows | checked | US1 email/VK/Яндекс; US2 buttons/gestures/session history; US3 forms/provider link. Отложенные задачи не скрывают пользовательский сценарий. |
| R15 Measurable feature outcomes | checked | Сценарии и проверки способны оценить SC001–004; отметка означает полноту требований, не уже достигнутые результаты. |
| R16 No implementation leakage | checked | Спецификация не предписывает remount/.id/controller fields; эти детали находятся только в design. Session identifier используется как наблюдаемый инвариант сохранности сессии. |

## Auth navigation:19 пунктов

| Пункт | Решение | Текущее основание |
|---|---|---|
| CHK001 | checked | Key Entities и FR002–003 разделяют stable document и one-shot; data-model задаёт GET, persistence/history/recovery. |
| CHK002 | checked | US1 и US3, continuation table none/primarySignIn/providerLink; provider link сохраняет авторизацию, primary sign-in меняет session presentation. |
| CHK003 | checked | FR004, edge cases и data-model session table описывают login/logout/expiry/workspace reselection. |
| CHK004 | checked | Spec Assumptions/FR007, plan Technical Context и contract Boundary исключают новые методы, providers, storage и server workaround. |
| CHK005 | checked | FR001/003/007 запрещают replay и изменение метода исходного action; текущая приёмка явно запрещает превращать POST в GET. |
| CHK006 | checked | FR002–005, US2 и contract invariant3 распространяют единый predicate на buttons, gestures, updateNSView и automatic recovery; restart восстанавливает stable document. |
| CHK007 | checked | FR004 и текущая приёмка: успешная граница после stable route/request identity;401/reselection немедленно закрывает прежнюю защищённую историю. |
| CHK008 | checked | FR006 и US2.2 сохраняют ordinary meetings/settings history; transient/prior-session entries отдельно исключены FR003–005. |
| CHK009 | checked | Каждый email/VK/Яндекс flow перечислен в US1/SC001–002 и T016; безопасная ошибка допустима, автоматический повтор запрещён. |
| CHK010 | checked | US2.1–2, FR005–006, SC003–004 и contract Observable behavior определяют Back/Forward/Reload и transient/normal targets. |
| CHK011 | checked | Edge cases и FR008 описывают provider cancel, server/form error, rate limit, restart и безопасный ручной retry. |
| CHK012 | checked | FR007 запрещает secrets/codes/content в диагностике; quickstart явно запрещает accounts/cookies/callback URL и private content в evidence. |
| CHK013 | checked | FR009 требует сохранить accessible names и одинаковое visual/accessibility состояние controls; plan и T010 сохраняют identifiers и проверяют control availability. |
| CHK014 | checked | Contract Boundary и FR007 сохраняют server methods/cookies/headers/provider protocol; research отклоняет GET-handlers workaround и arbitrary external links. |
| CHK015 | checked | Автотесты только synthetic без accounts; T016 отдельно требует разрешённый тестовый аккаунт и единственный GRAF Dev, metadata-only evidence. Недоступный стенд не даёт PASS. |
| CHK016 | checked | Session, plan resumed slice и tasks restoration явно отделяют T005/T006/T010/T017 от T004/T011/T012/T016; исторические x не текущая приёмка. |
| CHK017 | checked | FR001/006 и текущая приёмка требуют неизменную session при200/error/cancel, один POST, без GET replay/remount. |
| CHK018 | checked | FR004/current acceptance, data-model/contract уточнения: успешный commit после stable target;401/reselection immediate denial; stale callback не применяет boundary к новой navigation. |
| CHK019 | checked | Research receipt — исходный1PASS/1FAIL; quickstart требует новый RED/GREEN; T016 и неизвестный303 outcome остаются отдельно открытыми. |

## Важные условия прочтения и реализации

Research и contract содержат общую формулировку об отложенном уничтожении
history. Она относится к фиксации успешной стабильной границы, а не разрешает
сохранять доступ после401. Spec FR004, текущая приёмка, data-model и contract
уточнения явно требуют немедленного запрета прежней protected history и
native commands при401/reselection. В реализации и тестах должны быть
подтверждены оба события: немедленная защита и безопасный финальный commit.
Это не разрешение отложить fail-closed до успешной загрузки другой страницы.

Ordinary settings POST не означает смену session даже при failure/cancel;
запрет replay не означает запрет полезных Back/Forward/Reload на normal
documents. Устаревшие callbacks не получают права завершать новую navigation.
Полная матрица должна сохранить billing/download и attach/detach behavior,
как указано в plan; обнаруженная причинная связь с OAuth/303 потребует converge,
а не молчаливого объявления всей F136 готовой.

Основной агент дополнительно сообщил о текущем долге вложенных auth paths
в isSafeDocument/isSafeHistoryRequest. Это не GREEN требований root-only
login/signup и не подтверждение исторического T003. Spec сохраняет эту
границу, tasks явно называют старые x архивными, T004/T011/T012/T016 открыты.
Поэтому качество требований не зависит от предположения, что этот долг уже
устранён. При итоговом review/converge нельзя переносить текущий POST PASS
на незавершённую root-only/OAuth приёмку всей F136.

## Исходное доказательство и ограничения

Прочитан внешний
`/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/F136-boundary-probe-result-20261017.json`:
source_sha совпадает с базой, GET control PASS, settings POST200
FAIL_SESSION_BOUNDARY_CHANGED,2tests/1passed/1failed/0unexpected.
Receipt утверждает source_dirty=false/product_code_changed=false,
installed_GRAF_launched_or_modified=false/real_auth_or_account_data_used=false.
Проверка synthetic loopback с текущей зависимостью проекта не аттестует OAuth,
настоящий вход или installed app. Setup-error, constant binding fixture и
отдельное303 наблюдение исключены из причинного доказательства в receipt.
Reviewer не перезапускал этот опыт и не выдаёт его за GREEN исправления.

Ни GRAF, ни GRAF Dev reviewer не запускал, реальные аккаунты не использовал.
Никаких builds/tests/production/GitHub mutations/commits не выполнял.
Менялись только два разрешённых checklist и этот отчёт.

## Перечитывание и итог

После правок оба checklist перечитаны целиком и пересчитаны:

| Checklist | Checked | Unchecked |
|---|---:|---:|
| requirements.md |16|0|
| auth-navigation.md |19|0|
| Всего |35|0|

Оформление новых reviewer файлов проверено отдельно, потому что вся
восстановленная F136 пока untracked и обычный git diff --check её не охватывает.
Этот PASS снимает только requirements gate; разрешения commit/merge/release
и текущие source/CI/manual evidence им не заменяются.
