# Независимое ревью плана F136 — 21.10.2026

Проверяющий: `/root/review_f290_infra`. Ветка:
`codex/136-auth-navigation-recovery`; HEAD:
`a42b4ce6004531ea0439d5568b7930440b2a67b0`.
Полоса: существующий `high-risk-product`, T005/T006/T010/T018 и проверка T017.

**PASS требований и плана. Блокеров предварительного допуска: 0.**
Оба списка требований проверены по каждому пункту: requirements **16/0**,
auth-navigation **20/0**, всего **36 checked / 0 unchecked**.
Это предварительный допуск к ограниченному исправлению. Код ещё не исправлен,
замечание PR не снято, текущие тесты и GitHub checks этим отчётом не приняты.

## Источники и проверенная причина

Непосредственно прочитаны AGENTS, guidance index, document-reading,
codex-worktrees, spec-kit-flow, development-process, release-and-validation,
конституция, полный PRD, полный current-product-status и product-gates.
Повторно прочитаны spec, plan, tasks, quickstart, research, data-model,
контракт lifecycle и оба checklist активной F136. Указатель feature.json и
check-prerequisites подтверждают F136; исторические пути других фич не
используются для выбора текущей работы.

Текущее [замечание 4312424786](https://github.com/yshishenya/graf/pull/7668#discussion_r4312424786)
прочитано через GitHub API: оно относится к HEAD выше и
`EmbeddedCabinetWebView.swift`, исходная строка 542. Проверка только для чтения
подтвердила `observeNavigationRequest` на строках 649–657: небезопасный запрос
немедленно меняет URL-наборы, хотя новый документ ещё может не появиться.
`navigationDidFail` и `navigationDidCancel` очищают ожидающее состояние,
но прежний безопасный GET не восстанавливают. `didCommit` сейчас отсутствует.

Просмотрены controller и связанные callers: attach/detach, start/redirect,
finish/fail/cancel, resource/download terminals, response policy,
Back/Forward/Reload и отбрасывание устаревшей WKNavigation. В существующем
настоящем WebKit fixture есть отправки форм и история, но сценарии ошибки и
отмены проверяют прежде всего сессию и сохранение WebView. Они не доказывают
восстановление `canReload` и выбора прежней GET-записи после отказа формы.
Поэтому отсутствие новых регрессий нельзя заменить прежним общим PASS.

## Соответствие исходным критериям

Дополнение plan от 21.10 конкретизирует FR-002/003/005/006/008, SC-002–004,
US2 и текущую приёмку ordinary POST. Нового способа входа, серверного метода,
состояния сессии или разрешённого внешнего origin оно не вводит.

До фактической замены документа неудавшийся POST к тому же адресу оставляет
прежнюю GET-запись безопасной. После настоящего `didCommit` новая POST-запись
уже не разрешается для повтора, даже если `didFinish` не произошёл. Настоящий
завершённый GET может восстановить безопасность своей записи, сохраняя запрет
старых POST-записей того же адреса. Синтетический GET в finish и завершение
ресурса не подтверждают новый документ. Это согласуется с уточнением spec
от 19.10 и не ослабляет немедленную защиту при 401/выборе пространства.

Существующие T005/T006/T010 покрывают исправление общего lifecycle и проверки
истории. T018 сохраняет root-only auth predicate и проверяется на отсутствие
регрессии; её старая отметка сама по себе не доказывает новый сценарий.
Новая отдельная фича или второй механизм отката URL-наборов не требуются.
Итоговая проверка и новые доказательства принадлежат открытой T017.

## Все пункты requirements

Нумерация — позиция пункта внутри существующего раздела.

| Пункт | Текущее основание | Итог |
|---|---|---|
| Content Quality 1 | FR описывают результат и запрет повтора; выбор didCommit оставлен plan | PASS |
| Content Quality 2 | US1–US3: завершить вход, сохранить полезную историю, не повторять форму | PASS |
| Content Quality 3 | Русские пользовательские сценарии и результаты понятны без алгоритма WebKit | PASS |
| Content Quality 4 | Scenarios, Requirements, Entities, Success Criteria, Assumptions заполнены | PASS |
| Requirement Completeness 1 | Открытых NEEDS CLARIFICATION нет; новый план раскрывает существующий критерий ошибки/отмены | PASS |
| Requirement Completeness 2 | FR-002/003/006/008 и plan21.10 различают прежний GET и новый принятый POST | PASS |
| Requirement Completeness 3 | SC-001–004 задают срок, число запросов, безопасность и доступность навигации | PASS |
| Requirement Completeness 4 | SC описывают наблюдаемое поведение, не структуру наборов истории | PASS |
| Requirement Completeness 5 | US1–US3, текущая приёмка и plan21.10 покрывают положительный и отрицательный исход формы | PASS |
| Requirement Completeness 6 | Edge Cases и plan охватывают cancel/error/303/stale/same-URL/сессию | PASS |
| Requirement Completeness 7 | Clarifications, plan и tasks отделяют T004/T011/T012/T016, merge/release/deploy | PASS |
| Requirement Completeness 8 | Assumptions/quickstart: текущие серверные маршруты, синтетический WebKit fixture, отдельный GRAF Dev | PASS |
| Feature Readiness 1 | FR-001–009 соотнесены с US/SC; новые исходы конкретизируют FR-002/003/005/006/008 | PASS |
| Feature Readiness 2 | Основные вход, обычная история и формы сохранены; новый случай уточняет US2 | PASS |
| Feature Readiness 3 | Покрытие измеримыми критериями достаточно; пункт не означает исполненный продукт | PASS |
| Feature Readiness 4 | Новая техническая стратегия находится в plan, продуктовые критерии не подменены алгоритмом | PASS |

## Все пункты auth-navigation

| Пункт | Текущее основание | Итог |
|---|---|---|
| CHK001 | Key Entities, FR-002/003 и data-model различают стабильный документ и одноразовый переход | PASS |
| CHK002 | US1/US3 и OAuth continuation различают первичный вход и подключение провайдера | PASS |
| CHK003 | FR-004 и текущая приёмка задают вход/выход/expiry/reselection | PASS |
| CHK004 | FR-007/Assumptions/plan исключают серверные методы, провайдеры и хранение сессии | PASS |
| CHK005 | FR-001/003/007, уточнение19.10 и plan21.10 запрещают повтор и превращение POST в GET | PASS |
| CHK006 | FR-002–005 и plan сохраняют общее правило для кнопок/жестов/recovery/restart; неоднозначный жест закрыт | PASS |
| CHK007 | FR-004 и контракт задают стабильную цель до успешной границы и немедленную защиту при401 | PASS |
| CHK008 | FR-006/US2 и plan21.10 сохраняют прежний GET при непринятом POST, блокируют принятый POST | PASS |
| CHK009 | US1/SC-001/002 определяют одно действие и безопасный исход для email/VK/Яндекс | PASS |
| CHK010 | US2/SC-003/004 и plan21.10 охватывают Reload/Back и прежние Back/Forward/жесты | PASS |
| CHK011 | Edge Cases/FR-008/plan включают provider cancel, form/server error, rate-limit и restart | PASS |
| CHK012 | FR-007/Assumptions/plan запрещают секреты, cookies, коды и содержимое встреч в доказательствах | PASS |
| CHK013 | FR-009 сохраняет доступные имена и согласованность состояния навигации | PASS |
| CHK014 | FR-007/Assumptions/контракт сохраняют существующие серверные маршруты без обхода | PASS |
| CHK015 | Quickstart T016 требует разрешённые тестовые данные и только технические итоги | PASS |
| CHK016 | Clarifications/plan/tasks отделяют текущий срез от OAuth и установленной T016 | PASS |
| CHK017 | FR-001/006/текущая приёмка сохраняют сессию при success/error/cancel без повтора | PASS |
| CHK018 | FR-004/текущая приёмка/plan требуют настоящую текущую identity, deferred success и немедленную защиту401 | PASS |
| CHK019 | Spec/quickstart/plan отделяют RED, локальный GREEN, GitHub exact-SHA и ручную приёмку | PASS |
| CHK020 | Data-model/research/T018 оставляют стабильными только корневые login/signup | PASS |

## Обязательная регрессионная проверка исправления

Перед приёмкой кода требуется следующая матрица на настоящем WKWebView в
существующем loopback fixture. Сначала воспроизвести отказ на текущем коде;
не объявлять RED для случая, который ранее не отказывал.

1. Безопасный GET U, затем один POST U с сетевой ошибкой до `didCommit`:
   прежние currentItem/документ/WebView/сессия сохранены, loading завершён,
   Reload доступен. Явный Reload создаёт только GET, а не повтор POST.
2. Такой же POST U с отказом response policy до commit (например503) и
   отдельная явная отмена предварительной загрузки. Прежний GET пригоден для
   Reload и возврата через native Back/Forward; старые POST не реабилитированы.
3. POST U действительно проходит `didCommit`, затем завершается ошибкой или
   остановкой до `didFinish`. Зафиксировать реальный commit; новый currentItem
   запрещён для Reload и истории. Одного искусственного вызова didFail после
   успешного finish недостаточно для доказательства этого порядка.
4. Сохранить существующий сценарий POST U → новый настоящий GET U:
   Reload/Back/Forward нового GET работают, старый POST пропускается,
   неоднозначный WebKit gesture отклоняется, счётчик POST не растёт.
5. Проверить current identity до мутации при `didCommit`. Устаревший commit/
   finish/fail после новой навигации не меняет её pending state или историю.
   Не восстанавливать отвергнутую identity по одному совпадению URL.
6. Сохранить POST→303 GET, ordinary success/error/cancel без смены сессии,
   resource404/download terminal после superseded GET, attach/detach и
   сброс pending state. Эти пути не сертифицируют прежний POST как GET.
7. Сохранить вход/выход со стабильными route/request identity до границы,
   немедленную защиту401/reselection, root-only login/signup, billing и
   origin/header policy. Для401/reselection правило сохранения прежнего GET
   не разрешает доступ к старой защищённой сессии.

Перенос только на `didFinish` без защиты принятого, но незавершённого POST
не соответствует пункту3 и plan21.10. Снятие unsafe по URL целиком без учёта
старых WKBackForwardListItem тоже не соответствует исходным критериям.
Использовать существующий lifecycle, без второго реестра откатов и без
дополнительного автоматического запроса для «восстановления».

После профильных RED/GREEN выполнить весь DesktopCabinetWorkspaceTests,
DesktopCabinetRoutePolicyTests и текущий quickstart, затем независимое ревью
реализации и converge. Будущий разрешённый коммит требует всех трёх GitHub
checks на новом exact SHA/base через validate-pr-checks.py. Результаты старого
SHA и этого предварительного чтения не заменяют новые проверки.

## Ограничения и владение

Изменены только этот отчёт и примечания двух checklist. План с дополнением
21.10 принадлежит исполнителю и сохранён. Код, spec, tasks, Git/GitHub,
приложение, тестовые данные, коммиты, выпуск и развёртывание не менялись.
Сборки и тесты не запускались. Для этого предварительного ревью достаточно
чтения и проверки diff; оно не подтверждает работоспособность приложения.
T004/T011/T012, ручная T016 и итоговая T017 остаются отдельными этапами.

## Проверенные версии документов

SHA-256 файлов после полного чтения; пути ниже относительно корня репозитория.

```text
384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b  AGENTS.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d  docs/agent-guidance/codex-worktrees.md
5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887  docs/agent-guidance/spec-kit-flow.md
9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5  docs/agent-guidance/product-gates.md
736e720fb3a8b81cd4012980af41ece57a1218cc5d8f1b6aafd304e1380d1a5d  docs/agent-guidance/development-process.md
e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d  docs/agent-guidance/release-and-validation.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2  docs/prd-voice-layer-final.md
25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16  docs/current-product-status.md
6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668  specs/136-auth-navigation-recovery/spec.md
a24736cfdfd1b794c64ac9f58a83b8e182fe4c7f816bf60c7a5a5cafd9bcba10  specs/136-auth-navigation-recovery/plan.md
5420dd90e6c4f3dcc94ab88a9fd0a77356904285c00c809a8cdde622f6fe0141  specs/136-auth-navigation-recovery/tasks.md
5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2  specs/136-auth-navigation-recovery/research.md
ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac  specs/136-auth-navigation-recovery/data-model.md
3d3be9800e385c3e90e7b5568c022636bb41668c80e103818f09acdcc80bf5a1  specs/136-auth-navigation-recovery/quickstart.md
fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f  specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md
dca71fb3eaf1fd9609daca1adec01691c8f9d9e62d48887c4d8203189c2a3dfa  apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
8e8d1cef5d86543fa35fed11c6e7d615c390cdbc605ff0aa80af3e4db83deed8  apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

Оба checklist после внесения примечаний перечитаны и пересчитаны. Все36
существующих пунктов качества требований подтверждены; неподтверждённых0.
Поведение нового кода и проверки будущего SHA остаются непроверенными
зависимостями следующего этапа и не объявляются PASS.
